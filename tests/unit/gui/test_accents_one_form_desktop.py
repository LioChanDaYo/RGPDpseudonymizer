"""Story 10.20: an accent stored as a separate mark, in the desktop app (T11,
T19, T24, T25, G1).

Written by the BMAD dev agent (Claude). Single document: the real
``DetectionWorker`` run synchronously with
``DocumentProcessor._detect_and_filter_entities`` replaced (not
``detect_entities``, so the document goes through the real reader), the real
``ValidationScreen`` and the real ``FinalizationWorker``; the written text is
read from the results screen. Batch: the real ``BatchScreen``,
``ValidationScreen`` and ``BatchWorker`` thread, with the same detection
replaced (Story 10.10's harness, as in Story 10.16's
``test_custom_pseudonym_fixes_batch_worker.py``). The stand-in detector finds
each name given in its composed and its decomposed spelling, in the text it
receives. A correction goes through the screen's own
``_show_modify_text_dialog``, a custom pseudonym through
``_show_change_pseudonym_dialog``, with ``QInputDialog.getText`` replaced;
the messages are recorded from ``ConfirmDialog.informational``. The database
screen's search and the review's filter field are set as the user types.

Every text is written composed in this file; a decomposed form is made at
run time with ``unicodedata.normalize("NFD", ...)``: no combining mark is
written in this file. Preconditions call ``pytest.fail("PRE: ...")``, never
``assert``; the first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and main-corpus words
only.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Sequence
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
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 10.10's test_batch_review_real_worker.py). This is a
# warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
PENDING = EntityReviewState.PENDING
PERSON = "PERSON"

ZO = "Zórbalia"
ZQ = "Zórbalia Quentrel"
VM = "Vorlan Mestrix"
XV = "Xantor Vellion"
XQ = "Xantor Quovix"
XVE = "Xantor Véllion"

A_TEXT = "Vorlan Mestrix valide. Le contrat avec Zórbalia. Signé : Zórbalia."
E_TEXT = "Zórbalia Quentrel a signé. Signé : Zórbalia Quentrel."
R_TEXT = "Le contrat avec Zórbalia Quentrel a signé."


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


FORMS: dict[str, Callable[[str], str]] = {"nfc": nfc, "nfd": nfd}


def _mixed() -> str:
    """« Zórbalia Quentrel a signé. » composed, then « Signé : Zórbalia
    Quentrel. » decomposed."""
    return f"{nfc('Zórbalia Quentrel a signé.')} {nfd('Signé : Zórbalia Quentrel.')}"


def _pre(condition: bool, what: str) -> None:
    """A precondition: fails with "PRE: ..." (``pytest.fail`` raises
    ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {what}")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _either_form(
    names: Sequence[tuple[str, str]],
) -> Callable[..., list[DetectedEntity]]:
    """Stand-in for ``_detect_and_filter_entities``: every occurrence of each
    (name, type) given, in its composed and its decomposed spelling, in the
    text it receives; an occurrence inside a longer one found is dropped."""

    def detect(text: str, entity_type_filter: Any = None) -> list[DetectedEntity]:
        found: list[DetectedEntity] = []
        for name, entity_type in names:
            for form in dict.fromkeys((nfc(name), nfd(name))):
                start = text.find(form)
                while start != -1:
                    found.append(
                        DetectedEntity(
                            text=form,
                            entity_type=entity_type,
                            start_pos=start,
                            end_pos=start + len(form),
                            confidence=0.9,
                            source="spacy",
                        )
                    )
                    start = text.find(form, start + 1)
        return [
            entity
            for entity in found
            if not any(
                other.start_pos <= entity.start_pos
                and entity.end_pos <= other.end_pos
                and other.end_pos - other.start_pos > entity.end_pos - entity.start_pos
                for other in found
            )
        ]

    return detect


def _new_db(tmp_path: Path) -> str:
    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    return db


