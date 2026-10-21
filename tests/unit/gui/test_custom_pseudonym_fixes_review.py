"""Story 10.16: custom pseudonym fixes in the desktop review, single document
(T9-T13, T15; Codex release review #8, Lionel's 10.16 Q1).

SD = single document, as Story 10.11's ``test_custom_pseudonym_review.py``:
the real ``DetectionWorker`` run synchronously with detection replaced, the
real ``ValidationScreen`` and the real ``FinalizationWorker``; the dialog
through ``_show_change_pseudonym_dialog`` with ``QInputDialog.getText``
replaced, the messages recorded from ``ConfirmDialog.informational``, and the
written text read from the results screen.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict ``xfail(raises=AssertionError)`` never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). A refusal is asserted as exactly one message, not
empty, never its wording; the finalization error is Lionel's approved text,
byte for byte. Invented names, Lionel's preview values and main-corpus words
only.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QInputDialog

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
PENDING = EntityReviewState.PENDING
CONFIRMED = EntityReviewState.CONFIRMED
REJECTED = EntityReviewState.REJECTED

QZ = "Quentrel Zorbalia"
QZ_LOW = "quentrel zorbalia"

# Lionel's approved finalization error (10.16 Q1, "Add the new reason
# (Rec.)", 2026-10-16).
IN_DOCUMENT = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "it now matches a name in this document. Nothing was written."
)

DOC = "quentrel zorbalia a signé avec quentrix."
ORG_DOC = "zorbaville a signé le contrat."
QCDOC = "Zorbaville a signé avec Quentrel Zorbalia en avril, grâce à son petit groupe."
VARIANTS = (
    "quentrel quovan zorbalia a signé. le contrat est avec quentrel xelvan zorbalia."
)
ADDED_LATER = "quentrel zorbalia a signé avec zorbal."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test with "PRE: ..." (``pytest.fail``
    raises ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _fold(text: str) -> str:
    """Accents and capitals ignored."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _words(text: str) -> list[str]:
    """The folded whole words of ``text``."""
    return re.findall(r"\w+", _fold(text))


def _at(
    text: str, name: str, entity_type: str, start: int | None = None
) -> DetectedEntity:
    start = text.find(name) if start is None else start
    pre(start >= 0 and text[start : start + len(name)] == name, f"slice {name!r}")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _spans(entities: list[DetectedEntity]) -> list[tuple[int, int]]:
    return sorted((e.start_pos, e.end_pos) for e in entities)


def _replacements(output: str, source: str, spans: list[tuple[int, int]]) -> list[str]:
    """The string written in place of each span (in span order); every other
    character of the source unchanged."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    if match is None:
        pytest.fail(f"PRE: text damaged or a span not replaced: {output!r}")
    return list(match.groups())


def _new_db(tmp_path: Path) -> str:
    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    return db


def _stored(db: str, key: str, entity_type: str) -> tuple[Any, ...] | None:
    """(full_name, first_name, last_name, pseudonym_full, pseudonym_first,
    pseudonym_last) of the stored row of (key, type), or None."""
    with open_database(db, PASSPHRASE) as session:
        row = SQLiteMappingRepository(session).find_by_full_name_and_type(
            key, entity_type
        )
        if row is None:
            return None
        return (
            row.full_name,
            row.first_name,
            row.last_name,
            row.pseudonym_full,
            row.pseudonym_first,
            row.pseudonym_last,
        )


class _Dialogs:
    """Records ``ConfirmDialog.informational`` calls instead of showing them."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[tuple[str, str]] = []
        recorder = self

        class _Shown:
            def exec(self) -> int:
                return 0

        def informational(  # type: ignore[no-untyped-def]
            cls, title, message, dismiss_label="", parent=None
        ):
            recorder.calls.append((str(title), str(message)))
            return _Shown()

        monkeypatch.setattr(ConfirmDialog, "informational", classmethod(informational))

    def one_message(self) -> bool:
        """Exactly one message was shown, and it is not empty."""
        return len(self.calls) == 1 and bool(self.calls[0][1].strip())


def _type_in(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """The next ``QInputDialog.getText`` returns ``text`` and OK."""
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: (text, True))
    )


def _detect(
    db: str, path: Path, text: str, entities: list[DetectedEntity]
) -> DetectionResult:
    """The real DetectionWorker run synchronously, with detection replaced."""
    finished: list[object] = []
    worker = DetectionWorker(file_path=str(path), db_path=db, passphrase=PASSPHRASE)
    worker.setAutoDelete(False)
    worker.signals.finished.connect(finished.append)
    with patch.object(
        DocumentProcessor, "detect_entities", return_value=(text, entities)
    ):
        worker.run()
    pre(len(finished) == 1, "detection finished once")
    result = finished[0]
    if not isinstance(result, DetectionResult):
        pytest.fail("PRE: detection result")
    return result


