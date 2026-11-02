"""Story 10.21: one forms rule for names of two words or more (Lionel,
2026-11-01), in the desktop app's single-document review (Ex1 desktop).

Written by the BMAD dev agent (Claude), before the fix. The test drives the
real single-document path, as Story 10.19's desktop tests
(``test_capitals_correction_desktop.py``): the real ``DetectionWorker`` run
synchronously with detection replaced, the real ``ValidationScreen`` and the
real finalization; the written text is read from the results screen. The
correction goes through the screen's own ``_show_modify_text_dialog``, with
``QInputDialog.getText`` answered; every confirmation window answers yes.

Preconditions are ``pytest.fail("PRE: ...")`` calls, never ``assert``, so a
broken precondition is a red failure even under
``xfail(strict=True, raises=AssertionError)``; the first ``assert`` is the
expected failure on the unfixed code (``# expected failure``). Invented names
and main-corpus words only.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
PERSON = "PERSON"

EX1_TEXT = "Élorine du Prélis a signé le bail. ÉLORINE DU PRÉLIS valide."


def pre(condition: bool, message: str) -> None:
    """A precondition: ``pytest.fail``, never an ``AssertionError``."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def found_at(text: str, name: str) -> DetectedEntity:
    """The detector's PERSON entity at the first occurrence of ``name``."""
    start = text.find(name)
    pre(start >= 0, f"{name!r} in the text")
    return DetectedEntity(
        text=name,
        entity_type=PERSON,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


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
def dialogs(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every confirmation window continues (answers yes)."""
    monkeypatch.setattr(ConfirmDialog, "exec", lambda self: 1)
    yield


def _single(
    qtbot: Any,
    main_window: Any,
    tmp_path: Path,
    text: str,
    entities: list[DetectedEntity],
) -> Any:
    """``text`` detected with ``entities`` and shown in the single-document
    review: the validation screen."""
    from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen
    from gdpr_pseudonymizer.gui.workers.detection_worker import (
        DetectionResult,
        DetectionWorker,
    )

    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    vs = main_window.stack.widget(main_window._screens["validation"])
    pre(isinstance(vs, ValidationScreen), "validation screen")
    main_window.show()
    file_path = tmp_path / "doc0.txt"
    file_path.write_text(text, encoding="utf-8")
    worker = DetectionWorker(str(file_path), db, PASSPHRASE)
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
    pre(not errors, "no detection error")
    pre(len(results) == 1, "one detection result")
    pre(isinstance(results[0], DetectionResult), "detection result")
    vs.start_validation(results[0])
    main_window.navigate_to("validation")
    pre(not vs.batch_mode, "single-document mode")
    return vs


def _written(qtbot: Any, main_window: Any, vs: Any) -> str:
    """Every pending row accepted, the document validated: the written text."""
    state = vs.validation_state
    for review in state.get_all_entities():
        if review.state == EntityReviewState.PENDING:
            state.accept_entity(review.entity_id)
    vs._on_finalize()
    qtbot.waitUntil(
        lambda: main_window.current_screen_name() == "results", timeout=WAIT_MS
    )
    results = main_window.stack.currentWidget()
    return Path(results._temp_path).read_text(encoding="utf-8")


@pytest.mark.xfail(strict=True, raises=AssertionError)
def test_Ex1_desktop_correction_in_capitals_reaches_the_name_written_in_title_case(  # type: ignore[no-untyped-def]  # noqa: N802
    qtbot, main_window, tmp_path, monkeypatch, dialogs
) -> None:
    """Ex1 (AC1, AC2; Lionel: "yes"), the desktop's single-document review:
    « Élorine » and « ÉLORINE » found, one row; corrected « ELORINE DU
    PRELIS » through the edit dialog, it covers both places, nothing in
    clear."""
    from gdpr_pseudonymizer.gui.screens import validation as screen

    vs = _single(
        qtbot,
        main_window,
        tmp_path,
        EX1_TEXT,
        [found_at(EX1_TEXT, "Élorine"), found_at(EX1_TEXT, "ÉLORINE")],
    )
    rows = vs.validation_state.get_all_entities()
    pre(len(rows) == 1, f"one row in the review ({len(rows)})")
    monkeypatch.setattr(
        screen.QInputDialog,
        "getText",
        staticmethod(lambda *a, **k: ("ELORINE DU PRELIS", True)),
    )
    vs._show_modify_text_dialog(rows[0].entity_id)
    pre(
        rows[0].user_modification == "ELORINE DU PRELIS",
        "the row corrected through the dialog",
    )
    written = _written(qtbot, main_window, vs)
    assert (
        "Prélis" not in written and "PRÉLIS" not in written
    ), written  # expected failure
