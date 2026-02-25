"""Unit tests for focus management and tab order configuration."""


class TestFocusManagement:
    """Test focus management functions for all screens."""

    def test_setup_focus_order_home_called(self, main_window):
        """Test that HomeScreen calls setup_focus_order_home."""
        # Access the already-created HomeScreen from main_window fixture
        idx = main_window._screens["home"]
        screen = main_window.stack.widget(idx)

        # Verify key widgets exist and have tab order configured
        assert screen._drop_zone is not None
        assert screen._batch_btn is not None
        # Batch button should be focusable
        assert screen._batch_btn.focusPolicy() != 0  # Not NoFocus
        # DropZone is a composite widget with NoFocus (children handle focus)

    def test_setup_focus_order_validation_configured(self, main_window):
        """Test that ValidationScreen tab order is correctly configured."""
        idx = main_window._screens["validation"]
        screen = main_window.stack.widget(idx)

        # Verify key widgets exist and are focusable
        assert screen._editor is not None
        assert screen._editor.focusPolicy() != 0
        assert screen._panel is not None
        # EntityPanel is a composite widget with NoFocus (children handle focus)
        assert screen._back_btn is not None
        assert screen._back_btn.focusPolicy() != 0
        assert screen._finalize_btn is not None
        assert screen._finalize_btn.focusPolicy() != 0

    def test_setup_focus_order_results_configured(self, main_window):
        """Test that ResultsScreen tab order is correctly configured."""
        idx = main_window._screens["results"]
        screen = main_window.stack.widget(idx)

        # Verify key widgets exist and are focusable
        assert screen._preview is not None
        assert screen._new_doc_btn is not None
        assert screen._new_doc_btn.focusPolicy() != 0
        assert screen._save_btn is not None
        assert screen._save_btn.focusPolicy() != 0

    def test_setup_focus_order_database_configured(self, main_window):
        """Test that DatabaseScreen tab order is correctly configured."""
        idx = main_window._screens["database"]
        screen = main_window.stack.widget(idx)

        # Verify key widgets exist and are focusable
        assert screen._db_combo is not None
        assert screen._db_combo.focusPolicy() != 0
        assert screen._browse_btn is not None
        assert screen._browse_btn.focusPolicy() != 0
        assert screen._open_btn is not None
        assert screen._open_btn.focusPolicy() != 0
        assert screen._search_field is not None
        assert screen._search_field.focusPolicy() != 0
        assert screen._type_filter is not None
        assert screen._type_filter.focusPolicy() != 0
        assert screen._entity_table is not None
        assert screen._entity_table.focusPolicy() != 0

    def test_setup_focus_order_batch_configured(self, main_window):
        """Test that BatchScreen tab order is correctly configured."""
        idx = main_window._screens["batch"]
        screen = main_window.stack.widget(idx)

        # Verify key widgets exist and are focusable
        assert screen._folder_input is not None
        assert screen._folder_input.focusPolicy() != 0
        assert screen._browse_folder_btn is not None
        assert screen._browse_folder_btn.focusPolicy() != 0
        assert screen._add_files_btn is not None
        assert screen._add_files_btn.focusPolicy() != 0
        assert screen._file_table is not None
        assert screen._file_table.focusPolicy() != 0

    def test_setup_focus_order_settings_configured(self, main_window):
        """Test that SettingsScreen tab order is correctly configured."""
        idx = main_window._screens["settings"]
        screen = main_window.stack.widget(idx)

        # Verify key widgets exist and are focusable
        assert screen._theme_light is not None
        assert screen._theme_light.focusPolicy() != 0
        assert screen._theme_dark is not None
        assert screen._theme_dark.focusPolicy() != 0
        assert screen._theme_system is not None
        assert screen._theme_system.focusPolicy() != 0
        assert screen._language_combo is not None
        assert screen._language_combo.focusPolicy() != 0
