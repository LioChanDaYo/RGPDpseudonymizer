"""Validation data models for human-in-the-loop entity review."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


class EntityReviewState(Enum):
    """State of entity review in validation workflow.

    Attributes:
        PENDING: Entity awaiting user review
        CONFIRMED: Entity confirmed as correct by user
        REJECTED: Entity rejected as false positive
        MODIFIED: Entity text modified by user
        ADDED: Entity manually added by user
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    MODIFIED = "modified"
    ADDED = "added"


@dataclass
class UserDecision:
    """Records a user's decision about an entity.

    Attributes:
        entity_id: UUID of the detected entity
        action: User action (CONFIRM, REJECT, MODIFY, ADD, CHANGE_PSEUDONYM)
        original_entity: Original detected entity
        modified_entity: Modified entity if action is MODIFY or ADD
        new_pseudonym: Custom pseudonym if action is CHANGE_PSEUDONYM
        timestamp: ISO format timestamp of decision
    """

    entity_id: str
    action: str
    original_entity: DetectedEntity | None = None
    modified_entity: DetectedEntity | None = None
    new_pseudonym: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EntityReview:
    """Entity review state for validation workflow.

    Tracks the user's review decision for a single detected entity,
    including any modifications or rejections.

    Attributes:
        entity: Detected entity from NLP processing
        entity_id: Unique identifier for this entity
        state: Current review state
        user_modification: Modified entity text if state is MODIFIED
        suggested_pseudonym: Suggested pseudonym for display (optional)
        custom_pseudonym: User-provided custom pseudonym override
    """

    entity: DetectedEntity
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: EntityReviewState = EntityReviewState.PENDING
    user_modification: str | None = None
    suggested_pseudonym: str | None = None
    custom_pseudonym: str | None = None


