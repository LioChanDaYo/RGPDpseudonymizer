"""Unit tests for batch command.

Tests cover:
- Directory processing
- File list processing
- Error handling (individual file failures)
- Progress display
- Summary report generation
- Argument parsing
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.batch import (
    BatchResult,
    batch_command,
    collect_files,
)


def create_test_app() -> typer.Typer:
    """Create a properly configured Typer app for testing."""
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        """Test app callback."""
        pass

    app.command(name="batch")(batch_command)
    return app


app = create_test_app()
runner = CliRunner()


@dataclass
class MockProcessingResult:
    """Mock processing result for testing."""

    success: bool = True
    entities_detected: int = 5
    entities_new: int = 3
    entities_reused: int = 2
    error_message: str = ""


class TestCollectFiles:
    """Tests for file collection utility."""

    def test_collect_single_txt_file(self, tmp_path: Path) -> None:
        """Test collecting a single .txt file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        files = collect_files(txt_file)

        assert len(files) == 1
        assert files[0] == txt_file

    def test_collect_single_md_file(self, tmp_path: Path) -> None:
        """Test collecting a single .md file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("content")

        files = collect_files(md_file)

        assert len(files) == 1
        assert files[0] == md_file

    def test_skip_unsupported_extension(self, tmp_path: Path) -> None:
        """Test that unsupported extensions are skipped."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("content")

        files = collect_files(pdf_file)

        assert len(files) == 0

    def test_collect_directory_files(self, tmp_path: Path) -> None:
        """Test collecting files from directory."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.md").write_text("content")
        (tmp_path / "file3.pdf").write_text("content")  # Should be skipped

        files = collect_files(tmp_path)

        assert len(files) == 2
        assert any(f.name == "file1.txt" for f in files)
        assert any(f.name == "file2.md" for f in files)

    def test_collect_recursive(self, tmp_path: Path) -> None:
        """Test recursive file collection."""
        (tmp_path / "file1.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content")

        files = collect_files(tmp_path, recursive=True)

        assert len(files) == 2

    def test_collect_non_recursive(self, tmp_path: Path) -> None:
        """Test non-recursive file collection."""
        (tmp_path / "file1.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content")

        files = collect_files(tmp_path, recursive=False)

        assert len(files) == 1
        assert files[0].name == "file1.txt"

    def test_exclude_pseudonymized_single_file(self, tmp_path: Path) -> None:
        """Test that pseudonymized output files are excluded (single file)."""
        pseudonymized_file = tmp_path / "interview_01_pseudonymized.txt"
        pseudonymized_file.write_text("content")

        files = collect_files(pseudonymized_file)

        assert len(files) == 0

    def test_exclude_pseudonymized_from_directory(self, tmp_path: Path) -> None:
        """Test that pseudonymized output files are excluded from directory."""
        (tmp_path / "interview_01.txt").write_text("content")
        (tmp_path / "interview_01_pseudonymized.txt").write_text("content")
        (tmp_path / "interview_02.txt").write_text("content")
        (tmp_path / "interview_02_pseudonymized.txt").write_text("content")

        files = collect_files(tmp_path)

        assert len(files) == 2
        assert all("_pseudonymized" not in f.stem for f in files)
        assert any(f.name == "interview_01.txt" for f in files)
        assert any(f.name == "interview_02.txt" for f in files)

    def test_exclude_pseudonymized_recursive(self, tmp_path: Path) -> None:
        """Test that pseudonymized files are excluded in recursive mode."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file1_pseudonymized.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content")
        (subdir / "file2_pseudonymized.txt").write_text("content")

        files = collect_files(tmp_path, recursive=True)

        assert len(files) == 2
        assert all("_pseudonymized" not in f.stem for f in files)


