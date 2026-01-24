"""DetectedEntity test fixtures for validation workflow integration tests."""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


def create_simple_entities() -> list[DetectedEntity]:
    """Create simple entity list for basic workflow tests.

    Returns:
        List with 3 entities (1 PERSON, 1 ORG, 1 LOCATION), no duplicates
    """
    return [
        DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=0,
            end_pos=12,
            confidence=0.95,
            source="spacy",
        ),
        DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=24,
            end_pos=29,
            confidence=0.90,
            source="spacy",
        ),
        DetectedEntity(
            text="TechCorp",
            entity_type="ORG",
            start_pos=75,
            end_pos=83,
            confidence=0.85,
            source="spacy",
        ),
    ]


def create_duplicate_entities() -> list[DetectedEntity]:
    """Create entity list with duplicates for deduplication tests.

    Returns:
        List with 9 entities including duplicates:
        - Marie Dubois (PERSON) appears 3 times
        - Sophie Laurent (PERSON) appears 2 times
        - Paris (LOCATION) appears 2 times
        - TechCorp (ORG) appears 2 times
    """
    return [
        # First occurrence: Marie Dubois
        DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=0,
            end_pos=12,
            confidence=0.95,
            source="spacy",
        ),
        # Second occurrence: Marie Dubois
        DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=39,
            end_pos=51,
            confidence=0.95,
            source="spacy",
        ),
        # First occurrence: Sophie Laurent
        DetectedEntity(
            text="Sophie Laurent",
            entity_type="PERSON",
            start_pos=67,
            end_pos=81,
            confidence=0.95,
            source="spacy",
        ),
        # Second occurrence: Sophie Laurent
        DetectedEntity(
            text="Sophie Laurent",
            entity_type="PERSON",
            start_pos=94,
            end_pos=108,
            confidence=0.95,
            source="spacy",
        ),
        # First occurrence: TechCorp
        DetectedEntity(
            text="TechCorp",
            entity_type="ORG",
            start_pos=128,
            end_pos=136,
            confidence=0.85,
            source="spacy",
        ),
        # Second occurrence: TechCorp
        DetectedEntity(
            text="TechCorp",
            entity_type="ORG",
            start_pos=152,
            end_pos=160,
            confidence=0.85,
            source="spacy",
        ),
        # First occurrence: Paris
        DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=30,
            end_pos=35,
            confidence=0.90,
            source="spacy",
        ),
        # Second occurrence: Paris
        DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=182,
            end_pos=187,
            confidence=0.90,
            source="spacy",
        ),
        # Third occurrence: Marie Dubois
        DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=210,
            end_pos=222,
            confidence=0.95,
            source="spacy",
        ),
    ]


def create_large_entity_list() -> list[DetectedEntity]:
    """Create large entity list for performance tests.

    Returns:
        List with 100+ entities (simulated with patterns)
    """
    entities = []
    base_entities = [
        ("Marie Dubois", "PERSON", 0.95),
        ("Jean Martin", "PERSON", 0.95),
        ("Sophie Laurent", "PERSON", 0.95),
        ("Pierre Fontaine", "PERSON", 0.95),
        ("Claire Moreau", "PERSON", 0.95),
        ("Paris", "LOCATION", 0.90),
        ("Lyon", "LOCATION", 0.90),
        ("Marseille", "LOCATION", 0.90),
        ("TechCorp", "ORG", 0.85),
        ("Acme SA", "ORG", 0.85),
    ]

    # Generate 320 entities (10 base entities x 32 occurrences each)
    start_pos = 0
    for _ in range(32):
        for text, entity_type, confidence in base_entities:
            end_pos = start_pos + len(text)
            entities.append(
                DetectedEntity(
                    text=text,
                    entity_type=entity_type,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    confidence=confidence,
                    source="spacy",
                )
            )
            start_pos = end_pos + 50  # Add spacing between entities

    return entities


def create_mixed_type_entities() -> list[DetectedEntity]:
    """Create entity list with mixed types for type-based review tests.

    Returns:
        List with PERSON, ORG, and LOCATION entities
    """
    return [
        DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=0,
            end_pos=12,
            confidence=0.95,
            source="spacy",
        ),
        DetectedEntity(
            text="TechCorp",
            entity_type="ORG",
            start_pos=27,
            end_pos=35,
            confidence=0.85,
            source="spacy",
        ),
        DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=38,
            end_pos=43,
            confidence=0.90,
            source="spacy",
        ),
        DetectedEntity(
            text="Jean Martin",
            entity_type="PERSON",
            start_pos=45,
            end_pos=56,
            confidence=0.95,
            source="spacy",
        ),
        DetectedEntity(
            text="Acme SA",
            entity_type="ORG",
            start_pos=69,
            end_pos=76,
            confidence=0.85,
            source="spacy",
        ),
        DetectedEntity(
            text="Lyon",
            entity_type="LOCATION",
            start_pos=79,
            end_pos=83,
            confidence=0.90,
            source="spacy",
        ),
    ]


def create_person_only_entities() -> list[DetectedEntity]:
    """Create entity list with PERSON type only.

    Returns:
        List with only PERSON entities
    """
    return [
        DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=0,
            end_pos=12,
            confidence=0.95,
            source="spacy",
        ),
        DetectedEntity(
            text="Jean Martin",
            entity_type="PERSON",
            start_pos=14,
            end_pos=25,
            confidence=0.95,
            source="spacy",
        ),
        DetectedEntity(
            text="Sophie Laurent",
            entity_type="PERSON",
            start_pos=29,
            end_pos=43,
            confidence=0.95,
            source="spacy",
        ),
    ]
