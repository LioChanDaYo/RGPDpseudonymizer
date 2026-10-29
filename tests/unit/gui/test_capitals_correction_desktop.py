"""Story 10.19: a correction in the desktop app reaches the name's forms in
capitals (T8, T14, T15, T16, T19 desktop, T21 desktop, T26, T27, T29, T30
desktop, T31, T32, T35, T36 desktop), and what must not change (G3, G4, G5,
G8 desktop, G9, G10).

Written by the BMAD dev agent (Claude), before the fix. Each test drives the
real single-document path (``DetectionWorker``, the validation screen, the
finalization) or the real batch path (``BatchScreen``, ``ValidationScreen``
and the ``BatchWorker`` thread), as Story 10.17's and 10.10's desktop tests;
only detection is replaced. A correction is made the way the edit dialog makes
it, ``GUIValidationState.modify_entity_text``; a name is added the way the
editor's add menu adds it, its ``add_entity_requested`` signal. Every
confirmation window answers yes.

Preconditions are ``pytest.fail("PRE: ...")`` calls, never ``assert``, so a
broken precondition is a red failure even under
``xfail(strict=True, raises=AssertionError)``. Observations made during a flow
are recorded and asserted after the written file exists; the first ``assert``
of each test is its expected failure on the unfixed code. Invented names and
main-corpus words only; a decomposed text is made at run time with
``unicodedata.normalize("NFD", ...)``.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
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
# test_batch_review_real_worker.py and test_hand_added_every_place.py). This
# is a warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
PERSON = "PERSON"

PENDING = EntityReviewState.PENDING
REJECTED = EntityReviewState.REJECTED
ADDED = EntityReviewState.ADDED

ZQ = "Zorbal Quentrix"
VM = "Vorlan Mestrix"
VQ = "Vorlène Quentrix"

T8_TEXT = "Zorbal Quentrix a signé. Signé : ZORBAL QUENTRIX."
T15_TEXT = "Vorlène Quentrix a signé. Signé : VORLENE QUENTRIX."
G3_TEXT = "Zorbal Quentrix a signé. Signé : Zorbal Quentrix."
G5_TEXT = "Zorbal Quentrix a signé. Signé : zorbal quentrix."
G8_TEXT = (
    "Vorlène Quentrix a signé. Signé : VORLENE QUENTRIX. "
    "Le contrat avec Vorlene Quentrix."
)
G9_TEXT = "Zorbal Quentrix a signé. Signé : zorbal. Le contrat avec Zorbal Quentrix."
G10_TEXT = "Signé : ZELVINE TESTAR. Zélvine Testar a signé."
T26_TEXT = "Vorlène Quentrix Zorbal a signé. Signé : VORLENE QUENTRIX ZORBAL."
T27_TEXT = "Signé : ZÉLVINE TESTAR. Zélvine Testar a signé."
T31_TEXT = "Zélvine Mézor a signé. Zélvine Mèzor a signé."
T35_TEXT = "Signé : ZÉLVINE TESTAR. Zélvine\nTestar a signé."
T36_TEXT = "Vorlan Mestrix valide. Vorlène a signé. VORLENE a signé."
T36B_TEXT = "Vorlan Mestrix valide. Signé : Bélora. Signé : BÊLORA."
T29_TEXT = (
    "Signé : ZELVINE MÉZOR. Le contrat avec ZELVINE TESTAR. Zélvine Mézor a signé."
)

Drive = Callable[["_Review", dict[str, Any]], None]


def pre(condition: bool, message: str) -> None:
    """A precondition: ``pytest.fail``, never an ``AssertionError``."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def occurrence(text: str, name: str, n: int = 0) -> int:
    """Start of the ``n``-th occurrence of ``name`` in ``text`` (``str.find``,
    counted from 0)."""
    start = -1
    for _ in range(n + 1):
        start = text.find(name, start + 1)
        pre(start >= 0, f"occurrence {n} of the name")
    return start


def found_at(text: str, name: str, n: int = 0) -> DetectedEntity:
    """The detector's PERSON entity at the ``n``-th occurrence of ``name``."""
    start = occurrence(text, name, n)
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


