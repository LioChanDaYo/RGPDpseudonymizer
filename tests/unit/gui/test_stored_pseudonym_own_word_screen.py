"""Story 11.7: the database screen finds and replaces saved pseudonyms that
hold a word of their own name, and the desktop app gives one notice per
session when a document is written (G1-G6).

Written by the BMAD dev agent (Claude). The rows are saved directly in a
real encrypted database, as 2.3.0 could have saved them (the core file's
T4 and T5 rows). The screen's workers run synchronously
(``QThreadPool.start`` replaced, as ``test_database_screen.py`` does); the
screen is pointed at the database without its passphrase window, so the
desktop settings file is never written. Confirmation windows are replaced
by a recorder; toasts are recorded, never shown.

Every marked case reaches the new code through attributes read with
``getattr(..., None)`` (``own_words_label``, ``own_words_only``,
``replace_button``) or the worker's ``"replace"`` operation, which the base
answers as an unknown operation. Preconditions fail with
``pytest.fail("PRE: ...")``; the first ``assert`` after them is the
expected failure on the unfixed code (``# expected failure``). The tests
assert a few fixed words of each approved text, never whole sentences.
Invented names and main-corpus words only. No spaCy model.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from gdpr_pseudonymizer.core.custom_pseudonym import fold
from gdpr_pseudonymizer.gui.screens.database import DatabaseScreen
from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen
from gdpr_pseudonymizer.gui.widgets.toast import Toast
from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker
from gdpr_pseudonymizer.gui.workers.finalization_worker import FinalizationWorker
from tests.unit.test_custom_pseudonym_fixes_cli import PASSPHRASE, pre
from tests.unit.test_parallel_saved_pseudonym import _found
from tests.unit.test_stored_pseudonym_own_word import (
    DOC_QD,
    PERSON,
    QD,
    T4_ROWS,
    XB,
    XB_ROW,
    ZB_ROW,
    ZM,
    ZQ,
    _by_name,
    _db,
)

_FIRST = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 11.7 tests first: saved pseudonyms that hold a word of their own name",
)

WRONG = "zorbalia_pass_B_456!"
NAME_COLUMN = 2
PSEUDONYM_COLUMN = 3


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No user settings file is read or written."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(
        "gdpr_pseudonymizer.gui.config._config_path",
        lambda: tmp_path / ".gdpr-pseudo.yaml",
    )


@pytest.fixture()
def screen(main_window: Any) -> DatabaseScreen:
    widget = main_window.stack.widget(main_window._screens["database"])
    assert isinstance(widget, DatabaseScreen)
    return widget


@pytest.fixture()
def toasts() -> Iterator[list[str]]:
    """Every toast message shown, in order."""
    shown: list[str] = []

    def record(message: str, parent: Any, duration_ms: int = 3000) -> MagicMock:
        shown.append(str(message))
        return MagicMock()

    with patch.object(Toast, "show_message", side_effect=record):
        yield shown


def _sync(worker: Any, *args: Any) -> None:
    worker.run()


def _open(screen: DatabaseScreen, db: str) -> None:
    """The screen loads the database (the "list" worker, synchronously)."""
    screen._db_path = db
    screen._passphrase = PASSPHRASE
    screen._main_window.cached_passphrase = (db, PASSPHRASE)
    with patch("PySide6.QtCore.QThreadPool.start", side_effect=_sync):
        screen._load_entities()
    pre(screen.entity_table.rowCount() > 0, "the rows are shown")


def _shown_names(screen: DatabaseScreen) -> list[str]:
    table = screen.entity_table
    return [
        table.item(row, NAME_COLUMN).text()
        for row in range(table.rowCount())
        if not table.isRowHidden(row)
    ]


def _row_of(screen: DatabaseScreen, name: str) -> int:
    table = screen.entity_table
    rows = [
        row
        for row in range(table.rowCount())
        if table.item(row, NAME_COLUMN).text() == name
    ]
    pre(len(rows) == 1, f"one table row for « {name} »")
    return rows[0]


def _tick(screen: DatabaseScreen, name: str) -> None:
    item = screen.entity_table.item(_row_of(screen, name), 0)
    item.setCheckState(Qt.CheckState.Checked)


class _Confirm:
    """``ConfirmDialog.destructive``: records (title, message, button) and
    answers with ``accept``."""

    def __init__(self, accept: bool) -> None:
        self.accept = accept
        self.calls: list[tuple[str, str, str]] = []

    def __call__(
        self, title: str, message: str, confirm_label: str, parent: Any = None
    ) -> MagicMock:
        self.calls.append((str(title), str(message), str(confirm_label)))
        return MagicMock(exec=MagicMock(return_value=self.accept))


def _confirming(dialog: _Confirm) -> Any:
    return patch(
        "gdpr_pseudonymizer.gui.widgets.confirm_dialog.ConfirmDialog.destructive",
        dialog,
    )


@_FIRST
def test_screen_counts_and_filters_rows_found(
    screen: DatabaseScreen, tmp_path: Path, toasts: list[str]
) -> None:
    """G1 (AC3): T4's database: the count line shows 3, the tick box shows
    only those three rows, and their pseudonym cells name the word."""
    db, _ = _db(tmp_path, T4_ROWS)
    _open(screen, db)
    label = getattr(screen, "own_words_label", None)
    only = getattr(screen, "own_words_only", None)
    assert label is not None and only is not None  # expected failure
    assert not label.isHidden() and not only.isHidden()
    assert label.text().rstrip().endswith(": 3"), label.text()
    only.setChecked(True)
    assert sorted(_shown_names(screen)) == sorted([ZQ, ZM, "Zorbal"])
    cell = screen.entity_table.item(_row_of(screen, ZQ), PSEUDONYM_COLUMN)
    assert "Zorbal" in cell.toolTip(), cell.toolTip()


@_FIRST
def test_replace_selection(
    screen: DatabaseScreen, tmp_path: Path, toasts: list[str]
) -> None:
    """G2 (AC5): ticking « Zorbal Quentrix » counts 1 on the button; once
    confirmed, the worker replaces the whole group and the table shows the
    new part on the three rows."""
    db, _ = _db(tmp_path, T4_ROWS)
    _open(screen, db)
    _tick(screen, ZQ)
    button = getattr(screen, "replace_button", None)
    assert button is not None  # expected failure
    assert button.isEnabled() and "1" in button.text(), button.text()
    dialog = _Confirm(accept=True)
    with (
        _confirming(dialog),
        patch("PySide6.QtCore.QThreadPool.start", side_effect=_sync),
    ):
        button.click()
    assert len(dialog.calls) == 1
    after = _by_name(db)
    new = after[ZQ].pseudonym_first
    assert new and fold(new) != "zorbal", new
    assert after[ZM].pseudonym_first == new and after["Zorbal"].pseudonym_full == new
    table = screen.entity_table
    shown = {
        table.item(row, 2).text(): table.item(row, PSEUDONYM_COLUMN).text()
        for row in range(table.rowCount())
    }
    assert shown[ZQ] == f"{new} Brontel" and shown["Zorbal"] == new, shown


@_FIRST
def test_replace_ignores_clean_rows(
    screen: DatabaseScreen, tmp_path: Path, toasts: list[str]
) -> None:
    """G3 (AC5): a ticked row the check does not find is not counted: the
    button counts 0 and is disabled."""
    db, _ = _db(tmp_path, T4_ROWS)
    _open(screen, db)
    _tick(screen, QD)
    pre(len(screen._selected_ids) == 1, "one row ticked")
    button = getattr(screen, "replace_button", None)
    assert button is not None  # expected failure
    assert not button.isEnabled()
    assert "0" in button.text(), button.text()


@_FIRST
def test_confirmation_lists_moved_rows_and_warning(
    screen: DatabaseScreen, tmp_path: Path, toasts: list[str]
) -> None:
    """G4 (AC5): T5's database: the confirmation lists the leaking row,
    then the row that moves with it under the second list (D9, « aussi »),
    and the warning (D10, « déjà »). Cancelled: nothing changes."""
    db, _ = _db(tmp_path, [XB_ROW, ZB_ROW])
    _open(screen, db)
    _tick(screen, XB)
    button = getattr(screen, "replace_button", None)
    assert button is not None  # expected failure
    before = {name: row.pseudonym_full for name, row in _by_name(db).items()}
    dialog = _Confirm(accept=False)
    with (
        _confirming(dialog),
        patch("PySide6.QtCore.QThreadPool.start", side_effect=_sync),
    ):
        button.click()
    assert len(dialog.calls) == 1
    message = dialog.calls[0][1]
    assert XB in message and "Zorbal Brontel" in message, message
    assert message.index(XB) < message.index("aussi") < message.index("Zorbal Brontel")
    assert "déjà" in message
    assert {name: row.pseudonym_full for name, row in _by_name(db).items()} == before


@_FIRST
def test_wrong_passphrase_is_forgotten(
    screen: DatabaseScreen, tmp_path: Path, toasts: list[str]
) -> None:
    """G5 (AC5): the "replace" operation with a wrong passphrase sets
    ``is_passphrase_error``, so the screen forgets the remembered
    passphrase, as for "delete"."""
    db, ids = _db(tmp_path, T4_ROWS)
    screen._db_path = db
    screen._passphrase = WRONG
    screen._main_window.cached_passphrase = (db, WRONG)
    worker = DatabaseWorker(
        "replace",
        db,
        WRONG,
        entity_ids=[ids[ZQ]],
        confirmed=frozenset((ids[ZQ], ids[ZM], ids["Zorbal"])),
    )
    errors: list[str] = []
    worker.signals.error.connect(errors.append)
    worker.signals.error.connect(screen._on_db_error)
    screen._current_worker = worker
    worker.run()
    pre(len(errors) == 1, f"one error: {errors}")
    assert worker.is_passphrase_error  # expected failure
    assert screen._main_window.cached_passphrase is None


@_FIRST
def test_notice_once_per_session(
    main_window: Any, tmp_path: Path, toasts: list[str]
) -> None:
    """G6 (AC10): two documents written on T4's database, each through the
    desktop finalization: one notice toast (D18, the count 3)."""
    db, _ = _db(tmp_path, T4_ROWS)
    review = main_window.stack.widget(main_window._screens["validation"])
    pre(isinstance(review, ValidationScreen), "the review screen")
    names = [(QD, PERSON)]
    for tag in ("first", "second"):
        worker = FinalizationWorker(
            validated_entities=_found(DOC_QD, names),
            document_text=DOC_QD,
            db_path=db,
            passphrase=PASSPHRASE,
            theme="neutral",
            input_path=str(tmp_path / f"{tag}.txt"),
        )
        results: list[Any] = []
        errors: list[str] = []
        worker.signals.finished.connect(results.append)
        worker.signals.error.connect(errors.append)
        worker.run()
        if worker.output_path:
            Path(worker.output_path).unlink(missing_ok=True)
        pre(len(results) == 1 and not errors, f"{tag} document written: {errors}")
        review._on_finalize_finished(results[0])
    notices = [
        message
        for message in toasts
        if "Voir" in message and "Base" in message and "3" in message
    ]
    assert len(notices) == 1, toasts  # expected failure
