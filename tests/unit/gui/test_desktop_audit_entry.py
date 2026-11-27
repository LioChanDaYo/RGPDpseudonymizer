"""Story 17.1: the desktop app writes a processing entry in the audit log
(A1 to A3, T1, T2, B1 to B7, N1, X1, R1; controls K3 to K5).

Written by the BMAD dev agent (Claude), tests first. Desktop single = the
real ``DetectionWorker`` run synchronously, the real ``ValidationScreen``
(``start_validation``, every pending row accepted, ``_start_finalization``)
and the ``FinalizationWorker`` the screen builds. Desktop batch = the real
batch screen, the real ``BatchWorker`` thread and the review screen (Story
11.5's harnesses), with nothing replaced but the detector.

Detection is the control file's ``_StandIn`` (``HybridDetector`` replaced,
the real ``_get_detector`` kept): a processor that never detected reads
``fr_not_loaded-unknown``, one that did reads ``fr_core_news_zz-9.9.9``, so
the version a row carries tells which processor wrote it. R1 runs the real
``fr_core_news_lg``.

Each desktop row is compared with the row the CLI's ``process`` writes for
the same file on a fresh database, every group confirmed (``cli_rows``).
Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with
an ``assert``; the first ``assert`` after them is the expected failure on
the unfixed code (``# expected failure``). No marked case passes a new
parameter itself: every value reaches the code through the real screens and
workers. Invented names and main-corpus words only.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.validation.models import EntityReviewState
from tests.unit.gui.test_review_list_written_pseudonym_review import _Dialogs
from tests.unit.test_audit_entry_controls import (
    FORMAT_IDS,
    FORMATS,
    INVENTED,
    KEYS,
    PASSPHRASE,
    STAND_IN_VERSION,
    _StandIn,
    cli_rows,
    compared,
    failing_write,
    fresh_db,
    install_stand_in,
    pre,
    pre_package,
    rows_of,
    write_doc,
)
from tests.unit.test_erasure_log_no_name import (
    FIXTURE_MAIN_1F35DAE,
    FIXTURE_PASSPHRASE,
    FIXTURE_V2_2_0,
    _copy_fixture,
    _invoke,
)
from tests.unit.test_parallel_saved_pseudonym import (
    _settings,  # noqa: F401 - autouse fixture: no settings file read or written
)

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:805-811). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 10.10's test_batch_review_real_worker.py). This is a
# warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

TESTS_FIRST = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 17.1 tests first: the desktop app writes no processing entry",
)

ROOT = Path(__file__).resolve().parents[3]
WAIT_MS = 60000
PENDING = EntityReviewState.PENDING
OTHER_PASSPHRASE = "zorbalia_pass_B_123!"


@pytest.fixture(autouse=True)
def _package() -> None:
    pre_package(
        ROOT,
        [
            "tests.unit.test_audit_entry_controls",
            "tests.unit.test_review_rows_written",
            "tests.unit.gui.test_review_list_written_pseudonym_review",
            "tests.unit.test_erasure_log_no_name",
        ],
    )


@pytest.fixture
def stand_in(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_StandIn]]:
    yield from install_stand_in(monkeypatch)


@pytest.fixture
def dialogs(monkeypatch: pytest.MonkeyPatch) -> _Dialogs:
    return _Dialogs(monkeypatch)


# ---------------------------------------------------------------------------
# Harness (preconditions with pre)
# ---------------------------------------------------------------------------


def _detect(
    db: str, path: Path, passphrase: str = PASSPHRASE
) -> tuple[DetectionWorker, DetectionResult | None, list[str]]:
    """The real DetectionWorker run synchronously on ``path``."""
    finished: list[object] = []
    errors: list[str] = []
    worker = DetectionWorker(file_path=str(path), db_path=db, passphrase=passphrase)
    worker.setAutoDelete(False)
    worker.signals.finished.connect(finished.append)
    worker.signals.error.connect(errors.append)
    worker.run()
    result = finished[0] if finished else None
    if result is not None and not isinstance(result, DetectionResult):
        pytest.fail(f"PRE: a detection result: {result!r}")
    return worker, result, errors


def _detection_fails(db: str, path: Path) -> None:
    """PRE: the real DetectionWorker reports an error and no result."""
    _, result, errors = _detect(db, path)
    pre(result is None and len(errors) == 1, f"detection error: {errors}")


class _Single171:
    """One document in the desktop app, single-document mode."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        dialogs: _Dialogs,
        db: str,
        path: Path,
        passphrase: str = PASSPHRASE,
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        self.dialogs = dialogs
        _, result, errors = _detect(db, path, passphrase)
        if result is None:
            pytest.fail(f"PRE: detection finished: {errors}")
        self.result: DetectionResult = result
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        main_window.show()
        self.vs.start_validation(result)
        main_window.navigate_to("validation")
        pre(self.vs.validation_state is not None, "review shown")

    def finalize(self) -> float:
        """Every pending row accepted, then the screen's finalize; returns the
        wall time until the results screen or an error dialog."""
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        before = len(self.dialogs.calls)
        start = time.time()
        self.vs._start_finalization()
        self.qtbot.waitUntil(
            lambda: self.mw.current_screen_name() == "results"
            or len(self.dialogs.calls) > before,
            timeout=WAIT_MS,
        )
        return time.time() - start

    def written(self) -> float:
        """PRE: the document is written (the results screen is reached)."""
        took = self.finalize()
        pre(
            self.mw.current_screen_name() == "results",
            f"written: {self.dialogs.calls}",
        )
        return took

    def refused(self) -> None:
        """PRE: the write fails (the error dialog, still on the review)."""
        before = len(self.dialogs.calls)
        self.finalize()
        pre(
            self.mw.current_screen_name() == "validation"
            and len(self.dialogs.calls) == before + 1,
            f"finalize error shown: {self.dialogs.calls}",
        )


