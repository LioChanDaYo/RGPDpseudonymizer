"""GUI validation state adapter wrapping core ValidationSession + QUndoStack.

Provides a QObject-based interface for the validation screen, bridging
core validation models with Qt undo/redo and signal infrastructure.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import (
    EntityReview,
    EntityReviewState,
    ValidationSession,
)

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult


class GUIValidationState(QObject):
    """Manages validation state for the GUI, wrapping core ValidationSession.

    Provides action methods that record decisions via QUndoStack for
    undo/redo support, and emits signals for widget synchronization.
    """

    state_changed = Signal(str)  # entity_id whose state changed
    entity_added = Signal(str)  # entity_id of newly added entity
    entity_removed = Signal(str)  # entity_id of entity removed by undo of add

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = ValidationSession(document_path="", document_text="")
        self._undo_stack = QUndoStack(self)
        self._known_entity_ids: set[str] = set()
        self._pseudonym_previews: dict[str, str] = {}
        # Map entity_id -> EntityReview for fast lookup
        self._reviews_by_id: dict[str, EntityReview] = {}

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def session(self) -> ValidationSession:
        return self._session

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def init_from_detection_result(self, detection_result: DetectionResult) -> None:
        """Initialize state from a DetectionResult.

        Args:
            detection_result: Result from DetectionWorker
        """
        self._session = ValidationSession(
            document_path=detection_result.input_file,
            document_text=detection_result.document_text,
        )
        self._pseudonym_previews = dict(detection_result.pseudonym_previews)
        self._reviews_by_id.clear()
        self._known_entity_ids.clear()
        self._undo_stack.clear()

        for entity in detection_result.detected_entities:
            self._session.add_entity(entity)

        # Build id lookup
        for review in self._session._entity_reviews:
            self._reviews_by_id[review.entity_id] = review
            # Set pseudonym preview
            key = f"{review.entity.text}_{review.entity.start_pos}"
            if key in self._pseudonym_previews:
                review.suggested_pseudonym = self._pseudonym_previews[key]

    def classify_known_entities(self, db_path: str, passphrase: str) -> None:
        """Check which entities exist in the mapping DB and auto-accept them.

        Args:
            db_path: Path to mapping database
            passphrase: Database passphrase
        """
        try:
            from gdpr_pseudonymizer.data.database import open_database
            from gdpr_pseudonymizer.data.repositories.mapping_repository import (
                SQLiteMappingRepository,
            )

            with open_database(db_path, passphrase) as db_session:
                repo = SQLiteMappingRepository(db_session)
                for review in self._session._entity_reviews:
                    existing = repo.find_by_full_name(review.entity.text)
                    if existing:
                        self._known_entity_ids.add(review.entity_id)
                        review.state = EntityReviewState.CONFIRMED
                        review.suggested_pseudonym = existing.pseudonym_full
        except Exception:
            pass  # Non-fatal: unknown entities just stay PENDING

    # ------------------------------------------------------------------
    # Action methods (each creates QUndoCommand)
    # ------------------------------------------------------------------

    def accept_entity(self, entity_id: str) -> None:
        """Mark entity as confirmed."""
        cmd = _SingleActionCommand(self, entity_id, EntityReviewState.CONFIRMED)
        self._undo_stack.push(cmd)

    def reject_entity(self, entity_id: str) -> None:
        """Mark entity as rejected."""
        cmd = _SingleActionCommand(self, entity_id, EntityReviewState.REJECTED)
        self._undo_stack.push(cmd)

    def modify_entity_text(
        self,
        entity_id: str,
        new_text: str,
        new_start: int,
        new_end: int,
    ) -> None:
        """Modify entity text/boundaries."""
        cmd = _ModifyTextCommand(self, entity_id, new_text, new_start, new_end)
        self._undo_stack.push(cmd)

    def change_pseudonym(self, entity_id: str, new_pseudonym: str) -> None:
        """Override suggested pseudonym for an entity."""
        cmd = _ChangePseudonymCommand(self, entity_id, new_pseudonym)
        self._undo_stack.push(cmd)

    def change_entity_type(self, entity_id: str, new_type: str) -> None:
        """Change entity type (e.g. PERSON -> ORG)."""
        cmd = _ChangeTypeCommand(self, entity_id, new_type)
        self._undo_stack.push(cmd)

    def add_entity(
        self,
        text: str,
        entity_type: str,
        start_pos: int,
        end_pos: int,
    ) -> str:
        """Add a manually selected entity. Returns entity_id."""
        entity_id = str(uuid.uuid4())
        cmd = _AddEntityCommand(self, entity_id, text, entity_type, start_pos, end_pos)
        self._undo_stack.push(cmd)
        return entity_id

    def bulk_accept(self, entity_ids: list[str]) -> None:
        """Accept multiple entities as a single undoable action."""
        if not entity_ids:
            return
        self._undo_stack.beginMacro("Accepter la sélection")
        for eid in entity_ids:
            cmd = _SingleActionCommand(self, eid, EntityReviewState.CONFIRMED)
            self._undo_stack.push(cmd)
        self._undo_stack.endMacro()

    def bulk_reject(self, entity_ids: list[str]) -> None:
        """Reject multiple entities as a single undoable action."""
        if not entity_ids:
            return
        self._undo_stack.beginMacro("Rejeter la sélection")
        for eid in entity_ids:
            cmd = _SingleActionCommand(self, eid, EntityReviewState.REJECTED)
            self._undo_stack.push(cmd)
        self._undo_stack.endMacro()

    def accept_all_of_type(self, entity_type: str) -> None:
        """Accept all pending entities of a given type."""
        ids = [
            r.entity_id
            for r in self._session._entity_reviews
            if r.entity.entity_type == entity_type
            and r.state == EntityReviewState.PENDING
        ]
        if ids:
            self._undo_stack.beginMacro(f"Tout accepter: {entity_type}")
            for eid in ids:
                cmd = _SingleActionCommand(self, eid, EntityReviewState.CONFIRMED)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()

    def accept_all_known(self) -> None:
        """Accept all known entities."""
        ids = [
            r.entity_id
            for r in self._session._entity_reviews
            if r.entity_id in self._known_entity_ids
            and r.state != EntityReviewState.CONFIRMED
        ]
        if ids:
            self._undo_stack.beginMacro("Accepter les déjà connues")
            for eid in ids:
                cmd = _SingleActionCommand(self, eid, EntityReviewState.CONFIRMED)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_review(self, entity_id: str) -> EntityReview | None:
        """Get EntityReview by id."""
        return self._reviews_by_id.get(entity_id)

    def get_entities_by_type(self, entity_type: str) -> list[EntityReview]:
        """Get all reviews for a given entity type."""
        return [
            r
            for r in self._session._entity_reviews
            if r.entity.entity_type == entity_type
        ]

    def get_all_entities(self) -> list[EntityReview]:
        """Get all entity reviews."""
        return list(self._session._entity_reviews)

    def get_pending_count(self) -> int:
        """Number of entities not yet reviewed."""
        return sum(
            1
            for r in self._session._entity_reviews
            if r.state == EntityReviewState.PENDING
        )

    def get_summary(self) -> dict[str, int]:
        """Summary counts: accepted, rejected, modified, added."""
        counts: dict[str, int] = {
            "accepted": 0,
            "rejected": 0,
            "modified": 0,
            "added": 0,
            "total": len(self._session._entity_reviews),
        }
        for r in self._session._entity_reviews:
            if r.state == EntityReviewState.CONFIRMED:
                counts["accepted"] += 1
            elif r.state == EntityReviewState.REJECTED:
                counts["rejected"] += 1
            elif r.state == EntityReviewState.MODIFIED:
                counts["modified"] += 1
            elif r.state == EntityReviewState.ADDED:
                counts["added"] += 1
        return counts

    def get_validated_entities(self) -> list[DetectedEntity]:
        """Final entity list for finalization (excludes rejected)."""
        result: list[DetectedEntity] = []
        for review in self._session._entity_reviews:
            if review.state == EntityReviewState.REJECTED:
                continue
            if review.state == EntityReviewState.PENDING:
                continue
            if review.user_modification:
                result.append(
                    DetectedEntity(
                        text=review.user_modification,
                        entity_type=review.entity.entity_type,
                        start_pos=review.entity.start_pos,
                        end_pos=review.entity.end_pos,
                        confidence=review.entity.confidence,
                        gender=review.entity.gender,
                        is_ambiguous=review.entity.is_ambiguous,
                        source=review.entity.source,
                    )
                )
            else:
                result.append(review.entity)
        return result

    def is_entity_known(self, entity_id: str) -> bool:
        """Whether entity was found in the mapping DB."""
        return entity_id in self._known_entity_ids

    def get_pseudonym(self, entity_id: str) -> str:
        """Get current pseudonym for an entity (custom or suggested)."""
        review = self._reviews_by_id.get(entity_id)
        if review is None:
            return ""
        if review.custom_pseudonym:
            return review.custom_pseudonym
        return review.suggested_pseudonym or ""


# ------------------------------------------------------------------
# QUndoCommand subclasses
# ------------------------------------------------------------------


class _SingleActionCommand(QUndoCommand):
    """Accept or reject a single entity."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_state: EntityReviewState,
    ) -> None:
        label = "Accepter" if new_state == EntityReviewState.CONFIRMED else "Rejeter"
        super().__init__(label)
        self._state = state
        self._entity_id = entity_id
        self._new_state = new_state
        self._old_state: EntityReviewState | None = None

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            self._old_state = review.state
            review.state = self._new_state
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review and self._old_state is not None:
            review.state = self._old_state
            self._state.state_changed.emit(self._entity_id)


