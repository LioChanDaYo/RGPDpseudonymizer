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

    # Story 3.9: Cabinet Pattern Tests (AC2)
    def test_cabinet_pattern_single_name(self, matcher: RegexMatcher) -> None:
        """Test Cabinet + single name detected as ORG (Bug #3 fix)."""
        text = "Le Cabinet Mercier gère le dossier."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Cabinet Mercier" in e.text]
        assert len(matching) >= 1, "Cabinet Mercier should be detected as ORG"

    def test_cabinet_pattern_with_associates(self, matcher: RegexMatcher) -> None:
        """Test Cabinet + name with '& Associés' detected as ORG (Bug #3 fix)."""
        text = "Contactez le Cabinet Mercier & Associés pour plus d'informations."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Cabinet Mercier & Associés" in e.text]
        assert (
            len(matching) >= 1
        ), "Cabinet Mercier & Associés should be detected as ORG"

    def test_cabinet_pattern_multiple_names(self, matcher: RegexMatcher) -> None:
        """Test Cabinet + multiple names detected as ORG."""
        text = "Le Cabinet Dupont et Martin représente le client."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Cabinet Dupont et Martin" in e.text]
        assert len(matching) >= 1, "Cabinet Dupont et Martin should be detected as ORG"

    def test_cabinet_pattern_not_person(self, matcher: RegexMatcher) -> None:
        """Test Cabinet patterns are NOT detected as PERSON."""
        text = "Cabinet Mercier & Associés représente le client."
        entities = matcher.match_entities(text)

        # Check that "Cabinet Mercier" is not detected as PERSON
        persons = [e for e in entities if e.entity_type == "PERSON"]
        cabinet_as_person = [e for e in persons if "Cabinet" in e.text]
        assert len(cabinet_as_person) == 0, "Cabinet should not be detected as PERSON"

    def test_cabinet_pattern_complex(self, matcher: RegexMatcher) -> None:
        """Test Cabinet + complex pattern with comma and ampersand."""
        text = "Le Cabinet Dupont, Martin & Associés est renommé."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [
            e for e in orgs if "Cabinet Dupont" in e.text and "Associés" in e.text
        ]
        assert (
            len(matching) >= 1
        ), "Cabinet Dupont, Martin & Associés should be detected as ORG"

    # Story 3.9: Professional Title Detection Tests (AC4)
    def test_maitre_title_detection(self, matcher: RegexMatcher) -> None:
        """Test Maître title detection (attorney title, full form)."""
        text = "Maître Dubois représente le client."
        entities = matcher.match_entities(text)

        matching = [e for e in entities if "Maître Dubois" in e.text]
        assert len(matching) >= 1, "Maître Dubois should be detected"
        assert matching[0].entity_type == "PERSON"

    def test_me_title_detection(self, matcher: RegexMatcher) -> None:
        """Test Me title detection (attorney title, abbreviated)."""
        text = "Me Mercier a plaidé le dossier."
        entities = matcher.match_entities(text)

        matching = [e for e in entities if "Me Mercier" in e.text]
        assert len(matching) >= 1, "Me Mercier should be detected"
        assert matching[0].entity_type == "PERSON"

    def test_me_with_period_detection(self, matcher: RegexMatcher) -> None:
        """Test Me. title with period detection."""
        text = "Me. Dubois est absent aujourd'hui."
        entities = matcher.match_entities(text)

        matching = [e for e in entities if "Dubois" in e.text]
        assert len(matching) >= 1, "Me. Dubois should be detected"
        assert matching[0].entity_type == "PERSON"

    def test_maitre_title_full_name(self, matcher: RegexMatcher) -> None:
        """Test Maître title with full name."""
        text = "Maître Antoine Mercier est présent."
        entities = matcher.match_entities(text)

        matching = [
            e
            for e in entities
            if "Antoine Mercier" in e.text or "Maître Antoine" in e.text
        ]
        assert len(matching) >= 1, "Maître Antoine Mercier should be detected"
        assert all(e.entity_type == "PERSON" for e in matching)

    # Story 5.3: LastName, FirstName Pattern Tests (AC1)
    def test_last_first_name_simple(self, matcher: RegexMatcher) -> None:
        """Test LastName, FirstName pattern: 'Dubois, Jean-Marc'."""
        text = "Le dossier de Dubois, Jean-Marc est en cours."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if "Dubois" in e.text and e.entity_type == "PERSON"
        ]
        assert len(matching) >= 1, "Dubois, Jean-Marc should be detected as PERSON"

    def test_last_first_name_martin_sophie(self, matcher: RegexMatcher) -> None:
        """Test LastName, FirstName pattern: 'Martin, Sophie'."""
        text = "Convocation de Martin, Sophie pour le 15 mars."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if "Martin" in e.text and e.entity_type == "PERSON"
        ]
        assert len(matching) >= 1, "Martin, Sophie should be detected as PERSON"

    def test_last_first_name_diacritics_compound(self, matcher: RegexMatcher) -> None:
        """Test LastName, FirstName with diacritics + compound name."""
        text = "Le rapport de Lefèvre, Marie-Claire est complet."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if "Lefèvre" in e.text and e.entity_type == "PERSON"
        ]
        assert (
            len(matching) >= 1
        ), "Lefèvre, Marie-Claire should be detected as PERSON with diacritics"

    def test_last_first_name_negative_date_comma(self, matcher: RegexMatcher) -> None:
        """Test that date + name after comma is NOT matched as LastName, FirstName."""
        text = "le 15 janvier, Marie est arrivée."
        entities = matcher.match_entities(text)

        # "janvier, Marie" should NOT be matched as a LastName, FirstName PERSON
        bad_matches = [
            e
            for e in entities
            if "janvier" in e.text.lower() and e.entity_type == "PERSON"
        ]
        assert len(bad_matches) == 0, "janvier, Marie should NOT be detected as PERSON"

    # Story 5.3: Expanded ORG Suffix Tests (AC2)
    def test_org_suffix_association(self, matcher: RegexMatcher) -> None:
        """Test expanded ORG suffix: Association."""
        text = "TechCorp Association organise l'événement."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Association" in e.text]
        assert len(matching) >= 1, "TechCorp Association should be detected as ORG"

    def test_org_prefix_fondation(self, matcher: RegexMatcher) -> None:
        """Test expanded ORG prefix: Fondation."""
        text = "La Fondation Marie Curie finance la recherche."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Fondation" in e.text]
        assert len(matching) >= 1, "Fondation Marie Curie should be detected as ORG"

    def test_org_prefix_institut(self, matcher: RegexMatcher) -> None:
        """Test expanded ORG prefix: Institut."""
        text = "L'Institut Pasteur publie ses résultats."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Institut" in e.text]
        assert len(matching) >= 1, "Institut Pasteur should be detected as ORG"

    def test_org_prefix_groupe(self, matcher: RegexMatcher) -> None:
        """Test expanded ORG prefix: Groupe."""
        text = "Le Groupe Renault annonce ses résultats."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "Groupe" in e.text]
        assert len(matching) >= 1, "Groupe Renault should be detected as ORG"

    def test_org_suffix_sasu(self, matcher: RegexMatcher) -> None:
        """Test expanded ORG suffix: SASU."""
        text = "DataSoft SASU développe des logiciels."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "SASU" in e.text]
        assert len(matching) >= 1, "DataSoft SASU should be detected as ORG"

    def test_org_suffix_scop(self, matcher: RegexMatcher) -> None:
        """Test expanded ORG suffix: SCOP."""
        text = "Solutions SCOP est une coopérative."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        matching = [e for e in orgs if "SCOP" in e.text]
        assert len(matching) >= 1, "Solutions SCOP should be detected as ORG"

    def test_org_existing_suffixes_still_work(self, matcher: RegexMatcher) -> None:
        """Verify existing ORG suffixes (SA, SARL) still work after expansion."""
        text = "TechCorp SA et Solutions SARL sont partenaires."
        entities = matcher.match_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        org_texts = [e.text for e in orgs]
        assert any("SA" in t for t in org_texts), "TechCorp SA should still be detected"
        assert any(
            "SARL" in t for t in org_texts
        ), "Solutions SARL should still be detected"

    # Story 5.3: Geography Dictionary Tests (AC3)
    def test_geography_city_paris(self, matcher: RegexMatcher) -> None:
        """Test geography dictionary: Paris detected as LOCATION."""
        text = "Le siège est situé à Paris."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if e.text == "Paris" and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1, "Paris should be detected as LOCATION"

    def test_geography_city_marseille(self, matcher: RegexMatcher) -> None:
        """Test geography dictionary: Marseille detected as LOCATION."""
        text = "La succursale de Marseille est ouverte."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if e.text == "Marseille" and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1, "Marseille should be detected as LOCATION"

    def test_geography_region_ile_de_france(self, matcher: RegexMatcher) -> None:
        """Test geography dictionary: Île-de-France region detected."""
        text = "L'entreprise opère en Île-de-France."
        entities = matcher.match_entities(text)

        matching = [
            e
            for e in entities
            if "Île-de-France" in e.text and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1, "Île-de-France should be detected as LOCATION"

    def test_geography_department_bouches_du_rhone(self, matcher: RegexMatcher) -> None:
        """Test geography dictionary: Bouches-du-Rhône department detected."""
        text = "Le bureau des Bouches-du-Rhône traite le dossier."
        entities = matcher.match_entities(text)

        matching = [
            e
            for e in entities
            if "Bouches-du-Rhône" in e.text and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1, "Bouches-du-Rhône should be detected as LOCATION"

    def test_geography_negative_random_word(self, matcher: RegexMatcher) -> None:
        """Test geography dictionary: random word NOT detected as location."""
        text = "Le Xyzqwerty est un mot inventé."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if "Xyzqwerty" in e.text and e.entity_type == "LOCATION"
        ]
        assert len(matching) == 0, "Random word should NOT be detected as LOCATION"

    def test_geography_dictionary_loaded(self, matcher: RegexMatcher) -> None:
        """Test that geography dictionary is loaded by matcher."""
        stats = matcher.get_pattern_stats()
        assert stats["has_geography_dictionary"] is True

    def test_geography_city_with_hyphen(self, matcher: RegexMatcher) -> None:
        """Test geography dictionary: hyphenated city name (Aix-en-Provence)."""
        text = "Le festival d'Aix-en-Provence attire les visiteurs."
        entities = matcher.match_entities(text)

        matching = [
            e
            for e in entities
            if "Aix-en-Provence" in e.text and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1, "Aix-en-Provence should be detected as LOCATION"

    def test_geography_confidence_level(self, matcher: RegexMatcher) -> None:
        """Test that geography matches have correct confidence level."""
        text = "Le bureau de Toulouse est fermé."
        entities = matcher.match_entities(text)

        matching = [
            e for e in entities if e.text == "Toulouse" and e.entity_type == "LOCATION"
        ]
        assert len(matching) >= 1
        assert matching[0].confidence >= 0.60
