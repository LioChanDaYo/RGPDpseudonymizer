"""Story 15.1: every review row matches what is written (core and command
line; W1, E1, E3, E4, R1 to R6, controls K1 to K4).

Written by the BMAD dev agent (Claude), tests first. Two detections of one
text (a place and a person on the same word, a place with its preposition
over an organisation, a place inside an organisation name, two names that
overlap in part) each become a review row with its own pseudonym; the end
writes one replacement per overlap. These tests pin the end's one rule
(``written_parts``, Fix design E.1), the end that draws and saves only what
it writes (E), the command line's mark of a group whose pseudonym is not
written (B.5) and the crossing rule (Lionel's Q3).

Detection is a stand-in that returns the spans given, exactly (Story 11.5's
``_found`` drops a span inside a longer one, so it cannot make S2 to S4).
The command line's review is ``DocumentProcessor.process_document`` with its
interactive review, every group confirmed unless ``keys`` says otherwise;
``ReviewScreen.display_entity`` is wrapped to record, per (text, type), the
pseudonym shown and its ``not_written`` keyword (the string ``"absent"``
when none is passed). ``DocumentProcessor._resolve_pseudonyms`` is wrapped
to record the list the end receives.

Every marked case reaches the new interfaces through helpers that exist on
the unfixed code: ``_parts`` (None when ``core/written_spans.py`` or its
``written_parts`` is absent) and the display stand-in (``"absent"``).
Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and main-corpus words
only. No spaCy model, no Qt.
"""

from __future__ import annotations

import copy
import importlib
import importlib.util
import itertools
import random
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.ui import ReviewScreen
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _new_db,
    _replacements,
    pre,
)
from tests.unit.test_parallel_saved_pseudonym import (
    _settings,  # noqa: F401 - autouse fixture: no settings file read or written
)
from tests.unit.test_review_list_written_pseudonym import (
    _changed,
    _Draws,
    _finalize,
    _key,
    _places,
    _row,
    _saved,
    _store,
    install_draws,
)

PERSON = "PERSON"
LOCATION = "LOCATION"
ORG = "ORG"

ZORBAL = "Zorbal"
ZQ = "Zorbal Quentrix"
PLACE = "Zorbaville"
AT_PLACE = "à Zorbaville"
ORG_NAME = "Zorbtech"
AT_ORG = "à Zorbtech"
ORG_PLACE = "Zorbtech Zorbaville"
ORG_ZORBAL = "Zorbtech Zorbal"
CUSTOM = "Xantor Vellion"

ABSENT = "absent"

TESTS_FIRST = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 15.1 tests first: a review row shows a pseudonym that is not written",
)

# --- The test documents (Test Plan, "Conventions") ---------------------------

# A span given to the detector stand-in: (text, type, start)
Span = tuple[str, str, int]

S1 = "Réponse de Zorbal : d'accord."
S1_PLACE_FIRST: list[Span] = [(ZORBAL, LOCATION, 11), (ZORBAL, PERSON, 11)]
S1_PERSON_FIRST: list[Span] = [(ZORBAL, PERSON, 11), (ZORBAL, LOCATION, 11)]
S1_ORDERS = {"place_first": S1_PLACE_FIRST, "person_first": S1_PERSON_FIRST}

S2 = "Le poste est basé à Zorbtech."
S2_SPANS: list[Span] = [(AT_ORG, LOCATION, 18), (ORG_NAME, ORG, 20)]

S3 = "Elle travaille à Zorbaville. Zorbtech Zorbaville a signé le contrat."
S3_SPANS: list[Span] = [
    (AT_PLACE, LOCATION, 15),
    (ORG_PLACE, ORG, 29),
    (PLACE, LOCATION, 38),
]

S4 = "Zorbtech Zorbal Quentrix a signé le contrat."
S4_SPANS: list[Span] = [(ORG_ZORBAL, ORG, 0), (ZQ, PERSON, 9)]
S4_TAIL = " a signé le contrat."

