"""Story 11.7: saved pseudonyms that hold a word of their own name (T1-T15,
T17, T19-T22; the core and the command line).

Written by the BMAD dev agent (Claude). A mapping database filled before
Story 11.6 can hold rows whose pseudonym holds a word of the very name it
stands for (« Zorbal Quentrix » saved as « Zorbal Brontel »). The rows are
saved directly with ``SQLiteMappingRepository.save`` (theme ``neutral``), as
2.3.0 could have saved them. ``validate-mappings --own-words`` finds them,
``replace-pseudonym`` replaces them, every row that shares the replaced
part moving with them, and a note is printed when a document is written
while the database holds them.

Every marked case reaches the new code through an entry point that exists
on the base: the command line through ``CliRunner`` (an unknown option or
command exits 2), the core module after ``find_spec`` and ``getattr``
asserts. Detection is replaced by a stand-in that finds the names given; the
library's draw is forced with Story 11.6's ``_forced`` where a test needs
one value. No spaCy model, no Qt.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict ``xfail(raises=AssertionError)`` never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). The tests assert a few fixed words of each text,
never whole sentences. Invented names and main-corpus words only.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sqlite3
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
import readchar
from rich.console import Console, ConsoleDimensions
from rich.prompt import Confirm, Prompt
from typer.testing import CliRunner

import gdpr_pseudonymizer.core.document_processor as processor_module
from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.core.custom_pseudonym import fold
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.validation.workflow import ADD_MISSED_NAME_QUESTION
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _new_db,
    _words,
    pre,
)
from tests.unit.test_generated_pseudonym_document_words import _forced
from tests.unit.test_parallel_saved_pseudonym import (
    WAIT,
    _desktop,
    _found,
    _LockHolder,
    _Recorder,
    _settings,  # noqa: F401 (autouse: no settings file read or written)
    _write_lock_held,
    _written,
)

_FIRST = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 11.7 tests first: saved pseudonyms that hold a word of their own name",
)

PERSON, LOCATION, ORG = "PERSON", "LOCATION", "ORG"
CORE = "gdpr_pseudonymizer.core.saved_own_words"
COMMAND = "gdpr_pseudonymizer.cli.commands.replace_pseudonym"

ZQ = "Zorbal Quentrix"
ZM = "Zorbal Mestrix"
ZD = "Zorbal Dorvane"
XB = "Xantor Brontel"
QD = "Quilla Dorn"

# (type, name, pseudonym, first name, last name, pseudonym's first part,
# pseudonym's last part)
Row = tuple[str, str, str, str | None, str | None, str | None, str | None]

# T4's rows: one real first name « Zorbal » whose part is « Zorbal », in two
# full names and alone (a lone first name: its word in ``first_name``, its
# part in ``pseudonym_first``, as the engine saves it), and a clean row.
ZQ_ROW: Row = (PERSON, ZQ, "Zorbal Brontel", "Zorbal", "Quentrix", "Zorbal", "Brontel")
ZM_ROW: Row = (PERSON, ZM, "Zorbal Vellion", "Zorbal", "Mestrix", "Zorbal", "Vellion")
LONE_ROW: Row = (PERSON, "Zorbal", "Zorbal", "Zorbal", None, "Zorbal", None)
QD_ROW: Row = (PERSON, QD, "Pivel Xantor", "Quilla", "Dorn", "Pivel", "Xantor")
T4_ROWS = [ZQ_ROW, ZM_ROW, LONE_ROW, QD_ROW]

# T5's rows: « Xantor Brontel »'s last part is its own first name; the real
# last name Brontel's part « Xantor » is shared by a clean row.
XB_ROW: Row = (PERSON, XB, "Pivel Xantor", "Xantor", "Brontel", "Pivel", "Xantor")
ZB_ROW: Row = (
    PERSON,
    "Zorbal Brontel",
    "Quilla Xantor",
    "Zorbal",
    "Brontel",
    "Quilla",
    "Xantor",
)

# T1's cases: (row, word found, reported)
T1_CASES: dict[str, tuple[Row, str, bool]] = {
    "first_part": (ZQ_ROW, "Zorbal", True),
    "last_part_is_own_first_name": (XB_ROW, "Xantor", True),
    "lone_name": (LONE_ROW, "Zorbal", True),
    "place": (
        (LOCATION, "Zorbaville", "Zorbaville", None, None, None, None),
        "Zorbaville",
        True,
    ),
    "org_place_word": (
        (ORG, "Mairie de Zorbaville", "Groupe Zorbaville", None, None, None, None),
        "Zorbaville",
        True,
    ),
    "org_common_word": (
        (ORG, "Groupe Zorbaville", "Groupe Pivelle", None, None, None, None),
        "Groupe",
        False,
    ),
}
T1_ROWS = [row for row, _, _ in T1_CASES.values()]

# « Zorbaville » is one of the library's cities (an invented name is no
# library place; a place word is reported only when it is one)
ZORBAVILLE_A_CITY: dict[str, Sequence[str]] = {"place": ["Zorbaville"]}

DOC_QD = f"{QD} a signé le contrat."
LATER_DOC = (
    f"{ZQ} a signé le contrat. Zorbal a signé le contrat. {ZD} a signé le contrat."
)

# Fixed words of the approved texts (Dev Notes "Exact texts"), never whole
# sentences: C6, C12, C13, C15, C17c, C17f, C17g, C18
NONE_FOUND = "No pseudonym holds a word of its own name"
SECOND_HEADING = "will change too"
WARNING_START = "Documents already written"
CANCELLED = "Replacement cancelled"
NOT_FOUND = "Nothing to Replace"
NO_FREE = "No Free Pseudonym"
CHOSEN = "Chosen Pseudonym"
NOTICE = "saved pseudonym"
NOTICE_SEE = "validate-mappings --own-words"

ENV = {"GDPR_PSEUDO_PASSPHRASE": PASSPHRASE}
# Every Rich console of the command line is created at import, and one
# created while COLUMNS is set keeps that width (so an environment that sets
# it, as the Linux CI runners did, cut the table at 80 columns): every
# console reads this size while a command runs, whatever the OS
_WIDE = ConsoleDimensions(400, 100)
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_PERSON_FALLBACK = re.compile(r"^Person-\d+$")


# ---------------------------------------------------------------------------
# Saved rows
# ---------------------------------------------------------------------------


def _entity(row: Row, theme: str) -> Entity:
    entity_type, name, pseudonym, first, last, part_first, part_last = row
    return Entity(
        entity_type=entity_type,
        full_name=name,
        pseudonym_full=pseudonym,
        first_name=first,
        last_name=last,
        pseudonym_first=part_first,
        pseudonym_last=part_last,
        theme=theme,
    )


def _save(db: str, rows: Sequence[Row], theme: str = "neutral") -> dict[str, str]:
    """Save the rows as 2.3.0 could have saved them; their ids by name."""
    with open_database(db, PASSPHRASE) as session:
        repo = SQLiteMappingRepository(session)
        return {row[1]: repo.save(_entity(row, theme)).id for row in rows}


def _db(folder: Path, rows: Sequence[Row]) -> tuple[str, dict[str, str]]:
    folder.mkdir(parents=True, exist_ok=True)
    db = _new_db(folder)
    return db, _save(db, rows)


def _by_name(db: str) -> dict[str, Entity]:
    with open_database(db, PASSPHRASE) as session:
        rows = SQLiteMappingRepository(session).find_all()
    by_name = {row.full_name: row for row in rows}
    pre(len(by_name) == len(rows), "one row per name in these databases")
    return by_name


def _snapshot(db: str) -> dict[str, tuple[Any, ...]]:
    """Every field of every saved row, by id."""
    with open_database(db, PASSPHRASE) as session:
        rows = SQLiteMappingRepository(session).find_all()
    return {
        row.id: (
            row.entity_type,
            row.full_name,
            row.first_name,
            row.last_name,
            row.pseudonym_full,
            row.pseudonym_first,
            row.pseudonym_last,
            row.theme,
            row.gender,
            row.confidence_score,
            row.first_seen_timestamp,
            row.is_ambiguous,
            row.ambiguity_reason,
        )
        for row in rows
    }


def _kept(snapshot: tuple[Any, ...]) -> tuple[Any, ...]:
    """A row's fields other than its three pseudonym fields."""
    return snapshot[:4] + snapshot[7:]


