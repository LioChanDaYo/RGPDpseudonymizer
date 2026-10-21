"""Custom pseudonyms set during validation (Story 10.11).

A custom pseudonym is the pseudonym a user chooses for a name during
validation ("Changer le pseudonyme" in the desktop app, [C] in the command
line). It belongs to a name: the mapping key of the text sent to
finalization, and its type (Story 10.7).

This module is shared by the desktop review, the command-line review and
finalization:

- the custom pseudonym is normalized like a mapping key (titles and, for a
  place, a leading preposition removed; spaces collapsed);
- for a person it is split into a first-name part and a last-name part
  (Lionel's Q4 and Q-G): a part the real last or first name already has is
  matched whole first; else at its last space, except that the library's own
  last names of two or more words stay whole; a one-word pseudonym has no
  parts;
- it is checked against Lionel's rules, in this order: a name that already
  has a stored pseudonym keeps it (Q1); a real first or last name that
  already has a part keeps it (Q-D); it may not be, in whole or in part,
  another name's pseudonym (Q2); it may not be a real name: a capitalised
  word or words of the document, a name of the review whatever its
  capitals (Story 10.16, Codex #8), or a full name stored in the mapping
  database (Q2, Q-C, Q-C2). Capitals, accents and repeated spaces are
  ignored when comparing (Q-C). For a person, every beginning and every
  ending of the pseudonym (Q2) and every run of its words (Q-C; a linking
  word followed by another word is not compared alone, Lionel's Q-I) are
  checked, so the checks do not depend on where it is split (QA MW-001,
  PO A1).

Nothing here logs or raises with a name or a pseudonym in it.
"""

from __future__ import annotations

import functools
import json
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.utils.text_form import word_pattern

if TYPE_CHECKING:
    from gdpr_pseudonymizer.data.models import Entity

# The theme stored on the row of a custom pseudonym. The theme column holds
# the source of a pseudonym (a library theme); a custom pseudonym comes from
# the user. Later runs use it to find the custom values the library does not
# track (``untracked_custom_values``).
CUSTOM_THEME = "custom"

# A name, as finalization keys it: (mapping key, entity type).
NameKey = tuple[str, str]


class CustomPseudonymRefusal(Enum):
    """Why a custom pseudonym is refused (one per rule, in check order)."""

    ALREADY_STORED = "already_stored"  # Q1
    PART_BOUND = "part_bound"  # Q-D
    PSEUDONYM_TAKEN = "pseudonym_taken"  # Q2: another name's pseudonym or part
    REAL_NAME = "real_name"  # Q2, Q-C, Q-C2


@dataclass(frozen=True)
class Refusal:
    """A refused custom pseudonym and the values its message names.

    Attributes:
        reason: The rule the pseudonym breaks
        pseudonym: The normalized custom pseudonym
        other: ALREADY_STORED: the stored pseudonym. PART_BOUND: the real
            first or last name. PSEUDONYM_TAKEN: the other name.
            REAL_NAME: the word or words found.
        required: PART_BOUND: the part the real name already has
        example: PART_BOUND: a pseudonym that the rule accepts
        kind: PART_BOUND: "first" or "last"
        in_document: REAL_NAME: the words are a name of this document (a
            capitalised word of the document, or a name of the review or
            sent), not only a full name stored in the mapping database
            (Story 10.16, Lionel's 10.16 Q1)
    """

    reason: CustomPseudonymRefusal
    pseudonym: str
    other: str
    required: str = ""
    example: str = ""
    kind: str = ""
    in_document: bool = False


# The command line's set-time check: (name's mapping key, type, normalized
# custom pseudonym, this review's custom pseudonyms of other names, the
# mapping keys of this review's names not rejected (Story 10.16)) -> the
# refusal, or None.
PseudonymChecker = Callable[
    [str, str, str, Mapping[NameKey, str], Iterable[str]], Refusal | None
]


