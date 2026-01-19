"""Validation stub for entity review (placeholder for Story 1.7).

This module provides a simple validation interface for the walking skeleton.
It displays detected entities in a table and prompts for confirmation.

TODO: Replace with full validation UI in Story 1.7 (Epic 1 AC11).
"""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

# Create Rich console for output
console = Console()


def present_entities_for_validation(
    entities: list[tuple[str, str, int, int, str]]
) -> None:
    """Display detected entities in a formatted table.

    This function presents entities to the user for review before
    pseudonymization. It shows entity text, type, and suggested pseudonym.

    NOTE: This is a simplified placeholder. Story 1.7 will implement
    full validation UI with entity editing, context display, and batch actions.

    Args:
        entities: List of detected entities (entity_text, entity_type,
                 start_pos, end_pos, pseudonym)

    Examples:
        >>> entities = [("Marie Dubois", "PERSON", 0, 12, "Leia Organa")]
        >>> present_entities_for_validation(entities)
        # Displays Rich table with entity information
    """
    if not entities:
        console.print("[yellow]No entities detected.[/yellow]")
        return

    # Create table with entity information
    table = Table(title="Detected Entities", show_header=True, header_style="bold cyan")
    table.add_column("Entity", style="cyan", no_wrap=False)
    table.add_column("Type", style="magenta")
    table.add_column("Pseudonym", style="green", no_wrap=False)

    # Add entity rows (deduplicate by entity text for display)
    seen_entities = set()
    for entity_text, entity_type, start, end, pseudonym in entities:
        # Only show each unique entity once in the table
        if entity_text not in seen_entities:
            table.add_row(entity_text, entity_type, pseudonym)
            seen_entities.add(entity_text)

    console.print(table)
    console.print(f"\n[bold]Total entities found: {len(entities)}[/bold]")
    console.print(f"[bold]Unique entities: {len(seen_entities)}[/bold]\n")


def confirm_processing() -> bool:
    """Prompt user to confirm pseudonymization.

    This function asks the user to confirm whether to proceed with
    pseudonymization after reviewing detected entities.

    NOTE: This is a simplified placeholder. Story 1.7 will implement
    full validation workflow with entity modification capabilities.

    Returns:
        True if user confirms, False if user rejects

    Examples:
        >>> # User presses 'y'
        >>> confirm_processing()
        True

        >>> # User presses 'n'
        >>> confirm_processing()
        False
    """
    return Confirm.ask("Confirm pseudonymization?")
