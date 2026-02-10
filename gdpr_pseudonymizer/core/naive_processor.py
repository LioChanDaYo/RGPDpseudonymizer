"""Naive entity detection and pseudonymization processor.

DEPRECATED: This module is deprecated as of Story 1.6. Use SpaCyDetector instead.

This module provided simple string-matching entity detection and replacement
for the walking skeleton implementation (Story 1.5).

MIGRATION PATH:
- Replace: from gdpr_pseudonymizer.core.naive_processor import detect_naive_entities
- With: from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
- See: gdpr_pseudonymizer/cli/commands/process.py for migration example

This file will be removed in Epic 2.
"""

from __future__ import annotations

from gdpr_pseudonymizer.data.naive_data import NAIVE_ENTITIES


def detect_naive_entities(text: str) -> list[tuple[str, str, int, int, str]]:
    """Detect entities using simple string matching against hardcoded list.

    This function performs case-sensitive string matching to find entities
    from the NAIVE_ENTITIES list in the input text.

    Args:
        text: Input text to search for entities

    Returns:
        List of tuples containing:
            - entity_text (str): The matched entity text
            - entity_type (str): Entity type (PERSON, LOCATION, ORG)
            - start_pos (int): Start character position in text
            - end_pos (int): End character position in text
            - pseudonym (str): Suggested pseudonym for replacement

    Examples:
        >>> text = "Interview with Marie Dubois in Paris."
        >>> entities = detect_naive_entities(text)
        >>> len(entities)
        2
        >>> entities[0][0]
        'Marie Dubois'
        >>> entities[0][1]
        'PERSON'
    """
    detected: list[tuple[str, str, int, int, str]] = []

    for entity_text, entity_type, pseudonym in NAIVE_ENTITIES:
        # Find all occurrences of this entity in the text
        start_pos = 0
        while True:
            start_pos = text.find(entity_text, start_pos)
            if start_pos == -1:
                break

            end_pos = start_pos + len(entity_text)
            detected.append((entity_text, entity_type, start_pos, end_pos, pseudonym))

            # Move past this occurrence to find next one
            start_pos = end_pos

    # Sort by start position for consistent ordering
    detected.sort(key=lambda x: x[2])

    return detected


def apply_naive_replacements(
    text: str, entities: list[tuple[str, str, int, int, str]]
) -> str:
    """Apply pseudonym replacements to text.

    This function applies replacements in reverse order to maintain
    character offsets. Overlapping entities are skipped.

    Args:
        text: Original text
        entities: List of detected entities (from detect_naive_entities)

    Returns:
        Text with entities replaced by pseudonyms

    Examples:
        >>> text = "Interview with Marie Dubois in Paris."
        >>> entities = detect_naive_entities(text)
        >>> result = apply_naive_replacements(text, entities)
        >>> "Leia Organa" in result
        True
        >>> "Marie Dubois" in result
        False
    """
    if not entities:
        return text

    # Remove overlapping entities (keep first occurrence)
    non_overlapping: list[tuple[str, str, int, int, str]] = []
    for entity in entities:
        entity_text, entity_type, start, end, pseudonym = entity

        # Check if this entity overlaps with any already added
        overlaps = False
        for _, _, existing_start, existing_end, _ in non_overlapping:
            if start < existing_end and end > existing_start:
                overlaps = True
                break

        if not overlaps:
            non_overlapping.append(entity)

    # Sort by start position in reverse order (process from end to start)
    # This maintains character positions as we replace
    non_overlapping.sort(key=lambda x: x[2], reverse=True)

    # Apply replacements
    result = text
    for entity_text, entity_type, start, end, pseudonym in non_overlapping:
        result = result[:start] + pseudonym + result[end:]

    return result
