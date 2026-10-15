"""Story 10.11: a custom pseudonym in the desktop review (T1-T21, T7c, T9b).

"Changer le pseudonyme" sets a pseudonym of the user's own for a name. These
tests pin that it is written at every place of the name, stored in the
mapping database (split for a person, Lionel's Q4) and reused later, that the
pseudonyms Lionel's Q1, Q2, Q-C and Q-D refuse are refused with a message,
that a correction removes it (Q-E), and, in batch review, that it reaches
every place of the name (Q3) and follows the group like a correction (Q-B).

SD = single document: the real ``DetectionWorker`` run synchronously with
detection replaced, the real ``ValidationScreen`` and the real
``FinalizationWorker``; the written text is read from the results screen.
AR = batch review through the batch screen's ``_on_validation_required``,
without the worker thread. Each test asserts its preconditions (messages
start with "PRE:") before the behaviour under test; the first assertion after
them is the expected failure on the unfixed code. A refusal test asserts that
exactly one message was shown and that it is not empty, never its wording.
Invented names only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QInputDialog

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
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
MODIFIED = EntityReviewState.MODIFIED

QZ = "Quentrel Zorbalia"
CUSTOM = "Xantor Vellion"

ONE = (
    "Quentrel Zorbalia a signé avec Zorbaville. Le contrat est avec Quentrel Zorbalia."
)
PARTS = "Quentrel Zorbalia a signé. Le contrat est avec Zorbalia. Le projet est avec Quentrel."
LATER_LONE = "Zorbalia a signé le contrat."
REUSE = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est avec Zorbalia. Le projet est avec Quentrel."
)
CORR = "Quentrel Zorbalia a signé le contrat."
ORGDOC = "Zorbaville a signé."
TITLED = "Zorbal a signé avec M. Zorbal."
QCDOC = "Zorbaville a signé avec Quentrel Zorbalia en avril, grâce à son petit groupe."
HYPH = "Zorbal-Quentrix a signé avec Quentrel Zorbalia."
ONE_WORD = "Zorbal a signé avec Quentrel Zorbalia."
# As in Story 10.10's tests (test_validation_state_added_row.py,
# test_batch_review_real_worker.py).
SAINT = "Zorbal a signé avec Zorbal. Le projet est à Saint-Zorbal."
THREE = (
    "Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia Quentrix. "
    "Le projet est signé avec Quentrel Zorbalia Quentrix."
)
DOC1 = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    assert text[start : start + len(name)] == name, "PRE: entity slice"
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _all(text: str, name: str, entity_type: str) -> list[DetectedEntity]:
    """Every whole-word occurrence of ``name`` in ``text``."""
    found: list[DetectedEntity] = []
    start = text.find(name)
    while start >= 0:
        end = start + len(name)
        if (start == 0 or not text[start - 1].isalnum()) and (
            end == len(text) or not text[end].isalnum()
        ):
            found.append(_at(text, name, entity_type, start))
        start = text.find(name, start + 1)
    return found


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
    assert match is not None, f"text damaged or a span not replaced: {output!r}"
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


def _store_earlier(
    tmp_path: Path, db: str, text: str, entities: list[DetectedEntity]
) -> None:
    """Store names as an earlier document would (no custom pseudonym)."""
    output = tmp_path / f"earlier_{len(list(tmp_path.glob('earlier_*')))}.txt"
    result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
        text, entities, str(output)
    )
    assert result.success, "PRE: earlier document stored"


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
    assert len(finished) == 1, "PRE: detection finished once"
    result = finished[0]
    assert isinstance(result, DetectionResult), "PRE: detection result"
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
        assert isinstance(self.vs, ValidationScreen), "PRE: validation screen"
        main_window.show()
        self.vs.start_validation(result)
        main_window.navigate_to("validation")
        state = self.vs.validation_state
        assert state is not None, "PRE: review shown"
        self.state: GUIValidationState = state

    def row(self, text: str) -> Any:
        rows = [r for r in self.state.get_all_entities() if r.entity.text == text]
        assert len(rows) == 1, f"PRE: one row {text!r}"
        return rows[0]

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


def _one_entities() -> list[DetectedEntity]:
    return _all(ONE, QZ, "PERSON") + [
        _at(ONE, "Zorbaville", "ORG", ONE.find("Zorbaville"))
    ]


def _batch_state(
    main_window: Any, db: str, text: str, entities: list[DetectedEntity]
) -> GUIValidationState:
    """Batch validation of one document through the batch screen (one row per
    detection), as Story 10.10's ``_batch_state``."""
    from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

    main_window.navigate_to("batch")
    bs = main_window.stack.currentWidget()
    assert isinstance(bs, BatchScreen), "PRE: batch screen"
    bs._db_path, bs._passphrase, bs._validation_contexts = db, PASSPHRASE, {}
    bs._on_validation_required(
        [DetectedEntity(**vars(e)) for e in entities], text, 0, 1
    )
    state = main_window.stack.currentWidget().validation_state
    assert state is not None, "PRE: review shown"
    assert len(state.get_all_entities()) == len(entities), "PRE: one row each"
    return state


