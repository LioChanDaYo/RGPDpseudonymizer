"""Saved names an earlier version cut or kept a title in, rebuilt backwards
(Story 10.20, v1.10; the second Codex review of 56feb3d; v1.18 to v1.21).

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

The old key and today's key differ only where the two forms of a name make
the patterns match differently: next to an accent mark, and at « Maître »
and « à », the only words of the two patterns with an accent (Story 10.20,
v1.19 and v1.21, the table of the AC precisions):

- S1, a mark that starts a word (or follows a character that is neither a
  word character nor a mark): one or more title words ended right before
  it, the last one's last letter carrying the mark.
- S2, a mark followed by a word character: one or more title words and
  their spaces were taken off right after the mark.
- S3, a mark at the end of the last word, or before a character that is not
  a word character (another mark included): one or more title words were
  taken off right after it, leaving no sign (with the spaces before a
  « - » or a « . »). In the saved-real-name check only (``END_CUTS``;
  Lionel, 2026-10-22, end cut "A: Refuse them too (Rec.)").
- S4, « Maître » with its circumflex: the pattern's « Maître » is composed,
  so today's step takes it off wherever the pattern finds it and the old
  one never did. A whole word may be left out; so may one inside a word,
  joined by a character that is neither a letter nor a mark
  (« Maître-Zorbal »), with the space after it, or glued after a mark when
  title words are put back there. « Maitre » and « MAITRE » never matched
  the pattern: they are names (QA's REPAIR-001).
- S5, a place whose first word is « à » (the preposition pattern's « à »
  is composed and anchored at the start; never inside a word, as in a
  hyphenated place); and, after « Maître » words left out at the start of
  a place, the preposition today's step then takes off there.

This module imports only ``utils/french_patterns.py`` and
``utils/text_form.py``.
"""

from __future__ import annotations

import functools
import itertools
import re
import unicodedata
from collections.abc import Iterable, Iterator

from gdpr_pseudonymizer.utils.french_patterns import (
    FRENCH_PREPOSITION_PATTERN,
    FRENCH_TITLE_PATTERN,
)
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

# The shape of FRENCH_PREPOSITION_PATTERN the prepositions are read from.
_PREP_HEAD = r"^[\s]*(?:(?:"
_PREP_MIDDLE = r")|(?:"
_PREP_TAIL = r")\s+)"
_PREP_WORD = re.compile(r"[^\W\d_]+'?")

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


@functools.cache
def preposition_words() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The elisions and the words of ``FRENCH_PREPOSITION_PATTERN``, read
    from the pattern itself: ((« d' », « l' »), (« aux », « au », « des »,
    « du », « de », « à », « en »)).

    Raises:
        ValueError: The pattern no longer has the shape the old names were
            cut with, so the repair cannot be read from it.
    """
    pattern = FRENCH_PREPOSITION_PATTERN
    if not (
        pattern.startswith(_PREP_HEAD)
        and pattern.endswith(_PREP_TAIL)
        and pattern.count(_PREP_MIDDLE) == 1
    ):
        raise ValueError(
            "FRENCH_PREPOSITION_PATTERN no longer has the shape "
            f"{_PREP_HEAD!r} ... {_PREP_MIDDLE!r} ... {_PREP_TAIL!r}: the "
            "saved-name repair (core/legacy_names.py) must be read again "
            "from it"
        )
    elisions, words = pattern[len(_PREP_HEAD) : -len(_PREP_TAIL)].split(_PREP_MIDDLE)
    found = (tuple(elisions.split("|")), tuple(words.split("|")))
    for word in found[0] + found[1]:
        if not _PREP_WORD.fullmatch(word):
            raise ValueError(
                f"FRENCH_PREPOSITION_PATTERN alternative {word!r} is not a "
                "plain word: the saved-name repair (core/legacy_names.py) "
                "must be read again from it"
            )
    return found


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


@functools.cache
def _run_regex() -> str:
    """What the old step could take off at one place, folded: one or more
    title words in a row, one space between two of them (Story 10.20, v1.18;
    the third Codex review, P0-a).

    Derived from ``strip_french_titles``: it replaces every match of
    ``FRENCH_TITLE_PATTERN`` (``\\b``, a title word, ``(?!\\w)``, ``\\s*``)
    with nothing, case ignored, strips the ends and repeats until the text
    stops changing.

    - Matches side by side form one stretch, taken off together: T1 S1 ...
      Tk Sk, each Ti a title word and Si the spaces it ate. Inside a stretch
      each Si holds at least one space: with none, the next title word's
      first letter would follow Ti, and ``(?!\\w)`` after Ti, or ``\\b``
      before the next word, would fail.
    - Sk is all the spaces there were (``\\s*`` is greedy). It is empty when
      a non-word character follows (an accent mark, « - », « . », the end)
      and holds a space before a word character.
    - A second pass takes nothing more: a title word the first pass left
      has a word character beside it, and a pass never takes one off.
    - On text whose accents are separate marks, a mark is not a word
      character: ``\\b`` holds after a mark and ``(?!\\w)`` before one.

    Folded (accents and capitals ignored, spaces collapsed), a stretch
    reads « t1 ... tk », one space between two words: this regex.
    """
    titles = _titles_regex()
    return f"(?:{titles})(?: (?:{titles}))*"


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
    """The sites of a saved word where the old pattern took title words
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


