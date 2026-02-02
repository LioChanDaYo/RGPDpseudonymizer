"""Validate-mappings command for reviewing existing mappings.

This command displays mappings with metadata for review without processing.
Read-only database access.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm
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


def validate_mappings_command(
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
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode to review each mapping",
    ),
    entity_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by entity type (PERSON/LOCATION/ORG)",
    ),
) -> None:
    """Review existing mappings without processing documents.

    This command provides a read-only view of entity mappings with metadata
    such as creation timestamp and confidence scores. Use interactive mode
    to review mappings one by one and flag any that need correction.

    NOTE: This command does NOT modify the database. Use it for audit purposes.

    Examples:
        # View all mappings with metadata
        gdpr-pseudo validate-mappings

        # Interactive review mode
        gdpr-pseudo validate-mappings --interactive

        # Filter by entity type
        gdpr-pseudo validate-mappings --type PERSON
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
        valid_types = ["PERSON", "LOCATION", "ORG"]
        if entity_type is not None:
            entity_type_upper = entity_type.upper()
            if entity_type_upper not in valid_types:
                format_error_message(
                    "Invalid Entity Type",
                    f"Entity type '{entity_type}' is not valid.",
                    f"Valid types: {', '.join(valid_types)}",
                )
                sys.exit(1)
            entity_type = entity_type_upper

        # Get passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        # Open database and query mappings (read-only)
        with open_database(db_path, resolved_passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Query entities
            entities = repo.find_all(entity_type=entity_type)

            if not entities:
                console.print("\n[yellow]No mappings found in database.[/yellow]")
                sys.exit(0)

            if interactive:
                _interactive_review(entities)
            else:
                _display_validation_table(entities)

            logger.info(
                "mappings_validated",
                count=len(entities),
                interactive=interactive,
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
        console.print("\n\n[yellow]Review cancelled by user[/yellow]")
        sys.exit(0)

    except Exception as e:
        logger.error("validate_mappings_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)


def _display_validation_table(entities: list[Entity]) -> None:
    """Display mappings in a validation table with metadata.

    Args:
        entities: List of entities to display
    """
    console.print(f"\n[bold]Mapping Validation Review[/bold] ({len(entities)} mappings)\n")
    console.print("[dim]This is a read-only view. No modifications will be made.[/dim]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", width=4)
    table.add_column("Type", width=10)
    table.add_column("Original", min_width=18)
    table.add_column("Pseudonym", min_width=18)
    table.add_column("Confidence", width=10, justify="right")
    table.add_column("Created", width=12)
    table.add_column("Flags", width=10)

    for idx, entity in enumerate(entities, 1):
        # Format confidence
        conf_str = f"{entity.confidence_score:.2f}" if entity.confidence_score else "-"
        conf_color = "green" if entity.confidence_score and entity.confidence_score >= 0.85 else "yellow"

        # Format timestamp
        timestamp_str = (
            entity.first_seen_timestamp.strftime("%Y-%m-%d")
            if entity.first_seen_timestamp
            else "-"
        )

        # Format flags
        flags = []
        if entity.is_ambiguous:
            flags.append("[yellow]AMB[/yellow]")
        if entity.confidence_score and entity.confidence_score < 0.85:
            flags.append("[red]LOW[/red]")
        flags_str = " ".join(flags) if flags else "[green]OK[/green]"

        table.add_row(
            str(idx),
            entity.entity_type,
            entity.full_name,
            entity.pseudonym_full,
            f"[{conf_color}]{conf_str}[/{conf_color}]",
            timestamp_str,
            flags_str,
        )

    console.print(table)

    # Summary
    ambiguous_count = sum(1 for e in entities if e.is_ambiguous)
    low_conf_count = sum(1 for e in entities if e.confidence_score and e.confidence_score < 0.85)

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  • Total mappings: {len(entities)}")
    if ambiguous_count:
        console.print(f"  • Ambiguous (AMB): [yellow]{ambiguous_count}[/yellow]")
    if low_conf_count:
        console.print(f"  • Low confidence (LOW): [red]{low_conf_count}[/red]")


def _interactive_review(entities: list[Entity]) -> None:
    """Interactive mode to review each mapping.

    Args:
        entities: List of entities to review
    """
    console.print(f"\n[bold]Interactive Mapping Review[/bold] ({len(entities)} mappings)\n")
    console.print("[dim]Review each mapping. Press Enter to continue, 'q' to quit.[/dim]")
    console.print("[dim]Note: Flagging is for tracking only - no database changes are made.[/dim]\n")

    flagged = []

    for idx, entity in enumerate(entities, 1):
        console.print(f"\n[bold cyan]Mapping {idx}/{len(entities)}[/bold cyan]")
        console.print(f"  Type:       {entity.entity_type}")
        console.print(f"  Original:   [bold]{entity.full_name}[/bold]")
        console.print(f"  Pseudonym:  [bold]{entity.pseudonym_full}[/bold]")
        console.print(f"  Theme:      {entity.theme or '-'}")
        console.print(f"  Confidence: {entity.confidence_score:.2f}" if entity.confidence_score else "  Confidence: -")
        console.print(f"  Ambiguous:  {'Yes' if entity.is_ambiguous else 'No'}")

        try:
            should_flag = Confirm.ask("Flag this mapping for review?", default=False)
            if should_flag:
                flagged.append(entity)
                console.print("[yellow]  → Flagged[/yellow]")
        except KeyboardInterrupt:
            break

    # Summary
    console.print("\n[bold]Review Complete[/bold]")
    console.print(f"  • Reviewed: {idx}/{len(entities)}")
    console.print(f"  • Flagged: {len(flagged)}")

    if flagged:
        console.print("\n[bold]Flagged Mappings:[/bold]")
        for entity in flagged:
            console.print(f"  • {entity.full_name} → {entity.pseudonym_full}")
