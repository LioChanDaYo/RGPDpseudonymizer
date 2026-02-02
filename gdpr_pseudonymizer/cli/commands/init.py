"""Init command for database initialization.

This command initializes a new encrypted mapping database with user passphrase.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()


def init_command(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help="Database file path (default: mappings.db)",
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing database if it exists",
    ),
) -> None:
    """Initialize a new encrypted mapping database.

    Creates a new SQLite database with encryption enabled. The database stores
    entity-to-pseudonym mappings for GDPR-compliant pseudonymization.

    Passphrase requirements:
    - Minimum 12 characters
    - Used to derive encryption key for sensitive data

    Passphrase resolution order:
    1. --passphrase flag (for scripting)
    2. GDPR_PSEUDO_PASSPHRASE environment variable
    3. Interactive prompt (most secure)

    Examples:
        # Initialize with interactive passphrase prompt
        gdpr-pseudo init

        # Initialize with custom database path
        gdpr-pseudo init --db project_mappings.db

        # Initialize with passphrase from environment
        export GDPR_PSEUDO_PASSPHRASE="your_secure_passphrase"
        gdpr-pseudo init

        # Force overwrite existing database
        gdpr-pseudo init --force
    """
    try:
        # Check if database already exists
        db_file = Path(db_path)
        if db_file.exists():
            if not force:
                format_error_message(
                    "Database Already Exists",
                    f"Database file already exists at: {db_file.absolute()}",
                    "Use --force flag to overwrite existing database.",
                )
                sys.exit(1)
            else:
                # Delete existing database for --force
                console.print(
                    f"[yellow]Removing existing database: {db_file.absolute()}[/yellow]"
                )
                db_file.unlink()
                logger.info("existing_database_removed", path=str(db_file.absolute()))

        # Get passphrase (with confirmation for new database)
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase for new database",
            confirm=True,
        )

        # Initialize database with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing encrypted database...", total=None)

            try:
                init_database(db_path, resolved_passphrase)
                progress.update(task, description="✓ Database initialized")
            except ValueError as e:
                progress.update(task, description="✗ Initialization failed")
                console.print(f"\n[bold red]Database initialization failed:[/bold red] {e}")
                sys.exit(1)

        # Success message
        console.print("\n[bold green]✓ Database Initialized Successfully[/bold green]\n")
        console.print(f"[bold]Database path:[/bold] {db_file.absolute()}")
        console.print("\n[dim]You can now use 'gdpr-pseudo process' to pseudonymize documents.[/dim]")

        logger.info(
            "database_initialized",
            path=str(db_file.absolute()),
        )

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Initialization cancelled by user[/yellow]")
        logger.info("init_cancelled", reason="keyboard_interrupt")
        sys.exit(0)

    except Exception as e:
        logger.error("init_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Initialization Error",
            str(e),
            "Check file permissions and try again.",
        )
        sys.exit(2)
