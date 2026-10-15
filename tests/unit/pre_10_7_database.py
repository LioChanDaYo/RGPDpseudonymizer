"""Builder of a pre-10.7 mapping database for tests (Story 10.7, Task 3.1).

It writes, with plain ``sqlite3``, the file that ``init_database`` wrote at
``51d8429``, the last code before Story 10.7: the three tables with their exact
definitions (``UNIQUE (full_name)`` included), every index, the automatic ones
included, ``PRAGMA journal_mode=WAL``, and the four metadata rows with
``schema_version`` "1.0.0". Entity rows are encrypted as the repository of that
code stored them. The statements below are copied from ``sqlite_master`` of a
file made by the ``51d8429`` code, so the builder never depends on the current
models (story Debug Log, Task 3.1).

Invented names only (Story 10.7, AC11).
"""

from __future__ import annotations

import base64
import sqlite3
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gdpr_pseudonymizer.data.encryption import EncryptionService

PRE_10_7_SCHEMA_VERSION = "1.0.0"

# create_all at 51d8429, in its order (entities, operations, metadata).
_TABLES = (
    "CREATE TABLE entities (\n"
    "\tid VARCHAR NOT NULL, \n"
    "\tentity_type VARCHAR NOT NULL, \n"
    "\tfirst_name VARCHAR, \n"
    "\tlast_name VARCHAR, \n"
    "\tfull_name VARCHAR NOT NULL, \n"
    "\tpseudonym_first VARCHAR, \n"
    "\tpseudonym_last VARCHAR, \n"
    "\tpseudonym_full VARCHAR NOT NULL, \n"
    "\tfirst_seen_timestamp DATETIME NOT NULL, \n"
    "\tgender VARCHAR, \n"
    "\tconfidence_score FLOAT, \n"
    "\ttheme VARCHAR NOT NULL, \n"
    "\tis_ambiguous BOOLEAN NOT NULL, \n"
    "\tambiguity_reason VARCHAR, \n"
    "\tPRIMARY KEY (id), \n"
    "\tUNIQUE (full_name)\n"
    ")",
    "CREATE TABLE operations (\n"
    "\tid VARCHAR NOT NULL, \n"
    "\ttimestamp DATETIME NOT NULL, \n"
    "\toperation_type VARCHAR NOT NULL, \n"
    "\tfiles_processed JSON NOT NULL, \n"
    "\tuser_modifications JSON, \n"
    "\tmodel_name VARCHAR NOT NULL, \n"
    "\tmodel_version VARCHAR NOT NULL, \n"
    "\ttheme_selected VARCHAR NOT NULL, \n"
    "\tentity_count INTEGER NOT NULL, \n"
    "\tprocessing_time_seconds FLOAT NOT NULL, \n"
    "\tsuccess BOOLEAN NOT NULL, \n"
    "\terror_message VARCHAR, \n"
    "\tPRIMARY KEY (id)\n"
    ")",
    "CREATE TABLE metadata (\n"
    '\t"key" VARCHAR NOT NULL, \n'
    "\tvalue VARCHAR NOT NULL, \n"
    "\tupdated_at DATETIME NOT NULL, \n"
    '\tPRIMARY KEY ("key")\n'
    ")",
)

# init_database's indexes at 51d8429, in its order.
_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_entities_full_name ON entities(full_name)",
    "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)",
    "CREATE INDEX IF NOT EXISTS idx_entities_first_name ON entities(first_name)",
    "CREATE INDEX IF NOT EXISTS idx_entities_last_name ON entities(last_name)",
    "CREATE INDEX IF NOT EXISTS idx_entities_ambiguous ON entities(is_ambiguous) "
    "WHERE is_ambiguous = 1",
    "CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operations(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(operation_type)",
)

ENTITY_COLUMNS = (
    "id",
    "entity_type",
    "first_name",
    "last_name",
    "full_name",
    "pseudonym_first",
    "pseudonym_last",
    "pseudonym_full",
    "first_seen_timestamp",
    "gender",
    "confidence_score",
    "theme",
    "is_ambiguous",
    "ambiguity_reason",
)


@dataclass(frozen=True)
class LegacyRow:
    """One mapping row as the pre-10.7 code stored it (plaintext here)."""

    entity_type: str
    full_name: str
    pseudonym_full: str
    first_name: str | None = None
    last_name: str | None = None
    pseudonym_first: str | None = None
    pseudonym_last: str | None = None
    theme: str = "neutral"
    gender: str | None = None
    confidence_score: float | None = None
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


