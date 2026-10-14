"""Story 10.7, AC3: CLI commands on a pre-10.7 database (rule (a)).

Any open converts the file: a read-only command converts it and shows the
same output; ``batch`` converts it once, before any worker starts, and stops
before any document when the conversion cannot be made; ``destroy-table``
shows the conversion error, not "wrong passphrase". Driven through the CLI
runner. Invented names only (AC11).
"""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.batch import BatchResult, batch_command
from gdpr_pseudonymizer.cli.commands.destroy_table import destroy_table_command
from gdpr_pseudonymizer.cli.commands.list_entities import list_entities_command
from tests.unit.pre_10_7_database import (
    LegacyRow,
    build_pre_10_7_database,
    read_schema_version,
    unique_index_columns,
)

PASSPHRASE = "zorbalia_cmd_pass_123!"
ROWS = (
    LegacyRow("LOCATION", "Zorbaville", "Quentrel"),
    LegacyRow("ORG", "Zorbtech", "Quentrix Holding"),
)


def _app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="list-entities")(list_entities_command)
    app.command(name="destroy-table")(destroy_table_command)
    app.command(name="batch")(batch_command)
    return app


app = _app()
runner = CliRunner()


@pytest.fixture()
def old_db(tmp_path: Path) -> Path:
    path = tmp_path / "pre_10_7.db"
    build_pre_10_7_database(path, PASSPHRASE, ROWS)
    return path


def _make_read_only_or_skip(db_path: Path) -> None:
    db_path.chmod(stat.S_IREAD)
    try:
        with open(db_path, "r+b"):
            pass
    except OSError:
        return
    db_path.chmod(stat.S_IREAD | stat.S_IWRITE)
    pytest.skip("the file stays writable here (e.g. running as root)")


def _make_writable(db_path: Path) -> None:
    db_path.chmod(stat.S_IREAD | stat.S_IWRITE)


def test_list_entities_converts_and_lists_as_before(old_db: Path) -> None:
    result = runner.invoke(
        app, ["list-entities", "--db", str(old_db), "--passphrase", PASSPHRASE]
    )
    output = strip_ansi(result.output)

    assert result.exit_code == 0, output
    for expected in ("Zorbaville", "LOCATION", "Quentrel", "Zorbtech", "ORG"):
        assert expected in output
    assert read_schema_version(old_db) == "1.1.0"
    assert unique_index_columns(old_db) == [["full_name", "entity_type"]]


def test_destroy_table_shows_the_conversion_error(old_db: Path) -> None:
    bytes_before = old_db.read_bytes()
    _make_read_only_or_skip(old_db)
    try:
        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(old_db), "--passphrase", PASSPHRASE],
            input="no\n",
        )
    finally:
        _make_writable(old_db)
    output = strip_ansi(result.output)

    assert result.exit_code != 0, output
    assert "could not be converted" in output
    assert "Could not verify database with provided passphrase" not in output
    assert old_db.exists()
    assert old_db.read_bytes() == bytes_before


def _batch_inputs(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "zorbaville.txt").write_text("Zorbaville et Zorbtech.", encoding="utf-8")
    return docs


def _invoke_batch(docs: Path, db_path: Path) -> tuple[int, str]:
    result = runner.invoke(
        app,
        [
            "batch",
            str(docs),
            "--db",
            str(db_path),
            "--passphrase",
            PASSPHRASE,
            "--workers",
            "2",
        ],
    )
    return result.exit_code, strip_ansi(result.output)


def test_batch_converts_once_before_the_workers(old_db: Path, tmp_path: Path) -> None:
    docs = _batch_inputs(tmp_path)
    seen: dict[str, Any] = {}

    def fake_parallel(**kwargs: Any) -> BatchResult:
        # The pool would start here: the file must already be converted
        seen["version"] = read_schema_version(Path(kwargs["db_path"]))
        seen["files"] = len(kwargs["files"])
        return BatchResult(total_files=1, successful_files=1)

    with (
        patch("gdpr_pseudonymizer.cli.commands.batch.cpu_count", return_value=4),
        patch(
            "gdpr_pseudonymizer.cli.commands.batch._process_batch_parallel",
            side_effect=fake_parallel,
        ),
    ):
        code, output = _invoke_batch(docs, old_db)

    assert code == 0, output
    assert seen == {"version": "1.1.0", "files": 1}


def test_batch_stops_before_any_document_when_conversion_fails(
    old_db: Path, tmp_path: Path
) -> None:
    docs = _batch_inputs(tmp_path)
    bytes_before = old_db.read_bytes()
    calls: list[Any] = []

    _make_read_only_or_skip(old_db)
    try:
        with (
            patch("gdpr_pseudonymizer.cli.commands.batch.cpu_count", return_value=4),
            patch(
                "gdpr_pseudonymizer.cli.commands.batch._process_batch_parallel",
                side_effect=lambda **kwargs: calls.append(kwargs),
            ),
        ):
            code, output = _invoke_batch(docs, old_db)
    finally:
        _make_writable(old_db)

    assert calls == []
    assert code == 1, output
    assert "could not be converted" in output
    assert old_db.read_bytes() == bytes_before
    assert read_schema_version(old_db) == "1.0.0"
