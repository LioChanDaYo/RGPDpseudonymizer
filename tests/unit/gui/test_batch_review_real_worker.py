"""Story 10.10: desktop batch review through the real batch worker (T1-T5, T11, T12).

Each test drives the real ``BatchScreen``, ``ValidationScreen`` and
``BatchWorker`` thread; only ``DocumentProcessor._detect_and_filter_entities``
is replaced. Observations needed later are recorded during the flow and the
assertions run after the worker has finished, so the written files exist. Each
test asserts its preconditions (messages start with "PRE:") before the
behaviour under test; the first assertion after them is the expected failure on
the unfixed code. Invented names only.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QLabel

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered. This is a warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
NOTICE = "batchDocumentNotice"

DOC0 = "Zorbaville a signé à Zorbaville."
DOC1 = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
RICH = (
    "Quentrel Zorbalia a signé avec Quentrix à Zorbaville. "
    "Le contrat est avec Zorbalia. Le projet est avec Zorbal. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
SINGLE = "Zorbal a signé le contrat."

PENDING = EntityReviewState.PENDING
CONFIRMED = EntityReviewState.CONFIRMED
REJECTED = EntityReviewState.REJECTED
MODIFIED = EntityReviewState.MODIFIED
ADDED = EntityReviewState.ADDED

_XFAIL = "Story 10.10: reproduces {} on the unfixed batch review; fixed in Task 2"


def _xfail(failure: str) -> pytest.MarkDecorator:
    return pytest.mark.xfail(
        strict=True, raises=AssertionError, reason=_XFAIL.format(failure)
    )


def _at(
    text: str,
    name: str,
    entity_type: str,
    start: int,
    source: str = "spacy",
    is_ambiguous: bool = False,
) -> DetectedEntity:
    assert text[start : start + len(name)] == name, "PRE: entity slice"
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source=source,
        is_ambiguous=is_ambiguous,
    )


def _doc0_entities() -> list[DetectedEntity]:
    return [
        _at(DOC0, "Zorbaville", "ORG", 0),
        _at(DOC0, "Zorbaville", "ORG", 21),
        _at(DOC0, "Zorbaville", "LOCATION", 0, source="regex", is_ambiguous=True),
    ]


def _doc1_entities() -> list[DetectedEntity]:
    return [
        _at(DOC1, "Quentrel Zorbalia", "PERSON", 0),
        _at(DOC1, "Quentrel Zorbalia", "PERSON", 63),
    ]


def _rich_entities() -> list[DetectedEntity]:
    return [
        _at(RICH, "Quentrel Zorbalia", "PERSON", 0),
        _at(RICH, "avec Quentrix", "PERSON", RICH.find("avec Quentrix")),
        _at(RICH, "Zorbaville", "ORG", RICH.find("Zorbaville")),
        _at(RICH, "Zorbalia", "LOCATION", RICH.find("avec Zorbalia.") + 5),
        _at(RICH, "Quentrel Zorbalia", "PERSON", RICH.rfind("Quentrel Zorbalia")),
    ]


def _rows(state: Any) -> list[tuple[Any, ...]]:
    """Every decision of every row: text, type, span, state, edit, pseudonym."""
    return [
        (
            r.entity.text,
            r.entity.entity_type,
            r.entity.start_pos,
            r.entity.end_pos,
            r.state.value,
            r.user_modification,
            r.custom_pseudonym,
        )
        for r in state.get_all_entities()
    ]


def _sorted_spans(entities: list[DetectedEntity]) -> list[tuple[str, int, int]]:
    return sorted((e.entity_type, e.start_pos, e.end_pos) for e in entities)


def assert_clean(
    output: str, source: str, spans: list[tuple[int, int]], banned: tuple[str, ...]
) -> None:
    """The output is the source with each span replaced by a non-empty string,
    every other character unchanged, and no banned part anywhere."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    assert match is not None, f"text damaged or a span not replaced: {output!r}"
    for part in banned:
        assert part not in output, f"{part!r} left in the output: {output!r}"


def _notice_visible(vs: Any) -> bool:
    """Whether the batch line under the header is shown, with a text."""
    label = vs.findChild(QLabel, NOTICE)
    return label is not None and label.isVisibleTo(vs) and bool(label.text().strip())


