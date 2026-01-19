"""Hardcoded entity list for naive pseudonymization.

This module provides a simple entity list for the walking skeleton
implementation (Story 1.5). It will be replaced by NLP-based detection
in later stories.

IMPORTANT: This is a temporary implementation for demonstration purposes only.
"""

from __future__ import annotations

# Format: (entity_text, entity_type, pseudonym)
# entity_text: The text to find in documents
# entity_type: PERSON, LOCATION, or ORG
# pseudonym: The replacement text (Star Wars theme)
NAIVE_ENTITIES: list[tuple[str, str, str]] = [
    # PERSON entities (8 entries)
    ("Marie Dubois", "PERSON", "Leia Organa"),
    ("Jean Martin", "PERSON", "Luke Skywalker"),
    ("Pierre Dupont", "PERSON", "Han Solo"),
    ("Sophie Laurent", "PERSON", "Rey"),
    ("Antoine Bernard", "PERSON", "Anakin Skywalker"),
    ("Claire Moreau", "PERSON", "Padmé Amidala"),
    ("François Lefebvre", "PERSON", "Obi-Wan Kenobi"),
    ("Isabelle Rousseau", "PERSON", "Ahsoka Tano"),
    # LOCATION entities (3 entries)
    ("Paris", "LOCATION", "Coruscant"),
    ("Lyon", "LOCATION", "Naboo"),
    ("Marseille", "LOCATION", "Tatooine"),
    # ORG entities (2 entries)
    ("Acme SA", "ORG", "Rebel Alliance"),
    ("TechCorp", "ORG", "Galactic Empire"),
]
