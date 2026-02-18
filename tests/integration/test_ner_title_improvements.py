"""
Integration tests for Story 3.9: NER & Title Handling Improvements

Tests the full hybrid detection pipeline with:
- Bug #3 fix: Cabinet pattern detection as ORG (not PERSON)
- Bug #4 fix: Professional title (Maître/Me) recognition and preservation
"""

import sys
from pathlib import Path

import pytest

from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

pytestmark = [
    pytest.mark.spacy,
    pytest.mark.skipif(
        sys.version_info >= (3, 14),
        reason="spaCy compatibility issue with Python 3.14+ - tests run in CI with Python 3.9-3.12",
    ),
]


class TestNerTitleImprovementsIntegration:
    """Integration test suite for Story 3.9 improvements."""

    @pytest.fixture
    def detector(self) -> HybridDetector:
        """Create and load a HybridDetector instance."""
        hybrid_detector = HybridDetector()
        hybrid_detector.load_model("fr_core_news_lg")
        return hybrid_detector

    @pytest.fixture
    def interview_05_path(self) -> Path:
        """Path to interview_05.txt test corpus document."""
        return Path("tests/test_corpus/interview_transcripts/interview_05.txt")

    @pytest.fixture
    def interview_05_text(self, interview_05_path: Path) -> str:
        """Read interview_05.txt content."""
        return interview_05_path.read_text(encoding="utf-8")

    # AC2: Cabinet Pattern Integration Tests
    def test_cabinet_pattern_integration(self, detector: HybridDetector) -> None:
        """Test Cabinet pattern detected as ORG in document context."""
        document = """
        Le Cabinet Mercier & Associés représente SoftTech Industries dans ce litige.
        Leur directeur juridique, M. Hans Mueller, a contacté le Cabinet Dupont et Martin
        pour une consultation. Les deux cabinets sont basés à Paris.
        """

        entities = detector.detect_entities(document)

        # Find ORG entities
        orgs = [e for e in entities if e.entity_type == "ORG"]
        org_texts = [e.text for e in orgs]

        # Cabinet Mercier & Associés should be detected as ORG
        assert any(
            "Cabinet Mercier & Associés" in text for text in org_texts
        ), f"Cabinet Mercier & Associés should be ORG, got: {org_texts}"

        # Cabinet Dupont et Martin should be detected as ORG
        assert any(
            "Cabinet Dupont" in text and "Martin" in text for text in org_texts
        ), f"Cabinet Dupont et Martin should be ORG, got: {org_texts}"

    def test_cabinet_detected_as_org_in_hybrid(self, detector: HybridDetector) -> None:
        """Test Cabinet patterns ARE detected as ORG by regex in hybrid detector.

        Note: spaCy may still detect partial matches like 'Cabinet Mercier' as PERSON.
        The fix ensures our regex pattern correctly detects the full org name as ORG.
        In validation mode, users can confirm/correct the entity type.
        """
        document = "Cabinet Mercier & Associés représente le client. M. Mercier est l'associé principal."

        entities = detector.detect_entities(document)

        # Find ORG entities - the key fix is that Cabinet IS now detected as ORG
        orgs = [e for e in entities if e.entity_type == "ORG"]
        org_texts = [e.text for e in orgs]

        # Cabinet Mercier & Associés should be detected as ORG by regex
        assert any(
            "Cabinet Mercier & Associés" in text for text in org_texts
        ), f"Cabinet Mercier & Associés should be ORG, got: {org_texts}"

        # M. Mercier should still be detected as PERSON
        persons = [e for e in entities if e.entity_type == "PERSON"]
        person_texts = [e.text for e in persons]
        assert any(
            "Mercier" in text for text in person_texts
        ), f"M. Mercier should be detected as PERSON, got: {person_texts}"

    # AC4: Professional Title Integration Tests
    def test_professional_titles_integration(self, detector: HybridDetector) -> None:
        """Test Maître/Me titles are detected in document context."""
        document = """
        Maître Dubois représente le plaignant. Me Mercier est l'avocat de la défense.
        Me. Fontaine a été consulté pour un avis juridique. Maître Antoine Martin
        assistait à l'audience.
        """

        entities = detector.detect_entities(document)

        # Find PERSON entities
        persons = [e for e in entities if e.entity_type == "PERSON"]
        person_texts = [e.text for e in persons]

        # Maître Dubois should be detected
        assert any(
            "Maître Dubois" in text or "Dubois" in text for text in person_texts
        ), f"Maître Dubois should be detected, got: {person_texts}"

        # Me Mercier should be detected
        assert any(
            "Me Mercier" in text or "Mercier" in text for text in person_texts
        ), f"Me Mercier should be detected, got: {person_texts}"

        # Maître Antoine Martin should be detected
        assert any(
            "Antoine Martin" in text or "Maître Antoine" in text
            for text in person_texts
        ), f"Maître Antoine Martin should be detected, got: {person_texts}"

    # AC6: Test Corpus Validation - interview_05.txt
    def test_interview_05_cabinet_detection(
        self, detector: HybridDetector, interview_05_text: str
    ) -> None:
        """Test Cabinet Mercier & Associés detected as ORG in interview_05.txt."""
        entities = detector.detect_entities(interview_05_text)

        # Find ORG entities
        orgs = [e for e in entities if e.entity_type == "ORG"]
        org_texts = [e.text for e in orgs]

        # Cabinet Mercier & Associés should be detected as ORG
        assert any(
            "Cabinet Mercier & Associés" in text for text in org_texts
        ), f"Cabinet Mercier & Associés should be ORG in interview_05.txt, got: {org_texts}"

    def test_interview_05_professional_titles(
        self, detector: HybridDetector, interview_05_text: str
    ) -> None:
        """Test Maître/Me titles detected in interview_05.txt."""
        entities = detector.detect_entities(interview_05_text)

        # Find PERSON entities
        persons = [e for e in entities if e.entity_type == "PERSON"]
        person_texts = [e.text for e in persons]

        # Me Antoine Mercier should be detected
        assert any(
            "Antoine Mercier" in text or "Me Antoine" in text for text in person_texts
        ), f"Me Antoine Mercier should be detected, got: {person_texts}"

        # Maître Mercier should be detected (line 5)
        assert any(
            "Maître Mercier" in text or "Mercier" in text for text in person_texts
        ), f"Maître Mercier should be detected, got: {person_texts}"

        # Maître Sarah Goldman should be detected (line 11)
        assert any(
            "Sarah Goldman" in text or "Maître Sarah" in text for text in person_texts
        ), f"Maître Sarah Goldman should be detected, got: {person_texts}"

    def test_interview_05_full_processing(
        self, detector: HybridDetector, interview_05_text: str
    ) -> None:
        """End-to-end test: process interview_05.txt and verify all expected entities."""
        entities = detector.detect_entities(interview_05_text)

        # Collect entities by type
        persons = [e for e in entities if e.entity_type == "PERSON"]
        orgs = [e for e in entities if e.entity_type == "ORG"]
        locations = [e for e in entities if e.entity_type == "LOCATION"]

        # Expected entity counts (minimum - conservative to account for NLP variability)
        assert (
            len(persons) >= 10
        ), f"Expected at least 10 PERSON entities, got {len(persons)}"
        assert len(orgs) >= 3, f"Expected at least 3 ORG entities, got {len(orgs)}"
        assert (
            len(locations) >= 2
        ), f"Expected at least 2 LOCATION entities, got {len(locations)}"

        # Verify specific key entities
        person_texts = [e.text for e in persons]
        org_texts = [e.text for e in orgs]
        location_texts = [e.text for e in locations]

        # Key PERSON entities
        assert any(
            "Mercier" in text for text in person_texts
        ), "Mercier should be detected"
        assert any(
            "Rousseau" in text for text in person_texts
        ), "Rousseau should be detected"

        # Key ORG entities (Bug #3 fix validation)
        assert any(
            "Cabinet" in text for text in org_texts
        ), "Cabinet should be detected as ORG"

        # Key LOCATION entities
        assert any(
            "Paris" in text for text in location_texts
        ), "Paris should be detected"

    def test_interview_05_cabinet_as_org(
        self, detector: HybridDetector, interview_05_text: str
    ) -> None:
        """Verify Cabinet Mercier & Associés IS detected as ORG in interview_05.txt.

        Note: spaCy may also detect 'Cabinet Mercier' as PERSON due to NLP limitations.
        The key fix (Bug #3) ensures our regex pattern detects the full org name as ORG.
        """
        entities = detector.detect_entities(interview_05_text)

        # Find ORG entities - this is the key fix we're validating
        orgs = [e for e in entities if e.entity_type == "ORG"]
        org_texts = [e.text for e in orgs]

        # Cabinet Mercier & Associés should be detected as ORG by regex
        assert any(
            "Cabinet Mercier & Associés" in text or "Cabinet Mercier" in text
            for text in org_texts
        ), f"Cabinet should be detected as ORG in interview_05.txt, got: {org_texts}"

        # Bug #3 fix: Cabinet should NOT be detected as PERSON
        persons = [e for e in entities if e.entity_type == "PERSON"]
        person_texts = [e.text for e in persons]
        cabinet_as_person = [text for text in person_texts if "Cabinet" in text]
        assert (
            len(cabinet_as_person) == 0
        ), f"Cabinet should NOT be detected as PERSON, got: {cabinet_as_person}"
