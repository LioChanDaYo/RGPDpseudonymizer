"""Rich output formatting for CLI messages.

This module provides consistent formatting for success, error, and
informational messages using Rich styling.

Error Message Style Guide (AC1):
    Format: [ERROR] <Description> | Action: <Suggested action> | Docs: <doc link>
    Example: [ERROR] Passphrase incorrect | Action: Use same passphrase from 'init' command
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Create Rich console for output
console = Console()

# Default documentation base URL
DEFAULT_DOCS_URL = "https://github.com/YOUR_REPO/gdpr-pseudonymizer#"


class ErrorCode(Enum):
    """Standardized error codes for CLI error messages (AC1/AC2).

    Each error code maps to a catalog entry with description, action, and docs link.
    """

    # File/Path errors
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"

    # Database errors
    CORRUPT_DATABASE = "corrupt_database"
    DATABASE_NOT_FOUND = "database_not_found"
    NOT_SQLITE_FILE = "not_sqlite_file"
    SYMLINK_REJECTED = "symlink_rejected"

    # Security errors
    INVALID_PASSPHRASE = "invalid_passphrase"
    PASSPHRASE_VERIFICATION_FAILED = "passphrase_verification_failed"
    WEAK_PASSPHRASE = "weak_passphrase"

    # Configuration errors
    CONFIG_PARSE_ERROR = "config_parse_error"
    INVALID_THEME = "invalid_theme"
    INVALID_CONFIG_VALUE = "invalid_config_value"

    # NLP/Model errors
    MODEL_NOT_INSTALLED = "model_not_installed"

    # Validation errors
    VALIDATION_ERROR = "validation_error"


@dataclass
class ErrorInfo:
    """Information for a specific error code."""

    description: str
    action: str
    docs: str = ""


# Error catalog mapping error codes to user-friendly messages (AC2)
ERROR_CATALOG: dict[ErrorCode, ErrorInfo] = {
    ErrorCode.FILE_NOT_FOUND: ErrorInfo(
        description="File not found",
        action="Check file path. Use absolute or relative path from current directory.",
        docs=f"{DEFAULT_DOCS_URL}file-paths",
    ),
    ErrorCode.PERMISSION_DENIED: ErrorInfo(
        description="Permission denied",
        action="Check file permissions or run with appropriate privileges.",
        docs=f"{DEFAULT_DOCS_URL}troubleshooting",
    ),
    ErrorCode.CORRUPT_DATABASE: ErrorInfo(
        description="Mapping database corrupted",
        action="Restore from backup or re-run 'init' to create new database.",
        docs=f"{DEFAULT_DOCS_URL}database",
    ),
    ErrorCode.DATABASE_NOT_FOUND: ErrorInfo(
        description="Database not found",
        action="Run 'gdpr-pseudo init' to create a new mapping database.",
        docs=f"{DEFAULT_DOCS_URL}getting-started",
    ),
    ErrorCode.NOT_SQLITE_FILE: ErrorInfo(
        description="File is not a SQLite database",
        action="Verify the database path points to a valid SQLite file created by gdpr-pseudo.",
        docs=f"{DEFAULT_DOCS_URL}database",
    ),
    ErrorCode.SYMLINK_REJECTED: ErrorInfo(
        description="Refusing to operate on symbolic link",
        action="Provide the actual file path instead of a symbolic link for security.",
        docs=f"{DEFAULT_DOCS_URL}security",
    ),
    ErrorCode.INVALID_PASSPHRASE: ErrorInfo(
        description="Passphrase incorrect",
        action="Use the same passphrase from the 'init' command that created this database.",
        docs=f"{DEFAULT_DOCS_URL}encryption",
    ),
    ErrorCode.PASSPHRASE_VERIFICATION_FAILED: ErrorInfo(
        description="Passphrase verification failed",
        action="Enter the correct passphrase or use --skip-passphrase-check (not recommended).",
        docs=f"{DEFAULT_DOCS_URL}encryption",
    ),
    ErrorCode.WEAK_PASSPHRASE: ErrorInfo(
        description="Passphrase too weak",
        action="Use at least 12 characters with mixed case, numbers, and special characters.",
        docs=f"{DEFAULT_DOCS_URL}security",
    ),
    ErrorCode.CONFIG_PARSE_ERROR: ErrorInfo(
        description="Invalid YAML syntax in config file",
        action="Check config file for YAML syntax errors. Use 'gdpr-pseudo config --init' to generate template.",
        docs=f"{DEFAULT_DOCS_URL}configuration",
    ),
    ErrorCode.INVALID_THEME: ErrorInfo(
        description="Invalid pseudonym theme",
        action="Use a valid theme: neutral, star_wars, lotr",
        docs=f"{DEFAULT_DOCS_URL}themes",
    ),
    ErrorCode.INVALID_CONFIG_VALUE: ErrorInfo(
        description="Invalid configuration value",
        action="Check the value format and valid options for this setting.",
        docs=f"{DEFAULT_DOCS_URL}configuration",
    ),
    ErrorCode.MODEL_NOT_INSTALLED: ErrorInfo(
        description="spaCy French model not installed",
        action="Run: poetry run python scripts/install_spacy_model.py",
        docs=f"{DEFAULT_DOCS_URL}installation",
    ),
    ErrorCode.VALIDATION_ERROR: ErrorInfo(
        description="Validation failed",
        action="Review the error details and correct the input.",
        docs=f"{DEFAULT_DOCS_URL}validation",
    ),
}


def format_success_message(
    input_file: Path,
    output_file: Path,
    entities_detected: int,
    entities_replaced: int,
    unique_entities: int,
) -> None:
    """Display success message with processing summary.

    Args:
        input_file: Path to input file
        output_file: Path to output file
        entities_detected: Total number of entity occurrences detected
        entities_replaced: Total number of entity occurrences replaced
        unique_entities: Number of unique entities
    """
    # Create summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Input file", str(input_file))
    table.add_row("Output file", str(output_file))
    table.add_row("Entities detected", str(entities_detected))
    table.add_row("Entities replaced", str(entities_replaced))
    table.add_row("Unique entities", str(unique_entities))

    # Display success panel
    console.print()
    console.print(
        Panel(
            table,
            title="[bold green]+ Processing Complete[/bold green]",
            border_style="green",
        )
    )


def format_error_message(
    error_type: str, error_message: str, suggestion: Optional[str] = None
) -> None:
    """Display error message with optional suggestion.

    Args:
        error_type: Type of error (e.g., "File Not Found", "Permission Denied")
        error_message: Detailed error message
        suggestion: Optional suggestion for fixing the error
    """
    console.print()
    console.print(f"[bold red]X Error: {error_type}[/bold red]")
    console.print(f"[red]{error_message}[/red]")

    if suggestion:
        console.print()
        console.print(f"[yellow]> {suggestion}[/yellow]")

    console.print()


def format_info_message(message: str) -> None:
    """Display informational message.

    Args:
        message: Information message to display
    """
    console.print(f"[cyan]i {message}[/cyan]")


def format_warning_message(message: str) -> None:
    """Display warning message.

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]! {message}[/yellow]")


