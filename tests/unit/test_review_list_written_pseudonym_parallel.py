"""Story 11.5: two documents finalized at once, each with the pseudonyms its
review showed (T13, T14, T17; AC7).

Written by the BMAD dev agent (Claude), tests first. Story 10.22's harness:
two documents, each in its own thread (``A`` and ``B``) with its own
``DocumentProcessor``, so its own connection, their saves held together
(``held_pair(..., settle=True)``). ``A`` holds the database's write lock at
its save, so it keeps what its review showed; ``B`` reloads the saved rows
after ``A``'s save and must check its own proposals against them. Each
document is ``finalize_document``, the desktop reviews' path, with its
proposals (``_finalize_run``; Story 10.22's ``_desktop`` takes none).

The draw stand-in, ``_proposal``, ``_changed`` and the other helpers are
those of ``test_review_list_written_pseudonym.py``, so every marked case
reaches the new behaviour on the unfixed code too. Preconditions fail with
``pytest.fail("PRE: ...")``; the first ``assert`` is the expected failure on
the unfixed code (``# expected failure``). Invented names only. No spaCy
model, no Qt.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.data.models import Entity
from tests.unit.test_custom_pseudonym_fixes_cli import PASSPHRASE, _new_db
from tests.unit.test_parallel_saved_pseudonym import (
    _found,
    _saved,
    _settings,  # noqa: F401 - autouse fixture: no settings file read or written
    _written,
    held_pair,
)
from tests.unit.test_review_list_written_pseudonym import (
    DB_PS,
    MV_PS,
    PERSON,
    VM,
    WRITTEN,
    ZM,
    ZQ,
    _changed,
    _Draws,
    _key,
    _proposal,
    install_draws,
)

DOC_A_ZQ = f"{ZQ} a signé le contrat."
DOC_B_VM = f"{VM} a signé le contrat."
DOC_B_ZQ = f"Le contrat avec {ZQ}."
DOC_B_ZM = f"{ZM} a signé le contrat."


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


def _finalize_run(
    db: str,
    folder: Path,
    tag: str,
    text: str,
    name: str,
    proposal: Any,
    theme: str = "neutral",
) -> Callable[[], ProcessingResult]:
    """``finalize_document`` for one person name, with the pseudonym its
    review showed (passed only when ``finalize_document`` takes it)."""
    output = folder / f"{tag}_out.txt"
    entities = _found(text, [(name, PERSON)])
    pre_entities = len(entities) == 1
    proposals = {_key(name, PERSON): [proposal]}
    takes = (
        "proposals" in inspect.signature(DocumentProcessor.finalize_document).parameters
    )

    def run() -> ProcessingResult:
        if not pre_entities:
            pytest.fail(f"PRE: one place of {name!r} in {tag}")
        processor = DocumentProcessor(db_path=db, passphrase=PASSPHRASE, theme=theme)
        if takes:
            return processor.finalize_document(
                text, entities, str(output), proposals=proposals
            )
        return processor.finalize_document(text, entities, str(output))

    return run


def _rows(db: str, name: str) -> list[Entity]:
    return [row for row in _saved(db) if row.full_name == name]


def _one_row(db: str, name: str) -> Entity:
    rows = _rows(db, name)
    if len(rows) != 1:
        pytest.fail(f"PRE: one saved row for {name!r}: {len(rows)}")
    return rows[0]


def _both_written(a: ProcessingResult, b: ProcessingResult) -> None:
    if not (a.success and b.success):
        pytest.fail(f"PRE: both written: {a.error_message} {b.error_message}")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
@pytest.mark.parametrize(
    "theme", ["neutral", "neutral_id"], ids=["default", "neutral_id"]
)
def test_two_documents_one_proposal_two_names(
    tmp_path: Path, draws: _Draws, theme: str
) -> None:
    """T13 (AC7): two names shown one pseudonym in two reviews: the first
    document keeps it, the second is drawn again and reports it."""
    db = _new_db(tmp_path)
    shown = "PER-001" if theme == "neutral_id" else DB_PS
    a, b = held_pair(
        _finalize_run(
            db, tmp_path, "a", DOC_A_ZQ, ZQ, _proposal(PERSON, shown, theme), theme
        ),
        _finalize_run(
            db, tmp_path, "b", DOC_B_VM, VM, _proposal(PERSON, shown, theme), theme
        ),
        settle=True,
    )
    _both_written(a, b)
    row_a, row_b = _one_row(db, ZQ), _one_row(db, VM)
    changed = (_changed(a), _changed(b))
    expected = ([], [(VM, PERSON, shown, row_b.pseudonym_full)])
    assert changed == expected  # expected failure
    assert row_a.pseudonym_full == shown
    assert (
        row_a.pseudonym_full != row_b.pseudonym_full
        and row_a.pseudonym_first != row_b.pseudonym_first
        and row_a.pseudonym_last != row_b.pseudonym_last
    )
    assert _written(tmp_path, "a", DOC_A_ZQ, [(ZQ, PERSON)]) == [row_a.pseudonym_full]
    assert _written(tmp_path, "b", DOC_B_VM, [(VM, PERSON)]) == [row_b.pseudonym_full]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_two_documents_one_name_two_proposals(tmp_path: Path, draws: _Draws) -> None:
    """T14 (AC7): one name shown two pseudonyms in two reviews: one row; the
    document whose pseudonym was not kept reports it."""
    db = _new_db(tmp_path)
    a, b = held_pair(
        _finalize_run(db, tmp_path, "a", DOC_A_ZQ, ZQ, _proposal(PERSON, DB_PS)),
        _finalize_run(db, tmp_path, "b", DOC_B_ZQ, ZQ, _proposal(PERSON, MV_PS)),
        settle=True,
    )
    _both_written(a, b)
    row = _one_row(db, ZQ)
    changed = (_changed(a), _changed(b))
    expected = ([], [(ZQ, PERSON, MV_PS, row.pseudonym_full)])
    assert changed == expected  # expected failure
    assert row.pseudonym_full == DB_PS
    written = (
        _written(tmp_path, "a", DOC_A_ZQ, [(ZQ, PERSON)]),
        _written(tmp_path, "b", DOC_B_ZQ, [(ZQ, PERSON)]),
    )
    assert written == ([DB_PS], [DB_PS])


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_two_documents_one_first_name(tmp_path: Path, draws: _Draws) -> None:
    """T17 (AC7; Story 10.22): two names sharing a real first name, shown
    different first-name parts in two reviews: one first-name part saved; the
    second document reports its name."""
    db = _new_db(tmp_path)
    a, b = held_pair(
        _finalize_run(db, tmp_path, "a", DOC_A_ZQ, ZQ, _proposal(PERSON, DB_PS)),
        _finalize_run(db, tmp_path, "b", DOC_B_ZM, ZM, _proposal(PERSON, MV_PS)),
        settle=True,
    )
    _both_written(a, b)
    row_a, row_b = _one_row(db, ZQ), _one_row(db, ZM)
    changed = (_changed(a), _changed(b))
    expected = ([], [(ZM, PERSON, MV_PS, row_b.pseudonym_full)])
    assert changed == expected  # expected failure
    assert row_a.pseudonym_first == row_b.pseudonym_first == "Dravin"
