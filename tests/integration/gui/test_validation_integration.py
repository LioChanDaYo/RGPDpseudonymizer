"""Integration tests for the validation flow.

Tests end-to-end: detection result → validate entities → verify state.
Mock NLP detection but test real validation state + widget interactions.
"""

from __future__ import annotations

from gdpr_pseudonymizer.gui.main_window import MainWindow
from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.validation.models import EntityReviewState


def _get_validation_screen(window: MainWindow) -> ValidationScreen:
    idx = window._screens.get("validation")
    assert idx is not None
    widget = window.stack.widget(idx)
    assert isinstance(widget, ValidationScreen)
    return widget


class TestEndToEndAcceptAll:
    """Test: accept all → all entities marked confirmed."""

    def test_accept_all_entities(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        # Accept all entities
        for review in state.get_all_entities():
            state.accept_entity(review.entity_id)

        # All should be confirmed
        for review in state.get_all_entities():
            assert review.state == EntityReviewState.CONFIRMED

        # Validated list should include all
        validated = state.get_validated_entities()
        assert len(validated) == 4


class TestEndToEndRejectSome:
    """Test: reject some → output preserves original text for rejected."""

    def test_reject_excludes_from_validated(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()

        # Accept first two, reject third, accept fourth
        state.accept_entity(reviews[0].entity_id)
        state.accept_entity(reviews[1].entity_id)
        state.reject_entity(reviews[2].entity_id)
        state.accept_entity(reviews[3].entity_id)

        validated = state.get_validated_entities()
        assert len(validated) == 3

        rejected_text = reviews[2].entity.text
        assert rejected_text not in [e.text for e in validated]


class TestEndToEndAddManualEntity:
    """Test: add manual entity → included in validated list."""

    def test_manual_entity_in_validated(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        # Accept all existing entities
        for review in state.get_all_entities():
            state.accept_entity(review.entity_id)

        # Add manual entity
        state.add_entity("Bordeaux", "LOCATION", 95, 103)

        validated = state.get_validated_entities()
        # 4 original + 1 manual = 5
        assert len(validated) == 5
        assert "Bordeaux" in [e.text for e in validated]


class TestEndToEndChangePseudonym:
    """Test: change pseudonym → custom pseudonym preserved in state."""

    def test_custom_pseudonym_persists(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id

        state.change_pseudonym(eid, "Pierre Lambert")
        assert state.get_pseudonym(eid) == "Pierre Lambert"

        # Review should be modified
        review = state.get_review(eid)
        assert review is not None
        assert review.custom_pseudonym == "Pierre Lambert"


class TestEndToEndUndoRedo:
    """Test: undo/redo across validation flow."""

    def test_undo_redo_flow(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id

        # Accept → undo → should be pending
        state.accept_entity(eid)
        assert state.get_review(eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        state.undo_stack.undo()
        assert state.get_review(eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]

        # Redo → should be confirmed again
        state.undo_stack.redo()
        assert state.get_review(eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]


class TestWidgetSync:
    """Test editor/panel synchronization during validation flow."""

    def test_accept_updates_both_widgets(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        initial_selections = len(screen.editor.extraSelections())

        reviews = state.get_all_entities()
        state.accept_entity(reviews[0].entity_id)

        # Editor highlights should still exist (just color/format changes)
        assert len(screen.editor.extraSelections()) >= initial_selections - 1

        # Panel pending counter should update
        assert (
            "3" in screen.panel.pending_label.text()
            or "Toutes" in screen.panel.pending_label.text()
        )
