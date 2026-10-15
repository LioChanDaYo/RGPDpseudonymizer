"""The mapping key of a detected entity (Story 10.7).

One function builds the text part of a mapping row's key, for the core
(validation preview, known/unknown split, pseudonym resolution) and for the
desktop app's known-entity check, so they all agree. A row is identified by
this key and the entity type.
"""

from __future__ import annotations

from gdpr_pseudonymizer.utils.french_patterns import (
    strip_french_prepositions,
    strip_french_titles,
)


def mapping_key(entity_text: str, entity_type: str) -> str:
    """Normalize an entity's text into the text part of its mapping key.

    Strips French titles for every type, then leading French prepositions for
    LOCATION, then collapses every whitespace run (line breaks, tabs, no-break
    spaces, repeated spaces) to one space, so a name hard-wrapped over a line
    break gets the same key as its one-line spelling (10.3a QA REL-001).

    Args:
        entity_text: Entity text as detected (e.g. "Dr. Marie Dubois")
        entity_type: Entity type (PERSON, LOCATION, ORG)

    Returns:
        The key text (e.g. "Marie Dubois")
    """
    text = strip_french_titles(entity_text)
    if entity_type == "LOCATION":
        text = strip_french_prepositions(text)
    return " ".join(text.split())
