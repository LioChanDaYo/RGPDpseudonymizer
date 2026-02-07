"""Unit tests for import-mappings command."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.import_mappings import import_mappings_command


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for reliable string matching."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="import-mappings")(import_mappings_command)
    return app


app = create_test_app()
runner = CliRunner()


def create_mock_entity(full_name: str = "Marie Dubois") -> MagicMock:
    entity = MagicMock()
    entity.entity_type = "PERSON"
    entity.full_name = full_name
    entity.first_name = "Marie"
    entity.last_name = "Dubois"
    entity.pseudonym_full = "Leia Organa"
    entity.pseudonym_first = "Leia"
    entity.pseudonym_last = "Organa"
    entity.theme = "star_wars"
    entity.confidence_score = 0.95
    entity.is_ambiguous = False
    entity.ambiguity_reason = None
    entity.gender = None
    return entity


class TestImportMappingsCommand:
    def test_import_successful(self, tmp_path: Path) -> None:
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "target.db"
        source_db.touch()
        target_db.touch()

        mock_entities = [create_mock_entity()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities
            mock_repo.return_value.find_by_full_name.return_value = None

            result = runner.invoke(
                app,
                ["import-mappings", str(source_db), "--db", str(target_db)],
            )

        assert result.exit_code == 0
        assert "Import Complete" in result.stdout

    def test_import_source_not_found(self, tmp_path: Path) -> None:
        source_db = tmp_path / "nonexistent.db"
        target_db = tmp_path / "target.db"
        target_db.touch()

        result = runner.invoke(
            app,
            ["import-mappings", str(source_db), "--db", str(target_db)],
        )

        assert result.exit_code == 2  # Typer invalid argument

    def test_import_target_not_found(self, tmp_path: Path) -> None:
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "nonexistent.db"
        source_db.touch()

        result = runner.invoke(
            app,
            ["import-mappings", str(source_db), "--db", str(target_db)],
        )

        assert result.exit_code == 1
        assert "Target Database Not Found" in result.stdout

    def test_import_same_file_error(self, tmp_path: Path) -> None:
        db_path = tmp_path / "same.db"
        db_path.touch()

        result = runner.invoke(
            app,
            ["import-mappings", str(db_path), "--db", str(db_path)],
        )

        assert result.exit_code == 1
        assert "same file" in result.stdout

    def test_import_help_text(self) -> None:
        result = runner.invoke(app, ["import-mappings", "--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Import mappings from another database" in output
        assert "--source-passphrase" in output

    def test_import_empty_source(self, tmp_path: Path) -> None:
        """Test import from empty source database."""
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "target.db"
        source_db.touch()
        target_db.touch()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = []  # Empty source

            result = runner.invoke(
                app,
                ["import-mappings", str(source_db), "--db", str(target_db)],
            )

        assert result.exit_code == 0
        assert "No entities found" in result.stdout

    def test_import_skips_duplicates_by_default(self, tmp_path: Path) -> None:
        """Test that duplicates are skipped by default."""
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "target.db"
        source_db.touch()
        target_db.touch()

        mock_entities = [create_mock_entity()]
        existing_entity = create_mock_entity()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities
            mock_repo.return_value.find_by_full_name.return_value = existing_entity

            result = runner.invoke(
                app,
                ["import-mappings", str(source_db), "--db", str(target_db)],
            )

        assert result.exit_code == 0
        assert "Skipped:  1" in result.stdout

    def test_import_source_db_authentication_error(self, tmp_path: Path) -> None:
        """Test import with source database authentication error."""
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "target.db"
        source_db.touch()
        target_db.touch()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.open_database"
            ) as mock_open_db,
        ):
            mock_resolve.return_value = "wrongpassphrase!!"
            mock_open_db.side_effect = ValueError("Invalid passphrase")

            result = runner.invoke(
                app,
                ["import-mappings", str(source_db), "--db", str(target_db)],
            )

        assert result.exit_code == 1
        assert (
            "Source Database Error" in result.stdout
            or "Authentication Failed" in result.stdout
        )

    def test_import_unexpected_error(self, tmp_path: Path) -> None:
        """Test import with unexpected error."""
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "target.db"
        source_db.touch()
        target_db.touch()

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.open_database"
            ) as mock_open_db,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.side_effect = RuntimeError("Unexpected error")

            result = runner.invoke(
                app,
                ["import-mappings", str(source_db), "--db", str(target_db)],
            )

        assert result.exit_code == 2
        assert "Unexpected Error" in result.stdout

    def test_import_with_import_errors(self, tmp_path: Path) -> None:
        """Test import with entity save errors."""
        source_db = tmp_path / "source.db"
        target_db = tmp_path / "target.db"
        source_db.touch()
        target_db.touch()

        mock_entities = [create_mock_entity()]

        with (
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.resolve_passphrase"
            ) as mock_resolve,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.open_database"
            ) as mock_open_db,
            patch(
                "gdpr_pseudonymizer.cli.commands.import_mappings.SQLiteMappingRepository"
            ) as mock_repo,
        ):
            mock_resolve.return_value = "testpassphrase123!"
            mock_open_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_repo.return_value.find_all.return_value = mock_entities
            mock_repo.return_value.find_by_full_name.return_value = None
            mock_repo.return_value.save.side_effect = Exception("Save failed")

            result = runner.invoke(
                app,
                ["import-mappings", str(source_db), "--db", str(target_db)],
            )

        assert result.exit_code == 0
        assert "Errors:   1" in result.stdout
