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

from gdpr_pseudonymizer.core.custom_pseudonym import (
    NameKey,
    Refusal,
    check_custom_pseudonym,
    document_words,
)
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import (
    CandidateKey,
    EntityReview,
    EntityReviewState,
    NameOfReview,
    Place,
    ValidationSession,
    candidate_key,
    count_names_left_in_clear,
    place_of,
)
from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult

# The kinds of decision a row can hold (Story 10.10, AC14): kept (the row is
# sent: accepted, corrected, added) or dropped (rejected). Pending is neither.
_KEPT = frozenset(
    {EntityReviewState.CONFIRMED, EntityReviewState.MODIFIED, EntityReviewState.ADDED}
)
_DROPPED = frozenset({EntityReviewState.REJECTED})


def _same_kind(old: EntityReviewState | None, new: EntityReviewState) -> bool:
    """True when a row's decision stays kept, or stays dropped."""
    if old is None:
        return False
    return (old in _KEPT and new in _KEPT) or (old in _DROPPED and new in _DROPPED)


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
        # Name and type of each row added by hand, as it was added (Story
        # 10.10, Lionel's Q3): the name a correction or a type change groups
        # it by, fixed like a detected row's stored key, because a type
        # change retypes the row in place.
        self._hand_key_by_id: dict[str, tuple[str, str]] = {}
        # Ids of the rows whose current decision is their own: made on that
        # place alone (Story 10.10 AC14; Lionel, 2026-10-14, Q5-Q7 and
        # Ctrl+Shift+R). That is a row ticked in the list and accepted or
        # rejected, a row rejected with Ctrl+Shift+R, a row added by hand,
        # and an accept, reject, correction, type change or custom pseudonym
        # (Story 10.11, Lionel's Q-B) that reached that row only. A group
        # action skips another row's own opposite decision. Every command
        # that changes a row saves and restores the row's flag, so undo and
        # redo keep it exact.
        self._own_ids: set[str] = set()

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
        self._hand_key_by_id.clear()
        self._own_ids.clear()
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
        """Mark entity (and the other rows of its group) as confirmed.

        The row clicked is always accepted. Another row of its group
        (``_group_ids``) is accepted too, except a row the user rejected on
        its own: a place rejected only with its group comes back with the
        group (Story 10.10 AC14 (b); Lionel, 2026-10-14, "Skip rejected" and
        Q7 "Whole group back"). The accept is the row's own when it reaches
        that row only; otherwise every row it reaches follows the group.
        """
        review = self._reviews_by_id.get(entity_id)
        if review is None:
            return
        group_ids = [
            eid
            for eid in self._group_ids(review)
            if eid == entity_id or not self._decided_alone_id(eid, _DROPPED)
        ]
        if len(group_ids) > 1:
            self._undo_stack.beginMacro("Accepter le groupe")
            for eid in group_ids:
                cmd = _SingleActionCommand(self, eid, EntityReviewState.CONFIRMED)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
            cmd = _SingleActionCommand(
                self, entity_id, EntityReviewState.CONFIRMED, alone=True
            )
            self._undo_stack.push(cmd)

    def reject_entity(self, entity_id: str) -> None:
        """Mark entity (and the other rows of its group) as rejected.

        The row clicked is always rejected. Another row of its group
        (``_group_ids``) is rejected too, except a row the user accepted or
        corrected on its own (Story 10.10 AC14 (c); Lionel's Q5, 2026-10-14,
        "Skip your own"). A row that only followed a group action follows
        this one, so accepting a name and then rejecting it from any place
        rejects every place. The reject is the row's own when it reaches that
        row only; otherwise every row it reaches follows the group.
        """
        review = self._reviews_by_id.get(entity_id)
        if review is None:
            return
        group_ids = [
            eid
            for eid in self._group_ids(review)
            if eid == entity_id or not self._decided_alone_id(eid, _KEPT)
        ]
        if len(group_ids) > 1:
            self._undo_stack.beginMacro("Rejeter le groupe")
            for eid in group_ids:
                cmd = _SingleActionCommand(self, eid, EntityReviewState.REJECTED)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
            cmd = _SingleActionCommand(
                self, entity_id, EntityReviewState.REJECTED, alone=True
            )
            self._undo_stack.push(cmd)

    def _group_ids(self, review: EntityReview) -> list[str]:
        """Ids of the rows that one accept or reject acts on.

        A detected row uses the key stored at init: its group is every
        detected row of that (text, type), so a group action on a retyped
        row acts on its original group. A row added by hand has no stored
        key and is a group of one, so an accept or a reject on it never
        reaches a detected row (Story 10.10 AC3). The index holds detected
        rows only, so a detected row's group never holds a row added by hand.
        Corrections and type changes use ``_action_rows`` instead.
        """
        key = self._candidate_key_by_id.get(review.entity_id)
        if key is None:
            return [review.entity_id]
        return self._group_index.get((key[0], key[2]), [review.entity_id])

    def _decided_alone(
        self, review: EntityReview, kinds: frozenset[EntityReviewState]
    ) -> bool:
        """Whether the row holds a decision of ``kinds`` made on its own (AC14)."""
        return review.entity_id in self._own_ids and review.state in kinds

    def _decided_alone_id(
        self, entity_id: str, kinds: frozenset[EntityReviewState]
    ) -> bool:
        review = self._reviews_by_id.get(entity_id)
        return review is not None and self._decided_alone(review, kinds)

    def _set_own(self, entity_id: str, own: bool) -> None:
        """Record whether a row's current decision is its own (AC14)."""
        if own:
            self._own_ids.add(entity_id)
        else:
            self._own_ids.discard(entity_id)

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

    def _name_key(self, review: EntityReview) -> tuple[str, str] | None:
        """(text, type) a row's corrections and type changes group it by.

        A detected row: its stored key (Story 10.8). A row added by hand: the
        text and type it was added with (Story 10.10). Both are fixed when
        the row is created, so a type change or a text edit never moves a
        row out of its group.
        """
        key = self._candidate_key_by_id.get(review.entity_id)
        if key is not None:
            return (key[0], key[2])
        return self._hand_key_by_id.get(review.entity_id)

    def _action_rows(self, review: EntityReview) -> list[EntityReview]:
        """Rows one text edit or type change acts on (Stories 10.9, 10.10).

        The row itself first, always, whatever its state; then every other
        row of the same name and type (``_name_key``), found by the detector
        or added by hand (Lionel's Q3 on Story 10.10). In batch validation
        that is every row of the name; in single-document validation it is
        the detected row of the name (which stands for its variant
        occurrences) and the rows added by hand.

        Another row the user rejected on its own is skipped, so a correction
        never reaches a place the user rejected on that place; a row rejected
        only with its group is reached and takes the correction (Story 10.10
        AC14 (d); Lionel, 2026-10-14, Q7, which refines Story 10.9's rule of
        skipping every rejected row).

        Accept and reject do not use this: they use ``_group_ids``, where a
        row added by hand is alone.
        """
        rows = [review]
        name = self._name_key(review)
        if name is None:
            return rows
        for other in self._session._entity_reviews:
            if other is review or self._name_key(other) != name:
                continue
            if self._decided_alone(other, _DROPPED):
                continue
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
        second edit builds on the first (Story 10.9). The rows are those of
        ``_action_rows``: every place of the name and type, found or added
        by hand, except another place rejected on its own (Story 10.10). The
        edit is the row's own when it reaches that row only.
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
                self,
                entity_id,
                new_text,
                new_start,
                new_end,
                occurrence_spans=spans,
                alone=True,
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
        """Set a custom pseudonym at every place of the name (Story 10.11).

        The rows of ``_pseudonym_rows`` (Lionel's Q3): the row itself, then
        every other row of the same name as the written file reads it now
        (its current text and type, Story 10.16), found or added by hand,
        except another row rejected on its own; one undo reverts them all.
        Like a correction (Lionel's Q-B), it is the row's own decision when
        it reaches that row only; when it reaches several rows they follow
        the group.

        The checks of Lionel's Q1, Q2, Q-C and Q-D are made before, by
        ``custom_pseudonym_refusal``; undo and redo never open the database.
        """
        review = self._reviews_by_id.get(entity_id)
        rows = self._pseudonym_rows(review) if review is not None else []
        if len(rows) > 1:
            self._undo_stack.beginMacro("Changer le pseudonyme du groupe")
            for row in rows:
                cmd = _ChangePseudonymCommand(self, row.entity_id, new_pseudonym)
                self._undo_stack.push(cmd)
            self._undo_stack.endMacro()
        else:
            cmd = _ChangePseudonymCommand(self, entity_id, new_pseudonym, alone=True)
            self._undo_stack.push(cmd)

    def _pseudonym_rows(self, review: EntityReview) -> list[EntityReview]:
        """Rows one custom pseudonym acts on (Story 10.11, Lionel's Q3).

        ``_action_rows``' rule, with the name read as the written file reads
        it now: the mapping key of the row's current text and its current
        type (``_sent_name``; Story 10.16, Codex #7), so a titled form of the
        name ("M. Zorbal" next to "Zorbal") is the same name, a place
        corrected or retyped into another name is not, and a place corrected
        into the name is. The row itself first, always; then every other row
        of the name, found or added by hand, except a row rejected on its
        own.
        """
        rows = [review]
        name = self._sent_name(review)
        for other in self._session._entity_reviews:
            if other is review or self._sent_name(other) != name:
                continue
            if self._decided_alone(other, _DROPPED):
                continue
            rows.append(other)
        return rows

    @staticmethod
    def _sent_name(review: EntityReview) -> NameKey:
        """(mapping key, type) of the entity a row sends to finalization: its
        edited text or its detected text, and its current type (10.11)."""
        text = review.user_modification or review.entity.text
        entity_type = review.entity.entity_type
        return (mapping_key(text, entity_type), entity_type)

    def get_custom_pseudonyms(self) -> dict[NameKey, str]:
        """The custom pseudonym of each name sent to finalization (10.11).

        Keyed by ``_sent_name``; the first row of a name that holds one
        gives it, so the file holds one pseudonym per name and type.
        """
        customs: dict[NameKey, str] = {}
        for review, _entity in self._validated_rows():
            if review.custom_pseudonym:
                customs.setdefault(self._sent_name(review), review.custom_pseudonym)
        return customs

    def custom_pseudonym_refusal(
        self, entity_id: str, pseudonym: str, db_path: str, passphrase: str
    ) -> Refusal | None:
        """The rule a custom pseudonym breaks for a row's name, or None.

        Checks Lionel's Q1, Q-D, Q2 and Q-C (Story 10.11) against the mapping
        database, this document, the review's names whatever their capitals
        (every row not rejected, ``_review_names``; Story 10.16, Codex #8)
        and the review's other custom pseudonyms. The whole reach is checked
        before it is applied (Story 10.16, Codex #7): every name of the rows
        ``change_pseudonym`` would set (``_pseudonym_rows``), the others'
        custom pseudonyms read from the rows outside it. The database is
        opened here, as the known-entity pass does; when it cannot be opened,
        only this document and this review are checked, and finalization
        checks the rest.

        Args:
            entity_id: The row the pseudonym is set on
            pseudonym: The normalized custom pseudonym
            db_path: Path to the mapping database ("" when there is none)
            passphrase: Database passphrase
        """
        review = self._reviews_by_id.get(entity_id)
        if review is None:
            return None
        reach = self._pseudonym_rows(review)
        names = list(dict.fromkeys(self._sent_name(row) for row in reach))
        others: dict[NameKey, str] = {}
        for other in self._session._entity_reviews:
            if any(other is row for row in reach) or not other.custom_pseudonym:
                continue
            if other.state == EntityReviewState.REJECTED:
                continue
            key = self._sent_name(other)
            if key not in names:
                others.setdefault(key, other.custom_pseudonym)
        stored = None
        if db_path:
            try:
                from gdpr_pseudonymizer.data.database import open_database
                from gdpr_pseudonymizer.data.repositories.mapping_repository import (
                    SQLiteMappingRepository,
                )

                with open_database(db_path, passphrase) as db_session:
                    stored = SQLiteMappingRepository(db_session).find_all()
            except Exception:
                stored = None  # finalization checks the database again
        document_text = self._session.document_text
        words = document_words(document_text)
        review_names = self._review_names()
        for name in names:
            # The reach's other names (none, by ``_pseudonym_rows``' rule)
            # would get the same pseudonym
            reach_others = {key: pseudonym for key in names if key != name}
            refusal = check_custom_pseudonym(
                stored,
                name[0],
                name[1],
                pseudonym,
                document_text,
                {**others, **reach_others},
                words,
                review_names=review_names,
            )
            if refusal is not None:
                return refusal
        return None

    def change_entity_type(self, entity_id: str, new_type: str) -> None:
        """Change entity type (e.g. PERSON -> ORG) at every occurrence.

        The same rows as a text edit: in batch validation every row of the
        (text, type) group, as one undo macro. In single-document validation
        the row's other occurrences take its type at finalization
        (``expand_validated_entities``), as in the CLI (Story 10.9). Rows
        added by hand of the same name and type take it too, and another
        row rejected on its own is skipped (``_action_rows``, Story 10.10).
        The change is the row's own when it reaches that row only.
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
            cmd = _ChangeTypeCommand(self, entity_id, new_type, alone=True)
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

    def bulk_accept(self, entity_ids: list[str], alone: bool = True) -> None:
        """Accept multiple entities as a single undoable action.

        Acts on exactly the rows given. ``alone`` (Story 10.10 AC14): True
        (the default) when the rows were ticked one by one in the list, so
        each accept is that row's own; Ctrl+Shift+A passes False, so its
        accepts follow the group.
        """
        if not entity_ids:
            return
        self._undo_stack.beginMacro("Accepter la sélection")
        for eid in entity_ids:
            cmd = _SingleActionCommand(
                self, eid, EntityReviewState.CONFIRMED, alone=alone
            )
            self._undo_stack.push(cmd)
        self._undo_stack.endMacro()

    def bulk_reject(self, entity_ids: list[str], alone: bool = True) -> None:
        """Reject multiple entities as a single undoable action.

        Acts on exactly the rows given. ``alone`` (Story 10.10 AC14): True
        (the default) for the rows ticked in the list and for Ctrl+Shift+R,
        so each reject is that row's own (Lionel, 2026-10-14, "Stay
        rejected").
        """
        if not entity_ids:
            return
        self._undo_stack.beginMacro("Rejeter la sélection")
        for eid in entity_ids:
            cmd = _SingleActionCommand(
                self, eid, EntityReviewState.REJECTED, alone=alone
            )
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
        """Accept the known entities still to review.

        Only pending rows: a rejected place stays rejected, and a corrected
        place keeps its correction and stays "modifié" (Story 10.10 AC14
        (e); Lionel's Q6, 2026-10-14, "Skip rejected"). The accepts follow
        the group.
        """
        ids = [
            r.entity_id
            for r in self._session._entity_reviews
            if r.entity_id in self._known_entity_ids
            and r.state == EntityReviewState.PENDING
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

    def names_left_in_clear(self, sent: list[DetectedEntity]) -> int:
        """Count pending names left in clear for Story 10.13 AC1.

        Per Lionel's decision of 2026-10-16, a row's places are its variant
        occurrences in single-document validation, else its own span.
        ``sent`` is ``get_validated_entities()`` in batch mode and
        ``expand_validated_entities()`` for a single document.
        """
        pending: list[tuple[NameOfReview, list[Place]]] = []
        for review in self._session._entity_reviews:
            if review.state != EntityReviewState.PENDING:
                continue
            key = self._variant_key(review, review.entity)
            occurrences = self._variant_occurrences.get(key, [review.entity])
            name = (review.entity.text, review.entity.entity_type)
            pending.append((name, [place_of(entity) for entity in occurrences]))
        return count_names_left_in_clear(pending, sent)

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
        return self._expand(self._validated_rows())

    def _expand(
        self, rows: list[tuple[EntityReview, DetectedEntity]]
    ) -> list[DetectedEntity]:
        """``expand_validated_entities``' expansion of the given (row, entity
        sent) pairs (Story 10.16: shared with ``_review_names``)."""
        if not self._variant_occurrences:
            return [entity for _, entity in rows]

        expanded: list[DetectedEntity] = []
        for review, entity in rows:
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

    def _review_names(self) -> list[str]:
        """The mapping keys of the review's names that are not rejected
        (Story 10.16, Codex #8): the entities every row still to review,
        accepted, corrected, retyped or added by hand would send, expanded
        to their variant occurrences exactly as ``expand_validated_entities``
        expands the rows it sends."""
        rows = [
            (
                review,
                (
                    self._edited_entity(review)
                    if review.user_modification
                    else review.entity
                ),
            )
            for review in self._session._entity_reviews
            if review.state != EntityReviewState.REJECTED
        ]
        names = (mapping_key(e.text, e.entity_type) for e in self._expand(rows))
        return list(dict.fromkeys(names))

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


def _own_after(
    state: GUIValidationState,
    entity_id: str,
    alone: bool,
    old_own: bool,
    old_state: EntityReviewState | None,
    new_state: EntityReviewState,
) -> None:
    """Set a row's flag after a command changed it (Story 10.10 AC14 (a)).

    The decision is the row's own when the action was aimed at that row
    alone; otherwise the row keeps its flag only if it had one and its
    decision stays of the same kind (kept, or dropped).
    """
    state._set_own(entity_id, alone or (old_own and _same_kind(old_state, new_state)))


class _SingleActionCommand(QUndoCommand):
    """Accept or reject a single entity."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_state: EntityReviewState,
        alone: bool = False,
    ) -> None:
        label = "Accepter" if new_state == EntityReviewState.CONFIRMED else "Rejeter"
        super().__init__(label)
        self._state = state
        self._entity_id = entity_id
        self._new_state = new_state
        self._old_state: EntityReviewState | None = None
        # Story 10.10: whether the action is aimed at this row alone, and the
        # row's flag before the action (restored by undo).
        self._alone = alone
        self._old_own = False

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            self._old_state = review.state
            self._old_own = self._entity_id in self._state._own_ids
            review.state = self._new_state
            _own_after(
                self._state,
                self._entity_id,
                self._alone,
                self._old_own,
                self._old_state,
                self._new_state,
            )
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review and self._old_state is not None:
            review.state = self._old_state
            self._state._set_own(self._entity_id, self._old_own)
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
        alone: bool = False,
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
        self._old_custom: str | None = None
        # Story 10.10: as in _SingleActionCommand.
        self._alone = alone
        self._old_own = False

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            # Story 10.11 (Lionel's Q-E): a correction removes the row's
            # custom pseudonym; undo brings it back.
            self._old_custom = review.custom_pseudonym
            review.custom_pseudonym = None
            self._old_text = review.entity.text
            self._old_start = review.entity.start_pos
            self._old_end = review.entity.end_pos
            self._old_state = review.state
            self._old_modification = review.user_modification
            self._old_spans = self._state._edited_spans_by_id.get(self._entity_id)
            self._old_own = self._entity_id in self._state._own_ids
            if self._new_spans is not None:
                self._state._edited_spans_by_id[self._entity_id] = list(self._new_spans)
            review.user_modification = self._new_text
            review.entity.start_pos = self._new_start
            review.entity.end_pos = self._new_end
            review.state = EntityReviewState.MODIFIED
            _own_after(
                self._state,
                self._entity_id,
                self._alone,
                self._old_own,
                self._old_state,
                EntityReviewState.MODIFIED,
            )
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            if self._old_spans is None:
                self._state._edited_spans_by_id.pop(self._entity_id, None)
            else:
                self._state._edited_spans_by_id[self._entity_id] = self._old_spans
            review.user_modification = self._old_modification
            review.custom_pseudonym = self._old_custom
            review.entity.start_pos = self._old_start
            review.entity.end_pos = self._old_end
            if self._old_state is not None:
                review.state = self._old_state
            self._state._set_own(self._entity_id, self._old_own)
            self._state.state_changed.emit(self._entity_id)


