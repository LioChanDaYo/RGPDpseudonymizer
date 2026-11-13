"""Story 11.5: the review list shows the pseudonym that will be written (core
and command line; T1-T12, T18, T19, T27, T28, T38, T38c).

Written by the BMAD dev agent (Claude), tests first. The command line's
review is ``DocumentProcessor.process_document`` with its interactive review:
detection is replaced (Story 10.22's ``_detection``), every group is
confirmed, and the pseudonym each group shows is read from
``ReviewScreen.display_entity``. The desktop path is ``finalize_document``
with the pseudonyms the review showed (``proposals``), built here by hand.

The library's draw is a stand-in (``draws``): ``choice`` walks each list from
its first value, one counter per list, keyed by the list's contents. So on
the unfixed code the end's draw differs from the review's, and a value given
as a proposal is never the end's first draw.

Every marked case reaches the new behaviour through helpers that exist on
the unfixed code: ``_proposal`` (a local stand-in for ``PseudonymProposal``),
``_finalize`` (passes ``proposals`` only when ``finalize_document`` takes
it), ``_changed`` (``None`` when the result has no ``pseudonyms_changed``)
and ``_refresh`` (``{}`` when ``refresh_review_proposals`` does not exist).
Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and main-corpus words
only. No spaCy model, no Qt.
"""

from __future__ import annotations

import csv
import inspect
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import gdpr_pseudonymizer.core.document_processor as processor_module
import gdpr_pseudonymizer.pseudonym.library_manager as library_module
from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
)
from gdpr_pseudonymizer.pseudonym.library_manager import (
    LibraryBasedPseudonymManager,
)
from gdpr_pseudonymizer.validation.ui import ReviewScreen
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _new_db,
    _replacements,
    pre,
)
from tests.unit.test_parallel_saved_pseudonym import (
    _detection,
    _found,
    _settings,  # noqa: F401 - autouse fixture: no settings file read or written
    _spans,
)

ZQ = "Zorbal Quentrix"
ZM = "Zorbal Mestrix"
VM = "Vorlan Mestrix"
ZQ_CUT = "Zorbal Quentri"
TITLED = "Mme Zorbal Quentrix"
PLACE = "Zorbaville"
ORG_NAME = "Zorbtech"
PERSON = "PERSON"
LOCATION = "LOCATION"
ORG = "ORG"

DB_PS = "Dravin Brontel"
DT_PS = "Dravin Telvo"
MV_PS = "Morvane Vorlan"
DM_PS = "Dravin Morvane"
MT_PS = "Morvane Telvo"

ONE_DOC = f"{ZQ} a signé le contrat."
TITLE_DOC = f"{TITLED} a signé le contrat."
TWO_DOC = f"{ZQ} et {ZM} ont signé le contrat."
LONE_DOC = "Zorbal a signé le contrat."
LONE_FIRST_DOC = f"Zorbal a signé le contrat. {ZQ} a signé le contrat."
PLACE_DOC = f"{PLACE} a signé le contrat."
ORG_DOC = f"{ORG_NAME} a signé le contrat."
VM_DOC = f"{VM} a signé le contrat."
CUSTOM_DOC = f"{ZQ} et {VM} ont signé le contrat."
ADDED_DOC = f"{ZQ} et Mme Brontel ont signé le contrat."
WORD_DOC = f"{ZQ} a signé le contrat avec Brontel."

STANDALONE = "Standalone component without full name context"

WRITTEN = (
    "Story 11.5 tests first: the review list shows a pseudonym that is not written"
)
DOCUMENT = "Story 11.5 tests first: the review list shows a name of the document"


# --- The library's draw -----------------------------------------------------


