"""SQLAlchemy data models for entity mapping and audit logging."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Entity(Base):
    """Entity mapping table for storing pseudonymized name mappings.

    This table stores the mapping between real entities (names, locations, organizations)
    and their assigned pseudonyms. All sensitive fields will be encrypted at rest.
    """

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # PERSON, LOCATION, ORG

    # Encrypted fields (encryption logic in Epic 2)
    first_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # PERSON only
    last_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # PERSON only
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    pseudonym_first: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pseudonym_last: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pseudonym_full: Mapped[str] = mapped_column(String, nullable=False)

    # Metadata fields
    first_seen_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # male/female/neutral/unknown
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    theme: Mapped[str] = mapped_column(String, nullable=False)  # neutral/star_wars/lotr

    # Validation support fields
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ambiguity_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Operation(Base):
    """Operation audit log table for tracking all pseudonymization operations.

    This table maintains a comprehensive audit trail of all processing operations,
    including batch jobs, validation sessions, and individual document processing.
    """

    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    operation_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # PROCESS, BATCH, VALIDATE, etc.

    # JSON fields
    files_processed: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    user_modifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # Audit fields
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    theme_selected: Mapped[str] = mapped_column(String, nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Metadata(Base):
    """Metadata key-value store for configuration and encryption parameters.

    Critical keys:
    - passphrase_canary: Encrypted verification string
    - encryption_salt: Salt for PBKDF2 key derivation
    - kdf_iterations: PBKDF2 iteration count (default 100,000)
    - schema_version: Database schema version
    - file:{path}:hash: SHA-256 hash for idempotency detection
    - file:{path}:processed: Last processed timestamp
    """

    __tablename__ = "metadata"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)  # JSON-serialized
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