def normalize_custom_pseudonym(text: str, entity_type: str) -> str:
    """The custom pseudonym as it is stored and written.

    The text the user typed with its titles (and, for a place, a leading
    preposition) removed and its spaces collapsed, as a mapping key. The
    desktop dialog is pre-filled with the suggestion, which carries the
    name's title; the written text puts each occurrence's own title back.
    An empty result means no custom pseudonym.
    """
    return mapping_key(text, entity_type)


def split_custom_pseudonym(
    pseudonym: str,
    entity_type: str,
    bound_first: str | None = None,
    bound_last: str | None = None,
) -> tuple[str | None, str | None]:
    """A person's custom pseudonym split into a first-name part and a
    last-name part (Lionel's Q4 and Q-G; AC17 (b)).

    In this order: when the pseudonym ends with the part the real last name
    already has (``bound_last``, as whole words), the split falls just
    before it; else, when it starts with the part the real first name
    already has (``bound_first``), just after it (QA MW-001, PO A2); else,
    when it ends with one of the library's last names of two or more words,
    just before that name (Q-G); else at its last space (Q4). At least one
    word stays on each side; words are compared folded, and each part keeps
    the spelling typed.

    Returns (first-name part, last-name part); (None, None) for a one-word
    pseudonym and for any other type.
    """
    if entity_type != "PERSON":
        return None, None
    words = pseudonym.split()
    if len(words) < 2:
        return None, None
    if bound_last and _ends_with(words, bound_last):
        size = len(bound_last.split())
        return " ".join(words[:-size]), " ".join(words[-size:])
    if bound_first and _starts_with(words, bound_first):
        size = len(bound_first.split())
        return " ".join(words[:size]), " ".join(words[size:])
    for library_name in library_two_word_last_names():
        if _ends_with(words, library_name):
            size = len(library_name.split())
            return " ".join(words[:-size]), " ".join(words[-size:])
    return " ".join(words[:-1]), words[-1]


def _ends_with(words: list[str], part: str) -> bool:
    """Whether ``words`` end with ``part``'s words (folded), with at least
    one word before them."""
    size = len(part.split())
    return 0 < size < len(words) and fold(" ".join(words[-size:])) == fold(part)


def _starts_with(words: list[str], part: str) -> bool:
    """Whether ``words`` start with ``part``'s words (folded), with at least
    one word after them."""
    size = len(part.split())
    return 0 < size < len(words) and fold(" ".join(words[:size])) == fold(part)


