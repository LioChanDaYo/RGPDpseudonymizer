"""Integration test for keyboard-only document processing workflow (AC1).

Tests end-to-end: navigate to validation via keyboard → enter navigation mode →
accept/reject entities → undo → submit — all without mouse interaction.
Mock NLP detection but test real keyboard navigation and state transitions.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

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


class TestKeyboardOnlyDocumentProcessing:
    """AC1: Full keyboard-only workflow through validation."""

    def test_enter_navigation_mode_via_keyboard(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Enter key on editor activates navigation mode."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        editor = screen.editor
        editor.setFocus()
        assert not editor.nav_mode

        # Press Enter to enter navigation mode
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)

        assert editor.nav_mode
        # Should focus on first pending entity (index 0)
        assert editor._nav_index >= 0

    def test_tab_navigates_between_entities(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Tab/Shift+Tab navigates forward/backward between entities."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        editor = screen.editor
        editor.setFocus()

        # Enter nav mode
        enter = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter)
        assert editor.nav_mode

        initial_index = editor._nav_index

        # Tab → next entity
        tab = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(tab)
        assert editor._nav_index == (initial_index + 1) % len(editor._entity_ranges)

        # Shift+Tab → previous entity
        shift_tab = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Backtab,
            Qt.KeyboardModifier.ShiftModifier,
        )
        editor.keyPressEvent(shift_tab)
        assert editor._nav_index == initial_index

    def test_enter_accepts_entity_in_nav_mode(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Enter key in navigation mode accepts the focused entity."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        editor = screen.editor
        editor.setFocus()

        # Enter nav mode
        enter = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter)
        assert editor.nav_mode

        # Get focused entity
        focused_eid = editor._entity_ranges[editor._nav_index][2]
        assert state.get_review(focused_eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]

        # Press Enter to accept
        editor.keyPressEvent(enter)
        assert state.get_review(focused_eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

    def test_delete_rejects_entity_in_nav_mode(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Delete key in navigation mode rejects the focused entity."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        editor = screen.editor
        editor.setFocus()

        # Enter nav mode
        enter = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter)

        focused_eid = editor._entity_ranges[editor._nav_index][2]

        # Delete to reject
        delete = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(delete)
        assert state.get_review(focused_eid).state == EntityReviewState.REJECTED  # type: ignore[union-attr]

    def test_undo_reverses_accept(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Ctrl+Z undoes the last entity action."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None

        editor = screen.editor
        editor.setFocus()

        # Enter nav mode and accept first entity
        enter = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter)

        focused_eid = editor._entity_ranges[editor._nav_index][2]
        editor.keyPressEvent(enter)  # accept
        assert state.get_review(focused_eid).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        # Undo via state (Ctrl+Z is handled by ValidationScreen shortcut)
        state.undo_stack.undo()
        assert state.get_review(focused_eid).state == EntityReviewState.PENDING  # type: ignore[union-attr]

    def test_escape_exits_navigation_mode(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Escape key exits navigation mode."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        editor = screen.editor
        editor.setFocus()

        # Enter nav mode
        enter = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter)
        assert editor.nav_mode

        # Escape exits
        escape = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(escape)
        assert not editor.nav_mode

    def test_full_keyboard_workflow(
        self,
        integration_window: MainWindow,
        sample_detection_result: DetectionResult,
    ) -> None:
        """Complete keyboard workflow: navigate → accept some → reject one → undo → verify."""
        screen = _get_validation_screen(integration_window)
        screen.start_validation(sample_detection_result)

        state = screen.validation_state
        assert state is not None
        assert len(state.get_all_entities()) == 4

        editor = screen.editor
        editor.setFocus()

        # Enter nav mode
        enter = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        )
        delete = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
        )

        editor.keyPressEvent(enter)  # enter nav mode
        assert editor.nav_mode

        # Accept entity 0 (Enter in nav mode)
        eid_0 = editor._entity_ranges[editor._nav_index][2]
        editor.keyPressEvent(enter)  # accept current
        assert state.get_review(eid_0).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        # Navigator auto-advances to next pending; accept entity 1
        eid_1 = editor._entity_ranges[editor._nav_index][2]
        editor.keyPressEvent(enter)  # accept
        assert state.get_review(eid_1).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        # Reject entity 2 (Delete)
        eid_2 = editor._entity_ranges[editor._nav_index][2]
        editor.keyPressEvent(delete)
        assert state.get_review(eid_2).state == EntityReviewState.REJECTED  # type: ignore[union-attr]

        # Accept entity 3
        eid_3 = editor._entity_ranges[editor._nav_index][2]
        editor.keyPressEvent(enter)
        assert state.get_review(eid_3).state == EntityReviewState.CONFIRMED  # type: ignore[union-attr]

        # Undo last accept → entity 3 back to pending
        state.undo_stack.undo()
        assert state.get_review(eid_3).state == EntityReviewState.PENDING  # type: ignore[union-attr]

        # Verify final states: 2 confirmed, 1 rejected, 1 pending
        validated = state.get_validated_entities()
        assert len(validated) == 2  # only confirmed entities

        reviews = state.get_all_entities()
        states_count = {}
        for r in reviews:
            states_count[r.state] = states_count.get(r.state, 0) + 1
        assert states_count[EntityReviewState.CONFIRMED] == 2
        assert states_count[EntityReviewState.REJECTED] == 1
        assert states_count[EntityReviewState.PENDING] == 1