S5_CELL1 = "Zorbal a signé le contrat."
S5_CELL2 = "Zorbaville a signé le contrat."
S5_CELL1_SPANS: list[Span] = [(ZORBAL, LOCATION, 0), (ZORBAL, PERSON, 0)]
S5_CELL2_SPANS: list[Span] = [(PLACE, LOCATION, 0)]


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


# --- The end's rule today, copied (``_apply_replacements``, the loop) -------


def _today(spans: Sequence[tuple[int, int]]) -> set[int]:
    """The indices today's loop writes whole: sorted by start then longest,
    ties in input order; a span that overlaps none kept is kept."""
    kept: list[tuple[int, int]] = []
    indices: set[int] = set()
    for index in sorted(range(len(spans)), key=lambda i: (spans[i][0], -spans[i][1])):
        start, end = spans[index]
        if not any(not (end <= ks or start >= ke) for ks, ke in kept):
            kept.append((start, end))
            indices.add(index)
    return indices


def _today_cells(spans: Sequence[tuple[str, int, int]]) -> set[int]:
    """``_today`` within each cell (the tabular writer applies it per cell)."""
    indices: set[int] = set()
    by_cell: dict[str, list[int]] = {}
    for index, (cell, _, _) in enumerate(spans):
        by_cell.setdefault(cell, []).append(index)
    for members in by_cell.values():
        local = _today([(spans[i][1], spans[i][2]) for i in members])
        indices.update(members[k] for k in local)
    return indices


# --- The new interfaces, reached on the unfixed code too --------------------


def _parts() -> Callable[..., Any] | None:
    """``written_parts`` of ``core/written_spans.py`` (Fix design E.1), or
    None where the module or the function does not exist."""
    name = "gdpr_pseudonymizer.core.written_spans"
    if importlib.util.find_spec(name) is None:
        return None
    module = importlib.import_module(name)
    function: Callable[..., Any] | None = getattr(module, "written_parts", None)
    return function


def _mark(value: Any) -> Any:
    """A ``NotWritten`` as (lost, places, by); None and ``"absent"`` as
    they are."""
    if value is None or isinstance(value, str):
        return value
    by = getattr(value, "by", None)
    return (
        getattr(value, "lost", None),
        getattr(value, "places", None),
        None if by is None else tuple(tuple(entry) for entry in by),
    )


def _known(value: Any) -> Any:
    """A ``NotWritten``'s ``by_known`` as a tuple; None and ``"absent"`` as
    they are."""
    if value is None or isinstance(value, str):
        return value
    known = getattr(value, "by_known", None)
    return None if known is None else tuple(known)


# --- W1: the end's one rule --------------------------------------------------


def _violations(
    spans: Sequence[tuple[str, int, int]],
    texts: Mapping[str, str],
    parts: Sequence[Any],
) -> list[str]:
    """What breaks W1's four properties on one list (empty: none)."""
    if len(parts) != len(spans):
        return [f"{len(parts)} parts for {len(spans)} spans"]
    found: list[str] = []
    today = _today_cells(spans)
    whole = {
        i
        for i, part in enumerate(parts)
        if part is not None and tuple(part) == (spans[i][1], spans[i][2])
    }
    if whole != today:
        found.append(f"whole {sorted(whole)} != today {sorted(today)}")
    covered: dict[str, set[int]] = {}
    for i, part in enumerate(parts):
        if part is None:
            continue
        start, end = tuple(part)
        cell, span_start, span_end = spans[i]
        if i not in whole:
            text = texts[cell]
            if not (span_start <= start < end <= span_end):
                found.append(f"part {(start, end)} outside {spans[i]}")
            elif not text[start].isalnum():
                found.append(f"part {(start, end)} of {spans[i]} starts at {start}")
        chars = covered.setdefault(cell, set())
        for position in range(start, end):
            if position in chars:
                found.append(f"character {cell}:{position} written twice")
            chars.add(position)
    for i in today:
        cell, start, end = spans[i]
        if not set(range(start, end)) <= covered.get(cell, set()):
            found.append(f"today's {spans[i]} not covered")
    return found


