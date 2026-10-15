"""Database initialization and session management for encrypted SQLite database.

This module provides functions for creating and opening encrypted SQLite databases,
managing encryption keys, and handling database sessions with proper resource cleanup.
"""

from __future__ import annotations

import base64
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateTable

from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.data.models import Base, Entity, Metadata
from gdpr_pseudonymizer.exceptions import (
    CorruptedDatabaseError,
    DatabaseConversionError,
)
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)

# Story 10.7 (rule (a)): a database created or converted by this version keys
# its entities on (text, type) and holds schema_version "1.1.0". A database
# made before 10.7 holds "1.0.0" and a unique key on the text alone; the first
# open by this version converts it, once.
SCHEMA_VERSION = "1.1.0"
PRE_10_7_SCHEMA_VERSION = "1.0.0"

# How long a process waits for another one's conversion (its write lock)
CONVERSION_BUSY_TIMEOUT_SECONDS = 30.0

# Indexes of init_database, also recreated by the conversion
_ENTITY_INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_entities_full_name ON entities(full_name)",
    "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)",
    "CREATE INDEX IF NOT EXISTS idx_entities_first_name ON entities(first_name)",
    "CREATE INDEX IF NOT EXISTS idx_entities_last_name ON entities(last_name)",
    # Partial index for ambiguous entities
    "CREATE INDEX IF NOT EXISTS idx_entities_ambiguous ON entities(is_ambiguous) "
    "WHERE is_ambiguous = 1",
)
_OPERATION_INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operations(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(operation_type)",
)


