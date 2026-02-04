"""Unit tests for CLI configuration loading and validation.

Tests cover:
- Config priority resolution (CLI > project > home > defaults)
- Config validation (themes, models, log levels)
- Invalid config handling
- Missing config files (graceful fallback)
- SECURITY TEST: Config with database.passphrase field is rejected
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gdpr_pseudonymizer.cli.config import (
    AppConfig,
    BatchConfig,
    ConfigValidationError,
    DatabaseConfig,
    LoggingConfig,
    PassphraseInConfigError,
    PseudonymizationConfig,
    dict_to_config,
    get_default_config,
    load_config,
    load_config_file,
    merge_config_dicts,
    validate_config_dict,
)


class TestGetDefaultConfig:
    """Tests for default configuration."""

    def test_default_config_values(self) -> None:
        """Test default config has expected values."""
        config = get_default_config()

        assert config.database.path == "mappings.db"
        assert config.pseudonymization.theme == "neutral"
        assert config.pseudonymization.model == "spacy"
        assert config.logging.level == "INFO"
        assert config.logging.file is None
        assert config.batch.workers == 4
        assert config.batch.output_dir is None


class TestValidateConfigDict:
    """Tests for configuration validation."""

    def test_valid_config_passes(self) -> None:
        """Test that valid config passes validation."""
        config_dict = {
            "database": {"path": "custom.db"},
            "pseudonymization": {"theme": "star_wars", "model": "spacy"},
            "logging": {"level": "DEBUG", "file": "app.log"},
        }
        # Should not raise
        validate_config_dict(config_dict)

    def test_empty_config_passes(self) -> None:
        """Test that empty config passes validation."""
        validate_config_dict({})

    def test_passphrase_in_config_rejected(self) -> None:
        """SECURITY TEST: Config with passphrase field is rejected."""
        config_dict = {
            "database": {"path": "mappings.db", "passphrase": "secret123456!"}
        }

        with pytest.raises(PassphraseInConfigError) as exc_info:
            validate_config_dict(config_dict, source="test_config.yaml")

        assert "forbidden for security" in str(exc_info.value)
        assert "GDPR_PSEUDO_PASSPHRASE" in str(exc_info.value)

    def test_invalid_theme_rejected(self) -> None:
        """Test that invalid theme is rejected."""
        config_dict = {"pseudonymization": {"theme": "invalid_theme"}}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_dict(config_dict)

        assert "Invalid theme" in str(exc_info.value)
        assert "invalid_theme" in str(exc_info.value)

    def test_invalid_model_rejected(self) -> None:
        """Test that invalid model is rejected."""
        config_dict = {"pseudonymization": {"model": "unknown_model"}}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_dict(config_dict)

        assert "Invalid model" in str(exc_info.value)
        assert "unknown_model" in str(exc_info.value)

    def test_invalid_log_level_rejected(self) -> None:
        """Test that invalid log level is rejected."""
        config_dict = {"logging": {"level": "TRACE"}}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_dict(config_dict)

        assert "Invalid logging level" in str(exc_info.value)
        assert "TRACE" in str(exc_info.value)

    def test_valid_themes_accepted(self) -> None:
        """Test all valid themes are accepted."""
        for theme in ["neutral", "star_wars", "lotr"]:
            config_dict = {"pseudonymization": {"theme": theme}}
            validate_config_dict(config_dict)  # Should not raise

    def test_valid_log_levels_accepted(self) -> None:
        """Test all valid log levels are accepted."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config_dict = {"logging": {"level": level}}
            validate_config_dict(config_dict)  # Should not raise

    def test_batch_workers_validation_rejects_below_1(self) -> None:
        """Test batch.workers must be at least 1."""
        config_dict = {"batch": {"workers": 0}}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_dict(config_dict)

        assert "batch.workers" in str(exc_info.value)
        assert "must be 1-8" in str(exc_info.value)

    def test_batch_workers_validation_rejects_above_8(self) -> None:
        """Test batch.workers must be at most 8."""
        config_dict = {"batch": {"workers": 10}}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_dict(config_dict)

        assert "batch.workers" in str(exc_info.value)
        assert "must be 1-8" in str(exc_info.value)

    def test_batch_workers_validation_rejects_non_integer(self) -> None:
        """Test batch.workers must be an integer."""
        config_dict = {"batch": {"workers": "four"}}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_dict(config_dict)

        assert "batch.workers" in str(exc_info.value)

    def test_batch_workers_validation_accepts_valid_range(self) -> None:
        """Test valid worker counts are accepted."""
        for workers in [1, 2, 4, 8]:
            config_dict = {"batch": {"workers": workers}}
            validate_config_dict(config_dict)  # Should not raise

    def test_batch_output_dir_accepted(self) -> None:
        """Test batch.output_dir is accepted."""
        config_dict = {"batch": {"output_dir": "./output"}}
        validate_config_dict(config_dict)  # Should not raise


