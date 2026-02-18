"""Shared fixtures for GUI unit tests.

Uses pytest-qt's qapp fixture for QApplication lifecycle.
"""

from __future__ import annotations

from typing import Any

import pytest

from gdpr_pseudonymizer.gui.config import _DEFAULT_CONFIG
from gdpr_pseudonymizer.gui.main_window import MainWindow


@pytest.fixture()
def gui_config(tmp_path: object) -> dict[str, Any]:
    """Fresh config dict for each test."""
    config = dict(_DEFAULT_CONFIG)
    config["recent_files"] = []
    return config


@pytest.fixture()
def main_window(qtbot, gui_config: dict[str, Any]) -> MainWindow:  # type: ignore[no-untyped-def]
    """Create a MainWindow with test config."""
    window = MainWindow(config=gui_config)
    qtbot.addWidget(window)

    # Register screens
    from gdpr_pseudonymizer.gui.screens.home import HomeScreen
    from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen
    from gdpr_pseudonymizer.gui.screens.results import ResultsScreen
    from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen
    from gdpr_pseudonymizer.gui.screens.stub import StubScreen

    window.add_screen("home", HomeScreen(window))
    window.add_screen("settings", SettingsScreen(window))
    window.add_screen("processing", ProcessingScreen(window))
    window.add_screen("results", ResultsScreen(window))
    window.add_screen("batch", StubScreen("Traitement par lot", window))
    window.navigate_to("home")
    return window