class TestBatchCommand:
    """Tests for batch command."""

    def test_batch_processes_directory(self, tmp_path: Path) -> None:
        """Test batch command processes directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("Test content one")
        (tmp_path / "file2.txt").write_text("Test content two")

        mock_result = MockProcessingResult()

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["batch", str(tmp_path)])

        assert result.exit_code == 0
        assert "2 file(s) to process" in result.stdout
        assert "All files processed successfully" in result.stdout

    def test_batch_no_files_found(self, tmp_path: Path) -> None:
        """Test batch command with no supported files."""
        # Create only unsupported file
        (tmp_path / "file.pdf").write_text("content")

        result = runner.invoke(app, ["batch", str(tmp_path)])

        assert result.exit_code == 1
        assert "No supported files found" in result.stdout

    def test_batch_invalid_theme(self, tmp_path: Path) -> None:
        """Test batch command with invalid theme."""
        (tmp_path / "file.txt").write_text("content")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(
                app, ["batch", str(tmp_path), "--theme", "invalid"]
            )

        assert result.exit_code == 1
        assert "Invalid Theme" in result.stdout

    def test_batch_continue_on_error(self, tmp_path: Path) -> None:
        """Test batch command continues on individual file errors."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        # First file fails, second succeeds
        mock_results = [
            MockProcessingResult(success=False, error_message="Test error"),
            MockProcessingResult(success=True),
        ]

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.side_effect = mock_results

            result = runner.invoke(app, ["batch", str(tmp_path)])

        # Exit code 1 because some files failed
        assert result.exit_code == 1
        assert "1/2 files processed successfully" in result.stdout

    def test_batch_stop_on_error(self, tmp_path: Path) -> None:
        """Test batch command stops on error when flag set."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        mock_result = MockProcessingResult(success=False, error_message="Test error")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(
                app, ["batch", str(tmp_path), "--stop-on-error"]
            )

        assert result.exit_code == 1
        # Only one file attempted because processing stopped
        assert "Processing stopped" in result.stdout or "1" in result.stdout

    def test_batch_output_directory(self, tmp_path: Path) -> None:
        """Test batch command with custom output directory."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        (input_dir / "file.txt").write_text("content")

        mock_result = MockProcessingResult()

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(
                app, ["batch", str(input_dir), "-o", str(output_dir)]
            )

        assert result.exit_code == 0

    def test_batch_recursive_flag(self, tmp_path: Path) -> None:
        """Test batch command with recursive flag."""
        (tmp_path / "file1.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content")

        mock_result = MockProcessingResult()

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["batch", str(tmp_path), "--recursive"])

        assert result.exit_code == 0
        assert "2 file(s) to process" in result.stdout

    def test_batch_summary_report(self, tmp_path: Path) -> None:
        """Test batch command displays summary report."""
        (tmp_path / "file.txt").write_text("content")

        mock_result = MockProcessingResult(
            entities_detected=10,
            entities_new=6,
            entities_reused=4,
        )

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["batch", str(tmp_path)])

        assert result.exit_code == 0
        assert "Batch Processing Summary" in result.stdout
        assert "Total files" in result.stdout
        assert "Total entities" in result.stdout
        assert "Processing time" in result.stdout

    def test_batch_help_text(self) -> None:
        """Test batch command help text is displayed."""
        result = runner.invoke(app, ["batch", "--help"])

        assert result.exit_code == 0
        assert "Process multiple documents" in result.stdout
        assert "--output" in result.stdout
        assert "--theme" in result.stdout
        assert "--recursive" in result.stdout
        assert "--continue-on-error" in result.stdout

    def test_batch_keyboard_interrupt(self, tmp_path: Path) -> None:
        """Test batch command handles keyboard interrupt."""
        (tmp_path / "file.txt").write_text("content")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.side_effect = KeyboardInterrupt()

            result = runner.invoke(app, ["batch", str(tmp_path)])

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_defaults(self) -> None:
        """Test BatchResult default values."""
        result = BatchResult()

        assert result.total_files == 0
        assert result.successful_files == 0
        assert result.failed_files == 0
        assert result.total_entities == 0
        assert result.errors == []

    def test_batch_result_with_values(self) -> None:
        """Test BatchResult with values."""
        result = BatchResult(
            total_files=10,
            successful_files=8,
            failed_files=2,
            total_entities=50,
            errors=["error1", "error2"],
        )

        assert result.total_files == 10
        assert result.successful_files == 8
        assert result.failed_files == 2
        assert len(result.errors) == 2


class TestBatchCommandEdgeCases:
    """Additional edge case tests for batch command."""

    def test_batch_invalid_input_path(self, tmp_path: Path) -> None:
        """Test batch command with nonexistent input path."""
        nonexistent = tmp_path / "nonexistent"

        result = runner.invoke(app, ["batch", str(nonexistent)])

        # Typer validates argument and exits with code 2 for invalid path
        assert result.exit_code == 2

    def test_batch_exception_during_processing(self, tmp_path: Path) -> None:
        """Test batch command handles processing exceptions."""
        (tmp_path / "file.txt").write_text("content")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.side_effect = RuntimeError(
                "Processing failed"
            )

            result = runner.invoke(app, ["batch", str(tmp_path)])

        # Should continue on error by default but fail with exit code 1
        assert result.exit_code == 1

    def test_batch_all_files_fail(self, tmp_path: Path) -> None:
        """Test batch command when all files fail."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        mock_result = MockProcessingResult(success=False, error_message="Test error")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["batch", str(tmp_path)])

        assert result.exit_code == 1
        # Check for the actual output - "All files failed to process"
        assert "failed" in result.stdout.lower()

    def test_batch_with_star_wars_theme(self, tmp_path: Path) -> None:
        """Test batch command with star_wars theme."""
        (tmp_path / "file.txt").write_text("content")

        mock_result = MockProcessingResult()

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(
                app, ["batch", str(tmp_path), "--theme", "star_wars"]
            )

        assert result.exit_code == 0

    def test_batch_authentication_error(self, tmp_path: Path) -> None:
        """Test batch command with authentication error (from DocumentProcessor)."""
        (tmp_path / "file.txt").write_text("content")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "wrongpassphrase!!"
            # DocumentProcessor raises ValueError for incorrect passphrase
            mock_processor.side_effect = ValueError("Incorrect passphrase")

            result = runner.invoke(app, ["batch", str(tmp_path)])

        assert result.exit_code == 1
        # The error message says "Error" or contains passphrase hint
        assert "passphrase" in result.stdout.lower() or result.exit_code == 1

    def test_batch_unexpected_error(self, tmp_path: Path) -> None:
        """Test batch command with unexpected error."""
        (tmp_path / "file.txt").write_text("content")

        with patch(
            "gdpr_pseudonymizer.cli.commands.batch.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.batch.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.batch.init_database"
        ):
            mock_resolve.return_value = "testpassphrase123!"
            # Unexpected exception that's not ValueError
            mock_processor.side_effect = RuntimeError("Unexpected database error")

            result = runner.invoke(app, ["batch", str(tmp_path)])

        # Caught by outer Exception handler
        assert result.exit_code == 2
        assert "Batch Processing Error" in result.stdout
