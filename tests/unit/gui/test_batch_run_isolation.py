"""Story 10.14: a running batch is never mixed with another run or lost.

T1 to T6 and T9 to T11 of the story's Test Plan, written by the BMAD dev agent
(Claude). Each test drives the real ``BatchScreen``, ``ValidationScreen`` and
``BatchWorker`` threads. Only ``DocumentProcessor._detect_and_filter_entities``
is replaced, by a plain function that can hold a document's detection in the
worker's thread until the test releases it. Every ``ConfirmDialog`` is recorded
and answered; the file choosers, ``ProcessingScreen.start_processing`` and the
toasts are recorded and never run. Preconditions fail with
``pytest.fail("PRE: ...")``, never with an ``AssertionError``, so a strict xfail
can only take the expected assertion. Invented names only.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import pytest
from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt, QThreadPool, QUrl
from PySide6.QtGui import QDropEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLabel

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.gui.widgets.toast import Toast
from gdpr_pseudonymizer.gui.workers.batch_worker import BatchResult, BatchWorker
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

# _launch_worker disconnects two slots that are not connected yet
# (batch.py, the validation screen's two signals). PySide6 warns instead of
# raising RuntimeError there, and pytest.ini turns warnings into errors, so
# exactly those two warnings are filtered. This is a warnings filter, not a
# skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000

TEXT_A = "Zorbal Quentrix a signé le contrat."
TEXT_B = "Le contrat est signé avec Quentrel Zorbalia."
SINGLE = "Zorbaville a signé avec Quentrel."
CUSTOM = "Xantor Vellion"
BATCH_ERROR = "Une erreur inattendue s'est produite lors du traitement par lot."

PENDING = EntityReviewState.PENDING
CONFIRMED = EntityReviewState.CONFIRMED

Window = tuple[str, str, str, str]

# Lionel's approved texts (Story 10.14 Q2a and Q2b, 2026-10-16), as the
# informational window shows them: title, message, its one button, no cancel.
MSG_FR: Window = (
    "Lot en cours",
    "Un lot de documents est en cours de traitement. Pour ouvrir un autre "
    "document ou dossier, terminez d'abord ce lot ou arrêtez-le avec "
    "« Annuler le lot ».",
    "Revenir au lot",
    "",
)
MSG_EN: Window = (
    "Batch in progress",
    "A batch of documents is being processed. To open another document or "
    'folder, finish this batch first or stop it with "Cancel batch".',
    "Back to the batch",
    "",
)
# The review screen's « Annuler le lot » window (product strings).
CANCEL_WINDOW: Window = (
    "Annuler le lot",
    "Tous les documents traités seront annulés. "
    "Aucun fichier de sortie ne sera conservé.",
    "Annuler le lot",
    "Annuler",
)

ROUTES = [
    "ctrl_o",
    "ctrl_shift_o",
    "recent_menu",
    "home_batch_button",
    "home_drop_file",
    "home_drop_folder",
    "home_drop_files",
    "home_drop_click",
    "home_recent_list",
]


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test, never with an AssertionError."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _at(text: str, name: str, entity_type: str) -> DetectedEntity:
    start = text.find(name)
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _detections(text: str) -> list[DetectedEntity]:
    """Fresh detections of a test text (a new list of new objects per call)."""
    if text == TEXT_A:
        return [_at(TEXT_A, "Zorbal Quentrix", "PERSON")]
    if text == TEXT_B:
        return [_at(TEXT_B, "Quentrel Zorbalia", "PERSON")]
    if text == SINGLE:
        return [_at(SINGLE, "Zorbaville", "LOCATION")]
    raise RuntimeError()


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


class _Gate:
    """Holds a call in a worker's thread until the test releases it."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self._open = threading.Event()

    def hold(self) -> None:
        self.entered.set()
        if not self._open.wait(WAIT_MS / 1000):
            raise RuntimeError()

    def release(self) -> None:
        self._open.set()


