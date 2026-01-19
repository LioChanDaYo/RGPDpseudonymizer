"""Unit tests for naive entity detection and replacement processor."""

from __future__ import annotations

from gdpr_pseudonymizer.core.naive_processor import (
    apply_naive_replacements,
    detect_naive_entities,
)


def test_detect_naive_entities_finds_person_entities() -> None:
    """Test naive entity detection finds PERSON entities."""
    text = "Interview with Marie Dubois in Paris."
    entities = detect_naive_entities(text)

    # Should find Marie Dubois (PERSON) and Paris (LOCATION)
    assert len(entities) == 2

    # Check first entity (Marie Dubois)
    entity_text, entity_type, start, end, pseudonym = entities[0]
    assert entity_text == "Marie Dubois"
    assert entity_type == "PERSON"
    assert pseudonym == "Leia Organa"
    assert start == 15
    assert end == 27


def test_detect_naive_entities_finds_location_entities() -> None:
    """Test naive entity detection finds LOCATION entities."""
    text = "Meeting in Paris and Lyon."
    entities = detect_naive_entities(text)

    assert len(entities) == 2

    # Check Paris
    assert entities[0][0] == "Paris"
    assert entities[0][1] == "LOCATION"
    assert entities[0][4] == "Coruscant"

    # Check Lyon
    assert entities[1][0] == "Lyon"
    assert entities[1][1] == "LOCATION"
    assert entities[1][4] == "Naboo"


def test_detect_naive_entities_finds_org_entities() -> None:
    """Test naive entity detection finds ORG entities."""
    text = "Collaboration between Acme SA and TechCorp."
    entities = detect_naive_entities(text)

    assert len(entities) == 2

    # Check Acme SA
    assert entities[0][0] == "Acme SA"
    assert entities[0][1] == "ORG"
    assert entities[0][4] == "Rebel Alliance"

    # Check TechCorp
    assert entities[1][0] == "TechCorp"
    assert entities[1][1] == "ORG"
    assert entities[1][4] == "Galactic Empire"


def test_detect_naive_entities_returns_correct_positions() -> None:
    """Test naive entity detection returns correct character positions."""
    text = "Marie Dubois works at Acme SA in Paris."
    entities = detect_naive_entities(text)

    # Verify positions
    for entity_text, entity_type, start, end, pseudonym in entities:
        assert text[start:end] == entity_text


def test_detect_naive_entities_handles_empty_text() -> None:
    """Test naive entity detection handles empty text."""
    text = ""
    entities = detect_naive_entities(text)

    assert entities == []


def test_detect_naive_entities_handles_text_without_entities() -> None:
    """Test naive entity detection handles text without entities."""
    text = "This is a test sentence without any entities."
    entities = detect_naive_entities(text)

    assert entities == []


def test_detect_naive_entities_finds_multiple_occurrences() -> None:
    """Test naive entity detection finds multiple occurrences of same entity."""
    text = "Marie Dubois met with Marie Dubois yesterday."
    entities = detect_naive_entities(text)

    # Should find 2 occurrences of Marie Dubois
    assert len(entities) == 2
    assert entities[0][0] == "Marie Dubois"
    assert entities[1][0] == "Marie Dubois"
    assert entities[0][2] < entities[1][2]  # Second occurrence starts later


def test_apply_naive_replacements_replaces_entities() -> None:
    """Test naive replacement applies pseudonyms correctly."""
    text = "Interview with Marie Dubois in Paris."
    entities = detect_naive_entities(text)
    result = apply_naive_replacements(text, entities)

    assert "Leia Organa" in result
    assert "Coruscant" in result
    assert "Marie Dubois" not in result
    assert "Paris" not in result


def test_apply_naive_replacements_maintains_character_offsets() -> None:
    """Test naive replacement maintains correct character offsets."""
    text = "Marie Dubois works at Acme SA in Paris."
    entities = detect_naive_entities(text)
    result = apply_naive_replacements(text, entities)

    # Result should contain pseudonyms
    assert "Leia Organa" in result
    assert "Rebel Alliance" in result
    assert "Coruscant" in result

    # Original entities should be replaced
    assert "Marie Dubois" not in result
    assert "Acme SA" not in result
    assert "Paris" not in result


def test_apply_naive_replacements_handles_overlapping_entities() -> None:
    """Test naive replacement handles overlapping entities correctly."""
    # Create a text where entities might overlap if not handled properly
    text = "Paris and Lyon are cities."
    entities = detect_naive_entities(text)
    result = apply_naive_replacements(text, entities)

    # Should replace both without issues
    assert "Coruscant" in result
    assert "Naboo" in result
    assert "Paris" not in result
    assert "Lyon" not in result


def test_apply_naive_replacements_handles_empty_entity_list() -> None:
    """Test naive replacement handles empty entity list."""
    text = "This is a test sentence."
    entities = []
    result = apply_naive_replacements(text, entities)

    assert result == text


def test_apply_naive_replacements_handles_multiple_occurrences() -> None:
    """Test naive replacement handles multiple occurrences of same entity."""
    text = "Marie Dubois and Marie Dubois met in Paris."
    entities = detect_naive_entities(text)
    result = apply_naive_replacements(text, entities)

    # Both occurrences of Marie Dubois should be replaced
    assert result.count("Leia Organa") == 2
    assert "Marie Dubois" not in result
    assert "Coruscant" in result


def test_apply_naive_replacements_preserves_text_structure() -> None:
    """Test naive replacement preserves text structure and formatting."""
    text = "Interview with Marie Dubois.\nLocation: Paris.\nOrg: Acme SA."
    entities = detect_naive_entities(text)
    result = apply_naive_replacements(text, entities)

    # Newlines should be preserved
    assert "\n" in result
    # Structure should be maintained
    assert result.startswith("Interview with")
    assert "Location:" in result
    assert "Org:" in result


def test_end_to_end_detection_and_replacement() -> None:
    """Test end-to-end detection and replacement workflow."""
    text = (
        "Marie Dubois from Acme SA met with Jean Martin from TechCorp in Paris. "
        "They discussed the Lyon project with Sophie Laurent."
    )

    # Detect entities
    entities = detect_naive_entities(text)

    # Should find multiple entities
    assert len(entities) > 0

    # Apply replacements
    result = apply_naive_replacements(text, entities)

    # Original entities should be replaced
    assert "Marie Dubois" not in result
    assert "Jean Martin" not in result
    assert "Sophie Laurent" not in result
    assert "Acme SA" not in result
    assert "TechCorp" not in result
    assert "Paris" not in result
    assert "Lyon" not in result

    # Pseudonyms should be present
    assert "Leia Organa" in result
    assert "Luke Skywalker" in result
    assert "Rey" in result
    assert "Rebel Alliance" in result
    assert "Galactic Empire" in result
    assert "Coruscant" in result
    assert "Naboo" in result
