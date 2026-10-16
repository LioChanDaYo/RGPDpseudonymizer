"""Story 10.13: T1 (AC2, AC6), T2 (AC1 B2a, AC2), T3 (AC1 B2b), T4 (AC1),
T5 (AC3), T6 (AC5).

Written by Codex through Forge; invented names only. These tests drive the real
desktop batch and single workers with detection replaced. Preconditions fail;
observations are recorded during review and asserted after the worker finishes.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QLabel

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
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
DOC_A = "Zorbalia Quentrix a signé avec Quentrelle à Zorbaville. Quentrelle confirme."
DOC1 = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
PENDING = EntityReviewState.PENDING
CONFIRMED = EntityReviewState.CONFIRMED
Window = tuple[str, str, str, str]


def pre(condition: bool, message: str) -> None:
    """Fail a precondition outside strict AssertionError-only xfail handling."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def warn_fr(n: int) -> Window:
    return (
        "Noms encore à vérifier",
        f"Noms encore à vérifier dans ce document : {n}.\n"
        "Un nom ni accepté ni rejeté n'est pas pseudonymisé : "
        "il reste en clair dans le fichier de sortie.\n"
        "Continuer quand même ?",
        "Continuer quand même",
        "Annuler",
    )


def warn_en(n: int) -> Window:
    return (
        "Names still to review",
        f"Names still to review in this document: {n}.\n"
        "A name neither accepted nor rejected is not pseudonymized: "
        "it stays in plain text in the output file.\n"
        "Continue anyway?",
        "Continue anyway",
        "Cancel",
    )


def summary_fr(a: int, r: int, d: int, m: int) -> Window:
    return (
        "Résumé de validation",
        f"Vous avez accepté {a} entités, rejeté {r}, ajouté {d} manuellement "
        f"et modifié {m} pseudonymes.\n\nContinuer avec la pseudonymisation ?",
        "Confirmer",
        "Annuler",
    )


def _at(
    text: str,
    name: str,
    entity_type: str,
    start: int,
    source: str = "spacy",
    is_ambiguous: bool = False,
) -> DetectedEntity:
    pre(text[start : start + len(name)] == name, "entity_slice")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source=source,
        is_ambiguous=is_ambiguous,
    )


def _doc_a_entities() -> list[DetectedEntity]:
    return [
        _at(DOC_A, "Zorbalia Quentrix", "PERSON", DOC_A.find("Zorbalia Quentrix")),
        _at(DOC_A, "Quentrelle", "PERSON", DOC_A.find("Quentrelle")),
        _at(DOC_A, "Zorbaville", "LOCATION", DOC_A.find("Zorbaville")),
        _at(DOC_A, "Quentrelle", "PERSON", DOC_A.rfind("Quentrelle")),
    ]


def _doc1_entities() -> list[DetectedEntity]:
    return [
        _at(DOC1, "Quentrel Zorbalia", "PERSON", DOC1.find("Quentrel Zorbalia")),
        _at(DOC1, "Quentrel Zorbalia", "PERSON", DOC1.rfind("Quentrel Zorbalia")),
    ]


def _rows(state: Any) -> list[tuple[str, EntityReviewState]]:
    return [(r.entity.text, r.state) for r in state.get_all_entities()]


def _accept_doc_a_decisions(state: Any) -> None:
    """Accept the person and location while leaving Quentrelle pending."""
    for review in state.get_all_entities():
        if review.entity.text in ("Zorbalia Quentrix", "Zorbaville"):
            state.accept_entity(review.entity_id)


def _check_doc_a_batch_rows(state: Any) -> None:
    pre(
        _rows(state)
        == [
            ("Zorbalia Quentrix", CONFIRMED),
            ("Quentrelle", PENDING),
            ("Zorbaville", CONFIRMED),
            ("Quentrelle", PENDING),
        ],
        "doc_a_batch_rows",
    )


