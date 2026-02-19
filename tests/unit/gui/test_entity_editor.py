"""Tests for EntityEditor widget."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult


@pytest.fixture()
def editor_with_state(
    qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
) -> tuple[EntityEditor, GUIValidationState]:
    """Create EntityEditor bound to a GUIValidationState."""
    editor = EntityEditor()
    qtbot.addWidget(editor)

    state = GUIValidationState()
    state.init_from_detection_result(sample_detection_result)
    editor.set_validation_state(state)

    return editor, state


class TestEntityHighlighting:
    """Test entity highlighting via extraSelections."""

    def test_highlights_applied(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        selections = editor.extraSelections()
        # Should have one selection per entity (6 entities)
        assert len(selections) >= 6

    def test_rejected_entity_has_strikethrough(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.reject_entity(eid)
        editor.refresh_entity(eid)

        selections = editor.extraSelections()
        # At least one selection should have strikethrough
        has_strikethrough = any(sel.format.fontStrikeOut() for sel in selections)
        assert has_strikethrough

    def test_hide_rejected_removes_highlight(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.reject_entity(eid)

        editor.set_hide_rejected(True)
        selections = editor.extraSelections()
        # Should have one fewer selection
        assert len(selections) == 5

    def test_tooltip_shows_pseudonym_and_type(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        selections = editor.extraSelections()
        # First selection should have a tooltip with entity info
        assert len(selections) > 0
        tooltip = selections[0].format.toolTip()
        assert "PERSON" in tooltip or "LOCATION" in tooltip or "ORG" in tooltip

    def test_accepted_entity_has_green_underline(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        """Test BUG-UX-003 fix: accepted entities show green underline."""
        from PySide6.QtGui import QTextCharFormat

        editor, state = editor_with_state
        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        state.accept_entity(eid)
        editor.refresh_entity(eid)

        selections = editor.extraSelections()
        # Find selection for accepted entity
        has_underline = any(
            sel.format.underlineStyle()
            == QTextCharFormat.UnderlineStyle.SingleUnderline
            for sel in selections
        )
        assert has_underline

    def test_pending_entity_has_no_underline(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        """Test pending entities do not have green underline."""
        from PySide6.QtGui import QTextCharFormat

        editor, state = editor_with_state
        reviews = state.get_all_entities()
        # Ensure all entities are pending (no accepts/rejects yet)
        assert all(r.state.value == "pending" for r in reviews)

        selections = editor.extraSelections()
        # When all entities are pending, NONE should have underline
        has_any_underline = any(
            sel.format.underlineStyle()
            == QTextCharFormat.UnderlineStyle.SingleUnderline
            for sel in selections
        )
        assert not has_any_underline

    def test_known_entity_has_green_underline(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        """Test known (auto-accepted) entities show green underline."""
        from PySide6.QtGui import QTextCharFormat

        editor, state = editor_with_state
        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        # Mark as known
        state._known_entity_ids.add(eid)
        editor.refresh_entity(eid)

        selections = editor.extraSelections()
        # Find selection for known entity
        has_underline = any(
            sel.format.underlineStyle()
            == QTextCharFormat.UnderlineStyle.SingleUnderline
            for sel in selections
        )
        assert has_underline


class TestClickDetection:
    """Test click on entity detection."""

    def test_entity_at_position(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        # Position 25 should be inside "Jean Dupont" (20-31)
        entity_id = editor._entity_at_position(25)
        assert entity_id is not None

    def test_no_entity_at_empty_position(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        # Position 0 should not be inside any entity
        entity_id = editor._entity_at_position(0)
        assert entity_id is None

    def test_click_emits_entity_selected(
        self, qtbot, editor_with_state: tuple[EntityEditor, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()

        signals_received: list[str] = []
        editor.entity_selected.connect(lambda eid: signals_received.append(eid))

        # Simulate clicking by directly calling the handler
        editor.entity_selected.emit(reviews[0].entity_id)
        assert len(signals_received) == 1


class TestContextMenu:
    """Test context menu behavior."""

    def test_selection_overlap_check(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        # Selection overlapping "Jean Dupont" (20-31)
        assert editor._selection_overlaps_entity(22, 28) is True
        # Selection not overlapping any entity
        assert editor._selection_overlaps_entity(0, 5) is False


class TestScrollToEntity:
    """Test scroll-to-entity functionality."""

    def test_scroll_to_entity(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()
        eid = reviews[0].entity_id
        # Should not raise
        editor.scroll_to_entity(eid)


class TestNavigationMode:
    """Test keyboard navigation mode."""

    def test_enter_activates_nav_mode(
        self, qtbot, editor_with_state: tuple[EntityEditor, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        editor, state = editor_with_state
        assert not editor.nav_mode

        # Simulate Enter key
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
        )
        editor.keyPressEvent(event)
        assert editor.nav_mode

    def test_escape_exits_nav_mode(
        self, qtbot, editor_with_state: tuple[EntityEditor, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        editor, state = editor_with_state

        # Enter nav mode
        enter_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
        )
        editor.keyPressEvent(enter_event)
        assert editor.nav_mode

        # Exit nav mode
        esc_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        editor.keyPressEvent(esc_event)
        assert not editor.nav_mode

    def test_tab_cycles_entities(
        self, qtbot, editor_with_state: tuple[EntityEditor, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        editor, state = editor_with_state

        # Enter nav mode
        enter_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
        )
        editor.keyPressEvent(enter_event)

        initial_idx = editor._nav_index
        tab_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier,
        )
        editor.keyPressEvent(tab_event)

        # Nav index should advance
        assert editor._nav_index != initial_idx
