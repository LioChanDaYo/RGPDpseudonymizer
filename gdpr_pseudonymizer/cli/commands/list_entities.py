"""List-entities command for GDPR erasure workflow.

This command displays entities with their UUIDs, optimized for the
Article 17 erasure workflow (finding entities to delete).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()

# Valid entity types
VALID_ENTITY_TYPES = ["PERSON", "LOCATION", "ORG"]


def list_entities_command(
    db_path: str = typer.Option("mappings.db", "--db", help="Database file path"),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Search by entity name (case-insensitive substring match)",
    ),
    entity_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by type (PERSON/LOCATION/ORG)"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Limit number of results"
    ),
) -> None:
    """List entities with search capability for GDPR erasure workflow.

    Displays entity details including truncated UUID for use with
    the delete-mapping --id command.

    Examples:
        # List all entities
        gdpr-pseudo list-entities

        # Search by name
        gdpr-pseudo list-entities --search "Dupont"

        # Filter by type
        gdpr-pseudo list-entities --type PERSON

        # Combine filters with limit
        gdpr-pseudo list-entities --search "Marie" --type PERSON --limit 10
    """
    try:
        # Validate database exists
        db_file = Path(db_path)
        if not db_file.exists():
            format_error_message(
                "Database Not Found",
                f"Database file not found: {db_file.absolute()}",
                "Run 'gdpr-pseudo init' to create a new database.",
            )
            sys.exit(1)

        # Validate entity type if provided
        if entity_type is not None:
            entity_type_upper = entity_type.upper()
            if entity_type_upper not in VALID_ENTITY_TYPES:
                format_error_message(
                    "Invalid Entity Type",
                    f"Entity type '{entity_type}' is not valid.",
                    f"Valid types: {', '.join(VALID_ENTITY_TYPES)}",
                )
                sys.exit(1)
            entity_type = entity_type_upper

        # Resolve passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        # Open database and query entities
        with open_database(db_path, resolved_passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Search entities with filters
            entities = repo.search_entities(
                search_term=search,
                entity_type=entity_type,
            )

            # Apply limit
            if limit is not None and limit > 0:
                entities = entities[:limit]

            # Handle empty results
            if not entities:
                console.print("\n[yellow]No entities found matching criteria.[/yellow]")
                if entity_type:
                    console.print(f"[dim]Filter: type={entity_type}[/dim]")
                if search:
                    console.print(f'[dim]Filter: search="{search}"[/dim]')
                sys.exit(0)

            # Display table
            _display_entities_table(entities, entity_type, search)

            logger.info(
                "entities_listed",
                count=len(entities),
                type_filter=entity_type,
                search_filter=search,
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
        logger.error("list_entities_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)


def _display_entities_table(
    entities: list[Entity],
    type_filter: str | None,
    search_filter: str | None,
) -> None:
    """Display entities in a formatted table.

    Args:
        entities: List of entities to display
        type_filter: Type filter applied (for display)
        search_filter: Search filter applied (for display)
    """
    console.print(f"\n[bold]Entities[/bold] ({len(entities)} results)\n")

    # Show filters if applied
    if type_filter or search_filter:
        filter_parts = []
        if type_filter:
            filter_parts.append(f"type={type_filter}")
        if search_filter:
            filter_parts.append(f'search="{search_filter}"')
        console.print(f"[dim]Filters: {', '.join(filter_parts)}[/dim]\n")

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Entity ID", style="dim", width=10)
    table.add_column("Entity Name", min_width=20)
    table.add_column("Type", width=10)
    table.add_column("Pseudonym", min_width=20)
    table.add_column("First Seen", width=12)
    table.add_column("Doc Count", justify="right", width=10)

    for entity in entities:
        # Truncated UUID (first 8 chars)
        entity_id_short = entity.id[:8] if entity.id else "-"

        # Format entity type with color
        type_color = {
            "PERSON": "green",
            "LOCATION": "blue",
            "ORG": "magenta",
        }.get(entity.entity_type, "white")

        # Format first seen date
        first_seen = (
            entity.first_seen_timestamp.strftime("%Y-%m-%d")
            if entity.first_seen_timestamp
            else "-"
        )

        table.add_row(
            entity_id_short,
            entity.full_name,
            f"[{type_color}]{entity.entity_type}[/{type_color}]",
            entity.pseudonym_full,
            first_seen,
            "N/A",
        )

    console.print(table)
    console.print(
        "\n[dim]Note: Doc Count is N/A — per-entity document tracking "
        "will be added in a future release.[/dim]"
    )
    console.print(
        "[dim]Tip: Use the Entity ID with 'gdpr-pseudo delete-mapping --id <id>' "
        "for erasure.[/dim]"
    )