def assert_written_as_today(
    output: str, source: str, spans: list[tuple[int, int]]
) -> None:
    """Each span becomes non-empty text; every other character stays intact."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    assert re.fullmatch(pattern, output, flags=re.DOTALL) is not None


class _Dialogs:
    """Record built windows and supply queued answers, defaulting to confirm."""

    def __init__(self) -> None:
        self.shown: list[Window] = []
        self.answers: list[int] = []


@pytest.fixture()
def dialogs(monkeypatch: pytest.MonkeyPatch) -> _Dialogs:
    recorder = _Dialogs()
    original_init = ConfirmDialog.__init__

    def record_window(self: ConfirmDialog, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        label = self.findChild(QLabel)
        pre(label is not None, "confirm_dialog_label")
        recorder.shown.append(
            (
                self.windowTitle(),
                cast(QLabel, label).text(),
                self.confirm_button.text(),
                self.cancel_button.text(),
            )
        )

    def answer_window(self: ConfirmDialog) -> int:
        return recorder.answers.pop(0) if recorder.answers else 1

    monkeypatch.setattr(ConfirmDialog, "__init__", record_window)
    monkeypatch.setattr(ConfirmDialog, "exec", answer_window)
    return recorder


class _Batch:
    """Run real batch review with fresh detection copies for each document."""

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
        pre(isinstance(self.bs, BatchScreen), "batch_screen")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation_screen")
        self.bs._files = files
        self.bs._output_input.setText(str(self.out))
        self.bs._validate_checkbox.setChecked(True)

    def _detect(self, text: str) -> list[DetectedEntity]:
        return [DetectedEntity(**vars(e)) for e in self._by_text[text]]

    def run(self, body: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        record: dict[str, Any] = {}
        with patch.object(
            DocumentProcessor, "_detect_and_filter_entities", side_effect=self._detect
        ):
            self.bs._launch_worker(self.db, PASSPHRASE)
            try:
                body(record)
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=60000)
            finally:
                if self.bs._worker is not None:
                    self.bs._worker.cancel()
                    self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=60000)
        return record

    def wait_doc(self, index: int) -> Any:
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == index
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=60000,
        )
        return vs.validation_state

    def output(self, index: int) -> str:
        return (self.out / f"doc{index}_pseudonymized.txt").read_text(encoding="utf-8")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.13: no warning window before the batch writes a name still "
    "to review on the unfixed code; fixed in Task 2",
)
def test_batch_cancel_sends_nothing_and_batch_waits(
    qtbot, main_window, tmp_path: Path, dialogs: _Dialogs
) -> None:  # type: ignore[no-untyped-def]
    """T1 pins AC2/AC6: cancel keeps the batch waiting and sends nothing."""
    entities = _doc_a_entities()
    batch = _Batch(qtbot, main_window, tmp_path, [(DOC_A, entities)])
    dialogs.answers = [0, 1]

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        _accept_doc_a_decisions(state)
        _check_doc_a_batch_rows(state)
        pre(
            batch.vs.finalize_button.text() == "Valider et terminer ▶",
            "finalize_button",
        )
        batch.vs.finalize_button.click()
        record["windows"] = list(dialogs.shown)
        record["first_click"] = (
            batch.mw.stack.currentWidget() is batch.vs,
            0 in batch.bs._validation_results,
            batch.bs._worker is not None and batch.bs._worker._waiting_for_validation,
            batch.bs.awaiting_doc_index,
            (batch.out / "doc0_pseudonymized.txt").exists(),
        )
        if batch.mw.stack.currentWidget() is batch.vs:
            batch.vs.finalize_button.click()

    record = batch.run(body)
    assert record["windows"] == [warn_fr(1)]  # expected failure
    assert record["first_click"] == (True, False, True, 0, False)
    assert dialogs.shown == [warn_fr(1), warn_fr(1)]
    output = batch.output(0)
    assert_written_as_today(
        output,
        DOC_A,
        [(e.start_pos, e.end_pos) for e in entities if e.text != "Quentrelle"],
    )
    assert output.count("Quentrelle") == 2


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.13: 'Valider et continuer' sends a name still to review "
    "without a window on the unfixed code; fixed in Task 2",
)
def test_batch_continue_counts_one_name_and_writes_as_today(
    qtbot, main_window, tmp_path: Path, dialogs: _Dialogs
) -> None:  # type: ignore[no-untyped-def]
    """T2 pins AC1 B2a/AC2: two pending places warn once; decided doc skips it."""
    entities = _doc_a_entities()
    batch = _Batch(
        qtbot,
        main_window,
        tmp_path,
        [(DOC_A, entities), (DOC1, _doc1_entities())],
    )
    dialogs.answers = [1]

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        _accept_doc_a_decisions(state)
        _check_doc_a_batch_rows(state)
        pre(state.get_pending_count() == 2, "get_pending_count")
        pre(
            batch.vs.finalize_button.text() == "Valider et continuer ▶",
            "finalize_button",
        )
        batch.vs.finalize_button.click()
        record["windows"] = list(dialogs.shown)
        state = batch.wait_doc(1)
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        pre(_rows(state) == [("Quentrel Zorbalia", CONFIRMED)] * 2, "doc1_rows")
        pre(
            batch.vs.finalize_button.text() == "Valider et terminer ▶",
            "finalize_button",
        )
        batch.vs.finalize_button.click()

    record = batch.run(body)
    assert record["windows"] == [warn_fr(1)]  # expected failure
    assert dialogs.shown == [warn_fr(1)]
    output = batch.output(0)
    assert_written_as_today(
        output,
        DOC_A,
        [(e.start_pos, e.end_pos) for e in entities if e.text != "Quentrelle"],
    )
    assert output.count("Quentrelle") == 2
    output = batch.output(1)
    assert_written_as_today(output, DOC1, [(0, 17), (63, 80)])
    assert "orbalia" not in output


DOC0 = "Zorbaville a signé à Zorbaville."
DOC_P = "Quentrel Zorbalia a signé le contrat."


def _detect_single_document(
    tmp_path: Path, text: str, entities: list[DetectedEntity]
) -> Any:
    """Run real detection and variant grouping with fresh invented detections."""
    from gdpr_pseudonymizer.gui.workers.detection_worker import (
        DetectionResult,
        DetectionWorker,
    )

    file_path = tmp_path / "doc0.txt"
    file_path.write_text(text, encoding="utf-8")
    db_path = str(tmp_path / "mappings.db")
    init_database(db_path, PASSPHRASE)
    worker = DetectionWorker(str(file_path), db_path, PASSPHRASE)
    worker.setAutoDelete(False)
    results: list[Any] = []
    errors: list[str] = []
    worker.signals.finished.connect(results.append)
    worker.signals.error.connect(errors.append)
    with patch.object(
        DocumentProcessor,
        "detect_entities",
        return_value=(text, [DetectedEntity(**vars(e)) for e in entities]),
    ):
        worker.run()
    pre(not errors, "detection_error")
    pre(len(results) == 1, "detection_result_count")
    pre(isinstance(results[0], DetectionResult), "detection_result")
    return results[0]


class _Single:
    """Review and finalize one document through the real desktop screens."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        text: str,
        entities: list[DetectedEntity],
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        result = _detect_single_document(tmp_path, text, entities)
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation_screen")
        main_window.show()
        self.vs.start_validation(result)
        main_window.navigate_to("validation")
        pre(not self.vs.batch_mode, "single_document_mode")
        pre(self.vs.validation_state is not None, "validation_state")

    def output(self) -> str:
        self.qtbot.waitUntil(
            lambda: self.mw.current_screen_name() == "results", timeout=60000
        )
        results = self.mw.stack.currentWidget()
        return Path(results._temp_path).read_text(encoding="utf-8")


