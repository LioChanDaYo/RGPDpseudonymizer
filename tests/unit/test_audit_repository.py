"""Unit tests for AuditRepository with comprehensive coverage.

Tests audit logging, query operations, analytics methods, and export functionality.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Operation
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository


class TestAuditRepositoryLogOperation:
    """Test suite for log_operation() method."""

    def test_log_operation_creates_entry_with_all_fields(self, tmp_path: Path) -> None:
        """Test log_operation() creates entry with all required FR12 fields."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            operation = Operation(
                operation_type="PROCESS",
                files_processed=["doc1.txt", "doc2.txt"],
                model_name="spacy",
                model_version="fr_core_news_lg-3.8.0",
                theme_selected="star_wars",
                user_modifications={"entity_123": "corrected_name"},
                entity_count=10,
                processing_time_seconds=5.2,
                success=True,
                error_message=None,
            )

            logged = repo.log_operation(operation)

            # Verify all FR12 fields present
            assert logged.id is not None
            assert logged.timestamp is not None
            assert logged.operation_type == "PROCESS"
            assert logged.files_processed == ["doc1.txt", "doc2.txt"]
            assert logged.model_name == "spacy"
            assert logged.model_version == "fr_core_news_lg-3.8.0"
            assert logged.theme_selected == "star_wars"
            assert logged.user_modifications == {"entity_123": "corrected_name"}
            assert logged.entity_count == 10
            assert logged.processing_time_seconds == 5.2
            assert logged.success is True
            assert logged.error_message is None

    def test_log_operation_auto_generates_id(self, tmp_path: Path) -> None:
        """Test log_operation() auto-generates UUID if not provided."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            operation = Operation(
                operation_type="BATCH",
                files_processed=["test.txt"],
                model_name="spacy",
                model_version="3.8.0",
                theme_selected="neutral",
                entity_count=5,
                processing_time_seconds=2.5,
                success=True,
            )

            logged = repo.log_operation(operation)

            # Verify ID generated (UUID format)
            assert logged.id is not None
            assert len(logged.id) > 0
            assert "-" in logged.id  # UUID contains hyphens

    def test_log_operation_auto_generates_timestamp(self, tmp_path: Path) -> None:
        """Test log_operation() auto-generates timestamp if not provided."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            before_time = datetime.utcnow()

            operation = Operation(
                operation_type="VALIDATE",
                files_processed=["test.txt"],
                model_name="spacy",
                model_version="3.8.0",
                theme_selected="lotr",
                entity_count=3,
                processing_time_seconds=1.8,
                success=True,
            )

            logged = repo.log_operation(operation)

            after_time = datetime.utcnow()

            # Verify timestamp generated and within expected range
            assert logged.timestamp is not None
            assert before_time <= logged.timestamp <= after_time


