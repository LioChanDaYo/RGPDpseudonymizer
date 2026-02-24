"""Passphrase dialog for mapping database authentication.

Prompts user for a database path and passphrase before processing.
Auto-detects existing .gdpr-pseudo.db files in common locations.
Supports session caching to skip repeated passphrase entry.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

# Sentinel for special combo items
_BROWSE_ITEM = "__browse__"
_CREATE_ITEM = "__create__"

DB_FILENAME = ".gdpr-pseudo.db"


class PassphraseDialog(QDialog):
    """Dialog to select a mapping database and enter passphrase.

    Returns (db_path, passphrase, remember) on accept, None on cancel.
    """

    def __init__(
        self,
        file_directory: str = "",
        config: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._file_directory = file_directory
        self._config = config or {}
        self._result: tuple[str, str, bool] | None = None

        self.setMinimumWidth(450)
        self.setModal(True)

        self._build_ui()
        self.retranslateUi()
        self._populate_db_paths()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # DB path section
        self._db_label = QLabel()
        layout.addWidget(self._db_label)

        self._db_combo = QComboBox()
        self._db_combo.activated.connect(self._on_db_combo_changed)
        layout.addWidget(self._db_combo)

        self._db_hint = QLabel("")
        self._db_hint.setObjectName("secondaryLabel")
        self._db_hint.setStyleSheet("font-size: 11px; font-style: italic;")
        layout.addWidget(self._db_hint)

        # Passphrase section
        self._pass_label = QLabel()
        layout.addWidget(self._pass_label)

        pass_row = QHBoxLayout()
        self._passphrase_edit = QLineEdit()
        self._passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pass_row.addWidget(self._passphrase_edit)

        self._visibility_btn = QPushButton("\U0001f441")  # eye
        self._visibility_btn.setFixedWidth(36)
        self._visibility_btn.setObjectName("secondaryButton")
        self._visibility_btn.setCheckable(True)
        self._visibility_btn.toggled.connect(self._toggle_visibility)
        pass_row.addWidget(self._visibility_btn)
        layout.addLayout(pass_row)

        # Remember checkbox
        self._remember_check = QCheckBox()
        self._remember_check.setChecked(True)
        layout.addWidget(self._remember_check)

        # Buttons -- Cancel left, Confirm right (French convention)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._confirm_btn = QPushButton()
        self._confirm_btn.clicked.connect(self._on_confirm)
        self._confirm_btn.setEnabled(False)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)

        # Default focus on cancel (safe action)
        self._cancel_btn.setFocus()

        # Enable confirm when passphrase is non-empty
        self._passphrase_edit.textChanged.connect(self._update_confirm_state)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslateUi(self) -> None:
        """Re-set all translatable UI text."""
        self.setWindowTitle(self.tr("Phrase secr\u00e8te"))
        self._db_label.setText(self.tr("Base de correspondances :"))
        self._pass_label.setText(self.tr("Phrase secr\u00e8te :"))
        self._passphrase_edit.setPlaceholderText(
            self.tr("Entrez votre phrase secr\u00e8te")
        )
        self._visibility_btn.setToolTip(
            self.tr("Afficher/masquer la phrase secr\u00e8te")
        )
        self._remember_check.setText(self.tr("M\u00e9moriser pour cette session"))
        self._cancel_btn.setText(self.tr("Annuler"))
        self._confirm_btn.setText(self.tr("Continuer \u25b6"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def _populate_db_paths(self) -> None:
        """Detect and populate DB paths in the combo box."""
        self._db_combo.blockSignals(True)
        self._db_combo.clear()

        detected: list[str] = []

        # 1. Same directory as selected file
        if self._file_directory:
            candidate = Path(self._file_directory) / DB_FILENAME
            if candidate.exists():
                detected.append(str(candidate))

        # 2. User home directory
        home_candidate = Path.home() / DB_FILENAME
        if home_candidate.exists() and str(home_candidate) not in detected:
            detected.append(str(home_candidate))

        # 3. default_db_path from settings
        settings_path = self._config.get("default_db_path", "")
        if (
            settings_path
            and Path(settings_path).exists()
            and settings_path not in detected
        ):
            detected.append(settings_path)

        for db_path in detected:
            self._db_combo.addItem(db_path, db_path)

        # Special items
        self._db_combo.addItem(self.tr("Parcourir..."), _BROWSE_ITEM)
        self._db_combo.addItem(self.tr("Créer une nouvelle base"), _CREATE_ITEM)

        # Update hint
        if detected:
            self._db_hint.setText(self.tr("Base existante détectée"))
        else:
            self._db_hint.setText(
                self.tr("Aucune base détectée \u2014 créez-en une nouvelle")
            )
            # Default to "Create new" if no existing DB found
            create_idx = self._db_combo.findData(_CREATE_ITEM)
            if create_idx >= 0:
                self._db_combo.setCurrentIndex(create_idx)

        self._db_combo.blockSignals(False)

    def _on_db_combo_changed(self, index: int) -> None:
        """Handle combo box selection changes."""
        data = self._db_combo.itemData(index)
        if data == _BROWSE_ITEM:
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Sélectionner une base de correspondances"),
                "",
                self.tr("SQLite (*.db);;Tous (*)"),
            )
            if filepath:
                # Insert before special items and select it
                insert_idx = max(0, self._db_combo.count() - 2)
                self._db_combo.blockSignals(True)
                self._db_combo.insertItem(insert_idx, filepath, filepath)
                self._db_combo.setCurrentIndex(insert_idx)
                self._db_combo.blockSignals(False)
                self._db_hint.setText(self.tr("Base sélectionnée"))
            else:
                # Revert to first item
                self._db_combo.blockSignals(True)
                self._db_combo.setCurrentIndex(0)
                self._db_combo.blockSignals(False)
        elif data == _CREATE_ITEM:
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Créer une nouvelle base de correspondances"),
                str(Path(self._file_directory or Path.home()) / DB_FILENAME),
                self.tr("SQLite (*.db);;Tous (*)"),
            )
            if filepath:
                insert_idx = max(0, self._db_combo.count() - 2)
                self._db_combo.blockSignals(True)
                self._db_combo.insertItem(insert_idx, filepath, filepath)
                self._db_combo.setCurrentIndex(insert_idx)
                self._db_combo.blockSignals(False)
                self._db_hint.setText(self.tr("Nouvelle base sera créée"))
            else:
                self._db_combo.blockSignals(True)
                self._db_combo.setCurrentIndex(0)
                self._db_combo.blockSignals(False)

        self._update_confirm_state()

    def _toggle_visibility(self, visible: bool) -> None:
        """Toggle passphrase visibility."""
        if visible:
            self._passphrase_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def _update_confirm_state(self, _text: str = "") -> None:
        """Enable confirm button only when passphrase and DB path are valid."""
        has_passphrase = bool(self._passphrase_edit.text().strip())
        db_data = self._db_combo.currentData()
        has_db = db_data not in (_BROWSE_ITEM, _CREATE_ITEM, None)
        self._confirm_btn.setEnabled(has_passphrase and has_db)

    def _on_confirm(self) -> None:
        """Accept dialog and store result."""
        db_path = self._db_combo.currentData()
        passphrase = self._passphrase_edit.text()
        remember = self._remember_check.isChecked()
        self._result = (str(db_path), passphrase, remember)
        self.accept()

    def get_result(self) -> tuple[str, str, bool] | None:
        """Return (db_path, passphrase, remember) or None if cancelled."""
        return self._result

    def keyPressEvent(self, event: object) -> None:  # noqa: N802
        """Escape always dismisses."""
        from PySide6.QtGui import QKeyEvent

        if isinstance(event, QKeyEvent) and event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]

    # -- Test accessors --

    @property
    def db_combo(self) -> QComboBox:
        return self._db_combo

    @property
    def passphrase_edit(self) -> QLineEdit:
        return self._passphrase_edit

    @property
    def remember_check(self) -> QCheckBox:
        return self._remember_check

    @property
    def confirm_button(self) -> QPushButton:
        return self._confirm_btn

    @property
    def cancel_button(self) -> QPushButton:
        return self._cancel_btn

    @property
    def visibility_button(self) -> QPushButton:
        return self._visibility_btn
