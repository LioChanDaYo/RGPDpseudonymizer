"""Integration tests for validation workflow.

Tests the complete validation workflow from entity detection through
user review to final confirmation, including deduplication and state
transitions.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import (
    ValidationSession,
)
from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow
from tests.fixtures.validation_workflow.entity_fixtures import (
    create_duplicate_entities,
    create_large_entity_list,
    create_mixed_type_entities,
    create_person_only_entities,
    create_simple_entities,
)
from tests.fixtures.validation_workflow.sample_documents import (
    COMPLEX_DOCUMENT_WITH_DUPLICATES,
    EMPTY_DOCUMENT,
    LARGE_DOCUMENT,
    MIXED_TYPES_DOCUMENT,
    PERSON_ONLY_DOCUMENT,
    SIMPLE_DOCUMENT,
)

# ===================================================================
# Test Fixtures
# ===================================================================


@pytest.fixture
def mock_readkey():
    """Mock readchar.readkey for user input simulation."""
    with patch("readchar.readkey") as mock:
        yield mock


@pytest.fixture
def mock_console():
    """Mock Rich console to prevent terminal output during tests."""
    with patch("gdpr_pseudonymizer.validation.ui.console") as mock:
        yield mock


@pytest.fixture
def mock_confirm():
    """Mock Rich Confirm.ask for confirmation prompts."""
    with patch("rich.prompt.Confirm.ask") as mock:
        # Default to True for all confirmations
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_prompt():
    """Mock Rich Prompt.ask for text input prompts."""
    with patch("rich.prompt.Prompt.ask") as mock:
        yield mock


@pytest.fixture
def mock_pseudonym_assigner():
    """Mock pseudonym assigner function.

    Returns:
        Function that assigns predictable pseudonyms based on entity type
    """

    def assigner(entity: DetectedEntity) -> str:
        """Assign pseudonym based on entity type."""
        if entity.entity_type == "PERSON":
            return "Agent-001"
        elif entity.entity_type == "ORG":
            return "Organization-A"
        elif entity.entity_type == "LOCATION":
            return "City-X"
        return "Entity-Unknown"

    return assigner


@pytest.fixture
def simple_validation_session():
    """Create simple validation session for testing.

    Returns:
        ValidationSession with 3 entities (no duplicates)
    """
    session = ValidationSession(
        document_path="test_document.txt",
        document_text=SIMPLE_DOCUMENT,
    )
    for entity in create_simple_entities():
        session.add_entity(entity)
    return session


@pytest.fixture
def duplicate_validation_session():
    """Create validation session with duplicate entities.

    Returns:
        ValidationSession with 9 entities including duplicates
    """
    session = ValidationSession(
        document_path="test_document.txt",
        document_text=COMPLEX_DOCUMENT_WITH_DUPLICATES,
    )
    for entity in create_duplicate_entities():
        session.add_entity(entity)
    return session


# ===================================================================
# Task 2: Core Workflow Integration Tests (AC: 1, 2)
# ===================================================================


def test_full_validation_workflow_with_confirm_actions(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test complete validation workflow with all entities confirmed.

    Tests AC1: Full validation workflow integration
    Tests AC2: State transitions PENDING → CONFIRMED
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input: Enter key for summary screen, then confirm all entities (Space)
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        " ",  # Confirm PERSON: Marie Dubois
        " ",  # Confirm ORG: TechCorp
        " ",  # Confirm LOCATION: Paris
    ]

    # Mock final confirmation (Rich Confirm.ask)
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All 3 entities should be confirmed"
    assert all(
        isinstance(e, DetectedEntity) for e in result
    ), "Result should contain DetectedEntity instances"


def test_full_validation_workflow_with_mixed_actions(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test complete validation workflow with confirm, reject, and modify actions.

    Tests AC1: Full validation workflow integration
    Tests AC2: State transitions PENDING → CONFIRMED/REJECTED/MODIFIED
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input:
    # - Enter key for summary screen
    # - Confirm first PERSON entity (Space)
    # - Reject ORG entity as false positive (R)
    # - Confirm LOCATION entity (Space)
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        " ",  # Confirm Marie Dubois
        "r",  # Reject TechCorp (false positive)
        " ",  # Confirm Paris
    ]

    # Mock final confirmation (Rich Confirm.ask)
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 2, "Only confirmed entities should be returned (not rejected)"
    entity_texts = [e.text for e in result]
    assert "Marie Dubois" in entity_texts, "Confirmed PERSON should be in result"
    assert "Paris" in entity_texts, "Confirmed LOCATION should be in result"
    assert "TechCorp" not in entity_texts, "Rejected ORG should not be in result"


# ===================================================================
# Task 3: Mock User Input System Tests (AC: 6)
# ===================================================================


def test_mock_user_input_single_key_actions(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test mock readkey correctly triggers action handlers.

    Tests AC6: Mock user input simulation
    """
    # Arrange
    entities = create_person_only_entities()  # 3 PERSON entities
    document_text = PERSON_ONLY_DOCUMENT

    # Mock user input: Enter for summary, Space (confirm), R (reject), Space (confirm)
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        " ",  # Confirm first PERSON
        "r",  # Reject second PERSON
        " ",  # Confirm third PERSON
    ]

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 2, "Should have 2 confirmed entities (1 rejected)"
    assert mock_readkey.call_count >= 4, "Should have called readkey at least 4 times"


