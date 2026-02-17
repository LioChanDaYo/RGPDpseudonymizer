"""Stub placeholder screen for features not yet implemented."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class StubScreen(QWidget):
    """Placeholder screen showing 'En cours de développement'."""

    def __init__(self, screen_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._screen_name = screen_name
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(screen_name)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        message = QLabel("En cours de développement")
        message.setObjectName("secondaryLabel")
        message.setStyleSheet("font-size: 14px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

        back_btn = QPushButton("← Retour à l'accueil")
        back_btn.setObjectName("secondaryButton")
        back_btn.clicked.connect(self._go_home)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _go_home(self) -> None:
        """Navigate back to home screen."""
        from gdpr_pseudonymizer.gui.main_window import MainWindow

        parent = self.parent()
        while parent is not None:
            if isinstance(parent, MainWindow):
                parent.navigate_to("home")
                return
            parent = parent.parent()

    @property
    def screen_name(self) -> str:
        """Return the screen name."""
        return self._screen_name