class TestAuditRepositoryFindOperations:
    """Test suite for find_operations() query method."""

    def test_find_operations_no_filters_returns_all(self, tmp_path: Path) -> None:
        """Test find_operations() with no filters returns all operations."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create 3 operations
            for i in range(3):
                repo.log_operation(
                    Operation(
                        operation_type="PROCESS",
                        files_processed=[f"doc{i}.txt"],
                        model_name="spacy",
                        model_version="3.8.0",
                        theme_selected="neutral",
                        entity_count=5,
                        processing_time_seconds=2.0,
                        success=True,
                    )
                )

            results = repo.find_operations()

            assert len(results) == 3

    def test_find_operations_filter_by_operation_type(self, tmp_path: Path) -> None:
        """Test filtering operations by operation_type returns correct results."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations of different types
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.5,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc2.txt", "doc3.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="star_wars",
                    entity_count=50,
                    processing_time_seconds=15.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc4.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="lotr",
                    entity_count=3,
                    processing_time_seconds=1.8,
                    success=False,
                )
            )

            # Query with filter
            process_ops = repo.find_operations(operation_type="PROCESS")

            # Verify
            assert len(process_ops) == 2
            assert all(op.operation_type == "PROCESS" for op in process_ops)

    def test_find_operations_filter_by_success_true(self, tmp_path: Path) -> None:
        """Test filtering by success=True returns only successful operations."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create successful and failed operations
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.5,
                    success=False,
                    error_message="NLP model failed",
                )
            )

            # Query successful only
            successful_ops = repo.find_operations(success=True)

            # Verify
            assert len(successful_ops) == 1
            assert successful_ops[0].success is True

    def test_find_operations_filter_by_success_false(self, tmp_path: Path) -> None:
        """Test filtering by success=False returns only failed operations."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create successful and failed operations
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=0,
                    processing_time_seconds=0.5,
                    success=False,
                    error_message="File not found",
                )
            )

            # Query failed only
            failed_ops = repo.find_operations(success=False)

            # Verify
            assert len(failed_ops) == 1
            assert failed_ops[0].success is False
            assert failed_ops[0].error_message == "File not found"

    def test_find_operations_filter_by_date_range(self, tmp_path: Path) -> None:
        """Test filtering by date range (start_date, end_date) works correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations with different timestamps
            base_time = datetime.utcnow()

            repo.log_operation(
                Operation(
                    timestamp=base_time - timedelta(days=10),
                    operation_type="PROCESS",
                    files_processed=["old.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    timestamp=base_time - timedelta(days=3),
                    operation_type="PROCESS",
                    files_processed=["recent.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=7,
                    processing_time_seconds=2.5,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    timestamp=base_time,
                    operation_type="PROCESS",
                    files_processed=["today.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )

            # Query operations from last 5 days
            start_date = base_time - timedelta(days=5)
            recent_ops = repo.find_operations(start_date=start_date)

            # Verify
            assert len(recent_ops) == 2
            assert all(op.timestamp >= start_date for op in recent_ops)

    def test_find_operations_filter_by_limit(self, tmp_path: Path) -> None:
        """Test limit parameter returns correct number of results."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create 5 operations
            for i in range(5):
                repo.log_operation(
                    Operation(
                        operation_type="PROCESS",
                        files_processed=[f"doc{i}.txt"],
                        model_name="spacy",
                        model_version="3.8.0",
                        theme_selected="neutral",
                        entity_count=5,
                        processing_time_seconds=2.0,
                        success=True,
                    )
                )

            # Query with limit=2
            limited_ops = repo.find_operations(limit=2)

            # Verify
            assert len(limited_ops) == 2

    def test_find_operations_ordering_newest_first(self, tmp_path: Path) -> None:
        """Test operations returned in descending order (newest first)."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations with explicit timestamps
            base_time = datetime.utcnow()

            first_op = repo.log_operation(
                Operation(
                    timestamp=base_time - timedelta(hours=2),
                    operation_type="PROCESS",
                    files_processed=["first.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )
            second_op = repo.log_operation(
                Operation(
                    timestamp=base_time - timedelta(hours=1),
                    operation_type="PROCESS",
                    files_processed=["second.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=7,
                    processing_time_seconds=2.5,
                    success=True,
                )
            )
            third_op = repo.log_operation(
                Operation(
                    timestamp=base_time,
                    operation_type="PROCESS",
                    files_processed=["third.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )

            # Query all
            all_ops = repo.find_operations()

            # Verify ordering (newest first)
            assert len(all_ops) == 3
            assert all_ops[0].id == third_op.id
            assert all_ops[1].id == second_op.id
            assert all_ops[2].id == first_op.id


class TestAuditRepositoryGetOperationById:
    """Test suite for get_operation_by_id() method."""

    def test_get_operation_by_id_returns_correct_operation(
        self, tmp_path: Path
    ) -> None:
        """Test get_operation_by_id() returns correct operation."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operation
            operation = repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["test.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=5.0,
                    success=True,
                )
            )

            # Retrieve by ID
            retrieved = repo.get_operation_by_id(operation.id)

            # Verify
            assert retrieved is not None
            assert retrieved.id == operation.id
            assert retrieved.operation_type == "PROCESS"
            assert retrieved.entity_count == 10

    def test_get_operation_by_id_returns_none_for_non_existent(
        self, tmp_path: Path
    ) -> None:
        """Test get_operation_by_id() returns None for non-existent ID."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Query non-existent ID
            result = repo.get_operation_by_id("non-existent-uuid-12345")

            # Verify
            assert result is None


class TestAuditRepositoryGetTotalEntityCount:
    """Test suite for get_total_entity_count() analytics method."""

    def test_get_total_entity_count_correct_sum(self, tmp_path: Path) -> None:
        """Test get_total_entity_count() returns correct sum across operations."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations with different entity counts
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=25,
                    processing_time_seconds=5.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc3.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=15,
                    processing_time_seconds=4.0,
                    success=True,
                )
            )

            # Get total
            total = repo.get_total_entity_count()

            # Verify
            assert total == 50

    def test_get_total_entity_count_with_operation_type_filter(
        self, tmp_path: Path
    ) -> None:
        """Test get_total_entity_count() with operation_type filter."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations of different types
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc2.txt", "doc3.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="star_wars",
                    entity_count=100,
                    processing_time_seconds=20.0,
                    success=True,
                )
            )

            # Get total for PROCESS only
            process_total = repo.get_total_entity_count(operation_type="PROCESS")

            # Verify
            assert process_total == 10

    def test_get_total_entity_count_with_success_filter(self, tmp_path: Path) -> None:
        """Test get_total_entity_count() with success filter."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create successful and failed operations
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=False,
                    error_message="Failed",
                )
            )

            # Get total for successful only (default)
            successful_total = repo.get_total_entity_count(success=True)

            # Verify
            assert successful_total == 10


