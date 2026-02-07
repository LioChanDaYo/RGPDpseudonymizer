"""CLI entry point for GDPR pseudonymizer.

This module provides the main Typer application instance and
command registration for the CLI interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from gdpr_pseudonymizer.cli.commands.batch import batch_command
from gdpr_pseudonymizer.cli.commands.config_show import config_app
from gdpr_pseudonymizer.cli.commands.destroy_table import destroy_table_command
from gdpr_pseudonymizer.cli.commands.export import export_command
from gdpr_pseudonymizer.cli.commands.import_mappings import import_mappings_command
from gdpr_pseudonymizer.cli.commands.init import init_command
from gdpr_pseudonymizer.cli.commands.list_mappings import list_mappings_command
from gdpr_pseudonymizer.cli.commands.process import process_command
from gdpr_pseudonymizer.cli.commands.stats import stats_command
from gdpr_pseudonymizer.cli.commands.validate_mappings import validate_mappings_command
from gdpr_pseudonymizer.cli.config import (
    ConfigValidationError,
    PassphraseInConfigError,
    load_config,
)

# Create Typer app instance
# Note: invoke_without_command and no_args_is_help ensure proper help display
# The prog_name is set via context_settings to fix Windows display bug (shows .cmd extension)
app = typer.Typer(
    name="gdpr-pseudo",
    help="GDPR-compliant pseudonymization tool for French text documents",
    add_completion=False,
    context_settings={"help_option_names": ["--help", "-h"]},
)

# Create Rich console for output
console = Console()


def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        console.print("gdpr-pseudo version 0.1.0")
        raise typer.Exit()


@app.callback()  # type: ignore[untyped-decorator]
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (default: ~/.gdpr-pseudo.yaml or ./.gdpr-pseudo.yaml)",
        exists=False,  # Allow non-existent paths for error handling
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging (DEBUG level)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error output",
    ),
) -> None:
    """GDPR-compliant pseudonymization tool for French text documents.

    This tool performs entity detection and pseudonymization with
    human-in-the-loop validation for research interview transcripts.

    Quick Start:
        1. Initialize database:  gdpr-pseudo init
        2. Process a document:   gdpr-pseudo process document.txt
        3. View mappings:        gdpr-pseudo list-mappings

    Common Workflows:

        Single document with validation:
            gdpr-pseudo process interview.txt -o interview_pseudo.txt

        Batch processing with parallel workers:
            gdpr-pseudo batch ./transcripts/ -o ./output/ --workers 4

        Generate config template:
            gdpr-pseudo config --init

        Modify configuration:
            gdpr-pseudo config set pseudonymization.theme star_wars

    Global Options:
        --config, -c    Path to config file
        --verbose, -v   Enable verbose logging
        --quiet, -q     Suppress non-error output

    Configuration Priority:
        1. CLI flags (highest)
        2. Custom config file (--config)
        3. Project config (./.gdpr-pseudo.yaml)
        4. Home config (~/.gdpr-pseudo.yaml)
        5. Defaults (lowest)

    Security:
        Passphrase is NOT stored in config files.
        Use GDPR_PSEUDO_PASSPHRASE environment variable or interactive prompt.

    For detailed command help: gdpr-pseudo <command> --help
    """
    # Load and validate config file if specified
    if config is not None:
        if not config.exists():
            console.print(
                f"[bold red]Error:[/bold red] Config file not found: {config}"
            )
            raise typer.Exit(1)

        try:
            load_config(config_path=config)
        except PassphraseInConfigError as e:
            console.print(f"[bold red]Security Error:[/bold red] {e}")
            raise typer.Exit(1)
        except ConfigValidationError as e:
            console.print(f"[bold red]Config Error:[/bold red] {e}")
            raise typer.Exit(1)

    # Configure logging based on verbose/quiet flags
    if verbose and quiet:
        console.print(
            "[bold yellow]Warning:[/bold yellow] Both --verbose and --quiet specified. "
            "Using --verbose."
        )

    # Note: Verbose/quiet flags can be used by individual commands
    # via environment variables or context if needed


# Register all commands
app.command(name="init", help="Initialize a new encrypted mapping database")(
    init_command
)
app.command(name="process", help="Process a single document with pseudonymization")(
    process_command
)
app.command(name="batch", help="Process multiple documents in a directory")(
    batch_command
)
app.command(name="list-mappings", help="View entity-to-pseudonym mappings")(
    list_mappings_command
)
app.command(
    name="validate-mappings", help="Review existing mappings without processing"
)(validate_mappings_command)
app.command(name="stats", help="Show database statistics and usage information")(
    stats_command
)
app.command(name="import-mappings", help="Import mappings from another database")(
    import_mappings_command
)
app.command(name="export", help="Export audit log to JSON or CSV")(export_command)
app.command(name="destroy-table", help="Securely delete the mapping database")(
    destroy_table_command
)
app.add_typer(config_app, name="config", help="View or modify configuration settings")


def cli_main() -> None:
    """Entry point for CLI with explicit program name for Windows compatibility."""
    app(prog_name="gdpr-pseudo")


if __name__ == "__main__":
    cli_main()
