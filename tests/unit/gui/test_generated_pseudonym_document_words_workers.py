"""Story 11.6: no desktop path writes a drawn pseudonym that is a word of the
document (T1, desktop cases; AC1).

Written by the BMAD dev agent (Claude). The own-word document of
``test_generated_pseudonym_document_words.py``, with each name's own word
first in its own list (``_forced``), through the real desktop workers and the
real ``DocumentProcessor`` (no mock of the processor); only detection is
replaced. ``FinalizationWorker`` and ``ProcessingWorker`` run in the test's
thread; the desktop batch runs through the real ``BatchScreen`` and
``BatchWorker`` thread (Story 10.16's ``_Batch`` harness), with and without
its review.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gdpr_pseudonymizer.gui.workers.finalization_worker import FinalizationWorker
from gdpr_pseudonymizer.gui.workers.processing_worker import ProcessingWorker
from tests.unit.gui.test_custom_pseudonym_fixes_batch_worker import _Batch
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _new_db,
    _words,
    pre,
)
from tests.unit.test_generated_pseudonym_document_words import (
    OWN_DOC,
    OWN_FRONT,
    OWN_NAMES,
    OWN_WORDS,
    _forced,
)
from tests.unit.test_parallel_saved_pseudonym import (
    _detection,
    _found,
    _settings,  # noqa: F401 (autouse: no settings file read or written)
)

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708): PySide6 warns, and pytest.ini turns warnings into
# errors, so exactly those two warnings are filtered, as in Story 10.16's
# test_custom_pseudonym_fixes_batch_worker.py. A warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)


def _run_worker(worker: Any) -> str | None:
    """Run a desktop worker in this thread; the text it wrote, or None."""
    finished: list[Any] = []
    errors: list[str] = []
    worker.signals.finished.connect(finished.append)
    worker.signals.error.connect(errors.append)
    worker.run()
    if worker.output_path:
        Path(worker.output_path).unlink(missing_ok=True)
    if len(finished) != 1 or errors:
        return None
    return str(finished[0].pseudonymized_content)


def _desktop_written(
    qtbot: Any, main_window: Any, tmp_path: Path, case: str
) -> str | None:
    """The own-word document written through the desktop path ``case``,
    forced; the written text, or None when the path failed."""
    entities = _found(OWN_DOC, OWN_NAMES)
    if case in ("finalization_worker", "processing_worker"):
        db = _new_db(tmp_path)
        source = tmp_path / "own.txt"
        source.write_text(OWN_DOC, encoding="utf-8")
        with _forced(OWN_FRONT) as offers:
            if case == "finalization_worker":
                written = _run_worker(
                    FinalizationWorker(
                        entities, OWN_DOC, db, PASSPHRASE, "neutral", str(source)
                    )
                )
            else:
                with _detection(OWN_NAMES):
                    written = _run_worker(ProcessingWorker(str(source), db, PASSPHRASE))
        pre(offers.n > 0, "the forced words offered")
        return written
    batch = _Batch(qtbot, main_window, tmp_path, [(OWN_DOC, entities)])
    review = case == "batch_with_review"
    batch.bs._validate_checkbox.setChecked(review)
    if not review:
        # process_document also passes the type filter (None here)
        detect = batch._detect
        batch._detect = lambda text, *args, **kwargs: detect(text)  # type: ignore[method-assign]

    def body(record: dict[str, Any]) -> None:
        if review:
            batch.wait_doc(0)
            batch.accept_pending_and_validate()

    with _forced(OWN_FRONT) as offers:
        batch.run(body)
    pre(offers.n > 0, "the forced words offered")
    output = batch.out / "doc0_pseudonymized.txt"
    return output.read_text(encoding="utf-8") if output.exists() else None


@pytest.mark.parametrize(
    "case",
    [
        "finalization_worker",
        "processing_worker",
        "batch_with_review",
        "batch_without_review",
    ],
)
def test_desktop_own_word_never_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, case
) -> None:
    """T1, desktop (AC1): with each name's own word first in its own list, no
    desktop path writes « Zorbal », « Quentrix », « Zorbtech » or
    « Zorbaville »."""
    written = _desktop_written(qtbot, main_window, tmp_path, case)
    if written is None:
        pytest.fail(f"PRE: {case} wrote the document")
    assert not OWN_WORDS & set(_words(written)), written  # expected failure
