"""Config commands for displaying and modifying configuration.

This module provides commands for:
- Displaying merged configuration from all sources
- Generating template config files with --init
- Setting individual config values with 'config set'
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table

from gdpr_pseudonymizer.cli.config import (
    load_config_file,
    merge_config_dicts,
)
from gdpr_pseudonymizer.cli.formatters import (
    ErrorCode,
    format_styled_error,
)
from gdpr_pseudonymizer.cli.validators import (
    validate_log_level,
    validate_theme,
    validate_workers,
)

# Template for config file generation
CONFIG_TEMPLATE = """\
# GDPR Pseudonymizer Configuration
# Documentation: https://github.com/YOUR_REPO/gdpr-pseudonymizer
#
# Place this file at:
#   - ~/.gdpr-pseudo.yaml     (user defaults, lowest priority)
#   - ./.gdpr-pseudo.yaml     (project-specific, higher priority)
#
# CLI flags always override config file values.

database:
  path: mappings.db          # Path to SQLite mapping database

pseudonymization:
  theme: neutral             # Pseudonym theme: neutral, star_wars, lotr
  model: spacy               # NLP model: spacy

batch:
  workers: 4                 # Parallel workers for batch processing (1-8)
                             # Use 1 for interactive validation mode
  output_dir: null           # Default output directory (null = same as input)

logging:
  level: INFO                # Log level: DEBUG, INFO, WARNING, ERROR
  file: null                 # Log file path (null = console only)

# SECURITY NOTE: Passphrase must NEVER be stored in config files.
# Use environment variable GDPR_PSEUDO_PASSPHRASE or interactive prompt.
"""

# Rich console for output
console = Console()


def _get_config_with_sources() -> tuple[dict[str, Any], dict[str, str]]:
    """Load configuration and track source of each value.

    Returns:
        Tuple of (merged config dict, sources dict mapping keys to source names)
    """
    # Start with defaults
    config_dict: dict[str, Any] = {
        "database": {"path": "mappings.db"},
        "pseudonymization": {"theme": "neutral", "model": "spacy"},
        "logging": {"level": "INFO", "file": None},
        "batch": {"workers": 4, "output_dir": None},
    }

    # Track source for each value (nested keys like "database.path")
    sources: dict[str, str] = {
        "database.path": "default",
        "pseudonymization.theme": "default",
        "pseudonymization.model": "default",
        "logging.level": "default",
        "logging.file": "default",
        "batch.workers": "default",
        "batch.output_dir": "default",
    }

    # Track which config files were found
    config_files: list[tuple[Path, str, bool]] = []

    # Load home config if exists
    home_config_path = Path.home() / ".gdpr-pseudo.yaml"
    if home_config_path.exists():
        try:
            home_config = load_config_file(home_config_path)
            config_dict = merge_config_dicts(config_dict, home_config)
            # Update sources for values from home config
            _update_sources(sources, home_config, "home")
            config_files.append((home_config_path, "home", True))
        except Exception:
            config_files.append((home_config_path, "home", False))
    else:
        config_files.append((home_config_path, "home", False))

    # Load project config if exists
    project_config_path = Path.cwd() / ".gdpr-pseudo.yaml"
    if project_config_path.exists():
        try:
            project_config = load_config_file(project_config_path)
            config_dict = merge_config_dicts(config_dict, project_config)
            # Update sources for values from project config
            _update_sources(sources, project_config, "project")
            config_files.append((project_config_path, "project", True))
        except Exception:
            config_files.append((project_config_path, "project", False))
    else:
        config_files.append((project_config_path, "project", False))

    # Add config files info to return
    config_dict["_config_files"] = config_files

    return config_dict, sources


def _update_sources(
    sources: dict[str, str],
    config_section: dict[str, Any],
    source_name: str,
    prefix: str = "",
) -> None:
    """Update sources dict for values that came from a config file.

    Args:
        sources: Dict mapping dotted keys to source names
        config_section: Config section being processed
        source_name: Name of the source (home, project)
        prefix: Key prefix for nested dicts
    """
    for key, value in config_section.items():
        full_key = f"{prefix}{key}" if prefix else key

        if isinstance(value, dict):
            _update_sources(sources, value, source_name, f"{full_key}.")
        else:
            sources[full_key] = source_name


def _format_value(value: Any) -> str:
    """Format a config value for display.

    Args:
        value: The config value

    Returns:
        Formatted string representation
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _generate_config_template(force: bool = False) -> None:
    """Generate a template config file in the current directory.

    Args:
        force: If True, overwrite existing config file

    Raises:
        typer.Exit: If config file exists and force is False
    """
    config_path = Path.cwd() / ".gdpr-pseudo.yaml"

    if config_path.exists() and not force:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Config file already exists: {config_path}"
        )
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(1)

    try:
        config_path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        console.print(f"[bold green]Created:[/bold green] {config_path}")
        console.print("\nEdit this file to customize your settings.")
        console.print(
            "Run [bold]gdpr-pseudo config[/bold] to view effective configuration."
        )
    except OSError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to write config file: {e}")
        raise typer.Exit(1)


