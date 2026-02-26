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
                        # Mock strip_prepositions to return input unchanged (no prepositions in test data)
                        mock_engine.strip_prepositions.side_effect = lambda x: x
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
                        # skip_validation=True to test core processing without AC8 auto-accept
                        result = processor.process_document(
                            "input.txt", "output.txt", skip_validation=True
                        )

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
                    # skip_validation=True to test core processing without AC8 auto-accept
                    result = processor.process_document(
                        "input.txt", "output.txt", skip_validation=True
                    )

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
        assert result.error_message == "FileProcessingError: File not found: input.txt"

        # Assert: Failure logged to audit trail
        mock_audit_repo.log_operation.assert_called_once()
        logged_operation = mock_audit_repo.log_operation.call_args[0][0]
        assert logged_operation.success is False
        assert logged_operation.error_message is not None


class TestSanitizeErrorMessage:
    """Tests for DocumentProcessor._sanitize_error_message (SEC-001)."""

    def test_strips_single_quoted_entity_names(self) -> None:
        error = ValueError("Cannot parse entity 'Jean Dupont'")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Jean Dupont" not in result
        assert "'[REDACTED]'" in result
        assert result.startswith("ValueError: ")

    def test_strips_double_quoted_entity_names(self) -> None:
        error = RuntimeError('Failed to process "Marie Dubois"')
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Marie Dubois" not in result
        assert '"[REDACTED]"' in result
        assert result.startswith("RuntimeError: ")

    def test_strips_capitalized_name_sequences(self) -> None:
        error = ValueError("Entity Jean Pierre Dupont could not be resolved")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Jean Pierre Dupont" not in result
        assert "[REDACTED]" in result

    def test_strips_french_accented_names(self) -> None:
        error = ValueError("Cannot find entity 'Éloïse Béranger'")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Éloïse Béranger" not in result
        assert "'[REDACTED]'" in result

    def test_strips_organization_names(self) -> None:
        error = RuntimeError("Duplicate entry for 'Société Générale'")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Société Générale" not in result

    def test_strips_address_fragments(self) -> None:
        error = ValueError("Cannot geocode 'Rue de la Paix, Paris'")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Rue de la Paix" not in result
        assert "Paris" not in result

    def test_preserves_exception_type(self) -> None:
        error = OSError("Permission denied")
        result = DocumentProcessor._sanitize_error_message(error)
        assert result.startswith("OSError: ")

    def test_preserves_generic_error_structure(self) -> None:
        error = RuntimeError("database connection failed")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "database connection failed" in result

    def test_handles_empty_message(self) -> None:
        error = ValueError("")
        result = DocumentProcessor._sanitize_error_message(error)
        assert result == "ValueError: "

    def test_multiple_quoted_strings(self) -> None:
        error = ValueError("'Jean Dupont' conflicts with 'Marie Dubois'")
        result = DocumentProcessor._sanitize_error_message(error)
        assert "Jean Dupont" not in result
        assert "Marie Dubois" not in result
        assert result.count("[REDACTED]") == 2


