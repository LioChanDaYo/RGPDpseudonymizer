"""Gender detection from French first names.

Provides heuristic gender detection using a lookup dictionary built from
INSEE public data (Open License 2.0 / Etalab). Used by the compositional
pseudonym engine to assign gender-matched pseudonyms.
"""

from __future__ import annotations

import json
from pathlib import Path

from gdpr_pseudonymizer.resources import FRENCH_GENDER_LOOKUP_PATH
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


class GenderDetector:
    """Detect gender from French first names using lookup dictionary.

    Uses a pre-built dictionary of ~900+ French first names classified as
    male, female, or ambiguous. Ambiguous and unknown names return None,
    which causes the pseudonym manager to fall back to the combined list
    (preserving current behavior).

    Attributes:
        _male_names: Set of known male first names (normalized)
        _female_names: Set of known female first names (normalized)
        _ambiguous_names: Set of known ambiguous first names (normalized)
        _loaded: Whether the lookup dictionary has been loaded
    """

    def __init__(self, lookup_path: str | None = None) -> None:
        """Initialize gender detector.

        Args:
            lookup_path: Path to gender lookup JSON file. If None, uses
                the bundled package resource.
        """
        self._lookup_path = Path(lookup_path) if lookup_path else FRENCH_GENDER_LOOKUP_PATH
        self._male_names: set[str] = set()
        self._female_names: set[str] = set()
        self._ambiguous_names: set[str] = set()
        self._loaded: bool = False

    def load(self) -> None:
        """Load gender lookup dictionary from JSON.

        Raises:
            FileNotFoundError: If lookup file does not exist
            ValueError: If lookup file format is invalid
        """
        if not self._lookup_path.exists():
            raise FileNotFoundError(
                f"Gender lookup file not found: {self._lookup_path}"
            )

        with open(self._lookup_path, encoding="utf-8") as f:
            data = json.load(f)

        self._male_names = {self._normalize(n) for n in data.get("male", [])}
        self._female_names = {self._normalize(n) for n in data.get("female", [])}
        self._ambiguous_names = {self._normalize(n) for n in data.get("ambiguous", [])}
        self._loaded = True

        logger.info(
            "gender_lookup_loaded",
            male_count=len(self._male_names),
            female_count=len(self._female_names),
            ambiguous_count=len(self._ambiguous_names),
        )

    def _ensure_loaded(self) -> None:
        """Lazy-load lookup dictionary on first use."""
        if not self._loaded:
            self.load()

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a name for case-insensitive lookup.

        Args:
            name: Raw name string

        Returns:
            Capitalized name for consistent matching
        """
        return name.strip().capitalize()

    def detect_gender(self, first_name: str) -> str | None:
        """Detect gender from a first name.

        Args:
            first_name: First name to look up

        Returns:
            "male", "female", or None (unknown/ambiguous)
        """
        self._ensure_loaded()

        if not first_name or not first_name.strip():
            return None

        # Handle compound names: first component determines gender (AC4)
        normalized = self._normalize(first_name)
        if "-" in normalized:
            first_component = normalized.split("-")[0].strip()
            if first_component:
                normalized = self._normalize(first_component)

        if normalized in self._ambiguous_names:
            return None

        if normalized in self._male_names:
            return "male"

        if normalized in self._female_names:
            return "female"

        return None

    def detect_gender_from_full_name(
        self, full_name: str, entity_type: str
    ) -> str | None:
        """Detect gender from a full entity name.

        For PERSON entities: extracts first name component, detects gender.
        For non-PERSON entities: returns None (gender not applicable).
        Compound names: first component determines gender (AC4).

        Args:
            full_name: Full entity name (e.g., "Marie Dupont")
            entity_type: Entity type (PERSON, LOCATION, ORG)

        Returns:
            "male", "female", or None
        """
        if entity_type != "PERSON":
            return None

        if not full_name or not full_name.strip():
            return None

        # Extract first name: first word of the full name
        parts = full_name.strip().split()
        if not parts:
            return None

        first_name = parts[0]
        return self.detect_gender(first_name)
