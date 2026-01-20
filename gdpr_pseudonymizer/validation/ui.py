"""CLI UI components for validation workflow.

This module contains Rich-based UI components for displaying entities
and capturing user input during the validation workflow.
"""

from __future__ import annotations

import readchar
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

# Create Rich console for output
console = Console()


def get_user_action() -> str:
    """Capture single keypress for user action.

    Returns:
        Action string: confirm, reject, modify, add, change_pseudonym,
                      next, previous, help, quit, batch_accept, batch_reject, invalid
    """
    key = readchar.readkey()

    # Map single-key actions
    if key == " ":
        return "confirm"
    elif key.lower() == "r":
        return "reject"
    elif key.lower() == "e":
        return "modify"
    elif key.lower() == "a":
        return "add"
    elif key.lower() == "c":
        return "change_pseudonym"
    elif key.lower() == "h" or key == "?":
        return "help"
    elif key.lower() == "n" or key == readchar.key.DOWN or key == readchar.key.RIGHT:
        return "next"
    elif key.lower() == "p" or key == readchar.key.UP or key == readchar.key.LEFT:
        return "previous"
    elif key.lower() == "q":
        return "quit"
    elif key.upper() == "A":  # Shift+A
        return "batch_accept"
    elif key.upper() == "R":  # Shift+R
        return "batch_reject"
    else:
        return "invalid"


def get_text_input(prompt_text: str) -> str:
    """Get text input from user using Rich prompt.

    Args:
        prompt_text: Prompt message to display

    Returns:
        User input string
    """
    return Prompt.ask(prompt_text)


def get_confirmation(prompt_text: str) -> bool:
    """Get yes/no confirmation from user.

    Args:
        prompt_text: Confirmation message to display

    Returns:
        True if user confirms, False otherwise
    """
    return Confirm.ask(prompt_text)


