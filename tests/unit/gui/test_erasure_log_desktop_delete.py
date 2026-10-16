"""Story 10.12: desktop deletion (AC2, Q2); invented names only.

Runs under the GUI conftest's autouse _isolate_gui_config fixture.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker


def _platform_sqlite_leaves_deleted_data_in_place() -> bool:
    with closing(sqlite3.connect(":memory:")) as connection:
        return connection.execute("PRAGMA secure_delete").fetchone()[0] == 0


PLATFORM_SQLITE_LEAVES_DELETED_DATA_IN_PLACE = (
    _platform_sqlite_leaves_deleted_data_in_place()
)
PASSPHRASE = "zorbalia_desktop_pass_123!"
P2_FULL_NAME = "Quentrelle Zébrandine"
P2_FIRST_NAME = "Quentrelle"
P2_LAST_NAME = "Zébrandine"


def _seed(db_path: Path) -> str:
    init_database(str(db_path), PASSPHRASE)
    with open_database(str(db_path), PASSPHRASE) as session:
        repository = SQLiteMappingRepository(session)
        repository.save(
            Entity(
                entity_type="PERSON",
                full_name="Zorbal Quentrix",
                first_name="Zorbal",
                last_name="Quentrix",
                pseudonym_full="Xantor Vellion",
                pseudonym_first="Xantor",
                pseudonym_last="Vellion",
                theme="neutral",
            )
        )
        p2 = repository.save(
            Entity(
                entity_type="PERSON",
                full_name=P2_FULL_NAME,
                first_name=P2_FIRST_NAME,
                last_name=P2_LAST_NAME,
                pseudonym_full="Orvane Telqui",
                pseudonym_first="Orvane",
                pseudonym_last="Telqui",
                theme="neutral",
            )
        )
        repository.save(
            Entity(
                entity_type="LOCATION",
                full_name="Zorbaville",
                pseudonym_full="Velmarque",
                theme="neutral",
            )
        )
        return p2.id


def _raw_database_bytes(db_path: Path) -> bytes:
    paths = (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm"))
    return b"".join(path.read_bytes() for path in paths if path.exists())


def _name_forms(db_path: Path) -> dict[str, bytes]:
    with closing(sqlite3.connect(str(db_path))) as connection:
        metadata = dict(
            connection.execute('SELECT "key", value FROM metadata').fetchall()
        )
    encryption = EncryptionService(
        PASSPHRASE,
        base64.b64decode(metadata["encryption_salt"]),
        int(metadata["kdf_iterations"]),
    )
    forms = {"utf8": P2_FULL_NAME.encode("utf-8")}
    escaped = json.dumps(P2_FULL_NAME)[1:-1]
    if escaped != P2_FULL_NAME:
        forms["escaped"] = escaped.encode("ascii")
    for label, value in (
        ("cipher_full", P2_FULL_NAME),
        ("cipher_first", P2_FIRST_NAME),
        ("cipher_last", P2_LAST_NAME),
    ):
        ciphertext = encryption.encrypt(value)
        assert ciphertext is not None, "PRE: ciphertext"
        forms[label] = ciphertext.encode("ascii")
    return forms


def _present_forms(raw: bytes, forms: dict[str, bytes]) -> dict[str, int]:
    return {label: raw.count(value) for label, value in forms.items() if value in raw}


def _read_erasure_rows(db_path: Path) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(str(db_path))) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM operations WHERE operation_type = 'ERASURE' ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


@pytest.mark.xfail(
    PLATFORM_SQLITE_LEAVES_DELETED_DATA_IN_PLACE,
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.12: reproduces desktop erased ciphertext in database bytes on "
        "the unfixed code where the platform SQLite leaves deleted data in place "
        "(Debian and Ubuntu build SQLite with SECURE_DELETE on, so the unfixed "
        "desktop deletion already overwrites deleted data there); fixed in Task 2"
    ),
)
def test_desktop_deletion_leaves_no_copy(tmp_path: Path, qtbot: QtBot) -> None:
    db_path = tmp_path / "mappings.db"
    p2_id = _seed(db_path)
    forms = _name_forms(db_path)
    ciphertexts = {
        label: value for label, value in forms.items() if label.startswith("cipher_")
    }
    before = _raw_database_bytes(db_path)
    assert len(ciphertexts) == 3, "PRE: ciphertext count"
    assert all(
        value in before for value in ciphertexts.values()
    ), f"PRE: ciphertexts {_present_forms(before, ciphertexts)}"
    finished: list[Any] = []
    errors: list[str] = []
    worker = DatabaseWorker("delete", str(db_path), PASSPHRASE, entity_ids=[p2_id])
    worker.signals.finished.connect(lambda result: finished.append(result))
    worker.signals.error.connect(lambda message: errors.append(message))

    worker.run()

    assert finished == [1], "PRE: finished"
    assert not errors, f"PRE: error {errors}"
    erasure_rows = _read_erasure_rows(db_path)
    assert len(erasure_rows) == 1, "PRE: ERASURE count"
    assert erasure_rows[0]["entity_count"] == 1, "PRE: entity_count"
    assert erasure_rows[0]["user_modifications"] is None, "PRE: user_modifications"
    after = _raw_database_bytes(db_path)

    assert not _present_forms(after, forms), _present_forms(after, forms)
