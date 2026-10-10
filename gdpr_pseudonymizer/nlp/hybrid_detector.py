"""
Hybrid Entity Detector combining spaCy NER with regex pattern matching

Implements EntityDetector interface using a hybrid approach:
1. Run spaCy NER (baseline detection)
2. Run regex pattern matching
3. Merge results with deduplication
4. Return combined entity list
"""

from __future__ import annotations

import bisect
import dataclasses
import functools
import json
import re
from dataclasses import dataclass

import yaml

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector
from gdpr_pseudonymizer.nlp.model_names import DEFAULT_SPACY_MODEL
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary
from gdpr_pseudonymizer.nlp.regex_matcher import HSPACE, RegexMatcher
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.resources import (
    FRENCH_GEOGRAPHY_PATH,
    LOCATION_NOISE_FILTER_PATH,
    ORG_ROLE_FILTER_PATH,
    PERSON_BOUNDARIES_PATH,
    PLACE_ABBREVIATIONS_PATH,
    SALUTATIONS_PATH,
)
from gdpr_pseudonymizer.utils.french_patterns import (
    FRENCH_TITLE_PATTERN,
    strip_french_prepositions,
    strip_french_titles,
)
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ORG role filter (Story 10.2, AC3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrgRoleFilter:
    """Role list loaded from ``org_role_filter.yaml`` plus runtime region words."""

    acronyms: frozenset[str]
    vp_prefixes: tuple[str, ...]
    functions: frozenset[str]
    connectors: frozenset[str]
    region_phrases: tuple[tuple[str, ...], ...]


_ROLE_TOKEN_RE = re.compile(r"/|(?i:d')|[^\s/]+")

# Connectors that join two place words into one place ("Europe du Nord")
_PLACE_JOINERS = frozenset({"de", "du", "des", "d'"})

# Clause boundaries for the ORG segment trim (Story 10.2, V3): a line break;
# ",", ";" or ":" followed by whitespace; a sentence period followed by
# whitespace (guarded, see ``_clause_boundaries``).
_CLAUSE_BOUNDARY_RE = re.compile(r"\n|[,;:](?=\s)|\.(?=\s+\S)")
_LAST_WORD_RE = re.compile(r"([A-Za-zÀ-ÿ]+)$")
# A period after one of these is an abbreviation, not a sentence end
_PERIOD_TITLES = frozenset({"mme", "mlle", "prof", "dr", "pr", "me", "m"})
# Types whose spans are cut at clause boundaries. Not PERSON: a comma is part
# of the "Last, First" name form.
_SEGMENT_TRIM_TYPES = frozenset({"ORG"})


# A word: a letter followed by letters, digits, apostrophes or hyphens
_WORD_RE = re.compile(r"[^\W\d_][\w'’-]*")
_TITLE_WORD_RE = re.compile(FRENCH_TITLE_PATTERN, re.IGNORECASE)

# Line-break split, R-SPLIT (Story 10.3a): the line separators HSPACE
# excludes. A detected span is cut at each of them.
_LINE_BREAK_RE = re.compile("[\n\r\v\f\x85\u2028\u2029]")

# Wrapped-name join, W-JOIN (Story 10.3a, Lionel 2026-10-06): a PERSON name
# hard-wrapped over one line break (PDF text extraction).
_UPPER = "A-ZÀ-ÖØ-ÞĀ-ſ"
_LOWER = "a-zß-öø-ÿĀ-ſ"
_WRAP_TOKEN = f"[{_UPPER}][{_UPPER}{_LOWER}]*(?:[-'’][{_UPPER}][{_UPPER}{_LOWER}]*)*"
_WRAP_TOKEN_RE = re.compile(_WRAP_TOKEN)
# A lower-case word start: the line is prose, not a name-only line
_PROSE_WORD_RE = re.compile("(?<![\\w'’])[a-zß-öø-ÿ]")
# R-HYPH-FN (Story 10.3c AC3): the compound_names shape of
# detection_patterns.yaml, two capitalised words joined by one hyphen
_COMPOUND_NAME_RE = re.compile(f"[{_UPPER}][{_LOWER}]+-[{_UPPER}][{_LOWER}]+")


# ---------------------------------------------------------------------------
# PERSON boundaries (Story 10.3b, AC4-AC6, AC9) and W-JOIN particles (R-WJP)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PersonBoundaries:
    """Particle and role-word lists loaded from ``person_boundaries.yaml``."""

    particles: tuple[str, ...]
    allcaps_particles: tuple[str, ...]
    role_words: frozenset[str]


@functools.lru_cache(maxsize=1)
def load_person_boundaries() -> PersonBoundaries:
    """Load the PERSON boundary resource once (no spaCy import).

    All-caps particle forms are derived from the capitalised entries.
    """
    with open(PERSON_BOUNDARIES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    particles = tuple(e["term"] for e in data["particles"])
    allcaps = tuple(sorted({p.upper() for p in particles if p[:1].isupper()}))
    return PersonBoundaries(
        particles=particles,
        allcaps_particles=allcaps,
        role_words=frozenset(e["term"] for e in data["role_words"]),
    )


def _alternation(words: tuple[str, ...] | list[str] | frozenset[str]) -> str:
    """Regex alternation of literal words, longest first."""
    return "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True))


@dataclass(frozen=True)
class _BoundaryPatterns:
    part_spaced: re.Pattern[str]
    comma_role: re.Pattern[str]
    dash_role: re.Pattern[str]
    role_acronym: re.Pattern[str]


@functools.lru_cache(maxsize=1)
def _boundary_patterns() -> _BoundaryPatterns:
    """Patterns built from the frozen lists (particles, role words, acronyms)."""
    lists = load_person_boundaries()
    parts = _alternation(lists.particles + lists.allcaps_particles)
    roles = _alternation(lists.role_words)
    acronyms = _alternation(load_org_role_filter().acronyms)
    return _BoundaryPatterns(
        part_spaced=re.compile(f"{HSPACE}+({parts})(?={HSPACE})"),
        comma_role=re.compile(f",{HSPACE}+(?:{roles})(?![\\w])"),
        dash_role=re.compile(f"{HSPACE}+-{HSPACE}+(?:{roles})(?![\\w])"),
        role_acronym=re.compile(f"(?<=[^\\W\\d_]){HSPACE}+(?:{acronyms})$"),
    )


# Capitalised particles that W-JOIN does not take at the start of the next line
_LINE_START_WORDS = frozenset({"Le", "La", "De", "Du", "Des"})


@functools.lru_cache(maxsize=1)
def _wrap_re() -> re.Pattern[str]:
    """W-JOIN follower pattern, with the frozen particle list (R-WJP).

    After a one-word PERSON: optional particles, one line break, optional
    particles, one capitalised token, then end of text, , . ! ? ) or a space
    and a lower-case letter (never ":" or ";", which start a label line).
    On the next-line side, the capitalised articles and prepositions Le, La,
    De, Du, Des are not particles: at a line start they are everyday words
    ("Le Comité", "La Direction"; QA WJ-001, Lionel 2026-10-07).
    """
    particles = load_person_boundaries().particles
    before = f"(?:{_alternation(particles)})"
    after = (
        f"(?:{_alternation(tuple(p for p in particles if p not in _LINE_START_WORDS))})"
    )
    return re.compile(
        f"(?:{HSPACE}+{before})*{HSPACE}*\r?\n{HSPACE}*"
        f"(?P<right>(?:{after}{HSPACE}+)*{_WRAP_TOKEN})"
        f"(?={HSPACE}*(?:[,.!?)]|\\Z)|{HSPACE}+[a-zß-öø-ÿ])"
    )


@functools.lru_cache(maxsize=1)
def _geography_folded() -> frozenset[str]:
    """Every geography-dictionary entry, case-folded (absence is no evidence)."""
    with open(FRENCH_GEOGRAPHY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    words: set[str] = set()
    for key in ("cities", "regions", "departments", "countries_and_international"):
        words |= {w.casefold() for w in data.get(key, [])}
    return frozenset(words)


@functools.lru_cache(maxsize=1)
def load_location_noise_filter() -> frozenset[str]:
    """Load the LOCATION stoplist once (Story 10.3b), case-folded."""
    with open(LOCATION_NOISE_FILTER_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return frozenset(e["term"].casefold() for e in data["terms"])


# ---------------------------------------------------------------------------
# Salutation lines (Story 10.4, AC1-AC3)
# ---------------------------------------------------------------------------

# A name token: capitalised, hyphen allowed. A "known first name" is a name
# token for which the name dictionary knows the whole token.
_NAME_TOKEN = f"[{_UPPER}][{_UPPER}{_LOWER}]*(?:-[{_UPPER}][{_UPPER}{_LOWER}]*)*"
# Shape 1: one or two names alone on the line, ending with a comma
_SHAPE1_RE = re.compile(
    f"({_NAME_TOKEN})(?:{HSPACE}*,{HSPACE}*({_NAME_TOKEN}))?{HSPACE}*,{HSPACE}*$"
)
# Shape 2, after the opener: two names, else one, then , . ! or the line end
_OPENER_TWO_NAMES_RE = re.compile(
    f"({_NAME_TOKEN}){HSPACE}*,{HSPACE}*({_NAME_TOKEN})(?=[,.!]|{HSPACE}*$)",
    re.MULTILINE,
)
_OPENER_ONE_NAME_RE = re.compile(f"({_NAME_TOKEN})(?=[,.!]|{HSPACE}*$)", re.MULTILINE)
# A PERSON span "X, Y" (AC1)
_NAME_PAIR_RE = re.compile(f"({_NAME_TOKEN}){HSPACE}*,{HSPACE}*({_NAME_TOKEN})")
_HSPACE_STR = " \t\u00a0\u202f"


@dataclass(frozen=True)
class Salutations:
    """Opener list and shape-1 length limit loaded from ``salutations.yaml``."""

    max_line_length: int
    openers: tuple[tuple[str, str], ...]  # (term, kind)
    opener_re: re.Pattern[str]


@functools.lru_cache(maxsize=1)
def load_salutations() -> Salutations:
    """Load the salutation resource once (Story 10.4, AC2).

    An opener matches at the start of a line, case as written; a space in a
    term matches any run of horizontal whitespace. One or more horizontal
    whitespace must follow it.
    """
    with open(SALUTATIONS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    openers = tuple((e["term"], e["kind"]) for e in data["openers"])
    alternatives = "|".join(
        f"(?P<o{i}>{(HSPACE + '+').join(re.escape(w) for w in term.split())})"
        for i, (term, _kind) in enumerate(openers)
    )
    return Salutations(
        max_line_length=int(data["max_line_length"]),
        openers=openers,
        opener_re=re.compile(f"(?:{alternatives}){HSPACE}+"),
    )


@dataclass(frozen=True)
class _SalutationLine:
    """A salutation line: its shape (1 or 2), the opener kind ("names" for
    shape 1), the (start, end) of its one or two names, and whether a comma
    follows the last name."""

    start: int
    end: int
    shape: int
    kind: str
    names: tuple[tuple[int, int], ...]
    comma_after: bool


def _line_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of every line, split at ``_LINE_BREAK_RE``."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for match in _LINE_BREAK_RE.finditer(text):
        spans.append((pos, match.start()))
        pos = match.end()
    spans.append((pos, len(text)))
    return spans


# A LOCATION whose whole text is one of these is a fragment (Story 10.3b);
# the words of FRENCH_PREPOSITION_PATTERN
_BARE_PREPOSITIONS = frozenset({"d'", "l'", "aux", "au", "des", "du", "de", "à", "en"})


def _is_all_caps(text: str) -> bool:
    """At least two letters, all upper-case."""
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 2 and all(c.isupper() for c in letters)


@functools.lru_cache(maxsize=1)
def _default_name_dictionary() -> NameDictionary:
    """The bundled name dictionary, for the Q2 "Last, First" check."""
    names = NameDictionary()
    names.load()
    return names


_ELISION_RE = re.compile(f"{HSPACE}+([dD]['’])(?=[{_UPPER}])")
_HSPACE_RUN_RE = re.compile(f"{HSPACE}+")
_SURNAME_RE = re.compile(
    f"(?:M(?:a)?c[{_UPPER}][{_LOWER}]+|[{_UPPER}][{_LOWER}]+|[{_UPPER}]{{2,}})"
    f"(?:-(?:[{_UPPER}][{_LOWER}]+|[{_UPPER}]{{2,}}))*(?![\\w'’])"
)
_NEXT_CAPITAL_RE = re.compile(f"{HSPACE}+[{_UPPER}]")
_MC_TAIL_RE = re.compile(r"(?<![\w])Ma?c$")
_MC_WORD_RE = re.compile(f"[{_UPPER}][{_LOWER}]+")
_GLUED_PUNCT_RE = re.compile(r"[):,;]+$")
# At most this many particles before the surname ("van der", "de la")
_MAX_PARTICLES = 3
# The characters of HSPACE (regex_matcher.HSPACE)
_HSPACE_CHARS = frozenset(" \t\u00a0\u202f")
# Lower-case articles after which a role word is never a surname (QA REQ-001)
_LOWER_ARTICLES = frozenset({"le", "la"})
# Contracted particles: du = de + le, des = de + les (QA REQ-002)
_CONTRACTIONS = {"du": "le", "des": "les"}


@functools.lru_cache(maxsize=1)
def _particle_set() -> frozenset[str]:
    """Every particle form: listed entries and derived all-caps forms."""
    lists = load_person_boundaries()
    return frozenset(lists.particles + lists.allcaps_particles)


class _SpanIndex:
    """Interval queries over entity spans in O(log n) (no list scan).

    ``overlaps(a, b)``: some span overlaps [a, b). ``covers(a, b, exclude)``:
    some span other than ``exclude`` contains [a, b).
    """

    def __init__(self, spans: list[tuple[int, int, int]]) -> None:
        # (start, end, owner id), sorted by start; prefix top-2 ends
        spans = sorted(spans)
        self._starts = [s for s, _, _ in spans]
        self._prefix: list[tuple[int, int, int]] = []
        best_end, best_owner, second_end = -1, -1, -1
        for _, end, owner in spans:
            if end > best_end:
                if best_owner != owner:
                    second_end = best_end
                best_end, best_owner = end, owner
            elif end > second_end:
                second_end = end
            self._prefix.append((best_end, best_owner, second_end))

    @classmethod
    def of(cls, entities: list[DetectedEntity]) -> _SpanIndex:
        return cls([(e.start_pos, e.end_pos, id(e)) for e in entities])

    def overlaps(self, start: int, end: int) -> bool:
        i = bisect.bisect_left(self._starts, end)
        return i > 0 and self._prefix[i - 1][0] > start

    def covers(
        self, start: int, end: int, exclude: DetectedEntity | None = None
    ) -> bool:
        i = bisect.bisect_right(self._starts, start)
        if i == 0:
            return False
        best_end, best_owner, second_end = self._prefix[i - 1]
        if best_end >= end and (exclude is None or best_owner != id(exclude)):
            return True
        return exclude is not None and second_end >= end


@dataclass(frozen=True)
class _RoleGuard:
    """A guarded ", <role>" or " - <role>" trim: the cut stands only if every
    capitalised word after the role word(s) is covered by another kept
    detection."""

    index: int
    original: DetectedEntity
    words: tuple[tuple[int, int], ...]
    rule: str


def _is_sentence_period(raw: str, index: int) -> bool:
    """Whether the period at ``raw[index]`` ends a sentence.

    Not a sentence end after a word shorter than three letters, an all-caps
    word, or a title (Mme, Mlle, Prof, Dr, Pr, Me, M). Not either after an
    abbreviation (REL-002): a capitalised word of at most four letters
    ("Corp", "Inc", "Cie", "Ltd") followed by a capitalised word.
    """
    word = _LAST_WORD_RE.search(raw[:index])
    last = word.group(1) if word else ""
    if len(last) < 3 or last.lower() in _PERIOD_TITLES or last.isupper():
        return False
    following = raw[index + 1 :].lstrip()
    if len(last) <= 4 and last[0].isupper() and following[:1].isupper():
        return False
    return True


def _clause_boundaries(raw: str) -> list[tuple[int, int]]:
    """(start, end) offsets of the clause boundaries in ``raw``.

    A period counts only when it ends a sentence (``_is_sentence_period``).
    """
    found: list[tuple[int, int]] = []
    for match in _CLAUSE_BOUNDARY_RE.finditer(raw):
        if match.group() == "." and not _is_sentence_period(raw, match.start()):
            continue
        found.append((match.start(), match.end()))
    return found


def _capitalised_words(
    context: str, regions: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """(start, end) of the capitalised words inside ``regions`` (V3 guard).

    Excepted: a title from the French title pattern (it is not a name).
    The first word of a sentence is not excepted (Story 10.3a, REL-004
    option (b), Lionel 2026-10-06): it may be a name, so a cut that would
    leave it uncovered is refused.
    """
    found: list[tuple[int, int]] = []
    for start, end in regions:
        for match in _WORD_RE.finditer(context, start, end):
            word = match.group()
            if not word[0].isupper():
                continue
            if _TITLE_WORD_RE.fullmatch(word) or _TITLE_WORD_RE.fullmatch(word + "."):
                continue
            found.append((match.start(), match.end()))
    return found


PairKey = tuple[tuple[str, int, int, str, str], tuple[str, int, int, str, str]]


# Cap on dedup passes for the precise V3 guard (QA PERF-002). Realistic input
# needs at most about 10 passes (QA fuzz); only adversarial chains of nested
# refused cuts need more (n=200 nested run-on spans took 102 passes). After
# the cap, one last pass refuses every V3 cut that discards a capitalised
# word: that is the blunt guard, which never uncovers a name, so the cap
# bounds the time without giving up coverage.
_MAX_GUARD_PASSES = 16


@dataclass
class _V3Pass:
    """State of one dedup pass for the precise V3 guard.

    ``refused``: pairs whose V3 cut is refused in this pass (they keep their
    run-C result). ``cuts``: the V3 cuts applied in this pass that discard
    capitalised words, as (pair, entity type, discarded word spans).
    """

    refused: frozenset[PairKey]
    cuts: list[tuple[PairKey, str, list[tuple[int, int]]]]
    refuse_all: bool = False


def _pair_key(a: DetectedEntity, b: DetectedEntity) -> PairKey:
    """Value identity of a resolved pair (stable across dedup passes)."""
    return (
        (a.entity_type, a.start_pos, a.end_pos, a.source, a.text),
        (b.entity_type, b.start_pos, b.end_pos, b.source, b.text),
    )


def _role_token_spans(text: str) -> list[tuple[str, int, int]]:
    """Split a VP-form remainder into (token, start, end).

    Whitespace tokens, with "/" and the elision "d'" split off. "&" is a
    connector only as a standalone token ("Sales & Marketing"); inside a word
    ("R&D") it stays part of the word.
    """
    return [(m.group(), m.start(), m.end()) for m in _ROLE_TOKEN_RE.finditer(text)]


def _role_tokens(text: str) -> list[str]:
    """Tokens of a VP-form remainder (see ``_role_token_spans``)."""
    return [t for t, _, _ in _role_token_spans(text)]


def _load_geography_region_words() -> list[str]:
    """Country and French region names from the existing geography resource."""
    with open(FRENCH_GEOGRAPHY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("countries_and_international", [])) + list(
        data.get("regions", [])
    )


@functools.lru_cache(maxsize=1)
def load_org_role_filter() -> OrgRoleFilter:
    """Load the ORG role filter resource once (no spaCy import)."""
    with open(ORG_ROLE_FILTER_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    regions = [e["term"] for e in data["vp_regions"]] + _load_geography_region_words()
    phrases = {tuple(t.casefold() for t in _role_tokens(r)) for r in regions}
    return OrgRoleFilter(
        acronyms=frozenset(e["term"] for e in data["acronyms"]),
        vp_prefixes=tuple(e["term"] for e in data["vp_prefixes"]),
        functions=frozenset(e["term"].casefold() for e in data["vp_functions"]),
        connectors=frozenset(c.casefold() for c in data["connectors"]),
        region_phrases=tuple(sorted(phrases, key=len, reverse=True)),
    )


# vp_regions entries that are not places on their own: scope and compass words
# (Story 10.4, AC4)
_VP_NOT_PLACES = frozenset(
    {
        "International",
        "Monde",
        "Global",
        "Worldwide",
        "Nord",
        "North",
        "Sud",
        "South",
        "Est",
        "East",
        "Ouest",
        "West",
    }
)


@functools.lru_cache(maxsize=1)
def load_place_abbreviations() -> tuple[str, ...]:
    """Load the place abbreviations once (Story 10.4, AC4; GUIDELINES Q14, A5)."""
    with open(PLACE_ABBREVIATIONS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return tuple(e["term"] for e in data["terms"])


@functools.lru_cache(maxsize=1)
def _org_place_phrases() -> tuple[tuple[str, str], ...]:
    """(place, source) for the organisation + place merge, longest first.

    Sources: the countries and regions of the geography resource, the place
    entries of ``vp_regions`` (scope and compass words excluded), the cities
    of the geography resource, and the place abbreviations. A place listed
    twice keeps its first source.
    """
    with open(FRENCH_GEOGRAPHY_PATH, encoding="utf-8") as f:
        geography = json.load(f)
    with open(ORG_ROLE_FILTER_PATH, encoding="utf-8") as f:
        roles = yaml.safe_load(f)
    places: dict[str, str] = {}
    for place in _load_geography_region_words():
        places.setdefault(place, "country_region")
    for entry in roles["vp_regions"]:
        if entry["term"] not in _VP_NOT_PLACES:
            places.setdefault(entry["term"], "country_region")
    for place in geography.get("cities", []):
        places.setdefault(place, "city")
    for place in load_place_abbreviations():
        places.setdefault(place, "abbreviation")
    return tuple(sorted(places.items(), key=lambda item: len(item[0]), reverse=True))


def _place_after(
    text: str, start: int, phrases: tuple[tuple[str, str], ...]
) -> tuple[int, str] | None:
    """(end, source) of the listed place that starts at ``start``, if any.

    The place starts with an upper-case letter in the text and is not followed
    by a letter; it equals the list entry case-insensitively, or exactly for
    an abbreviation. The longest entry wins.
    """
    if start >= len(text) or not text[start].isupper():
        return None
    for phrase, source in phrases:
        end = start + len(phrase)
        candidate = text[start:end]
        if source == "abbreviation":
            if candidate != phrase:
                continue
        elif candidate.casefold() != phrase.casefold():
            continue
        if end < len(text) and text[end].isalpha():
            continue
        return end, source
    return None


def _vp_remainder(text: str, prefixes: tuple[str, ...]) -> str | None:
    """Return the text after a VP prefix ("" for a bare prefix), else None.

    "VP" is case-sensitive; spelled-out prefixes compare case-insensitively.
    """
    for prefix in prefixes:
        if prefix == "VP":
            if text == "VP":
                return ""
            if text.startswith("VP "):
                return text[3:]
        else:
            folded = text.casefold()
            if folded == prefix.casefold():
                return ""
            if folded.startswith(prefix.casefold() + " "):
                return text[len(prefix) + 1 :]
    return None


def _match_org_role_places(text: str) -> tuple[str | None, list[str]]:
    """Classify an ORG text as a role and return the place phrases it names.

    Returns:
        (reason, places): reason is "role_acronym", "vp_form" or None; places
        are the place phrases of a VP form, as they appear in the normalized
        text (e.g. ["Europe"] for "VP Europe", [] for "VP Engineering").
        Consecutive place words joined only by de/du/des/d' form one place
        ("Europe du Nord"); "et", "&" and "/" separate places.
    """
    role_filter = load_org_role_filter()
    normalized = " ".join(strip_french_titles(text).split())
    if normalized in role_filter.acronyms:
        return "role_acronym", []
    rest = _vp_remainder(normalized, role_filter.vp_prefixes)
    if rest is None:
        return None, []
    if rest == "":
        return "vp_form", []
    spans = _role_token_spans(rest)
    tokens = [t.casefold() for t, _, _ in spans]
    i = 0
    has_content = False
    places: list[list[int]] = []  # [start_token, end_token) per place
    while i < len(tokens):
        for phrase in role_filter.region_phrases:
            if tuple(tokens[i : i + len(phrase)]) == phrase:
                has_content = True
                if (
                    places
                    and i > places[-1][1]
                    and all(
                        tokens[k] in _PLACE_JOINERS for k in range(places[-1][1], i)
                    )
                ):
                    places[-1][1] = i + len(phrase)
                else:
                    places.append([i, i + len(phrase)])
                i += len(phrase)
                break
        else:
            if tokens[i] in role_filter.functions:
                has_content = True
                places.append([i, i])  # a function word ends the current place
            elif tokens[i] not in role_filter.connectors:
                return None, []
            i += 1
    if not has_content:
        return None, []
    phrases = [rest[spans[a][1] : spans[b - 1][2]] for a, b in places if b > a]
    return "vp_form", phrases


def match_org_role(text: str) -> str | None:
    """Classify an ORG text as a role (Story 10.2, AC3).

    The whole normalized text (titles stripped, whitespace collapsed, case
    kept) must be a role acronym, a bare VP prefix, or a VP prefix followed
    only by function words, region words and connectors, with at least one
    function or region word.

    Returns:
        "role_acronym", "vp_form", or None when the text is not a role
    """
    return _match_org_role_places(text)[0]


class HybridDetector(EntityDetector):
    """Hybrid entity detector combining spaCy NER with regex pattern matching.

    Detection Pipeline:
        1. Run spaCy NER (baseline detection)
        2. Run regex pattern matching
        3. Merge results with deduplication
        4. Return combined entity list

    Deduplication Rules:
        - Exact overlap (same span or same title-stripped text) → Keep spaCy entity
        - No overlap → Keep both entities
        - Different-type partial overlap → Flag regex entity as ambiguous, keep both
        - Same-type overlap → One span kept (Story 10.2 AC1, PR #81 review):
          containment keeps the containing span, unless C1 (lower-case,
          digit-free extra words → inner span) or the C2 trim (a containing
          span crossing a line break is cut at the break when it still
          contains the inner span) applies; a partial overlap becomes the
          union span (source "merged"); ties broken deterministically
        - ORG whose whole text is a job title or role acronym → Dropped (AC3);
          the place named in a dropped VP title is kept as a LOCATION

    Attributes:
        spacy_detector: SpaCyDetector instance for NLP-based detection
        regex_matcher: RegexMatcher instance for pattern-based detection
    """

    def __init__(self, default_model: str = DEFAULT_SPACY_MODEL) -> None:
        """Initialize hybrid detector with spaCy and regex components.

        Args:
            default_model: spaCy model loaded lazily on first detection when
                load_model() was not called (e.g., "en_core_web_trf")
        """
        self.spacy_detector = SpaCyDetector()
        self.regex_matcher = RegexMatcher()
        self.default_model = default_model
        self._model_loaded = False

    def load_model(self, model_name: str) -> None:
        """Load spaCy model and regex patterns.

        Args:
            model_name: spaCy model name (e.g., "fr_core_news_lg")

        Raises:
            ModelNotFoundError: If spaCy model is not installed
            FileNotFoundError: If regex pattern config not found
        """
        # Load spaCy model
        self.spacy_detector.load_model(model_name)

        # Load regex patterns
        self.regex_matcher.load_patterns()

        self._model_loaded = True
        logger.info(
            "hybrid_detector_loaded",
            spacy_model=model_name,
            regex_patterns_loaded=self.regex_matcher.get_pattern_stats()[
                "total_patterns"
            ],
        )

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        """Detect entities using hybrid spaCy + regex approach.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects from combined detection

        Raises:
            ValueError: If text is empty or invalid
            ModelNotLoadedError: If models not loaded
        """
        if not text:
            raise ValueError("Text cannot be empty")

        if not self._model_loaded:
            # Lazy load with default model
            logger.warning(
                "hybrid_detector_lazy_loading_model", model=self.default_model
            )
            self.load_model(self.default_model)

        # Step 1: spaCy NER
        spacy_entities = self.spacy_detector.detect_entities(text)
        for entity in spacy_entities:
            entity.source = "spacy"

        # Trim non-name tokens (timestamps, punctuation) off span edges before
        # merging, so dedup and mapping lookup see the bare name
        spacy_entities = self._trim_entity_boundaries(spacy_entities)

        logger.debug("spacy_detection_complete", entities_found=len(spacy_entities))

        # Step 2: Regex pattern matching (pass spaCy Doc for POS disambiguation)
        regex_entities = self.regex_matcher.match_entities(
            text, spacy_doc=self.spacy_detector.last_doc
        )
        for entity in regex_entities:
            entity.source = "regex"

        logger.debug("regex_detection_complete", entities_found=len(regex_entities))

        # Story 10.4 (AC2): a known first name alone on a salutation line, or
        # after a greeting, thanks or compliment opener, joins the regex list
        salutation_lines = self._salutation_lines(text)
        regex_entities = regex_entities + self._salutation_names(
            text, salutation_lines, spacy_entities, regex_entities
        )

        # Step 3: PERSON boundaries before the merge, on both sources (Story
        # 10.3b AC4-AC6, AC9): particles, Mc/Mac, trailing roles. The ORG and
        # LOCATION spans of both lists block a particle extension.
        blockers = [
            (e.start_pos, e.end_pos)
            for e in spacy_entities + regex_entities
            if e.entity_type in ("ORG", "LOCATION")
        ]
        spacy_entities, spacy_guards = self._fix_person_boundaries(
            spacy_entities, text, blockers
        )
        regex_entities, regex_guards = self._fix_person_boundaries(
            regex_entities, text, blockers
        )
        # Story 10.4 (AC1): "X, Y" on a salutation line, both known first
        # names → two PERSONs, on both lists
        spacy_entities, spacy_guards = self._split_salutation_pairs(
            spacy_entities, spacy_guards, text, salutation_lines
        )
        regex_entities, regex_guards = self._split_salutation_pairs(
            regex_entities, regex_guards, text, salutation_lines
        )
        # The merge flags regex entities in place: keep pristine copies in case
        # a guarded trim is refused and the document is merged once more
        pristine_regex = (
            [dataclasses.replace(e) for e in regex_entities]
            if spacy_guards or regex_guards
            else []
        )

        # Step 4: Merge with deduplication
        merged_entities = self._merge_entities(spacy_entities, regex_entities, text)

        if spacy_guards or regex_guards:
            kept = _SpanIndex.of(merged_entities)
            refused_spacy = self._refused_guards(spacy_guards, kept)
            refused_regex = self._refused_guards(regex_guards, kept)
            if refused_spacy or refused_regex:
                for index, original in refused_spacy.items():
                    spacy_entities[index] = original
                for index, original in refused_regex.items():
                    pristine_regex[index] = original
                merged_entities = self._merge_entities(
                    spacy_entities, pristine_regex, text
                )

        logger.info(
            "hybrid_detection_complete",
            spacy_count=len(spacy_entities),
            regex_count=len(regex_entities),
            merged_count=len(merged_entities),
        )

        return merged_entities

    def _merge_entities(
        self,
        spacy_entities: list[DetectedEntity],
        regex_entities: list[DetectedEntity],
        text: str | None = None,
    ) -> list[DetectedEntity]:
        """Merge spaCy and regex entities with deduplication logic.

        Deduplication Rules (the first overlapping spaCy entity decides):
            - Exact match (same span, or same text once titles are stripped),
              same type → Keep spaCy entity (prefer NLP confidence)
            - Exact match, different types → Keep both, flag the regex entity
              as ambiguous (Story 10.3c AC1); checked before the Cabinet case.
              Except a hyphenated PERSON with no known first name (R-HYPH-FN,
              AC3): the regex entity is skipped, as before
            - No overlap → Keep both entities
            - Partial overlap, different types → Flag regex entity as ambiguous,
              keep both
            - Partial overlap, same type → Keep both here; the same-type dedup
              pass below keeps one (Story 10.2 AC1)
            - Special case: Regex ORG with "Cabinet" overlapping spaCy PERSON → Prefer ORG

        Post-filters, in order: title-only PERSON, label words, ORG roles
        (AC3), same-type overlap dedup (AC1), then sort by start position.

        Args:
            spacy_entities: Entities detected by spaCy
            regex_entities: Entities detected by regex patterns
            text: Document text, used to slice spans built by the post-filters
                (union, trimmed and place spans). When None, the entity texts
                are used and are assumed to be raw slices of the document.

        Returns:
            Merged and deduplicated list of entities, sorted by position
        """
        merged: list[DetectedEntity] = list(spacy_entities)
        # Track spaCy entities to remove (when regex ORG supersedes spaCy PERSON)
        entities_to_remove: list[DetectedEntity] = []

        for regex_entity in regex_entities:
            overlap_found = False

            for spacy_entity in spacy_entities:
                if self._has_overlap(spacy_entity, regex_entity):
                    overlap_found = True

                    if self._is_exact_match(spacy_entity, regex_entity):
                        if regex_entity.entity_type == spacy_entity.entity_type:
                            # Exact match, same type → Skip regex entity (prefer spaCy)
                            logger.debug(
                                "duplicate_entity_removed",
                                text=regex_entity.text,
                                reason="exact_match_with_spacy",
                            )
                        elif self._is_hyphen_name_without_first_name(regex_entity):
                            # R-HYPH-FN (Story 10.3c AC3): a hyphenated PERSON
                            # with no known first name, which spaCy typed as a
                            # place or a company → skip it, as before 10.3c
                            self._log_cross_type_exact_match(
                                regex_entity,
                                spacy_entity,
                                decision="regex_skipped",
                                rule="hyphen_no_known_first_name",
                            )
                        else:
                            # Exact match, different types → keep both, flag the
                            # regex entity (Story 10.3c AC1, R-MX). This comes
                            # before the Cabinet case, which therefore sees
                            # exactly the pairs it saw before.
                            regex_entity.is_ambiguous = True
                            merged.append(regex_entity)
                            self._log_cross_type_exact_match(
                                regex_entity,
                                spacy_entity,
                                decision="kept_both",
                                rule="type_aware_exact_match",
                            )
                        break
                    elif self._should_prefer_regex_org(regex_entity, spacy_entity):
                        # Special case: Regex ORG (Cabinet pattern) supersedes spaCy PERSON
                        # Remove spaCy PERSON and add regex ORG (not ambiguous)
                        entities_to_remove.append(spacy_entity)
                        merged.append(regex_entity)
                        logger.debug(
                            "org_supersedes_person",
                            regex_text=regex_entity.text,
                            spacy_text=spacy_entity.text,
                            reason="cabinet_pattern_preferred",
                        )
                        break
                    elif regex_entity.entity_type != spacy_entity.entity_type:
                        # Partial overlap, different types → Flag regex entity
                        # as ambiguous, keep both
                        regex_entity.is_ambiguous = True
                        merged.append(regex_entity)
                        logger.debug(
                            "ambiguous_entity_added",
                            regex_text=regex_entity.text,
                            spacy_text=spacy_entity.text,
                            reason="partial_overlap",
                        )
                        break
                    else:
                        # Partial overlap, same type → keep for now, unflagged;
                        # _dedup_same_type_overlaps decides (Story 10.2 AC1)
                        merged.append(regex_entity)
                        break

            if not overlap_found:
                # No overlap → Add regex entity (new detection)
                merged.append(regex_entity)

        # Remove superseded spaCy entities
        for entity in entities_to_remove:
            if entity in merged:
                merged.remove(entity)

        # Filter out title-only entities (e.g., "Maître" without a name)
        merged = self._filter_title_only_entities(merged)

        # Filter out common French label words detected as entities
        merged = self._filter_label_words(merged)

        # Drop common words and fragments detected as places (Story 10.3b)
        merged = self._filter_location_noise(merged, text)

        # Filter out job titles / role acronyms detected as ORG (Story 10.2 AC3)
        merged = self._filter_org_roles(merged, text)

        # Organisation + place → one ORG, the place keeping its LOCATION
        # (Story 10.4 AC4, R-OPC)
        merged = self._merge_org_places(merged, text)

        # Keep one entity per same-type overlap (Story 10.2 AC1)
        merged = self._dedup_same_type_overlaps(merged, text)

        # Cut the spans that still cross a line break; the pieces go through
        # the same post-filters again (Story 10.3a AC2, R-SPLIT late)
        merged, split_count = self._split_at_line_breaks(merged, text)
        if split_count:
            merged = self._filter_title_only_entities(merged)
            merged = self._filter_label_words(merged)
            merged = self._filter_location_noise(merged, text)
            merged = self._filter_org_roles(merged, text)
            merged = self._merge_org_places(merged, text)
            merged = self._dedup_same_type_overlaps(merged, text)

        # Re-join a PERSON name hard-wrapped over one line (Story 10.3a W-JOIN),
        # then trim trailing roles once more on the final spans (Story 10.3b,
        # R-ROLE-LATE, Lionel 2026-10-07)
        if text is not None:
            merged = self._join_wrapped_names(merged, text)
            merged = self._trim_roles_late(merged, text)

        # Sort by start position
        merged.sort(key=lambda e: e.start_pos)

        return merged

    @staticmethod
    def _log_cross_type_exact_match(
        regex_entity: DetectedEntity,
        spacy_entity: DetectedEntity,
        decision: str,
        rule: str,
    ) -> None:
        """Log a different-type exact match (Story 10.3c AC1): types, match
        kind and offsets only, never entity text."""
        same_span = (
            regex_entity.start_pos == spacy_entity.start_pos
            and regex_entity.end_pos == spacy_entity.end_pos
        )
        logger.debug(
            "cross_type_exact_match",
            regex_type=regex_entity.entity_type,
            spacy_type=spacy_entity.entity_type,
            match="span" if same_span else "normalized_text",
            regex_start=regex_entity.start_pos,
            regex_end=regex_entity.end_pos,
            spacy_start=spacy_entity.start_pos,
            spacy_end=spacy_entity.end_pos,
            decision=decision,
            rule=rule,
        )

    @staticmethod
    def _refused_guards(
        guards: list[_RoleGuard], kept: _SpanIndex
    ) -> dict[int, DetectedEntity]:
        """Guarded trims whose discarded capitalised words are not all covered
        by a kept detection: list index → original entity."""
        refused: dict[int, DetectedEntity] = {}
        for guard in guards:
            if not all(kept.covers(start, end) for start, end in guard.words):
                refused[guard.index] = guard.original
                logger.debug(
                    "person_boundary_refused",
                    rule=guard.rule,
                    source=guard.original.source,
                    start=guard.original.start_pos,
                    end=guard.original.end_pos,
                )
        return refused

    def _fix_person_boundaries(
        self,
        entities: list[DetectedEntity],
        text: str,
        blockers: list[tuple[int, int]],
    ) -> tuple[list[DetectedEntity], list[_RoleGuard]]:
        """Fix PERSON span boundaries before the merge (Story 10.3b).

        In order, on each PERSON entity: Mc/Mac completion (AC5), particle
        extension (AC4), trailing-role trim (AC6, AC9). Other types are
        returned unchanged. A fixed span's text is the document slice.

        Args:
            entities: Pre-merge entities of one source
            text: Document text
            blockers: Pre-merge ORG and LOCATION spans of both sources

        Returns:
            (entities, guards): the guarded " - <role>" trims, to be checked
            against the merged detections (``_refused_guards``)
        """
        blocked = _SpanIndex([(s, e, 0) for s, e in blockers])
        out: list[DetectedEntity] = []
        guards: list[_RoleGuard] = []
        for entity in entities:
            if entity.entity_type != "PERSON" or entity.end_pos > len(text):
                out.append(entity)
                continue
            new = entity
            rules: list[str] = []
            extended = self._complete_mc(new, text)
            if extended is not None:
                new = extended
                rules.append("mc_mac")
            extended = self._extend_particles(new, text, blocked)
            if extended is not None:
                new = extended
                rules.append("particle")
            trimmed, rule, words = self._trim_trailing_role(new, text)
            if trimmed is not None:
                if words:
                    # a refused trim falls back to the span before the trim
                    guards.append(_RoleGuard(len(out), new, words, rule))
                new = trimmed
                rules.append(rule)
            for rule in rules:
                logger.debug(
                    "person_boundary_fixed",
                    rule=rule,
                    source=entity.source,
                    old_start=entity.start_pos,
                    old_end=entity.end_pos,
                    new_start=new.start_pos,
                    new_end=new.end_pos,
                )
            out.append(new)
        return out, guards

    @staticmethod
    def _respan(
        entity: DetectedEntity, text: str, start: int, end: int
    ) -> DetectedEntity:
        """The entity with a new span; its text is the document slice."""
        return dataclasses.replace(
            entity, text=text[start:end], start_pos=start, end_pos=end
        )

    @classmethod
    def _complete_mc(cls, entity: DetectedEntity, text: str) -> DetectedEntity | None:
        """A span ending in a bare "Mc"/"Mac" followed by an upper-case letter
        is extended to the end of that word (AC5)."""
        raw = text[entity.start_pos : entity.end_pos]
        end = entity.end_pos
        if not _MC_TAIL_RE.search(raw) or end >= len(text) or not text[end].isupper():
            return None
        word = _MC_WORD_RE.match(text, end)
        if word is None:
            return None
        return cls._respan(entity, text, entity.start_pos, word.end())

    @classmethod
    def _extend_particles(
        cls, entity: DetectedEntity, text: str, blocked: _SpanIndex
    ) -> DetectedEntity | None:
        """Extend a PERSON span over particle(s) + one surname token (AC4).

        Same line only. A span that already ends in particle(s) is re-anchored
        before them. The surname is one capitalised token (or Mc/Mac, or an
        all-caps token after a capitalised or all-caps particle), not followed
        by another capitalised token; the added text overlaps no ORG or
        LOCATION detection, and is not a geography-dictionary entry.
        """
        patterns = _boundary_patterns()
        raw = text[entity.start_pos : entity.end_pos]
        line_start = entity.start_pos + max(
            (m.end() for m in _LINE_BREAK_RE.finditer(raw)), default=0
        )
        anchor = cls._trailing_particles_start(text, line_start, entity.end_pos)
        pos = anchor
        parts: list[str] = []
        while len(parts) < _MAX_PARTICLES:
            match = patterns.part_spaced.match(text, pos)
            if match is None:
                break
            parts.append(match.group(1))
            pos = match.end()
        elision = _ELISION_RE.match(text, pos)
        if elision is not None:
            parts.append(elision.group(1))
            pos = elision.end()
        else:
            if not parts:
                return None
            space = _HSPACE_RUN_RE.match(text, pos)
            if space is None:
                return None
            pos = space.end()
        surname = _SURNAME_RE.match(text, pos)
        if surname is None or surname.end() <= entity.end_pos:
            return None
        end = surname.end()
        if _NEXT_CAPITAL_RE.match(text, end):
            return None
        token = surname.group(0)
        letters = token.replace("-", "")
        if len(letters) >= 2 and letters.isupper() and not parts[-1][:1].isupper():
            # all-caps after lower-case de/du/des/d': an acronym ORG ("du CNRS")
            return None
        if (
            parts[-1] in _LOWER_ARTICLES
            and token in load_person_boundaries().role_words
        ):
            # "Zorbalia le Directeur": a role after an article, not a surname
            # (GUIDELINES P6; QA REQ-001)
            return None
        if blocked.overlaps(entity.end_pos, end):
            return None
        places = _geography_folded()
        phrase = " ".join(text[anchor:end].split())
        if token.casefold() in places or phrase.casefold() in places:
            return None
        if cls._chain_names_a_place(parts, token, places):
            return None
        return cls._respan(entity, text, entity.start_pos, end)

    @staticmethod
    def _chain_names_a_place(
        parts: list[str], token: str, places: frozenset[str]
    ) -> bool:
        """Whether a tail of "particle(s) surname" is a dictionary place:
        "de La Zorbelle", "de Le Zorbmans", and the contractions du → le and
        des → les ("du Havre" → "Le Havre"). GUIDELINES Q12; QA REQ-002."""
        for i, part in enumerate(parts):
            rest = parts[i + 1 :] + [token]
            words = [part] + rest
            if " ".join(words).casefold() in places:
                return True
            article = _CONTRACTIONS.get(part.casefold())
            if article and " ".join([article] + rest).casefold() in places:
                return True
        return False

    @staticmethod
    def _trailing_particles_start(text: str, line_start: int, end: int) -> int:
        """Start of the run of at most ``_MAX_PARTICLES`` particles that ends a
        span (the space before the first one), else ``end``.

        Walks back over the last tokens only, so it is linear in their length
        whatever the span holds (QA PERF-001). The run must not start the line:
        some text must come before it.
        """
        particles = _particle_set()
        anchor = end
        pos = end
        for _ in range(_MAX_PARTICLES):
            token_start = pos
            while (
                token_start > line_start and text[token_start - 1] not in _HSPACE_CHARS
            ):
                token_start -= 1
            if token_start == pos or text[token_start:pos] not in particles:
                break
            space_start = token_start
            while space_start > line_start and text[space_start - 1] in _HSPACE_CHARS:
                space_start -= 1
            if space_start == token_start or space_start == line_start:
                break
            anchor = pos = space_start
        return anchor

    def _known_first_name(self, word: str) -> bool:
        names = self.regex_matcher.name_dictionary or _default_name_dictionary()
        return names.is_first_name(word)

    def _is_known_name_token(self, word: str) -> bool:
        """A known first name in the text (Story 10.4): capitalised there,
        and the whole token is a dictionary first name."""
        return bool(word) and word[0].isupper() and self._known_first_name(word)

    def _salutation_lines(self, text: str) -> list[_SalutationLine]:
        """The salutation lines of a document (Story 10.4, AC precisions).

        Shape 1: after removing leading and trailing horizontal whitespace,
        the line is one or two known first names (comma-separated) followed
        by a comma, and is at most ``max_line_length`` characters long.
        Shape 2 (tried when shape 1 does not apply): after optional leading
        horizontal whitespace, an opener of ``salutations.yaml``, then two
        known first names "N, N" or one, followed by , . ! or the end of the
        line. One pass over the lines.
        """
        lists = load_salutations()
        found: list[_SalutationLine] = []
        for start, end in _line_spans(text):
            line = text[start:end]
            body = start + len(line) - len(line.lstrip(_HSPACE_STR))
            shape1 = _SHAPE1_RE.fullmatch(text, body, end)
            if shape1:
                names = tuple(
                    (shape1.start(g), shape1.end(g)) for g in (1, 2) if shape1.group(g)
                )
                if all(self._is_known_name_token(text[a:b]) for a, b in names):
                    if len(line.strip(_HSPACE_STR)) <= lists.max_line_length:
                        found.append(
                            _SalutationLine(start, end, 1, "names", names, True)
                        )
                    continue
            opener = lists.opener_re.match(text, body, end)
            if opener is None:
                continue
            kind = lists.openers[int(str(opener.lastgroup)[1:])][1]
            two = _OPENER_TWO_NAMES_RE.match(text, opener.end(), end)
            if (
                two
                and self._is_known_name_token(two.group(1))
                and self._is_known_name_token(two.group(2))
            ):
                names = ((two.start(1), two.end(1)), (two.start(2), two.end(2)))
                comma = text[two.end() : two.end() + 1] == ","
                found.append(_SalutationLine(start, end, 2, kind, names, comma))
                continue
            one = _OPENER_ONE_NAME_RE.match(text, opener.end(), end)
            if one and self._is_known_name_token(one.group(1)):
                comma = text[one.end() : one.end() + 1] == ","
                found.append(
                    _SalutationLine(
                        start, end, 2, kind, ((one.start(1), one.end(1)),), comma
                    )
                )
        return found

    @staticmethod
    def _salutation_names(
        text: str,
        lines: list[_SalutationLine],
        spacy_entities: list[DetectedEntity],
        regex_entities: list[DetectedEntity],
    ) -> list[DetectedEntity]:
        """R-SAL-BARE (Story 10.4, AC2): each name of a salutation line that no
        PERSON of either list contains becomes a regex PERSON (confidence
        0.80). Only adds detections."""
        persons = [
            (e.start_pos, e.end_pos)
            for e in spacy_entities + regex_entities
            if e.entity_type == "PERSON"
        ]
        added: list[DetectedEntity] = []
        for line in lines:
            for start, end in line.names:
                if any(a <= start and end <= b for a, b in persons):
                    continue
                persons.append((start, end))
                added.append(
                    DetectedEntity(
                        text=text[start:end],
                        entity_type="PERSON",
                        start_pos=start,
                        end_pos=end,
                        confidence=0.80,
                        source="regex",
                    )
                )
                logger.debug(
                    "salutation_name_added",
                    shape=line.shape,
                    opener_kind=line.kind,
                    start=start,
                    end=end,
                )
        return added

    def _split_salutation_pairs(
        self,
        entities: list[DetectedEntity],
        guards: list[_RoleGuard],
        text: str,
        lines: list[_SalutationLine],
    ) -> tuple[list[DetectedEntity], list[_RoleGuard]]:
        """R-SAL-SPLIT (Story 10.4, AC1): a PERSON span "X, Y" that is exactly
        the two names of a salutation line whose names end with a comma, both
        known first names, is replaced in place by PERSON X and PERSON Y.
        Elsewhere (running text, "Last, First") the span is unchanged. The
        guards of the list are re-indexed to the new positions."""
        pairs = {
            (line.names[0][0], line.names[1][1])
            for line in lines
            if len(line.names) == 2 and line.comma_after
        }
        if not pairs:
            return entities, guards
        out: list[DetectedEntity] = []
        new_index: dict[int, int] = {}
        for index, entity in enumerate(entities):
            new_index[index] = len(out)
            match = (
                _NAME_PAIR_RE.fullmatch(text, entity.start_pos, entity.end_pos)
                if entity.entity_type == "PERSON"
                and (entity.start_pos, entity.end_pos) in pairs
                else None
            )
            if (
                match is None
                or not self._is_known_name_token(match.group(1))
                or not self._is_known_name_token(match.group(2))
            ):
                out.append(entity)
                continue
            for group in (1, 2):
                out.append(
                    dataclasses.replace(
                        entity,
                        text=match.group(group),
                        start_pos=match.start(group),
                        end_pos=match.end(group),
                        is_ambiguous=False,
                    )
                )
            logger.debug(
                "salutation_name_split",
                source=entity.source,
                old_start=entity.start_pos,
                old_end=entity.end_pos,
                first_start=match.start(1),
                first_end=match.end(1),
                second_start=match.start(2),
                second_end=match.end(2),
            )
        if len(out) == len(entities):
            return out, guards
        return out, [
            dataclasses.replace(guard, index=new_index[guard.index]) for guard in guards
        ]

    def _is_hyphen_name_without_first_name(self, entity: DetectedEntity) -> bool:
        """R-HYPH-FN (Story 10.3c AC3): a PERSON whose title-stripped text is
        one hyphenated compound (the compound_names shape) none of whose two
        parts is a known first name. Checked only on a different-type exact
        match, where it restores the pre-10.3c skip."""
        if entity.entity_type != "PERSON":
            return False
        core = self._normalize_entity_text(entity.text)
        if not _COMPOUND_NAME_RE.fullmatch(core):
            return False
        return not any(self._known_first_name(part) for part in core.split("-"))

    def _trim_trailing_role(
        self, entity: DetectedEntity, text: str
    ) -> tuple[DetectedEntity | None, str, tuple[tuple[int, int], ...]]:
        """Trim a trailing role from a single-line PERSON span (AC6, AC9).

        ", <role word> …" (not "Last, First") and " - <role word> …", both
        guarded: the capitalised words after the role words are returned and
        must be covered by another kept detection (QA COV-001); a role
        acronym right after a letter ("<Name> DRH"); glued trailing
        ``) : , ;`` ("<Name>):").

        Returns:
            (trimmed entity or None, rule, guard words)
        """
        raw = text[entity.start_pos : entity.end_pos]
        if _LINE_BREAK_RE.search(raw):
            return None, "", ()
        patterns = _boundary_patterns()
        roles = load_person_boundaries().role_words
        start = entity.start_pos
        match = patterns.comma_role.search(raw)
        if match is not None:
            word = raw[match.start() + 1 :].split()[0].strip(",.;:")
            keep = raw[: match.start()].rstrip()
            if keep and not self._known_first_name(word):
                # guarded like " - <role>" (QA COV-001): the capitalised
                # words after the role word(s) must be covered elsewhere
                words = tuple(
                    (start + w.start(), start + w.end())
                    for w in _WORD_RE.finditer(raw, match.end())
                    if w.group()[0].isupper() and w.group() not in roles
                )
                return (
                    self._respan(entity, text, start, start + len(keep)),
                    "trailing_role_comma",
                    words,
                )
        match = patterns.dash_role.search(raw)
        if match is not None:
            keep = raw[: match.start()].rstrip()
            words = tuple(
                (start + w.start(), start + w.end())
                for w in _WORD_RE.finditer(raw, match.end())
                if w.group()[0].isupper() and w.group() not in roles
            )
            if keep:
                return (
                    self._respan(entity, text, start, start + len(keep)),
                    "trailing_role_dash",
                    words,
                )
        match = patterns.role_acronym.search(raw)
        if match is not None and match.start() > 0:
            return (
                self._respan(entity, text, start, start + match.start()),
                "trailing_role_acronym",
                (),
            )
        match = _GLUED_PUNCT_RE.search(raw)
        if match is not None and match.start() > 0 and raw[match.start() - 1].isalpha():
            return (
                self._respan(entity, text, start, start + match.start()),
                "glued_punctuation",
                (),
            )
        return None, "", ()

    def _trim_roles_late(
        self, entities: list[DetectedEntity], text: str
    ) -> list[DetectedEntity]:
        """Trailing-role trims once more on the final PERSON spans
        (R-ROLE-LATE, Lionel 2026-10-07); then the same-type dedup again.

        A guarded " - <role>" trim stands only if another final entity
        covers each discarded capitalised word.
        """
        kept: _SpanIndex | None = None
        out: list[DetectedEntity] = []
        changed = False
        for entity in entities:
            if entity.entity_type != "PERSON" or entity.end_pos > len(text):
                out.append(entity)
                continue
            trimmed, rule, words = self._trim_trailing_role(entity, text)
            if trimmed is None:
                out.append(entity)
                continue
            if words:
                if kept is None:
                    kept = _SpanIndex.of(entities)
                if not all(kept.covers(s, e, exclude=entity) for s, e in words):
                    logger.debug(
                        "person_boundary_refused",
                        rule=rule,
                        source=entity.source,
                        start=entity.start_pos,
                        end=entity.end_pos,
                    )
                    out.append(entity)
                    continue
            logger.debug(
                "person_boundary_fixed",
                rule=rule,
                source=entity.source,
                old_start=entity.start_pos,
                old_end=entity.end_pos,
                new_start=trimmed.start_pos,
                new_end=trimmed.end_pos,
            )
            out.append(trimmed)
            changed = True
        if changed:
            out = self._dedup_same_type_overlaps(out, text)
        return out

    def _split_at_line_breaks(
        self, entities: list[DetectedEntity], text: str | None
    ) -> tuple[list[DetectedEntity], int]:
        """Cut every entity at each line break inside it (Story 10.3a, R-SPLIT).

        Each piece is whitespace-stripped and kept, with the same type and
        source and document offsets, if it holds an upper-case letter or a
        digit; the edge-junk trim then runs on the new pieces only. A name
        never spans a line break in the app's input formats.

        Args:
            entities: Merged, filtered, deduplicated entities
            text: Document text, or None (entity texts are then raw slices)

        Returns:
            (entities, number of entities that were split)
        """
        out: list[DetectedEntity] = []
        split_count = 0
        for entity in entities:
            raw = self._slice(entity, text)
            if not _LINE_BREAK_RE.search(raw):
                out.append(entity)
                continue
            split_count += 1
            pieces: list[DetectedEntity] = []
            dropped = 0
            pos = 0
            for part in _LINE_BREAK_RE.split(raw):
                part_start = pos
                pos += len(part) + 1
                stripped = part.strip()
                if not any(ch.isupper() or ch.isdigit() for ch in stripped):
                    dropped += 1 if stripped else 0
                    continue
                start = entity.start_pos + part_start + (len(part) - len(part.lstrip()))
                pieces.append(
                    dataclasses.replace(
                        entity,
                        text=stripped,
                        start_pos=start,
                        end_pos=start + len(stripped),
                    )
                )
            kept = self._trim_entity_boundaries(pieces)
            logger.debug(
                "span_split_linebreak",
                entity_type=entity.entity_type,
                source=entity.source,
                segments_kept=len(kept),
                segments_dropped=dropped + len(pieces) - len(kept),
            )
            out.extend(kept)
        return out, split_count

    @staticmethod
    def _join_wrapped_names(
        entities: list[DetectedEntity], text: str
    ) -> list[DetectedEntity]:
        """Extend a PERSON hard-wrapped over one line break (Story 10.3a W-JOIN).

        A PERSON whose text, titles stripped, is one capitalised name token,
        on a line that has a lower-case word before it, is extended across a
        single line break (no blank line, no punctuation at the line end) to
        the capitalised token that starts the next line, particles included,
        when that token is followed by the end of the text, , . ! ? ) or a
        space and a lower-case letter. PERSON entities inside the new span
        are dropped. Never a ":" or ";" follower (a label line), never a
        following capitalised token (a second name or a role line).

        Output order: the input entities that are kept, in input order, then
        the joined spans in the order they were made. Near-linear (QA
        PERF-001): removals are tracked by object identity, and the PERSON
        spans inside a new span are found by start offset, so no step scans
        the whole entity list.

        Args:
            entities: Entities after the line-break split
            text: Document text

        Returns:
            Entities with wrapped names joined
        """
        removed: set[int] = set()
        joined_spans: list[DetectedEntity] = []
        # PERSON candidates by start offset. A joined span starts where its
        # source entity starts, so ``starts`` also covers the joined spans.
        persons_at: dict[int, list[DetectedEntity]] = {}
        for entity in entities:
            if entity.entity_type == "PERSON":
                persons_at.setdefault(entity.start_pos, []).append(entity)
        starts = sorted(persons_at)
        for entity in entities:
            if entity.entity_type != "PERSON" or id(entity) in removed:
                continue
            if entity.end_pos > len(text):
                continue
            raw = text[entity.start_pos : entity.end_pos]
            if not raw or not raw[-1].isalpha():
                continue
            core = strip_french_titles(raw).split()
            if len(core) != 1 or not _WRAP_TOKEN_RE.fullmatch(core[0]):
                continue
            match = _wrap_re().match(text, entity.end_pos)
            if match is None:
                continue
            line_start = entity.start_pos
            while line_start > 0 and not _LINE_BREAK_RE.match(text[line_start - 1]):
                line_start -= 1
            if not _PROSE_WORD_RE.search(text, line_start, entity.start_pos):
                continue
            end = match.end("right")
            joined = dataclasses.replace(
                entity, text=text[entity.start_pos : end], end_pos=end
            )
            removed.add(id(entity))
            lo = bisect.bisect_left(starts, entity.start_pos)
            hi = bisect.bisect_right(starts, end)
            for start in starts[lo:hi]:
                for kept in persons_at[start]:
                    if kept.end_pos <= end:
                        removed.add(id(kept))
            persons_at[entity.start_pos].append(joined)
            joined_spans.append(joined)
            logger.debug(
                "wrapped_name_joined",
                entity_type=entity.entity_type,
                source=entity.source,
                start=entity.start_pos,
                end=end,
            )
        return [e for e in entities if id(e) not in removed] + [
            j for j in joined_spans if id(j) not in removed
        ]

    def _should_prefer_regex_org(
        self, regex_entity: DetectedEntity, spacy_entity: DetectedEntity
    ) -> bool:
        """Check if regex ORG entity should supersede spaCy PERSON entity.

        This handles the "Cabinet" pattern case where spaCy incorrectly detects
        "Cabinet Mercier" as PERSON, but regex correctly detects
        "Cabinet Mercier & Associés" as ORG.

        Args:
            regex_entity: Regex-detected entity
            spacy_entity: spaCy-detected entity

        Returns:
            True if regex ORG should replace spaCy PERSON
        """
        # Only apply when regex is ORG and spaCy is PERSON
        if regex_entity.entity_type != "ORG" or spacy_entity.entity_type != "PERSON":
            return False

        # Check if regex entity starts with organization prefix patterns
        org_prefixes = ("Cabinet", "Société", "Entreprise", "Groupe", "Compagnie")
        if not regex_entity.text.startswith(org_prefixes):
            return False

        # Check if spaCy entity is contained within regex entity
        # (i.e., regex detected a larger span that includes the spaCy detection)
        if (
            regex_entity.start_pos <= spacy_entity.start_pos
            and regex_entity.end_pos >= spacy_entity.end_pos
        ):
            return True

        return False

    @staticmethod
    def _is_edge_junk_token(token: str, entity_type: str) -> bool:
        """Check if a span-edge token cannot be part of an entity name.

        Tokens with letters are always kept. PERSON names never contain
        letterless tokens, so any is junk. ORG/LOCATION keep bare numbers
        ("Studio 54", "Paris 2024") and only lose timestamps and punctuation.

        Args:
            token: Whitespace-delimited token at the edge of an entity span
            entity_type: PERSON, LOCATION, or ORG

        Returns:
            True if the token should be trimmed off the span
        """
        if any(char.isalpha() for char in token):
            return False
        if entity_type == "PERSON":
            return True
        is_timestamp = ":" in token and any(char.isdigit() for char in token)
        is_punctuation = not any(char.isalnum() for char in token)
        return is_timestamp or is_punctuation

    def _trim_entity_boundaries(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Trim timestamps and punctuation that NER models glue to entity spans.

        Transformer models (e.g. en_core_web_trf) often draw spans too wide on
        transcripts: "Aino Virtanen        24:85:01" comes back as one PERSON.
        Since mappings are keyed on the full entity text, every timestamp would
        otherwise create a new entity with its own pseudonym.

        Args:
            entities: List of detected entities

        Returns:
            Entities with edge junk trimmed; entities that are only junk are dropped
        """
        trimmed = []
        for entity in entities:
            tokens = list(re.finditer(r"\S+", entity.text))
            first, last = 0, len(tokens) - 1
            while first <= last and self._is_edge_junk_token(
                tokens[first].group(), entity.entity_type
            ):
                first += 1
            while last >= first and self._is_edge_junk_token(
                tokens[last].group(), entity.entity_type
            ):
                last -= 1

            if first > last:
                logger.debug(
                    "junk_only_entity_filtered",
                    text=entity.text,
                    entity_type=entity.entity_type,
                    reason="no_name_tokens",
                )
                continue

            start = tokens[first].start()
            end = tokens[last].end()
            if start != 0 or end != len(entity.text):
                logger.debug(
                    "entity_boundary_trimmed",
                    original=entity.text,
                    trimmed=entity.text[start:end],
                )
                entity.start_pos += start
                entity.end_pos = entity.start_pos + (end - start)
                entity.text = entity.text[start:end]
            trimmed.append(entity)

        return trimmed

    def _filter_title_only_entities(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Filter out entities that are just titles without actual names.

        Entities like "Maître" or "Dr." alone (without a following name) are
        sometimes incorrectly detected by spaCy as PERSON entities. This filter
        removes such false positives.

        Args:
            entities: List of detected entities

        Returns:
            Filtered list with title-only entities removed
        """
        filtered = []
        for entity in entities:
            # Only filter PERSON entities (titles don't apply to ORG/LOCATION)
            if entity.entity_type != "PERSON":
                filtered.append(entity)
                continue

            # Check if entity becomes empty after stripping titles
            normalized = self._normalize_entity_text(entity.text)
            if normalized:
                filtered.append(entity)
            else:
                logger.debug(
                    "title_only_entity_filtered",
                    text=entity.text,
                    source=entity.source,
                    reason="entity_is_title_only",
                )

        return filtered

    def _filter_label_words(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Filter out common French label words incorrectly detected as entities.

        Words like "Lieu" (Location label), "Date", etc. are sometimes detected
        by spaCy as named entities when they appear as document labels.

        Args:
            entities: List of detected entities

        Returns:
            Filtered list with label words removed
        """
        # Common French label words that are not actual named entities
        # These appear in documents as field labels (e.g., "Lieu: Paris")
        label_words = {
            "lieu",  # Location label
            "date",  # Date label
            "heure",  # Time label
            "objet",  # Subject label
            "sujet",  # Subject label
            "titre",  # Title label
            "nom",  # Name label
            "adresse",  # Address label
        }

        filtered = []
        for entity in entities:
            # Check if entity text (lowercase) is just a label word
            if entity.text.lower().strip() in label_words:
                logger.debug(
                    "label_word_entity_filtered",
                    text=entity.text,
                    entity_type=entity.entity_type,
                    source=entity.source,
                    reason="entity_is_label_word",
                )
            else:
                filtered.append(entity)

        return filtered

    def _filter_location_noise(
        self, entities: list[DetectedEntity], text: str | None = None
    ) -> list[DetectedEntity]:
        """Drop common words and fragments detected as places (Story 10.3b).

        The text is normalized as the mapping key does: prepositions, then
        titles stripped, whitespace collapsed; compared case-folded. A
        LOCATION is dropped when the whole normalized text is a stoplist
        entry and not a geography-dictionary place (AC1, AC2; an all-caps
        detection only on a stoplist hit, never because it is absent from the
        dictionary), or when it is a fragment: nothing left, or a bare
        preposition ("à Dr", "à M"). Company names typed LOCATION are kept
        (AC3, no lexicon, Lionel 2026-10-07).

        Args:
            entities: Merged entities
            text: Document text (see ``_merge_entities``)

        Returns:
            Entities without the noise LOCATIONs
        """
        stoplist = load_location_noise_filter()
        places = _geography_folded()
        out: list[DetectedEntity] = []
        for entity in entities:
            if entity.entity_type != "LOCATION":
                out.append(entity)
                continue
            raw = self._slice(entity, text)
            norm = " ".join(strip_french_titles(strip_french_prepositions(raw)).split())
            folded = norm.casefold()
            reason = None
            if not norm or raw.strip().casefold() in _BARE_PREPOSITIONS:
                reason = "fragment"
            elif folded in stoplist and folded not in places:
                reason = "allcaps_common_word" if _is_all_caps(norm) else "common_noun"
            if reason is None:
                out.append(entity)
                continue
            logger.debug(
                "location_noise_filtered",
                reason=reason,
                action="dropped",
                source=entity.source,
                start=entity.start_pos,
                end=entity.end_pos,
            )
        return out

    def _filter_org_roles(
        self, entities: list[DetectedEntity], text: str | None = None
    ) -> list[DetectedEntity]:
        """Drop ORG detections whose whole normalized text is a job title.

        Role acronyms ("CTO", "DRH", "COMEX") and VP forms ("VP", "VP Sales",
        "VP Europe") are roles, not organisations (Story 10.2, AC3). The list
        lives in ``resources/org_role_filter.yaml``. ORG only, any source.
        When a dropped VP form names a place ("VP Europe"), the place part is
        kept as a LOCATION detection (Lionel, PR #81 review), so the place is
        still pseudonymized. Places come from the role list's region words and
        the geography resource only.

        Args:
            entities: List of detected entities
            text: Document text (see ``_merge_entities``)

        Returns:
            Filtered list with role ORG detections removed and place spans added
        """
        filtered = []
        for entity in entities:
            if entity.entity_type == "ORG":
                reason, places = _match_org_role_places(entity.text)
                if reason is not None:
                    emitted = self._place_entities(entity, places, text)
                    filtered.extend(emitted)
                    logger.debug(
                        "org_role_filtered",
                        entity_type=entity.entity_type,
                        source=entity.source,
                        reason=reason,
                        places_emitted=len(emitted),
                    )
                    continue
            filtered.append(entity)
        return filtered

    @staticmethod
    def _merge_org_places(
        entities: list[DetectedEntity], text: str | None
    ) -> list[DetectedEntity]:
        """R-OPC (Story 10.4, AC4): an ORG followed, on the same line, by one
        horizontal whitespace and a listed place becomes one ORG over both.

        The merged text must not be a role (``match_org_role``), so "VP" +
        "Europe" is never merged (the role filter ran before). The place keeps
        its own LOCATION (GUIDELINES Q3, G7): an existing LOCATION with the
        place's exact span is kept, otherwise one is emitted. Runs after
        ``_filter_org_roles``, before the same-type dedup.
        """
        if text is None:
            return entities
        phrases = _org_place_phrases()
        locations = {
            (e.start_pos, e.end_pos) for e in entities if e.entity_type == "LOCATION"
        }
        out: list[DetectedEntity] = []
        emitted: list[DetectedEntity] = []
        for entity in entities:
            if (
                entity.entity_type != "ORG"
                or entity.end_pos + 1 >= len(text)
                or text[entity.end_pos] not in _HSPACE_CHARS
            ):
                out.append(entity)
                continue
            place_start = entity.end_pos + 1
            place = _place_after(text, place_start, phrases)
            if place is None:
                out.append(entity)
                continue
            place_end, source = place
            merged_text = text[entity.start_pos : place_end]
            if match_org_role(merged_text) is not None:
                out.append(entity)
                continue
            out.append(
                dataclasses.replace(
                    entity, text=merged_text, end_pos=place_end, is_ambiguous=False
                )
            )
            location_emitted = (place_start, place_end) not in locations
            if location_emitted:
                emitted.append(
                    DetectedEntity(
                        text=text[place_start:place_end],
                        entity_type="LOCATION",
                        start_pos=place_start,
                        end_pos=place_end,
                        confidence=entity.confidence,
                        source=entity.source,
                    )
                )
                locations.add((place_start, place_end))
            logger.debug(
                "org_place_merged",
                source=entity.source,
                org_start=entity.start_pos,
                org_end=entity.end_pos,
                place_start=place_start,
                place_end=place_end,
                place_source=source,
                location_emitted=location_emitted,
            )
        return out + emitted

    @staticmethod
    def _place_entities(
        entity: DetectedEntity, places: list[str], text: str | None
    ) -> list[DetectedEntity]:
        """LOCATION detections for the place phrases of a dropped VP form."""
        raw = entity.text
        if text is not None and entity.end_pos <= len(text):
            raw = text[entity.start_pos : entity.end_pos]
        result: list[DetectedEntity] = []
        cursor = 0
        for phrase in places:
            # whole words only: never inside a longer word ("est" in "investir")
            pattern = (
                r"(?<!\w)"
                + r"\s+".join(re.escape(tok) for tok in phrase.split())
                + r"(?!\w)"
            )
            match = re.compile(pattern).search(raw, cursor)
            if match is None:
                continue
            cursor = match.end()
            result.append(
                DetectedEntity(
                    text=match.group(),
                    entity_type="LOCATION",
                    start_pos=entity.start_pos + match.start(),
                    end_pos=entity.start_pos + match.end(),
                    confidence=entity.confidence,
                    source=entity.source,
                )
            )
        return result

    # ------------------------------------------------------------------
    # Same-type overlap dedup (Story 10.2, AC1/AC2)
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup_norm(entity: DetectedEntity) -> str:
        """App normalization: titles stripped; prepositions too on LOCATION."""
        text = strip_french_titles(entity.text)
        if entity.entity_type == "LOCATION":
            text = strip_french_prepositions(text)
        return text

    @classmethod
    def _dedup_key(cls, entity: DetectedEntity) -> str:
        """Normalized text, lower-cased, whitespace collapsed (mapping key)."""
        return " ".join(cls._dedup_norm(entity).lower().split())

    @classmethod
    def _dedup_core(cls, entity: DetectedEntity) -> tuple[int, int]:
        """Character span of the normalized text inside the raw span."""
        norm = cls._dedup_norm(entity)
        i = entity.text.find(norm) if norm else -1
        if i >= 0:
            return (entity.start_pos + i, entity.start_pos + i + len(norm))
        return (entity.start_pos, entity.end_pos)

    @classmethod
    def _containment_added_text(
        cls, outer: DetectedEntity, inner: DetectedEntity
    ) -> str:
        """Text of the outer core outside the inner core (left + right)."""
        oc, ic = cls._dedup_core(outer), cls._dedup_core(inner)
        off = outer.start_pos
        left = outer.text[oc[0] - off : ic[0] - off]
        right = outer.text[ic[1] - off : oc[1] - off]
        return left + " " + right if left and right else left + right

    @staticmethod
    def _slice(entity: DetectedEntity, text: str | None) -> str:
        """Raw text of an entity's span: from the document when available."""
        if text is not None and entity.end_pos <= len(text):
            return text[entity.start_pos : entity.end_pos]
        return entity.text

    @classmethod
    def _union(
        cls, a: DetectedEntity, b: DetectedEntity, text: str | None
    ) -> DetectedEntity:
        """One span covering both a and b (source "merged")."""
        start, end = min(a.start_pos, b.start_pos), max(a.end_pos, b.end_pos)
        if text is not None and end <= len(text):
            union_text = text[start:end]
        else:
            left, right = (a, b) if a.start_pos <= b.start_pos else (b, a)
            union_text = left.text
            if right.end_pos > left.end_pos:
                union_text += right.text[left.end_pos - right.start_pos :]
        base = a if a.source == "spacy" or b.source != "spacy" else b
        return dataclasses.replace(
            base,
            text=union_text,
            start_pos=start,
            end_pos=end,
            source="merged",
            is_ambiguous=False,
        )

    @classmethod
    def _trim_at_line_break(
        cls, entity: DetectedEntity, text: str | None
    ) -> DetectedEntity | None:
        """The entity cut at its first line break, or None if it has none."""
        raw = cls._slice(entity, text)
        cut = raw.find("\n")
        if cut < 0:
            return None
        kept = raw[:cut].rstrip()
        if not kept:
            return None
        return dataclasses.replace(
            entity, text=kept, end_pos=entity.start_pos + len(kept)
        )

    @classmethod
    def _clause_segment(
        cls, entity: DetectedEntity, anchor: tuple[int, int], text: str | None
    ) -> DetectedEntity | None:
        """The part of ``entity`` between the clause boundaries around ``anchor``.

        Returns None when the anchor itself crosses a boundary, when the
        segment would be the whole span, or when it is empty.
        """
        raw = cls._slice(entity, text)
        a0, a1 = anchor[0] - entity.start_pos, anchor[1] - entity.start_pos
        bounds = _clause_boundaries(raw)
        if any(s < a1 and e > a0 for s, e in bounds):
            return None
        left = max((e for s, e in bounds if e <= a0), default=0)
        right = min((s for s, e in bounds if s >= a1), default=len(raw))
        if left == 0 and right == len(raw):
            return None
        segment = raw[left:right]
        lead = len(segment) - len(segment.lstrip())
        segment = segment.strip()
        if not segment:
            return None
        start = entity.start_pos + left + lead
        return dataclasses.replace(
            entity, text=segment, start_pos=start, end_pos=start + len(segment)
        )

    @classmethod
    def _resolve_same_type_pair(
        cls,
        a: DetectedEntity,
        b: DetectedEntity,
        text: str | None = None,
        v3: _V3Pass | None = None,
    ) -> tuple[DetectedEntity | None, str]:
        """Pairwise decision, with the ORG segment trim (Story 10.2, V3).

        After the base decision, for ORG pairs: a containment kept by the
        outer span (``containment`` or ``containment_outer_trimmed_linebreak``)
        is replaced by the outer span cut to the clause segment around the
        inner core, when that segment still contains the inner core (reason
        ``containment_outer_trimmed_boundary``). A union is cut the same way
        around the overlap of the two cores (``partial_overlap_union_trimmed``).

        Precise guard (Lionel, 2026-10-05): a cut whose discarded text holds
        capitalised words is applied provisionally and recorded in ``v3``;
        ``_dedup_same_type_overlaps`` refuses it afterwards if a discarded
        word is not covered by a kept same-type span. A refused pair (or any
        such cut when ``v3`` is None) keeps its base (run-C) result.
        """
        result, reason = cls._resolve_same_type_pair_base(a, b, text)
        if a.entity_type not in _SEGMENT_TRIM_TYPES or result is None:
            return result, reason
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        if reason in ("containment", "containment_outer_trimmed_linebreak"):
            a_contains = ca[0] <= cb[0] and cb[1] <= ca[1]
            outer, inner = (a, b) if a_contains else (b, a)
            inner_core = cls._dedup_core(inner)
            segment = cls._clause_segment(outer, inner_core, text)
            if segment is not None:
                sc = cls._dedup_core(segment)
                if (
                    sc[0] <= inner_core[0]
                    and inner_core[1] <= sc[1]
                    and cls._cut_allowed(a, b, outer, segment, text, v3)
                ):
                    return segment, "containment_outer_trimmed_boundary"
        elif reason == "partial_overlap_union":
            anchor = (max(ca[0], cb[0]), min(ca[1], cb[1]))
            segment = cls._clause_segment(result, anchor, text)
            if segment is not None and cls._cut_allowed(
                a, b, result, segment, text, v3
            ):
                return segment, "partial_overlap_union_trimmed"
        return result, reason

    @classmethod
    def _cut_allowed(
        cls,
        a: DetectedEntity,
        b: DetectedEntity,
        entity: DetectedEntity,
        segment: DetectedEntity,
        text: str | None,
        v3: _V3Pass | None,
    ) -> bool:
        """Whether a V3 cut of ``entity`` to ``segment`` may be applied now.

        A cut that discards no capitalised word is always allowed. Otherwise
        it is allowed provisionally (and recorded) unless the pair is already
        refused; outside a dedup pass (``v3`` None) it is refused.
        """
        words = cls._discarded_name_words(entity, segment, text)
        if not words:
            return True
        if v3 is None or v3.refuse_all:
            return False
        key = _pair_key(a, b)
        if key in v3.refused:
            return False
        v3.cuts.append((key, entity.entity_type, words))
        return True

    @classmethod
    def _discarded_name_words(
        cls, entity: DetectedEntity, segment: DetectedEntity, text: str | None
    ) -> list[tuple[int, int]]:
        """Document offsets of the capitalised words a cut would discard.

        Titles and sentence-start words are excepted (``_capitalised_words``).
        Words are read in the document when available, else in the entity
        text.
        """
        if text is not None and entity.end_pos <= len(text):
            context, offset = text, 0
        else:
            context, offset = entity.text, entity.start_pos
        regions = [
            (entity.start_pos - offset, segment.start_pos - offset),
            (segment.end_pos - offset, entity.end_pos - offset),
        ]
        return [
            (start + offset, end + offset)
            for start, end in _capitalised_words(context, regions)
        ]

    @classmethod
    def _resolve_same_type_pair_base(
        cls, a: DetectedEntity, b: DetectedEntity, text: str | None = None
    ) -> tuple[DetectedEntity | None, str]:
        """Pairwise decision for two same-type entities with overlapping spans.

        ``a`` precedes ``b`` in walk order. Returns (result, reason): result is
        a, b, a new entity replacing both (union or trimmed span), or None when
        both are kept (cores disjoint).
        """
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        a_contains = ca[0] <= cb[0] and cb[1] <= ca[1]
        b_contains = cb[0] <= ca[0] and ca[1] <= cb[1]
        # Equal cores, or equal keys when one core contains the other (title or
        # preposition variants). Equal text at two different, partly
        # overlapping positions is not a tie (QA REL-003): it is a partial
        # overlap and becomes a union below.
        equal = ca == cb or (
            cls._dedup_key(a) == cls._dedup_key(b) and (a_contains or b_contains)
        )
        if not equal:
            if not (ca[0] < cb[1] and cb[0] < ca[1]):
                return None, "cores_disjoint"
            if a_contains or b_contains:
                outer, inner = (a, b) if a_contains else (b, a)
                added = cls._containment_added_text(outer, inner)
                tokens = added.split()
                if tokens and all(
                    not any(ch.isupper() or ch.isdigit() for ch in tok)
                    for tok in tokens
                ):
                    return inner, "containment_inner_preferred"
                if "\n" in added:
                    trimmed = cls._trim_at_line_break(outer, text)
                    if trimmed is not None:
                        tc, ic = cls._dedup_core(trimmed), cls._dedup_core(inner)
                        if tc[0] <= ic[0] and ic[1] <= tc[1]:
                            return trimmed, "containment_outer_trimmed_linebreak"
                return outer, "containment"
            return cls._union(a, b, text), "partial_overlap_union"
        # Tie: spaCy first, longer raw span, earlier start, earlier in walk
        if a.source != b.source:
            return (a if a.source == "spacy" else b), "tie"
        raw_a, raw_b = a.end_pos - a.start_pos, b.end_pos - b.start_pos
        if raw_a != raw_b:
            return (a if raw_a > raw_b else b), "tie"
        if a.start_pos != b.start_pos:
            return (a if a.start_pos < b.start_pos else b), "tie"
        return a, "tie"

    def _dedup_same_type_overlaps(
        self, entities: list[DetectedEntity], text: str | None = None
    ) -> list[DetectedEntity]:
        """Keep one entity per same-type overlap (Story 10.2, AC1).

        Runs ``_dedup_walk`` in passes for the precise V3 guard (Lionel,
        2026-10-05). After each pass, every applied V3 cut that discarded
        capitalised words is checked against the kept entities: each such
        word must lie inside a kept span of the same type. Failing cuts are
        added to the refused set and the walk is run again from the start.
        The refused set only grows and is bounded by the number of pairs, so
        the loop terminates; each walk is deterministic (sorted input), so the
        result does not depend on the input order. Only the final pass logs.
        After ``_MAX_GUARD_PASSES`` passes, a last pass refuses every V3 cut
        that discards a capitalised word (QA PERF-002), so the time is bounded
        and coverage is kept.

        Args:
            entities: Merged, filtered entity list
            text: Document text (see ``_merge_entities``)

        Returns:
            Entity list without same-type overlaps (order not guaranteed)
        """
        refused: frozenset[PairKey] = frozenset()
        passes = 0
        while True:
            passes += 1
            v3 = _V3Pass(
                refused=refused, cuts=[], refuse_all=passes > _MAX_GUARD_PASSES
            )
            kept, events = self._dedup_walk(entities, text, v3)
            failing = {
                key
                for key, entity_type, words in v3.cuts
                if not all(
                    any(
                        k.entity_type == entity_type
                        and k.start_pos <= ws
                        and we <= k.end_pos
                        for k in kept
                    )
                    for ws, we in words
                )
            }
            if not failing:
                for kept_e, dropped_e, reason in events:
                    self._log_dedup(kept_e, dropped_e, reason)
                return kept
            refused = refused | failing

    def _dedup_walk(
        self,
        entities: list[DetectedEntity],
        text: str | None,
        v3: _V3Pass,
    ) -> tuple[list[DetectedEntity], list[tuple[DetectedEntity, DetectedEntity, str]]]:
        """One dedup pass; returns the kept entities and the log events.

        Walks entities by (start, -end, spaCy first). A new entity that loses
        to any kept same-type rival it conflicts with is dropped. When a pair
        resolves to a new span (union of a partial overlap, or an outer span
        trimmed at a line break), that span replaces both and is compared
        again with the kept entities. Otherwise every conflicting kept rival
        is dropped and the new entity is kept. Cross-type pairs are never
        compared (a LOCATION nested in an ORG is legitimate, GUIDELINES G7).

        Args:
            entities: Merged, filtered entity list
            text: Document text (see ``_merge_entities``)
            v3: Pass state of the precise V3 guard (refused pairs, cut record)

        Returns:
            (kept entities without same-type overlaps, in insertion order;
            the dedup log events of this pass)
        """
        events: list[tuple[DetectedEntity, DetectedEntity, str]] = []
        ordered = sorted(
            entities, key=lambda e: (e.start_pos, -e.end_pos, e.source != "spacy")
        )
        # Active window: kept entities that end at or before the walk position
        # can never overlap a later entity, so they are retired. A replacement
        # (union / trimmed span) can start before the walk position; only then
        # are the retired entities that reach into it compared again. Entries
        # carry their insertion number so that comparisons and the result keep
        # the exact insertion order (same outcome as a full scan).
        active: list[tuple[int, DetectedEntity]] = []
        retired: list[tuple[int, DetectedEntity]] = []
        seq = 0
        for entity in ordered:
            walk_pos = entity.start_pos
            still_active: list[tuple[int, DetectedEntity]] = []
            for item in active:
                (retired if item[1].end_pos <= walk_pos else still_active).append(item)
            active = still_active
            current: DetectedEntity | None = entity
            while current is not None:
                candidates = active
                if current.start_pos < walk_pos:
                    reach = [r for r in retired if r[1].end_pos > current.start_pos]
                    if reach:
                        candidates = sorted(active + reach, key=lambda item: item[0])
                rivals: list[tuple[tuple[int, DetectedEntity], str]] = []
                replaced: (
                    tuple[tuple[int, DetectedEntity], DetectedEntity, str] | None
                ) = None
                lost: tuple[DetectedEntity, str] | None = None
                for item in candidates:
                    other = item[1]
                    if (
                        other.entity_type != current.entity_type
                        or other.end_pos <= current.start_pos
                        or current.end_pos <= other.start_pos
                    ):
                        continue
                    result, reason = self._resolve_same_type_pair(
                        other, current, text, v3
                    )
                    if result is None:
                        continue
                    if result is other:
                        lost = (other, reason)
                        break
                    if result is current:
                        rivals.append((item, reason))
                        continue
                    replaced = (item, result, reason)
                    break
                if lost is not None:
                    events.append((lost[0], current, lost[1]))
                    current = None
                elif replaced is not None:
                    item, result, reason = replaced
                    self._remove_kept(item, active, retired)
                    events.append((result, item[1], reason))
                    events.append((result, current, reason))
                    current = result
                else:
                    for item, reason in rivals:
                        self._remove_kept(item, active, retired)
                        events.append((current, item[1], reason))
                    active.append((seq, current))
                    seq += 1
                    current = None
        kept = [e for _, e in sorted(active + retired, key=lambda item: item[0])]
        return kept, events

    @staticmethod
    def _remove_kept(
        item: tuple[int, DetectedEntity],
        active: list[tuple[int, DetectedEntity]],
        retired: list[tuple[int, DetectedEntity]],
    ) -> None:
        """Remove a kept entry from whichever window list holds it."""
        if item in active:
            active.remove(item)
        else:
            retired.remove(item)

    @staticmethod
    def _log_dedup(kept: DetectedEntity, dropped: DetectedEntity, reason: str) -> None:
        """Log a same-type dedup decision without any entity text (AC2)."""
        logger.debug(
            "same_type_overlap_resolved",
            entity_type=kept.entity_type,
            reason=reason,
            kept_source=kept.source,
            dropped_source=dropped.source,
            kept_start=kept.start_pos,
            kept_end=kept.end_pos,
            dropped_start=dropped.start_pos,
            dropped_end=dropped.end_pos,
        )

    def _has_overlap(self, e1: DetectedEntity, e2: DetectedEntity) -> bool:
        """Check if two entities overlap in text span.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities overlap, False otherwise
        """
        return not (e1.end_pos <= e2.start_pos or e2.end_pos <= e1.start_pos)

    def _normalize_entity_text(self, text: str) -> str:
        """Normalize entity text by stripping French titles.

        This ensures that "Dr. Marie Dubois" and "Marie Dubois" are recognized as
        the same entity during deduplication, preventing duplicate validation prompts.

        Args:
            text: Entity text potentially containing titles

        Returns:
            Text with titles removed and whitespace normalized

        Examples:
            "Dr. Marie Dubois" → "Marie Dubois"
            "Mme Fontaine" → "Fontaine"
            "Marie Dubois" → "Marie Dubois" (unchanged)
        """
        return strip_french_titles(text)

    def _is_exact_match(self, e1: DetectedEntity, e2: DetectedEntity) -> bool:
        """Check if two entities have identical span OR normalized text.

        Checks both positional exact match and normalized text match to handle
        cases where one detector includes a title and the other doesn't
        (e.g., "Dr. Marie Dubois" from regex vs "Marie Dubois" from spaCy).

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities have same start/end positions OR same normalized text
        """
        # Check positional exact match
        if e1.start_pos == e2.start_pos and e1.end_pos == e2.end_pos:
            return True

        # Check normalized text match (strips titles for comparison)
        # This handles "Dr. Marie Dubois" == "Marie Dubois" cases
        if self._normalize_entity_text(e1.text) == self._normalize_entity_text(e2.text):
            return True

        return False

    def get_model_info(self) -> dict[str, str]:
        """Get model metadata for audit logging.

        Returns:
            Dictionary with hybrid detector information
        """
        spacy_info = self.spacy_detector.get_model_info()
        regex_stats = self.regex_matcher.get_pattern_stats()

        return {
            "name": "hybrid_detector",
            "version": "1.0",
            "library": "hybrid",
            "language": "fr",
            "spacy_model": spacy_info.get("name", "unknown"),
            "spacy_version": spacy_info.get("version", "unknown"),
            "regex_patterns_count": str(regex_stats.get("total_patterns", 0)),
        }

    @property
    def supports_gender_classification(self) -> bool:
        """Whether this detector provides gender information.

        Returns:
            True if spaCy detector supports gender classification
        """
        return self.spacy_detector.supports_gender_classification
