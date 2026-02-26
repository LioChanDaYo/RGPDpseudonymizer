"""Tests for DatabaseWorker — background operations for the database screen."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from gdpr_pseudonymizer.gui.workers.database_worker import (
    DatabaseWorker,
    ListEntitiesResult,
)

# Patch targets: since DatabaseWorker uses lazy imports inside methods,
# we patch the source modules directly.
_OPEN_DB = "gdpr_pseudonymizer.data.database.open_database"
_MAPPING_REPO = (
    "gdpr_pseudonymizer.data.repositories.mapping_repository" ".SQLiteMappingRepository"
)
_AUDIT_REPO = "gdpr_pseudonymizer.data.repositories.audit_repository.AuditRepository"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(
    entity_id: str = "abc-123",
    entity_type: str = "PERSON",
    full_name: str = "Jean Dupont",
    pseudonym_full: str = "Luke Skywalker",
) -> MagicMock:
    """Create a mock Entity for testing."""
    e = MagicMock()
    e.id = entity_id
    e.entity_type = entity_type
    e.full_name = full_name
    e.pseudonym_full = pseudonym_full
    e.first_seen_timestamp = datetime(2026, 1, 15, tzinfo=timezone.utc)
    return e


def _capture_signals(worker: DatabaseWorker) -> dict[str, list]:
    """Attach signal capture lists to a worker."""
    captured: dict[str, list] = {
        "finished": [],
        "error": [],
        "progress": [],
    }
    worker.signals.finished.connect(lambda r: captured["finished"].append(r))
    worker.signals.error.connect(lambda msg: captured["error"].append(msg))
    worker.signals.progress.connect(lambda p, m: captured["progress"].append((p, m)))
    return captured


# ===========================================================================
# LIST ENTITIES
# ===========================================================================


class TestDatabaseWorkerList:
    """Test the 'list' operation."""

    @patch("gdpr_pseudonymizer.gui.workers.database_worker.Path")
    @patch(_AUDIT_REPO)
    @patch(_MAPPING_REPO)
    @patch(_OPEN_DB)
    def test_list_entities_success(
        self, mock_open_db, mock_repo_cls, mock_audit_cls, mock_path, qtbot
    ):
        """Successful load returns ListEntitiesResult via finished signal."""
        entities = [_make_entity(), _make_entity("def-456", full_name="Marie Martin")]
        mock_repo = MagicMock()
        mock_repo.find_all.return_value = entities
        mock_repo_cls.return_value = mock_repo

        mock_audit = MagicMock()
        mock_op = MagicMock()
        mock_op.timestamp = datetime(2026, 2, 20, tzinfo=timezone.utc)
        mock_audit.find_operations.return_value = [mock_op]
        mock_audit_cls.return_value = mock_audit

        mock_session = MagicMock()
        mock_open_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_open_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_stat = MagicMock()
        mock_stat.st_ctime = datetime(2026, 1, 1).timestamp()
        mock_path.return_value.stat.return_value = mock_stat

        worker = DatabaseWorker("list", "/fake/db.db", "passphrase123!")
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"]) == 1
        result = captured["finished"][0]
        assert isinstance(result, ListEntitiesResult)
        assert result.entity_count == 2
        assert len(result.entities) == 2
        assert result.db_created_str  # non-empty date string
        assert len(captured["error"]) == 0
        assert len(captured["progress"]) >= 2

    @patch(_OPEN_DB, side_effect=ValueError("Incorrect passphrase"))
    def test_list_entities_passphrase_error(self, mock_open_db, qtbot):
        """ValueError from open_database emits passphrase error."""
        worker = DatabaseWorker("list", "/fake/db.db", "wrong")
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["error"]) == 1
        assert "secrète" in captured["error"][0].lower()
        assert len(captured["finished"]) == 0

    def test_list_entities_corrupted_db(self, qtbot):
        """CorruptedDatabaseError emits corruption message."""
        from gdpr_pseudonymizer.exceptions import CorruptedDatabaseError

        with patch(_OPEN_DB, side_effect=CorruptedDatabaseError("metadata missing")):
            worker = DatabaseWorker("list", "/fake/db.db", "pass")
            captured = _capture_signals(worker)
            worker.run()

        assert len(captured["error"]) == 1
        assert "corrompue" in captured["error"][0].lower()

    def test_list_entities_encryption_error(self, qtbot):
        """EncryptionError emits decryption error message."""
        from gdpr_pseudonymizer.exceptions import EncryptionError

        with patch(_OPEN_DB, side_effect=EncryptionError("decrypt failed")):
            worker = DatabaseWorker("list", "/fake/db.db", "pass")
            captured = _capture_signals(worker)
            worker.run()

        assert len(captured["error"]) == 1
        assert "déchiffrement" in captured["error"][0].lower()

    def test_list_entities_database_error(self, qtbot):
        """DatabaseError emits generic DB error message."""
        from gdpr_pseudonymizer.exceptions import DatabaseError

        with patch(_OPEN_DB, side_effect=DatabaseError("connection lost")):
            worker = DatabaseWorker("list", "/fake/db.db", "pass")
            captured = _capture_signals(worker)
            worker.run()

        assert len(captured["error"]) == 1
        assert "base de données" in captured["error"][0].lower()

    @patch(_OPEN_DB, side_effect=OSError("file locked"))
    def test_list_entities_os_error(self, mock_open_db, qtbot):
        """OSError emits file access error message."""
        worker = DatabaseWorker("list", "/fake/db.db", "pass")
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["error"]) == 1
        assert "fichier" in captured["error"][0].lower()


# ===========================================================================
# SEARCH ENTITIES
# ===========================================================================


class TestDatabaseWorkerSearch:
    """Test the 'search' operation."""

    def test_search_by_name(self, qtbot):
        """Search filters entities by full_name substring."""
        entities = [
            _make_entity("1", full_name="Jean Dupont", pseudonym_full="Luke"),
            _make_entity("2", full_name="Marie Martin", pseudonym_full="Leia"),
            _make_entity("3", full_name="Pierre Durand", pseudonym_full="Han"),
        ]
        worker = DatabaseWorker(
            "search", entities=entities, search_text="jean", type_filter=""
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"]) == 1
        assert len(captured["finished"][0]) == 1
        assert captured["finished"][0][0].full_name == "Jean Dupont"

    def test_search_by_pseudonym(self, qtbot):
        """Search matches against pseudonym_full as well."""
        entities = [
            _make_entity("1", full_name="Jean Dupont", pseudonym_full="Luke Skywalker"),
            _make_entity("2", full_name="Marie Martin", pseudonym_full="Leia Organa"),
        ]
        worker = DatabaseWorker(
            "search", entities=entities, search_text="organa", type_filter=""
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"][0]) == 1
        assert captured["finished"][0][0].full_name == "Marie Martin"

    def test_search_by_type(self, qtbot):
        """Type filter restricts results to matching entity_type."""
        entities = [
            _make_entity("1", entity_type="PERSON"),
            _make_entity("2", entity_type="LOCATION"),
            _make_entity("3", entity_type="PERSON"),
        ]
        worker = DatabaseWorker(
            "search", entities=entities, search_text="", type_filter="PERSON"
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"][0]) == 2

    def test_search_combined(self, qtbot):
        """Type + text filter combined."""
        entities = [
            _make_entity(
                "1",
                entity_type="PERSON",
                full_name="Jean Dupont",
                pseudonym_full="Luke",
            ),
            _make_entity(
                "2",
                entity_type="PERSON",
                full_name="Marie Martin",
                pseudonym_full="Leia",
            ),
            _make_entity(
                "3",
                entity_type="LOCATION",
                full_name="Jean-de-Luz",
                pseudonym_full="Tatooine",
            ),
        ]
        worker = DatabaseWorker(
            "search", entities=entities, search_text="jean", type_filter="PERSON"
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"][0]) == 1
        assert captured["finished"][0][0].full_name == "Jean Dupont"

    def test_search_empty_returns_all(self, qtbot):
        """No filters returns all entities."""
        entities = [_make_entity("1"), _make_entity("2")]
        worker = DatabaseWorker(
            "search", entities=entities, search_text="", type_filter=""
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"][0]) == 2


# ===========================================================================
# DELETE ENTITIES
# ===========================================================================


class TestDatabaseWorkerDelete:
    """Test the 'delete' operation."""

    @patch(_AUDIT_REPO)
    @patch(_MAPPING_REPO)
    @patch(_OPEN_DB)
    def test_delete_success(self, mock_open_db, mock_repo_cls, mock_audit_cls, qtbot):
        """Deletes entities and logs ERASURE audit operation."""
        mock_repo = MagicMock()
        mock_repo.delete_entity_by_id.return_value = _make_entity()
        mock_repo_cls.return_value = mock_repo

        mock_audit = MagicMock()
        mock_audit_cls.return_value = mock_audit

        mock_session = MagicMock()
        mock_open_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_open_db.return_value.__exit__ = MagicMock(return_value=False)

        worker = DatabaseWorker(
            "delete",
            "/fake/db.db",
            "pass123456789!",
            entity_ids=["id-1", "id-2"],
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"]) == 1
        assert captured["finished"][0] == 2
        assert mock_repo.delete_entity_by_id.call_count == 2
        assert mock_audit.log_operation.call_count == 1
        logged_op = mock_audit.log_operation.call_args[0][0]
        assert logged_op.operation_type == "ERASURE"
        assert logged_op.entity_count == 2

    @patch(_OPEN_DB, side_effect=ValueError("bad passphrase"))
    def test_delete_passphrase_error(self, mock_open_db, qtbot):
        """ValueError during delete emits passphrase error."""
        worker = DatabaseWorker("delete", "/fake/db.db", "wrong", entity_ids=["id-1"])
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["error"]) == 1
        assert "secrète" in captured["error"][0].lower()

    def test_delete_empty_ids(self, qtbot):
        """Empty entity_ids list emits finished(0) immediately."""
        worker = DatabaseWorker("delete", "/fake/db.db", "pass", entity_ids=[])
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"]) == 1
        assert captured["finished"][0] == 0


# ===========================================================================
# EXPORT CSV
# ===========================================================================


class TestDatabaseWorkerExport:
    """Test the 'export' operation."""

    def test_export_success(self, qtbot, tmp_path):
        """CSV export writes correct content."""
        entities = [
            _make_entity("aaa-111", full_name="Jean D", pseudonym_full="Luke S"),
            _make_entity("bbb-222", full_name="Marie M", pseudonym_full="Leia O"),
        ]
        filepath = str(tmp_path / "export.csv")

        worker = DatabaseWorker("export", filepath=filepath, entities=entities)
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"]) == 1
        assert captured["finished"][0] is True
        assert len(captured["error"]) == 0

        # Verify CSV content
        content = (tmp_path / "export.csv").read_text(encoding="utf-8")
        assert "entity_id" in content  # header
        assert "Jean D" in content
        assert "Marie M" in content

    def test_export_os_error(self, qtbot):
        """OSError during CSV write emits error signal."""
        entities = [_make_entity()]

        worker = DatabaseWorker(
            "export", filepath="/nonexistent/dir/export.csv", entities=entities
        )
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["error"]) == 1
        assert "csv" in captured["error"][0].lower()


# ===========================================================================
# SIGNAL ORDER & PROGRESS
# ===========================================================================


class TestDatabaseWorkerSignals:
    """Test signal emission order and progress."""

    @patch("gdpr_pseudonymizer.gui.workers.database_worker.Path")
    @patch(_AUDIT_REPO)
    @patch(_MAPPING_REPO)
    @patch(_OPEN_DB)
    def test_list_progress_before_finished(
        self, mock_open_db, mock_repo_cls, mock_audit_cls, mock_path, qtbot
    ):
        """Progress signals are emitted before finished."""
        mock_repo = MagicMock()
        mock_repo.find_all.return_value = []
        mock_repo_cls.return_value = mock_repo

        mock_audit = MagicMock()
        mock_audit.find_operations.return_value = []
        mock_audit_cls.return_value = mock_audit

        mock_session = MagicMock()
        mock_open_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_open_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_stat = MagicMock()
        mock_stat.st_ctime = datetime(2026, 1, 1).timestamp()
        mock_path.return_value.stat.return_value = mock_stat

        worker = DatabaseWorker("list", "/fake/db.db", "pass")

        signal_order: list[str] = []
        worker.signals.progress.connect(lambda p, m: signal_order.append("progress"))
        worker.signals.finished.connect(lambda r: signal_order.append("finished"))
        worker.signals.error.connect(lambda m: signal_order.append("error"))

        worker.run()

        assert "finished" in signal_order
        finished_idx = signal_order.index("finished")
        for i, s in enumerate(signal_order):
            if s == "progress":
                assert i < finished_idx

    @patch(_OPEN_DB, side_effect=ValueError("bad"))
    def test_error_progress_before_error(self, mock_open_db, qtbot):
        """On error path, progress signals come before error signal."""
        worker = DatabaseWorker("list", "/fake/db.db", "wrong")

        signal_order: list[str] = []
        worker.signals.progress.connect(lambda p, m: signal_order.append("progress"))
        worker.signals.error.connect(lambda m: signal_order.append("error"))

        worker.run()

        assert "error" in signal_order
        if "progress" in signal_order:
            error_idx = signal_order.index("error")
            for i, s in enumerate(signal_order):
                if s == "progress":
                    assert i < error_idx


# ===========================================================================
# CANCELLATION
# ===========================================================================


class TestDatabaseWorkerCancellation:
    """Test cancellation via threading.Event."""

    def test_cancel_before_run(self, qtbot):
        """Cancelling before run() emits no signals."""
        worker = DatabaseWorker("list", "/fake/db.db", "pass")
        captured = _capture_signals(worker)

        worker.cancel()
        worker.run()

        assert len(captured["finished"]) == 0
        assert len(captured["error"]) == 0

    @patch(_OPEN_DB)
    def test_cancel_during_list(self, mock_open_db, qtbot):
        """Cancelling during list op prevents finished/error emission."""
        # Worker variable needs to be accessible in side_effect
        worker_ref: list[DatabaseWorker] = []

        def side_effect_cancel(path, passphrase):
            worker_ref[0].cancel()
            return MagicMock(
                __enter__=MagicMock(return_value=MagicMock()),
                __exit__=MagicMock(return_value=False),
            )

        mock_open_db.side_effect = side_effect_cancel

        worker = DatabaseWorker("list", "/fake/db.db", "pass")
        worker_ref.append(worker)
        captured = _capture_signals(worker)
        worker.run()

        assert len(captured["finished"]) == 0
        assert len(captured["error"]) == 0

    def test_cancel_search(self, qtbot):
        """Cancelling during search prevents result emission."""
        entities = [_make_entity(str(i)) for i in range(100)]

        worker = DatabaseWorker(
            "search", entities=entities, search_text="test", type_filter=""
        )
        captured = _capture_signals(worker)

        worker.cancel()
        worker.run()

        assert len(captured["finished"]) == 0
        assert len(captured["error"]) == 0

    def test_cancel_export(self, qtbot, tmp_path):
        """Cancelling export prevents finished emission."""
        worker = DatabaseWorker(
            "export",
            filepath=str(tmp_path / "cancel.csv"),
            entities=[],
        )
        captured = _capture_signals(worker)

        worker.cancel()
        worker.run()

        assert len(captured["finished"]) == 0
        assert len(captured["error"]) == 0
