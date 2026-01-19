"""CLI entry point for GDPR pseudonymizer.

This module provides the main Typer application instance and
command registration for the CLI interface.
"""

from __future__ import annotations

import typer
from rich.console import Console

from gdpr_pseudonymizer.cli.commands.process import process_command

# Create Typer app instance
app = typer.Typer(
    name="gdpr-pseudo",
    help="GDPR-compliant pseudonymization tool for French text documents",
    add_completion=False,
)

# Create Rich console for output
console = Console()


def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        console.print("gdpr-pseudo version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """GDPR-compliant pseudonymization tool for French text documents.

    This tool performs entity detection and pseudonymization with
    human-in-the-loop validation for research interview transcripts.
    """
    pass


# Register commands
app.command(name="process")(process_command)


if __name__ == "__main__":
    app()
