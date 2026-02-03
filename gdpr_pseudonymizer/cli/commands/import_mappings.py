"""Import-mappings command for loading mappings from another database.

This command merges entity mappings from a source database into the current one.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    DuplicateEntityError,
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()


def import_mappings_command(
    source_db: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Source database file to import from",
    ),
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help="Target database file path",
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Target database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    source_passphrase: Optional[str] = typer.Option(
        None,
        "--source-passphrase",
        help="Source database passphrase (prompts if not provided)",
    ),
    skip_duplicates: bool = typer.Option(
        True,
        "--skip-duplicates/--prompt-duplicates",
        help="Skip duplicate entities (default) or prompt for each",
    ),
) -> None:
    """Import mappings from another database.

    Merges entity mappings from a source database into the current database.
    Useful for combining mapping tables from different projects.

    Conflict handling:
    - By default, duplicate entities (same full_name + type) are skipped
    - Use --prompt-duplicates to be prompted for each conflict

    Examples:
        # Import from another database
        gdpr-pseudo import-mappings old_project.db

        # Import to specific database
        gdpr-pseudo import-mappings old_project.db --db new_project.db

        # Prompt for duplicate handling
        gdpr-pseudo import-mappings old.db --prompt-duplicates
    """
    try:
        # Validate target database exists
        target_db_file = Path(db_path)
        if not target_db_file.exists():
            format_error_message(
                "Target Database Not Found",
                f"Target database file not found: {target_db_file.absolute()}",
                "Run 'gdpr-pseudo init' to create a new database.",
            )
            sys.exit(1)

        # Validate source and target are different
        if source_db.resolve() == target_db_file.resolve():
            format_error_message(
                "Invalid Operation",
                "Source and target databases are the same file.",
                "Specify different source and target databases.",
            )
            sys.exit(1)

        # Get source passphrase
        console.print("\n[bold]Source Database[/bold]")
        source_resolved_passphrase = resolve_passphrase(
            cli_passphrase=source_passphrase,
            prompt_message=f"Enter passphrase for source database ({source_db.name})",
            confirm=False,
        )

        # Get target passphrase
        console.print("\n[bold]Target Database[/bold]")
        target_resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message=f"Enter passphrase for target database ({target_db_file.name})",
            confirm=False,
        )

        # Import statistics
        imported = 0
        skipped = 0
        errors = 0

        # Open source database and read entities
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Reading source database...", total=None)

            try:
                with open_database(
                    str(source_db), source_resolved_passphrase
                ) as source_session:
                    source_repo = SQLiteMappingRepository(source_session)
                    source_entities = source_repo.find_all()
                    progress.update(
                        task,
                        description=f"✓ Found {len(source_entities)} entities in source",
                    )
            except ValueError as e:
                progress.update(task, description="✗ Failed to open source database")
                format_error_message(
                    "Source Database Error",
                    str(e),
                    "Check source passphrase and try again.",
                )
                sys.exit(1)

        if not source_entities:
            console.print("\n[yellow]No entities found in source database.[/yellow]")
            sys.exit(0)

        console.print(f"\n[bold]Importing {len(source_entities)} entities...[/bold]\n")

        # Open target database and import
        with open_database(db_path, target_resolved_passphrase) as target_session:
            target_repo = SQLiteMappingRepository(target_session)

            for entity in source_entities:
                # Check for existing entity
                existing = target_repo.find_by_full_name(entity.full_name)

                if existing:
                    if skip_duplicates:
                        skipped += 1
                        continue

                    # Prompt user for duplicate
                    console.print(
                        f"\n[yellow]Duplicate found:[/yellow] {entity.full_name}"
                    )
                    console.print(f"  Existing pseudonym: {existing.pseudonym_full}")
                    console.print(f"  Import pseudonym:   {entity.pseudonym_full}")

                    if not Confirm.ask("Replace existing mapping?", default=False):
                        skipped += 1
                        continue

                try:
                    # Create new entity without ID (let DB generate new one)
                    from gdpr_pseudonymizer.data.models import Entity as EntityModel

                    new_entity = EntityModel(
                        entity_type=entity.entity_type,
                        full_name=entity.full_name,
                        first_name=entity.first_name,
                        last_name=entity.last_name,
                        pseudonym_full=entity.pseudonym_full,
                        pseudonym_first=entity.pseudonym_first,
                        pseudonym_last=entity.pseudonym_last,
                        theme=entity.theme,
                        confidence_score=entity.confidence_score,
                        is_ambiguous=entity.is_ambiguous,
                        ambiguity_reason=entity.ambiguity_reason,
                        gender=entity.gender,
                    )

                    target_repo.save(new_entity)
                    imported += 1

                except DuplicateEntityError:
                    skipped += 1
                except Exception as e:
                    errors += 1
                    logger.error(
                        "import_entity_error",
                        entity=entity.full_name,
                        error=str(e),
                    )

        # Display results
        console.print("\n[bold]Import Complete[/bold]\n")
        console.print(f"  Imported: [green]{imported}[/green]")
        console.print(f"  Skipped:  [yellow]{skipped}[/yellow]")
        if errors:
            console.print(f"  Errors:   [red]{errors}[/red]")

        logger.info(
            "import_complete",
            source=str(source_db),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

    except FileNotFoundError as e:
        format_error_message(
            "Database Not Found",
            str(e),
            "Check the database path and try again.",
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
        console.print("\n\n[yellow]Import cancelled by user[/yellow]")
        sys.exit(0)

    except Exception as e:
        logger.error("import_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)
