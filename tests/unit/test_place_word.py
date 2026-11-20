"""Story 13.1: a new place pseudonym fits the word before the place (W1-W7,
P1-P7, T-untaken, T-replace, T-cli-added, U1-U9; controls C1-C6).

Written by the BMAD dev agent (Claude), tests first. A resolve is
``DocumentProcessor._resolve_pseudonyms`` on a stand-in ``_ProcessingContext``
that holds a real manager loaded with the theme, a real
``CompositionalPseudonymEngine`` and a ``Mock`` mapping repository: it opens no
database, so a pool can be read by proposing each name of a theme in turn
(``_pool``: the names written as proposed, Story 11.5's ``proposals``). The
write paths reuse Story 11.5's, 11.6's and 11.7's helpers.

The library's draw is forced (``_offers``): each given name, in order, is
returned by the first ``secrets.choice`` whose list holds it; every other
choice is real. On the unfixed code every place is in one list, so the forced
name comes back; once a word's names are drawn first, it comes back only when
the names being drawn hold it.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict ``xfail(raises=AssertionError)`` never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names only: the library's own places are
read from the shipped files at run time, never written here. No spaCy model,
no Qt.
"""

from __future__ import annotations

import copy
import csv
import functools
import secrets
import unicodedata
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

import gdpr_pseudonymizer.pseudonym.library_manager as library_module
import gdpr_pseudonymizer.pseudonym.place_names as place_names_module
from gdpr_pseudonymizer.cli.commands.batch import _process_single_document_worker
from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    PseudonymProposal,
    _ProcessingContext,
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
from gdpr_pseudonymizer.utils.tabular_reader import read_csv_structured
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _new_db,
    _replacements,
    pre,
)
from tests.unit.test_parallel_saved_pseudonym import (
    _detection,
    _found,
    _output,
    _process,
    _settings,  # noqa: F401 (autouse: no settings file read or written)
    _spans,
)
from tests.unit.test_review_list_written_pseudonym import (
    _changed,
    _Draws,
    _finalize,
    _proposal,
    install_draws,
)
from tests.unit.test_review_list_written_pseudonym import _cli as _review_cli
from tests.unit.test_stored_pseudonym_own_word import _by_name, _replace

LOCATION, ORG = "LOCATION", "ORG"
THEME = "neutral"


# Invented places: consonant first (V, T, Z), vowel first (OS, AM, AU)
V = "Vellionie"
OS = "Ostrelle"
AM = "Ambrelie"
T = "Tarnevoux"
ZV = "Zorbaville"
AU = "Auvellion"
ZT = "Zorbtech"

EN_TEXT = "L'usine est en Vellionie."
AU_TEXT = "Elle part au Tarnevoux."

# W1: (text, the span detected, the names kept)
W1: dict[str, tuple[str, str, int]] = {
    "a": ("Le contrat a été signé à Vellionie.", V, 48),
    "a_capital": ("À Vellionie, le contrat a été signé.", V, 48),
    "a_unaccented": ("A Vellionie, le contrat a été signé.", V, 48),
    "en": (EN_TEXT, V, 14),
    "en_capital": ("En Vellionie, le contrat a été signé.", V, 14),
    "de": ("Le directeur de Vellionie a signé.", V, 49),
    "d_apostrophe": ("Le bureau d'Ostrelle ferme.", OS, 13),
    "d_typographic": ("Le bureau d’Ostrelle ferme.", OS, 13),
    "au": (AU_TEXT, T, 19),
    "du": ("Le directeur du Tarnevoux a signé.", T, 19),
    "in_span": (EN_TEXT, f"en {V}", 14),
    "no_word": ("Vellionie a signé le contrat.", V, 83),
    "other_word": ("Le bureau Vellionie a signé le contrat.", V, 83),
    "lowercase_a": ("Zorbtech a Vellionie pour site.", V, 83),
    "la": ("Le directeur de la Vellionie a signé.", V, 83),
    "line_break": ("Le contrat a été signé à\nVellionie.", V, 48),
    "span_starts_like_au": ("Le contrat a été signé à Auvellion.", AU, 48),
}

# U1-U9's sentences (W7 reads three of them)
U_LA = "Le directeur de la Vellionie a signé."
U_L = "Le directeur de l'Ambrelie a signé."
U_LE = "Elle travaille pour le Tarnevoux."

