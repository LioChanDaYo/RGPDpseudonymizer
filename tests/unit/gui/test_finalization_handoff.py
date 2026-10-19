"""Story 10.14: a document is written exactly as the user confirmed it.

T7 and T8 of the story's Test Plan, and T12, a guard of Story 10.13's count
(QA 10.13, TEST-001). Written by the BMAD dev agent (Claude). Each test drives
the real ``ValidationScreen`` and ``FinalizationWorker`` thread. Only
``DocumentProcessor.detect_entities`` is replaced, and
``DocumentProcessor.finalize_document`` can be held in the worker's thread,
before it reads its input, until the test releases it. Every ``ConfirmDialog``
is recorded and answered. Preconditions fail with ``pytest.fail("PRE: ...")``,
never with an ``AssertionError``, so a strict xfail can only take the expected
assertion. Invented names only.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QInputDialog, QLabel

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.screens.results import ResultsScreen
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000

TEXT_A = "Zorbal Quentrix a signé le contrat."
SINGLE = "Zorbaville a signé avec Quentrel."
DOC_H = "Zorbaville a signé avec Quentrix à Zorbaville."
CUSTOM = "Xantor Vellion"

PENDING = EntityReviewState.PENDING
REJECTED = EntityReviewState.REJECTED

Window = tuple[str, str, str, str]

# Story 10.13's window with the count 1 (Lionel's approved 10.13 texts, Q2a).
WARN_FR_1: Window = (
    "Noms encore à vérifier",
    "Noms encore à vérifier dans ce document : 1.\n"
    "Un nom ni accepté ni rejeté n'est pas pseudonymisé : "
    "il reste en clair dans le fichier de sortie.\n"
    "Continuer quand même ?",
    "Continuer quand même",
    "Annuler",
)


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test, never with an AssertionError."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _at(
    text: str,
    name: str,
    entity_type: str,
    start: int,
    source: str = "spacy",
    is_ambiguous: bool = False,
) -> DetectedEntity:
    pre(text[start : start + len(name)] == name, f"{name} at {start}")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source=source,
        is_ambiguous=is_ambiguous,
    )


def written_as(output: str, source: str, spans: list[tuple[int, int]]) -> list[str]:
    """The output is the source with each span replaced by a non-empty string
    and every other character unchanged. Returns the replacements."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    assert match is not None, f"not written as expected: {output!r}"
    return list(match.groups())


def stored_rows(db: str) -> list[tuple[str, str, str]]:
    """(full name, type, full pseudonym) of every stored row, decrypted, sorted."""
    with open_database(db, PASSPHRASE) as session:
        rows = SQLiteMappingRepository(session).find_all()
        return sorted((r.full_name, r.entity_type, r.pseudonym_full) for r in rows)


def _controls(vs: Any) -> list[bool]:
    """The editor, the list and the screen's six shortcuts."""
    shortcuts = (
        vs._undo_shortcut,
        vs._redo_shortcut,
        vs._redo_shortcut2,
        vs._find_shortcut,
        vs._accept_all_shortcut,
        vs._reject_all_shortcut,
    )
    return [vs.editor.isEnabled(), vs.panel.isEnabled()] + [
        shortcut.isEnabled() for shortcut in shortcuts
    ]


class _Gate:
    """Holds a call in a worker's thread until the test releases it."""

    def __init__(self, fail_after: bool = False) -> None:
        self.entered = threading.Event()
        self._open = threading.Event()
        self._fail_after = fail_after

    def hold(self) -> None:
        self.entered.set()
        if not self._open.wait(WAIT_MS / 1000):
            raise RuntimeError()
        if self._fail_after:
            raise RuntimeError()

    def release(self) -> None:
        self._open.set()


class _Env:
    """What the tests record, the finalization gate and the answers."""

    def __init__(self) -> None:
        self.windows: list[Window] = []
        self.answers: list[int] = []
        self.results: list[str] = []
        self.finalize_gate: _Gate | None = None


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch) -> _Env:
    recorder = _Env()

    original_dialog_init = ConfirmDialog.__init__

    def record_window(self: ConfirmDialog, *args: Any, **kwargs: Any) -> None:
        original_dialog_init(self, *args, **kwargs)
        label = self.findChild(QLabel)
        pre(label is not None, "the window's message label")
        recorder.windows.append(
            (
                self.windowTitle(),
                cast(QLabel, label).text(),
                self.confirm_button.text(),
                self.cancel_button.text(),
            )
        )

    def answer_window(self: ConfirmDialog) -> int:
        return recorder.answers.pop(0) if recorder.answers else 1

    original_finalize = DocumentProcessor.finalize_document

    def finalize(processor: DocumentProcessor, *args: Any, **kwargs: Any) -> Any:
        gate = recorder.finalize_gate
        if gate is not None:
            gate.hold()
        return original_finalize(processor, *args, **kwargs)

    original_show_results = ResultsScreen.show_results

    def record_results(self: ResultsScreen, *args: Any, **kwargs: Any) -> Any:
        recorder.results.append(str(kwargs.get("content", "")))
        return original_show_results(self, *args, **kwargs)

    monkeypatch.setattr(ConfirmDialog, "__init__", record_window)
    monkeypatch.setattr(ConfirmDialog, "exec", answer_window)
    monkeypatch.setattr(DocumentProcessor, "finalize_document", finalize)
    monkeypatch.setattr(ResultsScreen, "show_results", record_results)
    return recorder


