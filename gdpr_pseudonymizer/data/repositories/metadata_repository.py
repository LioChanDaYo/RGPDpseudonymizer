"""Metadata repository for configuration and file tracking.

Provides key-value storage for:
- Encryption parameters (salt, iterations, canary)
- Schema versioning
- File hash tracking for idempotency detection
- File processing timestamps
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from gdpr_pseudonymizer.data.models import Metadata


class MetadataRepository:
    """Repository for metadata key-value storage.

    Manages configuration parameters, encryption settings, and file tracking
    for idempotency detection and audit purposes.

    Example:
        >>> repo = MetadataRepository(session)
        >>> repo.set("config_key", "config_value")
        >>> value = repo.get("config_key")
        >>> repo.set_file_hash("document.md", "abc123...")
    """

    def __init__(self, session: Session) -> None:
        """Initialize metadata repository.

        Args:
            session: SQLAlchemy session for database operations
        """
        self._session = session

    def get(self, key: str) -> Optional[str]:
        """Retrieve value for given key.

        Args:
            key: Metadata key to retrieve

        Returns:
            Value associated with key, or None if key doesn't exist

        Example:
            >>> repo.get("schema_version")
            '1.0.0'
        """
        record = self._session.query(Metadata).filter_by(key=key).first()
        return record.value if record else None

    def set(self, key: str, value: str) -> None:
        """Set value for given key (upsert: insert or update).

        Args:
            key: Metadata key
            value: Value to store (will be converted to string)

        Example:
            >>> repo.set("last_backup", "2026-01-28T10:30:00Z")
        """
        record = self._session.query(Metadata).filter_by(key=key).first()

        if record:
            # Update existing record
            record.value = value
        else:
            # Insert new record
            record = Metadata(key=key, value=value)
            self._session.add(record)

        self._session.commit()

    def delete(self, key: str) -> None:
        """Delete metadata entry for given key.

        Args:
            key: Metadata key to delete

        Note:
            Silently succeeds if key doesn't exist (idempotent delete)

        Example:
            >>> repo.delete("temporary_key")
        """
        self._session.query(Metadata).filter_by(key=key).delete()
        self._session.commit()

    def set_file_hash(self, file_path: str, file_hash: str) -> None:
        """Store file hash for idempotency detection.

        Stores SHA-256 hash of processed file to detect duplicate processing.

        Args:
            file_path: Path to file (relative or absolute)
            file_hash: SHA-256 hash of file contents

        Example:
            >>> repo.set_file_hash("docs/report.md", "a3b4c5...")
        """
        key = f"file:{file_path}:hash"
        self.set(key, file_hash)

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Retrieve stored hash for file.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash of file, or None if never processed

        Example:
            >>> repo.get_file_hash("docs/report.md")
            'a3b4c5...'
        """
        key = f"file:{file_path}:hash"
        return self.get(key)

    def set_file_processed(self, file_path: str, timestamp: str) -> None:
        """Store last processed timestamp for file.

        Args:
            file_path: Path to file
            timestamp: ISO 8601 timestamp of processing

        Example:
            >>> repo.set_file_processed("docs/report.md", "2026-01-28T10:30:00Z")
        """
        key = f"file:{file_path}:processed"
        self.set(key, timestamp)

    def get_file_processed(self, file_path: str) -> Optional[str]:
        """Retrieve last processed timestamp for file.

        Args:
            file_path: Path to file

        Returns:
            ISO 8601 timestamp, or None if never processed

        Example:
            >>> repo.get_file_processed("docs/report.md")
            '2026-01-28T10:30:00Z'
        """
        key = f"file:{file_path}:processed"
        return self.get(key)

    def list_processed_files(self) -> list[str]:
        """List all files that have been processed.

        Returns:
            List of file paths that have hash entries

        Example:
            >>> repo.list_processed_files()
            ['docs/report.md', 'docs/notes.md']
        """
        # Query all metadata keys starting with "file:" and ending with ":hash"
        records = (
            self._session.query(Metadata).filter(Metadata.key.like("file:%:hash")).all()
        )

        # Extract file paths from keys (format: "file:{path}:hash")
        file_paths = []
        for record in records:
            # Remove "file:" prefix and ":hash" suffix
            path = record.key[5:-5]  # "file:" is 5 chars, ":hash" is 5 chars
            file_paths.append(path)

        return file_paths