def _doc0_entities() -> list[DetectedEntity]:
    return [
        _at(DOC0, "Zorbaville", "ORG", 0),
        _at(DOC0, "Zorbaville", "ORG", 21),
        _at(DOC0, "Zorbaville", "LOCATION", 0, "regex", is_ambiguous=True),
    ]


def _accept_doc0_orgs(state: Any) -> None:
    """Accept each ORG row and leave the overlapping LOCATION pending."""
    for review in state.get_all_entities():
        if review.entity.entity_type == "ORG":
            state.accept_entity(review.entity_id)


def _check_doc0_rows(state: Any, org_count: int) -> None:
    rows = [
        (review.entity.text, review.entity.entity_type, review.state)
        for review in state.get_all_entities()
    ]
    pre(len(rows) == org_count + 1, "doc0_row_count")
    pre(rows.count(("Zorbaville", "ORG", CONFIRMED)) == org_count, "doc0_org_rows")
    pre(rows.count(("Zorbaville", "LOCATION", PENDING)) == 1, "doc0_location_row")


@pytest.mark.parametrize("mode", ["batch", "single"], ids=["batch", "single"])
def test_same_place_other_type_counts_zero(
    qtbot, main_window, tmp_path: Path, dialogs: _Dialogs, mode: str
) -> None:  # type: ignore[no-untyped-def]
    """T3 guards AC1 B2b: accepted spans cover pending places of another type."""
    entities = _doc0_entities()
    dialogs.answers = [1]
    if mode == "batch":
        batch = _Batch(qtbot, main_window, tmp_path, [(DOC0, entities)])

        def body(record: dict[str, Any]) -> None:
            state = batch.wait_doc(0)
            _accept_doc0_orgs(state)
            _check_doc0_rows(state, 2)
            pre(
                batch.vs.finalize_button.text() == "Valider et terminer ▶",
                "finalize_button",
            )
            batch.vs.finalize_button.click()

        batch.run(body)
        output = batch.output(0)
        expected_windows: list[Window] = []
    else:
        single = _Single(qtbot, main_window, tmp_path, DOC0, entities)
        state = single.vs.validation_state
        _accept_doc0_orgs(state)
        _check_doc0_rows(state, 1)
        pre(single.vs.finalize_button.text() == "Finaliser ▶", "finalize_button")
        single.vs.finalize_button.click()
        output = single.output()
        expected_windows = [summary_fr(1, 0, 0, 0)]

    assert dialogs.shown == expected_windows
    assert "Zorbaville" not in output


