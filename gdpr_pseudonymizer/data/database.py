"""Database initialization and session management for encrypted SQLite database.

This module provides functions for creating and opening encrypted SQLite databases,
managing encryption keys, and handling database sessions with proper resource cleanup.
"""

from __future__ import annotations

import base64
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.data.models import Base, Metadata


class DatabaseSession:
    """Encapsulates database session with encryption service.

    Provides context manager support for safe resource management.

    Example:
        >>> with open_database("mapping.db", "my_passphrase") as db_session:
        ...     repo = SQLiteMappingRepository(db_session)
        ...     entity = repo.find_by_full_name("Marie Dubois")
    """

    def __init__(
        self, engine: Engine, session: Session, encryption_service: EncryptionService
    ) -> None:
        """Initialize database session.

        Args:
            engine: SQLAlchemy engine
            session: SQLAlchemy session
            encryption_service: Encryption service for sensitive fields
        """
        self.engine = engine
        self.session = session
        self.encryption = encryption_service

    def close(self) -> None:
        """Close session and release database resources."""
        self.session.close()
        self.engine.dispose()

    def __enter__(self) -> DatabaseSession:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit with automatic cleanup."""
        self.close()


def init_database(db_path: str, passphrase: str) -> None:
    """Initialize a new encrypted SQLite database.

    Creates database schema, enables SQLite optimizations (WAL mode, foreign keys),
    and stores encryption parameters in metadata table.

    Args:
        db_path: Path to database file (will be created)
        passphrase: User passphrase for encryption (min 12 characters)

    Raises:
        ValueError: If passphrase invalid or database already exists
        Exception: If database creation fails

    Example:
        >>> init_database("mapping.db", "my_secure_passphrase_123!")
    """
    # Validate passphrase strength before proceeding
    is_valid, feedback = EncryptionService.validate_passphrase(passphrase)
    if not is_valid:
        raise ValueError(f"Invalid passphrase: {feedback}")

    # Check if database already exists
    db_file = Path(db_path)
    if db_file.exists():
        raise ValueError(
            f"Database already exists at {db_path}. Use open_database() to open existing database."
        )

    # Generate salt and create encryption service
    salt = EncryptionService.generate_salt()
    encryption_service = EncryptionService(
        passphrase, salt, EncryptionService.PBKDF2_ITERATIONS
    )

    try:
        # Create SQLAlchemy engine
        engine = create_engine(f"sqlite:///{db_path}")

        # Create all tables from models
        Base.metadata.create_all(engine)

        # Enable SQLite optimizations
        with engine.connect() as conn:
            # Enable WAL mode for concurrent reads
            conn.execute(text("PRAGMA journal_mode=WAL"))
            # Enable foreign key constraints
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()

        # Create indexes for query optimization
        with engine.connect() as conn:
            # Entity table indexes (for encrypted field queries)
            conn.execute(
                text("CREATE INDEX idx_entities_full_name ON entities(full_name)")
            )
            conn.execute(
                text("CREATE INDEX idx_entities_type ON entities(entity_type)")
            )
            conn.execute(
                text("CREATE INDEX idx_entities_first_name ON entities(first_name)")
            )
            conn.execute(
                text("CREATE INDEX idx_entities_last_name ON entities(last_name)")
            )
            # Partial index for ambiguous entities
            conn.execute(
                text(
                    "CREATE INDEX idx_entities_ambiguous ON entities(is_ambiguous) "
                    "WHERE is_ambiguous = 1"
                )
            )

            # Operations table indexes (for audit queries)
            conn.execute(
                text("CREATE INDEX idx_operations_timestamp ON operations(timestamp)")
            )
            conn.execute(
                text("CREATE INDEX idx_operations_type ON operations(operation_type)")
            )

            conn.commit()

        # Initialize metadata table with encryption parameters
        session_local = sessionmaker(bind=engine)
        session = session_local()

        try:
            # Store schema version
            session.add(Metadata(key="schema_version", value="1.0.0"))

            # Store encryption salt (base64-encoded)
            session.add(
                Metadata(
                    key="encryption_salt", value=base64.b64encode(salt).decode("ascii")
                )
            )

            # Store KDF iterations
            session.add(
                Metadata(
                    key="kdf_iterations",
                    value=str(EncryptionService.PBKDF2_ITERATIONS),
                )
            )

            # Store encrypted passphrase canary for validation
            canary = encryption_service.encrypt_canary()
            session.add(Metadata(key="passphrase_canary", value=canary))

            session.commit()

        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to initialize metadata: {e}") from e
        finally:
            session.close()

        engine.dispose()

    except Exception as e:
        # Clean up partial database file on failure
        if db_file.exists():
            db_file.unlink()
        raise Exception(f"Database initialization failed: {e}") from e


def open_database(db_path: str, passphrase: str) -> DatabaseSession:
    """Open existing encrypted database with passphrase validation.

    Loads encryption parameters from metadata, validates passphrase using canary,
    and returns database session ready for use.

    Args:
        db_path: Path to existing database file
        passphrase: User passphrase for decryption

    Returns:
        DatabaseSession with authenticated encryption service

    Raises:
        FileNotFoundError: If database file doesn't exist
        ValueError: If passphrase incorrect
        CorruptedDatabaseError: If database metadata missing or invalid

    Example:
        >>> with open_database("mapping.db", "my_passphrase") as db_session:
        ...     # Use db_session for queries
        ...     pass
    """
    # Verify database file exists
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    # Create engine and session
    engine = create_engine(f"sqlite:///{db_path}")

    # Enable foreign keys (per-connection setting in SQLite)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

    session_local = sessionmaker(bind=engine)
    session = session_local()

    try:
        # Load encryption parameters from metadata
        salt_record = session.query(Metadata).filter_by(key="encryption_salt").first()
        iterations_record = (
            session.query(Metadata).filter_by(key="kdf_iterations").first()
        )
        canary_record = (
            session.query(Metadata).filter_by(key="passphrase_canary").first()
        )

        # Validate metadata exists
        if not salt_record:
            raise CorruptedDatabaseError(
                "Encryption salt missing from metadata - database may be corrupted"
            )
        if not iterations_record:
            raise CorruptedDatabaseError(
                "KDF iterations missing from metadata - database may be corrupted"
            )
        if not canary_record:
            raise CorruptedDatabaseError(
                "Passphrase canary missing from metadata - database may be corrupted"
            )

        # Parse encryption parameters
        salt = base64.b64decode(salt_record.value.encode("ascii"))
        iterations = int(iterations_record.value)

        # Create encryption service with provided passphrase
        encryption_service = EncryptionService(passphrase, salt, iterations)

        # Validate passphrase using canary
        if not encryption_service.verify_canary(canary_record.value):
            # Try to decrypt canary to distinguish between wrong passphrase vs corrupted data
            try:
                decrypted_canary = encryption_service.decrypt(canary_record.value)
                if decrypted_canary != EncryptionService.CANARY_VALUE:
                    raise ValueError(
                        "Incorrect passphrase - canary decrypts but value mismatch"
                    )
            except Exception:
                pass  # Decryption failed, treat as wrong passphrase

            raise ValueError(
                "Incorrect passphrase. Please check your passphrase and try again."
            )

        # Return database session with encryption service
        return DatabaseSession(engine, session, encryption_service)

    except (ValueError, CorruptedDatabaseError) as e:
        # Clean up on validation errors
        session.close()
        engine.dispose()
        raise e
    except Exception as e:
        # Clean up on unexpected errors
        session.close()
        engine.dispose()
        raise Exception(f"Failed to open database: {e}") from e


class CorruptedDatabaseError(Exception):
    """Raised when database metadata is missing or invalid."""

    pass
