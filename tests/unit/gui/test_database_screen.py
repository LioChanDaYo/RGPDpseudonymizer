"""Tests for DatabaseScreen."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.gui.screens.database import DatabaseScreen


@pytest.fixture()
def db_screen(main_window):  # type: ignore[no-untyped-def]
    """Get the database screen from main_window fixture."""
    idx = main_window._screens["database"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, DatabaseScreen)
    return screen


def _make_entity(
    entity_id: str,
    entity_type: str,
    full_name: str,
    pseudonym_full: str,
) -> MagicMock:
    """Create a mock Entity."""
    entity = MagicMock()
    entity.id = entity_id
    entity.entity_type = entity_type
    entity.full_name = full_name
    entity.pseudonym_full = pseudonym_full
    entity.first_seen_timestamp = None
    return entity


class TestEntityTable:
    """Tests for entity table population."""

    def test_populate_entity_table(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        entities = [
            _make_entity("id1", "PERSON", "Jean Dupont", "Leia Organa"),
            _make_entity("id2", "LOCATION", "Paris", "Coruscant"),
            _make_entity("id3", "ORG", "Acme Corp", "Empire"),
        ]
        db_screen._entities = entities
        db_screen._populate_entity_table()

        assert db_screen.entity_table.rowCount() == 3
        assert "3 correspondances" in db_screen.status_label.text()

    def test_search_filters_entities(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        entities = [
            _make_entity("id1", "PERSON", "Jean Dupont", "Leia Organa"),
            _make_entity("id2", "PERSON", "Marie Martin", "Padme Amidala"),
        ]
        db_screen._entities = entities
        db_screen._populate_entity_table()

        # Set search text, then trigger the debounced filter directly
        # (small dataset <200 uses inline path, but debounce timer delays execution)
        db_screen.search_field.setText("Jean")
        db_screen._apply_filters()
        assert db_screen.entity_table.rowCount() == 1

    def test_type_filter(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        entities = [
            _make_entity("id1", "PERSON", "Jean Dupont", "Leia Organa"),
            _make_entity("id2", "LOCATION", "Paris", "Coruscant"),
        ]
        db_screen._entities = entities
        db_screen._populate_entity_table()

        # Filter to PERSON
        person_idx = db_screen.type_filter.findData("PERSON")
        db_screen.type_filter.setCurrentIndex(person_idx)

        assert db_screen.entity_table.rowCount() == 1


class TestCheckboxSelection:
    """Tests for entity selection via checkboxes."""

    def test_checkbox_updates_selection_count(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        entities = [
            _make_entity("id1", "PERSON", "Jean Dupont", "Leia Organa"),
            _make_entity("id2", "PERSON", "Marie Martin", "Padme Amidala"),
        ]
        db_screen._entities = entities
        db_screen._populate_entity_table()

        assert "0 sélectionnées" in db_screen.status_label.text()
        assert not db_screen.delete_button.isEnabled()

        # Check first entity
        from PySide6.QtCore import Qt

        item = db_screen.entity_table.item(0, 0)
        item.setCheckState(Qt.CheckState.Checked)

        assert "1 sélectionnées" in db_screen.status_label.text()
        assert db_screen.delete_button.isEnabled()
        assert "1" in db_screen.delete_button.text()

    def test_delete_disabled_when_nothing_selected(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        assert not db_screen.delete_button.isEnabled()


class TestDeletion:
    """Tests for entity deletion flow."""

    def test_delete_calls_repo(self, db_screen, qtbot, monkeypatch):  # type: ignore[no-untyped-def]
        entities = [
            _make_entity("id1", "PERSON", "Jean Dupont", "Leia Organa"),
        ]
        db_screen._entities = entities
        db_screen._db_path = "/test.db"
        db_screen._passphrase = "test_passphrase"
        db_screen._populate_entity_table()

        # Select the entity
        from PySide6.QtCore import Qt

        item = db_screen.entity_table.item(0, 0)
        item.setCheckState(Qt.CheckState.Checked)

        # Mock the confirm dialog
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.widgets.confirm_dialog.ConfirmDialog.destructive",
            staticmethod(lambda *a, **kw: MagicMock(exec=MagicMock(return_value=True))),
        )

        # Mock database operations at the source module level
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.delete_entity_by_id.return_value = entities[0]
        mock_audit = MagicMock()

        mock_open_db = MagicMock()
        mock_open_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_open_db.return_value.__exit__ = MagicMock(return_value=False)

        # Mock QThreadPool.start to run the worker synchronously
        def run_worker_sync(worker):
            worker.run()

        with (
            patch(
                "gdpr_pseudonymizer.data.database.open_database",
                mock_open_db,
            ),
            patch(
                "gdpr_pseudonymizer.data.repositories.mapping_repository.SQLiteMappingRepository",
                return_value=mock_repo,
            ),
            patch(
                "gdpr_pseudonymizer.data.repositories.audit_repository.AuditRepository",
                return_value=mock_audit,
            ),
            patch(
                "PySide6.QtCore.QThreadPool.start",
                side_effect=run_worker_sync,
            ),
        ):
            db_screen._delete_selected()

        mock_repo.delete_entity_by_id.assert_called_once_with("id1")
        mock_audit.log_operation.assert_called_once()


class TestCsvExport:
    """Tests for CSV export."""

    def test_export_generates_csv(self, db_screen, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
        entities = [
            _make_entity("abcdefgh-1234", "PERSON", "Jean Dupont", "Leia Organa"),
        ]
        db_screen._entities = entities

        output_file = str(tmp_path / "export.csv")
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.screens.database.QFileDialog.getSaveFileName",
            lambda *a, **kw: (output_file, ""),
        )

        # Mock QThreadPool.start to run the worker synchronously
        def run_worker_sync(worker):
            worker.run()

        with patch(
            "PySide6.QtCore.QThreadPool.start",
            side_effect=run_worker_sync,
        ):
            db_screen._export_csv()

        content = Path(output_file).read_text(encoding="utf-8")
        assert "entity_id" in content
        assert "Jean Dupont" in content
        assert "Leia Organa" in content


class TestDatabaseInfo:
    """Tests for database info display."""

    def test_info_label_initially_empty(self, db_screen):  # type: ignore[no-untyped-def]
        assert db_screen.info_label.text() == ""

    def test_export_disabled_without_entities(self, db_screen):  # type: ignore[no-untyped-def]
        assert not db_screen.export_button.isEnabled()

    def test_progress_bar_hidden_initially(self, db_screen):  # type: ignore[no-untyped-def]
        assert not db_screen.progress_bar.isVisible()


class TestPassphraseCacheClearing:
    """TEST-001: Passphrase cache clearing on passphrase errors."""

    def test_passphrase_error_clears_cache(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        """Passphrase error from worker clears cached passphrase."""
        db_screen._db_path = "/test.db"
        db_screen._passphrase = "wrong"
        db_screen._main_window.cached_passphrase = ("/test.db", "wrong")

        # Create a worker with is_passphrase_error flag set
        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        worker = DatabaseWorker("list", "/test.db", "wrong")
        worker.is_passphrase_error = True
        db_screen._current_worker = worker

        # Simulate error handler call
        db_screen._on_db_error("Phrase secrète incorrecte.")

        assert db_screen._main_window.cached_passphrase is None

    def test_non_passphrase_error_keeps_cache(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        """Non-passphrase errors do not clear cached passphrase."""
        db_screen._db_path = "/test.db"
        db_screen._main_window.cached_passphrase = ("/test.db", "correct")

        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        worker = DatabaseWorker("list", "/test.db", "correct")
        # is_passphrase_error remains False (default)
        db_screen._current_worker = worker

        db_screen._on_db_error("La base de données est corrompue ou invalide.")

        # Cache should NOT be cleared
        assert db_screen._main_window.cached_passphrase == ("/test.db", "correct")


class TestSearchThresholdRouting:
    """TEST-002: Background vs inline search routing based on entity count."""

    def test_small_dataset_uses_inline(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        """Datasets <= 200 entities use inline filtering (no worker)."""
        entities = [
            _make_entity(f"id{i}", "PERSON", f"Name {i}", f"Pseudo {i}")
            for i in range(100)
        ]
        db_screen._entities = entities
        db_screen._populate_entity_table()

        with patch.object(db_screen, "_apply_filters_background") as mock_bg:
            db_screen.search_field.setText("Name 5")
            db_screen._apply_filters()

            mock_bg.assert_not_called()
        # Inline filter ran — should show filtered results
        assert db_screen.entity_table.rowCount() < 100

    def test_large_dataset_uses_background(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        """Datasets > 200 entities route through background worker."""
        entities = [
            _make_entity(f"id{i}", "PERSON", f"Name {i}", f"Pseudo {i}")
            for i in range(250)
        ]
        db_screen._entities = entities
        db_screen._populate_entity_table()

        with patch.object(db_screen, "_apply_filters_background") as mock_bg:
            db_screen.search_field.setText("Name 5")
            db_screen._apply_filters()

            mock_bg.assert_called_once_with("Name 5", "")


class TestCancelAndReplace:
    """TEST-003: Cancel-and-replace pattern at the screen level."""

    def test_new_worker_cancels_previous(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        """Starting a new worker cancels and replaces the previous one."""
        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        old_worker = DatabaseWorker("list", "/test.db", "pass")
        # Connect dummy slots so disconnect() in _cancel_current_worker succeeds
        old_worker.signals.finished.connect(lambda r: None)
        old_worker.signals.error.connect(lambda m: None)
        old_worker.signals.progress.connect(lambda p, m: None)
        db_screen._current_worker = old_worker

        # Calling _cancel_current_worker should set the cancelled flag
        db_screen._cancel_current_worker()

        assert old_worker._cancelled.is_set()
        assert db_screen._current_worker is None

    def test_start_worker_replaces_inflight(self, db_screen, qtbot):  # type: ignore[no-untyped-def]
        """_start_worker cancels in-flight worker before starting new one."""
        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        old_worker = DatabaseWorker("search", entities=[], search_text="old")
        # Connect dummy slots so disconnect() in _cancel_current_worker succeeds
        old_worker.signals.finished.connect(lambda r: None)
        old_worker.signals.error.connect(lambda m: None)
        old_worker.signals.progress.connect(lambda p, m: None)
        db_screen._current_worker = old_worker

        new_worker = DatabaseWorker("search", entities=[], search_text="new")

        def run_worker_sync(worker):
            worker.run()

        with patch("PySide6.QtCore.QThreadPool.start", side_effect=run_worker_sync):
            db_screen._start_worker(new_worker)

        assert old_worker._cancelled.is_set()
        assert db_screen._current_worker is new_worker
