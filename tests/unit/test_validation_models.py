"""Unit tests for validation data models.

Tests ValidationSession, EntityReviewState, UserDecision, EntityReview, and EntityGroup classes.
"""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import (
    EntityGroup,
    EntityReview,
    EntityReviewState,
    UserDecision,
    ValidationSession,
)


def test_entity_review_state_enum() -> None:
    """Test EntityReviewState enum values."""
    assert EntityReviewState.PENDING.value == "pending"
    assert EntityReviewState.CONFIRMED.value == "confirmed"
    assert EntityReviewState.REJECTED.value == "rejected"
    assert EntityReviewState.MODIFIED.value == "modified"
    assert EntityReviewState.ADDED.value == "added"


def test_user_decision_creation() -> None:
    """Test UserDecision creation with default timestamp."""
    entity = DetectedEntity(
        text="Marie Dubois",
        entity_type="PERSON",
        start_pos=0,
        end_pos=12,
        confidence=0.85,
    )

    decision = UserDecision(
        entity_id="test-id",
        action="CONFIRM",
        original_entity=entity,
    )

    assert decision.entity_id == "test-id"
    assert decision.action == "CONFIRM"
    assert decision.original_entity == entity
    assert decision.modified_entity is None
    assert decision.new_pseudonym is None
    assert decision.timestamp  # Should have auto-generated timestamp


def test_entity_review_creation() -> None:
    """Test EntityReview creation with defaults."""
    entity = DetectedEntity(
        text="Paris",
        entity_type="LOCATION",
        start_pos=26,
        end_pos=31,
    )

    review = EntityReview(entity=entity)

    assert review.entity == entity
    assert review.entity_id  # Should have auto-generated UUID
    assert review.state == EntityReviewState.PENDING
    assert review.user_modification is None
    assert review.suggested_pseudonym is None
    assert review.custom_pseudonym is None


def test_validation_session_add_entity() -> None:
    """Test adding entity to validation session."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris.",
    )

    entity = DetectedEntity(
        text="Marie Dubois",
        entity_type="PERSON",
        start_pos=0,
        end_pos=12,
    )

    session.add_entity(entity)

    assert len(session.entities) == 1
    assert session.entities[0] == entity
    assert len(session._entity_reviews) == 1
    assert session._entity_reviews[0].entity == entity


def test_validation_session_mark_confirmed() -> None:
    """Test marking entity as confirmed."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris.",
    )

    entity = DetectedEntity(
        text="Marie Dubois",
        entity_type="PERSON",
        start_pos=0,
        end_pos=12,
    )

    session.add_entity(entity)
    session.mark_confirmed(entity)

    assert len(session.user_decisions) == 1
    assert session.user_decisions[0].action == "CONFIRM"
    assert session.user_decisions[0].original_entity == entity

    review = session.get_entity_review(entity)
    assert review is not None
    assert review.state == EntityReviewState.CONFIRMED


def test_validation_session_mark_rejected() -> None:
    """Test marking entity as rejected."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris pour TechCorp.",
    )

    entity = DetectedEntity(
        text="TechCorp",
        entity_type="ORG",
        start_pos=40,
        end_pos=48,
    )

    session.add_entity(entity)
    session.mark_rejected(entity)

    assert len(session.user_decisions) == 1
    assert session.user_decisions[0].action == "REJECT"
    assert session.user_decisions[0].original_entity == entity

    review = session.get_entity_review(entity)
    assert review is not None
    assert review.state == EntityReviewState.REJECTED


def test_validation_session_mark_modified() -> None:
    """Test marking entity as modified."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie travaille à Paris.",
    )

    original_entity = DetectedEntity(
        text="Marie",
        entity_type="PERSON",
        start_pos=0,
        end_pos=5,
    )

    modified_entity = DetectedEntity(
        text="Marie Dubois",
        entity_type="PERSON",
        start_pos=0,
        end_pos=5,
        confidence=None,
    )

    session.add_entity(original_entity)
    session.mark_modified(original_entity, modified_entity)

    assert len(session.user_decisions) == 1
    assert session.user_decisions[0].action == "MODIFY"
    assert session.user_decisions[0].original_entity == original_entity
    assert session.user_decisions[0].modified_entity == modified_entity

    review = session.get_entity_review(original_entity)
    assert review is not None
    assert review.state == EntityReviewState.MODIFIED
    assert review.user_modification == "Marie Dubois"