class _Draws:
    """The library's ``secrets``: ``choice`` returns ``seq[0]``, ``seq[1]``...
    in order, one counter per list, keyed by the list's contents (never by
    identity: the first-name list of a name of no known gender is built again
    on every call, and every ``load_library`` builds new lists). Thread-safe:
    the desktop workers and Story 10.22's threads draw too."""

    def __init__(self) -> None:
        import threading

        self._lock = threading.Lock()
        self._count: dict[tuple[Any, ...], int] = {}

    def choice(self, seq: Sequence[Any]) -> Any:
        key = tuple(seq)
        with self._lock:
            k = self._count.get(key, 0)
            self._count[key] = k + 1
        return seq[k % len(seq)]


def install_draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    """The draw stand-in, for the whole test (the review's draws and the
    end's share its counters)."""
    stand_in = _Draws()
    monkeypatch.setattr(library_module, "secrets", stand_in)
    return stand_in


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


@contextmanager
def _last_name_first(value: str) -> Iterator[None]:
    """Every library loaded puts ``value`` first in its last names, so the
    stand-in's first last-name draw is it and the next one is the library's
    own first last name."""
    real = LibraryBasedPseudonymManager.load_library

    def load(self: Any, theme: str) -> None:
        real(self, theme)
        self.last_names = [value] + [v for v in self.last_names if v != value]

    with patch.object(LibraryBasedPseudonymManager, "load_library", load):
        yield


def _library(theme: str = "neutral") -> LibraryBasedPseudonymManager:
    manager = LibraryBasedPseudonymManager()
    manager.load_library(theme)
    return manager


def _first_names(theme: str = "neutral") -> list[str]:
    library = _library(theme)
    return (
        library.first_names["male"]
        + library.first_names["female"]
        + library.first_names["neutral"]
    )


def _places(theme: str = "neutral") -> list[str]:
    library = _library(theme)
    return library._flatten_location_list(library.locations)


def _organisations(theme: str = "neutral") -> list[str]:
    library = _library(theme)
    return library._flatten_organization_list(library.organizations)


def _is_person_draw(value: str, theme: str = "neutral") -> bool:
    """A two-part person pseudonym from the ``theme`` library's lists."""
    words = value.split(" ", 1)
    return (
        len(words) == 2
        and words[0] in _first_names(theme)
        and words[1] in _library(theme).last_names
    )


# --- The new interfaces, reached on the unfixed code too --------------------


@dataclass(frozen=True)
class _LocalProposal:
    """The fields of Fix design B.1's ``PseudonymProposal``, for the unfixed
    code (where that type does not exist yet)."""

    entity_type: str
    theme: str
    pseudonym_full: str
    pseudonym_first: str | None
    pseudonym_last: str | None
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


def _proposal(
    entity_type: str,
    pseudonym_full: str,
    theme: str = "neutral",
    lone: bool = False,
) -> Any:
    """A pseudonym the review showed: a person's is split at its space; a
    lone name's carries the draw's ambiguity flag."""
    first: str | None = None
    last: str | None = None
    if entity_type == PERSON:
        if theme == "neutral_id":
            first, last = f"{pseudonym_full}-P", f"{pseudonym_full}-N"
        else:
            first, last = pseudonym_full.split(" ", 1)
    cls = getattr(processor_module, "PseudonymProposal", None) or _LocalProposal
    return cls(
        entity_type=entity_type,
        theme=theme,
        pseudonym_full=pseudonym_full,
        pseudonym_first=first,
        pseudonym_last=last,
        is_ambiguous=lone,
        ambiguity_reason=STANDALONE if lone else None,
    )


def _changed(result: Any) -> list[tuple[str, str, str, str]] | None:
    """``pseudonyms_changed`` as (name, type, shown, written) tuples; None
    when the result has none (the unfixed code)."""
    value = getattr(result, "pseudonyms_changed", None)
    if value is None:
        return None
    return [(c.name, c.entity_type, c.shown, c.written) for c in value]