class _Single:
    """One document validated in the desktop app, single-document mode."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        db: str,
        text: str,
        entities: list[DetectedEntity],
        name: str = "doc.txt",
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = _detect(db, path, text, entities)
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        main_window.show()
        self.vs.start_validation(result)
        main_window.navigate_to("validation")
        state = self.vs.validation_state
        if state is None:
            pytest.fail("PRE: review shown")
        self.state: GUIValidationState = state

    def row(self, text: str) -> Any:
        rows = [r for r in self.state.get_all_entities() if r.entity.text == text]
        pre(len(rows) == 1, f"one row {text!r}")
        return rows[0]

    def dialog(
        self, monkeypatch: pytest.MonkeyPatch, entity_id: str, text: str
    ) -> None:
        """ "Changer le pseudonyme" on a row, the user typing ``text``."""
        _type_in(monkeypatch, text)
        self.vs._show_change_pseudonym_dialog(entity_id)

    def accept_pending(self) -> None:
        for review in self.state.get_all_entities():
            if review.state == PENDING:
                self.state.accept_entity(review.entity_id)

    def finalize(self, dialogs: _Dialogs) -> str | None:
        """Finalize with the real worker; the written text, or None when
        finalization ended in an error message."""
        before = len(dialogs.calls)
        self.vs._start_finalization()
        self.qtbot.waitUntil(
            lambda: self.mw.current_screen_name() == "results"
            or len(dialogs.calls) > before,
            timeout=WAIT_MS,
        )
        if self.mw.current_screen_name() != "results":
            return None
        results = self.mw.stack.widget(self.mw._screens["results"])
        return Path(results._temp_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# #8: the review's names count whatever their capitals (T9-T13)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "whole_name",
        "surname",
        "other_name_pending",
        "other_name_accepted",
        "added_by_hand",
    ],
)
def test_desktop_lowercase_review_name_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T9 (AC1, #8): the dialog refuses the lowercase name itself, its
    surname, or another lowercase name of the review (still to review,
    accepted, or added by hand); the name is written with a generated
    pseudonym and stored so."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    name = _at(DOC, QZ_LOW, "PERSON", 0)
    other = _at(DOC, "quentrix", "PERSON")
    detected = [name] if case == "added_by_hand" else [name, other]
    sd = _Single(qtbot, main_window, tmp_path, db, DOC, detected)
    if case == "added_by_hand":
        sd.state.add_entity("quentrix", "PERSON", other.start_pos, other.end_pos)
        pre(len(sd.state.get_all_entities()) == 2, "two rows")
    if case == "other_name_accepted":
        sd.state.accept_entity(sd.row("quentrix").entity_id)
        pre(sd.row("quentrix").state == CONFIRMED, "« quentrix » accepted")
    typed = {
        "whole_name": QZ_LOW,
        "surname": "Xantor Zorbalia",
    }.get(case, "Xantor Quentrix")
    row = sd.row(QZ_LOW)
    sd.dialog(monkeypatch, row.entity_id, typed)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    place = _replacements(written, DOC, _spans([name, other]))[0]
    assert _fold(place) != _fold(typed), written
    assert not {"quentrel", "zorbalia"} & set(_words(place)), written
    stored = _stored(db, QZ_LOW, "PERSON")
    assert stored is not None and stored[3] == place


def test_desktop_variant_occurrence_counts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T10 (AC1, #8; the names sent): one row stands for its variant
    occurrences, which finalization sends with their own text; a word of a
    variant occurrence counts, so "Xantor Xelvan" is refused."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    entities = [
        _at(VARIANTS, "quentrel quovan zorbalia", "PERSON", 0),
        _at(VARIANTS, "quentrel xelvan zorbalia", "PERSON"),
    ]
    sd = _Single(qtbot, main_window, tmp_path, db, VARIANTS, entities)
    rows = sd.state.get_all_entities()
    pre(
        len(rows) == 1 and rows[0].entity.text == "quentrel quovan zorbalia",
        f"one row: {[r.entity.text for r in rows]!r}",
    )
    row = rows[0]
    sd.dialog(monkeypatch, row.entity_id, "Xantor Xelvan")
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    places = _replacements(written, VARIANTS, _spans(entities))
    assert all("xelvan" not in _words(place) for place in places), written


@pytest.mark.parametrize(
    "case", ["rejected_name", "qc_grace_vellion", "qc_xantor_avril"]
)
def test_desktop_words_that_do_not_count(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T11 (a guard; AC1, Lionel's Q-C preview): a name rejected first does
    not count, and a word of the document in small letters still does not:
    the pseudonym is set without a message, written at the name and
    stored."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    if case == "rejected_name":
        text, key, typed = DOC, QZ_LOW, "Xantor Quentrix"
        sent = [_at(DOC, QZ_LOW, "PERSON", 0)]
        sd = _Single(
            qtbot,
            main_window,
            tmp_path,
            db,
            DOC,
            sent + [_at(DOC, "quentrix", "PERSON")],
        )
        sd.state.reject_entity(sd.row("quentrix").entity_id)
        pre(sd.row("quentrix").state == REJECTED, "« quentrix » rejected")
    else:
        text, key = QCDOC, QZ
        typed = "Grace Vellion" if case == "qc_grace_vellion" else "Xantor Avril"
        sent = [_at(QCDOC, QZ, "PERSON")]
        sd = _Single(qtbot, main_window, tmp_path, db, QCDOC, sent)
    row = sd.row(key)
    sd.dialog(monkeypatch, row.entity_id, typed)
    assert dialogs.calls == [], dialogs.calls
    assert row.custom_pseudonym == typed
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    assert _replacements(written, text, _spans(sent)) == [typed], written
    stored = _stored(db, key, "PERSON")
    assert stored is not None and stored[3] == typed


def test_desktop_pending_word_blocks_until_rejected(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T12 (AC1, the PM's reading): a lowercase detection still to review
    blocks a pseudonym until it is rejected: "Grace Vellion" is refused next
    to a pending « grâce », then set once « grâce » is rejected, and
    written."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    name = _at(QCDOC, QZ, "PERSON")
    grace = _at(QCDOC, "grâce", "PERSON")
    sd = _Single(qtbot, main_window, tmp_path, db, QCDOC, [name, grace])
    pre(sd.row("grâce").state == PENDING, "« grâce » still to review")
    row = sd.row(QZ)
    sd.dialog(monkeypatch, row.entity_id, "Grace Vellion")
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.state.reject_entity(sd.row("grâce").entity_id)
    assert sd.row("grâce").state == REJECTED
    sd.dialog(monkeypatch, row.entity_id, "Grace Vellion")
    assert len(dialogs.calls) == 1, dialogs.calls
    assert row.custom_pseudonym == "Grace Vellion"
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    assert _replacements(written, QCDOC, _spans([name])) == ["Grace Vellion"], written


def test_desktop_org_pseudonym_compared_whole(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T13 (AC1, #8): an organisation's pseudonym is compared whole with the
    review's names: "Zorbaville" for the lowercase organisation
    « zorbaville » is refused."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    org = _at(ORG_DOC, "zorbaville", "ORG", 0)
    sd = _Single(qtbot, main_window, tmp_path, db, ORG_DOC, [org])
    row = sd.row("zorbaville")
    sd.dialog(monkeypatch, row.entity_id, "Zorbaville")
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls
    place = _replacements(written, ORG_DOC, _spans([org]))[0]
    assert _fold(place) != "zorbaville", written
    stored = _stored(db, "zorbaville", "ORG")
    assert stored is not None and stored[3] == place


# ---------------------------------------------------------------------------
# Lionel's 10.16 Q1: a name marked after the pseudonym was set (T15)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", ["added_by_hand", "corrected_into", "accepted_again"])
def test_desktop_name_marked_after_the_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T15 (AC1, AC5; Lionel's 10.16 Q1): "Xantor Zorbal" is set while
    « zorbal » is no name and in small letters; « zorbal » then becomes a
    name (added by hand, a row corrected into it, or a rejected row accepted
    again): finalization stops with Lionel's new reason, the review stays
    open and no row is stored."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    start = ADDED_LATER.find("zorbal.")
    detected = [_at(ADDED_LATER, QZ_LOW, "PERSON", 0)]
    if case == "corrected_into":
        detected.append(_at(ADDED_LATER, "zorba", "PERSON", start))
    elif case == "accepted_again":
        detected.append(_at(ADDED_LATER, "zorbal", "PERSON", start))
    sd = _Single(qtbot, main_window, tmp_path, db, ADDED_LATER, detected)
    if case == "accepted_again":
        sd.state.reject_entity(sd.row("zorbal").entity_id)
        pre(sd.row("zorbal").state == REJECTED, "« zorbal » rejected")
    row = sd.row(QZ_LOW)
    sd.dialog(monkeypatch, row.entity_id, "Xantor Zorbal")
    pre(
        dialogs.calls == [] and row.custom_pseudonym == "Xantor Zorbal",
        f"set without a message: {dialogs.calls!r}",
    )
    if case == "added_by_hand":
        sd.state.add_entity("zorbal", "PERSON", start, start + len("zorbal"))
    elif case == "corrected_into":
        sd.state.modify_entity_text(
            sd.row("zorba").entity_id, "zorbal", start, start + len("zorbal")
        )
    else:
        sd.state.accept_entity(sd.row("zorbal").entity_id)
    sd.accept_pending()
    pre(
        any(e.text == "zorbal" for e in sd.state.expand_validated_entities()),
        "« zorbal » sent",
    )
    written = sd.finalize(dialogs)
    assert written is None, written  # expected failure
    assert len(dialogs.calls) == 1 and dialogs.calls[0][1] == IN_DOCUMENT, dialogs.calls
    assert main_window.current_screen_name() == "validation"
    assert _stored(db, QZ_LOW, "PERSON") is None
