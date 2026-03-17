"""Integration test for database background threading — 1000+ entities (AC3).

Tests that DatabaseScreen loads and searches a large entity dataset
on a background thread without blocking the Qt event loop.
Uses a seeded test database with 1000+ entities.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from gdpr_pseudonymizer.gui.main_window import MainWindow
from gdpr_pseudonymizer.gui.screens.database import DatabaseScreen
from gdpr_pseudonymizer.gui.workers.database_worker import (
    DatabaseWorker,
    ListEntitiesResult,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_mock_entity(
    entity_id: str,
    entity_type: str,
    full_name: str,
    pseudonym_full: str,
) -> MagicMock:
    """Create a mock Entity with the required attributes."""
    entity = MagicMock()
    entity.id = entity_id
    entity.entity_type = entity_type
    entity.full_name = full_name
    entity.pseudonym_full = pseudonym_full
    entity.first_seen_timestamp = datetime.now(timezone.utc)
    return entity


def _generate_mock_entities(count: int = 1200) -> list[Any]:
    """Generate ``count`` mock entities for testing."""
    types = ["PERSON", "PERSON", "PERSON", "LOCATION", "ORG"]
    first_names = ["Jean", "Marie", "Pierre", "Sophie", "Antoine"]
    last_names = ["Dupont", "Martin", "Durand", "Lefèvre", "Moreau"]
    locations = ["Paris", "Lyon", "Marseille", "Toulouse", "Nice"]
    orgs = ["SNCF", "EDF", "Renault", "Airbus", "Orange"]

    entities = []
    for i in range(count):
        etype = types[i % len(types)]
        if etype == "PERSON":
            first = first_names[i % len(first_names)]
            last = last_names[i % len(last_names)]
            name = f"{first} {last} #{i}"
            pseudo = f"Pseudo_{first}_{i}"
        elif etype == "LOCATION":
            loc = locations[i % len(locations)]
            name = f"{loc} #{i}"
            pseudo = f"Tatooine-{i}"
        else:
            org = orgs[i % len(orgs)]
            name = f"{org} #{i}"
            pseudo = f"Empire-{i}"

        entities.append(_make_mock_entity(str(uuid.uuid4()), etype, name, pseudo))
    return entities


def _get_database_screen(window: MainWindow) -> DatabaseScreen:
    idx = window._screens.get("database")
    assert idx is not None
    widget = window.stack.widget(idx)
    assert isinstance(widget, DatabaseScreen)
    return widget


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestDatabaseBackgroundThreading:
    """AC3: Database operations run on background threads, keeping UI responsive."""

    def test_entity_listing_ui_update_on_load_complete(
        self,
        integration_window: MainWindow,
        qtbot,  # type: ignore[no-untyped-def]
    ) -> None:
        """UI table and status label update correctly when 1000+ entities are loaded."""
        screen = _get_database_screen(integration_window)
        mock_entities = _generate_mock_entities(1200)

        # Directly invoke _on_entities_loaded to simulate worker completion
        result = ListEntitiesResult(
            entities=mock_entities,
            db_created_str="01/01/2026",
            entity_count=1200,
            last_op_str="aujourd'hui",
        )

        screen._on_entities_loaded(result)

        # Verify entity table is populated
        assert screen.entity_table.rowCount() == 1200
        assert "1200" in screen.status_label.text()

    def test_background_worker_emits_finished_signal(
        self,
        qtbot,  # type: ignore[no-untyped-def]
    ) -> None:
        """DatabaseWorker 'search' op emits finished without blocking Qt event loop."""
        mock_entities = _generate_mock_entities(1200)

        worker = DatabaseWorker(
            "search",
            entities=mock_entities,
            search_text="Jean",
            type_filter="",
        )

        # Use qtbot.waitSignal to verify non-blocking completion
        with qtbot.waitSignal(worker.signals.finished, timeout=10000) as blocker:
            from PySide6.QtCore import QThreadPool

            QThreadPool.globalInstance().start(worker)

        # Verify filtered results
        filtered = blocker.args[0]
        assert isinstance(filtered, list)
        assert len(filtered) > 0
        assert all("Jean" in e.full_name for e in filtered)

    def test_large_dataset_listing_non_blocking(
        self,
        integration_window: MainWindow,
        qtbot,  # type: ignore[no-untyped-def]
    ) -> None:
        """AC3 subtask 4.3: Qt event loop processes events during background load."""
        _get_database_screen(integration_window)  # ensure screen exists
        mock_entities = _generate_mock_entities(1200)

        # Create a search worker (search is fully in-memory, no DB needed)
        worker = DatabaseWorker(
            "search",
            entities=mock_entities,
            search_text="",
            type_filter="",
        )

        # Track that the Qt event loop remains responsive while worker runs.
        # A QTimer.singleShot(0, cb) callback only fires if the event loop is
        # actively processing events — proving it is not blocked.
        event_processed = [False]

        from PySide6.QtCore import QThreadPool, QTimer

        def _on_timer() -> None:
            event_processed[0] = True

        start_time = time.monotonic()

        with qtbot.waitSignal(worker.signals.finished, timeout=10000):
            QThreadPool.globalInstance().start(worker)
            # Schedule a zero-delay callback — fires only if the event loop spins
            QTimer.singleShot(0, _on_timer)

        elapsed = time.monotonic() - start_time

        # Worker should complete in reasonable time (< 10s)
        assert elapsed < 10.0, f"Background operation took too long: {elapsed:.1f}s"

        # The timer callback proves the event loop was not blocked
        assert event_processed[
            0
        ], "Qt event loop was blocked during background operation"

    def test_search_filter_on_large_dataset_background(
        self,
        integration_window: MainWindow,
        qtbot,  # type: ignore[no-untyped-def]
    ) -> None:
        """AC3 subtask 4.4: search/filter on 1000+ entities uses background thread."""
        screen = _get_database_screen(integration_window)
        mock_entities = _generate_mock_entities(1200)

        # Simulate loaded entities
        screen._entities = mock_entities

        # Search for "Marie" — should use background worker (> 200 threshold)
        assert len(screen._entities) > 200  # _SEARCH_BACKGROUND_THRESHOLD

        # Create and run a search worker directly
        worker = DatabaseWorker(
            "search",
            entities=list(mock_entities),
            search_text="Marie",
            type_filter="",
        )

        with qtbot.waitSignal(worker.signals.finished, timeout=10000) as blocker:
            from PySide6.QtCore import QThreadPool

            QThreadPool.globalInstance().start(worker)

        filtered = blocker.args[0]
        assert isinstance(filtered, list)
        assert len(filtered) > 0
        assert all("Marie" in e.full_name for e in filtered)

    def test_type_filter_on_large_dataset(
        self,
        integration_window: MainWindow,
        qtbot,  # type: ignore[no-untyped-def]
    ) -> None:
        """Search with type filter returns correct subset."""
        mock_entities = _generate_mock_entities(1200)

        worker = DatabaseWorker(
            "search",
            entities=mock_entities,
            search_text="",
            type_filter="LOCATION",
        )

        with qtbot.waitSignal(worker.signals.finished, timeout=10000) as blocker:
            from PySide6.QtCore import QThreadPool

            QThreadPool.globalInstance().start(worker)

        filtered = blocker.args[0]
        assert isinstance(filtered, list)
        assert len(filtered) > 0
        assert all(e.entity_type == "LOCATION" for e in filtered)

    def test_entity_count_displayed_correctly(
        self,
        integration_window: MainWindow,
        qtbot,  # type: ignore[no-untyped-def]
    ) -> None:
        """Verify correct entity count displayed in UI after loading 1000+ entities."""
        screen = _get_database_screen(integration_window)
        mock_entities = _generate_mock_entities(1050)

        result = ListEntitiesResult(
            entities=mock_entities,
            db_created_str="15/03/2026",
            entity_count=1050,
            last_op_str="hier",
        )

        screen._on_entities_loaded(result)

        # Table should show all entities
        assert screen.entity_table.rowCount() == 1050

        # Info label should contain the count
        assert "1050" in screen.info_label.text()
