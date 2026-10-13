"""Unit tests for database initialization and session management."""

from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
import stat
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from gdpr_pseudonymizer.data.database import (
    init_database,
    open_database,
)
from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.data.models import Base, Metadata
from gdpr_pseudonymizer.exceptions import CorruptedDatabaseError

# Story 10.5: invented passphrases for the two competing initializations.
PASS_A = "zorbalia_pass_A_123!"
PASS_B = "quentrix_pass_B_456!"

# The four metadata keys a new database holds (schema_version "1.0.0").
# Story 10.7 changes them here, in one place, if its rule needs to.
WINNER_METADATA_KEYS = {
    "schema_version",
    "encryption_salt",
    "kdf_iterations",
    "passphrase_canary",
}


def _assert_winner_db(db_path: Path, winner_pass: str, loser_pass: str) -> None:
    """Assert the winner's database is intact (Story 10.5, AC2).

    It exists, opens with the winner's passphrase, holds exactly the four
    metadata keys (schema_version "1.0.0", kdf_iterations "100000"), and
    rejects the loser's passphrase. Every failure is an AssertionError, so a
    strict xfail with raises=AssertionError only accepts a real assertion.
    """
    assert db_path.exists(), f"no database file at {db_path}"
    try:
        with open_database(str(db_path), winner_pass) as db_session:
            values = {
                row.key: row.value for row in db_session.session.query(Metadata).all()
            }
    except Exception as exc:
        raise AssertionError(
            f"the database does not open with the winner's passphrase: {exc!r}"
        ) from exc
    assert set(values) == WINNER_METADATA_KEYS, sorted(values)
    assert values["schema_version"] == "1.0.0", values["schema_version"]
    assert values["kdf_iterations"] == "100000", values["kdf_iterations"]
    try:
        loser_session = open_database(str(db_path), loser_pass)
    except ValueError as exc:
        assert "Incorrect passphrase" in str(exc), repr(exc)
    except Exception as exc:
        raise AssertionError(
            f"the loser's passphrase raised {exc!r}, not 'Incorrect passphrase'"
        ) from exc
    else:
        loser_session.close()
        raise AssertionError("the loser's passphrase opened the winner's database")


def _run_init(db_path: Path, passphrase: str) -> BaseException | None:
    """Call init_database and return what it raised (None on success)."""
    try:
        init_database(str(db_path), passphrase)
    except BaseException as exc:
        return exc
    return None


def _file_state(db_path: Path) -> tuple[str, int, list[str]]:
    """sha256, st_mtime_ns and the directory listing, to prove nothing changed."""
    digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
    return digest, db_path.stat().st_mtime_ns, sorted(os.listdir(db_path.parent))


