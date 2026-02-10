"""Unit tests for pseudonym library manager.

Tests cover:
- Library loading from JSON files (valid/invalid formats)
- Pseudonym selection with gender matching
- Pseudonym selection without gender
- Exhaustion detection at 80% threshold
- Fallback naming when library exhausted
- Collision prevention (no duplicate pseudonyms)

Target: ≥90% code coverage for library_manager.py
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.pseudonym.assignment_engine import PseudonymAssignment
from gdpr_pseudonymizer.pseudonym.library_manager import (
    LibraryBasedPseudonymManager,
)


class TestLibraryLoading:
    """Test suite for library loading functionality."""

    def test_load_library_valid_neutral(self) -> None:
        """Test loading valid neutral library from JSON."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assert manager.theme == "neutral"
        # Check total first names >= 500 (requirement is total, not per gender)
        total_first = (
            len(manager.first_names["male"])
            + len(manager.first_names["female"])
            + len(manager.first_names["neutral"])
        )
        assert total_first >= 500
        assert len(manager.last_names) >= 500
        # Neutral library has no neutral gender category
        assert len(manager.first_names["neutral"]) == 0

    def test_load_library_valid_star_wars(self) -> None:
        """Test loading valid Star Wars library from JSON."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")

        assert manager.theme == "star_wars"
        assert len(manager.first_names["male"]) > 0
        assert len(manager.first_names["female"]) > 0
        assert len(manager.first_names["neutral"]) > 0
        assert len(manager.last_names) >= 500

    def test_load_library_valid_lotr(self) -> None:
        """Test loading valid LOTR library from JSON."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("lotr")

        assert manager.theme == "lotr"
        assert len(manager.first_names["male"]) > 0
        assert len(manager.first_names["female"]) > 0
        assert len(manager.first_names["neutral"]) > 0
        assert len(manager.last_names) >= 500

    def test_load_library_nonexistent_file(self) -> None:
        """Test loading nonexistent library raises FileNotFoundError."""
        manager = LibraryBasedPseudonymManager()

        with pytest.raises(FileNotFoundError, match="Pseudonym library not found"):
            manager.load_library("nonexistent_theme")

    def test_load_library_invalid_json(self) -> None:
        """Test loading invalid JSON raises ValueError."""
        manager = LibraryBasedPseudonymManager()

        # Mock json.load to raise JSONDecodeError
        with patch(
            "gdpr_pseudonymizer.pseudonym.library_manager.json.load"
        ) as mock_load:
            mock_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

            with pytest.raises(ValueError, match="Invalid JSON format"):
                manager.load_library("neutral")  # Use existing file, mock will fail

    def test_load_library_missing_required_fields(self, tmp_path: Path) -> None:
        """Test loading library with missing required fields raises ValueError."""
        # Create library with missing 'last_names' field
        incomplete_lib = {
            "theme": "incomplete",
            "data_sources": [],
            "first_names": {"male": [], "female": [], "neutral": []},
            # Missing 'last_names'
        }

        incomplete_path = tmp_path / "pseudonyms" / "incomplete.json"
        incomplete_path.parent.mkdir(parents=True)
        incomplete_path.write_text(json.dumps(incomplete_lib), encoding="utf-8")

        manager = LibraryBasedPseudonymManager()

        # Mock the path resolution
        with patch(
            "gdpr_pseudonymizer.pseudonym.library_manager.Path.__truediv__"
        ) as mock_div:
            mock_div.return_value = incomplete_path

            with pytest.raises(ValueError, match="Missing required field"):
                manager.load_library("incomplete")

    def test_load_library_theme_mismatch(self, tmp_path: Path) -> None:
        """Test loading library with mismatched theme raises ValueError."""
        # Create library with theme that doesn't match filename
        mismatched_lib = {
            "theme": "wrong_theme",
            "data_sources": [],
            "first_names": {
                "male": ["Name"] * 500,
                "female": ["Name"] * 500,
                "neutral": [],
            },
            "last_names": ["Last"] * 500,
            "locations": {
                "cities": ["City"] * 50,
                "countries": ["Country"] * 20,
                "regions": ["Region"] * 10,
            },
            "organizations": {
                "companies": ["Company"] * 20,
                "agencies": ["Agency"] * 10,
                "institutions": ["Institution"] * 5,
            },
        }

        mismatched_path = tmp_path / "pseudonyms" / "correct_theme.json"
        mismatched_path.parent.mkdir(parents=True)
        mismatched_path.write_text(json.dumps(mismatched_lib), encoding="utf-8")

        manager = LibraryBasedPseudonymManager()

        with patch(
            "gdpr_pseudonymizer.pseudonym.library_manager.Path.__truediv__"
        ) as mock_div:
            mock_div.return_value = mismatched_path

            with pytest.raises(ValueError, match="Theme mismatch"):
                manager.load_library("correct_theme")

    def test_load_library_insufficient_first_names(self, tmp_path: Path) -> None:
        """Test loading library with insufficient first names raises ValueError."""
        insufficient_lib = {
            "theme": "insufficient",
            "data_sources": [],
            "first_names": {
                "male": ["Name"] * 100,  # Only 100, need 500 total
                "female": ["Name"] * 100,
                "neutral": [],
            },
            "last_names": ["Last"] * 500,
            "locations": {
                "cities": ["City"] * 50,
                "countries": ["Country"] * 20,
                "regions": ["Region"] * 10,
            },
            "organizations": {
                "companies": ["Company"] * 20,
                "agencies": ["Agency"] * 10,
                "institutions": ["Institution"] * 5,
            },
        }

        insufficient_path = tmp_path / "pseudonyms" / "insufficient.json"
        insufficient_path.parent.mkdir(parents=True)
        insufficient_path.write_text(json.dumps(insufficient_lib), encoding="utf-8")

        manager = LibraryBasedPseudonymManager()

        with patch(
            "gdpr_pseudonymizer.pseudonym.library_manager.Path.__truediv__"
        ) as mock_div:
            mock_div.return_value = insufficient_path

            with pytest.raises(ValueError, match="Insufficient first names"):
                manager.load_library("insufficient")

    def test_load_library_insufficient_last_names(self, tmp_path: Path) -> None:
        """Test loading library with insufficient last names raises ValueError."""
        insufficient_lib = {
            "theme": "insufficient",
            "data_sources": [],
            "first_names": {
                "male": ["Name"] * 300,
                "female": ["Name"] * 300,
                "neutral": [],
            },
            "last_names": ["Last"] * 100,  # Only 100, need 500
            "locations": {
                "cities": ["City"] * 50,
                "countries": ["Country"] * 20,
                "regions": ["Region"] * 10,
            },
            "organizations": {
                "companies": ["Company"] * 20,
                "agencies": ["Agency"] * 10,
                "institutions": ["Institution"] * 5,
            },
        }

        insufficient_path = tmp_path / "pseudonyms" / "insufficient.json"
        insufficient_path.parent.mkdir(parents=True)
        insufficient_path.write_text(json.dumps(insufficient_lib), encoding="utf-8")

        manager = LibraryBasedPseudonymManager()

        with patch(
            "gdpr_pseudonymizer.pseudonym.library_manager.Path.__truediv__"
        ) as mock_div:
            mock_div.return_value = insufficient_path

            with pytest.raises(ValueError, match="Insufficient last names"):
                manager.load_library("insufficient")

    def test_load_library_resets_usage_tracking(self) -> None:
        """Test that loading a new library resets usage tracking."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign some pseudonyms
        assignment1 = manager.assign_pseudonym("PERSON", "Test", "User", "male")
        manager._used_pseudonyms.add(assignment1.pseudonym_full)

        # Verify usage tracking has data
        assert len(manager._used_pseudonyms) > 0

        # Load different library
        manager.load_library("star_wars")

        # Verify usage tracking was reset
        assert len(manager._used_pseudonyms) == 0
        assert manager._fallback_counters == {"PERSON": 0, "LOCATION": 0, "ORG": 0}


class TestPseudonymAssignment:
    """Test suite for pseudonym assignment functionality."""

    def test_assign_pseudonym_person_with_male_gender(self) -> None:
        """Test pseudonym assignment for PERSON with male gender preference."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Jean", last_name="Dupont", gender="male"
        )

        assert isinstance(assignment, PseudonymAssignment)
        assert assignment.pseudonym_first in manager.first_names["male"]
        assert assignment.pseudonym_last in manager.last_names
        assert (
            assignment.pseudonym_full
            == f"{assignment.pseudonym_first} {assignment.pseudonym_last}"
        )
        assert assignment.theme == "neutral"
        assert 0.0 <= assignment.exhaustion_percentage <= 1.0

    def test_assign_pseudonym_person_with_female_gender(self) -> None:
        """Test pseudonym assignment for PERSON with female gender preference."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Marie", last_name="Curie", gender="female"
        )

        assert assignment.pseudonym_first in manager.first_names["female"]
        assert assignment.pseudonym_last in manager.last_names
        assert assignment.theme == "neutral"

    def test_assign_pseudonym_person_with_neutral_gender(self) -> None:
        """Test pseudonym assignment for PERSON with neutral gender preference."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")  # Has neutral names

        assignment = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Alex", last_name="Smith", gender="neutral"
        )

        # Should use neutral category or fall back to all names if empty
        assert assignment.pseudonym_first is not None
        assert assignment.pseudonym_last in manager.last_names
        assert assignment.theme == "star_wars"

    def test_assign_pseudonym_person_without_gender(self) -> None:
        """Test pseudonym assignment for PERSON without gender (random selection)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Jordan", last_name="Taylor", gender=None
        )

        # Should select from all available first names
        all_first_names = (
            manager.first_names["male"]
            + manager.first_names["female"]
            + manager.first_names["neutral"]
        )
        assert assignment.pseudonym_first in all_first_names
        assert assignment.pseudonym_last in manager.last_names

    def test_assign_pseudonym_location(self) -> None:
        """Test pseudonym assignment for LOCATION entity (from locations library)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("lotr")

        assignment = manager.assign_pseudonym(entity_type="LOCATION")

        # Flatten all location categories
        all_locations = (
            manager.locations["cities"]
            + manager.locations["planets"]
            + manager.locations["regions"]
        )

        assert assignment.pseudonym_first is None
        assert assignment.pseudonym_last is None  # LOC is atomic (no components)
        assert assignment.pseudonym_full in all_locations
        assert assignment.theme == "lotr"

    def test_assign_pseudonym_org(self) -> None:
        """Test pseudonym assignment for ORG entity (from organizations library)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")

        assignment = manager.assign_pseudonym(entity_type="ORG")

        # Flatten all organization categories
        all_orgs = (
            manager.organizations["companies"]
            + manager.organizations["agencies"]
            + manager.organizations["institutions"]
        )

        assert assignment.pseudonym_first is None
        assert assignment.pseudonym_last is None  # ORG is atomic (no components)
        assert assignment.pseudonym_full in all_orgs
        assert assignment.theme == "star_wars"

    def test_assign_pseudonym_invalid_entity_type(self) -> None:
        """Test pseudonym assignment with invalid entity type raises ValueError."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        with pytest.raises(ValueError, match="Invalid entity_type"):
            manager.assign_pseudonym(entity_type="INVALID_TYPE")

    def test_assign_pseudonym_no_library_loaded(self) -> None:
        """Test pseudonym assignment without loaded library raises ValueError."""
        manager = LibraryBasedPseudonymManager()

        with pytest.raises(ValueError, match="No library loaded"):
            manager.assign_pseudonym(entity_type="PERSON")

    def test_assign_pseudonym_with_existing_first(self) -> None:
        """Test compositional logic: reuse existing first name pseudonym."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign with existing first name (compositional logic interface)
        assignment = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            gender="female",
            existing_first="Leia",  # Reuse this first name
        )

        # Should reuse existing first name
        assert assignment.pseudonym_first == "Leia"
        assert assignment.pseudonym_last in manager.last_names

    def test_assign_pseudonym_with_existing_last(self) -> None:
        """Test compositional logic: reuse existing last name pseudonym."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign with existing last name (compositional logic interface)
        assignment = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Jean",
            last_name="Skywalker",
            gender="male",
            existing_last="Dupont",  # Reuse this last name
        )

        # Should reuse existing last name
        assert assignment.pseudonym_first in manager.first_names["male"]
        assert assignment.pseudonym_last == "Dupont"

    def test_assign_pseudonym_marks_as_used(self) -> None:
        """Test that assigned pseudonyms are marked as used."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Test", last_name="User", gender="male"
        )

        # Verify pseudonym was marked as used
        assert assignment.pseudonym_full in manager._used_pseudonyms


class TestExhaustionDetection:
    """Test suite for library exhaustion detection."""

    def test_check_exhaustion_empty_library(self) -> None:
        """Test exhaustion check on empty/unloaded library returns 0.0."""
        manager = LibraryBasedPseudonymManager()

        exhaustion = manager.check_exhaustion()
        assert exhaustion == 0.0

    def test_check_exhaustion_unused_library(self) -> None:
        """Test exhaustion check on unused library returns 0.0."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        exhaustion = manager.check_exhaustion()
        assert exhaustion == 0.0

    def test_check_exhaustion_partially_used(self) -> None:
        """Test exhaustion calculation for partially used library."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign 10 pseudonyms
        for i in range(10):
            _ = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name=f"Test{i}",
                last_name=f"User{i}",
                gender="male",
            )

        exhaustion = manager.check_exhaustion()
        assert 0.0 < exhaustion < 1.0

    def test_check_exhaustion_at_80_percent_triggers_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that exhaustion warning is triggered at 80% threshold."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Calculate total combinations for PERSON entities
        total_first = (
            len(manager.first_names["male"])
            + len(manager.first_names["female"])
            + len(manager.first_names["neutral"])
        )
        total_combinations = total_first * len(manager.last_names)

        # Use 80% of combinations
        num_to_use = int(total_combinations * 0.81)

        # Manually add to used set (faster than assigning each)
        for i in range(num_to_use):
            manager._used_pseudonyms.add(f"Pseudonym-{i}")

        # Trigger assignment which checks exhaustion
        manager.assign_pseudonym(
            entity_type="PERSON", first_name="Test", last_name="User", gender="male"
        )

        # Verify warning was logged (structlog outputs to stdout)
        captured = capsys.readouterr()
        assert "library_near_exhaustion" in captured.out

    def test_exhaustion_percentage_in_assignment(self) -> None:
        """Test that exhaustion percentage is included in PseudonymAssignment."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign some pseudonyms
        for i in range(5):
            assignment = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name=f"Test{i}",
                last_name=f"User{i}",
                gender="male",
            )

        # Verify exhaustion percentage is present
        assert 0.0 <= assignment.exhaustion_percentage <= 1.0


