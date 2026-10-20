"""Story 10.16, round 2: a separate accent mark in the custom pseudonym checks,
in desktop batch review through the real batch worker (T30-T32; Codex's
review of 463481a, the orchestrator's ruling).

Written by the BMAD dev agent (Claude). RW = the round-1 harness
(``test_custom_pseudonym_fixes_batch_worker.py``): the real ``BatchScreen``,
``ValidationScreen`` and ``BatchWorker`` thread, only
``DocumentProcessor._detect_and_filter_entities`` replaced; the pseudonym
through ``ValidationScreen._handle_entity_action`` with
``QInputDialog.getText`` replaced and the messages recorded. The assertions
run after the worker has finished, on the written file and the stored rows.

The texts are written composed in this file. Each test builds its forms at
run time with ``unicodedata.normalize``: ``[name_decomposed]`` the document
(and so every name in it) in NFD and the typed pseudonym in NFC;
``[pseudonym_decomposed]`` the reverse; ``[both_decomposed]`` both NFD. No
combining mark is written in this file.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and main-corpus words
only.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from typing import Any

import pytest

from tests.unit.gui.test_custom_pseudonym_fixes_batch_worker import (
    _at,
    _Batch,
    _Dialogs,
    _replacements,
    _stored,
    _words,
    pre,
)

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 10.10's test_batch_review_real_worker.py). This is a
# warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

# Lionel's approved finalization error (10.16 Q1, "Add the new reason
# (Rec.)", 2026-10-16).
IN_DOCUMENT = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "it now matches a name in this document. Nothing was written."
)

NAME_DECOMPOSED = "name_decomposed"
PSEUDONYM_DECOMPOSED = "pseudonym_decomposed"
BOTH_DECOMPOSED = "both_decomposed"
FORMS = [NAME_DECOMPOSED, PSEUDONYM_DECOMPOSED, BOTH_DECOMPOSED]

SET_DOC = "quentrel zórbalia a signé le contrat."
SET_NAME = "quentrel zórbalia"
SHARED = "Xantor Zórbalia"
NOT_SHARED = "Xantor Véllion"
ADD_DOC_GUI = "quentrel quovan a signé avec zórbalia."
ADD_NAME = "quentrel quovan"
ADDED = "zórbalia"

XFAIL = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.16 round 2: reproduces Codex's P0 (a separate accent mark) "
        "on 463481a; fixed in Task 2.7"
    ),
)

Form = Callable[[str], str]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


def _forms(form: str) -> tuple[Form, Form]:
    """(the document's form, the typed pseudonym's form)."""
    document = _nfd if form in (NAME_DECOMPOSED, BOTH_DECOMPOSED) else _nfc
    typed = _nfd if form in (PSEUDONYM_DECOMPOSED, BOTH_DECOMPOSED) else _nfc
    return document, typed


def _cases() -> list[Any]:
    """Each form; every case but ``[both_decomposed]`` is an expected failure
    on 463481a (both sides are cut alike there)."""
    return [
        pytest.param(form, marks=() if form == BOTH_DECOMPOSED else XFAIL, id=form)
        for form in FORMS
    ]


def _one_row(state: Any) -> Any:
    rows = state.get_all_entities()
    pre(len(rows) == 1, f"one row: {[r.entity.text for r in rows]!r}")
    return rows[0]


@pytest.mark.parametrize("form", _cases())
def test_batch_accents_refused_when_set(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """T30 (AC1, round 2): in batch review the dialog refuses "Xantor
    Zórbalia" on « quentrel zórbalia » whether the name, the pseudonym or both
    are written with a separate accent mark; the document is written with a
    generated pseudonym, stored so."""
    dialogs = _Dialogs(monkeypatch)
    document, typed_form = _forms(form)
    text, name_text = document(SET_DOC), document(SET_NAME)
    batch = _Batch(
        qtbot, main_window, tmp_path, [(text, [_at(text, name_text, "PERSON", 0)])]
    )

    def body(record: dict[str, Any]) -> None:
        row = _one_row(batch.wait_doc(0))
        batch.action(monkeypatch, row.entity_id, "change_pseudonym", typed_form(SHARED))
        record["messages"] = list(dialogs.calls)
        record["custom"] = row.custom_pseudonym
        batch.accept_pending_and_validate()

    record = batch.run(body)
    messages = record["messages"]
    assert len(messages) == 1 and messages[0][1].strip(), messages  # expected failure
    assert record["custom"] is None
    output = batch.out / "doc0_pseudonymized.txt"
    assert output.exists()
    (place,) = _replacements(
        output.read_text(encoding="utf-8"), text, [(0, len(name_text))]
    )
    assert not {"quentrel", "zorbalia"} & set(_words(place)), place
    stored = _stored(batch.db, name_text, "PERSON")
    assert stored is not None and stored[3] == place, stored


@pytest.mark.parametrize("form", _cases())
def test_batch_accents_name_added_after_the_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """T31 (AC1, AC5; Lionel's 10.16 Q1): in batch review "Xantor Zórbalia"
    is set on « quentrel quovan », then « zórbalia » is added by hand: the
    document fails with Lionel's new reason whichever side is written with a
    separate accent mark; no output file, no row."""
    dialogs = _Dialogs(monkeypatch)
    document, typed_form = _forms(form)
    text, name_text, added = document(ADD_DOC_GUI), document(ADD_NAME), document(ADDED)
    typed = typed_form(SHARED)
    batch = _Batch(
        qtbot, main_window, tmp_path, [(text, [_at(text, name_text, "PERSON", 0)])]
    )

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        row = _one_row(state)
        batch.action(monkeypatch, row.entity_id, "change_pseudonym", typed)
        pre(
            dialogs.calls == [] and row.custom_pseudonym == typed,
            f"set as typed, without a message: {dialogs.calls!r}",
        )
        start = text.find(added)
        state.add_entity(added, "PERSON", start, start + len(added))
        batch.accept_pending_and_validate()

    batch.run(body)
    output = batch.out / "doc0_pseudonymized.txt"
    assert not output.exists(), output.read_text(encoding="utf-8")  # expected failure
    result = batch.bs._batch_result
    errors = [doc.error_message for doc in result.per_document_results]
    assert errors == [IN_DOCUMENT], errors
    assert _stored(batch.db, name_text, "PERSON") is None


@pytest.mark.parametrize("form", FORMS)
def test_batch_accents_without_shared_word_accepted(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """T32 (a guard): in batch review "Xantor Véllion" shares no word with
    « quentrel zórbalia »: set without a message in every form, written as
    typed and stored under the name as the document writes it."""
    dialogs = _Dialogs(monkeypatch)
    document, typed_form = _forms(form)
    text, name_text, typed = (
        document(SET_DOC),
        document(SET_NAME),
        typed_form(NOT_SHARED),
    )
    batch = _Batch(
        qtbot, main_window, tmp_path, [(text, [_at(text, name_text, "PERSON", 0)])]
    )

    def body(record: dict[str, Any]) -> None:
        row = _one_row(batch.wait_doc(0))
        batch.action(monkeypatch, row.entity_id, "change_pseudonym", typed)
        record["messages"] = list(dialogs.calls)
        record["custom"] = row.custom_pseudonym
        batch.accept_pending_and_validate()

    record = batch.run(body)
    assert record["messages"] == [], record["messages"]
    assert record["custom"] == typed
    output = batch.out / "doc0_pseudonymized.txt"
    assert output.read_text(encoding="utf-8") == typed + text[len(name_text) :]
    stored = _stored(batch.db, name_text, "PERSON")
    assert stored is not None and stored[3] == typed, stored
