"""Input validation helpers for CLI commands (Story 3.4, AC4).

This module provides user-friendly validation functions for common CLI inputs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from gdpr_pseudonymizer.cli.formatters import (
    ErrorCode,
    format_error_message,
    format_styled_error,
    format_warning_message,
)
from gdpr_pseudonymizer.data.database import init_database

# Valid pseudonym themes
VALID_THEMES = ["neutral", "star_wars", "lotr"]

# Valid log levels
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


def validate_file_path(
    file_path: str,
    must_exist: bool = True,
    check_readable: bool = True,
) -> tuple[bool, Optional[Path]]:
    """Validate a file path with user-friendly error messages.

    Args:
        file_path: Path string to validate
        must_exist: If True, file must exist
        check_readable: If True, verify file is readable

    Returns:
        Tuple of (is_valid, resolved_path or None)
    """
    try:
        path = Path(file_path).resolve()

        if must_exist and not path.exists():
            format_styled_error(
                ErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}",
            )
            return False, None

        if must_exist and check_readable and path.exists():
            # Try to read first byte to verify access
            try:
                with open(path, "rb") as f:
                    f.read(1)
            except PermissionError:
                format_styled_error(
                    ErrorCode.PERMISSION_DENIED,
                    f"Cannot read file: {file_path}",
                )
                return False, None

        return True, path

    except Exception as e:
        format_styled_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid path '{file_path}': {e}",
        )
        return False, None


def validate_theme(theme: str) -> tuple[bool, str]:
    """Validate pseudonym theme with suggestions for invalid themes.

    Args:
        theme: Theme name to validate

    Returns:
        Tuple of (is_valid, normalized_theme or error_message)
    """
    theme_lower = theme.lower().strip()

    if theme_lower in VALID_THEMES:
        return True, theme_lower

    # Theme not found - show error with valid options
    format_styled_error(
        ErrorCode.INVALID_THEME,
        f"Theme '{theme}' not recognized. Valid themes: {', '.join(VALID_THEMES)}",
    )
    return False, f"Invalid theme: {theme}"


def validate_workers(workers: int) -> tuple[bool, int]:
    """Validate batch workers count (must be 1-8).

    Args:
        workers: Number of workers to validate

    Returns:
        Tuple of (is_valid, validated_workers)
    """
    if workers < 1:
        format_styled_error(
            ErrorCode.INVALID_CONFIG_VALUE,
            f"Workers must be at least 1 (got: {workers})",
        )
        return False, 1

    if workers > 8:
        format_styled_error(
            ErrorCode.INVALID_CONFIG_VALUE,
            f"Workers cannot exceed 8 (got: {workers})",
        )
        return False, 8

    return True, workers


def validate_log_level(level: str) -> tuple[bool, str]:
    """Validate logging level.

    Args:
        level: Log level string to validate

    Returns:
        Tuple of (is_valid, normalized_level or error_message)
    """
    level_upper = level.upper().strip()

    if level_upper in VALID_LOG_LEVELS:
        return True, level_upper

    format_styled_error(
        ErrorCode.INVALID_CONFIG_VALUE,
        f"Invalid log level '{level}'. Valid levels: {', '.join(VALID_LOG_LEVELS)}",
    )
    return False, f"Invalid level: {level}"


def validate_passphrase_strength(passphrase: str) -> tuple[bool, str]:
    """Validate passphrase strength with warnings for weak passphrases.

    This function validates passphrase meets minimum requirements and provides
    feedback. Unlike data/encryption.py's validate_passphrase, this focuses
    on user-facing warnings.

    Args:
        passphrase: Passphrase to validate

    Returns:
        Tuple of (meets_minimum, feedback_message)
    """
    if not passphrase:
        return False, "Passphrase cannot be empty"

    length = len(passphrase)

    # Minimum requirement check (will fail if < 12)
    if length < 12:
        return False, f"Passphrase must be at least 12 characters (current: {length})"

    # Strength analysis for warnings
    has_lower = any(c.islower() for c in passphrase)
    has_upper = any(c.isupper() for c in passphrase)
    has_digit = any(c.isdigit() for c in passphrase)
    has_special = any(not c.isalnum() for c in passphrase)

    diversity_count = sum([has_lower, has_upper, has_digit, has_special])

    # Provide feedback but still accept valid passphrase
    if length >= 12 and length < 16:
        format_warning_message(
            f"Passphrase is short ({length} chars). Consider 16+ characters for better security."
        )

    if diversity_count < 2:
        format_warning_message(
            "Passphrase could be stronger. Mix uppercase, lowercase, numbers, and special chars."
        )

    return True, "Passphrase accepted"


def validate_database_path(
    db_path: str,
    must_exist: bool = False,
    create_parent: bool = True,
) -> tuple[bool, Optional[Path]]:
    """Validate database path with appropriate error messages.

    Args:
        db_path: Database file path
        must_exist: If True, database must already exist
        create_parent: If True, parent directory will be validated/created

    Returns:
        Tuple of (is_valid, resolved_path or None)
    """
    try:
        path = Path(db_path).resolve()

        if must_exist and not path.exists():
            format_styled_error(
                ErrorCode.DATABASE_NOT_FOUND,
                f"Database not found: {db_path}",
            )
            return False, None

        # Validate parent directory
        parent = path.parent
        if not parent.exists():
            if create_parent:
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    format_styled_error(
                        ErrorCode.PERMISSION_DENIED,
                        f"Cannot create directory: {parent}",
                    )
                    return False, None
            else:
                format_styled_error(
                    ErrorCode.FILE_NOT_FOUND,
                    f"Parent directory does not exist: {parent}",
                )
                return False, None

        # Check write permission to parent (for new databases)
        if not must_exist:
            if not parent.exists() or not (parent.is_dir()):
                format_styled_error(
                    ErrorCode.PERMISSION_DENIED,
                    f"Cannot write to directory: {parent}",
                )
                return False, None

        return True, path

    except Exception as e:
        format_styled_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid database path '{db_path}': {e}",
        )
        return False, None


# ---------------------------------------------------------------------------
# Shared CLI command helpers (R6 — factored from process.py / batch.py)
# ---------------------------------------------------------------------------

VALID_ENTITY_TYPES = {"PERSON", "LOCATION", "ORG"}


def parse_entity_type_filter(
    entity_types: Optional[str], console: Console
) -> Optional[set[str]]:
    """Parse and validate an entity-type filter from a CLI argument.

    Args:
        entity_types: Comma-separated entity types (e.g. "PERSON,ORG") or None
        console: Rich console for output

    Returns:
        Set of valid entity types, or None if no filter was requested
    """
    if entity_types is None:
        return None

    parsed = {t.strip().upper() for t in entity_types.split(",")}
    invalid = parsed - VALID_ENTITY_TYPES
    if invalid:
        console.print(
            f"[yellow]Warning: Unknown entity type(s): {', '.join(sorted(invalid))}. "
            f"Valid types: {', '.join(sorted(VALID_ENTITY_TYPES))}[/yellow]"
        )
    result = parsed & VALID_ENTITY_TYPES
    if not result:
        console.print("[bold red]Error: No valid entity types specified.[/bold red]")
        sys.exit(1)
    console.print(f"[dim]Filtering entities: {', '.join(sorted(result))}[/dim]")
    return result


def validate_theme_or_exit(theme: str) -> None:
    """Validate theme and exit(1) if invalid.

    Args:
        theme: Theme name to check against VALID_THEMES
    """
    if theme not in VALID_THEMES:
        format_error_message(
            "Invalid Theme",
            f"Theme '{theme}' is not recognized.",
            f"Valid themes: {', '.join(VALID_THEMES)}",
        )
        sys.exit(1)


def ensure_database(db_path: str, passphrase: str, console: Console) -> None:
    """Initialize the database if it does not exist, with a progress spinner.

    Args:
        db_path: Path to the SQLite database file
        passphrase: Encryption passphrase
        console: Rich console for output
    """
    db_file = Path(db_path)
    if db_file.exists():
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing encrypted database...", total=None)
        try:
            init_database(db_path, passphrase)
            progress.update(task, description="✓ Database initialized")
        except ValueError as e:
            console.print(f"[bold red]Database initialization failed:[/bold red] {e}")
            sys.exit(1)
    console.print("[green]✓ New database created successfully[/green]\n")
