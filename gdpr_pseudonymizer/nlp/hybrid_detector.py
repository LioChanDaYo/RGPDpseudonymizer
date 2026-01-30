"""
Hybrid Entity Detector combining spaCy NER with regex pattern matching

Implements EntityDetector interface using a hybrid approach:
1. Run spaCy NER (baseline detection)
2. Run regex pattern matching
3. Merge results with deduplication
4. Return combined entity list
"""

from __future__ import annotations

import re

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)

# French title pattern for entity normalization during deduplication
# Same pattern used in assignment_engine.py to ensure consistency
FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|Madame|Monsieur|Mademoiselle|Dr\.?|Pr\.?|Prof\.?|M\.?|Mme\.?|Mlle\.?)(?!\w)\s*"


class HybridDetector(EntityDetector):
    """Hybrid entity detector combining spaCy NER with regex pattern matching.

    Detection Pipeline:
        1. Run spaCy NER (baseline detection)
        2. Run regex pattern matching
        3. Merge results with deduplication
        4. Return combined entity list

    Deduplication Rules:
        - Exact overlap (same span) → Keep spaCy entity
        - No overlap → Keep both entities
        - Partial overlap → Flag as ambiguous, keep both

    Attributes:
        spacy_detector: SpaCyDetector instance for NLP-based detection
        regex_matcher: RegexMatcher instance for pattern-based detection
    """

    def __init__(self) -> None:
        """Initialize hybrid detector with spaCy and regex components."""
        self.spacy_detector = SpaCyDetector()
        self.regex_matcher = RegexMatcher()
        self._model_loaded = False

    def load_model(self, model_name: str) -> None:
        """Load spaCy model and regex patterns.

        Args:
            model_name: spaCy model name (e.g., "fr_core_news_lg")

        Raises:
            ModelNotFoundError: If spaCy model is not installed
            FileNotFoundError: If regex pattern config not found
        """
        # Load spaCy model
        self.spacy_detector.load_model(model_name)

        # Load regex patterns
        self.regex_matcher.load_patterns()

        self._model_loaded = True
        logger.info(
            "hybrid_detector_loaded",
            spacy_model=model_name,
            regex_patterns_loaded=self.regex_matcher.get_pattern_stats()[
                "total_patterns"
            ],
        )

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        """Detect entities using hybrid spaCy + regex approach.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects from combined detection

        Raises:
            ValueError: If text is empty or invalid
            ModelNotLoadedError: If models not loaded
        """
        if not text:
            raise ValueError("Text cannot be empty")

        if not self._model_loaded:
            # Lazy load with default model
            logger.warning("hybrid_detector_lazy_loading_model")
            self.load_model("fr_core_news_lg")

        # Step 1: spaCy NER
        spacy_entities = self.spacy_detector.detect_entities(text)
        for entity in spacy_entities:
            entity.source = "spacy"

        logger.debug("spacy_detection_complete", entities_found=len(spacy_entities))

        # Step 2: Regex pattern matching
        regex_entities = self.regex_matcher.match_entities(text)
        for entity in regex_entities:
            entity.source = "regex"

        logger.debug("regex_detection_complete", entities_found=len(regex_entities))

        # Step 3: Merge with deduplication
        merged_entities = self._merge_entities(spacy_entities, regex_entities)

        logger.info(
            "hybrid_detection_complete",
            spacy_count=len(spacy_entities),
            regex_count=len(regex_entities),
            merged_count=len(merged_entities),
        )

        return merged_entities

    def _merge_entities(
        self,
        spacy_entities: list[DetectedEntity],
        regex_entities: list[DetectedEntity],
    ) -> list[DetectedEntity]:
        """Merge spaCy and regex entities with deduplication logic.

        Deduplication Rules:
            - Exact overlap (same span) → Keep spaCy entity (prefer NLP confidence)
            - No overlap → Keep both entities
            - Partial overlap → Flag regex entity as ambiguous, keep both

        Args:
            spacy_entities: Entities detected by spaCy
            regex_entities: Entities detected by regex patterns

        Returns:
            Merged and deduplicated list of entities, sorted by position
        """
        merged: list[DetectedEntity] = list(spacy_entities)

        for regex_entity in regex_entities:
            overlap_found = False

            for spacy_entity in spacy_entities:
                if self._has_overlap(spacy_entity, regex_entity):
                    overlap_found = True

                    if self._is_exact_match(spacy_entity, regex_entity):
                        # Exact match → Skip regex entity (prefer spaCy)
                        logger.debug(
                            "duplicate_entity_removed",
                            text=regex_entity.text,
                            reason="exact_match_with_spacy",
                        )
                        break
                    else:
                        # Partial overlap → Flag regex entity as ambiguous, add it
                        regex_entity.is_ambiguous = True
                        merged.append(regex_entity)
                        logger.debug(
                            "ambiguous_entity_added",
                            regex_text=regex_entity.text,
                            spacy_text=spacy_entity.text,
                            reason="partial_overlap",
                        )
                        break

            if not overlap_found:
                # No overlap → Add regex entity (new detection)
                merged.append(regex_entity)

        # Sort by start position
        merged.sort(key=lambda e: e.start_pos)

        return merged

    def _has_overlap(self, e1: DetectedEntity, e2: DetectedEntity) -> bool:
        """Check if two entities overlap in text span.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities overlap, False otherwise
        """
        return not (e1.end_pos <= e2.start_pos or e2.end_pos <= e1.start_pos)

    def _normalize_entity_text(self, text: str) -> str:
        """Normalize entity text by stripping French titles.

        This ensures that "Dr. Marie Dubois" and "Marie Dubois" are recognized as
        the same entity during deduplication, preventing duplicate validation prompts.

        Args:
            text: Entity text potentially containing titles

        Returns:
            Text with titles removed and whitespace normalized

        Examples:
            "Dr. Marie Dubois" → "Marie Dubois"
            "Mme Fontaine" → "Fontaine"
            "Marie Dubois" → "Marie Dubois" (unchanged)
        """
        # Strip titles iteratively (handles multiple titles like "Dr. Pr. Marie Dubois")
        normalized = text
        while True:
            stripped = re.sub(FRENCH_TITLE_PATTERN, "", normalized, flags=re.IGNORECASE).strip()
            if stripped == normalized:
                break
            normalized = stripped
        return normalized

    def _is_exact_match(self, e1: DetectedEntity, e2: DetectedEntity) -> bool:
        """Check if two entities have identical span OR normalized text.

        Checks both positional exact match and normalized text match to handle
        cases where one detector includes a title and the other doesn't
        (e.g., "Dr. Marie Dubois" from regex vs "Marie Dubois" from spaCy).

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities have same start/end positions OR same normalized text
        """
        # Check positional exact match
        if e1.start_pos == e2.start_pos and e1.end_pos == e2.end_pos:
            return True

        # Check normalized text match (strips titles for comparison)
        # This handles "Dr. Marie Dubois" == "Marie Dubois" cases
        if self._normalize_entity_text(e1.text) == self._normalize_entity_text(e2.text):
            return True

        return False

    def get_model_info(self) -> dict[str, str]:
        """Get model metadata for audit logging.

        Returns:
            Dictionary with hybrid detector information
        """
        spacy_info = self.spacy_detector.get_model_info()
        regex_stats = self.regex_matcher.get_pattern_stats()

        return {
            "name": "hybrid_detector",
            "version": "1.0",
            "library": "hybrid",
            "language": "fr",
            "spacy_model": spacy_info.get("name", "unknown"),
            "spacy_version": spacy_info.get("version", "unknown"),
            "regex_patterns_count": str(regex_stats.get("total_patterns", 0)),
        }

    @property
    def supports_gender_classification(self) -> bool:
        """Whether this detector provides gender information.

        Returns:
            True if spaCy detector supports gender classification
        """
        return self.spacy_detector.supports_gender_classification
