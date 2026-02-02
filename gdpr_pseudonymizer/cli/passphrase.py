"""Passphrase resolution utilities for CLI commands.

This module provides passphrase resolution with the following priority:
1. CLI flag --passphrase (highest priority - for automation/scripting)
2. Environment variable GDPR_PSEUDO_PASSPHRASE
3. Interactive prompt (most secure - default behavior)

SECURITY NOTE: Passphrase is NEVER stored in config files.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import typer
from rich.console import Console

from gdpr_pseudonymizer.data.encryption import EncryptionService
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


def resolve_passphrase(
    cli_passphrase: Optional[str] = None,
    prompt_message: str = "Enter passphrase to unlock encrypted mapping database",
    confirm: bool = False,
) -> str:
    """Resolve passphrase from CLI flag, environment variable, or user prompt.

    Priority order:
    1. CLI flag (highest priority - for automation/scripting)
    2. Environment variable GDPR_PSEUDO_PASSPHRASE
    3. Interactive prompt (most secure - default behavior)

    Args:
        cli_passphrase: Passphrase from CLI flag (optional)
        prompt_message: Message to display when prompting user
        confirm: If True, prompt user to confirm passphrase (for new databases)

    Returns:
        Validated passphrase string

    Raises:
        SystemExit: If passphrase invalid or user cancels prompt
    """
    passphrase: Optional[str] = None

    # Priority 1: CLI flag
    if cli_passphrase:
        logger.info("passphrase_source", source="cli_flag")
        passphrase = cli_passphrase

    # Priority 2: Environment variable
    if passphrase is None:
        env_passphrase = os.getenv("GDPR_PSEUDO_PASSPHRASE")
        if env_passphrase:
            logger.info("passphrase_source", source="environment_variable")
            passphrase = env_passphrase

    # Priority 3: Interactive prompt
    if passphrase is None:
        console.print("\n[bold yellow]Passphrase Required[/bold yellow]")
        console.print(f"{prompt_message} (min 12 characters):")

        passphrase = typer.prompt("Passphrase", hide_input=True)
        logger.info("passphrase_source", source="user_prompt")

        # Confirmation prompt for new databases
        if confirm:
            passphrase_confirm = typer.prompt("Confirm passphrase", hide_input=True)
            if passphrase != passphrase_confirm:
                console.print("[bold red]Passphrases do not match.[/bold red]")
                sys.exit(1)

    # Validate passphrase
    is_valid, feedback = EncryptionService.validate_passphrase(str(passphrase))
    if not is_valid:
        console.print(f"[bold red]Invalid passphrase:[/bold red] {feedback}")
        sys.exit(1)

    # Warning for weak passphrase (below recommended length but still valid)
    if len(str(passphrase)) < 12:
        console.print(
            "[yellow][WARNING] Passphrase is shorter than recommended 12 characters. "
            "Consider using a stronger passphrase.[/yellow]"
        )

    return str(passphrase)
