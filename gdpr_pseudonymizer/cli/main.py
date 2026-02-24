"""CLI entry point for GDPR pseudonymizer.

This module provides the main Typer application instance and
command registration for the CLI interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from gdpr_pseudonymizer.cli.commands.config_show import config_app
from gdpr_pseudonymizer.cli.config import load_config
from gdpr_pseudonymizer.cli.i18n import _, set_language
from gdpr_pseudonymizer.exceptions import (
    ConfigValidationError,
    PassphraseInConfigError,
)

# Create Typer app instance
# Note: invoke_without_command and no_args_is_help ensure proper help display
# The prog_name is set via context_settings to fix Windows display bug (shows .cmd extension)
app = typer.Typer(
    name="gdpr-pseudo",
    help=_("GDPR-compliant pseudonymization tool for French text documents"),
    add_completion=False,
    context_settings={"help_option_names": ["--help", "-h"]},
)

# Create Rich console for output
console = Console()


def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        from importlib.metadata import version

        console.print(f"gdpr-pseudo version {version('gdpr-pseudonymizer')}")
        raise typer.Exit()


def _lang_callback(value: Optional[str]) -> None:
    """Set CLI language via --lang flag (eager — runs before help)."""
    if value is not None:
        set_language(value)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help=_("Show version and exit"),
        callback=version_callback,
        is_eager=True,
    ),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        help=_("Language for CLI help text (fr/en)"),
        callback=_lang_callback,
        is_eager=True,
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help=_(
            "Path to config file (default: ~/.gdpr-pseudo.yaml or ./.gdpr-pseudo.yaml)"
        ),
        exists=False,  # Allow non-existent paths for error handling
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help=_("Enable verbose logging (DEBUG level)"),
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help=_("Suppress non-error output"),
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
        --lang          Language for help text (fr/en)

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


# ---------------------------------------------------------------------------
# Command wrappers with lazy imports
# Typer reads parameter signatures at app construction time for --help.
# Heavy dependencies (spaCy, SQLAlchemy, cryptography, etc.) are only
# imported when a command is actually invoked, keeping --help fast.
# ---------------------------------------------------------------------------


@app.command(name="init", help=_("Initialize a new encrypted mapping database"))
def _init(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Database file path (default: mappings.db)"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help=_("Overwrite existing database if it exists"),
    ),
) -> None:
    """Initialize a new encrypted mapping database."""
    from gdpr_pseudonymizer.cli.commands.init import init_command

    init_command(db_path=db_path, passphrase=passphrase, force=force)


@app.command(name="process", help=_("Process a single document with pseudonymization"))
def _process(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=_("Input file path (.txt, .md, .pdf, or .docx)"),
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help=_("Output file path (defaults to <input>_pseudonymized.ext)"),
    ),
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help=_(
            "Pseudonym library theme (neutral/star_wars/lotr). Default from config."
        ),
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help=_("NLP model name (spacy). Default from config."),
    ),
    db_path: Optional[str] = typer.Option(
        None,
        "--db",
        help=_("Database file path. Default from config."),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    entity_types: Optional[str] = typer.Option(
        None,
        "--entity-types",
        help=_(
            "Filter entity types to process (comma-separated). "
            "Options: PERSON, LOCATION, ORG. Default: all types."
        ),
    ),
) -> None:
    """Process a single document with pseudonymization."""
    from gdpr_pseudonymizer.cli.commands.process import process_command

    process_command(
        input_file=input_file,
        output_file=output_file,
        theme=theme,
        model=model,
        db_path=db_path,
        passphrase=passphrase,
        entity_types=entity_types,
    )


@app.command(name="batch", help=_("Process multiple documents in a directory"))
def _batch(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help=_("Input directory or file path"),
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help=_(
            "Output directory (defaults to same directory as input "
            "with _pseudonymized suffix)"
        ),
    ),
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help=_(
            "Pseudonym library theme (neutral/star_wars/lotr). Default from config."
        ),
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help=_("NLP model name (spacy). Default from config."),
    ),
    db_path: Optional[str] = typer.Option(
        None,
        "--db",
        help=_("Database file path. Default from config."),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help=_("Process subdirectories recursively"),
    ),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error/--no-continue-on-error",
        help=_("Continue processing on individual file errors (default: continue)"),
    ),
    workers: Optional[int] = typer.Option(
        None,
        "--workers",
        "-w",
        min=1,
        max=8,
        help=_(
            "Number of parallel workers (1=sequential with validation, "
            "2-8=parallel without validation). Default from config."
        ),
    ),
    entity_types: Optional[str] = typer.Option(
        None,
        "--entity-types",
        help=_(
            "Filter entity types to process (comma-separated). "
            "Options: PERSON, LOCATION, ORG. Default: all types."
        ),
    ),
) -> None:
    """Process multiple documents in a directory."""
    from gdpr_pseudonymizer.cli.commands.batch import batch_command

    batch_command(
        input_path=input_path,
        output_dir=output_dir,
        theme=theme,
        model=model,
        db_path=db_path,
        passphrase=passphrase,
        recursive=recursive,
        continue_on_error=continue_on_error,
        workers=workers,
        entity_types=entity_types,
    )


@app.command(name="list-mappings", help=_("View entity-to-pseudonym mappings"))
def _list_mappings(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Database file path"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    entity_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help=_("Filter by entity type (PERSON/LOCATION/ORG)"),
    ),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help=_("Search by entity name (case-insensitive substring match)"),
    ),
    export_path: Optional[Path] = typer.Option(
        None,
        "--export",
        "-e",
        help=_("Export mappings to CSV file"),
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help=_("Limit number of results"),
    ),
) -> None:
    """View entity-to-pseudonym mappings."""
    from gdpr_pseudonymizer.cli.commands.list_mappings import list_mappings_command

    list_mappings_command(
        db_path=db_path,
        passphrase=passphrase,
        entity_type=entity_type,
        search=search,
        export_path=export_path,
        limit=limit,
    )


@app.command(
    name="validate-mappings",
    help=_("Review existing mappings without processing"),
)
def _validate_mappings(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Database file path"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help=_("Interactive mode to review each mapping"),
    ),
    entity_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help=_("Filter by entity type (PERSON/LOCATION/ORG)"),
    ),
) -> None:
    """Review existing mappings without processing."""
    from gdpr_pseudonymizer.cli.commands.validate_mappings import (
        validate_mappings_command,
    )

    validate_mappings_command(
        db_path=db_path,
        passphrase=passphrase,
        interactive=interactive,
        entity_type=entity_type,
    )


@app.command(name="stats", help=_("Show database statistics and usage information"))
def _stats(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Database file path"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
) -> None:
    """Show database statistics and usage information."""
    from gdpr_pseudonymizer.cli.commands.stats import stats_command

    stats_command(db_path=db_path, passphrase=passphrase)


@app.command(
    name="import-mappings",
    help=_("Import mappings from another database"),
)
def _import_mappings(
    source_db: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=_("Source database file to import from"),
    ),
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Target database file path"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Target database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    source_passphrase: Optional[str] = typer.Option(
        None,
        "--source-passphrase",
        help=_("Source database passphrase (prompts if not provided)"),
    ),
    skip_duplicates: bool = typer.Option(
        True,
        "--skip-duplicates/--no-skip-duplicates",
        help=_("Skip duplicate entities (default) or prompt for each"),
    ),
) -> None:
    """Import mappings from another database."""
    from gdpr_pseudonymizer.cli.commands.import_mappings import import_mappings_command

    import_mappings_command(
        source_db=source_db,
        db_path=db_path,
        passphrase=passphrase,
        source_passphrase=source_passphrase,
        skip_duplicates=skip_duplicates,
    )


@app.command(name="export", help=_("Export audit log to JSON or CSV"))
def _export(
    output_path: Path = typer.Argument(
        ...,
        help=_("Output file path (.json or .csv)"),
    ),
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Database file path"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    operation_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help=_("Filter by operation type (PROCESS/BATCH/VALIDATE/etc.)"),
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help=_("Filter operations after this date (ISO 8601: YYYY-MM-DD)"),
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help=_("Filter operations before this date (ISO 8601: YYYY-MM-DD)"),
    ),
    success_only: bool = typer.Option(
        False,
        "--success-only",
        help=_("Show only successful operations"),
    ),
    failures_only: bool = typer.Option(
        False,
        "--failures-only",
        help=_("Show only failed operations"),
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help=_("Limit number of results"),
    ),
) -> None:
    """Export audit log to JSON or CSV."""
    from gdpr_pseudonymizer.cli.commands.export import export_command

    # Convert two boolean flags to Optional[bool] tri-state
    resolved_success: Optional[bool] = None
    if success_only:
        resolved_success = True
    elif failures_only:
        resolved_success = False

    export_command(
        output_path=output_path,
        db_path=db_path,
        passphrase=passphrase,
        operation_type=operation_type,
        from_date=from_date,
        to_date=to_date,
        success_only=resolved_success,
        limit=limit,
    )


@app.command(
    name="delete-mapping",
    help=_("Delete entity mapping (GDPR Article 17 erasure)"),
)
def _delete_mapping(
    entity_name: Optional[str] = typer.Argument(None, help=_("Entity name to delete")),
    db_path: str = typer.Option("mappings.db", "--db", help=_("Database file path")),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    entity_id: Optional[str] = typer.Option(
        None, "--id", help=_("Entity UUID to delete")
    ),
    reason: Optional[str] = typer.Option(
        None,
        "--reason",
        "-r",
        help=_("Reason for deletion (GDPR request reference)"),
    ),
    force: bool = typer.Option(
        False,
        "--force/--no-force",
        "-f",
        help=_("Skip confirmation prompt"),
    ),
) -> None:
    """Delete entity mapping (GDPR Article 17 erasure)."""
    from gdpr_pseudonymizer.cli.commands.delete_mapping import delete_mapping_command

    delete_mapping_command(
        entity_name=entity_name,
        db_path=db_path,
        passphrase=passphrase,
        entity_id=entity_id,
        reason=reason,
        force=force,
    )


@app.command(
    name="list-entities",
    help=_("List entities with search (for erasure workflow)"),
)
def _list_entities(
    db_path: str = typer.Option("mappings.db", "--db", help=_("Database file path")),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)"),
    ),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help=_("Search by entity name (case-insensitive substring match)"),
    ),
    entity_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help=_("Filter by type (PERSON/LOCATION/ORG)"),
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help=_("Limit number of results")
    ),
) -> None:
    """List entities with search (for erasure workflow)."""
    from gdpr_pseudonymizer.cli.commands.list_entities import list_entities_command

    list_entities_command(
        db_path=db_path,
        passphrase=passphrase,
        search=search,
        entity_type=entity_type,
        limit=limit,
    )


@app.command(
    name="destroy-table",
    help=_("Securely delete the mapping database"),
)
def _destroy_table(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help=_("Database file path to destroy"),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help=_("Skip confirmation prompt (use with caution)"),
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help=_("Passphrase to verify database ownership (recommended for safety)"),
    ),
    skip_passphrase_check: bool = typer.Option(
        False,
        "--skip-passphrase-check",
        help=_("Skip passphrase verification (not recommended)"),
    ),
) -> None:
    """Securely delete the mapping database."""
    from gdpr_pseudonymizer.cli.commands.destroy_table import destroy_table_command

    destroy_table_command(
        db_path=db_path,
        force=force,
        passphrase=passphrase,
        skip_passphrase_check=skip_passphrase_check,
    )


# Register config sub-app (lightweight — no heavy deps)
app.add_typer(
    config_app, name="config", help=_("View or modify configuration settings")
)


def cli_main() -> None:
    """Entry point for CLI with explicit program name for Windows compatibility."""
    app(prog_name="gdpr-pseudo")


if __name__ == "__main__":
    cli_main()
