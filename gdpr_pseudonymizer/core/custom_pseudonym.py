"""Custom pseudonyms set during validation (Story 10.11).

A custom pseudonym is the pseudonym a user chooses for a name during
validation ("Changer le pseudonyme" in the desktop app, [C] in the command
line). It belongs to a name: the mapping key of the text sent to
finalization, and its type (Story 10.7).

This module is shared by the desktop review, the command-line review and
finalization:

- the custom pseudonym is normalized like a mapping key (titles and, for a
  place, a leading preposition removed; spaces collapsed);
- for a person it is split at its last space into a first-name part and a
  last-name part (Lionel's Q4); a one-word pseudonym has no parts;
- it is checked against Lionel's rules, in this order: a name that already
  has a stored pseudonym keeps it (Q1); a real first or last name that
  already has a part keeps it (Q-D); it may not be, in whole or in part,
  another name's pseudonym (Q2); it may not be a real name: a capitalised
  word or words of the document, or a full name stored in the mapping
  database (Q2, Q-C, Q-C2). Capitals, accents and repeated spaces are
  ignored when comparing (Q-C).

Nothing here logs or raises with a name or a pseudonym in it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from gdpr_pseudonymizer.core.mapping_key import mapping_key

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
    """

    reason: CustomPseudonymRefusal
    pseudonym: str
    other: str
    required: str = ""
    example: str = ""
    kind: str = ""


# The command line's set-time check: (name's mapping key, type, normalized
# custom pseudonym, this review's custom pseudonyms of other names) -> the
# refusal, or None.
PseudonymChecker = Callable[[str, str, str, Mapping[NameKey, str]], Refusal | None]


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
    pseudonym: str, entity_type: str
) -> tuple[str | None, str | None]:
    """A person's custom pseudonym split at its last space (Lionel's Q4).

    Returns (first-name part, last-name part); (None, None) for a one-word
    pseudonym and for any other type.
    """
    if entity_type != "PERSON":
        return None, None
    first, separator, last = pseudonym.rpartition(" ")
    if not separator or not first or not last:
        return None, None
    return first, last


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
    """A stored row's pseudonym values, each with the real text it stands for."""
    values: list[_Value] = [(row.pseudonym_full, row.full_name, True)]
    if row.pseudonym_first:
        values.append((row.pseudonym_first, row.first_name, False))
    if row.pseudonym_last:
        values.append((row.pseudonym_last, row.last_name, False))
    return values


def _custom_values(name: str, entity_type: str, pseudonym: str) -> list[_Value]:
    """A custom pseudonym's values: the full one for the name, and for a
    person both parts after the split, each with the real first or last name
    it stands for. The last part on a one-word name stands for no real text
    (PO R1)."""
    values: list[_Value] = [(pseudonym, name, True)]
    first, last = split_custom_pseudonym(pseudonym, entity_type)
    if first and last:
        real_first, real_last = person_parts(name)
        values.append((first, real_first, False))
        values.append((last, real_last, False))
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


_WORD = re.compile(r"\w+")
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


def _capitalised_occurrence(candidate: str, document_text: str) -> bool:
    """Whether ``candidate`` occurs in the document as a real name (Q-C).

    Its words occur as consecutive whole words of the document, with the
    candidate's own separators between them, the first of them starting with
    a capital letter there (found by the detector or not; a sentence-initial
    word counts). Capitals and accents are ignored when comparing.
    """
    wanted_tokens = list(_WORD.finditer(candidate))
    if not wanted_tokens:
        return False
    wanted = [fold(token.group()) for token in wanted_tokens]
    wanted_gaps = [
        _separator_kind(candidate[a.end() : b.start()])
        for a, b in zip(wanted_tokens, wanted_tokens[1:])
    ]
    tokens = list(_WORD.finditer(document_text))
    folded = [fold(token.group()) for token in tokens]
    size = len(wanted)
    for start in range(len(tokens) - size + 1):
        if folded[start : start + size] != wanted:
            continue
        if not tokens[start].group()[0].isupper():
            continue
        gaps = [
            _separator_kind(document_text[tokens[j].end() : tokens[j + 1].start()])
            for j in range(start, start + size - 1)
        ]
        if gaps == wanted_gaps:
            return True
    return False


def _bound_parts(
    rows: list[Entity], other_customs: Mapping[NameKey, str]
) -> dict[tuple[str, str], str]:
    """(folded real first or last name, "first" or "last") -> the part it
    already has: from the stored person rows, then from this review's other
    custom pseudonyms. The first one read wins (Dev Notes, PO F6)."""
    bound: dict[tuple[str, str], str] = {}
    for row in rows:
        if row.entity_type != "PERSON":
            continue
        if row.first_name and row.pseudonym_first:
            bound.setdefault((fold(row.first_name), "first"), row.pseudonym_first)
        if row.last_name and row.pseudonym_last:
            bound.setdefault((fold(row.last_name), "last"), row.pseudonym_last)
    for (other_name, other_type), other in other_customs.items():
        first, last = split_custom_pseudonym(other, other_type)
        if not first or not last:
            continue
        real_first, real_last = person_parts(other_name)
        if real_first:
            bound.setdefault((fold(real_first), "first"), first)
        if real_last:
            bound.setdefault((fold(real_last), "last"), last)
    return bound


