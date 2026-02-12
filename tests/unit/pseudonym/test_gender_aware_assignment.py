"""Unit tests for gender-aware pseudonym assignment (Story 5.2, Task 5.2.8)."""

from __future__ import annotations

from unittest.mock import Mock

from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
    PseudonymAssignment,
)
from gdpr_pseudonymizer.pseudonym.gender_detector import GenderDetector
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager


class TestGenderAwarePseudonymSelection:
    """Test pseudonym selection respects gender (AC3)."""

    def test_assign_pseudonym_male_selects_from_male(self) -> None:
        """Male gender should select from male first names."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Jean",
            last_name="Dupont",
            gender="male",
        )

        assert assignment.pseudonym_first is not None
        assert assignment.pseudonym_first in manager.first_names["male"]

    def test_assign_pseudonym_female_selects_from_female(self) -> None:
        """Female gender should select from female first names."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            gender="female",
        )

        assert assignment.pseudonym_first is not None
        assert assignment.pseudonym_first in manager.first_names["female"]

    def test_assign_pseudonym_none_gender_uses_combined(self) -> None:
        """None gender should select from combined list (regression test)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Xyzabc",
            last_name="Smith",
            gender=None,
        )

        # Should get a pseudonym from the combined list (male + female + neutral)
        all_first_names = (
            manager.first_names["male"]
            + manager.first_names["female"]
            + manager.first_names["neutral"]
        )
        assert assignment.pseudonym_first is not None
        assert assignment.pseudonym_first in all_first_names


class TestCompositionalEngineGenderAutoDetect:
    """Test CompositionalPseudonymEngine auto-detects gender."""

    def test_engine_with_detector_auto_detects_gender(self) -> None:
        """Engine with gender_detector should auto-detect gender from entity text."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        mock_repo.find_by_component.return_value = []

        detector = GenderDetector()
        detector.load()

        mock_manager.assign_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Léa Martin",
            pseudonym_first="Léa",
            pseudonym_last="Martin",
            theme="neutral",
            exhaustion_percentage=0.0,
        )

        engine = CompositionalPseudonymEngine(
            pseudonym_manager=mock_manager,
            mapping_repository=mock_repo,
            gender_detector=detector,
        )

        engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender=None,
        )

        # Verify assign_pseudonym was called with detected gender="female"
        call_kwargs = mock_manager.assign_pseudonym.call_args
        assert (
            call_kwargs[1]["gender"] == "female"
            or call_kwargs.kwargs.get("gender") == "female"
        )

    def test_engine_without_detector_preserves_none_gender(self) -> None:
        """Engine without gender_detector should preserve gender=None (backward compat)."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        mock_repo.find_by_component.return_value = []

        mock_manager.assign_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Léa Martin",
            pseudonym_first="Léa",
            pseudonym_last="Martin",
            theme="neutral",
            exhaustion_percentage=0.0,
        )

        engine = CompositionalPseudonymEngine(
            pseudonym_manager=mock_manager,
            mapping_repository=mock_repo,
            # No gender_detector
        )

        engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender=None,
        )

        # Verify assign_pseudonym was called with gender=None
        call_kwargs = mock_manager.assign_pseudonym.call_args
        assert (
            call_kwargs[1]["gender"] is None or call_kwargs.kwargs.get("gender") is None
        )

    def test_engine_explicit_gender_not_overridden(self) -> None:
        """When gender is explicitly provided, detector should not override."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        mock_repo.find_by_component.return_value = []

        detector = GenderDetector()
        detector.load()

        mock_manager.assign_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Jean Martin",
            pseudonym_first="Jean",
            pseudonym_last="Martin",
            theme="neutral",
            exhaustion_percentage=0.0,
        )

        engine = CompositionalPseudonymEngine(
            pseudonym_manager=mock_manager,
            mapping_repository=mock_repo,
            gender_detector=detector,
        )

        # Marie is female, but we explicitly pass "male"
        engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender="male",
        )

        # Verify assign_pseudonym was called with explicit gender="male"
        call_kwargs = mock_manager.assign_pseudonym.call_args
        assert (
            call_kwargs[1]["gender"] == "male"
            or call_kwargs.kwargs.get("gender") == "male"
        )

    def test_engine_non_person_no_gender_detection(self) -> None:
        """Non-PERSON entities should not get gender detection."""
        mock_manager = Mock()
        mock_repo = Mock()

        detector = GenderDetector()
        detector.load()

        mock_manager.assign_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Lyon",
            pseudonym_first=None,
            pseudonym_last=None,
            theme="neutral",
            exhaustion_percentage=0.0,
        )

        engine = CompositionalPseudonymEngine(
            pseudonym_manager=mock_manager,
            mapping_repository=mock_repo,
            gender_detector=detector,
        )

        engine.assign_compositional_pseudonym(
            entity_text="Paris",
            entity_type="LOCATION",
            gender=None,
        )

        # For LOCATION, gender should remain None
        call_kwargs = mock_manager.assign_pseudonym.call_args
        assert (
            call_kwargs[1]["gender"] is None or call_kwargs.kwargs.get("gender") is None
        )


class TestGenderConsistency:
    """Test gender consistency: same real first name always gets same-gender pseudonym."""

    def test_same_first_name_consistent_gender(self) -> None:
        """Same real first name should always produce same-gender pseudonym."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        genders_seen: set[str | None] = set()
        for _ in range(10):
            assignment = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name="Marie",
                last_name=f"Name{_}",
                gender="female",
            )
            if assignment.pseudonym_first:
                is_female = assignment.pseudonym_first in manager.first_names["female"]
                genders_seen.add("female" if is_female else "not_female")

        # All assignments should be female
        assert genders_seen == {"female"}
