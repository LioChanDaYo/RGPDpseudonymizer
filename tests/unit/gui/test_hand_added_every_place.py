"""Story 10.17: a name added by hand in the desktop app, at every place.

T1-T23 and the guards G1, G2 of the story's Test Plan. Written by the BMAD dev
agent (Claude), before the fix. Each test drives the real single-document path
(``DetectionWorker``, the validation screen, ``FinalizationWorker``) or the
real batch path (``BatchScreen``, ``ValidationScreen`` and the ``BatchWorker``
thread); only detection is replaced. A name is added the way the editor's
« Ajouter comme entité » adds it: its ``add_entity_requested`` signal.

Preconditions are ``pytest.fail("PRE: ...")`` calls, never ``assert``, so a
broken precondition is a red failure even under
``xfail(strict=True, raises=AssertionError)``. Observations made during a flow
are recorded and asserted after the written file exists; the first ``assert``
of each test is its expected failure on the unfixed code. Invented names only.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QLabel

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

# _launch_worker disconnects two slots that are not connected yet. PySide6
# warns instead of raising RuntimeError there, and pytest.ini turns warnings
# into errors, so exactly those two warnings are filtered (as in
# test_batch_review_real_worker.py). This is a warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
MODES = ["single", "batch"]

PENDING = EntityReviewState.PENDING
CONFIRMED = EntityReviewState.CONFIRMED
REJECTED = EntityReviewState.REJECTED
ADDED = EntityReviewState.ADDED

VM = "Vorlan Mestrix"
ZQ = "Zorbal Quentrix"
VZ = "Vorlan Zorbal"
QV = "Quentrix Vorlan"
MDZ = "MARIE DE ZORBAL"
VORLENE = "Vorlène"
CUSTOM = "Xantor Vellion"

DOC = (
    "Vorlan Mestrix valide. Le contrat avec Zorbal Quentrix. "
    "Signé : Zorbal Quentrix."
)
ONE = "Vorlan Mestrix valide. Le contrat avec Zorbal Quentrix."
DOC0 = "Vorlan Mestrix valide."
T2T = (
    "Zorbal Quentrix valide. Le contrat avec Zorbal Quentrix. "
    "Signé : Zorbal Quentrix."
)
T3T = "Vorlan Mestrix a signé avec Saint-Zorbal, Zorbalix, l'Zorbal et Zorbal."
T6T = "Vorlan Zorbal Quentrix a signé. Le contrat avec Zorbal Quentrix."
T8T = "Zorbal Quentrix valide. Le contrat avec Zorbal Quentrix."
G2T = "Vorlan Mestrix a signé avec Zorbalix."
T14T = "Le contrat avec Zorbal Quentrix. Signé : Zorbal Quentrix."
C15 = "Zorbal valide. Le contrat avec ZORBAL. Signé : Zorbal."
C16 = "Petit valide. Le contrat avec petit et PETIT."
C17 = "Vorlan Zorbal valide. Le contrat avec Vorlan ZORBAL."
C18 = "MARIE DE ZORBAL valide. Le contrat avec Marie de Zorbal."
C19 = "Zorbal valide. Le contrat avec ZORBAL. Signé : ZORBAL."
O20 = "Vorlan Zorbal Quentrix a signé."
O21 = "Zorbal Quentrix Vorlan a signé."
O22 = "Zorbal Quentrix a validé. Vorlan Zorbal Quentrix a signé."
A23 = "Vorlène valide. Le contrat avec VORLÈNE et VORLENE. Signé : Vorlene."
KNOWN = "Vorlan Zorbal."
# G3 (Story 10.20): written to the file with its accents as separate marks.
VQ = "Vorlène Quentrix"
DEC = (
    "Vorlan Mestrix valide. Le contrat avec Vorlène Quentrix. "
    "Signé : Vorlène Quentrix."
)

Drive = Callable[["_Review", dict[str, Any]], None]


def pre(condition: bool, message: str) -> None:
    """A precondition: ``pytest.fail``, never an ``AssertionError``."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def occurrence(text: str, name: str, n: int) -> int:
    """Start of the ``n``-th occurrence of ``name`` in ``text`` (``str.find``,
    counted from 0)."""
    start = -1
    for _ in range(n + 1):
        start = text.find(name, start + 1)
        pre(start >= 0, f"occurrence {n} of the name")
    return start


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    pre(text[start : start + len(name)] == name, "entity slice")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _nth(text: str, name: str, entity_type: str, n: int = 0) -> DetectedEntity:
    return _at(text, name, entity_type, occurrence(text, name, n))


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test away from the user's settings file and home folder."""
    monkeypatch.setattr(
        "gdpr_pseudonymizer.gui.config._config_path",
        lambda: tmp_path / ".gdpr-pseudo.yaml",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))