@dataclass
class ValidationSession:
    """Manages validation state for a document.

    Coordinates the human-in-the-loop validation workflow, tracking
    which entities have been reviewed and storing user decisions.

    Attributes:
        document_path: Path to document being validated
        document_text: Full document text content
        entities: List of detected entities being reviewed
        context_cache: Cached context snippets for fast display
        user_decisions: List of all user decisions
        current_index: Index of entity currently being reviewed
        current_entity_type: Current entity type being reviewed
    """

    document_path: str
    document_text: str
    entities: list[DetectedEntity] = field(default_factory=list)
    context_cache: dict[str, str] = field(default_factory=dict)
    user_decisions: list[UserDecision] = field(default_factory=list)
    current_index: int = 0
    current_entity_type: str = "PERSON"
    _entity_reviews: list[EntityReview] = field(default_factory=list)

    def add_entity(self, entity: DetectedEntity) -> None:
        """Add detected entity to validation session.

        Args:
            entity: Entity detected by NLP engine
        """
        self.entities.append(entity)
        self._entity_reviews.append(
            EntityReview(entity=entity, state=EntityReviewState.PENDING)
        )

    def get_entity_review(self, entity: DetectedEntity) -> EntityReview | None:
        """Get EntityReview for a given DetectedEntity.

        Args:
            entity: Entity to find review for

        Returns:
            EntityReview if found, None otherwise
        """
        for review in self._entity_reviews:
            if review.entity == entity:
                return review
        return None

    def get_pending_entities(self) -> list[DetectedEntity]:
        """Get all entities that have not been reviewed yet.

        Returns:
            List of entities with PENDING state
        """
        decided_ids = {d.entity_id for d in self.user_decisions}
        return [
            review.entity
            for review in self._entity_reviews
            if review.entity_id not in decided_ids
        ]

    def mark_confirmed(self, entity: DetectedEntity) -> None:
        """Mark entity as confirmed by user.

        Args:
            entity: Entity to confirm
        """
        review = self.get_entity_review(entity)
        if review:
            review.state = EntityReviewState.CONFIRMED
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="CONFIRM",
                    original_entity=entity,
                )
            )

    def mark_rejected(self, entity: DetectedEntity) -> None:
        """Mark entity as rejected (false positive).

        Args:
            entity: Entity to reject
        """
        review = self.get_entity_review(entity)
        if review:
            review.state = EntityReviewState.REJECTED
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="REJECT",
                    original_entity=entity,
                )
            )

    def mark_modified(self, original: DetectedEntity, modified: DetectedEntity) -> None:
        """Mark entity as modified by user.

        Args:
            original: Original detected entity
            modified: Modified entity with corrected text
        """
        review = self.get_entity_review(original)
        if review:
            review.state = EntityReviewState.MODIFIED
            review.user_modification = modified.text
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="MODIFY",
                    original_entity=original,
                    modified_entity=modified,
                )
            )

    def add_manual_entity(self, new_entity: DetectedEntity) -> None:
        """Add manually added entity to session.

        Args:
            new_entity: Entity manually added by user
        """
        self.entities.append(new_entity)
        review = EntityReview(entity=new_entity, state=EntityReviewState.ADDED)
        self._entity_reviews.append(review)
        self.user_decisions.append(
            UserDecision(
                entity_id=review.entity_id,
                action="ADD",
                modified_entity=new_entity,
            )
        )

    def change_pseudonym(self, entity: DetectedEntity, new_pseudonym: str) -> None:
        """Change pseudonym for an entity.

        Args:
            entity: Entity to change pseudonym for
            new_pseudonym: Custom pseudonym
        """
        review = self.get_entity_review(entity)
        if review:
            review.custom_pseudonym = new_pseudonym
            review.state = EntityReviewState.CONFIRMED
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="CHANGE_PSEUDONYM",
                    original_entity=entity,
                    new_pseudonym=new_pseudonym,
                )
            )

    def get_validated_entities(self) -> list[DetectedEntity]:
        """Get final list of validated entities after user review.

        Includes confirmed and modified entities, excludes rejected entities,
        includes manually added entities.

        Returns:
            List of validated entities ready for pseudonymization
        """
        confirmed_ids = {
            d.entity_id
            for d in self.user_decisions
            if d.action in ("CONFIRM", "MODIFY", "CHANGE_PSEUDONYM")
        }
        rejected_ids = {
            d.entity_id for d in self.user_decisions if d.action == "REJECT"
        }
        added_entities = [
            d.modified_entity
            for d in self.user_decisions
            if d.action == "ADD" and d.modified_entity
        ]

        # Get confirmed/modified entities (excluding rejected)
        validated = []
        for review in self._entity_reviews:
            if (
                review.entity_id in confirmed_ids
                and review.entity_id not in rejected_ids
            ):
                # Apply modifications if present
                if (
                    review.state == EntityReviewState.MODIFIED
                    and review.user_modification
                ):
                    # Create modified entity
                    modified_entity = DetectedEntity(
                        text=review.user_modification,
                        entity_type=review.entity.entity_type,
                        start_pos=review.entity.start_pos,
                        end_pos=review.entity.end_pos,
                        confidence=review.entity.confidence,
                        gender=review.entity.gender,
                        is_ambiguous=review.entity.is_ambiguous,
                    )
                    validated.append(modified_entity)
                else:
                    validated.append(review.entity)

        return validated + added_entities

    def get_summary_stats(self) -> dict[str, int]:
        """Get summary statistics of validation decisions.

        Returns:
            Dictionary with counts of confirmed, rejected, modified, added entities
        """
        confirmed = sum(1 for d in self.user_decisions if d.action == "CONFIRM")
        rejected = sum(1 for d in self.user_decisions if d.action == "REJECT")
        modified = sum(1 for d in self.user_decisions if d.action == "MODIFY")
        added = sum(1 for d in self.user_decisions if d.action == "ADD")

        return {
            "confirmed": confirmed,
            "rejected": rejected,
            "modified": modified,
            "added": added,
            "total": len(self.entities),
        }
