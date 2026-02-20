"""Tests for settings persistence: write to YAML, read back, round-trip."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from gdpr_pseudonymizer.gui.config import (
    _DEFAULT_CONFIG,
    add_recent_database,
    add_recent_file,
    load_gui_config,
    save_gui_config,
)


class TestSettingsPersistence:
    """Config round-trip tests."""

    def test_save_and_load_theme(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        config = dict(_DEFAULT_CONFIG)
        config["theme"] = "dark"
        save_gui_config(config)

        loaded = load_gui_config()
        assert loaded["theme"] == "dark"

    def test_save_and_load_language(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        config = dict(_DEFAULT_CONFIG)
        config["language"] = "en"
        save_gui_config(config)

        loaded = load_gui_config()
        assert loaded["language"] == "en"

    def test_preserves_existing_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        # Write an existing key not in GUI config
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({"custom_key": "value"}, f)

        config = dict(_DEFAULT_CONFIG)
        config["theme"] = "dark"
        save_gui_config(config)

        with open(config_file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        assert raw["custom_key"] == "value"
        assert raw["theme"] == "dark"

    def test_defaults_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )
        loaded = load_gui_config()
        assert loaded["theme"] == "system"
        assert loaded["language"] == "fr"


class TestRecentFiles:
    """Recent files management."""

    def test_add_recent_file(self) -> None:
        config: dict[str, Any] = {"recent_files": []}
        add_recent_file("/path/to/file.txt", config)
        assert config["recent_files"] == ["/path/to/file.txt"]

    def test_add_moves_to_front(self) -> None:
        config: dict[str, Any] = {"recent_files": ["/a.txt", "/b.txt"]}
        add_recent_file("/b.txt", config)
        assert config["recent_files"][0] == "/b.txt"
        assert len(config["recent_files"]) == 2

    def test_max_ten_recent(self) -> None:
        config: dict[str, Any] = {"recent_files": [f"/{i}.txt" for i in range(10)]}
        add_recent_file("/new.txt", config)
        assert len(config["recent_files"]) == 10
        assert config["recent_files"][0] == "/new.txt"


class TestNewConfigKeys:
    """Tests for new config keys added in Story 6.5."""

    def test_default_theme_roundtrip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        config = dict(_DEFAULT_CONFIG)
        config["default_theme"] = "star_wars"
        save_gui_config(config)

        loaded = load_gui_config()
        assert loaded["default_theme"] == "star_wars"

    def test_batch_workers_roundtrip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        config = dict(_DEFAULT_CONFIG)
        config["batch_workers"] = 8
        save_gui_config(config)

        loaded = load_gui_config()
        assert loaded["batch_workers"] == 8

    def test_recent_databases_roundtrip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        config = dict(_DEFAULT_CONFIG)
        config["recent_databases"] = ["/path/to/db.db"]
        save_gui_config(config)

        loaded = load_gui_config()
        assert loaded["recent_databases"] == ["/path/to/db.db"]

    def test_defaults_include_new_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / ".gdpr-pseudo.yaml"
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config._config_path", lambda: config_file
        )

        loaded = load_gui_config()
        assert loaded["default_theme"] == "neutral"
        assert loaded["batch_workers"] == 4
        assert loaded["recent_databases"] == []


class TestRecentDatabases:
    """Recent databases management."""

    def test_add_recent_database(self) -> None:
        config: dict[str, Any] = {"recent_databases": []}
        add_recent_database("/path/to/db.db", config)
        assert config["recent_databases"] == ["/path/to/db.db"]

    def test_add_moves_to_front(self) -> None:
        config: dict[str, Any] = {"recent_databases": ["/a.db", "/b.db"]}
        add_recent_database("/b.db", config)
        assert config["recent_databases"][0] == "/b.db"
        assert len(config["recent_databases"]) == 2

    def test_max_five_recent(self) -> None:
        config: dict[str, Any] = {"recent_databases": [f"/{i}.db" for i in range(5)]}
        add_recent_database("/new.db", config)
        assert len(config["recent_databases"]) == 5
        assert config["recent_databases"][0] == "/new.db"
