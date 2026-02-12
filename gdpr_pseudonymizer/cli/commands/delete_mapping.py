"""Delete-mapping command for GDPR Article 17 erasure.

This command deletes a specific entity mapping from the database,
converting pseudonymization into anonymization for GDPR compliance.
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity, Operation
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()


def delete_mapping_command(
    entity_name: Optional[str] = typer.Argument(None, help="Entity name to delete"),
    db_path: str = typer.Option("mappings.db", "--db", help="Database file path"),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    entity_id: Optional[str] = typer.Option(None, "--id", help="Entity UUID to delete"),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Reason for deletion (GDPR request reference)"
    ),
    force: bool = typer.Option(
        False, "--force/--no-force", "-f", help="Skip confirmation prompt"
    ),
) -> None:
    """Delete an entity mapping from the database (GDPR Article 17 erasure).

    Deleting a mapping converts pseudonymization into anonymization:
    without the mapping, the pseudonym cannot be linked to an identifiable
    individual, placing the data outside GDPR scope.

    Examples:
        # Delete by entity name
        gdpr-pseudo delete-mapping "Marie Dupont" --db mappings.db

        # Delete by entity UUID
        gdpr-pseudo delete-mapping --id abc12345 --db mappings.db

        # Delete with reason for audit trail
        gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

        # Skip confirmation (for automation)
        gdpr-pseudo delete-mapping "Marie Dupont" --force
    """
    try:
        start_time = time.monotonic()

        # Validate: must provide exactly one of entity_name or entity_id
        if entity_name and entity_id:
            format_error_message(
                "Invalid Arguments",
                "Provide either an entity name or --id, not both.",
                "Use 'gdpr-pseudo delete-mapping \"Name\"' or 'gdpr-pseudo delete-mapping --id <uuid>'.",
            )
            sys.exit(1)

        if not entity_name and not entity_id:
            format_error_message(
                "Missing Argument",
                "No entity specified for deletion.",
                "Use 'gdpr-pseudo delete-mapping \"Name\"' or 'gdpr-pseudo delete-mapping --id <uuid>'.",
            )
            sys.exit(1)

        # Validate database exists
        db_file = Path(db_path)
        if not db_file.exists():
            format_error_message(
                "Database Not Found",
                f"Database file not found: {db_file.absolute()}",
                "Run 'gdpr-pseudo init' to create a new database.",
            )
            sys.exit(1)

        # Resolve passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        # Open database and perform deletion
        with open_database(db_path, resolved_passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            audit_repo = AuditRepository(db_session.session)

            # Find entity first (for confirmation display)
            if entity_name:
                entity = repo.find_by_full_name(entity_name)
            else:
                entity = _find_entity_by_id(repo, entity_id)  # type: ignore[arg-type]

            if entity is None:
                identifier = entity_name or entity_id
                format_error_message(
                    "Entity Not Found",
                    f"No entity found matching: {identifier}",
                    "Use 'gdpr-pseudo list-entities' to search for entities.",
                )
                sys.exit(1)

            # Display confirmation prompt (unless --force)
            if not force:
                _display_confirmation(entity)
                confirmation = Prompt.ask(
                    "Type 'yes' to confirm permanent deletion",
                    default="",
                )
                if confirmation.lower() != "yes":
                    console.print(
                        "\n[green]Deletion cancelled. No changes made.[/green]"
                    )
                    sys.exit(0)

            # Perform deletion (use entity.id for --id to handle partial UUIDs)
            if entity_name:
                deleted = repo.delete_entity_by_full_name(entity_name)
            else:
                deleted = repo.delete_entity_by_id(entity.id)

            if deleted is None:
                format_error_message(
                    "Deletion Failed",
                    "Entity was not found during deletion (may have been deleted concurrently).",
                    "Use 'gdpr-pseudo list-entities' to verify.",
                )
                sys.exit(1)

            # Create ERASURE audit log entry (Task 5.1.3)
            elapsed = time.monotonic() - start_time
            operation = Operation(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                operation_type="ERASURE",
                files_processed=[],
                user_modifications={
                    "deleted_entity_id": deleted.id,
                    "deleted_entity_name": deleted.full_name,
                    "deleted_entity_type": deleted.entity_type,
                    "reason": reason,
                },
                model_name="N/A",
                model_version="N/A",
                theme_selected=deleted.theme,
                entity_count=1,
                processing_time_seconds=round(elapsed, 3),
                success=True,
            )
            audit_repo.log_operation(operation)

            # Success output
            console.print(
                "\n[bold green]Entity mapping deleted successfully.[/bold green]"
            )
            console.print(
                f"  [bold]Entity:[/bold] {deleted.full_name} ({deleted.entity_type})"
            )
            console.print(f"  [bold]Pseudonym:[/bold] {deleted.pseudonym_full}")
            console.print(
                f"\n[dim]The pseudonym '{deleted.pseudonym_full}' is now permanently anonymous.[/dim]"
            )
            console.print(
                f"[dim]ERASURE audit log entry created (operation {operation.id[:8]}...).[/dim]"
            )

            logger.info(
                "entity_deleted",
                entity_id=deleted.id,
                entity_type=deleted.entity_type,
                reason=reason,
            )

    except FileNotFoundError:
        format_error_message(
            "Database Not Found",
            f"Database file not found: {db_path}",
            "Run 'gdpr-pseudo init' to create a new database.",
        )
        sys.exit(1)

    except ValueError as e:
        if "passphrase" in str(e).lower():
            format_error_message(
                "Authentication Failed",
                "Incorrect passphrase.",
                "Check your passphrase and try again.",
            )
        else:
            format_error_message(
                "Error",
                str(e),
                "Check the error message and try again.",
            )
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)

    except Exception as e:
        logger.error("delete_mapping_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)


def _find_entity_by_id(repo: SQLiteMappingRepository, entity_id: str) -> Entity | None:
    """Find entity by full or partial UUID.

    Args:
        repo: Repository instance
        entity_id: Full or partial UUID

    Returns:
        Matching entity, or None
    """
    # Try exact match first
    entities = repo.find_all()
    for entity in entities:
        if entity.id == entity_id:
            return entity

    # Try prefix match (user may pass truncated UUID from list-entities)
    matches = [e for e in entities if e.id.startswith(entity_id)]
    if len(matches) == 1:
        return matches[0]

    return None


def _display_confirmation(entity: Entity) -> None:
    """Display entity details and deletion warning.

    Args:
        entity: Entity to display
    """
    console.print("\n[bold red]WARNING: PERMANENT DELETION[/bold red]\n")
    console.print("You are about to delete the following entity mapping:\n")
    console.print(f"  [bold]Name:[/bold]       {entity.full_name}")
    console.print(f"  [bold]Type:[/bold]       {entity.entity_type}")
    console.print(f"  [bold]Pseudonym:[/bold]  {entity.pseudonym_full}")
    console.print(f"  [bold]Theme:[/bold]      {entity.theme}")
    if entity.first_seen_timestamp:
        console.print(
            f"  [bold]First seen:[/bold] {entity.first_seen_timestamp.strftime('%Y-%m-%d %H:%M')}"
        )
    console.print(
        f"\n[yellow]This will permanently delete the mapping. "
        f"The pseudonym '{entity.pseudonym_full}' will become permanently "
        f"anonymous. This cannot be undone.[/yellow]\n"
    )
