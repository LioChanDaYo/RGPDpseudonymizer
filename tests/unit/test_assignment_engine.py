"""Unit tests for compositional pseudonym assignment engine.

Tests cover:
- Full name parsing (two-word, single-word, multi-word)
- Compositional pseudonym assignment
- Component reuse logic (shared first/last names)
- Standalone component detection and ambiguity flagging
- Integration with MappingRepository for component queries
- Collision prevention and unique pseudonym enforcement

Target: ≥90% code coverage for assignment_engine.py
"""

from __future__ import annotations

from unittest.mock import Mock

from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
    PseudonymAssignment,
)


class TestParseFullName:
    """Test suite for full name parsing functionality."""

    def test_parse_full_name_two_words(self) -> None:
        """Test parsing two-word PERSON entity into first and last name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Marie Dubois")

        assert first == "Marie"
        assert last == "Dubois"
        assert ambiguous is False

    def test_parse_full_name_single_word(self) -> None:
        """Test parsing single-word entity returns first name only and ambiguous flag."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Marie")

        assert first == "Marie"
        assert last is None
        assert ambiguous is True

    def test_parse_full_name_three_words(self) -> None:
        """Test parsing three-word entity treats first two as first name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Marie Anne Dubois")

        assert first == "Marie Anne"
        assert last == "Dubois"
        assert ambiguous is True

    def test_parse_full_name_four_words(self) -> None:
        """Test parsing four-word entity combines all but last as first name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Jean Marie Pierre Dupont")

        assert first == "Jean Marie Pierre"
        assert last == "Dupont"
        assert ambiguous is True

    def test_parse_full_name_empty_string(self) -> None:
        """Test parsing empty string returns None and ambiguous flag."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("")

        assert first is None
        assert last is None
        assert ambiguous is True

    def test_parse_full_name_whitespace_only(self) -> None:
        """Test parsing whitespace-only string returns None and ambiguous flag."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("   ")

        assert first is None
        assert last is None
        assert ambiguous is True


class TestParseFullNameWithTitles:
    """Test suite for full name parsing with French titles (Story 2.3)."""

    def test_parse_full_name_with_title_dr(self) -> None:
        """Test parsing name with Dr. title strips title before parsing."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Dr. Marie Dubois")

        assert first == "Marie"
        assert last == "Dubois"
        assert ambiguous is False

    def test_parse_full_name_with_title_m(self) -> None:
        """Test parsing name with M. title strips title before parsing."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("M. Jean Martin")

        assert first == "Jean"
        assert last == "Martin"
        assert ambiguous is False

    def test_parse_full_name_with_title_mme(self) -> None:
        """Test parsing name with Mme. title strips title before parsing."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Mme. Sophie Dubois")

        assert first == "Sophie"
        assert last == "Dubois"
        assert ambiguous is False

    def test_parse_full_name_with_multiple_titles(self) -> None:
        """Test parsing name with multiple titles strips all titles."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Dr. Pr. Marie Dubois")

        assert first == "Marie"
        assert last == "Dubois"
        assert ambiguous is False

    def test_parse_full_name_with_title_uppercase(self) -> None:
        """Test parsing name with uppercase title (case-insensitive)."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("DR MARIE DUBOIS")

        assert first == "MARIE"
        assert last == "DUBOIS"
        assert ambiguous is False

    def test_parse_full_name_with_title_no_period(self) -> None:
        """Test parsing name with title without period."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Dr Marie Dubois")

        assert first == "Marie"
        assert last == "Dubois"
        assert ambiguous is False


