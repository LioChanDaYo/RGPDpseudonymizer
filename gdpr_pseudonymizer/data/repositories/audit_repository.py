"""Audit repository for operation logging and audit trail queries.

Provides comprehensive audit logging for all pseudonymization operations,
including batch jobs, validation sessions, and individual document processing.

Note: Operations table does NOT contain sensitive entity data, so no encryption needed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from gdpr_pseudonymizer.data.models import Operation


class AuditRepository:
    """Repository for audit log operations.

    Tracks all pseudonymization operations with metadata for compliance,
    debugging, and performance analysis. No encryption required as operations
    contain metadata only, not sensitive entity information.

    Example:
        >>> repo = AuditRepository(session)
        >>> operation = Operation(
        ...     operation_type="PROCESS",
        ...     files_processed=["doc.md"],
        ...     model_name="spacy",
        ...     model_version="3.8.0",
        ...     theme_selected="star_wars",
        ...     entity_count=10,
        ...     processing_time_seconds=5.2,
        ...     success=True
        ... )
        >>> logged = repo.log_operation(operation)
    """

    def __init__(self, session: Session) -> None:
        """Initialize audit repository.

        Args:
            session: SQLAlchemy session for database operations
        """
        self._session = session

    def log_operation(self, operation: Operation) -> Operation:
        """Log operation to audit trail.

        Args:
            operation: Operation to log (with or without ID)

        Returns:
            Saved operation with generated ID and timestamp

        Example:
            >>> operation = Operation(
            ...     operation_type="BATCH",
            ...     files_processed=["doc1.md", "doc2.md"],
            ...     model_name="spacy",
            ...     model_version="3.8.0",
            ...     theme_selected="neutral",
            ...     entity_count=25,
            ...     processing_time_seconds=12.5,
            ...     success=True,
            ...     user_modifications={"entity_123": "corrected_name"}
            ... )
            >>> logged = repo.log_operation(operation)
            >>> print(logged.id)  # UUID generated
        """
        self._session.add(operation)
        self._session.commit()

        # Refresh to get generated fields (id, timestamp)
        self._session.refresh(operation)

        return operation

    def find_operations(
        self,
        operation_type: Optional[str] = None,
        success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[Operation]:
        """Query operations with optional filters.

        Args:
            operation_type: Filter by operation type (PROCESS, BATCH, VALIDATE, etc.)
            success: Filter by success status (True/False)
            start_date: Filter operations after this timestamp (inclusive)
            end_date: Filter operations before this timestamp (inclusive)
            limit: Maximum number of results to return

        Returns:
            List of operations matching filters, ordered by timestamp (newest first)

        Example:
            >>> # Get failed operations from last week
            >>> failed_ops = repo.find_operations(
            ...     success=False,
            ...     start_date=datetime.now() - timedelta(days=7)
            ... )
        """
        query = self._session.query(Operation)

        # Apply filters
        if operation_type is not None:
            query = query.filter(Operation.operation_type == operation_type)
        if success is not None:
            query = query.filter(Operation.success == success)
        if start_date is not None:
            query = query.filter(Operation.timestamp >= start_date)
        if end_date is not None:
            query = query.filter(Operation.timestamp <= end_date)

        # Order by timestamp descending (newest first)
        query = query.order_by(Operation.timestamp.desc())

        # Apply limit
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_operation_by_id(self, operation_id: str) -> Optional[Operation]:
        """Retrieve specific operation by ID.

        Args:
            operation_id: UUID of operation to retrieve

        Returns:
            Operation if found, None otherwise

        Example:
            >>> operation = repo.get_operation_by_id("abc-123-def-456")
        """
        return self._session.query(Operation).filter_by(id=operation_id).first()

    def get_total_entity_count(
        self, operation_type: Optional[str] = None, success: Optional[bool] = True
    ) -> int:
        """Get total entity count across all operations.

        Args:
            operation_type: Filter by operation type
            success: Filter by success status (defaults to True)

        Returns:
            Total number of entities processed across matching operations

        Example:
            >>> # Get total successful entities processed
            >>> total = repo.get_total_entity_count(success=True)
        """
        query = self._session.query(Operation)

        if operation_type is not None:
            query = query.filter(Operation.operation_type == operation_type)
        if success is not None:
            query = query.filter(Operation.success == success)

        operations = query.all()
        return sum(op.entity_count for op in operations)

    def get_average_processing_time(
        self, operation_type: Optional[str] = None
    ) -> float:
        """Get average processing time across operations.

        Args:
            operation_type: Filter by operation type

        Returns:
            Average processing time in seconds, or 0.0 if no operations

        Example:
            >>> # Get average time for batch operations
            >>> avg_time = repo.get_average_processing_time(operation_type="BATCH")
        """
        query = self._session.query(Operation).filter(
            Operation.success == True
        )  # noqa: E712

        if operation_type is not None:
            query = query.filter(Operation.operation_type == operation_type)

        operations = query.all()

        if not operations:
            return 0.0

        total_time = sum(op.processing_time_seconds for op in operations)
        return total_time / len(operations)

    def get_failure_rate(self, operation_type: Optional[str] = None) -> float:
        """Calculate failure rate for operations.

        Args:
            operation_type: Filter by operation type

        Returns:
            Failure rate as decimal (0.0 to 1.0), or 0.0 if no operations

        Example:
            >>> failure_rate = repo.get_failure_rate()
            >>> print(f"Failure rate: {failure_rate * 100:.2f}%")
        """
        query = self._session.query(Operation)

        if operation_type is not None:
            query = query.filter(Operation.operation_type == operation_type)

        operations = query.all()

        if not operations:
            return 0.0

        failed_count = sum(1 for op in operations if not op.success)
        return failed_count / len(operations)