class _ModifyTextCommand(QUndoCommand):
    """Modify entity text/boundaries."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_text: str,
        new_start: int,
        new_end: int,
    ) -> None:
        super().__init__("Modifier le texte")
        self._state = state
        self._entity_id = entity_id
        self._new_text = new_text
        self._new_start = new_start
        self._new_end = new_end
        self._old_text: str | None = None
        self._old_start: int = 0
        self._old_end: int = 0
        self._old_state: EntityReviewState | None = None
        self._old_modification: str | None = None

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            self._old_text = review.entity.text
            self._old_start = review.entity.start_pos
            self._old_end = review.entity.end_pos
            self._old_state = review.state
            self._old_modification = review.user_modification
            review.user_modification = self._new_text
            review.entity.start_pos = self._new_start
            review.entity.end_pos = self._new_end
            review.state = EntityReviewState.MODIFIED
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            review.user_modification = self._old_modification
            review.entity.start_pos = self._old_start
            review.entity.end_pos = self._old_end
            if self._old_state is not None:
                review.state = self._old_state
            self._state.state_changed.emit(self._entity_id)


class _ChangePseudonymCommand(QUndoCommand):
    """Change pseudonym for an entity."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_pseudonym: str,
    ) -> None:
        super().__init__("Changer le pseudonyme")
        self._state = state
        self._entity_id = entity_id
        self._new_pseudonym = new_pseudonym
        self._old_pseudonym: str | None = None
        self._old_state: EntityReviewState | None = None

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            self._old_pseudonym = review.custom_pseudonym
            self._old_state = review.state
            review.custom_pseudonym = self._new_pseudonym
            review.state = EntityReviewState.MODIFIED
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            review.custom_pseudonym = self._old_pseudonym
            if self._old_state is not None:
                review.state = self._old_state
            self._state.state_changed.emit(self._entity_id)