class TestParseFullNameWithCompounds:
    """Test suite for compound name parsing (Story 2.3)."""

    def test_parse_full_name_compound_first_name(self) -> None:
        """Test parsing hyphenated compound first name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Jean-Pierre Martin")

        assert first == "Jean-Pierre"
        assert last == "Martin"
        assert ambiguous is False

    def test_parse_full_name_compound_last_name(self) -> None:
        """Test parsing hyphenated compound last name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Marie Paluel-Marmont")

        assert first == "Marie"
        assert last == "Paluel-Marmont"
        assert ambiguous is False

    def test_parse_full_name_compound_both(self) -> None:
        """Test parsing both compound first and last names."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Jean-Pierre Paluel-Marmont")

        assert first == "Jean-Pierre"
        assert last == "Paluel-Marmont"
        assert ambiguous is False

    def test_parse_full_name_compound_first_only(self) -> None:
        """Test parsing compound first name without last name (ambiguous)."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Jean-Pierre")

        assert first == "Jean-Pierre"
        assert last is None
        assert ambiguous is True

    def test_parse_full_name_multi_hyphen_first(self) -> None:
        """Test parsing multi-hyphen compound first name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Jean-Pierre-Paul Martin")

        assert first == "Jean-Pierre-Paul"
        assert last == "Martin"
        assert ambiguous is False

    def test_parse_full_name_multi_hyphen_last(self) -> None:
        """Test parsing multi-hyphen compound last name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Marie Saint-Exupéry-Dubois")

        assert first == "Marie"
        assert last == "Saint-Exupéry-Dubois"
        assert ambiguous is False

    def test_parse_full_name_title_and_compound(self) -> None:
        """Test parsing name with title and compound first name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("Dr. Jean-Pierre Dubois")

        assert first == "Jean-Pierre"
        assert last == "Dubois"
        assert ambiguous is False

    def test_parse_full_name_multiple_titles_and_compound(self) -> None:
        """Test parsing name with multiple titles and both compound names."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name(
            "Dr. Pr. Jean-Pierre Paluel-Marmont"
        )

        assert first == "Jean-Pierre"
        assert last == "Paluel-Marmont"
        assert ambiguous is False

    def test_parse_full_name_title_and_compound_first_only(self) -> None:
        """Test parsing title with compound first name only (ambiguous)."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        first, last, ambiguous = engine.parse_full_name("M. Jean-Pierre")

        assert first == "Jean-Pierre"
        assert last is None
        assert ambiguous is True


class TestFindStandaloneComponents:
    """Test suite for standalone component lookup functionality."""

    def test_find_standalone_component_first_name_found(self) -> None:
        """Test finding existing first name component mapping."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock existing entity with first name mapping
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
        mock_repo.find_by_component.return_value = [existing_entity]

        result = engine.find_standalone_components("Marie", "first_name")

        assert result == "Leia"
        mock_repo.find_by_component.assert_called_once_with("Marie", "first_name")

    def test_find_standalone_component_last_name_found(self) -> None:
        """Test finding existing last name component mapping."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock existing entity with last name mapping
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
        mock_repo.find_by_component.return_value = [existing_entity]

        result = engine.find_standalone_components("Dubois", "last_name")

        assert result == "Organa"
        mock_repo.find_by_component.assert_called_once_with("Dubois", "last_name")

    def test_find_standalone_component_not_found(self) -> None:
        """Test component lookup returns None when no mapping exists."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        mock_repo.find_by_component.return_value = []

        result = engine.find_standalone_components("Jean", "first_name")

        assert result is None
        mock_repo.find_by_component.assert_called_once_with("Jean", "first_name")

    def test_find_standalone_component_multiple_matches_uses_first(self) -> None:
        """Test that multiple component matches use first match for consistency."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Multiple entities share "Marie"
        entity1 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            pseudonym_full="Leia Organa",
            theme="star_wars",
        )
        entity2 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            full_name="Marie Dupont",
            pseudonym_first="Leia",  # Same pseudonym for shared component
            pseudonym_last="Skywalker",
            pseudonym_full="Leia Skywalker",
            theme="star_wars",
        )
        mock_repo.find_by_component.return_value = [entity1, entity2]

        result = engine.find_standalone_components("Marie", "first_name")

        # Should use first match
        assert result == "Leia"


class TestCompositionalAssignment:
    """Test suite for compositional pseudonym assignment."""

    def test_assign_compositional_pseudonym_new_full_name(self) -> None:
        """Test assigning pseudonym for new full name with no existing components."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # No existing components
        mock_repo.find_by_component.return_value = []

        # Mock pseudonym manager to return assignment
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify assignment
        assert assignment.pseudonym_full == "Leia Organa"
        assert assignment.pseudonym_first == "Leia"
        assert assignment.pseudonym_last == "Organa"
        assert assignment.is_ambiguous is False

        # Verify repository was queried for components
        assert mock_repo.find_by_component.call_count == 2

        # Verify manager was called with no existing components
        mock_manager.assign_pseudonym.assert_called_once()
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["existing_first"] is None
        assert call_kwargs["existing_last"] is None

    def test_assign_compositional_pseudonym_reuses_first_name(self) -> None:
        """Test compositional logic reuses existing first name mapping."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock existing first name mapping
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

        # First query (first_name) returns existing, second (last_name) returns empty
        mock_repo.find_by_component.side_effect = [
            [existing_entity],  # "Marie" found
            [],  # "Dupont" not found
        ]

        # Mock pseudonym manager to return assignment with reused first name
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Skywalker",
            pseudonym_first="Leia",
            pseudonym_last="Skywalker",
            theme="star_wars",
            exhaustion_percentage=0.02,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender="female",
        )

        # Verify assignment reuses "Leia" for "Marie"
        assert assignment.pseudonym_first == "Leia"
        assert assignment.pseudonym_last == "Skywalker"
        assert assignment.pseudonym_full == "Leia Skywalker"

        # Verify manager was called with existing_first="Leia"
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["existing_first"] == "Leia"
        assert call_kwargs["existing_last"] is None

    def test_assign_compositional_pseudonym_reuses_last_name(self) -> None:
        """Test compositional logic reuses existing last name mapping."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock existing last name mapping
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

        # First query (first_name) returns empty, second (last_name) returns existing
        mock_repo.find_by_component.side_effect = [
            [],  # "Jean" not found
            [existing_entity],  # "Dubois" found
        ]

        # Mock pseudonym manager to return assignment with reused last name
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Luke Organa",
            pseudonym_first="Luke",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.02,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Jean Dubois",
            entity_type="PERSON",
            gender="male",
        )

        # Verify assignment reuses "Organa" for "Dubois"
        assert assignment.pseudonym_first == "Luke"
        assert assignment.pseudonym_last == "Organa"
        assert assignment.pseudonym_full == "Luke Organa"

        # Verify manager was called with existing_last="Organa"
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["existing_first"] is None
        assert call_kwargs["existing_last"] == "Organa"

    def test_assign_compositional_pseudonym_reuses_both_components(self) -> None:
        """Test compositional logic reuses both first and last name mappings."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock existing components
        entity_marie = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            pseudonym_full="Leia Organa",
            theme="star_wars",
        )
        entity_jean = Entity(
            entity_type="PERSON",
            first_name="Jean",
            last_name="Dupont",
            full_name="Jean Dupont",
            pseudonym_first="Luke",
            pseudonym_last="Skywalker",
            pseudonym_full="Luke Skywalker",
            theme="star_wars",
        )

        # Both components found in existing mappings
        mock_repo.find_by_component.side_effect = [
            [entity_marie],  # "Marie" found
            [entity_jean],  # "Dupont" found (different entity)
        ]

        # Mock pseudonym manager to return assignment with both reused components
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Skywalker",
            pseudonym_first="Leia",
            pseudonym_last="Skywalker",
            theme="star_wars",
            exhaustion_percentage=0.03,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender="female",
        )

        # Verify both components reused
        assert assignment.pseudonym_first == "Leia"
        assert assignment.pseudonym_last == "Skywalker"

        # Verify manager was called with both existing components
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["existing_first"] == "Leia"
        assert call_kwargs["existing_last"] == "Skywalker"


class TestStandaloneComponentHandling:
    """Test suite for standalone component replacement and ambiguity flagging."""

    def test_assign_compositional_pseudonym_standalone_component_existing(
        self,
    ) -> None:
        """Test standalone component with existing mapping flagged as ambiguous."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        mock_manager.theme = "star_wars"
        mock_manager.check_exhaustion.return_value = 0.02
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock existing first name mapping
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
        mock_repo.find_by_component.return_value = [existing_entity]

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie",
            entity_type="PERSON",
            gender="female",
        )

        # Verify standalone component uses existing mapping
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

    def test_assign_compositional_pseudonym_standalone_component_new(self) -> None:
        """Test standalone component without existing mapping gets new pseudonym."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # No existing mapping for "Jean"
        mock_repo.find_by_component.return_value = []

        # Mock pseudonym manager to assign new pseudonym
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Luke Skywalker",
            pseudonym_first="Luke",
            pseudonym_last="Skywalker",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Jean",
            entity_type="PERSON",
            gender="male",
        )

        # Verify new pseudonym assigned
        assert assignment.pseudonym_full == "Luke Skywalker"

        # Verify ambiguity flag set
        assert assignment.is_ambiguous is True
        assert assignment.ambiguity_reason is not None
        assert (
            "Standalone component without full name context"
            in assignment.ambiguity_reason
        )


class TestNonPersonEntities:
    """Test suite for non-PERSON entity handling."""

    def test_assign_compositional_pseudonym_location(self) -> None:
        """Test LOCATION entity uses simple assignment without compositional logic."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock pseudonym manager assignment
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Tatooine",
            pseudonym_first=None,
            pseudonym_last="Tatooine",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Paris",
            entity_type="LOCATION",
            gender=None,
        )

        # Verify simple assignment used
        assert assignment.pseudonym_full == "Tatooine"
        assert assignment.pseudonym_first is None

        # Verify repository was NOT queried (no compositional logic)
        mock_repo.find_by_component.assert_not_called()

    def test_assign_compositional_pseudonym_org(self) -> None:
        """Test ORG entity uses simple assignment without compositional logic."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Mock pseudonym manager assignment
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Empire",
            pseudonym_first=None,
            pseudonym_last="Empire",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="ACME Corp",
            entity_type="ORG",
            gender=None,
        )

        # Verify simple assignment used
        assert assignment.pseudonym_full == "Empire"
        assert assignment.pseudonym_first is None

        # Verify repository was NOT queried
        mock_repo.find_by_component.assert_not_called()


class TestSharedComponentScenarios:
    """Test suite for shared component handling (FR5)."""

    def test_shared_first_name_different_last_names(self) -> None:
        """Test scenario: Marie Dubois → Leia Organa, Marie Dupont → Leia Skywalker."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # First entity: "Marie Dubois" (no existing components)
        mock_repo.find_by_component.side_effect = [[], []]  # Both components new
        mock_assignment_1 = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment_1

        assignment_1 = engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        assert assignment_1.pseudonym_full == "Leia Organa"

        # Reset mock for second entity
        mock_manager.reset_mock()
        mock_repo.reset_mock()

        # Second entity: "Marie Dupont" (Marie exists, Dupont is new)
        entity_marie = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            pseudonym_full="Leia Organa",
            theme="star_wars",
        )
        mock_repo.find_by_component.side_effect = [
            [entity_marie],  # "Marie" found
            [],  # "Dupont" not found
        ]
        mock_assignment_2 = PseudonymAssignment(
            pseudonym_full="Leia Skywalker",
            pseudonym_first="Leia",
            pseudonym_last="Skywalker",
            theme="star_wars",
            exhaustion_percentage=0.02,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment_2

        assignment_2 = engine.assign_compositional_pseudonym(
            entity_text="Marie Dupont",
            entity_type="PERSON",
            gender="female",
        )

        # Verify "Leia" reused for "Marie"
        assert assignment_2.pseudonym_first == "Leia"
        assert assignment_2.pseudonym_last == "Skywalker"

        # Verify manager called with existing_first="Leia"
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["existing_first"] == "Leia"

    def test_shared_last_name_different_first_names(self) -> None:
        """Test scenario: Marie Dubois → Leia Organa, Jean Dubois → Luke Organa."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # First entity: "Marie Dubois" (already exists from previous test)
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

        # Second entity: "Jean Dubois" (Jean is new, Dubois exists)
        mock_repo.find_by_component.side_effect = [
            [],  # "Jean" not found
            [existing_entity],  # "Dubois" found
        ]
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Luke Organa",
            pseudonym_first="Luke",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.02,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Jean Dubois",
            entity_type="PERSON",
            gender="male",
        )

        # Verify "Organa" reused for "Dubois"
        assert assignment.pseudonym_first == "Luke"
        assert assignment.pseudonym_last == "Organa"

        # Verify manager called with existing_last="Organa"
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["existing_first"] is None
        assert call_kwargs["existing_last"] == "Organa"


class TestAmbiguityDetection:
    """Test suite for ambiguity detection and flagging."""

    def test_assign_compositional_pseudonym_flags_three_word_name(self) -> None:
        """Test three-word name flagged as ambiguous due to parsing uncertainty."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # No existing components
        mock_repo.find_by_component.return_value = []

        # Mock pseudonym manager assignment
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Amidala Organa",
            pseudonym_first="Leia Amidala",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie Anne Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify ambiguity flag set
        assert assignment.is_ambiguous is True
        assert assignment.ambiguity_reason is not None
        assert "Multiple word name - parsing uncertain" in assignment.ambiguity_reason

    def test_assign_compositional_pseudonym_two_word_not_ambiguous(self) -> None:
        """Test two-word standard name not flagged as ambiguous."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # No existing components
        mock_repo.find_by_component.return_value = []

        # Mock pseudonym manager assignment
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify NOT flagged as ambiguous
        assert assignment.is_ambiguous is False


class TestComponentQueryPatterns:
    """Test suite for MappingRepository component query patterns."""

    def test_find_by_component_called_for_first_and_last(self) -> None:
        """Test that find_by_component is called for both first and last name."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # No existing components
        mock_repo.find_by_component.return_value = []

        # Mock pseudonym manager
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify find_by_component called twice (first_name, last_name)
        assert mock_repo.find_by_component.call_count == 2
        calls = mock_repo.find_by_component.call_args_list
        assert calls[0][0] == ("Marie", "first_name")
        assert calls[1][0] == ("Dubois", "last_name")

    def test_find_by_component_uses_first_match_for_consistency(self) -> None:
        """Test that first match is used when multiple entities share component."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        # Multiple entities share "Marie" - all should use same pseudonym
        entity1 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dubois",
            full_name="Marie Dubois",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            pseudonym_full="Leia Organa",
            theme="star_wars",
        )
        entity2 = Entity(
            entity_type="PERSON",
            first_name="Marie",
            last_name="Dupont",
            full_name="Marie Dupont",
            pseudonym_first="Leia",
            pseudonym_last="Skywalker",
            pseudonym_full="Leia Skywalker",
            theme="star_wars",
        )

        # Return multiple matches
        mock_repo.find_by_component.return_value = [entity1, entity2]

        result = engine.find_standalone_components("Marie", "first_name")

        # Should use FIRST match to maintain consistency
        assert result == "Leia"


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_assign_compositional_pseudonym_with_none_gender(self) -> None:
        """Test assignment with gender=None uses all available names."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        mock_repo.find_by_component.return_value = []
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.01,
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Jordan Taylor",
            entity_type="PERSON",
            gender=None,
        )

        # Verify assignment completed
        assert assignment.pseudonym_full == "Leia Organa"

        # Verify gender=None passed to manager
        call_kwargs = mock_manager.assign_pseudonym.call_args.kwargs
        assert call_kwargs["gender"] is None

    def test_assign_compositional_pseudonym_preserves_exhaustion_percentage(
        self,
    ) -> None:
        """Test that exhaustion percentage from manager is preserved in assignment."""
        mock_manager = Mock()
        mock_manager.get_component_mapping.return_value = None
        mock_repo = Mock()
        engine = CompositionalPseudonymEngine(mock_manager, mock_repo)

        mock_repo.find_by_component.return_value = []
        mock_assignment = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="star_wars",
            exhaustion_percentage=0.73,  # 73% exhausted
        )
        mock_manager.assign_pseudonym.return_value = mock_assignment

        assignment = engine.assign_compositional_pseudonym(
            entity_text="Marie Dubois",
            entity_type="PERSON",
            gender="female",
        )

        # Verify exhaustion percentage preserved
        assert assignment.exhaustion_percentage == 0.73