def _tables(db: str) -> dict[str, list[tuple[Any, ...]]]:
    """The raw rows of the entities, operations and metadata tables."""
    with closing(sqlite3.connect(db)) as connection:
        return {
            table: sorted(
                connection.execute(f"SELECT * FROM {table}").fetchall(), key=repr
            )
            for table in ("entities", "operations", "metadata")
        }


def _replacements_logged(db: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(db)) as connection:
        return connection.execute(
            "SELECT * FROM operations WHERE operation_type = 'REPLACEMENT'"
        ).fetchall()


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


def _cli(*args: str, typed: str | None = None) -> tuple[int, str]:
    """One ``gdpr-pseudo`` run: its exit code and what it shows, every
    console 400 columns wide."""
    with patch.object(Console, "size", new_callable=PropertyMock) as size:
        size.return_value = _WIDE
        result = CliRunner().invoke(app, list(args), env=ENV, input=typed)
    return result.exit_code, _ANSI.sub("", result.output)


def _flat(text: str) -> str:
    return " ".join(text.split())


def _own_words(db: str) -> tuple[int, str]:
    return _cli("validate-mappings", "--db", db, "--own-words")


def _validate(db: str) -> tuple[int, str]:
    return _cli("validate-mappings", "--db", db)


def _replace(db: str, *args: str, typed: str | None = None) -> tuple[int, str]:
    return _cli("replace-pseudonym", "--db", db, *args, typed=typed)