def _finalize(
    db: str,
    text: str,
    entities: list[DetectedEntity],
    output: Path,
    proposals: Mapping[tuple[str, str], list[Any]] | None = None,
    custom: dict[tuple[str, str], str] | None = None,
    theme: str = "neutral",
) -> ProcessingResult:
    """``finalize_document`` (the desktop path) with the pseudonyms shown,
    passed only when it takes them."""
    kwargs: dict[str, Any] = {}
    if custom:
        kwargs["custom_pseudonyms"] = custom
    takes = (
        "proposals" in inspect.signature(DocumentProcessor.finalize_document).parameters
    )
    if proposals is not None and takes:
        kwargs["proposals"] = proposals
    result = DocumentProcessor(
        db_path=db, passphrase=PASSPHRASE, theme=theme
    ).finalize_document(text, entities, str(output), **kwargs)
    pre(result.success, f"written: {result.error_message}")
    return result


def _refresh(
    db: str,
    text: str,
    names: list[tuple[str, str]],
    customs: dict[tuple[str, str], str],
    proposals: dict[tuple[str, str], Any],
    theme: str = "neutral",
) -> dict[tuple[str, str], Any]:
    """``refresh_review_proposals`` (Fix design B.8), or ``{}`` where it does
    not exist."""
    processor = DocumentProcessor(db_path=db, passphrase=PASSPHRASE, theme=theme)
    method: Callable[..., Any] | None = getattr(
        processor, "refresh_review_proposals", None
    )
    if method is None:
        return {}
    return dict(
        method(document_text=text, names=names, customs=customs, proposals=proposals)
    )


# --- Documents, rows, outputs -----------------------------------------------


def _key(name: str, entity_type: str) -> tuple[str, str]:
    return (mapping_key(name, entity_type), entity_type)


def _saved(db: str) -> list[Entity]:
    with open_database(db, PASSPHRASE) as session:
        return list(SQLiteMappingRepository(session).find_all())


def _row(db: str, name: str, entity_type: str) -> Entity:
    """The saved row of (mapping key of ``name``, type); PRE that it exists."""
    with open_database(db, PASSPHRASE) as session:
        row = SQLiteMappingRepository(session).find_by_full_name_and_type(
            mapping_key(name, entity_type), entity_type
        )
    if row is None:
        pytest.fail(f"PRE: a saved row for {name!r} ({entity_type})")
    return row


def _store(
    db: str,
    name: str,
    entity_type: str,
    pseudonym: str,
    first: str | None = None,
    last: str | None = None,
) -> None:
    """A row saved by an earlier document: a person's with its parts."""
    pseudonym_first = pseudonym_last = None
    if entity_type == PERSON:
        pseudonym_first, pseudonym_last = pseudonym.split(" ", 1)
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type=entity_type,
                full_name=name,
                first_name=first,
                last_name=last,
                pseudonym_full=pseudonym,
                pseudonym_first=pseudonym_first,
                pseudonym_last=pseudonym_last,
                theme="neutral",
            )
        )


def _written(output: Path, source: str, names: list[tuple[str, str]]) -> list[str]:
    """The string written at each place of ``names`` (in place order)."""
    pre(output.exists(), f"output written: {output}")
    return _replacements(
        output.read_text(encoding="utf-8"), source, _spans(source, names)
    )


def _cell(output: Path) -> str:
    """The one text cell of a ``.csv`` output (header « nom »)."""
    pre(output.exists(), f"output written: {output}")
    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.reader(handle) if row]
    pre(len(rows) == 2 and len(rows[1]) == 1, f"one text cell: {rows}")
    return rows[1][0]


@dataclass
class _Review:
    """One command-line run: the pseudonym each group showed (by entity
    text, first time shown), the result and the output path."""

    shown: dict[str, str]
    result: ProcessingResult
    output: Path


