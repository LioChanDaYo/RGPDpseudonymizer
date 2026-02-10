"""
Hybrid Entity Detector combining spaCy NER with regex pattern matching

Implements EntityDetector interface using a hybrid approach:
1. Run spaCy NER (baseline detection)
2. Run regex pattern matching
3. Merge results with deduplication
4. Return combined entity list
"""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.utils.french_patterns import strip_french_titles
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


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
            - Special case: Regex ORG with "Cabinet" overlapping spaCy PERSON → Prefer ORG

        Args:
            spacy_entities: Entities detected by spaCy
            regex_entities: Entities detected by regex patterns

        Returns:
            Merged and deduplicated list of entities, sorted by position
        """
        merged: list[DetectedEntity] = list(spacy_entities)
        # Track spaCy entities to remove (when regex ORG supersedes spaCy PERSON)
        entities_to_remove: list[DetectedEntity] = []

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
                    elif self._should_prefer_regex_org(regex_entity, spacy_entity):
                        # Special case: Regex ORG (Cabinet pattern) supersedes spaCy PERSON
                        # Remove spaCy PERSON and add regex ORG (not ambiguous)
                        entities_to_remove.append(spacy_entity)
                        merged.append(regex_entity)
                        logger.debug(
                            "org_supersedes_person",
                            regex_text=regex_entity.text,
                            spacy_text=spacy_entity.text,
                            reason="cabinet_pattern_preferred",
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

        # Remove superseded spaCy entities
        for entity in entities_to_remove:
            if entity in merged:
                merged.remove(entity)

        # Filter out title-only entities (e.g., "Maître" without a name)
        merged = self._filter_title_only_entities(merged)

        # Filter out common French label words detected as entities
        merged = self._filter_label_words(merged)

        # Sort by start position
        merged.sort(key=lambda e: e.start_pos)

        return merged

    def _should_prefer_regex_org(
        self, regex_entity: DetectedEntity, spacy_entity: DetectedEntity
    ) -> bool:
        """Check if regex ORG entity should supersede spaCy PERSON entity.

        This handles the "Cabinet" pattern case where spaCy incorrectly detects
        "Cabinet Mercier" as PERSON, but regex correctly detects
        "Cabinet Mercier & Associés" as ORG.

        Args:
            regex_entity: Regex-detected entity
            spacy_entity: spaCy-detected entity

        Returns:
            True if regex ORG should replace spaCy PERSON
        """
        # Only apply when regex is ORG and spaCy is PERSON
        if regex_entity.entity_type != "ORG" or spacy_entity.entity_type != "PERSON":
            return False

        # Check if regex entity starts with organization prefix patterns
        org_prefixes = ("Cabinet", "Société", "Entreprise", "Groupe", "Compagnie")
        if not regex_entity.text.startswith(org_prefixes):
            return False

        # Check if spaCy entity is contained within regex entity
        # (i.e., regex detected a larger span that includes the spaCy detection)
        if (
            regex_entity.start_pos <= spacy_entity.start_pos
            and regex_entity.end_pos >= spacy_entity.end_pos
        ):
            return True

        return False

    def _filter_title_only_entities(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Filter out entities that are just titles without actual names.

        Entities like "Maître" or "Dr." alone (without a following name) are
        sometimes incorrectly detected by spaCy as PERSON entities. This filter
        removes such false positives.

        Args:
            entities: List of detected entities

        Returns:
            Filtered list with title-only entities removed
        """
        filtered = []
        for entity in entities:
            # Only filter PERSON entities (titles don't apply to ORG/LOCATION)
            if entity.entity_type != "PERSON":
                filtered.append(entity)
                continue

            # Check if entity becomes empty after stripping titles
            normalized = self._normalize_entity_text(entity.text)
            if normalized:
                filtered.append(entity)
            else:
                logger.debug(
                    "title_only_entity_filtered",
                    text=entity.text,
                    source=entity.source,
                    reason="entity_is_title_only",
                )

        return filtered

    def _filter_label_words(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Filter out common French label words incorrectly detected as entities.

        Words like "Lieu" (Location label), "Date", etc. are sometimes detected
        by spaCy as named entities when they appear as document labels.

        Args:
            entities: List of detected entities

        Returns:
            Filtered list with label words removed
        """
        # Common French label words that are not actual named entities
        # These appear in documents as field labels (e.g., "Lieu: Paris")
        label_words = {
            "lieu",  # Location label
            "date",  # Date label
            "heure",  # Time label
            "objet",  # Subject label
            "sujet",  # Subject label
            "titre",  # Title label
            "nom",  # Name label
            "adresse",  # Address label
        }

        filtered = []
        for entity in entities:
            # Check if entity text (lowercase) is just a label word
            if entity.text.lower().strip() in label_words:
                logger.debug(
                    "label_word_entity_filtered",
                    text=entity.text,
                    entity_type=entity.entity_type,
                    source=entity.source,
                    reason="entity_is_label_word",
                )
            else:
                filtered.append(entity)

        return filtered

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
        return strip_french_titles(text)

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
