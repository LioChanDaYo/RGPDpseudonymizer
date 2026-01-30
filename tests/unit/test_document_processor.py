"""Unit tests for DocumentProcessor class.

Tests the core document processing workflow with mocked dependencies
to ensure correct orchestration of all Epic 2 components.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.assignment_engine import PseudonymAssignment


class TestDocumentProcessor:
    """Test suite for DocumentProcessor class."""

    @pytest.fixture
    def temp_db(self, tmp_path: Path) -> str:
        """Create temporary database file.

        Args:
            tmp_path: pytest temporary directory

        Returns:
            Path to temporary database file
        """
        db_path = tmp_path / "test_mappings.db"
        return str(db_path)

    @pytest.fixture
    def mock_db_session(self) -> MagicMock:
        """Create mock database session.

        Returns:
            Mocked DatabaseSession instance
        """
        session = MagicMock()
        session.session = MagicMock()
        session.encryption = MagicMock()
        return session

    @pytest.fixture
    def sample_entities(self) -> list[DetectedEntity]:
        """Create sample detected entities for testing.

        Returns:
            List of DetectedEntity objects
        """
        return [
            DetectedEntity(
                text="Marie Dubois",
                entity_type="PERSON",
                start_pos=0,
                end_pos=12,
            ),
            DetectedEntity(
                text="Paris",
                entity_type="LOCATION",
                start_pos=26,
                end_pos=31,
            ),
        ]

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_process_document_successful_processing(
        self,
        mock_detector_class: Mock,
        mock_write_file: Mock,
        mock_read_file: Mock,
        mock_open_db: Mock,
        mock_validation_workflow: Mock,
        temp_db: str,
        mock_db_session: MagicMock,
        sample_entities: list[DetectedEntity],
    ) -> None:
        """Test successful document processing with all components integrated.

        Verifies:
        - File read/write operations
        - Entity detection
        - Database operations (save/query)
        - Audit logging
        - Processing result metadata
        """
        # Arrange: Mock file I/O
        input_text = "Marie Dubois travaille à Paris."
        mock_read_file.return_value = input_text

        # Arrange: Mock NLP detector
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = sample_entities
        mock_detector.nlp = Mock()
        mock_detector.nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0"}
        mock_detector_class.return_value = mock_detector

        # Arrange: Mock validation workflow (simulate user accepting all entities)
        mock_validation_workflow.return_value = sample_entities

        # Arrange: Mock database session and repositories
        mock_db_session.__enter__ = Mock(return_value=mock_db_session)
        mock_db_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_db_session

        # Mock mapping repository (no existing entities)
        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = None
        mock_mapping_repo.find_all.return_value = []  # Story 2.8: No existing mappings
        mock_mapping_repo.save_batch.return_value = [
            Entity(
                id="test-id-1",
                entity_type="PERSON",
                full_name="Marie Dubois",
                pseudonym_full="Leia Organa",
                pseudonym_first="Leia",
                pseudonym_last="Organa",
                first_seen_timestamp=datetime.now(timezone.utc),
                theme="neutral",
            ),
            Entity(
                id="test-id-2",
                entity_type="LOCATION",
                full_name="Paris",
                pseudonym_full="Coruscant",
                pseudonym_first=None,
                pseudonym_last=None,
                first_seen_timestamp=datetime.now(timezone.utc),
                theme="neutral",
            ),
        ]

        # Mock audit repository
        mock_audit_repo = Mock()

        # Patch repositories
        with patch(
            "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
            return_value=mock_mapping_repo,
        ):
            with patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
                return_value=mock_audit_repo,
            ):
                # Mock pseudonym manager and engine
                with patch(
                    "gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager"
                ) as mock_manager_class:
                    with patch(
                        "gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine"
                    ) as mock_engine_class:
                        mock_manager = Mock()
                        mock_manager_class.return_value = mock_manager

                        mock_engine = Mock()
                        # Mock strip_titles to return input unchanged (no titles in test data)
                        mock_engine.strip_titles.side_effect = lambda x: x
                        # Mock parse_full_name for PERSON entities
                        mock_engine.parse_full_name.side_effect = [
                            ("Marie", "Dubois", False),  # First call for "Marie Dubois"
                            (None, None, False),  # Second call for "Paris" (if any)
                        ]
                        mock_engine.assign_compositional_pseudonym.side_effect = [
                            PseudonymAssignment(
                                pseudonym_full="Leia Organa",
                                pseudonym_first="Leia",
                                pseudonym_last="Organa",
                                theme="neutral",
                                exhaustion_percentage=0.1,
                                is_ambiguous=False,
                            ),
                            PseudonymAssignment(
                                pseudonym_full="Coruscant",
                                pseudonym_first=None,
                                pseudonym_last=None,
                                theme="neutral",
                                exhaustion_percentage=0.1,
                                is_ambiguous=False,
                            ),
                        ]
                        mock_engine_class.return_value = mock_engine

                        # Act: Process document
                        processor = DocumentProcessor(
                            db_path=temp_db,
                            passphrase="test_passphrase_12345",
                            theme="neutral",
                            model_name="spacy",
                        )
                        result = processor.process_document("input.txt", "output.txt")

        # Assert: Processing successful
        assert result.success is True
        assert result.entities_detected == 2
        assert result.entities_new == 2
        assert result.entities_reused == 0
        # Note: With mocking, processing can be very fast (< timer resolution)
        assert result.processing_time_seconds >= 0
        assert result.error_message is None

        # Assert: File operations
        mock_read_file.assert_called_once_with("input.txt")
        mock_write_file.assert_called_once()

        # Assert: Entity detection
        mock_detector.detect_entities.assert_called_once_with(input_text)

        # Assert: Database operations
        assert mock_mapping_repo.find_by_full_name.call_count == 2
        # Verify batch save was called once with 2 entities for transaction safety
        mock_mapping_repo.save_batch.assert_called_once()
        saved_entities = mock_mapping_repo.save_batch.call_args[0][0]
        assert len(saved_entities) == 2

        # Assert: Audit logging
        mock_audit_repo.log_operation.assert_called_once()
        logged_operation = mock_audit_repo.log_operation.call_args[0][0]
        assert logged_operation.operation_type == "PROCESS"
        assert logged_operation.success is True
        assert logged_operation.entity_count == 2

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_process_document_idempotency_reuses_mappings(
        self,
        mock_detector_class: Mock,
        mock_read_file: Mock,
        mock_open_db: Mock,
        mock_validation_workflow: Mock,
        temp_db: str,
        mock_db_session: MagicMock,
        sample_entities: list[DetectedEntity],
    ) -> None:
        """Test idempotency: reprocessing same document reuses existing mappings.

        Verifies:
        - Existing entities are found in database
        - No new entities are created
        - Existing pseudonyms are reused
        - entities_reused counter is correct
        """
        # Arrange: Mock file I/O
        input_text = "Marie Dubois travaille à Paris."
        mock_read_file.return_value = input_text

        # Arrange: Mock NLP detector
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = sample_entities
        mock_detector.nlp = Mock()
        mock_detector.nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0"}
        mock_detector_class.return_value = mock_detector

        # Arrange: Mock validation workflow (simulate user accepting all entities)
        mock_validation_workflow.return_value = sample_entities

        # Arrange: Mock database session
        mock_db_session.__enter__ = Mock(return_value=mock_db_session)
        mock_db_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_db_session

        # Mock mapping repository (existing entities found)
        existing_person = Entity(
            id="existing-person",
            entity_type="PERSON",
            full_name="Marie Dubois",
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            first_seen_timestamp=datetime.now(timezone.utc),
            theme="neutral",
        )
        existing_location = Entity(
            id="existing-location",
            entity_type="LOCATION",
            full_name="Paris",
            pseudonym_full="Coruscant",
            pseudonym_first=None,
            pseudonym_last=None,
            first_seen_timestamp=datetime.now(timezone.utc),
            theme="neutral",
        )

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.side_effect = [
            existing_person,
            existing_location,
        ]
        mock_mapping_repo.find_all.return_value = [
            existing_person,
            existing_location,
        ]  # Story 2.8: Existing mappings to load

        mock_audit_repo = Mock()

        # Patch repositories
        with patch(
            "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
            return_value=mock_mapping_repo,
        ):
            with patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
                return_value=mock_audit_repo,
            ):
                with patch(
                    "gdpr_pseudonymizer.core.document_processor.write_file"
                ) as mock_write_file:
                    # Act: Process document (second time - idempotent)
                    processor = DocumentProcessor(
                        db_path=temp_db,
                        passphrase="test_passphrase_12345",
                        theme="neutral",
                        model_name="spacy",
                    )
                    result = processor.process_document("input.txt", "output.txt")

        # Assert: Processing successful
        assert result.success is True
        assert result.entities_detected == 2
        assert result.entities_new == 0  # No new entities
        assert result.entities_reused == 2  # Both entities reused
        assert result.error_message is None

        # Assert: No new entities saved to database
        mock_mapping_repo.save.assert_not_called()

        # Assert: Pseudonymized text written
        mock_write_file.assert_called_once()
        written_text = mock_write_file.call_args[0][1]
        assert "Leia Organa" in written_text
        assert "Coruscant" in written_text

    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    def test_process_document_file_not_found_error(
        self, mock_read_file: Mock, temp_db: str
    ) -> None:
        """Test error handling when input file not found.

        Verifies:
        - FileProcessingError is caught
        - Processing result indicates failure
        - Error message is populated
        - Audit log records failure
        """
        # Arrange: Mock file read to raise error
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        mock_read_file.side_effect = FileProcessingError("File not found: input.txt")

        with patch(
            "gdpr_pseudonymizer.core.document_processor.open_database"
        ) as mock_open_db:
            mock_db_session = MagicMock()
            mock_db_session.__enter__ = Mock(return_value=mock_db_session)
            mock_db_session.__exit__ = Mock(return_value=None)
            mock_open_db.return_value = mock_db_session

            mock_audit_repo = Mock()
            with patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
                return_value=mock_audit_repo,
            ):
                # Act: Process document
                processor = DocumentProcessor(
                    db_path=temp_db,
                    passphrase="test_passphrase_12345",
                )
                result = processor.process_document("input.txt", "output.txt")

        # Assert: Processing failed
        assert result.success is False
        assert result.entities_detected == 0
        assert result.error_message == "File not found: input.txt"

        # Assert: Failure logged to audit trail
        mock_audit_repo.log_operation.assert_called_once()
        logged_operation = mock_audit_repo.log_operation.call_args[0][0]
        assert logged_operation.success is False
        assert logged_operation.error_message is not None