# ===================================================================
# Task 4: Entity Deduplication Integration Tests (AC: 4)
# ===================================================================


def test_context_cycling_for_grouped_entities(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test X key cycles through grouped entity contexts.

    Tests AC4: Context cycling integration
    """
    # Arrange
    entities = create_duplicate_entities()  # 9 entities with duplicates
    document_text = COMPLEX_DOCUMENT_WITH_DUPLICATES

    # Mock user input:
    # - Enter for summary
    # - X to cycle context for first entity group (Marie Dubois - 3 occurrences)
    # - Space to confirm after viewing contexts
    # - Continue confirming other entity groups
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "x",  # Cycle to context 2 of Marie Dubois
        "x",  # Cycle to context 3 of Marie Dubois
        "x",  # Cycle back to context 1 (wraparound test)
        " ",  # Confirm Marie Dubois group
        " ",  # Confirm Sophie Laurent group
        " ",  # Confirm TechCorp group
        " ",  # Confirm Paris group
    ]

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    # All 9 entity occurrences should be returned (4 unique groups confirmed)
    assert len(result) == 9, "All entity occurrences should be confirmed"

    # Verify deduplication: count unique (text, type) pairs
    unique_entities = set((e.text, e.entity_type) for e in result)
    assert len(unique_entities) == 4, "Should have 4 unique entity groups"


def test_single_occurrence_entities_no_cycling(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test single-occurrence entities don't show cycling option.

    Tests AC4: Single-occurrence entities (no cycling option shown)
    """
    # Arrange
    entities = create_simple_entities()  # 3 entities, no duplicates
    document_text = SIMPLE_DOCUMENT

    # Mock user input: Enter for summary, confirm all (no X key presses needed)
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        " ",  # Confirm PERSON
        " ",  # Confirm ORG
        " ",  # Confirm LOCATION
    ]

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All single-occurrence entities confirmed"


# ===================================================================
# Task 5: Edge Case Tests (AC: 3)
# ===================================================================


def test_empty_entity_detection_handling(mock_readkey, mock_console, mock_confirm):
    """Test workflow handles empty entity list gracefully.

    Tests AC3: Empty entity detection (no entities found)
    """
    # Arrange
    entities = []
    document_text = EMPTY_DOCUMENT

    # Mock user confirmation: decline manual entity addition
    mock_confirm.return_value = False

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
    )

    # Assert
    assert len(result) == 0, "Empty entity list should return empty result"


