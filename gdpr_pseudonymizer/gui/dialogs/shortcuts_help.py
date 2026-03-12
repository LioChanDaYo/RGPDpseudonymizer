"""Keyboard shortcuts help dialog showing all available shortcuts."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.accessibility.shortcuts import (
    NAVIGATION_MODE_DESCRIPTION,
    get_all_shortcuts,
)


class ShortcutsHelpDialog(QDialog):
    """Dialog showing keyboard shortcuts organized by screen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Raccourcis clavier"))
        self.setMinimumSize(700, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel(self.tr("Raccourcis clavier"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "Utilisez ces raccourcis clavier pour naviguer "
                "rapidement dans l'application."
            )
        )
        desc.setWordWrap(True)
        desc.setObjectName("secondaryLabel")
        layout.addWidget(desc)

        # Scrollable shortcuts table
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.viewport().setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Build shortcuts tables by screen
        shortcuts_by_screen = get_all_shortcuts()

        for screen_name, shortcuts in shortcuts_by_screen.items():
            if not shortcuts:
                continue

            # Screen section header
            section_label = QLabel(self.tr(screen_name))
            section_font = QFont()
            section_font.setPointSize(11)
            section_font.setBold(True)
            section_label.setFont(section_font)
            content_layout.addWidget(section_label)

            # Navigation Mode: add explanatory text (AC3)
            if screen_name == "Navigation Mode":
                nav_desc = QLabel(self.tr(NAVIGATION_MODE_DESCRIPTION))
                nav_desc.setWordWrap(True)
                nav_desc.setObjectName("secondaryLabel")
                nav_desc_font = QFont()
                nav_desc_font.setItalic(True)
                nav_desc.setFont(nav_desc_font)
                content_layout.addWidget(nav_desc)

            # Shortcuts table
            table = QTableWidget(len(shortcuts), 2)
            table.setHorizontalHeaderLabels([self.tr("Raccourci"), self.tr("Action")])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            table.setMaximumHeight(len(shortcuts) * 35 + 35)

            for row, shortcut in enumerate(shortcuts):
                # Key column
                key_item = QTableWidgetItem(shortcut.key)
                key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                key_item.setFont(key_item.font())
                f = key_item.font()
                f.setFamily("Consolas")
                f.setBold(True)
                key_item.setFont(f)
                table.setItem(row, 0, key_item)

                # Action column
                action_item = QTableWidgetItem(self.tr(shortcut.action))
                action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 1, action_item)

            content_layout.addWidget(table)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton(self.tr("Fermer"))
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