class SummaryScreen:
    """Summary screen showing entity detection statistics."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize summary screen.

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()

    def display(self, total_entities: int, entity_counts: dict[str, int]) -> None:
        """Display summary of detected entities.

        Args:
            total_entities: Total number of entities detected
            entity_counts: Dictionary mapping entity type to count
        """
        self.console.clear()
        self.console.print()

        # Create summary panel
        summary_lines = [
            f"[bold cyan]Total entities detected:[/bold cyan] {total_entities}",
            "",
        ]

        for entity_type, count in sorted(entity_counts.items()):
            if entity_type == "PERSON":
                icon = "👤"
            elif entity_type == "LOCATION":
                icon = "📍"
            elif entity_type == "ORG":
                icon = "🏢"
            else:
                icon = "❓"
            summary_lines.append(f"{icon} [magenta]{entity_type}:[/magenta] {count}")

        summary_lines.append("")

        # Estimate validation time (6 seconds per entity)
        estimated_minutes = (total_entities * 6) // 60
        if estimated_minutes < 1:
            time_str = "< 1 minute"
        else:
            time_str = f"~{estimated_minutes} minutes"

        summary_lines.append(f"[yellow]Estimated validation time:[/yellow] {time_str}")
        summary_lines.append("")
        summary_lines.append(
            "[dim]Press [bold]Enter[/bold] to begin validation review...[/dim]"
        )

        panel = Panel(
            "\n".join(summary_lines),
            title="📋 Entity Detection Summary",
            border_style="cyan",
        )

        self.console.print(panel)

    def wait_for_enter(self) -> None:
        """Wait for user to press Enter to continue."""
        readchar.readkey()


class ReviewScreen:
    """Entity review screen for single entity validation."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize review screen.

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()

    def display_entity(
        self,
        entity: DetectedEntity,
        context: str,
        pseudonym: str,
        entity_number: int,
        total_entities: int,
        entity_type_filter: str | None = None,
    ) -> None:
        """Display single entity for review.

        Args:
            entity: Entity to display
            context: Context snippet showing entity in document
            pseudonym: Suggested pseudonym
            entity_number: Current entity number (1-indexed)
            total_entities: Total number of entities
            entity_type_filter: Current entity type being reviewed (optional)
        """
        self.console.clear()
        self.console.print()

        # Progress indicator
        progress_text = f"Entity {entity_number}/{total_entities}"
        if entity_type_filter:
            progress_text += f" ({entity_type_filter})"

        self.console.print(f"[dim]{progress_text}[/dim]")
        self.console.print()

        # Create entity display table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Entity text
        entity_display = f"[bold cyan]{entity.text}[/bold cyan]"
        if entity.is_ambiguous:
            entity_display = f"⚠️  {entity_display} [yellow](ambiguous)[/yellow]"

        table.add_row("Entity:", entity_display)
        table.add_row("Type:", f"[magenta]{entity.entity_type}[/magenta]")

        # Confidence score with color coding
        if entity.confidence is not None:
            conf_percent = int(entity.confidence * 100)
            if conf_percent >= 80:
                conf_color = "green"
            elif conf_percent >= 60:
                conf_color = "yellow"
            else:
                conf_color = "red"
            confidence_bar = "█" * (conf_percent // 5)
            table.add_row(
                "Confidence:",
                f"[{conf_color}]{conf_percent}%[/{conf_color}] [{conf_color}]{confidence_bar}[/{conf_color}]",
            )

        table.add_row("→ Pseudonym:", f"[green]{pseudonym}[/green]")
        table.add_row("", "")
        table.add_row("Context:", f"[dim]{context}[/dim]")

        self.console.print(table)
        self.console.print()

        # Action hints
        self.console.print("[bold]Actions:[/bold]")
        self.console.print(
            "  [Space] Confirm  [R] Reject  [E] Modify  [C] Change Pseudonym"
        )
        self.console.print(
            "  [N/→] Next  [P/←] Previous  [A] Add Entity  [H] Help  [Q] Quit"
        )
        self.console.print()
        self.console.print("[dim]Choose action:[/dim] ", end="")

    def display_ambiguous_warning(self, entity: DetectedEntity, reason: str) -> None:
        """Display warning for ambiguous entity.

        Args:
            entity: Ambiguous entity
            reason: Reason for ambiguity
        """
        warning_panel = Panel(
            f"⚠️  [yellow]Ambiguous entity detected[/yellow]\n\n"
            f"Entity: [bold]{entity.text}[/bold]\n"
            f"Reason: {reason}\n\n"
            f"[dim]Please review carefully and confirm or modify.[/dim]",
            title="Ambiguity Warning",
            border_style="yellow",
        )
        self.console.print(warning_panel)
        self.console.print()


class FinalConfirmationScreen:
    """Final confirmation screen showing validation summary."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize final confirmation screen.

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()

    def display(self, summary_stats: dict[str, int]) -> None:
        """Display validation summary and prompt for final confirmation.

        Args:
            summary_stats: Dictionary with counts (confirmed, rejected, modified, added)
        """
        self.console.clear()
        self.console.print()

        # Create summary lines
        summary_lines = [
            "[bold cyan]Validation Complete![/bold cyan]",
            "",
            f"✓ Confirmed: [green]{summary_stats.get('confirmed', 0)}[/green]",
            f"✗ Rejected: [red]{summary_stats.get('rejected', 0)}[/red]",
            f"✏️  Modified: [yellow]{summary_stats.get('modified', 0)}[/yellow]",
            f"➕ Added: [cyan]{summary_stats.get('added', 0)}[/cyan]",
            "",
            f"[bold]Total entities to process:[/bold] {summary_stats.get('confirmed', 0) + summary_stats.get('modified', 0) + summary_stats.get('added', 0)}",
        ]

        panel = Panel(
            "\n".join(summary_lines),
            title="📊 Validation Summary",
            border_style="green",
        )

        self.console.print(panel)
        self.console.print()


class HelpOverlay:
    """Help overlay displaying keyboard shortcuts."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize help overlay.

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()

    def display(self) -> None:
        """Display help overlay with keyboard shortcuts."""
        help_text = """[bold cyan]Keyboard Shortcuts[/bold cyan]

[bold]Core Actions:[/bold]
  [Space]     Confirm entity and pseudonym
  [R]         Reject entity (mark as false positive)
  [E]         Edit entity text
  [A]         Add missed entity manually
  [C]         Change suggested pseudonym

[bold]Navigation:[/bold]
  [N] / [→]   Next entity
  [P] / [←]   Previous entity
  [Q]         Quit validation (with confirmation)

[bold]Batch Operations:[/bold]
  [Shift+A]   Accept all entities of current type
  [Shift+R]   Reject all entities of current type

[bold]Help & Utility:[/bold]
  [H] / [?]   Show this help overlay

[dim]Press any key to close help...[/dim]
"""
        self.console.clear()
        self.console.print()

        panel = Panel(help_text, title="❓ Help", border_style="cyan")
        self.console.print(panel)

        # Wait for any key
        readchar.readkey()


def display_error_message(title: str, message: str) -> None:
    """Display error message to user.

    Args:
        title: Error title
        message: Error message details
    """
    console.print()
    error_panel = Panel(f"[red]{message}[/red]", title=f"❌ {title}", border_style="red")
    console.print(error_panel)
    console.print()


def display_info_message(message: str) -> None:
    """Display info message to user.

    Args:
        message: Info message to display
    """
    console.print(f"[cyan]ℹ️  {message}[/cyan]")


def display_warning_message(message: str) -> None:
    """Display warning message to user.

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def display_success_message(message: str) -> None:
    """Display success message to user.

    Args:
        message: Success message to display
    """
    console.print(f"[green]✓ {message}[/green]")