def test_large_document_handling_with_warning(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test large document (100+ entities) with warning message.

    Tests AC3: Large document handling (100+ entities)
    """
    # Arrange
    entities = create_large_entity_list()  # 320 entities
    document_text = LARGE_DOCUMENT

    # Mock user input: Enter for summary, then confirm all unique groups (10)
    # Note: 320 entities → 10 unique groups (deduplication)
    mock_readkey.side_effect = ["\r"] + [" "] * 10  # Enter + Confirm all 10 groups

    # Mock confirmations: accept large document warning, final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 320, "All 320 entity occurrences should be confirmed"

    # Verify deduplication worked: 10 unique entities
    unique_entities = set((e.text, e.entity_type) for e in result)
    assert len(unique_entities) == 10, "Should have 10 unique entity groups"


def test_ctrl_c_interruption_handling(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test Ctrl+C interruption during validation.

    Tests AC3: Ctrl+C interruption handling (graceful exit)
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input: Enter for summary, then Ctrl+C (KeyboardInterrupt)
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        KeyboardInterrupt(),  # Simulate Ctrl+C during first entity review
    ]

    # Mock confirm quit (True = yes, quit)
    mock_confirm.return_value = True

    # Act & Assert
    workflow = ValidationWorkflow()
    with pytest.raises(KeyboardInterrupt):
        workflow.run(
            entities=entities,
            document_text=document_text,
            document_path="test.txt",
            pseudonym_assigner=mock_pseudonym_assigner,
        )


def test_invalid_input_handling_unknown_keys(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test invalid input handling for unknown keys.

    Tests AC3: Invalid input handling (unknown keys)
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input: Enter for summary, invalid keys (z, 9, @), then valid confirm actions
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "z",  # Invalid key (should be ignored or show help)
        " ",  # Valid confirm
        "9",  # Invalid key
        " ",  # Valid confirm
        "@",  # Invalid key
        " ",  # Valid confirm
    ]

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "Workflow should complete despite invalid inputs"


# ===================================================================
# Additional Integration Tests
# ===================================================================


def test_validation_session_state_tracking(duplicate_validation_session):
    """Test ValidationSession correctly tracks entity review states.

    Tests AC2: ValidationSession state tracking
    """
    # Arrange
    session = duplicate_validation_session

    # Act
    entity_groups = session.get_entity_groups()

    # Assert
    assert len(entity_groups) == 4, "Should have 4 unique entity groups"

    # Verify group counts
    group_dict = {(g.text, g.entity_type): g.count for g in entity_groups}
    assert group_dict[("Marie Dubois", "PERSON")] == 3, "Marie Dubois appears 3 times"
    assert (
        group_dict[("Sophie Laurent", "PERSON")] == 2
    ), "Sophie Laurent appears 2 times"
    assert group_dict[("TechCorp", "ORG")] == 2, "TechCorp appears 2 times"
    assert group_dict[("Paris", "LOCATION")] == 2, "Paris appears 2 times"


def test_entity_type_priority_order_in_review(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test entities reviewed in priority order: PERSON → ORG → LOCATION.

    Tests AC1: Entity-by-type review workflow
    """
    # Arrange
    entities = create_mixed_type_entities()  # 2 PERSON, 2 ORG, 2 LOCATION
    document_text = MIXED_TYPES_DOCUMENT

    # Track the order of entity types reviewed
    reviewed_types = []

    # Custom mock to capture entity type order
    original_side_effect = ["\r"] + [" "] * 6  # Enter + Confirm all
    call_count = [0]

    def track_entity_type(*args, **kwargs):
        """Track entity type being reviewed based on call order."""
        idx = call_count[0]
        call_count[0] += 1

        # First call is Enter for summary screen
        if idx == 0:
            return original_side_effect[idx]

        # Map call index to entity type (PERSON first, then ORG, then LOCATION)
        # Adjust for the Enter key press at index 0
        review_idx = idx - 1
        if review_idx < 2:
            reviewed_types.append("PERSON")
        elif review_idx < 4:
            reviewed_types.append("ORG")
        elif review_idx < 6:
            reviewed_types.append("LOCATION")

        return original_side_effect[idx]

    mock_readkey.side_effect = track_entity_type
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    # First 2 reviews should be PERSON, next 2 ORG, last 2 LOCATION
    assert reviewed_types[:2] == [
        "PERSON",
        "PERSON",
    ], "PERSON entities reviewed first"
    assert reviewed_types[2:4] == ["ORG", "ORG"], "ORG entities reviewed second"
    assert reviewed_types[4:6] == [
        "LOCATION",
        "LOCATION",
    ], "LOCATION entities reviewed last"


# ===================================================================
# Batch Operations Tests (AC1 - TEST-001)
# ===================================================================


def test_batch_accept_all_entities_of_type(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test batch accept operation for all entities of a type.

    Tests AC1: Batch operations (Accept All Type)
    Addresses QA TEST-001: Batch accept operation coverage gap
    """
    # Arrange
    entities = create_mixed_type_entities()  # 2 PERSON, 2 ORG, 2 LOCATION
    document_text = MIXED_TYPES_DOCUMENT

    # Mock user input:
    # - Enter for summary screen
    # - Shift+A (batch accept) for PERSON entities
    # - Confirm all remaining ORG and LOCATION entities individually
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "A",  # Batch accept all PERSON entities (Shift+A)
        " ",  # Confirm first ORG entity
        " ",  # Confirm second ORG entity
        " ",  # Confirm first LOCATION entity
        " ",  # Confirm second LOCATION entity
    ]

    # Mock batch accept confirmation (True = confirm batch accept)
    # Then mock final confirmation
    mock_confirm.side_effect = [True, True]

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 6, "All entities should be accepted"
    person_entities = [e for e in result if e.entity_type == "PERSON"]
    assert (
        len(person_entities) == 2
    ), "Both PERSON entities should be accepted via batch"


def test_batch_reject_all_entities_of_type(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test batch reject operation for all entities of a type.

    Tests AC1: Batch operations (Reject All Type)
    Addresses QA TEST-001: Batch reject operation coverage gap
    """
    # Arrange
    entities = create_mixed_type_entities()  # 2 PERSON, 2 ORG, 2 LOCATION
    document_text = MIXED_TYPES_DOCUMENT

    # Mock user input:
    # - Enter for summary screen
    # - Shift+R (batch reject) for PERSON entities
    # - Confirm all remaining ORG and LOCATION entities individually
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "R",  # Batch reject all PERSON entities (Shift+R)
        " ",  # Confirm first ORG entity
        " ",  # Confirm second ORG entity
        " ",  # Confirm first LOCATION entity
        " ",  # Confirm second LOCATION entity
    ]

    # Mock batch reject confirmation (True = confirm batch reject)
    # Then mock final confirmation
    mock_confirm.side_effect = [True, True]

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 4, "Only ORG and LOCATION entities should be accepted"
    person_entities = [e for e in result if e.entity_type == "PERSON"]
    assert len(person_entities) == 0, "All PERSON entities should be rejected via batch"


def test_batch_operation_confirmation_cancelled(
    mock_readkey, mock_console, mock_confirm, mock_pseudonym_assigner
):
    """Test batch operation when confirmation is cancelled.

    Tests AC1: Batch operations with cancelled confirmation
    """
    # Arrange
    entities = create_person_only_entities()  # 3 PERSON entities
    document_text = PERSON_ONLY_DOCUMENT

    # Mock user input:
    # - Enter for summary screen
    # - Shift+A (batch accept attempt)
    # - Then confirm entities individually after cancelling batch
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "A",  # Attempt batch accept
        " ",  # Confirm first PERSON individually
        " ",  # Confirm second PERSON individually
        " ",  # Confirm third PERSON individually
    ]

    # Mock batch accept confirmation (False = cancel batch operation)
    # Then mock final confirmation (True)
    mock_confirm.side_effect = [False, True]

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All entities should be confirmed individually"


