"""Unit tests for delete-mapping CLI command (Story 5.1)."""

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


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="delete-mapping")(delete_mapping_command)
    return app


app = create_test_app()
runner = CliRunner()

PASSPHRASE = "test_passphrase_123!"


def _seed_entity(db_path: str, passphrase: str, **overrides: object) -> Entity:
    """Seed a test entity and return it."""
    defaults = {
        "entity_type": "PERSON",
        "first_name": "Marie",
        "last_name": "Dupont",
        "full_name": "Marie Dupont",
        "pseudonym_first": "Leia",
        "pseudonym_last": "Organa",
        "pseudonym_full": "Leia Organa",
        "theme": "star_wars",
    }
    defaults.update(overrides)

    with open_database(db_path, passphrase) as db_session:
        repo = SQLiteMappingRepository(db_session)
        return repo.save(Entity(**defaults))


class TestDeleteMappingCommand:
    def test_delete_by_name_with_confirmation(self, tmp_path: Path) -> None:
        """Delete entity by name with user confirmation."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entity(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
            ],
            input="yes\n",
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "deleted successfully" in output

        # Verify entity is gone
        with open_database(db_path, PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            assert repo.find_by_full_name("Marie Dupont") is None

    def test_delete_by_id_with_confirmation(self, tmp_path: Path) -> None:
        """Delete entity by UUID with user confirmation."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        saved = _seed_entity(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "--id",
                saved.id,
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
            ],
            input="yes\n",
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "deleted successfully" in output

    def test_delete_with_force_skips_confirmation(self, tmp_path: Path) -> None:
        """--force flag skips the confirmation prompt."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entity(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
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

    def test_delete_nonexistent_entity(self, tmp_path: Path) -> None:
        """Deleting a nonexistent entity shows error."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["delete-mapping", "Nobody", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Entity Not Found" in output

    def test_delete_cancelled_by_user(self, tmp_path: Path) -> None:
        """User typing 'no' cancels the deletion."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entity(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
            ],
            input="no\n",
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "cancelled" in output.lower()

        # Entity should still exist
        with open_database(db_path, PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            assert repo.find_by_full_name("Marie Dupont") is not None

    def test_missing_both_name_and_id(self, tmp_path: Path) -> None:
        """Error when neither name nor --id provided."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            ["delete-mapping", "--db", db_path, "--passphrase", PASSPHRASE],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Missing Argument" in output

    def test_both_name_and_id_error(self, tmp_path: Path) -> None:
        """Error when both name and --id provided."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
                "--id",
                "some-uuid",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Invalid Arguments" in output

    def test_audit_log_created_on_deletion(self, tmp_path: Path) -> None:
        """ERASURE audit log entry created after successful deletion."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entity(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--force",
            ],
        )
        assert result.exit_code == 0

        # Verify audit log
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

    def test_reason_stored_in_audit(self, tmp_path: Path) -> None:
        """--reason flag value stored in audit entry."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        _seed_entity(db_path, PASSPHRASE)

        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie Dupont",
                "--db",
                db_path,
                "--passphrase",
                PASSPHRASE,
                "--force",
                "--reason",
                "GDPR-REQ-2026-042",
            ],
        )
        assert result.exit_code == 0

        with open_database(db_path, PASSPHRASE) as db_session:
            audit_repo = AuditRepository(db_session.session)
            operations = audit_repo.find_operations(operation_type="ERASURE")
            assert len(operations) == 1
            assert operations[0].user_modifications["reason"] == "GDPR-REQ-2026-042"

    def test_database_not_found(self, tmp_path: Path) -> None:
        """Error when database file doesn't exist."""
        result = runner.invoke(
            app,
            [
                "delete-mapping",
                "Marie",
                "--db",
                str(tmp_path / "missing.db"),
                "--passphrase",
                PASSPHRASE,
            ],
        )

        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Database Not Found" in output

    def test_delete_by_partial_id(self, tmp_path: Path) -> None:
        """Delete entity using truncated UUID prefix."""
        db_path = str(tmp_path / "test.db")
        init_database(db_path, PASSPHRASE)
        saved = _seed_entity(db_path, PASSPHRASE)
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
