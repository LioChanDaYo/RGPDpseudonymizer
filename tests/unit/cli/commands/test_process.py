"""Unit tests for process command.

Tests cover:
- Configuration file integration
- CLI argument override behavior
- Help text validation
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.process import process_command


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


def create_test_app() -> typer.Typer:
    """Create a properly configured Typer app for testing."""
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        """Test app callback."""
        pass

    app.command(name="process")(process_command)
    return app


app = create_test_app()
runner = CliRunner()


class TestProcessCommand:
    """Tests for process command."""

    def test_help_text(self) -> None:
        """Test process command help text displays properly."""
        result = runner.invoke(app, ["process", "--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--theme" in output
        assert "--model" in output
        assert "--db" in output
        assert "--passphrase" in output
        assert "--output" in output

    def test_help_text_mentions_config(self) -> None:
        """Test process command help text mentions config defaults."""
        result = runner.invoke(app, ["process", "--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        # Help text should mention that values come from config
        assert "config" in output.lower() or "Default from config" in output


class TestProcessConfigIntegration:
    """Tests for process command configuration file integration (Story 3.3.3)."""

    def test_uses_config_file_theme(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test process command uses theme from config file when not specified on CLI."""
        # Create project directory with config file
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / ".gdpr-pseudo.yaml"
        config_file.write_text(
            """
pseudonymization:
  theme: star_wars
"""
        )

        # Create test file
        input_file = project_dir / "input.txt"
        input_file.write_text("Test content")

        # Create empty home dir (no home config)
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        with patch(
            "gdpr_pseudonymizer.cli.commands.process.resolve_passphrase"
        ) as mock_passphrase, patch(
            "gdpr_pseudonymizer.cli.commands.process.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.process.init_database"
        ):
            mock_passphrase.return_value = "testpassphrase123!"

            # Mock a successful processing result
            mock_result = type(
                "MockResult",
                (),
                {
                    "success": True,
                    "entities_detected": 5,
                    "entities_new": 3,
                    "entities_reused": 2,
                    "processing_time_seconds": 1.5,
                    "error_message": None,
                },
            )()
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["process", str(input_file)])

        assert result.exit_code == 0
        # Check that star_wars theme was passed to DocumentProcessor
        call_kwargs = mock_processor.call_args
        assert call_kwargs[1]["theme"] == "star_wars"

    def test_uses_config_file_model(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test process command uses model from config file when not specified on CLI."""
        # Create project directory with config file
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / ".gdpr-pseudo.yaml"
        config_file.write_text(
            """
pseudonymization:
  model: spacy
"""
        )

        # Create test file
        input_file = project_dir / "input.txt"
        input_file.write_text("Test content")

        # Create empty home dir (no home config)
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        with patch(
            "gdpr_pseudonymizer.cli.commands.process.resolve_passphrase"
        ) as mock_passphrase, patch(
            "gdpr_pseudonymizer.cli.commands.process.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.process.init_database"
        ):
            mock_passphrase.return_value = "testpassphrase123!"

            # Mock a successful processing result
            mock_result = type(
                "MockResult",
                (),
                {
                    "success": True,
                    "entities_detected": 5,
                    "entities_new": 3,
                    "entities_reused": 2,
                    "processing_time_seconds": 1.5,
                    "error_message": None,
                },
            )()
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["process", str(input_file)])

        assert result.exit_code == 0
        # Check that spacy model was passed to DocumentProcessor
        call_kwargs = mock_processor.call_args
        assert call_kwargs[1]["model_name"] == "spacy"

    def test_uses_config_file_db_path(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test process command uses db_path from config file when not specified on CLI."""
        # Create project directory with config file
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / ".gdpr-pseudo.yaml"
        config_file.write_text(
            """
database:
  path: custom_db.db
"""
        )

        # Create test file
        input_file = project_dir / "input.txt"
        input_file.write_text("Test content")

        # Create empty home dir (no home config)
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        with patch(
            "gdpr_pseudonymizer.cli.commands.process.resolve_passphrase"
        ) as mock_passphrase, patch(
            "gdpr_pseudonymizer.cli.commands.process.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.process.init_database"
        ):
            mock_passphrase.return_value = "testpassphrase123!"

            # Mock a successful processing result
            mock_result = type(
                "MockResult",
                (),
                {
                    "success": True,
                    "entities_detected": 5,
                    "entities_new": 3,
                    "entities_reused": 2,
                    "processing_time_seconds": 1.5,
                    "error_message": None,
                },
            )()
            mock_processor.return_value.process_document.return_value = mock_result

            result = runner.invoke(app, ["process", str(input_file)])

        assert result.exit_code == 0
        # Check that custom_db.db was passed to DocumentProcessor
        call_kwargs = mock_processor.call_args
        assert call_kwargs[1]["db_path"] == "custom_db.db"

    def test_cli_flag_overrides_config_theme(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test CLI --theme flag overrides config file value."""
        # Create project directory with config file
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / ".gdpr-pseudo.yaml"
        config_file.write_text(
            """
pseudonymization:
  theme: star_wars
"""
        )

        # Create test file
        input_file = project_dir / "input.txt"
        input_file.write_text("Test content")

        # Create empty home dir (no home config)
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        with patch(
            "gdpr_pseudonymizer.cli.commands.process.resolve_passphrase"
        ) as mock_passphrase, patch(
            "gdpr_pseudonymizer.cli.commands.process.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.process.init_database"
        ):
            mock_passphrase.return_value = "testpassphrase123!"

            # Mock a successful processing result
            mock_result = type(
                "MockResult",
                (),
                {
                    "success": True,
                    "entities_detected": 5,
                    "entities_new": 3,
                    "entities_reused": 2,
                    "processing_time_seconds": 1.5,
                    "error_message": None,
                },
            )()
            mock_processor.return_value.process_document.return_value = mock_result

            # CLI flag overrides config
            result = runner.invoke(app, ["process", str(input_file), "--theme", "lotr"])

        assert result.exit_code == 0
        # Check that lotr theme was used (CLI override)
        call_kwargs = mock_processor.call_args
        assert call_kwargs[1]["theme"] == "lotr"

    def test_cli_flag_overrides_config_db_path(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test CLI --db flag overrides config file value."""
        # Create project directory with config file
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_file = project_dir / ".gdpr-pseudo.yaml"
        config_file.write_text(
            """
database:
  path: config_db.db
"""
        )

        # Create test file
        input_file = project_dir / "input.txt"
        input_file.write_text("Test content")

        # Create empty home dir (no home config)
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        with patch(
            "gdpr_pseudonymizer.cli.commands.process.resolve_passphrase"
        ) as mock_passphrase, patch(
            "gdpr_pseudonymizer.cli.commands.process.DocumentProcessor"
        ) as mock_processor, patch(
            "gdpr_pseudonymizer.cli.commands.process.init_database"
        ):
            mock_passphrase.return_value = "testpassphrase123!"

            # Mock a successful processing result
            mock_result = type(
                "MockResult",
                (),
                {
                    "success": True,
                    "entities_detected": 5,
                    "entities_new": 3,
                    "entities_reused": 2,
                    "processing_time_seconds": 1.5,
                    "error_message": None,
                },
            )()
            mock_processor.return_value.process_document.return_value = mock_result

            # CLI flag overrides config
            result = runner.invoke(
                app, ["process", str(input_file), "--db", "cli_db.db"]
            )

        assert result.exit_code == 0
        # Check that cli_db.db was used (CLI override)
        call_kwargs = mock_processor.call_args
        assert call_kwargs[1]["db_path"] == "cli_db.db"


# Import pytest for MonkeyPatch type hint
import pytest  # noqa: E402