class _ChangeTypeCommand(QUndoCommand):
    """Change entity type."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_type: str,
    ) -> None:
        super().__init__("Changer le type")
        self._state = state
        self._entity_id = entity_id
        self._new_type = new_type
        self._old_type: str | None = None
        self._old_state: EntityReviewState | None = None

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            self._old_type = review.entity.entity_type
            self._old_state = review.state
            review.entity.entity_type = self._new_type
            review.state = EntityReviewState.MODIFIED
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            if self._old_type is not None:
                review.entity.entity_type = self._old_type
            if self._old_state is not None:
                review.state = self._old_state
            self._state.state_changed.emit(self._entity_id)


class _AddEntityCommand(QUndoCommand):
    """Add a manually selected entity."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        text: str,
        entity_type: str,
        start_pos: int,
        end_pos: int,
    ) -> None:
        super().__init__("Ajouter une entité")
        self._state = state
        self._entity_id = entity_id
        self._text = text
        self._entity_type = entity_type
        self._start_pos = start_pos
        self._end_pos = end_pos

    def redo(self) -> None:
        entity = DetectedEntity(
            text=self._text,
            entity_type=self._entity_type,
            start_pos=self._start_pos,
            end_pos=self._end_pos,
            confidence=1.0,
            gender=None,
            is_ambiguous=False,
            source="manual",
        )
        review = EntityReview(
            entity=entity,
            entity_id=self._entity_id,
            state=EntityReviewState.ADDED,
        )
        self._state._session._entity_reviews.append(review)
        self._state._session.entities.append(entity)
        self._state._reviews_by_id[self._entity_id] = review
        self._state.entity_added.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.pop(self._entity_id, None)
        if review:
            self._state._session._entity_reviews.remove(review)
            if review.entity in self._state._session.entities:
                self._state._session.entities.remove(review.entity)
            self._state.entity_removed.emit(self._entity_id)