class TestMergeConfigDicts:
    """Tests for configuration merging."""

    def test_simple_merge(self) -> None:
        """Test merging simple config dicts."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = merge_config_dicts(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        """Test merging nested config dicts."""
        base = {
            "database": {"path": "default.db"},
            "logging": {"level": "INFO", "file": None},
        }
        override = {
            "database": {"path": "custom.db"},
            "logging": {"file": "app.log"},
        }

        result = merge_config_dicts(base, override)

        assert result["database"]["path"] == "custom.db"
        assert result["logging"]["level"] == "INFO"  # Preserved from base
        assert result["logging"]["file"] == "app.log"  # Overridden

    def test_base_unmodified(self) -> None:
        """Test that base dict is not modified."""
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}

        merge_config_dicts(base, override)

        assert base["a"]["b"] == 1  # Original unchanged


class TestDictToConfig:
    """Tests for converting dict to AppConfig."""

    def test_full_config_conversion(self) -> None:
        """Test converting complete config dict to AppConfig."""
        config_dict = {
            "database": {"path": "custom.db"},
            "pseudonymization": {"theme": "star_wars", "model": "spacy"},
            "logging": {"level": "DEBUG", "file": "app.log"},
            "batch": {"workers": 2, "output_dir": "./output"},
        }

        config = dict_to_config(config_dict)

        assert isinstance(config, AppConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.pseudonymization, PseudonymizationConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.batch, BatchConfig)
        assert config.database.path == "custom.db"
        assert config.pseudonymization.theme == "star_wars"
        assert config.logging.level == "DEBUG"
        assert config.logging.file == "app.log"
        assert config.batch.workers == 2
        assert config.batch.output_dir == "./output"

    def test_partial_config_uses_defaults(self) -> None:
        """Test that missing fields use defaults."""
        config_dict = {"database": {"path": "custom.db"}}

        config = dict_to_config(config_dict)

        assert config.database.path == "custom.db"
        assert config.pseudonymization.theme == "neutral"  # Default
        assert config.pseudonymization.model == "spacy"  # Default
        assert config.logging.level == "INFO"  # Default
        assert config.logging.file is None  # Default
        assert config.batch.workers == 4  # Default
        assert config.batch.output_dir is None  # Default

    def test_empty_dict_uses_all_defaults(self) -> None:
        """Test that empty dict uses all defaults."""
        config = dict_to_config({})

        assert config.database.path == "mappings.db"
        assert config.pseudonymization.theme == "neutral"
        assert config.pseudonymization.model == "spacy"
        assert config.logging.level == "INFO"
        assert config.logging.file is None
        assert config.batch.workers == 4
        assert config.batch.output_dir is None


class TestLoadConfigFile:
    """Tests for loading config from file."""

    def test_load_valid_config_file(self, tmp_path: Path) -> None:
        """Test loading valid config file."""
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        config_file.write_text(
            """
database:
  path: custom.db
pseudonymization:
  theme: lotr
logging:
  level: WARNING