class _Review:
    """One review of one document through the real desktop path, ``single``
    (single-document review) or ``batch`` (batch review)."""

    def __init__(
        self,
        mode: str,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        text: str,
        entities: list[DetectedEntity],
        through_reader: bool = False,
    ) -> None:
        """``through_reader`` (single only): the file holds ``text`` as given,
        the app's reader (``read_file``) reads it, and only
        ``_detect_and_filter_entities`` is replaced; ``entities`` are placed
        in the composed text the reader returns."""
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.mode = mode
        self.qtbot = qtbot
        self.mw = main_window
        self.tmp_path = tmp_path
        self.file_text = text
        self.entities = entities
        self.through_reader = through_reader
        self.db = str(tmp_path / "mappings.db")
        init_database(self.db, PASSPHRASE)
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        self._output: str | None = None
        main_window.show()
        if mode == "batch":
            source_dir = tmp_path / "in"
            source_dir.mkdir()
            self.out = tmp_path / "out"
            path = source_dir / "doc0.txt"
            path.write_text(text, encoding="utf-8")
            main_window.navigate_to("batch")
            self.bs = main_window.stack.currentWidget()
            pre(isinstance(self.bs, BatchScreen), "batch screen")
            self.bs._files = [path]
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
        """The review's rows (of ``name`` when given)."""
        return [
            r
            for r in self.state.get_all_entities()
            if name is None or r.entity.text == name
        ]

    def row(self, name: str) -> Any:
        """The one detected row whose text is ``name``."""
        rows = [r for r in self.reviews(name) if r.state != ADDED]
        pre(len(rows) == 1, f"one detected row of the name ({len(rows)})")
        return rows[0]

    def add(self, name: str, n: int) -> None:
        """The editor's add request (PERSON) on the ``n``-th occurrence of
        ``name``."""
        start = occurrence(self.text, name, n)
        before = len(self.reviews())
        self.vs.editor.add_entity_requested.emit(PERSON, start, start + len(name))
        pre(len(self.reviews()) == before + 1, "the add made one row")

    def correct(self, review: Any, new_text: str, start: int) -> None:
        """The edit dialog's correction of a row to ``new_text`` at ``start``."""
        self.state.modify_entity_text(
            review.entity_id, new_text, start, start + len(new_text)
        )

    def accept_pending(self) -> None:
        state = self.state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)

    def validate(self) -> None:
        if self.mode == "single":
            self.vs._on_finalize()
        else:
            self.vs.finalize_button.click()

    # -- running ----------------------------------------------------------

    def run(self, drive: Drive) -> dict[str, Any]:
        """Review the document with ``drive``, validate it, wait for the
        written file. Returns what ``drive`` recorded."""
        record: dict[str, Any] = {}
        if self.mode == "single":
            self._start_single()
            drive(self, record)
            self.validate()
            self.qtbot.waitUntil(
                lambda: self.mw.current_screen_name() == "results", timeout=WAIT_MS
            )
            results = self.mw.stack.currentWidget()
            self._output = Path(results._temp_path).read_text(encoding="utf-8")
            return record
        self._run_batch(drive, record)
        return record

    def _start_single(self) -> None:
        from gdpr_pseudonymizer.gui.workers.detection_worker import (
            DetectionResult,
            DetectionWorker,
        )

        file_path = self.tmp_path / "doc0.txt"
        file_path.write_text(self.file_text, encoding="utf-8")
        worker = DetectionWorker(str(file_path), self.db, PASSPHRASE)
        worker.setAutoDelete(False)
        results: list[Any] = []
        errors: list[str] = []
        worker.signals.finished.connect(results.append)
        worker.signals.error.connect(errors.append)
        entities = self.entities
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
                read == [unicodedata.normalize("NFC", self.file_text)],
                "the detector is given the composed text",
            )
        else:
            with patch.object(
                DocumentProcessor,
                "detect_entities",
                return_value=(
                    self.file_text,
                    [DetectedEntity(**vars(e)) for e in entities],
                ),
            ):
                worker.run()
        pre(not errors, "no detection error")
        pre(len(results) == 1, "one detection result")
        pre(isinstance(results[0], DetectionResult), "detection result")
        self.vs.start_validation(results[0])
        self.mw.navigate_to("validation")
        pre(not self.vs.batch_mode, "single-document mode")

    def _run_batch(self, drive: Drive, record: dict[str, Any]) -> None:
        entities = self.entities

        def detect(text: str, *args: Any, **kwargs: Any) -> list[DetectedEntity]:
            return [DetectedEntity(**vars(e)) for e in entities]

        with patch.object(
            DocumentProcessor, "_detect_and_filter_entities", side_effect=detect
        ):
            self.bs._launch_worker(self.db, PASSPHRASE)
            try:
                self._wait_doc()
                drive(self, record)
                self.validate()
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)
            finally:
                if self.bs._worker is not None:
                    self.bs._worker.cancel()
                    self.qtbot.waitUntil(
                        lambda: self.bs._worker is None, timeout=WAIT_MS
                    )
        written = self.out / "doc0_pseudonymized.txt"
        pre(written.is_file(), "the batch wrote the document")
        self._output = written.read_text(encoding="utf-8")

    def _wait_doc(self) -> None:
        """Wait until the batch's document waits for its review."""
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == 0
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=WAIT_MS,
        )
        pre(vs.batch_mode, "batch mode")

    # -- the written file and the stored rows -------------------------------

    def output(self) -> str:
        pre(self._output is not None, "the written file")
        return str(self._output)

    def stored(self) -> list[tuple[str, str, str]]:
        """(full name, type, full pseudonym) of every stored row, sorted."""
        with open_database(self.db, PASSPHRASE) as session:
            rows = SQLiteMappingRepository(session).find_all()
            return sorted((r.full_name, r.entity_type, r.pseudonym_full) for r in rows)

    def names(self) -> list[tuple[str, str]]:
        """(full name, type) of every stored row, sorted."""
        return [(name, entity_type) for name, entity_type, _ in self.stored()]

    def pseudonym(self, name: str) -> str:
        """The pseudonym of the one PERSON row stored for ``name``."""
        rows = [p for n, t, p in self.stored() if (n, t) == (name, PERSON)]
        pre(len(rows) == 1, f"one stored row for {name!r}")
        return rows[0]