def _save(db: str, rows: Sequence[tuple[str, str, str]]) -> None:
    """Rows saved in order, each with the exact name given: (full_name,
    type, pseudonym)."""
    with open_database(db, PASSPHRASE) as session:
        repo = SQLiteMappingRepository(session)
        for full_name, entity_type, pseudonym in rows:
            repo.save(
                Entity(
                    entity_type=entity_type,
                    full_name=full_name,
                    pseudonym_full=pseudonym,
                    theme="neutral",
                )
            )


def _rows(db: str) -> list[tuple[str, str, str]]:
    """Every stored row: (full_name, entity_type, pseudonym_full)."""
    with open_database(db, PASSPHRASE) as session:
        return [
            (row.full_name, row.entity_type, row.pseudonym_full)
            for row in SQLiteMappingRepository(session).find_all()
        ]


def _names(db: str) -> list[tuple[str, str]]:
    """Every stored (full_name, entity_type), sorted."""
    return sorted((name, entity_type) for name, entity_type, _ in _rows(db))


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


def _type_in(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """The next ``QInputDialog.getText`` returns ``text`` and OK."""
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: (text, True))
    )


class _Single:
    """One document reviewed in the desktop app, single-document mode."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        text: str,
        names: Sequence[tuple[str, str]],
        db: str | None = None,
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        self.db = db if db is not None else _new_db(tmp_path)
        path = tmp_path / "doc.txt"
        path.write_text(text, encoding="utf-8")
        finished: list[object] = []
        worker = DetectionWorker(
            file_path=str(path), db_path=self.db, passphrase=PASSPHRASE
        )
        worker.setAutoDelete(False)
        worker.signals.finished.connect(finished.append)
        with patch.object(
            DocumentProcessor,
            "_detect_and_filter_entities",
            side_effect=_either_form(names),
        ):
            worker.run()
        _pre(len(finished) == 1, "detection finished once")
        result = finished[0]
        if not isinstance(result, DetectionResult):
            pytest.fail("PRE: detection result")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        _pre(isinstance(self.vs, ValidationScreen), "validation screen")
        main_window.show()
        self.vs.start_validation(result)
        main_window.navigate_to("validation")
        state = self.vs.validation_state
        if state is None:
            pytest.fail("PRE: review shown")
        self.state = state

    def rows(self) -> list[Any]:
        """The review's rows, in document order."""
        return sorted(self.state.get_all_entities(), key=lambda r: r.entity.start_pos)

    def accept_pending(self) -> None:
        for review in self.state.get_all_entities():
            if review.state == PENDING:
                self.state.accept_entity(review.entity_id)

    def finalize(self, dialogs: _Dialogs) -> str | None:
        """Finalize with the real worker; the written text, or None when
        finalization ended in a message."""
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


