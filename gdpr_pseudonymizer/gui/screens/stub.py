"""Stub placeholder screen for features not yet implemented."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class StubScreen(QWidget):
    """Placeholder screen showing 'En cours de développement'."""

    def __init__(self, screen_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._screen_name = screen_name
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(screen_name)
        self._title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        self._message = QLabel()
        self._message.setObjectName("secondaryLabel")
        self._message.setStyleSheet("font-size: 14px;")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._message)

        self._back_btn = QPushButton()
        self._back_btn.setObjectName("secondaryButton")
        self._back_btn.clicked.connect(self._go_home)
        layout.addWidget(self._back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.retranslateUi()

    def retranslateUi(self) -> None:
        """Re-set all translatable UI text."""
        self._message.setText(self.tr("En cours de développement"))
        self._back_btn.setText(self.tr("\u2190 Retour à l'accueil"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

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
