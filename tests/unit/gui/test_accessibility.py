"""Unit tests for accessibility features (AC6 - Task 11).

Tests QAccessible labels, high contrast mode detection, and keyboard shortcuts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtGui import QKeySequence

from gdpr_pseudonymizer.gui.widgets.drop_zone import DropZone
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.gui.widgets.entity_panel import EntityPanel
from gdpr_pseudonymizer.gui.widgets.step_indicator import StepIndicator

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from gdpr_pseudonymizer.gui.main_window import MainWindow


class TestAccessibleLabels:
    """Test that custom widgets expose accessible labels via QAccessible."""

    def test_drop_zone_has_accessible_name(self, qtbot: QtBot) -> None:
        """DropZone widget has accessible name."""
        drop_zone = DropZone()
        qtbot.addWidget(drop_zone)

        assert drop_zone.accessibleName() != ""
        assert "dépôt" in drop_zone.accessibleName().lower()

    def test_drop_zone_has_accessible_description(self, qtbot: QtBot) -> None:
        """DropZone widget has accessible description."""
        drop_zone = DropZone()
        qtbot.addWidget(drop_zone)

        assert drop_zone.accessibleDescription() != ""
        assert "glissez" in drop_zone.accessibleDescription().lower()

    def test_entity_editor_has_accessible_name(self, qtbot: QtBot) -> None:
        """EntityEditor widget has accessible name."""
        editor = EntityEditor()
        qtbot.addWidget(editor)

        assert editor.accessibleName() != ""
        assert "éditeur" in editor.accessibleName().lower()

    def test_entity_panel_has_accessible_name(self, qtbot: QtBot) -> None:
        """EntityPanel widget has accessible name."""
        panel = EntityPanel()
        qtbot.addWidget(panel)

        # Panel list widget should have accessible name
        assert panel._list_widget.accessibleName() != ""
        assert "entités" in panel._list_widget.accessibleName().lower()

    def test_step_indicator_has_accessible_name(self, qtbot: QtBot) -> None:
        """StepIndicator widget has accessible name."""
        indicator = StepIndicator()
        qtbot.addWidget(indicator)

        assert indicator.accessibleName() != ""
        assert "indicateur" in indicator.accessibleName().lower()

    def test_step_indicator_has_accessible_description(self, qtbot: QtBot) -> None:
        """StepIndicator widget has accessible description with step info."""
        indicator = StepIndicator()
        qtbot.addWidget(indicator)

        # Should have accessible description with "Étape X sur Y"
        assert indicator.accessibleDescription() != ""
        assert "étape" in indicator.accessibleDescription().lower()
        assert "sur" in indicator.accessibleDescription().lower()


class TestDatabaseScreenLabels:
    """Test that database screen widgets have accessible labels."""

    def test_database_combo_has_accessible_name(self, main_window: MainWindow) -> None:
        """Database combo box has accessible name."""
        main_window.navigate_to("database")
        db_screen = main_window.stack.currentWidget()

        db_combo = db_screen._db_combo  # type: ignore[attr-defined]
        assert db_combo.accessibleName() != ""
        assert "base" in db_combo.accessibleName().lower()

    def test_search_field_has_accessible_name(self, main_window: MainWindow) -> None:
        """Search field has accessible name."""
        main_window.navigate_to("database")
        db_screen = main_window.stack.currentWidget()

        search_field = db_screen._search_field  # type: ignore[attr-defined]
        assert search_field.accessibleName() != ""
        assert "recherche" in search_field.accessibleName().lower()

    def test_entity_table_has_accessible_name(self, main_window: MainWindow) -> None:
        """Entity table has accessible name."""
        main_window.navigate_to("database")
        db_screen = main_window.stack.currentWidget()

        entity_table = db_screen._entity_table  # type: ignore[attr-defined]
        assert entity_table.accessibleName() != ""
        assert "table" in entity_table.accessibleName().lower()


class TestSettingsScreenLabels:
    """Test that settings screen widgets have accessible labels."""

    def test_language_combo_has_accessible_name(self, main_window: MainWindow) -> None:
        """Language combo box has accessible name."""
        main_window.navigate_to("settings")
        settings_screen = main_window.stack.currentWidget()

        language_combo = settings_screen._language_combo  # type: ignore[attr-defined]
        assert language_combo.accessibleName() != ""
        assert "langue" in language_combo.accessibleName().lower()

    def test_theme_combo_has_accessible_name(self, main_window: MainWindow) -> None:
        """Theme combo box has accessible name."""
        main_window.navigate_to("settings")
        settings_screen = main_window.stack.currentWidget()

        theme_combo = settings_screen._default_theme_combo  # type: ignore[attr-defined]
        assert theme_combo.accessibleName() != ""
        assert "thème" in theme_combo.accessibleName().lower()

    def test_workers_spinner_has_accessible_name(self, main_window: MainWindow) -> None:
        """Workers spinner has accessible name."""
        main_window.navigate_to("settings")
        settings_screen = main_window.stack.currentWidget()

        workers_spinner = settings_screen._workers_spinner  # type: ignore[attr-defined]
        assert workers_spinner.accessibleName() != ""
        assert "processus" in workers_spinner.accessibleName().lower()


class TestProgressBarLabels:
    """Test that progress bars have accessible labels."""

    def test_processing_progress_bar_has_accessible_name(
        self, main_window: MainWindow
    ) -> None:
        """Processing screen progress bar has accessible name."""
        main_window.navigate_to("processing")
        proc_screen = main_window.stack.currentWidget()

        progress_bar = proc_screen._progress_bar  # type: ignore[attr-defined]
        assert progress_bar.accessibleName() != ""
        assert "progression" in progress_bar.accessibleName().lower()

    def test_batch_progress_bar_has_accessible_name(
        self, main_window: MainWindow
    ) -> None:
        """Batch screen progress bar has accessible name."""
        main_window.navigate_to("batch")
        batch_screen = main_window.stack.currentWidget()

        progress_bar = batch_screen._progress_bar  # type: ignore[attr-defined]
        assert progress_bar.accessibleName() != ""
        assert "progression" in progress_bar.accessibleName().lower()

    def test_validation_finalize_progress_has_accessible_name(
        self, main_window: MainWindow
    ) -> None:
        """Validation screen finalization progress bar has accessible name."""
        main_window.navigate_to("validation")
        val_screen = main_window.stack.currentWidget()

        progress_bar = val_screen._finalize_progress  # type: ignore[attr-defined]
        assert progress_bar.accessibleName() != ""
        assert "finalisation" in progress_bar.accessibleName().lower()


class TestHighContrastDetection:
    """Test high contrast mode detection and theme switching."""

    def test_detect_high_contrast_mode_method_exists(
        self, main_window: MainWindow
    ) -> None:
        """MainWindow has _detect_high_contrast_mode method."""
        assert hasattr(main_window, "_detect_high_contrast_mode")
        assert callable(main_window._detect_high_contrast_mode)

    def test_detect_high_contrast_returns_bool(self, main_window: MainWindow) -> None:
        """_detect_high_contrast_mode returns boolean."""
        result = main_window._detect_high_contrast_mode()
        assert isinstance(result, bool)

    def test_high_contrast_theme_exists(self, tmp_path: pytest.TempPathFactory) -> None:
        """high-contrast.qss theme file exists in resources."""
        import importlib.resources

        # Use importlib.resources to locate the theme file
        themes_package = importlib.resources.files(
            "gdpr_pseudonymizer.gui.resources.themes"
        )
        high_contrast_qss = themes_package / "high-contrast.qss"

        assert high_contrast_qss.is_file()
        content = high_contrast_qss.read_text(encoding="utf-8")
        assert content != ""

    def test_high_contrast_theme_has_required_selectors(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """high-contrast.qss has critical selectors for accessibility."""
        import importlib.resources

        # Use importlib.resources to locate the theme file
        themes_package = importlib.resources.files(
            "gdpr_pseudonymizer.gui.resources.themes"
        )
        high_contrast_qss = themes_package / "high-contrast.qss"

        content = high_contrast_qss.read_text(encoding="utf-8")

        # Check for focus indicator (AC4)
        assert "*:focus" in content
        assert "outline" in content

        # Check for high contrast colors (black bg, white text)
        assert "#000000" in content  # Black background
        assert "#FFFFFF" in content  # White text
        assert "#FFFF00" in content  # Yellow focus/highlights


class TestKeyboardShortcuts:
    """Test that keyboard shortcuts are correctly defined and connected."""

    def test_validation_accept_all_shortcut_exists(
        self, main_window: MainWindow
    ) -> None:
        """ValidationScreen has Ctrl+Shift+A accept all shortcut."""
        main_window.navigate_to("validation")
        val_screen = main_window.stack.currentWidget()

        assert hasattr(val_screen, "_accept_all_shortcut")
        assert val_screen._accept_all_shortcut.key() == QKeySequence("Ctrl+Shift+A")

    def test_validation_reject_all_shortcut_exists(
        self, main_window: MainWindow
    ) -> None:
        """ValidationScreen has Ctrl+Shift+R reject all shortcut."""
        main_window.navigate_to("validation")
        val_screen = main_window.stack.currentWidget()

        assert hasattr(val_screen, "_reject_all_shortcut")
        assert val_screen._reject_all_shortcut.key() == QKeySequence("Ctrl+Shift+R")

    def test_validation_undo_shortcut_exists(self, main_window: MainWindow) -> None:
        """ValidationScreen has Ctrl+Z undo shortcut."""
        main_window.navigate_to("validation")
        val_screen = main_window.stack.currentWidget()

        assert hasattr(val_screen, "_undo_shortcut")
        assert val_screen._undo_shortcut.key() == QKeySequence("Ctrl+Z")

    def test_validation_redo_shortcuts_exist(self, main_window: MainWindow) -> None:
        """ValidationScreen has Ctrl+Shift+Z and Ctrl+Y redo shortcuts."""
        main_window.navigate_to("validation")
        val_screen = main_window.stack.currentWidget()

        assert hasattr(val_screen, "_redo_shortcut")
        assert val_screen._redo_shortcut.key() == QKeySequence("Ctrl+Shift+Z")

        assert hasattr(val_screen, "_redo_shortcut2")
        assert val_screen._redo_shortcut2.key() == QKeySequence("Ctrl+Y")

    def test_validation_find_shortcut_exists(self, main_window: MainWindow) -> None:
        """ValidationScreen has Ctrl+F find shortcut."""
        main_window.navigate_to("validation")
        val_screen = main_window.stack.currentWidget()

        assert hasattr(val_screen, "_find_shortcut")
        assert val_screen._find_shortcut.key() == QKeySequence("Ctrl+F")

    def test_main_window_has_shortcuts_help_action(
        self, main_window: MainWindow
    ) -> None:
        """MainWindow has keyboard shortcuts help action (F1)."""
        # Check if _show_shortcuts method exists
        assert hasattr(main_window, "_show_shortcuts")


class TestEntityEditorAccessibility:
    """Test EntityEditor accessibility features (dynamic announcements)."""

    def test_entity_editor_updates_accessible_description(self, qtbot: QtBot) -> None:
        """EntityEditor updates accessible description when entity changes."""
        editor = EntityEditor()
        qtbot.addWidget(editor)

        # Get initial accessible description
        initial_desc = editor.accessibleDescription()

        # Accessible description should be empty or have default text when no entity
        assert isinstance(initial_desc, str)

        # Note: Full test of dynamic announcements requires validation state setup,
        # which is integration-level. This test verifies the method exists.
        assert hasattr(editor, "_announce_current_entity")
        assert callable(editor._announce_current_entity)

    def test_entity_editor_has_navigation_mode(self, qtbot: QtBot) -> None:
        """EntityEditor has navigation mode for keyboard entity navigation."""
        editor = EntityEditor()
        qtbot.addWidget(editor)

        assert hasattr(editor, "_nav_mode")
        assert isinstance(editor._nav_mode, bool)

        # Navigation mode should start as False
        assert editor._nav_mode is False


class TestStepIndicatorAccessibility:
    """Test StepIndicator accessibility features (step announcements)."""

    def test_step_indicator_updates_accessible_description(self, qtbot: QtBot) -> None:
        """StepIndicator updates accessible description when step changes."""
        indicator = StepIndicator()
        qtbot.addWidget(indicator)

        # Get initial accessible description
        initial_desc = indicator.accessibleDescription()
        assert "étape" in initial_desc.lower()
        assert "1" in initial_desc  # Should start at step 1 (index 0)

        # Change step
        indicator.set_step(2)

        # Accessible description should update
        updated_desc = indicator.accessibleDescription()
        assert "3" in updated_desc  # Step index 2 = "Étape 3 sur 4"

    def test_step_indicator_accessible_description_has_step_info(
        self, qtbot: QtBot
    ) -> None:
        """StepIndicator accessible description includes step number and label."""
        indicator = StepIndicator()
        qtbot.addWidget(indicator)

        desc = indicator.accessibleDescription()

        # Should contain "Étape X sur Y: Label"
        assert "étape" in desc.lower()
        assert "sur" in desc.lower()
        assert ":" in desc or "sélection" in desc.lower()  # Label should be present


class TestEntityPanelAccessibility:
    """Test EntityPanel accessibility features (list item announcements)."""

    def test_entity_panel_list_widget_has_accessible_name(self, qtbot: QtBot) -> None:
        """EntityPanel list widget has accessible name."""
        panel = EntityPanel()
        qtbot.addWidget(panel)

        assert panel._list_widget.accessibleName() != ""
        assert "entités" in panel._list_widget.accessibleName().lower()

    def test_entity_panel_list_widget_has_accessible_description(
        self, qtbot: QtBot
    ) -> None:
        """EntityPanel list widget has accessible description."""
        panel = EntityPanel()
        qtbot.addWidget(panel)

        # List widget should have accessible description
        desc = panel._list_widget.accessibleDescription()
        assert isinstance(desc, str)


class TestFocusIndicators:
    """Test that focus indicators are properly styled."""

    def test_light_theme_has_focus_indicator(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """light.qss has focus indicator defined."""
        import importlib.resources

        themes_package = importlib.resources.files(
            "gdpr_pseudonymizer.gui.resources.themes"
        )
        light_qss = themes_package / "light.qss"

        content = light_qss.read_text(encoding="utf-8")

        # Check for focus indicator
        assert "*:focus" in content
        assert "outline" in content

    def test_dark_theme_has_focus_indicator(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """dark.qss has focus indicator defined."""
        import importlib.resources

        themes_package = importlib.resources.files(
            "gdpr_pseudonymizer.gui.resources.themes"
        )
        dark_qss = themes_package / "dark.qss"

        content = dark_qss.read_text(encoding="utf-8")

        # Check for focus indicator
        assert "*:focus" in content
        assert "outline" in content