def _doc_p_entities(case: str) -> list[DetectedEntity]:
    pre(case in ("partial", "two_pieces", "dedup_dropped"), "doc_p_case")
    if case == "dedup_dropped":
        return [
            _at(DOC_P, "Quentrel", "PERSON", 0),
            _at(DOC_P, "rel Zorbalia", "ORG", 5),
            _at(DOC_P, "Zorbalia", "LOCATION", 9),
        ]
    entities = [
        _at(DOC_P, "Quentrel Zorbalia", "PERSON", 0),
        _at(DOC_P, "Quentrel", "ORG", 0),
    ]
    if case == "two_pieces":
        entities.append(_at(DOC_P, "Zorbalia", "ORG", 9))
    return entities


def _accept_except_type(state: Any, pending_type: str) -> None:
    """Accept every row except the planned pending type."""
    for review in state.get_all_entities():
        if review.entity.entity_type != pending_type:
            state.accept_entity(review.entity_id)


def _check_doc_p_rows(
    state: Any, entities: list[DetectedEntity], pending_type: str
) -> None:
    rows = state.get_all_entities()
    pre(len(rows) == len(entities), "doc_p_row_count")
    expected = {
        (e.text, e.entity_type, e.start_pos, e.end_pos): (
            PENDING if e.entity_type == pending_type else CONFIRMED
        )
        for e in entities
    }
    observed = {
        (
            r.entity.text,
            r.entity.entity_type,
            r.entity.start_pos,
            r.entity.end_pos,
        ): r.state
        for r in rows
    }
    pre(observed == expected, "doc_p_rows")
    pre(sum(r.state == PENDING for r in rows) == 1, "doc_p_pending_count")


@pytest.mark.parametrize(
    "case",
    ["partial", "two_pieces", "dedup_dropped"],
    ids=["partial", "two_pieces", "dedup_dropped"],
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.13: the summary window comes first and no warning counts "
    "a name left in clear on the unfixed code; fixed in Task 2",
)
def test_count_rule_cases(
    qtbot, main_window, tmp_path: Path, dialogs: _Dialogs, case: str
) -> None:  # type: ignore[no-untyped-def]
    """T4 pins AC1: partial, combined and dropped spans leave a pending name."""
    entities = _doc_p_entities(case)
    single = _Single(qtbot, main_window, tmp_path, DOC_P, entities)
    dialogs.answers = [1, 1]
    pending_type = "LOCATION" if case == "dedup_dropped" else "PERSON"
    state = single.vs.validation_state
    _accept_except_type(state, pending_type)
    _check_doc_p_rows(state, entities, pending_type)
    pre(single.vs.finalize_button.text() == "Finaliser ▶", "finalize_button")
    single.vs.finalize_button.click()
    output = single.output()

    assert dialogs.shown[:1] == [warn_fr(1)]  # expected failure
    spans = [(0, 8), (9, 17)] if case == "two_pieces" else [(0, 8)]
    assert_written_as_today(output, DOC_P, spans)


