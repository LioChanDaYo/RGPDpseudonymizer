"""Tests for validate-once-per-entity grouping in GUIValidationState.

Story 7.1 — Tasks 8.1-8.4, 8.7: text-based grouping, undo, and bulk isolation.
"""

from __future__ import annotations

from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState


def _make_grouped_detection_result(tmp_path: object) -> DetectionResult:
    """Create a DetectionResult with 3 entities sharing the same text."""
    entities = [
        DetectedEntity(
            text="Marie Dupont",
            entity_type="PERSON",
            start_pos=10,
            end_pos=22,
            confidence=0.95,
            gender="female",
            source="spacy",
        ),
        DetectedEntity(
            text="Marie Dupont",
            entity_type="PERSON",
            start_pos=100,
            end_pos=112,
            confidence=0.93,
            gender="female",
            source="spacy",
        ),
        DetectedEntity(
            text="Marie Dupont",
            entity_type="PERSON",
            start_pos=200,
            end_pos=212,
            confidence=0.90,
            gender="female",
            source="spacy",
        ),
        DetectedEntity(
            text="Marie",
            entity_type="PERSON",
            start_pos=300,
            end_pos=305,
            confidence=0.80,
            gender="female",
            source="spacy",
        ),
    ]
    doc_text = "x" * 320
    previews: dict[str, str] = {}
    for e in entities:
        previews[f"{e.text}_{e.start_pos}"] = f"Pseudo_{e.text.replace(' ', '_')}"
    return DetectionResult(
        document_text=doc_text,
        detected_entities=entities,
        pseudonym_previews=previews,
        entity_type_counts={"PERSON": 4},
        db_path=str(tmp_path) + "/test.db",
        passphrase="test",
        theme="neutral",
        input_file="test.txt",
        detection_time_seconds=0.5,
    )


class TestGroupAccept:
    """Test 8.1: accepting one occurrence confirms all same-text entities."""

    def test_accept_groups_all_same_text(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        # First 3 are "Marie Dupont"
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]
        assert len(dupont_ids) == 3

        # Accept one occurrence
        state.accept_entity(dupont_ids[0])

        # All 3 should be CONFIRMED
        for eid in dupont_ids:
            review = state.get_review(eid)
            assert review is not None
            assert review.state == EntityReviewState.CONFIRMED


class TestGroupReject:
    """Test 8.2: rejecting one occurrence rejects all same-text entities."""

    def test_reject_groups_all_same_text(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]

        state.reject_entity(dupont_ids[1])

        for eid in dupont_ids:
            review = state.get_review(eid)
            assert review is not None
            assert review.state == EntityReviewState.REJECTED


class TestGroupUndo:
    """Test 8.3: undo reverses the entire group action."""

    def test_undo_reverts_group_accept(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]

        state.accept_entity(dupont_ids[0])

        # Verify all confirmed
        for eid in dupont_ids:
            assert state.get_review(eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        # Undo
        state.undo_stack.undo()

        # All should revert to PENDING
        for eid in dupont_ids:
            assert state.get_review(eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]

    def test_undo_reverts_group_reject(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]

        state.reject_entity(dupont_ids[2])
        state.undo_stack.undo()

        for eid in dupont_ids:
            assert state.get_review(eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]


class TestNoGroupingForDifferentText:
    """Test 8.4: different text entities are independent."""

    def test_accept_marie_dupont_does_not_affect_marie(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]
        marie_ids = [r.entity_id for r in reviews if r.entity.text == "Marie"]
        assert len(marie_ids) == 1

        # Accept "Marie Dupont" group
        state.accept_entity(dupont_ids[0])

        # "Marie" should still be PENDING
        review = state.get_review(marie_ids[0])
        assert review is not None
        assert review.state == EntityReviewState.PENDING


class TestBulkDoesNotTriggerGrouping:
    """Test 8.7: bulk_accept with explicit IDs does NOT trigger grouping."""

    def test_bulk_accept_only_affects_explicit_ids(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]

        # Bulk accept only first occurrence
        state.bulk_accept([dupont_ids[0]])

        # Only the explicitly provided ID should be CONFIRMED
        assert state.get_review(dupont_ids[0]).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]
        assert state.get_review(dupont_ids[1]).state == EntityReviewState.PENDING  # type: ignore[union-attr]
        assert state.get_review(dupont_ids[2]).state == EntityReviewState.PENDING  # type: ignore[union-attr]

    def test_bulk_reject_only_affects_explicit_ids(self, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
        state = GUIValidationState()
        dr = _make_grouped_detection_result(tmp_path)
        state.init_from_detection_result(dr)

        reviews = state.get_all_entities()
        dupont_ids = [r.entity_id for r in reviews if r.entity.text == "Marie Dupont"]

        # Bulk reject only second occurrence
        state.bulk_reject([dupont_ids[1]])

        assert state.get_review(dupont_ids[0]).state == EntityReviewState.PENDING  # type: ignore[union-attr]
        assert state.get_review(dupont_ids[1]).state == EntityReviewState.REJECTED  # type: ignore[union-attr]
        assert state.get_review(dupont_ids[2]).state == EntityReviewState.PENDING  # type: ignore[union-attr]