class DatabaseSession:
    """Encapsulates database session with encryption service.

    Provides context manager support for safe resource management.

    Example:
        >>> with open_database("mapping.db", "my_passphrase") as db_session:
        ...     repo = SQLiteMappingRepository(db_session)
        ...     entity = repo.find_by_full_name_and_type("Marie Dubois", "PERSON")
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


def _already_exists_message(db_path: str) -> str:
    """Message of the ValueError raised when db_path already exists."""
    return f"Database already exists at {db_path}. Use open_database() to open existing database."


def _create_exclusively(db_path: str) -> int:
    """Create db_path, failing if it exists, and return the open descriptor.

    Mode 0o644 is SQLite's own default for a file it creates, so the on-disk
    permissions are those of a database SQLite would have created itself.

    Raises:
        ValueError: If db_path already exists (another call created it)
        Exception: If the file cannot be created (missing directory, permissions)
    """
    try:
        return os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as exc:
        raise ValueError(_already_exists_message(db_path)) from exc
    except OSError as e:
        raise Exception(f"Database initialization failed: {e}") from e


def _dispose_quietly(engine: Engine | None) -> None:
    """Dispose engine on the failure path; log a failure, never raise it."""
    if engine is None:
        return
    try:
        engine.dispose()
    except Exception as err:
        logger.warning(
            "database_init_cleanup_failed",
            step="dispose",
            error_type=type(err).__name__,
        )


def _is_same_file(fd: int, db_path: str) -> bool:
    """True if db_path is still the file open as fd (False if either stat fails)."""
    try:
        return os.path.samestat(os.fstat(fd), os.stat(db_path))
    except OSError:
        return False


def _delete_quietly(db_path: str) -> None:
    """Delete db_path, then its SQLite sidecars; log a failure, never raise it.

    The first error stops the step, so a sidecar is never deleted while its
    main file stays. A missing file is fine.
    """
    try:
        for path in (
            db_path,
            f"{db_path}-wal",
            f"{db_path}-shm",
            f"{db_path}-journal",
        ):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    except Exception as err:
        logger.warning(
            "database_init_cleanup_failed",
            step="delete",
            error_type=type(err).__name__,
        )


def init_database(db_path: str, passphrase: str) -> None:
    """Initialize a new encrypted SQLite database.

    Creates database schema, enables SQLite optimizations (WAL mode, foreign keys),
    and stores encryption parameters in metadata table.

    The file is created exclusively (``O_CREAT | O_EXCL``) after the key
    derivation, and its descriptor stays open until the call ends. If another
    call or process created ``db_path`` first, this call raises the "Database
    already exists" ``ValueError`` and touches nothing. On failure, the engine
    is disposed first, then ``db_path`` and its ``-wal``, ``-shm`` and
    ``-journal`` files are deleted only if ``db_path`` is still the file this
    call created: the function never deletes a file it did not create.

    Args:
        db_path: Path to database file (will be created)
        passphrase: User passphrase for encryption (min 12 characters)

    Raises:
        ValueError: If passphrase invalid or database already exists (also when
            another process creates it during this call)
        Exception: If database creation fails
        KeyboardInterrupt: Re-raised unwrapped, after the same cleanup

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
        raise ValueError(_already_exists_message(db_path))

    # Generate salt and create encryption service (before the file exists, so
    # the slow key derivation never runs while a half-built file is visible)
    salt = EncryptionService.generate_salt()
    encryption_service = EncryptionService(
        passphrase, salt, EncryptionService.PBKDF2_ITERATIONS
    )

    engine: Engine | None = None
    # Exclusive create: ValueError if the file exists by now. The descriptor
    # stays open until the call ends, so the file's identity cannot be reused
    # (POSIX) and no other process can delete or replace it (Windows).
    fd = _create_exclusively(db_path)
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

        # Create indexes for query optimization: entity table indexes (for
        # encrypted field queries), then operations table indexes (for audit
        # queries)
        with engine.connect() as conn:
            for statement in _ENTITY_INDEX_STATEMENTS + _OPERATION_INDEX_STATEMENTS:
                conn.execute(text(statement))
            conn.commit()

        # Initialize metadata table with encryption parameters
        session_local = sessionmaker(bind=engine)
        session = session_local()

        try:
            # Store schema version (Story 10.7: the (text, type) key)
            session.add(Metadata(key="schema_version", value=SCHEMA_VERSION))

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

    except BaseException as exc:
        # Clean up this call's own partial database, and nothing else
        try:
            # Dispose first: on Windows an open connection blocks the delete
            _dispose_quietly(engine)
            # Identity from the still-open descriptor: is db_path still ours?
            ours = _is_same_file(fd, db_path)
        finally:
            # Close only after the dispose: on POSIX, closing any descriptor
            # on a file drops every fcntl lock this process holds on it,
            # SQLite's included. Never move this close earlier.
            os.close(fd)
            fd = -1
        if ours:
            _delete_quietly(db_path)
        if isinstance(exc, Exception):
            raise Exception(f"Database initialization failed: {exc}") from exc
        # KeyboardInterrupt, SystemExit: re-raised unwrapped
        raise
    finally:
        if fd >= 0:
            # Success: closed after engine.dispose() (see above)
            os.close(fd)


