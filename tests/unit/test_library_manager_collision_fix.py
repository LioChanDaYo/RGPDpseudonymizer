"""Unit tests for Story 2.8: Pseudonym Component Collision Fix.

Tests cover:
- Component-level collision prevention (different real components get different pseudonyms)
- Component reuse consistency (same real component gets same pseudonym)
- Component exhaustion handling (library exhausted after N unique assignments)
- Compositional logic integration (standalone components reuse existing mappings)
- Backwards compatibility (loading existing mappings from database)

Target: ≥95% code coverage for modified methods in library_manager.py
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdpr_pseudonymizer.pseudonym.library_manager import (
    LibraryBasedPseudonymManager,
)


class TestComponentCollisionPrevention:
    """Test suite for component-level collision prevention (Story 2.8)."""

    def test_different_last_names_get_unique_pseudonyms(self) -> None:
        """Test that different real last names get different pseudonym components.

        This is the CRITICAL test case from Story 2.7 bug discovery:
        - "Dubois" and "Lefebvre" should NEVER both map to "Neto"
        - Ensures 1:1 reversible mapping (GDPR Article 4(5))
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign pseudonyms for "Marie Dubois" and "Pierre Lefebvre"
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            gender="female",
        )

        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Pierre",
            last_name="Lefebvre",
            gender="male",
        )

        # CRITICAL: Verify last names got different pseudonyms
        assert assignment1.pseudonym_last != assignment2.pseudonym_last
        assert assignment1.pseudonym_last is not None
        assert assignment2.pseudonym_last is not None

        # Verify first names also got different pseudonyms (different real components)
        assert assignment1.pseudonym_first != assignment2.pseudonym_first
        assert assignment1.pseudonym_first is not None
        assert assignment2.pseudonym_first is not None

        # Verify full pseudonyms are different
        assert assignment1.pseudonym_full != assignment2.pseudonym_full

    def test_same_last_name_returns_same_pseudonym(self) -> None:
        """Test that same real last name returns same pseudonym (idempotency)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign pseudonym for "Dubois" first time
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            gender="female",
        )

        # Assign pseudonym for "Dubois" second time (different first name)
        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Pierre",
            last_name="Dubois",
            gender="male",
        )

        # Verify last name component is reused
        assert assignment1.pseudonym_last == assignment2.pseudonym_last

        # Verify first name components are different (different real first names)
        assert assignment1.pseudonym_first != assignment2.pseudonym_first

    def test_100_unique_last_names_no_collisions(self) -> None:
        """Test that 100 different real last names get 100 unique pseudonyms.

        This validates that the collision prevention logic works at scale.
        With neutral library (500+ last names), there should be no collisions.
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        pseudonym_last_names: set[str] = set()
        real_to_pseudonym: dict[str, str] = {}

        # Assign 100 unique last names
        for i in range(100):
            real_last_name = f"LastName{i:03d}"
            assignment = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name="Test",
                last_name=real_last_name,
                gender="neutral",
            )

            # Collect pseudonym last names
            assert assignment.pseudonym_last is not None
            pseudonym_last_names.add(assignment.pseudonym_last)
            real_to_pseudonym[real_last_name] = assignment.pseudonym_last

        # All 100 should be unique (no collisions)
        assert len(pseudonym_last_names) == 100

        # Verify mapping consistency: assign same real last name again
        assignment_recheck = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="TestRecheck",
            last_name="LastName000",
            gender="neutral",
        )
        assert assignment_recheck.pseudonym_last == real_to_pseudonym["LastName000"]

    def test_same_first_name_returns_same_pseudonym(self) -> None:
        """Test that same real first name returns same pseudonym (idempotency)."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign pseudonym for "Marie" first time
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            gender="female",
        )

        # Assign pseudonym for "Marie" second time (different last name)
        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            gender="female",
        )

        # Verify first name component is reused
        assert assignment1.pseudonym_first == assignment2.pseudonym_first

        # Verify last name components are different (different real last names)
        assert assignment1.pseudonym_last != assignment2.pseudonym_last

    def test_100_unique_first_names_no_collisions(self) -> None:
        """Test that 100 different real first names get 100 unique pseudonyms."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        pseudonym_first_names: set[str] = set()

        # Assign 100 unique first names
        for i in range(100):
            real_first_name = f"FirstName{i:03d}"
            assignment = manager.assign_pseudonym(
                entity_type="PERSON",
                first_name=real_first_name,
                last_name="CommonLastName",
                gender="neutral",
            )

            # Collect pseudonym first names
            assert assignment.pseudonym_first is not None
            pseudonym_first_names.add(assignment.pseudonym_first)

        # All 100 should be unique (no collisions)
        assert len(pseudonym_first_names) == 100

    def test_component_reuse_compositional_logic(self) -> None:
        """Test compositional reuse maintains consistency.

        Scenario (from Story 2.7 bug report):
        1. "Marie Dubois" -> "Alexia Neto"
        2. "Dubois" (standalone) -> Should reuse "Neto" mapping
        3. "Marie Dupont" -> Should reuse "Alexia" for first name
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Step 1: Assign "Marie Dubois"
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            gender="female",
        )
        marie_pseudo = assignment1.pseudonym_first
        dubois_pseudo = assignment1.pseudonym_last

        # Step 2: Assign standalone "Dubois" (last name only)
        # This should reuse the Dubois->dubois_pseudo mapping
        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name=None,
            last_name="Dubois",
            gender=None,
        )
        assert assignment2.pseudonym_last == dubois_pseudo

        # Step 3: Assign "Marie Dupont" (reuse Marie, new last name)
        assignment3 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            gender="female",
        )
        assert assignment3.pseudonym_first == marie_pseudo
        assert assignment3.pseudonym_last != dubois_pseudo  # Different last name

        # Step 4: Verify Dupont consistently maps to same pseudonym
        assignment4 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Pierre",
            last_name="Dupont",
            gender="male",
        )
        assert assignment4.pseudonym_last == assignment3.pseudonym_last


class TestComponentExhaustion:
    """Test suite for component-level exhaustion handling."""

    def test_component_exhaustion_raises_runtime_error(self) -> None:
        """Test that library exhaustion at component level raises RuntimeError.

        Uses a mock library with only 2 last names to force exhaustion.
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Override last_names with small list for testing
        manager.last_names = ["Alpha", "Beta"]

        # Assign 2 unique last names (exhaust library)
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Test1",
            last_name="RealName1",
            gender="neutral",
        )
        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Test2",
            last_name="RealName2",
            gender="neutral",
        )

        # Verify both got unique pseudonyms
        assert assignment1.pseudonym_last != assignment2.pseudonym_last

        # Third unique last name should fail (library exhausted)
        with pytest.raises(
            RuntimeError,
            match="Unable to find unique last name component for 'RealName3'",
        ):
            manager.assign_pseudonym(
                entity_type="PERSON",
                first_name="Test3",
                last_name="RealName3",
                gender="neutral",
            )

    def test_component_exhaustion_first_names(self) -> None:
        """Test exhaustion handling for first name components."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Override first_names with small list for testing
        manager.first_names = {
            "male": ["Charlie", "Delta"],
            "female": [],
            "neutral": [],
        }

        # Assign 2 unique first names (exhaust male category)
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="RealFirst1",
            last_name="Test",
            gender="male",
        )
        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="RealFirst2",
            last_name="Test",
            gender="male",
        )

        # Verify both got unique pseudonyms
        assert assignment1.pseudonym_first != assignment2.pseudonym_first

        # Third unique first name should fail (library exhausted)
        with pytest.raises(
            RuntimeError,
            match="Unable to find unique first name component for 'RealFirst3'",
        ):
            manager.assign_pseudonym(
                entity_type="PERSON",
                first_name="RealFirst3",
                last_name="Test",
                gender="male",
            )


class TestBackwardsCompatibility:
    """Test suite for backwards compatibility with existing database mappings."""

    def test_load_existing_mappings_from_database(self) -> None:
        """Test loading existing component mappings from database.

        Simulates database with existing entities to verify collision prevention
        with pre-existing data.
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Create mock entities (simulating database records)
        mock_entity1 = MagicMock()
        mock_entity1.entity_type = "PERSON"
        mock_entity1.first_name = "Marie"
        mock_entity1.last_name = "Dubois"
        mock_entity1.pseudonym_first = "Alexia"
        mock_entity1.pseudonym_last = "Neto"
        mock_entity1.pseudonym_full = "Alexia Neto"

        mock_entity2 = MagicMock()
        mock_entity2.entity_type = "PERSON"
        mock_entity2.first_name = "Pierre"
        mock_entity2.last_name = "Lefebvre"
        mock_entity2.pseudonym_first = "Maurice"
        mock_entity2.pseudonym_last = "Silva"
        mock_entity2.pseudonym_full = "Maurice Silva"

        existing_entities = [mock_entity1, mock_entity2]

        # Load existing mappings
        manager.load_existing_mappings(existing_entities)

        # Verify component mappings loaded
        assert len(manager._component_mappings) == 4  # 2 first + 2 last
        assert manager._component_mappings[("Marie", "first_name")] == "Alexia"
        assert manager._component_mappings[("Dubois", "last_name")] == "Neto"
        assert manager._component_mappings[("Pierre", "first_name")] == "Maurice"
        assert manager._component_mappings[("Lefebvre", "last_name")] == "Silva"

        # Verify full pseudonyms tracked as used
        assert "Alexia Neto" in manager._used_pseudonyms
        assert "Maurice Silva" in manager._used_pseudonyms

        # Now assign pseudonym for "Marie" - should reuse "Alexia"
        assignment = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            gender="female",
        )
        assert assignment.pseudonym_first == "Alexia"
        assert assignment.pseudonym_last != "Neto"  # Different last name

    def test_load_existing_mappings_ignores_non_person_entities(self) -> None:
        """Test that LOCATION/ORG entities don't populate component mappings.

        Only PERSON entities have component-level tracking.
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Create mock LOCATION entity
        mock_location = MagicMock()
        mock_location.entity_type = "LOCATION"
        mock_location.first_name = None
        mock_location.last_name = None
        mock_location.pseudonym_first = None
        mock_location.pseudonym_last = "Paris"
        mock_location.pseudonym_full = "Paris"

        existing_entities = [mock_location]

        # Load existing mappings
        manager.load_existing_mappings(existing_entities)

        # Verify no component mappings added (only PERSON entities tracked)
        assert len(manager._component_mappings) == 0

        # Verify full pseudonym still tracked as used
        assert "Paris" in manager._used_pseudonyms

    def test_load_existing_mappings_handles_null_components(self) -> None:
        """Test handling of entities with null component fields."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Create mock entity with null first_name
        mock_entity = MagicMock()
        mock_entity.entity_type = "PERSON"
        mock_entity.first_name = None
        mock_entity.last_name = "Dubois"
        mock_entity.pseudonym_first = None
        mock_entity.pseudonym_last = "Neto"
        mock_entity.pseudonym_full = "Neto"

        existing_entities = [mock_entity]

        # Load existing mappings (should not crash)
        manager.load_existing_mappings(existing_entities)

        # Verify only last_name mapping added
        assert len(manager._component_mappings) == 1
        assert manager._component_mappings[("Dubois", "last_name")] == "Neto"


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_component_without_real_name_no_collision_tracking(self) -> None:
        """Test that LOCATION/ORG entities don't use component collision tracking.

        If real_name is None, no component mapping is created.
        Full pseudonym collision still prevented via _used_pseudonyms.
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Override last_names with small list
        manager.last_names = ["Alpha", "Beta"]

        # Assign without real_name (LOCATION entity)
        assignment1 = manager.assign_pseudonym(
            entity_type="LOCATION",
            first_name=None,
            last_name=None,
        )

        # Another LOCATION could randomly get same pseudonym component,
        # but full pseudonym collision prevention still applies
        assignment2 = manager.assign_pseudonym(
            entity_type="LOCATION",
            first_name=None,
            last_name=None,
        )

        # First should be from library
        assert assignment1.pseudonym_full in ["Alpha", "Beta"]

        # Second could be same or different from library, OR fallback if collision
        assert (
            assignment2.pseudonym_full in ["Alpha", "Beta"]
            or assignment2.pseudonym_full == "Location-001"
        )

        # Verify no component mappings created (LOCATION entities don't track components)
        assert len(manager._component_mappings) == 0

    def test_component_mapping_persists_across_assignments(self) -> None:
        """Test that component mappings persist across multiple assignments.

        The component mappings should be reused even after many intervening
        assignments. This tests that _component_mappings dict is not cleared
        or corrupted during normal operation.
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")

        # Assign "Marie Dubois"
        assignment1 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            gender="female",
        )
        marie_pseudo = assignment1.pseudonym_first
        dubois_pseudo = assignment1.pseudonym_last

        # Assign 10 other people (different names)
        for i in range(10):
            manager.assign_pseudonym(
                entity_type="PERSON",
                first_name=f"Person{i}",
                last_name=f"Name{i}",
                gender="neutral",
            )

        # Now assign "Marie Dupont" - should reuse "Marie" component
        assignment2 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            gender="female",
        )
        assert assignment2.pseudonym_first == marie_pseudo  # Reused Marie mapping

        # Assign "Pierre Dubois" - should reuse "Dubois" component
        assignment3 = manager.assign_pseudonym(
            entity_type="PERSON",
            first_name="Pierre",
            last_name="Dubois",
            gender="male",
        )
        assert assignment3.pseudonym_last == dubois_pseudo  # Reused Dubois mapping

        # Verify component mappings count (Marie, Dubois, + 10 Person + 10 Name = 22)
        assert (
            len(manager._component_mappings) >= 12
        )  # At least Marie + Dubois + 10 others
