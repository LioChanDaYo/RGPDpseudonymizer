"""Pseudonym library manager with JSON loading and gender-matching logic."""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from typing import Any, TypedDict

from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    PseudonymAssignment,
    PseudonymManager,
)

# Configure structured logging (no sensitive data)
logger = logging.getLogger(__name__)


class DataSource(TypedDict):
    """Data source metadata for legal compliance documentation."""

    source_name: str
    url: str
    license: str
    usage_justification: str
    extraction_date: str
    extraction_method: str


class FirstNames(TypedDict):
    """First names grouped by gender."""

    male: list[str]
    female: list[str]
    neutral: list[str]


class PseudonymLibrary(TypedDict):
    """JSON structure for pseudonym library files."""

    theme: str
    data_sources: list[DataSource]
    first_names: FirstNames
    last_names: list[str]


class LibraryBasedPseudonymManager(PseudonymManager):
    """Concrete implementation of PseudonymManager with JSON library loading.

    Features:
    - Load themed libraries from JSON files (neutral, star_wars, lotr)
    - Gender-preserving pseudonym selection (when gender metadata available)
    - Exhaustion detection with 80% warning threshold
    - Systematic fallback naming when library exhausted (Person-001, Location-001)
    - Collision prevention (no duplicate pseudonyms assigned)

    Attributes:
        theme: Currently loaded library theme
        first_names: First names grouped by gender
        last_names: Last names list
        _used_pseudonyms: Set of already assigned full pseudonyms
        _fallback_counters: Counters for fallback naming by entity type
    """

    def __init__(self) -> None:
        """Initialize pseudonym manager with empty state."""
        self.theme: str | None = None
        self.first_names: FirstNames = {"male": [], "female": [], "neutral": []}
        self.last_names: list[str] = []
        self._used_pseudonyms: set[str] = set()
        self._fallback_counters: dict[str, int] = {
            "PERSON": 0,
            "LOCATION": 0,
            "ORG": 0,
        }

    def load_library(self, theme: str) -> None:
        """Load pseudonym library from JSON file.

        Args:
            theme: Library theme name (neutral, star_wars, lotr)

        Raises:
            FileNotFoundError: If library file not found
            ValueError: If library format is invalid
        """
        # Construct path: data/pseudonyms/{theme}.json
        library_path = (
            Path(__file__).parent.parent.parent
            / "data"
            / "pseudonyms"
            / f"{theme}.json"
        )

        if not library_path.exists():
            raise FileNotFoundError(f"Pseudonym library not found: {library_path}")

        # Load and validate JSON structure
        try:
            with open(library_path, encoding="utf-8") as f:
                library_data: dict[Any, Any] = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {library_path}: {e}")

        # Validate required fields
        self._validate_library_structure(library_data, theme)

        # Store library data
        self.theme = library_data["theme"]
        self.first_names = library_data["first_names"]
        self.last_names = library_data["last_names"]

        # Reset usage tracking for new library
        self._used_pseudonyms.clear()
        self._fallback_counters = {"PERSON": 0, "LOCATION": 0, "ORG": 0}

        logger.info(
            "Pseudonym library loaded: theme=%s, male_first=%d, female_first=%d, neutral_first=%d, last=%d",
            self.theme,
            len(self.first_names["male"]),
            len(self.first_names["female"]),
            len(self.first_names["neutral"]),
            len(self.last_names),
        )

    def _validate_library_structure(
        self, library_data: dict[Any, Any], expected_theme: str
    ) -> None:
        """Validate library JSON structure and minimum requirements.

        Args:
            library_data: Parsed JSON data
            expected_theme: Expected theme name

        Raises:
            ValueError: If validation fails
        """
        # Check required top-level fields
        required_fields = ["theme", "data_sources", "first_names", "last_names"]
        for field in required_fields:
            if field not in library_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate theme matches filename
        if library_data["theme"] != expected_theme:
            raise ValueError(
                f"Theme mismatch: expected '{expected_theme}', "
                f"got '{library_data['theme']}'"
            )

        # Validate first_names structure
        first_names = library_data["first_names"]
        if not isinstance(first_names, dict):
            raise ValueError("first_names must be a dictionary")

        required_gender_keys = ["male", "female", "neutral"]
        for gender_key in required_gender_keys:
            if gender_key not in first_names:
                raise ValueError(f"Missing gender category: {gender_key}")
            if not isinstance(first_names[gender_key], list):
                raise ValueError(f"first_names.{gender_key} must be a list")

        # Validate last_names is a list
        if not isinstance(library_data["last_names"], list):
            raise ValueError("last_names must be a list")

        # Check minimum name counts (≥500 first names total, ≥500 last names)
        total_first_names = (
            len(first_names["male"])
            + len(first_names["female"])
            + len(first_names["neutral"])
        )
        if total_first_names < 500:
            raise ValueError(
                f"Insufficient first names: {total_first_names} < 500 required"
            )

        if len(library_data["last_names"]) < 500:
            raise ValueError(
                f"Insufficient last names: {len(library_data['last_names'])} < 500 required"
            )

    def assign_pseudonym(
        self,
        entity_type: str,
        first_name: str | None = None,
        last_name: str | None = None,
        gender: str | None = None,
        existing_first: str | None = None,
        existing_last: str | None = None,
    ) -> PseudonymAssignment:
        """Assign pseudonym using gender-matching logic and exhaustion handling.

        Args:
            entity_type: Entity type (PERSON, LOCATION, ORG)
            first_name: First name component (PERSON only, currently unused)
            last_name: Last name component (PERSON only, currently unused)
            gender: Gender hint for name selection (male/female/neutral/unknown)
            existing_first: Existing first name pseudonym to reuse (Story 2.2)
            existing_last: Existing last name pseudonym to reuse (Story 2.2)

        Returns:
            PseudonymAssignment with selected pseudonym and metadata

        Raises:
            ValueError: If entity_type is invalid or library not loaded
            RuntimeError: If library is exhausted and fallback fails
        """
        if self.theme is None:
            raise ValueError("No library loaded. Call load_library() first.")

        if entity_type not in ["PERSON", "LOCATION", "ORG"]:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        # Check exhaustion and warn at 80% threshold
        exhaustion = self.check_exhaustion()
        if exhaustion >= 0.8:
            logger.warning(
                "Library 80%% exhausted (theme=%s, exhaustion=%.2f%%). Consider switching themes or expect fallback naming.",
                self.theme,
                exhaustion * 100,
            )

        # Compositional logic (Story 2.2) - for now, just interface support
        # Future: Query MappingRepository for existing components
        pseudonym_first_name = existing_first
        pseudonym_last_name = existing_last

        # Generate pseudonym based on entity type
        if entity_type == "PERSON":
            if pseudonym_first_name is None:
                pseudonym_first_name = self._select_first_name(gender)
            if pseudonym_last_name is None:
                pseudonym_last_name = self._select_last_name()

            pseudonym_full = f"{pseudonym_first_name} {pseudonym_last_name}"
        else:
            # LOCATION and ORG use only last names
            pseudonym_first_name = None
            if pseudonym_last_name is None:
                pseudonym_last_name = self._select_last_name()
            pseudonym_full = pseudonym_last_name

        # Check for collision and use fallback if needed
        if pseudonym_full in self._used_pseudonyms:
            logger.warning(
                "Pseudonym collision detected: %s (entity_type=%s, theme=%s)",
                pseudonym_full,
                entity_type,
                self.theme,
            )
            # Use fallback naming
            pseudonym_full = self._generate_fallback_name(entity_type)
            if entity_type == "PERSON":
                # Parse fallback name (e.g., "Person-001" -> first=None, last="Person-001")
                pseudonym_first_name = None
                pseudonym_last_name = pseudonym_full
            else:
                pseudonym_last_name = pseudonym_full

        # Mark as used
        self._used_pseudonyms.add(pseudonym_full)

        return PseudonymAssignment(
            pseudonym_full=pseudonym_full,
            pseudonym_first=pseudonym_first_name,
            pseudonym_last=pseudonym_last_name,
            theme=self.theme,
            exhaustion_percentage=exhaustion,
        )

    def _select_first_name(self, gender: str | None) -> str:
        """Select first name from library with gender-matching.

        Args:
            gender: Gender hint (male/female/neutral/unknown/None)

        Returns:
            Selected first name

        Raises:
            RuntimeError: If no names available for gender
        """
        # Map gender to library categories
        if gender == "male" and self.first_names["male"]:
            candidates = self.first_names["male"]
        elif gender == "female" and self.first_names["female"]:
            candidates = self.first_names["female"]
        elif gender == "neutral" and self.first_names["neutral"]:
            candidates = self.first_names["neutral"]
        else:
            # Unknown/None gender or empty category -> use all available names
            candidates = (
                self.first_names["male"]
                + self.first_names["female"]
                + self.first_names["neutral"]
            )

        if not candidates:
            raise RuntimeError(f"No first names available for gender: {gender}")

        return secrets.choice(candidates)

    def _select_last_name(self) -> str:
        """Select last name from library.

        Returns:
            Selected last name

        Raises:
            RuntimeError: If no last names available
        """
        if not self.last_names:
            raise RuntimeError("No last names available in library")

        return secrets.choice(self.last_names)

    def _generate_fallback_name(self, entity_type: str) -> str:
        """Generate systematic fallback name when library exhausted.

        Args:
            entity_type: Entity type (PERSON, LOCATION, ORG)

        Returns:
            Fallback name in format "{Type}-{Counter:03d}"
        """
        self._fallback_counters[entity_type] += 1
        counter = self._fallback_counters[entity_type]
        return f"{entity_type.title()}-{counter:03d}"

    def check_exhaustion(self) -> float:
        """Get library exhaustion percentage.

        Calculates exhaustion based on used pseudonyms vs. total possible combinations.
        For PERSON entities: total = first_names * last_names
        For LOCATION/ORG: total = last_names only

        Returns:
            Float between 0.0 (unused) and 1.0 (fully exhausted)
        """
        if self.theme is None or not self.last_names:
            return 0.0

        # Calculate total possible combinations
        # For simplicity, assume most entities are PERSON type
        total_first_names = (
            len(self.first_names["male"])
            + len(self.first_names["female"])
            + len(self.first_names["neutral"])
        )

        if total_first_names == 0:
            # Only last names available (edge case)
            total_combinations = len(self.last_names)
        else:
            # PERSON entities use first + last combinations
            total_combinations = total_first_names * len(self.last_names)

        # Calculate exhaustion percentage
        if total_combinations == 0:
            return 1.0  # Fully exhausted

        return len(self._used_pseudonyms) / total_combinations