@TESTS_FIRST
@pytest.mark.parametrize("case", ["grid", "random"])
def test_written_parts_keeps_todays_rule(case: str) -> None:
    """W1 (AC12): ``written_parts`` writes whole exactly the spans today's
    loop writes, covers every character it covers, never writes a character
    twice, and writes a trimmed part only inside its span from a letter or
    digit. [grid]: every list of up to 4 of the 21 spans over « ab, c »
    (204,205 lists); [random]: 500 seeded lists of 60 spans over 3 cells."""
    written_parts = _parts()
    assert written_parts is not None  # expected failure
    lists: Iterator[tuple[list[tuple[str, int, int]], dict[str, str]]]
    if case == "grid":
        text = "ab, c"
        texts = {"": text}
        grid = [("", s, e) for s in range(6) for e in range(s, 6)]
        pre(len(grid) == 21, f"21 spans: {len(grid)}")
        lists = (
            (list(chosen), texts)
            for size in range(5)
            for chosen in itertools.product(grid, repeat=size)
        )
    else:
        lists = _random_lists()
    checked = 0
    failures: list[tuple[Any, list[str]]] = []
    for spans, texts in lists:
        checked += 1
        parts = written_parts(spans, texts)
        found = _violations(spans, texts, list(parts))
        if found:
            failures.append((spans, found))
    pre(checked == (204205 if case == "grid" else 500), f"lists: {checked}")
    assert failures[:3] == [], f"{len(failures)} lists break the rule"


def _random_lists() -> Iterator[tuple[list[tuple[str, int, int]], dict[str, str]]]:
    rng = random.Random(151)
    alphabet = "abcdefgh" * 3 + ",  "
    for _ in range(500):
        texts = {
            cell: "".join(rng.choice(alphabet) for _ in range(rng.randint(20, 40)))
            for cell in ("A1", "A2", "B1")
        }
        spans: list[tuple[str, int, int]] = []
        for _ in range(60):
            cell = rng.choice(sorted(texts))
            length = len(texts[cell])
            start = rng.randint(0, length)
            spans.append((cell, start, rng.randint(start, min(length, start + 10))))
        yield spans, texts


# --- The command line's review -----------------------------------------------


def _entity(name: str, entity_type: str, start: int, text: str) -> DetectedEntity:
    pre(text[start : start + len(name)] == name, f"slice {name!r} at {start}")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _entities(text: str, spans: Sequence[Span]) -> list[DetectedEntity]:
    return [_entity(name, etype, start, text) for name, etype, start in spans]


class _Detector:
    """Detection replaced: each text (a document, or a cell) gets exactly
    the spans given for it, as new entities on every call; any other text
    (a header cell) gets none."""

    def __init__(self, found: Mapping[str, Sequence[Span]]) -> None:
        self.found = found

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        return _entities(text, self.found.get(text, ()))


@contextmanager
def _detection(found: Mapping[str, Sequence[Span]]) -> Iterator[None]:
    with patch.object(
        DocumentProcessor, "_get_detector", lambda self: _Detector(found)
    ):
        yield


@dataclass
class _Run:
    """One command-line run: per (text, type) of each group, the pseudonym
    it showed and its ``not_written`` keyword (first display); the lists
    the end received; the result and the output path."""

    result: ProcessingResult
    output: Path
    shown: dict[tuple[str, str], str] = field(default_factory=dict)
    marks: dict[tuple[str, str], Any] = field(default_factory=dict)
    sent: list[list[DetectedEntity]] = field(default_factory=list)

    def written(self) -> str:
        pre(self.output.exists(), f"output written: {self.output}")
        return self.output.read_text(encoding="utf-8")

    def received(self) -> list[DetectedEntity]:
        pre(len(self.sent) == 1, f"the end ran once: {len(self.sent)}")
        return self.sent[0]