class _Single:
    """The real single-document path: detection, review, finalization."""

    def __init__(self, qtbot: Any, main_window: Any, tmp_path: Path, env: _Env):
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        self.env = env
        self.tmp = tmp_path
        self.db = str(tmp_path / "mappings.db")
        init_database(self.db, PASSPHRASE)
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "the validation screen")
        main_window.show()
        self._results_seen = 0

    def open(self, name: str, text: str, entities: list[DetectedEntity]) -> Any:
        """Detect a document through the real ``DetectionWorker`` (detection
        replaced) and show its review; returns the review state."""
        from gdpr_pseudonymizer.gui.workers.detection_worker import (
            DetectionResult,
            DetectionWorker,
        )

        file_path = self.tmp / name
        file_path.write_text(text, encoding="utf-8")
        worker = DetectionWorker(str(file_path), self.db, PASSPHRASE)
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
        pre(not errors and len(results) == 1, "one detection result")
        pre(isinstance(results[0], DetectionResult), "a detection result")
        self.vs.start_validation(results[0])
        self.mw.navigate_to("validation")
        pre(not self.vs.batch_mode, "single-document review")
        pre(self.vs.validation_state is not None, "a review state")
        return self.vs.validation_state

    def wait(self, condition: Callable[[], bool], message: str) -> None:
        """Wait on a condition; a condition never met is a failed precondition."""
        try:
            self.qtbot.waitUntil(condition, timeout=WAIT_MS)
        except Exception:
            pytest.fail(f"PRE: {message}")

    def hold_finalize(self, fail_after: bool = False) -> _Gate:
        gate = _Gate(fail_after)
        self.env.finalize_gate = gate
        return gate

    def wait_results(self) -> str:
        """Wait for the results screen of the next written document."""
        seen = self._results_seen
        self.wait(
            lambda: len(self.env.results) > seen
            and self.mw.current_screen_name() == "results",
            "the results screen",
        )
        self._results_seen = len(self.env.results)
        return self.env.results[-1]

    def finish(self) -> None:
        if self.env.finalize_gate is not None:
            self.env.finalize_gate.release()
        QThreadPool.globalInstance().waitForDone(WAIT_MS)
        QApplication.processEvents()


