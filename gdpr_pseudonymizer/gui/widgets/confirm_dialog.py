"""Standardized confirmation dialogs.

Factory methods: .destructive(), .proceeding(), .informational()
Button order: Cancel left, Confirm right (French convention).
Default focus: Cancel (safe action). Escape always dismisses.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class ConfirmDialog(QDialog):
    """Confirmation dialog with factory methods for common patterns."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str,
        cancel_label: str = "Annuler",
        confirm_style: str = "",
        parent: object = None,
    ) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Message
        msg = QLabel(message)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton(cancel_label)
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._confirm_btn = QPushButton(confirm_label)
        if confirm_style:
            self._confirm_btn.setObjectName(confirm_style)
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)

        # Default focus on Cancel (safe action)
        self._cancel_btn.setFocus()

    @property
    def confirm_button(self) -> QPushButton:
        """Access confirm button for testing."""
        return self._confirm_btn

    @property
    def cancel_button(self) -> QPushButton:
        """Access cancel button for testing."""
        return self._cancel_btn

    def keyPressEvent(self, event: object) -> None:
        """Escape always dismisses."""
        from PySide6.QtGui import QKeyEvent

        if isinstance(event, QKeyEvent) and event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def destructive(
        cls,
        title: str,
        message: str,
        confirm_label: str,
        parent: object = None,
    ) -> ConfirmDialog:
        """Create a destructive action dialog (red confirm button)."""
        return cls(
            title=title,
            message=message,
            confirm_label=confirm_label,
            confirm_style="destructiveButton",
            parent=parent,
        )

    @classmethod
    def proceeding(
        cls,
        title: str,
        message: str,
        confirm_label: str,
        parent: object = None,
    ) -> ConfirmDialog:
        """Create a proceeding action dialog (accent blue confirm)."""
        return cls(
            title=title,
            message=message,
            confirm_label=confirm_label,
            parent=parent,
        )

    @classmethod
    def informational(
        cls,
        title: str,
        message: str,
        dismiss_label: str = "Fermer",
        parent: object = None,
    ) -> ConfirmDialog:
        """Create an informational dialog (grey dismiss)."""
        dlg = cls(
            title=title,
            message=message,
            confirm_label=dismiss_label,
            cancel_label="",
            parent=parent,
        )
        dlg._cancel_btn.hide()
        dlg._confirm_btn.setFocus()
        return dlg