class _Keys:
    """``readchar.readkey`` in the review: Space (confirm) every time."""

    def __init__(self) -> None:
        self.read = 0

    def __call__(self) -> str:
        self.read += 1
        if self.read > 60:
            raise RuntimeError("more than 60 keys read")
        return " "


def _answers(prompt: Any, *args: Any, **kwargs: Any) -> bool:
    """``Confirm.ask``: no to Story 10.18's question, yes otherwise."""
    return str(prompt) != ADD_MISSED_NAME_QUESTION


def _no_typing(prompt: Any, *args: Any, **kwargs: Any) -> str:
    raise RuntimeError(f"no typed text expected: {prompt!r}")


@contextmanager
def _documents(names: list[tuple[str, str]]) -> Iterator[None]:
    """Detection finds the names given; the review confirms each one."""
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                DocumentProcessor,
                "_detect_and_filter_entities",
                lambda self, text, entity_type_filter=None: _found(text, names),
            )
        )
        stack.enter_context(patch.object(readchar, "readkey", _Keys()))
        stack.enter_context(patch.object(Confirm, "ask", _answers))
        stack.enter_context(patch.object(Prompt, "ask", _no_typing))
        yield


def _process(
    folder: Path, db: str, text: str, names: list[tuple[str, str]], tag: str
) -> tuple[int, str]:
    """One ``gdpr-pseudo process`` run of ``text``."""
    source = folder / f"{tag}.txt"
    source.write_text(text, encoding="utf-8")
    output = folder / f"{tag}_out.txt"
    with _documents(names):
        return _cli("process", str(source), "--db", db, "-o", str(output))


class _InProcessPool:
    """``multiprocessing.Pool`` run in this process, so that the detection
    stand-in reaches the workers (PO, v1.4)."""

    def __init__(self, processes: int | None = None) -> None:
        self.processes = processes

    def __enter__(self) -> _InProcessPool:
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def imap_unordered(self, func: Any, items: Any) -> Iterator[Any]:
        return map(func, items)


def _batch(
    folder: Path, db: str, texts: list[str], names: list[tuple[str, str]], tag: str
) -> tuple[int, str]:
    """One ``gdpr-pseudo batch --workers 2`` run (the parallel path)."""
    source = folder / tag
    source.mkdir()
    for index, text in enumerate(texts):
        (source / f"doc{index}.txt").write_text(text, encoding="utf-8")
    with (
        _documents(names),
        patch("gdpr_pseudonymizer.cli.commands.batch.cpu_count", return_value=4),
        patch("gdpr_pseudonymizer.cli.commands.batch.Pool", _InProcessPool),
    ):
        return _cli(
            "batch",
            str(source),
            "--db",
            db,
            "--workers",
            "2",
            "-o",
            str(folder / f"{tag}_out"),
        )


def _line_of(output: str, text: str) -> str:
    """The one line of ``output`` that holds ``text``."""
    lines = [line for line in output.splitlines() if text in line]
    pre(len(lines) == 1, f"one line holds {text!r}: {output!r}")
    return lines[0]


# ---------------------------------------------------------------------------
# The check (T1-T3, T15)
# ---------------------------------------------------------------------------


@_FIRST
@pytest.mark.parametrize("case", list(T1_CASES))
def test_own_word_row_is_reported(tmp_path: Path, case: str) -> None:
    """T1 (AC1, AC2, AC10): one saved row each. `--own-words` lists it with
    its ID and the word found; `validate-mappings` flags it `OWN`. An
    organisation that shares only a common word is not reported (Lionel,
    "report only real leaks")."""
    row, word, reported = T1_CASES[case]
    db, ids = _db(tmp_path, [row])
    short_id = ids[row[1]][:8]
    with _forced(ZORBAVILLE_A_CITY):
        code, shown = _own_words(db)
        assert code == 0, (code, shown)  # expected failure
        table_code, table = _validate(db)
    assert table_code == 0, table
    if reported:
        line = _line_of(shown, short_id)
        assert row[1] in line and word in line, line
        assert "replace-pseudonym" in _flat(shown)
        assert "OWN" in table
    else:
        assert short_id not in shown
        assert NONE_FOUND in _flat(shown)
        assert "OWN" not in table