def _saint(
    main_window: Any, tmp_path: Path
) -> tuple[GUIValidationState, Any, Any, Any]:
    """SAINT in batch review: rows 1, 2 and 3 (row 3 is Saint-Zorbal)."""
    entities = [
        _at(SAINT, "Zorbal", "PERSON", 0),
        _at(SAINT, "Zorbal", "PERSON", SAINT.find("Zorbal", 1)),
        _at(SAINT, "Zorbal", "PERSON", SAINT.find("Saint-Zorbal") + 6),
    ]
    state = _batch_state(main_window, _new_db(tmp_path), SAINT, entities)
    r1, r2, r3 = state.get_all_entities()
    return state, r1, r2, r3


# ---------------------------------------------------------------------------
# Single document (SD): written, stored, reused
# ---------------------------------------------------------------------------


def test_custom_pseudonym_written_and_stored(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T1 (AC1, AC2, Q4): the dialog's pseudonym is written at every place of
    the name and stored, split at its last space."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    person = sd.row(QZ)
    _type_in(monkeypatch, CUSTOM)
    sd.vs._show_change_pseudonym_dialog(person.entity_id)
    assert dialogs.calls == [], "PRE: no message"
    assert sd.state.get_pseudonym(person.entity_id) == CUSTOM, "PRE: list shows it"
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, "PRE: finalized"
    parts = _replacements(written, ONE, _spans(_one_entities()))
    assert [parts[0], parts[2]] == [CUSTOM, CUSTOM], written  # expected failure
    assert "Zorbaville" not in parts[1]
    assert _stored(db, QZ, "PERSON") == (
        QZ,
        "Quentrel",
        "Zorbalia",
        CUSTOM,
        "Xantor",
        "Vellion",
    )


def test_lone_first_and_last_name_take_the_parts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T2 (Q4, same document): a lone last name and a lone first name take
    the parts of the custom pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    entities = [
        _at(PARTS, QZ, "PERSON", 0),
        _at(PARTS, "Zorbalia", "PERSON", PARTS.find("avec Zorbalia") + 5),
        _at(PARTS, "Quentrel", "PERSON", PARTS.rfind("Quentrel")),
    ]
    sd = _Single(qtbot, main_window, tmp_path, db, PARTS, entities)
    assert len(sd.state.get_all_entities()) == 2, "PRE: two rows"
    sd.state.change_pseudonym(sd.row(QZ).entity_id, CUSTOM)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, "PRE: finalized"
    got = _replacements(written, PARTS, _spans(entities))
    assert got == [CUSTOM, "Vellion", "Xantor"], written  # expected failure


def test_one_word_custom_pseudonym_has_no_parts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T3 (Q4, one word): stored for the full name only; a later lone last
    name gets its own pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    sd.state.change_pseudonym(sd.row(QZ).entity_id, "Xantor")
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, "PRE: finalized"
    parts = _replacements(written, ONE, _spans(_one_entities()))
    assert [parts[0], parts[2]] == ["Xantor", "Xantor"], written  # expected failure
    assert _stored(db, QZ, "PERSON") == (QZ, None, None, "Xantor", None, None)
    later = [_at(LATER_LONE, "Zorbalia", "PERSON", 0)]
    sd2 = _Single(qtbot, main_window, tmp_path, db, LATER_LONE, later, "later.txt")
    sd2.accept_pending()
    written2 = sd2.finalize(dialogs)
    assert written2 is not None, "PRE: later document finalized"
    (lone,) = _replacements(written2, LATER_LONE, _spans(later))
    assert lone != "Xantor" and "orbal" not in lone, written2


def test_later_document_reuses_custom_and_parts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T4 (AC2, Q4): a later document shows and writes the custom pseudonym,
    and its parts for the first or last name alone."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    sd.state.change_pseudonym(sd.row(QZ).entity_id, CUSTOM)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, "PRE: finalized"
    first = _replacements(written, ONE, _spans(_one_entities()))[0]
    assert first == CUSTOM, written  # expected failure
    later = [
        _at(REUSE, QZ, "PERSON", 0),
        _at(REUSE, "Zorbalia", "PERSON", REUSE.find("avec Zorbalia") + 5),
        _at(REUSE, "Quentrel", "PERSON", REUSE.rfind("Quentrel")),
    ]
    sd2 = _Single(qtbot, main_window, tmp_path, db, REUSE, later, "reuse.txt")
    known = sd2.row(QZ)
    assert known.state == CONFIRMED
    assert sd2.state.get_pseudonym(known.entity_id) == CUSTOM
    sd2.accept_pending()
    written2 = sd2.finalize(dialogs)
    assert written2 is not None, "PRE: later document finalized"
    assert _replacements(written2, REUSE, _spans(later)) == [
        CUSTOM,
        "Vellion",
        "Xantor",
    ], written2


# ---------------------------------------------------------------------------
# Single document (SD): refusals (Q1, Q2, Q-C, Q-D)
# ---------------------------------------------------------------------------


def test_name_already_stored_is_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T5 (Q1): a stored name keeps its pseudonym; the dialog says why."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    before = _stored(db, QZ, "PERSON")
    assert before is not None, "PRE: stored earlier"
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    person = sd.row(QZ)
    assert person.state == CONFIRMED, "PRE: known"
    _type_in(monkeypatch, CUSTOM)
    sd.vs._show_change_pseudonym_dialog(person.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert person.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    assert _replacements(written, ONE, _spans(_one_entities()))[0] == before[3]
    assert _stored(db, QZ, "PERSON") == before


def test_pseudonym_of_another_name_is_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T6 (Q2): the stored pseudonym of another name is refused."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, ORGDOC, [_at(ORGDOC, "Zorbaville", "ORG", 0)])
    other = _stored(db, "Zorbaville", "ORG")
    assert other is not None, "PRE: other name stored"
    sd = _Single(qtbot, main_window, tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    person = sd.row(QZ)
    _type_in(monkeypatch, other[3])
    sd.vs._show_change_pseudonym_dialog(person.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert person.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[3] != other[3]


@pytest.mark.parametrize(
    "case",
    [
        "other_name",
        "same_name",
        "other_name_lowercase",
        "part_is_real",
        "one_word_name",
        "hyphenated_whole",
        "hyphenated_last_part",
        "hyphenated_first_part",
    ],
)
def test_real_name_of_the_document_is_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T7 (Q2, Q-C; PO R1, F1): a capitalised real name of the document, or a
    part of the pseudonym that is one, is refused; the file and the row do not
    take it."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    if case == "one_word_name":
        text = ONE_WORD
        entities = [
            _at(text, "Zorbal", "PERSON", 0),
            _at(text, QZ, "PERSON", text.find(QZ)),
        ]
        name, typed = "Zorbal", "Xantor Zorbalia"
    elif case.startswith("hyphenated"):
        text = HYPH
        entities = [_at(text, QZ, "PERSON", text.find(QZ))]
        name = QZ
        typed = {
            "hyphenated_whole": "Zorbal-Quentrix",
            "hyphenated_last_part": "Xantor Zorbal-Quentrix",
            "hyphenated_first_part": "Zorbal-Quentrix Xantor",
        }[case]
    else:
        text, entities, name = ONE, _one_entities(), QZ
        typed = {
            "other_name": "Zorbaville",
            "same_name": QZ,
            "other_name_lowercase": "zorbaville",
            "part_is_real": "Xantor Zorbaville",
        }[case]
    sd = _Single(qtbot, main_window, tmp_path, db, text, entities)
    row = sd.row(name)
    _type_in(monkeypatch, typed)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    assert _replacements(written, text, _spans(entities))[0] != typed
    stored = _stored(db, name, "PERSON")
    assert stored is not None and stored[3] != typed


@pytest.mark.parametrize(
    "typed, refused",
    [
        ("Xantor Zorbalia", True),
        ("Xantor Zorbaville", True),
        ("Grace Vellion", False),
        ("Xantor Avril", False),
    ],
    ids=["found_name_part", "missed_capitalised", "lowercase_grace", "lowercase_avril"],
)
def test_lionel_qc_preview(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, typed, refused
) -> None:
    """T7c (Q-C "Capitalised words", Lionel's preview): the detector found
    "Quentrel Zorbalia" and missed "Zorbaville"; a capitalised word of the
    document is refused, a word in small letters is not."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    entities = [_at(QCDOC, QZ, "PERSON", QCDOC.find(QZ))]
    sd = _Single(qtbot, main_window, tmp_path, db, QCDOC, entities)
    row = sd.row(QZ)
    _type_in(monkeypatch, typed)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    if refused:
        assert dialogs.one_message(), dialogs.calls  # expected failure
        assert row.custom_pseudonym is None
        return
    assert dialogs.calls == [] and row.custom_pseudonym == typed, "PRE: accepted"
    written = sd.finalize(dialogs)
    assert written is not None, "PRE: finalized"
    got = _replacements(written, QCDOC, _spans(entities))
    assert got == [typed], written  # expected failure


def test_same_custom_for_two_names_is_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T8 (Q2, AC3): the custom pseudonym another name of this review already
    holds is refused."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    sd.state.change_pseudonym(sd.row(QZ).entity_id, CUSTOM)
    org = sd.row("Zorbaville")
    _type_in(monkeypatch, CUSTOM)
    sd.vs._show_change_pseudonym_dialog(org.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert org.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    assert _replacements(written, ONE, _spans(_one_entities()))[1] != CUSTOM
    stored = _stored(db, "Zorbaville", "ORG")
    assert stored is not None and stored[3] != CUSTOM


@pytest.mark.parametrize(
    "case",
    [
        "other_last_name",
        "same_first_name",
        "one_word_name",
    ],
)
def test_part_of_another_names_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T9 (Q2 with Q4's parts, Story 2.8; PO R1): a part that already stands
    for another real last name is refused, also as the last part on a
    one-word name; the part a real first name already has is accepted
    (same_first_name, a guard)."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[4] and stored[5], "PRE: parts stored"
    if case == "other_last_name":
        name = "Quentrix Zorbal"
    elif case == "one_word_name":
        name = "Zorbal"
    else:
        name = "Quentrel Zorbal"
    text = f"{name} a signé le contrat."
    sd = _Single(qtbot, main_window, tmp_path, db, text, [_at(text, name, "PERSON", 0)])
    row = sd.row(name)
    typed = (
        f"{stored[4]} Vellion" if case == "same_first_name" else f"Xantor {stored[5]}"
    )
    _type_in(monkeypatch, typed)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    if case == "same_first_name":
        assert dialogs.calls == [] and row.custom_pseudonym == typed
        return
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None


@pytest.mark.parametrize("kind", ["first_name", "last_name", "both"])
def test_name_with_a_stored_part_requires_it(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, kind
) -> None:
    """T9b (Q-D "Refuse"; PO F3): a real first (last) name that already has a
    stored part refuses a pseudonym whose first (last) part differs; the
    example the message offers (a data value) is then accepted, written and
    stored."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[4] and stored[5], "PRE: parts stored"
    if kind == "both":
        other_text = "Quentrix Zorbal a signé le contrat."
        _store_earlier(
            tmp_path, db, other_text, [_at(other_text, "Quentrix Zorbal", "PERSON", 0)]
        )
        other = _stored(db, "Quentrix Zorbal", "PERSON")
        assert other is not None and other[5], "PRE: Zorbal has a part"
        name, good = "Quentrel Zorbal", f"{stored[4]} {other[5]}"
        expected_row = (
            "Quentrel Zorbal",
            "Quentrel",
            "Zorbal",
            good,
            stored[4],
            other[5],
        )
    elif kind == "first_name":
        name, good = "Quentrel Zorbal", f"{stored[4]} Vellion"
        expected_row = (
            "Quentrel Zorbal",
            "Quentrel",
            "Zorbal",
            good,
            stored[4],
            "Vellion",
        )
    else:
        name, good = "Quentrix Zorbalia", f"Xantor {stored[5]}"
        expected_row = (
            "Quentrix Zorbalia",
            "Quentrix",
            "Zorbalia",
            good,
            "Xantor",
            stored[5],
        )
    text = f"{name} a signé le contrat."
    entities = [_at(text, name, "PERSON", 0)]
    sd = _Single(qtbot, main_window, tmp_path, db, text, entities)
    row = sd.row(name)
    _type_in(monkeypatch, CUSTOM)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    assert good in dialogs.calls[0][1]  # the example value (%3), not the wording
    _type_in(monkeypatch, good)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    assert len(dialogs.calls) == 1 and row.custom_pseudonym == good
    written = sd.finalize(dialogs)
    assert written is not None
    assert _replacements(written, text, _spans(entities)) == [good]
    assert _stored(db, name, "PERSON") == expected_row


def test_real_name_stored_in_database_is_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T10 (Q-C, Q-C2): a full name stored from an earlier document is
    refused."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, ORGDOC, [_at(ORGDOC, "Zorbaville", "ORG", 0)])
    sd = _Single(qtbot, main_window, tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    row = sd.row(QZ)
    _type_in(monkeypatch, "Zorbaville")
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert row.custom_pseudonym is None
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    assert _replacements(written, CORR, [(0, len(QZ))]) != ["Zorbaville"]
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[3] != "Zorbaville"


# ---------------------------------------------------------------------------
# Single document (SD): correction, undo, other types, the last check
# ---------------------------------------------------------------------------


def test_correction_removes_custom_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T11 (AC5, Q-E; PO F6): a correction removes the custom pseudonym; one
    undo brings back the old name and its pseudonym; the stored name keeps
    its own pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    before = _stored(db, QZ, "PERSON")
    assert before is not None, "PRE: stored earlier"
    sd = _Single(
        qtbot, main_window, tmp_path, db, CORR, [_at(CORR, "Quentrel", "PERSON", 0)]
    )
    row = sd.row("Quentrel")
    typed = f"{before[4]} Vellion"  # Q-D: "Quentrel" already has before[4]
    _type_in(monkeypatch, typed)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    assert dialogs.calls == [] and row.custom_pseudonym == typed, "PRE: set"
    _type_in(monkeypatch, QZ)
    sd.vs._show_modify_text_dialog(row.entity_id)
    assert row.user_modification == QZ, "PRE: corrected"
    assert row.custom_pseudonym is None  # expected failure
    sd.state.undo_stack.undo()
    assert row.user_modification is None and row.custom_pseudonym == typed
    sd.state.undo_stack.redo()
    assert row.user_modification == QZ and row.custom_pseudonym is None
    written = sd.finalize(dialogs)
    assert written is not None
    assert _replacements(written, CORR, [(0, len(QZ))]) == [before[3]]
    assert _stored(db, QZ, "PERSON") == before


def test_undone_custom_pseudonym_is_never_stored(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T12 (AC5, a guard): an undone custom pseudonym is neither written nor
    stored."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    person = sd.row(QZ)
    sd.state.change_pseudonym(person.entity_id, CUSTOM)
    sd.state.undo_stack.undo()
    assert person.custom_pseudonym is None and person.state == PENDING, "PRE: undone"
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    parts = _replacements(written, ONE, _spans(_one_entities()))
    assert CUSTOM not in written and parts[0] == parts[2]
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[3] == parts[0]


def test_custom_pseudonym_on_org_has_no_parts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T13 (AC2): an organisation's custom pseudonym is written and stored
    whole, without parts."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    sd.state.change_pseudonym(sd.row("Zorbaville").entity_id, "Xantorville")
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    org = _replacements(written, ONE, _spans(_one_entities()))[1]
    assert org == "Xantorville", written  # expected failure
    assert _stored(db, "Zorbaville", "ORG") == (
        "Zorbaville",
        None,
        None,
        "Xantorville",
        None,
        None,
    )


def test_database_changed_meanwhile_nothing_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T14 (the last check; PO R9): another name took the pseudonym in the
    database after it was set: finalization stops with an error message,
    nothing is stored and the temporary output file stays empty."""
    import tempfile

    created: list[str] = []
    original = tempfile.NamedTemporaryFile

    def recording(*args: Any, **kwargs: Any) -> Any:
        handle = original(*args, **kwargs)
        created.append(handle.name)
        return handle

    monkeypatch.setattr(
        "gdpr_pseudonymizer.gui.workers.finalization_worker.tempfile.NamedTemporaryFile",
        recording,
    )
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    sd.state.change_pseudonym(sd.row(QZ).entity_id, CUSTOM)
    sd.accept_pending()
    with open_database(db, PASSPHRASE) as session:  # as another process would
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type="PERSON",
                full_name="Zorbal",
                pseudonym_full=CUSTOM,
                theme="neutral",
            )
        )
    written = sd.finalize(dialogs)
    assert written is None and len(dialogs.calls) == 1, written  # expected failure
    assert _stored(db, QZ, "PERSON") is None
    assert created and all(Path(name).stat().st_size == 0 for name in created)


def test_without_custom_pseudonym_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T15 (AC13, a guard): without a custom pseudonym nothing changes: one
    pseudonym per name, written and stored."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(qtbot, main_window, tmp_path, db, ONE, _one_entities())
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None
    parts = _replacements(written, ONE, _spans(_one_entities()))
    assert parts[0] == parts[2] and "orbal" not in written
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[3] == parts[0]


# ---------------------------------------------------------------------------
# Batch review (AR): reach, the "own" rule, undo and redo
# ---------------------------------------------------------------------------


def test_custom_reaches_every_place_undo_redo(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T16 (Q3, AC5; PO R7): every place of the name but the one rejected on
    its own; one undo reverts it everywhere, redo gives it back."""
    state, r1, r2, r3 = _saint(main_window, tmp_path)
    state.bulk_reject([r3.entity_id])
    assert [r1.state, r2.state, r3.state] == [PENDING, PENDING, REJECTED], "PRE"
    state.change_pseudonym(r1.entity_id, CUSTOM)
    shown = [state.get_pseudonym(r.entity_id) for r in (r1, r2, r3)]
    assert shown[:2] == [CUSTOM] * 2 and shown[2] != CUSTOM, shown  # expected failure
    assert [r1.state, r2.state, r3.state] == [MODIFIED, MODIFIED, REJECTED]
    state.undo_stack.undo()
    assert [r1.state, r2.state, r3.state] == [PENDING, PENDING, REJECTED]
    assert [r.custom_pseudonym for r in (r1, r2, r3)] == [None, None, None]
    state.undo_stack.redo()
    assert [r1.state, r2.state, r3.state] == [MODIFIED, MODIFIED, REJECTED]
    assert [r.custom_pseudonym for r in (r1, r2, r3)] == [CUSTOM, CUSTOM, None]


def test_custom_on_several_places_follows_the_group(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T17 (AC16, Q-B "Like a correction"): a custom pseudonym that reached
    several places follows the group, so a later reject of the name from
    another found place reaches them all."""
    state, r1, r2, r3 = _saint(main_window, tmp_path)
    state.change_pseudonym(r1.entity_id, CUSTOM)
    assert [r.state for r in (r1, r2, r3)] == [MODIFIED] * 3  # expected failure
    state.reject_entity(r2.entity_id)
    assert [r1.state, r2.state, r3.state] == [REJECTED, REJECTED, REJECTED]


def test_custom_on_one_place_alone_stays_own(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T18 (AC16, a guard): a custom pseudonym that reached one place alone is
    that place's own decision; a group reject skips it (10.10 Q5)."""
    state, r1, r2, r3 = _saint(main_window, tmp_path)
    state.bulk_reject([r2.entity_id, r3.entity_id])
    state.change_pseudonym(r1.entity_id, CUSTOM)
    assert [r1.state, r2.state, r3.state] == [MODIFIED, REJECTED, REJECTED], "PRE"
    state.reject_entity(r2.entity_id)
    assert [r1.state, r2.state, r3.state] == [MODIFIED, REJECTED, REJECTED]
    assert r1.custom_pseudonym == CUSTOM


def test_custom_reaches_titled_form(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T19 (AC1 reach): "M. Zorbal" is the same name as "Zorbal" for the file,
    so it takes the custom pseudonym too."""
    entities = [
        _at(TITLED, "Zorbal", "PERSON", 0),
        _at(TITLED, "M. Zorbal", "PERSON", TITLED.find("M. Zorbal")),
    ]
    state = _batch_state(main_window, _new_db(tmp_path), TITLED, entities)
    r1, r2 = state.get_all_entities()
    state.change_pseudonym(r1.entity_id, CUSTOM)
    shown = [state.get_pseudonym(r.entity_id) for r in (r1, r2)]
    assert shown == [CUSTOM, CUSTOM], shown  # expected failure
    assert [r1.state, r2.state] == [MODIFIED, MODIFIED]


def test_custom_on_added_place_reaches_found_places(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T20 (Q3): set on a place added by hand, it reaches the found places of
    the name, as a correction does (10.10)."""
    starts = [THREE.find(QZ), THREE.find(QZ, 1), THREE.rfind(QZ)]
    state = _batch_state(
        main_window,
        _new_db(tmp_path),
        THREE,
        [_at(THREE, QZ, "PERSON", starts[0]), _at(THREE, QZ, "PERSON", starts[1])],
    )
    r1, r2 = state.get_all_entities()
    state.accept_entity(r1.entity_id)
    assert [r1.state, r2.state] == [CONFIRMED, CONFIRMED], "PRE: found places accepted"
    added = state.add_entity(QZ, "PERSON", starts[2], starts[2] + len(QZ))
    state.change_pseudonym(added, CUSTOM)
    customs = [r1.custom_pseudonym, r2.custom_pseudonym]
    assert customs == [CUSTOM, CUSTOM], customs  # expected failure
    assert [r1.state, r2.state] == [MODIFIED, MODIFIED]


def test_dialog_refuses_a_stored_name_in_batch(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T21 (Q1 in batch review): the dialog checks the batch's database."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store_earlier(tmp_path, db, CORR, [_at(CORR, QZ, "PERSON", 0)])
    before = _stored(db, QZ, "PERSON")
    assert before is not None, "PRE: stored earlier"
    state = _batch_state(main_window, db, DOC1, _all(DOC1, QZ, "PERSON"))
    r1, r2 = state.get_all_entities()
    assert [r1.state, r2.state] == [CONFIRMED, CONFIRMED], "PRE: both rows known"
    vs = main_window.stack.widget(main_window._screens["validation"])
    _type_in(monkeypatch, CUSTOM)
    vs._show_change_pseudonym_dialog(r1.entity_id)
    assert dialogs.one_message(), dialogs.calls  # expected failure
    assert [r1.custom_pseudonym, r2.custom_pseudonym] == [None, None]
    assert _stored(db, QZ, "PERSON") == before
