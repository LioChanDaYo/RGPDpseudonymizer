"""Saved names an earlier version cut or kept a title in, rebuilt backwards
(Story 10.20, v1.10; the second Codex review of 56feb3d).

Before Story 10.20 the mapping key was built from the text as read. A name
whose accents were stored as separate marks went through the title pattern
(``FRENCH_TITLE_PATTERN``) with marks that are not word characters, so the
pattern could take off letters of the name (« Mélora » saved as « lora »
after a lone mark, « Zorbôme Quentrel » saved as « Zorbô » + « Quentrel »)
or keep a « Maître » it could not see. Such a row stays as saved (Lionel,
Qa): nothing is rewritten.

The exact keyed lookups reach it by replaying the old steps forward
(``mapping_key.former_keys``). The two comparisons that scan every saved
name, the saved-real-name check (Q-C2) and the searches, compare each saved
name as saved **and** each text it may stand for, rebuilt backwards from the
old pattern. The repair only adds texts; it never replaces the saved name.

Where the old pattern left a sign in a saved name:

- S1, a mark that starts a word (or follows a character that is neither a
  word character nor a mark): a title word ended right before it, its last
  letter carrying the mark.
- S2, a mark followed by a word character: a title word and its spaces
  were taken off right after the mark.
- S3, a mark at the end of the last word, or before a character that is not
  a word character (another mark included): a title word was taken off right
  after it, leaving no sign. In the saved-real-name check only
  (``END_CUTS``; Lionel, 2026-10-22, end cut "A: Refuse them too (Rec.)").
- S4, a word « Maître » with its circumflex: the pattern's « Maître » is
  composed, so a decomposed one was kept; the name may stand for itself
  without it. « Maitre » and « MAITRE » never matched the pattern: they
  are names.
- S5, a place whose first word is « à »: the preposition pattern's « à »
  is composed and anchored at the start; the place may stand for itself
  without it (never inside a word, as in a hyphenated place).

This module imports only ``utils/french_patterns.py`` and
``utils/text_form.py``.
"""

from __future__ import annotations

import functools
import itertools
import re
import unicodedata
from collections.abc import Iterable

from gdpr_pseudonymizer.utils.french_patterns import FRENCH_TITLE_PATTERN
from gdpr_pseudonymizer.utils.text_form import composed, is_mark, mark_class

# Lionel, 2026-10-22, end cut "A: Refuse them too (Rec.)": the saved-real-name
# check also tries a title word put back after a mark that ends a saved name
# or stands before a non-word character (S3). The lookups and the searches
# never do: such a saved name is also the correct name of someone else.
END_CUTS = True

# The shape of FRENCH_TITLE_PATTERN the title words are read from.
_HEAD = r"\b(?:"
_TAIL = r")(?!\w)\s*"
_OPTIONAL_DOT = r"\.?"
_TITLE_WORD = re.compile(r"[^\W\d_]+\.?")

_MAITRE = "maitre"  # fold("Maître"), in the patterns over folded text
_MAITRE_WORD = "maître"  # the pattern's « Maître », casefolded
_A = "à"
_WORD_CHAR = re.compile(r"\w")

# Patterns and search texts kept per saved name (a database of 10,000 names
# fits, so a second check or search reuses them).
_CACHE_SIZE = 1 << 16

_S1, _S2, _S3 = "S1", "S2", "S3"


@functools.cache
def title_words() -> tuple[str, ...]:
    """The title words of ``FRENCH_TITLE_PATTERN``, read from the pattern
    itself: each alternative, one ending in ``\\.?`` with and without its
    « . » (20 words).

    Raises:
        ValueError: The pattern no longer has the shape the old names were
            cut with, so the repair cannot be read from it.
    """
    pattern = FRENCH_TITLE_PATTERN
    if not (pattern.startswith(_HEAD) and pattern.endswith(_TAIL)):
        raise ValueError(
            "FRENCH_TITLE_PATTERN no longer starts with "
            f"{_HEAD!r} and ends with {_TAIL!r}: the saved-name repair "
            "(core/legacy_names.py) must be read again from it"
        )
    words: list[str] = []
    for alternative in pattern[len(_HEAD) : -len(_TAIL)].split("|"):
        if alternative.endswith(_OPTIONAL_DOT):
            base = alternative[: -len(_OPTIONAL_DOT)]
            choices = [base, base + "."]
        else:
            choices = [alternative]
        for word in choices:
            if not _TITLE_WORD.fullmatch(word):
                raise ValueError(
                    f"FRENCH_TITLE_PATTERN alternative {alternative!r} is not a "
                    "plain word: the saved-name repair (core/legacy_names.py) "
                    "must be read again from it"
                )
        words += choices
    return tuple(words)