class _Env:
    """What the tests record, and the gates and answers they set."""

    def __init__(self) -> None:
        self.windows: list[Window] = []
        self.answers: list[int] = []
        self.workers: list[Any] = []
        self.ended: list[threading.Event] = []
        self.choosers: list[str] = []
        self.processing: list[str] = []
        self.toasts: list[str] = []
        self.submitted: list[tuple[list[DetectedEntity], Any]] = []
        self.detection_gates: dict[str, _Gate] = {}
        self.finalize_gate: _Gate | None = None
        self.chooser_file = ""
        self.chooser_folder = ""

    def clear(self) -> None:
        self.windows.clear()
        self.answers.clear()
        self.choosers.clear()
        self.processing.clear()
        self.toasts.clear()

    def ended_of(self, worker: Any) -> threading.Event:
        for built, ended in zip(self.workers, self.ended):
            if built is worker:
                return ended
        pytest.fail("PRE: a worker built by the test")


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

    original_worker_init = BatchWorker.__init__

    def record_worker(self: BatchWorker, *args: Any, **kwargs: Any) -> None:
        original_worker_init(self, *args, **kwargs)
        ended = threading.Event()
        # Set in the worker's own thread when its run emits its last signal.
        self.signals.finished.connect(
            lambda *_: ended.set(), Qt.ConnectionType.DirectConnection
        )
        self.signals.error.connect(
            lambda *_: ended.set(), Qt.ConnectionType.DirectConnection
        )
        recorder.workers.append(self)
        recorder.ended.append(ended)

    original_submit = BatchWorker.submit_validation_result

    def record_submission(
        self: BatchWorker,
        entities: list[DetectedEntity],
        custom_pseudonyms: Any = None,
    ) -> None:
        recorder.submitted.append((entities, custom_pseudonyms))
        original_submit(self, entities, custom_pseudonyms)

    def detect(
        processor: DocumentProcessor,
        document_text: str,
        entity_type_filter: Any = None,
    ) -> list[DetectedEntity]:
        gate = recorder.detection_gates.get(document_text)
        if gate is not None:
            gate.hold()
        return _detections(document_text)

    original_finalize = DocumentProcessor.finalize_document

    def finalize(processor: DocumentProcessor, *args: Any, **kwargs: Any) -> Any:
        gate = recorder.finalize_gate
        if gate is not None:
            gate.hold()
        return original_finalize(processor, *args, **kwargs)

    def choose_file(*args: Any, **kwargs: Any) -> tuple[str, str]:
        recorder.choosers.append("file")
        return (recorder.chooser_file, "")

    def choose_folder(*args: Any, **kwargs: Any) -> str:
        recorder.choosers.append("folder")
        return recorder.chooser_folder

    def start_processing(
        self: ProcessingScreen, file_path: str, db_path: str, passphrase: str
    ) -> None:
        recorder.processing.append(file_path)

    def show_toast(
        cls: type[Toast], message: str, parent: Any, duration_ms: int = 3000
    ) -> None:
        recorder.toasts.append(message)

    monkeypatch.setattr(ConfirmDialog, "__init__", record_window)
    monkeypatch.setattr(ConfirmDialog, "exec", answer_window)
    monkeypatch.setattr(BatchWorker, "__init__", record_worker)
    monkeypatch.setattr(BatchWorker, "submit_validation_result", record_submission)
    monkeypatch.setattr(DocumentProcessor, "_detect_and_filter_entities", detect)
    monkeypatch.setattr(DocumentProcessor, "finalize_document", finalize)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(choose_file))
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", staticmethod(choose_folder)
    )
    monkeypatch.setattr(ProcessingScreen, "start_processing", start_processing)
    monkeypatch.setattr(Toast, "show_message", classmethod(show_toast))
    return recorder


