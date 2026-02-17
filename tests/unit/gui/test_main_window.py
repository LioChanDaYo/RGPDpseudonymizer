"""Tests for MainWindow: creation, menu bar, sizing, navigation."""

from __future__ import annotations

from gdpr_pseudonymizer.gui.main_window import MainWindow


class TestMainWindowCreation:
    """Window creation and basic properties."""

    def test_window_title(self, main_window: MainWindow) -> None:
        assert main_window.windowTitle() == "GDPR Pseudonymizer"

    def test_minimum_size(self, main_window: MainWindow) -> None:
        assert main_window.minimumWidth() == 900
        assert main_window.minimumHeight() == 600

    def test_default_size(self, main_window: MainWindow) -> None:
        assert main_window.width() == 1200
        assert main_window.height() == 800


class TestMenuBar:
    """Menu bar structure and items."""

    def test_menu_bar_exists(self, main_window: MainWindow) -> None:
        menu_bar = main_window.menuBar()
        assert menu_bar is not None

    def test_file_menu_exists(self, main_window: MainWindow) -> None:
        actions = main_window.menuBar().actions()
        menu_titles = [a.text() for a in actions]
        assert "Fichier" in menu_titles

    def test_view_menu_exists(self, main_window: MainWindow) -> None:
        actions = main_window.menuBar().actions()
        menu_titles = [a.text() for a in actions]
        assert "Affichage" in menu_titles

    def test_tools_menu_exists(self, main_window: MainWindow) -> None:
        actions = main_window.menuBar().actions()
        menu_titles = [a.text() for a in actions]
        assert "Outils" in menu_titles

    def test_help_menu_exists(self, main_window: MainWindow) -> None:
        actions = main_window.menuBar().actions()
        menu_titles = [a.text() for a in actions]
        assert "Aide" in menu_titles


class TestNavigation:
    """Screen navigation via QStackedWidget."""

    def test_navigate_to_home(self, main_window: MainWindow) -> None:
        main_window.navigate_to("home")
        assert main_window.current_screen_name() == "home"

    def test_navigate_to_settings(self, main_window: MainWindow) -> None:
        main_window.navigate_to("settings")
        assert main_window.current_screen_name() == "settings"

    def test_navigate_to_unknown(self, main_window: MainWindow) -> None:
        """Navigating to unknown screen is a no-op."""
        main_window.navigate_to("home")
        main_window.navigate_to("nonexistent")
        assert main_window.current_screen_name() == "home"

    def test_navigate_to_processing(self, main_window: MainWindow) -> None:
        main_window.navigate_to("processing")
        assert main_window.current_screen_name() == "processing"


class TestStatusBar:
    """Status bar content."""

    def test_status_bar_default_message(self, main_window: MainWindow) -> None:
        assert main_window.statusBar().currentMessage() == "Prêt"

    def test_theme_toggle_button_exists(self, main_window: MainWindow) -> None:
        btn = main_window.findChild(
            type(main_window._theme_toggle_btn), "themeToggleButton"
        )
        assert btn is not None


class TestStepIndicator:
    """Step indicator in main window."""

    def test_step_indicator_exists(self, main_window: MainWindow) -> None:
        assert main_window.step_indicator is not None

    def test_step_indicator_default_step(self, main_window: MainWindow) -> None:
        assert main_window.step_indicator.current_step() == 0