@_FIRST
def test_clean_rows_are_not_reported(tmp_path: Path) -> None:
    """T2 (AC1, AC2): rows that hold no word of their own name, « Le » not
    compared alone, a custom row and a ``neutral_id`` row: `--own-words`
    prints its "none" line and exits 0."""
    db, _ = _db(
        tmp_path,
        [
            (PERSON, ZQ, "Xantor Brontel", "Zorbal", "Quentrix", "Xantor", "Brontel"),
            (LOCATION, "Zorbaville", "Pivelle", None, None, None, None),
            (LOCATION, "Le Vellion", "Le Brontel", None, None, None, None),
        ],
    )
    # A custom pseudonym (Story 10.16 refuses one that holds its own name's
    # word, so the check skips the theme) and an identifier
    _save(
        db,
        [
            (
                PERSON,
                "Tobrek Lanvis",
                "Tobrek Fendra",
                "Tobrek",
                "Lanvis",
                "Tobrek",
                "Fendra",
            )
        ],
        "custom",
    )
    _save(db, [(PERSON, QD, "PER-001", "Quilla", "Dorn", None, None)], "neutral_id")
    code, shown = _own_words(db)
    assert code == 0, (code, shown)  # expected failure
    assert NONE_FOUND in _flat(shown)
    table_code, table = _validate(db)
    assert table_code == 0 and "OWN" not in table, table


@_FIRST
def test_check_is_read_only(tmp_path: Path) -> None:
    """T3 (AC1): `--own-words` changes no row, no audit entry and no
    metadata."""
    db, _ = _db(tmp_path, T1_ROWS)
    before = _tables(db)
    with _forced(ZORBAVILLE_A_CITY):
        plain_code, plain = _validate(db)
        pre(plain_code == 0, f"validate-mappings ran: {plain!r}")
        pre(_tables(db) == before, "validate-mappings writes nothing (the base)")
        code, shown = _own_words(db)
    assert code == 0, (code, shown)  # expected failure
    assert _tables(db) == before


def test_validate_mappings_unchanged_without_leak(tmp_path: Path) -> None:
    """T15 (AC2, control): without a row found, `validate-mappings` prints
    what it prints on the base: every row `OK`, the same summary."""
    db, _ = _db(
        tmp_path,
        [
            (PERSON, ZQ, "Xantor Brontel", "Zorbal", "Quentrix", "Xantor", "Brontel"),
            (LOCATION, "Zorbaville", "Pivelle", None, None, None, None),
        ],
    )
    code, shown = _validate(db)
    assert code == 0, shown
    assert "OWN" not in shown
    assert shown.count("OK") == 2, shown
    summary = shown.split("Summary:", 1)[1]
    assert [line.strip() for line in summary.splitlines() if line.strip()] == [
        "• Total mappings: 2"
    ]


# ---------------------------------------------------------------------------
# The replacement (T4-T10, T14, T19, T22)
# ---------------------------------------------------------------------------


@_FIRST
def test_replace_moves_the_whole_group(tmp_path: Path) -> None:
    """T4 (AC4, AC6): replacing « Zorbal Quentrix » gives the three rows of
    the real first name Zorbal one new first part; last parts, ids, names
    and themes are kept; the clean row does not change."""
    db, ids = _db(tmp_path, T4_ROWS)
    before = _snapshot(db)
    code, shown = _replace(db, "--id", ids[ZQ][:8], "--force")
    assert code == 0, (code, shown)  # expected failure
    after = _by_name(db)
    new = after[ZQ].pseudonym_first
    assert new and fold(new) != "zorbal", new
    assert after[ZM].pseudonym_first == new
    assert (after[ZQ].pseudonym_last, after[ZM].pseudonym_last) == (
        "Brontel",
        "Vellion",
    )
    assert after[ZQ].pseudonym_full == f"{new} Brontel"
    assert after[ZM].pseudonym_full == f"{new} Vellion"
    lone = after["Zorbal"]
    assert (lone.pseudonym_full, lone.pseudonym_first, lone.pseudonym_last) == (
        new,
        new,
        None,
    )
    now = _snapshot(db)
    assert now[ids[QD]] == before[ids[QD]]
    assert set(now) == set(before)
    assert all(_kept(now[key]) == _kept(before[key]) for key in before)


