"""Integration tests for DocumentProcessor with real SQLite repository.

Uses a real SQLiteMappingRepository (not mocks) to exercise the full
process_document workflow: detection -> pseudonym assignment -> DB save -> output.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

TEST_PASSPHRASE = "integration_test_passphrase_123!"


class TestDocumentProcessorIntegration:
    """End-to-end integration tests with real database."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> str:
        path = str(tmp_path / "integration_test.db")
        init_database(path, TEST_PASSPHRASE)
        return path

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    def test_full_workflow_detection_to_output(
        self,
        mock_write_file: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        db_path: str,
        tmp_path: Path,
    ) -> None:
        """End-to-end: detect entities -> assign pseudonyms -> save to DB -> write output."""
        input_text = "Marie Dubois habite à Paris."
        mock_read_file.return_value = input_text

        detected_entities = [
            DetectedEntity(
                text="Marie Dubois",
                entity_type="PERSON",
                start_pos=0,
                end_pos=12,
            ),
            DetectedEntity(
                text="Paris",
                entity_type="LOCATION",
                start_pos=23,
                end_pos=28,
            ),
        ]
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = detected_entities
        mock_detector.nlp = Mock()
        mock_detector.nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0"}
        mock_detector_class.return_value = mock_detector

        processor = DocumentProcessor(
            db_path=db_path,
            passphrase=TEST_PASSPHRASE,
            theme="neutral",
        )
        result = processor.process_document(
            input_path="input.txt",
            output_path=str(tmp_path / "output.txt"),
            skip_validation=True,
        )

        # Verify success
        assert result.success is True
        assert result.entities_detected == 2
        assert result.entities_new == 2
        assert result.entities_reused == 0

        # Verify output was written with pseudonyms (not original names)
        mock_write_file.assert_called_once()
        written_text = mock_write_file.call_args[0][1]
        assert "Marie Dubois" not in written_text
        assert "Paris" not in written_text

        # Verify entities are saved in the real database
        with open_database(db_path, TEST_PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            person = repo.find_by_full_name("Marie Dubois")
            assert person is not None
            assert person.entity_type == "PERSON"
            assert person.pseudonym_full is not None

            location = repo.find_by_full_name("Paris")
            assert location is not None
            assert location.entity_type == "LOCATION"

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    def test_idempotency_no_duplicates(
        self,
        mock_write_file: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        db_path: str,
        tmp_path: Path,
    ) -> None:
        """Process same document twice: verify reuse, no duplicate entities."""
        input_text = "Marie Dubois habite à Paris."
        mock_read_file.return_value = input_text

        detected_entities = [
            DetectedEntity(
                text="Marie Dubois",
                entity_type="PERSON",
                start_pos=0,
                end_pos=12,
            ),
            DetectedEntity(
                text="Paris",
                entity_type="LOCATION",
                start_pos=23,
                end_pos=28,
            ),
        ]
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = detected_entities
        mock_detector.nlp = Mock()
        mock_detector.nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0"}
        mock_detector_class.return_value = mock_detector

        processor = DocumentProcessor(
            db_path=db_path,
            passphrase=TEST_PASSPHRASE,
            theme="neutral",
        )

        # First pass
        result1 = processor.process_document(
            "input.txt", str(tmp_path / "output1.txt"), skip_validation=True
        )
        assert result1.success is True
        assert result1.entities_new == 2

        # Second pass — same entities should be reused
        result2 = processor.process_document(
            "input.txt", str(tmp_path / "output2.txt"), skip_validation=True
        )
        assert result2.success is True
        assert result2.entities_new == 0
        assert result2.entities_reused == 2

        # Both outputs should have the same pseudonyms
        call1_text = mock_write_file.call_args_list[0][0][1]
        call2_text = mock_write_file.call_args_list[1][0][1]
        assert call1_text == call2_text

        # Database should have exactly 2 entities (not 4)
        with open_database(db_path, TEST_PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            all_entities = repo.find_all()
            assert len(all_entities) == 2