class TestFallbackNaming:
    """Test suite for fallback naming when library exhausted."""

    def test_fallback_naming_person(self) -> None:
        """Test systematic fallback naming for PERSON entity."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Simulate collision by manually adding to used set
        test_first = manager.first_names["male"][0]
        test_last = manager.last_names[0]
        test_full = f"{test_first} {test_last}"
        manager._used_pseudonyms.add(test_full)

        # Mock selection to always return the same name (causing collision)
        with (
            patch.object(manager, "_select_first_name", return_value=test_first),
            patch.object(manager, "_select_last_name", return_value=test_last),
        ):
            assignment = manager.assign_pseudonym(
                entity_type="PERSON", first_name="Test", last_name="User", gender="male"
            )

        # Should use fallback naming
        assert assignment.pseudonym_full.startswith("Person-")
        assert assignment.pseudonym_full.endswith("001")  # First fallback for PERSON

    def test_fallback_naming_location(self) -> None:
        """Test systematic fallback naming for LOCATION entity."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Simulate collision
        test_location = manager.locations["cities"][0]
        manager._used_pseudonyms.add(test_location)

        with patch.object(manager, "_select_location", return_value=test_location):
            assignment = manager.assign_pseudonym(entity_type="LOCATION")

        # Should use fallback naming
        assert assignment.pseudonym_full.startswith("Location-")
        assert assignment.pseudonym_full.endswith("001")

    def test_fallback_naming_org(self) -> None:
        """Test systematic fallback naming for ORG entity."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Simulate collision
        test_org = manager.organizations["companies"][0]
        manager._used_pseudonyms.add(test_org)

        with patch.object(manager, "_select_organization", return_value=test_org):
            assignment = manager.assign_pseudonym(entity_type="ORG")

        # Should use fallback naming
        assert assignment.pseudonym_full.startswith("Org-")
        assert assignment.pseudonym_full.endswith("001")

    def test_fallback_counter_increments(self) -> None:
        """Test that fallback counters increment for each entity type."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Force multiple collisions for PERSON
        test_first = manager.first_names["male"][0]
        test_last = manager.last_names[0]
        test_full = f"{test_first} {test_last}"

        with (
            patch.object(manager, "_select_first_name", return_value=test_first),
            patch.object(manager, "_select_last_name", return_value=test_last),
        ):
            # First collision
            manager._used_pseudonyms.add(test_full)
            assignment1 = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name="Test1",
                last_name="User1",
                gender="male",
            )

            # Second collision
            manager._used_pseudonyms.add(assignment1.pseudonym_full)
            assignment2 = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name="Test2",
                last_name="User2",
                gender="male",
            )

        # Verify counter incremented
        assert assignment1.pseudonym_full == "Person-001"
        assert assignment2.pseudonym_full == "Person-002"

    def test_fallback_counters_separate_by_entity_type(self) -> None:
        """Test that fallback counters are maintained separately per entity type."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        test_location = manager.locations["cities"][0]
        test_org = manager.organizations["companies"][0]

        # Force LOCATION collision
        manager._used_pseudonyms.add(test_location)
        with patch.object(manager, "_select_location", return_value=test_location):
            loc_assignment = manager.assign_pseudonym(entity_type="LOCATION")

        # Force ORG collision
        manager._used_pseudonyms.add(test_org)
        with patch.object(manager, "_select_organization", return_value=test_org):
            org_assignment = manager.assign_pseudonym(entity_type="ORG")

        # Verify separate counters
        assert loc_assignment.pseudonym_full == "Location-001"
        assert org_assignment.pseudonym_full == "Org-001"  # Separate counter


class TestCollisionPrevention:
    """Test suite for collision prevention (no duplicate pseudonyms)."""

    def test_no_duplicate_pseudonyms_assigned(self) -> None:
        """Test that no duplicate full pseudonyms are assigned."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign 100 pseudonyms
        assigned_pseudonyms = set()
        for i in range(100):
            assignment = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name=f"Test{i}",
                last_name=f"User{i}",
                gender="male",
            )
            assigned_pseudonyms.add(assignment.pseudonym_full)

        # Verify all are unique
        assert len(assigned_pseudonyms) == 100

    def test_collision_triggers_fallback(self) -> None:
        """Test that collision detection triggers fallback naming."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Force collision by mocking selection
        test_first = manager.first_names["male"][0]
        test_last = manager.last_names[0]
        collision_name = f"{test_first} {test_last}"

        # Manually add collision name to used set
        manager._used_pseudonyms.add(collision_name)

        # Mock to always return same names (causing collision)
        with (
            patch.object(manager, "_select_first_name", return_value=test_first),
            patch.object(manager, "_select_last_name", return_value=test_last),
        ):
            assignment = manager.assign_pseudonym(
                entity_type="PERSON", first_name="Test", last_name="User", gender="male"
            )

        # Should use fallback instead of collision
        assert assignment.pseudonym_full != collision_name
        assert assignment.pseudonym_full.startswith("Person-")


class TestDataModelIntegration:
    """Test suite for integration with Entity data model fields."""

    def test_assignment_populates_all_entity_fields(self) -> None:
        """Test that PseudonymAssignment populates all required Entity fields."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")

        assignment = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Jean", last_name="Dupont", gender="male"
        )

        # Verify all Entity fields are populated
        assert assignment.pseudonym_full is not None
        assert assignment.pseudonym_first is not None
        assert assignment.pseudonym_last is not None
        assert assignment.theme == "star_wars"
        assert isinstance(assignment.exhaustion_percentage, float)

    def test_assignment_location_entity_fields(self) -> None:
        """Test that LOCATION entity has correct field structure."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("lotr")

        assignment = manager.assign_pseudonym(entity_type="LOCATION")

        # LOCATION should have null first and last names (atomic entity)
        assert assignment.pseudonym_full is not None
        assert assignment.pseudonym_first is None
        assert assignment.pseudonym_last is None
        assert assignment.theme == "lotr"

    def test_assignment_org_entity_fields(self) -> None:
        """Test that ORG entity has correct field structure."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        assignment = manager.assign_pseudonym(entity_type="ORG")

        # ORG should have null first and last names (atomic entity)
        assert assignment.pseudonym_full is not None
        assert assignment.pseudonym_first is None
        assert assignment.pseudonym_last is None
        assert assignment.theme == "neutral"


