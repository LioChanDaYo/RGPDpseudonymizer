"""Unit tests for gender storage in Entity via DocumentProcessor (Story 5.2, Task 5.2.9)."""

from __future__ import annotations

from unittest.mock import Mock

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.gender_detector import GenderDetector


def _make_processor() -> object:
    """Create a DocumentProcessor without triggering DB or NLP init."""
    from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

    return DocumentProcessor(db_path="test.db", passphrase="test_pass")


def _make_entity(
    text: str, entity_type: str, start: int = 0, end: int = 0
) -> DetectedEntity:
    """Create a DetectedEntity for testing."""
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=end or start + len(text),
        confidence=0.95,
        source="test",
    )


class TestGenderStorageInEntity:
    """Tests for gender field population in _assign_new_pseudonym()."""

    def test_person_entity_gets_detected_gender_female(self) -> None:
        """PERSON entity with known female name gets gender='female'."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Léa Martin"
        assignment.pseudonym_first = "Léa"
        assignment.pseudonym_last = "Martin"
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )
        ctx.compositional_engine.parse_full_name.return_value = (
            "Marie",
            "Dupont",
            False,
        )

        detector = GenderDetector()
        detector.load()
        ctx.compositional_engine.gender_detector = detector

        processor = _make_processor()
        _, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Marie Dupont", "PERSON"), "Marie Dupont"
        )

        assert entity.gender == "female"

    def test_person_entity_gets_detected_gender_male(self) -> None:
        """PERSON entity with known male name gets gender='male'."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Lucas Bernard"
        assignment.pseudonym_first = "Lucas"
        assignment.pseudonym_last = "Bernard"
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )
        ctx.compositional_engine.parse_full_name.return_value = (
            "Jean",
            "Martin",
            False,
        )

        detector = GenderDetector()
        detector.load()
        ctx.compositional_engine.gender_detector = detector

        processor = _make_processor()
        _, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Jean Martin", "PERSON"), "Jean Martin"
        )

        assert entity.gender == "male"

    def test_person_entity_unknown_gender_is_none(self) -> None:
        """PERSON entity with unknown name gets gender=None."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Léa Martin"
        assignment.pseudonym_first = "Léa"
        assignment.pseudonym_last = "Martin"
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )
        ctx.compositional_engine.parse_full_name.return_value = (
            "Xyzabc",
            "Unknown",
            False,
        )

        detector = GenderDetector()
        detector.load()
        ctx.compositional_engine.gender_detector = detector

        processor = _make_processor()
        _, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Xyzabc Unknown", "PERSON"), "Xyzabc Unknown"
        )

        assert entity.gender is None

    def test_non_person_entity_gender_is_none(self) -> None:
        """Non-PERSON entity always gets gender=None."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Lyon"
        assignment.pseudonym_first = None
        assignment.pseudonym_last = None
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )

        detector = GenderDetector()
        detector.load()
        ctx.compositional_engine.gender_detector = detector

        processor = _make_processor()
        _, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Paris", "LOCATION"), "Paris"
        )

        assert entity.gender is None

    def test_no_detector_gender_is_none(self) -> None:
        """Without gender_detector, PERSON entity gets gender=None."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Léa Martin"
        assignment.pseudonym_first = "Léa"
        assignment.pseudonym_last = "Martin"
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )
        ctx.compositional_engine.parse_full_name.return_value = (
            "Marie",
            "Dupont",
            False,
        )
        ctx.compositional_engine.gender_detector = None

        processor = _make_processor()
        _, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Marie Dupont", "PERSON"), "Marie Dupont"
        )

        assert entity.gender is None
