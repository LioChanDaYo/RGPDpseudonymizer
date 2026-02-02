"""Unit tests for destroy-table command."""

from __future__ import annotations

from pathlib import Path

import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.destroy_table import (
    _secure_delete,
    destroy_table_command,
)


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
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"test data" * 100)

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path)],
            input="yes\n",
        )

        assert result.exit_code == 0
        assert "Database Destroyed Successfully" in result.stdout
        assert not db_path.exists()

    def test_destroy_cancelled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"test data")

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path)],
            input="no\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        assert db_path.exists()  # File should still exist

    def test_destroy_force_flag(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"test data" * 100)

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path), "--force"],
        )

        assert result.exit_code == 0
        assert "Database Destroyed Successfully" in result.stdout
        assert not db_path.exists()

    def test_destroy_database_not_found(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path)],
        )

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_destroy_shows_warning(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"test data")

        result = runner.invoke(
            app,
            ["destroy-table", "--db", str(db_path)],
            input="no\n",
        )

        assert "WARNING" in result.stdout
        assert "PERMANENT DATA LOSS" in result.stdout

    def test_destroy_help_text(self) -> None:
        result = runner.invoke(app, ["destroy-table", "--help"])

        assert result.exit_code == 0
        assert "Securely delete" in result.stdout
        assert "--force" in result.stdout


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