"""
        )

        config_dict = load_config_file(config_file)

        assert config_dict["database"]["path"] == "custom.db"
        assert config_dict["pseudonymization"]["theme"] == "lotr"
        assert config_dict["logging"]["level"] == "WARNING"

    def test_load_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Test that loading nonexistent file raises FileNotFoundError."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config_file(config_file)

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises ConfigValidationError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("{ invalid yaml: [")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config_file(config_file)

        assert "Invalid YAML" in str(exc_info.value)

    def test_load_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        """Test that empty config file returns empty dict."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config_dict = load_config_file(config_file)

        assert config_dict == {}

    def test_passphrase_in_file_rejected(self, tmp_path: Path) -> None:
        """SECURITY TEST: Config file with passphrase is rejected."""
        config_file = tmp_path / "insecure.yaml"
        config_file.write_text(
            """
database:
  path: mappings.db
  passphrase: my_secret_passphrase_123
"""
        )

        with pytest.raises(PassphraseInConfigError) as exc_info:
            load_config_file(config_file)

        assert "forbidden for security" in str(exc_info.value)


class TestLoadConfig:
    """Tests for full config loading with priority resolution."""

    def test_load_defaults_when_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that defaults are used when no config files exist."""
        # Change to temp directory with no config files
        monkeypatch.chdir(tmp_path)

        # Mock home directory to temp path (no config there either)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        config = load_config()

        assert config.database.path == "mappings.db"
        assert config.pseudonymization.theme == "neutral"

    def test_project_config_overrides_home_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that project config overrides home config."""
        # Create home config
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        home_config = home_dir / ".gdpr-pseudo.yaml"
        home_config.write_text(
            """
database:
  path: home.db
pseudonymization:
  theme: star_wars
"""
        )

        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".gdpr-pseudo.yaml"
        project_config.write_text(
            """
database:
  path: project.db
"""
        )

        # Mock home and cwd
        monkeypatch.setattr(Path, "home", lambda: home_dir)
        monkeypatch.chdir(project_dir)

        config = load_config()

        # Project config overrides database path
        assert config.database.path == "project.db"
        # Home config provides theme (not in project config)
        assert config.pseudonymization.theme == "star_wars"

    def test_custom_config_path_overrides_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that custom config path overrides project and home config."""
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".gdpr-pseudo.yaml"
        project_config.write_text(
            """
database:
  path: project.db
pseudonymization:
  theme: star_wars
"""
        )

        # Create custom config
        custom_config = tmp_path / "custom.yaml"
        custom_config.write_text(
            """
database:
  path: custom.db
"""
        )

        # Mock cwd
        monkeypatch.chdir(project_dir)
        # Mock home to empty dir
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        config = load_config(config_path=custom_config)

        # Custom config overrides database path
        assert config.database.path == "custom.db"
        # Project config provides theme (not in custom config)
        assert config.pseudonymization.theme == "star_wars"

    def test_cli_overrides_have_highest_priority(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that CLI overrides have highest priority."""
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".gdpr-pseudo.yaml"
        project_config.write_text(
            """
database:
  path: project.db
pseudonymization:
  theme: star_wars
"""
        )

        # Mock cwd and home
        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        cli_overrides = {
            "database": {"path": "cli.db"},
            "pseudonymization": {"theme": "lotr"},
        }

        config = load_config(cli_overrides=cli_overrides)

        # CLI overrides all
        assert config.database.path == "cli.db"
        assert config.pseudonymization.theme == "lotr"

    def test_passphrase_in_any_config_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SECURITY TEST: Passphrase in any config source is rejected."""
        # Test CLI overrides with passphrase
        cli_overrides = {"database": {"path": "cli.db", "passphrase": "secret"}}

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        with pytest.raises(PassphraseInConfigError):
            load_config(cli_overrides=cli_overrides)

    def test_custom_config_file_not_found(self, tmp_path: Path) -> None:
        """Test that missing custom config file raises error."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(config_path=nonexistent)

    def test_graceful_fallback_for_missing_optional_configs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test graceful fallback when home/project configs don't exist."""
        # Empty directories with no config files
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # Should not raise - uses defaults
        config = load_config()

        assert config.database.path == "mappings.db"
        assert config.pseudonymization.theme == "neutral"
