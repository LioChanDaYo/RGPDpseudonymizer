"""
French Name Dictionary Loader

Provides utilities for loading and querying French name dictionaries
used in regex pattern matching for entity detection.
"""

from __future__ import annotations

import json
from pathlib import Path

from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


class NameDictionary:
    """French name dictionary for pattern-based entity detection.

    Loads common French first names and last names from JSON file
    and provides fast lookup methods for name validation.

    Attributes:
        first_names: Set of common French first names
        last_names: Set of common French last names
    """

    def __init__(self, dictionary_path: str | None = None):
        """Initialize name dictionary.

        Args:
            dictionary_path: Path to french_names.json file.
                           Defaults to data/french_names.json
        """
        self.first_names: set[str] = set()
        self.last_names: set[str] = set()
        self._dictionary_path = dictionary_path or "data/french_names.json"

    def load(self) -> None:
        """Load name dictionary from JSON file.

        Raises:
            FileNotFoundError: If dictionary file doesn't exist
            ValueError: If dictionary file is malformed
        """
        path = Path(self._dictionary_path)

        if not path.exists():
            logger.error(
                "name_dictionary_not_found",
                path=str(path),
            )
            raise FileNotFoundError(f"Name dictionary not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            self.first_names = set(data.get("first_names", []))
            self.last_names = set(data.get("last_names", []))

            logger.info(
                "name_dictionary_loaded",
                first_names_count=len(self.first_names),
                last_names_count=len(self.last_names),
            )

        except json.JSONDecodeError as e:
            logger.error(
                "name_dictionary_json_error",
                path=str(path),
                error=str(e),
            )
            raise ValueError(f"Malformed name dictionary JSON: {e}") from e

    def is_first_name(self, name: str) -> bool:
        """Check if name is a known French first name.

        Args:
            name: Name to check (case-insensitive)

        Returns:
            True if name is in first names dictionary
        """
        # Case-insensitive lookup
        return name.lower().capitalize() in self.first_names or name in self.first_names

    def is_last_name(self, name: str) -> bool:
        """Check if name is a known French last name.

        Args:
            name: Name to check (case-insensitive)

        Returns:
            True if name is in last names dictionary
        """
        # Case-insensitive lookup with capitalization normalization
        normalized = name.capitalize()
        return normalized in self.last_names or name in self.last_names

    def is_full_name(self, first_name: str, last_name: str) -> bool:
        """Check if both components form a valid French full name.

        Args:
            first_name: First name to check
            last_name: Last name to check

        Returns:
            True if both are in respective dictionaries
        """
        return self.is_first_name(first_name) and self.is_last_name(last_name)

    def get_stats(self) -> dict[str, int]:
        """Get dictionary statistics.

        Returns:
            Dictionary with first_names_count and last_names_count
        """
        return {
            "first_names_count": len(self.first_names),
            "last_names_count": len(self.last_names),
        }
