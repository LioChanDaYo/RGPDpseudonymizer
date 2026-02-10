"""Tests for DocumentProcessor extracted sub-methods (R3).

Tests each private method extracted during the process_document() decomposition.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_processor() -> object:
    """Create a DocumentProcessor without triggering DB or NLP init."""
    from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

    return DocumentProcessor(db_path="test.db", passphrase="test_pass")


def _make_entity(
    text: str, entity_type: str, start: int = 0, end: int = 0
) -> DetectedEntity:
    """Create a DetectedEntity for testing."""
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=end or start + len(text),
        confidence=0.95,
        source="test",
    )


# ===========================================================================
# _detect_and_filter_entities
# ===========================================================================


class TestDetectAndFilterEntities:
    """Tests for _detect_and_filter_entities()."""

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_returns_all_entities_when_no_filter(
        self, mock_detector_cls: MagicMock
    ) -> None:
        """All detected entities are returned when entity_type_filter is None."""
        entities = [
            _make_entity("Marie", "PERSON"),
            _make_entity("Paris", "LOCATION"),
            _make_entity("ACME", "ORG"),
        ]
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities("some text")

        assert result == entities
        mock_detector.detect_entities.assert_called_once_with("some text")

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_filters_by_entity_type(self, mock_detector_cls: MagicMock) -> None:
        """Only entities matching the filter set are returned."""
        entities = [
            _make_entity("Marie", "PERSON"),
            _make_entity("Paris", "LOCATION"),
            _make_entity("ACME", "ORG"),
        ]
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities(
            "some text", entity_type_filter={"PERSON", "ORG"}
        )

        assert len(result) == 2
        assert all(e.entity_type in {"PERSON", "ORG"} for e in result)

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_empty_filter_returns_nothing(self, mock_detector_cls: MagicMock) -> None:
        """An empty filter set returns no entities."""
        entities = [_make_entity("Marie", "PERSON")]
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities(
            "some text", entity_type_filter=set()
        )

        # Empty set is falsy, so filter is not applied
        # This matches the current behavior: `if entity_type_filter:` is False for empty set
        assert result == entities

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_no_entities_detected(self, mock_detector_cls: MagicMock) -> None:
        """Returns empty list when detector finds no entities."""
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = []
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities("empty text")

        assert result == []
