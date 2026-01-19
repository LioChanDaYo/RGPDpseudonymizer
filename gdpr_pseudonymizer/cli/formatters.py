"""Rich output formatting for CLI messages.

This module provides consistent formatting for success, error, and
informational messages using Rich styling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Create Rich console for output
console = Console()


def format_success_message(
    input_file: Path,
    output_file: Path,
    entities_detected: int,
    entities_replaced: int,
    unique_entities: int,
) -> None:
    """Display success message with processing summary.

    Args:
        input_file: Path to input file
        output_file: Path to output file
        entities_detected: Total number of entity occurrences detected
        entities_replaced: Total number of entity occurrences replaced
        unique_entities: Number of unique entities
    """
    # Create summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Input file", str(input_file))
    table.add_row("Output file", str(output_file))
    table.add_row("Entities detected", str(entities_detected))
    table.add_row("Entities replaced", str(entities_replaced))
    table.add_row("Unique entities", str(unique_entities))

    # Display success panel
    console.print()
    console.print(
        Panel(
            table,
            title="[bold green]+ Processing Complete[/bold green]",
            border_style="green",
        )
    )


def format_error_message(
    error_type: str, error_message: str, suggestion: Optional[str] = None
) -> None:
    """Display error message with optional suggestion.

    Args:
        error_type: Type of error (e.g., "File Not Found", "Permission Denied")
        error_message: Detailed error message
        suggestion: Optional suggestion for fixing the error
    """
    console.print()
    console.print(f"[bold red]X Error: {error_type}[/bold red]")
    console.print(f"[red]{error_message}[/red]")

    if suggestion:
        console.print()
        console.print(f"[yellow]> {suggestion}[/yellow]")

    console.print()


def format_info_message(message: str) -> None:
    """Display informational message.

    Args:
        message: Information message to display
    """
    console.print(f"[cyan]i {message}[/cyan]")


def format_warning_message(message: str) -> None:
    """Display warning message.

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]! {message}[/yellow]")


def format_validation_cancelled() -> None:
    """Display message when user cancels validation."""
    console.print()
    console.print("[yellow]X Processing cancelled by user[/yellow]")
    console.print()