def _cli(
    tmp_path: Path,
    db: str,
    found: Mapping[str, Sequence[Span]],
    source: str,
    suffix: str = ".txt",
    keys: list[str] | None = None,
    groups: Sequence[tuple[str, str]] = (),
) -> _Run:
    """Story 11.5's ``_cli`` with the detector stand-in: ``process_document``
    with its interactive review over the file holding ``source``, every
    group confirmed unless ``keys`` gives the answers to
    ``get_user_action``. PRE: each (text, type) of ``groups`` displayed."""
    path = tmp_path / f"doc{suffix}"
    path.write_text(source, encoding="utf-8")
    output = tmp_path / f"doc_out{suffix}"
    shown: dict[tuple[str, str], str] = {}
    marks: dict[tuple[str, str], Any] = {}
    sent: list[list[DetectedEntity]] = []
    display_real = ReviewScreen.display_entity
    resolve_real = DocumentProcessor._resolve_pseudonyms

    def display(
        self: Any,
        entity: DetectedEntity,
        context: str,
        pseudonym: str,
        *a: Any,
        **k: Any,
    ) -> Any:
        key = (entity.text, entity.entity_type)
        shown.setdefault(key, pseudonym)
        marks.setdefault(key, k["not_written"] if "not_written" in k else ABSENT)
        return display_real(self, entity, context, pseudonym, *a, **k)

    def resolve(
        self: Any, ctx: Any, entities: list[DetectedEntity], *a: Any, **k: Any
    ) -> Any:
        sent.append([copy.copy(entity) for entity in entities])
        return resolve_real(self, ctx, entities, *a, **k)

    with (
        _detection(found),
        patch.object(ReviewScreen, "display_entity", display),
        patch.object(DocumentProcessor, "_resolve_pseudonyms", resolve),
        patch("gdpr_pseudonymizer.validation.ui.readchar.readkey", return_value="\r"),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_user_action",
            side_effect=keys if keys is not None else ["confirm"] * 20,
        ),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True
        ),
    ):
        result = DocumentProcessor(
            db_path=db, passphrase=PASSPHRASE, theme="neutral"
        ).process_document(str(path), str(output))
    pre(result.success, f"written: {result.error_message}")
    for group in groups:
        pre(group in shown, f"{group!r} shown in the review: {sorted(shown)}")
    return _Run(result, output, shown, marks, sent)


def _text_cli(
    tmp_path: Path,
    db: str,
    text: str,
    spans: Sequence[Span],
    keys: list[str] | None = None,
    groups: Sequence[tuple[str, str]] = (),
) -> _Run:
    return _cli(tmp_path, db, {text: spans}, text, keys=keys, groups=groups)


def _csv_cli(
    tmp_path: Path,
    db: str,
    cells: Sequence[tuple[str, Sequence[Span]]],
    groups: Sequence[tuple[str, str]] = (),
) -> _Run:
    """A ``.csv`` with the header « nom » and one text cell per line."""
    source = "nom\n" + "".join(f"{text}\n" for text, _ in cells)
    return _cli(tmp_path, db, dict(cells), source, suffix=".csv", groups=groups)


def _names(db: str) -> list[tuple[str, str]]:
    """(name, type) of every saved row, sorted."""
    return sorted((row.full_name, row.entity_type) for row in _saved(db))


def _prefix(entity: DetectedEntity) -> str:
    """The words before the name's mapping key (« à » of « à Zorbtech »),
    which the end writes in front of the pseudonym."""
    key = mapping_key(entity.text, entity.entity_type)
    at = entity.text.rfind(key)
    pre(at >= 0, f"the key {key!r} in {entity.text!r}")
    return entity.text[:at]


# --- E1, E3: the end saves and counts only the name written ------------------