@functools.cache
def library_two_word_last_names() -> tuple[str, ...]:
    """The library's last names of two or more words, folded, longest first
    (Lionel's Q-G, "Keep the app's four whole").

    Read from the pseudonym library files of every theme, once per process,
    so the set follows the library; today the four of ``neutral.json``. A
    small constant of the package: no document data is kept.
    """
    from gdpr_pseudonymizer.resources import PSEUDONYMS_DIR

    names: set[str] = set()
    for path in sorted(PSEUDONYMS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for last_name in data.get("last_names", []):
            if isinstance(last_name, str) and len(last_name.split()) >= 2:
                names.add(fold(last_name))
    return tuple(sorted(names, key=lambda name: (-len(name.split()), name)))


def person_parts(name: str) -> tuple[str | None, str | None]:
    """A person's real first and last name, as the pseudonym engine parses
    them (``parse_full_name``): the last word is the last name and the words
    before it the first name; one word is a first name only."""
    words = name.split()
    if not words:
        return None, None
    if len(words) == 1:
        return words[0], None
    return " ".join(words[:-1]), words[-1]


def fold(text: str) -> str:
    """Comparison form (Q-C): accents and capitals ignored, spaces collapsed."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


# A pseudonym value, the real text it stands for (None for a part with no
# real counterpart) and whether it is a full pseudonym.
_Value = tuple[str, str | None, bool]


def _row_values(row: Entity) -> list[_Value]:
    """A stored row's pseudonym values, each with the real text it stands for.

    A person's custom pseudonym (theme ``custom``) gives the same values as
    one of this review (``_custom_values``): every beginning and every
    ending, the values the generation guard keeps, so the check is the same
    in both directions (PO B1). A library row gives its full pseudonym and
    its two stored parts."""
    if row.theme == CUSTOM_THEME and row.entity_type == "PERSON":
        return _custom_values(row.full_name, row.entity_type, row.pseudonym_full)
    values: list[_Value] = [(row.pseudonym_full, row.full_name, True)]
    if row.pseudonym_first:
        values.append((row.pseudonym_first, row.first_name, False))
    if row.pseudonym_last:
        values.append((row.pseudonym_last, row.last_name, False))
    return values


def _custom_values(name: str, entity_type: str, pseudonym: str) -> list[_Value]:
    """The values a custom pseudonym is compared with (Q2; AC17 (c)).

    The full pseudonym, for the name; for a person also every beginning (one
    or more whole words, for the real first name) and every ending (for the
    real last name; on a one-word name it stands for no real text, PO R1).
    For two words these are the full pseudonym and its two parts; none of
    them depends on where the pseudonym is split (QA MW-001, PO A1). An
    organisation's or a place's has the full value only (PO A3)."""
    values: list[_Value] = [(pseudonym, name, True)]
    if entity_type != "PERSON":
        return values
    words = pseudonym.split()
    real_first, real_last = person_parts(name)
    for size in range(1, len(words)):
        values.append((" ".join(words[:size]), real_first, False))
        values.append((" ".join(words[-size:]), real_last, False))
    return values


def _clash(mine: list[_Value], theirs: list[_Value]) -> bool:
    """Whether two sets of values share a value (Q2).

    Two equal parts that stand for the same real first or last name do not
    clash (Story 2.8: one real name, one part). A part with no real
    counterpart never takes that exception, and two full pseudonyms never do
    (Story 10.7: two types of one text never share a pseudonym).
    """
    for value, real, is_full in mine:
        for other_value, other_real, other_full in theirs:
            if fold(value) != fold(other_value):
                continue
            if (
                real is not None
                and other_real is not None
                and fold(real) == fold(other_real)
                and not (is_full and other_full)
            ):
                continue
            return True
    return False


# Story 10.20 (AC4): a word is a run of word characters and combining marks, so
# a mark with no composed letter (« x » + U+0301) stays inside its word.
_WORD = word_pattern()
_APOSTROPHES = frozenset({"'", "’"})


def _separator_kind(gap: str) -> str:
    """The kind of separator between two words (PO F1): a space for any run
    of whitespace, a hyphen, an apostrophe, else the folded text itself."""
    if gap and gap.isspace():
        return "space"
    if gap == "-":
        return "hyphen"
    if gap in _APOSTROPHES:
        return "apostrophe"
    return "other:" + fold(gap)


@dataclass(frozen=True)
class DocumentWords:
    """A document's words, read once per check or per finalization (QA
    PERF-001, PO A5): their spans, their folded forms and, for each folded
    word, the positions where it occurs. Nothing keeps it after the check.
    """

    text: str
    spans: tuple[tuple[int, int], ...]
    folded: tuple[str, ...]
    where: Mapping[str, tuple[int, ...]]


def document_words(document_text: str) -> DocumentWords:
    """Read a document's words once (``DocumentWords``).

    Story 10.16 (Codex's review of 463481a): the text is read in one composed
    form (Unicode NFC) before it is cut into words, so a letter written with a
    separate accent mark (a letter, then U+0301) stays inside its word; a
    mark alone is not a word character. ``DocumentWords.text`` is that
    composed text, read only by ``_occurrence``: nothing written or stored
    changes.
    """
    text = unicodedata.normalize("NFC", document_text)
    spans = tuple(token.span() for token in _WORD.finditer(text))
    folded = tuple(fold(text[start:end]) for start, end in spans)
    where: dict[str, list[int]] = {}
    for position, word in enumerate(folded):
        where.setdefault(word, []).append(position)
    return DocumentWords(
        text,
        spans,
        folded,
        {word: tuple(positions) for word, positions in where.items()},
    )


def _capitalised_occurrence(candidate: str, words: DocumentWords) -> bool:
    """Whether ``candidate`` occurs in the document as a real name (Q-C).

    Its words occur as consecutive whole words of the document, with the
    candidate's own separators between them, the first of them starting with
    a capital letter there (found by the detector or not; a sentence-initial
    word counts). Capitals and accents are ignored when comparing.
    """
    return _occurrence(candidate, words, capitalised=True)


def _occurrence(candidate: str, words: DocumentWords, capitalised: bool) -> bool:
    """Whether ``candidate``'s words occur as consecutive whole words of
    ``words``, with the candidate's own separators between them (a space for
    any whitespace, a hyphen, an apostrophe; PO F1), compared folded.

    ``capitalised``: the first of them must start with a capital letter
    there (the document, Q-C). Without it, capitals do not matter (a name of
    the review, Story 10.16).
    """
    wanted_tokens = list(_WORD.finditer(candidate))
    if not wanted_tokens:
        return False
    wanted = [fold(token.group()) for token in wanted_tokens]
    wanted_gaps = [
        _separator_kind(candidate[a.end() : b.start()])
        for a, b in zip(wanted_tokens, wanted_tokens[1:])
    ]
    text, spans, folded = words.text, words.spans, words.folded
    size = len(wanted)
    for start in words.where.get(wanted[0], ()):
        if list(folded[start : start + size]) != wanted:
            continue
        if capitalised and not text[spans[start][0]].isupper():
            continue
        gaps = [
            _separator_kind(text[spans[j][1] : spans[j + 1][0]])
            for j in range(start, start + size - 1)
        ]
        if gaps == wanted_gaps:
            return True
    return False


# Small linking words (Lionel's Q-I, "Not alone (Rec.)"), compared folded.
LINKING_WORDS = frozenset(
    {
        "da",
        "das",
        "de",
        "del",
        "della",
        "des",
        "di",
        "do",
        "dos",
        "du",
        "la",
        "le",
        "les",
        "van",
        "von",
        "der",
    }
)


def _word_runs(pseudonym: str, entity_type: str) -> list[str]:
    """The runs of words compared with real names (Q-C, Q-C2; PO A1, A3).

    For a person, every run of consecutive whole words: the full pseudonym
    first, then longer runs before shorter ones, left to right. For an
    organisation or a place, the full pseudonym only.
    """
    if entity_type != "PERSON":
        return [pseudonym]
    words = pseudonym.split()
    return [
        " ".join(words[start : start + size])
        for size in range(len(words), 0, -1)
        for start in range(len(words) - size + 1)
    ]


def _document_runs(pseudonym: str, entity_type: str) -> list[str]:
    """The runs compared with the document (Q-C as Lionel's Q-I refines it):
    ``_word_runs`` without a linking word that another word of the
    pseudonym follows, on its own. The words around it, every longer run
    that holds it and a linking word at the end are kept."""
    if entity_type != "PERSON":
        return [pseudonym]
    words = pseudonym.split()
    return [
        " ".join(words[start : start + size])
        for size in range(len(words), 0, -1)
        for start in range(len(words) - size + 1)
        if not (
            size == 1 and start < len(words) - 1 and fold(words[start]) in LINKING_WORDS
        )
    ]


# (folded real first or last name, "first" or "last") -> the part it has
_Bound = dict[tuple[str, str], str]


def _stored_bound(rows: list[Entity]) -> _Bound:
    """The parts the real first and last names already have in the stored
    person rows. The first one read wins (Dev Notes, PO F6)."""
    bound: _Bound = {}
    for row in rows:
        if row.entity_type != "PERSON":
            continue
        if row.first_name and row.pseudonym_first:
            bound.setdefault((fold(row.first_name), "first"), row.pseudonym_first)
        if row.last_name and row.pseudonym_last:
            bound.setdefault((fold(row.last_name), "last"), row.pseudonym_last)
    return bound


def _bound_of(bound: _Bound, name: str) -> tuple[str | None, str | None]:
    """The parts a name's real first and last name already have."""
    real_first, real_last = person_parts(name)
    first = bound.get((fold(real_first), "first")) if real_first else None
    last = bound.get((fold(real_last), "last")) if real_last else None
    return first, last


def _bound_parts(stored: _Bound, other_customs: Mapping[NameKey, str]) -> _Bound:
    """The stored parts, then the parts this review's other custom
    pseudonyms give (each split with its own real names' stored parts)."""
    bound = dict(stored)
    for (other_name, other_type), other in other_customs.items():
        first, last = split_custom_pseudonym(
            other, other_type, *_bound_of(stored, other_name)
        )
        if not first or not last:
            continue
        real_first, real_last = person_parts(other_name)
        if real_first:
            bound.setdefault((fold(real_first), "first"), first)
        if real_last:
            bound.setdefault((fold(real_last), "last"), last)
    return bound


def _part_refusal(
    bound: _Bound, name: str, entity_type: str, pseudonym: str
) -> Refusal | None:
    """Q-D: a real first or last name that already has a part keeps it.

    Only for a person and a custom pseudonym of two or more words, split
    with the parts the real names already have, so a part of several words
    is matched whole (QA MW-001, PO A2). One refusal per attempt, the first
    name checked first. The example takes the required part and, for the
    other side, the part that side already has, else the part typed, so the
    example is accepted by this rule (PO F3).
    """
    bound_first, bound_last = _bound_of(bound, name)
    first, last = split_custom_pseudonym(
        pseudonym, entity_type, bound_first, bound_last
    )
    if not first or not last:
        return None
    real_first, real_last = person_parts(name)
    example = f"{bound_first or first} {bound_last or last}"
    if real_first and bound_first is not None and fold(bound_first) != fold(first):
        return Refusal(
            CustomPseudonymRefusal.PART_BOUND,
            pseudonym,
            real_first,
            required=bound_first,
            example=example,
            kind="first",
        )
    if real_last and bound_last is not None and fold(bound_last) != fold(last):
        return Refusal(
            CustomPseudonymRefusal.PART_BOUND,
            pseudonym,
            real_last,
            required=bound_last,
            example=example,
            kind="last",
        )
    return None


def check_custom_pseudonym(
    stored_rows: Iterable[Entity] | None,
    name: str,
    entity_type: str,
    pseudonym: str,
    document_text: str,
    other_customs: Mapping[NameKey, str],
    words: DocumentWords | None = None,
    review_names: Iterable[str] = (),
) -> Refusal | None:
    """The first rule a custom pseudonym breaks, or None if it is accepted.

    Story 10.16 (Codex #8; the PM's reading of Lionel's #8 decision, which
    the PO found faithful): the name itself and the names of the review count
    as real names whatever their capitals. A run of the pseudonym (read as
    Q-C reads it, with Q-I's linking-word rule) that occurs in one of them as
    consecutive whole words, with its own separators, is refused, as a
    capitalised word of the document is. The document's other words in small
    letters still do not count (Q-C).

    Args:
        stored_rows: The decrypted mapping rows, or None when the database
            could not be opened (the stored parts of the checks are skipped)
        name: The name's mapping key (the text sent, after corrections)
        entity_type: The name's type
        pseudonym: The normalized custom pseudonym
        document_text: The document's text (Q-C)
        other_customs: This review's custom pseudonyms of other names,
            keyed by (mapping key, type); the name's own entry is ignored
        words: The document's words, when the caller checks several custom
            pseudonyms of one document (finalization); else read here
        review_names: The mapping keys of the review's other names: when the
            pseudonym is set, every name not rejected; at finalization, the
            names sent (Story 10.16). The name itself is always added

    Returns:
        The refusal (Q1, Q-D, Q2, then Q-C), or None
    """
    rows = list(stored_rows) if stored_rows is not None else []
    for row in rows:  # Q1: the name already has a stored pseudonym
        if row.full_name == name and row.entity_type == entity_type:
            return Refusal(
                CustomPseudonymRefusal.ALREADY_STORED, pseudonym, row.pseudonym_full
            )
    others = {
        key: value for key, value in other_customs.items() if key != (name, entity_type)
    }
    bound = _bound_parts(_stored_bound(rows), others)
    part_refusal = _part_refusal(bound, name, entity_type, pseudonym)
    if part_refusal is not None:  # Q-D
        return part_refusal
    mine = _custom_values(name, entity_type, pseudonym)
    for row in rows:  # Q2: another stored name's pseudonym, or a part of it
        if _clash(mine, _row_values(row)):
            return Refusal(
                CustomPseudonymRefusal.PSEUDONYM_TAKEN, pseudonym, row.full_name
            )
    for (other_name, other_type), other in others.items():  # Q2: this review
        # every beginning and ending, as its stored row will give (PO B1)
        if _clash(mine, _custom_values(other_name, other_type, other)):
            return Refusal(
                CustomPseudonymRefusal.PSEUDONYM_TAKEN, pseudonym, other_name
            )
    if words is None:
        words = document_words(document_text)
    # Story 10.16: the name and the review's names, each read as a short text
    names = [
        document_words(text)
        for text in dict.fromkeys([name, *review_names])
        if text.strip()
    ]
    # Story 10.16 (Codex's review of 463481a): the runs are cut from the
    # pseudonym's composed form (NFC), as document_words reads the document
    # and the names, so a separate accent mark stays inside its word. The
    # refusal keeps the pseudonym as received; nothing typed is changed.
    composed = unicodedata.normalize("NFC", pseudonym)
    for run in _document_runs(composed, entity_type):  # Q2, Q-C, Q-I
        if _capitalised_occurrence(run, words) or any(
            _occurrence(run, name_words, capitalised=False) for name_words in names
        ):
            return Refusal(
                CustomPseudonymRefusal.REAL_NAME, pseudonym, run, in_document=True
            )
    stored_names = {fold(row.full_name) for row in rows}
    for run in _word_runs(pseudonym, entity_type):  # Q-C2: a stored full name
        if fold(run) in stored_names:
            return Refusal(CustomPseudonymRefusal.REAL_NAME, pseudonym, run)
    return None


def _engine_ambiguity(name: str, entity_type: str) -> tuple[bool, str | None]:
    """``is_ambiguous`` and its reason, as the pseudonym engine sets them for
    a person (PO R9): one word, or three or more words, is ambiguous."""
    if entity_type != "PERSON":
        return False, None
    words = name.split()
    if len(words) == 1:
        return True, "Standalone component without full name context"
    if len(words) >= 3:
        return True, "Multiple word name - parsing uncertain"
    return False, None


def custom_entity_fields(
    name: str,
    entity_type: str,
    pseudonym: str,
    stored_rows: Iterable[Entity] = (),
    other_customs: Mapping[NameKey, str] | None = None,
) -> dict[str, Any]:
    """The name parts, pseudonym parts and ambiguity of a custom row (AC2).

    For a person with a custom pseudonym of two or more words: the real
    first and last name as the engine reads them, and the pseudonym's parts
    as ``split_custom_pseudonym`` splits it, with the parts the real names
    already have in ``stored_rows`` or in this run's other custom
    pseudonyms (AC17 (b)). On a one-word name the last part has no real
    counterpart (``last_name`` None). A one-word custom pseudonym, a place
    and an organisation have no parts.
    """
    fields: dict[str, Any] = {
        "first_name": None,
        "last_name": None,
        "pseudonym_first": None,
        "pseudonym_last": None,
    }
    others = {
        key: value
        for key, value in (other_customs or {}).items()
        if key != (name, entity_type)
    }
    bound = _bound_parts(_stored_bound(list(stored_rows)), others)
    first, last = split_custom_pseudonym(
        pseudonym, entity_type, *_bound_of(bound, name)
    )
    if first and last:
        real_first, real_last = person_parts(name)
        fields.update(
            first_name=real_first,
            last_name=real_last,
            pseudonym_first=first,
            pseudonym_last=last,
        )
    is_ambiguous, reason = _engine_ambiguity(name, entity_type)
    fields["is_ambiguous"] = is_ambiguous
    fields["ambiguity_reason"] = reason
    return fields


# A real first or last name in a role: (folded real word, "first" or "last").
Owner = tuple[str, str]
# The values a generated pseudonym must not take, each with the real words
# that may take it, in their role (``untracked_custom_values``).
CustomReservations = Mapping[str, frozenset[Owner]]


def untracked_custom_values(rows: Iterable[Entity]) -> dict[str, frozenset[Owner]]:
    """The values of custom pseudonyms a later generated pseudonym must not
    take (10.11 AC19), each with its owners (Story 10.16, Codex #6).

    For each custom row of a person: every beginning and every ending of its
    pseudonym (one or more whole words, the whole one included), folded.
    Each value's owners are the row's real words, in a role, that already
    have that value as their part in that role in ``rows``: its own stored
    parts, or the part the same real word has in another row (QA GUARD-001).
    A row's real words are ``person_parts`` of its ``full_name``: the first
    name in the role "first" and the last name in the role "last"; a
    one-word name in both roles, since the engine matches a lone word as a
    first or a last name (``_handle_standalone_component``). Roles are kept
    apart and real words are compared folded, so a value stays reserved for
    another role and another spelling, which the library does not track
    (it compares exact spellings, per role). Pass every stored row, with
    this run's custom rows.
    """
    rows = list(rows)
    # (folded real first or last name, role) -> the folded parts it has
    parts_of: dict[Owner, set[str]] = {}
    for row in rows:
        if row.entity_type != "PERSON":
            continue
        if row.first_name and row.pseudonym_first:
            parts_of.setdefault((fold(row.first_name), "first"), set()).add(
                fold(row.pseudonym_first)
            )
        if row.last_name and row.pseudonym_last:
            parts_of.setdefault((fold(row.last_name), "last"), set()).add(
                fold(row.pseudonym_last)
            )
    reserved: dict[str, set[Owner]] = {}
    for row in rows:
        if row.theme != CUSTOM_THEME or row.entity_type != "PERSON":
            continue
        real_first, real_last = person_parts(row.full_name)
        own: list[Owner] = []
        if real_first and real_last:
            own = [(fold(real_first), "first"), (fold(real_last), "last")]
        elif real_first:
            own = [(fold(real_first), "first"), (fold(real_first), "last")]
        words = row.pseudonym_full.split()
        for size in range(1, len(words) + 1):
            for value in (" ".join(words[:size]), " ".join(words[-size:])):
                folded = fold(value)
                owners = reserved.setdefault(folded, set())
                owners.update(
                    owner for owner in own if folded in parts_of.get(owner, ())
                )
    return {value: frozenset(owners) for value, owners in reserved.items()}


def _reserved_for(
    value: str, real: str | None, role: str, reserved: CustomReservations
) -> bool:
    """Whether a generated part may not take ``value``: it is reserved, and
    the part's real word (None when it has none) does not own it in
    ``role``."""
    owners = reserved.get(fold(value))
    if owners is None:
        return False
    return real is None or (fold(real), role) not in owners


def takes_custom_value(entity: Entity, reserved: CustomReservations) -> bool:
    """Whether a generated row takes a value of a custom pseudonym that it
    may not (Story 10.16, AC2; Codex #6).

    Its first part, unless its real first name owns it as a first name; its
    last part, unless its real last name owns it as a last name (a lone name
    whose last part the engine matched has no first part, and its one word
    is its real last name; a lone name's freshly drawn last part has no real
    word); its full pseudonym, when it differs from its parts (several
    parts, an organisation or a place), at all. The reuse 10.11 requires (a
    part bound to the same real word, in the same role) is the only one
    allowed.
    """
    if not reserved:
        return False
    first, last = entity.pseudonym_first, entity.pseudonym_last
    if first and _reserved_for(first, entity.first_name, "first", reserved):
        return True
    if last:
        real_last = entity.last_name or (entity.first_name if not first else None)
        if _reserved_for(last, real_last, "last", reserved):
            return True
    full = entity.pseudonym_full
    if full and fold(full) not in {fold(part) for part in (first, last) if part}:
        return fold(full) in reserved
    return False


# The command line's refusal lines (Lionel's Q-A, 2026-10-15: the approved
# English texts with plain quotes; the first names the command line's way to
# remove a name).
_CLI_ALREADY_STORED = (
    "This name already has a pseudonym in your mapping database: '{other}'. "
    "That pseudonym is kept. To choose another one, remove the name with "
    "'gdpr-pseudo delete-mapping', then process the document again."
)
_CLI_FIRST_PART = (
    "The first name '{other}' is already replaced by '{required}'. "
    "Your pseudonym must therefore have '{required}' as its first name, "
    "for example '{example}'."
)
_CLI_LAST_PART = (
    "The last name '{other}' is already replaced by '{required}'. "
    "Your pseudonym must therefore have '{required}' as its last name, "
    "for example '{example}'."
)
_CLI_TAKEN = (
    "'{pseudonym}' (or a part of it) is already used for another name: "
    "'{other}'. Two different names cannot share a pseudonym: choose another one."
)
_CLI_REAL_NAME = (
    "'{other}' appears in this document or in your mapping database, so "
    "'{pseudonym}' could be taken for a real name. Choose another one."
)


def cli_refusal_message(refusal: Refusal) -> str:
    """The command line's line for a refusal (Lionel's Q-A)."""
    if refusal.reason is CustomPseudonymRefusal.ALREADY_STORED:
        template = _CLI_ALREADY_STORED
    elif refusal.reason is CustomPseudonymRefusal.PART_BOUND:
        template = _CLI_FIRST_PART if refusal.kind == "first" else _CLI_LAST_PART
    elif refusal.reason is CustomPseudonymRefusal.PSEUDONYM_TAKEN:
        template = _CLI_TAKEN
    else:
        template = _CLI_REAL_NAME
    return template.format(
        pseudonym=refusal.pseudonym,
        other=refusal.other,
        required=refusal.required,
        example=refusal.example,
    )


# The finalization error's reasons (Lionel's Q-A): English, no names.
_FINALIZATION_REASONS = {
    CustomPseudonymRefusal.ALREADY_STORED: (
        "the name now has a pseudonym in the mapping database"
    ),
    CustomPseudonymRefusal.PART_BOUND: (
        "the first or last name now has a different part in the mapping database"
    ),
    CustomPseudonymRefusal.PSEUDONYM_TAKEN: (
        "it, or a part of it, is now used for another name"
    ),
    CustomPseudonymRefusal.REAL_NAME: "it now matches a name in the mapping database",
}


# The fifth reason (Lionel's 10.16 Q1, "Add the new reason (Rec.)",
# 2026-10-16), for a REAL_NAME refusal whose words are a name of this
# document; a full name stored in the database keeps 10.11's reason.
_IN_DOCUMENT_REASON = "it now matches a name in this document"


def finalization_message(refusal: Refusal) -> str:
    """The finalization error's message (Lionel's Q-A and 10.16 Q1): no
    name, no pseudonym. The user reads it after the prefix
    "CustomPseudonymError: "."""
    if refusal.reason is CustomPseudonymRefusal.REAL_NAME and refusal.in_document:
        reason = _IN_DOCUMENT_REASON
    else:
        reason = _FINALIZATION_REASONS[refusal.reason]
    return (
        "A pseudonym you chose can no longer be used: "
        f"{reason}. Nothing was written."
    )