class _Batch:
    """A real batch run with a review per document; only detection replaced
    (Story 10.10's harness)."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        texts: Sequence[str],
        names: Sequence[tuple[str, str]],
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        source_dir = tmp_path / "in"
        source_dir.mkdir()
        self.out = tmp_path / "out"
        self.db = _new_db(tmp_path)
        self.detect = _either_form(names)
        files: list[Path] = []
        for index, text in enumerate(texts):
            path = source_dir / f"doc{index}.txt"
            path.write_text(text, encoding="utf-8")
            files.append(path)
        main_window.show()
        main_window.navigate_to("batch")
        self.bs = main_window.stack.currentWidget()
        _pre(isinstance(self.bs, BatchScreen), "batch screen")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        _pre(isinstance(self.vs, ValidationScreen), "validation screen")
        self.bs._files = files
        self.bs._output_input.setText(str(self.out))
        self.bs._validate_checkbox.setChecked(True)

    def run(self, body: Callable[[], None]) -> None:
        """Run the batch; ``body`` drives it."""
        with patch.object(
            DocumentProcessor, "_detect_and_filter_entities", side_effect=self.detect
        ):
            self.bs._launch_worker(self.db, PASSPHRASE)
            try:
                body()
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)
            finally:
                if self.bs._worker is not None:
                    self.bs._worker.cancel()
                    self.qtbot.waitUntil(
                        lambda: self.bs._worker is None, timeout=WAIT_MS
                    )

    def wait_doc(self, index: int) -> Any:
        """Wait until document ``index`` is waiting; return its review state."""
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == index
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=WAIT_MS,
        )
        return vs.validation_state

    def accept_pending_and_validate(self) -> None:
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        self.vs.finalize_button.click()


# ---------------------------------------------------------------------------
# Paths 5 and 6: a correction typed composed on a decomposed name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", ["nfd-single", "nfd-batch", "mixed-single", "mixed-batch"]
)
def test_desktop_correction(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T11 (paths 5 and 6): « Zórbalia » found, the first row corrected into
    « Zórbalia Quentrel » typed composed, in a decomposed document or one
    holding both forms: every place reached, no « Quentrel » in clear, one
    row, composed."""
    dialogs = _Dialogs(monkeypatch)
    text = nfd(E_TEXT) if case.startswith("nfd") else _mixed()
    names = [(ZO, PERSON)]
    written: str | None
    if case.endswith("single"):
        sd = _Single(qtbot, main_window, tmp_path, text, names)
        first = sd.rows()[0]
        _type_in(monkeypatch, ZQ)
        sd.vs._show_modify_text_dialog(first.entity_id)
        _pre(first.user_modification == ZQ, "the first row corrected")
        sd.accept_pending()
        written = sd.finalize(dialogs)
        db = sd.db
    else:
        batch = _Batch(qtbot, main_window, tmp_path, [text], names)

        def body() -> None:
            state = batch.wait_doc(0)
            rows = sorted(state.get_all_entities(), key=lambda r: r.entity.start_pos)
            _pre(len(rows) >= 1, "a row to correct")
            _type_in(monkeypatch, ZQ)
            batch.vs._show_modify_text_dialog(rows[0].entity_id)
            _pre(rows[0].user_modification == ZQ, "the first row corrected")
            batch.accept_pending_and_validate()

        batch.run(body)
        output = batch.out / "doc0_pseudonymized.txt"
        written = output.read_text(encoding="utf-8") if output.is_file() else None
        db = batch.db
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    assert "Quentrel" not in written, repr(written)  # expected failure
    assert _names(db) == [(ZQ, PERSON)]


# ---------------------------------------------------------------------------
# AC2, AC3: the database screen's search
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "saved, searched", [("nfd", "nfc"), ("nfc", "nfd")], ids=["nfd-nfc", "nfc-nfd"]
)
def test_desktop_database_search(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, saved, searched
) -> None:
    """T19 (AC2, AC3): « Zórbalia » typed in the other form in the database
    screen's search finds the row."""
    db = _new_db(tmp_path)
    _save(db, [(FORMS[saved](ZQ), PERSON, XV), (VM, PERSON, XQ)])
    screen = main_window.stack.widget(main_window._screens["database"])
    with open_database(db, PASSPHRASE) as session:
        screen._entities = SQLiteMappingRepository(session).find_all()
    screen._populate_entity_table()
    screen.search_field.setText(FORMS[searched](ZO))
    screen._apply_filters()
    shown = screen.entity_table.rowCount()
    _pre(shown <= 2, f"at most two rows shown: {shown}")
    assert shown == 1, shown  # expected failure


# ---------------------------------------------------------------------------
# AC2: a custom pseudonym typed decomposed; the review's filter field
# ---------------------------------------------------------------------------