def format_styled_error(
    error_code: ErrorCode,
    details: str = "",
    docs_url: Optional[str] = None,
) -> None:
    """Format error with standardized style guide format (AC1).

    Format: [ERROR] <Description> | Action: <action> | Docs: <link>

    Args:
        error_code: The ErrorCode enum value identifying the error type
        details: Optional additional details about the specific error
        docs_url: Optional override for documentation URL

    Example:
        >>> format_styled_error(ErrorCode.INVALID_PASSPHRASE)
        [ERROR] Passphrase incorrect
        Action: Use the same passphrase from the 'init' command...
        Docs: https://...
    """
    error_info = ERROR_CATALOG.get(error_code)

    if error_info is None:
        # Fallback for unknown error codes
        console.print(
            f"\n[bold red][ERROR] Unknown error: {error_code.value}[/bold red]"
        )
        if details:
            console.print(f"[red]{details}[/red]")
        console.print()
        return

    console.print()
    console.print(f"[bold red][ERROR] {error_info.description}[/bold red]")

    if details:
        console.print(f"[red]{details}[/red]")

    console.print(f"[yellow]Action: {error_info.action}[/yellow]")

    final_docs = docs_url or error_info.docs
    if final_docs:
        console.print(f"[dim]Docs: {final_docs}[/dim]")

    console.print()


def get_error_info(error_code: ErrorCode) -> Optional[ErrorInfo]:
    """Get error info for a given error code.

    Args:
        error_code: The ErrorCode enum value

    Returns:
        ErrorInfo dataclass with description, action, docs, or None if not found
    """
    return ERROR_CATALOG.get(error_code)


def format_validation_cancelled() -> None:
    """Display message when user cancels validation."""
    console.print()
    console.print("[yellow]X Processing cancelled by user[/yellow]")
    console.print()
