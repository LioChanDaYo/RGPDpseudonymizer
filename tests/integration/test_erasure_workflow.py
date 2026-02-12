"""Integration test for GDPR Article 17 erasure workflow (Story 5.1).

End-to-end test flow:
1. Init database
2. Create entity mappings
3. list-entities — verify entity appears
4. delete-mapping — verify deletion
5. list-entities — verify entity is gone
6. Verify ERASURE audit log entry
7. Verify remaining entities unaffected
"""

from __future__ import annotations

from pathlib import Path

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.delete_mapping import delete_mapping_command
from gdpr_pseudonymizer.cli.commands.list_entities import list_entities_command
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)


def _create_test_app() -> typer.Typer:
    """Create a test app with both commands registered."""
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="delete-mapping")(delete_mapping_command)
    app.command(name="list-entities")(list_entities_command)
    return app


app = _create_test_app()
runner = CliRunner()

PASSPHRASE = "test_passphrase_123!"


class TestErasureWorkflow:
    """End-to-end test for the GDPR erasure workflow."""

    def test_full_erasure_workflow(self, tmp_path: Path) -> None:
        """Complete erasure workflow: create → list → delete → verify → audit."""
        db_path = str(tmp_path / "test.db")

        # Step 1: Init database
        init_database(db_path, PASSPHRASE)

        # Step 2: Create entity mappings
        with open_database(db_path, PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity_marie = repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Dupont",
                    full_name="Marie Dupont",
                    pseudonym_first="Leia",
                    pseudonym_last="Organa",
                    pseudonym_full="Leia Organa",
                    theme="star_wars",
                )
            )
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Jean",
                    last_name="Martin",
                    full_name="Jean Martin",
                    pseudonym_first="Luke",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Luke Skywalker",
                    theme="star_wars",
                )
            )

        # Step 3: list-entities — verify both entities appear
        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Marie Dupont" in output
        assert "Jean Martin" in output
        assert "2 results" in output

        # Step 3b: list-entities with search — verify specific entity found
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
        assert "Marie Dupont" in output
        assert "Jean Martin" not in output
        assert "1 results" in output

        # Step 4: delete-mapping — delete Marie Dupont with confirmation
        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--reason",
                "GDPR-REQ-2026-042",
                "--force",
            ],
        )
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "deleted successfully" in output

        # Step 5: list-entities — verify Marie is gone
        result = runner.invoke(
            app,
            ["list-entities", "--db", db_path, "--passphrase", PASSPHRASE],
        )
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Marie Dupont" not in output
        assert "Jean Martin" in output
        assert "1 results" in output

        # Step 6: Verify ERASURE audit log entry
        with open_database(db_path, PASSPHRASE) as db_session:
            audit_repo = AuditRepository(db_session.session)
            operations = audit_repo.find_operations(operation_type="ERASURE")

            assert len(operations) == 1
            op = operations[0]
            assert op.operation_type == "ERASURE"
            assert op.success is True
            assert op.entity_count == 1
            assert op.user_modifications is not None
            assert op.user_modifications["deleted_entity_name"] == "Marie Dupont"
            assert op.user_modifications["deleted_entity_type"] == "PERSON"
            assert op.user_modifications["deleted_entity_id"] == entity_marie.id
            assert op.user_modifications["reason"] == "GDPR-REQ-2026-042"
            assert op.theme_selected == "star_wars"

        # Step 7: Verify remaining entity unaffected
        with open_database(db_path, PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            remaining = repo.find_all()
            assert len(remaining) == 1
            assert remaining[0].full_name == "Jean Martin"
            assert remaining[0].pseudonym_full == "Luke Skywalker"

    def test_erasure_by_id_workflow(self, tmp_path: Path) -> None:
        """Erasure workflow using entity UUID instead of name."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)

        with open_database(db_path, PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            saved = repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Dupont",
                    full_name="Marie Dupont",
                    pseudonym_first="Leia",
                    pseudonym_last="Organa",
                    pseudonym_full="Leia Organa",
                    theme="star_wars",
                )
            )

        # Delete by truncated UUID (as user would copy from list-entities)
        short_id = saved.id[:8]
        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "--id",
                short_id,
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--force",
            ],
        )
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "deleted successfully" in output

        # Verify gone
        with open_database(db_path, PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            assert repo.find_by_full_name("Marie Dupont") is None