def test_validation_session_add_manual_entity() -> None:
    """Test manually adding entity to session."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Document about Jean Dupont.",
    )

    new_entity = DetectedEntity(
        text="Jean Dupont",
        entity_type="PERSON",
        start_pos=14,
        end_pos=25,
        confidence=None,
    )

    session.add_manual_entity(new_entity)

    assert len(session.entities) == 1
    assert session.entities[0] == new_entity
    assert len(session.user_decisions) == 1
    assert session.user_decisions[0].action == "ADD"
    assert session.user_decisions[0].modified_entity == new_entity


def test_validation_session_change_pseudonym() -> None:
    """Test changing pseudonym for entity."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris.",
    )

    entity = DetectedEntity(
        text="Marie Dubois",
        entity_type="PERSON",
        start_pos=0,
        end_pos=12,
    )

    session.add_entity(entity)
    session.change_pseudonym(entity, "Leia Organa")

    assert len(session.user_decisions) == 1
    assert session.user_decisions[0].action == "CHANGE_PSEUDONYM"
    assert session.user_decisions[0].new_pseudonym == "Leia Organa"

    review = session.get_entity_review(entity)
    assert review is not None
    assert review.custom_pseudonym == "Leia Organa"
    assert review.state == EntityReviewState.CONFIRMED


def test_validation_session_get_validated_entities() -> None:
    """Test getting final validated entity list."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris pour TechCorp.",
    )

    entity1 = DetectedEntity(
        text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
    )
    entity2 = DetectedEntity(
        text="Paris", entity_type="LOCATION", start_pos=26, end_pos=31
    )
    entity3 = DetectedEntity(
        text="TechCorp", entity_type="ORG", start_pos=40, end_pos=48
    )

    session.add_entity(entity1)
    session.add_entity(entity2)
    session.add_entity(entity3)

    # Confirm entity1, reject entity3, confirm entity2
    session.mark_confirmed(entity1)
    session.mark_rejected(entity3)
    session.mark_confirmed(entity2)

    validated = session.get_validated_entities()

    assert len(validated) == 2
    assert entity1 in validated or any(e.text == entity1.text for e in validated)
    assert entity2 in validated or any(e.text == entity2.text for e in validated)
    assert entity3 not in validated
    assert not any(e.text == entity3.text for e in validated)


def test_validation_session_get_summary_stats() -> None:
    """Test getting validation summary statistics."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris pour TechCorp.",
    )

    entity1 = DetectedEntity(
        text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
    )
    entity2 = DetectedEntity(
        text="Paris", entity_type="LOCATION", start_pos=26, end_pos=31
    )
    entity3 = DetectedEntity(
        text="TechCorp", entity_type="ORG", start_pos=40, end_pos=48
    )

    session.add_entity(entity1)
    session.add_entity(entity2)
    session.add_entity(entity3)

    # 1 confirmed, 1 rejected, 1 modified
    session.mark_confirmed(entity1)
    session.mark_rejected(entity3)
    modified_entity2 = DetectedEntity(
        text="Paris, France", entity_type="LOCATION", start_pos=26, end_pos=31
    )
    session.mark_modified(entity2, modified_entity2)

    stats = session.get_summary_stats()

    assert stats["confirmed"] == 1
    assert stats["rejected"] == 1
    assert stats["modified"] == 1
    assert stats["added"] == 0
    assert stats["total"] == 3


def test_validation_session_get_pending_entities() -> None:
    """Test getting pending (unreviewed) entities."""
    session = ValidationSession(
        document_path="/path/to/doc.txt",
        document_text="Marie Dubois travaille à Paris pour TechCorp.",
    )

    entity1 = DetectedEntity(
        text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
    )
    entity2 = DetectedEntity(
        text="Paris", entity_type="LOCATION", start_pos=26, end_pos=31
    )
    entity3 = DetectedEntity(
        text="TechCorp", entity_type="ORG", start_pos=40, end_pos=48
    )

    session.add_entity(entity1)
    session.add_entity(entity2)
    session.add_entity(entity3)

    # Confirm only entity1
    session.mark_confirmed(entity1)

    pending = session.get_pending_entities()

    assert len(pending) == 2
    # entity2 and entity3 should still be pending
    assert any(e.text == entity2.text for e in pending)
    assert any(e.text == entity3.text for e in pending)
    assert not any(e.text == entity1.text for e in pending)


# ===== Entity Deduplication Tests (Story 1.9) =====


