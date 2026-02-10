"""Centralized French language patterns for entity normalization.

Single canonical definitions of title and preposition patterns used across
the NLP, pseudonym, and validation layers. Eliminates duplication from
hybrid_detector.py, assignment_engine.py, and entity_grouping.py.

See Story 4.6.1 (R2) for rationale and R2b for preposition pattern analysis.
"""

from __future__ import annotations

import re

# French title pattern for entity normalization
# Matches common French honorifics and professional titles
# (?!\w) ensures title is not followed by a word character (prevents "Dr" matching in "Drapeau")
# \s* consumes optional trailing whitespace
FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|Madame|Monsieur|Mademoiselle|Maître|Dr\.?|Pr\.?|Prof\.?|M\.?|Mme\.?|Mlle\.?|Me\.?)(?!\w)\s*"

# French preposition pattern for location preprocessing
# Matches common French prepositions that precede location names
# NOTE: Does NOT include la/le/les — these are articles that form part of city names
# (e.g., "La Rochelle", "Le Mans", "Les Ulis"). See R2b investigation (Story 4.6.1).
# Longer alternatives listed first to prevent greedy partial matching (e.g., "des" before "de").
# ^[\s]* matches optional leading whitespace
# Two groups: (1) d'/l' elisions (no trailing space needed) (2) word prepositions (\s+ required)
FRENCH_PREPOSITION_PATTERN = r"^[\s]*(?:(?:d'|l')|(?:aux|au|des|du|de|à|en)\s+)"


def strip_french_titles(text: str) -> str:
    """Remove French titles/honorifics from entity text.

    Strips titles iteratively to handle multiple stacked titles
    (e.g., "Dr. Pr. Marie Dubois" → "Marie Dubois").

    Args:
        text: Entity text potentially containing titles

    Returns:
        Text with all leading titles removed
    """
    normalized = text
    while True:
        stripped = re.sub(
            FRENCH_TITLE_PATTERN, "", normalized, flags=re.IGNORECASE
        ).strip()
        if stripped == normalized:
            break
        normalized = stripped
    return normalized


def strip_french_prepositions(text: str) -> str:
    """Remove leading French prepositions from location entity text.

    Only strips from the beginning of the text.

    Examples:
        "à Paris" → "Paris"
        "en France" → "France"
        "du Nord" → "Nord"
        "l'Europe" → "Europe"
        "au Brésil" → "Brésil"

    Args:
        text: Entity text potentially containing prepositions

    Returns:
        Text with leading prepositions removed
    """
    stripped = re.sub(FRENCH_PREPOSITION_PATTERN, "", text, flags=re.IGNORECASE).strip()
    return stripped
