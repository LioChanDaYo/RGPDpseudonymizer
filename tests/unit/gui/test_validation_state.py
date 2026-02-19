"""Tests for GUIValidationState adapter."""

from __future__ import annotations

from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.validation.models import EntityReviewState


class TestGUIValidationStateInit:
    """Test initialization from DetectionResult."""

    def test_init_from_detection_result(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()
        state.init_from_detection_result(sample_detection_result)

        assert len(state.get_all_entities()) == 6
        assert state.get_pending_count() == 6

    def test_pseudonym_previews_assigned(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        # Each entity should have a suggested pseudonym from previews
        for review in reviews:
            pseudonym = state.get_pseudonym(review.entity_id)
            assert pseudonym, f"No pseudonym for {review.entity.text}"


class TestAcceptReject:
    """Test accept/reject entity actions."""

    def test_accept_entity(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.accept_entity(eid)

        review = state.get_review(eid)
        assert review is not None
        assert review.state == EntityReviewState.CONFIRMED
        assert state.get_pending_count() == 5

    def test_reject_entity(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.reject_entity(eid)

        review = state.get_review(eid)
        assert review is not None
        assert review.state == EntityReviewState.REJECTED

    def test_accept_emits_state_changed(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id

        with qtbot.waitSignal(state.state_changed, timeout=1000) as blocker:
            state.accept_entity(eid)
        assert blocker.args == [eid]


class TestModifyEntity:
    """Test entity modification actions."""

    def test_modify_entity_text(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.modify_entity_text(eid, "Jean-Pierre Dupont", 20, 38)

        review = state.get_review(eid)
        assert review is not None
        assert review.state == EntityReviewState.MODIFIED
        assert review.user_modification == "Jean-Pierre Dupont"

    def test_change_pseudonym(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.change_pseudonym(eid, "Pierre Lambert")

        review = state.get_review(eid)
        assert review is not None
        assert review.custom_pseudonym == "Pierre Lambert"
        assert state.get_pseudonym(eid) == "Pierre Lambert"

    def test_change_entity_type(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id  # PERSON
        state.change_entity_type(eid, "ORG")

        review = state.get_review(eid)
        assert review is not None
        assert review.entity.entity_type == "ORG"
        assert review.state == EntityReviewState.MODIFIED


class TestAddEntity:
    """Test manual entity addition."""

    def test_add_entity(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        initial_count = len(state.get_all_entities())
        new_id = state.add_entity("Bordeaux", "LOCATION", 150, 158)

        assert len(state.get_all_entities()) == initial_count + 1
        review = state.get_review(new_id)
        assert review is not None
        assert review.state == EntityReviewState.ADDED
        assert review.entity.text == "Bordeaux"
        assert review.entity.source == "manual"

    def test_add_entity_emits_signal(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        with qtbot.waitSignal(state.entity_added, timeout=1000):
            state.add_entity("Bordeaux", "LOCATION", 150, 158)


class TestBulkActions:
    """Test bulk accept/reject operations."""

    def test_bulk_accept(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        ids = [r.entity_id for r in reviews[:3]]
        state.bulk_accept(ids)

        for eid in ids:
            review = state.get_review(eid)
            assert review is not None
            assert review.state == EntityReviewState.CONFIRMED

    def test_bulk_reject(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        ids = [r.entity_id for r in reviews[:2]]
        state.bulk_reject(ids)

        for eid in ids:
            review = state.get_review(eid)
            assert review is not None
            assert review.state == EntityReviewState.REJECTED


class TestUndoRedo:
    """Test undo/redo support."""

    def test_undo_reverses_accept(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.accept_entity(eid)

        assert state.get_review(eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]
        state.undo_stack.undo()
        assert state.get_review(eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]

    def test_redo_reapplies_accept(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.accept_entity(eid)
        state.undo_stack.undo()
        state.undo_stack.redo()

        assert state.get_review(eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

    def test_bulk_undo_reverses_entire_bulk(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        ids = [r.entity_id for r in reviews[:3]]
        state.bulk_accept(ids)

        # All three should be confirmed
        for eid in ids:
            assert state.get_review(eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        # Single undo should revert all three
        state.undo_stack.undo()
        for eid in ids:
            assert state.get_review(eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]


class TestQueryMethods:
    """Test query methods."""

    def test_get_validated_entities_excludes_rejected(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        state.accept_entity(reviews[0].entity_id)
        state.reject_entity(reviews[1].entity_id)
        state.accept_entity(reviews[2].entity_id)

        validated = state.get_validated_entities()
        assert len(validated) == 2
        assert reviews[1].entity.text not in [e.text for e in validated]

    def test_get_summary(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        state.accept_entity(reviews[0].entity_id)
        state.reject_entity(reviews[1].entity_id)

        summary = state.get_summary()
        assert summary["accepted"] == 1
        assert summary["rejected"] == 1
        assert summary["total"] == 6

    def test_get_entities_by_type(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        persons = state.get_entities_by_type("PERSON")
        assert len(persons) == 3
        locations = state.get_entities_by_type("LOCATION")
        assert len(locations) == 2
        orgs = state.get_entities_by_type("ORG")
        assert len(orgs) == 1

    def test_known_entity_classification(
        self, qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
    ) -> None:
        """Known entity classification requires a real DB — test the flag API."""
        state = GUIValidationState()

        state.init_from_detection_result(sample_detection_result)

        reviews = state.get_all_entities()
        # By default, no entities are known (no DB)
        for review in reviews:
            assert not state.is_entity_known(review.entity_id)