@_FIRST
def test_replace_shows_and_moves_a_clean_row(tmp_path: Path) -> None:
    """T5 (AC4, AC6): « Xantor Brontel »'s last part is its own first name;
    « Zorbal Brontel » holds the same part for the same real last name. The
    question lists it under the second heading; both get one new part."""
    db, ids = _db(tmp_path, [XB_ROW, ZB_ROW])
    code, shown = _replace(db, "--id", ids[XB][:8], typed="yes\n")
    assert code == 0, (code, shown)  # expected failure
    flat = _flat(shown)
    pre(SECOND_HEADING in flat and WARNING_START in flat, f"plan shown: {flat!r}")
    second = flat.split(SECOND_HEADING, 1)[1].split(WARNING_START, 1)[0]
    assert "Zorbal Brontel" in second, flat
    after = _by_name(db)
    new = after[XB].pseudonym_last
    assert new and fold(new) != "xantor", new
    assert after["Zorbal Brontel"].pseudonym_last == new
    assert after[XB].pseudonym_first == "Pivel"
    assert after["Zorbal Brontel"].pseudonym_first == "Quilla"


@_FIRST
def test_replace_all(tmp_path: Path) -> None:
    """T6 (AC4, AC10): `--all --force` on T1's rows and two clean rows:
    nothing is found afterwards; the organisation that shares only a common
    word and the clean rows do not change."""
    clean: list[Row] = [
        (PERSON, "Tobrek Lanvis", "Dorn Kelvar", "Tobrek", "Lanvis", "Dorn", "Kelvar"),
        (LOCATION, "Pivelle", "Fendra", None, None, None, None),
    ]
    db, ids = _db(tmp_path, [*T1_ROWS, *clean])
    before = _snapshot(db)
    unchanged = [ids["Groupe Zorbaville"], ids["Tobrek Lanvis"], ids["Pivelle"]]
    with _forced(ZORBAVILLE_A_CITY):
        code, shown = _replace(db, "--all", "--force")
        assert code == 0, (code, shown)  # expected failure
        again_code, again = _own_words(db)
    assert again_code == 0 and NONE_FOUND in _flat(again), again
    now = _snapshot(db)
    assert all(now[key] == before[key] for key in unchanged)


@_FIRST
@pytest.mark.parametrize(
    "case",
    [
        "own_word",
        "saved_name",
        "other_role_part",
        "group_member_part",
        "full_taken",
        "real_word_has_another_part",
    ],
)
def test_new_value_is_drawn_again(tmp_path: Path, case: str) -> None:
    """T7 (AC6): the first candidate offered is refused for exactly one
    reason: the own word, a word of a saved name, a saved last part, a group
    member's own last part, a new full pseudonym already saved, or a saved
    part of the same real first word outside the group (PO, v1.2: the draw
    never returns a saved binding unchecked)."""
    rows: list[Row] = [
        ZQ_ROW,
        ZM_ROW,
        (PERSON, "Xantor Pivane", "Dorn Kelvar", "Xantor", "Pivane", "Dorn", "Kelvar"),
        # Saved with no parts, as _assign_untaken_pseudonym saves one
        (PERSON, "Tobrek Lanvis", "Fendra Brontel", "Tobrek", "Lanvis", None, None),
    ]
    candidate = {
        "own_word": "Zorbal",
        "saved_name": "Xantor",
        "other_role_part": "Kelvar",
        "group_member_part": "Vellion",
        "full_taken": "Fendra",
        "real_word_has_another_part": "Vorlane",
    }[case]
    if case == "real_word_has_another_part":
        rows.append((PERSON, "Zorbal", "Vorlane", "Zorbal", None, "Vorlane", None))
    db, ids = _db(tmp_path, rows)
    with _forced({"first": [candidate]}) as offers:
        code, shown = _replace(db, "--id", ids[ZQ][:8], "--force")
    assert code == 0, (code, shown)  # expected failure
    assert offers.n > 0
    after = _by_name(db)
    new = after[ZQ].pseudonym_first
    assert new and after[ZM].pseudonym_first == new
    assert fold(new) not in {fold(candidate), "zorbal"}, new
    assert not _PERSON_FALLBACK.match(new), new
    assert (after[ZQ].pseudonym_last, after[ZM].pseudonym_last) == (
        "Brontel",
        "Vellion",
    )


