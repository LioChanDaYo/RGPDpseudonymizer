"""Pseudonym assignment engine interface and stub implementation."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdpr_pseudonymizer.data.repositories.mapping_repository import (
        MappingRepository,
    )

# Configure structured logging (no sensitive data)
logger = logging.getLogger(__name__)

# French title pattern for preprocessing
# Matches: Dr./Dr, Docteur, Pr./Pr, Prof./Prof, Professeur, M./M, Mme./Mme, Mlle./Mlle, Madame, Monsieur, Mademoiselle
# Also matches: Maître (attorney title), Me./Me (abbreviated attorney title)
# Case-insensitive, with or without periods
# (?!\w) ensures title is not followed by a word character (prevents matching "Dr" in "Drapeau")
# \s* consumes optional trailing whitespace
FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|Madame|Monsieur|Mademoiselle|Maître|Dr\.?|Pr\.?|Prof\.?|M\.?|Mme\.?|Mlle\.?|Me\.?)(?!\w)\s*"

# French preposition pattern for location preprocessing
# Matches common French prepositions that precede location names: à, au, aux, en, de, du, des, d', l'
# Handles contractions and elisions
# ^[\s]* matches optional leading whitespace
# \s* consumes trailing whitespace after preposition
FRENCH_PREPOSITION_PATTERN = r"^[\s]*(?:à|au|aux|en|de|du|des|d'|l'|la|le|les)\s+"


@dataclass
class PseudonymAssignment:
    """Result of pseudonym assignment operation.

    Attributes:
        pseudonym_full: Complete pseudonym string
        pseudonym_first: First name component (PERSON only)
        pseudonym_last: Last name component (PERSON only)
        theme: Library used for assignment (neutral/star_wars/lotr)
        exhaustion_percentage: Library usage percentage (0.0-1.0)
        is_ambiguous: Whether entity is flagged as ambiguous
        ambiguity_reason: Reason for ambiguity flag (if any)
    """

    pseudonym_full: str
    pseudonym_first: str | None
    pseudonym_last: str | None
    theme: str
    exhaustion_percentage: float
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class PseudonymManager(ABC):
    """Abstract interface for pseudonym assignment.

    Implementations must handle compositional logic (reusing first/last names)
    and library exhaustion tracking.
    """

    @abstractmethod
    def load_library(self, theme: str) -> None:
        """Load pseudonym library from JSON file.

        Args:
            theme: Library theme name (neutral, star_wars, lotr)

        Raises:
            FileNotFoundError: If library file not found
            ValueError: If library format is invalid
        """
        pass

    @abstractmethod
    def assign_pseudonym(
        self,
        entity_type: str,
        first_name: str | None = None,
        last_name: str | None = None,
        gender: str | None = None,
        existing_first: str | None = None,
        existing_last: str | None = None,
    ) -> PseudonymAssignment:
        """Assign pseudonym using compositional logic.

        For PERSON entities with split names, this method will attempt to reuse
        existing pseudonym components to maintain consistency.

        Args:
            entity_type: Entity type (PERSON, LOCATION, ORG)
            first_name: First name component (PERSON only)
            last_name: Last name component (PERSON only)
            gender: Gender hint for name selection (male/female/neutral/unknown)
            existing_first: Existing first name pseudonym to reuse
            existing_last: Existing last name pseudonym to reuse

        Returns:
            PseudonymAssignment with selected pseudonym and metadata

        Raises:
            ValueError: If entity_type is invalid
            RuntimeError: If library is exhausted
        """
        pass

    @abstractmethod
    def check_exhaustion(self) -> float:
        """Get library exhaustion percentage.

        Returns:
            Float between 0.0 (unused) and 1.0 (fully exhausted)
        """
        pass


class SimplePseudonymManager(PseudonymManager):
    """Stub implementation of PseudonymManager interface.

    This is a minimal placeholder. Full implementation will be completed
    in Epic 2 with proper library loading, compositional logic, and
    exhaustion tracking.
    """

    def __init__(self) -> None:
        """Initialize pseudonym manager with empty state."""
        self._theme: str | None = None

    def load_library(self, theme: str) -> None:
        """Load library (stub implementation).

        Args:
            theme: Library theme name
        """
        # Stub: Full implementation in Epic 2
        self._theme = theme

    def assign_pseudonym(
        self,
        entity_type: str,
        first_name: str | None = None,
        last_name: str | None = None,
        gender: str | None = None,
        existing_first: str | None = None,
        existing_last: str | None = None,
    ) -> PseudonymAssignment:
        """Assign pseudonym (stub implementation).

        Args:
            entity_type: Entity type
            first_name: First name
            last_name: Last name
            gender: Gender hint
            existing_first: Existing first pseudonym
            existing_last: Existing last pseudonym

        Returns:
            Stub pseudonym assignment
        """
        # Stub: Full implementation in Epic 2
        return PseudonymAssignment(
            pseudonym_full="PLACEHOLDER",
            pseudonym_first="PLACEHOLDER_FIRST" if entity_type == "PERSON" else None,
            pseudonym_last="PLACEHOLDER_LAST" if entity_type == "PERSON" else None,
            theme=self._theme or "neutral",
            exhaustion_percentage=0.0,
        )

    def check_exhaustion(self) -> float:
        """Get exhaustion percentage (stub implementation).

        Returns:
            0.0 (stub)
        """
        # Stub: Full implementation in Epic 2
        return 0.0


class CompositionalPseudonymEngine:
    """Assigns pseudonyms using compositional strict matching logic.

    This engine implements the compositional pseudonymization logic where:
    - Full names are parsed into first and last name components
    - Existing component mappings are reused for consistency
    - Standalone components are flagged as potentially ambiguous
    - Shared components maintain consistent pseudonym mapping

    Example:
        "Marie Dubois" -> "Leia Organa"
        "Marie Dupont" -> "Leia Skywalker" (reuses "Leia" for "Marie")
        "Marie" (standalone) -> "Leia" (flagged as ambiguous)

    Attributes:
        pseudonym_manager: LibraryBasedPseudonymManager for pseudonym selection
        mapping_repository: MappingRepository for component query/persistence
    """

    def __init__(
        self,
        pseudonym_manager: PseudonymManager,
        mapping_repository: MappingRepository,
    ):
        """Initialize compositional pseudonym engine.

        Args:
            pseudonym_manager: Pseudonym manager for library-based selection
            mapping_repository: Repository for querying existing component mappings
        """
        self.pseudonym_manager = pseudonym_manager
        self.mapping_repository = mapping_repository

    def strip_titles(self, text: str) -> str:
        """Remove French honorific titles from entity text.

        Handles titles with/without periods, case-insensitive.
        Multiple titles are stripped iteratively.

        Examples:
            "Dr. Marie Dubois" → "Marie Dubois"
            "M Jean-Pierre" → "Jean-Pierre"
            "DR MARIE DUBOIS" → "MARIE DUBOIS"
            "Dr. Pr. Marie Dubois" → "Marie Dubois"

        Args:
            text: Entity text potentially containing titles

        Returns:
            Text with titles removed
        """
        # Strip titles iteratively (handles multiple titles)
        while True:
            stripped = re.sub(
                FRENCH_TITLE_PATTERN, "", text, flags=re.IGNORECASE
            ).strip()
            if stripped == text:
                break
            text = stripped

        return text

    def strip_prepositions(self, text: str) -> str:
        """Remove French prepositions from location entity text.

        Handles common prepositions that precede location names in French.
        Only strips from the beginning of the text.

        Examples:
            "à Paris" → "Paris"
            "en France" → "France"
            "du Nord" → "Nord"
            "l'Europe" → "Europe"
            "au Brésil" → "Brésil"

        Args:
            text: Entity text potentially containing prepositions

        Returns:
            Text with leading prepositions removed
        """
        # Strip prepositions from the beginning only
        stripped = re.sub(
            FRENCH_PREPOSITION_PATTERN, "", text, flags=re.IGNORECASE
        ).strip()
        return stripped

    def assign_compositional_pseudonym(
        self,
        entity_text: str,
        entity_type: str,
        gender: str | None = None,
    ) -> PseudonymAssignment:
        """Assign pseudonym using compositional logic.

        For PERSON entities with full names:
        1. Parse first and last name components
        2. Check for existing component mappings
        3. Reuse existing pseudonym components if found
        4. Assign new components for unmatched parts
        5. Flag ambiguous cases (standalone components, etc.)

        Args:
            entity_text: Entity text to pseudonymize (e.g., "Marie Dubois")
            entity_type: Entity type (PERSON, LOCATION, ORG)
            gender: Gender hint for name selection (male/female/neutral/unknown)

        Returns:
            PseudonymAssignment with full pseudonym and components
        """
        # Non-PERSON entities: use simple assignment (no compositional logic)
        if entity_type != "PERSON":
            assignment = self.pseudonym_manager.assign_pseudonym(
                entity_type=entity_type, gender=gender
            )
            return assignment

        # PERSON entity: apply compositional logic
        first_name, last_name, is_ambiguous = self.parse_full_name(entity_text)

        # Handle standalone component (single word)
        if is_ambiguous and first_name and not last_name:
            return self._handle_standalone_component(first_name, gender)

        # Full name: check for existing component mappings
        existing_first_pseudonym = None
        existing_last_pseudonym = None

        if first_name:
            existing_first_pseudonym = self.find_standalone_components(
                first_name, "first_name"
            )

        if last_name:
            existing_last_pseudonym = self.find_standalone_components(
                last_name, "last_name"
            )

        # Assign pseudonym with compositional logic
        assignment = self.pseudonym_manager.assign_pseudonym(
            entity_type=entity_type,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            existing_first=existing_first_pseudonym,
            existing_last=existing_last_pseudonym,
        )

        # Flag multi-word names as potentially ambiguous (Story requirement)
        if is_ambiguous:
            assignment.is_ambiguous = True
            assignment.ambiguity_reason = "Multiple word name - parsing uncertain"
            logger.info(
                "Ambiguous name parsing detected: entity_type=%s, word_count=%d",
                entity_type,
                len(entity_text.split()),
            )

        return assignment

    def parse_full_name(self, entity_text: str) -> tuple[str | None, str | None, bool]:
        """Parse PERSON entity text into first and last name components.

        NEW: Handles titles and compound names (first or last).

        Steps:
        1. Strip titles (Dr., M., Mme., etc.)
        2. Split on whitespace
        3. Detect compound names (hyphenated first or last names)
        4. Parse into first_name, last_name

        Parsing logic:
        - Single word: first_name only, flagged as ambiguous
        - Two words: first_name + last_name, not ambiguous
        - Three+ words: first words as first_name, last word as last_name, flagged as ambiguous

        Examples:
            "Dr. Marie Dubois" → ("Marie", "Dubois", False)
            "Jean-Pierre Martin" → ("Jean-Pierre", "Martin", False)
            "Marie Paluel-Marmont" → ("Marie", "Paluel-Marmont", False)
            "Dr. Jean-Pierre" → ("Jean-Pierre", None, True)

        Args:
            entity_text: Entity text to parse (e.g., "Marie Dubois")

        Returns:
            Tuple of (first_name, last_name, is_ambiguous)
        """
        # Step 1: Strip titles
        text = self.strip_titles(entity_text)

        # Step 2: Split words
        words = text.strip().split()

        if len(words) == 0:
            return None, None, True

        if len(words) == 1:
            # Standalone component - ambiguous
            return words[0], None, True

        if len(words) == 2:
            # Standard case: first + last
            return words[0], words[1], False

        # Three+ words: treat as compound first name + last name
        # Example: "Marie Anne Dubois" -> first="Marie Anne", last="Dubois"
        first_name = " ".join(words[:-1])
        last_name = words[-1]
        return first_name, last_name, True

    def find_standalone_components(
        self, component: str, component_type: str
    ) -> str | None:
        """Find existing pseudonym for standalone component.

        Checks both database (persisted mappings) AND in-memory component mappings
        (validation preview mappings that haven't been saved yet).

        Args:
            component: Name component to search for (e.g., "Marie")
            component_type: Type of component ("first_name" or "last_name")

        Returns:
            Pseudonym component if found, None otherwise
        """
        # FIRST: Check in-memory component mappings (validation preview)
        # This ensures consistent pseudonym component reuse during validation
        # Example: "Claire Fontaine" preview generates ("Fontaine", "last_name") -> "Martin"
        #          Later "Fontaine" standalone should reuse "Martin"
        if hasattr(self.pseudonym_manager, "_component_mappings"):
            component_mappings = self.pseudonym_manager._component_mappings
            # Ensure it's actually a dict (not a Mock in tests)
            if isinstance(component_mappings, dict):
                mapping_key = (component, component_type)
                if mapping_key in component_mappings:
                    result: str = component_mappings[mapping_key]
                    return result

        # SECOND: Query repository for existing component mappings (persisted)
        existing_entities = self.mapping_repository.find_by_component(
            component, component_type
        )

        if not existing_entities:
            return None

        # Use first match to maintain consistency
        first_match = existing_entities[0]

        if component_type == "first_name":
            pseudonym: str | None = first_match.pseudonym_first
            return pseudonym
        else:  # last_name
            pseudonym_last: str | None = first_match.pseudonym_last
            return pseudonym_last

    def _handle_standalone_component(
        self, component: str, gender: str | None
    ) -> PseudonymAssignment:
        """Handle standalone component pseudonymization with ambiguity flagging.

        CRITICAL FIX: Check BOTH first_name and last_name for existing mappings.
        Single words like "Dubois" could be either a first or last name.

        Args:
            component: Standalone component text (e.g., "Marie" or "Dubois")
            gender: Gender hint for name selection

        Returns:
            PseudonymAssignment with ambiguity flag set
        """
        # Check if component already mapped as FIRST name
        existing_first_pseudonym = self.find_standalone_components(
            component, "first_name"
        )

        # CRITICAL FIX: Also check if component already mapped as LAST name
        # Example: "Dr. Marie Dubois" stored as first="Marie", last="Dubois"
        # Later "Dr. Dubois" should match the existing last_name="Dubois"
        existing_last_pseudonym = self.find_standalone_components(
            component, "last_name"
        )

        if existing_first_pseudonym:
            # Use existing first_name mapping, but flag as ambiguous
            assignment = PseudonymAssignment(
                pseudonym_full=existing_first_pseudonym,
                pseudonym_first=existing_first_pseudonym,
                pseudonym_last=None,
                theme=getattr(self.pseudonym_manager, "theme", "unknown"),
                exhaustion_percentage=self.pseudonym_manager.check_exhaustion(),
                is_ambiguous=True,
                ambiguity_reason="Standalone component without full name context",
            )
            logger.info(
                "Standalone component matched existing first_name: component=%s",
                component,
            )
        elif existing_last_pseudonym:
            # Use existing last_name mapping, but flag as ambiguous
            assignment = PseudonymAssignment(
                pseudonym_full=existing_last_pseudonym,
                pseudonym_first=None,
                pseudonym_last=existing_last_pseudonym,
                theme=getattr(self.pseudonym_manager, "theme", "unknown"),
                exhaustion_percentage=self.pseudonym_manager.check_exhaustion(),
                is_ambiguous=True,
                ambiguity_reason="Standalone component without full name context",
            )
            logger.info(
                "Standalone component matched existing last_name: component=%s",
                component,
            )
        else:
            # Assign new pseudonym for standalone component
            assignment = self.pseudonym_manager.assign_pseudonym(
                entity_type="PERSON",
                first_name=component,
                last_name=None,
                gender=gender,
            )
            assignment.is_ambiguous = True
            assignment.ambiguity_reason = (
                "Standalone component without full name context"
            )
            logger.info(
                "Standalone component assigned new pseudonym: component=%s",
                component,
            )

        return assignment