# ---------------------------------------------------------------------------
# AC3: a correction reaches the name's forms in capitals
# ---------------------------------------------------------------------------


def test_desktop_correction_reaches_capital_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T8 (AC3, single document): « Zorbal » and « ZORBAL » are one row;
    corrected as « Zorbal Quentrix », no part of « ZORBAL QUENTRIX » stays in
    clear."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T8_TEXT,
        [found_at(T8_TEXT, "Zorbal"), found_at(T8_TEXT, "ZORBAL")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one row in the review")
        r.correct(r.row("Zorbal"), ZQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "QUENTRIX" not in output, output  # expected failure
    zq = review.pseudonym(ZQ)
    assert output == f"{zq} a signé. Signé : {zq}."
    assert review.names() == [(ZQ, PERSON)]


def test_batch_correction_reaches_other_capitals(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T14 (AC3, Lionel's Q4): in batch review, correcting the « Zorbal » row
    also corrects the « ZORBAL » row."""
    review = _Review(
        "batch",
        qtbot,
        main_window,
        tmp_path,
        T8_TEXT,
        [found_at(T8_TEXT, "Zorbal"), found_at(T8_TEXT, "ZORBAL")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Zorbal"), ZQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "QUENTRIX" not in output, output  # expected failure
    zq = review.pseudonym(ZQ)
    assert output == f"{zq} a signé. Signé : {zq}."
    assert review.names() == [(ZQ, PERSON)]


def test_correction_reaches_accentless_capitals(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T15 (AC3, Q3 in a correction; the PO's S2): « Vorlène » and « VORLENE »
    are two rows; correcting « Vorlène » reaches « VORLENE QUENTRIX »."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T15_TEXT,
        [found_at(T15_TEXT, "Vorlène"), found_at(T15_TEXT, "VORLENE")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Vorlène"), VQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "QUENTRIX" not in output, output  # expected failure
    vq = review.pseudonym(VQ)
    assert output == f"{vq} a signé. Signé : {vq}."
    assert review.names() == [(VQ, PERSON)]


def test_batch_correction_reaches_accentless_capitals(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T16 (AC3, Q4 with Q3; the PO's M1): T15's document in batch review."""
    review = _Review(
        "batch",
        qtbot,
        main_window,
        tmp_path,
        T15_TEXT,
        [found_at(T15_TEXT, "Vorlène"), found_at(T15_TEXT, "VORLENE")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Vorlène"), VQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "QUENTRIX" not in output, output  # expected failure
    vq = review.pseudonym(VQ)
    assert output == f"{vq} a signé. Signé : {vq}."
    assert review.names() == [(VQ, PERSON)]


def test_desktop_decomposed_document(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T19 desktop (AC1-AC3 with Story 10.20's readers): T15's document, every
    accent stored as a separate mark, read by the app's own reader."""
    stored = unicodedata.normalize("NFD", T15_TEXT)
    pre(stored != T15_TEXT, "the file holds separate marks")
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        stored,
        [found_at(T15_TEXT, "Vorlène"), found_at(T15_TEXT, "VORLENE")],
        through_reader=True,
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(r.text == T15_TEXT, "the review's text is composed")
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Vorlène"), VQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "QUENTRIX" not in output, output  # expected failure
    vq = review.pseudonym(VQ)
    assert output == f"{vq} a signé. Signé : {vq}."
    assert review.names() == [(VQ, PERSON)]


def test_hand_row_reached_by_its_written_texts(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T21 desktop (AC3, G8's rule for rows added by hand; the orchestrator's
    ruling, 2026-10-25): « VORLENE » added by hand stands for « VORLENE » and
    « Vorlene » (Story 10.17); the every-place check reads the text written
    at each place, so the correction of « Vorlène » does not reach that row,
    which keeps its own decision."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        G8_TEXT,
        [found_at(G8_TEXT, "Vorlène")],
    )
    caps = occurrence(G8_TEXT, "VORLENE")
    other = occurrence(G8_TEXT, "Vorlene")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one detected row before the add")
        r.add("VORLENE", 0)
        hand = [x for x in r.reviews() if x.state == ADDED]
        pre(len(hand) == 1, "one row added by hand")
        places = r.state._occurrences(hand[0]) or []
        pre(
            [(p.start_pos, p.end_pos) for p in places]
            == [(caps, caps + 7), (other, other + 7)],
            "the hand row's places",
        )
        r.correct(r.row("Vorlène"), VQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    pre((VQ, PERSON) in review.names(), "(VQ, PERSON) saved")
    vq = review.pseudonym(VQ)
    assert f"avec {vq}" not in output, output  # expected failure
    hand = review.pseudonym("VORLENE")
    assert output == (
        f"{vq} a signé. Signé : {hand} QUENTRIX. Le contrat avec {hand} Quentrix."
    )
    assert review.names() == sorted([(VQ, PERSON), ("VORLENE", PERSON)])


@pytest.mark.parametrize("mode", ["single", "batch"])
def test_second_correction_reaches_rows_the_first_reached(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T26 (AC3, the second Codex review's first P0): « Vorlène » corrected to
    « Vorlène Quentrix » also corrects « VORLENE »; corrected again to
    « Vorlène Quentrix Zorbal », it reaches « VORLENE » again, through the
    span the first correction gave it."""
    review = _Review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        T26_TEXT,
        [found_at(T26_TEXT, "Vorlène"), found_at(T26_TEXT, "VORLENE")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Vorlène"), VQ, 0)
        pre(
            r.row("Vorlène").user_modification == VQ
            and r.row("VORLENE").user_modification == VQ,
            "both rows hold the first correction",
        )
        r.correct(r.row("Vorlène"), f"{VQ} Zorbal", 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "ZORBAL" not in output, output  # expected failure
    p = review.pseudonym(f"{VQ} Zorbal")
    assert output == f"{p} a signé. Signé : {p}."
    assert review.names() == [(f"{VQ} Zorbal", PERSON)]


def test_batch_unreached_row_stays_pending(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T27 (AC3, the second Codex review's second P0, CAPS-001 in the desktop):
    in batch review, « ZÉLVINE » corrected to « ZELVINE TESTAR » does not
    reach the « Zélvine » row, which stays pending, as on main."""
    review = _Review(
        "batch",
        qtbot,
        main_window,
        tmp_path,
        T27_TEXT,
        [found_at(T27_TEXT, "ZÉLVINE"), found_at(T27_TEXT, "Zélvine")],
    )
    caps = occurrence(T27_TEXT, "ZÉLVINE")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("ZÉLVINE"), "ZELVINE TESTAR", caps)
        record["accented"] = r.row("Zélvine").state
        r.accept_pending()

    record = review.run(drive)
    assert record["accented"] == PENDING, record  # expected failure
    zt, z = review.pseudonym("ZELVINE TESTAR"), review.pseudonym("Zélvine")
    assert review.output() == f"Signé : {zt}. {z} Testar a signé."


def test_single_row_unreached_at_one_place_stays_pending(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T29 (AC3, the second P0's rule in single-document review): the
    « ZELVINE » row stands for « ZELVINE MÉZOR » and « ZELVINE TESTAR »;
    « Zélvine » corrected to « Zélvine Mézor » reaches only the first, so
    that row stays pending, never written with a partial span."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T29_TEXT,
        [
            found_at(T29_TEXT, "ZELVINE", 0),
            found_at(T29_TEXT, "ZELVINE", 1),
            found_at(T29_TEXT, "Zélvine"),
        ],
    )
    title = occurrence(T29_TEXT, "Zélvine")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Zélvine"), "Zélvine Mézor", title)
        record["caps"] = r.row("ZELVINE").state
        r.accept_pending()

    record = review.run(drive)
    assert record["caps"] == PENDING, record  # expected failure
    z, zm = review.pseudonym("ZELVINE"), review.pseudonym("Zélvine Mézor")
    assert review.output() == (
        f"Signé : {z} MÉZOR. Le contrat avec {z} TESTAR. {zm} a signé."
    )


def test_desktop_single_added_words_never_left_in_clear(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T30 desktop (AC3, Lionel's answer on the leak, "fix it in 10.19"):
    « ZÉLVINE » and « Zélvine » are one row; corrected as « ZELVINE TESTAR »,
    the place « Zélvine » is widened over « Testar », the word the correction
    adds, so nothing of the name stays in clear."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T27_TEXT,
        [found_at(T27_TEXT, "ZÉLVINE"), found_at(T27_TEXT, "Zélvine")],
    )
    caps = occurrence(T27_TEXT, "ZÉLVINE")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one row in the review")
        r.correct(r.row("ZÉLVINE"), "ZELVINE TESTAR", caps)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "TESTAR" not in output.upper(), output  # expected failure
    p = review.pseudonym("ZELVINE TESTAR")
    assert output == f"Signé : {p}. {p} a signé."


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.19 v1.15: reproduces the widening over « Mèzor », another "
    "name's word, on 919a227; fixed in Task 11.2",
)
def test_desktop_single_widening_never_takes_another_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T31 desktop (AC3; the third Codex review's P0-1, the orchestrator's
    ruling 1): the « Zélvine » row corrected as « Zélvine Mézor » is never
    widened over « Mèzor » at its other place."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T31_TEXT,
        [found_at(T31_TEXT, "Zélvine", 0), found_at(T31_TEXT, "Zélvine", 1)],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one row in the review")
        r.correct(r.row("Zélvine"), "Zélvine Mézor", 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "Mèzor a signé" in output, output  # expected failure
    p = review.pseudonym("Zélvine Mézor")
    assert output == f"{p} a signé. {p} Mèzor a signé."


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.19 v1.15: reproduces a second correction from the capitals "
    "row missing the « Vorlène » row on 919a227; fixed in Task 11.2",
)
@pytest.mark.parametrize("mode", ["single", "batch"])
def test_desktop_second_correction_from_the_capitals_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs, mode
) -> None:
    """T32 (AC3; the third Codex review's P0-2, the orchestrator's ruling 3):
    « Vorlène » corrected to « Vorlène Quentrix » also corrects « VORLENE »;
    the « VORLENE » row then corrected to « Vorlène Quentrix Zorbal » reaches
    the « Vorlène » row again through their shared earlier correction."""
    review = _Review(
        mode,
        qtbot,
        main_window,
        tmp_path,
        T26_TEXT,
        [found_at(T26_TEXT, "Vorlène"), found_at(T26_TEXT, "VORLENE")],
    )
    caps = occurrence(T26_TEXT, "VORLENE")
    whole = f"{VQ} Zorbal"

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Vorlène"), VQ, 0)
        pre(
            r.row("Vorlène").user_modification == VQ
            and r.row("VORLENE").user_modification == VQ,
            "both rows hold the first correction",
        )
        r.correct(r.row("VORLENE"), whole, caps)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "ZORBAL" not in output.upper(), output  # expected failure
    p = review.pseudonym(whole)
    assert output == f"{p} a signé. Signé : {p}."


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.19 v1.15: reproduces « Testar » left past a line break on "
    "919a227; fixed in Task 11.2",
)
def test_desktop_single_widening_across_a_line_break(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T35 desktop (AC3; the third Codex review's P0-5, the orchestrator's
    ruling 2): the added word written after a line break is covered too."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T35_TEXT,
        [found_at(T35_TEXT, "ZÉLVINE"), found_at(T35_TEXT, "Zélvine")],
    )
    caps = occurrence(T35_TEXT, "ZÉLVINE")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one row in the review")
        r.correct(r.row("ZÉLVINE"), "ZELVINE TESTAR", caps)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    assert "TESTAR" not in output.upper(), output  # expected failure
    p = review.pseudonym("ZELVINE TESTAR")
    assert output == f"Signé : {p}. {p} a signé."


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.19 v1.15: reproduces a second add of « VORLENE » making a "
    "row for a place the « Vorlène » row holds on 919a227; fixed in Task 11.2",
)
def test_desktop_single_repeated_add_recognises_held_capitals_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T36 desktop (AC2; the third Codex review's P1, the orchestrator's
    ruling 6): « Vorlène » added by hand holds « VORLENE » too; adding
    « VORLENE » then makes no row."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T36_TEXT,
        [found_at(T36_TEXT, VM)],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        title = occurrence(T36_TEXT, "Vorlène")
        first = r.state.add_entity("Vorlène", PERSON, title, title + 7)
        pre(first != "" and len(r.reviews()) == 2, "the first add made a row")
        caps = occurrence(T36_TEXT, "VORLENE")
        record["second"] = r.state.add_entity("VORLENE", PERSON, caps, caps + 7)
        record["rows"] = len(r.reviews())
        r.accept_pending()

    record = review.run(drive)
    assert record["second"] == "" and record["rows"] == 2, record  # expected failure
    assert review.names() == sorted([(VM, PERSON), ("Vorlène", PERSON)])


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.19 v1.15: reproduces a second add of « Bélora » holding "
    "« BÊLORA », held by the « Belora » row, on 919a227; fixed in Task 11.2",
)
def test_desktop_single_repeated_add_reads_the_text_written_at_a_held_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """T36 desktop, case 2 (AC2; ADD-1019-01 through the text written): the
    « Belora » row holds « BÊLORA »; the « Bélora » row added next stands
    for « Bélora » only."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        T36B_TEXT,
        [found_at(T36B_TEXT, VM)],
    )
    title = occurrence(T36B_TEXT, "Bélora")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        caps = occurrence(T36B_TEXT, "BÊLORA")
        first = r.state.add_entity("Belora", PERSON, caps, caps + 6)
        pre(first != "", "the first add made a row")
        second = r.state.add_entity("Bélora", PERSON, title, title + 6)
        record["spans"] = sorted(r.state._hand_spans_by_id.get(second, []))
        r.accept_pending()

    record = review.run(drive)
    assert record["spans"] == [(title, title + 6)], record  # expected failure


# ---------------------------------------------------------------------------
# Guards (pass on the unfixed and the fixed code)
# ---------------------------------------------------------------------------


def test_desktop_correction_exact_capitals_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """G3 (AC12): a correction whose exact text is found at every place is
    placed as today."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        G3_TEXT,
        [found_at(G3_TEXT, "Zorbal", 0), found_at(G3_TEXT, "Zorbal", 1)],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one row in the review")
        r.correct(r.row("Zorbal"), ZQ, 0)
        r.accept_pending()

    review.run(drive)
    zq = review.pseudonym(ZQ)
    assert review.output() == f"{zq} a signé. Signé : {zq}."


def test_batch_own_rejected_row_stays(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """G4 (AC3, Q4: "except a row the user rejected on its own"): the
    « ZORBAL » row rejected on its own keeps its reject when the « Zorbal »
    row is corrected."""
    review = _Review(
        "batch",
        qtbot,
        main_window,
        tmp_path,
        T8_TEXT,
        [found_at(T8_TEXT, "Zorbal"), found_at(T8_TEXT, "ZORBAL")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        caps = r.row("ZORBAL")
        r.state.reject_entity(caps.entity_id)
        pre(caps.state == REJECTED, "the « ZORBAL » row rejected")
        r.correct(r.row("Zorbal"), ZQ, 0)
        r.accept_pending()

    review.run(drive)
    zq = review.pseudonym(ZQ)
    assert review.output() == f"{zq} a signé. Signé : ZORBAL QUENTRIX."
    assert review.names() == [(ZQ, PERSON)]


def test_batch_small_letter_row_not_reached(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """G5 (AC3, Q4: "never a row written entirely in small letters"): the
    « zorbal » row keeps its text when the « Zorbal » row is corrected."""
    review = _Review(
        "batch",
        qtbot,
        main_window,
        tmp_path,
        G5_TEXT,
        [found_at(G5_TEXT, "Zorbal"), found_at(G5_TEXT, "zorbal")],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        small = r.row("zorbal")
        r.correct(r.row("Zorbal"), ZQ, 0)
        record["small_text"] = small.entity.text
        r.accept_pending()

    record = review.run(drive)
    assert record["small_text"] == "zorbal"
    assert ("zorbal", PERSON) in review.names()


def test_desktop_three_spellings_keep_other_letters_apart(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """G8 desktop (AC3, single document; the orchestrator's ruling on the PO's
    v1.2 M1): the « VORLENE » row stands for « VORLENE » and « Vorlene », so a
    correction of « Vorlène » does not reach it."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        G8_TEXT,
        [
            found_at(G8_TEXT, "Vorlène"),
            found_at(G8_TEXT, "VORLENE"),
            found_at(G8_TEXT, "Vorlene"),
        ],
    )

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("Vorlène"), VQ, 0)
        r.accept_pending()

    review.run(drive)
    output = review.output()
    pre((VQ, PERSON) in review.names(), "(VQ, PERSON) saved")
    vq = review.pseudonym(VQ)
    assert f"avec {vq}" not in output, output
    assert review.names() == sorted(
        [(VQ, PERSON), ("VORLENE", PERSON), ("Vorlene", PERSON)]
    )
    caps, other = review.pseudonym("VORLENE"), review.pseudonym("Vorlene")
    assert output == (
        f"{vq} a signé. Signé : {caps} QUENTRIX. Le contrat avec {other} Quentrix."
    )


def test_hand_row_reaches_detected_row_of_same_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """G9 (AC3, 10.10's rule, Lionel's Q3 there; the orchestrator's ruling on
    the PO's v1.3 M1): « Zorbal » added by hand beside the detected « Zorbal »
    row that also stands for « zorbal », then corrected: the correction
    reaches that row, as today."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        G9_TEXT,
        [found_at(G9_TEXT, "Zorbal"), found_at(G9_TEXT, "zorbal")],
    )
    second = occurrence(G9_TEXT, "Zorbal", 1)

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 1, "one detected row before the add")
        r.add("Zorbal", 1)
        hand = [x for x in r.reviews("Zorbal") if x.state == ADDED]
        pre(len(hand) == 1, "one row added by hand")
        record["added"] = (hand[0].entity.start_pos, hand[0].entity.end_pos)
        r.correct(hand[0], ZQ, second)
        record["after"] = [
            (x.entity.text, x.entity.start_pos, x.entity.end_pos, x.state.name)
            for x in r.reviews()
        ]
        r.accept_pending()

    record = review.run(drive)
    output = review.output()
    pre((ZQ, PERSON) in review.names(), "(ZQ, PERSON) saved")
    assert "Quentrix" not in output, (record, output)
    zq = review.pseudonym(ZQ)
    assert output == f"{zq} a signé. Signé : {zq}. Le contrat avec {zq}."
    assert review.names() == [(ZQ, PERSON)]


def test_capitals_correction_leaves_accented_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, dialogs
) -> None:
    """G10 (AC3, QA's CAPS-001; the orchestrator's ruling): a correction typed
    in capitals without accents reaches from the name to its capitals forms,
    not back. Correcting the « ZELVINE » row leaves the « Zélvine » row to
    review, pending; the user then accepts it as it is."""
    review = _Review(
        "single",
        qtbot,
        main_window,
        tmp_path,
        G10_TEXT,
        [found_at(G10_TEXT, "ZELVINE"), found_at(G10_TEXT, "Zélvine")],
    )
    caps = occurrence(G10_TEXT, "ZELVINE")

    def drive(r: _Review, record: dict[str, Any]) -> None:
        pre(len(r.reviews()) == 2, "two rows in the review")
        r.correct(r.row("ZELVINE"), "ZELVINE TESTAR", caps)
        record["accented"] = r.row("Zélvine").state
        r.accept_pending()

    record = review.run(drive)
    assert record["accented"] == PENDING
    zt, z = review.pseudonym("ZELVINE TESTAR"), review.pseudonym("Zélvine")
    assert review.output() == f"Signé : {zt}. {z} Testar a signé."
