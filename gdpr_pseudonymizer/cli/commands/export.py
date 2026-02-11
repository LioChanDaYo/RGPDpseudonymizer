"""Export command for exporting audit log.

This command exports operations from the audit log to JSON or CSV format.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()


def export_command(
    output_path: Path = typer.Argument(
        ...,
        help="Output file path (.json or .csv)",
    ),
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
    operation_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by operation type (PROCESS/BATCH/VALIDATE/etc.)",
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Filter operations after this date (ISO 8601: YYYY-MM-DD)",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="Filter operations before this date (ISO 8601: YYYY-MM-DD)",
    ),
    success_only: Optional[bool] = typer.Option(
        None,
        "--success-only",
        help="Filter by success status (True=successes, False=failures, None=all)",
        hidden=True,
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of results",
    ),
) -> None:
    """Export audit log to JSON or CSV file.

    Exports processing operations from the audit log for compliance and reporting.
    Format is auto-detected from the file extension (.json or .csv).

    Examples:
        # Export all operations to JSON
        gdpr-pseudo export audit_log.json

        # Export to CSV
        gdpr-pseudo export audit_log.csv

        # Filter by date range
        gdpr-pseudo export audit.json --from 2026-01-01 --to 2026-01-31

        # Filter by operation type
        gdpr-pseudo export audit.json --type PROCESS

        # Export only successful operations
        gdpr-pseudo export audit.json --success-only
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

        # Validate output format
        output_ext = output_path.suffix.lower()
        if output_ext not in [".json", ".csv"]:
            format_error_message(
                "Invalid Output Format",
                f"Output format '{output_ext}' is not supported.",
                "Use .json or .csv file extension.",
            )
            sys.exit(1)

        # Parse date filters
        start_date: Optional[datetime] = None
        end_date: Optional[datetime] = None

        if from_date:
            try:
                start_date = datetime.fromisoformat(from_date)
            except ValueError:
                format_error_message(
                    "Invalid Date Format",
                    f"Cannot parse --from date: {from_date}",
                    "Use ISO 8601 format: YYYY-MM-DD",
                )
                sys.exit(1)

        if to_date:
            try:
                end_date = datetime.fromisoformat(to_date)
                # Add time to include the entire day
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                format_error_message(
                    "Invalid Date Format",
                    f"Cannot parse --to date: {to_date}",
                    "Use ISO 8601 format: YYYY-MM-DD",
                )
                sys.exit(1)

        # Get passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        # Open database and export
        with open_database(db_path, resolved_passphrase) as db_session:
            audit_repo = AuditRepository(db_session.session)

            # Build filter info for display
            filter_info = []
            if operation_type:
                filter_info.append(f"type={operation_type}")
            if from_date:
                filter_info.append(f"from={from_date}")
            if to_date:
                filter_info.append(f"to={to_date}")
            if success_only is not None:
                filter_info.append("success" if success_only else "failures")
            if limit:
                filter_info.append(f"limit={limit}")

            if filter_info:
                console.print(f"\n[dim]Filters: {', '.join(filter_info)}[/dim]")

            # Export based on format
            if output_ext == ".json":
                audit_repo.export_to_json(
                    output_path=str(output_path),
                    operation_type=operation_type,
                    success=success_only,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                )
            else:  # .csv
                audit_repo.export_to_csv(
                    output_path=str(output_path),
                    operation_type=operation_type,
                    success=success_only,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                )

            # Count exported records for message
            operations = audit_repo.find_operations(
                operation_type=operation_type,
                success=success_only,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )

        console.print(
            f"\n[green]✓ Exported {len(operations)} operations to {output_path}[/green]"
        )

        logger.info(
            "audit_exported",
            path=str(output_path),
            format=output_ext,
            count=len(operations),
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

    except OSError as e:
        format_error_message(
            "File Error",
            str(e),
            "Check file path and permissions.",
        )
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Export cancelled by user[/yellow]")
        sys.exit(0)

    except Exception as e:
        logger.error("export_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)