# L4: which lists of a theme play the city and the region
_CITY_LIKE = {"star_wars": ("cities",), "lotr": ("cities", "planets")}
_REGION_LIKE = {"star_wars": ("planets", "regions"), "lotr": ("regions",)}


# ---------------------------------------------------------------------------
# The library, read at run time
# ---------------------------------------------------------------------------


@functools.cache
def _loaded(theme: str) -> LibraryBasedPseudonymManager:
    """The theme's manager as loaded (copied before each use)."""
    manager = LibraryBasedPseudonymManager()
    manager.load_library(theme)
    return manager


def _list(theme: str, key: str) -> list[str]:
    """One place list of the shipped theme (empty if it has no such key)."""
    values: list[str] = dict(_loaded(theme).locations).get(key) or []
    return list(values)


def _places(theme: str) -> list[str]:
    manager = _loaded(theme)
    return list(manager._flatten_location_list(manager.locations))


def _lists(theme: str, keys: Sequence[str]) -> list[str]:
    return [name for key in keys for name in _list(theme, key)]


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.replace("’", "'"))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _vowel(name: str) -> bool:
    """L5: « a », « e », « i », « o », « u » (accents ignored) are vowels;
    « h » a consonant; « y » a vowel before a consonant, a consonant before
    a vowel."""
    folded = _fold(name)
    if not folded:
        return False
    if folded[0] == "y":
        return len(folded) > 1 and folded[1] not in "aeiouy"
    return folded[0] in "aeiou"


def _article(name: str) -> bool:
    """L1: the name starts with « Le », « La », « Les », « L' » or « The »
    followed by a word."""
    folded = _fold(name)
    return folded.startswith(("le ", "la ", "les ", "l'", "the "))


def _first(values: Sequence[str], vowel: bool | None = None) -> str:
    """The first name of ``values`` without an article (of that letter
    class, when given)."""
    for value in values:
        if _article(value):
            continue
        if vowel is None or _vowel(value) == vowel:
            return value
    pytest.fail(f"PRE: a name of that kind in {values[:3]!r}...")


# ---------------------------------------------------------------------------
# The forced draw
# ---------------------------------------------------------------------------


class _Offer:
    """The library's ``secrets``: each pending name, in order, is returned by
    the first ``choice(seq)`` whose ``seq`` holds it; every other call is the
    real ``secrets.choice``."""

    def __init__(self, names: Sequence[str]) -> None:
        self.pending = list(names)
        self.n = 0

    def choice(self, seq: Sequence[Any]) -> Any:
        if self.pending and self.pending[0] in seq:
            self.n += 1
            return self.pending.pop(0)
        return secrets.choice(seq)


@contextmanager
def _offers(names: Sequence[str] = ()) -> Iterator[_Offer]:
    """``names`` forced, in order (none: every draw real, whatever stand-in
    a test installed)."""
    offer = _Offer(names)
    with patch.object(library_module, "secrets", offer):
        yield offer


# ---------------------------------------------------------------------------
# A resolve, and the names kept
# ---------------------------------------------------------------------------


def _context(manager: LibraryBasedPseudonymManager) -> _ProcessingContext:
    """A stand-in context: the real manager and engine, no database."""
    repo = Mock()
    repo.find_by_full_name_and_type.return_value = None
    repo.find_all_by_full_name.return_value = []
    repo.find_all.return_value = []
    return _ProcessingContext(
        mapping_repo=repo,
        audit_repo=Mock(),
        pseudonym_manager=manager,
        compositional_engine=CompositionalPseudonymEngine(
            pseudonym_manager=manager, mapping_repository=repo
        ),
    )


def _occurrences(text: str, span: str) -> list[DetectedEntity]:
    found = _found(text, [(span, LOCATION)])
    pre(bool(found), f"{span!r} in {text!r}")
    return found


def _resolve(
    theme: str,
    text: str,
    span: str,
    *,
    used: Sequence[str] = (),
    forced: Sequence[str] = (),
    proposals: dict[tuple[str, str], list[Any]] | None = None,
    reverse: bool = False,
) -> list[str]:
    """The value written at each place of ``span`` in ``text`` (in text
    order), without the prefix kept in front of it."""
    manager = copy.deepcopy(_loaded(theme))
    manager._used_pseudonyms.update(used)
    ctx = _context(manager)
    entities = _occurrences(text, span)
    sent = list(reversed(entities)) if reverse else list(entities)
    processor = DocumentProcessor(
        db_path="not-opened.db", passphrase=PASSPHRASE, theme=theme
    )
    with _offers(forced):
        result = processor._resolve_pseudonyms(
            ctx, sent, document_text=text, proposals=proposals
        )
    by_span = {(start, end): value for start, end, value in result.replacements}
    written: list[str] = []
    for entity in entities:
        value = by_span.get((entity.start_pos, entity.end_pos))
        if value is None:
            pytest.fail(f"PRE: a value written at {entity.start_pos}")
        prefix = processor._compute_replacement_prefix(ctx, entity)
        pre(value.startswith(prefix), f"prefix {prefix!r} kept")
        written.append(value[len(prefix) :])
    return written