def config_show_command(
    init: bool = typer.Option(
        False,
        "--init",
        help="Generate a template .gdpr-pseudo.yaml in current directory",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing config file when using --init",
    ),
) -> None:
    """Display the current effective configuration or generate a template.

    Without flags, shows the merged configuration from all sources with
    annotations indicating where each value came from.

    Configuration sources (in priority order):

    1. CLI flags (highest priority - not shown in this command)
    2. Project config: ./.gdpr-pseudo.yaml in current directory
    3. Home config: ~/.gdpr-pseudo.yaml in user home directory
    4. Built-in defaults (lowest priority)

    Source annotations shown for each value:
    - [project] = from ./.gdpr-pseudo.yaml
    - [home] = from ~/.gdpr-pseudo.yaml
    - [default] = built-in default value

    Examples:
        gdpr-pseudo config              # Show current config
        gdpr-pseudo config --init       # Generate template config file
        gdpr-pseudo config --init -f    # Overwrite existing config file
    """
    # Handle --init flag
    if init:
        _generate_config_template(force)
        return
    config_dict, sources = _get_config_with_sources()
    config_files = config_dict.pop("_config_files", [])

    console.print("\n[bold]Effective Configuration[/bold]")
    console.print("=" * 40)
    console.print()

    # Create table for config display
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Source", style="dim")

    # Helper to format source annotation (escape brackets for Rich)
    def source_annotation(key: str) -> str:
        return f"\\[{sources.get(key, 'default')}]"

    # Database section
    db_path = config_dict.get("database", {}).get("path", "mappings.db")
    table.add_row(
        "database.path",
        _format_value(db_path),
        source_annotation("database.path"),
    )

    table.add_row("", "", "")  # Spacing

    # Pseudonymization section
    pseudo_config = config_dict.get("pseudonymization", {})
    table.add_row(
        "pseudonymization.theme",
        _format_value(pseudo_config.get("theme", "neutral")),
        source_annotation("pseudonymization.theme"),
    )
    table.add_row(
        "pseudonymization.model",
        _format_value(pseudo_config.get("model", "spacy")),
        source_annotation("pseudonymization.model"),
    )

    table.add_row("", "", "")  # Spacing

    # Batch section
    batch_config = config_dict.get("batch", {})
    table.add_row(
        "batch.workers",
        _format_value(batch_config.get("workers", 4)),
        source_annotation("batch.workers"),
    )
    table.add_row(
        "batch.output_dir",
        _format_value(batch_config.get("output_dir")),
        source_annotation("batch.output_dir"),
    )

    table.add_row("", "", "")  # Spacing

    # Logging section
    logging_config = config_dict.get("logging", {})
    table.add_row(
        "logging.level",
        _format_value(logging_config.get("level", "INFO")),
        source_annotation("logging.level"),
    )
    table.add_row(
        "logging.file",
        _format_value(logging_config.get("file")),
        source_annotation("logging.file"),
    )

    console.print(table)

    # Show config files status
    console.print()
    console.print("[bold]Config files loaded:[/bold]")
    for path, source_type, loaded in config_files:
        if loaded:
            console.print(f"  [green]\u2713[/green] {path} (\\[{source_type}])")
        else:
            console.print(f"  [dim]\u2717 {path} (not found)[/dim]")

    console.print()


# Valid config keys and their validators
CONFIG_KEY_VALIDATORS = {
    "pseudonymization.theme": ("theme", validate_theme),
    "pseudonymization.model": ("model", lambda x: (x.lower() == "spacy", x.lower())),
    "batch.workers": ("workers", lambda x: validate_workers(int(x))),
    "batch.output_dir": (
        "output_dir",
        lambda x: (True, x if x.lower() != "null" else None),
    ),
    "logging.level": ("level", validate_log_level),
    "logging.file": ("file", lambda x: (True, x if x.lower() != "null" else None)),
    "database.path": ("path", lambda x: (True, x)),
}


