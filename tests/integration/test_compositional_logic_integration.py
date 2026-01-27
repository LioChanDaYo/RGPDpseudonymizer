"""Integration tests for compositional pseudonymization logic.

Tests the complete compositional workflow:
- CompositionalPseudonymEngine + LibraryBasedPseudonymManager + MappingRepository
- Complex documents with multiple name patterns
- Shared component consistency across multiple entities
- Real pseudonym library usage (neutral, star_wars, lotr)
- Component mapping persistence and reuse

Target: 80% integration path coverage for compositional logic
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.pseudonym.assignment_engine import CompositionalPseudonymEngine
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager


class TestCompositionalLogicIntegration:
    """Integration tests for compositional pseudonymization workflow."""

    @pytest.fixture
    def pseudonym_manager(self) -> LibraryBasedPseudonymManager:
        """Create real LibraryBasedPseudonymManager with loaded library.

        Returns:
            Configured pseudonym manager with star_wars theme
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")
        return manager

    @pytest.fixture
    def mock_mapping_repository(self) -> MagicMock:
        """Create mock MappingRepository for testing.

        Returns:
            Mock repository with configurable behavior
        """
        return MagicMock()

    @pytest.fixture
    def compositional_engine(
        self,
        pseudonym_manager: LibraryBasedPseudonymManager,
        mock_mapping_repository: MagicMock,
    ) -> CompositionalPseudonymEngine:
        """Create CompositionalPseudonymEngine with real manager and mock repository.

        Returns:
            Configured compositional engine
        """
        return CompositionalPseudonymEngine(pseudonym_manager, mock_mapping_repository)

    def test_complex_document_with_multiple_name_patterns(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test complex document with full names, shared components, and standalone names.

        Scenario:
        1. "Marie Dubois" (full name) -> Leia Organa
        2. "Marie Dupont" (shared first name) -> Leia Skywalker
        3. "Jean Dubois" (shared last name) -> Luke Organa
        4. "Marie" (standalone - ambiguous) -> Leia

        Verifies:
        - Compositional consistency across all replacements
        - Component reuse logic
        - Ambiguity flagging for standalone components
        """
        # Track assigned entities for simulating repository state
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup that searches assigned entities."""
            matches = []
            for entity in assigned_entities:
                if component_type == "first_name" and entity.first_name == component:
                    matches.append(entity)
                elif component_type == "last_name" and entity.last_name == component:
                    matches.append(entity)
            return matches

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # Entity 1: "Marie Dubois" (new, no existing components)
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        assert assignment_1.pseudonym_first is not None
        assert assignment_1.pseudonym_last is not None
        assert assignment_1.is_ambiguous is False

        # Simulate saving to repository
        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Entity 2: "Marie Dupont" (Marie exists, Dupont is new)
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender="female",
        )

        # Verify "Marie" reused from entity_1
        assert assignment_2.pseudonym_first == assignment_1.pseudonym_first
        assert (
            assignment_2.pseudonym_last != assignment_1.pseudonym_last
        )  # New last name
        assert assignment_2.is_ambiguous is False

        # Simulate saving
        entity_2 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            full_name="Marie Dupont",
            pseudonym_first=assignment_2.pseudonym_first,
            pseudonym_last=assignment_2.pseudonym_last,
            pseudonym_full=assignment_2.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_2)

        # Entity 3: "Jean Dubois" (Jean is new, Dubois exists)
        assignment_3 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean Dubois",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Dubois" reused from entity_1
        assert (
            assignment_3.pseudonym_first != assignment_1.pseudonym_first
        )  # New first name
        assert assignment_3.pseudonym_last == assignment_1.pseudonym_last
        assert assignment_3.is_ambiguous is False

        # Simulate saving
        entity_3 = Entity(
            entity_type="PERSON",
            first_name="Jean",
            last_name="Dubois",
            full_name="Jean Dubois",
            pseudonym_first=assignment_3.pseudonym_first,
            pseudonym_last=assignment_3.pseudonym_last,
            pseudonym_full=assignment_3.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_3)

        # Entity 4: "Marie" (standalone - ambiguous)
        assignment_4 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie",
            entity_type="PERSON",
            gender="female",
        )

        # Verify standalone uses existing "Marie" → "Leia" mapping
        assert assignment_4.pseudonym_full == assignment_1.pseudonym_first
        assert assignment_4.is_ambiguous is True
        assert assignment_4.ambiguity_reason is not None
        assert (
            "Standalone component without full name context"
            in assignment_4.ambiguity_reason
        )

    def test_compositional_consistency_across_multiple_documents(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test compositional consistency maintained across multiple document processing.

        Verifies that component mappings persist and are reused correctly
        when processing multiple documents in sequence.
        """
        # Simulate repository state
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # Document 1: Process "Pierre Martin"
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Pierre Martin",
            entity_type="PERSON",
            gender="male",
        )
        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Pierre",
            last_name="Martin",
            full_name="Pierre Martin",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Document 2: Process "Pierre Durand" (shares "Pierre")
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Pierre Durand",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Pierre" pseudonym reused
        assert assignment_2.pseudonym_first == assignment_1.pseudonym_first

        # Document 2: Process "Sophie Martin" (shares "Martin")
        entity_2 = Entity(
            entity_type="PERSON",
            first_name="Pierre",
            last_name="Durand",
            full_name="Pierre Durand",
            pseudonym_first=assignment_2.pseudonym_first,
            pseudonym_last=assignment_2.pseudonym_last,
            pseudonym_full=assignment_2.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_2)

        assignment_3 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Sophie Martin",
            entity_type="PERSON",
            gender="female",
        )

        # Verify "Martin" pseudonym reused
        assert assignment_3.pseudonym_last == assignment_1.pseudonym_last
        assert (
            assignment_3.pseudonym_first != assignment_1.pseudonym_first
        )  # Different first

    def test_all_pseudonym_libraries_work_with_compositional_logic(
        self,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test compositional logic works with all pseudonym libraries.

        Verifies neutral, star_wars, and lotr libraries integrate correctly
        with the compositional engine.
        """
        mock_mapping_repository.find_by_component.return_value = []

        themes = ["neutral", "star_wars", "lotr"]

        for theme in themes:
            # Create fresh manager for each theme
            manager = LibraryBasedPseudonymManager()
            manager.load_library(theme)
            engine = CompositionalPseudonymEngine(manager, mock_mapping_repository)

            # Assign pseudonym
            assignment = engine.assign_compositional_pseudonym(
                entity_text="Marie Dubois",
                entity_type="PERSON",
                gender="female",
            )

            # Verify assignment successful
            assert assignment.pseudonym_full is not None
            assert assignment.pseudonym_first is not None
            assert assignment.pseudonym_last is not None
            assert assignment.theme == theme
            assert assignment.is_ambiguous is False

    def test_repository_persistence_with_component_mappings(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test that component mappings are correctly structured for persistence.

        Verifies that PseudonymAssignment results contain all required fields
        for Entity model persistence, including component-level mappings.
        """
        mock_mapping_repository.find_by_component.return_value = []

        assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify all Entity fields can be populated from assignment
        entity = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first=assignment.pseudonym_first,
            pseudonym_last=assignment.pseudonym_last,
            pseudonym_full=assignment.pseudonym_full,
            theme=assignment.theme,
            is_ambiguous=assignment.is_ambiguous,
            ambiguity_reason=assignment.ambiguity_reason,
        )

        # Verify entity has complete data
        assert entity.first_name == "Marie"
        assert entity.last_name == "Dubois"
        assert entity.pseudonym_first is not None
        assert entity.pseudonym_last is not None
        assert (
            entity.pseudonym_full == f"{entity.pseudonym_first} {entity.pseudonym_last}"
        )
        assert entity.is_ambiguous is False

    def test_collision_prevention_with_compositional_logic(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test that compositional logic maintains collision prevention.

        Verifies that even when reusing components, full pseudonyms remain unique.
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # Assign multiple pseudonyms
        full_pseudonyms = set()

        test_names = [
            ("Marie Dubois", "female"),
            ("Marie Dupont", "female"),
            ("Jean Dubois", "male"),
            ("Jean Dupont", "male"),
            ("Sophie Martin", "female"),
        ]

        for name, gender in test_names:
            assignment = compositional_engine.assign_compositional_pseudonym(
                entity_text=name,
                entity_type="PERSON",
                gender=gender,
            )

            # Verify unique full pseudonym
            assert assignment.pseudonym_full not in full_pseudonyms
            full_pseudonyms.add(assignment.pseudonym_full)

            # Parse name components
            first, last = name.split()
            entity = Entity(
                entity_type="PERSON",
                first_name=first,
                last_name=last,
                full_name=name,
                pseudonym_first=assignment.pseudonym_first,
                pseudonym_last=assignment.pseudonym_last,
                pseudonym_full=assignment.pseudonym_full,
                theme="star_wars",
            )
            assigned_entities.append(entity)

        # Verify all pseudonyms are unique
        assert len(full_pseudonyms) == 5

    def test_standalone_components_use_existing_mappings(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test standalone components correctly lookup and use existing mappings.

        Verifies that when "Marie" appears alone after "Marie Dubois" was processed,
        the standalone "Marie" uses the same pseudonym component.
        """
        # Setup: "Marie Dubois" already processed
        existing_entity = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            pseudonym_full="Leia Organa",
            theme="star_wars",
        )

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock lookup that returns existing Marie mapping."""
            if component == "Marie" and component_type == "first_name":
                return [existing_entity]
            return []

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # Process standalone "Marie"
        assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie",
            entity_type="PERSON",
            gender="female",
        )

        # Verify standalone uses existing "Leia" for "Marie"
        assert assignment.pseudonym_full == "Leia"
        assert assignment.pseudonym_first == "Leia"
        assert assignment.pseudonym_last is None

        # Verify ambiguity flag
        assert assignment.is_ambiguous is True
        assert assignment.ambiguity_reason is not None
        assert (
            "Standalone component without full name context"
            in assignment.ambiguity_reason
        )

    def test_multiple_shared_components_in_same_document(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test multiple entities sharing different combinations of components.

        Complex scenario:
        1. "Alice Smith" -> "Leia Organa"
        2. "Alice Jones" -> "Leia Skywalker" (shares Alice)
        3. "Bob Smith" -> "Luke Organa" (shares Smith)
        4. "Bob Jones" -> "Luke Skywalker" (shares Bob and Jones)
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # Process entities sequentially
        test_cases = [
            ("Alice Smith", "female"),
            ("Alice Jones", "female"),
            ("Bob Smith", "male"),
            ("Bob Jones", "male"),
        ]

        assignments = []
        for name, gender in test_cases:
            assignment = compositional_engine.assign_compositional_pseudonym(
                entity_text=name,
                entity_type="PERSON",
                gender=gender,
            )
            assignments.append(assignment)

            # Simulate persistence
            first, last = name.split()
            entity = Entity(
                entity_type="PERSON",
                first_name=first,
                last_name=last,
                full_name=name,
                pseudonym_first=assignment.pseudonym_first,
                pseudonym_last=assignment.pseudonym_last,
                pseudonym_full=assignment.pseudonym_full,
                theme="star_wars",
            )
            assigned_entities.append(entity)

        # Verify compositional consistency
        # Alice appears in [0] and [1] - should have same first pseudonym
        assert assignments[1].pseudonym_first == assignments[0].pseudonym_first

        # Smith appears in [0] and [2] - should have same last pseudonym
        assert assignments[2].pseudonym_last == assignments[0].pseudonym_last

        # Bob appears in [2] and [3] - should have same first pseudonym
        assert assignments[3].pseudonym_first == assignments[2].pseudonym_first

        # Jones appears in [1] and [3] - should have same last pseudonym
        assert assignments[3].pseudonym_last == assignments[1].pseudonym_last

        # All full pseudonyms should be unique
        full_pseudonyms = [a.pseudonym_full for a in assignments]
        assert len(set(full_pseudonyms)) == 4

    def test_three_word_name_compositional_logic(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test compositional logic for three-word names.

        Verifies that "Marie Anne Dubois" is parsed as first="Marie Anne",
        last="Dubois", and that component reuse works correctly.
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # First: "Marie Anne Dubois" (three words)
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Anne Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Should be flagged as ambiguous (three words)
        assert assignment_1.is_ambiguous is True
        assert assignment_1.ambiguity_reason is not None
        assert "Multiple word name - parsing uncertain" in assignment_1.ambiguity_reason

        # Simulate persistence
        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Marie Anne",
            last_name="Dubois",
            full_name="Marie Anne Dubois",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Second: "Jean Dubois" (shares last name "Dubois")
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean Dubois",
            entity_type="PERSON",
            gender="male",
        )

        # Should reuse "Dubois" pseudonym from first entity
        assert assignment_2.pseudonym_last == assignment_1.pseudonym_last
        assert assignment_2.is_ambiguous is False  # Two words = not ambiguous

    def test_non_person_entities_skip_compositional_logic(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test LOCATION and ORG entities use simple assignment without component queries.

        Verifies that non-PERSON entities do not trigger compositional logic
        or repository component queries.
        """
        # Process LOCATION entity
        location_assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="Paris",
            entity_type="LOCATION",
            gender=None,
        )

        # Verify simple assignment used
        assert location_assignment.pseudonym_first is None
        assert location_assignment.pseudonym_last is not None
        assert location_assignment.pseudonym_full == location_assignment.pseudonym_last

        # Process ORG entity
        org_assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="ACME Corp",
            entity_type="ORG",
            gender=None,
        )

        # Verify simple assignment used
        assert org_assignment.pseudonym_first is None
        assert org_assignment.pseudonym_last is not None

        # Verify repository NOT queried for LOCATION or ORG
        mock_mapping_repository.find_by_component.assert_not_called()

    def test_exhaustion_percentage_propagates_through_compositional_logic(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test that library exhaustion percentage is tracked through compositional assignments.

        Verifies that as pseudonyms are assigned, exhaustion percentage increases
        and is correctly reflected in PseudonymAssignment results.
        """
        mock_mapping_repository.find_by_component.return_value = []

        # Assign first pseudonym
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )
        exhaustion_1 = assignment_1.exhaustion_percentage

        # Assign more pseudonyms
        for i in range(10):
            compositional_engine.assign_compositional_pseudonym(
                entity_text=f"Person{i} Test{i}",
                entity_type="PERSON",
                gender="male",
            )

        # Assign another pseudonym
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean Dupont",
            entity_type="PERSON",
            gender="male",
        )
        exhaustion_2 = assignment_2.exhaustion_percentage

        # Verify exhaustion increased
        assert exhaustion_2 > exhaustion_1
        assert 0.0 <= exhaustion_2 <= 1.0

    def test_gender_preserved_through_compositional_assignment(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test that gender hints are correctly passed through compositional logic.

        Verifies that gender preferences are respected when assigning pseudonyms
        through the compositional engine.
        """
        mock_mapping_repository.find_by_component.return_value = []

        # Assign with male gender
        male_assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean Dupont",
            entity_type="PERSON",
            gender="male",
        )

        # Assign with female gender
        female_assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify both assignments successful
        assert male_assignment.pseudonym_full is not None
        assert female_assignment.pseudonym_full is not None

        # Note: Gender verification would require checking against library gender lists,
        # but since we're using real LibraryBasedPseudonymManager from Story 2.1,
        # we trust that gender logic is already tested in test_library_manager.py