@pytest.fixture()
def dialogs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, str]]]:
    """Record (title, message) of every confirmation window; each continues."""
    shown: list[tuple[str, str]] = []
    original_init = ConfirmDialog.__init__

    def record_window(self: ConfirmDialog, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        label = self.findChild(QLabel)
        pre(label is not None, "confirm dialog label")
        shown.append((self.windowTitle(), label.text() if label else ""))

    monkeypatch.setattr(ConfirmDialog, "__init__", record_window)
    monkeypatch.setattr(ConfirmDialog, "exec", lambda self: 1)
    yield shown


def pending_counts(shown: list[tuple[str, str]]) -> list[int]:
    """The counts of Story 10.13's window among the windows shown, read from
    its message (« … : 1. »), not from its wording."""
    counts: list[int] = []
    for _title, message in shown:
        match = re.search(r":\s*(\d+)\.\n", message)
        if match is not None:
            counts.append(int(match.group(1)))
    return counts


class _Review:
    """One review through the real desktop path, ``single`` or ``batch``."""

    def __init__(
        self,
        mode: str,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        docs: list[tuple[str, list[DetectedEntity]]],
        known: list[DetectedEntity] | None = None,
        through_reader: bool = False,
    ) -> None:
        """``through_reader`` (the Story 10.20 guard): the file is read by the
        app's reader (``read_file``), only ``_detect_and_filter_entities`` is
        replaced in both modes, and a document's entities are looked up by its
        composed text (positions in the text the reader returns)."""
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.mode = mode
        self.qtbot = qtbot
        self.mw = main_window
        self.tmp_path = tmp_path
        self.docs = docs
        self.through_reader = through_reader
        self.db = str(tmp_path / "mappings.db")
        init_database(self.db, PASSPHRASE)
        if known is not None:
            # A name stored by an earlier finalization, so the review finds it
            # known (accepted when the review is built).
            result = DocumentProcessor(
                db_path=self.db, passphrase=PASSPHRASE
            ).finalize_document(
                document_text=KNOWN,
                validated_entities=known,
                output_path=str(tmp_path / "known_out.txt"),
            )
            pre(result.success, "the known name stored")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        self._outputs: list[str] = []
        main_window.show()
        if mode == "batch":
            source_dir = tmp_path / "in"
            source_dir.mkdir()
            self.out = tmp_path / "out"
            self._by_text: dict[str, list[DetectedEntity]] = {}
            files: list[Path] = []
            for index, (text, entities) in enumerate(docs):
                path = source_dir / f"doc{index}.txt"
                path.write_text(text, encoding="utf-8")
                files.append(path)
                key = unicodedata.normalize("NFC", text) if through_reader else text
                self._by_text[key] = entities
            main_window.navigate_to("batch")
            self.bs = main_window.stack.currentWidget()
            pre(isinstance(self.bs, BatchScreen), "batch screen")
            self.bs._files = files
            self.bs._output_input.setText(str(self.out))
            self.bs._validate_checkbox.setChecked(True)

    # -- the review -------------------------------------------------------

    @property
    def state(self) -> Any:
        state = self.vs.validation_state
        pre(state is not None, "a review is shown")
        return state

    @property
    def text(self) -> str:
        return str(self.state.session.document_text)

    def reviews(self, name: str | None = None) -> list[Any]:
        return [
            r
            for r in self.state.get_all_entities()
            if name is None or r.entity.text == name
        ]

    def found(self, name: str, entity_type: str = "PERSON") -> list[Any]:
        """The detected rows of a name (not added by hand)."""
        return [
            r
            for r in self.reviews(name)
            if r.entity.entity_type == entity_type and r.state != ADDED
        ]

    def add(self, name: str, entity_type: str = "PERSON", n: int = 0) -> None:
        """« Ajouter comme entité » on the ``n``-th occurrence of ``name``."""
        before = len(self.reviews())
        self.add_again(name, entity_type, n)
        pre(len(self.reviews()) > before, "the add made a row")

    def add_again(self, name: str, entity_type: str = "PERSON", n: int = 0) -> None:
        start = occurrence(self.text, name, n)
        self.vs.editor.add_entity_requested.emit(entity_type, start, start + len(name))

    def added_row(self, name: str, start: int | None = None) -> Any:
        """The row added by hand for ``name`` (at ``start`` when given)."""
        rows = [
            r
            for r in self.reviews(name)
            if r.state == ADDED and (start is None or r.entity.start_pos == start)
        ]
        pre(len(rows) >= 1, "a row added by hand")
        return rows[0]

    def accept_pending(self) -> None:
        state = self.state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)

    def places_shown(self, name: str) -> list[tuple[int, int]]:
        """Single: the editor's highlighted places of the rows of ``name``;
        batch: the spans of the rows added by hand with that text."""
        state = self.state
        if self.mode == "single":
            self.vs.editor.refresh_all()
            spans = []
            for start, end, entity_id in self.vs.editor._entity_ranges:
                review = state.get_review(entity_id)
                if review is not None and review.entity.text == name:
                    spans.append((start, end))
            return sorted(spans)
        return sorted(
            (r.entity.start_pos, r.entity.end_pos)
            for r in state.get_all_entities()
            if r.state == ADDED and r.entity.text == name
        )

    def validate(self) -> None:
        if self.mode == "single":
            self.vs._on_finalize()
        else:
            self.vs.finalize_button.click()

    # -- running ----------------------------------------------------------

    def run(self, drive: Drive) -> dict[str, Any]:
        """Review document 0 with ``drive``, validate it, wait for the file."""
        record: dict[str, Any] = {}
        if self.mode == "single":
            pre(len(self.docs) == 1, "one document")
            self._start_single()
            drive(self, record)
            self.validate()
            self.qtbot.waitUntil(
                lambda: self.mw.current_screen_name() == "results", timeout=WAIT_MS
            )
            results = self.mw.stack.currentWidget()
            self._outputs = [Path(results._temp_path).read_text(encoding="utf-8")]
            return record

        def body(r: _Review, inner: dict[str, Any]) -> None:
            r.wait_doc(0)
            drive(r, inner)
            r.validate()

        return self.run_batch(body)

    def _start_single(self) -> None:
        from gdpr_pseudonymizer.gui.workers.detection_worker import (
            DetectionResult,
            DetectionWorker,
        )

        text, entities = self.docs[0]
        file_path = self.tmp_path / "doc0.txt"
        file_path.write_text(text, encoding="utf-8")
        worker = DetectionWorker(str(file_path), self.db, PASSPHRASE)
        worker.setAutoDelete(False)
        results: list[Any] = []
        errors: list[str] = []
        worker.signals.finished.connect(results.append)
        worker.signals.error.connect(errors.append)
        if self.through_reader:
            read: list[str] = []

            def detect(document_text: str, *args: Any, **kwargs: Any) -> Any:
                read.append(document_text)
                return [DetectedEntity(**vars(e)) for e in entities]

            with patch.object(
                DocumentProcessor, "_detect_and_filter_entities", side_effect=detect
            ):
                worker.run()
            pre(
                read == [unicodedata.normalize("NFC", text)],
                "the reader gave the composed text",
            )
        else:
            with patch.object(
                DocumentProcessor,
                "detect_entities",
                return_value=(text, [DetectedEntity(**vars(e)) for e in entities]),
            ):
                worker.run()
        pre(not errors, "detection error")
        pre(len(results) == 1, "one detection result")
        pre(isinstance(results[0], DetectionResult), "detection result")
        self.vs.start_validation(results[0])
        self.mw.navigate_to("validation")
        pre(not self.vs.batch_mode, "single-document mode")

    def run_batch(self, body: Drive) -> dict[str, Any]:
        """Run the batch; ``body`` drives it. Returns what ``body`` recorded."""
        pre(self.mode == "batch", "batch mode")
        record: dict[str, Any] = {}

        def detect(text: str, *args: Any, **kwargs: Any) -> list[DetectedEntity]:
            return [DetectedEntity(**vars(e)) for e in self._by_text[text]]

        with patch.object(
            DocumentProcessor, "_detect_and_filter_entities", side_effect=detect
        ):
            self.bs._launch_worker(self.db, PASSPHRASE)
            try:
                body(self, record)
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)
            finally:
                if self.bs._worker is not None:
                    self.bs._worker.cancel()
                    self.qtbot.waitUntil(
                        lambda: self.bs._worker is None, timeout=WAIT_MS
                    )
        self._outputs = [
            (self.out / f"doc{index}_pseudonymized.txt").read_text(encoding="utf-8")
            for index in range(len(self.docs))
        ]
        return record

    def wait_doc(self, index: int) -> Any:
        """Wait until batch document ``index`` is waiting; return its review."""
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == index
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=WAIT_MS,
        )
        pre(vs.batch_mode, "batch mode")
        return vs.validation_state

    # -- the written file and the stored rows -------------------------------

    def output(self, index: int = 0) -> str:
        pre(index < len(self._outputs), "the written file")
        return self._outputs[index]

    def stored(self) -> list[tuple[str, str, str]]:
        """(full name, type, full pseudonym) of every stored row."""
        with open_database(self.db, PASSPHRASE) as session:
            rows = SQLiteMappingRepository(session).find_all()
            return sorted((r.full_name, r.entity_type, r.pseudonym_full) for r in rows)

    def pseudonym(self, name: str, entity_type: str = "PERSON") -> str:
        """The pseudonym of the one row stored for (name, type)."""
        key = mapping_key(name, entity_type)
        rows = [p for n, t, p in self.stored() if n == key and t == entity_type]
        pre(len(rows) == 1, f"one stored row for a {entity_type} name")
        return rows[0]

    def has_row(self, name: str, entity_type: str) -> bool:
        key = mapping_key(name, entity_type)
        return any(n == key and t == entity_type for n, t, _ in self.stored())


