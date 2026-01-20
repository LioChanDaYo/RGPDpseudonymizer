"""Unit tests for validation data models.

Tests ValidationSession, EntityReviewState, UserDecision, and EntityReview classes.
"""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import (
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