def _check_doc_a_single_rows(state: Any) -> None:
    """Check the canonical rows after accepting the person and location."""
    pre(
        _rows(state)
        == [
            ("Zorbalia Quentrix", CONFIRMED),
            ("Quentrelle", PENDING),
            ("Zorbaville", CONFIRMED),
        ],
        "doc_a_single_rows",
    )


@pytest.fixture()
def finalization_constructions(monkeypatch: pytest.MonkeyPatch) -> list[None]:
    """Count worker constructions while preserving the real initializer."""
    from gdpr_pseudonymizer.gui.workers.finalization_worker import (
        FinalizationWorker,
    )

    constructions: list[None] = []
    original_init = FinalizationWorker.__init__

    def count_construction(self: FinalizationWorker, *args: Any, **kwargs: Any) -> None:
        constructions.append(None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(FinalizationWorker, "__init__", count_construction)
    return constructions


@pytest.fixture()
def english(qapp, main_window) -> Iterator[None]:  # type: ignore[no-untyped-def]
    """Use English after window setup and restore French even on failure."""
    from gdpr_pseudonymizer.gui.i18n.translator import switch_language

    try:
        pre(switch_language(qapp, "en"), "switch_language_en")
        yield
    finally:
        switch_language(qapp, "fr")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.13: 'Finaliser' shows only the summary window with a name "
    "still to review on the unfixed code; fixed in Task 2",
)
def test_single_cancel_writes_nothing_then_continue(
    qtbot,
    main_window,
    tmp_path: Path,
    dialogs: _Dialogs,
    finalization_constructions: list[None],
) -> None:  # type: ignore[no-untyped-def]
    """T5 pins AC3: cancel starts nothing; continuing keeps finalization intact."""
    entities = _doc_a_entities()
    single = _Single(qtbot, main_window, tmp_path, DOC_A, entities)
    dialogs.answers = [0, 1, 1]
    state = single.vs.validation_state
    _accept_doc_a_decisions(state)
    _check_doc_a_single_rows(state)
    pre(single.vs.finalize_button.text() == "Finaliser ▶", "finalize_button")

    single.vs.finalize_button.click()
    first_windows = list(dialogs.shown)
    first_click = (
        len(finalization_constructions),
        main_window.current_screen_name(),
        single.vs.finalize_button.isEnabled(),
        single.vs.back_button.isEnabled(),
    )
    single.vs.finalize_button.click()
    output = single.output()

    assert first_windows == [warn_fr(1)]  # expected failure
    assert first_click == (0, "validation", True, True)
    assert dialogs.shown == [warn_fr(1), warn_fr(1), summary_fr(2, 0, 0, 0)]
    assert_written_as_today(
        output,
        DOC_A,
        [(e.start_pos, e.end_pos) for e in entities if e.text != "Quentrelle"],
    )
    assert output.count("Quentrelle") == 2


@pytest.mark.parametrize("mode", ["batch", "single"], ids=["batch", "single"])
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.13: no English warning window on the unfixed code; "
    "fixed in Task 2",
)
def test_english_texts(
    qtbot,
    main_window,
    tmp_path: Path,
    dialogs: _Dialogs,
    english,
    finalization_constructions: list[None],
    mode: str,
) -> None:  # type: ignore[no-untyped-def]
    """T6 pins AC5: the English warning includes Cancel in both review modes."""
    entities = _doc_a_entities()
    dialogs.answers = [0, 1]
    if mode == "batch":
        batch = _Batch(qtbot, main_window, tmp_path, [(DOC_A, entities)])

        def body(record: dict[str, Any]) -> None:
            state = batch.wait_doc(0)
            _accept_doc_a_decisions(state)
            _check_doc_a_batch_rows(state)
            batch.vs.finalize_button.click()
            if batch.mw.stack.currentWidget() is batch.vs:
                batch.vs.finalize_button.click()

        batch.run(body)
        output = batch.output(0)
    else:
        single = _Single(qtbot, main_window, tmp_path, DOC_A, entities)
        state = single.vs.validation_state
        _accept_doc_a_decisions(state)
        _check_doc_a_single_rows(state)
        single.vs.finalize_button.click()

    assert dialogs.shown[:1] == [warn_en(1)]  # expected failure
    if mode == "batch":
        assert_written_as_today(
            output,
            DOC_A,
            [(e.start_pos, e.end_pos) for e in entities if e.text != "Quentrelle"],
        )
        assert output.count("Quentrelle") == 2
    else:
        assert len(finalization_constructions) == 0
