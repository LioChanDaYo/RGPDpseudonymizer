"""Validation data models for human-in-the-loop entity review."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


class EntityReviewState(Enum):
    """State of entity review in validation workflow.

    Attributes:
        PENDING: Entity awaiting user review
        CONFIRMED: Entity confirmed as correct by user
        REJECTED: Entity rejected as false positive
        MODIFIED: Entity text modified by user
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class EntityReview:
    """Entity review state for validation workflow.

    Tracks the user's review decision for a single detected entity,
    including any modifications or rejections.

    Attributes:
        entity: Detected entity from NLP processing
        state: Current review state
        user_modification: Modified entity text if state is MODIFIED
        suggested_pseudonym: Suggested pseudonym for display (optional)
    """

    entity: DetectedEntity
    state: EntityReviewState = EntityReviewState.PENDING
    user_modification: Optional[str] = None
    suggested_pseudonym: Optional[str] = None


@dataclass
class ValidationSession:
    """Manages validation state for a document.

    Coordinates the human-in-the-loop validation workflow, tracking
    which entities have been reviewed and storing user decisions.

    Attributes:
        document_path: Path to document being validated
        document_text: Full document text content
        entities: List of entities awaiting or completed review
        current_index: Index of entity currently being reviewed
    """

    document_path: str
    document_text: str
    entities: List[EntityReview] = field(default_factory=list)
    current_index: int = 0

    def add_entity(self, entity: DetectedEntity) -> None:
        """Add detected entity to validation session.

        Args:
            entity: Entity detected by NLP engine
        """
        self.entities.append(
            EntityReview(entity=entity, state=EntityReviewState.PENDING)
        )

    def get_current_entity(self) -> Optional[EntityReview]:
        """Get entity at current review index.

        Returns:
            EntityReview if index is valid, None if past end
        """
        if 0 <= self.current_index < len(self.entities):
            return self.entities[self.current_index]
        return None

    def confirm_entity(self, index: int) -> None:
        """Mark entity as confirmed by user.

        Args:
            index: Index of entity to confirm
        """
        if 0 <= index < len(self.entities):
            self.entities[index].state = EntityReviewState.CONFIRMED

    def reject_entity(self, index: int) -> None:
        """Mark entity as rejected (false positive).

        Args:
            index: Index of entity to reject
        """
        if 0 <= index < len(self.entities):
            self.entities[index].state = EntityReviewState.REJECTED

    def modify_entity(self, index: int, new_text: str) -> None:
        """Modify entity text based on user correction.

        Args:
            index: Index of entity to modify
            new_text: Corrected entity text
        """
        if 0 <= index < len(self.entities):
            self.entities[index].state = EntityReviewState.MODIFIED
            self.entities[index].user_modification = new_text
