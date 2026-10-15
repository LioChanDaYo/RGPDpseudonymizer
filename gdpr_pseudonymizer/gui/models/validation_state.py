"""GUI validation state adapter wrapping core ValidationSession + QUndoStack.

Provides a QObject-based interface for the validation screen, bridging
core validation models with Qt undo/redo and signal infrastructure.
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import (
    CandidateKey,
    EntityReview,
    EntityReviewState,
    ValidationSession,
    candidate_key,
)
from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow

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
        self._pseudonym_previews: dict[CandidateKey, str] = {}
        # Map entity_id -> EntityReview for fast lookup
        self._reviews_by_id: dict[str, EntityReview] = {}
        # Variant occurrence map: canonical candidate key (text, start_pos,
        # entity_type) → all DetectedEntity instances
        self._variant_occurrences: dict[CandidateKey, list[DetectedEntity]] = {}
        # Candidate key of each detected row, taken once at init (Story 10.8).
        # Type and text edits change review.entity in place, so expansion,
        # ranges and group actions read this key, never one recomputed from
        # the edited row. Rows added by hand have none.
        self._candidate_key_by_id: dict[str, CandidateKey] = {}
        # Same-text grouping index: (entity_text, entity_type) → [entity_id, ...]
        self._group_index: dict[tuple[str, str], list[str]] = {}
        # Spans of the occurrences of a text-edited row, in its variant
        # group's order, set by each edit's command (Story 10.9). A second
        # edit is placed from these spans, not from the detected ones.
        self._edited_spans_by_id: dict[str, list[tuple[int, int]]] = {}

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
        self._variant_occurrences = dict(detection_result.variant_occurrences or {})
        self._reviews_by_id.clear()
        self._candidate_key_by_id.clear()
        self._edited_spans_by_id.clear()
        self._known_entity_ids.clear()
        self._undo_stack.clear()

        for entity in detection_result.detected_entities:
            self._session.add_entity(entity)

        # Build id lookup, stored candidate keys and the (text, type) grouping
        # index. Each row's key is computed once, here (Story 10.8).
        self._group_index.clear()
        for review in self._session._entity_reviews:
            self._reviews_by_id[review.entity_id] = review
            key = candidate_key(review.entity)
            self._candidate_key_by_id[review.entity_id] = key
            # Set pseudonym preview
            if key in self._pseudonym_previews:
                review.suggested_pseudonym = self._pseudonym_previews[key]
            # Build (text, type) grouping index (exact text, case-sensitive)
            group_key = (key[0], key[2])
            self._group_index.setdefault(group_key, []).append(review.entity_id)

    def classify_known_entities(self, db_path: str, passphrase: str) -> None:
        """Check which entities exist in the mapping DB and auto-accept them.

        An entity is known when its text, normalized with the core's mapping
        key, is stored under its own type, as in the CLI (Story 10.7, AC4).
        Errors are swallowed: when the database cannot be opened (a failed
        conversion of a pre-10.7 file included), every entity stays pending.

        Args:
            db_path: Path to mapping database
            passphrase: Database passphrase
        """
        try:
            from gdpr_pseudonymizer.core.mapping_key import mapping_key
            from gdpr_pseudonymizer.data.database import open_database
            from gdpr_pseudonymizer.data.repositories.mapping_repository import (
                SQLiteMappingRepository,
            )

            with open_database(db_path, passphrase) as db_session:
                repo = SQLiteMappingRepository(db_session)
                for review in self._session._entity_reviews:
                    entity_type = review.entity.entity_type
                    existing = repo.find_by_full_name_and_type(
                        mapping_key(review.entity.text, entity_type), entity_type
                    )
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
        """Mark entity (and all rows of the same text and type) as confirmed."""
        review = self._reviews_by_id.get(entity_id)
        if review is None:
            return
        group_ids = self._group_ids(review)
        if len(group_ids) > 1:
            self._undo_stack.beginMacro("Accepter le groupe")
            for eid in group_ids:
                cmd = _SingleActionCommand(self, eid, EntityReviewState.CONFIRMED)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
            cmd = _SingleActionCommand(self, entity_id, EntityReviewState.CONFIRMED)
            self._undo_stack.push(cmd)

    def reject_entity(self, entity_id: str) -> None:
        """Mark entity (and all rows of the same text and type) as rejected."""
        review = self._reviews_by_id.get(entity_id)
        if review is None:
            return
        group_ids = self._group_ids(review)
        if len(group_ids) > 1:
            self._undo_stack.beginMacro("Rejeter le groupe")
            for eid in group_ids:
                cmd = _SingleActionCommand(self, eid, EntityReviewState.REJECTED)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
            cmd = _SingleActionCommand(self, entity_id, EntityReviewState.REJECTED)
            self._undo_stack.push(cmd)

    def _group_ids(self, review: EntityReview) -> list[str]:
        """Ids of the rows that one accept or reject acts on: same text and type.

        A detected row uses the key stored at init, so a group action on a
        retyped row acts on its original (text, type) group. A row added by
        hand has no stored key and uses its current text and type.
        """
        key = self._candidate_key_by_id.get(review.entity_id)
        if key is not None:
            group_key = (key[0], key[2])
        else:
            group_key = (review.entity.text, review.entity.entity_type)
        return self._group_index.get(group_key, [review.entity_id])

    def _variant_key(
        self, review: EntityReview, entity: DetectedEntity
    ) -> CandidateKey:
        """Key of a row's occurrences in the variant map.

        A detected row uses the key stored at init, so a type change or a
        custom pseudonym still reaches every occurrence of its group. A row
        added by hand keeps the computed lookup, with the type: ``entity`` is
        the entity sent to finalization (expansion) or ``review.entity``
        (highlight ranges). A row whose text the user edited does not come
        here: see ``_edited_occurrences`` (Story 10.9).
        """
        key = self._candidate_key_by_id.get(review.entity_id)
        if key is not None:
            return key
        return candidate_key(entity)

    def _action_rows(self, review: EntityReview) -> list[EntityReview]:
        """Rows one text edit or type change acts on (Story 10.9).

        The row itself first, then every other row of its (text, type) group,
        the group accept and reject use. In batch validation that is every
        row of the name; in single-document validation a detected row is
        alone, and a row added by hand joins the detected row of its text and
        type.

        Another row the user rejected is skipped, so a correction never
        reaches a place the user rejected; the row acted on is always kept,
        whatever its state (Story 10.9 AC11; Lionel, 2026-10-14).
        """
        rows = [review]
        for eid in self._group_ids(review):
            if eid == review.entity_id:
                continue
            other = self._reviews_by_id.get(eid)
            if other is not None and other.state != EntityReviewState.REJECTED:
                rows.append(other)
        return rows

    def modify_entity_text(
        self,
        entity_id: str,
        new_text: str,
        new_start: int,
        new_end: int,
    ) -> None:
        """Modify entity text/boundaries at every occurrence of the name.

        The edited row takes the span its caller passes. In batch
        validation every other row of its (text, type) group takes the edit
        too, each on the span the CLI's rule gives on its own current span;
        the whole edit is one undo macro, as group accept and reject are. In
        single-document validation the row stands for every occurrence of
        its variant group: each other occurrence's span is placed with the
        CLI's rule from its current span (the previous edit's, else the
        detected one) and stored with the row's one command
        (``_occurrence_spans_for_edit``), so one undo reverts them all and a
        second edit builds on the first (Story 10.9).
        """
        review = self._reviews_by_id.get(entity_id)
        rows = self._action_rows(review) if review is not None else []
        if len(rows) > 1:
            document_text = self._session.document_text
            self._undo_stack.beginMacro("Modifier le texte du groupe")
            for row in rows:
                if row is review:
                    start, end = new_start, new_end
                else:
                    start, end = ValidationWorkflow._locate_modified_span(
                        document_text, row.entity, new_text
                    )
                spans = self._occurrence_spans_for_edit(row, new_text, (start, end))
                cmd = _ModifyTextCommand(
                    self, row.entity_id, new_text, start, end, occurrence_spans=spans
                )
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
            spans = (
                self._occurrence_spans_for_edit(review, new_text, (new_start, new_end))
                if review is not None
                else None
            )
            cmd = _ModifyTextCommand(
                self, entity_id, new_text, new_start, new_end, occurrence_spans=spans
            )
            self._undo_stack.push(cmd)

    def _occurrence_spans_for_edit(
        self, review: EntityReview, new_text: str, own_span: tuple[int, int]
    ) -> list[tuple[int, int]] | None:
        """Span of each occurrence of a row's variant group after an edit.

        Returns ``None`` when the row has no stored key or the key has no
        variant entry (batch rows, rows added by hand). Otherwise, in the
        group's order: ``own_span`` for the row's own occurrence, and for
        every other occurrence the span the CLI's rule gives from its current
        span: the span the row's previous edit gave it when the row has a
        text edit, else its detected span (Story 10.9).
        """
        key = self._candidate_key_by_id.get(review.entity_id)
        if key is None or key not in self._variant_occurrences:
            return None
        occurrences = self._variant_occurrences[key]
        current = (
            self._edited_spans_by_id.get(review.entity_id)
            if review.user_modification
            else None
        )
        if current is not None and len(current) != len(occurrences):
            current = None
        document_text = self._session.document_text
        spans: list[tuple[int, int]] = []
        for index, occurrence in enumerate(occurrences):
            if occurrence is review.entity:
                spans.append(own_span)
                continue
            anchor = (
                occurrence
                if current is None
                else dataclasses.replace(
                    occurrence,
                    start_pos=current[index][0],
                    end_pos=current[index][1],
                )
            )
            spans.append(
                ValidationWorkflow._locate_modified_span(
                    document_text, anchor, new_text
                )
            )
        return spans

    def change_pseudonym(self, entity_id: str, new_pseudonym: str) -> None:
        """Override suggested pseudonym for an entity."""
        cmd = _ChangePseudonymCommand(self, entity_id, new_pseudonym)
        self._undo_stack.push(cmd)

    def change_entity_type(self, entity_id: str, new_type: str) -> None:
        """Change entity type (e.g. PERSON -> ORG) at every occurrence.

        The same rows as a text edit: in batch validation every row of the
        (text, type) group, as one undo macro. In single-document validation
        the row's other occurrences take its type at finalization
        (``expand_validated_entities``), as in the CLI (Story 10.9).
        """
        review = self._reviews_by_id.get(entity_id)
        rows = self._action_rows(review) if review is not None else []
        if len(rows) > 1:
            self._undo_stack.beginMacro("Changer le type du groupe")
            for row in rows:
                cmd = _ChangeTypeCommand(self, row.entity_id, new_type)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
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

    def _edited_entity(self, review: EntityReview) -> DetectedEntity:
        """The entity sent for a row whose text the user edited.

        The edited text, the row's current type and its (moved) span; the
        other fields come from the row's entity.
        """
        return DetectedEntity(
            text=review.user_modification or review.entity.text,
            entity_type=review.entity.entity_type,
            start_pos=review.entity.start_pos,
            end_pos=review.entity.end_pos,
            confidence=review.entity.confidence,
            gender=review.entity.gender,
            is_ambiguous=review.entity.is_ambiguous,
            source=review.entity.source,
            context_label=review.entity.context_label,
        )

    def _edited_occurrences(
        self, review: EntityReview, edited: DetectedEntity
    ) -> list[DetectedEntity] | None:
        """Every occurrence of a text-edited row, each with the edit (Story 10.9).

        Looks up the row's variant group with the key stored at init. Returns
        ``None`` when the row has no stored key or the key has no variant
        entry (batch rows, rows added by hand). Otherwise, in the group's
        order: ``edited`` for the row's own occurrence, and for every other
        occurrence a new entity with the edited text and the row's current
        type. Its span is the one the edit's command stored
        (``_occurrence_spans_for_edit``); without a stored list, the span the
        CLI's rule gives on the occurrence's detected span (the edited text
        where it overlaps it, else the detected span). The text, type and
        other fields are taken on each call, and the stored spans are set and
        restored by the edit's one command, so undo and redo revert and
        re-apply every occurrence.
        """
        key = self._candidate_key_by_id.get(review.entity_id)
        if key is None or key not in self._variant_occurrences:
            return None
        document_text = self._session.document_text
        group = self._variant_occurrences[key]
        stored = self._edited_spans_by_id.get(review.entity_id)
        if stored is not None and len(stored) != len(group):
            stored = None
        occurrences: list[DetectedEntity] = []
        for index, occurrence in enumerate(group):
            if occurrence is review.entity:
                occurrences.append(edited)
                continue
            if stored is not None:
                start, end = stored[index]
            else:
                start, end = ValidationWorkflow._locate_modified_span(
                    document_text, occurrence, edited.text
                )
            occurrences.append(
                DetectedEntity(
                    text=edited.text,
                    entity_type=edited.entity_type,
                    start_pos=start,
                    end_pos=end,
                    confidence=occurrence.confidence,
                    gender=occurrence.gender,
                    is_ambiguous=occurrence.is_ambiguous,
                    source=occurrence.source,
                    context_label=occurrence.context_label,
                )
            )
        if not any(o is edited for o in occurrences):
            occurrences.insert(0, edited)
        return occurrences

    def _validated_rows(self) -> list[tuple[EntityReview, DetectedEntity]]:
        """(row, entity sent to finalization) for every row kept by the user.

        Rejected and pending rows are skipped. A row whose text the user
        edited gives a new entity with the edited text.
        """
        rows: list[tuple[EntityReview, DetectedEntity]] = []
        for review in self._session._entity_reviews:
            if review.state == EntityReviewState.REJECTED:
                continue
            if review.state == EntityReviewState.PENDING:
                continue
            if review.user_modification:
                rows.append((review, self._edited_entity(review)))
            else:
                rows.append((review, review.entity))
        return rows

    def get_validated_entities(self) -> list[DetectedEntity]:
        """Final entity list for finalization (excludes rejected)."""
        return [entity for _, entity in self._validated_rows()]

    def expand_validated_entities(self) -> list[DetectedEntity]:
        """Expand validated canonical entities to include all variant occurrences.

        For validated rows whose candidate key (text, start_pos, entity_type)
        exists in the variant map, replaces the single canonical with ALL
        occurrences (at all positions) so every instance in the document gets
        pseudonymized. A detected row is looked up with the key stored at init,
        so a row whose type or pseudonym the user changed still expands. A
        retyped row sends every occurrence with its current type.

        A row whose text the user edited expands to every occurrence of its
        group, each on its edited span or, where the edited text is absent,
        the span it had before that edit: the previous edit's, else the
        detected one (Story 10.9). Rows added by hand are looked up with
        a key computed from the entity sent to finalization, so they normally
        stay single.
        """
        validated = self._validated_rows()
        if not self._variant_occurrences:
            return [entity for _, entity in validated]

        expanded: list[DetectedEntity] = []
        for review, entity in validated:
            if review.user_modification:
                occurrences = self._edited_occurrences(review, entity)
                expanded.extend(occurrences if occurrences is not None else [entity])
                continue
            key = self._variant_key(review, entity)
            if key not in self._variant_occurrences:
                expanded.append(entity)
                continue
            row_type = review.entity.entity_type
            stored = self._candidate_key_by_id.get(review.entity_id)
            if stored is not None and stored[2] != row_type:
                # Retyped row: every occurrence takes the row's type (Story
                # 10.9); the variant map itself is never changed.
                expanded.extend(
                    (
                        occurrence
                        if occurrence is review.entity
                        else dataclasses.replace(occurrence, entity_type=row_type)
                    )
                    for occurrence in self._variant_occurrences[key]
                )
            else:
                expanded.extend(self._variant_occurrences[key])
        return expanded

    def get_all_entity_ranges(self) -> list[tuple[int, int, str]]:
        """Return (start, end, entity_id) for all entities including variant occurrences.

        Variant occurrences share the same entity_id as their canonical entity,
        so highlights/clicks on any occurrence map back to the same review row.
        The variant map is keyed by text, start and type, so each type of a
        same-span pair maps its own occurrences to its own row. A row whose
        text the user edited gives exactly the spans finalization sends for
        it (Story 10.9).
        """
        ranges: list[tuple[int, int, str]] = []
        for review in self._session._entity_reviews:
            if review.user_modification:
                occurrences = self._edited_occurrences(
                    review, self._edited_entity(review)
                )
                if occurrences is None:
                    ranges.append(
                        (
                            review.entity.start_pos,
                            review.entity.end_pos,
                            review.entity_id,
                        )
                    )
                else:
                    ranges.extend(
                        (o.start_pos, o.end_pos, review.entity_id) for o in occurrences
                    )
                continue
            canonical = review.entity
            key = self._variant_key(review, canonical)

            if key in self._variant_occurrences:
                for occ in self._variant_occurrences[key]:
                    ranges.append((occ.start_pos, occ.end_pos, review.entity_id))
            else:
                ranges.append(
                    (canonical.start_pos, canonical.end_pos, review.entity_id)
                )
        return ranges

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
        occurrence_spans: list[tuple[int, int]] | None = None,
    ) -> None:
        super().__init__("Modifier le texte")
        self._state = state
        self._entity_id = entity_id
        self._new_text = new_text
        self._new_start = new_start
        self._new_end = new_end
        # Spans of the row's occurrences after this edit (Story 10.9).
        self._new_spans = occurrence_spans
        self._old_spans: list[tuple[int, int]] | None = None
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
            self._old_spans = self._state._edited_spans_by_id.get(self._entity_id)
            if self._new_spans is not None:
                self._state._edited_spans_by_id[self._entity_id] = list(self._new_spans)
            review.user_modification = self._new_text
            review.entity.start_pos = self._new_start
            review.entity.end_pos = self._new_end
            review.state = EntityReviewState.MODIFIED
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            if self._old_spans is None:
                self._state._edited_spans_by_id.pop(self._entity_id, None)
            else:
                self._state._edited_spans_by_id[self._entity_id] = self._old_spans
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