def _one(theme: str, text: str, span: str, **kwargs: Any) -> str:
    """The one value written at every place of ``span``."""
    written = _resolve(theme, text, span, **kwargs)
    pre(len(set(written)) == 1, f"one pseudonym per place: {written}")
    return written[0]


@functools.cache
def _pool(theme: str, text: str, span: str, reverse: bool = False) -> frozenset[str]:
    """The names of the theme a review proposal keeps for ``span`` in
    ``text``: each place name proposed in turn, in a fresh context, with
    every draw real."""
    key = (mapping_key(span, LOCATION), LOCATION)
    kept: set[str] = set()
    for name in _places(theme):
        proposal = PseudonymProposal(
            entity_type=LOCATION,
            theme=theme,
            pseudonym_full=name,
            pseudonym_first=None,
            pseudonym_last=None,
        )
        written = _resolve(
            theme, text, span, proposals={key: [proposal]}, reverse=reverse
        )
        if all(value == name for value in written):
            kept.add(name)
    return frozenset(kept)


def _kept(theme: str, text: str, span: str, reverse: bool = False) -> int:
    return len(_pool(theme, text, span, reverse))


def _en_names() -> frozenset[str]:
    """The names kept after « en » (a feminine region, by W1)."""
    return _pool(THEME, EN_TEXT, V)


def _du_names() -> frozenset[str]:
    """The names kept after « au » (a masculine region, by W1)."""
    return _pool(THEME, AU_TEXT, T)


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


# ---------------------------------------------------------------------------
# W1-W3: the word read, the occurrence that sets it, the theme's pools
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", list(W1))
def test_word_read(case: str) -> None:
    """W1 (AC1, AC2): the names a place can get after each word, as read
    before the place, in its span, with capitals, « d’ », a lone « A », a
    line break, and a span that only starts with the letters of « au »."""
    text, span, expected = W1[case]
    kept = _kept(THEME, text, span)
    assert kept == expected, f"{case}: {kept} names kept"  # expected failure


W2: dict[str, tuple[str, bool, int]] = {
    "later_listed": (
        "Le bureau Vellionie a signé ; l'usine est en Vellionie.",
        False,
        14,
    ),
    "document_order": (
        "L'usine est en Vellionie ; le bureau à Vellionie ferme.",
        True,
        14,
    ),
    "first_listed_wins": (
        "Le bureau à Vellionie ferme ; l'usine est en Vellionie.",
        False,
        48,
    ),
    "epic_beats_q4": (
        "La Région Vellionie a signé ; l'usine est en Vellionie.",
        False,
        14,
    ),
}


@pytest.mark.parametrize("case", list(W2))
def test_first_occurrence_sets_the_word(case: str) -> None:
    """W2 (AC1, AC3): one word per place, in document order: the first
    occurrence's epic word, else a later one's; an epic word beats a Q4
    word. ``document_order`` sends the later occurrence first."""
    text, reverse, expected = W2[case]
    kept = _kept(THEME, text, V, reverse)
    assert kept == expected, f"{case}: {kept} names kept"  # expected failure


W3: dict[str, int] = {
    "star_wars-a": 30,
    "star_wars-en": 50,
    "star_wars-de": 63,
    "star_wars-d_apostrophe": 17,
    "star_wars-au": 38,
    "lotr-a": 50,
    "lotr-en": 29,
    "lotr-de": 58,
    "lotr-d_apostrophe": 21,
    "lotr-au": 19,
    "lotr-no_word": 79,
}


@pytest.mark.parametrize("case", list(W3))
def test_pool_size(case: str) -> None:
    """W3 (AC1, AC8): Pool sizes for `star_wars` and `lotr` (after « du » or
    « au », names starting with a consonant only: L4, the PO's note)."""
    theme, word = case.split("-", 1)
    text, span, _ = W1[word]
    kept = _kept(theme, text, span)
    assert kept == W3[case], f"{case}: {kept} names kept"  # expected failure


