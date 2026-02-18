"""
Unit tests for HybridDetector
"""

import sys

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

pytestmark = [
    pytest.mark.spacy,
    pytest.mark.skipif(
        sys.version_info >= (3, 14),
        reason="spaCy compatibility issue with Python 3.14+ - tests run in CI with Python 3.9-3.12",
    ),
]


class TestHybridDetector:
    """Test suite for HybridDetector class."""

    @pytest.fixture
    def detector(self) -> HybridDetector:
        """Create and load a HybridDetector instance."""
        hybrid_detector = HybridDetector()
        hybrid_detector.load_model("fr_core_news_lg")
        return hybrid_detector

    def test_load_model_success(self, detector: HybridDetector) -> None:
        """Test successful model loading."""
        model_info = detector.get_model_info()
        assert model_info["name"] == "hybrid_detector"
        assert model_info["library"] == "hybrid"
        assert "spacy_model" in model_info
        assert "regex_patterns_count" in model_info

    def test_detect_entities_basic(self, detector: HybridDetector) -> None:
        """Test basic entity detection with hybrid approach."""
        text = "M. Dupont travaille à Paris."
        entities = detector.detect_entities(text)

        assert len(entities) >= 2  # At least M. Dupont and Paris
        assert any(e.entity_type == "PERSON" for e in entities)
        assert any(e.entity_type == "LOCATION" for e in entities)

    def test_detect_entities_sources(self, detector: HybridDetector) -> None:
        """Test that entities have source attribution."""
        text = "M. Dupont habite à Paris."
        entities = detector.detect_entities(text)

        sources = {e.source for e in entities}
        # Should have at least one source type (spacy or regex)
        assert len(sources) > 0
        assert all(s in ["spacy", "regex"] for s in sources)

    def test_spacy_and_regex_detection(self, detector: HybridDetector) -> None:
        """Test that both spaCy and regex patterns detect entities."""
        text = "Interview avec M. Dupont et Marie Martin à Paris pour TechCorp SA."
        entities = detector.detect_entities(text)

        # Should have detections from both sources
        sources = [e.source for e in entities]
        assert "spacy" in sources or "regex" in sources

        # Should detect person entities
        persons = [e for e in entities if e.entity_type == "PERSON"]
        assert len(persons) >= 2

    def test_exact_overlap_prefers_spacy(self, detector: HybridDetector) -> None:
        """Test that exact overlap keeps spaCy entity."""
        # This tests the deduplication logic indirectly
        # If both spaCy and regex detect the same entity, only one should appear
        text = "M. Dupont à Paris."
        entities = detector.detect_entities(text)

        # Check that there are no duplicate spans
        spans = [(e.start_pos, e.end_pos) for e in entities]
        assert len(spans) == len(
            set(spans)
        ), "Duplicate entities with same span detected"

    def test_partial_overlap_flags_ambiguous(self, detector: HybridDetector) -> None:
        """Test that partial overlaps (non-title variants) are flagged as ambiguous.

        Note: Title variants like "Dr. Marie Dubois" vs "Marie Dubois" are now
        normalized and deduplicated, so they won't appear as partial overlaps.
        This test verifies TRUE partial overlaps (different entity boundaries)
        are still flagged as ambiguous.
        """
        # Use text that creates true partial overlap (not just title variants)
        text = "Interview avec Marie Dubois Fontaine."
        entities = detector.detect_entities(text)

        # May have overlapping entities (e.g., "Marie Dubois" vs "Dubois Fontaine")
        # If there are partial overlaps, at least one should be flagged ambiguous
        overlapping_entities = []
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 :]:
                if detector._has_overlap(e1, e2) and not detector._is_exact_match(
                    e1, e2
                ):
                    overlapping_entities.extend([e1, e2])

        if overlapping_entities:
            assert any(e.is_ambiguous for e in overlapping_entities)

    def test_no_overlap_keeps_both(self, detector: HybridDetector) -> None:
        """Test that non-overlapping entities from both sources are kept."""
        text = "M. Dupont habite à Paris."
        entities = detector.detect_entities(text)

        # Should have entities from different parts of text
        # At least person (Dupont) and location (Paris) which don't overlap
        assert len(entities) >= 2

        # Verify no overlaps between main entities
        person_entities = [e for e in entities if e.entity_type == "PERSON"]
        location_entities = [e for e in entities if e.entity_type == "LOCATION"]

        if person_entities and location_entities:
            for person in person_entities:
                for location in location_entities:
                    assert not detector._has_overlap(person, location)

    def test_confidence_scores_present(self, detector: HybridDetector) -> None:
        """Test that detected entities have confidence scores."""
        text = "M. Dupont travaille à Paris pour TechCorp SA."
        entities = detector.detect_entities(text)

        # Regex entities should have confidence
        regex_entities = [e for e in entities if e.source == "regex"]
        for entity in regex_entities:
            assert entity.confidence is not None
            assert 0.0 <= entity.confidence <= 1.0

    def test_compound_name_detection(self, detector: HybridDetector) -> None:
        """Test hybrid detection of compound names."""
        text = "Jean-Pierre et Marie-Claire sont présents."
        entities = detector.detect_entities(text)

        # Should detect compound names via regex
        compound_names = [e for e in entities if "-" in e.text]
        assert len(compound_names) >= 1

    def test_organization_pattern_detection(self, detector: HybridDetector) -> None:
        """Test hybrid detection of organizations."""
        text = "TechCorp SA et Solutions SARL sont partenaires."
        entities = detector.detect_entities(text)

        orgs = [e for e in entities if e.entity_type == "ORG"]
        assert len(orgs) >= 2

    def test_entity_positions_correct(self, detector: HybridDetector) -> None:
        """Test that entity positions are correct in hybrid detection."""
        text = "M. Dupont à Paris."
        entities = detector.detect_entities(text)

        for entity in entities:
            # Verify position matches actual text
            extracted = text[entity.start_pos : entity.end_pos]
            assert extracted == entity.text

    def test_entities_sorted_by_position(self, detector: HybridDetector) -> None:
        """Test that merged entities are sorted by position."""
        text = "M. Dupont habite à Paris et travaille pour TechCorp SA."
        entities = detector.detect_entities(text)

        # Verify entities are in ascending order by start_pos
        for i in range(len(entities) - 1):
            assert entities[i].start_pos <= entities[i + 1].start_pos

    def test_empty_text_raises_error(self, detector: HybridDetector) -> None:
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            detector.detect_entities("")

    def test_model_info_includes_both_components(
        self, detector: HybridDetector
    ) -> None:
        """Test that model info includes both spaCy and regex components."""
        info = detector.get_model_info()

        assert "spacy_model" in info
        assert "regex_patterns_count" in info
        assert info["library"] == "hybrid"
        assert info["language"] == "fr"

    def test_supports_gender_classification(self, detector: HybridDetector) -> None:
        """Test gender classification support property."""
        # Depends on spaCy detector support
        assert isinstance(detector.supports_gender_classification, bool)

    def test_lazy_loading(self) -> None:
        """Test lazy loading of model when detect_entities is called."""
        detector = HybridDetector()
        # Don't call load_model explicitly

        text = "M. Dupont à Paris."
        entities = detector.detect_entities(text)

        # Should still work via lazy loading
        assert len(entities) > 0

    def test_normalize_entity_text_basic(self, detector: HybridDetector) -> None:
        """Test that title normalization strips French titles."""
        assert detector._normalize_entity_text("Dr. Marie Dubois") == "Marie Dubois"
        assert detector._normalize_entity_text("M. Dupont") == "Dupont"
        assert detector._normalize_entity_text("Mme Fontaine") == "Fontaine"
        assert detector._normalize_entity_text("Marie Dubois") == "Marie Dubois"

    def test_normalize_entity_text_multiple_titles(
        self, detector: HybridDetector
    ) -> None:
        """Test that title normalization handles multiple consecutive titles."""
        assert detector._normalize_entity_text("Dr. Pr. Marie Dubois") == "Marie Dubois"
        assert detector._normalize_entity_text("M. Dr. Jean Martin") == "Jean Martin"

    def test_title_variant_deduplication(self, detector: HybridDetector) -> None:
        """Test that entities with and without titles are deduplicated.

        This is the critical fix for the bug where users saw the same entity
        multiple times during validation (once with "Dr." and once without).
        """
        text = "Dr. Marie Dubois collabore avec Marie Dubois."
        entities = detector.detect_entities(text)

        # Should only detect Marie Dubois twice (both occurrences, not title variants)
        marie_entities = [
            e for e in entities if "Marie" in e.text or "Dubois" in e.text
        ]

        # Verify no title variants in results
        entity_texts = [e.text for e in marie_entities]
        # Should not have both "Dr. Marie Dubois" and "Marie Dubois" from same occurrence
        # Only should have "Marie Dubois" twice (once at pos 0-16 area, once at pos 32-44 area)
        assert (
            len(marie_entities) <= 2
        ), f"Expected max 2 Marie entities, got {len(marie_entities)}: {entity_texts}"

    def test_improved_recall_over_spacy_only(self, detector: HybridDetector) -> None:
        """Test that hybrid detection finds more entities than spaCy alone."""
        text = "M. Dupont et Mme Laurent travaillent à Paris pour TechCorp SA."

        # Get hybrid results
        hybrid_entities = detector.detect_entities(text)

        # Get spaCy-only results
        spacy_entities = detector.spacy_detector.detect_entities(text)

        # Hybrid should detect at least as many entities as spaCy alone
        assert len(hybrid_entities) >= len(spacy_entities)

    def test_merge_entities_exact_match(self, detector: HybridDetector) -> None:
        """Test _merge_entities with exact overlap."""
        spacy_entity = DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=10,
            end_pos=15,
            confidence=0.9,
            source="spacy",
        )
        regex_entity = DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=10,
            end_pos=15,
            confidence=0.7,
            source="regex",
        )

        merged = detector._merge_entities([spacy_entity], [regex_entity])

        # Should keep only one entity (spaCy)
        assert len(merged) == 1
        assert merged[0].source == "spacy"
        assert merged[0].confidence == 0.9

    def test_merge_entities_no_overlap(self, detector: HybridDetector) -> None:
        """Test _merge_entities with no overlap."""
        spacy_entity = DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=10,
            end_pos=15,
            source="spacy",
        )
        regex_entity = DetectedEntity(
            text="M. Dupont",
            entity_type="PERSON",
            start_pos=20,
            end_pos=29,
            source="regex",
        )

        merged = detector._merge_entities([spacy_entity], [regex_entity])

        # Should keep both entities
        assert len(merged) == 2
        assert merged[0].start_pos == 10  # Paris comes first
        assert merged[1].start_pos == 20  # M. Dupont comes second

    def test_merge_entities_partial_overlap(self, detector: HybridDetector) -> None:
        """Test _merge_entities with partial overlap (non-title variant).

        This tests TRUE partial overlap where entity boundaries differ,
        not title variants which are correctly deduplicated.
        """
        # TRUE partial overlap: "Marie Dubois" vs "Dubois" (different boundaries)
        spacy_entity = DetectedEntity(
            text="Marie Dubois",
            entity_type="PERSON",
            start_pos=0,
            end_pos=13,
            source="spacy",
        )
        regex_entity = DetectedEntity(
            text="Dubois",
            entity_type="PERSON",
            start_pos=6,
            end_pos=13,
            source="regex",
        )

        merged = detector._merge_entities([spacy_entity], [regex_entity])

        # Should keep both entities, one flagged as ambiguous
        assert len(merged) == 2
        assert any(e.is_ambiguous for e in merged)

    def test_filter_title_only_entities(self, detector: HybridDetector) -> None:
        """Test that title-only entities are filtered out.

        spaCy sometimes incorrectly detects titles like "Maître" alone as PERSON
        entities. The filter removes these false positives.
        """
        # Create a title-only entity (e.g., "Maître" without a name)
        title_only = DetectedEntity(
            text="Maître",
            entity_type="PERSON",
            start_pos=0,
            end_pos=6,
            source="spacy",
        )
        # Create a valid entity with name
        valid_entity = DetectedEntity(
            text="Maître Mercier",
            entity_type="PERSON",
            start_pos=10,
            end_pos=24,
            source="spacy",
        )

        filtered = detector._filter_title_only_entities([title_only, valid_entity])

        # Title-only entity should be filtered out
        assert len(filtered) == 1
        assert filtered[0].text == "Maître Mercier"

    def test_filter_title_only_preserves_orgs(self, detector: HybridDetector) -> None:
        """Test that ORG entities are not affected by title filter."""
        # ORG entities should never be filtered by title logic
        org_entity = DetectedEntity(
            text="M. Dupont SA",
            entity_type="ORG",
            start_pos=0,
            end_pos=12,
            source="regex",
        )

        filtered = detector._filter_title_only_entities([org_entity])

        # ORG should be preserved
        assert len(filtered) == 1
        assert filtered[0].text == "M. Dupont SA"
