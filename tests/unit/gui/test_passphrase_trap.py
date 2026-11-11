"""Story 11.4: two passphrase traps of the desktop app (T1-T7, T12-T18).

Written by the BMAD dev agent (Claude).

- First trap: the passphrase window accepted a passphrase that a new mapping
  database refuses (fewer than 12 characters). With « Mémoriser pour cette
  session » ticked, every document opened on its own was then refused, and
  the remembered passphrase was never forgotten (T1-T7).
- Second trap: a wrong passphrase for an existing database went unnoticed
  until the end of a document or of a batch, and stayed remembered
  (T12-T18).

The real passphrase window, screens and workers run offscreen. Error windows
are recorded (``_Dialogs``), never shown. The passphrase window opened by a
screen is replaced by a counter that answers « Annuler ». Detection is
replaced by a stand-in that finds the invented « Quentrel Zorbalia »: for a
single document at ``DocumentProcessor.detect_entities`` (what
``DetectionWorker`` calls), for a batch at ``DocumentProcessor._get_detector``
(what every batch path reaches). No spaCy model is loaded.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and passphrases only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.exceptions import FileProcessingError
from gdpr_pseudonymizer.gui.widgets import passphrase_dialog as pd
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.gui.workers.batch_worker import BatchWorker
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionWorker
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

# The window's new label and the worker's message for a new database (T-FR1,
# W-MSG12), and the worker's message for a wrong passphrase (W-MSGBAD).
MSG_12 = "La phrase secrète doit contenir au moins 12 caractères."
MSG_BAD = "Phrase secrète incorrecte. Veuillez réessayer."
MSG_CREATE = "Impossible de créer la base de correspondances : "

PASSPHRASE = "zorbalia_pass_A_123!"
WRONG = "mauvaise_phrase_9!"
SHORT_8 = "court123"
SHORT_11 = "onze_carac!"
TWELVE = "douze_caract"

NAME = "Quentrel Zorbalia"
TEXT = "Quentrel Zorbalia a signé le contrat."
PLAIN = "Compte rendu de la séance.\n"

_MODEL_INSTALLED = (
    "gdpr_pseudonymizer.gui.workers.model_manager.ModelManager.is_model_installed"
)


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test with "PRE: ..." (``pytest.fail``
    raises ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _entity() -> DetectedEntity:
    return DetectedEntity(
        text=NAME,
        entity_type="PERSON",
        start_pos=0,
        end_pos=len(NAME),
        confidence=0.9,
        source="spacy",
    )


def _stand_in() -> Any:
    """Detection replaced: the document and the one name in it."""
    return patch.object(
        DocumentProcessor, "detect_entities", return_value=(TEXT, [_entity()])
    )


class _Dialogs:
    """Records ``ConfirmDialog.informational`` calls instead of showing them."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.messages: list[str] = []
        recorder = self

        class _Shown:
            def exec(self) -> int:
                return 0

        def informational(  # type: ignore[no-untyped-def]
            cls, title, message, dismiss_label="", parent=None
        ):
            recorder.messages.append(str(message))
            return _Shown()

        monkeypatch.setattr(ConfirmDialog, "informational", classmethod(informational))


