"""Unit tests for process command."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from gdpr_pseudonymizer.cli.commands.process import process_command
from gdpr_pseudonymizer.exceptions import FileProcessingError


def test_process_command_reads_input_file(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command reads input file."""
    # Create test file
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test content with Marie Dubois.")

    # Mock components to isolate file reading
    mock_read = mocker.patch("gdpr_pseudonymizer.cli.commands.process.read_file")
    mock_read.return_value = "Test content with Marie Dubois."
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.detect_naive_entities")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command
    process_command(input_file=input_file, output_file=None, validate=False)

    # Verify read_file was called
    mock_read.assert_called_once_with(str(input_file))


def test_process_command_writes_output_file(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command writes output file."""
    # Create test file
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test content.")
    output_file = tmp_path / "output.txt"

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test content.",
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities", return_value=[]
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements",
        return_value="Test content.",
    )
    mock_write = mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command
    process_command(input_file=input_file, output_file=output_file, validate=False)

    # Verify write_file was called
    mock_write.assert_called_once()
    assert mock_write.call_args[0][0] == str(output_file)


def test_process_command_handles_file_not_found_error(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command handles file not found error."""
    # Create non-existent file path
    input_file = tmp_path / "nonexistent.txt"

    # Mock read_file to raise FileProcessingError
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        side_effect=FileProcessingError("File not found: nonexistent.txt"),
    )
    mock_error_format = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.format_error_message"
    )

    # Run command and expect sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        process_command(input_file=input_file, output_file=None, validate=False)

    assert exc_info.value.code == 1
    mock_error_format.assert_called_once()


def test_process_command_handles_permission_error(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command handles permission error."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test content.")

    # Mock read_file to raise FileProcessingError (permission denied)
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        side_effect=FileProcessingError("Permission denied: test.txt"),
    )
    mock_error_format = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.format_error_message"
    )

    # Run command and expect sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        process_command(input_file=input_file, output_file=None, validate=False)

    assert exc_info.value.code == 1
    mock_error_format.assert_called_once()


def test_process_command_validates_file_extensions(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command validates file extensions."""
    # Create file with invalid extension
    input_file = tmp_path / "test.docx"
    input_file.write_text("Test content.")

    mock_error_format = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.format_error_message"
    )

    # Run command and expect sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        process_command(input_file=input_file, output_file=None, validate=False)

    assert exc_info.value.code == 1
    mock_error_format.assert_called_once()
    # Verify error message mentions invalid extension
    call_args = mock_error_format.call_args[0]
    assert "Invalid File Format" in call_args[0]


def test_process_command_with_validation_enabled(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command with validation enabled."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test with Marie Dubois.")

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test with Marie Dubois.",
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities",
        return_value=[("Marie Dubois", "PERSON", 10, 22, "Leia Organa")],
    )
    mock_present = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.present_entities_for_validation"
    )
    mock_confirm = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.confirm_processing",
        return_value=True,
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements",
        return_value="Test with Leia Organa.",
    )
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command with validation
    process_command(input_file=input_file, output_file=None, validate=True)

    # Verify validation functions were called
    mock_present.assert_called_once()
    mock_confirm.assert_called_once()


def test_process_command_with_validation_user_rejects(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command when user rejects validation."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test with Marie Dubois.")

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test with Marie Dubois.",
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities",
        return_value=[("Marie Dubois", "PERSON", 10, 22, "Leia Organa")],
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.present_entities_for_validation"
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.confirm_processing",
        return_value=False,
    )
    mock_write = mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mock_cancelled = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.format_validation_cancelled"
    )
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")

    # Run command and expect sys.exit(0)
    with pytest.raises(SystemExit) as exc_info:
        process_command(input_file=input_file, output_file=None, validate=True)

    assert exc_info.value.code == 0
    mock_cancelled.assert_called_once()
    # Verify write_file was NOT called (user rejected)
    mock_write.assert_not_called()


def test_process_command_generates_default_output_filename(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command generates default output filename."""
    input_file = tmp_path / "interview.txt"
    input_file.write_text("Test content.")

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test content.",
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities", return_value=[]
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements",
        return_value="Test content.",
    )
    mock_write = mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command without output_file
    process_command(input_file=input_file, output_file=None, validate=False)

    # Verify default filename was generated
    mock_write.assert_called_once()
    output_path = mock_write.call_args[0][0]
    assert "interview_pseudonymized.txt" in output_path


def test_process_command_calls_detect_naive_entities(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command calls entity detection."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test with Marie Dubois.")

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test with Marie Dubois.",
    )
    mock_detect = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities",
        return_value=[("Marie Dubois", "PERSON", 10, 22, "Leia Organa")],
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements",
        return_value="Test with Leia Organa.",
    )
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command
    process_command(input_file=input_file, output_file=None, validate=False)

    # Verify detect was called with file content
    mock_detect.assert_called_once_with("Test with Marie Dubois.")


def test_process_command_calls_apply_naive_replacements(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command calls replacement logic."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test with Marie Dubois.")

    entities = [("Marie Dubois", "PERSON", 10, 22, "Leia Organa")]

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test with Marie Dubois.",
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities",
        return_value=entities,
    )
    mock_apply = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements",
        return_value="Test with Leia Organa.",
    )
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_info_message")
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command
    process_command(input_file=input_file, output_file=None, validate=False)

    # Verify apply was called with content and entities
    mock_apply.assert_called_once_with("Test with Marie Dubois.", entities)


def test_process_command_logs_processing_steps(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test process command logs processing steps."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Test content.")

    # Mock components
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.read_file",
        return_value="Test content.",
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.detect_naive_entities", return_value=[]
    )
    mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.apply_naive_replacements",
        return_value="Test content.",
    )
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.write_file")
    mock_info = mocker.patch(
        "gdpr_pseudonymizer.cli.commands.process.format_info_message"
    )
    mocker.patch("gdpr_pseudonymizer.cli.commands.process.format_success_message")

    # Run command
    process_command(input_file=input_file, output_file=None, validate=False)

    # Verify info messages were displayed
    assert mock_info.call_count >= 3  # Reading, detecting, writing messages
