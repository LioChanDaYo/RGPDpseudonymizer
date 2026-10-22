"""The mapping key of a detected entity (Story 10.7).

One function builds the text part of a mapping row's key, for the core
(validation preview, known/unknown split, pseudonym resolution) and for the
desktop app's known-entity check, so they all agree. A row is identified by
this key and the entity type.

Story 10.20: the key is built from the composed text (Unicode NFC), so a name
whose accents are stored as separate marks has the key of the usual name.
``former_keys`` gives the keys an earlier version could have saved for a name
read with separate marks; the mapping repository looks them up too, and no
saved row is rewritten (Lionel, 2026-10-21, Qa).
"""

from __future__ import annotations

import itertools
import unicodedata

from gdpr_pseudonymizer.utils.french_patterns import (
    strip_french_prepositions,
    strip_french_titles,
)
from gdpr_pseudonymizer.utils.text_form import composed, is_mark

# The only accented words of FRENCH_TITLE_PATTERN (every type) and of
# FRENCH_PREPOSITION_PATTERN (LOCATION), in the case forms the patterns match
# (they ignore case). Read with separate marks, an earlier version did not see
# them as a title or a preposition and kept them in the key (Story 10.20, the
# PO's M1). A new accented title or preposition in utils/french_patterns.py
# needs its word here.
FORMER_TITLE_WORDS = ("Maître", "maître", "MAÎTRE")
FORMER_PREPOSITION_WORDS = ("à", "À")


def _key_steps(entity_text: str, entity_type: str) -> str:
    """The key's steps on the text as given: titles stripped for every type,
    then leading prepositions for LOCATION, then whitespace collapsed."""
    text = strip_french_titles(entity_text)
    if entity_type == "LOCATION":
        text = strip_french_prepositions(text)
    return " ".join(text.split())


def mapping_key(entity_text: str, entity_type: str) -> str:
    """Normalize an entity's text into the text part of its mapping key.

    Composes the text (Unicode NFC, Story 10.20), then strips French titles
    for every type, then leading French prepositions for LOCATION, then
    collapses every whitespace run (line breaks, tabs, no-break spaces,
    repeated spaces) to one space, so a name hard-wrapped over a line break
    gets the same key as its one-line spelling (10.3a QA REL-001).

    Args:
        entity_text: Entity text as detected (e.g. "Dr. Marie Dubois")
        entity_type: Entity type (PERSON, LOCATION, ORG)

    Returns:
        The key text (e.g. "Marie Dubois")
    """
    return _key_steps(composed(entity_text), entity_type)


# Story 10.20, v1.7 (the Codex review's P1-1): the per-word mixes of composed
# and decomposed words are tried for a name of at most this many accented
# words (16 mixes); a longer name, its two whole forms only.
MAX_MIXED_WORDS = 4

# The kinds of an old key (Story 10.20, v1.7): the text an earlier version
# was given, kept whole ("whole") or with a decomposed title or preposition
# kept in it ("titled"); cut by the old title pattern at a mark in a way that
# leaves a sign no correct name has, a word starting with a combining mark or
# two words glued together ("sign"); or cut without such a sign ("cut").
_WHOLE = "whole"
_TITLED = "titled"
_SIGN = "sign"
_CUT = "cut"


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


def _key_texts(key: str, entity_type: str) -> list[tuple[str, bool]]:
    """The texts an earlier version could have been given for a name whose
    key is ``key``, each with whether a word was inserted (a title, or a
    LOCATION's preposition): every per-word mix of the words' composed and
    decomposed forms (every word decomposed first) when at most
    ``MAX_MIXED_WORDS`` words carry an accent, else the two whole forms; then
    each of the two whole forms with a decomposed « Maître » (each case form)
    at each word position, and for a LOCATION with a decomposed « à » or
    « À » in front."""
    words = key.split()
    if not words:
        return []
    choices = [(_nfd(word), word) if _nfd(word) != word else (word,) for word in words]
    accented = sum(1 for choice in choices if len(choice) == 2)
    decomposed = [_nfd(word) for word in words]
    if accented <= MAX_MIXED_WORDS:
        mixes = [" ".join(mix) for mix in itertools.product(*choices)]
    else:
        mixes = [" ".join(decomposed), " ".join(words)]
    texts = [(mix, False) for mix in mixes]
    wholes = (decomposed, words)
    for whole in wholes:
        for title in FORMER_TITLE_WORDS:
            for position in range(len(whole) + 1):
                inserted = [*whole[:position], _nfd(title), *whole[position:]]
                texts.append((" ".join(inserted), True))
    if entity_type == "LOCATION":
        for whole in wholes:
            for preposition in FORMER_PREPOSITION_WORDS:
                texts.append((" ".join([_nfd(preposition), *whole]), True))
    return texts


