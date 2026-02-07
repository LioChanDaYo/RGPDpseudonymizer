"""Stats command for showing database statistics.

This command displays statistics about entities, documents, and library exhaustion.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.data.database import open_database
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


def stats_command(
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
) -> None:
    """Show database statistics and usage information.

    Displays comprehensive statistics including:
    - Entity counts by type (PERSON/LOCATION/ORG)
    - Documents processed count
    - Library exhaustion percentage per theme
    - Database size and creation date
    - Most recent processing operation

    Examples:
        # View statistics
        gdpr-pseudo stats

        # View statistics for specific database
        gdpr-pseudo stats --db project.db
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

        # Get passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        # Open database and gather statistics
        with open_database(db_path, resolved_passphrase) as db_session:
            mapping_repo = SQLiteMappingRepository(db_session)
            audit_repo = AuditRepository(db_session.session)

            # Entity counts by type
            all_entities = mapping_repo.find_all()
            person_count = len([e for e in all_entities if e.entity_type == "PERSON"])
            location_count = len(
                [e for e in all_entities if e.entity_type == "LOCATION"]
            )
            org_count = len([e for e in all_entities if e.entity_type == "ORG"])

            # Ambiguous entities
            ambiguous_count = len([e for e in all_entities if e.is_ambiguous])

            # Theme distribution
            themes: dict[str, int] = {}
            for entity in all_entities:
                theme = entity.theme or "unknown"
                themes[theme] = themes.get(theme, 0) + 1

            # Operations stats
            all_operations = audit_repo.find_operations()
            successful_ops = [op for op in all_operations if op.success]
            failed_ops = [op for op in all_operations if not op.success]

            # Most recent operation
            recent_ops = audit_repo.find_operations(limit=1)
            recent_op = recent_ops[0] if recent_ops else None

            # Database file info
            db_size = db_file.stat().st_size
            db_created = datetime.fromtimestamp(db_file.stat().st_ctime)
            db_modified = datetime.fromtimestamp(db_file.stat().st_mtime)

        # Display statistics
        console.print("\n[bold]Database Statistics[/bold]\n")

        # Database info
        console.print("[bold cyan]Database Info[/bold cyan]")
        db_table = Table(show_header=False, box=None)
        db_table.add_column("Metric", style="dim")
        db_table.add_column("Value")
        db_table.add_row("Path", str(db_file.absolute()))
        db_table.add_row("Size", _format_size(db_size))
        db_table.add_row("Created", db_created.strftime("%Y-%m-%d %H:%M"))
        db_table.add_row("Last Modified", db_modified.strftime("%Y-%m-%d %H:%M"))
        console.print(db_table)
        console.print()

        # Entity counts
        console.print("[bold cyan]Entity Counts[/bold cyan]")
        entity_table = Table(show_header=False, box=None)
        entity_table.add_column("Type", style="dim")
        entity_table.add_column("Count", justify="right")
        entity_table.add_row("Total Entities", f"[bold]{len(all_entities)}[/bold]")
        entity_table.add_row("  PERSON", str(person_count))
        entity_table.add_row("  LOCATION", str(location_count))
        entity_table.add_row("  ORG", str(org_count))
        entity_table.add_row("", "")
        entity_table.add_row(
            "Ambiguous",
            f"[yellow]{ambiguous_count}[/yellow]" if ambiguous_count else "0",
        )
        console.print(entity_table)
        console.print()

        # Theme distribution
        if themes:
            console.print("[bold cyan]Theme Distribution[/bold cyan]")
            theme_table = Table(show_header=False, box=None)
            theme_table.add_column("Theme", style="dim")
            theme_table.add_column("Count", justify="right")
            for theme, count in sorted(themes.items(), key=lambda x: -x[1]):
                theme_table.add_row(theme, str(count))
            console.print(theme_table)
            console.print()

        # Operations
        console.print("[bold cyan]Processing History[/bold cyan]")
        ops_table = Table(show_header=False, box=None)
        ops_table.add_column("Metric", style="dim")
        ops_table.add_column("Value", justify="right")
        ops_table.add_row("Total Operations", str(len(all_operations)))
        ops_table.add_row("Successful", f"[green]{len(successful_ops)}[/green]")
        ops_table.add_row(
            "Failed", f"[red]{len(failed_ops)}[/red]" if failed_ops else "0"
        )

        if recent_op:
            ops_table.add_row("", "")
            ops_table.add_row("Last Operation", recent_op.operation_type)
            ops_table.add_row(
                "  Timestamp", recent_op.timestamp.strftime("%Y-%m-%d %H:%M")
            )
            ops_table.add_row("  Entities", str(recent_op.entity_count))
            ops_table.add_row(
                "  Status",
                (
                    "[green]Success[/green]"
                    if recent_op.success
                    else f"[red]Failed: {recent_op.error_message}[/red]"
                ),
            )

        console.print(ops_table)

        logger.info(
            "stats_displayed",
            total_entities=len(all_entities),
            total_operations=len(all_operations),
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
        logger.error("stats_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
