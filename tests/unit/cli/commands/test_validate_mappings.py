"""Unit tests for validate-mappings command."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.validate_mappings import validate_mappings_command


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="validate-mappings")(validate_mappings_command)
    return app


app = create_test_app()
runner = CliRunner()


def create_mock_entity(
    entity_type: str = "PERSON",
    full_name: str = "Marie Dubois",
    pseudonym_full: str = "Leia Organa",
    confidence_score: float = 0.95,
    is_ambiguous: bool = False,
) -> MagicMock:
    entity = MagicMock()
    entity.entity_type = entity_type
    entity.full_name = full_name
    entity.pseudonym_full = pseudonym_full
    entity.confidence_score = confidence_score
    entity.is_ambiguous = is_ambiguous
    entity.theme = "star_wars"
    entity.first_seen_timestamp = datetime(2026, 1, 15, 10, 30, 0)
    return entity


class TestValidateMappingsCommand:
    def test_validate_displays_mappings(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Mapping Validation Review" in result.stdout

    def test_validate_empty_database(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db_path.touch()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = []

            result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "No mappings found" in result.stdout

    def test_validate_database_not_found(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nonexistent.db"

        result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Database Not Found" in result.stdout

    def test_validate_help_text(self) -> None:
        result = runner.invoke(app, ["validate-mappings", "--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Review existing mappings" in output
        assert "--interactive" in output

    def test_validate_with_type_filter(self, tmp_path: Path) -> None:
        """Test validate-mappings with --type filter."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity(entity_type="PERSON")]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(
                app, ["validate-mappings", "--db", str(db_path), "--type", "PERSON"]
            )

        assert result.exit_code == 0
        mock_repo.return_value.find_all.assert_called_once_with(entity_type="PERSON")

    def test_validate_invalid_entity_type(self, tmp_path: Path) -> None:
        """Test validate-mappings with invalid entity type."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            app, ["validate-mappings", "--db", str(db_path), "--type", "INVALID"]
        )

        assert result.exit_code == 1
        assert "Invalid Entity Type" in result.stdout

    def test_validate_displays_ambiguous_flag(self, tmp_path: Path) -> None:
        """Test that ambiguous entities are flagged in display."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity(is_ambiguous=True)]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Ambiguous" in result.stdout

    def test_validate_displays_low_confidence_flag(self, tmp_path: Path) -> None:
        """Test that low confidence entities are flagged in display."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity(confidence_score=0.5)]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities

            result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Low confidence" in result.stdout

    def test_validate_interactive_mode(self, tmp_path: Path) -> None:
        """Test validate-mappings in interactive mode."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities
            mock_confirm.return_value = False  # Don't flag

            result = runner.invoke(
                app, ["validate-mappings", "--db", str(db_path), "--interactive"]
            )

        assert result.exit_code == 0
        assert "Interactive Mapping Review" in result.stdout
        assert "Review Complete" in result.stdout

    def test_validate_interactive_with_flagging(self, tmp_path: Path) -> None:
        """Test interactive mode with flagging a mapping."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        mock_entities = [create_mock_entity()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.SQLiteMappingRepository"
            ) as mock_repo,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities
            mock_confirm.return_value = True  # Flag this mapping

            result = runner.invoke(
                app, ["validate-mappings", "--db", str(db_path), "--interactive"]
            )

        assert result.exit_code == 0
        assert "Flagged: 1" in result.stdout

    def test_validate_authentication_error(self, tmp_path: Path) -> None:
        """Test validate-mappings with authentication error."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
        ):
            mock_resolve.return_value = "wrongpassphrase!!"
            mock_open_db.side_effect = ValueError("Invalid passphrase")

            result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "Authentication Failed" in result.stdout

    def test_validate_unexpected_error(self, tmp_path: Path) -> None:
        """Test validate-mappings with unexpected error."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.validate_mappings.open_database"
            ) as mock_open_db,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.side_effect = RuntimeError("Unexpected error")

            result = runner.invoke(app, ["validate-mappings", "--db", str(db_path)])

        assert result.exit_code == 2
        assert "Unexpected Error" in result.stdout