def _former(entity_text: str, entity_type: str) -> list[tuple[str, str]]:
    """The keys an earlier version saved for this text, replayed, each with
    its kind, today's key left out. P0-1 (Lionel, 2026-10-22, "A: Only with a
    sign (Rec.)"): a "cut" key could be another person's name, so it is
    dropped."""
    key = mapping_key(entity_text, entity_type)
    found: dict[str, str] = {}
    for text, inserted in _key_texts(key, entity_type):
        if text == key:
            # v1.19 (row c6): every word composed, what an earlier version
            # saved is today's key itself; the steps again on a place's key
            # that still starts with a preposition (« de Zórbaville ») would
            # give a key no version saved
            continue
        old = _key_steps(text, entity_type)
        if not old or old == key or old in found:
            continue
        if old == text:
            found[old] = _TITLED if inserted else _WHOLE
        elif any(is_mark(word[0]) for word in old.split()) or len(old.split()) < len(
            text.split()
        ):
            found[old] = _SIGN
        else:
            found[old] = _CUT
    return [(old, kind) for old, kind in found.items() if kind != _CUT]


def former_keys(entity_text: str, entity_type: str) -> list[str]:
    """The keys an earlier version could have saved for this text, read with
    separate accent marks (Unicode NFD) (Story 10.20, Lionel's Qa; v1.7, the
    Codex review of 186972b).

    The old steps (titles taken off anywhere, a LOCATION's leading
    preposition, spaces collapsed) replayed on each per-word mix of today's
    key and on its two whole forms with a decomposed « Maître » or (for a
    LOCATION) « à » kept in it (``_key_texts``). A key the old steps leave as
    it was ("whole" or "titled"), or cut leaving a sign ("sign": « Mélora
    Quentrel » saved as « lora Quentrel » after a lone U+0301; « Zorbôme
    Quentrel » glued as « ZorbôQuentrel »); a key cut without a sign is never
    returned (Lionel's P0-1). Without duplicates and without today's key.

    Args:
        entity_text: The text looked up (a key, or a name as typed)
        entity_type: Entity type (PERSON, LOCATION, ORG)

    Returns:
        The former keys, possibly empty
    """
    return [old for old, _ in _former(entity_text, entity_type)]


def saved_name_forms(entity_text: str, entity_type: str) -> list[str]:
    """Every text a saved row of this name and type may hold (Story 10.20,
    v1.7; Lionel's Qa and Qb), in the order a lookup prefers them: the
    composed text; the keys an earlier version saved (``former_keys``); the
    text as given. Without duplicates; the composed text first (rule A).

    Every form but the composed text and the text as given holds an accent
    mark: each text the replay tries, but the all-composed one, holds a
    decomposed letter, « Maître » or « à », and no old step takes a mark
    off. So no form is a name today's code saves. v1.18 (the third Codex
    review, P0-b): an old key is no longer tried in its composed form. It
    could be the correct name of another person saved today (« Vorlan
    ZorbôQuentrel » for « Vorlan Zorbôme Quentrel »), which Lionel's P0-1
    answer forbids, and no path stores a composed old key (``import-mappings``
    copies rows as saved since v1.14)."""
    former = _former(entity_text, entity_type)
    forms = [composed(entity_text), *(old for old, _ in former), entity_text]
    return list(dict.fromkeys(forms))