class _Batch171:
    """A real batch run (Story 11.5's ``_Batch``) on ``files``, on ``db``."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        db: str,
        files: list[Path],
        out: Path,
        review: bool = True,
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        self.db = db
        main_window.show()
        main_window.navigate_to("batch")
        self.bs = main_window.stack.currentWidget()
        pre(isinstance(self.bs, BatchScreen), "batch screen")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        self.bs._files = list(files)
        self.bs._output_input.setText(str(out))
        self.bs._validate_checkbox.setChecked(review)

    def run(self, body: Callable[[], None] = lambda: None) -> None:
        """Run the batch; ``body`` drives the reviews; wait for its end."""
        self.bs._launch_worker(self.db, PASSPHRASE)
        try:
            body()
            self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)
        finally:
            if self.bs._worker is not None:
                self.bs._worker.cancel()
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)

    def wait_doc(self, index: int) -> None:
        """Wait until document ``index`` is waiting for its review."""
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == index
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=WAIT_MS,
        )

    def accept_pending_and_validate(self) -> None:
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        self.vs.finalize_button.click()

    def validate_each(
        self, count: int, open_seconds: float = 0.0
    ) -> Callable[[], None]:
        """A body: each of ``count`` documents reviewed in turn, every row
        accepted, after the review stayed open ``open_seconds``."""

        def body() -> None:
            for index in range(count):
                self.wait_doc(index)
                if open_seconds:
                    self.qtbot.wait(int(open_seconds * 1000))
                self.accept_pending_and_validate()

        return body


def _cli_row(tmp_path: Path, path: Path, n: int = 0) -> dict[str, Any]:
    """PRE: the CLI writes exactly one row for ``path`` on a fresh database."""
    rows = cli_rows(fresh_db(tmp_path / str(n) / "mappings.db"), path)
    pre(len(rows) == 1, f"one CLI row: {rows}")
    return rows[0]


def _seen(row: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    """A row's compared fields and its files."""
    return compared(row), row["files_processed"]


# ---------------------------------------------------------------------------
# A1 to A3: one row per document written, equal to the CLI's
# ---------------------------------------------------------------------------


@TESTS_FIRST
@pytest.mark.parametrize("suffix", FORMATS, ids=FORMAT_IDS)
def test_a1_desktop_single_writes_the_cli_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs, suffix: str
) -> None:
    path = write_doc(tmp_path / f"doc{suffix}")
    cli = _cli_row(tmp_path, path)
    pre(cli["success"], f"CLI row: {cli}")
    db = fresh_db(tmp_path / "mappings.db")
    _Single171(qtbot, main_window, dialogs, db, path).written()
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert compared(rows[0]) == compared(cli)
    assert rows[0]["files_processed"] == [str(path)]
    assert rows[0]["model_version"] == STAND_IN_VERSION
    assert rows[0]["entity_count"] == 4


