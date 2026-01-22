"""
Unit tests for RegexMatcher
"""

import pytest

from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher


class TestRegexMatcher:
    """Test suite for RegexMatcher class."""

    @pytest.fixture
    def matcher(self) -> RegexMatcher:
        """Create and load a RegexMatcher instance."""
        regex_matcher = RegexMatcher()
        regex_matcher.load_patterns()
        return regex_matcher

    def test_load_patterns_success(self, matcher: RegexMatcher) -> None:
        """Test successful pattern loading."""
        stats = matcher.get_pattern_stats()
        assert stats["categories_loaded"] > 0
        assert stats["total_patterns"] > 0

    def test_load_patterns_file_not_found(self) -> None:
        """Test error handling when config file doesn't exist."""
        matcher = RegexMatcher(config_path="nonexistent.yaml")
        with pytest.raises(FileNotFoundError):
            matcher.load_patterns()

    def test_title_pattern_single(self, matcher: RegexMatcher) -> None:
        """Test title + name pattern detection (single)."""
        text = "Interview avec M. Dupont ce matin."
        entities = matcher.match_entities(text)

        assert len(entities) >= 1
        matching = [e for e in entities if "Dupont" in e.text]
        assert len(matching) == 1
        assert matching[0].entity_type == "PERSON"
        assert matching[0].confidence >= 0.8

    def test_title_pattern_multiple(self, matcher: RegexMatcher) -> None:
        """Test title + name pattern detection (multiple)."""
        text = "Réunion entre M. Dupont et Mme Laurent."
        entities = matcher.match_entities(text)

        assert len(entities) >= 2
        names = [e.text for e in entities]
        assert any("Dupont" in name for name in names)
        assert any("Laurent" in name for name in names)

    def test_title_pattern_with_first_name(self, matcher: RegexMatcher) -> None:
        """Test title + full name pattern."""
        text = "Le Dr. Marie Dubois est absent."
        entities = matcher.match_entities(text)

        assert len(entities) >= 1
        matching = [e for e in entities if "Marie Dubois" in e.text]
        # Note: May detect both "Dr. Marie Dubois" and "Marie Dubois" (overlapping patterns)
        assert len(matching) >= 1
        assert all(e.entity_type == "PERSON" for e in matching)

    def test_compound_name_pattern(self, matcher: RegexMatcher) -> None:
        """Test hyphenated compound name detection."""
        text = "Jean-Pierre travaille avec Marie-Claire."
        entities = matcher.match_entities(text)

        assert len(entities) >= 2
        names = [e.text for e in entities]
        assert "Jean-Pierre" in names
        assert "Marie-Claire" in names

        for entity in entities:
            if "-" in entity.text:
                assert entity.entity_type == "PERSON"
                assert entity.confidence >= 0.7

    def test_location_indicator_paris(self, matcher: RegexMatcher) -> None:
        """Test location indicator pattern for Paris."""
        text = "Il habite à Paris depuis 2020."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if "Paris" in e.text and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1
        assert matching[0].confidence >= 0.6

    def test_location_indicator_multiple(self, matcher: RegexMatcher) -> None:
        """Test location indicator patterns (multiple)."""
        text = "De Paris en France près de Lyon."
        entities = matcher.match_entities(text)

        locations = [e for e in entities if e.entity_type == "LOCATION"]
        assert len(locations) >= 2

    def test_organization_suffix_pattern(self, matcher: RegexMatcher) -> None:
        """Test organization suffix detection (SA, SARL)."""
        text = "TechCorp SA et Solutions SARL sont partenaires."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        assert len(orgs) >= 2

        org_texts = [e.text for e in orgs]
        assert any("SA" in text for text in org_texts)
        assert any("SARL" in text for text in org_texts)

    def test_organization_prefix_pattern(self, matcher: RegexMatcher) -> None:
        """Test organization prefix detection (Société, Entreprise)."""
        text = "La Société TechCorp et l'Entreprise Dubois."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        assert len(orgs) >= 2

    def test_full_name_dictionary_match(self, matcher: RegexMatcher) -> None:
        """Test full name matching using name dictionary."""
        text = "Marie Dubois rencontre Jean Martin."
        entities = matcher.match_entities(text)

        persons = [e for e in entities if e.entity_type == "PERSON"]
        assert len(persons) >= 2

        names = [e.text for e in persons]
        assert "Marie Dubois" in names or any(
            "Marie" in n and "Dubois" in n for n in names
        )
        assert "Jean Martin" in names or any(
            "Jean" in n and "Martin" in n for n in names
        )

    def test_full_name_not_in_dictionary(self, matcher: RegexMatcher) -> None:
        """Test that non-dictionary names are not matched."""
        text = "XyzAbc NotRealName was present."
        entities = matcher.match_entities(text)

        # Should not match fake names
        fake_entities = [
            e for e in entities if "XyzAbc" in e.text or "NotRealName" in e.text
        ]
        assert len(fake_entities) == 0

    def test_entity_positions_correct(self, matcher: RegexMatcher) -> None:
        """Test that entity start/end positions are correct."""
        text = "Interview avec M. Dupont."
        entities = matcher.match_entities(text)

        assert len(entities) >= 1
        entity = entities[0]

        # Verify position matches actual text
        extracted = text[entity.start_pos : entity.end_pos]
        assert extracted == entity.text

    def test_no_duplicate_entities(self, matcher: RegexMatcher) -> None:
        """Test that duplicate entities (same span) are removed."""
        text = "M. Dupont habite à Paris."
        entities = matcher.match_entities(text)

        # Check for duplicates by span
        spans = [(e.start_pos, e.end_pos) for e in entities]
        assert len(spans) == len(
            set(spans)
        ), "Duplicate entities with same span detected"

    def test_french_accents_in_patterns(self, matcher: RegexMatcher) -> None:
        """Test pattern matching with French accented characters."""
        text = "François Lefèvre à Montréal."
        entities = matcher.match_entities(text)

        # Should detect François Lefèvre (if in dictionary) or Montréal
        assert len(entities) >= 1

    def test_document_start_end_entities(self, matcher: RegexMatcher) -> None:
        """Test entity detection at document start and end."""
        text = "M. Dupont travaille à Paris"
        entities = matcher.match_entities(text)

        # Should detect entities at both start and end
        assert len(entities) >= 2

        # Check start entity
        start_entities = [e for e in entities if e.start_pos == 0]
        assert len(start_entities) >= 1

        # Check end entity
        end_entities = [e for e in entities if e.end_pos == len(text)]
        assert len(end_entities) >= 1

    def test_special_characters_handling(self, matcher: RegexMatcher) -> None:
        """Test handling of special characters around entities."""
        text = 'Meeting with "M. Dupont" and (Mme Laurent).'
        entities = matcher.match_entities(text)

        assert len(entities) >= 2
        names = [e.text for e in entities]
        assert any("Dupont" in name for name in names)
        assert any("Laurent" in name for name in names)

    def test_empty_text(self, matcher: RegexMatcher) -> None:
        """Test behavior with empty text."""
        text = ""
        entities = matcher.match_entities(text)
        assert len(entities) == 0

    def test_text_without_entities(self, matcher: RegexMatcher) -> None:
        """Test behavior with text containing no entities."""
        text = "This is some random text without any named entities."
        entities = matcher.match_entities(text)
        # Might be 0 or small number depending on patterns
        # Main test is that it doesn't crash
        assert isinstance(entities, list)
