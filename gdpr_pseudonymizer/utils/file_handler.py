"""File handling utilities with cross-platform path support.

This module provides safe file I/O operations using pathlib
for cross-platform compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from gdpr_pseudonymizer.exceptions import FileProcessingError


def read_file(file_path: str) -> str:
    """Read text file contents.

    Args:
        file_path: Path to file (absolute or relative)

    Returns:
        File contents as string

    Raises:
        FileProcessingError: If file not found or cannot be read
    """
    path = Path(file_path)

    if not path.exists():
        raise FileProcessingError(f"File not found: {file_path}")

    if not path.is_file():
        raise FileProcessingError(f"Path is not a file: {file_path}")

    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except PermissionError as e:
        raise FileProcessingError(f"Permission denied: {file_path}") from e
    except OSError as e:
        raise FileProcessingError(f"Cannot read file {file_path}: {e}") from e


def write_file(file_path: str, content: str) -> None:
    """Write text content to file.

    Args:
        file_path: Path to file (absolute or relative)
        content: Text content to write

    Raises:
        FileProcessingError: If file cannot be written
    """
    path = Path(file_path)

    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except PermissionError as e:
        raise FileProcessingError(f"Permission denied: {file_path}") from e
    except OSError as e:
        raise FileProcessingError(f"Cannot write file {file_path}: {e}") from e


def validate_file_path(file_path: str, allowed_extensions: List[str]) -> bool:
    """Validate file path and extension.

    Args:
        file_path: Path to validate
        allowed_extensions: List of allowed file extensions (e.g., ['.txt', '.md'])

    Returns:
        True if path is valid and has allowed extension

    Raises:
        FileProcessingError: If path is invalid or extension not allowed
    """
    path = Path(file_path)

    # Check if path is absolute or can be resolved
    if not path.is_absolute():
        path = path.resolve()

    # Check file extension
    if path.suffix.lower() not in allowed_extensions:
        raise FileProcessingError(
            f"Invalid file extension: {path.suffix}. "
            f"Allowed: {', '.join(allowed_extensions)}"
        )

    return True


def get_file_extension(file_path: str) -> str:
    """Get file extension from path.

    Args:
        file_path: Path to file

    Returns:
        File extension with dot (e.g., '.txt', '.md')
    """
    return Path(file_path).suffix.lower()


def ensure_absolute_path(file_path: str) -> str:
    """Convert relative path to absolute path.

    Args:
        file_path: Path to convert

    Returns:
        Absolute path as string
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = path.resolve()
    return str(path)
