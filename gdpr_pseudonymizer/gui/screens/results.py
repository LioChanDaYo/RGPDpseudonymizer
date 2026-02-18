"""Results screen with pseudonymized document preview and save functionality.

Shows entity summary, highlighted document preview, and save/navigation buttons.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.config import add_recent_file, save_gui_config
from gdpr_pseudonymizer.gui.widgets.step_indicator import StepMode
from gdpr_pseudonymizer.gui.widgets.toast import Toast
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow
    from gdpr_pseudonymizer.gui.workers.processing_worker import GUIProcessingResult

logger = get_logger(__name__)

# Entity type colors (from UX spec)
ENTITY_COLORS: dict[str, str] = {
    "PERSON": "#1565C0",
    "LOCATION": "#2E7D32",
    "ORG": "#E65100",
}


class ResultsScreen(QWidget):
    """Screen showing pseudonymized document preview and entity summary."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._original_path = ""
        self._temp_path = ""

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # Entity summary header
        self._summary_widget = QWidget()
        summary_layout = QHBoxLayout(self._summary_widget)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        self._summary_widget.setObjectName("resultsSummary")

        self._person_label = _create_type_label("PERSON", "Personnes")
        self._location_label = _create_type_label("LOCATION", "Lieux")
        self._org_label = _create_type_label("ORG", "Organisations")

        summary_layout.addWidget(self._person_label)
        summary_layout.addWidget(self._location_label)
        summary_layout.addWidget(self._org_label)
        summary_layout.addStretch()

        self._stats_label = QLabel("")
        self._stats_label.setObjectName("secondaryLabel")
        self._stats_label.setStyleSheet("font-size: 11px;")
        summary_layout.addWidget(self._stats_label)

        layout.addWidget(self._summary_widget)

        # Document preview
        preview_label = QLabel("Aperçu du document pseudonymisé")
        preview_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(preview_label)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Consolas", 10))
        layout.addWidget(self._preview, stretch=1)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._new_doc_btn = QPushButton("Nouveau document")
        self._new_doc_btn.setObjectName("secondaryButton")
        self._new_doc_btn.clicked.connect(self._on_new_document)
        btn_layout.addWidget(self._new_doc_btn)

        self._save_btn = QPushButton("Enregistrer sous...")
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

    def show_results(
        self,
        result: GUIProcessingResult,
        content: str,
        entity_mappings: list[tuple[str, str]],
        original_path: str,
        temp_path: str,
    ) -> None:
        """Display processing results.

        Args:
            result: Processing result with counts and timing.
            content: Pseudonymized document text.
            entity_mappings: List of (pseudonym_full, entity_type) for highlighting.
            original_path: Original file path.
            temp_path: Temporary output file path.
        """
        self._original_path = original_path
        self._temp_path = temp_path

        # Update entity summary
        counts = result.entity_type_counts
        self._person_label.setText(
            f'<span style="color:{ENTITY_COLORS["PERSON"]};">\u25cf</span> '
            f'{counts.get("PERSON", 0)} Personnes'
        )
        self._location_label.setText(
            f'<span style="color:{ENTITY_COLORS["LOCATION"]};">\u25cf</span> '
            f'{counts.get("LOCATION", 0)} Lieux'
        )
        self._org_label.setText(
            f'<span style="color:{ENTITY_COLORS["ORG"]};">\u25cf</span> '
            f'{counts.get("ORG", 0)} Organisations'
        )

        self._stats_label.setText(
            f"{result.entities_new} nouvelles | "
            f"{result.entities_reused} réutilisées | "
            f"{result.processing_time_seconds:.1f}s"
        )

        # Set document content
        self._preview.setPlainText(content)

        # Apply pseudonym highlighting
        self._apply_highlighting(content, entity_mappings)

        # Step indicator
        self._main_window.step_indicator.set_mode(StepMode.SINGLE)
        self._main_window.step_indicator.set_step(3)

    def _apply_highlighting(
        self,
        content: str,
        entity_mappings: list[tuple[str, str]],
    ) -> None:
        """Highlight pseudonyms in the preview using entity-type colors."""
        if not entity_mappings:
            return

        cursor = self._preview.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for pseudonym, entity_type in entity_mappings:
            if not pseudonym:
                continue

            color = ENTITY_COLORS.get(entity_type, "#757575")
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(color).lighter(180))
            fmt.setForeground(QColor(color).darker(120))

            # Find and highlight all occurrences
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            while True:
                cursor = self._preview.document().find(pseudonym, cursor)
                if cursor.isNull():
                    break
                cursor.mergeCharFormat(fmt)

    def _on_save(self) -> None:
        """Save pseudonymized document to user-selected location."""
        stem = Path(self._original_path).stem
        default_name = f"{stem}_pseudonymise.txt"

        default_dir = self._main_window.config.get("default_output_dir", "")
        if not default_dir:
            default_dir = str(Path(self._original_path).parent)

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le document pseudonymisé",
            os.path.join(default_dir, default_name),
            "Texte (*.txt);;Tous (*)",
        )

        if not filepath:
            return

        try:
            shutil.copy2(self._temp_path, filepath)
            # Add to recent files
            add_recent_file(filepath, self._main_window.config)
            save_gui_config(self._main_window.config)

            Toast.show_message(
                "Document enregistré avec succès.",
                self._main_window,
            )
            logger.info("document_saved", output_path=filepath)
        except OSError as e:
            logger.error("document_save_failed", error=str(e))
            Toast.show_message(
                "Erreur lors de l'enregistrement.",
                self._main_window,
                duration_ms=4000,
            )

    def _on_new_document(self) -> None:
        """Return to home screen and clean up temp file."""
        # Add processed file to recent files
        add_recent_file(self._original_path, self._main_window.config)
        save_gui_config(self._main_window.config)

        # Clean up temp file
        self._cleanup_temp()

        self._main_window.step_indicator.set_step(0)
        self._main_window.navigate_to("home")

    def _cleanup_temp(self) -> None:
        """Remove temporary output file if it exists."""
        if self._temp_path:
            try:
                Path(self._temp_path).unlink(missing_ok=True)
            except OSError:
                pass
            self._temp_path = ""

    # -- Test accessors --

    @property
    def preview(self) -> QTextEdit:
        return self._preview

    @property
    def person_label(self) -> QLabel:
        return self._person_label

    @property
    def location_label(self) -> QLabel:
        return self._location_label

    @property
    def org_label(self) -> QLabel:
        return self._org_label

    @property
    def stats_label(self) -> QLabel:
        return self._stats_label

    @property
    def save_button(self) -> QPushButton:
        return self._save_btn

    @property
    def new_document_button(self) -> QPushButton:
        return self._new_doc_btn


def _create_type_label(entity_type: str, display_name: str) -> QLabel:
    """Create a styled label for an entity type count."""
    color = ENTITY_COLORS.get(entity_type, "#757575")
    label = QLabel(f'<span style="color:{color};">\u25cf</span> 0 {display_name}')
    label.setStyleSheet("font-size: 13px; padding: 0 8px;")
    return label
