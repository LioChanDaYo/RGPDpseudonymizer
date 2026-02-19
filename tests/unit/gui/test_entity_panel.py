"""Tests for EntityPanel widget."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.entity_panel import EntityPanel
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult


@pytest.fixture()
def panel_with_state(
    qtbot, sample_detection_result: DetectionResult  # type: ignore[no-untyped-def]
) -> tuple[EntityPanel, GUIValidationState]:
    """Create EntityPanel bound to a GUIValidationState."""
    panel = EntityPanel()
    qtbot.addWidget(panel)

    state = GUIValidationState()
    state.init_from_detection_result(sample_detection_result)
    panel.set_validation_state(state)

    return panel, state


class TestEntityGrouping:
    """Test entities are grouped by type with section headers."""

    def test_entities_grouped_by_type(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        # List should contain section headers + entity rows
        total_items = panel.list_widget.count()
        # 3 section headers + 6 entities = 9
        assert total_items == 9

    def test_section_headers_present(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        headers = []
        for i in range(panel.list_widget.count()):
            item = panel.list_widget.item(i)
            if item and "──" in item.text():
                headers.append(item.text())
        assert len(headers) == 3  # PERSONNES, LIEUX, ORGANISATIONS


class TestEntityRow:
    """Test entity row display."""

    def test_entity_row_shows_status_and_name(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        # First entity row (index 1, after header)
        item = panel.list_widget.item(1)
        assert item is not None
        text = item.text()
        assert "○" in text  # Pending icon
        assert "Jean Dupont" in text

    def test_entity_row_shows_pseudonym(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        item = panel.list_widget.item(1)
        assert item is not None
        text = item.text()
        assert "→" in text  # Pseudonym arrow


class TestEntityClick:
    """Test click on entity row."""

    def test_click_emits_entity_clicked(
        self, qtbot, panel_with_state: tuple[EntityPanel, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        panel, state = panel_with_state
        signals: list[str] = []
        panel.entity_clicked.connect(lambda eid: signals.append(eid))

        # Click first entity row (index 1)
        item = panel.list_widget.item(1)
        if item:
            panel._on_item_clicked(item)

        assert len(signals) == 1


class TestCheckboxSelection:
    """Test checkbox multi-selection."""

    def test_checkbox_adds_to_checked(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        item = panel.list_widget.item(1)
        if item:
            item.setCheckState(Qt.CheckState.Checked)
            panel._on_item_clicked(item)

        assert len(panel._checked_ids) == 1


class TestBulkActions:
    """Test bulk action operations."""

    def test_bulk_accept_emits_signal(
        self, qtbot, panel_with_state: tuple[EntityPanel, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        panel, state = panel_with_state

        # Check first two entities
        for idx in [1, 2]:
            item = panel.list_widget.item(idx)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
                panel._on_item_clicked(item)

        signals: list[tuple[str, list]] = []
        panel.bulk_action_requested.connect(
            lambda action, ids: signals.append((action, ids))
        )

        panel._on_bulk_accept()
        assert len(signals) == 1
        assert signals[0][0] == "accept"
        assert len(signals[0][1]) == 2

    def test_bulk_reject_emits_signal(
        self, qtbot, panel_with_state: tuple[EntityPanel, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        panel, state = panel_with_state

        item = panel.list_widget.item(1)
        if item:
            item.setCheckState(Qt.CheckState.Checked)
            panel._on_item_clicked(item)

        signals: list[tuple[str, list]] = []
        panel.bulk_action_requested.connect(
            lambda action, ids: signals.append((action, ids))
        )

        panel._on_bulk_reject()
        assert len(signals) == 1
        assert signals[0][0] == "reject"

    def test_accept_all_type(
        self, qtbot, panel_with_state: tuple[EntityPanel, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        panel, state = panel_with_state

        signals: list[tuple[str, list]] = []
        panel.bulk_action_requested.connect(
            lambda action, ids: signals.append((action, ids))
        )

        panel._on_accept_all_type()
        assert len(signals) == 1
        assert signals[0][0].startswith("accept_type:")

    def test_accept_known(
        self, qtbot, panel_with_state: tuple[EntityPanel, GUIValidationState]  # type: ignore[no-untyped-def]
    ) -> None:
        panel, state = panel_with_state

        signals: list[tuple[str, list]] = []
        panel.bulk_action_requested.connect(
            lambda action, ids: signals.append((action, ids))
        )

        panel._on_accept_known()
        assert len(signals) == 1
        assert signals[0][0] == "accept_known"


class TestPendingCounter:
    """Test pending counter updates."""

    def test_pending_counter_initial(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        assert "6" in panel.pending_label.text()

    def test_pending_counter_after_accept(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        reviews = state.get_all_entities()
        state.accept_entity(reviews[0].entity_id)
        panel.update_entity_row(reviews[0].entity_id)
        assert "5" in panel.pending_label.text()

    def test_all_verified_label(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        # Accept all entities
        for review in state.get_all_entities():
            state.accept_entity(review.entity_id)
            panel.update_entity_row(review.entity_id)

        assert "Toutes" in panel.pending_label.text()


class TestKnownEntityBadge:
    """Test 'déjà connu' badge display."""

    def test_known_entity_shows_badge(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        # Mark first entity as known manually (bypassing DB)
        reviews = state.get_all_entities()
        state._known_entity_ids.add(reviews[0].entity_id)
        panel.populate()

        item = panel.list_widget.item(1)
        assert item is not None
        assert "déjà connu" in item.text()


class TestFilter:
    """Test filter field functionality."""

    def test_filter_reduces_visible_entities(
        self, panel_with_state: tuple[EntityPanel, GUIValidationState]
    ) -> None:
        panel, state = panel_with_state
        initial_count = panel.list_widget.count()

        panel.find_field.setText("Jean")
        # Should show only matching entities
        assert panel.list_widget.count() < initial_count
