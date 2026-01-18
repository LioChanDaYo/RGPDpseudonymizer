"""Unit tests for EntityDetector interface and implementations."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector


def test_detected_entity_initialization() -> None:
    """Test DetectedEntity dataclass initialization and field validation."""
    entity = DetectedEntity(
        text="Marie Dubois",
        entity_type="PERSON",
        start_pos=0,
        end_pos=12,
        confidence=0.95,
        gender="female",
    )

    assert entity.text == "Marie Dubois"
    assert entity.entity_type == "PERSON"
    assert entity.start_pos == 0
    assert entity.end_pos == 12
    assert entity.confidence == 0.95
    assert entity.gender == "female"


def test_detected_entity_optional_fields() -> None:
    """Test DetectedEntity with optional fields set to None."""
    entity = DetectedEntity(
        text="Paris", entity_type="LOCATION", start_pos=50, end_pos=55
    )

    assert entity.text == "Paris"
    assert entity.entity_type == "LOCATION"
    assert entity.confidence is None
    assert entity.gender is None


def test_entity_detector_is_abstract() -> None:
    """Test that EntityDetector interface cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        EntityDetector()  # type: ignore


def test_spacy_detector_implements_interface() -> None:
    """Test that SpaCyDetector implements all required EntityDetector methods."""
    detector = SpaCyDetector()

    # Verify all abstract methods are implemented
    assert hasattr(detector, "load_model")
    assert hasattr(detector, "detect_entities")
    assert hasattr(detector, "get_model_info")
    assert hasattr(detector, "supports_gender_classification")

    # Verify they are callable
    assert callable(detector.load_model)
    assert callable(detector.detect_entities)
    assert callable(detector.get_model_info)


def test_spacy_detector_get_model_info_before_loading() -> None:
    """Test get_model_info returns expected structure before model is loaded."""
    detector = SpaCyDetector()
    model_info = detector.get_model_info()

    assert isinstance(model_info, dict)
    assert "name" in model_info
    assert "version" in model_info
    assert "library" in model_info
    assert "language" in model_info
    assert model_info["library"] == "spacy"
    assert model_info["language"] == "fr"


def test_spacy_detector_supports_gender_classification() -> None:
    """Test that SpaCyDetector reports gender classification support correctly."""
    detector = SpaCyDetector()
    assert detector.supports_gender_classification is False


def test_spacy_detector_load_model_with_mock(mocker: MockerFixture) -> None:
    """Test spaCy detector model loading without requiring actual model download."""
    # Create mock spaCy module and model
    mock_nlp = mocker.Mock()
    mock_nlp.meta = {
        "name": "fr_core_news_lg",
        "version": "3.8.0",
        "lang": "fr",
    }

    mock_spacy = mocker.Mock()
    mock_spacy.load.return_value = mock_nlp
    mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

    detector = SpaCyDetector()
    detector.load_model("fr_core_news_lg")

    # Verify model was loaded
    mock_spacy.load.assert_called_once_with("fr_core_news_lg")

    # Verify model info is correct
    model_info = detector.get_model_info()
    assert model_info["name"] == "fr_core_news_lg"
    assert model_info["version"] == "3.8.0"


def test_spacy_detector_model_not_found_error(mocker: MockerFixture) -> None:
    """Test error handling when spaCy model is not installed."""
    # Mock spaCy to raise OSError
    mock_spacy = mocker.Mock()
    mock_spacy.load.side_effect = OSError("Model not found")
    mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

    detector = SpaCyDetector()

    with pytest.raises(OSError, match="not found"):
        detector.load_model("fr_core_news_lg")


def test_spacy_detector_detect_entities_empty_text() -> None:
    """Test that detect_entities raises ValueError for empty text."""
    detector = SpaCyDetector()

    with pytest.raises(ValueError, match="Text cannot be empty"):
        detector.detect_entities("")


def test_spacy_detector_detect_entities_with_mock(mocker: MockerFixture) -> None:
    """Test entity detection with mocked spaCy model."""
    # Create mock entity
    mock_entity = mocker.Mock()
    mock_entity.text = "Marie Dubois"
    mock_entity.label_ = "PER"
    mock_entity.start_char = 0
    mock_entity.end_char = 12

    # Create mock doc
    mock_doc = mocker.Mock()
    mock_doc.ents = [mock_entity]

    # Create mock nlp model
    mock_nlp = mocker.Mock()
    mock_nlp.return_value = mock_doc
    mock_nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0", "lang": "fr"}

    # Mock spaCy
    mock_spacy = mocker.Mock()
    mock_spacy.load.return_value = mock_nlp
    mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

    detector = SpaCyDetector()
    detector.load_model("fr_core_news_lg")

    entities = detector.detect_entities("Marie Dubois travaille à Paris.")

    assert len(entities) == 1
    assert entities[0].text == "Marie Dubois"
    assert entities[0].entity_type == "PERSON"
    assert entities[0].start_pos == 0
    assert entities[0].end_pos == 12
    assert entities[0].confidence is None
    assert entities[0].gender is None
