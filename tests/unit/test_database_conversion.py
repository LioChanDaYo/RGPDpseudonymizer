"""Story 10.7, AC3: a pre-10.7 database is converted once, on open (rule (a)).

Each pre-10.7 file is written by ``tests.unit.pre_10_7_database``, which
reproduces what ``init_database`` wrote at ``51d8429`` (Task 3.1). Every test
goes through ``open_database``. Invented names only (AC11).
"""

from __future__ import annotations

import sqlite3
import stat
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DuplicateEntityError
from tests.unit.pre_10_7_database import (
    LegacyRow,
    build_pre_10_7_database,
    journal_mode,
    read_entity_rows,
    read_master,
    read_schema_version,
    read_table,
    unique_index_columns,
)

PASSPHRASE = "zorbalia_conv_pass_123!"
WRONG_PASSPHRASE = "quentrix_wrong_pass_456!"

OLD_VERSION = "1.0.0"
NEW_VERSION = "1.1.0"  # Story 10.7, AC3 (Task 2.2)
NEW_KEY = [["full_name", "entity_type"]]
OLD_KEY = [["full_name"]]
NAMED_INDEXES = {
    "idx_entities_full_name",
    "idx_entities_type",
    "idx_entities_first_name",
    "idx_entities_last_name",
    "idx_entities_ambiguous",
    "idx_operations_timestamp",
    "idx_operations_type",
}

ROWS = (
    LegacyRow("LOCATION", "Zorbaville", "Quentrel"),
    LegacyRow(
        "PERSON",
        "Zorbalia Quentrix",
        "Zorbtech Quentrel",
        first_name="Zorbalia",
        last_name="Quentrix",
        pseudonym_first="Zorbtech",
        pseudonym_last="Quentrel",
        gender="female",
        confidence_score=0.91,
        is_ambiguous=True,
        ambiguity_reason="invented reason",
    ),
    LegacyRow("ORG", "Zorbtech", "Quentrix Holding"),
)


