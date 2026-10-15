"""Story 10.7, AC4: delete-mapping with one name stored under two types.

By name, every row of the name is listed and deleted, with one ERASURE audit
entry per row; by ``--id``, one row is deleted and the output says which rows
of the same name remain. Driven through the CLI runner on a real temporary
database. Invented names only (AC11).
"""

from __future__ import annotations

from pathlib import Path

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.delete_mapping import delete_mapping_command
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DuplicateEntityError


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="delete-mapping")(delete_mapping_command)
    return app


app = create_test_app()
runner = CliRunner()

PASSPHRASE = "zorbalia_delete_pass_123!"


def _seed(db_path: str, *rows: tuple[str, str, str, str]) -> list[Entity]:
    """Store (type, name, pseudonym, theme) rows; return the stored ones.

    A row the database rejects as a duplicate text is left out, so the tests
    run (and fail on their assertions) against the code before Story 10.7.
    """
    stored: list[Entity] = []
    with open_database(db_path, PASSPHRASE) as session:
        repo = SQLiteMappingRepository(session)
        for entity_type, name, pseudonym, theme in rows:
            try:
                stored.append(
                    repo.save(
                        Entity(
                            entity_type=entity_type,
                            full_name=name,
                            pseudonym_full=pseudonym,
                            theme=theme,
                        )
                    )
                )
            except DuplicateEntityError:
                pass
    return stored


def _stored_rows(db_path: str) -> list[tuple[str, str]]:
    with open_database(db_path, PASSPHRASE) as session:
        return sorted(
            (e.full_name, e.entity_type)
            for e in SQLiteMappingRepository(session).find_all()
        )


def _erasures(db_path: str) -> list[dict[str, object]]:
    with open_database(db_path, PASSPHRASE) as session:
        operations = AuditRepository(session.session).find_operations(
            operation_type="ERASURE"
        )
        return [
            {
                "entity_count": op.entity_count,
                "success": op.success,
                "theme": op.theme_selected,
                **(op.user_modifications or {}),
            }
            for op in operations
        ]


def _invoke(*args: str, answer: str | None = None) -> tuple[int, str]:
    result = runner.invoke(
        app,
        ["delete-mapping", *args, "--passphrase", PASSPHRASE],
        input=answer,
    )
    return result.exit_code, strip_ansi(result.output)


TWO_TYPES = (
    ("LOCATION", "Zorbaville", "Quentrel", "neutral"),
    ("ORG", "Zorbaville", "Zorbtech Group", "star_wars"),
    ("PERSON", "Zorbalia Quentrix", "Quentrix Zorbtech", "neutral"),
)


class TestDeleteByName:
    def test_confirmation_lists_every_row_and_yes_deletes_all(
        self, tmp_path: Path
    ) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        _seed(db_path, *TWO_TYPES)

        code, output = _invoke("Zorbaville", "--db", db_path, answer="yes\n")

        assert code == 0, output
        confirmation = output.split("Type 'yes'")[0]
        for expected in ("LOCATION", "Quentrel", "neutral"):
            assert expected in confirmation
        for expected in ("ORG", "Zorbtech Group", "star_wars"):
            assert expected in confirmation
        assert "deleted successfully" in output
        result_part = output.split("Type 'yes'")[1]
        assert "Quentrel" in result_part and "Zorbtech Group" in result_part
        assert _stored_rows(db_path) == [("Zorbalia Quentrix", "PERSON")]
        erasures = sorted(
            _erasures(db_path), key=lambda e: str(e["deleted_entity_type"])
        )
        assert [e["deleted_entity_type"] for e in erasures] == ["LOCATION", "ORG"]
        for erasure in erasures:
            assert erasure["deleted_entity_name"] == "Zorbaville"
            assert erasure["entity_count"] == 1
            assert erasure["success"] is True
            assert erasure["deleted_entity_id"]
            assert "reason" in erasure

    def test_force_deletes_every_row(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        _seed(db_path, *TWO_TYPES)

        code, output = _invoke(
            "Zorbaville", "--db", db_path, "--force", "--reason", "REQ-ZORB-1"
        )

        assert code == 0, output
        assert "LOCATION" in output and "ORG" in output
        assert _stored_rows(db_path) == [("Zorbalia Quentrix", "PERSON")]
        erasures = _erasures(db_path)
        assert len(erasures) == 2
        assert {e["reason"] for e in erasures} == {"REQ-ZORB-1"}

    def test_cancel_keeps_every_row(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        _seed(db_path, *TWO_TYPES)

        code, output = _invoke("Zorbaville", "--db", db_path, answer="no\n")

        assert code == 0, output
        assert "cancelled" in output.lower()
        assert ("Zorbaville", "LOCATION") in _stored_rows(db_path)
        assert ("Zorbaville", "ORG") in _stored_rows(db_path)
        assert _erasures(db_path) == []

    def test_one_row_as_before(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        _seed(db_path, ("LOCATION", "Zorbaville", "Quentrel", "neutral"))

        code, output = _invoke("Zorbaville", "--db", db_path, "--force")

        assert code == 0, output
        assert "deleted successfully" in output
        assert _stored_rows(db_path) == []
        assert len(_erasures(db_path)) == 1

    def test_not_found(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        _seed(db_path, ("LOCATION", "Zorbaville", "Quentrel", "neutral"))

        code, output = _invoke("Quentrel", "--db", db_path, "--force")

        assert code == 1
        assert "Entity Not Found" in output
        assert _stored_rows(db_path) == [("Zorbaville", "LOCATION")]


class TestDeleteById:
    def test_id_deletes_one_row_and_reports_the_rest(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        stored = _seed(db_path, *TWO_TYPES)
        location = next(e for e in stored if e.entity_type == "LOCATION")

        code, output = _invoke("--id", location.id, "--db", db_path, "--force")

        assert code == 0, output
        assert "deleted successfully" in output
        assert ("Zorbaville", "LOCATION") not in _stored_rows(db_path)
        assert ("Zorbaville", "ORG") in _stored_rows(db_path)
        remaining = output.split("deleted successfully")[1]
        assert "1 other row" in remaining
        assert "ORG" in remaining
        assert "delete-mapping" in remaining
        assert len(_erasures(db_path)) == 1

    def test_id_with_no_other_row_says_nothing_more(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "mappings.db")
        init_database(db_path, PASSPHRASE)
        stored = _seed(db_path, ("LOCATION", "Zorbaville", "Quentrel", "neutral"))

        code, output = _invoke("--id", stored[0].id, "--db", db_path, "--force")

        assert code == 0, output
        assert "other row" not in output
        assert _stored_rows(db_path) == []