class _Asked:
    """The passphrase window a screen opens: counted, then « Annuler »."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        recorder = self

        def exec_(self: Any) -> int:
            recorder.count += 1
            return 0

        monkeypatch.setattr(pd.PassphraseDialog, "exec", exec_)


# ---------------------------------------------------------------------------
# The passphrase window (T1-T4)
# ---------------------------------------------------------------------------


def _dialog_new_db(qtbot: Any, path: Path) -> pd.PassphraseDialog:
    """The window with « Créer une nouvelle base » and ``path`` chosen."""
    dialog = pd.PassphraseDialog(file_directory=str(path.parent))
    qtbot.addWidget(dialog)
    create_idx = dialog.db_combo.findData(pd._CREATE_ITEM)
    pre(create_idx >= 0, "« Créer une nouvelle base » listed")
    with patch.object(pd.QFileDialog, "getSaveFileName", return_value=(str(path), "")):
        dialog._on_db_combo_changed(create_idx)
    pre(dialog.db_combo.currentData() == str(path), "the new database selected")
    pre(not path.exists(), "the new database does not exist")
    return dialog


@pytest.mark.parametrize("short", [SHORT_8, SHORT_11], ids=["8", "11"])
def test_new_database_short_passphrase_refused(qtbot, tmp_path, short):  # type: ignore[no-untyped-def]
    """T1 (AC1): for a new database, fewer than 12 characters keep
    « Continuer » disabled and show the message; 12 are accepted."""
    dialog = _dialog_new_db(qtbot, tmp_path / "nouvelle.db")
    dialog.passphrase_edit.setText(short)
    assert not dialog.confirm_button.isEnabled()  # expected failure
    label = dialog.passphrase_error_label
    assert label.isVisibleTo(dialog)
    assert label.text() == MSG_12
    dialog.confirm_button.click()
    assert dialog.get_result() is None
    dialog.passphrase_edit.setText("")
    assert not label.isVisibleTo(dialog)
    dialog.passphrase_edit.setText(TWELVE)
    assert dialog.confirm_button.isEnabled()
    assert not label.isVisibleTo(dialog)


def test_new_database_12_characters_accepted(qtbot, tmp_path):  # type: ignore[no-untyped-def]
    """T2 (AC1, control): 12 characters for a new database are accepted."""
    path = tmp_path / "nouvelle.db"
    dialog = _dialog_new_db(qtbot, path)
    dialog.passphrase_edit.setText(TWELVE)
    pre(len(TWELVE) == 12, "a 12-character passphrase")
    assert dialog.confirm_button.isEnabled()
    dialog.confirm_button.click()
    assert dialog.get_result() == (str(path), TWELVE, True)


def test_existing_database_short_passphrase_accepted_by_window(qtbot, tmp_path):  # type: ignore[no-untyped-def]
    """T3 (AC2, control): for an existing database the window accepts any
    passphrase that is not blank, as before."""
    db = tmp_path / pd.DB_FILENAME
    db.touch()
    dialog = pd.PassphraseDialog(file_directory=str(tmp_path))
    qtbot.addWidget(dialog)
    pre(dialog.db_combo.currentData() == str(db), "the existing database selected")
    dialog.passphrase_edit.setText(SHORT_8)
    assert dialog.confirm_button.isEnabled()
    dialog.confirm_button.click()
    assert dialog.get_result() == (str(db), SHORT_8, True)


def test_message_follows_the_selected_database(qtbot, tmp_path):  # type: ignore[no-untyped-def]
    """T4 (AC1): the refusal follows the database chosen."""
    existing = tmp_path / "existante.db"
    existing.touch()
    dialog = _dialog_new_db(qtbot, tmp_path / "nouvelle.db")
    dialog.passphrase_edit.setText(SHORT_8)
    assert not dialog.confirm_button.isEnabled()  # expected failure
    browse_idx = dialog.db_combo.findData(pd._BROWSE_ITEM)
    with patch.object(
        pd.QFileDialog, "getOpenFileName", return_value=(str(existing), "")
    ):
        dialog._on_db_combo_changed(browse_idx)
    assert dialog.db_combo.currentData() == str(existing)
    assert dialog.confirm_button.isEnabled()
    assert not dialog.passphrase_error_label.isVisibleTo(dialog)


# ---------------------------------------------------------------------------
# A single document (T5-T7, T12-T14)
# ---------------------------------------------------------------------------


def _screen(main_window: Any, name: str) -> Any:
    return main_window.stack.widget(main_window._screens[name])


def _open_plain(qtbot: Any, main_window: Any, path: Path, dialogs: _Dialogs) -> Any:
    """A document without names opened from the home screen; waits until a
    message is shown or the processing screen stops."""
    home = _screen(main_window, "home")
    proc = _screen(main_window, "processing")
    before = len(dialogs.messages)
    path.write_text(PLAIN, encoding="utf-8")
    with patch(_MODEL_INSTALLED, return_value=True):
        home._on_file_selected(str(path))
        qtbot.waitUntil(
            lambda: len(dialogs.messages) > before or not proc._is_processing,
            timeout=60000,
        )
    return proc


def _open_named(
    qtbot: Any, main_window: Any, path: Path, dialogs: _Dialogs, wait: bool = True
) -> Any:
    """The document with « Quentrel Zorbalia » opened from the home screen,
    detection replaced; waits until a message is shown or detection ends."""
    home = _screen(main_window, "home")
    proc = _screen(main_window, "processing")
    proc._detection_result = None
    before = len(dialogs.messages)
    path.write_text(TEXT, encoding="utf-8")
    with _stand_in(), patch(_MODEL_INSTALLED, return_value=True):
        home._on_file_selected(str(path))
        if wait:
            qtbot.waitUntil(
                lambda: len(dialogs.messages) > before
                or proc._detection_result is not None,
                timeout=60000,
            )
    return proc


def test_single_document_forgets_refused_passphrase(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
):
    """T5 (AC5): a remembered passphrase that a new database refuses is
    refused once, then forgotten; the next document asks again."""
    dialogs = _Dialogs(monkeypatch)
    asked = _Asked(monkeypatch)
    db = tmp_path / "nouvelle.db"
    main_window.cached_passphrase = (str(db), SHORT_8)  # an earlier session's
    _open_plain(qtbot, main_window, tmp_path / "document1.txt", dialogs)
    pre(dialogs.messages == [MSG_12], f"the first document refused: {dialogs.messages}")
    pre(asked.count == 0, "the window not asked for the first document")
    assert main_window.cached_passphrase is None  # expected failure
    assert not db.exists()
    _open_plain(qtbot, main_window, tmp_path / "document2.txt", dialogs)
    assert asked.count == 1
    assert dialogs.messages == [MSG_12]


def test_other_error_keeps_cache(qtbot, main_window, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    """T6 (AC5, control): any other detection error keeps the remembered
    passphrase."""
    dialogs = _Dialogs(monkeypatch)
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    main_window.cached_passphrase = (str(db), PASSPHRASE)
    with patch.object(
        DocumentProcessor,
        "detect_entities",
        side_effect=FileProcessingError("Zorbalix vrombu"),
    ):
        _open_plain(qtbot, main_window, tmp_path / "document1.txt", dialogs)
    pre(len(dialogs.messages) == 1, f"one message shown: {dialogs.messages}")
    assert main_window.cached_passphrase == (str(db), PASSPHRASE)


def test_worker_flags_refused_passphrase(tmp_path):  # type: ignore[no-untyped-def]
    """T7 (AC3): the worker flags a passphrase refused for a new database."""
    db = tmp_path / "nouvelle.db"
    doc = tmp_path / "document.txt"
    doc.write_text(PLAIN, encoding="utf-8")
    errors: list[str] = []
    worker = DetectionWorker(str(doc), str(db), SHORT_8)
    worker.setAutoDelete(False)
    worker.signals.error.connect(errors.append)
    worker.run()
    pre(errors == [MSG_12], f"the passphrase refused: {errors}")
    assert getattr(worker, "is_passphrase_error", False) is True  # expected failure
    assert not db.exists()


def test_worker_refuses_wrong_passphrase_at_start(tmp_path):  # type: ignore[no-untyped-def]
    """T12 (AC4): a wrong passphrase for an existing database is refused
    before detection, and flagged."""
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    doc = tmp_path / "document.txt"
    doc.write_text(TEXT, encoding="utf-8")
    errors: list[str] = []
    finished: list[object] = []
    worker = DetectionWorker(str(doc), str(db), WRONG)
    worker.setAutoDelete(False)
    worker.signals.error.connect(errors.append)
    worker.signals.finished.connect(finished.append)
    with _stand_in() as detect:
        worker.run()
    assert errors == [MSG_BAD]  # expected failure
    assert finished == []
    assert detect.call_count == 0
    assert getattr(worker, "is_passphrase_error", False) is True


def test_single_document_forgets_wrong_passphrase(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
):
    """T13 (AC4, AC5): a remembered wrong passphrase stops the document at
    the start, is forgotten, and the next document asks again."""
    dialogs = _Dialogs(monkeypatch)
    asked = _Asked(monkeypatch)
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    main_window.cached_passphrase = (str(db), WRONG)
    proc = _open_named(qtbot, main_window, tmp_path / "document1.txt", dialogs)
    pre(asked.count == 0, "the window not asked for the first document")
    assert dialogs.messages == [MSG_BAD]  # expected failure
    assert proc._detection_result is None
    assert main_window.cached_passphrase is None
    assert main_window.current_screen_name() == "home"
    _open_named(qtbot, main_window, tmp_path / "document2.txt", dialogs, wait=False)
    assert asked.count == 1
    assert dialogs.messages == [MSG_BAD]


def test_right_passphrase_existing_database_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
):
    """T14 (AC4, control): the right passphrase for an existing database
    still gives the review its pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    main_window.cached_passphrase = (str(db), PASSPHRASE)
    proc = _open_named(qtbot, main_window, tmp_path / "document1.txt", dialogs)
    assert dialogs.messages == []
    assert proc._detection_result is not None
    assert len(proc._detection_result.pseudonym_previews) == 1
    assert main_window.cached_passphrase == (str(db), PASSPHRASE)


