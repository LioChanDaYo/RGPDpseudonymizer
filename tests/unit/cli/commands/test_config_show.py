"""Unit tests for config show command.

Tests cover:
- Config display output formatting
- Source tracking (project, home, default)
- Config files status display
"""

from __future__ import annotations

from pathlib import Path

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.config_show import (
    CONFIG_TEMPLATE,
    _format_value,
    _get_config_with_sources,
    _update_sources,
    config_show_command,
)


def create_test_app() -> typer.Typer:
    """Create a properly configured Typer app for testing."""
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        """Test app callback."""
        pass

    app.command(name="config")(config_show_command)
    return app


app = create_test_app()
runner = CliRunner()


class TestFormatValue:
    """Tests for _format_value helper function."""

    def test_format_none(self) -> None:
        """Test formatting None value."""
        assert _format_value(None) == "null"

    def test_format_bool_true(self) -> None:
        """Test formatting True value."""
        assert _format_value(True) == "true"

    def test_format_bool_false(self) -> None:
        """Test formatting False value."""
        assert _format_value(False) == "false"

    def test_format_string(self) -> None:
        """Test formatting string value."""
        assert _format_value("test") == "test"

    def test_format_int(self) -> None:
        """Test formatting integer value."""
        assert _format_value(42) == "42"


class TestUpdateSources:
    """Tests for _update_sources helper function."""

    def test_updates_simple_key(self) -> None:
        """Test updating sources for simple key."""
        sources: dict[str, str] = {"test.key": "default"}
        config = {"test": {"key": "value"}}

        _update_sources(sources, config, "project")

        assert sources["test.key"] == "project"

    def test_handles_nested_keys(self) -> None:
        """Test updating sources for nested keys."""
        sources: dict[str, str] = {}
        config = {"outer": {"inner": {"deep": "value"}}}

        _update_sources(sources, config, "home")

        assert sources["outer.inner.deep"] == "home"


class TestGetConfigWithSources:
    """Tests for _get_config_with_sources function."""

    def test_returns_defaults_when_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that defaults are returned when no config files exist."""
        # Empty directories with no config files
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        config_dict, sources = _get_config_with_sources()

        # Check default values
        assert config_dict["database"]["path"] == "mappings.db"
        assert config_dict["pseudonymization"]["theme"] == "neutral"
        assert config_dict["batch"]["workers"] == 4

        # Check all sources are default
        assert sources["database.path"] == "default"
        assert sources["pseudonymization.theme"] == "default"
        assert sources["batch.workers"] == "default"

    def test_tracks_home_config_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that home config values are tracked as 'home' source."""
        # Create home config
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        home_config = home_dir / ".gdpr-pseudo.yaml"
        home_config.write_text(
            """
pseudonymization:
  theme: star_wars
"""
        )

        # Empty project dir
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        config_dict, sources = _get_config_with_sources()

        assert config_dict["pseudonymization"]["theme"] == "star_wars"
        assert sources["pseudonymization.theme"] == "home"
        # Other values should still be default
        assert sources["database.path"] == "default"

    def test_tracks_project_config_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that project config values are tracked as 'project' source."""
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".gdpr-pseudo.yaml"
        project_config.write_text(
            """
batch:
  workers: 2
"""
        )

        # Empty home dir
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        config_dict, sources = _get_config_with_sources()

        assert config_dict["batch"]["workers"] == 2
        assert sources["batch.workers"] == "project"

    def test_project_overrides_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that project config overrides home config."""
        # Create home config
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        home_config = home_dir / ".gdpr-pseudo.yaml"
        home_config.write_text(
            """
pseudonymization:
  theme: star_wars
"""
        )

        # Create project config with different theme
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".gdpr-pseudo.yaml"
        project_config.write_text(
            """
pseudonymization:
  theme: lotr
"""
        )

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        config_dict, sources = _get_config_with_sources()

        # Project config should win
        assert config_dict["pseudonymization"]["theme"] == "lotr"
        assert sources["pseudonymization.theme"] == "project"


class TestConfigShowCommand:
    """Tests for config show command."""

    def test_displays_effective_configuration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that command displays effective configuration."""
        # Empty directories
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "Effective Configuration" in output
        assert "database.path" in output
        assert "pseudonymization.theme" in output
        assert "batch.workers" in output
        assert "logging.level" in output

    def test_displays_source_annotations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that command displays source annotations."""
        # Empty directories
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "[default]" in output

    def test_displays_config_files_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that command displays config files status."""
        # Empty directories
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "Config files loaded" in output
        assert "not found" in output

    def test_displays_loaded_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that loaded config files are shown as loaded."""
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".gdpr-pseudo.yaml"
        project_config.write_text(
            """
pseudonymization:
  theme: lotr
"""
        )

        # Empty home dir
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        # Should show project config with source
        assert "[project]" in output
        # Should show lotr theme from project config
        assert "lotr" in output

    def test_help_text(self) -> None:
        """Test config command help text."""
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        # Basic help should be present
        assert "Display the current effective configuration" in output


# Import pytest for MonkeyPatch type hint
import pytest  # noqa: E402


class TestConfigInit:
    """Tests for config --init functionality."""

    def test_init_creates_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --init creates a config file in current directory."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "--init"])

        assert result.exit_code == 0
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "pseudonymization:" in content
        assert "theme: neutral" in content

    def test_init_creates_valid_yaml_template(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that generated template contains all config sections."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "--init"])

        assert result.exit_code == 0
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        content = config_file.read_text()

        # Check all sections present
        assert "database:" in content
        assert "pseudonymization:" in content
        assert "batch:" in content
        assert "logging:" in content
        # Check key values
        assert "workers: 4" in content
        assert "level: INFO" in content

    def test_init_refuses_overwrite_without_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --init won't overwrite existing config without --force."""
        monkeypatch.chdir(tmp_path)

        # Create existing config
        existing_config = tmp_path / ".gdpr-pseudo.yaml"
        existing_config.write_text("existing: config\n")

        result = runner.invoke(app, ["config", "--init"])

        assert result.exit_code == 1
        output = strip_ansi(result.stdout)
        assert "already exists" in output
        assert "--force" in output
        # Original content preserved
        assert existing_config.read_text() == "existing: config\n"

    def test_init_overwrites_with_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --init --force overwrites existing config."""
        monkeypatch.chdir(tmp_path)

        # Create existing config
        existing_config = tmp_path / ".gdpr-pseudo.yaml"
        existing_config.write_text("existing: config\n")

        result = runner.invoke(app, ["config", "--init", "--force"])

        assert result.exit_code == 0
        content = existing_config.read_text()
        assert "existing: config" not in content
        assert "pseudonymization:" in content

    def test_init_displays_success_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --init displays helpful success message."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "--init"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "Created:" in output
        assert ".gdpr-pseudo.yaml" in output

    def test_init_template_has_security_note(self) -> None:
        """Test that template includes passphrase security warning."""
        assert "SECURITY NOTE" in CONFIG_TEMPLATE
        assert "Passphrase must NEVER be stored" in CONFIG_TEMPLATE

    def test_init_help_shows_flag(self) -> None:
        """Test that --init flag appears in help."""
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--init" in output
        assert "template" in output.lower()
