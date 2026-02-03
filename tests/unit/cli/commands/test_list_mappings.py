"""Unit tests for list-mappings command.

Tests cover:
- Display all mappings
- --type filter (PERSON/LOCATION/ORG)
- --search filter
- CSV export
- Empty database case
- Argument parsing
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.list_mappings import (
    _export_to_csv,
    list_mappings_command,
)


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for reliable string matching."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


def create_test_app() -> typer.Typer:
    """Create a properly configured Typer app for testing."""
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        """Test app callback."""
        pass

    app.command(name="list-mappings")(list_mappings_command)
    return app


app = create_test_app()
runner = CliRunner()


def create_mock_entity(
    entity_type: str = "PERSON",
    full_name: str = "Marie Dubois",
    pseudonym_full: str = "Leia Organa",
    first_name: str = "Marie",
    last_name: str = "Dubois",
    pseudonym_first: str = "Leia",
    pseudonym_last: str = "Organa",
    theme: str = "star_wars",
    confidence_score: float = 0.95,
    is_ambiguous: bool = False,
) -> MagicMock:
    """Create a mock Entity object for testing."""
    entity = MagicMock()
    entity.entity_type = entity_type
    entity.full_name = full_name
    entity.first_name = first_name
    entity.last_name = last_name
    entity.pseudonym_full = pseudonym_full
    entity.pseudonym_first = pseudonym_first
    entity.pseudonym_last = pseudonym_last
    entity.theme = theme
    entity.confidence_score = confidence_score
    entity.is_ambiguous = is_ambiguous
    entity.first_seen_timestamp = datetime(2026, 1, 15, 10, 30, 0)
    return entity


class TestListMappingsCommand:
    """Tests for list-mappings command."""

    def test_list_all_mappings(self, tmp_path: Path) -> None:
        """Test listing all mappings."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [
            create_mock_entity(full_name="Marie Dubois"),
            create_mock_entity(full_name="Jean Martin"),
        ]

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.SQLiteMappingRepository"
        ) as mock_repo:
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(app, ["list-mappings", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Entity Mappings" in result.stdout
        assert "2 results" in result.stdout

    def test_list_mappings_type_filter(self, tmp_path: Path) -> None:
        """Test listing mappings with type filter."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [
            create_mock_entity(entity_type="PERSON"),
        ]

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.SQLiteMappingRepository"
        ) as mock_repo:
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(
                app, ["list-mappings", "--db", str(db_path), "--type", "PERSON"]
            )

            # Verify find_all was called with entity_type
            mock_repo.return_value.find_all.assert_called_once_with(
                entity_type="PERSON"
            )

        assert result.exit_code == 0

    def test_list_mappings_invalid_type(self, tmp_path: Path) -> None:
        """Test listing mappings with invalid type filter."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            app, ["list-mappings", "--db", str(db_path), "--type", "INVALID"]
        )

        assert result.exit_code == 1
        assert "Invalid Entity Type" in result.stdout

    def test_list_mappings_search_filter(self, tmp_path: Path) -> None:
        """Test listing mappings with search filter."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [
            create_mock_entity(full_name="Marie Dubois", pseudonym_full="Leia Organa"),
            create_mock_entity(
                full_name="Jean Martin", pseudonym_full="Luke Skywalker"
            ),
        ]

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.SQLiteMappingRepository"
        ) as mock_repo:
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(
                app, ["list-mappings", "--db", str(db_path), "--search", "marie"]
            )

        assert result.exit_code == 0
        # Only Marie Dubois should be displayed (case-insensitive search)
        assert "1 results" in result.stdout

    def test_list_mappings_csv_export(self, tmp_path: Path) -> None:
        """Test exporting mappings to CSV."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        export_path = tmp_path / "export.csv"

        mock_entities = [
            create_mock_entity(full_name="Marie Dubois"),
        ]

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.SQLiteMappingRepository"
        ) as mock_repo:
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(
                app,
                ["list-mappings", "--db", str(db_path), "--export", str(export_path)],
            )

        assert result.exit_code == 0
        assert "Exported" in result.stdout
        assert export_path.exists()

        # Verify CSV content
        content = export_path.read_text()
        assert "entity_type" in content
        assert "full_name" in content
        assert "Marie Dubois" in content

    def test_list_mappings_empty_database(self, tmp_path: Path) -> None:
        """Test listing mappings from empty database."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.SQLiteMappingRepository"
        ) as mock_repo:
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = []

            result = runner.invoke(app, ["list-mappings", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "No mappings found" in result.stdout

    def test_list_mappings_database_not_found(self, tmp_path: Path) -> None:
        """Test listing mappings when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(app, ["list-mappings", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_list_mappings_limit(self, tmp_path: Path) -> None:
        """Test listing mappings with limit."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity(full_name=f"Person {i}") for i in range(10)]

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.SQLiteMappingRepository"
        ) as mock_repo:
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(
                app, ["list-mappings", "--db", str(db_path), "--limit", "5"]
            )

        assert result.exit_code == 0
        assert "5 results" in result.stdout

    def test_list_mappings_help_text(self) -> None:
        """Test list-mappings command help text is displayed."""
        result = runner.invoke(app, ["list-mappings", "--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "View entity-to-pseudonym mappings" in output
        assert "--type" in output
        assert "--search" in output
        assert "--export" in output

    def test_list_mappings_wrong_passphrase(self, tmp_path: Path) -> None:
        """Test listing mappings with wrong passphrase."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.resolve_passphrase"
        ) as mock_resolve, patch(
            "gdpr_pseudonymizer.cli.commands.list_mappings.open_database"
        ) as mock_open_db:
            mock_resolve.return_value = "wrongpassphrase123!"
            mock_open_db.side_effect = ValueError("Incorrect passphrase")

            result = runner.invoke(app, ["list-mappings", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Authentication Failed" in result.stdout


class TestExportToCsv:
    """Tests for CSV export functionality."""

    def test_export_creates_file(self, tmp_path: Path) -> None:
        """Test that export creates CSV file."""
        output_path = tmp_path / "export.csv"
        entities = [create_mock_entity()]

        _export_to_csv(entities, output_path)

        assert output_path.exists()

    def test_export_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that export creates parent directories."""
        output_path = tmp_path / "subdir" / "export.csv"
        entities = [create_mock_entity()]

        _export_to_csv(entities, output_path)

        assert output_path.exists()

    def test_export_csv_headers(self, tmp_path: Path) -> None:
        """Test that exported CSV has correct headers."""
        output_path = tmp_path / "export.csv"
        entities = [create_mock_entity()]

        _export_to_csv(entities, output_path)

        content = output_path.read_text()
        expected_headers = [
            "entity_type",
            "full_name",
            "first_name",
            "last_name",
            "pseudonym_full",
            "pseudonym_first",
            "pseudonym_last",
            "theme",
            "confidence_score",
            "is_ambiguous",
            "first_seen_timestamp",
        ]
        for header in expected_headers:
            assert header in content

    def test_export_csv_data(self, tmp_path: Path) -> None:
        """Test that exported CSV contains entity data."""
        output_path = tmp_path / "export.csv"
        entities = [
            create_mock_entity(
                full_name="Marie Dubois",
                pseudonym_full="Leia Organa",
                theme="star_wars",
            )
        ]

        _export_to_csv(entities, output_path)

        content = output_path.read_text()
        assert "Marie Dubois" in content
        assert "Leia Organa" in content
        assert "star_wars" in content
