"""Unit tests for init command.

Tests cover:
- Successful database initialization
- Passphrase validation (min 12 characters)
- Existing database error
- --force override behavior
- Argument parsing
- Error handling (permissions, invalid paths)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.init import init_command


def create_test_app() -> typer.Typer:
    """Create a properly configured Typer app for testing."""
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        """Test app callback."""
        pass

    app.command(name="init")(init_command)
    return app


app = create_test_app()
runner = CliRunner()


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_database(self, tmp_path: Path) -> None:
        """Test init command creates database with valid passphrase."""
        db_path = tmp_path / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(app, ["init", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Database Initialized Successfully" in result.stdout
        assert db_path.exists()

    def test_init_shows_database_path(self, tmp_path: Path) -> None:
        """Test init command displays database path on success."""
        db_path = tmp_path / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(app, ["init", "--db", str(db_path)])

        assert result.exit_code == 0
        # Rich may wrap long paths with newlines, so check for the filename
        assert "test.db" in result.stdout
        assert "Database path:" in result.stdout

    def test_init_fails_if_database_exists(self, tmp_path: Path) -> None:
        """Test init command fails if database already exists."""
        db_path = tmp_path / "existing.db"
        db_path.touch()  # Create empty file

        result = runner.invoke(app, ["init", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Database Already Exists" in result.stdout
        assert "--force" in result.stdout

    def test_init_force_overwrites_existing_database(self, tmp_path: Path) -> None:
        """Test init command with --force overwrites existing database."""
        db_path = tmp_path / "existing.db"
        db_path.write_text("old data")

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(app, ["init", "--db", str(db_path), "--force"])

        assert result.exit_code == 0
        assert "Database Initialized Successfully" in result.stdout
        # Verify old content replaced
        assert db_path.read_bytes() != b"old data"

    def test_init_validates_passphrase_minimum_length(self, tmp_path: Path) -> None:
        """Test init command validates passphrase minimum length."""
        db_path = tmp_path / "test.db"

        # Mock resolve_passphrase to simulate validation failure
        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            # Simulate sys.exit(1) from passphrase validation
            mock_resolve.side_effect = SystemExit(1)

            result = runner.invoke(app, ["init", "--db", str(db_path)])

        assert result.exit_code == 1
        assert not db_path.exists()

    def test_init_uses_cli_passphrase_flag(self, tmp_path: Path) -> None:
        """Test init command accepts passphrase via CLI flag."""
        db_path = tmp_path / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "clipassphrase123!"

            result = runner.invoke(
                app, ["init", "--db", str(db_path), "--passphrase", "clipassphrase123!"]
            )

            # Verify resolve_passphrase was called with CLI passphrase
            mock_resolve.assert_called_once()
            call_args = mock_resolve.call_args
            assert call_args.kwargs["cli_passphrase"] == "clipassphrase123!"

        assert result.exit_code == 0

    def test_init_default_database_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test init command uses default database path."""
        monkeypatch.chdir(tmp_path)

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (tmp_path / "mappings.db").exists()

    def test_init_handles_invalid_path(self, tmp_path: Path) -> None:
        """Test init command handles invalid database path."""
        # Path to non-existent directory
        invalid_path = tmp_path / "nonexistent" / "dir" / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(app, ["init", "--db", str(invalid_path)])

        # Should fail due to invalid path
        assert result.exit_code != 0

    def test_init_help_text(self) -> None:
        """Test init command help text is displayed."""
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize a new encrypted mapping database" in result.stdout
        assert "--db" in result.stdout
        assert "--passphrase" in result.stdout
        assert "--force" in result.stdout

    def test_init_keyboard_interrupt(self, tmp_path: Path) -> None:
        """Test init command handles keyboard interrupt gracefully."""
        db_path = tmp_path / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.side_effect = KeyboardInterrupt()

            result = runner.invoke(app, ["init", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()


class TestInitCommandPassphraseIntegration:
    """Integration tests for passphrase handling in init command."""

    def test_passphrase_confirmation_required(self, tmp_path: Path) -> None:
        """Test that passphrase confirmation is requested for new database."""
        db_path = tmp_path / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            runner.invoke(app, ["init", "--db", str(db_path)])

            # Verify confirm=True was passed
            mock_resolve.assert_called_once()
            call_args = mock_resolve.call_args
            assert call_args.kwargs["confirm"] is True

    def test_init_with_short_flag(self, tmp_path: Path) -> None:
        """Test init command accepts short flags."""
        db_path = tmp_path / "test.db"

        with patch(
            "gdpr_pseudonymizer.cli.commands.init.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(
                app, ["init", "--db", str(db_path), "-p", "shortflagpass123!"]
            )

            # Verify -p flag works
            mock_resolve.assert_called_once()
            call_args = mock_resolve.call_args
            assert call_args.kwargs["cli_passphrase"] == "shortflagpass123!"

        assert result.exit_code == 0