def _timestamp() -> str:
    """A DATETIME value as SQLAlchemy's SQLite dialect stores it."""
    return datetime(2026, 10, 1, 9, 30, 0, 123456).strftime("%Y-%m-%d %H:%M:%S.%f")


def build_pre_10_7_database(
    db_path: Path, passphrase: str, rows: Sequence[LegacyRow] = ()
) -> list[str]:
    """Write a pre-10.7 database at db_path and return the ids of its rows.

    Args:
        db_path: Path of the new file (must not exist)
        passphrase: Passphrase of the file (at least 12 characters)
        rows: Entity rows to store, encrypted as the pre-10.7 repository did

    Returns:
        The id of each stored row, in the order of ``rows``
    """
    if db_path.exists():
        raise ValueError(f"{db_path} already exists")
    salt = EncryptionService.generate_salt()
    encryption = EncryptionService(
        passphrase, salt, EncryptionService.PBKDF2_ITERATIONS
    )
    ids: list[str] = []
    conn = sqlite3.connect(str(db_path))
    try:
        for statement in _TABLES:
            conn.execute(statement)
        conn.commit()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()
        for statement in _INDEXES:
            conn.execute(statement)
        conn.commit()
        stamp = _timestamp()
        metadata = (
            ("schema_version", PRE_10_7_SCHEMA_VERSION),
            ("encryption_salt", base64.b64encode(salt).decode("ascii")),
            ("kdf_iterations", str(EncryptionService.PBKDF2_ITERATIONS)),
            ("passphrase_canary", encryption.encrypt_canary()),
        )
        conn.executemany(
            'INSERT INTO metadata ("key", value, updated_at) VALUES (?, ?, ?)',
            [(key, value, stamp) for key, value in metadata],
        )
        for row in rows:
            row_id = str(uuid.uuid4())
            ids.append(row_id)
            conn.execute(
                f"INSERT INTO entities ({', '.join(ENTITY_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in ENTITY_COLUMNS)})",
                (
                    row_id,
                    row.entity_type,
                    encryption.encrypt(row.first_name),
                    encryption.encrypt(row.last_name),
                    encryption.encrypt(row.full_name),
                    encryption.encrypt(row.pseudonym_first),
                    encryption.encrypt(row.pseudonym_last),
                    encryption.encrypt(row.pseudonym_full),
                    stamp,
                    row.gender,
                    row.confidence_score,
                    row.theme,
                    1 if row.is_ambiguous else 0,
                    row.ambiguity_reason,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return ids


def read_master(db_path: Path) -> list[tuple[str, str, str, str | None]]:
    """(type, name, tbl_name, sql) of every schema object, sorted by name."""
    conn = sqlite3.connect(str(db_path))
    try:
        return sorted(
            conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master")
        )
    finally:
        conn.close()


def read_entity_rows(db_path: Path) -> list[tuple[object, ...]]:
    """Every entities row as stored, by named columns, sorted by id."""
    conn = sqlite3.connect(str(db_path))
    try:
        return list(
            conn.execute(
                f"SELECT {', '.join(ENTITY_COLUMNS)} FROM entities ORDER BY id"
            )
        )
    finally:
        conn.close()


def read_table(db_path: Path, table: str) -> list[tuple[object, ...]]:
    """Every row of a table as stored (all columns), sorted."""
    conn = sqlite3.connect(str(db_path))
    try:
        return sorted(conn.execute(f"SELECT * FROM {table}"), key=repr)
    finally:
        conn.close()


def read_schema_version(db_path: Path) -> str | None:
    """The stored schema_version, or None if the row is missing."""
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT value FROM metadata WHERE \"key\" = 'schema_version'"
        ).fetchone()
        return None if row is None else str(row[0])
    finally:
        conn.close()


def unique_index_columns(db_path: Path, table: str = "entities") -> list[list[str]]:
    """Columns of each UNIQUE index of a table (primary key excluded), sorted."""
    conn = sqlite3.connect(str(db_path))
    try:
        result = []
        for _seq, name, unique, origin, _partial in conn.execute(
            f"PRAGMA index_list('{table}')"
        ):
            if not unique or origin == "pk":
                continue
            columns = [info[2] for info in conn.execute(f"PRAGMA index_info('{name}')")]
            result.append(columns)
        return sorted(result)
    finally:
        conn.close()


def journal_mode(db_path: Path) -> str:
    """The file's journal mode as SQLite reports it."""
    conn = sqlite3.connect(str(db_path))
    try:
        return str(conn.execute("PRAGMA journal_mode").fetchone()[0])
    finally:
        conn.close()