def _joined_titles(word: str) -> dict[int, int]:
    """The « Maître » inside a saved word that is not one itself (S4), each
    as start -> end: in each run of word characters and marks, the end of
    the run (before a character that is neither, or the word's end) when it
    reads « Maître » from the run's start (the word's start, or after a
    character that is neither) or from right after a mark followed by a word
    character (an S2 site). Today's pattern takes such a « Maître » off
    (``\\b`` before it, ``(?!\\w)`` after it); the old one never did."""
    found: dict[int, int] = {}
    if _is_maitre(word):
        return found
    index = 0
    while index < len(word):
        if not (_is_word_char(word[index]) or is_mark(word[index])):
            index += 1
            continue
        end = index
        while end < len(word) and (_is_word_char(word[end]) or is_mark(word[end])):
            end += 1
        starts = [index] + [
            position + 1
            for position in range(index, end - 1)
            if is_mark(word[position]) and _is_word_char(word[position + 1])
        ]
        for start in starts:
            if _is_maitre(word[start:end]):
                found[start] = end
                break
        index = end
    return found


def _span_regex(
    word: str, low: int, high: int, kinds: dict[int, list[str]]
) -> tuple[str, list[str]]:
    """``word[low:high]`` as a regex over folded text, one or more title
    words optional at each of its sites (``_run_regex``), and its literal
    pieces between sites."""
    run = _run_regex()
    regex: list[str] = []
    pieces: list[str] = []
    start = low
    for index in sorted(position for position in kinds if low <= position < high):
        site = kinds[index]
        piece = fold(word[start:index])
        pieces.append(piece)
        regex.append(re.escape(piece))
        start = index + 1
        if _S1 in site:
            regex.append(f"(?:{run})?")
        if _S2 in site:
            regex.append(f"(?:{run} )?")
        if _S3 in site:
            # before a character other than a mark (« - », « . »), the
            # spaces after the last title word were taken off too
            after = word[start] if start < len(word) else ""
            space = " ?" if after and not is_mark(after) else ""
            regex.append(f"(?:{run}{space})?")
    piece = fold(word[start:high])
    pieces.append(piece)
    regex.append(re.escape(piece))
    return "".join(regex), pieces


@functools.lru_cache(maxsize=_CACHE_SIZE)
def _word_regex(
    word: str, last_word: bool, last_kept: bool
) -> tuple[str, tuple[str, ...], bool]:
    """A saved word as a regex over folded text: one or more title words
    optional at each site (S1 to S3), and each « Maître » inside it
    (``_joined_titles``) optional where today's pattern takes it off (S4).
    Also its literal pieces outside those « Maître », and whether the regex
    holds the space after the word.

    A « Maître » at the word's start or after a character that is neither a
    letter nor a mark (« - », « ' », « . ») is optional; when it ends a word
    that is not the last kept, the space after it goes with it (``\\s*``
    took it). Right after a mark (an S2 site), it goes only with title
    words put back there: today's ``\\b`` before it needed the space the old
    step took off with them."""
    run = _run_regex()
    kinds: dict[int, list[str]] = {}
    for index, kind in _sites(word, last_word):
        kinds.setdefault(index, []).append(kind)
    regex: list[str] = []
    pieces: list[str] = []
    space_held = False
    cursor = 0
    for start, end in sorted(_joined_titles(word).items()):
        after_mark = start > 0 and is_mark(word[start - 1])
        head, head_pieces = _span_regex(
            word, cursor, start - 1 if after_mark else start, kinds
        )
        regex.append(head)
        pieces += head_pieces
        title, _ = _span_regex(word, start, end, kinds)
        if after_mark:
            if _S1 in kinds.get(start - 1, []):
                regex.append(f"(?:{run})?")
            if end < len(word):
                regex.append(f"(?:{run} (?:{title})?|{title})")
            else:
                regex.append(f"(?:{run}(?: {title})?|{title})")
        elif end == len(word) and not last_kept:
            regex.append(f"(?:{title} |)")
            space_held = True
        else:
            regex.append(f"(?:{title})?")
        cursor = end
    tail, tail_pieces = _span_regex(word, cursor, len(word), kinds)
    regex.append(tail)
    pieces += tail_pieces
    return "".join(regex), tuple(piece for piece in pieces if piece), space_held


