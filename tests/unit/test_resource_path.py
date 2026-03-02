"""Tests for resource_path() helper — frozen vs non-frozen contexts.

Validates that the resource path resolution in standalone_entry works
correctly for both PyInstaller frozen bundles and normal Python execution.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def standalone_entry():
    """Import standalone_entry module from scripts/."""
    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import importlib

    mod = importlib.import_module("standalone_entry")
    yield mod

    if scripts_dir in sys.path:
        sys.path.remove(scripts_dir)


class TestResourcePathNonFrozen:
    """Test resource_path() in normal (non-frozen) Python execution."""

    def test_returns_absolute_path(self, standalone_entry):
        """Returned path is always absolute."""
        result = standalone_entry.resource_path("some/file.txt")
        assert result.is_absolute()

    def test_resolves_relative_to_project_root(self, standalone_entry):
        """Path is relative to the project root."""
        project_root = Path(standalone_entry.__file__).resolve().parent.parent
        result = standalone_entry.resource_path("gdpr_pseudonymizer/resources")
        assert result == project_root / "gdpr_pseudonymizer" / "resources"

    def test_existing_resource_found(self, standalone_entry):
        """An actual project resource file is correctly resolved."""
        result = standalone_entry.resource_path(
            "gdpr_pseudonymizer/resources/french_names.json"
        )
        assert result.exists(), f"Expected resource not found: {result}"


class TestResourcePathFrozen:
    """Test resource_path() in simulated PyInstaller frozen context."""

    def test_resolves_relative_to_meipass(self, standalone_entry, tmp_path):
        """Frozen: path is relative to sys._MEIPASS."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                result = standalone_entry.resource_path("some/resource.json")
                assert result == tmp_path / "some" / "resource.json"

    def test_frozen_path_is_absolute(self, standalone_entry, tmp_path):
        """Frozen: returned path is absolute."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                result = standalone_entry.resource_path("data/file.txt")
                assert result.is_absolute()

    def test_frozen_resource_directory(self, standalone_entry, tmp_path):
        """Frozen: resource directories resolve correctly."""
        (tmp_path / "gdpr_pseudonymizer" / "resources").mkdir(parents=True)
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                result = standalone_entry.resource_path("gdpr_pseudonymizer/resources")
                assert result.exists()
                assert result.is_dir()