class TestDatabaseInitialization:
    """Test suite for init_database() function."""

    def test_init_database_creates_all_tables(self, tmp_path: Path) -> None:
        """Test database initialization creates entities, operations, and metadata tables."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Verify database file created
        assert db_path.exists()

        # Open database and verify tables exist
        with open_database(str(db_path), passphrase) as db_session:
            # Query table names from SQLite
            result = db_session.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in result]

            assert "entities" in tables
            assert "operations" in tables
            assert "metadata" in tables

    def test_init_database_metadata_keys_initialized(self, tmp_path: Path) -> None:
        """Test metadata table contains all required keys after initialization."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            metadata = db_session.session.query(Metadata).order_by(Metadata.key).all()
            keys = {m.key for m in metadata}

            # Verify all required keys present
            assert "schema_version" in keys
            assert "encryption_salt" in keys
            assert "kdf_iterations" in keys
            assert "passphrase_canary" in keys

            # Verify values
            schema_version = next(m for m in metadata if m.key == "schema_version")
            assert schema_version.value == "1.0.0"

            kdf_iterations = next(m for m in metadata if m.key == "kdf_iterations")
            assert int(kdf_iterations.value) == 100000

    def test_init_database_weak_passphrase_rejected(self, tmp_path: Path) -> None:
        """Test weak passphrase rejected during initialization."""
        db_path = tmp_path / "test.db"
        weak_passphrase = "short"  # Less than 12 characters

        with pytest.raises(ValueError, match="Invalid passphrase"):
            init_database(str(db_path), weak_passphrase)

        # Verify no database file created
        assert not db_path.exists()

    def test_init_database_wal_mode_enabled(self, tmp_path: Path) -> None:
        """Test WAL mode enabled correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            result = db_session.session.execute(text("PRAGMA journal_mode"))
            journal_mode = result.scalar()
            assert journal_mode.lower() == "wal"

    def test_init_database_foreign_keys_enabled(self, tmp_path: Path) -> None:
        """Test foreign key constraints enabled."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            result = db_session.session.execute(text("PRAGMA foreign_keys"))
            foreign_keys = result.scalar()
            assert foreign_keys == 1  # 1 = enabled

    def test_init_database_duplicate_initialization_fails(self, tmp_path: Path) -> None:
        """Test duplicate initialization raises error."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        # First initialization succeeds
        init_database(str(db_path), passphrase)

        # Second initialization should fail
        with pytest.raises(ValueError, match="Database already exists"):
            init_database(str(db_path), passphrase)

    def test_init_database_invalid_path_handling(self) -> None:
        """Test initialization with invalid path raises appropriate error."""
        invalid_path = "/invalid/nonexistent/path/test.db"
        passphrase = "test_passphrase_123!"

        # Should raise exception (exact type depends on OS)
        with pytest.raises(Exception):
            init_database(invalid_path, passphrase)

    def test_init_database_indexes_created(self, tmp_path: Path) -> None:
        """Test database indexes are created for query optimization."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            # Query indexes from SQLite
            result = db_session.session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name"
                )
            )
            indexes = [row[0] for row in result]

            # Verify entity table indexes
            assert "idx_entities_full_name" in indexes
            assert "idx_entities_type" in indexes
            assert "idx_entities_first_name" in indexes
            assert "idx_entities_last_name" in indexes
            assert "idx_entities_ambiguous" in indexes

            # Verify operations table indexes
            assert "idx_operations_timestamp" in indexes
            assert "idx_operations_type" in indexes

    def test_init_database_twice_same_path_keeps_existing_db(
        self, tmp_path: Path
    ) -> None:
        """Calling init_database twice on one path leaves the first DB usable."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)
        with pytest.raises(ValueError, match="Database already exists"):
            init_database(str(db_path), passphrase)

        # Existing DB survives the rejected second call, indexes intact
        with open_database(str(db_path), passphrase) as db_session:
            result = db_session.session.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND name LIKE 'idx_%'"
                )
            )
            assert len({row[0] for row in result}) == 7

    # Story 10.5 (AC1, AC2): the PR #83 test
    # test_init_database_index_creation_idempotent stood here. It patched Path
    # in database.py to replay an initialization on an existing database, and
    # that mock also made the failure cleanup's exists() return False, so it
    # hid the very delete of the other call's database that 10.5 removes. T1
    # below replaces it with a real competitor between the existence check and
    # the create. The #83 "CREATE INDEX IF NOT EXISTS" statements stay in
    # init_database.
    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            "Story 10.5: reproduces the loser deleting the winner's database "
            "(POSIX) or raising PermissionError (Windows) on the unfixed "
            "init_database; fixed in Task 2"
        ),
    )
    def test_init_database_competitor_between_check_and_create(
        self, tmp_path: Path
    ) -> None:
        """T1: a competitor creates the database between the check and the create."""
        db_path = tmp_path / "mappings.db"
        real_generate_salt = EncryptionService.generate_salt
        competitor_ran = False

        def competitor_then_salt() -> bytes:
            # Runs after the outer call passed its existence check.
            nonlocal competitor_ran
            if not competitor_ran:
                competitor_ran = True
                init_database(str(db_path), PASS_A)
            return real_generate_salt()

        with patch.object(
            EncryptionService, "generate_salt", side_effect=competitor_then_salt
        ):
            outcome = _run_init(db_path, PASS_B)

        assert competitor_ran
        assert isinstance(outcome, ValueError), repr(outcome)
        assert str(outcome).startswith("Database already exists"), str(outcome)
        assert isinstance(outcome.__cause__, FileExistsError), repr(outcome.__cause__)
        _assert_winner_db(db_path, PASS_A, PASS_B)

    def test_init_database_existing_file_untouched(self, tmp_path: Path) -> None:
        """T2: an existing database, or a 0-byte file, is never touched."""
        made = tmp_path / "made" / "mappings.db"
        made.parent.mkdir()
        init_database(str(made), PASS_A)
        empty = tmp_path / "empty" / "mappings.db"
        empty.parent.mkdir()
        empty.write_bytes(b"")

        for db_path in (made, empty):
            before = _file_state(db_path)
            outcome = _run_init(db_path, PASS_B)

            assert isinstance(outcome, ValueError), repr(outcome)
            assert str(outcome).startswith("Database already exists"), str(outcome)
            assert _file_state(db_path) == before

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            "Story 10.5: reproduces a late failure leaving -wal/-shm (POSIX) or "
            "the database plus a PermissionError (Windows) on the unfixed "
            "init_database; fixed in Task 2"
        ),
    )
    def test_init_database_late_failure_leaves_nothing(self, tmp_path: Path) -> None:
        """T3: a failure at the metadata step leaves no file behind."""
        db_path = tmp_path / "mappings.db"

        with patch.object(
            EncryptionService,
            "encrypt_canary",
            side_effect=RuntimeError("injected canary failure"),
        ):
            outcome = _run_init(db_path, PASS_A)

        assert type(outcome) is Exception, repr(outcome)
        assert str(outcome).startswith("Database initialization failed"), str(outcome)
        assert sorted(os.listdir(tmp_path)) == []

    def test_init_database_schema_failure_leaves_nothing(self, tmp_path: Path) -> None:
        """T4: a failure at the schema step leaves no file behind."""
        db_path = tmp_path / "mappings.db"

        with patch.object(
            Base.metadata,
            "create_all",
            side_effect=RuntimeError("injected schema failure"),
        ):
            outcome = _run_init(db_path, PASS_A)

        assert type(outcome) is Exception, repr(outcome)
        assert str(outcome).startswith("Database initialization failed"), str(outcome)
        assert sorted(os.listdir(tmp_path)) == []

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            "Story 10.5: reproduces a Ctrl+C leaving a partial database on the "
            "unfixed init_database; fixed in Task 2"
        ),
    )
    def test_init_database_interrupt_cleans_up(self, tmp_path: Path) -> None:
        """T5: a KeyboardInterrupt is re-raised unwrapped and leaves no file."""
        db_path = tmp_path / "mappings.db"

        with patch.object(
            EncryptionService, "encrypt_canary", side_effect=KeyboardInterrupt
        ):
            outcome = _run_init(db_path, PASS_A)

        assert type(outcome) is KeyboardInterrupt, repr(outcome)
        assert sorted(os.listdir(tmp_path)) == []

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows: the held descriptor stops the file being replaced",
    )
    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            "Story 10.5: reproduces the cleanup deleting a file that replaced "
            "the call's own on the unfixed init_database; fixed in Task 2"
        ),
    )
    def test_init_database_cleanup_spares_replaced_file(self, tmp_path: Path) -> None:
        """T6: the cleanup never deletes a file that replaced the call's own."""
        db_path = tmp_path / "mappings.db"

        def replace_then_fail(*args: object, **kwargs: object) -> None:
            if db_path.exists():
                db_path.unlink()
            db_path.write_bytes(b"other")
            raise RuntimeError("injected engine failure")

        with patch(
            "gdpr_pseudonymizer.data.database.create_engine",
            side_effect=replace_then_fail,
        ):
            outcome = _run_init(db_path, PASS_A)

        assert type(outcome) is Exception, repr(outcome)
        assert db_path.exists(), "the replacement file was deleted"
        assert db_path.read_bytes() == b"other"

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            "Story 10.5: reproduces a cleanup error masking the original error "
            "(or no cleanup-failure log) on the unfixed init_database; fixed in "
            "Task 2"
        ),
    )
    def test_init_database_cleanup_error_never_masks_original(
        self, tmp_path: Path
    ) -> None:
        """T7: a failing delete is logged once and never replaces the original."""
        db_path = tmp_path / "mappings.db"

        with (
            patch.object(
                EncryptionService,
                "encrypt_canary",
                side_effect=RuntimeError("injected canary failure"),
            ),
            patch("os.unlink", side_effect=PermissionError("injected unlink failure")),
            patch(
                "gdpr_pseudonymizer.data.database.logger", create=True
            ) as mock_logger,
        ):
            outcome = _run_init(db_path, PASS_A)

        assert type(outcome) is Exception, repr(outcome)
        assert "injected canary failure" in str(outcome), str(outcome)
        warnings = mock_logger.warning.call_args_list
        assert len(warnings) == 1, warnings
        args, kwargs = warnings[0]
        assert args == ("database_init_cleanup_failed",), args
        assert kwargs.get("step") == "delete", kwargs
        assert kwargs.get("error_type") == "PermissionError", kwargs
        assert not {"path", "db_path", "passphrase"} & set(kwargs), kwargs
        for value in kwargs.values():
            assert str(db_path) not in str(value), kwargs
            assert PASS_A not in str(value), kwargs

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits only")
    def test_init_database_file_mode_matches_sqlite(self, tmp_path: Path) -> None:
        """T8: a new database has the mode SQLite gives a file it creates."""
        db_path = tmp_path / "mappings.db"
        init_database(str(db_path), PASS_A)

        reference = tmp_path / "reference.db"
        connection = sqlite3.connect(str(reference))
        try:
            connection.execute("CREATE TABLE reference_table (value INTEGER)")
            connection.commit()
        finally:
            connection.close()

        assert stat.S_IMODE(db_path.stat().st_mode) == stat.S_IMODE(
            reference.stat().st_mode
        )

    def test_init_database_canary_encrypted_correctly(self, tmp_path: Path) -> None:
        """Test passphrase canary is encrypted and stored correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            canary_record = (
                db_session.session.query(Metadata)
                .filter_by(key="passphrase_canary")
                .first()
            )

            assert canary_record is not None
            assert EncryptionService.CANARY_VALUE not in canary_record.value

            # Verify can decrypt with encryption service
            salt_record = (
                db_session.session.query(Metadata)
                .filter_by(key="encryption_salt")
                .first()
            )
            salt = base64.b64decode(salt_record.value.encode("ascii"))
            service = EncryptionService(passphrase, salt)

            decrypted = service.decrypt(canary_record.value)
            assert decrypted == EncryptionService.CANARY_VALUE


class TestDatabaseSessionManagement:
    """Test suite for open_database() and DatabaseSession."""

    def test_open_database_with_correct_passphrase(self, tmp_path: Path) -> None:
        """Test opening database with correct passphrase succeeds."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Should open successfully
        db_session = open_database(str(db_path), passphrase)
        assert db_session is not None
        assert db_session.session is not None
        assert db_session.encryption is not None

        db_session.close()

    def test_open_database_with_incorrect_passphrase(self, tmp_path: Path) -> None:
        """Test opening database with incorrect passphrase raises ValueError."""
        db_path = tmp_path / "test.db"
        correct_passphrase = "correct_passphrase_123!"
        wrong_passphrase = "wrong_passphrase_456!"

        init_database(str(db_path), correct_passphrase)

        with pytest.raises(ValueError, match="Incorrect passphrase"):
            open_database(str(db_path), wrong_passphrase)

    def test_open_database_nonexistent_file(self, tmp_path: Path) -> None:
        """Test opening non-existent database raises FileNotFoundError."""
        db_path = tmp_path / "nonexistent.db"
        passphrase = "test_passphrase_123!"

        with pytest.raises(FileNotFoundError, match="Database file not found"):
            open_database(str(db_path), passphrase)

    def test_open_database_missing_salt_metadata(self, tmp_path: Path) -> None:
        """Test opening database with missing salt raises CorruptedDatabaseError."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Corrupt database by deleting salt metadata
        with open_database(str(db_path), passphrase) as db_session:
            db_session.session.query(Metadata).filter_by(key="encryption_salt").delete()
            db_session.session.commit()

        # Attempt to open corrupted database
        with pytest.raises(CorruptedDatabaseError, match="Encryption salt missing"):
            open_database(str(db_path), passphrase)

    def test_open_database_missing_canary_metadata(self, tmp_path: Path) -> None:
        """Test opening database with missing canary raises CorruptedDatabaseError."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Corrupt database by deleting canary metadata
        with open_database(str(db_path), passphrase) as db_session:
            db_session.session.query(Metadata).filter_by(
                key="passphrase_canary"
            ).delete()
            db_session.session.commit()

        # Attempt to open corrupted database
        with pytest.raises(CorruptedDatabaseError, match="Passphrase canary missing"):
            open_database(str(db_path), passphrase)

    def test_open_database_corrupted_canary_value(self, tmp_path: Path) -> None:
        """Test opening database with corrupted canary (decrypts but wrong value) raises ValueError."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Corrupt canary by replacing with different encrypted value
        with open_database(str(db_path), passphrase) as db_session:
            # Encrypt a wrong value with same encryption service
            wrong_canary = db_session.encryption.encrypt("WRONG_CANARY_VALUE")

            canary_record = (
                db_session.session.query(Metadata)
                .filter_by(key="passphrase_canary")
                .first()
            )
            canary_record.value = wrong_canary  # type: ignore
            db_session.session.commit()

        # Attempt to open with corrupted canary
        with pytest.raises(ValueError, match="Incorrect passphrase"):
            open_database(str(db_path), passphrase)

    def test_database_session_close(self, tmp_path: Path) -> None:
        """Test DatabaseSession.close() can be called without errors."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        db_session = open_database(str(db_path), passphrase)

        # Verify session works before close
        metadata = db_session.session.query(Metadata).all()
        assert len(metadata) > 0

        # Close session - should not raise any errors
        db_session.close()

        # Verify engine is disposed (connection pool closed)
        # After dispose(), the engine's pool should be recreated on next use
        # We can't easily test the internal state, but calling close() twice
        # should not raise an error
        db_session.close()  # Second close should be safe

    def test_database_session_context_manager(self, tmp_path: Path) -> None:
        """Test DatabaseSession context manager automatically closes session."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Use context manager
        with open_database(str(db_path), passphrase) as db_session:
            # Session should work inside context
            metadata = db_session.session.query(Metadata).all()
            assert len(metadata) > 0

        # After context exit, close() should have been called
        # We can't easily verify internal state, but we can verify
        # that we can still open a new session successfully
        # (which wouldn't work if resources weren't properly released in WAL mode)
        with open_database(str(db_path), passphrase) as db_session2:
            metadata2 = db_session2.session.query(Metadata).all()
            assert len(metadata2) > 0

    def test_open_database_encryption_service_functional(self, tmp_path: Path) -> None:
        """Test encryption service from open_database() works correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            # Test encryption roundtrip
            plaintext = "Test Value"
            encrypted = db_session.encryption.encrypt(plaintext)
            decrypted = db_session.encryption.decrypt(encrypted)

            assert decrypted == plaintext
            assert encrypted != plaintext
