"""Home screen with drop zone and recent files list."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.config import add_recent_file, save_gui_config
from gdpr_pseudonymizer.gui.widgets.drop_zone import DropZone
from gdpr_pseudonymizer.gui.widgets.toast import Toast

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow


class HomeScreen(QWidget):
    """Welcome / home screen with file drop zone and recent files."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._config = main_window.config

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(20)

        # Title
        title = QLabel("GDPR Pseudonymizer")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "Pseudonymisation conforme au RGPD pour vos documents en français"
        )
        subtitle.setObjectName("secondaryLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Drop zone
        self._drop_zone = DropZone(self)
        self._drop_zone.file_selected.connect(self._on_file_selected)
        self._drop_zone.folder_selected.connect(self._on_folder_selected)
        self._drop_zone.multi_file_dropped.connect(self._on_multi_file_dropped)
        self._drop_zone.invalid_drop.connect(self._on_invalid_drop)
        layout.addWidget(self._drop_zone)

        # Batch processing card
        batch_card = QFrame()
        batch_card.setStyleSheet(
            "QFrame { border: 1px solid #E0E0E0; border-radius: 8px; padding: 12px; }"
        )
        batch_layout = QHBoxLayout(batch_card)
        batch_label = QLabel("Traitement par lot")
        batch_label.setStyleSheet("font-weight: bold;")
        batch_layout.addWidget(batch_label)
        batch_desc = QLabel("Traiter plusieurs documents d'un dossier")
        batch_desc.setObjectName("secondaryLabel")
        batch_layout.addWidget(batch_desc)
        batch_layout.addStretch()
        batch_btn = QPushButton("Ouvrir un dossier")
        batch_btn.setObjectName("secondaryButton")
        batch_btn.clicked.connect(lambda: self._main_window.navigate_to("batch"))
        batch_layout.addWidget(batch_btn)
        layout.addWidget(batch_card)

        # Recent files section
        recent_header = QLabel("Fichiers récents")
        recent_header.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(recent_header)

        self._recent_area = QScrollArea()
        self._recent_area.setWidgetResizable(True)
        self._recent_area.setFrameShape(QFrame.Shape.NoFrame)
        self._recent_area.viewport().setAutoFillBackground(False)
        self._recent_area.setMaximumHeight(200)

        self._recent_container = QWidget()
        self._recent_layout = QVBoxLayout(self._recent_container)
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(4)
        self._recent_area.setWidget(self._recent_container)

        layout.addWidget(self._recent_area)
        layout.addStretch()

        self._rebuild_recent_list()

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def _rebuild_recent_list(self) -> None:
        """Rebuild the recent files widget list."""
        # Clear existing
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent = self._config.get("recent_files", [])
        if not recent:
            empty = QLabel("Aucun fichier récent")
            empty.setObjectName("secondaryLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._recent_layout.addWidget(empty)
            return

        for filepath in recent:
            row = self._create_recent_row(filepath)
            self._recent_layout.addWidget(row)

    def _create_recent_row(self, filepath: str) -> QWidget:
        """Create a row widget for a recent file."""
        row = QFrame()
        row.setStyleSheet(
            "QFrame { border-radius: 4px; padding: 4px; }"
            "QFrame:hover { background-color: rgba(21, 101, 192, 0.08); }"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)

        p = Path(filepath)
        exists = p.exists()

        name_label = QLabel(p.name)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)

        path_label = QLabel(str(p.parent))
        path_label.setObjectName("secondaryLabel")
        path_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(path_label)

        layout.addStretch()

        if exists:
            # Relative timestamp
            mtime = p.stat().st_mtime
            age = _relative_time_fr(mtime)
            time_label = QLabel(age)
            time_label.setObjectName("secondaryLabel")
            time_label.setStyleSheet("font-size: 11px;")
            layout.addWidget(time_label)

            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.mousePressEvent = lambda e, fp=filepath: self._on_file_selected(fp)  # type: ignore[method-assign,misc]
        else:
            missing = QLabel("Fichier introuvable")
            missing.setStyleSheet("color: #C62828; font-size: 11px;")
            layout.addWidget(missing)

            remove_btn = QPushButton("Retirer")
            remove_btn.setObjectName("secondaryButton")
            remove_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
            remove_btn.clicked.connect(
                lambda checked=False, fp=filepath: self._remove_recent(fp)
            )
            layout.addWidget(remove_btn)

        return row

    def _remove_recent(self, filepath: str) -> None:
        """Remove a file from the recent list."""
        recent = self._config.get("recent_files", [])
        self._config["recent_files"] = [f for f in recent if f != filepath]
        save_gui_config(self._config)
        self._rebuild_recent_list()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_file_selected(self, filepath: str) -> None:
        """Handle file selection from drop zone or recent list."""
        add_recent_file(filepath, self._config)
        save_gui_config(self._config)
        self._rebuild_recent_list()

        # Check session passphrase cache
        cached = self._main_window.cached_passphrase
        file_dir = str(Path(filepath).parent)

        if cached is not None:
            db_path, passphrase = cached
            self._start_processing(filepath, db_path, passphrase)
            return

        # Show passphrase dialog
        from gdpr_pseudonymizer.gui.widgets.passphrase_dialog import PassphraseDialog

        dialog = PassphraseDialog(
            file_directory=file_dir,
            config=self._config,
            parent=self._main_window,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        result = dialog.get_result()
        if result is None:
            return

        db_path, passphrase, remember = result
        if remember:
            self._main_window.cached_passphrase = (db_path, passphrase)

        self._start_processing(filepath, db_path, passphrase)

    def _start_processing(self, filepath: str, db_path: str, passphrase: str) -> None:
        """Navigate to processing screen and start processing."""
        self._main_window.navigate_to("processing")

        # Get the processing screen and start processing
        proc_idx = self._main_window._screens.get("processing")
        if proc_idx is not None:
            widget = self._main_window.stack.widget(proc_idx)
            from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen

            if isinstance(widget, ProcessingScreen):
                widget.start_processing(filepath, db_path, passphrase)

    def _on_folder_selected(self, folder_path: str) -> None:
        """Handle folder drop — redirect to batch flow."""
        Toast.show_message(
            "Ouverture du traitement par lot...",
            self._main_window,
        )
        self._main_window.navigate_to("batch", folder_path=folder_path)

    def _on_multi_file_dropped(self) -> None:
        """Handle multi-file drop — only first file is processed."""
        Toast.show_message(
            "Un seul fichier à la fois — seul le premier sera traité.",
            self._main_window,
            duration_ms=4000,
        )

    def _on_invalid_drop(self) -> None:
        """Handle invalid file type drop."""
        Toast.show_message(
            "Format non pris en charge. " "Formats acceptés : .txt, .md, .pdf, .docx",
            self._main_window,
            duration_ms=4000,
        )

    @property
    def drop_zone(self) -> DropZone:
        """Access drop zone for testing."""
        return self._drop_zone


def _relative_time_fr(timestamp: float) -> str:
    """Convert a timestamp to a French relative time string."""
    delta = time.time() - timestamp
    if delta < 60:
        return "À l'instant"
    if delta < 3600:
        minutes = int(delta / 60)
        return f"Il y a {minutes} min"
    if delta < 86400:
        hours = int(delta / 3600)
        return f"Il y a {hours} h"
    days = int(delta / 86400)
    if days == 1:
        return "Hier"
    if days < 30:
        return f"Il y a {days} jours"
    return "Il y a plus d'un mois"
