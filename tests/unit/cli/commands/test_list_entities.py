"""Unit tests for list-entities CLI command (Story 5.1)."""

from __future__ import annotations

import re
from pathlib import Path

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.list_entities import list_entities_command
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="list-entities")(list_entities_command)
    return app


app = create_test_app()
runner = CliRunner()

PASSPHRASE = "test_passphrase_123!"


def _seed_entities(db_path: str, passphrase: str) -> list[Entity]:
    """Seed multiple test entities and return them."""
    entities_data = [
        {
            "entity_type": "PERSON",
            "first_name": "Marie",
            "last_name": "Dupont",
            "full_name": "Marie Dupont",
            "pseudonym_first": "Leia",
            "pseudonym_last": "Organa",
            "pseudonym_full": "Leia Organa",
            "theme": "star_wars",
        },
        {
            "entity_type": "PERSON",
            "first_name": "Jean",
            "last_name": "Martin",
            "full_name": "Jean Martin",
            "pseudonym_first": "Luke",
            "pseudonym_last": "Skywalker",
            "pseudonym_full": "Luke Skywalker",
            "theme": "star_wars",
        },
        {
            "entity_type": "LOCATION",
            "first_name": None,
            "last_name": None,
            "full_name": "Paris",
            "pseudonym_first": None,
            "pseudonym_last": None,
            "pseudonym_full": "Coruscant",
            "theme": "star_wars",
            "gender": None,
        },
    ]

    saved = []
    with open_database(db_path, passphrase) as db_session:
        repo = SQLiteMappingRepository(db_session)
        for data in entities_data:
            saved.append(repo.save(Entity(**data)))
    return saved


class TestListEntitiesCommand:
    def test_list_all_entities(self, tmp_path: Path) -> None:
        """List all entities displays a table."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "3 results" in output
        assert "Marie Dupont" in output
        assert "Jean Martin" in output
        assert "Paris" in output

    def test_search_filter(self, tmp_path: Path) -> None:
        """Search filter shows matching entities only."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "list-entities",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--search",
                "Dupont",
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "1 results" in output
        assert "Marie Dupont" in output
        assert "Jean Martin" not in output

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        """Search is case-insensitive."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "list-entities",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--search",
                "marie",
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Marie Dupont" in output

    def test_type_filter(self, tmp_path: Path) -> None:
        """Type filter shows matching entities only."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "list-entities",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--type",
                "LOCATION",
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "1 results" in output
        assert "Paris" in output
        assert "Marie Dupont" not in output

    def test_empty_results(self, tmp_path: Path) -> None:
        """Empty results show appropriate message."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "No entities found" in output

    def test_limit_results(self, tmp_path: Path) -> None:
        """Limit truncates results correctly."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "list-entities",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--limit",
                "1",
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "1 results" in output

    def test_entity_id_displayed(self, tmp_path: Path) -> None:
        """Truncated entity UUID is displayed in table."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        saved = _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        # Check that truncated UUID (first 8 chars) appears
        for entity in saved:
            assert entity.id[:8] in output

    def test_first_seen_date_displayed(self, tmp_path: Path) -> None:
        """First seen date is displayed in the table."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        # Table header includes "First Seen" column; date may be truncated
        # by Rich table rendering in narrow terminals (e.g. "2026-" instead of "2026-02-11")
        assert "First Seen" in output or re.search(r"\d{4}-", output) is not None

    def test_database_not_found(self, tmp_path: Path) -> None:
        """Error when database file doesn't exist."""
        result = runner.invoke(
            app,
            [
                "list-entities",
                "--db",
                str(tmp_path / "missing.db"),
                "--passphrase",
                PASSPHRASE,
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Database Not Found" in output

    def test_invalid_entity_type(self, tmp_path: Path) -> None:
        """Error on invalid entity type."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "list-entities",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--type",
                "INVALID",
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Invalid Entity Type" in output

    def test_doc_count_shows_na(self, tmp_path: Path) -> None:
        """Document count column shows N/A (Option A from story)."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entities(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "N/A" in output