@_FIRST
def test_library_out_of_names_changes_nothing(tmp_path: Path) -> None:
    """T8 (AC6): the only last name left is the row's own word: the
    replacement stops, nothing written, no audit entry."""
    db, ids = _db(tmp_path, [XB_ROW])
    before = _snapshot(db)
    with _forced({}, last_names=["Xantor"]):
        code, shown = _replace(db, "--id", ids[XB][:8], "--force")
    assert code == 1, (code, shown)  # expected failure
    assert NO_FREE in _flat(shown)
    assert _snapshot(db) == before
    assert _replacements_logged(db) == []


@_FIRST
def test_clean_id_is_refused(tmp_path: Path) -> None:
    """T9 (AC4): an --id the check does not find is refused; nothing
    changes."""
    db, ids = _db(
        tmp_path,
        [(PERSON, ZQ, "Xantor Brontel", "Zorbal", "Quentrix", "Xantor", "Brontel")],
    )
    before = _snapshot(db)
    code, shown = _replace(db, "--id", ids[ZQ][:8], "--force")
    assert code == 1, (code, shown)  # expected failure
    assert NOT_FOUND in _flat(shown)
    assert _snapshot(db) == before


@_FIRST
def test_cancel_changes_nothing(tmp_path: Path) -> None:
    """T10 (AC4): answering « no » cancels; nothing changes."""
    db, ids = _db(tmp_path, T4_ROWS)
    before = _snapshot(db)
    code, shown = _replace(db, "--id", ids[ZQ][:8], typed="no\n")
    assert code == 0, (code, shown)  # expected failure
    assert CANCELLED in _flat(shown)
    assert _snapshot(db) == before
    assert _replacements_logged(db) == []


@_FIRST
def test_custom_row_in_group_stops(tmp_path: Path) -> None:
    """T14 (AC6): the group of « Xantor Brontel »'s last part holds a
    pseudonym the user chose (« Zorbal Brontel », theme custom): the
    replacement stops, nothing written."""
    db, ids = _db(tmp_path, [XB_ROW])
    _save(db, [ZB_ROW], "custom")
    before = _snapshot(db)
    code, shown = _replace(db, "--id", ids[XB][:8], "--force")
    assert code == 1, (code, shown)  # expected failure
    assert CHOSEN in _flat(shown)
    assert _snapshot(db) == before
    assert _replacements_logged(db) == []


@_FIRST
def test_place_fallback_is_a_new_name(tmp_path: Path) -> None:
    """T19 (AC6): the library's one place is the row's own name: the place
    gets the next fallback after the saved one, never a saved one."""
    db, ids = _db(
        tmp_path,
        [
            (LOCATION, "Zorbaville", "Zorbaville", None, None, None, None),
            (LOCATION, "Pivelle", "Location-001", None, None, None, None),
        ],
    )
    before = _snapshot(db)
    with _forced({}, places=["Zorbaville"]):
        code, shown = _replace(db, "--all", "--force")
    assert code == 0, (code, shown)  # expected failure
    after = _by_name(db)
    assert after["Zorbaville"].pseudonym_full == "Location-002"
    assert _snapshot(db)[ids["Pivelle"]] == before[ids["Pivelle"]]


@_FIRST
def test_groups_of_one_replacement_never_share_a_new_part(tmp_path: Path) -> None:
    """T22 (AC6, PO v1.4): two last-part groups and one free last name: the
    first group drawn takes it, the second has none left, so nothing is
    written (a draw on the database alone gives both the same part)."""
    db, _ = _db(
        tmp_path,
        [
            XB_ROW,
            (
                PERSON,
                "Tobrek Lanvis",
                "Dorn Tobrek",
                "Tobrek",
                "Lanvis",
                "Dorn",
                "Tobrek",
            ),
        ],
    )
    before = _snapshot(db)
    with _forced({}, last_names=["Quilla"]):
        code, shown = _replace(db, "--all", "--force")
    assert code == 1, (code, shown)  # expected failure
    assert NO_FREE in _flat(shown)
    assert _snapshot(db) == before
    assert _replacements_logged(db) == []


# ---------------------------------------------------------------------------
# After a replacement (T11-T13)
# ---------------------------------------------------------------------------


@_FIRST
def test_later_document_writes_the_new_part(tmp_path: Path) -> None:
    """T11 (AC8): after the replacement, a document naming the replaced
    name, the lone first name and a new person sharing it writes no
    « Zorbal »."""
    db, ids = _db(tmp_path, T4_ROWS)
    code, shown = _replace(db, "--id", ids[ZQ][:8], "--force")
    assert code == 0, (code, shown)  # expected failure
    new = _by_name(db)[ZQ].pseudonym_first
    names = [(ZQ, PERSON), (ZD, PERSON), ("Zorbal", PERSON)]
    result = _desktop(db, tmp_path, "later", LATER_DOC, names)()
    pre(result.success, f"the later document is written: {result.error_message}")
    written = (tmp_path / "later_out.txt").read_text(encoding="utf-8")
    assert "zorbal" not in _words(written), written
    assert _by_name(db)[ZD].pseudonym_first == new


