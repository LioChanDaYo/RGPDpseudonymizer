"""Tests for theme loading: light/dark QSS applied without error."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestThemeLoading:
    """Verify QSS files load without errors."""

    @pytest.fixture()
    def themes_dir(self) -> Path:
        return (
            Path(__file__).parent.parent.parent.parent
            / "gdpr_pseudonymizer"
            / "gui"
            / "resources"
            / "themes"
        )

    def test_light_qss_exists(self, themes_dir: Path) -> None:
        assert (themes_dir / "light.qss").exists()

    def test_dark_qss_exists(self, themes_dir: Path) -> None:
        assert (themes_dir / "dark.qss").exists()

    def test_light_qss_loads(self, themes_dir: Path) -> None:
        content = (themes_dir / "light.qss").read_text(encoding="utf-8")
        assert len(content) > 100
        assert "QMainWindow" in content

    def test_dark_qss_loads(self, themes_dir: Path) -> None:
        content = (themes_dir / "dark.qss").read_text(encoding="utf-8")
        assert len(content) > 100
        assert "QMainWindow" in content

    def test_light_qss_applied_without_error(self, qtbot, themes_dir: Path) -> None:  # type: ignore[no-untyped-def]
        from PySide6.QtWidgets import QApplication

        content = (themes_dir / "light.qss").read_text(encoding="utf-8")
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        app.setStyleSheet(content)
        app.setStyleSheet("")  # reset

    def test_dark_qss_applied_without_error(self, qtbot, themes_dir: Path) -> None:  # type: ignore[no-untyped-def]
        from PySide6.QtWidgets import QApplication

        content = (themes_dir / "dark.qss").read_text(encoding="utf-8")
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        app.setStyleSheet(content)
        app.setStyleSheet("")  # reset