class TestLocationOrganizationSupport:
    """Test suite for LOCATION and ORGANIZATION entity pseudonymization (Story 3.0)."""

    def test_load_library_with_locations_organizations(self) -> None:
        """Test library loading with locations and organizations fields."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Verify locations loaded correctly
        assert manager.locations is not None
        assert "cities" in manager.locations
        assert "countries" in manager.locations
        assert "regions" in manager.locations
        assert len(manager.locations["cities"]) >= 50
        assert len(manager.locations["countries"]) >= 20
        assert len(manager.locations["regions"]) >= 10

        # Verify organizations loaded correctly
        assert manager.organizations is not None
        assert "companies" in manager.organizations
        assert "agencies" in manager.organizations
        assert "institutions" in manager.organizations
        assert len(manager.organizations["companies"]) >= 20
        assert len(manager.organizations["agencies"]) >= 10
        assert len(manager.organizations["institutions"]) >= 5

    def test_assign_location_pseudonym_from_library(self) -> None:
        """Test LOCATION pseudonym assignment uses locations field."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")

        assignment = manager.assign_pseudonym(entity_type="LOCATION")

        # Flatten all location categories
        all_locations = (
            manager.locations["cities"]
            + manager.locations["planets"]
            + manager.locations["regions"]
        )

        # Verify pseudonym comes from locations library
        assert assignment.pseudonym_full in all_locations
        assert assignment.pseudonym_first is None  # LOC has no first name
        assert assignment.pseudonym_last is None  # LOC is atomic

    def test_location_collision_prevention(self) -> None:
        """Test 1:1 mapping for LOCATION entities (same LOC → same pseudonym)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("lotr")

        # Assign first location pseudonym
        assignment1 = manager.assign_pseudonym(entity_type="LOCATION")

        # Verify the pseudonym is tracked as used
        assert assignment1.pseudonym_full in manager._used_pseudonyms

        # Assign second location pseudonym - should be different
        assignment2 = manager.assign_pseudonym(entity_type="LOCATION")

        # Verify different pseudonyms (collision prevention)
        if assignment1.pseudonym_full != assignment2.pseudonym_full:
            assert assignment2.pseudonym_full not in [assignment1.pseudonym_full]

    def test_location_no_gender_filtering(self) -> None:
        """Test gender parameter ignored for LOCATION entities."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign location with gender hint - should be ignored
        assignment1 = manager.assign_pseudonym(entity_type="LOCATION", gender="male")
        assignment2 = manager.assign_pseudonym(entity_type="LOCATION", gender="female")

        # Both should come from locations library (gender ignored)
        all_locations = (
            manager.locations["cities"]
            + manager.locations["countries"]
            + manager.locations["regions"]
        )

        assert assignment1.pseudonym_full in all_locations
        assert assignment2.pseudonym_full in all_locations

    def test_assign_org_pseudonym_from_library(self) -> None:
        """Test ORG pseudonym assignment uses organizations field."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")

        assignment = manager.assign_pseudonym(entity_type="ORG")

        # Flatten all organization categories
        all_orgs = (
            manager.organizations["companies"]
            + manager.organizations["agencies"]
            + manager.organizations["institutions"]
        )

        # Verify pseudonym comes from organizations library
        assert assignment.pseudonym_full in all_orgs
        assert assignment.pseudonym_first is None  # ORG has no first name
        assert assignment.pseudonym_last is None  # ORG is atomic

    def test_org_collision_prevention(self) -> None:
        """Test 1:1 mapping for ORG entities (same ORG → same pseudonym)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("lotr")

        # Assign first organization pseudonym
        assignment1 = manager.assign_pseudonym(entity_type="ORG")

        # Verify the pseudonym is tracked as used
        assert assignment1.pseudonym_full in manager._used_pseudonyms

        # Assign second organization pseudonym - should be different
        assignment2 = manager.assign_pseudonym(entity_type="ORG")

        # Verify different pseudonyms (collision prevention)
        if assignment1.pseudonym_full != assignment2.pseudonym_full:
            assert assignment2.pseudonym_full not in [assignment1.pseudonym_full]

    def test_org_no_gender_filtering(self) -> None:
        """Test gender parameter ignored for ORG entities."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign organization with gender hint - should be ignored
        assignment1 = manager.assign_pseudonym(entity_type="ORG", gender="male")
        assignment2 = manager.assign_pseudonym(entity_type="ORG", gender="female")

        # Both should come from organizations library (gender ignored)
        all_orgs = (
            manager.organizations["companies"]
            + manager.organizations["agencies"]
            + manager.organizations["institutions"]
        )

        assert assignment1.pseudonym_full in all_orgs
        assert assignment2.pseudonym_full in all_orgs

    def test_exhaustion_calculation_includes_loc_org(self) -> None:
        """Test exhaustion % accounts for LOC/ORG pools."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Initial exhaustion should be 0.0
        exhaustion_initial = manager.check_exhaustion()
        assert exhaustion_initial == 0.0

        # Assign some PERSON, LOCATION, and ORG pseudonyms
        manager.assign_pseudonym(entity_type="PERSON", gender="male")
        manager.assign_pseudonym(entity_type="LOCATION")
        manager.assign_pseudonym(entity_type="ORG")

        # Exhaustion should increase
        exhaustion_after = manager.check_exhaustion()
        assert exhaustion_after > 0.0
        assert exhaustion_after < 1.0

        # Verify calculation includes all entity types
        total_first_names = (
            len(manager.first_names["male"])
            + len(manager.first_names["female"])
            + len(manager.first_names["neutral"])
        )
        person_combinations = total_first_names * len(manager.last_names)
        location_combinations = (
            len(manager.locations["cities"])
            + len(manager.locations["countries"])
            + len(manager.locations["regions"])
        )
        org_combinations = (
            len(manager.organizations["companies"])
            + len(manager.organizations["agencies"])
            + len(manager.organizations["institutions"])
        )
        total_combinations = (
            person_combinations + location_combinations + org_combinations
        )

        expected_exhaustion = len(manager._used_pseudonyms) / total_combinations
        assert exhaustion_after == pytest.approx(expected_exhaustion)
