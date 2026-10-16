"""Story 10.13: T7 to T10 pin the CLI summary (AC1 B2b and AC4).

T10 pins coverage per cell, including the PO's finding 3.

Written by Codex through Forge. Invented names only. The real command-line
review receives planned detections and keypresses; its final panel and question
are recorded in order, and its written output is checked. Preconditions fail
through pytest.fail before any behavior assertion.
"""

from __future__ import annotations

import io
import re
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import readchar
from rich.console import Console

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.ui import FinalConfirmationScreen

PASSPHRASE = "zorbalia_pass_A_123!"
DOC_C = "Quentrelle a signé avec Zorbalia Quentrix à Zorbaville. Quentrelle confirme."
DOC_L = "Zorbaville a signé à Quentrix."
STILL_TO_REVIEW = "⚠ Still to review: 1 (left in plain text)"
FINAL_QUESTION = "Ready to process document with validated entities?"


def pre(condition: bool, message: str) -> None:
    """Fail a precondition without allowing an AssertionError xfail to absorb it."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _at(
    text: str,
    name: str,
    entity_type: str,
    start: int,
    *,
    source: str = "spacy",
    is_ambiguous: bool = False,
) -> DetectedEntity:
    """Build a planned detection after checking its source slice."""
    pre(start >= 0 and text[start : start + len(name)] == name, "entity_slice")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source=source,
        is_ambiguous=is_ambiguous,
    )


def _doc_c_entities() -> list[DetectedEntity]:
    """Plan both occurrences of the first name and the two other names."""
    return [
        _at(DOC_C, "Quentrelle", "PERSON", DOC_C.find("Quentrelle")),
        _at(DOC_C, "Zorbalia Quentrix", "PERSON", DOC_C.find("Zorbalia Quentrix")),
        _at(DOC_C, "Zorbaville", "LOCATION", DOC_C.find("Zorbaville")),
        _at(DOC_C, "Quentrelle", "PERSON", DOC_C.rfind("Quentrelle")),
    ]


def _new_db(tmp_path: Path) -> str:
    """Initialize a real database for one test's processing runs."""
    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    return db


def _cli(
    tmp_path: Path,
    db: str,
    name: str,
    text: str,
    entities: list[DetectedEntity] | None,
    keys: list[str],
) -> tuple[str, list[tuple[str, str]]]:
    """Run real processing and record the final panel before its question.

    Preserve the input extension for future CSV runs, whose detector can be
    supplied by an enclosing patch of DocumentProcessor._get_detector.
    """
    source = tmp_path / name
    source.write_text(text, encoding="utf-8")
    output = tmp_path / f"{source.stem}.out{source.suffix}"
    events: list[tuple[str, str]] = []
    original_display = FinalConfirmationScreen.display

    def record_summary(
        screen: FinalConfirmationScreen, *args: Any, **kwargs: Any
    ) -> None:
        screen.console = Console(record=True, width=200, file=io.StringIO())
        original_display(screen, *args, **kwargs)
        events.append(("summary", screen.console.export_text()))

    def record_confirmation(prompt: str) -> bool:
        events.append(("ask", prompt))
        return True

    with (
        (
            patch.object(
                DocumentProcessor,
                "_detect_and_filter_entities",
                side_effect=lambda *args, **kwargs: [
                    DetectedEntity(**vars(entity)) for entity in entities
                ],
            )
            if entities is not None
            else nullcontext()
        ),
        patch("gdpr_pseudonymizer.validation.ui.readchar.readkey", side_effect=keys),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_confirmation",
            side_effect=record_confirmation,
        ),
        patch.object(FinalConfirmationScreen, "display", new=record_summary),
    ):
        result = DocumentProcessor(db, PASSPHRASE).process_document(
            str(source), str(output)
        )

    pre(result.success, "process_document.success")
    pre([kind for kind, _ in events] == ["summary", "ask"], "events")
    pre(output.is_file(), "output.is_file")
    return output.read_text(encoding="utf-8"), events


def _panel_text_lines(summary: str) -> list[str]:
    """Extract nonempty panel content without its borders or padding."""
    return [
        content
        for line in summary.splitlines()
        if line.startswith("│")
        if (content := line.removeprefix("│").removesuffix("│").strip())
    ]