@_FIRST
def test_audit_and_logs_hold_no_name(tmp_path: Path) -> None:
    """T12 (AC9): one REPLACEMENT entry with the row ids; neither it nor any
    log call of the new code holds a name, an old or new pseudonym or the
    word."""
    db, ids = _db(tmp_path, T4_ROWS)
    assert importlib.util.find_spec(CORE) is not None  # expected failure
    assert importlib.util.find_spec(COMMAND) is not None
    core = importlib.import_module(CORE)
    command = importlib.import_module(COMMAND)
    assert getattr(core, "logger", None) is not None
    assert getattr(command, "logger", None) is not None
    recorder = _Recorder()
    with (
        patch.object(core, "logger", recorder),
        patch.object(command, "logger", recorder),
    ):
        code, shown = _replace(db, "--id", ids[ZQ][:8], "--force")
    assert code == 0, (code, shown)
    new = _by_name(db)[ZQ].pseudonym_first
    assert new
    secret = {"zorbal", "quentrix", "mestrix", "brontel", "vellion", *_words(new)}
    entries = _replacements_logged(db)
    assert len(entries) == 1, entries
    assert not secret & set(_words(repr(entries[0])))
    assert all(ids[name] in repr(entries[0]) for name in (ZQ, ZM, "Zorbal"))
    assert recorder.calls
    assert not secret & set(_words(repr(recorder.calls)))


@_FIRST
@pytest.mark.parametrize(
    "case",
    ["waits_for_a_document", "document_waits_for_it", "row_added_after_the_list"],
)
def test_replace_and_documents_one_at_a_time(tmp_path: Path, case: str) -> None:
    """T13 (AC7): the replacement takes the lock as a document does. Held
    by another connection, it waits, then completes; holding it, a
    document waits and then writes the new part; a row sharing the part
    saved after the user saw the list stops it, nothing written."""
    db, ids = _db(tmp_path, T4_ROWS)
    assert importlib.util.find_spec(CORE) is not None  # expected failure
    core = importlib.import_module(CORE)
    replace = getattr(core, "replace_own_word_rows", None)
    assert replace is not None
    group = (ids[ZQ], ids[ZM], ids["Zorbal"])

    if case == "row_added_after_the_list":
        # The user was shown T4's group, then a document saved a row that
        # shares its part
        confirmed = frozenset(group)
        _save(
            db,
            [
                (
                    PERSON,
                    "Zorbal Pivane",
                    "Zorbal Dorn",
                    "Zorbal",
                    "Pivane",
                    "Zorbal",
                    "Dorn",
                )
            ],
        )
        before = _snapshot(db)
        with open_database(db, PASSPHRASE) as session:
            result = replace(session, [ids[ZQ]], confirmed)
        assert result.stop_reason == "changed"
        assert _snapshot(db) == before
        assert _replacements_logged(db) == []
        return

    document: dict[str, Any] = {}
    if case == "waits_for_a_document":
        holder = _LockHolder(db)
        timer = threading.Timer(1.0, holder.release.set)
        try:
            holder.start("before the replacement")
            holder.attempting()
            timer.start()
            started = time.monotonic()
            with open_database(db, PASSPHRASE) as session:
                result = replace(session, [ids[ZQ]], None)
            waited = time.monotonic() - started
        finally:
            timer.cancel()
            holder.stop()
        assert waited >= 0.5, waited
    else:
        me = threading.current_thread()
        real_find_all = SQLiteMappingRepository.find_all
        real_lock = processor_module.pseudonym_lock
        asked = threading.Event()
        reads_under_lock: list[bool] = []
        run_document = _desktop(
            db, tmp_path, "doc", f"{ZM} a signé le contrat.", [(ZM, PERSON)]
        )

        def write_document() -> None:
            try:
                document["result"] = run_document()
            except BaseException as error:  # noqa: BLE001 - shown by the PRE below
                document["result"] = error

        thread = threading.Thread(target=write_document, name="doc")

        @contextmanager
        def lock(db_session: Any) -> Iterator[None]:
            if threading.current_thread() is thread:
                asked.set()
            with real_lock(db_session):
                yield

        def find_all(self: Any, *args: Any, **kwargs: Any) -> Any:
            if (
                threading.current_thread() is me
                and not reads_under_lock
                and _write_lock_held(db)
            ):
                # The replacement holds the lock: the document starts now
                # and asks for it
                reads_under_lock.append(True)
                thread.start()
                pre(asked.wait(30.0), "the document asked for the lock")
                time.sleep(0.5)
            return real_find_all(self, *args, **kwargs)

        with (
            patch.object(SQLiteMappingRepository, "find_all", find_all),
            patch.object(processor_module, "pseudonym_lock", lock),
        ):
            with open_database(db, PASSPHRASE) as session:
                result = replace(session, [ids[ZQ]], None)
            if thread.is_alive() or thread.ident is not None:
                thread.join(WAIT)
        pre(reads_under_lock == [True], "the replacement read the rows under the lock")
        pre(not thread.is_alive(), "the document finished")

    assert result.stop_reason is None
    after = _by_name(db)
    new = after[ZQ].pseudonym_first
    assert new and fold(new) != "zorbal", new
    assert after[ZM].pseudonym_first == new
    assert after["Zorbal"].pseudonym_full == new
    assert after[QD].pseudonym_full == "Pivel Xantor"
    if case == "document_waits_for_it":
        written = document.get("result")
        assert getattr(written, "success", False), written
        assert _written(
            tmp_path, "doc", f"{ZM} a signé le contrat.", [(ZM, PERSON)]
        ) == [after[ZM].pseudonym_full]