@TESTS_FIRST
@pytest.mark.parametrize(
    "case", ["desktop_finalize", "cli_process", "csv_cell", "custom_not_written"]
)
def test_end_saves_only_the_name_written(
    tmp_path: Path, draws: _Draws, case: str
) -> None:
    """E1 (AC12): S1 with the place first: only the place « Zorbal » is
    written, so only it is saved; on [custom_not_written] the custom
    pseudonym of the person « Zorbal » (not written) is not saved either."""
    db = _new_db(tmp_path)
    output = tmp_path / "out.txt"
    if case == "desktop_finalize":
        _finalize(db, S1, _entities(S1, S1_PLACE_FIRST), output)
    elif case == "custom_not_written":
        _finalize(
            db,
            S1,
            _entities(S1, S1_PLACE_FIRST),
            output,
            custom={_key(ZORBAL, PERSON): CUSTOM},
        )
    elif case == "cli_process":
        _text_cli(tmp_path, db, S1, S1_PLACE_FIRST)
    else:
        _csv_cli(tmp_path, db, [(S5_CELL1, S5_CELL1_SPANS)])
    assert _names(db) == [(ZORBAL, LOCATION)]  # expected failure
    assert [row for row in _saved(db) if row.pseudonym_full == CUSTOM] == []


@TESTS_FIRST
def test_end_counts_only_the_name_written(tmp_path: Path, draws: _Draws) -> None:
    """E3 (AC12): S1 through ``finalize_document``: one new name, one
    place counted."""
    db = _new_db(tmp_path)
    result = _finalize(db, S1, _entities(S1, S1_PLACE_FIRST), tmp_path / "out.txt")
    counts = (result.entities_new, dict(result.entity_type_counts))
    assert counts == (1, {LOCATION: 1})  # expected failure


# --- E4: the crossing rule ---------------------------------------------------


@TESTS_FIRST
@pytest.mark.parametrize("case", ["desktop_finalize", "cli_process"])
def test_crossing_detection_written_over_its_own_words(
    tmp_path: Path, draws: _Draws, case: str
) -> None:
    """E4 (AC6, Lionel's Q3): S4, every row accepted. The organisation
    « Zorbtech Zorbal » is written over its span and the person « Zorbal
    Quentrix » over « Quentrix », each with its pseudonym; nothing of
    « Quentrix » stays in clear, and both names are saved."""
    db = _new_db(tmp_path)
    if case == "desktop_finalize":
        output = tmp_path / "out.txt"
        _finalize(db, S4, _entities(S4, S4_SPANS), output)
        written = output.read_text(encoding="utf-8")
        saved = {(r.full_name, r.entity_type): r.pseudonym_full for r in _saved(db)}
        pre((ORG_ZORBAL, ORG) in saved, f"the organisation saved: {sorted(saved)}")
        org_shown = saved[(ORG_ZORBAL, ORG)]
        person_shown = saved.get((ZQ, PERSON), "")
    else:
        run = _text_cli(
            tmp_path, db, S4, S4_SPANS, groups=[(ORG_ZORBAL, ORG), (ZQ, PERSON)]
        )
        written = run.written()
        org_shown = run.shown[(ORG_ZORBAL, ORG)]
        person_shown = run.shown[(ZQ, PERSON)]
    assert written == f"{org_shown} {person_shown}{S4_TAIL}"  # expected failure
    assert "Quentrix" not in written
    assert _names(db) == sorted([(ORG_ZORBAL, ORG), (ZQ, PERSON)])


# --- R1 to R6: the command line marks a group not written --------------------


@TESTS_FIRST
@pytest.mark.parametrize("order", ["place_first", "person_first"])
def test_cli_marks_the_group_not_written(
    tmp_path: Path, draws: _Draws, order: str
) -> None:
    """R1 (AC1, AC5): « Réponse de Zorbal : d'accord. » with a place and a
    person « Zorbal » on the same span: the group the end does not write
    (the second sent) is displayed with ``not_written`` 1 of 1 and the
    other as ``by``; the group written is displayed with None."""
    spans = S1_ORDERS[order]
    first, second = spans[0][1], spans[1][1]
    run = _text_cli(
        tmp_path,
        _new_db(tmp_path),
        S1,
        spans,
        groups=[(ZORBAL, PERSON), (ZORBAL, LOCATION)],
    )
    lost = _mark(run.marks[(ZORBAL, second)])
    assert lost == (1, 1, ((ZORBAL, first),))  # expected failure
    assert run.marks[(ZORBAL, first)] is None