# ---------------------------------------------------------------------------
# W4-W7: letter class, used-up words, names with an article, themes
# ---------------------------------------------------------------------------


def _w4(case: str) -> tuple[str, str, str, bool, frozenset[str]]:
    """(text, real place, forced name, vowel expected, names allowed)."""
    cities = _list(THEME, "cities")
    countries = _list(THEME, "countries")
    return {
        "a-vowel": (
            f"Le contrat a été signé à {OS}.",
            OS,
            _first(cities, vowel=False),
            True,
            frozenset(cities),
        ),
        "a-consonant": (
            f"Le contrat a été signé à {V}.",
            V,
            _first(cities, vowel=True),
            False,
            frozenset(cities),
        ),
        "en-vowel": (
            f"L'usine est en {AM}.",
            AM,
            _first(countries, vowel=False),
            True,
            _en_names(),
        ),
        "en-consonant": (
            EN_TEXT,
            V,
            _first(countries, vowel=True),
            False,
            _en_names(),
        ),
        "none-vowel": (
            f"{OS} a signé le contrat.",
            OS,
            _first(cities, vowel=False),
            True,
            frozenset(cities),
        ),
        "none-consonant": (
            f"{V} a signé le contrat.",
            V,
            _first(cities, vowel=True),
            False,
            frozenset(cities),
        ),
    }[case]


@pytest.mark.parametrize(
    "case",
    [
        "a-vowel",
        "a-consonant",
        "en-vowel",
        "en-consonant",
        "none-vowel",
        "none-consonant",
    ],
)
def test_same_letter_first(case: str) -> None:
    """W4 (AC1): within a word, names of the real place's letter class come
    first; the name of the other class offered first is not taken."""
    text, real, forced, vowel, allowed = _w4(case)
    written = _one(THEME, text, real, forced=[forced])
    assert _vowel(written) == vowel, written  # expected failure
    assert written in allowed, written


@pytest.mark.parametrize(
    "case",
    ["de_regions_next", "d_regions_next", "a_used_up", "en_used_up", "du_used_up"],
)
def test_no_free_name(case: str) -> None:
    """W5 (AC1, AC2): « de » and « d' » fall back from cities to feminine
    regions of their letter class; once a word's names are used up, the
    place gets ``Location-001``, never another word's names."""
    cities = _list(THEME, "cities")
    countries = _list(THEME, "countries")
    consonant_cities = [c for c in cities if not _article(c) and not _vowel(c)]
    vowel_cities = [c for c in cities if _vowel(c)]
    text, real, used, forced = {
        "de_regions_next": (
            W1["de"][0],
            V,
            consonant_cities,
            _first(cities, vowel=True),
        ),
        "d_regions_next": (
            W1["d_apostrophe"][0],
            OS,
            vowel_cities,
            _first(cities, vowel=False),
        ),
        "a_used_up": (W1["a"][0], V, cities, _first(countries)),
        "en_used_up": (EN_TEXT, V, countries, _first(cities)),
        "du_used_up": (W1["du"][0], T, countries, _first(cities)),
    }[case]
    written = _one(THEME, text, real, used=used, forced=[forced])
    if case == "de_regions_next":
        assert written in countries and not _vowel(written), written  # expected failure
    elif case == "d_regions_next":
        assert written in countries and _vowel(written), written  # expected failure
    else:
        assert written == "Location-001", written  # expected failure


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 13.1 PERF-131-01 tests first: a used-up place draw rebuilds "
        "its tiers on every attempt"
    ),
)
@pytest.mark.parametrize("word", ["no_word", "a"])
def test_used_up_draw_builds_its_tiers_once(word: str) -> None:
    """W8 (QA's PERF-131-01): a place draw whose names are all used builds
    the word's tiers once, not once per attempt. The work is counted (each
    ``draw_tiers`` call, ``fits``' own included), never timed: a timing test
    fails on a slow runner (Story 11.8)."""
    manager = copy.deepcopy(_loaded(THEME))
    manager._used_pseudonyms.update(_places(THEME))
    place_word = {"no_word": None, "a": place_names_module.A}[word]
    real = place_names_module.draw_tiers
    builds = {"n": 0}

    def counting(*args: Any, **kwargs: Any) -> list[list[str]]:
        builds["n"] += 1
        return real(*args, **kwargs)

    with (
        patch.object(place_names_module, "draw_tiers", counting),
        patch.object(library_module, "draw_tiers", counting),
        _offers(()),
    ):
        value = manager.assign_pseudonym(
            LOCATION, place_word=place_word, real_place=V
        ).pseudonym_full
    pre(value == "Location-001", f"the fallback name written: {value!r}")
    assert (
        builds["n"] <= 1
    ), f"{builds['n']} tier builds for one draw"  # expected failure