class TestAuditRepositoryGetAverageProcessingTime:
    """Test suite for get_average_processing_time() analytics method."""

    def test_get_average_processing_time_correct_calculation(
        self, tmp_path: Path
    ) -> None:
        """Test get_average_processing_time() returns correct average."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations with different processing times
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=15,
                    processing_time_seconds=4.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc3.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=20,
                    processing_time_seconds=6.0,
                    success=True,
                )
            )

            # Get average (2.0 + 4.0 + 6.0) / 3 = 4.0
            avg_time = repo.get_average_processing_time()

            # Verify
            assert avg_time == 4.0

    def test_get_average_processing_time_with_operation_type_filter(
        self, tmp_path: Path
    ) -> None:
        """Test get_average_processing_time() with operation_type filter."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operations of different types
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc2.txt", "doc3.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="star_wars",
                    entity_count=100,
                    processing_time_seconds=20.0,
                    success=True,
                )
            )

            # Get average for BATCH only
            batch_avg = repo.get_average_processing_time(operation_type="BATCH")

            # Verify
            assert batch_avg == 20.0

    def test_get_average_processing_time_returns_zero_for_no_operations(
        self, tmp_path: Path
    ) -> None:
        """Test get_average_processing_time() returns 0.0 for no operations."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # No operations created
            avg_time = repo.get_average_processing_time()

            # Verify
            assert avg_time == 0.0


class TestAuditRepositoryGetFailureRate:
    """Test suite for get_failure_rate() analytics method."""

    def test_get_failure_rate_correct_percentage(self, tmp_path: Path) -> None:
        """Test get_failure_rate() returns correct percentage calculation."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create 3 successful, 1 failed = 25% failure rate
            for _ in range(3):
                repo.log_operation(
                    Operation(
                        operation_type="PROCESS",
                        files_processed=["doc.txt"],
                        model_name="spacy",
                        model_version="3.8.0",
                        theme_selected="neutral",
                        entity_count=10,
                        processing_time_seconds=3.0,
                        success=True,
                    )
                )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["failed.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=0,
                    processing_time_seconds=1.0,
                    success=False,
                    error_message="Error occurred",
                )
            )

            # Get failure rate (1 failed / 4 total = 0.25)
            failure_rate = repo.get_failure_rate()

            # Verify
            assert failure_rate == 0.25

    def test_get_failure_rate_with_operation_type_filter(self, tmp_path: Path) -> None:
        """Test get_failure_rate() with operation_type filter."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create PROCESS operations with 50% failure rate
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=0,
                    processing_time_seconds=1.0,
                    success=False,
                    error_message="Failed",
                )
            )

            # Create BATCH operation (100% success)
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["batch.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="star_wars",
                    entity_count=50,
                    processing_time_seconds=10.0,
                    success=True,
                )
            )

            # Get failure rate for PROCESS only (1 failed / 2 total = 0.5)
            process_failure_rate = repo.get_failure_rate(operation_type="PROCESS")

            # Verify
            assert process_failure_rate == 0.5

    def test_get_failure_rate_returns_zero_for_no_operations(
        self, tmp_path: Path
    ) -> None:
        """Test get_failure_rate() returns 0.0 for no operations."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # No operations created
            failure_rate = repo.get_failure_rate()

            # Verify
            assert failure_rate == 0.0