@TESTS_FIRST
@pytest.mark.parametrize("suffix", FORMATS, ids=FORMAT_IDS)
def test_a2_desktop_batch_review_writes_the_cli_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs, suffix: str
) -> None:
    path = write_doc(tmp_path / "in" / f"doc{suffix}")
    cli = _cli_row(tmp_path, path)
    pre(cli["success"], f"CLI row: {cli}")
    db = fresh_db(tmp_path / "mappings.db")
    batch = _Batch171(qtbot, main_window, db, [path], tmp_path / "out")
    batch.run(batch.validate_each(1))
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert compared(rows[0]) == compared(cli)
    assert rows[0]["files_processed"] == [str(path)]
    assert rows[0]["model_version"] == STAND_IN_VERSION
    assert rows[0]["entity_count"] == 4


@TESTS_FIRST
def test_a3_desktop_batch_review_two_documents_two_rows(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    paths = [write_doc(tmp_path / "in" / f"doc{index}.txt") for index in range(2)]
    clis = [_cli_row(tmp_path, path, i) for i, path in enumerate(paths)]
    db = fresh_db(tmp_path / "mappings.db")
    batch = _Batch171(qtbot, main_window, db, paths, tmp_path / "out")
    batch.run(batch.validate_each(2))
    rows = rows_of(db)
    assert len(rows) == 2  # expected failure
    assert [row["files_processed"] for row in rows] == [[str(p)] for p in paths]
    assert [compared(row) for row in rows] == [compared(cli) for cli in clis]


# ---------------------------------------------------------------------------
# T1, T2: the row's time is the app's work, without the review
# ---------------------------------------------------------------------------


@TESTS_FIRST
def test_t1_desktop_single_time_is_analysis_plus_finalize(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "doc.txt")
    db = fresh_db(tmp_path / "mappings.db")
    stand_in.delay = 1.0
    single = _Single171(qtbot, main_window, dialogs, db, path)
    stand_in.delay = 0.0
    analysis = single.result.detection_time_seconds
    pre(analysis >= 1.0, f"analysis took the delay: {analysis}")
    qtbot.wait(1500)
    took = single.written()
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert analysis <= rows[0]["processing_time_seconds"] <= analysis + took


@TESTS_FIRST
def test_t2_desktop_batch_time_is_without_the_review(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "in" / "doc0.txt")
    db = fresh_db(tmp_path / "mappings.db")
    stand_in.delay = 1.0
    batch = _Batch171(qtbot, main_window, db, [path], tmp_path / "out")
    batch.run(batch.validate_each(1, open_seconds=3.0))
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert 1.0 <= rows[0]["processing_time_seconds"] < 4.0


# ---------------------------------------------------------------------------
# B1 to B7: failure rows equal to the CLI's, with the input file
# ---------------------------------------------------------------------------


@TESTS_FIRST
def test_b1_desktop_single_write_fails(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "doc.txt")
    with failing_write():
        cli = _cli_row(tmp_path, path)
        db = fresh_db(tmp_path / "mappings.db")
        _Single171(qtbot, main_window, dialogs, db, path).refused()
    pre(not cli["success"], f"CLI failure row: {cli}")
    assert [_seen(row) for row in rows_of(db)] == [
        (compared(cli), [str(path)])
    ]  # expected failure


@TESTS_FIRST
def test_b2_desktop_batch_write_fails(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "in" / "doc0.txt")
    with failing_write():
        cli = _cli_row(tmp_path, path)
        db = fresh_db(tmp_path / "mappings.db")
        batch = _Batch171(qtbot, main_window, db, [path], tmp_path / "out")
        batch.run(batch.validate_each(1))
    pre(not cli["success"], f"CLI failure row: {cli}")
    assert [_seen(row) for row in rows_of(db)] == [
        (compared(cli), [str(path)])
    ]  # expected failure


@TESTS_FIRST
def test_b3_desktop_single_read_fails(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = tmp_path / "doc9.txt"
    pre(not path.exists(), "doc9.txt missing")
    cli = _cli_row(tmp_path, path)
    db = fresh_db(tmp_path / "mappings.db")
    _detection_fails(db, path)
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert _seen(rows[0]) == (compared(cli), [str(path)])


@TESTS_FIRST
def test_b4_desktop_single_detection_fails(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "doc.txt")
    stand_in.fail = True
    cli = _cli_row(tmp_path, path)
    db = fresh_db(tmp_path / "mappings.db")
    _detection_fails(db, path)
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert _seen(rows[0]) == (compared(cli), [str(path)])


@TESTS_FIRST
def test_b5_desktop_batch_read_fails(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = tmp_path / "in" / "doc9.txt"
    pre(not path.exists(), "doc9.txt missing")
    cli = _cli_row(tmp_path, path)
    db = fresh_db(tmp_path / "mappings.db")
    _Batch171(qtbot, main_window, db, [path], tmp_path / "out").run()
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert _seen(rows[0]) == (compared(cli), [str(path)])


@TESTS_FIRST
def test_b6_desktop_batch_detection_fails(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "in" / "doc0.txt")
    stand_in.fail = True
    cli = _cli_row(tmp_path, path)
    db = fresh_db(tmp_path / "mappings.db")
    _Batch171(qtbot, main_window, db, [path], tmp_path / "out").run()
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert _seen(rows[0]) == (compared(cli), [str(path)])


@TESTS_FIRST
def test_b7_desktop_single_retry_after_failed_write(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "doc.txt")
    with failing_write():
        cli_failure = _cli_row(tmp_path, path, 1)
    cli_success = _cli_row(tmp_path, path, 2)
    db = fresh_db(tmp_path / "mappings.db")
    single = _Single171(qtbot, main_window, dialogs, db, path)
    with failing_write():
        single.refused()
    pre(single.vs.finalize_button.isEnabled(), "finalize enabled again")
    single.written()
    rows = rows_of(db)
    assert len(rows) == 2  # expected failure
    assert [_seen(row) for row in rows] == [
        (compared(cli_failure), [str(path)]),
        (compared(cli_success), [str(path)]),
    ]


# ---------------------------------------------------------------------------
# N1: no detected name and no pseudonym in any field of the new rows
# ---------------------------------------------------------------------------


def _pseudonyms(db: str) -> list[str]:
    with open_database(db, PASSPHRASE) as session:
        entities = SQLiteMappingRepository(session).find_all()
        return [
            value
            for entity in entities
            for value in (
                entity.pseudonym_full,
                entity.pseudonym_first,
                entity.pseudonym_last,
            )
            if value
        ]


@TESTS_FIRST
def test_n1_no_name_in_the_new_rows(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    db = fresh_db(tmp_path / "mappings.db")
    # a desktop single success
    _Single171(
        qtbot, main_window, dialogs, db, write_doc(tmp_path / "doc.txt")
    ).written()
    # a desktop single detection failure, the invented names in its error
    stand_in.fail = True
    _detection_fails(db, write_doc(tmp_path / "doc1.txt"))
    stand_in.fail = False
    # a desktop batch with review, then a desktop batch read failure
    batch = _Batch171(
        qtbot,
        main_window,
        db,
        [write_doc(tmp_path / "in" / "doc0.txt")],
        tmp_path / "out",
    )
    batch.run(batch.validate_each(1))
    missing = tmp_path / "in" / "doc9.txt"
    pre(not missing.exists(), "doc9.txt missing")
    _Batch171(qtbot, main_window, db, [missing], tmp_path / "out").run()
    rows = rows_of(db)
    assert len(rows) == 4  # expected failure
    words = INVENTED + sorted(set(_pseudonyms(db)))
    pre(len(words) > len(INVENTED), "pseudonyms saved")
    hits = [
        (key, word)
        for row in rows
        for key, value in row.items()
        for word in words
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", str(value), re.IGNORECASE)
    ]
    assert hits == []


# ---------------------------------------------------------------------------
# X1: a database made before the fix takes the new row; old rows unchanged
# ---------------------------------------------------------------------------


def _export(tmp_path: Path, db: Path, n: int) -> list[dict[str, Any]]:
    output = tmp_path / str(n) / "audit.json"
    output.parent.mkdir()
    code, shown = _invoke(
        "export", str(output), "--db", str(db), passphrase=FIXTURE_PASSPHRASE
    )
    pre(code == 0 and output.is_file(), f"export {n}: {code} {shown}")
    operations: list[dict[str, Any]] = json.loads(output.read_text(encoding="utf-8"))[
        "operations"
    ]
    return operations


@TESTS_FIRST
@pytest.mark.parametrize(
    "fixture_path",
    [FIXTURE_V2_2_0, FIXTURE_MAIN_1F35DAE],
    ids=["v2_2_0", "main_1f35dae"],
)
def test_x1_old_database_takes_one_new_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs, fixture_path: Path
) -> None:
    db = _copy_fixture(fixture_path, tmp_path)
    before = _export(tmp_path, db, 0)
    path = write_doc(tmp_path / "doc.txt")
    _Single171(
        qtbot, main_window, dialogs, str(db), path, passphrase=FIXTURE_PASSPHRASE
    ).written()
    after = _export(tmp_path, db, 1)
    assert len(after) == len(before) + 1  # expected failure
    old_ids = {op["id"] for op in before}
    new = [op for op in after if op["id"] not in old_ids]
    assert len(new) == 1
    assert new[0]["operation_type"] == "PROCESS"
    assert new[0]["files_processed"] == [str(path)]
    after_by_id = {op["id"]: op for op in after}
    assert all(after_by_id.get(op["id"]) == op for op in before)
    assert all(list(op) == KEYS for op in before + after)


# ---------------------------------------------------------------------------
# R1: the real model's version, equal to the CLI's
# ---------------------------------------------------------------------------


@TESTS_FIRST
@pytest.mark.spacy
def test_r1_desktop_single_real_model_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    path = write_doc(tmp_path / "doc.txt")
    cli = _cli_row(tmp_path, path)
    pre(cli["success"], f"CLI row: {cli}")
    db = fresh_db(tmp_path / "mappings.db")
    _Single171(qtbot, main_window, dialogs, db, path).written()
    rows = rows_of(db)
    assert len(rows) == 1  # expected failure
    assert compared(rows[0]) == compared(cli)
    assert rows[0]["files_processed"] == [str(path)]
    assert rows[0]["model_version"].startswith("fr_core_news_lg-")
    assert rows[0]["model_version"] != "fr_core_news_lg-unknown"


# ---------------------------------------------------------------------------
# Controls: the paths that log today, and the paths that write nothing
# ---------------------------------------------------------------------------


def test_k3_desktop_batch_without_review_rows_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    paths = [write_doc(tmp_path / "in" / f"doc{index}.txt") for index in range(2)]
    clis = [_cli_row(tmp_path, path, i) for i, path in enumerate(paths)]
    db = fresh_db(tmp_path / "mappings.db")
    _Batch171(qtbot, main_window, db, paths, tmp_path / "out", review=False).run()
    assert [_seen(row) for row in rows_of(db)] == [
        (compared(cli), [str(path)]) for cli, path in zip(clis, paths)
    ]


def test_k3b_desktop_batch_without_review_failure_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    path = write_doc(tmp_path / "in" / "doc0.txt")
    stand_in.fail = True
    cli = _cli_row(tmp_path, path)
    db = fresh_db(tmp_path / "mappings.db")
    _Batch171(qtbot, main_window, db, [path], tmp_path / "out", review=False).run()
    assert [_seen(row) for row in rows_of(db)] == [(compared(cli), [str(path)])]


def test_k4a_desktop_single_review_left_writes_nothing(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    db = fresh_db(tmp_path / "mappings.db")
    _Single171(qtbot, main_window, dialogs, db, write_doc(tmp_path / "doc.txt"))
    main_window.navigate_to("home")
    pre(main_window.current_screen_name() == "home", "home screen")
    assert rows_of(db) == []


def test_k4b_desktop_batch_cancelled_at_first_review_writes_nothing(  # type: ignore[no-untyped-def]
    qtbot, main_window, monkeypatch, tmp_path, stand_in, dialogs
) -> None:
    class _Confirmed:
        def exec(self) -> int:
            return 1

    monkeypatch.setattr(
        ConfirmDialog, "destructive", classmethod(lambda cls, *a, **k: _Confirmed())
    )
    paths = [write_doc(tmp_path / "in" / f"doc{index}.txt") for index in range(2)]
    db = fresh_db(tmp_path / "mappings.db")
    batch = _Batch171(qtbot, main_window, db, paths, tmp_path / "out")

    def cancel_at_first_review() -> None:
        batch.wait_doc(0)
        batch.vs.batch_cancel_button.click()

    batch.run(cancel_at_first_review)
    assert rows_of(db) == []


def test_k5_desktop_single_wrong_passphrase_writes_nothing(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, stand_in, dialogs
) -> None:
    db = str(tmp_path / "mappings.db")
    init_database(db, OTHER_PASSPHRASE)
    worker, result, _ = _detect(db, write_doc(tmp_path / "doc.txt"))
    pre(result is None, "no detection result")
    assert worker.is_passphrase_error is True
    assert rows_of(db, OTHER_PASSPHRASE) == []
