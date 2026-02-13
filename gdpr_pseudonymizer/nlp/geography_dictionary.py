"""
French Geography Dictionary Loader

Provides utilities for loading and querying French geography data
(cities, regions, departments) for LOCATION entity detection.
"""

from __future__ import annotations

import json
from pathlib import Path

from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


class GeographyDictionary:
    """French geography dictionary for location entity detection.

    Loads French cities, regions, and departments from JSON file
    and provides O(1) set lookups for location validation.

    Attributes:
        cities: Set of French city names
        regions: Set of French region names
        departments: Set of French department names
        all_locations: Combined set of all location names
    """

    def __init__(self, dictionary_path: str | None = None):
        """Initialize geography dictionary.

        Args:
            dictionary_path: Path to french_geography.json file.
                           Defaults to bundled resource file.
        """
        self.cities: set[str] = set()
        self.regions: set[str] = set()
        self.departments: set[str] = set()
        self.all_locations: set[str] = set()
        if dictionary_path is None:
            from gdpr_pseudonymizer.resources import FRENCH_GEOGRAPHY_PATH

            dictionary_path = str(FRENCH_GEOGRAPHY_PATH)
        self._dictionary_path = dictionary_path

    def load(self) -> None:
        """Load geography dictionary from JSON file.

        Raises:
            FileNotFoundError: If dictionary file doesn't exist
            ValueError: If dictionary file is malformed
        """
        path = Path(self._dictionary_path)

        if not path.exists():
            logger.error("geography_dictionary_not_found", path=str(path))
            raise FileNotFoundError(f"Geography dictionary not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            self.cities = set(data.get("cities", []))
            self.regions = set(data.get("regions", []))
            self.departments = set(data.get("departments", []))
            self.all_locations = self.cities | self.regions | self.departments

            logger.info(
                "geography_dictionary_loaded",
                cities_count=len(self.cities),
                regions_count=len(self.regions),
                departments_count=len(self.departments),
            )

        except json.JSONDecodeError as e:
            logger.error(
                "geography_dictionary_json_error",
                path=str(path),
                error=str(e),
            )
            raise ValueError(f"Malformed geography dictionary JSON: {e}") from e

    def is_location(self, name: str) -> bool:
        """Check if name is a known French location.

        Args:
            name: Location name to check (exact match)

        Returns:
            True if name is in the geography dictionary
        """
        return name in self.all_locations

    def get_stats(self) -> dict[str, int]:
        """Get dictionary statistics.

        Returns:
            Dictionary with counts per category
        """
        return {
            "cities_count": len(self.cities),
            "regions_count": len(self.regions),
            "departments_count": len(self.departments),
            "total_locations": len(self.all_locations),
        }
