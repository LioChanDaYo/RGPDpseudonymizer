"""Unit tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import pytest

from gdpr_pseudonymizer.exceptions import ConfigurationError
from gdpr_pseudonymizer.utils.config_manager import Config, load_config


def test_config_default_values() -> None:
    """Test Config dataclass with default values."""
    config = Config()

    assert config.log_level == "INFO"
    assert config.model_name == "fr_core_news_lg"
    assert config.theme == "neutral"
    assert config.db_path == "./gdpr-pseudo.db"
    assert config.validation_enabled is True


def test_load_config_with_missing_file(tmp_path: Path) -> None:
    """Test loading config from non-existent explicit path raises error."""
    nonexistent_path = tmp_path / "missing.yaml"

    with pytest.raises(ConfigurationError, match="Config file not found"):
        load_config(str(nonexistent_path))


def test_load_config_with_valid_yaml(tmp_path: Path) -> None:
    """Test loading valid YAML config file."""
    config_file = tmp_path / "test-config.yaml"
    config_file.write_text("""
logging:
  level: DEBUG

nlp:
  model_name: fr_core_news_md

pseudonym:
  theme: star_wars

database:
  path: /tmp/test.db

validation:
  enabled: false
""")

    config = load_config(str(config_file))

    assert config.log_level == "DEBUG"
    assert config.model_name == "fr_core_news_md"
    assert config.theme == "star_wars"
    assert config.db_path == "/tmp/test.db"
    assert config.validation_enabled is False


def test_load_config_partial_yaml(tmp_path: Path) -> None:
    """Test loading config file with only some sections (rest use defaults)."""
    config_file = tmp_path / "partial-config.yaml"
    config_file.write_text("""
logging:
  level: WARNING

pseudonym:
  theme: lotr
""")

    config = load_config(str(config_file))

    # Specified values
    assert config.log_level == "WARNING"
    assert config.theme == "lotr"

    # Default values for unspecified sections
    assert config.model_name == "fr_core_news_lg"
    assert config.db_path == "./gdpr-pseudo.db"
    assert config.validation_enabled is True


def test_load_config_invalid_yaml_syntax(tmp_path: Path) -> None:
    """Test error handling for invalid YAML syntax."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("""
logging:
  level: DEBUG
    broken indentation
""")

    with pytest.raises(ConfigurationError, match="Invalid YAML syntax"):
        load_config(str(config_file))


def test_load_config_invalid_log_level(tmp_path: Path) -> None:
    """Test validation of log level values."""
    config_file = tmp_path / "invalid-log-level.yaml"
    config_file.write_text("""
logging:
  level: INVALID
""")

    with pytest.raises(ConfigurationError, match="Invalid log level"):
        load_config(str(config_file))


def test_load_config_invalid_theme(tmp_path: Path) -> None:
    """Test validation of theme values."""
    config_file = tmp_path / "invalid-theme.yaml"
    config_file.write_text("""
pseudonym:
  theme: invalid_theme
""")

    with pytest.raises(ConfigurationError, match="Invalid theme"):
        load_config(str(config_file))


def test_load_config_invalid_section_type(tmp_path: Path) -> None:
    """Test error handling when section is not a dictionary."""
    config_file = tmp_path / "invalid-section.yaml"
    config_file.write_text("""
logging: not_a_dict
""")

    with pytest.raises(ConfigurationError, match="must be a dictionary"):
        load_config(str(config_file))


def test_load_config_empty_file(tmp_path: Path) -> None:
    """Test loading empty YAML file returns defaults."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("")

    config = load_config(str(config_file))

    # Should use all default values
    assert config.log_level == "INFO"
    assert config.model_name == "fr_core_news_lg"
    assert config.theme == "neutral"
    assert config.db_path == "./gdpr-pseudo.db"
    assert config.validation_enabled is True


def test_load_config_not_yaml_dict(tmp_path: Path) -> None:
    """Test error when YAML file doesn't contain a dictionary at root."""
    config_file = tmp_path / "list.yaml"
    config_file.write_text("""
- item1
- item2
""")

    with pytest.raises(ConfigurationError, match="must contain a YAML dictionary"):
        load_config(str(config_file))


def test_load_config_search_order_defaults() -> None:
    """Test default config when no config file exists in search paths."""
    # Load without specifying path (uses search order)
    # Since no config file exists in project root or home, should use defaults
    config = load_config()

    assert config.log_level == "INFO"
    assert config.model_name == "fr_core_news_lg"
    assert config.theme == "neutral"
    assert config.db_path == "./gdpr-pseudo.db"
    assert config.validation_enabled is True


def test_load_config_invalid_validation_enabled_type(tmp_path: Path) -> None:
    """Test error when validation.enabled is not a boolean."""
    config_file = tmp_path / "invalid-validation.yaml"
    config_file.write_text("""
validation:
  enabled: "yes"
""")

    with pytest.raises(ConfigurationError, match="must be true or false"):
        load_config(str(config_file))


def test_load_config_permission_denied(tmp_path: Path) -> None:
    """Test error handling when config file cannot be read."""
    config_file = tmp_path / "unreadable.yaml"
    config_file.write_text("logging:\n  level: DEBUG\n")

    # Make file unreadable (Unix-like systems only)
    import os
    import stat

    if os.name != "nt":  # Skip on Windows
        config_file.chmod(stat.S_IWUSR)  # Write-only permission

        with pytest.raises(ConfigurationError, match="Cannot read config file"):
            load_config(str(config_file))

        # Restore permissions for cleanup
        config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
