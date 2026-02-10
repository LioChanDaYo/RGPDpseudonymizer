"""
spaCy-based Named Entity Detector Implementation

This module implements the EntityDetector interface using the spaCy NLP library
with the fr_core_news_lg French language model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from spacy.language import Language

logger = get_logger(__name__)


class SpaCyDetector(EntityDetector):
    """spaCy-based implementation of EntityDetector interface.

    Uses spaCy's fr_core_news_lg model for French named entity recognition.
    Model is loaded lazily on first detect_entities() call.
    """

    def __init__(self) -> None:
        """Initialize spaCy detector without loading model."""
        self._nlp: Language | None = None
        self._model_name: str | None = None

    def load_model(self, model_name: str = "fr_core_news_lg") -> None:
        """Load spaCy NLP model into memory.

        Args:
            model_name: spaCy model name (default: fr_core_news_lg)

        Raises:
            OSError: If model is not installed
            Exception: If model loading fails
        """
        try:
            import spacy

            logger.info("loading_spacy_model", model=model_name)
            self._nlp = spacy.load(model_name)
            self._model_name = model_name
            logger.info("spacy_model_loaded", model=model_name)
        except OSError as e:
            logger.error("spacy_model_not_found", model=model_name, error=str(e))
            raise OSError(
                f"spaCy model '{model_name}' not found. "
                f"Install with: python -m spacy download {model_name}"
            ) from e
        except Exception as e:
            logger.error("spacy_model_load_failed", model=model_name, error=str(e))
            raise

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        """Detect named entities in text using spaCy.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects

        Raises:
            ValueError: If text is empty or None
            RuntimeError: If model loading fails
        """
        if not text:
            raise ValueError("Text cannot be empty or None")

        # Lazy load model if not already loaded
        if self._nlp is None:
            self.load_model()

        # Type guard: load_model() guarantees _nlp is not None
        assert self._nlp is not None, "Model failed to load"

        try:
            # Process text with spaCy
            doc = self._nlp(text)

            # Extract entities
            entities = []
            for ent in doc.ents:
                # Map spaCy entity labels to our standard types
                entity_type = self._map_entity_type(ent.label_)

                # Only include PERSON, LOCATION, ORG entities
                if entity_type:
                    entities.append(
                        DetectedEntity(
                            text=ent.text,
                            entity_type=entity_type,
                            start_pos=ent.start_char,
                            end_pos=ent.end_char,
                            confidence=None,  # spaCy doesn't provide per-entity confidence
                            gender=None,  # spaCy doesn't provide gender classification
                        )
                    )

            logger.info("entities_detected", count=len(entities), text_length=len(text))
            return entities

        except Exception as e:
            logger.error("entity_detection_failed", error=str(e))
            raise RuntimeError(f"Entity detection failed: {str(e)}") from e

    def _map_entity_type(self, spacy_label: str) -> str | None:
        """Map spaCy entity labels to standard entity types.

        Args:
            spacy_label: spaCy's entity label (PER, LOC, ORG, MISC, etc.)

        Returns:
            Standard entity type (PERSON, LOCATION, ORG) or None if not mapped
        """
        # spaCy French model uses these labels
        label_mapping = {
            "PER": "PERSON",
            "PERSON": "PERSON",
            "LOC": "LOCATION",
            "LOCATION": "LOCATION",
            "GPE": "LOCATION",  # Geopolitical entity
            "ORG": "ORG",
            "ORGANIZATION": "ORG",
        }
        return label_mapping.get(spacy_label.upper())

    def get_model_info(self) -> dict[str, str]:
        """Get spaCy model metadata.

        Returns:
            Dictionary with model information
        """
        if self._nlp is None:
            return {
                "name": self._model_name or "not_loaded",
                "version": "unknown",
                "library": "spacy",
                "language": "fr",
            }

        meta = self._nlp.meta
        return {
            "name": meta.get("name", self._model_name),
            "version": meta.get("version", "unknown"),
            "library": "spacy",
            "language": meta.get("lang", "fr"),
        }

    @property
    def supports_gender_classification(self) -> bool:
        """spaCy does not provide gender classification.

        Returns:
            False
        """
        return False