@TESTS_FIRST
def test_cli_marks_a_group_not_written_at_some_places(
    tmp_path: Path, draws: _Draws
) -> None:
    """R2 (AC1): S3: the place group (« à Zorbaville » and « Zorbaville »)
    is not written at its second place, inside « Zorbtech Zorbaville »."""
    run = _text_cli(
        tmp_path,
        _new_db(tmp_path),
        S3,
        S3_SPANS,
        groups=[(AT_PLACE, LOCATION), (ORG_PLACE, ORG)],
    )
    pre(
        sorted(run.shown) == sorted([(AT_PLACE, LOCATION), (ORG_PLACE, ORG)]),
        f"one place group, one organisation group: {sorted(run.shown)}",
    )
    lost = _mark(run.marks[(AT_PLACE, LOCATION)])
    assert lost == (1, 2, ((ORG_PLACE, ORG),))  # expected failure
    assert run.marks[(ORG_PLACE, ORG)] is None


@TESTS_FIRST
def test_cli_marks_the_organisation_under_a_place_with_its_preposition(
    tmp_path: Path, draws: _Draws
) -> None:
    """R3 (AC1): S2: the organisation « Zorbtech » lies under the place
    « à Zorbtech », which is written."""
    run = _text_cli(
        tmp_path,
        _new_db(tmp_path),
        S2,
        S2_SPANS,
        groups=[(AT_ORG, LOCATION), (ORG_NAME, ORG)],
    )
    lost = _mark(run.marks[(ORG_NAME, ORG)])
    assert lost == (1, 1, ((AT_ORG, LOCATION),))  # expected failure
    assert run.marks[(AT_ORG, LOCATION)] is None


@TESTS_FIRST
def test_cli_crossing_group_is_not_marked(tmp_path: Path, draws: _Draws) -> None:
    """R4 (AC1, the crossing rule): S4: the person is written over
    « Quentrix », so neither group is marked; both get the keyword."""
    run = _text_cli(
        tmp_path,
        _new_db(tmp_path),
        S4,
        S4_SPANS,
        groups=[(ORG_ZORBAL, ORG), (ZQ, PERSON)],
    )
    assert run.marks[(ZQ, PERSON)] is None  # expected failure
    assert run.marks[(ORG_ZORBAL, ORG)] is None


@TESTS_FIRST
def test_cli_marks_a_group_lost_to_a_known_name(tmp_path: Path, draws: _Draws) -> None:
    """R5 (AC1): S1 with the place first, « Zorbal » already saved as a
    place: the place is written without review, so the person group is
    displayed with ``not_written`` naming it, ``by_known`` (True,)."""
    db = _new_db(tmp_path)
    _store(db, ZORBAL, LOCATION, _places()[-1])
    run = _text_cli(tmp_path, db, S1, S1_PLACE_FIRST, groups=[(ZORBAL, PERSON)])
    pre((ZORBAL, LOCATION) not in run.shown, "the known place is not reviewed")
    value = run.marks[(ZORBAL, PERSON)]
    assert _mark(value) == (1, 1, ((ZORBAL, LOCATION),))  # expected failure
    assert _known(value) == (True,)


@TESTS_FIRST
def test_cli_spreadsheet_marks_per_cell(tmp_path: Path, draws: _Draws) -> None:
    """R6 (AC1): S5 as a ``.csv``: cell 1's person group is marked (the
    place « Zorbal » of the same cell is written); the place « Zorbaville »
    of cell 2, at the same offsets in another cell, is not."""
    run = _csv_cli(
        tmp_path,
        _new_db(tmp_path),
        [(S5_CELL1, S5_CELL1_SPANS), (S5_CELL2, S5_CELL2_SPANS)],
        groups=[(ZORBAL, PERSON), (ZORBAL, LOCATION), (PLACE, LOCATION)],
    )
    lost = _mark(run.marks[(ZORBAL, PERSON)])
    assert lost == (1, 1, ((ZORBAL, LOCATION),))  # expected failure
    assert run.marks[(PLACE, LOCATION)] is None
    assert run.marks[(ZORBAL, LOCATION)] is None


