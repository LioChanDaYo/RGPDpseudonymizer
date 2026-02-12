"""Integration tests for CLI commands.

Tests verify:
- All commands are registered
- Help text displays correctly for all commands
- Global options work across commands
- Config file loading
"""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app

# CliRunner for testing CLI commands
runner = CliRunner(mix_stderr=False)


class TestCLICommandRegistration:
    """Tests verifying all commands are registered."""

    def test_all_commands_registered(self) -> None:
        """Verify all 9 commands are registered in the app."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0

        # Check all commands are listed in help
        expected_commands = [
            "init",
            "process",
            "batch",
            "list-mappings",
            "validate-mappings",
            "stats",
            "import-mappings",
            "export",
            "destroy-table",
        ]

        for cmd in expected_commands:
            assert cmd in result.stdout, f"Command '{cmd}' not found in help output"

    def test_main_help_displays(self) -> None:
        """Test main help text displays correctly."""
        result = runner.invoke(app, ["--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "GDPR-compliant pseudonymization tool" in output
        assert "--version" in output
        assert "--config" in output
        assert "--verbose" in output
        assert "--quiet" in output


class TestCommandHelp:
    """Tests for individual command help text."""

    @pytest.mark.parametrize(
        "command,expected_text",
        [
            ("init", "Initialize a new encrypted mapping database"),
            ("process", "Process"),
            ("batch", "Process multiple documents"),
            ("list-mappings", "View entity-to-pseudonym mappings"),
            ("validate-mappings", "Review existing mappings"),
            ("stats", "Show database statistics"),
            ("import-mappings", "Import mappings from another database"),
            ("export", "Export audit log"),
            ("destroy-table", "Securely delete"),
        ],
    )
    def test_command_help(self, command: str, expected_text: str) -> None:
        """Test each command has help text."""
        result = runner.invoke(app, [command, "--help"])

        assert result.exit_code == 0
        assert expected_text in result.stdout, f"Expected text not found for {command}"


class TestGlobalOptions:
    """Tests for global options."""

    def test_version_option(self) -> None:
        """Test --version displays version."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "gdpr-pseudo version" in result.stdout

    def test_config_option_nonexistent(self, tmp_path: Path) -> None:
        """Test --config with non-existent file."""
        config_path = tmp_path / "nonexistent.yaml"

        result = runner.invoke(app, ["--config", str(config_path), "stats", "--help"])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_config_option_with_invalid_config(self, tmp_path: Path) -> None:
        """Test --config with invalid config file."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("pseudonymization:\n  theme: invalid_theme")

        result = runner.invoke(app, ["--config", str(config_path), "stats", "--help"])

        assert result.exit_code == 1
        assert "Invalid theme" in result.stdout

    def test_config_option_with_passphrase_rejected(self, tmp_path: Path) -> None:
        """SECURITY TEST: Config with passphrase is rejected."""
        config_path = tmp_path / "insecure.yaml"
        config_path.write_text("database:\n  passphrase: secret123")

        result = runner.invoke(app, ["--config", str(config_path), "stats", "--help"])

        assert result.exit_code == 1
        assert "Security Error" in result.stdout

    def test_config_option_with_valid_config(self, tmp_path: Path) -> None:
        """Test --config with valid config file."""
        config_path = tmp_path / "valid.yaml"
        config_path.write_text(
            """
database:
  path: custom.db
pseudonymization:
  theme: star_wars
"""
        )

        # Should succeed and display help
        result = runner.invoke(app, ["--config", str(config_path), "--help"])

        assert result.exit_code == 0

    def test_verbose_and_quiet_flags_exist(self) -> None:
        """Test that both --verbose and --quiet flags are available."""
        result = runner.invoke(app, ["--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "--verbose" in output
        assert "--quiet" in output


class TestCommandExecution:
    """Tests for command execution."""

    def test_init_creates_database(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test init command creates database."""
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "test.db"

        # Set passphrase via environment
        monkeypatch.setenv("GDPR_PSEUDO_PASSPHRASE", "testpassphrase123!")

        result = runner.invoke(app, ["init", "--db", str(db_path)])

        assert result.exit_code == 0
        assert db_path.exists()

    def test_stats_requires_database(self, tmp_path: Path) -> None:
        """Test stats command requires existing database."""
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(app, ["stats", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_list_mappings_requires_database(self, tmp_path: Path) -> None:
        """Test list-mappings command requires existing database."""
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(app, ["list-mappings", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_destroy_table_requires_confirmation(self, tmp_path: Path) -> None:
        """Test destroy-table requires confirmation."""
        db_path = tmp_path / "test.db"
        # Must include SQLite magic header for security verification (Story 3.4)
        sqlite_magic = b"SQLite format 3\x00"
        db_path.write_bytes(sqlite_magic + b"\x00" * 100)

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path), "--skip-passphrase-check"],
            input="no\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        assert db_path.exists()  # File should still exist
