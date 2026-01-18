"""Pseudonym assignment engine interface and stub implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PseudonymAssignment:
    """Result of pseudonym assignment operation.

    Attributes:
        pseudonym_full: Complete pseudonym string
        pseudonym_first: First name component (PERSON only)
        pseudonym_last: Last name component (PERSON only)
        theme: Library used for assignment (neutral/star_wars/lotr)
        exhaustion_percentage: Library usage percentage (0.0-1.0)
    """

    pseudonym_full: str
    pseudonym_first: str | None
    pseudonym_last: str | None
    theme: str
    exhaustion_percentage: float


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