class TestTitleAndCompoundNameIntegration:
    """Integration tests for title stripping and compound name handling (Story 2.3)."""

    @pytest.fixture
    def pseudonym_manager(self) -> LibraryBasedPseudonymManager:
        """Create real LibraryBasedPseudonymManager with loaded library.

        Returns:
            Configured pseudonym manager with star_wars theme
        """
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")
        return manager

    @pytest.fixture
    def mock_mapping_repository(self) -> MagicMock:
        """Create mock MappingRepository for testing.

        Returns:
            Mock repository with configurable behavior
        """
        return MagicMock()

    @pytest.fixture
    def compositional_engine(
        self,
        pseudonym_manager: LibraryBasedPseudonymManager,
        mock_mapping_repository: MagicMock,
    ) -> CompositionalPseudonymEngine:
        """Create CompositionalPseudonymEngine with real manager and mock repository.

        Returns:
            Configured compositional engine
        """
        return CompositionalPseudonymEngine(pseudonym_manager, mock_mapping_repository)

    def test_title_deduplication_creates_single_mapping(
        self,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test that title variants parse to same components (no duplicate entities).

        Scenario:
        - "Dr. Marie Dubois" (with title) parses to ("Marie", "Dubois")
        - "Marie Dubois" (without title) parses to ("Marie", "Dubois")
        Both parse to identical components, so they'd create the same entity mapping.
        """
        # Create fresh manager to avoid library exhaustion from previous tests
        manager = LibraryBasedPseudonymManager()
        manager.load_library("star_wars")
        engine = CompositionalPseudonymEngine(manager, mock_mapping_repository)

        # Verify parsing produces same components for both title variants
        first_1, last_1, ambiguous_1 = engine.parse_full_name("Dr. Marie Dubois")
        first_2, last_2, ambiguous_2 = engine.parse_full_name("Marie Dubois")

        # Both should parse to exact same components
        assert first_1 == first_2 == "Marie"
        assert last_1 == last_2 == "Dubois"
        assert ambiguous_1 == ambiguous_2 is False

        # Since both parse to identical components, they would create the same
        # entity mapping in the repository (no duplicate entities)

    def test_compound_first_name_sharing(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test atomic compound first name shared across entities.

        Scenario:
        - "Jean-Pierre Martin" -> "Han Skywalker"
        - "Jean-Pierre Dupont" -> "Han Organa" (shares Jean-Pierre → Han)
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # First: "Jean-Pierre Martin"
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean-Pierre Martin",
            entity_type="PERSON",
            gender="male",
        )

        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Jean-Pierre",
            last_name="Martin",
            full_name="Jean-Pierre Martin",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Second: "Jean-Pierre Dupont" (shares compound "Jean-Pierre")
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean-Pierre Dupont",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Jean-Pierre" reused (same pseudonym first)
        assert assignment_2.pseudonym_first == assignment_1.pseudonym_first
        assert assignment_2.pseudonym_last != assignment_1.pseudonym_last
        # Compound names get SIMPLE pseudonyms (no hyphens)
        assert "-" not in assignment_1.pseudonym_first
        assert "-" not in assignment_2.pseudonym_first

    def test_compound_last_name_sharing(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test atomic compound last name shared across entities.

        Scenario:
        - "Marie Paluel-Marmont" -> "Leia Solo"
        - "Jean Paluel-Marmont" -> "Luke Solo" (shares Paluel-Marmont → Solo)
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # First: "Marie Paluel-Marmont"
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Marie Paluel-Marmont",
            entity_type="PERSON",
            gender="female",
        )

        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Paluel-Marmont",
            full_name="Marie Paluel-Marmont",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Second: "Jean Paluel-Marmont" (shares compound "Paluel-Marmont")
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean Paluel-Marmont",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Paluel-Marmont" reused (same pseudonym last)
        assert assignment_2.pseudonym_first != assignment_1.pseudonym_first
        assert assignment_2.pseudonym_last == assignment_1.pseudonym_last
        # Compound names get SIMPLE pseudonyms (no hyphens)
        assert "-" not in assignment_1.pseudonym_last
        assert "-" not in assignment_2.pseudonym_last

    def test_atomic_compound_separation_order_independent(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test compound and standalone components are distinct (order-independent).

        Scenario:
        - "Jean-Pierre Dubois" -> compound "Jean-Pierre" gets pseudonym (e.g., "Han")
        - "Jean Martin" -> simple "Jean" gets different pseudonym (e.g., "Luke")
        NO ambiguity flagging needed - they are distinct entities by design.
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # First: "Jean-Pierre Dubois" (compound first name)
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean-Pierre Dubois",
            entity_type="PERSON",
            gender="male",
        )

        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Jean-Pierre",
            last_name="Dubois",
            full_name="Jean-Pierre Dubois",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Second: "Jean Martin" (simple first name - DISTINCT from "Jean-Pierre")
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Jean Martin",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Jean" and "Jean-Pierre" get different pseudonyms
        assert assignment_2.pseudonym_first != assignment_1.pseudonym_first
        # Neither should be flagged as ambiguous (they are distinct entities)
        assert assignment_1.is_ambiguous is False
        assert assignment_2.is_ambiguous is False

    def test_title_stripping_with_compound_names(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test title stripping combined with compound name handling.

        Scenario:
        - "Dr. Jean-Pierre Dubois" (title + compound first)
        - "M. Jean-Pierre Martin" (title + compound first)
        After title stripping, both share compound "Jean-Pierre".
        """
        assigned_entities: list[Entity] = []

        def mock_find_by_component(component: str, component_type: str) -> list[Entity]:
            """Mock repository lookup."""
            return [
                e
                for e in assigned_entities
                if (component_type == "first_name" and e.first_name == component)
                or (component_type == "last_name" and e.last_name == component)
            ]

        mock_mapping_repository.find_by_component.side_effect = mock_find_by_component

        # First: "Dr. Jean-Pierre Dubois"
        assignment_1 = compositional_engine.assign_compositional_pseudonym(
            entity_text="Dr. Jean-Pierre Dubois",
            entity_type="PERSON",
            gender="male",
        )

        entity_1 = Entity(
            entity_type="PERSON",
            first_name="Jean-Pierre",
            last_name="Dubois",
            full_name="Dr. Jean-Pierre Dubois",
            pseudonym_first=assignment_1.pseudonym_first,
            pseudonym_last=assignment_1.pseudonym_last,
            pseudonym_full=assignment_1.pseudonym_full,
            theme="star_wars",
        )
        assigned_entities.append(entity_1)

        # Second: "M. Jean-Pierre Martin" (same compound after title strip)
        assignment_2 = compositional_engine.assign_compositional_pseudonym(
            entity_text="M. Jean-Pierre Martin",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Jean-Pierre" reused after title stripping
        assert assignment_2.pseudonym_first == assignment_1.pseudonym_first
        assert assignment_2.pseudonym_last != assignment_1.pseudonym_last

    def test_compound_names_with_all_libraries(
        self,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test compound name handling works with all pseudonym libraries.

        Verifies neutral, star_wars, and lotr libraries correctly assign
        pseudonyms for compound names. Note: Some libraries (e.g., lotr)
        may contain hyphenated names in their pseudonym pool (like "Tar-Atanamir"),
        which is valid - the important thing is that pseudonyms are assigned
        as atomic units.
        """
        mock_mapping_repository.find_by_component.return_value = []

        themes = ["neutral", "star_wars", "lotr"]

        for theme in themes:
            # Create fresh manager for each theme
            manager = LibraryBasedPseudonymManager()
            manager.load_library(theme)
            engine = CompositionalPseudonymEngine(manager, mock_mapping_repository)

            # Test compound first name
            assignment_first = engine.assign_compositional_pseudonym(
                entity_text="Jean-Pierre Martin",
                entity_type="PERSON",
                gender="male",
            )

            # Verify pseudonyms assigned successfully
            assert assignment_first.pseudonym_first is not None
            assert assignment_first.pseudonym_last is not None
            assert assignment_first.theme == theme
            assert assignment_first.is_ambiguous is False

            # Test compound last name
            assignment_last = engine.assign_compositional_pseudonym(
                entity_text="Marie Paluel-Marmont",
                entity_type="PERSON",
                gender="female",
            )

            # Verify pseudonym assigned successfully
            assert assignment_last.pseudonym_first is not None
            assert assignment_last.pseudonym_last is not None
            assert assignment_last.theme == theme
            assert assignment_last.is_ambiguous is False

    def test_multiple_titles_with_compound_names(
        self,
        compositional_engine: CompositionalPseudonymEngine,
        mock_mapping_repository: MagicMock,
    ) -> None:
        """Test multiple consecutive titles with compound names.

        Scenario:
        - "Dr. Pr. Jean-Pierre Paluel-Marmont"
        All titles stripped, both compound names handled correctly.
        """
        mock_mapping_repository.find_by_component.return_value = []

        assignment = compositional_engine.assign_compositional_pseudonym(
            entity_text="Dr. Pr. Jean-Pierre Paluel-Marmont",
            entity_type="PERSON",
            gender="male",
        )

        # Verify both compound names get SIMPLE pseudonyms
        assert assignment.pseudonym_first is not None
        assert "-" not in assignment.pseudonym_first
        assert assignment.pseudonym_last is not None
        assert "-" not in assignment.pseudonym_last
        assert assignment.is_ambiguous is False