class _Batch:
    """A real batch run with validation per document; only detection replaced."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        docs: list[tuple[str, list[DetectedEntity]]],
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        source_dir = tmp_path / "in"
        source_dir.mkdir()
        self.out = tmp_path / "out"
        self.db = str(tmp_path / "mappings.db")
        init_database(self.db, PASSPHRASE)
        self._by_text: dict[str, list[DetectedEntity]] = {}
        files: list[Path] = []
        for index, (text, entities) in enumerate(docs):
            path = source_dir / f"doc{index}.txt"
            path.write_text(text, encoding="utf-8")
            files.append(path)
            self._by_text[text] = entities
        main_window.show()
        main_window.navigate_to("batch")
        self.bs = main_window.stack.currentWidget()
        assert isinstance(self.bs, BatchScreen), "PRE: batch screen"
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        assert isinstance(self.vs, ValidationScreen), "PRE: validation screen"
        self.bs._files = files
        self.bs._output_input.setText(str(self.out))
        self.bs._validate_checkbox.setChecked(True)

    def _detect(self, text: str) -> list[DetectedEntity]:
        return [DetectedEntity(**vars(e)) for e in self._by_text[text]]

    def run(self, body: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Run the batch; ``body`` drives it. Returns what ``body`` recorded."""
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

    def output(self, index: int) -> str:
        return (self.out / f"doc{index}_pseudonymized.txt").read_text(encoding="utf-8")

    def doc0_decide_and_validate(self) -> list[tuple[Any, ...]]:
        """QA's probe G on doc 0: retype LOCATION to PERSON, accept the ORG group,
        validate. Returns doc 0's rows just before the click."""
        state = self.wait_doc(0)
        reviews = state.get_all_entities()
        assert [r.entity.entity_type for r in reviews] == [
            "ORG",
            "ORG",
            "LOCATION",
        ], "PRE: doc 0 rows"
        location = next(r for r in reviews if r.entity.entity_type == "LOCATION")
        org = next(r for r in reviews if r.entity.entity_type == "ORG")
        state.change_entity_type(location.entity_id, "PERSON")
        state.accept_entity(org.entity_id)
        rows = _rows(state)
        self.vs.finalize_button.click()
        return rows

    def go_previous(self) -> None:
        """'◀ Précédent' from doc 1 to doc 0."""
        assert self.vs.prev_button.isVisibleTo(self.vs), "PRE: Précédent visible"
        self.vs.prev_button.click()
        assert self.vs.doc_index == 0, "PRE: on doc 0"
        texts = [r.entity.text for r in self.vs.validation_state.get_all_entities()]
        assert texts == ["Zorbaville"] * 3, "PRE: doc 0 rows shown"

    def go_next(self) -> None:
        """'Suivant ▶' from doc 0 to doc 1."""
        self.vs.next_button.click()
        assert self.vs.doc_index == 1, "PRE: back on doc 1"

    def accept_pending_and_validate(self) -> None:
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        self.vs.finalize_button.click()


def _doc1_accepted(batch: _Batch) -> Any:
    state = batch.wait_doc(1)
    reviews = state.get_all_entities()
    assert [r.state for r in reviews] == [PENDING, PENDING], "PRE: doc 1 pending"
    state.accept_entity(reviews[0].entity_id)
    assert [r.state for r in reviews] == [
        CONFIRMED,
        CONFIRMED,
    ], "PRE: doc 1 accepted"
    return state


DOC1_SPANS = [(0, 17), (63, 80)]
DOC1_BANNED = ("Quentrel", "Zorbalia", "orbalia")
DOC0_SPANS = [(0, 10), (21, 31)]


# ---------------------------------------------------------------------------
# PRE-001
# ---------------------------------------------------------------------------


@_xfail("doc 1 written with doc 0's positions (PRE-001)")
@pytest.mark.parametrize("how", ["button", "handler"])
def test_prev_then_validate_never_sends_to_waiting_doc(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, how
) -> None:
    """AC1: 'Valider et continuer' on an earlier document never reaches the
    document the worker waits on."""
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (DOC1, _doc1_entities())],
    )
    vs = batch.vs

    def body(record: dict[str, Any]) -> None:
        batch.doc0_decide_and_validate()
        _doc1_accepted(batch)
        batch.go_previous()
        if how == "button":
            vs.finalize_button.click()
        else:
            vs._on_finalize()
        record["still_on_validation"] = main_window.stack.currentWidget() is vs
        record["doc_index"] = vs.doc_index
        record["finalize_enabled"] = vs.finalize_button.isEnabled()
        record["notice"] = _notice_visible(vs)
        record["stored_1_at_click"] = 1 in batch.bs._validation_results
        if record["still_on_validation"]:
            batch.go_next()
            batch.accept_pending_and_validate()

    record = batch.run(body)
    assert_clean(batch.output(1), DOC1, DOC1_SPANS, DOC1_BANNED)  # expected failure
    assert_clean(batch.output(0), DOC0, DOC0_SPANS, ("Zorbaville",))
    assert _sorted_spans(batch.bs._validation_results[1]) == [
        ("PERSON", 0, 17),
        ("PERSON", 63, 80),
    ]
    assert record["still_on_validation"] is True
    assert record["doc_index"] == 0
    assert record["finalize_enabled"] is False
    assert record["notice"] is True
    assert record["stored_1_at_click"] is False
    table = batch.bs.summary_table
    assert [
        (table.item(r, 0).text(), table.item(r, 1).text(), table.item(r, 3).text())
        for r in range(table.rowCount())
    ] == [("doc0.txt", "3", "Traité"), ("doc1.txt", "2", "Traité")]