def _cli(
    tmp_path: Path,
    db: str,
    text: str,
    names: list[tuple[str, str]],
    suffix: str = ".txt",
    theme: str = "neutral",
) -> _Review:
    """``process_document`` with its interactive review, every group
    confirmed. A ``.csv`` holds one header cell « nom » and one cell of
    text."""
    source = tmp_path / f"doc{suffix}"
    if suffix == ".csv":
        source.write_text(f"nom\n{text}\n", encoding="utf-8")
    else:
        source.write_text(text, encoding="utf-8")
    output = tmp_path / f"doc_out{suffix}"
    shown: dict[str, str] = {}
    original = ReviewScreen.display_entity

    def display(
        self: Any,
        entity: DetectedEntity,
        context: str,
        pseudonym: str,
        *a: Any,
        **k: Any,
    ) -> Any:
        shown.setdefault(entity.text, pseudonym)
        return original(self, entity, context, pseudonym, *a, **k)

    with (
        _detection(names),
        patch.object(ReviewScreen, "display_entity", display),
        patch("gdpr_pseudonymizer.validation.ui.readchar.readkey", return_value="\r"),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_user_action",
            side_effect=["confirm"] * 20,
        ),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True
        ),
    ):
        result = DocumentProcessor(
            db_path=db, passphrase=PASSPHRASE, theme=theme
        ).process_document(str(source), str(output))
    pre(result.success, f"written: {result.error_message}")
    for name, _ in names:
        pre(name in shown, f"{name!r} shown in the review")
    return _Review(shown, result, output)


def _untitled(shown: str) -> str:
    return shown.removeprefix("Mme ")


# --- T1, T2: the command line writes what its review shows -------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
@pytest.mark.parametrize("case", ["one_name", "title", "two_people_one_first_name"])
def test_cli_review_writes_what_it_shows(
    tmp_path: Path, draws: _Draws, case: str
) -> None:
    """T1 (AC1): each place carries the pseudonym its group showed (title
    included), and the saved row holds it."""
    db = _new_db(tmp_path)
    text, names = {
        "one_name": (ONE_DOC, [(ZQ, PERSON)]),
        "title": (TITLE_DOC, [(TITLED, PERSON)]),
        "two_people_one_first_name": (TWO_DOC, [(ZQ, PERSON), (ZM, PERSON)]),
    }[case]
    review = _cli(tmp_path, db, text, names)
    shown = [review.shown[name] for name, _ in names]
    written = _written(review.output, text, names)
    assert written == shown  # expected failure
    saved = [_row(db, name, etype).pseudonym_full for name, etype in names]
    assert saved == [_untitled(value) for value in shown]
    assert _changed(review.result) == []


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_cli_spreadsheet_review_writes_what_it_shows(
    tmp_path: Path, draws: _Draws
) -> None:
    """T2 (AC2): a ``.csv`` cell carries the pseudonym its group showed."""
    db = _new_db(tmp_path)
    review = _cli(tmp_path, db, ONE_DOC, [(ZQ, PERSON)], suffix=".csv")
    shown = [review.shown[ZQ]]
    cell = _cell(review.output)
    written = _replacements(cell, ONE_DOC, _spans(ONE_DOC, [(ZQ, PERSON)]))
    assert written == shown  # expected failure
    assert _changed(review.result) == []


