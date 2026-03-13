"""Counter-based pseudonym generator for the neutral_id theme."""

from __future__ import annotations

# Mapping from entity type to short prefix
_ENTITY_PREFIX: dict[str, str] = {
    "PERSON": "PER",
    "LOCATION": "LOC",
    "ORG": "ORG",
}


class NeutralIdPseudonymGenerator:
    """Generate sequential identifiers like PER-001, LOC-001, ORG-001.

    Each entity type maintains its own independent counter.
    Counters start at 0; the first call to ``generate()`` returns 001.
    """

    def __init__(self) -> None:
        """Initialize with all counters at zero."""
        self._counters: dict[str, int] = {
            "PERSON": 0,
            "LOCATION": 0,
            "ORG": 0,
        }

    def generate(self, entity_type: str) -> str:
        """Increment counter for *entity_type* and return the next identifier.

        Args:
            entity_type: One of ``"PERSON"``, ``"LOCATION"``, ``"ORG"``.

        Returns:
            Formatted identifier, e.g. ``"PER-001"``.

        Raises:
            ValueError: If *entity_type* is not recognised.
        """
        if entity_type not in _ENTITY_PREFIX:
            raise ValueError(
                f"Unknown entity_type '{entity_type}'. "
                f"Valid types: {', '.join(sorted(_ENTITY_PREFIX))}"
            )

        self._counters[entity_type] += 1
        prefix = _ENTITY_PREFIX[entity_type]
        return f"{prefix}-{self._counters[entity_type]:03d}"

    def reset(self) -> None:
        """Reset all counters to zero."""
        for key in self._counters:
            self._counters[key] = 0

    def get_counter(self, entity_type: str) -> int:
        """Return the current counter value for *entity_type*.

        Args:
            entity_type: One of ``"PERSON"``, ``"LOCATION"``, ``"ORG"``.

        Returns:
            Current counter value (0 means no identifiers generated yet).

        Raises:
            ValueError: If *entity_type* is not recognised.
        """
        if entity_type not in self._counters:
            raise ValueError(
                f"Unknown entity_type '{entity_type}'. "
                f"Valid types: {', '.join(sorted(self._counters))}"
            )
        return self._counters[entity_type]

    def set_counter(self, entity_type: str, value: int) -> None:
        """Set the counter for *entity_type* so the next ``generate()`` resumes from *value + 1*.

        Args:
            entity_type: One of ``"PERSON"``, ``"LOCATION"``, ``"ORG"``.
            value: Current maximum counter value already used.

        Raises:
            ValueError: If *entity_type* is not recognised.
        """
        if entity_type not in self._counters:
            raise ValueError(
                f"Unknown entity_type '{entity_type}'. "
                f"Valid types: {', '.join(sorted(self._counters))}"
            )
        self._counters[entity_type] = value