# --- Controls (unmarked; pass on the base and the head) ----------------------


@pytest.mark.parametrize("case", ["s1_place_first", "s1_person_first", "s2", "s3"])
def test_written_spans_and_types_unchanged(
    tmp_path: Path, draws: _Draws, case: str
) -> None:
    """K1 (AC6): every group confirmed, the spans written and their types
    are those today's rule gives over the list the end receives: at each
    span it keeps, the text written is the preposition, if any, then the
    saved pseudonym of that name and type."""
    text, spans = {
        "s1_place_first": (S1, S1_PLACE_FIRST),
        "s1_person_first": (S1, S1_PERSON_FIRST),
        "s2": (S2, S2_SPANS),
        "s3": (S3, S3_SPANS),
    }[case]
    db = _new_db(tmp_path)
    run = _text_cli(tmp_path, db, text, spans)
    received = run.received()
    kept = sorted(
        (received[i] for i in _today([(e.start_pos, e.end_pos) for e in received])),
        key=lambda entity: entity.start_pos,
    )
    expected = [
        _prefix(entity) + _row(db, entity.text, entity.entity_type).pseudonym_full
        for entity in kept
    ]
    written = _replacements(
        run.written(), text, [(e.start_pos, e.end_pos) for e in kept]
    )
    assert written == expected


@pytest.mark.parametrize("case", ["s1_place_first", "s2"])
def test_rejecting_the_written_group_writes_the_other(
    tmp_path: Path, draws: _Draws, case: str
) -> None:
    """K2 (AC6): the group written rejected, the other is written over its
    own span with the pseudonym it showed. The command line asks the
    groups person, organisation, place: the place is the second asked."""
    text, spans, other = {
        "s1_place_first": (S1, S1_PLACE_FIRST, (ZORBAL, PERSON)),
        "s2": (S2, S2_SPANS, (ORG_NAME, ORG)),
    }[case]
    run = _text_cli(
        tmp_path,
        _new_db(tmp_path),
        text,
        spans,
        keys=["confirm", "reject"] + ["confirm"] * 20,
        groups=[other],
    )
    start = next(s for name, etype, s in spans if (name, etype) == other)
    span = (start, start + len(other[0]))
    assert _replacements(run.written(), text, [span]) == [run.shown[other]]


def test_written_group_shows_what_is_written(tmp_path: Path, draws: _Draws) -> None:
    """K3 (AC8): S1 with the place first, every group confirmed: the place
    group showed the pseudonym written, and nothing is reported changed."""
    run = _text_cli(
        tmp_path,
        _new_db(tmp_path),
        S1,
        S1_PLACE_FIRST,
        groups=[(ZORBAL, PERSON), (ZORBAL, LOCATION)],
    )
    written = _replacements(run.written(), S1, [(11, 17)])
    assert written == [run.shown[(ZORBAL, LOCATION)]]
    assert _changed(run.result) == []


def test_audit_counts_every_entity_sent(tmp_path: Path, draws: _Draws) -> None:
    """K4 (AC12, Lionel's Q5): S1 with the place first, every group
    confirmed: the audit log's one PROCESS row counts the two entities
    sent, though one is written."""
    db = _new_db(tmp_path)
    _text_cli(tmp_path, db, S1, S1_PLACE_FIRST)
    with open_database(db, PASSPHRASE) as session:
        operations = AuditRepository(session.session).find_operations(
            operation_type="PROCESS"
        )
        counts = [operation.entity_count for operation in operations]
    assert counts == [2]
