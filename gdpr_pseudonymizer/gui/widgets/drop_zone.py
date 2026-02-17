"""Drag-and-drop file target widget.

Dashed border, file icon, drag-enter visual feedback,
click-to-browse, file type validation.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class DropZone(QFrame):
    """Drag-and-drop zone for file selection."""

    file_selected = Signal(str)
    folder_selected = Signal(str)
    multi_file_dropped = Signal()
    invalid_drop = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        # File icon
        self._icon_label = QLabel("\U0001f4c4")  # document emoji
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(self._icon_label)

        # Main text
        self._text_label = QLabel("Glissez un fichier ici\nou cliquez pour ouvrir")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(self._text_label)

        # Format badges
        badge_layout = QHBoxLayout()
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_layout.setSpacing(8)
        for ext in [".txt", ".md", ".pdf", ".docx"]:
            badge = QLabel(ext)
            badge.setStyleSheet(
                "background-color: #E3F2FD; color: #1565C0; "
                "border-radius: 4px; padding: 2px 8px; font-size: 11px;"
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_layout.addWidget(badge)
        layout.addLayout(badge_layout)

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = Path(urls[0].toLocalFile())
                if path.is_dir() or path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    self.setProperty("dragActive", True)
                    self.setProperty("dragInvalid", False)
                    event.acceptProposedAction()
                else:
                    self.setProperty("dragActive", False)
                    self.setProperty("dragInvalid", True)
                    event.acceptProposedAction()
                self.style().unpolish(self)
                self.style().polish(self)
                self.update()
                return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self.setProperty("dragActive", False)
        self.setProperty("dragInvalid", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("dragActive", False)
        self.setProperty("dragInvalid", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        urls = event.mimeData().urls()
        if not urls:
            return

        path = Path(urls[0].toLocalFile())

        if path.is_dir():
            self.folder_selected.emit(str(path))
            return

        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            self.file_selected.emit(str(path))
            if len(urls) > 1:
                self.multi_file_dropped.emit()
            return

        self.invalid_drop.emit()

    # ------------------------------------------------------------------
    # Click to browse
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()

    def _open_file_dialog(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un document",
            "",
            "Documents (*.txt *.md *.pdf *.docx);;Tous (*)",
        )
        if filepath:
            self.file_selected.emit(filepath)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_supported_file(filepath: str) -> bool:
        """Check if a file has a supported extension."""
        return Path(filepath).suffix.lower() in SUPPORTED_EXTENSIONS

    @staticmethod
    def supported_extensions() -> set[str]:
        """Return set of supported file extensions."""
        return set(SUPPORTED_EXTENSIONS)
