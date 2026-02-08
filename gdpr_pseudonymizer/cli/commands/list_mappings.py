"""List-mappings command for viewing entity-pseudonym correspondences.

This command displays all mappings from the encrypted database in a formatted table.
"""

from __future__ import annotations

import csv
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


def list_mappings_command(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help="Database file path",
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    entity_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by entity type (PERSON/LOCATION/ORG)",
    ),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Search by entity name (case-insensitive substring match)",
    ),
    export_path: Optional[Path] = typer.Option(
        None,
        "--export",
        "-e",
        help="Export mappings to CSV file",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of results",
    ),
) -> None:
    """View entity-to-pseudonym mappings from the database.

    Displays all mappings in a formatted table with options to filter by type,
    search by name, or export to CSV.

    Examples:
        # List all mappings
        gdpr-pseudo list-mappings

        # Filter by entity type
        gdpr-pseudo list-mappings --type PERSON

        # Search for specific entity
        gdpr-pseudo list-mappings --search "Marie"

        # Export to CSV
        gdpr-pseudo list-mappings --export mappings.csv

        # Combine filters
        gdpr-pseudo list-mappings --type PERSON --search "Dubois" --limit 10
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

        # Get passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        # Open database and query mappings
        with open_database(db_path, resolved_passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Query entities with filter
            entities = repo.find_all(entity_type=entity_type)

            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                entities = [
                    e
                    for e in entities
                    if search_lower in e.full_name.lower()
                    or search_lower in e.pseudonym_full.lower()
                ]

            # Apply limit if provided
            if limit is not None and limit > 0:
                entities = entities[:limit]

            # Handle empty results
            if not entities:
                console.print("\n[yellow]No mappings found matching criteria.[/yellow]")
                if entity_type:
                    console.print(f"[dim]Filter: type={entity_type}[/dim]")
                if search:
                    console.print(f'[dim]Filter: search="{search}"[/dim]')
                sys.exit(0)

            # Export to CSV if requested
            if export_path:
                _export_to_csv(entities, export_path)
                console.print(
                    f"\n[green]✓ Exported {len(entities)} mappings to {export_path}[/green]"
                )
                logger.info(
                    "mappings_exported",
                    count=len(entities),
                    path=str(export_path),
                )
                sys.exit(0)

            # Display in table
            _display_mappings_table(entities, entity_type, search)

            logger.info(
                "mappings_listed",
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
        logger.error("list_mappings_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)


def _display_mappings_table(
    entities: list[Entity],
    type_filter: Optional[str],
    search_filter: Optional[str],
) -> None:
    """Display mappings in a formatted table.

    Args:
        entities: List of entities to display
        type_filter: Type filter applied (for display)
        search_filter: Search filter applied (for display)
    """
    console.print(f"\n[bold]Entity Mappings[/bold] ({len(entities)} results)\n")

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
    table.add_column("Type", style="dim", width=10)
    table.add_column("Original Name", min_width=20)
    table.add_column("Pseudonym", min_width=20)
    table.add_column("Theme", width=12)
    table.add_column("Confidence", justify="right", width=10)

    for entity in entities:
        # Format entity type with color
        type_color = {
            "PERSON": "green",
            "LOCATION": "blue",
            "ORG": "magenta",
        }.get(entity.entity_type, "white")

        # Format confidence score
        confidence_str = (
            f"{entity.confidence_score:.2f}"
            if entity.confidence_score is not None
            else "-"
        )

        table.add_row(
            f"[{type_color}]{entity.entity_type}[/{type_color}]",
            entity.full_name,
            entity.pseudonym_full,
            entity.theme or "-",
            confidence_str,
        )

    console.print(table)


def _export_to_csv(entities: list[Entity], output_path: Path) -> None:
    """Export mappings to CSV file.

    Args:
        entities: List of entities to export
        output_path: Path to output CSV file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
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
            ],
        )
        writer.writeheader()

        for entity in entities:
            writer.writerow(
                {
                    "entity_type": entity.entity_type,
                    "full_name": entity.full_name,
                    "first_name": entity.first_name,
                    "last_name": entity.last_name,
                    "pseudonym_full": entity.pseudonym_full,
                    "pseudonym_first": entity.pseudonym_first,
                    "pseudonym_last": entity.pseudonym_last,
                    "theme": entity.theme,
                    "confidence_score": entity.confidence_score,
                    "is_ambiguous": entity.is_ambiguous,
                    "first_seen_timestamp": (
                        entity.first_seen_timestamp.isoformat()
                        if entity.first_seen_timestamp
                        else ""
                    ),
                }
            )
