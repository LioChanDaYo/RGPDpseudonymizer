"""Validation workflow orchestration.

This module coordinates the human-in-the-loop validation process,
managing the flow between entity detection, user review, and
pseudonym assignment.

Full implementation in Story 1.7.
"""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import ValidationSession


def create_validation_session(
    document_path: str, document_text: str, entities: list[DetectedEntity]
) -> ValidationSession:
    """Create validation session from detected entities (stub for Story 1.7).

    Args:
        document_path: Path to document being validated
        document_text: Full document text
        entities: List of entities detected by NLP engine

    Returns:
        Initialized ValidationSession
    """
    # Stub: Full implementation in Story 1.7
    session = ValidationSession(
        document_path=document_path, document_text=document_text
    )
    for entity in entities:
        session.add_entity(entity)
    return session


def run_validation_workflow(session: ValidationSession) -> None:
    """Execute interactive validation workflow (stub for Story 1.7).

    Args:
        session: ValidationSession to process
    """
    # Stub: Full implementation in Story 1.7
    pass