def _with_prepositions(
    words: list[str], kept: tuple[int, ...], entity_type: str
) -> Iterator[list[tuple[int, str]]]:
    """The kept words, each with its position; and, for a place whose words
    before the first kept one are all « Maître » left out, the same without
    the preposition today's step then takes off at the start
    (``FRENCH_PREPOSITION_PATTERN``, once, after the titles; the old step
    met « Maître » first and took none): the first kept word when it is a
    preposition and more words follow, or its elision « d' » or « l' »; and,
    when what follows the elision is « Maître », the whole word (today's
    title step took that « Maître » off before the elision)."""
    chosen = [(index, words[index]) for index in kept]
    yield chosen
    if entity_type != "LOCATION" or kept[0] == 0:
        return
    if not all(_is_maitre(words[index]) for index in range(kept[0])):
        return
    elisions, prepositions = preposition_words()
    index, first = chosen[0]
    more = len(chosen) > 1
    if more and composed(first).lower() in prepositions:
        yield chosen[1:]
    if composed(first[:2]).lower() in elisions:
        rest = first[2:]
        if rest or more:
            yield ([(index, rest)] if rest else []) + chosen[1:]
        if rest and more and _is_maitre(rest):
            yield chosen[1:]


@functools.lru_cache(maxsize=_CACHE_SIZE)
def legacy_pattern(full_name: str, entity_type: str) -> re.Pattern[str]:
    """Every whole text a saved name may stand for, as one regex over folded
    text (``fold``), compared with ``fullmatch``: one or more title words
    optional at each site (S1 to S3: at S3, before a « - » or a « . », with a
    space), any number of sites at once; each « Maître » (S4) and a place's
    first « à » (S5) optional, and a place's preposition after « Maître » at
    its start (``_with_prepositions``), the choices as alternatives; and a
    place made only of « Maître » words may stand for a preposition alone
    (« de Maître »: the old step took « de » off before the « Maître » it
    could not see; today's takes « Maître » off and keeps « de »)."""
    words = full_name.split()
    last = len(words) - 1
    choices: dict[str, None] = {}
    for kept in _word_choices(words, entity_type):
        for chosen in _with_prepositions(words, kept, entity_type):
            parts: list[str] = []
            for position, (index, word) in enumerate(chosen):
                last_kept = position == len(chosen) - 1
                regex, _, space_held = _word_regex(word, index == last, last_kept)
                parts.append(regex)
                if not last_kept and not space_held:
                    parts.append(" ")
            choices["".join(parts)] = None
    if entity_type == "LOCATION" and all(_is_maitre(word) for word in words):
        for preposition in preposition_words()[1]:
            choices[re.escape(fold(preposition))] = None
    return re.compile("(?:" + "|".join(choices) + ")")


@functools.lru_cache(maxsize=_CACHE_SIZE)
def legacy_piece(full_name: str, entity_type: str) -> str:
    """The longest piece of letters of a saved name between its sites and
    outside its « Maître », in a word it never leaves out (for a place
    whose first words may go, the next one may lose its preposition: left
    out too): every text ``legacy_pattern`` matches holds it (a quick test
    before the pattern)."""
    words = full_name.split()
    skipped = set(_droppable(words, entity_type))
    if entity_type == "LOCATION":
        first = next((i for i in range(len(words)) if i not in skipped), None)
        if first is not None and first > 0:
            skipped.add(first)
    pieces = [
        piece
        for index, word in enumerate(words)
        if index not in skipped
        for piece in _word_regex(word, index == len(words) - 1, False)[1]
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
    """The texts a search compares with a saved name: each word choice (whole
    « Maître » words, S5), alone and with one S1 or S2 site repaired by one
    title word, composed and lowercased, each with the span of what was put
    back (empty when nothing was). S3 sites are never used.

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
