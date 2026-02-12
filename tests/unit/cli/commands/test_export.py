"""Unit tests for export command."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.export import export_command
from gdpr_pseudonymizer.cli.main import app as main_app


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="export")(export_command)
    return app


app = create_test_app()
runner = CliRunner()


def create_mock_operation() -> MagicMock:
    op = MagicMock()
    op.operation_type = "PROCESS"
    op.timestamp = datetime(2026, 1, 15, 10, 30, 0)
    op.entity_count = 5
    op.success = True
    return op


class TestExportCommand:
    def test_export_json(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        mock_operations = [create_mock_operation()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path)],
            )

        assert result.exit_code == 0
        assert "Exported" in result.stdout

    def test_export_csv(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.csv"

        mock_operations = [create_mock_operation()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path)],
            )

        assert result.exit_code == 0
        assert "Exported" in result.stdout

    def test_export_invalid_format(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.txt"

        result = runner.invoke(
            app,
            ["export", str(output_path), "--db", str(db_path)],
        )

        assert result.exit_code == 1
        assert "Invalid Output Format" in result.stdout

    def test_export_database_not_found(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nonexistent.db"
        output_path = tmp_path / "export.json"

        result = runner.invoke(
            app,
            ["export", str(output_path), "--db", str(db_path)],
        )

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_export_date_filter(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        mock_operations = [create_mock_operation()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(
                app,
                [
                    "export",
                    str(output_path),
                    "--db",
                    str(db_path),
                    "--from",
                    "2026-01-01",
                    "--to",
                    "2026-01-31",
                ],
            )

        assert result.exit_code == 0

    def test_export_invalid_date(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        with patch(
            "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
        ) as mock_resolve:
            mock_resolve.return_value = "testpassphrase123!"

            result = runner.invoke(
                app,
                [
                    "export",
                    str(output_path),
                    "--db",
                    str(db_path),
                    "--from",
                    "invalid-date",
                ],
            )

        assert result.exit_code == 1
        assert "Invalid Date Format" in result.stdout

    def test_export_help_text(self) -> None:
        result = runner.invoke(app, ["export", "--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Export audit log" in output
        assert "--type" in output
        assert "--from" in output
        assert "--to" in output

    def test_export_empty_operations(self, tmp_path: Path) -> None:
        """Test export with no operations."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = []

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path)],
            )

        assert result.exit_code == 0
        # Exports 0 operations when database is empty
        assert "0 operations" in result.stdout

    def test_export_with_type_filter(self, tmp_path: Path) -> None:
        """Test export with --type filter."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        mock_operations = [create_mock_operation()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path), "--type", "PROCESS"],
            )

        assert result.exit_code == 0
        mock_repo.return_value.find_operations.assert_called_once()

    def test_export_success_only_filter(self, tmp_path: Path) -> None:
        """Test export with --success-only filter."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        mock_operations = [create_mock_operation()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path), "--success-only"],
            )

        assert result.exit_code == 0

    def test_export_failures_only_filter(self, tmp_path: Path) -> None:
        """Test export with --failures-only filter via main app wrapper."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        mock_operations = [create_mock_operation()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.AuditRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(
                main_app,
                ["export", str(output_path), "--db", str(db_path), "--failures-only"],
            )

        assert result.exit_code == 0

    def test_export_authentication_error(self, tmp_path: Path) -> None:
        """Test export with authentication error."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
        ):
            mock_resolve.return_value = "wrongpassphrase!!"
            mock_open_db.side_effect = ValueError("Invalid passphrase")

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path)],
            )

        assert result.exit_code == 1
        assert "Authentication Failed" in result.stdout

    def test_export_unexpected_error(self, tmp_path: Path) -> None:
        """Test export with unexpected error."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        output_path = tmp_path / "export.json"

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.export.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.export.open_database"
            ) as mock_open_db,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.side_effect = RuntimeError("Unexpected error")

            result = runner.invoke(
                app,
                ["export", str(output_path), "--db", str(db_path)],
            )

        assert result.exit_code == 2
        assert "Unexpected Error" in result.stdout
