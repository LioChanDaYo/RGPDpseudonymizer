"""Story 10.11: a custom pseudonym in desktop batch review, through the real
batch worker (T22-T24, T16b, T19b, T20b).

Each test drives the real ``BatchScreen``, ``ValidationScreen`` and
``BatchWorker`` thread; only ``DocumentProcessor._detect_and_filter_entities``
is replaced (Story 10.10's harness). The assertions run after the worker has
finished, on the written files and the stored rows. Each test asserts its
preconditions (messages start with "PRE:") before the behaviour under test;
the first assertion after them is the expected failure on the unfixed code.
Invented names only.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 10.10's test_batch_review_real_worker.py). This is a
# warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
PENDING = EntityReviewState.PENDING
REJECTED = EntityReviewState.REJECTED

QZ = "Quentrel Zorbalia"
CUSTOM = "Xantor Vellion"

# As in Story 10.10's tests.
DOC0 = "Zorbaville a signé à Zorbaville."
DOC1 = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
SAINT = "Zorbal a signé avec Zorbal. Le projet est à Saint-Zorbal."
THREE = (
    "Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia Quentrix. "
    "Le projet est signé avec Quentrel Zorbalia Quentrix."
)
TITLED = "Zorbal a signé avec M. Zorbal."
LATER2 = "Zorbalia a signé avec Quentrel Zorbalia."


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    assert text[start : start + len(name)] == name, "PRE: entity slice"
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _spans(entities: list[DetectedEntity]) -> list[tuple[int, int]]:
    return sorted((e.start_pos, e.end_pos) for e in entities)


def _replacements(output: str, source: str, spans: list[tuple[int, int]]) -> list[str]:
    """The string written in place of each span (in span order); every other
    character of the source unchanged."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    assert match is not None, f"text damaged or a span not replaced: {output!r}"
    return list(match.groups())


def _stored(db: str, key: str, entity_type: str) -> tuple[Any, ...] | None:
    """(full_name, first_name, last_name, pseudonym_full, pseudonym_first,
    pseudonym_last) of the stored row of (key, type), or None."""
    with open_database(db, PASSPHRASE) as session:
        row = SQLiteMappingRepository(session).find_by_full_name_and_type(
            key, entity_type
        )
        if row is None:
            return None
        return (
            row.full_name,
            row.first_name,
            row.last_name,
            row.pseudonym_full,
            row.pseudonym_first,
            row.pseudonym_last,
        )


class _Batch:
    """A real batch run with validation per document; only detection replaced
    (Story 10.10's harness, test_batch_review_real_worker.py)."""

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

    def accept_pending_and_validate(self) -> None:
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        self.vs.finalize_button.click()

    def output(self, index: int) -> str:
        return (self.out / f"doc{index}_pseudonymized.txt").read_text(encoding="utf-8")