def test_article_name_never_drawn() -> None:
    """W6 (AC2, L1): a name that starts with an article is never drawn, even
    offered first."""
    text = f"{V} a signé le contrat."
    with_article = [name for name in _places(THEME) if _article(name)]
    pre(len(with_article) == 12, f"12 names with an article: {len(with_article)}")
    written = [_one(THEME, text, V, forced=[name]) for name in with_article]
    drawn = [value for value in written if _article(value)]
    assert drawn == [], drawn  # expected failure


def _w7(
    case: str,
) -> tuple[str, str, str, Sequence[str], str, bool, bool | None]:
    """(theme, text, real place, used names, forced name, whether the
    written name must be city-like (else region-like), and its letter class
    when checked: False is consonant-first)."""
    theme, word = case.split("-", 1)
    region_like = _lists(theme, _REGION_LIKE[theme])
    vowel_regions = [name for name in region_like if _vowel(name)]
    consonant_regions = [name for name in region_like if not _vowel(name)]
    first_region = _first(_list(theme, "regions"))
    first_city = _first(_list(theme, "cities"))
    rows: dict[str, tuple[str, str, Sequence[str], str, str]] = {
        "a": (W1["a"][0], V, (), first_region, "city"),
        "en": (EN_TEXT, V, (), first_city, "region"),
        "la": (U_LA, V, (), first_city, "region"),
        "le": (U_LE, T, (), first_city, "region"),
        "l_used_up": (U_L, AM, vowel_regions, _first(region_like, vowel=False), "city"),
        "la_used_up": (
            U_LA,
            V,
            consonant_regions,
            _first(region_like, vowel=True),
            "city",
        ),
    }
    text, real, used, forced, role = rows[word]
    vowel = False if word in ("la", "le") else None
    return theme, text, real, used, forced, role == "city", vowel


@pytest.mark.parametrize(
    "case",
    [
        "star_wars-a",
        "lotr-a",
        "star_wars-en",
        "lotr-en",
        "star_wars-la",
        "lotr-le",
        "star_wars-l_used_up",
        "lotr-la_used_up",
    ],
)
def test_theme_roles(case: str) -> None:
    """W7 (AC1, L3b, L4): a theme's city-like names follow « à », its
    region-like names « en » and Q4's words (« le », « la » consonant-first:
    R2); once an article's own names are used up, the no-word row follows,
    never a region-like name of the other letter class."""
    theme, text, real, used, forced, city, vowel = _w7(case)
    written = _one(theme, text, real, used=used, forced=[forced])
    keys = _CITY_LIKE[theme] if city else _REGION_LIKE[theme]
    assert written in _lists(theme, keys), written  # expected failure
    if vowel is not None:
        assert _vowel(written) == vowel, written


# ---------------------------------------------------------------------------
# P1-P7: every path passes the word
# ---------------------------------------------------------------------------


def _stored_place(db: str, name: str) -> str | None:
    with open_database(db, PASSPHRASE) as session:
        row = SQLiteMappingRepository(session).find_by_full_name_and_type(
            mapping_key(name, LOCATION), LOCATION
        )
    return None if row is None else row.pseudonym_full


def _csv_cells(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.reader(handle) if row]


def _write_two_cells(path: Path) -> None:
    """A spreadsheet of two cells, one per row: « Zorbtech a signé le
    contrat », then « L'usine est en Vellionie. »; PRE that the reader
    gives them so, and that the joined text at the place's cell position
    reads inside « signé ». (The first cell has no full stop: with one in
    each row, the reader's delimiter guess takes the full stop.)"""
    first = f"{ZT} a signé le contrat"
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows([[first], [EN_TEXT]])
    cells = [cell.value for cell in read_csv_structured(str(path)).cells]
    pre(cells == [first, EN_TEXT], f"two cells: {cells}")
    joined = "\n".join(cells)
    start = EN_TEXT.find(V)
    word = joined.find("signé")
    pre(word < start < word + len("signé"), "the cell position reads inside a word")