def open_database(db_path: str, passphrase: str) -> DatabaseSession:
    """Open existing encrypted database with passphrase validation.

    Loads encryption parameters from metadata, validates passphrase using canary,
    and returns database session ready for use.

    A database made before Story 10.7 (one row per text) is converted to one
    row per (text, type) right after the passphrase check, once, in one
    transaction (rule (a)): every row keeps its id, type and pseudonym. If the
    conversion cannot be made, the file is left unchanged and the open stops
    with DatabaseConversionError.

    Args:
        db_path: Path to existing database file
        passphrase: User passphrase for decryption

    Returns:
        DatabaseSession with authenticated encryption service

    Raises:
        FileNotFoundError: If database file doesn't exist
        ValueError: If passphrase incorrect
        CorruptedDatabaseError: If database metadata missing or invalid
        DatabaseConversionError: If a pre-10.7 database cannot be converted, or
            its schema version and table definition disagree (file unchanged)

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

        # Story 10.7 (rule (a)): convert a pre-10.7 file once, after the
        # passphrase check and before anything else uses it. The session's
        # connection is released first; the session is used again afterwards.
        session.close()
        _ensure_current_schema(db_path)

        # Return database session with encryption service
        return DatabaseSession(engine, session, encryption_service)

    except (ValueError, CorruptedDatabaseError, DatabaseConversionError) as e:
        # Clean up on validation errors
        session.close()
        engine.dispose()
        raise e
    except Exception as e:
        # Clean up on unexpected errors
        session.close()
        engine.dispose()
        raise Exception(f"Failed to open database: {e}") from e


# ---------------------------------------------------------------------------
# Story 10.7, rule (a): conversion of a pre-10.7 file, once, on open
# ---------------------------------------------------------------------------


def _read_schema_version(conn: sqlite3.Connection) -> str | None:
    """The stored schema_version, or None if the row is missing."""
    row = conn.execute(
        "SELECT value FROM metadata WHERE \"key\" = 'schema_version'"
    ).fetchone()
    return None if row is None else str(row[0])


def _unique_keys(conn: sqlite3.Connection) -> list[list[str]]:
    """Columns of each UNIQUE index of the entities table (primary key excluded)."""
    keys: list[list[str]] = []
    for _seq, name, unique, origin, _partial in conn.execute(
        "PRAGMA index_list('entities')"
    ).fetchall():
        if not unique or origin == "pk":
            continue
        quoted = '"' + str(name).replace('"', '""') + '"'
        keys.append(
            [str(info[2]) for info in conn.execute(f"PRAGMA index_info({quoted})")]
        )
    return keys


def _is_pre_10_7(conn: sqlite3.Connection) -> bool:
    """True for a pre-10.7 file, False for a 10.7 one.

    A pre-10.7 file holds schema_version "1.0.0" and a unique index on the
    text alone; a 10.7 file holds neither.

    Raises:
        DatabaseConversionError: If only one of the two holds (format not
            recognised); nothing is changed
    """
    version = _read_schema_version(conn)
    old_version = version == PRE_10_7_SCHEMA_VERSION
    old_key = ["full_name"] in _unique_keys(conn)
    if old_version and old_key:
        return True
    if not old_version and not old_key:
        return False
    logger.error(
        "database_format_not_recognised",
        schema_version=version,
        unique_key_on_text_alone=old_key,
    )
    raise DatabaseConversionError(
        "The database format is not recognised: its schema version "
        f"({version if version is not None else 'missing'}) does not match its "
        "table definition. The file was not changed."
    )


def _begin_immediate(conn: sqlite3.Connection) -> None:
    """Start the conversion's transaction, taking the write lock at once."""
    conn.execute("BEGIN IMMEDIATE")


def _entities_table_sql(table_name: str) -> str:
    """CREATE TABLE statement of the current Entity model, under table_name."""
    statement = CreateTable(Entity.__table__)  # type: ignore[arg-type]
    sql = str(statement.compile(dialect=sqlite_dialect.dialect())).strip()
    prefix = "CREATE TABLE entities ("
    if not sql.startswith(prefix):
        raise RuntimeError("unexpected CREATE TABLE statement for entities")
    return f"CREATE TABLE {table_name} (" + sql[len(prefix) :]


def _rebuild_entities_table(conn: sqlite3.Connection) -> int:
    """Rebuild the entities table with the (text, type) key; return its row count.

    Creates the new table, copies every row by named columns (values as
    stored, nothing decrypted), checks the row count, drops the old table,
    renames the new one and recreates the indexes. Runs inside the caller's
    transaction.
    """
    columns = [column.name for column in Entity.__table__.columns]
    stored = [
        str(row[1]) for row in conn.execute("PRAGMA table_info('entities')").fetchall()
    ]
    if sorted(stored) != sorted(columns):
        raise RuntimeError("the entities table has unexpected columns")
    column_list = ", ".join(columns)
    before = int(conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0])
    conn.execute(_entities_table_sql("entities_new"))
    conn.execute(
        f"INSERT INTO entities_new ({column_list}) SELECT {column_list} FROM entities"
    )
    copied = int(conn.execute("SELECT COUNT(*) FROM entities_new").fetchone()[0])
    if copied != before:
        raise RuntimeError(f"row count mismatch: {before} before, {copied} copied")
    conn.execute("DROP TABLE entities")
    conn.execute("ALTER TABLE entities_new RENAME TO entities")
    for statement in _ENTITY_INDEX_STATEMENTS:
        conn.execute(statement)
    return before