class _ChangePseudonymCommand(QUndoCommand):
    """Change pseudonym for an entity."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_pseudonym: str,
        alone: bool = False,
    ) -> None:
        super().__init__("Changer le pseudonyme")
        self._state = state
        self._entity_id = entity_id
        self._new_pseudonym = new_pseudonym
        self._old_pseudonym: str | None = None
        self._old_state: EntityReviewState | None = None
        # Story 10.11 (Lionel's Q-B): like a correction, the row's own
        # decision when it reaches that row only (as in
        # _SingleActionCommand); undo restores the flag it had.
        self._alone = alone
        self._old_own = False

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            self._old_pseudonym = review.custom_pseudonym
            self._old_state = review.state
            self._old_own = self._entity_id in self._state._own_ids
            review.custom_pseudonym = self._new_pseudonym
            review.state = EntityReviewState.MODIFIED
            _own_after(
                self._state,
                self._entity_id,
                self._alone,
                self._old_own,
                self._old_state,
                EntityReviewState.MODIFIED,
            )
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            review.custom_pseudonym = self._old_pseudonym
            if self._old_state is not None:
                review.state = self._old_state
            self._state._set_own(self._entity_id, self._old_own)
            self._state.state_changed.emit(self._entity_id)


class _ChangeTypeCommand(QUndoCommand):
    """Change entity type."""

    def __init__(
        self,
        state: GUIValidationState,
        entity_id: str,
        new_type: str,
        alone: bool = False,
    ) -> None:
        super().__init__("Changer le type")
        self._state = state
        self._entity_id = entity_id
        self._new_type = new_type
        self._old_type: str | None = None
        self._old_state: EntityReviewState | None = None
        self._old_custom: str | None = None
        # Story 10.10: as in _SingleActionCommand.
        self._alone = alone
        self._old_own = False

    def redo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            # Story 10.11 (Lionel's Q-E): a type change removes the row's
            # custom pseudonym; undo brings it back.
            self._old_custom = review.custom_pseudonym
            review.custom_pseudonym = None
            self._old_type = review.entity.entity_type
            self._old_state = review.state
            self._old_own = self._entity_id in self._state._own_ids
            review.entity.entity_type = self._new_type
            review.state = EntityReviewState.MODIFIED
            _own_after(
                self._state,
                self._entity_id,
                self._alone,
                self._old_own,
                self._old_state,
                EntityReviewState.MODIFIED,
            )
            self._state.state_changed.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.get(self._entity_id)
        if review:
            review.custom_pseudonym = self._old_custom
            if self._old_type is not None:
                review.entity.entity_type = self._old_type
            if self._old_state is not None:
                review.state = self._old_state
            self._state._set_own(self._entity_id, self._old_own)
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
        # Story 10.10: the row's fixed name and type for corrections, and an
        # added row is the user's own decision.
        self._state._hand_key_by_id[self._entity_id] = (self._text, self._entity_type)
        self._state._own_ids.add(self._entity_id)
        self._state.entity_added.emit(self._entity_id)

    def undo(self) -> None:
        review = self._state._reviews_by_id.pop(self._entity_id, None)
        self._state._hand_key_by_id.pop(self._entity_id, None)
        self._state._own_ids.discard(self._entity_id)
        if review:
            self._state._session._entity_reviews.remove(review)
            if review.entity in self._state._session.entities:
                self._state._session.entities.remove(review.entity)
            self._state.entity_removed.emit(self._entity_id)