def _path_written(
    tmp_path: Path, path: str, forced: str
) -> tuple[str, str | None, Any]:
    """(written place, stored pseudonym, extra): the review's shown value
    and the changes reported (``cli_review``), the changes reported
    (``review_proposal``), else None."""
    db = _new_db(tmp_path)
    names = [(V, LOCATION)]
    spans = _spans(EN_TEXT, names)
    extra: Any = None
    with _offers([forced]):
        if path == "finalize":
            output = tmp_path / "doc_out.txt"
            _finalize(db, EN_TEXT, _found(EN_TEXT, names), output)
            written = _replacements(output.read_text(encoding="utf-8"), EN_TEXT, spans)
        elif path == "cli_review":
            run = _review_cli(tmp_path, db, EN_TEXT, names)
            extra = (run.shown[V], _changed(run.result))
            written = _replacements(
                run.output.read_text(encoding="utf-8"), EN_TEXT, spans
            )
        elif path == "no_review":
            with _detection(names):
                result = _process(db, tmp_path, "doc", EN_TEXT)()
            pre(result.success, f"written: {result.error_message}")
            text = _output(tmp_path, "doc")
            pre(text is not None, "output written")
            written = _replacements(str(text), EN_TEXT, spans)
        elif path == "parallel_worker":
            source, output = tmp_path / "doc.txt", tmp_path / "doc_out.txt"
            source.write_text(EN_TEXT, encoding="utf-8")
            with _detection(names):
                outcome = _process_single_document_worker(
                    (str(source), str(output), db, PASSPHRASE, THEME, "spacy", None)
                )
            pre(outcome["success"], f"written: {outcome}")
            written = _replacements(output.read_text(encoding="utf-8"), EN_TEXT, spans)
        elif path in ("csv", "tabular_finalize"):
            source, output = tmp_path / "doc.csv", tmp_path / "doc_out.csv"
            _write_two_cells(source)
            processor = DocumentProcessor(
                db_path=db, passphrase=PASSPHRASE, theme=THEME
            )
            with _detection(names):
                if path == "csv":
                    result = processor.process_document(
                        str(source), str(output), skip_validation=True
                    )
                else:
                    tabular, found = processor.detect_entities_tabular(str(source))
                    result = processor.finalize_document_tabular(
                        tabular, found, str(output), str(source)
                    )
            pre(result.success, f"written: {result.error_message}")
            cells = _csv_cells(output)
            pre(len(cells) == 2 and len(cells[1]) == 1, f"two cells: {cells}")
            written = _replacements(cells[1][0], EN_TEXT, spans)
        else:
            output = tmp_path / "doc_out.txt"
            city = _first(_list(THEME, "cities"))
            result = _finalize(
                db,
                EN_TEXT,
                _found(EN_TEXT, names),
                output,
                proposals={(V, LOCATION): [_proposal(LOCATION, city)]},
            )
            extra = _changed(result)
            written = _replacements(output.read_text(encoding="utf-8"), EN_TEXT, spans)
    pre(len(written) == 1, f"one place written: {written}")
    return written[0], _stored_place(db, V), extra


@pytest.mark.parametrize(
    "path",
    [
        "finalize",
        "cli_review",
        "no_review",
        "parallel_worker",
        "csv",
        "tabular_finalize",
        "review_proposal",
    ],
)
def test_word_reaches_the_draw(tmp_path: Path, path: str) -> None:
    """P1-P7 (AC1, AC7): « L'usine est en Vellionie. » gets a feminine region
    on every path (the first city offered first is not taken); it is stored;
    the command-line review showed it; the city a review showed for it is
    reported as changed."""
    countries = _list(THEME, "countries")
    en_names = _en_names()
    city = _first(_list(THEME, "cities"))
    written, stored, extra = _path_written(tmp_path, path, city)
    assert written in countries and written in en_names, written  # expected failure
    assert stored == written
    if path == "cli_review":
        assert extra == (written, [])
    elif path == "review_proposal":
        assert extra == [(V, LOCATION, city, written)]


# ---------------------------------------------------------------------------
# T-untaken, T-replace, T-cli-added
# ---------------------------------------------------------------------------