def _set_nested_value(config: dict[str, Any], key: str, value: Any) -> None:
    """Set a nested value in a config dictionary.

    Args:
        config: Config dictionary to modify
        key: Dotted key path (e.g., "pseudonymization.theme")
        value: Value to set
    """
    parts = key.split(".")
    current = config

    # Navigate to parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value


def config_set_command(
    key: str = typer.Argument(..., help="Config key (e.g., pseudonymization.theme)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value.

    Modifies the project config file (.gdpr-pseudo.yaml) in the current directory.
    Creates the file if it doesn't exist.

    Supported keys:
        pseudonymization.theme   Theme for pseudonyms (neutral, star_wars, lotr)
        pseudonymization.model   NLP model (spacy)
        batch.workers            Number of parallel workers (1-8)
        batch.output_dir         Default output directory (or null)
        logging.level            Log level (DEBUG, INFO, WARNING, ERROR)
        logging.file             Log file path (or null)
        database.path            Database file path

    Examples:
        gdpr-pseudo config set pseudonymization.theme star_wars
        gdpr-pseudo config set batch.workers 2
        gdpr-pseudo config set logging.level DEBUG
    """
    # Validate key
    if key not in CONFIG_KEY_VALIDATORS:
        format_styled_error(
            ErrorCode.INVALID_CONFIG_VALUE,
            f"Unknown config key: {key}",
        )
        console.print(
            f"[dim]Valid keys: {', '.join(CONFIG_KEY_VALIDATORS.keys())}[/dim]"
        )
        raise typer.Exit(1)

    # Validate value
    field_name, validator = CONFIG_KEY_VALIDATORS[key]
    try:
        is_valid, validated_value = validator(value)
    except (ValueError, TypeError) as e:
        format_styled_error(
            ErrorCode.INVALID_CONFIG_VALUE,
            f"Invalid value for {key}: {e}",
        )
        raise typer.Exit(1)

    if not is_valid:
        raise typer.Exit(1)

    # Load existing config or create empty
    config_path = Path.cwd() / ".gdpr-pseudo.yaml"
    config_dict: dict[str, Any] = {}

    if config_path.exists():
        try:
            content = config_path.read_text(encoding="utf-8")
            loaded = yaml.safe_load(content)
            if loaded is not None:
                config_dict = loaded
        except yaml.YAMLError as e:
            format_styled_error(
                ErrorCode.CONFIG_PARSE_ERROR,
                f"Failed to parse existing config: {e}",
            )
            raise typer.Exit(1)

    # Set the value
    _set_nested_value(config_dict, key, validated_value)

    # Write back
    try:
        # Use yaml.dump with nice formatting
        yaml_content = yaml.dump(
            config_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        # Add header comment if new file
        if not config_path.exists():
            header = "# GDPR Pseudonymizer Configuration\n# Generated by 'gdpr-pseudo config set'\n\n"
            yaml_content = header + yaml_content

        config_path.write_text(yaml_content, encoding="utf-8")
        console.print(f"[green]Set {key} = {validated_value}[/green]")
        console.print(f"[dim]Config file: {config_path}[/dim]")

    except OSError as e:
        format_styled_error(
            ErrorCode.PERMISSION_DENIED,
            f"Failed to write config file: {e}",
        )
        raise typer.Exit(1)


# Create config sub-app for subcommands
config_app = typer.Typer(
    name="config",
    help="View or modify configuration settings",
    no_args_is_help=False,
    invoke_without_command=True,
)


@config_app.callback(invoke_without_command=True)  # type: ignore[untyped-decorator]
def config_callback(
    ctx: typer.Context,
    init: bool = typer.Option(
        False,
        "--init",
        help="Generate a template .gdpr-pseudo.yaml in current directory",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing config file when using --init",
    ),
) -> None:
    """Display the current effective configuration or generate a template.

    Without flags or subcommands, shows the merged configuration from all
    sources with annotations indicating where each value came from.
    """
    # If no subcommand was invoked, run the show command
    if ctx.invoked_subcommand is None:
        config_show_command(init=init, force=force)


# Register set subcommand
config_app.command(name="set")(config_set_command)
