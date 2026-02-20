"""GUI configuration management.

Handles loading, saving, and accessing GUI-specific settings
persisted in .gdpr-pseudo.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG: dict[str, Any] = {
    "theme": "system",
    "language": "fr",
    "default_output_dir": "",
    "default_db_path": "",
    "default_theme": "neutral",
    "batch_validation_mode": "per_document",
    "batch_workers": 4,
    "continue_on_error": True,
    "welcome_shown": False,
    "validation_hints_shown": False,
    "recent_files": [],
    "recent_databases": [],
}

_CONFIG_FILENAME = ".gdpr-pseudo.yaml"


def _config_path() -> Path:
    """Return path to config file (project root, then home)."""
    local = Path(_CONFIG_FILENAME)
    if local.exists():
        return local
    home = Path.home() / _CONFIG_FILENAME
    return home


def load_gui_config() -> dict[str, Any]:
    """Load GUI config from YAML, merged with defaults."""
    config: dict[str, Any] = dict(_DEFAULT_CONFIG)
    path = _config_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                for key in _DEFAULT_CONFIG:
                    if key in data:
                        config[key] = data[key]
        except (yaml.YAMLError, OSError):
            pass
    return config


def save_gui_config(config: dict[str, Any]) -> None:
    """Save GUI config keys to YAML, preserving other keys."""
    path = _config_path()
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                existing = data
        except (yaml.YAMLError, OSError):
            pass

    for key in _DEFAULT_CONFIG:
        if key in config:
            existing[key] = config[key]

    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(existing, f, default_flow_style=False, allow_unicode=True)
    except OSError:
        pass


def add_recent_file(filepath: str, config: dict[str, Any]) -> None:
    """Add a file to recent files list (max 10, most recent first)."""
    recent: list[str] = config.get("recent_files", [])
    if not isinstance(recent, list):
        recent = []
    # Remove if already present
    recent = [f for f in recent if f != filepath]
    recent.insert(0, filepath)
    config["recent_files"] = recent[:10]


def add_recent_database(db_path: str, config: dict[str, Any]) -> None:
    """Add a database path to recent databases list (max 5, most recent first)."""
    recent: list[str] = config.get("recent_databases", [])
    if not isinstance(recent, list):
        recent = []
    recent = [p for p in recent if p != db_path]
    recent.insert(0, db_path)
    config["recent_databases"] = recent[:5]