class TestAuditRepositoryExportToJson:
    """Test suite for export_to_json() export functionality."""

    def test_export_to_json_creates_valid_json_file(self, tmp_path: Path) -> None:
        """Test export_to_json() creates valid JSON file with correct format."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create test operation
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["test.txt"],
                    model_name="spacy",
                    model_version="fr_core_news_lg-3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=5.2,
                    success=True,
                )
            )

            # Export to JSON
            output_path = tmp_path / "audit_export.json"
            repo.export_to_json(str(output_path))

            # Verify file exists and contains valid JSON
            assert output_path.exists()
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)

            # Verify structure
            assert "export_metadata" in data
            assert "operations" in data
            assert len(data["operations"]) == 1
            assert data["operations"][0]["operation_type"] == "PROCESS"
            assert data["operations"][0]["entity_count"] == 10

            # Verify metadata
            assert data["export_metadata"]["schema_version"] == "1.0.0"
            assert "export_timestamp" in data["export_metadata"]
            assert data["export_metadata"]["total_results"] == 1

    def test_export_to_json_with_filters_applied(self, tmp_path: Path) -> None:
        """Test export_to_json() with filters applied."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create multiple operations
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="star_wars",
                    entity_count=50,
                    processing_time_seconds=15.0,
                    success=True,
                )
            )

            # Export with filter
            output_path = tmp_path / "filtered_export.json"
            repo.export_to_json(str(output_path), operation_type="PROCESS")

            # Verify
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)

            assert len(data["operations"]) == 1
            assert data["operations"][0]["operation_type"] == "PROCESS"
            assert (
                data["export_metadata"]["filters_applied"]["operation_type"]
                == "PROCESS"
            )

    def test_export_to_json_handles_empty_results(self, tmp_path: Path) -> None:
        """Test export_to_json() handles empty results gracefully."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # No operations created
            output_path = tmp_path / "empty_export.json"
            repo.export_to_json(str(output_path))

            # Verify file created with empty operations
            assert output_path.exists()
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)

            assert data["operations"] == []
            assert data["export_metadata"]["total_results"] == 0

    def test_export_to_json_datetime_serialization_iso8601(
        self, tmp_path: Path
    ) -> None:
        """Test export_to_json() uses ISO 8601 format for datetime serialization."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operation with explicit timestamp
            timestamp = datetime(2026, 1, 28, 14, 30, 0)
            repo.log_operation(
                Operation(
                    timestamp=timestamp,
                    operation_type="PROCESS",
                    files_processed=["test.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )

            # Export
            output_path = tmp_path / "datetime_export.json"
            repo.export_to_json(str(output_path))

            # Verify datetime format (ISO 8601)
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)

            timestamp_str = data["operations"][0]["timestamp"]
            assert "2026-01-28" in timestamp_str
            assert "T" in timestamp_str  # ISO 8601 separator

    def test_export_to_json_file_io_error_raises_exception(
        self, tmp_path: Path
    ) -> None:
        """Test export_to_json() raises OSError for file I/O errors."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operation
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["test.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )

            # Mock Path.open to raise PermissionError
            output_path = tmp_path / "export.json"
            with patch(
                "pathlib.Path.open", side_effect=PermissionError("Access denied")
            ):
                with pytest.raises(OSError, match="Failed to write JSON export"):
                    repo.export_to_json(str(output_path))


class TestAuditRepositoryExportToCsv:
    """Test suite for export_to_csv() export functionality."""

    def test_export_to_csv_creates_valid_csv_file(self, tmp_path: Path) -> None:
        """Test export_to_csv() creates valid CSV file with header row."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create test operation
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc1.txt", "doc2.txt"],
                    model_name="spacy",
                    model_version="fr_core_news_lg-3.8.0",
                    theme_selected="star_wars",
                    entity_count=25,
                    processing_time_seconds=12.5,
                    success=True,
                )
            )

            # Export to CSV
            output_path = tmp_path / "audit_export.csv"
            repo.export_to_csv(str(output_path))

            # Verify file exists and contains valid CSV
            assert output_path.exists()
            with open(output_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Verify header and content
            assert len(rows) == 1
            assert "operation_type" in rows[0]
            assert rows[0]["operation_type"] == "BATCH"
            assert rows[0]["entity_count"] == "25"

    def test_export_to_csv_with_filters_applied(self, tmp_path: Path) -> None:
        """Test export_to_csv() with filters applied."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create multiple operations
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=10,
                    processing_time_seconds=3.0,
                    success=True,
                )
            )
            repo.log_operation(
                Operation(
                    operation_type="BATCH",
                    files_processed=["doc2.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="star_wars",
                    entity_count=50,
                    processing_time_seconds=15.0,
                    success=False,
                    error_message="Error",
                )
            )

            # Export with filter
            output_path = tmp_path / "filtered_export.csv"
            repo.export_to_csv(str(output_path), success=False)

            # Verify
            with open(output_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["success"] == "False"
            assert rows[0]["error_message"] == "Error"

    def test_export_to_csv_handles_empty_results(self, tmp_path: Path) -> None:
        """Test export_to_csv() handles empty results gracefully."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # No operations created
            output_path = tmp_path / "empty_export.csv"
            repo.export_to_csv(str(output_path))

            # Verify file created with header only
            assert output_path.exists()
            with open(output_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 0  # No data rows, only header

    def test_export_to_csv_header_row_present(self, tmp_path: Path) -> None:
        """Test export_to_csv() includes CSV header row with all fields."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operation
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["test.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )

            # Export
            output_path = tmp_path / "header_test.csv"
            repo.export_to_csv(str(output_path))

            # Verify header
            with open(output_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

            # Check all expected headers present
            expected_headers = [
                "id",
                "timestamp",
                "operation_type",
                "files_processed",
                "model_name",
                "model_version",
                "theme_selected",
                "user_modifications",
                "entity_count",
                "processing_time_seconds",
                "success",
                "error_message",
            ]
            assert headers == expected_headers

    def test_export_to_csv_json_fields_flattened_correctly(
        self, tmp_path: Path
    ) -> None:
        """Test export_to_csv() flattens JSON fields correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operation with JSON fields
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["doc1.txt", "doc2.txt", "doc3.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    user_modifications={"entity_123": "corrected_name"},
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )

            # Export
            output_path = tmp_path / "flatten_test.csv"
            repo.export_to_csv(str(output_path))

            # Verify flattening
            with open(output_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # files_processed should be comma-separated string
            assert rows[0]["files_processed"] == "doc1.txt,doc2.txt,doc3.txt"

            # user_modifications should be JSON string
            assert "entity_123" in rows[0]["user_modifications"]
            assert "corrected_name" in rows[0]["user_modifications"]

    def test_export_to_csv_file_io_error_raises_exception(self, tmp_path: Path) -> None:
        """Test export_to_csv() raises OSError for file I/O errors."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = AuditRepository(db_session.session)

            # Create operation
            repo.log_operation(
                Operation(
                    operation_type="PROCESS",
                    files_processed=["test.txt"],
                    model_name="spacy",
                    model_version="3.8.0",
                    theme_selected="neutral",
                    entity_count=5,
                    processing_time_seconds=2.0,
                    success=True,
                )
            )

            # Mock Path.open to raise PermissionError
            output_path = tmp_path / "export.csv"
            with patch(
                "pathlib.Path.open", side_effect=PermissionError("Access denied")
            ):
                with pytest.raises(OSError, match="Failed to write CSV export"):
                    repo.export_to_csv(str(output_path))