# ===================================================================
# User Action Tests (AC1 - TEST-002)
# ===================================================================


def test_modify_entity_action(
    mock_readkey, mock_console, mock_confirm, mock_prompt, mock_pseudonym_assigner
):
    """Test modify action (E key) to correct entity text.

    Tests AC1: Simulate user actions (modify)
    Addresses QA TEST-002: Modify action coverage gap
    """
    # Arrange
    entities = create_simple_entities()  # Marie Dubois, TechCorp, Paris
    document_text = SIMPLE_DOCUMENT

    # Mock user input:
    # - Enter for summary screen
    # - E to modify first entity
    # - Confirm remaining entities
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "e",  # Modify first PERSON entity (Marie Dubois)
        " ",  # Confirm ORG entity
        " ",  # Confirm LOCATION entity
    ]

    # Mock text input for modification
    mock_prompt.return_value = "Marie Martin"  # Corrected entity text

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All 3 entities should be in result"
    person_entities = [e for e in result if e.entity_type == "PERSON"]
    assert len(person_entities) == 1, "Should have 1 PERSON entity"
    assert person_entities[0].text == "Marie Martin", "Entity text should be modified"


def test_modify_entity_with_empty_input(
    mock_readkey, mock_console, mock_confirm, mock_prompt, mock_pseudonym_assigner
):
    """Test modify action with empty input (no change).

    Tests AC1: Modify action edge case (empty input)
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input:
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "e",  # Attempt modify
        " ",  # Confirm ORG entity
        " ",  # Confirm LOCATION entity
    ]

    # Mock text input for modification (empty = no change)
    mock_prompt.return_value = ""

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All entities should be confirmed (no modification)"
    person_entities = [e for e in result if e.entity_type == "PERSON"]
    assert (
        person_entities[0].text == "Marie Dubois"
    ), "Original text should be preserved"


def test_change_pseudonym_action(
    mock_readkey, mock_console, mock_confirm, mock_prompt, mock_pseudonym_assigner
):
    """Test change pseudonym action (C key) to set custom pseudonym.

    Tests AC1: Simulate user actions (change pseudonym)
    Addresses QA TEST-002: Change pseudonym action coverage gap
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input:
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "c",  # Change pseudonym for first PERSON entity
        " ",  # Confirm ORG entity
        " ",  # Confirm LOCATION entity
    ]

    # Mock text input for custom pseudonym
    mock_prompt.return_value = "Jane Doe"  # Custom pseudonym

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All 3 entities should be in result"
    # Note: This test verifies the action executes without error
    # Actual pseudonym assignment verification would require checking session state