def _write_schema_version(conn: sqlite3.Connection, version: str) -> None:
    """Write schema_version; the last step of the conversion before COMMIT."""
    stamp = datetime.now(timezone.utc).replace(tzinfo=None)
    cursor = conn.execute(
        "UPDATE metadata SET value = ?, updated_at = ? "
        "WHERE \"key\" = 'schema_version'",
        (version, stamp.strftime("%Y-%m-%d %H:%M:%S.%f")),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("schema_version row not found")


def _conversion_failed_message(error: BaseException) -> str:
    """User message of a failed conversion (no entity text, no file content)."""
    detail = str(error).lower()
    if isinstance(error, PermissionError) or "readonly" in detail:
        cause = "the database file or its folder is read-only"
    elif "locked" in detail or "busy" in detail:
        cause = "another program is using the database"
    elif "full" in detail or "disk" in detail:
        cause = "the disk is full or cannot be written"
    else:
        cause = (
            "the file or its folder is read-only, the disk is full, "
            "or another program is using the database"
        )
    return (
        "The database could not be converted to the new format "
        "(one row per name and type). The file is unchanged. "
        f"Likely cause: {cause}. ({type(error).__name__}: {error})"
    )


def _ensure_current_schema(db_path: str) -> bool:
    """Convert a pre-10.7 file to the (text, type) key, once (Story 10.7, rule (a)).

    Runs on its own connection in autocommit mode with an explicit
    ``BEGIN IMMEDIATE``, so the whole conversion (the table rebuild and the
    new schema_version) is one transaction: a failure at any point rolls back
    every change and the file is left as it was. A second process waits for
    the write lock (busy timeout), checks the file again inside its own
    transaction, finds it converted and changes nothing.

    Args:
        db_path: Path to an existing database whose passphrase was checked

    Returns:
        True if this call converted the file, False if it had nothing to do

    Raises:
        DatabaseConversionError: If the conversion cannot be made, or the
            format is not recognised; the file is unchanged
    """
    conn = sqlite3.connect(
        db_path, timeout=CONVERSION_BUSY_TIMEOUT_SECONDS, isolation_level=None
    )
    try:
        if not _is_pre_10_7(conn):
            return False
        started = time.monotonic()
        try:
            _begin_immediate(conn)
            try:
                if not _is_pre_10_7(conn):
                    # Another process converted the file meanwhile
                    conn.execute("ROLLBACK")
                    return False
                rows = _rebuild_entities_table(conn)
                _write_schema_version(conn, SCHEMA_VERSION)
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    try:
                        conn.execute("ROLLBACK")
                    except sqlite3.Error as rollback_error:
                        logger.error(
                            "database_conversion_rollback_failed",
                            error_type=type(rollback_error).__name__,
                        )
                raise
        except DatabaseConversionError:
            raise
        except Exception as exc:
            logger.error("database_conversion_failed", error_type=type(exc).__name__)
            raise DatabaseConversionError(_conversion_failed_message(exc)) from exc
        logger.info(
            "database_converted",
            rows=rows,
            from_version=PRE_10_7_SCHEMA_VERSION,
            to_version=SCHEMA_VERSION,
            duration_seconds=round(time.monotonic() - started, 3),
        )
        return True
    finally:
        conn.close()
