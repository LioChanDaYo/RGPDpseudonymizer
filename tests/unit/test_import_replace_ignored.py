"""Story 11.2: import replace ignored (T9-T13).

With ``gdpr-pseudo import-mappings <source> --no-skip-duplicates``, a yes to
"Replace existing mapping?" built a new row for a name the target already
held; the unique key refused it, the row was counted as skipped and the old
pseudonym stayed. The fix replaces the existing row's mapping, and the
summary counts it on a new "  Replaced: <n>" line (Lionel's Q-T1, option a).

Two databases are made by the real ``init`` command, with rows stored by
``SQLiteMappingRepository.save`` and fixed pseudonyms. The real
``import-mappings`` runs through ``CliRunner`` on ``gdpr_pseudonymizer.cli.main
.app``, with ``rich.prompt.Confirm.ask`` replaced; no user or project settings
file is read.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict expected-failure marker never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names only. No spaCy model, no Qt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rich.prompt import Confirm
from sqlalchemy import text
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DatabaseError

PASSPHRASE = "zorbalia_pass_A_123!"
ENV = {"GDPR_PSEUDO_PASSPHRASE": PASSPHRASE}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

NAME = "Xantor Velmar"


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test with "PRE: ..." (``pytest.fail``
    raises ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {message}")


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The commands read no user or project settings file."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)


@dataclass(frozen=True)
class _Row:
    """The stored row of (NAME, PERSON), as read from the database."""

    id: str
    first_seen: datetime
    pseudonym_full: str | None
    pseudonym_first: str | None
    pseudonym_last: str | None
    theme: str | None


def _init(path: Path) -> Path:
    """A new database made by the real ``init`` command."""
    result = CliRunner().invoke(
        app, ["init", "--db", str(path)], env=ENV, catch_exceptions=False
    )
    pre(result.exit_code == 0 and path.is_file(), f"init made {path.name}")
    return path


def _save(db: Path, pseudonym: str, first: str, last: str, theme: str) -> None:
    """(NAME, PERSON) stored with a fixed pseudonym and parts."""
    with open_database(str(db), PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type="PERSON",
                full_name=NAME,
                first_name="Xantor",
                last_name="Velmar",
                pseudonym_full=pseudonym,
                pseudonym_first=first,
                pseudonym_last=last,
                theme=theme,
            )
        )


def _rows(db: Path) -> list[_Row]:
    """Every stored row of (NAME, PERSON)."""
    with open_database(str(db), PASSPHRASE) as session:
        return [
            _Row(
                row.id,
                row.first_seen_timestamp,
                row.pseudonym_full,
                row.pseudonym_first,
                row.pseudonym_last,
                row.theme,
            )
            for row in SQLiteMappingRepository(session).find_all()
            if row.full_name == NAME and row.entity_type == "PERSON"
        ]


@dataclass
class _Import:
    """One ``import-mappings`` run: its exit code, its output without ANSI
    codes, the questions asked and the target's row before the run."""

    exit_code: int
    output: str
    asked: list[str]
    before: _Row


def _import(tmp_path: Path, answer: bool | None) -> _Import:
    """Source: (NAME, PERSON) → « Dravin Brontel » (Dravin, Brontel), theme
    ``custom``. Target: → « Morvane Vorlan » (Morvane, Vorlan), theme
    ``neutral``. ``answer`` is the reply to every question, with
    ``--no-skip-duplicates``; None runs with the default
    ``--skip-duplicates``."""
    source = _init(tmp_path / "source.db")
    target = _init(tmp_path / "target.db")
    _save(source, "Dravin Brontel", "Dravin", "Brontel", "custom")
    _save(target, "Morvane Vorlan", "Morvane", "Vorlan", "neutral")
    before = _rows(target)
    pre(len(before) == 1, "one target row before the import")
    asked: list[str] = []

    def ask(prompt: Any, *args: Any, **kwargs: Any) -> bool:
        asked.append(str(prompt))
        if answer is None:
            pytest.fail("PRE: no question with --skip-duplicates")
        return answer

    args = ["import-mappings", str(source), "--db", str(target)]
    if answer is not None:
        args.append("--no-skip-duplicates")
    with patch.object(Confirm, "ask", new=ask):
        result = CliRunner().invoke(app, args, env=ENV, catch_exceptions=False)
    return _Import(result.exit_code, _ANSI.sub("", result.output), asked, before[0])


def _summary(output: str) -> list[str]:
    """The lines of the summary after "Import Complete"."""
    lines = output.splitlines()
    pre("Import Complete" in lines, f"summary shown: {output!r}")
    return [
        line for line in lines[lines.index("Import Complete") + 1 :] if line.strip()
    ]


# ---------------------------------------------------------------------------
# Marked: a yes replaces, and is counted as replaced (T9, T10)
# ---------------------------------------------------------------------------


