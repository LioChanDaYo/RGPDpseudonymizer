"""Story 11.5: the desktop review list shows the pseudonym that will be
written (T20-T26, T29, T34-T37).

Written by the BMAD dev agent (Claude), tests first. SD = single document:
the real ``DetectionWorker`` run synchronously with detection replaced, the
real ``ValidationScreen`` and the real ``FinalizationWorker``; the written
text is read from the results screen (Story 10.11's harness). AR = batch
review through the batch screen's ``_on_validation_required``, without the
worker thread. BW = a real batch run through the real ``BatchWorker``
thread, only detection replaced (Story 10.10's harness). What the end
reported is read by wrapping ``DocumentProcessor.finalize_document``.

The library's draw is the stand-in of ``test_review_list_written_pseudonym``
(each list walked from its first value, one counter per list's contents), so
on the unfixed code the end's draw differs from the list's. The harnesses
here check their preconditions with ``pytest.fail("PRE: ...")`` (``pre``),
never with an ``assert``, so a strict ``xfail(raises=AssertionError)`` never
absorbs a broken harness. The first ``assert`` after them is the expected
failure on the unfixed code (``# expected failure``). Invented names only.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QInputDialog

import gdpr_pseudonymizer.core.document_processor as processor_module
import gdpr_pseudonymizer.data.database as database_module
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _replacements,
    pre,
)
from tests.unit.test_review_list_written_pseudonym import (
    DB_PS,
    LOCATION,
    ONE_DOC,
    PERSON,
    PLACE,
    PLACE_DOC,
    TITLE_DOC,
    TITLED,
    TWO_DOC,
    WRITTEN,
    ZM,
    ZQ,
    ZQ_CUT,
    _changed,
    _Draws,
    _is_person_draw,
    _places,
    _row,
    _store,
    install_draws,
)

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 10.10's test_batch_review_real_worker.py). This is a
# warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

WAIT_MS = 60000
PENDING = EntityReviewState.PENDING

TITLE = "Story 11.5 tests first: a stored titled name loses its title in the list"
THEME = "Story 11.5 tests first: the desktop batch previews ignore the theme"
UPDATE = (
    "Story 11.5 tests first: the desktop list does not update after a type "
    "change or a custom pseudonym"
)

LONE_AFTER = f"{ZQ} a signé le contrat. Zorbal a signé le contrat."
TWICE = f"{ZQ} a signé le contrat. {ZQ} a signé le contrat."


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


# ---------------------------------------------------------------------------
# Helpers (preconditions with pre)
# ---------------------------------------------------------------------------


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    pre(text[start : start + len(name)] == name, f"slice {name!r} at {start}")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _first(text: str, name: str, entity_type: str) -> DetectedEntity:
    return _at(text, name, entity_type, text.find(name))


def _new_db(tmp_path: Path) -> str:
    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    return db


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


class _Ends:
    """Records every ``finalize_document`` result (what the end reported)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.results: list[Any] = []
        real = DocumentProcessor.finalize_document
        recorder = self

        def finalize(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = real(self, *args, **kwargs)
            recorder.results.append(result)
            return result

        monkeypatch.setattr(DocumentProcessor, "finalize_document", finalize)

    def changed(self) -> list[tuple[str, str, str, str]] | None:
        pre(len(self.results) == 1, f"one document written: {len(self.results)}")
        pre(self.results[0].success, f"written: {self.results[0].error_message}")
        return _changed(self.results[0])


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
        pytest.fail(f"PRE: a detection result: {result!r}")
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
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        self.text = text
        path = tmp_path / "doc.txt"
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
        pre(len(rows) == 1, f"one row {text!r}: {len(rows)}")
        return rows[0]

    def shown(self, text: str) -> str:
        return self.state.get_pseudonym(self.row(text).entity_id)

    def accept_pending(self) -> None:
        for review in self.state.get_all_entities():
            if review.state == PENDING:
                self.state.accept_entity(review.entity_id)

    def finalize(self, dialogs: _Dialogs) -> str:
        """Every pending row accepted, finalized with the real worker; the
        written text (PRE: the results screen is reached)."""
        self.accept_pending()
        before = len(dialogs.calls)
        self.vs._start_finalization()
        self.qtbot.waitUntil(
            lambda: self.mw.current_screen_name() == "results"
            or len(dialogs.calls) > before,
            timeout=WAIT_MS,
        )
        pre(self.mw.current_screen_name() == "results", f"written: {dialogs.calls}")
        results = self.mw.stack.widget(self.mw._screens["results"])
        return Path(results._temp_path).read_text(encoding="utf-8")


def _batch_state(
    main_window: Any, db: str, text: str, entities: list[DetectedEntity]
) -> GUIValidationState:
    """Batch validation of one document through the batch screen (one row per
    detection), as Story 10.10's ``_batch_state``."""
    from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

    main_window.navigate_to("batch")
    bs = main_window.stack.currentWidget()
    pre(isinstance(bs, BatchScreen), "batch screen")
    bs._db_path, bs._passphrase, bs._validation_contexts = db, PASSPHRASE, {}
    bs._on_validation_required(
        [DetectedEntity(**vars(e)) for e in entities], text, 0, 1
    )
    state = main_window.stack.currentWidget().validation_state
    if state is None:
        pytest.fail("PRE: review shown")
    pre(len(state.get_all_entities()) == len(entities), "one row each")
    return state


class _Batch:
    """A real batch run with validation per document; only detection replaced
    (Story 10.10's harness, test_batch_review_real_worker.py)."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        text: str,
        entities: list[DetectedEntity],
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        source_dir = tmp_path / "in"
        source_dir.mkdir()
        self.out = tmp_path / "out"
        self.db = _new_db(tmp_path)
        self.entities = entities
        path = source_dir / "doc0.txt"
        path.write_text(text, encoding="utf-8")
        main_window.show()
        main_window.navigate_to("batch")
        self.bs = main_window.stack.currentWidget()
        pre(isinstance(self.bs, BatchScreen), "batch screen")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        self.bs._files = [path]
        self.bs._output_input.setText(str(self.out))
        self.bs._validate_checkbox.setChecked(True)

    def _detect(self, text: str) -> list[DetectedEntity]:
        return [DetectedEntity(**vars(e)) for e in self.entities]

    def run(self, body: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Run the batch; ``body`` drives the review. Returns what ``body``
        recorded."""
        record: dict[str, Any] = {}
        with patch.object(
            DocumentProcessor, "_detect_and_filter_entities", side_effect=self._detect
        ):
            self.bs._launch_worker(self.db, PASSPHRASE)
            try:
                body(record)
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)
            finally:
                if self.bs._worker is not None:
                    self.bs._worker.cancel()
                    self.qtbot.waitUntil(
                        lambda: self.bs._worker is None, timeout=WAIT_MS
                    )
        return record

    def wait_doc(self) -> GUIValidationState:
        """Wait until the document is waiting; return its review state."""
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=WAIT_MS,
        )
        state: GUIValidationState = vs.validation_state
        return state

    def accept_pending_and_validate(self) -> None:
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        self.vs.finalize_button.click()

    def output(self) -> str:
        path = self.out / "doc0_pseudonymized.txt"
        pre(path.exists(), f"output written: {path}")
        return path.read_text(encoding="utf-8")