# ---------------------------------------------------------------------------
# A batch (T15-T18)
# ---------------------------------------------------------------------------


def _batch(main_window: Any, tmp_path: Path, db: Path, passphrase: str) -> Any:
    """The batch screen with two files, the output folder set, no review per
    document, and ``(db, passphrase)`` remembered."""
    main_window.cached_passphrase = (str(db), passphrase)
    bs = _screen(main_window, "batch")
    folder = tmp_path / "in"
    folder.mkdir()
    files: list[Path] = []
    for name in ("doc1.txt", "doc2.txt"):
        path = folder / name
        path.write_text(TEXT, encoding="utf-8")
        files.append(path)
    bs._files = files
    bs._output_input.setText(str(tmp_path / "out"))
    bs._validate_checkbox.setChecked(False)
    return bs


class _FakeDetector:
    """The NLP detector of a batch, replaced: it finds the invented name at
    the start of a text and loads no model. Records each text it reads."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        self.texts.append(text)
        return [_entity()] if text.startswith(NAME) else []


def _batch_detection(detector: _FakeDetector | None = None) -> Any:
    """Every detection path of a batch reaches the NLP model through
    ``DocumentProcessor._get_detector``: ``_detect_and_filter_entities``
    (text files without a review, and every file with a review per
    document) and ``detect_entities_tabular`` (.csv and .xlsx without a
    review). Patched here: it hands out ``detector``, or, with None, raises,
    so that a detection the start check should have prevented fails the file
    instead of waiting for a review. The patch is the spy (``call_count``)."""
    if detector is None:
        return patch.object(
            DocumentProcessor,
            "_get_detector",
            side_effect=RuntimeError("detection reached"),
        )
    return patch.object(DocumentProcessor, "_get_detector", return_value=detector)


def _run(qtbot: Any, bs: Any, detector: _FakeDetector) -> Any:
    """One run started with « Démarrer », the cached passphrase used; returns
    the detection spy."""
    with _batch_detection(detector) as spy:
        bs._start_batch()
        qtbot.waitUntil(lambda: bs._worker is None, timeout=60000)
    return spy


@pytest.mark.parametrize("review", [False, True], ids=["no_review", "review"])
@pytest.mark.parametrize("suffix", [".txt", ".csv"], ids=["text", "table"])
def test_batch_worker_refuses_wrong_passphrase_at_start(  # type: ignore[no-untyped-def]
    tmp_path, review, suffix
):
    """T15 (AC4): the batch worker refuses a wrong passphrase before any
    file, and flags it; no detection path is reached, with or without a
    review per document, for a text file or a table."""
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    doc = tmp_path / f"document{suffix}"
    doc.write_text(TEXT, encoding="utf-8")
    errors: list[str] = []
    finished: list[object] = []
    worker = BatchWorker(
        files=[doc],
        output_dir=tmp_path / "out",
        db_path=str(db),
        passphrase=WRONG,
        validate_per_document=review,
    )
    worker.setAutoDelete(False)
    worker.signals.error.connect(errors.append)
    worker.signals.finished.connect(finished.append)
    with _batch_detection() as detect:
        worker.run()
    assert errors == [MSG_BAD]
    assert finished == []
    assert detect.call_count == 0
    assert getattr(worker, "is_passphrase_error", False) is True


def test_batch_forgets_wrong_passphrase(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
):
    """T16 (AC4, AC5): a remembered wrong passphrase stops the batch before
    its first file, is forgotten, and the next run asks again."""
    dialogs = _Dialogs(monkeypatch)
    asked = _Asked(monkeypatch)
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    bs = _batch(main_window, tmp_path, db, WRONG)
    detector = _FakeDetector()
    detect = _run(qtbot, bs, detector)
    pre(asked.count == 0, "the window not asked for the first run")
    assert dialogs.messages == [MSG_BAD]
    assert detect.call_count == 0
    assert detector.texts == []
    assert getattr(bs, "_batch_result", None) is None
    assert main_window.cached_passphrase is None
    assert bs._phases.currentIndex() == 0
    bs._start_batch()
    assert asked.count == 1
    assert dialogs.messages == [MSG_BAD]


def test_batch_right_passphrase_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
):
    """T17 (AC4, control): the right passphrase still processes both files,
    through the detection stand-in (no NLP model)."""
    dialogs = _Dialogs(monkeypatch)
    db = tmp_path / "existante.db"
    init_database(str(db), PASSPHRASE)
    bs = _batch(main_window, tmp_path, db, PASSPHRASE)
    detector = _FakeDetector()
    _run(qtbot, bs, detector)
    pre(
        detector.texts == [TEXT, TEXT],
        f"both files read by the stand-in: {detector.texts}",
    )
    assert dialogs.messages == []
    result = getattr(bs, "_batch_result", None)
    assert result is not None
    assert (result.successful_files, result.failed_files) == (2, 0)
    assert main_window.cached_passphrase == (str(db), PASSPHRASE)


def test_batch_creation_refusal_still_forgotten(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch
):
    """T18 (AC5, control): a passphrase refused when a batch creates the
    database is still forgotten, by today's text match."""
    dialogs = _Dialogs(monkeypatch)
    db = tmp_path / "nouvelle.db"
    bs = _batch(main_window, tmp_path, db, SHORT_8)
    _run(qtbot, bs, _FakeDetector())
    assert len(dialogs.messages) == 1
    assert dialogs.messages[0].startswith(MSG_CREATE)
    assert main_window.cached_passphrase is None
    assert not db.exists()