def test_entity_group_creation() -> None:
    """Test EntityGroup creation and properties."""
    entities = [
        DetectedEntity("Marie Dubois", "PERSON", 0, 12),
        DetectedEntity("Marie Dubois", "PERSON", 50, 62),
        DetectedEntity("Marie Dubois", "PERSON", 100, 112),
    ]

    group = EntityGroup(
        unique_key=("Marie Dubois", "PERSON"),
        occurrences=entities,
    )

    assert group.text == "Marie Dubois"
    assert group.entity_type == "PERSON"
    assert group.count == 3
    assert len(group.occurrences) == 3
    assert group.current_context_index == 0


def test_entity_group_representative_entity() -> None:
    """Test getting representative entity from group."""
    entities = [
        DetectedEntity("Paris", "LOCATION", 10, 15),
        DetectedEntity("Paris", "LOCATION", 40, 45),
    ]

    group = EntityGroup(
        unique_key=("Paris", "LOCATION"),
        occurrences=entities,
    )

    # Should return first entity by default
    representative = group.get_representative_entity()
    assert representative == entities[0]
    assert representative.start_pos == 10


def test_entity_group_cycle_context() -> None:
    """Test cycling through contexts in entity group."""
    entities = [
        DetectedEntity("Marie Dubois", "PERSON", 0, 12),
        DetectedEntity("Marie Dubois", "PERSON", 50, 62),
        DetectedEntity("Marie Dubois", "PERSON", 100, 112),
    ]

    group = EntityGroup(
        unique_key=("Marie Dubois", "PERSON"),
        occurrences=entities,
    )

    # Start at index 0
    assert group.current_context_index == 0
    assert group.get_representative_entity() == entities[0]

    # Cycle to index 1
    group.cycle_context()
    assert group.current_context_index == 1
    assert group.get_representative_entity() == entities[1]

    # Cycle to index 2
    group.cycle_context()
    assert group.current_context_index == 2
    assert group.get_representative_entity() == entities[2]

    # Cycle back to index 0
    group.cycle_context()
    assert group.current_context_index == 0
    assert group.get_representative_entity() == entities[0]


def test_get_entity_groups_basic() -> None:
    """Test grouping entities by unique (text, entity_type)."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Marie Dubois travaille à Paris avec Marie Dubois à Paris.",
    )

    # Add duplicate entities
    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 0, 12))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 26, 31))
    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 37, 49))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 52, 57))

    groups = session.get_entity_groups()

    # Should have 2 groups: Marie Dubois (PERSON) and Paris (LOCATION)
    assert len(groups) == 2

    # Verify Marie Dubois group
    marie_group = next(g for g in groups if g.text == "Marie Dubois")
    assert marie_group.entity_type == "PERSON"
    assert marie_group.count == 2
    assert marie_group.occurrences[0].start_pos == 0
    assert marie_group.occurrences[1].start_pos == 37

    # Verify Paris group
    paris_group = next(g for g in groups if g.text == "Paris")
    assert paris_group.entity_type == "LOCATION"
    assert paris_group.count == 2
    assert paris_group.occurrences[0].start_pos == 26
    assert paris_group.occurrences[1].start_pos == 52


def test_get_entity_groups_filter_by_type() -> None:
    """Test filtering entity groups by entity type."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Marie Dubois at TechCorp in Paris.",
    )

    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 0, 12))
    session.add_entity(DetectedEntity("TechCorp", "ORG", 16, 24))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 28, 33))

    # Get only PERSON groups
    person_groups = session.get_entity_groups("PERSON")
    assert len(person_groups) == 1
    assert person_groups[0].text == "Marie Dubois"
    assert person_groups[0].entity_type == "PERSON"

    # Get only LOCATION groups
    location_groups = session.get_entity_groups("LOCATION")
    assert len(location_groups) == 1
    assert location_groups[0].text == "Paris"

    # Get all groups
    all_groups = session.get_entity_groups()
    assert len(all_groups) == 3


def test_get_entity_groups_different_types_same_text() -> None:
    """Test that same text with different types creates separate groups."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Paris (the city) and Paris (the company).",
    )

    # Same text "Paris" but different types
    session.add_entity(DetectedEntity("Paris", "LOCATION", 0, 5))
    session.add_entity(DetectedEntity("Paris", "ORG", 21, 26))

    groups = session.get_entity_groups()

    # Should have 2 separate groups
    assert len(groups) == 2

    location_group = next(g for g in groups if g.entity_type == "LOCATION")
    assert location_group.count == 1
    assert location_group.text == "Paris"

    org_group = next(g for g in groups if g.entity_type == "ORG")
    assert org_group.count == 1
    assert org_group.text == "Paris"


def test_get_entity_groups_sorted_by_position() -> None:
    """Test that groups are sorted by first occurrence position."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Paris, Marie Dubois, TechCorp, Paris again.",
    )

    # Add in non-position order
    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 7, 19))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 0, 5))
    session.add_entity(DetectedEntity("TechCorp", "ORG", 21, 29))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 31, 36))

    groups = session.get_entity_groups()

    # Groups should be sorted by first occurrence position
    assert groups[0].text == "Paris"  # First at position 0
    assert groups[1].text == "Marie Dubois"  # Second at position 7
    assert groups[2].text == "TechCorp"  # Third at position 21