def test_desktop_custom_pseudonym_typed_decomposed(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T24 (AC2): « Xantor Véllion » typed decomposed in the custom pseudonym
    dialog is stored and written composed."""
    dialogs = _Dialogs(monkeypatch)
    sd = _Single(qtbot, main_window, tmp_path, "Vorlan Mestrix valide.", [(VM, PERSON)])
    row = sd.rows()[0]
    _type_in(monkeypatch, nfd(XVE))
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    _pre(dialogs.calls == [], f"no refusal: {dialogs.calls!r}")
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    _pre(nfc(written) == f"{XVE} valide.", f"the pseudonym written: {written!r}")
    rows = _rows(sd.db)
    _pre(len(rows) == 1, f"one row: {rows!r}")
    assert rows[0][2] == XVE, repr(rows[0][2])  # expected failure
    assert written == nfc(written)


def test_desktop_review_filter_typed_decomposed(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T25 (AC2): « Zórbalia » typed decomposed in the review's filter field
    lists the row of « Zórbalia Quentrel »."""
    sd = _Single(qtbot, main_window, tmp_path, R_TEXT, [(ZQ, PERSON)])
    _pre(len(sd.state.get_all_entities()) == 1, "one row")
    panel = sd.vs.panel
    panel.find_field.setText(nfd(ZO))
    listed = [
        nfc(panel.list_widget.item(index).text())
        for index in range(panel.list_widget.count())
    ]
    assert any(ZQ in item for item in listed), listed  # expected failure


# ---------------------------------------------------------------------------
# G1: a name added by hand, the same in both forms (a guard)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("form", ["nfc", "nfd"])
def test_guard_hand_added_same_in_both_forms(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """G1 (path 5 guard): « Zórbalia » selected at its first place and added
    by hand: the same result in both forms (its second place is 10.17's)."""
    dialogs = _Dialogs(monkeypatch)
    sd = _Single(qtbot, main_window, tmp_path, FORMS[form](A_TEXT), [(VM, PERSON)])
    document = sd.state.session.document_text
    places = [
        (document.find(spelling), spelling)
        for spelling in dict.fromkeys((nfc(ZO), nfd(ZO)))
        if spelling in document
    ]
    _pre(bool(places), "« Zórbalia » in the review's text")
    start, spelling = min(places)
    sd.state.add_entity(spelling, PERSON, start, start + len(spelling))
    _pre(len(sd.state.get_all_entities()) == 2, "two rows")
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    assert nfc(written).count(ZO) == 1, repr(written)
    assert sorted((nfc(name), kind) for name, kind in _names(sd.db)) == sorted(
        [(VM, PERSON), (ZO, PERSON)]
    )


# ---------------------------------------------------------------------------
# v1.5: the database search reaches the rows an earlier version saved with
# letters lost (QA's SEARCH-001; T32); the correction dialog typed decomposed
# (QA's TEST-001, M27; G11)
# ---------------------------------------------------------------------------

ACUTE = unicodedata.lookup("COMBINING ACUTE ACCENT")


def _cut_row(case: str) -> tuple[str, str]:
    """(the name an earlier version saved, the name searched): letters lost
    to the title pattern, with a decomposed « Maître » in front for
    ``maitre_melora``."""
    if case == "zorbome":
        return nfd("Zorbô") + "Quentrel", "Zorbôme Quentrel"
    lost = ACUTE + "lora Quentrel"
    if case == "maitre_melora":
        return nfd("Maître") + " " + lost, "Mélora Quentrel"
    return lost, "Mélora Quentrel"


@pytest.mark.parametrize("case", ["melora", "zorbome", "maitre_melora"])
@pytest.mark.parametrize("path", ["inline", "worker"])
def test_desktop_search_lists_a_row_that_lost_letters(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, path, case
) -> None:
    """T32 (v1.5, SEARCH-001; AC3): the database screen's search with the full
    name composed, inline and in ``DatabaseWorker``, lists the row an earlier
    version saved with letters lost, and not another name's row."""
    from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

    db = _new_db(tmp_path)
    stored, name = _cut_row(case)
    _save(db, [(stored, PERSON, XV), (VM, PERSON, XQ)])
    with open_database(db, PASSPHRASE) as session:
        entities = SQLiteMappingRepository(session).find_all()
    if path == "inline":
        screen = main_window.stack.widget(main_window._screens["database"])
        screen._entities = entities
        screen._populate_entity_table()
        screen.search_field.setText(name)
        screen._apply_filters()
        shown = screen.entity_table.rowCount()
        _pre(shown <= 2, f"at most two rows shown: {shown}")
        pseudonyms = [screen.entity_table.item(row, 3).text() for row in range(shown)]
        assert shown == 1, pseudonyms  # expected failure
        assert XQ not in pseudonyms
    else:
        worker = DatabaseWorker(
            "search", entities=entities, search_text=name, type_filter=""
        )
        results: list[Any] = []
        worker.signals.finished.connect(results.append)
        worker.run()
        _pre(len(results) == 1, f"one result: {results!r}")
        found = [entity.pseudonym_full for entity in results[0]]
        assert found == [XV], found  # expected failure


@pytest.mark.parametrize("form", ["nfd", "nfc"])
def test_guard_desktop_correction_typed_decomposed(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, form
) -> None:
    """G11 (v1.5, QA's M27; AC2): « Zórbalia » corrected into « Zórbalia
    Quentrel » typed decomposed, in a decomposed or composed document: no
    « Quentrel » in clear, one row, composed."""
    dialogs = _Dialogs(monkeypatch)
    sd = _Single(qtbot, main_window, tmp_path, FORMS[form](E_TEXT), [(ZO, PERSON)])
    first = sd.rows()[0]
    _type_in(monkeypatch, nfd(ZQ))
    sd.vs._show_modify_text_dialog(first.entity_id)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    assert "Quentrel" not in written, repr(written)
    assert _names(sd.db) == [(ZQ, PERSON)]


# ---------------------------------------------------------------------------
# v1.7: the Codex review of 186972b in the desktop app: a custom pseudonym
# equal to an old saved name (T35), or set on a name saved decomposed (T37);
# a database with no old rows as today (G14)
# ---------------------------------------------------------------------------

PLACE_TEXT = "Le contrat a été signé à Zórbaville."


def test_desktop_custom_pseudonym_equal_to_an_old_saved_name_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T35 (v1.7, Codex P0-2): « Éloria Quentrel » typed in the custom
    pseudonym dialog is refused beside the row an earlier version saved for
    « Maître Éloria Quentrel »."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _save(db, [(nfd("Maître Éloria Quentrel"), PERSON, XV)])
    sd = _Single(
        qtbot, main_window, tmp_path, "Vorlan Mestrix valide.", [(VM, PERSON)], db
    )
    row = sd.rows()[0]
    _type_in(monkeypatch, "Éloria Quentrel")
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    refusals = list(dialogs.calls)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    assert "Éloria Quentrel" not in nfc(written), repr(written)  # expected failure
    assert refusals, refusals


def test_desktop_custom_pseudonym_for_a_name_saved_decomposed_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """T37 (v1.7, Codex P1-2): a place saved decomposed keeps its pseudonym:
    « Quovixville » typed in the custom pseudonym dialog is refused."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _save(db, [(nfd("Zórbaville"), "LOCATION", "Xantorville")])
    sd = _Single(
        qtbot, main_window, tmp_path, PLACE_TEXT, [("Zórbaville", "LOCATION")], db
    )
    row = sd.rows()[0]
    _type_in(monkeypatch, "Quovixville")
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    refusals = list(dialogs.calls)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    rows = _rows(db)
    assert len(rows) == 1, rows  # expected failure
    assert "Xantorville" in written, repr(written)
    assert refusals, refusals


@pytest.mark.parametrize("case", ["custom_place_already_stored"])
def test_guard_clean_database_as_today(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """G14 (v1.7; AC13), the desktop case: a place saved composed, as today's
    code saves it, keeps its pseudonym: « Quovixville » typed in the custom
    pseudonym dialog is refused, one row, « Xantorville » written."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    _save(db, [("Zórbaville", "LOCATION", "Xantorville")])
    sd = _Single(
        qtbot, main_window, tmp_path, PLACE_TEXT, [("Zórbaville", "LOCATION")], db
    )
    row = sd.rows()[0]
    _type_in(monkeypatch, "Quovixville")
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    refusals = list(dialogs.calls)
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if written is None:
        pytest.fail(f"PRE: written: {dialogs.calls!r}")
    assert refusals, refusals
    assert len(_rows(db)) == 1, _rows(db)
    assert "Xantorville" in written, repr(written)


# ---------------------------------------------------------------------------
# v1.10 and v1.11: the second Codex review of 56feb3d in the desktop app: a
# search with a title (T44), and a hyphenated first name an old row was cut
# from, as a custom pseudonym (T47)
# ---------------------------------------------------------------------------

XFAIL = "Story 10.20 v1.10: reproduces {} on the unfixed code; fixed in Task 2.10"
MAITREQUIX = "Éloria Maîtrequix"
HYPHEN_CUT = "Zorbôme-Quovan Quentrel"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=XFAIL.format("a search with a title listing another name"),
)
@pytest.mark.parametrize("path", ["inline", "worker"])
def test_search_with_a_title_lists_no_other_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, path
) -> None:
    """T44 (v1.10; Codex review 2, P1; AC13): the database screen's search
    « Mme Éloria », inline and in ``DatabaseWorker``, lists no « Éloria
    Maîtrequix »."""
    from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

    db = _new_db(tmp_path)
    _save(db, [(MAITREQUIX, PERSON, XV), (VM, PERSON, XQ)])
    with open_database(db, PASSPHRASE) as session:
        entities = SQLiteMappingRepository(session).find_all()
    if path == "inline":
        screen = main_window.stack.widget(main_window._screens["database"])
        screen._entities = entities
        screen._populate_entity_table()
        screen.search_field.setText("Mme Éloria")
        screen._apply_filters()
        shown = screen.entity_table.rowCount()
        _pre(shown <= 2, f"at most two rows shown: {shown}")
        assert shown == 0, shown  # expected failure
    else:
        worker = DatabaseWorker(
            "search", entities=entities, search_text="Mme Éloria", type_filter=""
        )
        results: list[Any] = []
        worker.signals.finished.connect(results.append)
        worker.run()
        _pre(len(results) == 1, f"one result: {results!r}")
        found = [entity.pseudonym_full for entity in results[0]]
        assert found == [], found  # expected failure


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=XFAIL.format("a hyphenated first name cut before its hyphen accepted"),
)
@pytest.mark.parametrize("path", ["desktop_set", "desktop_final"])
def test_end_cut_hyphenated_first_name_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, path
) -> None:
    """T47 (v1.11; Lionel's end-cut answer A; the PO's case): the row an
    earlier version saved from nfd(« Zorbôme-Quovan Quentrel ») refuses that
    name in the custom pseudonym dialog (the row saved first) and at
    finalization (the row saved after the dialog accepted it)."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    stored = nfd("Zorbô") + "-Quovan Quentrel"
    if path == "desktop_set":
        _save(db, [(stored, PERSON, XV)])
    sd = _Single(
        qtbot, main_window, tmp_path, "Vorlan Mestrix valide.", [(VM, PERSON)], db
    )
    row = sd.rows()[0]
    _type_in(monkeypatch, HYPHEN_CUT)
    sd.vs._show_change_pseudonym_dialog(row.entity_id)
    if path == "desktop_final":
        _pre(dialogs.calls == [], f"set without a message: {dialogs.calls!r}")
        _save(db, [(stored, PERSON, XV)])
    sd.accept_pending()
    written = sd.finalize(dialogs)
    if path == "desktop_set":
        if written is None:
            pytest.fail(f"PRE: written: {dialogs.calls!r}")
        assert HYPHEN_CUT not in nfc(written), repr(written)  # expected failure
        assert dialogs.calls, dialogs.calls
    else:
        name_written = written is not None and HYPHEN_CUT in nfc(written)
        assert not name_written, repr(written)  # expected failure
        assert dialogs.calls, dialogs.calls
        assert written is None and len(_rows(db)) == 1, (written, _rows(db))
