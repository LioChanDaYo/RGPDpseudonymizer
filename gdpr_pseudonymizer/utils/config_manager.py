"""Configuration management for GDPR pseudonymizer.

This module handles loading and parsing configuration from YAML files
with a well-defined search order and validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from gdpr_pseudonymizer.exceptions import ConfigurationError


@dataclass
class Config:
    """Application configuration.

    Attributes:
        log_level: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
        model_name: NLP model name (e.g., fr_core_news_lg)
        theme: Pseudonym library theme (neutral, star_wars, lotr)
        db_path: SQLite database file path
        validation_enabled: Enable human-in-the-loop validation
    """

    log_level: str = "INFO"
    model_name: str = "fr_core_news_lg"
    theme: str = "neutral"
    db_path: str = "./gdpr-pseudo.db"
    validation_enabled: bool = True


def load_config(config_path: str | None = None) -> Config:
    """Load configuration from YAML file or defaults.

    Search order (if config_path not specified):
    1. ./gdpr-pseudo.yaml (project root)
    2. ~/.gdpr-pseudo.yaml (home directory)
    3. Default values (fallback)

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Config object with loaded or default values

    Raises:
        ConfigurationError: If config file is invalid or has syntax errors
    """
    config_data: dict[str, Any] = {}

    # If explicit path provided, use it exclusively
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            raise ConfigurationError(f"Config file not found: {config_path}")
        config_data = _load_yaml_file(config_file)
    else:
        # Search order: project root -> home directory -> defaults
        search_paths = [
            Path("./gdpr-pseudo.yaml"),
            Path.home() / ".gdpr-pseudo.yaml",
        ]

        for path in search_paths:
            if path.exists():
                config_data = _load_yaml_file(path)
                break

    # Build Config from loaded data or defaults
    return _build_config(config_data)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse YAML file with secure loader.

    Args:
        path: Path to YAML file

    Returns:
        Parsed YAML as dictionary

    Raises:
        ConfigurationError: If YAML is invalid or file cannot be read
    """
    try:
        with open(path, encoding="utf-8") as f:
            # Use safe_load to prevent code execution attacks
            data = yaml.safe_load(f)
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise ConfigurationError(
                    f"Config file must contain a YAML dictionary: {path}"
                )
            return data
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML syntax in {path}: {e}") from e
    except OSError as e:
        raise ConfigurationError(f"Cannot read config file {path}: {e}") from e


def _build_config(data: dict[str, Any]) -> Config:
    """Build Config object from parsed YAML data.

    Args:
        data: Parsed YAML dictionary

    Returns:
        Config object with validated values

    Raises:
        ConfigurationError: If required fields are invalid
    """
    config = Config()

    # Extract logging section
    if "logging" in data:
        logging_section = data["logging"]
        if not isinstance(logging_section, dict):
            raise ConfigurationError("'logging' section must be a dictionary")

        if "level" in logging_section:
            log_level = logging_section["level"]
            if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                raise ConfigurationError(
                    f"Invalid log level: {log_level}. "
                    "Must be DEBUG, INFO, WARNING, or ERROR"
                )
            config.log_level = log_level

    # Extract NLP section
    if "nlp" in data:
        nlp_section = data["nlp"]
        if not isinstance(nlp_section, dict):
            raise ConfigurationError("'nlp' section must be a dictionary")

        if "model_name" in nlp_section:
            config.model_name = str(nlp_section["model_name"])

    # Extract pseudonym section
    if "pseudonym" in data:
        pseudonym_section = data["pseudonym"]
        if not isinstance(pseudonym_section, dict):
            raise ConfigurationError("'pseudonym' section must be a dictionary")

        if "theme" in pseudonym_section:
            theme = pseudonym_section["theme"]
            if theme not in ["neutral", "star_wars", "lotr"]:
                raise ConfigurationError(
                    f"Invalid theme: {theme}. " "Must be neutral, star_wars, or lotr"
                )
            config.theme = theme

    # Extract database section
    if "database" in data:
        database_section = data["database"]
        if not isinstance(database_section, dict):
            raise ConfigurationError("'database' section must be a dictionary")

        if "path" in database_section:
            config.db_path = str(database_section["path"])

    # Extract validation section
    if "validation" in data:
        validation_section = data["validation"]
        if not isinstance(validation_section, dict):
            raise ConfigurationError("'validation' section must be a dictionary")

        if "enabled" in validation_section:
            enabled = validation_section["enabled"]
            if not isinstance(enabled, bool):
                raise ConfigurationError("'validation.enabled' must be true or false")
            config.validation_enabled = enabled

    return config