# --- T3: a free proposal is kept --------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
@pytest.mark.parametrize(
    "case",
    [
        "person",
        "place",
        "organisation",
        "lone_first_name",
        "neutral_id",
        "lone_first_name_before_full_name",
    ],
)
def test_free_proposal_is_kept(tmp_path: Path, draws: _Draws, case: str) -> None:
    """T3 (AC5): a pseudonym shown and still free is written and saved with
    its parts and the processor's theme; nothing is reported."""
    db = _new_db(tmp_path)
    theme = "neutral_id" if case == "neutral_id" else "neutral"
    if case == "lone_first_name_before_full_name":
        names = [("Zorbal", PERSON), (ZQ, PERSON)]
        proposals = {
            _key("Zorbal", PERSON): [_proposal(PERSON, DB_PS, lone=True)],
            _key(ZQ, PERSON): [_proposal(PERSON, DT_PS)],
        }
        entities = _found(LONE_FIRST_DOC, names)
        pre(len(entities) == 2, f"the lone name and the full name: {entities}")
        result = _finalize(
            db, LONE_FIRST_DOC, entities, tmp_path / "out.txt", proposals
        )
        changed = _changed(result)
        assert changed == []  # expected failure
        written = _written(tmp_path / "out.txt", LONE_FIRST_DOC, names)
        assert written == [DB_PS, DT_PS]
        assert sorted(row.pseudonym_full for row in _saved(db)) == [DB_PS, DT_PS]
        return
    text, name, etype, value, lone = {
        "person": (ONE_DOC, ZQ, PERSON, DB_PS, False),
        "place": (PLACE_DOC, PLACE, LOCATION, _places()[1], False),
        "organisation": (ORG_DOC, ORG_NAME, ORG, _organisations()[1], False),
        "lone_first_name": (LONE_DOC, "Zorbal", PERSON, DB_PS, True),
        "neutral_id": (ONE_DOC, ZQ, PERSON, "PER-003", False),
    }[case]
    proposal = _proposal(etype, value, theme=theme, lone=lone)
    names = [(name, etype)]
    result = _finalize(
        db,
        text,
        _found(text, names),
        tmp_path / "out.txt",
        {_key(name, etype): [proposal]},
        theme=theme,
    )
    written = _written(tmp_path / "out.txt", text, names)
    assert written == [value]  # expected failure
    rows = _saved(db)
    assert [
        (r.pseudonym_full, r.pseudonym_first, r.pseudonym_last, r.theme) for r in rows
    ] == [(value, proposal.pseudonym_first, proposal.pseudonym_last, theme)]
    assert _changed(result) == []
    if case == "neutral_id":
        _finalize(
            db,
            VM_DOC,
            _found(VM_DOC, [(VM, PERSON)]),
            tmp_path / "later.txt",
            theme=theme,
        )
        assert _row(db, VM, PERSON).pseudonym_full == "PER-004"


