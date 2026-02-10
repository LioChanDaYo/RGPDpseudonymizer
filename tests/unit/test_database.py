"""Unit tests for database initialization and session management."""

import base64
from pathlib import Path

import pytest
from sqlalchemy import text

from gdpr_pseudonymizer.data.database import (
    init_database,
    open_database,
)
from gdpr_pseudonymizer.exceptions import CorruptedDatabaseError
from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.data.models import Metadata


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
