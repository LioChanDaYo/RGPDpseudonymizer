"""User action handlers for validation workflow.

This module implements handlers for user actions during entity validation,
including confirm, reject, modify, add, and change pseudonym operations.
"""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


class UserAction:
    """Base class for user actions during validation."""

    def execute(self) -> None:
        """Execute the user action."""
        raise NotImplementedError("Subclasses must implement execute()")


class ConfirmAction(UserAction):
    """Action to confirm an entity as correctly detected."""

    def __init__(self, entity: DetectedEntity) -> None:
        """Initialize confirm action.

        Args:
            entity: Entity to confirm
        """
        self.entity = entity

    def execute(self) -> None:
        """Execute confirmation (mark entity as accepted)."""
        # Action handled by ValidationSession
        pass


class RejectAction(UserAction):
    """Action to reject an entity as false positive."""

    def __init__(self, entity: DetectedEntity) -> None:
        """Initialize reject action.

        Args:
            entity: Entity to reject
        """
        self.entity = entity

    def execute(self) -> None:
        """Execute rejection (mark entity for removal)."""
        # Action handled by ValidationSession
        pass


class ModifyAction(UserAction):
    """Action to modify entity text."""

    def __init__(self, entity: DetectedEntity, new_text: str) -> None:
        """Initialize modify action.

        Args:
            entity: Entity to modify
            new_text: Corrected entity text
        """
        self.entity = entity
        self.new_text = new_text

    def execute(self) -> None:
        """Execute modification (update entity text)."""
        # Action handled by ValidationSession
        pass


class AddAction(UserAction):
    """Action to manually add a missed entity."""

    def __init__(
        self,
        text: str,
        entity_type: str,
        start_pos: int,
        end_pos: int,
    ) -> None:
        """Initialize add action.

        Args:
            text: Entity text
            entity_type: Type of entity (PERSON, LOCATION, ORG)
            start_pos: Start position in document
            end_pos: End position in document
        """
        self.text = text
        self.entity_type = entity_type
        self.start_pos = start_pos
        self.end_pos = end_pos

    def execute(self) -> None:
        """Execute addition (handled by ValidationSession)."""
        # Action handled by ValidationSession.add_manual_entity
        pass

    def create_entity(self) -> DetectedEntity:
        """Create new DetectedEntity from action parameters.

        Returns:
            Newly created DetectedEntity
        """
        return DetectedEntity(
            text=self.text,
            entity_type=self.entity_type,
            start_pos=self.start_pos,
            end_pos=self.end_pos,
            confidence=None,  # Manually added entities have no confidence score
            gender=None,
            is_ambiguous=False,
        )


class ChangePseudonymAction(UserAction):
    """Action to override suggested pseudonym."""

    def __init__(self, entity: DetectedEntity, new_pseudonym: str) -> None:
        """Initialize change pseudonym action.

        Args:
            entity: Entity to change pseudonym for
            new_pseudonym: User-provided pseudonym override
        """
        self.entity = entity
        self.new_pseudonym = new_pseudonym

    def execute(self) -> None:
        """Execute pseudonym change (update mapping)."""
        # Action handled by pseudonym assignment engine
        pass
