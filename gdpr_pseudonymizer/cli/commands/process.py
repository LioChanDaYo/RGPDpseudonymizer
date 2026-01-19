"""Process command for single document pseudonymization.

This module implements the `process` command that performs naive
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
from gdpr_pseudonymizer.cli.validation_stub import (
    confirm_processing,
    present_entities_for_validation,
)
from gdpr_pseudonymizer.core.naive_processor import (
    apply_naive_replacements,
    detect_naive_entities,
)
from gdpr_pseudonymizer.exceptions import FileProcessingError, ValidationError
from gdpr_pseudonymizer.utils.file_handler import read_file, write_file
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


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
    validate: bool = typer.Option(
        False,
        "--validate",
        help="Enable validation mode (review entities before processing)",
    ),
) -> None:
    """Process a single document and apply naive pseudonymization.

    This command reads a text document, detects entities using a hardcoded list,
    optionally presents them for validation, and writes the pseudonymized output.

    Args:
        input_file: Path to input document (.txt or .md)
        output_file: Path to output document (optional)
        validate: Enable validation mode for entity review

    Examples:
        gdpr-pseudo process interview.txt
        gdpr-pseudo process interview.txt output.txt --validate
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
            validation_enabled=validate,
        )

        format_info_message(f"Reading input file: {input_file}")

        # Read input file
        content = read_file(str(input_file))

        # Detect entities
        format_info_message("Detecting entities...")
        entities = detect_naive_entities(content)

        # Count unique entities
        unique_entities = len(set(entity[0] for entity in entities))

        # Log entities detected
        logger.info(
            "entities_detected",
            count=len(entities),
            unique_count=unique_entities,
            types=list(set(entity[1] for entity in entities)),
        )

        # Validation mode: present entities and confirm
        if validate:
            present_entities_for_validation(entities)

            if not confirm_processing():
                format_validation_cancelled()
                logger.info("processing_cancelled", reason="user_rejected")
                sys.exit(0)

        # Apply replacements
        format_info_message("Applying pseudonymization...")
        pseudonymized_content = apply_naive_replacements(content, entities)

        # Write output file
        format_info_message(f"Writing output file: {output_file}")
        write_file(str(output_file), pseudonymized_content)

        # Log completion
        logger.info(
            "processing_complete",
            output_file=str(output_file),
            entities_replaced=len(entities),
        )

        # Display success message
        format_success_message(
            input_file=input_file,
            output_file=output_file,
            entities_detected=len(entities),
            entities_replaced=len(entities),
            unique_entities=unique_entities,
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
