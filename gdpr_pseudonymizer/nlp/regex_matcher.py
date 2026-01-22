"""
Regex Pattern Matcher for French Entity Detection

Provides pattern-based entity detection using regex patterns
to complement NLP-based detection (hybrid approach).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


class RegexMatcher:
    """Pattern-based entity matcher using regex and French name dictionary.

    Detects entities using predefined regex patterns for:
    - Titles + names (M. Dupont, Dr. Marie Dubois)
    - Compound names (Jean-Pierre, Marie-Claire)
    - Location indicators (à Paris, en France)
    - Organization patterns (TechCorp SA, Société Acme)
    - Full names using name dictionary (Marie Dubois)

    Attributes:
        patterns: Dictionary of compiled regex patterns by category
        name_dictionary: French name dictionary for full name matching
    """

    def __init__(self, config_path: str = "config/detection_patterns.yaml"):
        """Initialize regex matcher.

        Args:
            config_path: Path to detection patterns YAML configuration
        """
        self.config_path = config_path
        self.patterns: dict = {}
        self.name_dictionary: NameDictionary | None = None
        self._config: dict = {}

    def load_patterns(self, config_path: str | None = None) -> None:
        """Load regex patterns from YAML configuration.

        Args:
            config_path: Optional path override for configuration file

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is malformed
        """
        path_str = config_path or self.config_path
        path = Path(path_str)

        if not path.exists():
            logger.error("pattern_config_not_found", path=str(path))
            raise FileNotFoundError(f"Pattern configuration not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f)

            # Compile regex patterns
            self._compile_patterns()

            # Load name dictionary if needed
            if self._needs_name_dictionary():
                self.name_dictionary = NameDictionary()
                self.name_dictionary.load()

            logger.info(
                "patterns_loaded",
                categories_count=len(self.patterns),
                has_name_dictionary=self.name_dictionary is not None,
            )

        except yaml.YAMLError as e:
            logger.error("pattern_config_yaml_error", path=str(path), error=str(e))
            raise ValueError(f"Malformed pattern configuration YAML: {e}") from e

    def _compile_patterns(self) -> None:
        """Compile regex patterns from configuration."""
        pattern_config = self._config.get("patterns", {})

        for category, config in pattern_config.items():
            if not config.get("enabled", True):
                continue

            # Skip full_names category (handled separately with dictionary)
            if category == "full_names":
                continue

            category_patterns = []
            for pattern_def in config.get("patterns", []):
                try:
                    compiled = re.compile(pattern_def["pattern"], re.UNICODE)
                    category_patterns.append(
                        {
                            "regex": compiled,
                            "entity_type": config.get("entity_type", "PERSON"),
                            "confidence": config.get("confidence", 0.5),
                            "description": pattern_def.get("description", ""),
                        }
                    )
                except re.error as e:
                    logger.warning(
                        "pattern_compile_error",
                        category=category,
                        pattern=pattern_def["pattern"],
                        error=str(e),
                    )

            if category_patterns:
                self.patterns[category] = category_patterns

    def _needs_name_dictionary(self) -> bool:
        """Check if name dictionary is required by configuration."""
        pattern_config = self._config.get("patterns", {})
        full_names_config = pattern_config.get("full_names", {})
        return full_names_config.get("enabled", False) and full_names_config.get(
            "use_name_dictionary", False
        )

    def match_entities(self, text: str) -> list[DetectedEntity]:
        """Match entities in text using regex patterns.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects found via pattern matching
        """
        entities: list[DetectedEntity] = []

        # Apply regex patterns by category
        for category, pattern_list in self.patterns.items():
            for pattern_def in pattern_list:
                matches = pattern_def["regex"].finditer(text)
                for match in matches:
                    # Extract entity text (full match or last capturing group)
                    entity_text = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()

                    entity = DetectedEntity(
                        text=entity_text,
                        entity_type=pattern_def["entity_type"],
                        start_pos=start_pos,
                        end_pos=end_pos,
                        confidence=pattern_def["confidence"],
                        source="regex",  # type: ignore[call-arg]
                    )
                    entities.append(entity)

        # Apply name dictionary matching if enabled
        if self.name_dictionary and self._is_full_names_enabled():
            entities.extend(self._match_full_names(text))

        # Remove duplicates (same span)
        entities = self._deduplicate_entities(entities)

        logger.debug("regex_matching_complete", entities_found=len(entities))
        return entities

    def _is_full_names_enabled(self) -> bool:
        """Check if full names pattern matching is enabled."""
        pattern_config = self._config.get("patterns", {})
        return pattern_config.get("full_names", {}).get("enabled", False)

    def _match_full_names(self, text: str) -> list[DetectedEntity]:
        """Match full names using name dictionary.

        Looks for patterns like "[Firstname] [Lastname]" where both
        components are in the French name dictionary.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects for full names
        """
        entities: list[DetectedEntity] = []

        if not self.name_dictionary:
            return entities

        # Pattern: Capitalized word followed by capitalized word
        # This is a candidate full name that we'll validate with dictionary
        name_pattern = re.compile(
            r"\b([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]+(?:-[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]+)?)"
            r"\s+"
            r"([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]+)",
            re.UNICODE,
        )

        matches = name_pattern.finditer(text)
        confidence = (
            self._config.get("patterns", {})
            .get("full_names", {})
            .get("confidence", 0.65)
        )

        for match in matches:
            first_name = match.group(1)
            last_name = match.group(2)

            # Validate with name dictionary
            if self.name_dictionary.is_full_name(first_name, last_name):
                entity_text = f"{first_name} {last_name}"
                entity = DetectedEntity(
                    text=entity_text,
                    entity_type="PERSON",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=confidence,
                    source="regex",  # type: ignore[call-arg]
                )
                entities.append(entity)

        return entities

    def _deduplicate_entities(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Remove duplicate entities with same span.

        When multiple patterns match the same text span, keep the one
        with highest confidence.

        Args:
            entities: List of entities to deduplicate

        Returns:
            Deduplicated list of entities
        """
        # Group by (start_pos, end_pos)
        span_map: dict[tuple[int, int], DetectedEntity] = {}

        for entity in entities:
            span = (entity.start_pos, entity.end_pos)
            if span not in span_map:
                span_map[span] = entity
            else:
                # Keep entity with higher confidence
                existing_conf = span_map[span].confidence or 0.0
                new_conf = entity.confidence or 0.0
                if new_conf > existing_conf:
                    span_map[span] = entity

        # Return sorted by position
        deduplicated = list(span_map.values())
        deduplicated.sort(key=lambda e: e.start_pos)
        return deduplicated

    def get_pattern_stats(self) -> dict[str, int]:
        """Get statistics about loaded patterns.

        Returns:
            Dictionary with pattern category counts
        """
        stats = {
            "categories_loaded": len(self.patterns),
            "total_patterns": sum(len(plist) for plist in self.patterns.values()),
            "has_name_dictionary": self.name_dictionary is not None,
        }
        return stats