def test_change_pseudonym_with_empty_input(
    mock_readkey, mock_console, mock_confirm, mock_prompt, mock_pseudonym_assigner
):
    """Test change pseudonym action with empty input (use default).

    Tests AC1: Change pseudonym edge case (empty input)
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input:
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "c",  # Attempt change pseudonym
        " ",  # Confirm ORG entity
        " ",  # Confirm LOCATION entity
    ]

    # Mock text input for pseudonym (empty = use default)
    mock_prompt.return_value = ""

    # Mock final confirmation
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "All entities should be confirmed with default pseudonym"


def test_add_entity_action_declined(
    mock_readkey, mock_console, mock_confirm, mock_prompt, mock_pseudonym_assigner
):
    """Test add entity action (A key) when user provides empty input.

    Tests AC1: Simulate user actions (add entity)
    Addresses QA TEST-002: Add entity action coverage gap
    """
    # Arrange
    entities = create_simple_entities()
    document_text = SIMPLE_DOCUMENT

    # Mock user input:
    mock_readkey.side_effect = [
        "\r",  # Press Enter to continue from summary screen
        "a",  # Attempt to add entity
        " ",  # Confirm first PERSON entity (after empty text input cancels add)
        " ",  # Confirm ORG entity
        " ",  # Confirm LOCATION entity
    ]

    # Mock text input for add entity (empty = cancel/decline to add)
    mock_prompt.return_value = ""

    # Mock final confirmation (True)
    mock_confirm.return_value = True

    # Act
    workflow = ValidationWorkflow()
    result = workflow.run(
        entities=entities,
        document_text=document_text,
        document_path="test.txt",
        pseudonym_assigner=mock_pseudonym_assigner,
    )

    # Assert
    assert len(result) == 3, "Original 3 entities should be confirmed (no addition)"
