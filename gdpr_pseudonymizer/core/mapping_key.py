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

import unicodedata

from gdpr_pseudonymizer.utils.french_patterns import (
    strip_french_prepositions,
    strip_french_titles,
)
from gdpr_pseudonymizer.utils.text_form import composed

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


def former_keys(entity_text: str, entity_type: str) -> list[str]:
    """The keys an earlier version could have saved for this text, read with
    separate accent marks (Unicode NFD) (Story 10.20, Lionel's Qa).

    In order: the key's steps on the decomposed text (a title pattern cut at
    a mark: « Mélora Quentrel » saved as « lora Quentrel » after a lone
    U+0301); the decomposed key; the key's steps on the decomposed key with
    « Maître » in front, in each case form, for every type, and with « à » or
    « À » in front for a LOCATION (a decomposed title or preposition kept in
    the key). Without duplicates and without the composed key itself.

    Args:
        entity_text: The text looked up (a key, or a name as typed)
        entity_type: Entity type (PERSON, LOCATION, ORG)

    Returns:
        The former keys, possibly empty
    """
    key = mapping_key(entity_text, entity_type)
    words = FORMER_TITLE_WORDS + (
        FORMER_PREPOSITION_WORDS if entity_type == "LOCATION" else ()
    )
    candidates = [
        _key_steps(unicodedata.normalize("NFD", entity_text), entity_type),
        unicodedata.normalize("NFD", key),
        *(
            _key_steps(unicodedata.normalize("NFD", f"{word} {key}"), entity_type)
            for word in words
        ),
    ]
    return [
        candidate
        for candidate in dict.fromkeys(candidates)
        if candidate and candidate != key
    ]