def assert_written_as_today(
    output: str, source: str, spans: list[tuple[int, int]]
) -> list[str]:
    """Check nonempty span replacements and preserve every other character."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    assert match is not None
    return list(match.groups())


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.13: no 'Still to review' line in the CLI summary on the unfixed "
        "code; fixed in Task 2"
    ),
)
@pytest.mark.parametrize(
    "skip_key", ["n", readchar.key.RIGHT, readchar.key.DOWN], ids=["n", "right", "down"]
)
def test_cli_skipped_name_gives_the_line(tmp_path: Path, skip_key: str) -> None:
    """T7 (AC4): skipping one repeated name adds one final warning line."""
    entities = _doc_c_entities()
    output, events = _cli(
        tmp_path,
        _new_db(tmp_path),
        "doc0.txt",
        DOC_C,
        entities,
        ["\r", skip_key, " ", " "],
    )
    lines = [line for line in events[0][1].splitlines() if "Still to review" in line]
    assert len(lines) == 1 and STILL_TO_REVIEW in lines[0]  # expected failure
    assert events[1] == ("ask", FINAL_QUESTION)
    panel_lines = _panel_text_lines(events[0][1])
    assert panel_lines[-1] == STILL_TO_REVIEW
    assert panel_lines[-2].startswith("Total entities to process")
    spans = [
        (entity.start_pos, entity.end_pos)
        for entity in entities
        if entity.text != "Quentrelle"
    ]
    assert_written_as_today(output, DOC_C, spans)
    assert output.count("Quentrelle") == 2


def test_cli_every_name_decided_no_line(tmp_path: Path) -> None:
    """T8 (AC4): deciding every name keeps the summary free of a warning."""
    entities = _doc_c_entities()
    output, events = _cli(
        tmp_path,
        _new_db(tmp_path),
        "doc0.txt",
        DOC_C,
        entities,
        ["\r", " ", " ", " "],
    )
    assert not any("Still to review" in line for line in events[0][1].splitlines())
    assert "Quentr" not in output and "orbal" not in output


def _doc_l_entities() -> list[DetectedEntity]:
    """Plan a place covered by another type and a separate location."""
    return [
        _at(DOC_L, "Zorbaville", "ORG", 0),
        _at(
            DOC_L,
            "Zorbaville",
            "LOCATION",
            0,
            source="regex",
            is_ambiguous=True,
        ),
        _at(DOC_L, "Quentrix", "LOCATION", DOC_L.find("Quentrix")),
    ]


@pytest.mark.parametrize("case", ["in_review", "known"])
def test_cli_same_place_other_type_no_line(tmp_path: Path, case: str) -> None:
    """T9 (AC1 B2b, AC4): reviewed or known coverage suppresses the warning."""
    db = _new_db(tmp_path)
    entities = _doc_l_entities()
    keys = ["\r", " ", "n", " "]
    if case == "known":
        seed = "Zorbaville."
        result = DocumentProcessor(db, PASSPHRASE).finalize_document(
            seed,
            [_at(seed, "Zorbaville", "ORG", 0)],
            str(tmp_path / "seed.txt"),
        )
        pre(result.success, "finalize_document.success")
        keys = ["\r", "n", " "]

    output, events = _cli(tmp_path, db, "doc0.txt", DOC_L, entities, keys)
    pre("Zorbaville" not in output, "Zorbaville")
    pre("Quentrix" not in output, "Quentrix")
    assert not any("Still to review" in line for line in events[0][1].splitlines())


def _csv_cell_plan(case: str) -> list[tuple[str, list[DetectedEntity]]]:
    """Plan identical offsets in either separate cells or a shared cell."""
    org = _at("Zorbaville", "Zorbaville", "ORG", 0)
    location = _at(
        "Zorbaville",
        "Zorbaville",
        "LOCATION",
        0,
        source="regex",
        is_ambiguous=True,
    )
    last_cell = ("Quentrix", [_at("Quentrix", "Quentrix", "LOCATION", 0)])
    if case == "other_cell":
        return [("Zorbaville", [org]), ("Zorbaville", [location]), last_cell]
    return [("Zorbaville", [org, location]), last_cell]


class PlannedCellDetector:
    """Return fresh detections after checking each cell in reading order."""

    def __init__(self, plan: list[tuple[str, list[DetectedEntity]]]) -> None:
        self.plan = plan
        self.calls: list[str] = []

    def detect_entities(self, cell_text: str) -> list[DetectedEntity]:
        """Check the next cell's text and copy its planned entities."""
        pre(len(self.calls) < len(self.plan), "detect_entities.calls")
        planned_text, entities = self.plan[len(self.calls)]
        pre(cell_text == planned_text, "detect_entities.cell_text")
        self.calls.append(cell_text)
        return [DetectedEntity(**vars(entity)) for entity in entities]


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            "other_cell",
            marks=pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason=(
                    "Story 10.13: no 'Still to review' line for a cell left in clear "
                    "on the unfixed code; fixed in Task 2"
                ),
            ),
            id="other_cell",
        ),
        pytest.param("same_cell", id="same_cell"),
    ],
)
def test_cli_spreadsheet_counts_per_cell(tmp_path: Path, case: str) -> None:
    """T10 (AC1, AC4; PO finding 3): coverage applies within each CSV cell."""
    plan = _csv_cell_plan(case)
    detector = PlannedCellDetector(plan)
    text = ",".join(cell_text for cell_text, _ in plan) + "\n"
    with patch.object(DocumentProcessor, "_get_detector", return_value=detector):
        output, events = _cli(
            tmp_path,
            _new_db(tmp_path),
            "doc0.csv",
            text,
            None,
            ["\r", " ", "n", " "],
        )

    pre(detector.calls == [cell_text for cell_text, _ in plan], "detected_cells")
    lines = [line for line in events[0][1].splitlines() if "Still to review" in line]
    if case == "other_cell":
        assert len(lines) == 1 and STILL_TO_REVIEW in lines[0]  # expected failure
        assert output.count("Zorbaville") == 1
    else:
        assert not lines
        assert "Zorbaville" not in output
    assert "Quentrix" not in output
