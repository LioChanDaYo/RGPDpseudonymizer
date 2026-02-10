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


class Locations(TypedDict):
    """Locations grouped by type (cities, planets/countries, regions)."""

    cities: list[str]
    planets: list[str]  # or 'countries' for neutral theme
    regions: list[str]


class Organizations(TypedDict):
    """Organizations grouped by type (companies, agencies, institutions)."""

    companies: list[str]
    agencies: list[str]
    institutions: list[str]


class PseudonymLibrary(TypedDict):
    """JSON structure for pseudonym library files."""

    theme: str
    data_sources: list[DataSource]
    first_names: FirstNames
    last_names: list[str]
    locations: Locations
    organizations: Organizations


class LibraryBasedPseudonymManager(PseudonymManager):
    """Concrete implementation of PseudonymManager with JSON library loading.

    Features:
    - Load themed libraries from JSON files (neutral, star_wars, lotr)
    - Gender-preserving pseudonym selection (when gender metadata available)
    - Exhaustion detection with 80% warning threshold
    - Systematic fallback naming when library exhausted (Person-001, Location-001)
    - Collision prevention (no duplicate pseudonyms assigned)
    - Component-level collision prevention (Story 2.8) - ensures 1:1 reversible mapping

    Attributes:
        theme: Currently loaded library theme
        first_names: First names grouped by gender
        last_names: Last names list
        locations: Locations grouped by type (cities, planets/countries, regions)
        organizations: Organizations grouped by type (companies, agencies, institutions)
        _used_pseudonyms: Set of already assigned full pseudonyms
        _component_mappings: Dict mapping (real_component, component_type) to pseudonym_component
        _fallback_counters: Counters for fallback naming by entity type
    """

    def __init__(self) -> None:
        """Initialize pseudonym manager with empty state."""
        self.theme: str | None = None
        self.first_names: FirstNames = {"male": [], "female": [], "neutral": []}
        self.last_names: list[str] = []
        self.locations: Locations = {"cities": [], "planets": [], "regions": []}
        self.organizations: Organizations = {
            "companies": [],
            "agencies": [],
            "institutions": [],
        }
        self._used_pseudonyms: set[str] = set()

        # Component-level collision prevention (Story 2.8)
        # Key: (real_component_value, component_type)
        # Value: pseudonym_component
        # Example: {("Dubois", "last_name"): "Neto", ("Marie", "first_name"): "Alexia"}
        self._component_mappings: dict[tuple[str, str], str] = {}

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
        self.locations = library_data["locations"]
        self.organizations = library_data["organizations"]

        # Reset usage tracking for new library
        self._used_pseudonyms.clear()
        self._component_mappings.clear()
        self._fallback_counters = {"PERSON": 0, "LOCATION": 0, "ORG": 0}

        # Calculate location and organization totals
        # Use planets for themed libraries, countries for neutral
        planets_or_countries = self.locations.get(
            "planets", self.locations.get("countries", [])
        )
        if planets_or_countries is None:
            planets_or_countries = []
        total_locations = (
            len(self.locations["cities"])
            + len(planets_or_countries)
            + len(self.locations["regions"])
        )
        total_organizations = (
            len(self.organizations["companies"])
            + len(self.organizations["agencies"])
            + len(self.organizations["institutions"])
        )

        logger.info(
            "Pseudonym library loaded: theme=%s, male_first=%d, female_first=%d, neutral_first=%d, last=%d, locations=%d, organizations=%d",
            self.theme,
            len(self.first_names["male"]),
            len(self.first_names["female"]),
            len(self.first_names["neutral"]),
            len(self.last_names),
            total_locations,
            total_organizations,
        )

    def reset_preview_state(self) -> None:
        """Reset internal state accumulated during validation preview.

        Clears used pseudonyms and component mappings generated during
        preview/validation so they don't cause false collision positives
        during actual processing.
        """
        self._used_pseudonyms.clear()
        self._component_mappings.clear()

    def get_component_mapping(self, component: str, component_type: str) -> str | None:
        """Look up an in-memory component mapping.

        Args:
            component: Real component value (e.g., "Dubois")
            component_type: Component type ("first_name" or "last_name")

        Returns:
            Pseudonym component if found, None otherwise
        """
        return self._component_mappings.get((component, component_type))

    def _flatten_location_list(
        self, locations: Locations | dict[Any, Any]
    ) -> list[str]:
        """Flatten location categories into a single list.

        Args:
            locations: Locations dictionary with cities, planets/countries, regions

        Returns:
            Flattened list of all location names
        """
        planets_or_countries = locations.get("planets", locations.get("countries", []))
        if planets_or_countries is None:
            planets_or_countries = []

        return locations["cities"] + planets_or_countries + locations["regions"]

    def _flatten_organization_list(
        self, organizations: Organizations | dict[Any, Any]
    ) -> list[str]:
        """Flatten organization categories into a single list.

        Args:
            organizations: Organizations dictionary with companies, agencies, institutions

        Returns:
            Flattened list of all organization names
        """
        return (
            organizations["companies"]
            + organizations["agencies"]
            + organizations["institutions"]
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
        required_fields = [
            "theme",
            "data_sources",
            "first_names",
            "last_names",
            "locations",
            "organizations",
        ]
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

        # Validate locations structure
        locations = library_data["locations"]
        if not isinstance(locations, dict):
            raise ValueError("locations must be a dictionary")

        required_location_keys = ["cities", "regions"]
        for loc_key in required_location_keys:
            if loc_key not in locations:
                raise ValueError(f"Missing location category: {loc_key}")
            if not isinstance(locations[loc_key], list):
                raise ValueError(f"locations.{loc_key} must be a list")

        # Check for planets (themed) or countries (neutral) - at least one must exist
        if "planets" not in locations and "countries" not in locations:
            raise ValueError(
                "locations must have either 'planets' or 'countries' field"
            )
        if "planets" in locations and not isinstance(locations["planets"], list):
            raise ValueError("locations.planets must be a list")
        if "countries" in locations and not isinstance(locations["countries"], list):
            raise ValueError("locations.countries must be a list")

        # Validate organizations structure
        organizations = library_data["organizations"]
        if not isinstance(organizations, dict):
            raise ValueError("organizations must be a dictionary")

        required_org_keys = ["companies", "agencies", "institutions"]
        for org_key in required_org_keys:
            if org_key not in organizations:
                raise ValueError(f"Missing organization category: {org_key}")
            if not isinstance(organizations[org_key], list):
                raise ValueError(f"organizations.{org_key} must be a list")

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

        # Check minimum location counts (≥80 total)
        total_locations = len(self._flatten_location_list(locations))
        if total_locations < 80:
            raise ValueError(f"Insufficient locations: {total_locations} < 80 required")

        # Check minimum organization counts (≥35 total)
        total_organizations = len(self._flatten_organization_list(organizations))
        if total_organizations < 35:
            raise ValueError(
                f"Insufficient organizations: {total_organizations} < 35 required"
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
                # Pass real first name for component collision tracking
                pseudonym_first_name = self._select_first_name(gender, first_name)
            if pseudonym_last_name is None:
                # Pass real last name for component collision tracking
                pseudonym_last_name = self._select_last_name(last_name)

            pseudonym_full = f"{pseudonym_first_name} {pseudonym_last_name}"
        elif entity_type == "LOCATION":
            # LOCATION entities use dedicated location library (no components)
            pseudonym_first_name = None
            pseudonym_last_name = None
            if existing_last is not None:
                # Reuse existing location pseudonym for consistency
                pseudonym_full = existing_last
            else:
                pseudonym_full = self._select_location()
        elif entity_type == "ORG":
            # ORG entities use dedicated organization library (no components)
            pseudonym_first_name = None
            pseudonym_last_name = None
            if existing_last is not None:
                # Reuse existing organization pseudonym for consistency
                pseudonym_full = existing_last
            else:
                pseudonym_full = self._select_organization()
        else:
            raise ValueError(f"Unsupported entity_type: {entity_type}")

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
                # For compositional consistency: preserve existing components if provided
                # If existing_first was passed, keep it (e.g., reusing "Leia" from previous mapping)
                # Only replace the component that wasn't already assigned
                if existing_first and not existing_last:
                    # Keep existing first, use fallback for last
                    pseudonym_first_name = existing_first
                    pseudonym_last_name = pseudonym_full
                    pseudonym_full = f"{pseudonym_first_name} {pseudonym_last_name}"
                elif existing_last and not existing_first:
                    # Keep existing last, use fallback for first
                    pseudonym_first_name = pseudonym_full
                    pseudonym_last_name = existing_last
                    pseudonym_full = f"{pseudonym_first_name} {pseudonym_last_name}"
                else:
                    # No existing components or both provided: use fallback as single unit
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

    def _select_first_name(
        self, gender: str | None, real_first_name: str | None = None
    ) -> str:
        """Select first name from library with gender-matching and collision prevention.

        Args:
            gender: Gender hint (male/female/neutral/unknown/None)
            real_first_name: Real first name component (for collision tracking)

        Returns:
            Selected first name

        Raises:
            RuntimeError: If no names available for gender or no collision-free component found
        """
        # Check if real_first_name already has mapping
        if real_first_name:
            mapping_key = (real_first_name, "first_name")
            if mapping_key in self._component_mappings:
                # Reuse existing mapping for consistency
                return self._component_mappings[mapping_key]

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

        # Select with collision prevention
        max_attempts = 100
        for attempt in range(max_attempts):
            candidate = secrets.choice(candidates)

            # Check if this pseudonym component already used for different real component
            is_collision = False
            for (
                real_comp,
                comp_type,
            ), pseudo_comp in self._component_mappings.items():
                if comp_type == "first_name" and pseudo_comp == candidate:
                    # This pseudonym is already used for a different real first name
                    if real_first_name and real_comp != real_first_name:
                        is_collision = True
                        break

            if not is_collision:
                # No collision - safe to use this pseudonym component
                if real_first_name:
                    self._component_mappings[(real_first_name, "first_name")] = (
                        candidate
                    )
                return candidate

        # Failed to find collision-free component after max attempts
        raise RuntimeError(
            f"Unable to find unique first name component for '{real_first_name}' "
            f"after {max_attempts} attempts. Library may be exhausted."
        )

    def _select_last_name(self, real_last_name: str | None = None) -> str:
        """Select last name from library with collision prevention.

        Args:
            real_last_name: Real last name component (for collision tracking)

        Returns:
            Selected last name

        Raises:
            RuntimeError: If no last names available or no collision-free component found
        """
        if not self.last_names:
            raise RuntimeError("No last names available in library")

        # Check if real_last_name already has mapping
        if real_last_name:
            mapping_key = (real_last_name, "last_name")
            if mapping_key in self._component_mappings:
                # Reuse existing mapping for consistency
                return self._component_mappings[mapping_key]

        # Select new pseudonym component, ensure no collision
        max_attempts = 100
        for attempt in range(max_attempts):
            candidate = secrets.choice(self.last_names)

            # Check if this pseudonym component already used for different real component
            is_collision = False
            for (real_comp, comp_type), pseudo_comp in self._component_mappings.items():
                if comp_type == "last_name" and pseudo_comp == candidate:
                    # This pseudonym is already used for a different real last name
                    if real_last_name and real_comp != real_last_name:
                        is_collision = True
                        break

            if not is_collision:
                # No collision - safe to use this pseudonym component
                if real_last_name:
                    self._component_mappings[(real_last_name, "last_name")] = candidate
                return candidate

        # Failed to find collision-free component after max attempts
        raise RuntimeError(
            f"Unable to find unique last name component for '{real_last_name}' "
            f"after {max_attempts} attempts. Library may be exhausted."
        )

    def _select_location(self) -> str:
        """Select location pseudonym from library with collision prevention.

        Returns:
            Selected location name

        Raises:
            RuntimeError: If no locations available or unable to find unique location
        """
        if not self.locations:
            raise RuntimeError("No locations available in library")

        # Flatten all location categories into single candidate list
        candidates = self._flatten_location_list(self.locations)

        if not candidates:
            raise RuntimeError("No location candidates available in library")

        # Select with collision prevention
        max_attempts = 100
        for attempt in range(max_attempts):
            candidate = secrets.choice(candidates)
            if candidate not in self._used_pseudonyms:
                return candidate

        # Library exhausted - use fallback naming (Location-001, Location-002, etc.)
        logger.warning(
            "Location library exhausted after %d attempts, using fallback naming",
            max_attempts,
        )
        return self._generate_fallback_name("LOCATION")

    def _select_organization(self) -> str:
        """Select organization pseudonym from library with collision prevention.

        Returns:
            Selected organization name

        Raises:
            RuntimeError: If no organizations available or unable to find unique organization
        """
        if not self.organizations:
            raise RuntimeError("No organizations available in library")

        # Flatten all organization categories into single candidate list
        candidates = self._flatten_organization_list(self.organizations)

        if not candidates:
            raise RuntimeError("No organization candidates available in library")

        # Select with collision prevention
        max_attempts = 100
        for attempt in range(max_attempts):
            candidate = secrets.choice(candidates)
            if candidate not in self._used_pseudonyms:
                return candidate

        # Library exhausted - use fallback naming (Org-001, Org-002, etc.)
        logger.warning(
            "Organization library exhausted after %d attempts, using fallback naming",
            max_attempts,
        )
        return self._generate_fallback_name("ORG")

    def _generate_fallback_name(self, entity_type: str) -> str:
        """Generate systematic fallback name when library exhausted.

        Generates unique fallback names like "Org-001", "Location-002", etc.
        Loops until finding a name not already in _used_pseudonyms to prevent
        collisions with previously assigned pseudonyms.

        Args:
            entity_type: Entity type (PERSON, LOCATION, ORG)

        Returns:
            Fallback name in format "{Type}-{Counter:03d}"
        """
        # Safety limit to prevent infinite loops
        max_attempts = 10000

        for _ in range(max_attempts):
            self._fallback_counters[entity_type] += 1
            counter = self._fallback_counters[entity_type]
            fallback_name = f"{entity_type.title()}-{counter:03d}"

            # Check if this fallback name is already used
            if fallback_name not in self._used_pseudonyms:
                return fallback_name

            # Name already used, continue to next counter value
            logger.debug(
                "Fallback name %s already in use, incrementing counter",
                fallback_name,
            )

        # Should never reach here in normal usage
        raise RuntimeError(
            f"Unable to generate unique fallback name for {entity_type} "
            f"after {max_attempts} attempts"
        )

    def load_existing_mappings(
        self, existing_entities: list[Any]
    ) -> None:  # pragma: no cover
        """Load existing component mappings from database to prevent collisions.

        Reconstructs _component_mappings from existing database entities to ensure
        new assignments don't collide with previously assigned pseudonyms.

        Also restores fallback counters from existing fallback-style pseudonyms
        (e.g., "Org-001", "Location-002") to ensure new fallback names don't collide.

        Args:
            existing_entities: List of Entity objects from MappingRepository.find_all()
        """
        import re

        loaded_components = 0

        # Pattern to match fallback-style pseudonyms: "Person-001", "Location-002", "Org-003"
        fallback_pattern = re.compile(r"^(Person|Location|Org)-(\d+)$")

        for entity in existing_entities:
            # Only PERSON entities have component-level tracking
            if entity.entity_type == "PERSON":
                # Extract real components and pseudonym components
                if entity.first_name and entity.pseudonym_first:
                    key = (entity.first_name, "first_name")
                    self._component_mappings[key] = entity.pseudonym_first
                    loaded_components += 1

                if entity.last_name and entity.pseudonym_last:
                    key = (entity.last_name, "last_name")
                    self._component_mappings[key] = entity.pseudonym_last
                    loaded_components += 1

            # Track full pseudonym as used
            self._used_pseudonyms.add(entity.pseudonym_full)

            # Check if this is a fallback-style pseudonym and update counter
            match = fallback_pattern.match(entity.pseudonym_full)
            if match:
                entity_type_str = match.group(1).upper()
                counter_value = int(match.group(2))

                # Update counter to max of current and loaded value
                if entity_type_str in self._fallback_counters:
                    if counter_value > self._fallback_counters[entity_type_str]:
                        self._fallback_counters[entity_type_str] = counter_value
                        logger.debug(
                            "Updated fallback counter for %s to %d",
                            entity_type_str,
                            counter_value,
                        )

        logger.info(
            "Loaded %d existing component mappings from database (%d entities processed). "
            "Fallback counters: PERSON=%d, LOCATION=%d, ORG=%d",
            loaded_components,
            len(existing_entities),
            self._fallback_counters["PERSON"],
            self._fallback_counters["LOCATION"],
            self._fallback_counters["ORG"],
        )

    def check_exhaustion(self) -> float:
        """Get library exhaustion percentage.

        Calculates exhaustion based on used pseudonyms vs. total possible combinations.
        For PERSON entities: total = first_names * last_names
        For LOCATION entities: total = cities + planets/countries + regions
        For ORG entities: total = companies + agencies + institutions

        Returns:
            Float between 0.0 (unused) and 1.0 (fully exhausted)
        """
        if self.theme is None or not self.last_names:
            return 0.0

        # Calculate total possible combinations for PERSON entities
        total_first_names = (
            len(self.first_names["male"])
            + len(self.first_names["female"])
            + len(self.first_names["neutral"])
        )

        if total_first_names == 0:
            # Only last names available (edge case)
            person_combinations = len(self.last_names)
        else:
            # PERSON entities use first + last combinations
            person_combinations = total_first_names * len(self.last_names)

        # Calculate total available LOCATION pseudonyms
        location_combinations = len(self._flatten_location_list(self.locations))

        # Calculate total available ORG pseudonyms
        org_combinations = len(self._flatten_organization_list(self.organizations))

        # Total pool includes PERSON, LOCATION, and ORG pseudonyms
        total_combinations = (
            person_combinations + location_combinations + org_combinations
        )

        # Calculate exhaustion percentage
        if total_combinations == 0:
            return 1.0  # Fully exhausted

        return len(self._used_pseudonyms) / total_combinations
