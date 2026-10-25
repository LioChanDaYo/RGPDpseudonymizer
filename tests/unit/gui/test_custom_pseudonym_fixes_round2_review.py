"""Story 10.16, round 2: a separate accent mark in the custom pseudonym checks,
in the desktop review, single document (T25-T29; Codex's review of 463481a,
the orchestrator's ruling, QA's TEST-001).

Written by the BMAD dev agent (Claude). SD = the round-1 harness
(``test_custom_pseudonym_fixes_review.py``): the real ``DetectionWorker`` run
synchronously with detection replaced, the real ``ValidationScreen`` and the
real ``FinalizationWorker``; the dialog with ``QInputDialog.getText``
replaced, the messages recorded, the written text read from the results
screen.

The texts are written composed in this file. Each test builds its forms at
run time with ``unicodedata.normalize``: ``[name_decomposed]`` the document
(and so every name in it) in NFD and the typed pseudonym in NFC;
``[pseudonym_decomposed]`` the reverse; ``[both_decomposed]`` both NFD. No
combining mark is written in this file.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). A refusal is asserted as exactly one
message, not empty; the finalization error is Lionel's approved text, byte
for byte. Invented names and main-corpus words only.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from typing import Any

import pytest

from tests.unit.gui.test_custom_pseudonym_fixes_review import (
    IN_DOCUMENT,
    REJECTED,
    _at,
    _Dialogs,
    _new_db,
    _replacements,
    _Single,
    _stored,
    _type_in,
    _words,
    pre,
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
OWN_DOC = "quentrel zorbalia a signé avec quovan."
CORR_DOC = "quentrel zorbalia a signé avec zorbal."

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
    """Each form (on 463481a every case but ``[both_decomposed]`` failed;
    both sides are cut alike there)."""
    return [pytest.param(form, id=form) for form in FORMS]


@pytest.mark.parametrize("form", _cases())
def test_desktop_accents_refused_when_set(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """T25 (AC1, round 2): the dialog refuses "Xantor Zórbalia" on
    « quentrel zórbalia » whether the name, the pseudonym or both are written
    with a separate accent mark; the name is written with a generated
    pseudonym and stored so."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    document, typed_form = _forms(form)
    text, name_text = document(SET_DOC), document(SET_NAME)
    sd = _Single(
        qtbot, main_window, tmp_path, db, text, [_at(text, name_text, "PERSON", 0)]
    )
    row = sd.row(name_text)
    sd.dialog(monkeypatch, row.entity_id, typed_form(SHARED))
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    (place,) = _replacements(written, _nfc(text), [(0, len(_nfc(name_text)))])
    assert not {"quentrel", "zorbalia"} & set(_words(place)), written
    stored = _stored(db, name_text, "PERSON")
    assert stored is not None and stored[3] == place, stored


@pytest.mark.parametrize("form", _cases())
def test_desktop_accents_name_added_after_the_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """T26 (AC1, AC5; Lionel's 10.16 Q1): "Xantor Zórbalia" is set on
    « quentrel quovan », then « zórbalia » is added by hand: finalization
    stops with Lionel's new reason whichever side is written with a separate
    accent mark; the review stays open and no row is stored."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    document, typed_form = _forms(form)
    text, name_text, added = document(ADD_DOC_GUI), document(ADD_NAME), document(ADDED)
    typed = typed_form(SHARED)
    sd = _Single(
        qtbot, main_window, tmp_path, db, text, [_at(text, name_text, "PERSON", 0)]
    )
    row = sd.row(name_text)
    sd.dialog(monkeypatch, row.entity_id, typed)
    pre(
        dialogs.calls == [] and row.custom_pseudonym == _nfc(typed),
        f"set as typed, without a message: {dialogs.calls!r}",
    )
    start = text.find(added)
    sd.state.add_entity(added, "PERSON", start, start + len(added))
    sd.accept_pending()
    pre(
        any(e.text == added for e in sd.state.expand_validated_entities()),
        "the added name is sent",
    )
    written = sd.finalize(dialogs)
    assert written is None, written  # expected failure
    assert len(dialogs.calls) == 1 and dialogs.calls[0][1] == IN_DOCUMENT, dialogs.calls
    assert main_window.current_screen_name() == "validation"
    assert _stored(db, name_text, "PERSON") is None


@pytest.mark.parametrize("form", FORMS)
def test_desktop_accents_without_shared_word_accepted(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """T27 (a guard): "Xantor Véllion" shares no word with « quentrel
    zórbalia »: set without a message in every form, written as typed and
    stored under the name as the document writes it."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    document, typed_form = _forms(form)
    text, name_text, typed = (
        document(SET_DOC),
        document(SET_NAME),
        typed_form(NOT_SHARED),
    )
    sd = _Single(
        qtbot, main_window, tmp_path, db, text, [_at(text, name_text, "PERSON", 0)]
    )
    row = sd.row(name_text)
    sd.dialog(monkeypatch, row.entity_id, typed)
    assert dialogs.calls == [], dialogs.calls
    assert row.custom_pseudonym == _nfc(typed)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written == _nfc(typed + text[len(name_text) :]), written
    stored = _stored(db, name_text, "PERSON")
    assert stored is not None and stored[3] == _nfc(typed), stored


def test_desktop_rejected_row_own_surname_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T28 (a guard; QA's TEST-001, n2): the name a pseudonym replaces always
    counts, even on a row rejected first: "Xantor Zorbalia" on the rejected
    « quentrel zorbalia » is refused; accepted again, the name is written
    with a generated pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    entities = [
        _at(OWN_DOC, "quentrel zorbalia", "PERSON", 0),
        _at(OWN_DOC, "quovan", "PERSON"),
    ]
    sd = _Single(qtbot, main_window, tmp_path, db, OWN_DOC, entities)
    row = sd.row("quentrel zorbalia")
    sd.state.reject_entity(row.entity_id)
    pre(row.state == REJECTED, "« quentrel zorbalia » rejected")
    sd.dialog(monkeypatch, row.entity_id, "Xantor Zorbalia")
    assert dialogs.one_message(), dialogs.calls
    assert row.custom_pseudonym is None
    sd.state.accept_entity(row.entity_id)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    spans = sorted((e.start_pos, e.end_pos) for e in entities)
    place = _replacements(written, OWN_DOC, spans)[0]
    assert not {"quentrel", "zorbalia"} & set(_words(place)), written


def test_desktop_corrected_row_counts_when_set(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T29 (a guard; QA's TEST-001, n6): the desktop names read each row's
    correction: « zorba » corrected into « zorbal » blocks "Xantor Zorbal"
    on « quentrel zorbalia »."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    start = CORR_DOC.find("zorbal.")
    entities = [
        _at(CORR_DOC, "quentrel zorbalia", "PERSON", 0),
        _at(CORR_DOC, "zorba", "PERSON", start),
    ]
    sd = _Single(qtbot, main_window, tmp_path, db, CORR_DOC, entities)
    corrected = sd.row("zorba")
    _type_in(monkeypatch, "zorbal")
    sd.vs._handle_entity_action(corrected.entity_id, "modify_text")
    pre(corrected.user_modification == "zorbal", "« zorba » corrected into « zorbal »")
    row = sd.row("quentrel zorbalia")
    sd.dialog(monkeypatch, row.entity_id, "Xantor Zorbal")
    assert dialogs.one_message(), dialogs.calls
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    spans = [(0, len("quentrel zorbalia")), (start, start + len("zorbal"))]
    place = _replacements(written, CORR_DOC, spans)[0]
    assert "zorbal" not in _words(place), written