def test_untaken_redraw_keeps_the_word() -> None:
    """T-untaken (AC1): the redraw for a value another type or a custom
    pseudonym holds keeps the place's word."""
    ctx = _context(copy.deepcopy(_loaded(THEME)))
    # The field exists after the fix; the unfixed code ignores the attribute
    setattr(ctx, "place_words", {(V, LOCATION): "en"})
    row = Entity(entity_type=LOCATION, full_name=V, pseudonym_full=V, theme=THEME)
    with _offers([_first(_list(THEME, "cities"))]):
        value, _ = DocumentProcessor._assign_untaken_pseudonym(ctx, row, set(), None)
    assert (
        value in _list(THEME, "countries") and value in _en_names()
    ), value  # expected failure


@contextmanager
def _ostrelle_a_city() -> Iterator[None]:
    """Every `neutral` library loaded holds « Ostrelle » at the end of its
    cities (an invented name is no library place; Story 11.7 reports a
    place word only when it is one)."""
    real = LibraryBasedPseudonymManager.load_library

    def load(self: Any, theme: str) -> None:
        real(self, theme)
        if theme == THEME and OS not in self.locations["cities"]:
            self.locations["cities"].append(OS)

    with patch.object(LibraryBasedPseudonymManager, "load_library", load):
        yield


def test_replace_flow_keeps_the_letter(tmp_path: Path) -> None:
    """T-replace (AC1): Story 11.7's replacement of a saved place draws as for
    no such word, ordered by the stored real place's first letter."""
    cities = _list(THEME, "cities")
    db = _new_db(tmp_path)
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(entity_type=LOCATION, full_name=OS, pseudonym_full=OS, theme=THEME)
        )
    with _ostrelle_a_city(), _offers([_first(cities, vowel=False)]):
        code, shown = _replace(db, "--all", "--force")
    pre(code == 0, f"replaced: {code} {shown}")
    new = _by_name(db)[OS].pseudonym_full
    pre(new != OS, "the own-word place replaced")
    assert _vowel(new), new  # expected failure
    assert new in cities, new


def test_cli_added_place_fits_the_word(tmp_path: Path) -> None:
    """T-cli-added (AC1, AC7): a place added by hand in the command-line
    review ([A], during the review of « Zorbtech ») is shown with a name of
    its own word, written and stored with it, and nothing is reported."""
    text = f"{ZT} a signé le contrat. {EN_TEXT}"
    names = [(ZT, ORG)]
    en_names = _en_names()
    db = _new_db(tmp_path)
    with _offers([_first(_list(THEME, "cities"))]):
        run = _review_cli(
            tmp_path,
            db,
            text,
            names,
            keys=["add"] + ["confirm"] * 19,
            typed=[V, LOCATION],
        )
    pre(V in run.shown, f"the place added by hand shown: {sorted(run.shown)}")
    shown = run.shown[V]
    spans = _spans(text, [(ZT, ORG), (V, LOCATION)])
    written = _replacements(run.output.read_text(encoding="utf-8"), text, spans)
    pre(len(written) == 2, f"two places written: {written}")
    assert (
        shown in _list(THEME, "countries") and shown in en_names
    ), shown  # expected failure
    assert written[1] == shown
    assert _stored_place(db, V) == shown
    assert _changed(run.result) == []


# ---------------------------------------------------------------------------
# U1-U9: the words the epic does not list (Lionel's Q4 (b), R1)
# ---------------------------------------------------------------------------


U: dict[str, tuple[str, str]] = {
    "la": (U_LA, V),
    "l": (U_L, AM),
    "le": (U_LE, T),
    "les": ("Elle travaille pour les Tarnevoux.", T),
    "region": ("La Région Vellionie a signé.", V),
    "region_later": ("Vellionie a signé le contrat. La Région Vellionie a signé.", V),
    "des": ("Le directeur des Tarnevoux a signé.", T),
    "aux": ("Elle part aux Tarnevoux.", T),
    "region_added": ("La Région Vellionie a signé.", V),
}


@pytest.mark.parametrize("case", list(U))
def test_unlisted_word(case: str) -> None:
    """U1-U9 (AC1, AC2): « la » a consonant-first feminine region, « l' » a
    vowel-first region, « le » a masculine region, « les », « des », « aux »
    a plural region, « région » a region (Q5's names included: R1)."""
    cities = _list(THEME, "cities")
    countries = _list(THEME, "countries")
    en_names, du_names = _en_names(), _du_names()
    text, real = U[case]
    forced = (
        _first(countries) if case in ("le", "les", "des", "aux") else _first(cities)
    )
    used = countries[:20] if case == "region_added" else []
    written = _one(THEME, text, real, used=used, forced=[forced])
    if case == "la":
        # In `countries` too: before the fix every name is kept after « en »,
        # so the « en » names alone would not see the forced city
        assert (  # expected failure
            written in countries and written in en_names and not _vowel(written)
        ), written
    elif case == "l":
        assert written in countries and _vowel(written), written  # expected failure
    elif case == "le":
        assert (
            written in du_names and written not in en_names
        ), written  # expected failure
    elif case in ("les", "des", "aux"):
        assert (  # expected failure
            written in countries and written not in en_names and written not in du_names
        ), written
    else:
        assert written in countries, written  # expected failure