def _doc1_entities() -> list[DetectedEntity]:
    return [_at(DOC1, QZ, "PERSON", 0), _at(DOC1, QZ, "PERSON", DOC1.rfind(QZ))]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.11: reproduces the custom pseudonym never written in batch on the unfixed code; fixed in Task 2",
)
def test_batch_custom_written_at_every_place_and_stored(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T22 (AC1, AC2, Q3): set on one place, written at both places of the
    name and stored, split."""
    batch = _Batch(qtbot, main_window, tmp_path, [(DOC1, _doc1_entities())])

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        r1, r2 = state.get_all_entities()
        assert [r1.state, r2.state] == [PENDING, PENDING], "PRE: pending"
        state.change_pseudonym(r1.entity_id, CUSTOM)
        batch.accept_pending_and_validate()

    batch.run(body)
    written = _replacements(batch.output(0), DOC1, _spans(_doc1_entities()))
    assert written == [CUSTOM, CUSTOM], written  # expected failure
    assert _stored(batch.db, QZ, "PERSON") == (
        QZ,
        "Quentrel",
        "Zorbalia",
        CUSTOM,
        "Xantor",
        "Vellion",
    )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.11: reproduces the custom pseudonym never written in batch on the unfixed code; fixed in Task 2",
)
def test_batch_custom_survives_prev_next(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T23 (AC5): "◀ Précédent" and "Suivant ▶" keep it, and it is written."""
    doc0 = [_at(DOC0, "Zorbaville", "ORG", 0), _at(DOC0, "Zorbaville", "ORG", 21)]
    batch = _Batch(
        qtbot, main_window, tmp_path, [(DOC0, doc0), (DOC1, _doc1_entities())]
    )

    def body(record: dict[str, Any]) -> None:
        batch.wait_doc(0)
        batch.accept_pending_and_validate()
        state = batch.wait_doc(1)
        state.change_pseudonym(state.get_all_entities()[0].entity_id, CUSTOM)
        assert batch.vs.prev_button.isVisibleTo(batch.vs), "PRE: Précédent visible"
        batch.vs.prev_button.click()
        assert batch.vs.doc_index == 0, "PRE: on doc 0"
        batch.vs.next_button.click()
        assert batch.vs.doc_index == 1, "PRE: back on doc 1"
        batch.accept_pending_and_validate()

    batch.run(body)
    written = _replacements(batch.output(1), DOC1, _spans(_doc1_entities()))
    assert written == [CUSTOM, CUSTOM], written  # expected failure


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.11: reproduces the custom pseudonym never written in batch on the unfixed code; fixed in Task 2",
)
def test_batch_later_document_reuses_custom(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T24 (AC2, Q4): the next document of the batch shows and writes the
    custom pseudonym, and its last part for the last name alone."""
    later = [
        _at(LATER2, "Zorbalia", "PERSON", 0),
        _at(LATER2, QZ, "PERSON", LATER2.find(QZ)),
    ]
    batch = _Batch(
        qtbot, main_window, tmp_path, [(DOC1, _doc1_entities()), (LATER2, later)]
    )

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        state.change_pseudonym(state.get_all_entities()[0].entity_id, CUSTOM)
        batch.accept_pending_and_validate()
        state2 = batch.wait_doc(1)
        record["shown"] = [
            state2.get_pseudonym(r.entity_id) for r in state2.get_all_entities()
        ]
        batch.accept_pending_and_validate()

    record = batch.run(body)
    written = _replacements(batch.output(0), DOC1, _spans(_doc1_entities()))
    assert written == [CUSTOM, CUSTOM], written  # expected failure
    assert _replacements(batch.output(1), LATER2, _spans(later)) == ["Vellion", CUSTOM]
    assert record["shown"][1] == CUSTOM


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.11: reproduces the custom pseudonym never written in batch (Lionel's Q3 preview) on the unfixed code; fixed in Task 2",
)
def test_lionel_q3_preview_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T16b (Q3, Lionel's preview; PO R7): [Zorbal] [Zorbal] [rejected:
    Saint-Zorbal]; "Xantor" on row 1 is written at rows 1 and 2; Saint-Zorbal
    stays as it is."""
    entities = [
        _at(SAINT, "Zorbal", "PERSON", 0),
        _at(SAINT, "Zorbal", "PERSON", SAINT.find("Zorbal", 1)),
        _at(SAINT, "Zorbal", "PERSON", SAINT.find("Saint-Zorbal") + 6),
    ]
    batch = _Batch(qtbot, main_window, tmp_path, [(SAINT, entities)])

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        r1, r2, r3 = state.get_all_entities()
        state.bulk_reject([r3.entity_id])
        assert [r1.state, r2.state, r3.state] == [PENDING, PENDING, REJECTED], "PRE"
        state.change_pseudonym(r1.entity_id, "Xantor")
        batch.accept_pending_and_validate()

    batch.run(body)
    expected = "Xantor a signé avec Xantor. Le projet est à Saint-Zorbal."
    written = batch.output(0)
    assert written == expected, written  # expected failure


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.11: reproduces the custom pseudonym never written in batch (titled form) on the unfixed code; fixed in Task 2",
)
def test_titled_form_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T19b (AC1; PO R7): the titled form keeps its title and takes the
    pseudonym."""
    entities = [
        _at(TITLED, "Zorbal", "PERSON", 0),
        _at(TITLED, "M. Zorbal", "PERSON", TITLED.find("M. Zorbal")),
    ]
    batch = _Batch(qtbot, main_window, tmp_path, [(TITLED, entities)])

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        state.change_pseudonym(state.get_all_entities()[0].entity_id, CUSTOM)
        batch.accept_pending_and_validate()

    batch.run(body)
    expected = "Xantor Vellion a signé avec M. Xantor Vellion."
    written = batch.output(0)
    assert written == expected, written  # expected failure


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.11: reproduces the custom pseudonym never written in batch (added row) on the unfixed code; fixed in Task 2",
)
def test_added_place_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """T20b (Q3; PO R7): set on a place added by hand, written at the found
    places of the name too."""
    starts = [THREE.find(QZ), THREE.find(QZ, 1), THREE.rfind(QZ)]
    entities = [
        _at(THREE, QZ, "PERSON", starts[0]),
        _at(THREE, QZ, "PERSON", starts[1]),
    ]
    batch = _Batch(qtbot, main_window, tmp_path, [(THREE, entities)])

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        r1, _r2 = state.get_all_entities()
        state.accept_entity(r1.entity_id)
        added = state.add_entity(QZ, "PERSON", starts[2], starts[2] + len(QZ))
        state.change_pseudonym(added, CUSTOM)
        batch.accept_pending_and_validate()

    batch.run(body)
    spans = [(start, start + len(QZ)) for start in starts]
    written = _replacements(batch.output(0), THREE, spans)
    assert written == [CUSTOM] * 3, written  # expected failure