def fold(text: str) -> str:
    """Comparison form, as ``custom_pseudonym.fold`` (Q-C): accents and
    capitals ignored, spaces collapsed."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


@functools.cache
def _mark_search() -> re.Pattern[str]:
    return re.compile(f"[{mark_class()}]")


@functools.cache
def _titles_regex() -> str:
    """The folded title words as one alternation (longest first)."""
    folded = sorted(
        {fold(word) for word in title_words()}, key=lambda word: (-len(word), word)
    )
    return "|".join(re.escape(word) for word in folded)


def _is_word_char(char: str) -> bool:
    return _WORD_CHAR.match(char) is not None


def _is_maitre(word: str) -> bool:
    """Whether a word is « Maître » with its circumflex, in any case,
    composed or decomposed (S4): the only form of the word the old pattern
    could leave in a name. « Maitre » and « MAITRE » never matched it; they
    are names (QA's REPAIR-001)."""
    return composed(word).casefold() == _MAITRE_WORD


def _droppable(words: list[str], entity_type: str) -> list[int]:
    """The positions of the words a saved name may stand for itself
    without: each « Maître » (S4), and a place's first word « à » (S5)."""
    positions = [index for index, word in enumerate(words) if _is_maitre(word)]
    if (
        entity_type == "LOCATION"
        and words
        and composed(words[0]).lower() == _A
        and 0 not in positions
    ):
        positions.insert(0, 0)
    return positions


@functools.lru_cache(maxsize=_CACHE_SIZE)
def is_legacy(full_name: str, entity_type: str) -> bool:
    """Whether a saved name may stand for another text: it holds a mark, a
    word « Maître » with its circumflex (any case, composed or decomposed),
    or, for a place, a first word « à »."""
    if _mark_search().search(full_name):
        return True
    return bool(_droppable(full_name.split(), entity_type))


def _sites(word: str, last_word: bool) -> list[tuple[int, str]]:
    """The sites of a saved word where the old pattern took a title word
    off, each as (the position of its mark, S1, S2 or S3)."""
    sites: list[tuple[int, str]] = []
    for found in _mark_search().finditer(word):
        index = found.start()
        before = word[index - 1] if index else ""
        after = word[index + 1] if index + 1 < len(word) else ""
        if not before or not (_is_word_char(before) or is_mark(before)):
            sites.append((index, _S1))
        if after and _is_word_char(after):
            sites.append((index, _S2))
        elif END_CUTS and (after or last_word):
            sites.append((index, _S3))
    return sites


def _word_choices(words: list[str], entity_type: str) -> list[tuple[int, ...]]:
    """The positions of the words kept, for every way of leaving out the
    droppable words (S4, S5) or not; never every word."""
    droppable = _droppable(words, entity_type)
    choices: list[tuple[int, ...]] = []
    for dropped in itertools.product((False, True), repeat=len(droppable)):
        left_out = {position for position, drop in zip(droppable, dropped) if drop}
        kept = tuple(index for index in range(len(words)) if index not in left_out)
        if kept:
            choices.append(kept)
    return choices


def _word_regex(word: str, last_word: bool) -> tuple[str, list[str]]:
    """A saved word as a regex over folded text, a title word optional at
    each site, and its literal pieces between sites."""
    titles = _titles_regex()
    kinds: dict[int, list[str]] = {}
    for index, kind in _sites(word, last_word):
        kinds.setdefault(index, []).append(kind)
    regex: list[str] = []
    pieces: list[str] = []
    start = 0
    for index, site in sorted(kinds.items()):
        piece = fold(word[start:index])
        pieces.append(piece)
        regex.append(re.escape(piece))
        start = index + 1
        if _S1 in site:
            regex.append(f"(?:{titles})?")
        if _S2 in site:
            if _is_maitre(word[start:]):
                # S4 after an S2 site: the « Maître » joined to the word
                # before it may be left out, a title word in its place
                regex.append(f"(?:(?:{titles})(?: {_MAITRE})?|{_MAITRE})")
                return "".join(regex), [p for p in pieces if p]
            regex.append(f"(?:(?:{titles}) )?")
        if _S3 in site:
            regex.append(f"(?:{titles})?")
    piece = fold(word[start:])
    pieces.append(piece)
    regex.append(re.escape(piece))
    return "".join(regex), [p for p in pieces if p]


@functools.lru_cache(maxsize=_CACHE_SIZE)
def legacy_pattern(full_name: str, entity_type: str) -> re.Pattern[str]:
    """Every whole text a saved name may stand for, as one regex over folded
    text (``fold``), compared with ``fullmatch``: at each S1 and S3 site a
    title word optional, at each S2 site a title word and a space optional,
    any number of sites at once; the word choices (S4, S5) as
    alternatives."""
    words = full_name.split()
    regexes = [
        _word_regex(word, index == len(words) - 1)[0]
        for index, word in enumerate(words)
    ]
    choices = dict.fromkeys(
        " ".join(regexes[index] for index in kept)
        for kept in _word_choices(words, entity_type)
    )
    return re.compile("(?:" + "|".join(choices) + ")")


@functools.lru_cache(maxsize=_CACHE_SIZE)
def legacy_piece(full_name: str, entity_type: str) -> str:
    """The longest piece of letters of a saved name between its sites, in a
    word it never leaves out: every text ``legacy_pattern`` matches holds it
    (a quick test before the pattern)."""
    words = full_name.split()
    droppable = set(_droppable(words, entity_type))
    pieces = [
        piece
        for index, word in enumerate(words)
        if index not in droppable
        for piece in _word_regex(word, index == len(words) - 1)[1]
    ]
    return max(pieces, key=len, default="")


def is_saved_real_name(run: str, legacy_rows: Iterable[tuple[str, str]]) -> bool:
    """Whether a run of words of a custom pseudonym is a whole text one of
    these saved names may stand for, accents and capitals ignored (Q-C2;
    Lionel's 10.11 Q-C2 "Whole names only (Rec.)").

    Args:
        run: A run of whole words of the pseudonym
        legacy_rows: The (full name, type) of the saved names ``is_legacy``
            keeps

    Returns:
        True when the run is refused
    """
    folded = fold(run)
    return any(
        legacy_piece(full_name, entity_type) in folded
        and legacy_pattern(full_name, entity_type).fullmatch(folded) is not None
        for full_name, entity_type in legacy_rows
    )


@functools.lru_cache(maxsize=_CACHE_SIZE)
def legacy_search_texts(
    full_name: str, entity_type: str
) -> tuple[tuple[str, int, int], ...]:
    """The texts a search compares with a saved name: each word choice (S4,
    S5), alone and with one S1 or S2 site repaired by one title word,
    composed and lowercased, each with the span of what was put back
    (empty when nothing was). S3 sites are never used.

    One site at a time: a name with two repaired sites is listed by a part
    of it, not by its full name.
    """
    words = full_name.split()
    texts: list[tuple[str, int, int]] = []
    for kept in _word_choices(words, entity_type):
        chosen = [(index, words[index]) for index in kept]
        texts.append((composed(" ".join(word for _, word in chosen)).lower(), 0, 0))
        for position, (index, word) in enumerate(chosen):
            before = " ".join(w for _, w in chosen[:position])
            before = before + " " if before else ""
            after = " ".join(w for _, w in chosen[position + 1 :])
            after = " " + after if after else ""
            for mark, kind in _sites(word, index == len(words) - 1):
                if kind == _S3:
                    continue
                # Composed in pieces cut before a letter or a space, where
                # composing never joins two characters: the text composed
                # whole, at a fraction of the cost
                if kind == _S1:
                    # the title word put back before the mark, its last
                    # letter carrying it
                    head = composed(before + word[:mark]).lower()
                    tail = composed(after).lower()
                    for title in title_words():
                        put_back = composed(title + word[mark]).lower()
                        repaired = composed(title + word[mark:]).lower()
                        start = len(head)
                        texts.append(
                            (head + repaired + tail, start, start + len(put_back))
                        )
                else:
                    # the title word and a space put back after the mark
                    head = composed(before + word[: mark + 1]).lower()
                    tail = composed(word[mark + 1 :] + after).lower()
                    for title in title_words():
                        put_back = (title + " ").lower()
                        start = len(head)
                        texts.append(
                            (head + put_back + tail, start, start + len(put_back))
                        )
    return tuple(dict.fromkeys(texts))


def matches_search(search_lower: str, full_name: str, entity_type: str) -> bool:
    """Whether a search lists a saved name: the search (composed and
    lowercased, as typed) is a part of the saved name as saved, composed and
    lowercased, or of a text it may stand for (``legacy_search_texts``),
    unless that part lies wholly inside what was put back (a search for
    « Madame » alone does not list every old name).

    Args:
        search_lower: The search, composed and lowercased
        full_name: The saved name, as saved
        entity_type: Its type

    Returns:
        True when the row is listed
    """
    if search_lower in composed(full_name).lower():
        return True
    if not search_lower or not is_legacy(full_name, entity_type):
        return False
    size = len(search_lower)
    for text, start, end in legacy_search_texts(full_name, entity_type):
        found = text.find(search_lower)
        while found != -1:
            if not (start <= found and found + size <= end):
                return True
            found = text.find(search_lower, found + 1)
    return False