def _add_operation(db_path: Path) -> None:
    """One audit row, written as the pre-10.7 code wrote it."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO operations (id, timestamp, operation_type, files_processed, "
            "user_modifications, model_name, model_version, theme_selected, "
            "entity_count, processing_time_seconds, success, error_message) "
            "VALUES ('op-1', '2026-10-01 09:30:00.000000', 'PROCESS', "
            "'[\"zorbaville.txt\"]', NULL, 'spacy', '3.8.0', 'neutral', 3, 0.5, 1, NULL)"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def old_db(tmp_path: Path) -> Path:
    path = tmp_path / "pre_10_7.db"
    build_pre_10_7_database(path, PASSPHRASE, ROWS)
    _add_operation(path)
    return path


def _metadata_without_version(db_path: Path) -> list[tuple[object, ...]]:
    return [
        row for row in read_table(db_path, "metadata") if row[0] != "schema_version"
    ]


def _snapshot(db_path: Path) -> tuple[Any, ...]:
    return (
        read_master(db_path),
        read_schema_version(db_path),
        read_entity_rows(db_path),
        read_table(db_path, "operations"),
        read_table(db_path, "metadata"),
    )


def _open_and_close(db_path: Path, passphrase: str = PASSPHRASE) -> None:
    with open_database(str(db_path), passphrase):
        pass


def _make_read_only(db_path: Path) -> None:
    db_path.chmod(stat.S_IREAD)


def _make_writable(db_path: Path) -> None:
    db_path.chmod(stat.S_IREAD | stat.S_IWRITE)


class TestConversion:
    """The conversion keeps every row and gives the file the (text, type) key."""

    def test_open_converts_pre_10_7_file(self, old_db: Path) -> None:
        assert read_schema_version(old_db) == OLD_VERSION
        assert unique_index_columns(old_db) == OLD_KEY
        rows_before = read_entity_rows(old_db)
        operations_before = read_table(old_db, "operations")
        metadata_before = _metadata_without_version(old_db)

        _open_and_close(old_db)

        assert read_schema_version(old_db) == NEW_VERSION
        assert unique_index_columns(old_db) == NEW_KEY
        assert read_entity_rows(old_db) == rows_before
        assert read_table(old_db, "operations") == operations_before
        assert _metadata_without_version(old_db) == metadata_before
        index_names = {
            name
            for kind, name, _table, sql in read_master(old_db)
            if kind == "index" and sql is not None
        }
        assert index_names == NAMED_INDEXES
        tables = {name for kind, name, _t, _s in read_master(old_db) if kind == "table"}
        assert tables == {"entities", "operations", "metadata"}
        assert journal_mode(old_db) == "wal"

    def test_converted_file_has_the_schema_of_a_new_file(
        self, old_db: Path, tmp_path: Path
    ) -> None:
        new_db = tmp_path / "new.db"
        init_database(str(new_db), PASSPHRASE)

        _open_and_close(old_db)

        def shape(db_path: Path) -> list[tuple[str, str, str]]:
            # Names and tables of every object (automatic indexes included)
            return sorted(
                (kind, name, table) for kind, name, table, _sql in read_master(db_path)
            )

        assert unique_index_columns(old_db) == NEW_KEY
        assert shape(old_db) == shape(new_db)
        assert unique_index_columns(old_db) == unique_index_columns(new_db)

    def test_converted_file_accepts_a_second_type(self, old_db: Path) -> None:
        with open_database(str(old_db), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            try:
                saved: Entity | None = repo.save(
                    Entity(
                        entity_type="ORG",
                        full_name="Zorbaville",
                        pseudonym_full="Zorbtech Group",
                        theme="neutral",
                    )
                )
            except DuplicateEntityError:
                saved = None
            types = sorted(
                e.entity_type for e in repo.find_all() if e.full_name == "Zorbaville"
            )
            stored_location = [
                e.pseudonym_full
                for e in repo.find_all()
                if e.full_name == "Zorbaville" and e.entity_type == "LOCATION"
            ]

        assert saved is not None, "ORG 'Zorbaville' rejected as a duplicate text"
        assert types == ["LOCATION", "ORG"]
        assert stored_location == ["Quentrel"]

    def test_second_open_changes_nothing(self, old_db: Path) -> None:
        _open_and_close(old_db)
        assert read_schema_version(old_db) == NEW_VERSION
        after_first = _snapshot(old_db)

        _open_and_close(old_db)

        assert _snapshot(old_db) == after_first

    def test_wrong_passphrase_converts_nothing(self, old_db: Path) -> None:
        before = _snapshot(old_db)

        with pytest.raises(ValueError, match="Incorrect passphrase"):
            open_database(str(old_db), WRONG_PASSPHRASE)

        assert _snapshot(old_db) == before
        assert read_schema_version(old_db) == OLD_VERSION


class TestFailedConversion:
    """A conversion that cannot be made leaves the whole file as it was."""

    def test_failure_after_old_table_dropped_rolls_back_everything(
        self, old_db: Path
    ) -> None:
        """PO B1: the failure comes after create, copy, drop and rename."""
        from gdpr_pseudonymizer.data import database
        from gdpr_pseudonymizer.exceptions import DatabaseConversionError

        before = _snapshot(old_db)
        seen: dict[str, Any] = {}

        def fail_inside_transaction(conn: sqlite3.Connection, version: str) -> None:
            seen["tables"] = sorted(
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            )
            seen["unique"] = sorted(
                [info[2] for info in conn.execute(f"PRAGMA index_info('{row[1]}')")]
                for row in conn.execute("PRAGMA index_list('entities')")
                if row[2] and row[3] != "pk"
            )
            seen["rows"] = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            raise RuntimeError("injected failure before COMMIT")

        with patch.object(
            database, "_write_schema_version", side_effect=fail_inside_transaction
        ):
            with pytest.raises(DatabaseConversionError) as caught:
                open_database(str(old_db), PASSPHRASE)

        # The injection ran after the old table was dropped and the new one renamed
        assert seen["tables"] == ["entities", "metadata", "operations"]
        assert seen["unique"] == NEW_KEY
        assert seen["rows"] == len(ROWS)
        # ... and the rollback restored everything
        assert old_db.exists()
        assert _snapshot(old_db) == before
        assert read_schema_version(old_db) == OLD_VERSION
        assert "unchanged" in str(caught.value)

        # The file then opens again and converts normally
        _open_and_close(old_db)
        assert read_schema_version(old_db) == NEW_VERSION
        assert unique_index_columns(old_db) == NEW_KEY
        assert read_entity_rows(old_db) == before[2]

    def test_read_only_file_stops_with_conversion_error(self, old_db: Path) -> None:
        from gdpr_pseudonymizer.exceptions import DatabaseConversionError

        bytes_before = old_db.read_bytes()
        _make_read_only(old_db)
        try:
            try:
                with open(old_db, "r+b"):
                    pass
            except OSError:
                pass
            else:
                pytest.skip("the file stays writable here (e.g. running as root)")

            with pytest.raises(DatabaseConversionError) as caught:
                open_database(str(old_db), PASSPHRASE)
        finally:
            _make_writable(old_db)

        message = str(caught.value)
        assert "could not be converted" in message
        assert "unchanged" in message
        assert "read-only" in message
        assert old_db.read_bytes() == bytes_before
        assert read_schema_version(old_db) == OLD_VERSION

    @pytest.mark.parametrize("case", ["new_version_old_key", "old_version_new_key"])
    def test_version_and_key_disagree_stops_and_changes_nothing(
        self, case: str, tmp_path: Path
    ) -> None:
        from gdpr_pseudonymizer.exceptions import DatabaseConversionError

        db_path = tmp_path / "mixed.db"
        if case == "new_version_old_key":
            build_pre_10_7_database(db_path, PASSPHRASE, ROWS)
            version = NEW_VERSION
        else:
            init_database(str(db_path), PASSPHRASE)
            version = OLD_VERSION
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE metadata SET value = ? WHERE \"key\" = 'schema_version'",
                (version,),
            )
            conn.commit()
        finally:
            conn.close()
        before = _snapshot(db_path)

        with pytest.raises(DatabaseConversionError) as caught:
            open_database(str(db_path), PASSPHRASE)

        assert "not recognised" in str(caught.value)
        assert _snapshot(db_path) == before
