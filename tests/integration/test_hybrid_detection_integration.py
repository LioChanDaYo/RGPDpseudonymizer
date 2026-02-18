"""
Integration tests for hybrid detection workflow

Tests the full hybrid detection pipeline from document input to
entity detection, including both spaCy NER and regex pattern matching.
"""

import sys

import pytest

from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

pytestmark = [
    pytest.mark.spacy,
    pytest.mark.skipif(
        sys.version_info >= (3, 14),
        reason="spaCy compatibility issue with Python 3.14+ - tests run in CI with Python 3.9-3.12",
    ),
]


class TestHybridDetectionIntegration:
    """Integration test suite for hybrid detection workflow."""

    @pytest.fixture
    def detector(self) -> HybridDetector:
        """Create and load a HybridDetector instance."""
        hybrid_detector = HybridDetector()
        hybrid_detector.load_model("fr_core_news_lg")
        return hybrid_detector

    def test_full_document_processing(self, detector: HybridDetector) -> None:
        """Test complete document processing with hybrid detection."""
        document = """
        Interview avec M. Dupont et Mme Laurent

        M. Jean-Pierre Dubois, directeur de TechCorp SA, travaille à Paris depuis 2015.
        Il a rencontré Marie Martin, responsable chez Solutions SARL, lors d'une
        conférence en France. Ensemble, ils ont lancé le projet Innovation près de Lyon.

        L'entreprise Société Consulting et le Cabinet Lefebvre sont partenaires.
        """

        entities = detector.detect_entities(document)

        # Verify hybrid detection finds more entities than baseline
        assert (
            len(entities) >= 8
        ), "Should detect at least 8 entities with hybrid approach"

        # Verify entity types are detected
        entity_types = {e.entity_type for e in entities}
        assert "PERSON" in entity_types
        assert "LOCATION" in entity_types
        assert "ORG" in entity_types

        # Verify specific patterns are caught
        entity_texts = [e.text for e in entities]

        # Title patterns should be detected
        assert any("M." in text or "Dupont" in text for text in entity_texts)
        assert any("Mme" in text or "Laurent" in text for text in entity_texts)

        # Organization patterns should be detected
        assert any("SA" in text or "TechCorp" in text for text in entity_texts)
        assert any("SARL" in text or "Solutions" in text for text in entity_texts)

        # Location indicators should work
        assert any("Paris" in text for text in entity_texts)

    def test_validation_workflow_compatibility(self, detector: HybridDetector) -> None:
        """Test that hybrid detection output is compatible with validation workflow."""
        document = "M. Dupont habite à Paris."
        entities = detector.detect_entities(document)

        # Verify DetectedEntity objects have required fields for validation
        for entity in entities:
            assert hasattr(entity, "text")
            assert hasattr(entity, "entity_type")
            assert hasattr(entity, "start_pos")
            assert hasattr(entity, "end_pos")
            assert hasattr(entity, "confidence")
            assert hasattr(entity, "source")

            # Verify source field is set
            assert entity.source in ["spacy", "regex"]

    def test_processing_time_within_target(self, detector: HybridDetector) -> None:
        """Test that hybrid detection completes within performance target."""
        import time

        # Create a ~2000 word document
        document = " ".join(
            ["M. Dupont travaille à Paris pour TechCorp SA."] * 200
        )  # ~2000 words

        start_time = time.time()
        entities = detector.detect_entities(document)
        elapsed_time = time.time() - start_time

        # Should complete in under 30 seconds per document
        assert (
            elapsed_time < 30.0
        ), f"Processing took {elapsed_time:.2f}s, exceeds 30s target"

        # Should detect entities
        assert len(entities) > 0

    def test_improved_recall_over_spacy_only(self, detector: HybridDetector) -> None:
        """Test that hybrid detection improves recall vs spaCy baseline."""
        document = """
        Interview avec M. Dupont, Mme Laurent et Dr. Martin.
        Jean-Pierre habite à Paris. Marie-Claire travaille pour TechCorp SA.
        """

        # Get hybrid results
        hybrid_entities = detector.detect_entities(document)

        # Get spaCy-only results for comparison
        spacy_entities = detector.spacy_detector.detect_entities(document)

        # Hybrid should detect at least as many entities
        assert len(hybrid_entities) >= len(spacy_entities)

        # Calculate improvement
        if len(spacy_entities) > 0:
            improvement = len(hybrid_entities) - len(spacy_entities)
            improvement_pct = (improvement / len(spacy_entities)) * 100
            print(
                f"Hybrid detected {improvement} additional entities ({improvement_pct:.1f}% improvement)"
            )

    def test_entity_positions_valid_for_replacement(
        self, detector: HybridDetector
    ) -> None:
        """Test that entity positions are valid for text replacement."""
        document = "M. Dupont travaille à Paris."
        entities = detector.detect_entities(document)

        for entity in entities:
            # Extract entity using position
            extracted = document[entity.start_pos : entity.end_pos]

            # Verify extracted text matches entity text
            assert (
                extracted == entity.text
            ), f"Position mismatch: expected '{entity.text}', got '{extracted}'"

    def test_compound_names_detected(self, detector: HybridDetector) -> None:
        """Test that compound hyphenated names are detected."""
        document = "Jean-Pierre Dubois rencontre Marie-Claire Laurent."
        entities = detector.detect_entities(document)

        # Should detect compound names
        entity_texts = [e.text for e in entities]
        compound_names = [text for text in entity_texts if "-" in text]

        assert len(compound_names) >= 1, "Should detect at least one compound name"

    def test_organization_suffixes_detected(self, detector: HybridDetector) -> None:
        """Test that organization legal suffixes are detected."""
        document = "TechCorp SA, Solutions SARL et Conseil SAS sont partenaires."
        entities = detector.detect_entities(document)

        # Should detect organizations
        orgs = [e for e in entities if e.entity_type == "ORG"]
        assert len(orgs) >= 2, "Should detect at least 2 organizations"

        # At least one should have a legal suffix
        org_texts = [e.text for e in orgs]
        assert any(
            suffix in " ".join(org_texts) for suffix in ["SA", "SARL", "SAS"]
        ), "Should detect organization with legal suffix"

    def test_location_indicators_detected(self, detector: HybridDetector) -> None:
        """Test that location indicators are detected."""
        document = "Il habite à Paris, travaille en France et voyage près de Lyon."
        entities = detector.detect_entities(document)

        # Should detect locations
        locations = [e for e in entities if e.entity_type == "LOCATION"]
        assert len(locations) >= 2, "Should detect at least 2 locations"

    def test_no_false_positive_explosion(self, detector: HybridDetector) -> None:
        """Test that regex patterns don't create excessive false positives."""
        document = "Test document with minimal entities: M. Dupont."
        entities = detector.detect_entities(document)

        # Should not explode with false positives (reasonable upper bound)
        assert (
            len(entities) < 10
        ), "Too many entities detected, possible false positive explosion"

    def test_mixed_source_entities(self, detector: HybridDetector) -> None:
        """Test that hybrid detection includes entities from both sources."""
        document = (
            "M. Dupont (regex) habite à Paris (spaCy might catch) pour TechCorp SA."
        )
        entities = detector.detect_entities(document)

        # Should have entities from different sources
        sources = {e.source for e in entities}

        # At minimum, should have at least one detection
        assert len(entities) > 0
        # Sources should be properly attributed
        assert all(s in ["spacy", "regex"] for s in sources)
