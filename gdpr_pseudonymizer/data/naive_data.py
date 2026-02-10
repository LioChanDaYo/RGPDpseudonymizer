"""Hardcoded entity list for naive pseudonymization.

PARTIALLY DEPRECATED: Pseudonym mappings still in use by process.py.

This module provided a simple entity list for the walking skeleton
implementation (Story 1.5). Entity detection has been replaced by SpaCyDetector,
but the pseudonym lists (NAIVE_ENTITIES) are still used for mapping detected
entities to Star Wars pseudonyms.

FUTURE: This will be replaced by proper pseudonym library system in Epic 2.
For now: Pseudonym assignments are managed in process.py using these pools.

NOTE: The entity_text field (first tuple element) is no longer used for detection.
Only the pseudonym pools (entity_type + pseudonym) are actively used.
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