def test_get_entity_groups_single_occurrence() -> None:
    """Test entity groups with single occurrence (edge case)."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Marie Dubois works at TechCorp.",
    )

    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 0, 12))
    session.add_entity(DetectedEntity("TechCorp", "ORG", 22, 30))

    groups = session.get_entity_groups()

    # Each entity should be in its own group with count=1
    assert len(groups) == 2
    assert all(g.count == 1 for g in groups)


def test_decision_applies_to_all_group_occurrences() -> None:
    """Test that confirming applies to all entity instances in group."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Marie Dubois and Marie Dubois and Marie Dubois.",
    )

    # Add 3 occurrences of same entity
    e1 = DetectedEntity("Marie Dubois", "PERSON", 0, 12)
    e2 = DetectedEntity("Marie Dubois", "PERSON", 17, 29)
    e3 = DetectedEntity("Marie Dubois", "PERSON", 34, 46)

    session.add_entity(e1)
    session.add_entity(e2)
    session.add_entity(e3)

    # Confirm all occurrences
    session.mark_confirmed(e1)
    session.mark_confirmed(e2)
    session.mark_confirmed(e3)

    # All should be confirmed
    validated = session.get_validated_entities()
    assert len(validated) == 3
    assert all(e.text == "Marie Dubois" for e in validated)


def test_custom_pseudonym_applies_to_all_group_occurrences() -> None:
    """Test that custom pseudonym applies to all entity instances in group (AC3)."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Marie Dubois met Marie Dubois.",
    )

    # Add 2 occurrences of same entity
    e1 = DetectedEntity("Marie Dubois", "PERSON", 0, 12)
    e2 = DetectedEntity("Marie Dubois", "PERSON", 17, 29)

    session.add_entity(e1)
    session.add_entity(e2)

    # Change pseudonym for both occurrences
    session.change_pseudonym(e1, "Leia Organa")
    session.change_pseudonym(e2, "Leia Organa")

    # Verify both have custom pseudonym
    review1 = session.get_entity_review(e1)
    review2 = session.get_entity_review(e2)

    assert review1 is not None
    assert review2 is not None
    assert review1.custom_pseudonym == "Leia Organa"
    assert review2.custom_pseudonym == "Leia Organa"


def test_get_summary_stats_includes_unique_count() -> None:
    """Test that summary stats includes unique entity count for deduplication."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Marie Dubois and Marie Dubois at Paris and Paris.",
    )

    # Add 4 entities (2 unique)
    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 0, 12))
    session.add_entity(DetectedEntity("Marie Dubois", "PERSON", 17, 29))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 33, 38))
    session.add_entity(DetectedEntity("Paris", "LOCATION", 43, 48))

    stats = session.get_summary_stats()

    assert stats["total"] == 4  # Total occurrences
    assert stats["unique"] == 2  # Unique entities (Marie Dubois + Paris)


def test_get_entity_groups_empty_session() -> None:
    """Test get_entity_groups on session with no entities."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="No entities here.",
    )

    groups = session.get_entity_groups()
    assert len(groups) == 0


def test_get_entity_groups_occurrences_sorted_by_position() -> None:
    """Test that occurrences within group are sorted by position."""
    session = ValidationSession(
        document_path="test.txt",
        document_text="Text with Paris at start and Paris at end and Paris in middle.",
    )

    # Add in non-position order
    session.add_entity(DetectedEntity("Paris", "LOCATION", 45, 50))  # Middle
    session.add_entity(DetectedEntity("Paris", "LOCATION", 10, 15))  # Start
    session.add_entity(DetectedEntity("Paris", "LOCATION", 29, 34))  # End

    groups = session.get_entity_groups()
    assert len(groups) == 1

    paris_group = groups[0]
    # Occurrences should be sorted by start_pos
    assert paris_group.occurrences[0].start_pos == 10  # Start
    assert paris_group.occurrences[1].start_pos == 29  # End
    assert paris_group.occurrences[2].start_pos == 45  # Middle
