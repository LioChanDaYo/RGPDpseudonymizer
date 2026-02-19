"""Tests for ValidationScreen."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QSplitter

from gdpr_pseudonymizer.gui.main_window import MainWindow
from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.gui.widgets.entity_panel import EntityPanel
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult


@pytest.fixture()
def validation_screen(
    main_window: MainWindow,
) -> ValidationScreen:
    """Get the validation screen from main window."""
    idx = main_window._screens.get("validation")
    assert idx is not None
    widget = main_window.stack.widget(idx)
    assert isinstance(widget, ValidationScreen)
    return widget


class TestScreenLayout:
    """Test validation screen layout."""

    def test_screen_has_splitter(self, validation_screen: ValidationScreen) -> None:
        assert isinstance(validation_screen.splitter, QSplitter)

    def test_splitter_has_editor_and_panel(
        self, validation_screen: ValidationScreen
    ) -> None:
        splitter = validation_screen.splitter
        assert splitter.count() == 2
        assert isinstance(validation_screen.editor, EntityEditor)
        assert isinstance(validation_screen.panel, EntityPanel)

    def test_back_button_exists(self, validation_screen: ValidationScreen) -> None:
        assert validation_screen.back_button is not None
        assert not validation_screen.back_button.isHidden()

    def test_finalize_button_exists(self, validation_screen: ValidationScreen) -> None:
        assert validation_screen.finalize_button is not None
        assert not validation_screen.finalize_button.isHidden()


class TestStartValidation:
    """Test start_validation populates widgets."""

    def test_start_validation_creates_state(
        self,
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        assert validation_screen.validation_state is not None

    def test_editor_populated_after_start(
        self,
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        text = validation_screen.editor.toPlainText()
        assert len(text) > 0

    def test_panel_populated_after_start(
        self,
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        assert validation_screen.panel.list_widget.count() > 0

    def test_step_indicator_set_to_2(
        self,
        main_window: MainWindow,
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        assert main_window.step_indicator.current_step() == 2


class TestBidirectionalSync:
    """Test editor ↔ panel synchronization."""

    def test_editor_click_highlights_panel(
        self,
        qtbot,  # type: ignore[no-untyped-def]
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        state = validation_screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id

        # Simulate editor click by emitting signal
        validation_screen.editor.entity_selected.emit(eid)
        # Panel should respond (no assertion on scroll position,
        # just verify no crash)

    def test_panel_click_scrolls_editor(
        self,
        qtbot,  # type: ignore[no-untyped-def]
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        state = validation_screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id

        # Simulate panel click
        validation_screen.panel.entity_clicked.emit(eid)
        # Editor should respond (no crash)


class TestStatusLabel:
    """Test status label updates."""

    def test_status_label_initial(
        self,
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        text = validation_screen.status_label.text()
        assert "0/6" in text  # No entities reviewed yet

    def test_status_label_after_accept(
        self,
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        state = validation_screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()
        state.accept_entity(reviews[0].entity_id)
        text = validation_screen.status_label.text()
        assert "1" in text


class TestKeyboardShortcuts:
    """Test keyboard shortcuts on validation screen."""

    def test_ctrl_z_triggers_undo(
        self,
        qtbot,  # type: ignore[no-untyped-def]
        validation_screen: ValidationScreen,
        sample_detection_result: DetectionResult,
    ) -> None:
        validation_screen.start_validation(sample_detection_result)
        state = validation_screen.validation_state
        assert state is not None

        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.accept_entity(eid)

        # Trigger undo
        validation_screen._on_undo()
        from gdpr_pseudonymizer.validation.models import EntityReviewState

        assert state.get_review(eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]
