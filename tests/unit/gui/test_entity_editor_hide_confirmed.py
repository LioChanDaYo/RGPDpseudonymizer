"""Tests for hide-confirmed toggle in EntityEditor.

Story 7.1 — Tasks 8.5-8.6: hide-confirmed toggle behavior.
"""

from __future__ import annotations

import pytest

from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.validation.models import EntityReviewState


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


class TestHideConfirmedToggle:
    """Test 8.5: hide-confirmed toggle hides CONFIRMED entities."""

    def test_confirmed_entities_hidden_when_toggle_on(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()

        # Count initial highlights
        initial_count = len(editor.extraSelections())
        assert initial_count >= 6

        # Accept first entity (single entity, no grouping in sample data)
        eid = reviews[0].entity_id
        state.accept_entity(eid)
        editor.refresh_entity(eid)

        # Enable hide-confirmed
        editor.set_hide_confirmed(True)
        hidden_count = len(editor.extraSelections())

        # Should have fewer highlights (confirmed entity hidden)
        assert hidden_count < initial_count

    def test_pending_entities_visible_when_toggle_on(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()

        # Accept first entity
        eid = reviews[0].entity_id
        state.accept_entity(eid)
        editor.refresh_entity(eid)

        # Enable hide-confirmed
        editor.set_hide_confirmed(True)

        # Remaining entities (PENDING) should still be visible
        # 6 entities total, 1 accepted (hidden) = 5 visible
        visible_count = len(editor.extraSelections())
        assert visible_count >= 5

    def test_rejected_entities_visible_when_toggle_on(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()

        # Accept one, reject another
        state.accept_entity(reviews[0].entity_id)
        state.reject_entity(reviews[1].entity_id)
        editor.refresh_entity(reviews[0].entity_id)
        editor.refresh_entity(reviews[1].entity_id)

        # Enable hide-confirmed only
        editor.set_hide_confirmed(True)

        selections = editor.extraSelections()
        # Rejected entity should still be visible (has strikethrough)
        has_strikethrough = any(sel.format.fontStrikeOut() for sel in selections)
        assert has_strikethrough

    def test_hide_confirmed_off_shows_all(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()

        state.accept_entity(reviews[0].entity_id)
        editor.refresh_entity(reviews[0].entity_id)

        # Toggle on then off
        editor.set_hide_confirmed(True)
        editor.set_hide_confirmed(False)

        # All entities should be visible again
        visible_count = len(editor.extraSelections())
        assert visible_count >= 6


class TestHideConfirmedKnownEntities:
    """Test 8.6: known (auto-accepted) entities are also hidden."""

    def test_known_entities_hidden_when_toggle_on(
        self, editor_with_state: tuple[EntityEditor, GUIValidationState]
    ) -> None:
        editor, state = editor_with_state
        reviews = state.get_all_entities()

        # Simulate a known entity by adding to known set and confirming
        eid = reviews[0].entity_id
        state._known_entity_ids.add(eid)
        reviews[0].state = EntityReviewState.CONFIRMED
        editor.refresh_entity(eid)

        initial_count_before_hide = len(editor.extraSelections())

        # Enable hide-confirmed
        editor.set_hide_confirmed(True)
        hidden_count = len(editor.extraSelections())

        # Known entity should be hidden
        assert hidden_count < initial_count_before_hide