def _review(
    mode: str,
    qtbot: Any,
    main_window: Any,
    tmp_path: Path,
    text: str,
    entities: list[DetectedEntity],
    known: list[DetectedEntity] | None = None,
) -> _Review:
    return _Review(mode, qtbot, main_window, tmp_path, [(text, entities)], known)


# ---------------------------------------------------------------------------
# T1-T14: every place of a name added by hand
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_added_name_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T1 (AC1; the PO's case): a name added at one of its two places."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zq = review.pseudonym(VM), review.pseudonym(ZQ)
    assert ZQ not in output  # expected failure
    assert output == f"{vm} valide. Le contrat avec {zq}. Signé : {zq}."


@pytest.mark.parametrize("found", ["pending", "rejected"])
@pytest.mark.parametrize("mode", MODES)
def test_found_place_keeps_its_decision(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode, found
) -> None:
    """T2 (AC1, AC3): a place the detector found keeps its own decision, and
    Story 10.13's warning still counts it when it is left to review."""
    review = _review(
        mode, qtbot, main_window, tmp_path, T2T, [_nth(T2T, ZQ, "PERSON", 0)]
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        rows = r.found(ZQ)
        pre(len(rows) == 1 and rows[0].state == PENDING, "the found row")
        found_row = rows[0]
        if found == "rejected":
            r.state.reject_entity(found_row.entity_id)
            pre(found_row.state == REJECTED, "the found row rejected")
        r.add(ZQ, "PERSON", 1)
        record["found_state"] = found_row.state

    record = review.run(drive)
    output = review.output()
    zq = review.pseudonym(ZQ)
    assert output.endswith(f"Signé : {zq}.")  # expected failure
    assert output == f"Zorbal Quentrix valide. Le contrat avec {zq}. Signé : {zq}."
    assert record["found_state"] == (PENDING if found == "pending" else REJECTED)
    assert pending_counts(dialogs) == ([1] if found == "pending" else [])


@pytest.mark.parametrize("mode", MODES)
def test_whole_words_only(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T3 (AC1, AC13 (a); Lionel's 10.15 Q3): whole words only, a hyphen
    joins words, an apostrophe does not."""
    review = _review(mode, qtbot, main_window, tmp_path, T3T, [_nth(T3T, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add("Zorbal", "PERSON", 3)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zorbal = review.pseudonym(VM), review.pseudonym("Zorbal")
    assert f"l'{zorbal} et {zorbal}." in output  # expected failure
    assert output == (
        f"{vm} a signé avec Saint-Zorbal, Zorbalix, l'{zorbal} et {zorbal}."
    )


@pytest.mark.parametrize("mode", MODES)
def test_one_undo_removes_the_add_everywhere(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T4 (AC2, AC3; guard): one undo removes the add at every place."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        r.vs._on_undo()
        record["left"] = len(r.reviews(ZQ))
        r.accept_pending()

    record = review.run(drive)
    output = review.output()
    vm = review.pseudonym(VM)
    assert record["left"] == 0
    assert output == (
        f"{vm} valide. Le contrat avec Zorbal Quentrix. Signé : Zorbal Quentrix."
    )
    assert not review.has_row(ZQ, "PERSON")


@pytest.mark.parametrize("mode", MODES)
def test_undo_then_redo_restores_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T5 (AC2): one redo restores the add at every place."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        r.vs._on_undo()
        r.vs._on_redo()
        pre(len(r.reviews(ZQ)) >= 1, "a row of the added name again")
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zq = review.pseudonym(VM), review.pseudonym(ZQ)
    assert ZQ not in output  # expected failure
    assert output == f"{vm} valide. Le contrat avec {zq}. Signé : {zq}."


@pytest.mark.parametrize("case", ["single", "batch", "single_known", "batch_known"])
def test_overlap_takes_the_added_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, case
) -> None:
    """T6 (AC8, AC13 (e); Lionel's 10.15 Q4): a place of the added name that
    partly overlaps a name being written (found and accepted, or known) is
    widened and takes the added name's pseudonym."""
    mode, _, kind = case.partition("_")
    known = [_at(KNOWN, VZ, "PERSON", 0)] if kind == "known" else None
    review = _review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        T6T,
        [_at(T6T, VZ, "PERSON", 0)],
        known=known,
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        rows = r.found(VZ)
        pre(len(rows) == 1, "the found row of the overlapped name")
        if known is not None:
            pre(
                r.state.is_entity_known(rows[0].entity_id)
                and rows[0].state == CONFIRMED,
                "the overlapped name is known",
            )
        r.add(ZQ, "PERSON", 1)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    review.pseudonym(VZ)
    zq = review.pseudonym(ZQ)
    assert "Quentrix" not in output and "Vorlan" not in output  # expected failure
    assert output == f"{zq} a signé. Le contrat avec {zq}."


def test_batch_previous_next_keeps_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T7 (batch; Consumer Trace #12): « ◀ Précédent » then « Suivant ▶ »
    keep every row the add made."""
    review = _Review(
        "batch",
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, [_nth(DOC0, VM, "PERSON")]), (DOC, [_nth(DOC, VM, "PERSON")])],
    )

    def body(r: _Review, record: dict[str, Any]) -> None:
        r.wait_doc(0)
        r.accept_pending()
        r.validate()
        state = r.wait_doc(1)
        r.add(ZQ, "PERSON", 0)
        ids = [rv.entity_id for rv in state.get_all_entities()]
        pre(r.vs.prev_button.isVisibleTo(r.vs), "Précédent visible")
        r.vs.prev_button.click()
        pre(r.vs.doc_index == 0, "on doc 0")
        r.vs.next_button.click()
        pre(r.vs.doc_index == 1, "back on doc 1")
        pre(r.vs.validation_state is state, "doc 1's review kept")
        pre(
            [rv.entity_id for rv in state.get_all_entities()] == ids,
            "the added rows kept",
        )
        r.accept_pending()
        r.validate()

    review.run_batch(body)
    output = review.output(1)
    vm, zq = review.pseudonym(VM), review.pseudonym(ZQ)
    assert ZQ not in output  # expected failure
    assert output == f"{vm} valide. Le contrat avec {zq}. Signé : {zq}."


@pytest.mark.parametrize("mode", MODES)
def test_text_found_with_another_type(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T8 (AC13 (b), (e)): a place found with another type and left to review
    is a place of the added name."""
    review = _review(mode, qtbot, main_window, tmp_path, T8T, [_nth(T8T, ZQ, "ORG", 0)])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.found(ZQ, "ORG")) == 1, "the place found as ORG")
        r.add(ZQ, "PERSON", 1)

    review.run(drive)
    output = review.output()
    zq = review.pseudonym(ZQ, "PERSON")
    pre(not review.has_row(ZQ, "ORG"), "no row for the ORG left to review")
    assert ZQ not in output  # expected failure
    assert output == f"{zq} valide. Le contrat avec {zq}."


@pytest.mark.parametrize("mode", MODES)
def test_every_place_shown(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T9 (AC2): the added name's places are shown, as they will be written."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        record["shown"] = r.places_shown(ZQ)
        record["rows"] = len(r.reviews(ZQ))
        r.accept_pending()

    record = review.run(drive)
    first = occurrence(DOC, ZQ, 0)
    second = occurrence(DOC, ZQ, 1)
    assert record["shown"] == [  # expected failure
        (first, first + len(ZQ)),
        (second, second + len(ZQ)),
    ]
    assert record["rows"] == (1 if mode == "single" else 2)


@pytest.mark.parametrize("mode", MODES)
def test_add_twice_adds_once(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T10 (AC13 (b)): a place already added by hand is not added twice."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        r.add_again(ZQ, "PERSON", 0)
        record["shown"] = r.places_shown(ZQ)
        r.accept_pending()

    record = review.run(drive)
    output = review.output()
    vm, zq = review.pseudonym(VM), review.pseudonym(ZQ)
    first = occurrence(DOC, ZQ, 0)
    second = occurrence(DOC, ZQ, 1)
    assert ZQ not in output  # expected failure
    assert record["shown"] == [(first, first + len(ZQ)), (second, second + len(ZQ))]
    assert output == f"{vm} valide. Le contrat avec {zq}. Signé : {zq}."


@pytest.mark.parametrize("mode", MODES)
def test_custom_pseudonym_on_added_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T11 (10.11 Q3, 10.16): a custom pseudonym set on the added name is
    written at every place."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        row = r.added_row(ZQ)
        refusal = r.state.custom_pseudonym_refusal(
            row.entity_id, CUSTOM, r.db, PASSPHRASE
        )
        pre(refusal is None, "the custom pseudonym is allowed")
        r.state.change_pseudonym(row.entity_id, CUSTOM)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm = review.pseudonym(VM)
    pre(review.pseudonym(ZQ) == CUSTOM, "the added name's row holds it")
    assert ZQ not in output  # expected failure
    assert output == f"{vm} valide. Le contrat avec {CUSTOM}. Signé : {CUSTOM}."


@pytest.mark.parametrize("mode", MODES)
def test_correction_on_added_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T12 (10.9, 10.10 Q3): a correction of the added name reaches every
    place."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])
    first = occurrence(DOC, ZQ, 0)

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add("Zorbal", "PERSON", 0)
        row = r.added_row("Zorbal", first)
        r.state.modify_entity_text(row.entity_id, ZQ, first, first + len(ZQ))
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zq = review.pseudonym(VM), review.pseudonym(ZQ)
    assert "Quentrix" not in output and "Zorbal" not in output  # expected failure
    assert output == f"{vm} valide. Le contrat avec {zq}. Signé : {zq}."


@pytest.mark.parametrize("mode", MODES)
def test_type_change_on_added_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T13 (10.9 type change, 10.10 Q3): a type change of the added name
    reaches every place."""
    review = _review(mode, qtbot, main_window, tmp_path, DOC, [_nth(DOC, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        row = r.added_row(ZQ, occurrence(DOC, ZQ, 0))
        r.state.change_entity_type(row.entity_id, "ORG")
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zq_org = review.pseudonym(VM), review.pseudonym(ZQ, "ORG")
    assert ZQ not in output  # expected failure
    assert output == f"{vm} valide. Le contrat avec {zq_org}. Signé : {zq_org}."
    assert not review.has_row(ZQ, "PERSON")


@pytest.mark.parametrize("mode", MODES)
def test_nothing_detected_add_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T14 (AC1; the PO's M2): nothing detected, a name added by hand."""
    review = _review(mode, qtbot, main_window, tmp_path, T14T, [])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.reviews() == [], "nothing detected")
        r.add(ZQ, "PERSON", 0)

    review.run(drive)
    output = review.output()
    zq = review.pseudonym(ZQ)
    assert ZQ not in output  # expected failure
    assert len(review.stored()) == 1
    assert output == f"Le contrat avec {zq}. Signé : {zq}."


# ---------------------------------------------------------------------------
# T15-T19, T23: the forms of the name in capitals (Lionel, 2026-10-19)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_capital_form_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T15 (AC1, AC3, AC13 (d)): « ZORBAL » is a place of an added « Zorbal »."""
    review = _review(mode, qtbot, main_window, tmp_path, C15, [])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.reviews() == [], "nothing detected")
        r.add("Zorbal", "PERSON", 0)
        record["rows"] = len(r.reviews("Zorbal"))

    record = review.run(drive)
    output = review.output()
    zorbal = review.pseudonym("Zorbal")
    assert "ZORBAL" not in output  # expected failure
    assert output == f"{zorbal} valide. Le contrat avec {zorbal}. Signé : {zorbal}."
    assert len(review.stored()) == 1
    assert record["rows"] == (1 if mode == "single" else 3)


@pytest.mark.parametrize("mode", MODES)
def test_small_letter_word_never_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T16 (AC1, AC3): « petit » is never a place of an added « Petit »."""
    review = _review(mode, qtbot, main_window, tmp_path, C16, [])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.reviews() == [], "nothing detected")
        r.add("Petit", "PERSON", 0)

    review.run(drive)
    output = review.output()
    petit = review.pseudonym("Petit")
    assert "PETIT" not in output  # expected failure
    assert output == f"{petit} valide. Le contrat avec petit et {petit}."


@pytest.mark.parametrize("mode", MODES)
def test_mixed_form_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T17 (AC3): « Vorlan ZORBAL » is a place of an added « Vorlan Zorbal »."""
    review = _review(mode, qtbot, main_window, tmp_path, C17, [])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.reviews() == [], "nothing detected")
        r.add(VZ, "PERSON", 0)

    review.run(drive)
    output = review.output()
    vz = review.pseudonym(VZ)
    assert "ZORBAL" not in output  # expected failure
    assert output == f"{vz} valide. Le contrat avec {vz}."
    assert len(review.stored()) == 1


@pytest.mark.parametrize("mode", MODES)
def test_small_particle_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T18 (AC3): « Marie de Zorbal » is a place of an added
    « MARIE DE ZORBAL »."""
    review = _review(mode, qtbot, main_window, tmp_path, C18, [])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.reviews() == [], "nothing detected")
        r.add(MDZ, "PERSON", 0)

    review.run(drive)
    output = review.output()
    mdz = review.pseudonym(MDZ)
    assert "Zorbal" not in output  # expected failure
    assert output == f"{mdz} valide. Le contrat avec {mdz}."
    assert len(review.stored()) == 1


@pytest.mark.parametrize("mode", MODES)
def test_found_capital_place_keeps_its_decision(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T19 (AC1, AC13 (b)): a place found in capitals keeps its decision."""
    review = _review(
        mode, qtbot, main_window, tmp_path, C19, [_nth(C19, "ZORBAL", "PERSON", 0)]
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        rows = r.found("ZORBAL")
        pre(len(rows) == 1 and rows[0].state == PENDING, "the found row")
        found_row = rows[0]
        r.state.reject_entity(found_row.entity_id)
        pre(found_row.state == REJECTED, "the found row rejected")
        r.add("Zorbal", "PERSON", 0)
        record["found_state"] = found_row.state

    record = review.run(drive)
    output = review.output()
    zorbal = review.pseudonym("Zorbal")
    assert output.endswith(f"Signé : {zorbal}.")  # expected failure
    assert output == f"{zorbal} valide. Le contrat avec ZORBAL. Signé : {zorbal}."
    assert record["found_state"] == REJECTED


@pytest.mark.parametrize("mode", MODES)
def test_accents_in_capitals(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T23 (AC1, AC3; Lionel's 10.19 Q3): « VORLÈNE » and « VORLENE » are
    places of an added « Vorlène »; « Vorlene » is not."""
    review = _review(mode, qtbot, main_window, tmp_path, A23, [])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.reviews() == [], "nothing detected")
        r.add(VORLENE, "PERSON", 0)

    review.run(drive)
    output = review.output()
    vorlene = review.pseudonym(VORLENE)
    assert "VORLÈNE" not in output and "VORLENE" not in output  # expected failure
    written = f"{vorlene} valide. Le contrat avec {vorlene} et {vorlene}."
    assert output == f"{written} Signé : Vorlene."
    assert len(review.stored()) == 1


# ---------------------------------------------------------------------------
# T20-T22: a correction that partly overlaps another name (AC8)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_correction_overlapping_accepted_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T20 (AC8, AC3; the PO's desktop probe): accept, then correct."""
    review = _review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        O20,
        [_at(O20, VZ, "PERSON", 0), _at(O20, "Quentrix", "PERSON", 14)],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        vz_rows, q_rows = r.found(VZ), r.found("Quentrix")
        pre(len(vz_rows) == 1 and len(q_rows) == 1, "two rows")
        r.state.accept_entity(vz_rows[0].entity_id)
        r.state.modify_entity_text(q_rows[0].entity_id, ZQ, 7, 22)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    review.pseudonym(VZ)
    zq = review.pseudonym(ZQ)
    assert not any(  # expected failure
        part in output for part in ("Vorlan", "Zorbal", "Quentrix")
    )
    assert output == f"{zq} a signé."
    assert len(review.stored()) == 2


@pytest.mark.parametrize("mode", MODES)
def test_correction_then_accepted_overlap(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T21 (AC8): the mirror order, correct then accept."""
    review = _review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        O21,
        [_at(O21, "Zorbal", "PERSON", 0), _at(O21, QV, "PERSON", 7)],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        z_rows, qv_rows = r.found("Zorbal"), r.found(QV)
        pre(len(z_rows) == 1 and len(qv_rows) == 1, "two rows")
        r.state.modify_entity_text(z_rows[0].entity_id, ZQ, 0, 15)
        r.state.accept_entity(qv_rows[0].entity_id)

    review.run(drive)
    output = review.output()
    review.pseudonym(QV)
    zq = review.pseudonym(ZQ)
    assert not any(  # expected failure
        part in output for part in ("Vorlan", "Zorbal", "Quentrix")
    )
    assert output == f"{zq} a signé."
    assert len(review.stored()) == 2


@pytest.mark.parametrize("mode", MODES)
def test_correction_overlap_at_second_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T22 (AC8, AC13 (e); the PO's M1): every place a correction reaches is
    typed, the overlap being only at the second one."""
    review = _review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        O22,
        [
            _at(O22, "Quentrix", "PERSON", 7),
            _at(O22, VZ, "PERSON", 26),
            _at(O22, "Quentrix", "PERSON", 40),
        ],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        q_rows, vz_rows = r.found("Quentrix"), r.found(VZ)
        expected = 1 if r.mode == "single" else 2
        pre(len(q_rows) == expected and len(vz_rows) == 1, "the found rows")
        pre(q_rows[0].entity.start_pos == 7, "the first Quentrix row")
        r.state.accept_entity(vz_rows[0].entity_id)
        r.state.modify_entity_text(q_rows[0].entity_id, ZQ, 0, 15)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    review.pseudonym(VZ)
    zq = review.pseudonym(ZQ)
    assert not any(  # expected failure
        part in output for part in ("Vorlan", "Zorbal", "Quentrix")
    )
    assert output == f"{zq} a validé. {zq} a signé."
    assert len(review.stored()) == 2


# ---------------------------------------------------------------------------
# Guards: what must not change (AC10)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_single_place_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """G1 (AC10): a name added at its only place is written as today."""
    review = _review(mode, qtbot, main_window, tmp_path, ONE, [_nth(ONE, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add(ZQ, "PERSON", 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zq = review.pseudonym(VM), review.pseudonym(ZQ)
    assert output == f"{vm} valide. Le contrat avec {zq}."


@pytest.mark.parametrize("mode", MODES)
def test_selected_place_always_replaced(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """G2 (AC10, AC13 (c)): the place selected is replaced, even inside a
    longer word."""
    review = _review(mode, qtbot, main_window, tmp_path, G2T, [_nth(G2T, VM, "PERSON")])

    def drive(r: _Review, record: dict[str, Any]) -> None:
        r.add("Zorbal", "PERSON", 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    vm, zorbal = review.pseudonym(VM), review.pseudonym("Zorbal")
    assert output == f"{vm} a signé avec {zorbal}ix."


# ---------------------------------------------------------------------------
# Guards added in the rebase on Story 10.20 (no marker: they pass on the code)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_decomposed_document_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """G3 (Story 10.20, its path 9): a document whose accents are stored as
    separate marks (NFD). The app's reader gives the review the composed
    text; a name added by hand there reaches every place, and the written
    file holds no part of it in clear."""
    stored = unicodedata.normalize("NFD", DEC)
    pre(stored != DEC, "the file stores its accents as separate marks")
    review = _Review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        [(stored, [_nth(DEC, VM, "PERSON")])],
        through_reader=True,
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.text == DEC, "the review's text is composed")
        r.add(VQ, "PERSON", 0)
        record["shown"] = r.places_shown(VQ)
        r.accept_pending()

    record = review.run(drive)
    output = review.output()
    vm, vq = review.pseudonym(VM), review.pseudonym(VQ)
    written = unicodedata.normalize("NFC", output)
    assert "Vorlène" not in written and "Quentrix" not in written
    assert output == f"{vm} valide. Le contrat avec {vq}. Signé : {vq}."
    first, second = occurrence(DEC, VQ, 0), occurrence(DEC, VQ, 1)
    assert record["shown"] == [(first, first + len(VQ)), (second, second + len(VQ))]
    assert len(review.stored()) == 2


@pytest.mark.parametrize("mode", MODES)
def test_found_variants_keep_their_decision(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """G4 (AC13 (b); QA's TEST-001): a name the detector found at two places
    (in single-document review one row that stands for both), rejected, then
    added by hand at its third place. The two found places keep the user's
    reject; only the third is written."""
    review = _review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        T2T,
        [_nth(T2T, ZQ, "PERSON", 0), _nth(T2T, ZQ, "PERSON", 1)],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        rows = r.found(ZQ)
        pre(len(rows) == (1 if r.mode == "single" else 2), "the found rows")
        for row in rows:
            r.state.reject_entity(row.entity_id)
        pre(all(row.state == REJECTED for row in rows), "the found rows rejected")
        r.add(ZQ, "PERSON", 2)
        record["found_states"] = [row.state for row in rows]

    record = review.run(drive)
    output = review.output()
    zq = review.pseudonym(ZQ)
    assert output == (
        f"Zorbal Quentrix valide. Le contrat avec Zorbal Quentrix. Signé : {zq}."
    )
    assert record["found_states"] == [REJECTED] * (1 if mode == "single" else 2)
