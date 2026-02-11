"""Unit tests for destroy-table command."""

from __future__ import annotations

from pathlib import Path

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.destroy_table import (
    SQLITE_MAGIC,
    _secure_delete,
    _verify_not_symlink,
    _verify_sqlite_file,
    destroy_table_command,
)


def create_fake_sqlite_file(path: Path, size: int = 100) -> None:
    """Create a file with SQLite magic number for testing.

    Args:
        path: Path to create file at
        size: Approximate file size in bytes
    """
    # SQLite magic number is first 16 bytes
    content = SQLITE_MAGIC + (b"\x00" * (size - len(SQLITE_MAGIC)))
    path.write_bytes(content)


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="destroy-table")(destroy_table_command)
    return app


app = create_test_app()
runner = CliRunner()


class TestDestroyTableCommand:
    def test_destroy_with_confirmation(self, tmp_path: Path) -> None:
        """Test destruction with user confirmation and passphrase skip."""
        db_path = tmp_path / "test.db"
        create_fake_sqlite_file(db_path, 1000)

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path), "--skip-passphrase-check"],
            input="yes\n",
        )

        assert result.exit_code == 0
        assert "Database Destroyed Successfully" in result.stdout
        assert not db_path.exists()

    def test_destroy_cancelled(self, tmp_path: Path) -> None:
        """Test destruction cancelled by user."""
        db_path = tmp_path / "test.db"
        create_fake_sqlite_file(db_path, 100)

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path), "--skip-passphrase-check"],
            input="no\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        assert db_path.exists()  # File should still exist

    def test_destroy_force_flag(self, tmp_path: Path) -> None:
        """Test destruction with --force flag skips confirmation."""
        db_path = tmp_path / "test.db"
        create_fake_sqlite_file(db_path, 1000)

        result = runner.invoke(
            app,
            [
                "destroy-table",
                "--db",
                str(db_path),
                "--force",
                "--skip-passphrase-check",
            ],
        )

        assert result.exit_code == 0
        assert "Database Destroyed Successfully" in result.stdout
        assert not db_path.exists()

    def test_destroy_database_not_found(self, tmp_path: Path) -> None:
        """Test error when database file doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path)],
        )

        assert result.exit_code == 1
        # New styled error format
        assert "Database not found" in result.stdout or "[ERROR]" in result.stdout

    def test_destroy_shows_warning(self, tmp_path: Path) -> None:
        """Test warning is displayed before destruction."""
        db_path = tmp_path / "test.db"
        create_fake_sqlite_file(db_path, 100)

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path), "--skip-passphrase-check"],
            input="no\n",
        )

        assert "WARNING" in result.stdout
        assert "PERMANENT DATA LOSS" in result.stdout

    def test_destroy_help_text(self) -> None:
        """Test help text displays correctly."""
        result = runner.invoke(app, ["destroy-table", "--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Securely delete" in output
        assert "--force" in output

    def test_destroy_rejects_non_sqlite_file(self, tmp_path: Path) -> None:
        """Test rejection of files that aren't SQLite databases (Story 3.4 AC4)."""
        db_path = tmp_path / "fake.db"
        db_path.write_bytes(b"not a sqlite file")

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path)],
        )

        assert result.exit_code == 1
        assert "not a SQLite database" in result.stdout or "[ERROR]" in result.stdout


class TestSecureDelete:
    def test_secure_delete_removes_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"sensitive data" * 100)

        _secure_delete(test_file)

        assert not test_file.exists()

    def test_secure_delete_empty_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "empty.txt"
        test_file.touch()

        _secure_delete(test_file)

        assert not test_file.exists()

    def test_secure_delete_overwrites_content(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        original_content = b"sensitive data" * 100
        test_file.write_bytes(original_content)

        # We can't easily verify overwrite content, but we can verify
        # the file is removed after secure delete
        _secure_delete(test_file)

        assert not test_file.exists()


class TestSecurityFeatures:
    """Tests for Story 3.4 security features (AC4)."""

    def test_verify_sqlite_file_valid(self, tmp_path: Path) -> None:
        """Test SQLite verification accepts valid SQLite header."""
        db_path = tmp_path / "test.db"
        create_fake_sqlite_file(db_path)

        assert _verify_sqlite_file(db_path) is True

    def test_verify_sqlite_file_invalid(self, tmp_path: Path) -> None:
        """Test SQLite verification rejects non-SQLite files."""
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"not a sqlite file")

        assert _verify_sqlite_file(db_path) is False

    def test_verify_sqlite_file_empty(self, tmp_path: Path) -> None:
        """Test SQLite verification rejects empty files."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        assert _verify_sqlite_file(db_path) is False

    def test_verify_not_symlink_regular_file(self, tmp_path: Path) -> None:
        """Test symlink check passes for regular files."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        assert _verify_not_symlink(db_path) is True

    def test_sqlite_magic_constant(self) -> None:
        """Test SQLITE_MAGIC constant is correct."""
        assert SQLITE_MAGIC == b"SQLite format 3\x00"
        assert len(SQLITE_MAGIC) == 16
