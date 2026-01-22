"""Process command for single document pseudonymization.

This module implements the `process` command that performs spaCy-based
pseudonymization on a single document with optional validation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from gdpr_pseudonymizer.cli.formatters import (
    format_error_message,
    format_info_message,
    format_success_message,
    format_validation_cancelled,
)
from gdpr_pseudonymizer.cli.naive_data import NAIVE_ENTITIES
from gdpr_pseudonymizer.exceptions import FileProcessingError, ValidationError
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.utils.file_handler import read_file, write_file
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger
from gdpr_pseudonymizer.validation.workflow import run_validation_workflow

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Pseudonym mapping cache (entity_text -> pseudonym)
_pseudonym_cache: dict[str, str] = {}

# Build pseudonym pools by type from naive data
_pseudonym_pools: dict[str, list[str]] = {
    "PERSON": [],
    "LOCATION": [],
    "ORG": [],
}

# Initialize pseudonym pools from naive data
for entity_text, entity_type, pseudonym in NAIVE_ENTITIES:
    if (
        entity_type in _pseudonym_pools
        and pseudonym not in _pseudonym_pools[entity_type]
    ):
        _pseudonym_pools[entity_type].append(pseudonym)


def assign_pseudonym(entity: DetectedEntity) -> str:
    """Assign a pseudonym to a detected entity.

    Uses consistent mapping: same entity text always gets the same pseudonym.
    Pseudonyms are assigned from the pool for the entity's type.

    Args:
        entity: Detected entity to assign pseudonym to

    Returns:
        Assigned pseudonym string

    Examples:
        >>> entity = DetectedEntity("Marie Dubois", "PERSON", 0, 12)
        >>> assign_pseudonym(entity)
        "Leia Organa"
        >>> # Same entity always gets same pseudonym
        >>> assign_pseudonym(entity)
        "Leia Organa"
    """
    # Check if we've already assigned a pseudonym for this entity
    if entity.text in _pseudonym_cache:
        return _pseudonym_cache[entity.text]

    # Get available pseudonyms for this entity type
    available_pseudonyms = _pseudonym_pools.get(entity.entity_type, [])

    if not available_pseudonyms:
        # Fallback if no pseudonyms available for this type
        pseudonym = f"[{entity.entity_type}_{len(_pseudonym_cache) + 1}]"
    else:
        # Assign next available pseudonym (round-robin)
        # Count how many pseudonyms of this type we've already assigned
        assigned_count = sum(
            1 for k, v in _pseudonym_cache.items() if v in available_pseudonyms
        )
        pseudonym = available_pseudonyms[assigned_count % len(available_pseudonyms)]

    # Cache the assignment
    _pseudonym_cache[entity.text] = pseudonym
    return pseudonym


def apply_pseudonymization(text: str, entities: list[DetectedEntity]) -> str:
    """Apply pseudonymization to text by replacing detected entities.

    Replaces entities from end to start to preserve character positions.

    Args:
        text: Original document text
        entities: List of detected entities to replace

    Returns:
        Pseudonymized text with entities replaced

    Examples:
        >>> text = "Marie Dubois travaille à Paris."
        >>> entities = [
        ...     DetectedEntity("Marie Dubois", "PERSON", 0, 12),
        ...     DetectedEntity("Paris", "LOCATION", 26, 31),
        ... ]
        >>> apply_pseudonymization(text, entities)
        "Leia Organa travaille à Coruscant."
    """
    if not entities:
        return text

    # Sort entities by start position (descending) to replace from end to start
    sorted_entities = sorted(entities, key=lambda e: e.start_pos, reverse=True)

    result = text
    for entity in sorted_entities:
        pseudonym = assign_pseudonym(entity)
        # Replace entity text with pseudonym
        result = result[: entity.start_pos] + pseudonym + result[entity.end_pos :]

    return result


def convert_entities_for_validation(
    entities: list[DetectedEntity],
) -> list[tuple[str, str, int, int, str]]:
    """Convert DetectedEntity objects to validation stub format.

    Args:
        entities: List of DetectedEntity objects from spaCy detection

    Returns:
        List of tuples (entity_text, entity_type, start_pos, end_pos, pseudonym)
        compatible with validation_stub.present_entities_for_validation()

    Examples:
        >>> entities = [DetectedEntity("Marie", "PERSON", 0, 5)]
        >>> convert_entities_for_validation(entities)
        [("Marie", "PERSON", 0, 5, "Leia Organa")]
    """
    return [
        (
            entity.text,
            entity.entity_type,
            entity.start_pos,
            entity.end_pos,
            assign_pseudonym(entity),
        )
        for entity in entities
    ]


def process_command(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Input file path (.txt or .md)",
    ),
    output_file: Optional[Path] = typer.Argument(
        None,
        help="Output file path (default: <input>_pseudonymized.txt)",
    ),
) -> None:
    """Process a single document and apply hybrid (spaCy + regex) pseudonymization.

    This command reads a text document, detects entities using hybrid detection
    (spaCy NLP + regex patterns), presents them for mandatory validation, and
    writes the pseudonymized output.

    Validation is required for accuracy assurance. All detected entities must be reviewed.

    Args:
        input_file: Path to input document (.txt or .md)
        output_file: Path to output document (optional)

    Examples:
        gdpr-pseudo process interview.txt
        gdpr-pseudo process interview.txt output.txt
    """
    try:
        # Validate file extension
        allowed_extensions = [".txt", ".md"]
        if input_file.suffix.lower() not in allowed_extensions:
            format_error_message(
                "Invalid File Format",
                f"File extension '{input_file.suffix}' is not supported.",
                f"Supported formats: {', '.join(allowed_extensions)}",
            )
            sys.exit(1)

        # Generate default output filename if not provided
        if output_file is None:
            output_file = input_file.parent / f"{input_file.stem}_pseudonymized.txt"

        # Log processing start
        logger.info(
            "processing_started",
            input_file=str(input_file),
            output_file=str(output_file),
            validation_enabled=True,  # Validation is mandatory
        )

        format_info_message(f"Reading input file: {input_file}")

        # Read input file
        content = read_file(str(input_file))

        # Initialize hybrid detector (spaCy + regex)
        format_info_message(
            "Loading hybrid detection model (spaCy + regex patterns)..."
        )
        try:
            detector = HybridDetector()
        except OSError as e:
            format_error_message(
                "NLP Model Not Found",
                str(e),
                "Run: python scripts/install_spacy_model.py",
            )
            sys.exit(2)

        # Detect entities using hybrid approach
        format_info_message("Detecting entities with hybrid detector...")
        try:
            entities = detector.detect_entities(content)
        except ValueError as e:
            format_error_message(
                "Invalid Input",
                str(e),
                "Ensure file contains valid text content.",
            )
            sys.exit(1)
        except RuntimeError as e:
            format_error_message(
                "Entity Detection Failed",
                str(e),
                "Check input file encoding and format.",
            )
            sys.exit(2)

        # Count unique entities
        unique_entities = len(set(entity.text for entity in entities))

        # Log entities detected
        logger.info(
            "entities_detected",
            count=len(entities),
            unique_count=unique_entities,
            types=list(set(entity.entity_type for entity in entities)),
        )

        # MANDATORY VALIDATION WORKFLOW (Story 1.7)
        format_info_message("Starting validation workflow...")
        try:
            validated_entities = run_validation_workflow(
                entities=entities,
                document_text=content,
                document_path=str(input_file),
                pseudonym_assigner=assign_pseudonym,
            )
        except KeyboardInterrupt:
            format_validation_cancelled()
            logger.info("processing_cancelled", reason="user_quit_validation")
            sys.exit(0)

        # Log validation results
        logger.info(
            "validation_complete",
            original_count=len(entities),
            validated_count=len(validated_entities),
        )

        # Apply pseudonymization with validated entities
        format_info_message("Applying pseudonymization...")
        pseudonymized_content = apply_pseudonymization(content, validated_entities)

        # Write output file
        format_info_message(f"Writing output file: {output_file}")
        write_file(str(output_file), pseudonymized_content)

        # Log completion
        logger.info(
            "processing_complete",
            output_file=str(output_file),
            entities_replaced=len(validated_entities),
        )

        # Display success message
        format_success_message(
            input_file=input_file,
            output_file=output_file,
            entities_detected=len(entities),
            entities_replaced=len(validated_entities),
            unique_entities=len(set(e.text for e in validated_entities)),
        )

    except FileProcessingError as e:
        # Handle file I/O errors
        logger.error("file_processing_error", error=str(e))
        format_error_message(
            "File Processing Error",
            str(e),
            "Check file path and permissions.",
        )
        sys.exit(1)

    except ValidationError as e:
        # Handle validation errors
        logger.error("validation_error", error=str(e))
        format_error_message(
            "Validation Error",
            str(e),
            "Check validation workflow and try again.",
        )
        sys.exit(1)

    except Exception as e:
        # Handle unexpected errors
        logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)
