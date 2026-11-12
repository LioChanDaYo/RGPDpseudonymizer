"""Replace-pseudonym command (Story 11.7).

A mapping database filled before 2.3.1 can hold pseudonyms that hold a word
of the very name they stand for (« Élodie Martin » saved as « Élodie
Lucas »): later documents write that word in clear. This command replaces
them, one (``--id``) or all (``--all``), after showing every row that
changes: the pseudonyms of the names that share the replaced first or last
name change with them, so that one name keeps one pseudonym. It is built
like ``delete-mapping``: the same options, a typed ``yes``, one audit entry,
the same exit codes (0 done or cancelled, 1 refused, 2 unexpected).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.core.saved_own_words import (
    STOP_CHANGED,
    STOP_CUSTOM_ROW,
    STOP_NOT_FOUND,
    ReplacementPlan,
    plan_replacement,
    replace_own_word_rows,
)
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

# The approved texts (Story 11.7, Dev Notes "Exact texts"; C11-C17)
LEAKING_HEADING = "These pseudonyms hold a word of their own name and will be replaced:"
SHARING_HEADING = (
    "These share their first or last name with them and will change too, "
    "so that one name keeps one pseudonym:"
)
WARNING = (
    "Documents already written keep the old pseudonyms, and this database "
    "will no longer say which name they stood for. Process their original "
    "documents again to write the new pseudonyms. Replaced pseudonyms are free "
    "again: one may later be given to another name, so old and new documents "
    "could then use the same pseudonym for two different names."
)
PROMPT = "Type 'yes' to replace these pseudonyms"
CANCELLED = "Replacement cancelled. No changes made."
NONE_TO_REPLACE = "No pseudonym holds a word of its own name. Nothing to replace."
USAGE_HINT = (
    "Use 'gdpr-pseudo replace-pseudonym --id <id>' or "
    "'gdpr-pseudo replace-pseudonym --all'."
)


def replace_pseudonym_command(
    db_path: str = typer.Option("mappings.db", "--db", help="Database file path"),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    entity_id: Optional[str] = typer.Option(
        None,
        "--id",
        help="ID of the mapping to replace (see 'validate-mappings --own-words')",
    ),
    replace_all: bool = typer.Option(
        False,
        "--all",
        help="Replace every pseudonym that contains a word of the name it replaces",
    ),
    force: bool = typer.Option(
        False, "--force/--no-force", "-f", help="Skip confirmation prompt"
    ),
) -> None:
    """Replace pseudonyms that contain a word of the name they replace.

    Examples:
        # Replace one (its ID as validate-mappings --own-words shows it)
        gdpr-pseudo replace-pseudonym --id abc12345

        # Replace all of them
        gdpr-pseudo replace-pseudonym --all
    """
    try:
        if entity_id and replace_all:
            format_error_message(
                "Invalid Arguments",
                "Provide either --id or --all, not both.",
                USAGE_HINT,
            )
            sys.exit(1)
        if not entity_id and not replace_all:
            format_error_message(
                "Missing Argument", "No mapping specified.", USAGE_HINT
            )
            sys.exit(1)

        db_file = Path(db_path)
        if not db_file.exists():
            format_error_message(
                "Database Not Found",
                f"Database file not found: {db_file.absolute()}",
                "Run 'gdpr-pseudo init' to create a new database.",
            )
            sys.exit(1)

        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase to unlock database",
            confirm=False,
        )

        with open_database(db_path, resolved_passphrase) as db_session:
            rows = SQLiteMappingRepository(db_session).find_all()
            by_id = {row.id: row for row in rows}

            entity_ids: list[str] | None = None
            if entity_id:
                full_id = _full_id(rows, entity_id)
                if full_id is None:
                    _not_found(entity_id)
                entity_ids = [full_id]

            plan = plan_replacement(rows, entity_ids)
            if replace_all and not plan.groups and plan.stop_reason is None:
                console.print(NONE_TO_REPLACE)
                sys.exit(0)
            if plan.stop_reason is not None:
                _stop(plan.stop_reason, plan, by_id, entity_id or "")

            _display_plan(plan, by_id)

            if not force:
                answer = Prompt.ask(PROMPT, default="")
                if answer.lower() != "yes":
                    console.print(CANCELLED)
                    sys.exit(0)

            result = replace_own_word_rows(
                db_session, entity_ids, confirmed=plan.changed_ids
            )
            if result.stop_reason is not None:
                _stop(result.stop_reason, result.plan, by_id, entity_id or "")

            count = len(result.changes)
            console.print(
                (
                    "\n1 pseudonym replaced:"
                    if count == 1
                    else f"\n{count} pseudonyms replaced:"
                ),
                markup=False,
            )
            for change in result.changes:
                console.print(
                    f"  {change.name} ({change.entity_type}): "
                    f"{change.old} → {change.new}",
                    markup=False,
                    highlight=False,
                )
            console.print(
                "REPLACEMENT audit log entry created "
                f"(operation {(result.operation_id or '')[:8]}...).",
                markup=False,
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
        # Story 11.7 (AC9): no name, pseudonym or word in a log line
        logger.error("replace_pseudonym_error", error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)


def _full_id(rows: list[Entity], entity_id: str) -> str | None:
    """The full id of a row given in full or by a prefix (as
    ``delete-mapping --id``); None if none or several."""
    for row in rows:
        if row.id == entity_id:
            return row.id
    matches = [row.id for row in rows if row.id.startswith(entity_id)]
    return matches[0] if len(matches) == 1 else None


def _not_found(entity_id: str) -> NoReturn:
    format_error_message(
        "Nothing to Replace",
        f"No mapping with this ID holds a word of its own name: {entity_id}",
        "Use 'gdpr-pseudo validate-mappings --own-words' to list them.",
    )
    sys.exit(1)


def _stop(
    reason: str, plan: ReplacementPlan, by_id: dict[str, Entity], entity_id: str
) -> NoReturn:
    """Show why nothing was replaced (C17c, C17e, C17f, C17g) and exit 1."""
    if reason == STOP_NOT_FOUND:
        _not_found(entity_id or (plan.stop_ids[0][:8] if plan.stop_ids else ""))
    if reason == STOP_CHANGED:
        format_error_message(
            "Database Changed",
            "The database has changed since the list was shown. "
            "Nothing was replaced.",
            "Run the command again.",
        )
    elif reason == STOP_CUSTOM_ROW:
        lead = by_id.get(plan.stop_ids[0]) if plan.stop_ids else None
        custom = by_id.get(plan.stop_ids[-1]) if plan.stop_ids else None
        format_error_message(
            "Chosen Pseudonym",
            f"The pseudonym of {lead.full_name if lead else ''} shares a first "
            "or last name with a pseudonym you chose yourself "
            f"({custom.pseudonym_full if custom else ''}). Nothing was replaced.",
            "Replace the others one at a time with --id. To replace this one, "
            "first delete the mapping of the pseudonym you chose "
            "('gdpr-pseudo delete-mapping').",
        )
    else:
        format_error_message(
            "No Free Pseudonym",
            "The pseudonym library has no free name left for one of these "
            "pseudonyms. Nothing was replaced.",
            "Replace the others one at a time with --id, or report this issue.",
        )
    sys.exit(1)


def _display_plan(plan: ReplacementPlan, by_id: dict[str, Entity]) -> None:
    """The rows that leak (with the word), the rows that change with them,
    then the warning (C11, C12, C13); every line is printed."""
    console.print()
    console.print(LEAKING_HEADING, markup=False)
    for own in plan.leaking:
        row = by_id[own.entity_id]
        console.print(
            f"  {row.full_name} ({row.entity_type}): {row.pseudonym_full}"
            f"   (word: {own.word})",
            markup=False,
            highlight=False,
        )
    if plan.others:
        console.print()
        console.print(SHARING_HEADING, markup=False)
        for other_id in plan.others:
            row = by_id[other_id]
            console.print(
                f"  {row.full_name} ({row.entity_type}): {row.pseudonym_full}",
                markup=False,
                highlight=False,
            )
    console.print()
    console.print(WARNING, markup=False)
    console.print()