class TestDetectEntities:
    """Tests for DocumentProcessor.detect_entities() (GUI phase 1)."""

    @pytest.fixture
    def processor(self, tmp_path: Path) -> DocumentProcessor:
        return DocumentProcessor(
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
        )

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    def test_happy_path(
        self,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_read_file.return_value = "Marie Dubois habite à Paris."
        entities = [
            DetectedEntity(
                text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
            ),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=23, end_pos=28
            ),
        ]
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_class.return_value = mock_detector

        text, detected = processor.detect_entities("input.txt")

        assert text == "Marie Dubois habite à Paris."
        assert len(detected) == 2
        mock_read_file.assert_called_once_with("input.txt")

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    def test_empty_document(
        self,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_read_file.return_value = ""
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = []
        mock_detector_class.return_value = mock_detector

        text, detected = processor.detect_entities("empty.txt")

        assert text == ""
        assert detected == []

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    def test_entity_type_filter(
        self,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_read_file.return_value = "Marie Dubois habite à Paris."
        entities = [
            DetectedEntity(
                text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
            ),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=23, end_pos=28
            ),
        ]
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_class.return_value = mock_detector

        _, detected = processor.detect_entities(
            "input.txt", entity_type_filter={"PERSON"}
        )

        assert len(detected) == 1
        assert detected[0].entity_type == "PERSON"

    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    def test_file_read_error(
        self,
        mock_read_file: Mock,
        processor: DocumentProcessor,
    ) -> None:
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        mock_read_file.side_effect = FileProcessingError("Cannot read file")

        with pytest.raises(FileProcessingError, match="Cannot read file"):
            processor.detect_entities("bad_file.txt")


class TestBuildPseudonymPreviews:
    """Tests for DocumentProcessor.build_pseudonym_previews() (GUI phase)."""

    @pytest.fixture
    def processor(self, tmp_path: Path) -> DocumentProcessor:
        return DocumentProcessor(
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            theme="neutral",
        )

    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_happy_path_new_entities(
        self,
        mock_open_db: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        # Setup DB session mock
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        mock_engine = Mock()
        mock_engine.strip_titles.side_effect = lambda x: x
        mock_engine.strip_prepositions.side_effect = lambda x: x
        mock_engine.assign_compositional_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="neutral",
            exhaustion_percentage=0.1,
            is_ambiguous=False,
        )
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = None
        mock_mapping_repo.find_all.return_value = []

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
        ):
            entities = [
                DetectedEntity(
                    text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
                ),
            ]
            previews = processor.build_pseudonym_previews(entities)

        assert "Marie Dubois_0" in previews
        assert previews["Marie Dubois_0"] == "Leia Organa"

    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_existing_mapping(
        self,
        mock_open_db: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        existing = Entity(
            id="e1",
            entity_type="PERSON",
            full_name="Marie Dubois",
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            first_seen_timestamp=datetime.now(timezone.utc),
            theme="neutral",
        )

        mock_engine = Mock()
        mock_engine.strip_titles.side_effect = lambda x: x
        mock_engine.strip_prepositions.side_effect = lambda x: x
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = existing
        mock_mapping_repo.find_all.return_value = [existing]

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
        ):
            entities = [
                DetectedEntity(
                    text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
                ),
            ]
            previews = processor.build_pseudonym_previews(entities)

        assert previews["Marie Dubois_0"] == "Leia Organa"

    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_title_preservation(
        self,
        mock_open_db: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        mock_engine = Mock()
        mock_engine.strip_titles.side_effect = lambda x: x.replace("Dr. ", "").replace(
            "Dr ", ""
        )
        mock_engine.strip_prepositions.side_effect = lambda x: x
        mock_engine.assign_compositional_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="neutral",
            exhaustion_percentage=0.1,
            is_ambiguous=False,
        )
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = None
        mock_mapping_repo.find_all.return_value = []

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
        ):
            entities = [
                DetectedEntity(
                    text="Dr. Marie Dubois",
                    entity_type="PERSON",
                    start_pos=0,
                    end_pos=16,
                ),
            ]
            previews = processor.build_pseudonym_previews(entities)

        key = "Dr. Marie Dubois_0"
        assert key in previews
        assert previews[key].startswith("Dr.")