# --- T4-T11, T18, T19: not free at the end, drawn again and reported --------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_proposal_given_to_another_name_since_the_review(
    tmp_path: Path, draws: _Draws
) -> None:
    """T4 (AC5, AC6): another document gave the pseudonym shown to another
    name meanwhile: drawn again, reported."""
    db = _new_db(tmp_path)
    _finalize(
        db,
        ONE_DOC,
        _found(ONE_DOC, [(ZQ, PERSON)]),
        tmp_path / "a.txt",
        {_key(ZQ, PERSON): [_proposal(PERSON, DB_PS)]},
    )
    names = [(VM, PERSON)]
    b = _finalize(
        db,
        VM_DOC,
        _found(VM_DOC, names),
        tmp_path / "b.txt",
        {_key(VM, PERSON): [_proposal(PERSON, DB_PS)]},
    )
    row_a, row_b = _row(db, ZQ, PERSON), _row(db, VM, PERSON)
    changed, expected = _changed(b), [(VM, PERSON, DB_PS, row_b.pseudonym_full)]
    assert changed == expected  # expected failure
    assert (
        row_b.pseudonym_full != row_a.pseudonym_full
        and row_b.pseudonym_first != row_a.pseudonym_first
        and row_b.pseudonym_last != row_a.pseudonym_last
    )
    assert _written(tmp_path / "b.txt", VM_DOC, names) == [row_b.pseudonym_full]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_name_saved_since_the_review_keeps_its_saved_pseudonym(
    tmp_path: Path, draws: _Draws
) -> None:
    """T5 (AC6): the name itself was saved meanwhile: its saved pseudonym is
    written, reported."""
    db = _new_db(tmp_path)
    _store(db, ZQ, PERSON, DB_PS, "Zorbal", "Quentrix")
    names = [(ZQ, PERSON)]
    b = _finalize(
        db,
        ONE_DOC,
        _found(ONE_DOC, names),
        tmp_path / "b.txt",
        {_key(ZQ, PERSON): [_proposal(PERSON, MV_PS)]},
    )
    changed = _changed(b)
    assert changed == [(ZQ, PERSON, MV_PS, DB_PS)]  # expected failure
    assert [row.full_name for row in _saved(db)] == [ZQ]
    assert _written(tmp_path / "b.txt", ONE_DOC, names) == [DB_PS]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_first_name_part_saved_since_the_review(tmp_path: Path, draws: _Draws) -> None:
    """T6 (AC5): the real first name got a part meanwhile: drawn again with
    that part, reported."""
    db = _new_db(tmp_path)
    _store(db, ZQ, PERSON, DB_PS, "Zorbal", "Quentrix")
    b = _finalize(
        db,
        f"{ZM} a signé le contrat.",
        _found(f"{ZM} a signé le contrat.", [(ZM, PERSON)]),
        tmp_path / "b.txt",
        {_key(ZM, PERSON): [_proposal(PERSON, MV_PS)]},
    )
    row = _row(db, ZM, PERSON)
    changed, expected = _changed(b), [(ZM, PERSON, MV_PS, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert row.pseudonym_first == "Dravin"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_proposal_of_another_type_of_the_same_text(
    tmp_path: Path, draws: _Draws
) -> None:
    """T7 (AC5, Story 10.7): the pseudonym shown is the same text's under
    another type: drawn again, reported."""
    db = _new_db(tmp_path)
    taken = _organisations()[1]
    _store(db, ORG_NAME, ORG, taken)
    b = _finalize(
        db,
        ORG_DOC,
        _found(ORG_DOC, [(ORG_NAME, LOCATION)]),
        tmp_path / "b.txt",
        {_key(ORG_NAME, LOCATION): [_proposal(LOCATION, taken)]},
    )
    row = _row(db, ORG_NAME, LOCATION)
    changed, expected = _changed(b), [(ORG_NAME, LOCATION, taken, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert row.pseudonym_full != taken


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_proposal_using_a_custom_value(tmp_path: Path, draws: _Draws) -> None:
    """T8 (AC5, Story 10.11 AC3): the pseudonym shown takes a value of
    another name's custom pseudonym: drawn again, reported."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), (VM, PERSON)]
    result = _finalize(
        db,
        CUSTOM_DOC,
        _found(CUSTOM_DOC, names),
        tmp_path / "out.txt",
        {_key(ZQ, PERSON): [_proposal(PERSON, DT_PS)]},
        custom={_key(VM, PERSON): DB_PS},
    )
    row = _row(db, ZQ, PERSON)
    changed, expected = _changed(result), [(ZQ, PERSON, DT_PS, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert row.pseudonym_first != "Dravin"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_proposal_part_is_a_real_name_at_the_end(tmp_path: Path, draws: _Draws) -> None:
    """T9 (AC6, AC8): a name sent at the end (added in the review) makes a
    part shown a real name of the document: drawn again, reported."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), ("Mme Brontel", PERSON)]
    entities = _found(ADDED_DOC, names)
    pre(len(entities) == 2, f"both names sent: {entities}")
    result = _finalize(
        db,
        ADDED_DOC,
        entities,
        tmp_path / "out.txt",
        {_key(ZQ, PERSON): [_proposal(PERSON, DB_PS)]},
    )
    row = _row(db, ZQ, PERSON)
    changed, expected = _changed(result), [(ZQ, PERSON, DB_PS, row.pseudonym_full)]
    assert changed == expected  # expected failure
    written = _written(tmp_path / "out.txt", ADDED_DOC, names)
    assert written[0].split(" ")[-1] != "Brontel"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_type_changed_since_the_preview(tmp_path: Path, draws: _Draws) -> None:
    """T10 (AC5, AC6): a pseudonym shown for another type (a CLI [T], or the
    end's backstop when the list could not update): drawn again, reported."""
    db = _new_db(tmp_path)
    result = _finalize(
        db,
        ORG_DOC,
        _found(ORG_DOC, [(ORG_NAME, ORG)]),
        tmp_path / "out.txt",
        {_key(ORG_NAME, ORG): [_proposal(PERSON, DB_PS)]},
    )
    row = _row(db, ORG_NAME, ORG)
    changed, expected = _changed(result), [(ORG_NAME, ORG, DB_PS, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert row.pseudonym_full in _organisations()


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_custom_pseudonym_on_a_name_sharing_the_first_name(
    tmp_path: Path, draws: _Draws
) -> None:
    """T11 (AC5, AC6; Story 10.11's one first name, one part): a custom
    pseudonym set on a name sharing the real first name (a CLI [C], or the
    end's backstop): the other name is drawn again with its part, reported."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), (ZM, PERSON)]
    result = _finalize(
        db,
        TWO_DOC,
        _found(TWO_DOC, names),
        tmp_path / "out.txt",
        {_key(ZM, PERSON): [_proposal(PERSON, MV_PS)]},
        custom={_key(ZQ, PERSON): DB_PS},
    )
    row = _row(db, ZM, PERSON)
    changed, expected = _changed(result), [(ZM, PERSON, MV_PS, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert row.pseudonym_first == "Dravin"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_proposal_part_saved_in_the_other_role(tmp_path: Path, draws: _Draws) -> None:
    """T18 (AC5; Story 11.6's other-role guard): a part shown is saved
    meanwhile as another name's part in the other role: drawn again,
    reported."""
    db = _new_db(tmp_path)
    _store(db, ZQ, PERSON, DM_PS, "Zorbal", "Quentrix")
    b = _finalize(
        db,
        VM_DOC,
        _found(VM_DOC, [(VM, PERSON)]),
        tmp_path / "b.txt",
        {_key(VM, PERSON): [_proposal(PERSON, MT_PS)]},
    )
    row = _row(db, VM, PERSON)
    changed, expected = _changed(b), [(VM, PERSON, MT_PS, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert (row.pseudonym_first or "").casefold() != "morvane"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
def test_proposal_of_another_theme(tmp_path: Path, draws: _Draws) -> None:
    """T19 (AC5): a pseudonym shown from another theme is never kept."""
    db = _new_db(tmp_path)
    neutral = f"{_first_names()[1]} {_library().last_names[1]}"
    result = _finalize(
        db,
        ONE_DOC,
        _found(ONE_DOC, [(ZQ, PERSON)]),
        tmp_path / "out.txt",
        {_key(ZQ, PERSON): [_proposal(PERSON, neutral)]},
        theme="star_wars",
    )
    row = _row(db, ZQ, PERSON)
    changed, expected = _changed(result), [(ZQ, PERSON, neutral, row.pseudonym_full)]
    assert changed == expected  # expected failure
    assert _is_person_draw(row.pseudonym_full, "star_wars")


# --- T27: the list never shows a name of the document ------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=DOCUMENT)
@pytest.mark.parametrize("case", ["cli_capitalised_word", "preview_own_last_name"])
def test_list_never_shows_a_name_of_the_document(
    tmp_path: Path, draws: _Draws, case: str
) -> None:
    """T27 (AC8): a value the real-name rule refuses is never shown; the
    library's next value is."""
    db = _new_db(tmp_path)
    forced = "Brontel" if case == "cli_capitalised_word" else "Quentrix"
    second = _library().last_names[0]
    with _last_name_first(forced):
        if case == "cli_capitalised_word":
            shown = _cli(tmp_path, db, WORD_DOC, [(ZQ, PERSON)]).shown[ZQ]
        else:
            entities = _found(ONE_DOC, [(ZQ, PERSON)])
            previews = DocumentProcessor(
                db_path=db, passphrase=PASSPHRASE
            ).build_pseudonym_previews(entities)
            pre(len(previews) == 1, f"one preview: {previews}")
            shown = next(iter(previews.values()))
    pre(len(shown.split(" ")) == 2, f"two parts shown: {shown!r}")
    assert shown.split(" ")[1] == second  # expected failure


# --- T38: the review's update (Fix design B.8) -------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=WRITTEN)
@pytest.mark.parametrize("case", ["retyped", "shared_first_name", "stored_since"])
def test_refresh_review_proposals(tmp_path: Path, draws: _Draws, case: str) -> None:
    """T38 (AC19): what the end would write now, for the names whose value
    changes."""
    db = _new_db(tmp_path)
    if case == "retyped":
        key = (PLACE, PERSON)
        refreshed = _refresh(
            db,
            PLACE_DOC,
            [key],
            {},
            {key: _proposal(LOCATION, _places()[1])},
        )
        assert list(refreshed) == [key]  # expected failure
        value = refreshed[key]
        assert value.entity_type == PERSON and _is_person_draw(value.pseudonym_full)
        parts = (value.pseudonym_first, value.pseudonym_last)
        assert parts == tuple(value.pseudonym_full.split(" ", 1))
    elif case == "shared_first_name":
        zq, zm = _key(ZQ, PERSON), _key(ZM, PERSON)
        refreshed = _refresh(
            db,
            TWO_DOC,
            [zq, zm],
            {zq: DB_PS},
            {zm: _proposal(PERSON, MV_PS)},
        )
        assert list(refreshed) == [zm]  # expected failure
        assert refreshed[zm].pseudonym_first == "Dravin"
    else:
        _store(db, ZQ, PERSON, DB_PS, "Zorbal", "Quentrix")
        zq = _key(ZQ, PERSON)
        refreshed = _refresh(db, ONE_DOC, [zq], {}, {zq: _proposal(PERSON, MV_PS)})
        assert refreshed == {zq: DB_PS}  # expected failure


# --- Controls (unmarked) ----------------------------------------------------


def test_no_proposal_unchanged(tmp_path: Path, draws: _Draws) -> None:
    """T12 (control): without proposals, as today: one row per name, the
    output carries the rows, nothing reported."""
    db = _new_db(tmp_path)
    text = f"{ZQ} et {PLACE} ont signé le contrat."
    names = [(ZQ, PERSON), (PLACE, LOCATION)]
    result = _finalize(db, text, _found(text, names), tmp_path / "out.txt")
    rows = [_row(db, name, etype).pseudonym_full for name, etype in names]
    assert _written(tmp_path / "out.txt", text, names) == rows
    assert len(_saved(db)) == 2
    assert _changed(result) in ([], None)


def test_refresh_keeps_a_free_proposal(tmp_path: Path, draws: _Draws) -> None:
    """T38c (control): a free proposal and no custom pseudonym: nothing
    changes."""
    db = _new_db(tmp_path)
    zq = _key(ZQ, PERSON)
    assert _refresh(db, ONE_DOC, [zq], {}, {zq: _proposal(PERSON, DB_PS)}) == {}


def test_preview_fallback_is_not_kept(tmp_path: Path, draws: _Draws) -> None:
    """T28 (control): when the review's draw fails, its placeholder is shown
    and the end draws as today; nothing is reported."""
    db = _new_db(tmp_path)
    real = CompositionalPseudonymEngine.assign_compositional_pseudonym
    calls = {"n": 0}

    def failing_once(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("library exhausted")
        return real(self, *args, **kwargs)

    with patch.object(
        CompositionalPseudonymEngine, "assign_compositional_pseudonym", failing_once
    ):
        review = _cli(tmp_path, db, ONE_DOC, [(ZQ, PERSON)])
    assert review.shown[ZQ] == "[PERSON_PREVIEW]"
    row = _row(db, ZQ, PERSON)
    assert _written(review.output, ONE_DOC, [(ZQ, PERSON)]) == [row.pseudonym_full]
    assert _changed(review.result) in ([], None)