def test_batch_without_going_back_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC8 guard: a batch run that never goes back writes the same files."""
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (DOC1, _doc1_entities())],
    )

    def body(record: dict[str, Any]) -> None:
        batch.doc0_decide_and_validate()
        _doc1_accepted(batch)
        batch.vs.finalize_button.click()

    batch.run(body)
    assert_clean(batch.output(1), DOC1, DOC1_SPANS, DOC1_BANNED)
    assert_clean(batch.output(0), DOC0, DOC0_SPANS, ("Zorbaville",))
    assert sorted(batch.bs._validation_results) == [0, 1]


# ---------------------------------------------------------------------------
# PRE-002
# ---------------------------------------------------------------------------


@_xfail("the accepts lost by 'Précédent' then 'Suivant' (PRE-002)")
def test_prev_next_keeps_accepts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC2: 'Précédent' then 'Suivant' keeps doc 1's accepts and its undo."""
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (DOC1, _doc1_entities())],
    )

    def body(record: dict[str, Any]) -> None:
        batch.doc0_decide_and_validate()
        state = _doc1_accepted(batch)
        record["before"] = _rows(state)
        batch.go_previous()
        batch.go_next()
        state = batch.vs.validation_state
        record["after"] = _rows(state)
        state.undo_stack.undo()
        record["after_undo"] = [r.state for r in state.get_all_entities()]
        batch.accept_pending_and_validate()

    record = batch.run(body)
    assert record["after"] == record["before"]  # expected failure
    assert record["after_undo"] == [PENDING, PENDING]
    assert_clean(batch.output(1), DOC1, DOC1_SPANS, DOC1_BANNED)


@_xfail("every decision lost by two round trips (PRE-002)")
def test_every_decision_kind_survives_two_round_trips(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC2: accept, custom pseudonym, edit, reject, type change and an added row
    all survive two round trips, and the file is written from them."""
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (RICH, _rich_entities())],
    )
    added_start = RICH.find("avec Zorbal.") + 5
    edit_start = RICH.find("avec Quentrix") + 5
    lone_start = RICH.find("avec Zorbalia.") + 5
    last_start = RICH.rfind("Quentrel Zorbalia")

    def body(record: dict[str, Any]) -> None:
        batch.doc0_decide_and_validate()
        state = batch.wait_doc(1)
        reviews = state.get_all_entities()
        assert len(reviews) == 5, "PRE: 5 rows"
        known = reviews[2]
        assert (
            known.entity.text == "Zorbaville"
            and known.state == CONFIRMED
            and state.is_entity_known(known.entity_id)
        ), "PRE: the known row"
        assert [r.state for r in (reviews[0], reviews[1], reviews[3], reviews[4])] == [
            PENDING
        ] * 4, "PRE: the other rows pending"
        state.accept_entity(reviews[0].entity_id)
        state.change_pseudonym(reviews[0].entity_id, "Xantor Vellion")
        state.modify_entity_text(
            reviews[1].entity_id, "Quentrix", edit_start, edit_start + 8
        )
        state.reject_entity(known.entity_id)
        state.change_entity_type(reviews[3].entity_id, "PERSON")
        state.add_entity("Zorbal", "PERSON", added_start, added_start + 6)
        assert [r.state for r in state.get_all_entities()] == [
            MODIFIED,
            MODIFIED,
            REJECTED,
            MODIFIED,
            CONFIRMED,
            ADDED,
        ], "PRE: the decisions made"
        record["before"] = _rows(state)
        record["after"] = []
        for _ in range(2):
            batch.go_previous()
            batch.go_next()
            record["after"].append(_rows(batch.vs.validation_state))
        batch.vs.finalize_button.click()

    record = batch.run(body)
    spans = [
        (0, 17),
        (edit_start, edit_start + 8),
        (lone_start, lone_start + 8),
        (added_start, added_start + 6),
        (last_start, last_start + 17),
    ]
    output = batch.output(1)
    assert_clean(output, RICH, spans, ("Quentr", "orbal"))  # expected failure
    assert output.count("Zorbaville") == 1
    assert record["after"] == [record["before"], record["before"]]


@_xfail("an earlier document shown without its decisions (PRE-002)")
def test_previous_document_shows_its_decisions(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC2: 'Précédent' shows a validated document with the decisions it was
    validated with."""
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (DOC1, _doc1_entities())],
    )

    def body(record: dict[str, Any]) -> None:
        record["doc0_validated"] = batch.doc0_decide_and_validate()
        batch.wait_doc(1)
        batch.go_previous()
        record["doc0_shown"] = _rows(batch.vs.validation_state)
        batch.go_next()
        batch.accept_pending_and_validate()

    record = batch.run(body)
    assert record["doc0_shown"] == record["doc0_validated"]  # expected failure


