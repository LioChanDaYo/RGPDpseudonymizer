"""Integration tests for PyInstaller build output structure.

These tests verify that the PyInstaller build produces the expected
directory layout and includes all required files.

Marked @pytest.mark.slow — runs only in CI or when explicitly requested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The PyInstaller output directory
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "dist" / "gdpr-pseudonymizer"


@pytest.mark.slow
class TestPyInstallerBuildOutput:
    """Verify the PyInstaller build output structure."""

    def test_dist_directory_exists(self):
        """Build output directory exists."""
        if not DIST_DIR.exists():
            pytest.skip(
                "PyInstaller build not found — run 'poetry run pyinstaller gdpr-pseudo-gui.spec' first"
            )
        assert DIST_DIR.is_dir()

    def test_executable_exists(self):
        """Main GUI executable is present."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")

        if sys.platform == "win32":
            exe = DIST_DIR / "gdpr-pseudonymizer.exe"
        else:
            exe = DIST_DIR / "gdpr-pseudonymizer"

        assert exe.exists(), f"GUI executable not found: {exe}"

    def test_cli_executable_exists(self):
        """Console-mode CLI executable is present."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")

        if sys.platform == "win32":
            exe = DIST_DIR / "gdpr-pseudo.exe"
        else:
            exe = DIST_DIR / "gdpr-pseudo"

        assert exe.exists(), f"CLI executable not found: {exe}"

    def test_internal_directory_exists(self):
        """_internal directory (PyInstaller 6.x) is present."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        internal = DIST_DIR / "_internal"
        assert internal.exists(), "_internal directory not found"

    def test_spacy_model_bundled(self):
        """spaCy fr_core_news_lg model is included in the bundle."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        internal = DIST_DIR / "_internal"
        model_dir = internal / "fr_core_news_lg"
        assert model_dir.exists(), f"spaCy model not found: {model_dir}"
        # Verify model has meta.json (proof it's a real model)
        assert (model_dir / "meta.json").exists(), "spaCy model meta.json missing"

    def test_resource_files_bundled(self):
        """Application resource files are included."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        resources = DIST_DIR / "_internal" / "gdpr_pseudonymizer" / "resources"
        assert resources.exists(), f"Resources dir not found: {resources}"

        expected_files = [
            "french_names.json",
            "french_gender_lookup.json",
            "french_geography.json",
            "detection_patterns.yaml",
        ]
        for filename in expected_files:
            assert (resources / filename).exists(), f"Missing resource: {filename}"

    def test_pseudonym_libraries_bundled(self):
        """Pseudonym library JSON files are included."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        pseudonyms = (
            DIST_DIR / "_internal" / "gdpr_pseudonymizer" / "resources" / "pseudonyms"
        )
        assert pseudonyms.exists(), f"Pseudonyms dir not found: {pseudonyms}"

        expected_themes = ["neutral.json", "star_wars.json", "lotr.json"]
        for theme in expected_themes:
            assert (pseudonyms / theme).exists(), f"Missing pseudonym theme: {theme}"

    def test_gui_icons_bundled(self):
        """GUI icon files are included."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        icons = (
            DIST_DIR
            / "_internal"
            / "gdpr_pseudonymizer"
            / "gui"
            / "resources"
            / "icons"
        )
        assert icons.exists(), f"Icons dir not found: {icons}"
        assert (icons / "app.ico").exists(), "app.ico missing"

    def test_gui_themes_bundled(self):
        """GUI QSS theme files are included."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        themes = (
            DIST_DIR
            / "_internal"
            / "gdpr_pseudonymizer"
            / "gui"
            / "resources"
            / "themes"
        )
        assert themes.exists(), f"Themes dir not found: {themes}"

        for qss in ["light.qss", "dark.qss", "high-contrast.qss"]:
            assert (themes / qss).exists(), f"Missing theme: {qss}"

    def test_i18n_files_bundled(self):
        """Compiled translation (.qm) files are included."""
        if not DIST_DIR.exists():
            pytest.skip("PyInstaller build not found")
        i18n = DIST_DIR / "_internal" / "gdpr_pseudonymizer" / "gui" / "i18n"
        assert i18n.exists(), f"i18n dir not found: {i18n}"

        for qm in ["en.qm", "fr.qm"]:
            assert (i18n / qm).exists(), f"Missing translation: {qm}"
