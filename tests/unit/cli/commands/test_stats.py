"""Unit tests for stats command."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.stats import stats_command


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="stats")(stats_command)
    return app


app = create_test_app()
runner = CliRunner()


def create_mock_entity(entity_type: str = "PERSON", theme: str = "neutral") -> MagicMock:
    entity = MagicMock()
    entity.entity_type = entity_type
    entity.theme = theme
    entity.is_ambiguous = False
    return entity


def create_mock_operation(success: bool = True) -> MagicMock:
    op = MagicMock()
    op.operation_type = "PROCESS"
    op.timestamp = datetime(2026, 1, 15, 10, 30, 0)
    op.entity_count = 5
    op.success = success
    op.error_message = None if success else "Test error"
    return op


class TestStatsCommand:
    def test_stats_displays_info(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"test" * 100)  # Create file with some content

        mock_entities = [create_mock_entity()]
        mock_operations = [create_mock_operation()]

        with patch(
            "gdpr_pseudonymizer.cli.commands.stats.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.stats.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.stats.SQLiteMappingRepository"
        ) as mock_mapping_repo, patch(
            "gdpr_pseudonymizer.cli.commands.stats.AuditRepository"
        ) as mock_audit_repo:
            mock_resolve.return_value = "testpassphrase123!"
            db_session = MagicMock()
            mock_open_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_mapping_repo.return_value.find_all.return_value = mock_entities
            mock_audit_repo.return_value.find_operations.return_value = mock_operations

            result = runner.invoke(app, ["stats", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Database Statistics" in result.stdout
        assert "Entity Counts" in result.stdout

    def test_stats_database_not_found(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(app, ["stats", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_stats_help_text(self) -> None:
        result = runner.invoke(app, ["stats", "--help"])

        assert result.exit_code == 0
        assert "Show database statistics" in result.stdout