def _one_row(state: GUIValidationState) -> Any:
    rows = state.get_all_entities()
    pre(len(rows) == 1, f"one row: {len(rows)}")
    return rows[0]


def _spans(entities: list[DetectedEntity]) -> list[tuple[int, int]]:
    return sorted((e.start_pos, e.end_pos) for e in entities)


# ---------------------------------------------------------------------------
# T20-T24, T26: the list shows what is written
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
@pytest.mark.parametrize("case", ["one_name", "two_people_one_first_name", "title"])
def test_desktop_list_shows_what_is_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws, case
) -> None:
    """T20 (AC3): each row's "→ X" is the text written at each place of its
    name, and the saved pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    text, names = {
        "one_name": (ONE_DOC, [ZQ]),
        "two_people_one_first_name": (TWO_DOC, [ZQ, ZM]),
        "title": (TITLE_DOC, [TITLED]),
    }[case]
    entities = [_first(text, name, PERSON) for name in names]
    sd = _Single(qtbot, main_window, tmp_path, db, text, entities)
    shown = [sd.shown(name) for name in names]
    pre(all(shown), f"every row shows a pseudonym: {shown}")
    written = _replacements(sd.finalize(dialogs), text, _spans(entities))
    assert written == shown  # expected failure
    saved = [_row(db, name, PERSON).pseudonym_full for name in names]
    assert saved == [value.removeprefix("Mme ") for value in shown]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=TITLE)
@pytest.mark.parametrize("case", ["single", "batch"])
def test_desktop_saved_titled_name_keeps_its_title(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws, case
) -> None:
    """T21 (AC9): a stored name found with a title shows the title in front
    of its stored pseudonym."""
    db = _new_db(tmp_path)
    _store(db, ZQ, PERSON, DB_PS, "Zorbal", "Quentrix")
    entities = [_first(TITLE_DOC, TITLED, PERSON)]
    if case == "single":
        sd = _Single(qtbot, main_window, tmp_path, db, TITLE_DOC, entities)
        state = sd.state
    else:
        state = _batch_state(main_window, db, TITLE_DOC, entities)
    row = _one_row(state)
    pre(state.is_entity_known(row.entity_id), "the stored name is known")
    shown = state.get_pseudonym(row.entity_id)
    assert shown == f"Mme {DB_PS}"  # expected failure


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=THEME)
def test_desktop_batch_previews_use_the_theme_and_are_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T22 (AC4): the batch list's pseudonym comes from the batch's theme and
    is the one written."""
    main_window.config["default_theme"] = "star_wars"
    entities = [_first(ONE_DOC, ZQ, PERSON)]
    batch = _Batch(qtbot, main_window, tmp_path, ONE_DOC, entities)

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc()
        record["shown"] = state.get_pseudonym(_one_row(state).entity_id)
        batch.accept_pending_and_validate()

    shown = batch.run(body).get("shown", "")
    pre(bool(shown), "the row shows a pseudonym")
    assert _is_person_draw(shown, "star_wars")  # expected failure
    assert _replacements(batch.output(), ONE_DOC, _spans(entities)) == [shown]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_desktop_ok_unchanged_keeps_the_shown_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T23 (AC10, Q-H): OK on the pre-filled pseudonym sets no custom
    pseudonym, and the file holds the pseudonym shown."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    entities = [_first(ONE_DOC, ZQ, PERSON)]
    sd = _Single(qtbot, main_window, tmp_path, db, ONE_DOC, entities)
    row = sd.row(ZQ)
    prefilled = sd.state.get_pseudonym(row.entity_id)
    pre(" " in prefilled, f"a suggestion: {prefilled!r}")
    _type_in(monkeypatch, prefilled)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    pre(dialogs.calls == [], "no message")
    customs = sd.state.get_custom_pseudonyms()
    written = _replacements(sd.finalize(dialogs), ONE_DOC, _spans(entities))
    assert written == [prefilled]  # expected failure
    assert customs == {}


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_desktop_corrected_text_keeps_the_shown_pseudonym(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T24 (Lionel's answer 1): a name's text corrected in the review keeps
    the pseudonym shown."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    sd = _Single(
        qtbot, main_window, tmp_path, db, ONE_DOC, [_at(ONE_DOC, ZQ_CUT, PERSON, 0)]
    )
    row = sd.row(ZQ_CUT)
    before = sd.state.get_pseudonym(row.entity_id)
    pre(" " in before, f"a suggestion: {before!r}")
    _type_in(monkeypatch, ZQ)
    sd.vs._show_modify_text_dialog(row.entity_id)
    pre(row.user_modification == ZQ, f"corrected: {row.user_modification!r}")
    written = _replacements(sd.finalize(dialogs), ONE_DOC, [(0, len(ZQ))])
    assert written == [before]  # expected failure
    assert sd.state.get_pseudonym(row.entity_id) == before


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_desktop_two_rows_corrected_into_one_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T26 (AC6): two rows that showed different pseudonyms end as one name:
    one of them is written at every place, the other is reported."""
    dialogs = _Dialogs(monkeypatch)
    ends = _Ends(monkeypatch)
    db = _new_db(tmp_path)
    second = TWICE.rfind(ZQ)
    entities = [_at(TWICE, ZQ_CUT, PERSON, 0), _at(TWICE, ZQ, PERSON, second)]
    sd = _Single(qtbot, main_window, tmp_path, db, TWICE, entities)
    cut, full = sd.row(ZQ_CUT), sd.row(ZQ)
    s1 = sd.state.get_pseudonym(cut.entity_id)
    s2 = sd.state.get_pseudonym(full.entity_id)
    pre(bool(s1) and bool(s2) and s1 != s2, f"two previews: {s1!r} {s2!r}")
    _type_in(monkeypatch, ZQ)
    sd.vs._show_modify_text_dialog(cut.entity_id)
    pre(cut.user_modification == ZQ, f"corrected: {cut.user_modification!r}")
    spans = [(0, len(ZQ)), (second, second + len(ZQ))]
    written = _replacements(sd.finalize(dialogs), TWICE, spans)
    other = s2 if written[0] == s1 else s1
    changed = ends.changed()
    assert changed == [(ZQ, PERSON, other, written[0])]  # expected failure
    assert written == [written[0], written[0]] and written[0] in (s1, s2)


def test_desktop_saved_untitled_name_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T29 (control): a stored name without a title shows and writes its
    stored pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _store(db, ZQ, PERSON, DB_PS, "Zorbal", "Quentrix")
    entities = [_first(ONE_DOC, ZQ, PERSON)]
    sd = _Single(qtbot, main_window, tmp_path, db, ONE_DOC, entities)
    assert sd.shown(ZQ) == DB_PS
    assert _replacements(sd.finalize(dialogs), ONE_DOC, _spans(entities)) == [DB_PS]


# ---------------------------------------------------------------------------
# T25, T34-T37: the list updates at once (Lionel's answers 2 and 3)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=UPDATE)
@pytest.mark.parametrize("case", ["single", "batch"])
def test_desktop_type_change_updates_the_list_at_once(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws, case
) -> None:
    """T25 (AC19): a place retyped as a person shows a person's pseudonym at
    once; it is written, and nothing is reported."""
    ends = _Ends(monkeypatch)
    entities = [_first(PLACE_DOC, PLACE, LOCATION)]
    places = _places()
    if case == "single":
        dialogs = _Dialogs(monkeypatch)
        sd = _Single(
            qtbot, main_window, tmp_path, _new_db(tmp_path), PLACE_DOC, entities
        )
        row = sd.row(PLACE)
        pre(sd.state.get_pseudonym(row.entity_id) in places, "a place shown")
        sd.state.change_entity_type(row.entity_id, PERSON)
        shown = sd.state.get_pseudonym(row.entity_id)
        output = sd.finalize(dialogs)
    else:
        batch = _Batch(qtbot, main_window, tmp_path, PLACE_DOC, entities)

        def body(record: dict[str, Any]) -> None:
            state = batch.wait_doc()
            row = _one_row(state)
            record["before"] = state.get_pseudonym(row.entity_id)
            state.change_entity_type(row.entity_id, PERSON)
            record["shown"] = state.get_pseudonym(row.entity_id)
            batch.accept_pending_and_validate()

        record = batch.run(body)
        pre(record.get("before") in places, f"a place shown: {record}")
        shown = record["shown"]
        output = batch.output()
    assert shown not in places and _is_person_draw(shown)  # expected failure
    assert _replacements(output, PLACE_DOC, _spans(entities)) == [shown]
    assert ends.changed() == []


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=UPDATE)
def test_desktop_custom_pseudonym_updates_the_sharing_row_at_once(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T34 (AC19; Lionel's answer 3): a custom pseudonym on one of two names
    sharing a real first name shows its first part on the other row at once;
    that is written, and nothing is reported."""
    dialogs = _Dialogs(monkeypatch)
    ends = _Ends(monkeypatch)
    db = _new_db(tmp_path)
    entities = [_first(TWO_DOC, ZQ, PERSON), _first(TWO_DOC, ZM, PERSON)]
    sd = _Single(qtbot, main_window, tmp_path, db, TWO_DOC, entities)
    pre(not sd.shown(ZM).startswith("Dravin "), f"shown: {sd.shown(ZM)!r}")
    sd.state.change_pseudonym(sd.row(ZQ).entity_id, DB_PS)
    shown = sd.shown(ZM)
    first_part = shown.split(" ")[0]
    assert first_part == "Dravin"  # expected failure
    written = _replacements(sd.finalize(dialogs), TWO_DOC, _spans(entities))
    assert written == [DB_PS, shown]
    assert ends.changed() == []


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=UPDATE)
def test_desktop_lone_name_takes_the_custom_part_at_once(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """T35 (AC19; B32): in the batch review, a lone first name's row takes
    the custom pseudonym's first part at once."""
    entities = [
        _at(LONE_AFTER, ZQ, PERSON, 0),
        _at(LONE_AFTER, "Zorbal", PERSON, LONE_AFTER.rfind("Zorbal")),
    ]
    state = _batch_state(main_window, _new_db(tmp_path), LONE_AFTER, entities)
    full, lone = state.get_all_entities()
    pre(lone.entity.text == "Zorbal", "the lone row second")
    pre(state.get_pseudonym(lone.entity_id) != "Dravin", "not yet the part")
    state.change_pseudonym(full.entity_id, DB_PS)
    shown = state.get_pseudonym(lone.entity_id)
    assert shown == "Dravin"  # expected failure


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=UPDATE)
def test_desktop_undo_restores_the_list_without_the_database(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T36 (AC20): undo shows the previous pseudonym again and redo the one
    drawn, without opening the database."""
    sd = _Single(
        qtbot,
        main_window,
        tmp_path,
        _new_db(tmp_path),
        PLACE_DOC,
        [_first(PLACE_DOC, PLACE, LOCATION)],
    )
    row = sd.row(PLACE)
    before = sd.state.get_pseudonym(row.entity_id)
    pre(before in _places(), f"a place shown: {before!r}")
    sd.state.change_entity_type(row.entity_id, PERSON)
    after = sd.state.get_pseudonym(row.entity_id)
    assert after != before  # expected failure

    def closed(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("the database was opened")

    monkeypatch.setattr(processor_module, "open_database", closed)
    monkeypatch.setattr(database_module, "open_database", closed)
    sd.state.undo_stack.undo()
    undone = sd.state.get_pseudonym(row.entity_id)
    sd.state.undo_stack.redo()
    redone = sd.state.get_pseudonym(row.entity_id)
    assert (undone, redone) == (before, after)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=UPDATE)
def test_desktop_update_that_cannot_run(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """T37 (AC19): when the update cannot run, the retyped row shows nothing;
    the end draws a person's pseudonym and reports nothing."""
    dialogs = _Dialogs(monkeypatch)
    ends = _Ends(monkeypatch)

    def failing(*args: Any, **kwargs: Any) -> Any:
        raise OSError("database not reachable")

    monkeypatch.setattr(
        DocumentProcessor, "refresh_review_proposals", failing, raising=False
    )
    entities = [_first(PLACE_DOC, PLACE, LOCATION)]
    sd = _Single(qtbot, main_window, tmp_path, _new_db(tmp_path), PLACE_DOC, entities)
    row = sd.row(PLACE)
    pre(sd.state.get_pseudonym(row.entity_id) in _places(), "a place shown")
    sd.state.change_entity_type(row.entity_id, PERSON)
    shown = sd.state.get_pseudonym(row.entity_id)
    assert shown == ""  # expected failure
    written = _replacements(sd.finalize(dialogs), PLACE_DOC, _spans(entities))
    assert _is_person_draw(written[0])
    assert ends.changed() == []
