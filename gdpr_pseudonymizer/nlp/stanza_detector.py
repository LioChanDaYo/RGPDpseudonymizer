"""
Stanza-based Named Entity Detector Implementation

This module implements the EntityDetector interface using the Stanza NLP library
(Stanford NLP) with French language models.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector

if TYPE_CHECKING:
    from stanza.pipeline.core import Pipeline

logger = logging.getLogger(__name__)


class StanzaDetector(EntityDetector):
    """Stanza-based implementation of EntityDetector interface.

    Uses Stanford's Stanza library with French NER models.
    Model is loaded lazily on first detect_entities() call.
    """

    def __init__(self) -> None:
        """Initialize Stanza detector without loading model."""
        self._nlp: Pipeline | None = None
        self._model_name: str | None = None

    def load_model(self, model_name: str = "fr") -> None:
        """Load Stanza NLP model into memory.

        Args:
            model_name: Stanza language code (default: fr for French)

        Raises:
            Exception: If model loading fails or models not downloaded
        """
        try:
            import stanza

            logger.info(f"loading_stanza_model: model={model_name}")
            # Load French pipeline with NER processor
            self._nlp = stanza.Pipeline(
                lang=model_name,
                processors="tokenize,ner",
                logging_level="WARNING",  # Suppress verbose logs
            )
            self._model_name = model_name
            logger.info(f"stanza_model_loaded: model={model_name}")
        except Exception as e:
            logger.error(
                f"stanza_model_load_failed: model={model_name}, error={str(e)}"
            )
            raise RuntimeError(
                f"Stanza model '{model_name}' loading failed. "
                f"Download with: import stanza; stanza.download('{model_name}')"
            ) from e

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        """Detect named entities in text using Stanza.

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
            # Process text with Stanza
            doc = self._nlp(text)

            # Extract entities
            entities = []
            for sentence in doc.sentences:
                for ent in sentence.ents:
                    # Map Stanza entity labels to our standard types
                    entity_type = self._map_entity_type(ent.type)

                    # Only include PERSON, LOCATION, ORG entities
                    if entity_type:
                        entities.append(
                            DetectedEntity(
                                text=ent.text,
                                entity_type=entity_type,
                                start_pos=ent.start_char,
                                end_pos=ent.end_char,
                                confidence=None,  # Stanza doesn't provide per-entity confidence in standard output
                                gender=None,  # Stanza doesn't provide gender classification
                            )
                        )

            logger.info(
                f"entities_detected: count={len(entities)}, text_length={len(text)}"
            )
            return entities

        except Exception as e:
            logger.error(f"entity_detection_failed: error={str(e)}")
            raise RuntimeError(f"Entity detection failed: {str(e)}") from e

    def _map_entity_type(self, stanza_label: str) -> str | None:
        """Map Stanza entity labels to standard entity types.

        Args:
            stanza_label: Stanza's entity type (PER, LOC, ORG, MISC, etc.)

        Returns:
            Standard entity type (PERSON, LOCATION, ORG) or None if not mapped
        """
        # Stanza uses OntoNotes-style labels
        label_mapping = {
            "PER": "PERSON",
            "PERSON": "PERSON",
            "LOC": "LOCATION",
            "LOCATION": "LOCATION",
            "GPE": "LOCATION",  # Geopolitical entity
            "ORG": "ORG",
            "ORGANIZATION": "ORG",
        }
        return label_mapping.get(stanza_label.upper())

    def get_model_info(self) -> dict[str, str]:
        """Get Stanza model metadata.

        Returns:
            Dictionary with model information
        """
        if self._nlp is None:
            return {
                "name": self._model_name or "not_loaded",
                "version": "unknown",
                "library": "stanza",
                "language": "fr",
            }

        # Stanza doesn't expose version easily, use package version
        try:
            import stanza

            version = stanza.__version__
        except AttributeError:
            version = "unknown"

        return {
            "name": f"stanza_{self._model_name}",
            "version": version,
            "library": "stanza",
            "language": self._model_name or "fr",
        }

    @property
    def supports_gender_classification(self) -> bool:
        """Stanza does not provide gender classification.

        Returns:
            False
        """
        return False
