"""Unit tests for file handler utilities."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gdpr_pseudonymizer.exceptions import FileProcessingError
from gdpr_pseudonymizer.utils.file_handler import (
    ensure_absolute_path,
    get_file_extension,
    read_file,
    validate_file_path,
    write_file,
)


def test_read_file_success(tmp_path: Path) -> None:
    """Test reading valid text file."""
    test_file = tmp_path / "test.txt"
    test_content = "Hello, World!\nThis is a test file."
    test_file.write_text(test_content, encoding="utf-8")

    content = read_file(str(test_file))

    assert content == test_content


def test_read_file_markdown(tmp_path: Path) -> None:
    """Test reading markdown file."""
    test_file = tmp_path / "test.md"
    test_content = "# Heading\n\nThis is **markdown** content."
    test_file.write_text(test_content, encoding="utf-8")

    content = read_file(str(test_file))

    assert content == test_content


def test_read_file_not_found(tmp_path: Path) -> None:
    """Test error handling for non-existent file."""
    nonexistent_file = tmp_path / "missing.txt"

    with pytest.raises(FileProcessingError, match="File not found"):
        read_file(str(nonexistent_file))


def test_read_file_is_directory(tmp_path: Path) -> None:
    """Test error handling when path is a directory."""
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    with pytest.raises(FileProcessingError, match="Path is not a file"):
        read_file(str(test_dir))


def test_write_file_success(tmp_path: Path) -> None:
    """Test writing content to file."""
    test_file = tmp_path / "output.txt"
    test_content = "This is test output."

    write_file(str(test_file), test_content)

    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == test_content


def test_write_file_creates_parent_directories(tmp_path: Path) -> None:
    """Test that write_file creates parent directories if they don't exist."""
    nested_file = tmp_path / "subdir" / "nested" / "file.txt"
    test_content = "Nested file content."

    write_file(str(nested_file), test_content)

    assert nested_file.exists()
    assert nested_file.read_text(encoding="utf-8") == test_content


def test_write_file_overwrites_existing(tmp_path: Path) -> None:
    """Test that write_file overwrites existing file content."""
    test_file = tmp_path / "overwrite.txt"
    test_file.write_text("Original content", encoding="utf-8")

    new_content = "New content"
    write_file(str(test_file), new_content)

    assert test_file.read_text(encoding="utf-8") == new_content


def test_validate_file_path_valid_extension(tmp_path: Path) -> None:
    """Test file path validation with allowed extension."""
    test_file = tmp_path / "document.txt"

    result = validate_file_path(str(test_file), [".txt", ".md"])

    assert result is True


def test_validate_file_path_case_insensitive(tmp_path: Path) -> None:
    """Test file path validation is case-insensitive for extensions."""
    test_file = tmp_path / "document.TXT"

    result = validate_file_path(str(test_file), [".txt", ".md"])

    assert result is True


def test_validate_file_path_invalid_extension(tmp_path: Path) -> None:
    """Test error for invalid file extension."""
    test_file = tmp_path / "document.pdf"

    with pytest.raises(FileProcessingError, match="Invalid file extension"):
        validate_file_path(str(test_file), [".txt", ".md"])


def test_get_file_extension_txt() -> None:
    """Test getting file extension for .txt file."""
    extension = get_file_extension("document.txt")
    assert extension == ".txt"


def test_get_file_extension_markdown() -> None:
    """Test getting file extension for .md file."""
    extension = get_file_extension("README.md")
    assert extension == ".md"


def test_get_file_extension_multiple_dots() -> None:
    """Test getting extension from filename with multiple dots."""
    extension = get_file_extension("file.backup.txt")
    assert extension == ".txt"


def test_get_file_extension_no_extension() -> None:
    """Test getting extension from filename without extension."""
    extension = get_file_extension("filename")
    assert extension == ""


def test_get_file_extension_case_normalization() -> None:
    """Test that extension is returned in lowercase."""
    extension = get_file_extension("DOCUMENT.TXT")
    assert extension == ".txt"


def test_ensure_absolute_path_relative() -> None:
    """Test converting relative path to absolute."""
    relative_path = "subdir/file.txt"
    absolute_path = ensure_absolute_path(relative_path)

    # Use os.path.isabs for more reliable cross-platform check
    assert os.path.isabs(absolute_path), f"Expected absolute path, got: {absolute_path}"
    assert Path(absolute_path).is_absolute()


def test_ensure_absolute_path_already_absolute(tmp_path: Path) -> None:
    """Test that already absolute path is unchanged."""
    absolute_path = str(tmp_path / "file.txt")
    result = ensure_absolute_path(absolute_path)

    assert Path(result).is_absolute()
    assert result == str(Path(absolute_path).resolve())


def test_read_file_unicode_content(tmp_path: Path) -> None:
    """Test reading file with Unicode characters."""
    test_file = tmp_path / "unicode.txt"
    test_content = "Français: café, naïve, œuvre\nChinese: 你好世界"
    test_file.write_text(test_content, encoding="utf-8")

    content = read_file(str(test_file))

    assert content == test_content


def test_write_file_unicode_content(tmp_path: Path) -> None:
    """Test writing file with Unicode characters."""
    test_file = tmp_path / "unicode_out.txt"
    test_content = "Special chars: é à ç ñ ü"

    write_file(str(test_file), test_content)

    assert test_file.read_text(encoding="utf-8") == test_content


def test_read_file_permission_denied(tmp_path: Path) -> None:
    """Test error handling for permission denied (Unix-like systems only)."""
    import os
    import stat

    if os.name == "nt":  # Skip on Windows
        pytest.skip("Permission tests not applicable on Windows")

    test_file = tmp_path / "no_read_permission.txt"
    test_file.write_text("Secret content", encoding="utf-8")

    # Remove read permission
    test_file.chmod(stat.S_IWUSR)  # Write-only

    with pytest.raises(FileProcessingError, match="Permission denied"):
        read_file(str(test_file))

    # Restore permissions for cleanup
    test_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
