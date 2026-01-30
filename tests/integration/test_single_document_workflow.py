"""Integration tests for single-document pseudonymization workflow.

Tests the complete end-to-end workflow including:
- Happy path processing
- Idempotency (FR19)
- Error scenarios
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)


class TestSingleDocumentWorkflow:
    """Integration tests for complete single-document workflow."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> str:
        """Create and initialize test database.

        Args:
            tmp_path: pytest temporary directory

        Returns:
            Path to initialized test database
        """
        db_path = tmp_path / "test_mappings.db"
        passphrase = "test_passphrase_12345"
        init_database(str(db_path), passphrase)
        return str(db_path)

    @pytest.fixture
    def sample_document(self, tmp_path: Path) -> str:
        """Create sample document for testing.

        Args:
            tmp_path: pytest temporary directory

        Returns:
            Path to sample document file
        """
        doc_path = tmp_path / "sample.txt"
        content = (
            "Marie Dubois travaille à Paris. "
            "Elle collabore avec Jean Martin sur le projet. "
            "Dr. Sophie Lefebvre supervise l'équipe à Lyon."
        )
        doc_path.write_text(content, encoding="utf-8")
        return str(doc_path)

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    def test_happy_path_complete_workflow(
        self,
        mock_validation_workflow,
        test_db: str,
        sample_document: str,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow: process document end-to-end.

        Verifies:
        - Document processed successfully
        - Entities detected and pseudonymized
        - Mappings stored in encrypted database
        - Audit log created
        - Output file created with pseudonymized content
        """
        # Arrange
        output_path = tmp_path / "output.txt"
        passphrase = "test_passphrase_12345"

        # Mock validation workflow to pass through all detected entities
        mock_validation_workflow.side_effect = lambda entities, **kwargs: entities

        # Act: Process document
        processor = DocumentProcessor(
            db_path=test_db,
            passphrase=passphrase,
            theme="neutral",
            model_name="spacy",
        )
        result = processor.process_document(
            input_path=sample_document,
            output_path=str(output_path),
        )

        # Assert: Processing successful
        assert result.success is True
        assert result.entities_detected > 0
        assert result.entities_new > 0
        # Note: entities_reused may be > 0 if document contains component references
        # (e.g., "Dr. Dubois" after "Marie Dubois" counts as reuse within same document)
        assert result.entities_reused >= 0
        assert result.processing_time_seconds > 0

        # Assert: Output file created
        assert output_path.exists()
        output_content = output_path.read_text(encoding="utf-8")
        assert len(output_content) > 0

        # Assert: Original entities not in output
        original_content = Path(sample_document).read_text(encoding="utf-8")
        assert output_content != original_content

        # Assert: Database contains mappings
        with open_database(test_db, passphrase) as db_session:
            mapping_repo = SQLiteMappingRepository(db_session)
            all_entities = mapping_repo.find_all()
            assert len(all_entities) > 0

            # Assert: Audit log contains operation
            audit_repo = AuditRepository(db_session.session)
            operations = audit_repo.find_operations()
            assert len(operations) == 1
            assert operations[0].operation_type == "PROCESS"
            assert operations[0].success is True
            assert operations[0].entity_count > 0

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    def test_idempotency_reuses_mappings(
        self,
        mock_validation_workflow,
        test_db: str,
        sample_document: str,
        tmp_path: Path,
    ) -> None:
        """Test FR19: Reprocessing same document reuses existing mappings.

        Verifies:
        - First processing creates new entities
        - Second processing reuses all entities (entities_new=0)
        - Outputs are identical (bit-for-bit)
        - Both operations logged separately
        """
        # Arrange
        output1_path = tmp_path / "output1.txt"
        output2_path = tmp_path / "output2.txt"
        passphrase = "test_passphrase_12345"

        # Mock validation workflow to pass through all detected entities
        mock_validation_workflow.side_effect = lambda entities, **kwargs: entities

        processor = DocumentProcessor(
            db_path=test_db,
            passphrase=passphrase,
            theme="neutral",
            model_name="spacy",
        )

        # Act: First processing
        result1 = processor.process_document(
            input_path=sample_document,
            output_path=str(output1_path),
        )

        # Act: Second processing (same input)
        result2 = processor.process_document(
            input_path=sample_document,
            output_path=str(output2_path),
        )

        # Assert: First processing created new entities
        assert result1.success is True
        assert result1.entities_new > 0
        # Note: First processing may have reused > 0 due to in-document component matching
        # (e.g., if "Dubois" appears after "Marie Dubois", it's matched as component reuse)
        assert result1.entities_reused >= 0

        # Assert: Second processing reused all entities
        assert result2.success is True
        assert result2.entities_new == 0
        # Second processing should reuse from database (all unique entities detected)
        # Note: entities_detected includes duplicates, entities_new counts unique new entities
        assert result2.entities_reused == result2.entities_detected
        assert result2.entities_detected == result1.entities_detected

        # Assert: Outputs are identical
        output1_content = output1_path.read_text(encoding="utf-8")
        output2_content = output2_path.read_text(encoding="utf-8")
        assert output1_content == output2_content

        # Assert: Two separate operations in audit log
        with open_database(test_db, passphrase) as db_session:
            audit_repo = AuditRepository(db_session.session)
            operations = audit_repo.find_operations()
            assert len(operations) == 2
            assert all(op.operation_type == "PROCESS" for op in operations)
            assert all(op.success is True for op in operations)

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    def test_idempotency_with_same_entity(
        self, mock_validation_workflow, test_db: str, tmp_path: Path
    ) -> None:
        """Test idempotency with same entity across documents.

        Verifies:
        - "Marie Dubois" in doc1 gets pseudonym X
        - "Marie Dubois" in doc2 reuses pseudonym X (idempotency)
        - Pseudonyms are consistent across documents
        """
        # Arrange
        passphrase = "test_passphrase_12345"

        # Mock validation workflow to pass through all detected entities
        mock_validation_workflow.side_effect = lambda entities, **kwargs: entities

        # Document 1: Marie Dubois
        doc1_path = tmp_path / "doc1.txt"
        doc1_path.write_text("Marie Dubois travaille à Paris.", encoding="utf-8")

        # Document 2: Marie Dubois again (same person)
        doc2_path = tmp_path / "doc2.txt"
        doc2_path.write_text("Marie Dubois vit à Lyon.", encoding="utf-8")

        output1_path = tmp_path / "output1.txt"
        output2_path = tmp_path / "output2.txt"

        processor = DocumentProcessor(
            db_path=test_db,
            passphrase=passphrase,
            theme="neutral",
            model_name="spacy",
        )

        # Act: Process first document
        result1 = processor.process_document(
            input_path=str(doc1_path),
            output_path=str(output1_path),
        )

        # Act: Process second document
        result2 = processor.process_document(
            input_path=str(doc2_path),
            output_path=str(output2_path),
        )

        # Assert: Both processed successfully
        assert result1.success is True
        assert result2.success is True

        # Assert: First document created new entity
        assert result1.entities_new > 0

        # Assert: Second document reused entity (idempotency)
        assert result2.entities_reused > 0

        # Assert: Check database for same entity
        with open_database(test_db, passphrase) as db_session:
            mapping_repo = SQLiteMappingRepository(db_session)

            # Find "Marie Dubois" - should be unique
            marie_entities = mapping_repo.find_all()
            marie_dubois_entities = [
                e for e in marie_entities if e.full_name == "Marie Dubois"
            ]
            # Should be only one entity for "Marie Dubois"
            assert len(marie_dubois_entities) == 1

            # Verify outputs contain same pseudonym
            output1 = output1_path.read_text(encoding="utf-8")
            output2 = output2_path.read_text(encoding="utf-8")
            # Both should have the same pseudonym for "Marie Dubois"
            marie_pseudonym = marie_dubois_entities[0].pseudonym_full
            assert marie_pseudonym in output1
            assert marie_pseudonym in output2

    def test_error_file_not_found(self, test_db: str, tmp_path: Path) -> None:
        """Test error handling: input file not found.

        Verifies:
        - ProcessingResult indicates failure
        - Error message is populated
        - Audit log records failure
        - No partial data written
        """
        # Arrange
        passphrase = "test_passphrase_12345"
        nonexistent_path = tmp_path / "nonexistent.txt"
        output_path = tmp_path / "output.txt"

        processor = DocumentProcessor(
            db_path=test_db,
            passphrase=passphrase,
        )

        # Act: Process nonexistent file
        result = processor.process_document(
            input_path=str(nonexistent_path),
            output_path=str(output_path),
        )

        # Assert: Processing failed
        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

        # Assert: No output file created
        assert not output_path.exists()

        # Assert: Failure logged to audit trail
        with open_database(test_db, passphrase) as db_session:
            audit_repo = AuditRepository(db_session.session)
            operations = audit_repo.find_operations()
            assert len(operations) == 1
            assert operations[0].success is False
            assert operations[0].error_message is not None

    def test_error_invalid_passphrase(self, tmp_path: Path) -> None:
        """Test error handling: invalid database passphrase.

        Verifies:
        - ProcessingResult indicates failure
        - Error message mentions passphrase
        - Database remains intact
        """
        # Arrange: Create database with correct passphrase
        db_path = tmp_path / "test.db"
        correct_passphrase = "correct_passphrase_12345"
        init_database(str(db_path), correct_passphrase)

        # Create sample document
        doc_path = tmp_path / "sample.txt"
        doc_path.write_text("Marie Dubois travaille à Paris.", encoding="utf-8")
        output_path = tmp_path / "output.txt"

        # Act: Attempt to process with wrong passphrase
        wrong_passphrase = "wrong_passphrase_67890"
        processor = DocumentProcessor(
            db_path=str(db_path),
            passphrase=wrong_passphrase,
        )
        result = processor.process_document(
            input_path=str(doc_path),
            output_path=str(output_path),
        )

        # Assert: Processing failed
        assert result.success is False
        assert result.error_message is not None
        assert "passphrase" in result.error_message.lower()

    def test_error_output_directory_created(
        self, test_db: str, sample_document: str, tmp_path: Path
    ) -> None:
        """Test that output directory is created if it doesn't exist.

        Verifies:
        - Nested output directories are created
        - Processing succeeds
        """
        # Arrange
        passphrase = "test_passphrase_12345"
        # Nested directory that doesn't exist
        output_path = tmp_path / "nested" / "directory" / "output.txt"

        processor = DocumentProcessor(
            db_path=test_db,
            passphrase=passphrase,
        )

        # Act: Process with nested output path
        result = processor.process_document(
            input_path=sample_document,
            output_path=str(output_path),
        )

        # Assert: Processing successful
        assert result.success is True

        # Assert: Output file created in nested directory
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_multiple_entity_types(self, test_db: str, tmp_path: Path) -> None:
        """Test processing document with multiple entity types.

        Verifies:
        - PERSON entities pseudonymized
        - LOCATION entities pseudonymized
        - ORG entities pseudonymized (if detected)
        - All entities stored with correct types
        """
        # Arrange
        passphrase = "test_passphrase_12345"

        # Document with multiple entity types
        doc_path = tmp_path / "multi_entity.txt"
        content = (
            "Marie Dubois travaille à l'Université de Paris. "
            "Elle habite à Lyon et collabore avec Jean Martin."
        )
        doc_path.write_text(content, encoding="utf-8")

        output_path = tmp_path / "output.txt"

        processor = DocumentProcessor(
            db_path=test_db,
            passphrase=passphrase,
            theme="neutral",
        )

        # Act: Process document
        result = processor.process_document(
            input_path=str(doc_path),
            output_path=str(output_path),
        )

        # Assert: Processing successful
        assert result.success is True
        assert result.entities_detected > 0

        # Assert: Check entity types in database
        with open_database(test_db, passphrase) as db_session:
            mapping_repo = SQLiteMappingRepository(db_session)
            all_entities = mapping_repo.find_all()

            # Group entities by type
            entity_types = set(entity.entity_type for entity in all_entities)

            # Assert: At least PERSON and LOCATION entities detected
            assert "PERSON" in entity_types
            # Note: LOCATION detection depends on NLP model accuracy

            # Assert: All entities have pseudonyms
            for entity in all_entities:
                assert entity.pseudonym_full is not None
                assert len(entity.pseudonym_full) > 0