def _drop(zone: Any, paths: list[Path]) -> None:
    """A drop on the drop zone (a file, a folder or several files)."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    zone.dropEvent(
        QDropEvent(
            QPointF(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def _click(widget: Any) -> None:
    """A left click sent through Qt's event system, so event filters see it."""
    position = QPointF(10, 10)
    for kind, buttons in (
        (QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton),
    ):
        event = QMouseEvent(
            kind,
            position,
            position,
            Qt.MouseButton.LeftButton,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(widget, event)


@contextmanager
def _language(qapp: Any, language: str) -> Iterator[None]:
    """English through ``switch_language``; back to French the same way."""
    from gdpr_pseudonymizer.gui.i18n.translator import switch_language

    if language == "fr":
        yield
        return
    pre(switch_language(qapp, language), f"switch_language {language}")
    try:
        yield
    finally:
        switch_language(qapp, "fr")


class _Harness:
    """The real batch path: runs started with ``_launch_worker`` (10.10)."""

    def __init__(self, qtbot: Any, main_window: Any, tmp_path: Path, env: _Env):
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.home import HomeScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        self.env = env
        self.tmp = tmp_path
        self.db = str(tmp_path / "mappings.db")
        init_database(self.db, PASSPHRASE)
        main_window.cached_passphrase = (self.db, PASSPHRASE)
        self.out = tmp_path / "out"
        # What a route would open: a file and a folder.
        self.single = tmp_path / "single.txt"
        self.single.write_text(SINGLE, encoding="utf-8")
        self.in2 = tmp_path / "in2"
        self.in2.mkdir()
        (self.in2 / "other.txt").write_text(SINGLE, encoding="utf-8")
        env.chooser_file = str(self.single)
        env.chooser_folder = str(self.in2)
        main_window.show()
        self.bs = self._screen("batch", BatchScreen)
        self.vs = self._screen("validation", ValidationScreen)
        self.home = self._screen("home", HomeScreen)

    def _screen(self, name: str, kind: type) -> Any:
        widget = self.mw.stack.widget(self.mw._screens[name])
        pre(isinstance(widget, kind), f"the {name} screen")
        return widget

    def folder(self, name: str, docs: list[tuple[str, str]]) -> list[Path]:
        folder = self.tmp / name
        folder.mkdir()
        paths: list[Path] = []
        for file_name, text in docs:
            path = folder / file_name
            path.write_text(text, encoding="utf-8")
            paths.append(path)
        return paths

    def launch(self, files: list[Path]) -> Any:
        """Start a run with validation per document; returns its worker."""
        self.bs._files = files
        self.bs._output_input.setText(str(self.out))
        self.bs._validate_checkbox.setChecked(True)
        built = len(self.env.workers)
        self.bs._launch_worker(self.db, PASSPHRASE)
        pre(len(self.env.workers) == built + 1, "one worker built by the launch")
        return self.env.workers[-1]

    def wait(self, condition: Callable[[], bool], message: str) -> None:
        """Wait on a condition; a condition never met is a failed precondition."""
        try:
            self.qtbot.waitUntil(condition, timeout=WAIT_MS)
        except Exception:
            pytest.fail(f"PRE: {message}")

    def ended(self, worker: Any) -> threading.Event:
        return self.env.ended_of(worker)

    def waits(self, worker: Any, index: int) -> bool:
        """The run's worker waits on document ``index`` and its context is kept."""
        return (
            bool(worker._waiting_for_validation)
            and self.bs.awaiting_doc_index == index
            and index in self.bs._validation_contexts
        )

    def intact(self, worker: Any, index: int) -> bool:
        """The batch screen still holds the run, waiting on document ``index``."""
        return self.bs._worker is worker and self.waits(worker, index)

    def wait_doc(self, worker: Any, index: int) -> Any:
        """Wait until document ``index`` waits on the validation screen."""
        vs = self.vs
        self.wait(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == index
            and vs.validation_state is not None
            and self.waits(worker, index),
            f"document {index} waits",
        )
        return vs.validation_state

    def accept_and_validate(self) -> str:
        """Accept every pending row of the review shown and validate it.

        Returns the text of the review that was validated."""
        state = self.vs.validation_state
        pre(state is not None, "a review is shown")
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        text = str(state.session.document_text)
        pre(self.vs.finalize_button.isEnabled(), "the validate button is enabled")
        self.vs.finalize_button.click()
        return text

    def wait_end(self, worker: Any) -> None:
        ended = self.ended(worker)
        self.wait(
            lambda: ended.is_set() and self.bs._worker is not worker,
            "the run ended",
        )

    def complete(self, worker: Any, docs: int, start: int = 0) -> list[str]:
        """Validate the run's documents from ``start`` on, each once it waits
        (reached through its cached context), then wait for the run's end.
        Stops at once if the batch screen no longer holds the run. Returns the
        texts of the reviews validated."""
        texts: list[str] = []
        for index in range(start, docs):
            self.wait(
                lambda index=index: self.waits(worker, index)
                or self.bs._worker is not worker,
                f"document {index} waits",
            )
            if self.bs._worker is not worker:
                return texts
            if self.mw.stack.currentWidget() is not self.vs or (
                self.vs.doc_index != index
            ):
                self.mw.navigate_to("validation", **self.bs._validation_contexts[index])
            texts.append(self.accept_and_validate())
        self.wait_end(worker)
        return texts

    def go_home(self) -> None:
        """Home through Outils › "Paramètres...", then "Retour"."""
        from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen

        self.mw._action_settings.trigger()
        pre(self.mw.current_screen_name() == "settings", "the settings screen")
        self._screen("settings", SettingsScreen)._back_btn.click()
        pre(self.mw.current_screen_name() == "home", "the home screen")

    def _recent_rows(self) -> list[Any]:
        layout = self.home._recent_layout
        widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
        return [
            w for w in widgets if w is not None and w.objectName() == "recentFileRow"
        ]

    def prepare(self, route: str) -> None:
        """What a route needs before it is taken (recent entries, home)."""
        if route in ("recent_menu", "home_recent_list"):
            self.mw.config["recent_files"] = [str(self.single)]
            self.mw._rebuild_recent_menu()
        if route.startswith("home_"):
            self.go_home()
            self.home._rebuild_recent_list()

    def route(self, route: str) -> None:
        mw, home = self.mw, self.home
        if route == "ctrl_o":
            mw._action_open.trigger()
        elif route == "ctrl_shift_o":
            mw._action_open_folder.trigger()
        elif route == "recent_menu":
            entries = [
                a for a in mw._recent_menu.actions() if a.text() == str(self.single)
            ]
            pre(len(entries) == 1, "the recent menu's entry")
            entries[0].trigger()
        elif route == "home_batch_button":
            home._batch_btn.click()
        elif route == "home_drop_file":
            _drop(home.drop_zone, [self.single])
        elif route == "home_drop_folder":
            _drop(home.drop_zone, [self.in2])
        elif route == "home_drop_files":
            _drop(home.drop_zone, [self.single, self.in2 / "other.txt"])
        elif route == "home_drop_click":
            _click(home.drop_zone)
        elif route == "home_recent_list":
            rows = self._recent_rows()
            pre(len(rows) == 1, "the recent list's row")
            rows[0].mousePressEvent(None)
        else:
            pytest.fail(f"PRE: unknown route {route}")

    def output(self, name: str) -> str:
        return (self.out / name).read_text(encoding="utf-8")

    def finish(self) -> None:
        """Release every gate and end every worker built.

        A cancel that lands between a worker's ``validation_required`` and its
        wait is lost (Codex #10, backlog), so the cancel is repeated on every
        poll until the run has ended."""
        for gate in self.env.detection_gates.values():
            gate.release()
        if self.env.finalize_gate is not None:
            self.env.finalize_gate.release()
        for worker, ended in zip(self.env.workers, self.env.ended):

            def stopped(worker: Any = worker, ended: threading.Event = ended) -> bool:
                if not ended.is_set():
                    worker.cancel()
                return ended.is_set()

            self.qtbot.waitUntil(stopped, timeout=WAIT_MS)
        QThreadPool.globalInstance().waitForDone(WAIT_MS)
        QApplication.processEvents()


# ---------------------------------------------------------------------------
# T1 (AC1, AC6): every open route during a running batch is refused
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("route", ROUTES)
def test_open_route_during_batch_is_refused(  # type: ignore[no-untyped-def]
    qtbot, qapp, main_window, tmp_path: Path, env: _Env, route: str, language: str
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files = h.folder("in", [("doc0.txt", TEXT_A)])
    with _language(qapp, language):
        try:
            worker = h.launch(files)
            state = h.wait_doc(worker, 0)
            h.prepare(route)
            before = h.mw.stack.currentWidget()
            recent = list(h.mw.config.get("recent_files", []))
            env.clear()
            env.answers = [0]
            h.route(route)
            windows = list(env.windows)
            choosers = list(env.choosers)
            record = (
                h.mw.stack.currentWidget() is before,
                list(env.processing),
                len(env.workers),
                h.bs._worker is worker,
                bool(worker._waiting_for_validation),
                h.bs.awaiting_doc_index,
                h.bs._phases.currentIndex(),
                h.bs._files == files,
                h.mw.config.get("recent_files", []) == recent,
                list(env.toasts),
                h.vs.validation_state is state,
            )
            if h.intact(worker, 0):
                h.complete(worker, 1)
        finally:
            h.finish()

    assert windows == [MSG_FR if language == "fr" else MSG_EN]  # expected failure
    assert record == (True, [], 1, True, True, 0, 1, True, True, [], True)
    assert choosers == []
    replaced = written_as(h.output("doc0_pseudonymized.txt"), TEXT_A, [(0, 15)])
    assert stored_rows(h.db) == [("Zorbal Quentrix", "PERSON", replaced[0])]


# ---------------------------------------------------------------------------
# T2 (AC2): « Revenir au lot » brings back the running batch where it waits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "where",
    [
        "review_from_home",
        "review_from_database_ctrl_o",
        "progress_from_home_drop_folder",
    ],
)
def test_back_to_the_batch(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env, where: str
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files = h.folder("in", [("doc0.txt", TEXT_A), ("doc1.txt", TEXT_B)])
    progress = where.startswith("progress")
    gate = _Gate()
    if progress:
        env.detection_gates[TEXT_B] = gate
    try:
        worker = h.launch(files)
        state = h.wait_doc(worker, 0)
        for review in state.get_all_entities():
            state.accept_entity(review.entity_id)
        if progress:
            h.vs.finalize_button.click()
            h.wait(
                lambda: gate.entered.is_set()
                and h.mw.current_screen_name() == "batch"
                and h.bs.awaiting_doc_index is None,
                "document 1's detection held, the progress screen shown",
            )
            h.go_home()
        elif where == "review_from_home":
            h.go_home()
        else:
            h.mw._action_db.trigger()
            pre(h.mw.current_screen_name() == "database", "the database screen")
        env.clear()
        env.answers = [1]
        if progress:
            _drop(h.home.drop_zone, [h.in2])
        elif where == "review_from_home":
            h.home._batch_btn.click()
        else:
            h.mw._action_open.trigger()
        windows = list(env.windows)
        if progress:
            record: tuple[Any, ...] = (
                h.mw.current_screen_name(),
                h.bs._phases.currentIndex(),
                h.bs._worker is worker,
                len(env.workers),
            )
            gate.release()
            h.complete(worker, 2, start=1)
        else:
            reviews = state.get_all_entities()
            record = (
                h.mw.current_screen_name(),
                h.vs.doc_index,
                h.vs.validation_state is state,
                reviews[0].state if reviews else None,
                h.bs._worker is worker,
                len(env.workers),
            )
            h.complete(worker, 2)
    finally:
        h.finish()

    assert windows == [MSG_FR]  # expected failure
    if progress:
        assert record == ("batch", 1, True, 1)
    else:
        assert record == ("validation", 0, True, CONFIRMED, True, 1)
    written_as(h.output("doc0_pseudonymized.txt"), TEXT_A, [(0, 15)])
    written_as(h.output("doc1_pseudonymized.txt"), TEXT_B, [(26, 43)])


# ---------------------------------------------------------------------------
# T3 (AC2): after the home route, « Annuler le lot » still stops the batch
# ---------------------------------------------------------------------------


def test_cancel_still_stops_the_batch_after_home_route(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files = h.folder("in", [("doc0.txt", TEXT_A), ("doc1.txt", TEXT_B)])
    try:
        worker = h.launch(files)
        h.wait_doc(worker, 0)
        h.go_home()
        env.clear()
        env.answers = [1, 1]
        h.home._batch_btn.click()
        if h.mw.stack.currentWidget() is not h.vs:
            pre(0 in h.bs._validation_contexts, "document 0's context is kept")
            h.mw.navigate_to("validation", **h.bs._validation_contexts[0])
        pre(h.vs.batch_cancel_button.isVisibleTo(h.vs), "« Annuler le lot » shown")
        h.vs.batch_cancel_button.click()
        ended = h.ended(worker)
        h.wait(
            lambda: ended.is_set() or h.bs._worker is None,
            "the run ended or the batch screen holds no worker",
        )
        windows = list(env.windows)
        ended_by_cancel = ended.is_set()
        built = len(env.workers)
    finally:
        h.finish()

    assert windows == [MSG_FR, CANCEL_WINDOW]  # expected failure
    assert ended_by_cancel is True
    assert built == 1
    assert not (h.out / "doc0_pseudonymized.txt").exists()


# ---------------------------------------------------------------------------
# T4 (#1, AC3): a second run never mixes with the first, in both orders
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("order", ["A_first", "B_first"])
def test_second_run_never_mixes_with_the_first(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env, order: str
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files_a = h.folder("lotA", [("lotA.txt", TEXT_A)])
    files_b = h.folder("lotB", [("lotB.txt", TEXT_B)])
    gate_a, gate_b = _Gate(), _Gate()
    env.detection_gates = {TEXT_A: gate_a, TEXT_B: gate_b}

    def cached(text: str) -> bool:
        context = h.bs._validation_contexts.get(0)
        return context is not None and context.get("document_text") == text

    try:
        worker_a = h.launch(files_a)
        h.wait(gate_a.entered.is_set, "run A's detection held")
        # Run B started the way a route AC1 missed would start it.
        worker_b = h.launch(files_b)
        h.wait(gate_b.entered.is_set, "run B's detection held")
        ended_a, ended_b = h.ended(worker_a), h.ended(worker_b)

        def a_settled() -> bool:
            return ended_a.is_set() or cached(TEXT_A)

        def b_waits() -> bool:
            return (
                cached(TEXT_B)
                and bool(worker_b._waiting_for_validation)
                and h.mw.stack.currentWidget() is h.vs
                and h.vs.validation_state is not None
            )

        if order == "A_first":
            gate_a.release()
            h.wait(a_settled, "run A ended or its document is cached")
            gate_b.release()
            h.wait(b_waits, "run B's document waits")
        else:
            gate_b.release()
            h.wait(b_waits, "run B's document waits")
            gate_a.release()
            h.wait(a_settled, "run A ended or its document is cached")
        review_text = h.accept_and_validate()
        h.wait(ended_b.is_set, "run B ended")
        a_ended_by_itself = ended_a.is_set()
    finally:
        h.finish()

    output = h.output("lotB_pseudonymized.txt")
    replaced = written_as(output, TEXT_B, [(26, 43)])  # expected failure, A_first
    for part in ("Zorbal", "Quentr", "a signé le"):
        assert part not in output
    assert a_ended_by_itself is True  # expected failure, B_first
    assert review_text == TEXT_B
    assert stored_rows(h.db) == [("Quentrel Zorbalia", "PERSON", replaced[0])]


# ---------------------------------------------------------------------------
# T5 (AC3): the signals of an old run are ignored
# ---------------------------------------------------------------------------


def test_signals_of_an_old_run_are_ignored(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files_a = h.folder("lotA", [("lotA.txt", TEXT_A)])
    files_b = h.folder("lotB", [("lotB.txt", TEXT_B)])
    gate_b = _Gate()
    env.detection_gates[TEXT_B] = gate_b
    try:
        worker_a = h.launch(files_a)
        signals_a = worker_a.signals
        h.complete(worker_a, 1)
        pre(h.bs._phases.currentIndex() == 2, "run A's summary shown")
        worker_b = h.launch(files_b)
        h.wait(gate_b.entered.is_set, "run B's detection held")
        env.clear()
        signals_a.validation_required.emit(_detections(TEXT_A), TEXT_A, 0, 1)
        signals_a.progress.emit(100, "DOC_DONE:0")
        signals_a.finished.emit(BatchResult(total_files=1, successful_files=1))
        signals_a.error.emit(BATCH_ERROR)
        record = (
            h.mw.current_screen_name(),
            h.bs._phases.currentIndex(),
            h.bs._worker is worker_b,
            sorted(h.bs._validation_contexts),
            h.bs.awaiting_doc_index,
            list(env.windows),
        )
        gate_b.release()
        texts = h.complete(worker_b, 1)
    finally:
        h.finish()

    assert record == ("batch", 1, True, [], None, [])  # expected failure
    assert texts == [TEXT_B]
    written_as(h.output("lotB_pseudonymized.txt"), TEXT_B, [(26, 43)])


# ---------------------------------------------------------------------------
# T6 (AC4, batch): the hand-off shares nothing with the kept review
# ---------------------------------------------------------------------------


def test_batch_handoff_shares_nothing_with_the_kept_review(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files = h.folder("in", [("doc0.txt", TEXT_A)])
    gate = _Gate()
    env.finalize_gate = gate
    try:
        worker = h.launch(files)
        state = h.wait_doc(worker, 0)
        reviews = state.get_all_entities()
        pre(len(reviews) == 1, "one row")
        row_id = reviews[0].entity_id
        monkeypatch.setattr(
            QInputDialog, "getText", staticmethod(lambda *a, **k: (CUSTOM, True))
        )
        h.vs._handle_entity_action(row_id, "change_pseudonym")
        state.accept_entity(row_id)
        pre(
            list(state.get_custom_pseudonyms().values()) == [CUSTOM],
            "the custom pseudonym is set",
        )
        h.vs.finalize_button.click()
        h.wait(gate.entered.is_set, "the worker holds before it writes")
        pre(len(env.submitted) == 1, "one list submitted")
        sent, customs = env.submitted[0]
        row_entities = [review.entity for review in state.get_all_entities()]
        shared = [e for e in sent if any(e is entity for entity in row_entities)]
        sent_customs = list(customs.values()) if isinstance(customs, dict) else None
        state.modify_entity_text(row_id, "Zorbal", 0, 6)
        moved = state.get_review(row_id)
        pre(
            moved is not None
            and (moved.entity.start_pos, moved.entity.end_pos) == (0, 6),
            "the kept review's row now spans 0-6",
        )
        gate.release()
        h.wait_end(worker)
    finally:
        h.finish()

    assert shared == []  # expected failure
    assert sent_customs == [CUSTOM]
    assert h.output("doc0_pseudonymized.txt") == f"{CUSTOM} a signé le contrat."
    assert stored_rows(h.db) == [("Zorbal Quentrix", "PERSON", CUSTOM)]


# ---------------------------------------------------------------------------
# T9 (AC6): the review screen's batch cancel button in English
# ---------------------------------------------------------------------------


def test_english_review_cancel_button(  # type: ignore[no-untyped-def]
    qtbot, qapp, main_window, tmp_path: Path, env: _Env
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files = h.folder("in", [("doc0.txt", TEXT_A)])
    with _language(qapp, "en"):
        try:
            worker = h.launch(files)
            h.wait_doc(worker, 0)
            qapp.processEvents()
            h.vs.retranslateUi()
            h.bs.retranslateUi()
            labels = (h.vs.batch_cancel_button.text(), h.bs._cancel_btn.text())
            h.complete(worker, 1)
        finally:
            h.finish()

    assert labels == ("Cancel batch", "Cancel batch")  # expected failure


# ---------------------------------------------------------------------------
# T10 (AC1, guard): the routes are unchanged when no batch runs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("moment", ["before_any_batch", "after_summary"])
@pytest.mark.parametrize("route", ["ctrl_o", "ctrl_shift_o", "home_batch_button"])
def test_routes_unchanged_when_no_batch_runs(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env, route: str, moment: str
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    try:
        if moment == "after_summary":
            worker = h.launch(h.folder("in", [("doc0.txt", TEXT_A)]))
            h.complete(worker, 1)
            pre(
                h.bs._phases.currentIndex() == 2 and h.bs._worker is None,
                "the run's summary shown",
            )
        h.prepare(route)
        env.clear()
        h.route(route)
        windows = list(env.windows)
        choosers = list(env.choosers)
        processing = list(env.processing)
        screen = (
            h.mw.current_screen_name(),
            h.bs._phases.currentIndex(),
            [path.name for path in h.bs._files],
            h.bs._worker is None,
        )
    finally:
        h.finish()

    assert windows == []
    if route == "ctrl_o":
        assert (choosers, processing) == (["file"], [str(h.single)])
    elif route == "ctrl_shift_o":
        assert (choosers, screen) == (["folder"], ("batch", 0, ["other.txt"], True))
    else:
        assert (choosers, screen) == ([], ("batch", 0, [], True))


# ---------------------------------------------------------------------------
# T11 (AC1): "Démarrer" while a batch runs is refused
# ---------------------------------------------------------------------------


def test_start_while_a_batch_runs_is_refused(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path: Path, env: _Env
) -> None:
    h = _Harness(qtbot, main_window, tmp_path, env)
    files = h.folder("in", [("doc0.txt", TEXT_A)])
    try:
        h.mw.navigate_to("batch", folder_path=str(files[0].parent))
        h.bs._output_input.setText(str(h.out))
        h.bs._validate_checkbox.setChecked(True)
        pre([path.name for path in h.bs._files] == ["doc0.txt"], "the folder's file")
        pre(h.bs._start_btn.isEnabled(), "« Démarrer » enabled")
        h.bs._start_btn.click()
        pre(len(env.workers) == 1, "one worker started")
        first = env.workers[0]
        h.wait_doc(first, 0)
        pre(h.bs._start_btn.isEnabled(), "« Démarrer » still enabled in phase 1")
        env.clear()
        env.answers = [0]
        h.bs._start_btn.click()
        windows = list(env.windows)
        record = (
            len(env.workers),
            h.bs._worker is first,
            bool(first._waiting_for_validation),
        )
        if h.intact(first, 0):
            h.complete(first, 1)
    finally:
        h.finish()

    assert windows == [MSG_FR]  # expected failure
    assert record == (1, True, True)
    written_as(h.output("doc0_pseudonymized.txt"), TEXT_A, [(0, 15)])