# ---------------------------------------------------------------------------
# AC11: a single document never reaches a batch
# ---------------------------------------------------------------------------


def _single_result(
    db: str, tmp_path: Path, text: str, entities: list[DetectedEntity]
) -> DetectionResult:
    """Run the real DetectionWorker synchronously, with detection replaced."""
    finished: list[object] = []
    worker = DetectionWorker(
        file_path=str(tmp_path / "single.txt"), db_path=db, passphrase=PASSPHRASE
    )
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


@_xfail("a single document left in batch mode after a batch run (AC11)")
@pytest.mark.parametrize("ending", ["batch_completed", "cancelled_from_earlier_doc"])
def test_single_document_after_batch_run_leaves_batch_mode(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, ending
) -> None:
    """AC11: a single document validated after a batch run is in
    single-document mode."""
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (DOC1, _doc1_entities())],
    )
    vs = batch.vs

    def body(record: dict[str, Any]) -> None:
        batch.doc0_decide_and_validate()
        if ending == "batch_completed":
            _doc1_accepted(batch)
            vs.finalize_button.click()
        else:
            batch.wait_doc(1)
            batch.go_previous()
            vs.batch_cancel_requested.emit()  # what "Annuler le lot" emits

    batch.run(body)
    if ending == "batch_completed":
        assert sorted(batch.bs._validation_results) == [0, 1], "PRE: batch finished"
    else:
        assert batch.bs._batch_result.cancelled, "PRE: batch cancelled"
        assert not batch.out.exists() or not any(
            batch.out.iterdir()
        ), "PRE: no output file left"
    result = _single_result(batch.db, tmp_path, DOC1, _doc1_entities())
    vs.start_validation(result)
    main_window.navigate_to("validation")
    assert vs.batch_mode is False  # expected failure
    assert not vs.batch_header.isVisibleTo(vs)
    assert vs.back_button.isVisibleTo(vs)
    assert vs.finalize_button.isEnabled()
    assert not _notice_visible(vs)


class _NoDialog:
    """A confirmation dialog the user answers with "no"."""

    def exec(self) -> int:
        return 0


@_xfail("a single document written over the waiting batch document (AC1, AC11)")
def test_single_document_opened_during_batch_never_reaches_worker(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
) -> None:
    """AC1, AC11: a single document opened while a batch waits (Ctrl+O, a
    recent file) never reaches the waiting batch document."""
    from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC0, _doc0_entities()), (DOC1, _doc1_entities())],
    )
    monkeypatch.setattr(
        ConfirmDialog, "proceeding", staticmethod(lambda *a, **k: _NoDialog())
    )
    vs = batch.vs

    def body(record: dict[str, Any]) -> None:
        batch.doc0_decide_and_validate()
        batch.wait_doc(1)
        result = _single_result(
            batch.db, tmp_path, SINGLE, [_at(SINGLE, "Zorbal", "PERSON", 0)]
        )
        vs.start_validation(result)  # what Ctrl+O or a recent file leads to
        main_window.navigate_to("validation")
        state = vs.validation_state
        reviews = state.get_all_entities()
        assert [r.entity.text for r in reviews] == ["Zorbal"], "PRE: single document"
        state.accept_entity(reviews[0].entity_id)
        vs.finalize_button.click()
        record["screen_at_call"] = main_window.current_screen_name()
        record["stored_1_at_call"] = 1 in batch.bs._validation_results
        if main_window.current_screen_name() == "validation":
            # Back to the waiting batch document, then validate it.
            vs.set_context(**batch.bs._validation_contexts[1])
            batch.accept_pending_and_validate()

    record = batch.run(body)
    assert_clean(batch.output(1), DOC1, DOC1_SPANS, DOC1_BANNED)  # expected failure
    assert _sorted_spans(batch.bs._validation_results[1]) == [
        ("PERSON", 0, 17),
        ("PERSON", 63, 80),
    ]
    assert record["screen_at_call"] == "validation"
    assert record["stored_1_at_call"] is False
