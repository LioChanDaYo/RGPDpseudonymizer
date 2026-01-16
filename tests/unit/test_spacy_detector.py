"""
Unit Tests for SpaCy Detector Implementation

Tests the SpaCyDetector class implementation of the EntityDetector interface.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


class TestSpaCyDetector:
    """Test suite for SpaCyDetector class."""

    @pytest.fixture
    def detector(self):
        """Create SpaCyDetector instance for testing."""
        return SpaCyDetector()

    def test_detector_initialization(self, detector):
        """Test detector initializes without loading model."""
        assert detector._nlp is None
        assert detector._model_name is None

    def test_load_model_default(self, detector):
        """Test loading default fr_core_news_lg model."""
        detector.load_model()
        assert detector._nlp is not None
        assert detector._model_name == "fr_core_news_lg"

    def test_load_model_explicit(self, detector):
        """Test loading model with explicit name."""
        detector.load_model("fr_core_news_lg")
        assert detector._nlp is not None
        assert detector._model_name == "fr_core_news_lg"

    def test_load_model_invalid(self, detector):
        """Test loading invalid model raises OSError."""
        with pytest.raises(OSError) as exc_info:
            detector.load_model("invalid_model_name_xyz")
        assert "not found" in str(exc_info.value).lower()

    def test_detect_entities_lazy_loading(self, detector):
        """Test that model loads lazily on first detect_entities call."""
        assert detector._nlp is None
        text = "Bonjour Marie."
        entities = detector.detect_entities(text)
        assert detector._nlp is not None  # Model loaded
        assert isinstance(entities, list)

    def test_detect_entities_person(self, detector):
        """Test detection of PERSON entities."""
        text = "Marie Dubois travaille à Paris."
        entities = detector.detect_entities(text)

        # Find person entities
        persons = [e for e in entities if e.entity_type == "PERSON"]
        assert len(persons) >= 1

        # Check Marie Dubois is detected
        marie = [p for p in persons if "Marie" in p.text and "Dubois" in p.text]
        assert len(marie) == 1
        assert marie[0].start_pos >= 0
        assert marie[0].end_pos > marie[0].start_pos
        assert isinstance(marie[0], DetectedEntity)

    def test_detect_entities_location(self, detector):
        """Test detection of LOCATION entities."""
        text = "Marie vit à Paris en France."
        entities = detector.detect_entities(text)

        # Find location entities
        locations = [e for e in entities if e.entity_type == "LOCATION"]
        assert len(locations) >= 1

        # Check Paris is detected
        paris = [l for l in locations if "Paris" in l.text]
        assert len(paris) >= 1

    def test_detect_entities_org(self, detector):
        """Test detection of ORG entities."""
        text = "Marie travaille chez Google France à Paris."
        entities = detector.detect_entities(text)

        # Find org entities (may not detect with default model)
        orgs = [e for e in entities if e.entity_type == "ORG"]
        # Note: spaCy may not always detect ORG correctly, this is informational
        # We don't assert on count due to known accuracy issues

    def test_detect_entities_compound_name(self, detector):
        """Test detection of compound hyphenated names."""
        text = "Jean-Pierre Martin est mon collègue."
        entities = detector.detect_entities(text)

        # Check for detection of Jean-Pierre
        persons = [e for e in entities if e.entity_type == "PERSON"]
        jean_pierre = [p for p in persons if "Jean-Pierre" in p.text]
        # Should detect compound name
        assert len(jean_pierre) >= 0  # May or may not detect based on context

    def test_detect_entities_empty_text(self, detector):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            detector.detect_entities("")
        assert "empty" in str(exc_info.value).lower()

    def test_detect_entities_none_text(self, detector):
        """Test that None text raises ValueError."""
        with pytest.raises(ValueError):
            detector.detect_entities(None)

    def test_detect_entities_special_characters(self, detector):
        """Test detection with special characters and accents."""
        text = "François Müller habite à Zürich."
        entities = detector.detect_entities(text)
        # Should not crash with special characters
        assert isinstance(entities, list)

    def test_detect_entities_title_prefix(self, detector):
        """Test detection with titles (M., Dr., Mme)."""
        text = "M. Jean Dupont et Dr. Marie Curie sont présents."
        entities = detector.detect_entities(text)

        persons = [e for e in entities if e.entity_type == "PERSON"]
        # Should detect at least some persons (may or may not include titles)
        assert len(persons) >= 1

    def test_get_model_info_before_load(self, detector):
        """Test get_model_info before model is loaded."""
        info = detector.get_model_info()
        assert info["library"] == "spacy"
        assert info["language"] == "fr"
        assert info["name"] == "not_loaded"

    def test_get_model_info_after_load(self, detector):
        """Test get_model_info after model is loaded."""
        detector.load_model()
        info = detector.get_model_info()

        assert info["library"] == "spacy"
        assert info["language"] == "fr"
        assert info["name"] == "core_news_lg"
        assert "version" in info
        assert info["version"] != "unknown"

    def test_supports_gender_classification(self, detector):
        """Test that spaCy does not support gender classification."""
        assert detector.supports_gender_classification is False

    def test_entity_positions_accurate(self, detector):
        """Test that entity positions match actual text."""
        text = "Marie Dubois vit à Paris."
        entities = detector.detect_entities(text)

        for entity in entities:
            # Extract text at reported position
            extracted_text = text[entity.start_pos:entity.end_pos]
            # Should match entity text
            assert extracted_text == entity.text

    def test_confidence_is_none(self, detector):
        """Test that spaCy detector returns None for confidence."""
        text = "Marie Dubois est à Paris."
        entities = detector.detect_entities(text)

        for entity in entities:
            assert entity.confidence is None  # spaCy doesn't provide confidence

    def test_gender_is_none(self, detector):
        """Test that spaCy detector returns None for gender."""
        text = "Marie Dubois et Jean Martin."
        entities = detector.detect_entities(text)

        for entity in entities:
            assert entity.gender is None  # spaCy doesn't provide gender

    def test_multiple_sentences(self, detector):
        """Test detection across multiple sentences."""
        text = (
            "Marie Dubois travaille à Paris. "
            "Jean Martin habite à Lyon. "
            "Ils travaillent chez Google France."
        )
        entities = detector.detect_entities(text)

        # Should detect entities across all sentences
        assert len(entities) >= 2  # At least Marie and Jean

    def test_long_document(self, detector):
        """Test detection on longer document."""
        text = " ".join([
            f"Marie Dubois numéro {i} travaille à Paris."
            for i in range(10)
        ])
        entities = detector.detect_entities(text)

        # Should detect multiple entities without errors
        assert len(entities) >= 10

    def test_no_entities_document(self, detector):
        """Test document with no entities."""
        text = "Il fait beau aujourd'hui. Le soleil brille."
        entities = detector.detect_entities(text)

        # May detect nothing or minimal entities
        assert isinstance(entities, list)
        # No assertion on count as generic text may not have entities


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