class TestFinalizeDocument:
    """Tests for DocumentProcessor.finalize_document() (GUI phase 2)."""

    @pytest.fixture
    def processor(self, tmp_path: Path) -> DocumentProcessor:
        return DocumentProcessor(
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
        )

    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_happy_path(
        self,
        mock_open_db: Mock,
        mock_write_file: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        mock_engine = Mock()
        mock_engine.strip_titles.side_effect = lambda x: x
        mock_engine.strip_prepositions.side_effect = lambda x: x
        mock_engine.parse_full_name.return_value = ("Marie", "Dubois", False)
        mock_engine.gender_detector = None
        mock_engine.assign_compositional_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="neutral",
            exhaustion_percentage=0.1,
            is_ambiguous=False,
        )
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = None
        mock_mapping_repo.find_all.return_value = []
        mock_mapping_repo.save_batch.return_value = []

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
        ):
            entities = [
                DetectedEntity(
                    text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
                ),
            ]
            result = processor.finalize_document(
                "Marie Dubois habite ici.", entities, "output.txt"
            )

        assert result.success is True
        assert result.entities_new == 1
        mock_write_file.assert_called_once()
        written_text = mock_write_file.call_args[0][1]
        assert "Leia Organa" in written_text

    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_error_during_processing(
        self,
        mock_open_db: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_open_db.side_effect = RuntimeError("DB connection failed")

        # Mock _log_failed_operation to avoid secondary DB access
        with patch.object(processor, "_log_failed_operation"):
            result = processor.finalize_document("some text", [], "output.txt")

        assert result.success is False
        assert "RuntimeError" in (result.error_message or "")

    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_empty_entity_list(
        self,
        mock_open_db: Mock,
        mock_write_file: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_all.return_value = []

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
        ):
            result = processor.finalize_document(
                "Document text here.", [], "output.txt"
            )

        assert result.success is True
        assert result.entities_detected == 0
        mock_write_file.assert_called_once()
        written_text = mock_write_file.call_args[0][1]
        assert written_text == "Document text here."


class TestErrorCases:
    """Error case tests for DocumentProcessor (TEST-002)."""

    @pytest.fixture
    def processor(self, tmp_path: Path) -> DocumentProcessor:
        return DocumentProcessor(
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
        )

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_encryption_error_during_processing(
        self,
        mock_open_db: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        """Test process_document with EncryptionError (database corruption)."""
        from gdpr_pseudonymizer.exceptions import EncryptionError

        mock_read_file.return_value = "Some text"
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = []
        mock_detector_class.return_value = mock_detector

        mock_open_db.side_effect = EncryptionError("Decryption failed: corrupt data")

        # Mock _log_failed_operation to avoid secondary DB access
        with patch.object(processor, "_log_failed_operation"):
            result = processor.process_document("input.txt", "output.txt")

        assert result.success is False
        assert "EncryptionError" in (result.error_message or "")

    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_save_batch_failure(
        self,
        mock_open_db: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        processor: DocumentProcessor,
    ) -> None:
        """Test process_document with save_batch database write error."""
        from gdpr_pseudonymizer.exceptions import DatabaseError

        mock_read_file.return_value = "Marie Dubois"
        entities = [
            DetectedEntity(
                text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
            ),
        ]
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_class.return_value = mock_detector

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        mock_engine = Mock()
        mock_engine.strip_titles.side_effect = lambda x: x
        mock_engine.strip_prepositions.side_effect = lambda x: x
        mock_engine.parse_full_name.return_value = ("Marie", "Dubois", False)
        mock_engine.gender_detector = None
        mock_engine.assign_compositional_pseudonym.return_value = PseudonymAssignment(
            pseudonym_full="Leia Organa",
            pseudonym_first="Leia",
            pseudonym_last="Organa",
            theme="neutral",
            exhaustion_percentage=0.1,
            is_ambiguous=False,
        )
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = None
        mock_mapping_repo.find_all.return_value = []
        mock_mapping_repo.save_batch.side_effect = DatabaseError("disk I/O error")

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
            patch.object(processor, "_log_failed_operation"),
        ):
            result = processor.process_document(
                "input.txt", "output.txt", skip_validation=True
            )

        assert result.success is False
        assert "DatabaseError" in (result.error_message or "")

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    @patch("gdpr_pseudonymizer.core.document_processor.GenderDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_keyboard_interrupt_during_validation(
        self,
        mock_open_db: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        mock_manager_class: Mock,
        mock_engine_class: Mock,
        mock_gender_class: Mock,
        mock_validation_workflow: Mock,
        processor: DocumentProcessor,
    ) -> None:
        """Test KeyboardInterrupt during validation propagates correctly."""
        mock_read_file.return_value = "Marie Dubois"
        entities = [
            DetectedEntity(
                text="Marie Dubois", entity_type="PERSON", start_pos=0, end_pos=12
            ),
        ]
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_class.return_value = mock_detector

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_open_db.return_value = mock_session

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        mock_engine = Mock()
        mock_engine.strip_titles.side_effect = lambda x: x
        mock_engine.strip_prepositions.side_effect = lambda x: x
        mock_engine_class.return_value = mock_engine

        mock_gender = Mock()
        mock_gender_class.return_value = mock_gender

        mock_mapping_repo = Mock()
        mock_mapping_repo.find_by_full_name.return_value = None
        mock_mapping_repo.find_all.return_value = []

        mock_validation_workflow.side_effect = KeyboardInterrupt()

        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository",
                return_value=mock_mapping_repo,
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.AuditRepository",
            ),
        ):
            with pytest.raises(KeyboardInterrupt):
                processor.process_document(
                    "input.txt", "output.txt", skip_validation=False
                )

    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_invalid_passphrase(
        self,
        mock_open_db: Mock,
        mock_read_file: Mock,
        processor: DocumentProcessor,
    ) -> None:
        """Test process_document with invalid passphrase (ValueError)."""
        mock_read_file.return_value = "Some text"

        mock_open_db.side_effect = ValueError("Invalid passphrase: canary mismatch")

        with patch.object(processor, "_log_failed_operation"):
            result = processor.process_document("input.txt", "output.txt")

        assert result.success is False
        assert "ValueError" in (result.error_message or "")
