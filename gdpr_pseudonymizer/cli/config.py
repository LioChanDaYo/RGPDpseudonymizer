"""Configuration file loading and validation for CLI.

This module provides configuration loading with priority resolution:
1. CLI flags (highest priority)
2. Project config (./.gdpr-pseudo.yaml)
3. Home config (~/.gdpr-pseudo.yaml)
4. Defaults (lowest priority)

SECURITY: Passphrase is NEVER stored in config files (plaintext storage forbidden).
Config validation rejects any config containing database.passphrase field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    path: str = "mappings.db"


@dataclass
class PseudonymizationConfig:
    """Pseudonymization configuration settings."""

    theme: str = "neutral"
    model: str = "spacy"


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    file: Optional[str] = None


@dataclass
class AppConfig:
    """Complete application configuration."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    pseudonymization: PseudonymizationConfig = field(
        default_factory=PseudonymizationConfig
    )
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class PassphraseInConfigError(ConfigValidationError):
    """Raised when passphrase is found in config file (security violation)."""

    pass


# Valid configuration values
VALID_THEMES = ["neutral", "star_wars", "lotr"]
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
VALID_MODELS = ["spacy"]


def get_default_config() -> AppConfig:
    """Get default application configuration.

    Returns:
        AppConfig with default values
    """
    return AppConfig()


def validate_config_dict(config_dict: dict[str, Any], source: str = "config") -> None:
    """Validate configuration dictionary.

    Args:
        config_dict: Configuration dictionary to validate
        source: Description of config source for error messages

    Raises:
        PassphraseInConfigError: If passphrase found in config (security violation)
        ConfigValidationError: If config values are invalid

    Note:
        SECURITY: Passphrase in config files is forbidden for security reasons.
        Use environment variable GDPR_PSEUDO_PASSPHRASE or interactive prompt.
    """
    # SECURITY CHECK: Reject any config with passphrase field
    database_config = config_dict.get("database", {})
    if isinstance(database_config, dict) and "passphrase" in database_config:
        raise PassphraseInConfigError(
            f"Passphrase in config file is forbidden for security. "
            f"Use environment variable GDPR_PSEUDO_PASSPHRASE or interactive prompt. "
            f"Source: {source}"
        )

    # Validate theme
    pseudonymization = config_dict.get("pseudonymization", {})
    if isinstance(pseudonymization, dict):
        theme = pseudonymization.get("theme")
        if theme is not None and theme not in VALID_THEMES:
            raise ConfigValidationError(
                f"Invalid theme '{theme}' in {source}. "
                f"Valid themes: {', '.join(VALID_THEMES)}"
            )

        model = pseudonymization.get("model")
        if model is not None and model not in VALID_MODELS:
            raise ConfigValidationError(
                f"Invalid model '{model}' in {source}. "
                f"Valid models: {', '.join(VALID_MODELS)}"
            )

    # Validate logging level
    logging_config = config_dict.get("logging", {})
    if isinstance(logging_config, dict):
        level = logging_config.get("level")
        if level is not None and level.upper() not in VALID_LOG_LEVELS:
            raise ConfigValidationError(
                f"Invalid logging level '{level}' in {source}. "
                f"Valid levels: {', '.join(VALID_LOG_LEVELS)}"
            )


def load_config_file(config_path: Path) -> dict[str, Any]:
    """Load and validate a single config file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigValidationError: If config file is invalid
        PassphraseInConfigError: If passphrase found in config
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(
            f"Invalid YAML in config file {config_path}: {e}"
        ) from e

    # Handle empty config file
    if config_dict is None:
        config_dict = {}

    # Validate config
    validate_config_dict(config_dict, source=str(config_path))

    return dict(config_dict)


def merge_config_dicts(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Deep merge two configuration dictionaries.

    Args:
        base: Base configuration (lower priority)
        override: Override configuration (higher priority)

    Returns:
        Merged configuration dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = merge_config_dicts(result[key], value)
        else:
            # Override value
            result[key] = value

    return result


def dict_to_config(config_dict: dict[str, Any]) -> AppConfig:
    """Convert configuration dictionary to AppConfig dataclass.

    Args:
        config_dict: Configuration dictionary

    Returns:
        AppConfig instance
    """
    database_dict = config_dict.get("database", {})
    pseudonymization_dict = config_dict.get("pseudonymization", {})
    logging_dict = config_dict.get("logging", {})

    return AppConfig(
        database=DatabaseConfig(
            path=database_dict.get("path", "mappings.db"),
        ),
        pseudonymization=PseudonymizationConfig(
            theme=pseudonymization_dict.get("theme", "neutral"),
            model=pseudonymization_dict.get("model", "spacy"),
        ),
        logging=LoggingConfig(
            level=logging_dict.get("level", "INFO"),
            file=logging_dict.get("file"),
        ),
    )


def load_config(
    config_path: Optional[Path] = None,
    cli_overrides: Optional[dict[str, Any]] = None,
) -> AppConfig:
    """Load configuration with priority resolution.

    Priority (highest to lowest):
    1. CLI overrides
    2. Custom config path (if provided)
    3. Project config (./.gdpr-pseudo.yaml)
    4. Home config (~/.gdpr-pseudo.yaml)
    5. Defaults

    Args:
        config_path: Optional custom config file path
        cli_overrides: Optional CLI flag overrides

    Returns:
        Resolved AppConfig

    Raises:
        ConfigValidationError: If any config file is invalid
        PassphraseInConfigError: If passphrase found in any config
    """
    # Start with default config as dict
    config_dict: dict[str, Any] = {
        "database": {"path": "mappings.db"},
        "pseudonymization": {"theme": "neutral", "model": "spacy"},
        "logging": {"level": "INFO", "file": None},
    }

    # Load home config if exists (~/.gdpr-pseudo.yaml)
    home_config_path = Path.home() / ".gdpr-pseudo.yaml"
    if home_config_path.exists():
        home_config = load_config_file(home_config_path)
        config_dict = merge_config_dicts(config_dict, home_config)

    # Load project config if exists (./.gdpr-pseudo.yaml)
    project_config_path = Path.cwd() / ".gdpr-pseudo.yaml"
    if project_config_path.exists():
        project_config = load_config_file(project_config_path)
        config_dict = merge_config_dicts(config_dict, project_config)

    # Load custom config path if provided
    if config_path is not None:
        custom_config = load_config_file(config_path)
        config_dict = merge_config_dicts(config_dict, custom_config)

    # Apply CLI overrides (highest priority)
    if cli_overrides is not None:
        # Validate CLI overrides
        validate_config_dict(cli_overrides, source="CLI flags")
        config_dict = merge_config_dicts(config_dict, cli_overrides)

    return dict_to_config(config_dict)
