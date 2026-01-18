"""
EntityDetector Interface for NLP Engine

This module defines the abstract interface that all NLP detector implementations
must conform to. This enables swapping between different NLP libraries (spaCy, Stanza)
without changing core application logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DetectedEntity:
    """Represents a detected named entity from NER processing.

    Attributes:
        text: Original entity text (e.g., "Marie Dubois")
        entity_type: Entity classification (PERSON, LOCATION, or ORG)
        start_pos: Character offset start position in document
        end_pos: Character offset end position in document
        confidence: NER confidence score (0.0-1.0), None if not available
        gender: Gender classification (male/female/neutral/unknown), None if not available
    """

    text: str
    entity_type: str
    start_pos: int
    end_pos: int
    confidence: Optional[float] = None
    gender: Optional[str] = None


class EntityDetector(ABC):
    """Abstract interface for named entity detection implementations.

    All NLP detector implementations (spaCy, Stanza) must implement this interface
    to ensure consistent behavior across the application.
    """

    @abstractmethod
    def load_model(self, model_name: str) -> None:
        """Load NLP model into memory.

        Args:
            model_name: Name/identifier of the model to load
                       (e.g., "fr_core_news_lg" for spaCy)

        Raises:
            ModelNotFoundError: If model is not installed
            ModelLoadError: If model fails to load
        """
        pass

    @abstractmethod
    def detect_entities(self, text: str) -> List[DetectedEntity]:
        """Detect named entities in text.

        This method performs NER on the input text and returns all detected entities.
        Model is loaded lazily on first call if not already loaded.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects with position and classification

        Raises:
            ValueError: If text is empty or invalid
            ModelNotLoadedError: If model loading fails
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """Get model metadata for audit logging.

        Returns:
            Dictionary with model information:
                - name: Model name/identifier
                - version: Model version string
                - library: NLP library name (spacy/stanza)
                - language: Model language code (fr)
        """
        pass

    @property
    @abstractmethod
    def supports_gender_classification(self) -> bool:
        """Whether this NLP library provides gender information.

        Returns:
            True if library can classify entity gender, False otherwise
        """
        pass