def _part_refusal(
    rows: list[Entity],
    others: Mapping[NameKey, str],
    name: str,
    entity_type: str,
    pseudonym: str,
) -> Refusal | None:
    """Q-D: a real first or last name that already has a part keeps it.

    Only for a person and a custom pseudonym of two or more words. One
    refusal per attempt, the first name checked first. The example takes the
    required part and, for the other side, the part that side already has,
    else the part typed, so the example is accepted by this rule (PO F3).
    """
    first, last = split_custom_pseudonym(pseudonym, entity_type)
    if not first or not last:
        return None
    bound = _bound_parts(rows, others)
    real_first, real_last = person_parts(name)
    bound_first = bound.get((fold(real_first), "first")) if real_first else None
    bound_last = bound.get((fold(real_last), "last")) if real_last else None
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
) -> Refusal | None:
    """The first rule a custom pseudonym breaks, or None if it is accepted.

    Args:
        stored_rows: The decrypted mapping rows, or None when the database
            could not be opened (the stored parts of the checks are skipped)
        name: The name's mapping key (the text sent, after corrections)
        entity_type: The name's type
        pseudonym: The normalized custom pseudonym
        document_text: The document's text (Q-C)
        other_customs: This review's custom pseudonyms of other names,
            keyed by (mapping key, type); the name's own entry is ignored

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
    part_refusal = _part_refusal(rows, others, name, entity_type, pseudonym)
    if part_refusal is not None:  # Q-D
        return part_refusal
    mine = _custom_values(name, entity_type, pseudonym)
    for row in rows:  # Q2: another stored name's pseudonym, or a part of it
        if _clash(mine, _row_values(row)):
            return Refusal(
                CustomPseudonymRefusal.PSEUDONYM_TAKEN, pseudonym, row.full_name
            )
    for (other_name, other_type), other in others.items():  # Q2: this review
        if _clash(mine, _custom_values(other_name, other_type, other)):
            return Refusal(
                CustomPseudonymRefusal.PSEUDONYM_TAKEN, pseudonym, other_name
            )
    candidates = [value for value, _real, _full in mine]
    for candidate in candidates:  # Q2, Q-C: a real name of the document
        if _capitalised_occurrence(candidate, document_text):
            return Refusal(CustomPseudonymRefusal.REAL_NAME, pseudonym, candidate)
    stored_names = {fold(row.full_name) for row in rows}
    for candidate in candidates:  # Q-C2: a full name stored in the database
        if fold(candidate) in stored_names:
            return Refusal(CustomPseudonymRefusal.REAL_NAME, pseudonym, candidate)
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


def custom_entity_fields(name: str, entity_type: str, pseudonym: str) -> dict[str, Any]:
    """The name parts, pseudonym parts and ambiguity of a custom row (AC2).

    For a person with a custom pseudonym of two or more words: the real
    first and last name as the engine reads them, and the pseudonym's parts
    split at its last space. On a one-word name the last part has no real
    counterpart (``last_name`` None). A one-word custom pseudonym, a place
    and an organisation have no parts.
    """
    fields: dict[str, Any] = {
        "first_name": None,
        "last_name": None,
        "pseudonym_first": None,
        "pseudonym_last": None,
    }
    first, last = split_custom_pseudonym(pseudonym, entity_type)
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


def untracked_custom_values(rows: Iterable[Entity]) -> set[str]:
    """Folded values of custom rows that the library does not track (AC3).

    The library marks a part as used only when it is stored next to its real
    part. A one-word custom pseudonym of a person, and a part stored without
    its real counterpart (the last part on a one-word name), are not marked,
    so finalization keeps them here and never generates them again.
    """
    taken: set[str] = set()
    for row in rows:
        if row.theme != CUSTOM_THEME or row.entity_type != "PERSON":
            continue
        if not row.pseudonym_first and not row.pseudonym_last:
            if " " not in row.pseudonym_full:
                taken.add(fold(row.pseudonym_full))
        if row.pseudonym_first and not row.first_name:
            taken.add(fold(row.pseudonym_first))
        if row.pseudonym_last and not row.last_name:
            taken.add(fold(row.pseudonym_last))
    return taken


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


def finalization_message(refusal: Refusal) -> str:
    """The finalization error's message (Lionel's Q-A): no name, no
    pseudonym. The user reads it after the prefix "CustomPseudonymError: "."""
    return (
        "A pseudonym you chose can no longer be used: "
        f"{_FINALIZATION_REASONS[refusal.reason]}. Nothing was written."
    )
