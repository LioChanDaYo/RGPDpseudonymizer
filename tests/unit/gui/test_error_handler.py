"""Tests for global exception handler."""

from __future__ import annotations

import sys
from unittest.mock import patch

from gdpr_pseudonymizer.gui.error_handler import install_exception_handler
from gdpr_pseudonymizer.gui.main_window import MainWindow


class TestExceptionHandler:
    """Global exception handler tests."""

    def test_installs_excepthook(self, main_window: MainWindow) -> None:
        original = sys.excepthook
        install_exception_handler(main_window)
        assert sys.excepthook is not original
        sys.excepthook = original  # restore

    def test_handler_navigates_home(self, main_window: MainWindow) -> None:
        install_exception_handler(main_window)
        main_window.navigate_to("settings")

        with patch("PySide6.QtWidgets.QMessageBox.critical"):
            try:
                raise ValueError("test error")
            except ValueError:
                sys.excepthook(*sys.exc_info())

        assert main_window.current_screen_name() == "home"

    def test_handler_shows_dialog(self, main_window: MainWindow) -> None:
        install_exception_handler(main_window)

        with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical:
            try:
                raise RuntimeError("boom")
            except RuntimeError:
                sys.excepthook(*sys.exc_info())

            mock_critical.assert_called_once()
            args = mock_critical.call_args
            assert "Erreur inattendue" in args[0][1]
            assert "RuntimeError" in args[0][2]