# ---------------------------------------------------------------------------
# C1-C6: controls (pass before and after the fix)
# ---------------------------------------------------------------------------


def test_stored_place_reused_as_stored(tmp_path: Path) -> None:
    """C1 (AC6): a place saved with a district keeps it, though that name is
    no longer drawn and does not follow « à »."""
    district = _list(THEME, "regions")[0]
    db = _new_db(tmp_path)
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type=LOCATION,
                full_name=ZV,
                pseudonym_full=district,
                theme=THEME,
            )
        )
    text = f"Le contrat a été signé à {ZV}."
    names = [(ZV, LOCATION)]
    output = tmp_path / "doc_out.txt"
    _finalize(db, text, _found(text, names), output)
    written = _replacements(
        output.read_text(encoding="utf-8"), text, _spans(text, names)
    )
    assert written == [district]
    assert _stored_place(db, ZV) == district


def test_neutral_id_unchanged(tmp_path: Path) -> None:
    """C2 (AC1): `neutral_id` still writes « LOC-001 »."""
    db = _new_db(tmp_path)
    names = [(V, LOCATION)]
    output = tmp_path / "doc_out.txt"
    _finalize(db, EN_TEXT, _found(EN_TEXT, names), output, theme="neutral_id")
    written = _replacements(
        output.read_text(encoding="utf-8"), EN_TEXT, _spans(EN_TEXT, names)
    )
    assert written == ["LOC-001"]


def test_review_place_shown_is_written(tmp_path: Path) -> None:
    """C3 (AC7, Story 11.5): the place the command-line review shows is the
    one written and stored."""
    text = f"Le contrat a été signé à {ZV}."
    names = [(ZV, LOCATION)]
    db = _new_db(tmp_path)
    run = _review_cli(tmp_path, db, text, names)
    written = _replacements(
        run.output.read_text(encoding="utf-8"), text, _spans(text, names)
    )
    assert written == [run.shown[ZV]]
    assert _stored_place(db, ZV) == run.shown[ZV]
    assert _changed(run.result) == []


def test_fallback_name_still_kept(tmp_path: Path) -> None:
    """C4 (AC7): a fallback name the review showed is judged as today: kept,
    not reported."""
    db = _new_db(tmp_path)
    names = [(V, LOCATION)]
    output = tmp_path / "doc_out.txt"
    result = _finalize(
        db,
        EN_TEXT,
        _found(EN_TEXT, names),
        output,
        proposals={(V, LOCATION): [_proposal(LOCATION, "Location-001")]},
    )
    written = _replacements(
        output.read_text(encoding="utf-8"), EN_TEXT, _spans(EN_TEXT, names)
    )
    assert written == ["Location-001"]
    assert _changed(result) == []


def test_fitting_proposal_written_as_shown(tmp_path: Path, draws: _Draws) -> None:
    """C5 (AC7): a feminine region shown after « en » is written as shown and
    not reported."""
    region = _list(THEME, "countries")[1]
    db = _new_db(tmp_path)
    names = [(V, LOCATION)]
    output = tmp_path / "doc_out.txt"
    result = _finalize(
        db,
        EN_TEXT,
        _found(EN_TEXT, names),
        output,
        proposals={(V, LOCATION): [_proposal(LOCATION, region)]},
    )
    written = _replacements(
        output.read_text(encoding="utf-8"), EN_TEXT, _spans(EN_TEXT, names)
    )
    assert written == [region]
    assert _changed(result) == []


def test_unlisted_word_used_up_falls_back() -> None:
    """C6 (AC2, Q4 (b)): once every region is used, a place after « la » gets
    a city (the no-word row), never ``Location-NNN``."""
    used = _list(THEME, "countries") + _list(THEME, "regions")
    written = _one(THEME, U_LA, V, used=used)
    assert written in _list(THEME, "cities"), written
