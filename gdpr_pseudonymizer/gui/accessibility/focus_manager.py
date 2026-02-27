"""Focus management and tab order configuration for all screens.

Provides functions to set up logical keyboard navigation flow for each screen.
Each function accepts a screen instance and configures tab order using
Qt's setTabOrder() method.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
    from gdpr_pseudonymizer.gui.screens.database import DatabaseScreen
    from gdpr_pseudonymizer.gui.screens.home import HomeScreen
    from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen
    from gdpr_pseudonymizer.gui.screens.results import ResultsScreen
    from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen
    from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen


def setup_focus_order_home(screen: HomeScreen) -> None:
    """Configure tab order for Home screen.

    Order: DropZone -> Batch button -> Recent files (if any)
    """
    from PySide6.QtWidgets import QWidget

    # Primary navigation widgets
    QWidget.setTabOrder(screen._drop_zone, screen._batch_btn)

    # Note: Recent files are dynamically created, tab order will follow
    # widget creation order naturally


def setup_focus_order_processing(screen: ProcessingScreen) -> None:
    """Configure tab order for Processing screen.

    Order: Cancel button -> Validate button -> Continue buttons (when visible)
    """
    from PySide6.QtWidgets import QWidget

    # Processing screen has limited interactivity during processing
    # Tab order: cancel_btn -> validation_btn -> continue_btn
    if hasattr(screen, "_cancel_btn"):
        if hasattr(screen, "_validation_btn"):
            QWidget.setTabOrder(screen._cancel_btn, screen._validation_btn)
            if hasattr(screen, "_continue_btn"):
                QWidget.setTabOrder(screen._validation_btn, screen._continue_btn)
        elif hasattr(screen, "_continue_btn"):
            QWidget.setTabOrder(screen._cancel_btn, screen._continue_btn)


def setup_focus_order_validation(screen: ValidationScreen) -> None:
    """Configure tab order for Validation screen.

    Single mode: EntityEditor -> EntityPanel -> Back button -> Finalize button
    Batch mode: Prev -> Next -> Cancel lot -> EntityEditor -> EntityPanel -> Finalize
    """
    from PySide6.QtWidgets import QWidget

    if screen._batch_mode:
        # Batch mode focus order includes navigation buttons
        QWidget.setTabOrder(screen._prev_btn, screen._next_btn)
        QWidget.setTabOrder(screen._next_btn, screen._batch_cancel_btn)
        QWidget.setTabOrder(screen._batch_cancel_btn, screen._editor)
        QWidget.setTabOrder(screen._editor, screen._panel)
        QWidget.setTabOrder(screen._panel, screen._finalize_btn)
    else:
        # Primary workflow order
        QWidget.setTabOrder(screen._editor, screen._panel)
        QWidget.setTabOrder(screen._panel, screen._back_btn)
        QWidget.setTabOrder(screen._back_btn, screen._finalize_btn)


def setup_focus_order_results(screen: ResultsScreen) -> None:
    """Configure tab order for Results screen.

    Order: Preview (read-only) -> New Document button -> Save button -> Database button
    """
    from PySide6.QtWidgets import QWidget

    # Results screen action flow
    if hasattr(screen, "_preview"):
        first: QWidget = screen._preview
        if hasattr(screen, "_new_doc_btn"):
            QWidget.setTabOrder(first, screen._new_doc_btn)
            first = screen._new_doc_btn
        if hasattr(screen, "_save_btn"):
            QWidget.setTabOrder(first, screen._save_btn)
            first = screen._save_btn
        if hasattr(screen, "_db_btn"):
            QWidget.setTabOrder(first, screen._db_btn)


def setup_focus_order_batch(screen: BatchScreen) -> None:
    """Configure tab order for Batch screen.

    Handles three phases (selection, processing, summary) with different tab orders.
    Only configures the selection phase initially; processing/summary phases
    are configured when visible.
    """
    from PySide6.QtWidgets import QWidget

    # Phase 0: Selection
    # Folder input -> Browse -> Add files -> File table -> Validate checkbox -> Start
    if hasattr(screen, "_folder_input"):
        QWidget.setTabOrder(screen._folder_input, screen._browse_folder_btn)
        QWidget.setTabOrder(screen._browse_folder_btn, screen._add_files_btn)
        last: QWidget = screen._add_files_btn
        if hasattr(screen, "_file_table"):
            QWidget.setTabOrder(last, screen._file_table)
            last = screen._file_table
        if hasattr(screen, "_validate_checkbox"):
            QWidget.setTabOrder(last, screen._validate_checkbox)
            last = screen._validate_checkbox
        if hasattr(screen, "_start_btn"):
            QWidget.setTabOrder(last, screen._start_btn)

    # Phase 1: Processing (pause/cancel buttons)
    # Phase 2: Summary (export/new batch buttons)
    # These are configured when phases become visible


def setup_focus_order_database(screen: DatabaseScreen) -> None:
    """Configure tab order for Database screen.

    Order: DB combo -> Browse button -> Open button -> Search field ->
           Type filter -> Entity table -> Delete button -> Export button
    """
    from PySide6.QtWidgets import QWidget

    # Database selection flow
    QWidget.setTabOrder(screen._db_combo, screen._browse_btn)
    QWidget.setTabOrder(screen._browse_btn, screen._open_btn)

    # Search/filter flow
    QWidget.setTabOrder(screen._open_btn, screen._search_field)
    QWidget.setTabOrder(screen._search_field, screen._type_filter)

    # Table and actions
    QWidget.setTabOrder(screen._type_filter, screen._entity_table)

    # Action buttons (delete, export)
    if hasattr(screen, "_delete_btn"):
        QWidget.setTabOrder(screen._entity_table, screen._delete_btn)
        if hasattr(screen, "_export_btn"):
            QWidget.setTabOrder(screen._delete_btn, screen._export_btn)
    elif hasattr(screen, "_export_btn"):
        QWidget.setTabOrder(screen._entity_table, screen._export_btn)


def setup_focus_order_settings(screen: SettingsScreen) -> None:
    """Configure tab order for Settings screen.

    Order: Back button -> Theme radios -> Language combo -> Pseudonym settings ->
           NLP settings -> Batch settings
    """
    from PySide6.QtWidgets import QWidget

    # Header
    first: QWidget
    if hasattr(screen, "_back_btn"):
        first = screen._back_btn
    else:
        # Start with first theme radio if no back button
        first = screen._theme_light

    # Appearance section
    QWidget.setTabOrder(first, screen._theme_light)
    QWidget.setTabOrder(screen._theme_light, screen._theme_dark)
    QWidget.setTabOrder(screen._theme_dark, screen._theme_system)
    QWidget.setTabOrder(screen._theme_system, screen._language_combo)

    # Pseudonym section
    last: QWidget = screen._language_combo
    if hasattr(screen, "_library_combo"):
        QWidget.setTabOrder(last, screen._library_combo)
        last = screen._library_combo

    # NLP section
    if hasattr(screen, "_confidence_spin"):
        QWidget.setTabOrder(last, screen._confidence_spin)
        last = screen._confidence_spin

    # Batch section
    if hasattr(screen, "_batch_workers_spin"):
        QWidget.setTabOrder(last, screen._batch_workers_spin)
        last = screen._batch_workers_spin

    # Output directory
    if hasattr(screen, "_output_dir_edit"):
        QWidget.setTabOrder(last, screen._output_dir_edit)
        if hasattr(screen, "_output_dir_browse"):
            QWidget.setTabOrder(screen._output_dir_edit, screen._output_dir_browse)
