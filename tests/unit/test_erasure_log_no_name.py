"""Story 10.12: erasure entries, exports and file bytes (AC1, AC2, AC5, AC9).

Shared AC3 harness; invented names only (AC12).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from typing import Any, NamedTuple

import pytest
import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.delete_mapping import delete_mapping_command
from gdpr_pseudonymizer.cli.commands.export import export_command
from gdpr_pseudonymizer.data import database
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DatabaseConversionError

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "erasure_log"
FIXTURE_V2_2_0 = FIXTURE_DIR / "v2.2.0.db"
FIXTURE_MAIN_1F35DAE = FIXTURE_DIR / "1f35dae.db"
FIXTURE_PASSPHRASE = "zorbalia_pass_A_123!"
PASSPHRASE = "zorbalia_erasure_pass_123!"
THEME = "neutral"
REFERENCE_P1 = "REQ-2026-0042"
REFERENCE_P2 = "REQ-2026-0043"


class Person(NamedTuple):
    full_name: str
    first_name: str
    last_name: str
    pseudonym_full: str
    pseudonym_first: str
    pseudonym_last: str


P1 = Person(
    "Zorbal Quentrix",
    "Zorbal",
    "Quentrix",
    "Xantor Vellion",
    "Xantor",
    "Vellion",
)
P2 = Person(
    "Quentrelle Zébrandine",
    "Quentrelle",
    "Zébrandine",
    "Orvane Telqui",
    "Orvane",
    "Telqui",
)
L1 = ("Zorbaville", "Velmarque")


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="delete-mapping")(delete_mapping_command)
    app.command(name="export")(export_command)
    return app


app = create_test_app()
runner = CliRunner()


def _invoke(*args: str, passphrase: str = PASSPHRASE) -> tuple[int, str]:
    result = runner.invoke(app, [*args, "--passphrase", passphrase])
    return result.exit_code, strip_ansi(result.output)


def _seed(db_path: Path) -> dict[str, Entity]:
    init_database(str(db_path), PASSPHRASE)
    stored: dict[str, Entity] = {}
    with open_database(str(db_path), PASSPHRASE) as session:
        repository = SQLiteMappingRepository(session)
        for person in (P1, P2):
            stored[person.full_name] = repository.save(
                Entity(entity_type="PERSON", theme=THEME, **person._asdict())
            )
        stored[L1[0]] = repository.save(
            Entity(
                entity_type="LOCATION",
                full_name=L1[0],
                pseudonym_full=L1[1],
                theme=THEME,
            )
        )
    return stored


def _copy_fixture(fixture_path: Path, tmp_path: Path) -> Path:
    db_path = tmp_path / fixture_path.name
    shutil.copyfile(fixture_path, db_path)
    return db_path


def _read_operations(db_path: Path) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM operations ORDER BY id").fetchall()
        return [dict(row) for row in rows]


def _read_metadata(db_path: Path) -> dict[str, str]:
    with closing(sqlite3.connect(str(db_path))) as connection:
        return dict(connection.execute('SELECT "key", value FROM metadata').fetchall())


def _raw_database_bytes(db_path: Path) -> bytes:
    paths = (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm"))
    return b"".join(path.read_bytes() for path in paths if path.exists())


def _name_forms(
    db_path: Path, person: Person, passphrase: str = PASSPHRASE
) -> dict[str, bytes]:
    metadata = _read_metadata(db_path)
    encryption = EncryptionService(
        passphrase,
        base64.b64decode(metadata["encryption_salt"]),
        int(metadata["kdf_iterations"]),
    )
    forms = {"utf8": person.full_name.encode("utf-8")}
    escaped = json.dumps(person.full_name)[1:-1]
    if escaped != person.full_name:
        forms["escaped"] = escaped.encode("ascii")
    for label, value in (
        ("cipher_full", person.full_name),
        ("cipher_first", person.first_name),
        ("cipher_last", person.last_name),
    ):
        ciphertext = encryption.encrypt(value)
        assert ciphertext is not None, "PRE: ciphertext"
        forms[label] = ciphertext.encode("ascii")
    return forms


def _present_forms(raw: bytes, forms: dict[str, bytes]) -> dict[str, int]:
    return {label: raw.count(value) for label, value in forms.items() if value in raw}


def _open_and_close(db_path: Path, passphrase: str = PASSPHRASE) -> None:
    with open_database(str(db_path), passphrase):
        pass


def _stored_rows(
    db_path: Path, passphrase: str = PASSPHRASE
) -> list[tuple[str, str, str]]:
    with open_database(str(db_path), passphrase) as session:
        return sorted(
            (entity.full_name, entity.pseudonym_full, entity.entity_type)
            for entity in SQLiteMappingRepository(session).find_all()
        )


def _delete_p2(
    db_path: Path, entity_id: str, delete_by: str = "by_name"
) -> tuple[int, str]:
    selector = ["--id", entity_id[:8]] if delete_by == "by_id" else [P2.full_name]
    return _invoke(
        "delete-mapping",
        *selector,
        "--force",
        "--reason",
        REFERENCE_P2,
        "--db",
        str(db_path),
    )


@pytest.mark.parametrize("delete_by", ["by_name", "by_id"], ids=["by_name", "by_id"])
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces deleted_entity_name in erasure entry on the "
        "unfixed code; fixed in Task 2"
    ),
)
def test_new_erasure_entry_has_no_name(tmp_path: Path, delete_by: str) -> None:
    db_path = tmp_path / "mappings.db"
    stored = _seed(db_path)
    entity_id = stored[P2.full_name].id

    code, output = _delete_p2(db_path, entity_id, delete_by)

    assert code == 0, f"PRE: delete exit_code {code}: {output}"
    assert f"{P2.full_name} (PERSON)" in output, "PRE: entity output"
    operations = _read_operations(db_path)
    assert len(operations) == 1, "PRE: operation count"
    operation = operations[0]
    assert operation["operation_type"] == "ERASURE", "PRE: operation_type"
    modifications = json.loads(operation["user_modifications"])
    assert isinstance(modifications, dict), "PRE: user_modifications"

    assert set(modifications) == {"deleted_entity_id", "deleted_entity_type", "reason"}
    assert all(P2.full_name not in str(value) for value in modifications.values())
    assert modifications["deleted_entity_id"] == entity_id
    assert modifications["deleted_entity_type"] == "PERSON"
    assert modifications["reason"] == REFERENCE_P2
    assert operation["timestamp"]


@pytest.mark.parametrize("export_format", ["json", "csv"], ids=["json", "csv"])
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces erased name in audit export on the unfixed code; "
        "fixed in Task 2"
    ),
)
def test_export_holds_no_name(tmp_path: Path, export_format: str) -> None:
    db_path = tmp_path / "mappings.db"
    stored = _seed(db_path)
    entity_id = stored[P2.full_name].id
    forms = _name_forms(db_path, P2)
    code, output = _delete_p2(db_path, entity_id)
    assert code == 0, f"PRE: delete exit_code {code}: {output}"
    output_path = tmp_path / f"audit.{export_format}"

    code, output = _invoke("export", str(output_path), "--db", str(db_path))

    assert code == 0, f"PRE: export exit_code {code}: {output}"
    assert output_path.is_file(), "PRE: export file"
    exported = output_path.read_bytes()
    assert entity_id.encode("ascii") in exported, "PRE: exported entity_id"

    assert forms["utf8"] not in exported, _present_forms(exported, forms)
    assert forms["escaped"] not in exported, _present_forms(exported, forms)


@pytest.mark.parametrize("delete_by", ["by_name", "by_id"], ids=["by_name", "by_id"])
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces erased ciphertext in database bytes on the "
        "unfixed code; fixed in Task 2"
    ),
)
def test_deletion_leaves_no_copy_in_the_file(tmp_path: Path, delete_by: str) -> None:
    db_path = tmp_path / "mappings.db"
    stored = _seed(db_path)
    forms = _name_forms(db_path, P2)
    ciphertexts = {
        label: value for label, value in forms.items() if label.startswith("cipher_")
    }
    before = _raw_database_bytes(db_path)
    assert len(ciphertexts) == 3, "PRE: ciphertext count"
    assert all(
        value in before for value in ciphertexts.values()
    ), f"PRE: ciphertexts {_present_forms(before, ciphertexts)}"

    code, output = _delete_p2(db_path, stored[P2.full_name].id, delete_by)

    assert code == 0, f"PRE: delete exit_code {code}: {output}"
    after = _raw_database_bytes(db_path)

    assert not _present_forms(after, ciphertexts), _present_forms(after, ciphertexts)
    assert not _present_forms(after, forms), _present_forms(after, forms)
    assert _stored_rows(db_path) == sorted(
        [(P1.full_name, P1.pseudonym_full, "PERSON"), (*L1, "LOCATION")]
    )


def _read_erasure_rows(db_path: Path) -> list[dict[str, Any]]:
    return [
        row for row in _read_operations(db_path) if row["operation_type"] == "ERASURE"
    ]


def _erasure_names(db_path: Path) -> list[str]:
    names: list[str] = []
    for row in _read_erasure_rows(db_path):
        modifications = json.loads(row["user_modifications"])
        if "deleted_entity_name" in modifications:
            names.append(modifications["deleted_entity_name"])
    return names


def _assert_fixture_has_erased_names_and_copies(
    db_path: Path, schema_version: str
) -> dict[str, dict[str, bytes]]:
    assert (
        _read_metadata(db_path)["schema_version"] == schema_version
    ), "PRE: schema_version"
    assert sorted(_erasure_names(db_path)) == sorted(
        [P1.full_name, P2.full_name]
    ), "PRE: deleted_entity_name"
    forms = {
        person.full_name: _name_forms(db_path, person, FIXTURE_PASSPHRASE)
        for person in (P1, P2)
    }
    raw = _raw_database_bytes(db_path)
    for person_forms in forms.values():
        ciphertexts = {
            label: value
            for label, value in person_forms.items()
            if label.startswith("cipher_")
        }
        assert len(ciphertexts) == 3, "PRE: ciphertext count"
        assert all(
            value in raw for value in ciphertexts.values()
        ), f"PRE: ciphertexts {_present_forms(raw, ciphertexts)}"
    assert forms[P2.full_name]["escaped"] in raw, "PRE: escaped"
    return forms


@pytest.mark.parametrize(
    ("fixture_path", "schema_version"),
    [(FIXTURE_V2_2_0, "1.0.0"), (FIXTURE_MAIN_1F35DAE, "1.1.0")],
    ids=["v2_2_0", "main_1f35dae"],
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces erased names in old database bytes on the "
        "unfixed code; fixed in Task 2"
    ),
)
def test_old_file_first_open_removes_every_copy(
    tmp_path: Path, fixture_path: Path, schema_version: str
) -> None:
    db_path = _copy_fixture(fixture_path, tmp_path)
    forms = _assert_fixture_has_erased_names_and_copies(db_path, schema_version)
    operations_before = _read_erasure_rows(db_path)
    metadata_before = _read_metadata(db_path)

    _open_and_close(db_path, FIXTURE_PASSPHRASE)

    after = _raw_database_bytes(db_path)
    remaining = {name: _present_forms(after, values) for name, values in forms.items()}
    assert not any(remaining.values()), remaining
    operations_after = _read_erasure_rows(db_path)
    assert len(operations_after) == len(operations_before)
    for before_row, after_row in zip(operations_before, operations_after):
        assert json.loads(after_row["user_modifications"]) == {
            key: value
            for key, value in json.loads(before_row["user_modifications"]).items()
            if key != "deleted_entity_name"
        }
        assert {
            key: value
            for key, value in after_row.items()
            if key != "user_modifications"
        } == {
            key: value
            for key, value in before_row.items()
            if key != "user_modifications"
        }
    metadata_after = _read_metadata(db_path)
    assert metadata_after == {**metadata_before, "schema_version": "1.1.0"}
    assert "erasure_log_compaction_due" not in metadata_after
    assert _stored_rows(db_path, FIXTURE_PASSPHRASE) == [(*L1, "LOCATION")]
    for export_format in ("json", "csv"):
        output_path = tmp_path / f"audit.{export_format}"
        code, output = _invoke(
            "export",
            str(output_path),
            "--db",
            str(db_path),
            passphrase=FIXTURE_PASSPHRASE,
        )
        assert code == 0, f"PRE: export exit_code {code}: {output}"
        assert output_path.is_file(), "PRE: export file"
        exported = output_path.read_bytes()
        for person_forms in forms.values():
            assert not _present_forms(exported, person_forms), _present_forms(
                exported, person_forms
            )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces erased ciphertext without log names on the "
        "unfixed code; fixed in Task 2"
    ),
)
def test_first_open_compacts_even_without_names(tmp_path: Path) -> None:
    db_path = _copy_fixture(FIXTURE_MAIN_1F35DAE, tmp_path)
    forms = _assert_fixture_has_erased_names_and_copies(db_path, "1.1.0")
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.execute(
            "UPDATE operations SET user_modifications = "
            "json_remove(user_modifications, '$.deleted_entity_name') "
            "WHERE operation_type = 'ERASURE'"
        )
        connection.commit()
    assert not _erasure_names(db_path), "PRE: deleted_entity_name"
    ciphertexts = {
        label: value
        for label, value in forms[P2.full_name].items()
        if label.startswith("cipher_")
    }
    before = _raw_database_bytes(db_path)
    assert all(
        value in before for value in ciphertexts.values()
    ), f"PRE: ciphertexts {_present_forms(before, ciphertexts)}"

    _open_and_close(db_path, FIXTURE_PASSPHRASE)

    after = _raw_database_bytes(db_path)
    assert not _present_forms(after, ciphertexts), _present_forms(after, ciphertexts)


def test_second_open_changes_nothing(tmp_path: Path) -> None:
    from hashlib import sha256

    db_path = _copy_fixture(FIXTURE_V2_2_0, tmp_path)
    assert db_path.is_file(), "PRE: fixture file"
    _open_and_close(db_path, FIXTURE_PASSPHRASE)
    digest_before = sha256(db_path.read_bytes()).hexdigest()
    listing_before = sorted(path.name for path in tmp_path.iterdir())

    _open_and_close(db_path, FIXTURE_PASSPHRASE)

    assert sha256(db_path.read_bytes()).hexdigest() == digest_before
    assert sorted(path.name for path in tmp_path.iterdir()) == listing_before


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces missing compaction due marker on the unfixed "
        "code; fixed in Task 2"
    ),
)
def test_reader_held_open_leaves_compaction_due_then_next_open_completes(
    tmp_path: Path,
) -> None:
    db_path = _copy_fixture(FIXTURE_V2_2_0, tmp_path)
    forms = _assert_fixture_has_erased_names_and_copies(db_path, "1.0.0")
    reader = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM operations").fetchall()
        assert reader.in_transaction, "PRE: reader transaction"

        _open_and_close(db_path, FIXTURE_PASSPHRASE)

        assert "erasure_log_compaction_due" in _read_metadata(db_path)
        assert not _erasure_names(db_path)
    finally:
        reader.close()

    assert "erasure_log_compaction_due" in _read_metadata(
        db_path
    ), "PRE: erasure_log_compaction_due"
    _open_and_close(db_path, FIXTURE_PASSPHRASE)

    assert "erasure_log_compaction_due" not in _read_metadata(db_path)
    after = _raw_database_bytes(db_path)
    for person_forms in forms.values():
        assert not _present_forms(after, person_forms), _present_forms(
            after, person_forms
        )


@pytest.mark.parametrize(
    "fixture_path",
    [FIXTURE_V2_2_0, FIXTURE_MAIN_1F35DAE],
    ids=["v2_2_0", "main_1f35dae"],
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces open after failed name removal on the unfixed "
        "code; fixed in Task 2"
    ),
)
def test_failed_removal_stops_the_open(tmp_path: Path, fixture_path: Path) -> None:
    db_path = _copy_fixture(fixture_path, tmp_path)
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.execute(
            "CREATE TRIGGER zorbal_block BEFORE UPDATE ON operations "
            "BEGIN SELECT RAISE(ABORT, 'zorbal'); END"
        )
        connection.commit()
    assert sorted(_erasure_names(db_path)) == sorted(
        [P1.full_name, P2.full_name]
    ), "PRE: deleted_entity_name"
    rows_before = _read_erasure_rows(db_path)

    raised: Exception | None = None
    try:
        _open_and_close(db_path, FIXTURE_PASSPHRASE)
    except Exception as exc:
        raised = exc

    assert isinstance(raised, DatabaseConversionError)
    error_text = str(raised)
    assert error_text
    assert all(person.full_name not in error_text for person in (P1, P2))
    assert "one row per name and type" not in error_text
    assert _read_erasure_rows(db_path) == rows_before
    assert _read_metadata(db_path)["schema_version"] == "1.1.0"
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.execute("DROP TRIGGER zorbal_block")
        connection.commit()

    _open_and_close(db_path, FIXTURE_PASSPHRASE)

    assert not _erasure_names(db_path)


class _DatabaseLogRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def debug(self, event: str, **kwargs: Any) -> None:
        self.events.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.events.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.events.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.events.append(("error", event, kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self.events.append(("exception", event, kwargs))


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces names retained beside malformed JSON on the "
        "unfixed code; fixed in Task 2"
    ),
)
def test_malformed_entry_is_skipped_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = _copy_fixture(FIXTURE_V2_2_0, tmp_path)
    assert sorted(_erasure_names(db_path)) == sorted(
        [P1.full_name, P2.full_name]
    ), "PRE: deleted_entity_name"
    valid_rows_before = _read_erasure_rows(db_path)
    assert len(valid_rows_before) == 2, "PRE: valid ERASURE count"
    malformed_json = json.dumps({"deleted_entity_name": "Velmor Quandrix"})[:-1]
    malformed_row = {
        **valid_rows_before[0],
        "id": "zorbal-bad",
        "user_modifications": malformed_json,
    }
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.execute(
            "INSERT INTO operations (id, timestamp, operation_type, files_processed, "
            "user_modifications, model_name, model_version, theme_selected, "
            "entity_count, processing_time_seconds, success, error_message) "
            "VALUES (:id, :timestamp, :operation_type, :files_processed, "
            ":user_modifications, :model_name, :model_version, :theme_selected, "
            ":entity_count, :processing_time_seconds, :success, :error_message)",
            malformed_row,
        )
        connection.commit()
        json_valid = connection.execute(
            "SELECT json_valid(user_modifications) FROM operations WHERE id = ?",
            ("zorbal-bad",),
        ).fetchone()
        assert json_valid == (0,), "PRE: malformed JSON"
    malformed_rows_before = [
        row for row in _read_erasure_rows(db_path) if row["id"] == "zorbal-bad"
    ]
    assert malformed_rows_before == [malformed_row], "PRE: malformed ERASURE row"
    recorder = _DatabaseLogRecorder()
    monkeypatch.setattr(database, "logger", recorder)

    _open_and_close(db_path, FIXTURE_PASSPHRASE)

    rows_after = {row["id"]: row for row in _read_erasure_rows(db_path)}
    valid_modifications = [
        json.loads(rows_after[row["id"]]["user_modifications"])
        for row in valid_rows_before
    ]
    assert all("deleted_entity_name" not in entry for entry in valid_modifications)
    assert rows_after["zorbal-bad"] == malformed_row
    cleaned_events = [
        kwargs for _, event, kwargs in recorder.events if event == "erasure_log_cleaned"
    ]
    assert len(cleaned_events) == 1
    assert cleaned_events[0]["skipped"] == 1
    entity_texts = (
        P1.full_name,
        P2.full_name,
        "Velmor Quandrix",
        P1.first_name,
        P1.last_name,
        P2.first_name,
        P2.last_name,
        "Velmor",
        "Quandrix",
    )
    assert all(
        text not in str(value)
        for _, event, kwargs in recorder.events
        for value in (event, *kwargs.values())
        for text in entity_texts
    )


def test_new_file_needs_neither_step(tmp_path: Path) -> None:
    db_path = tmp_path / "mappings.db"
    init_database(str(db_path), PASSPHRASE)
    assert db_path.is_file(), "PRE: database file"
    digest_before = hashlib.sha256(db_path.read_bytes()).hexdigest()

    _open_and_close(db_path)

    assert hashlib.sha256(db_path.read_bytes()).hexdigest() == digest_before
    assert "erasure_log_compaction_due" not in _read_metadata(db_path)


def test_read_only_file_without_names_opens(tmp_path: Path) -> None:
    db_path = _copy_fixture(FIXTURE_MAIN_1F35DAE, tmp_path)
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.execute(
            "UPDATE operations SET user_modifications = "
            "json_remove(user_modifications, '$.deleted_entity_name') "
            "WHERE operation_type = 'ERASURE'"
        )
        connection.commit()
    assert not _erasure_names(db_path), "PRE: deleted_entity_name"
    digest_before = hashlib.sha256(db_path.read_bytes()).hexdigest()
    db_path.chmod(stat.S_IREAD)
    try:
        if os.access(db_path, os.W_OK):
            pytest.skip("writable")
        raised: Exception | None = None
        try:
            _open_and_close(db_path, FIXTURE_PASSPHRASE)
        except Exception as exc:
            raised = exc

        assert raised is None, raised
        assert hashlib.sha256(db_path.read_bytes()).hexdigest() == digest_before
        assert "erasure_log_compaction_due" not in _read_metadata(db_path)
    finally:
        db_path.chmod(stat.S_IREAD | stat.S_IWRITE)