def test_replace_yes_updates_the_existing_row(tmp_path: Path) -> None:
    """T9 (AC3): a yes to "Replace existing mapping?" leaves exactly one
    target row for the name, with the source's pseudonym, parts and theme,
    and the target row's id and first-seen time."""
    run = _import(tmp_path, True)
    pre(run.exit_code == 0, f"import ran: {run.output!r}")
    pre(run.asked == ["Replace existing mapping?"], f"asked: {run.asked!r}")
    rows = _rows(tmp_path / "target.db")
    assert len(rows) == 1, rows
    (row,) = rows
    assert row.pseudonym_full == "Dravin Brontel", row  # expected failure
    assert (row.pseudonym_first, row.pseudonym_last) == ("Dravin", "Brontel"), row
    assert row.theme == "custom", row
    assert row.id == run.before.id, row
    assert row.first_seen == run.before.first_seen, row


def test_replace_yes_counted_as_replaced(tmp_path: Path) -> None:
    """T10 (AC4): the summary shows "  Imported: 0", "  Replaced: 1" and
    "  Skipped:  0", in that order."""
    run = _import(tmp_path, True)
    pre(run.exit_code == 0, f"import ran: {run.output!r}")
    assert _summary(run.output) == [  # expected failure
        "  Imported: 0",
        "  Replaced: 1",
        "  Skipped:  0",
    ], run.output


# ---------------------------------------------------------------------------
# Controls: a no and the default keep the row (T11, T12)
# ---------------------------------------------------------------------------


def test_replace_no_keeps_the_row(tmp_path: Path) -> None:
    """T11 (AC3, AC4, a control): a no keeps the row and counts it as
    skipped; no "Replaced:" line."""
    run = _import(tmp_path, False)
    pre(run.exit_code == 0, f"import ran: {run.output!r}")
    pre(run.asked == ["Replace existing mapping?"], f"asked: {run.asked!r}")
    assert _rows(tmp_path / "target.db") == [run.before]
    assert _summary(run.output) == ["  Imported: 0", "  Skipped:  1"], run.output
    assert "Replaced:" not in run.output


def test_default_skips_duplicates(tmp_path: Path) -> None:
    """T12 (AC3, AC4, a control): without ``--no-skip-duplicates`` no
    question is asked, the row is kept and counted as skipped; no
    "Replaced:" line."""
    run = _import(tmp_path, None)
    pre(run.exit_code == 0, f"import ran: {run.output!r}")
    assert run.asked == []
    assert _rows(tmp_path / "target.db") == [run.before]
    assert _summary(run.output) == ["  Imported: 0", "  Skipped:  1"], run.output
    assert "Replaced:" not in run.output


# ---------------------------------------------------------------------------
# The repository method (T13)
# ---------------------------------------------------------------------------


def _table(db: Path) -> list[tuple[Any, ...]]:
    """(id, encrypted full_name, first_seen_timestamp) of every row, read
    from the table itself."""
    with open_database(str(db), PASSPHRASE) as session:
        return [
            tuple(row)
            for row in session.session.execute(
                text("SELECT id, full_name, first_seen_timestamp FROM entities")
            )
        ]


def test_replace_mapping_keeps_id_name_and_first_seen(tmp_path: Path) -> None:
    """T13 (AC3, AC8): ``replace_mapping`` gives the stored row the other
    row's pseudonym and parts; the row keeps its id, its encrypted name
    (byte for byte) and its first-seen time; the lookup then finds the new
    pseudonym. A missing id raises ``DatabaseError`` with no name in it."""
    db = _init(tmp_path / "target.db")
    _save(db, "Morvane Vorlan", "Morvane", "Vorlan", "neutral")
    before = _table(db)
    pre(len(before) == 1, "one row stored")
    row_id, _, _ = before[0]
    source = Entity(
        entity_type="PERSON",
        full_name=NAME,
        first_name="Xantor",
        last_name="Velmar",
        pseudonym_full="Dravin Brontel",
        pseudonym_first="Dravin",
        pseudonym_last="Brontel",
        theme="custom",
    )
    with open_database(str(db), PASSPHRASE) as session:
        returned = SQLiteMappingRepository(session).replace_mapping(row_id, source)
        returned_values = (
            returned.id,
            returned.full_name,
            returned.pseudonym_full,
            returned.pseudonym_first,
            returned.pseudonym_last,
            returned.theme,
        )
    assert returned_values == (
        row_id,
        NAME,
        "Dravin Brontel",
        "Dravin",
        "Brontel",
        "custom",
    )
    assert _table(db) == before
    with open_database(str(db), PASSPHRASE) as session:
        found = SQLiteMappingRepository(session).find_by_full_name_and_type(
            NAME, "PERSON"
        )
        assert found is not None
        assert (found.pseudonym_full, found.pseudonym_first, found.pseudonym_last) == (
            "Dravin Brontel",
            "Dravin",
            "Brontel",
        )
    with open_database(str(db), PASSPHRASE) as session:
        with pytest.raises(DatabaseError) as raised:
            SQLiteMappingRepository(session).replace_mapping("no-such-id", source)
    message = str(raised.value)
    for word in ("Xantor", "Velmar", "Dravin", "Brontel", "Morvane", "Vorlan"):
        assert word not in message, message