# ---------------------------------------------------------------------------
# The notice when a document is written (T17, T20, T21)
# ---------------------------------------------------------------------------


@_FIRST
def test_notice_after_a_document(tmp_path: Path) -> None:
    """T17 (AC10): `process` on a database that holds T4's three rows
    prints the note once, with the count 3."""
    db, _ = _db(tmp_path, T4_ROWS)
    code, shown = _process(tmp_path, db, DOC_QD, [(QD, PERSON)], "doc")
    pre(code == 0, f"process ran: {shown!r}")
    flat = _flat(shown)
    assert flat.count(NOTICE) == 1, flat  # expected failure
    assert f"3 {NOTICE}s" in flat
    assert NOTICE_SEE in flat


@_FIRST
def test_no_notice_without_leaking_rows(tmp_path: Path) -> None:
    """T20 (AC10): `batch --workers 2` (the parallel path, its worker's
    dict) prints the note once on a database that holds T4's rows; `process`
    and `batch` on a clean database print none."""
    db, _ = _db(tmp_path / "leaking", T4_ROWS)
    code, shown = _batch(tmp_path, db, [DOC_QD], [(QD, PERSON)], "leaking_docs")
    pre(code == 0, f"batch ran: {shown!r}")
    flat = _flat(shown)
    assert flat.count(NOTICE) == 1, flat  # expected failure
    assert f"3 {NOTICE}s" in flat
    clean, _ = _db(tmp_path / "clean", [])
    code, shown = _process(tmp_path, clean, DOC_QD, [(QD, PERSON)], "clean_doc")
    pre(code == 0, f"process ran: {shown!r}")
    assert NOTICE not in _flat(shown)
    code, shown = _batch(tmp_path, clean, [DOC_QD], [(QD, PERSON)], "clean_docs")
    pre(code == 0, f"batch ran: {shown!r}")
    assert NOTICE not in _flat(shown)


@_FIRST
def test_notice_counts_a_row_this_document_saved(tmp_path: Path) -> None:
    """T21 (AC10, Story 11.6's KL-008): the real first name Xantor keeps its
    part « Brontel », a word of the new « Xantor Brontel »'s own name: the
    document that saves that row prints the note, count 1."""
    db, _ = _db(
        tmp_path,
        [
            (
                PERSON,
                "Xantor Quentrix",
                "Brontel Pivel",
                "Xantor",
                "Quentrix",
                "Brontel",
                "Pivel",
            )
        ],
    )
    code, shown = _process(
        tmp_path, db, f"{XB} a signé le contrat.", [(XB, PERSON)], "doc"
    )
    pre(code == 0, f"process ran: {shown!r}")
    saved = _by_name(db).get(XB)
    pre(
        saved is not None and saved.pseudonym_first == "Brontel",
        f"« {XB} » saved with the kept part « Brontel »: {saved and saved.pseudonym_full}",
    )
    flat = _flat(shown)
    assert flat.count(NOTICE) == 1, flat  # expected failure
    assert f"1 {NOTICE} " in flat
    listed_code, listed = _own_words(db)
    assert listed_code == 0, listed
    line = _line_of(listed, saved.id[:8])
    assert XB in line and "Brontel" in line