# ---------------------------------------------------------------------------
# T7 (#4, AC4): the file holds what was confirmed, whatever the review does
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.14: finalization writes the review's live entities, so a "
    "change made after « Confirmer » changes the file, on the unfixed code; "
    "fixed in Task 2",
)
@pytest.mark.parametrize(
    "case", ["edit_generated", "edit_custom", "undo_generated", "undo_custom"]
)
def test_finalization_writes_what_was_confirmed(  # type: ignore[no-untyped-def]
    qtbot,
    main_window,
    tmp_path: Path,
    env: _Env,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    edit = case.startswith("edit")
    custom = case.endswith("custom")
    single = _Single(qtbot, main_window, tmp_path, env)
    detected_type = "PERSON" if edit else "ORG"
    try:
        state = single.open(
            "doc0.txt", TEXT_A, [_at(TEXT_A, "Zorbal Quentrix", detected_type, 0)]
        )
        reviews = state.get_all_entities()
        pre(len(reviews) == 1, "one row")
        row_id = reviews[0].entity_id
        if not edit:
            state.change_entity_type(row_id, "PERSON")
        if custom:
            monkeypatch.setattr(
                QInputDialog, "getText", staticmethod(lambda *a, **k: (CUSTOM, True))
            )
            single.vs._handle_entity_action(row_id, "change_pseudonym")
            pre(
                list(state.get_custom_pseudonyms().values()) == [CUSTOM],
                "the custom pseudonym is set",
            )
        state.accept_entity(row_id)
        review = state.get_review(row_id)
        pre(
            review is not None
            and review.entity.entity_type == "PERSON"
            and review.state not in (PENDING, REJECTED),
            "the row is PERSON and kept",
        )
        gate = single.hold_finalize()
        env.answers = [1]
        single.vs.finalize_button.click()
        single.wait(gate.entered.is_set, "the worker holds before it reads its input")
        if edit:
            state.modify_entity_text(row_id, "Zorbal", 0, 6)
            moved = state.get_review(row_id)
            pre(
                moved is not None
                and (moved.entity.start_pos, moved.entity.end_pos) == (0, 6),
                "the row now spans 0-6",
            )
        else:
            while state.undo_stack.canUndo():
                state.undo_stack.undo()
            undone = state.get_review(row_id)
            pre(
                undone is not None and undone.entity.entity_type == "ORG",
                "the row is ORG again",
            )
        gate.release()
        output = single.wait_results()
    finally:
        single.finish()

    rows = stored_rows(single.db)
    pseudonym = CUSTOM if custom else (rows[0][2] if rows else "")
    assert (output, rows) == (  # expected failure
        f"{pseudonym} a signé le contrat.",
        [("Zorbal Quentrix", "PERSON", pseudonym)],
    )
    assert "Zorbal" not in output and "Quentrix" not in output


# ---------------------------------------------------------------------------
# T8 (AC5): the review cannot change while a document is written
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.14: the editor, the list and the shortcuts stay enabled while "
    "a document is written, on the unfixed code; fixed in Task 2",
)
@pytest.mark.parametrize("case", ["failure", "success_then_next"])
def test_review_disabled_while_writing_and_enabled_again(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env, case: str
) -> None:
    single = _Single(qtbot, main_window, tmp_path, env)
    try:
        state = single.open(
            "doc0.txt", TEXT_A, [_at(TEXT_A, "Zorbal Quentrix", "PERSON", 0)]
        )
        for review in state.get_all_entities():
            state.accept_entity(review.entity_id)
        pre(_controls(single.vs) == [True] * 8, "the review's controls enabled")
        gate = single.hold_finalize(fail_after=case == "failure")
        env.answers = [1, 1]
        single.vs.finalize_button.click()
        single.wait(gate.entered.is_set, "the worker holds before it writes")
        during = _controls(single.vs)
        buttons = (
            single.vs.finalize_button.isEnabled(),
            single.vs.back_button.isEnabled(),
        )
        gate.release()
        if case == "failure":
            single.wait(
                lambda: any(w[0] == "Erreur de pseudonymisation" for w in env.windows),
                "the error window",
            )
        else:
            single.wait_results()
            single.open(
                "single.txt", SINGLE, [_at(SINGLE, "Zorbaville", "LOCATION", 0)]
            )
        after = _controls(single.vs) + [
            single.vs.finalize_button.isEnabled(),
            single.vs.back_button.isEnabled(),
        ]
    finally:
        single.finish()

    assert during == [False] * 8  # expected failure
    assert buttons == (False, False)
    assert after == [True] * 10


# ---------------------------------------------------------------------------
# T12 (guard of Story 10.13's AC1): a variant place left in clear is counted
# ---------------------------------------------------------------------------


def test_variant_place_left_in_clear_is_counted(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env
) -> None:
    single = _Single(qtbot, main_window, tmp_path, env)
    second = DOC_H.rfind("Zorbaville")
    try:
        state = single.open(
            "doc0.txt",
            DOC_H,
            [
                _at(DOC_H, "Zorbaville", "ORG", 0),
                _at(DOC_H, "Zorbaville", "LOCATION", 0, "regex", is_ambiguous=True),
                _at(DOC_H, "Zorbaville", "LOCATION", second),
                _at(DOC_H, "Quentrix", "PERSON", DOC_H.find("Quentrix")),
            ],
        )
        reviews = state.get_all_entities()
        rows = {(r.entity.text, r.entity.entity_type): r for r in reviews}
        pre(
            len(reviews) == 3
            and sorted(rows)
            == [
                ("Quentrix", "PERSON"),
                ("Zorbaville", "LOCATION"),
                ("Zorbaville", "ORG"),
            ],
            "three rows",
        )
        location = rows[("Zorbaville", "LOCATION")]
        places = state._variant_occurrences.get(
            state._variant_key(location, location.entity), [location.entity]
        )
        pre(
            sorted(o.start_pos for o in places) == [0, second],
            "the LOCATION row stands for both places",
        )
        state.accept_entity(rows[("Zorbaville", "ORG")].entity_id)
        state.accept_entity(rows[("Quentrix", "PERSON")].entity_id)
        pre(
            [r.entity.entity_type for r in reviews if r.state == PENDING]
            == ["LOCATION"],
            "only the LOCATION row is still to review",
        )
        env.answers = [1, 1]
        single.vs.finalize_button.click()
        output = single.wait_results()
    finally:
        single.finish()

    assert env.windows[:1] == [WARN_FR_1]
    assert [window[0] for window in env.windows] == [
        "Noms encore à vérifier",
        "Résumé de validation",
    ]
    written_as(output, DOC_H, [(0, 10), (24, 32)])
    assert output.count("Zorbaville") == 1 and output.endswith("à Zorbaville.")
