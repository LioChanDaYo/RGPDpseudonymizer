"""Settings screen with preferences management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.config import save_gui_config
from gdpr_pseudonymizer.gui.widgets.toast import Toast

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow


class SettingsScreen(QWidget):
    """Configuration management screen with auto-save."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._config = main_window.config

        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header with back button
        header = QHBoxLayout()
        back_btn = QPushButton("← Retour")
        back_btn.setObjectName("secondaryButton")
        back_btn.clicked.connect(lambda: self._main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addStretch()
        title = QLabel("Paramètres")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        outer.addLayout(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 16, 40, 24)
        layout.setSpacing(16)

        # -- Apparence --
        appearance_group = QGroupBox("Apparence")
        appearance_layout = QFormLayout(appearance_group)

        theme_row = QHBoxLayout()
        self._theme_light = QRadioButton("Clair")
        self._theme_dark = QRadioButton("Sombre")
        self._theme_system = QRadioButton("Système")
        self._theme_light.toggled.connect(
            lambda c: self._save("theme", "light") if c else None
        )
        self._theme_dark.toggled.connect(
            lambda c: self._save("theme", "dark") if c else None
        )
        self._theme_system.toggled.connect(
            lambda c: self._save("theme", "system") if c else None
        )
        theme_row.addWidget(self._theme_light)
        theme_row.addWidget(self._theme_dark)
        theme_row.addWidget(self._theme_system)
        theme_row.addStretch()
        appearance_layout.addRow("Thème :", theme_row)

        lang_row = QHBoxLayout()
        self._language_combo = QComboBox()
        self._language_combo.addItem("Français", "fr")
        self._language_combo.addItem("English", "en")
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self._language_combo)
        lang_hint = QLabel("Redémarrage requis")
        lang_hint.setObjectName("secondaryLabel")
        lang_hint.setStyleSheet("font-size: 11px; font-style: italic;")
        lang_row.addWidget(lang_hint)
        lang_row.addStretch()
        appearance_layout.addRow("Langue :", lang_row)

        layout.addWidget(appearance_group)

        # -- Traitement --
        processing_group = QGroupBox("Traitement")
        processing_layout = QFormLayout(processing_group)

        output_row = QHBoxLayout()
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("Même dossier que le fichier source")
        self._output_dir.textChanged.connect(
            lambda t: self._save("default_output_dir", t)
        )
        output_browse = QPushButton("Parcourir...")
        output_browse.setObjectName("secondaryButton")
        output_browse.clicked.connect(self._browse_output_dir)
        output_row.addWidget(self._output_dir)
        output_row.addWidget(output_browse)
        processing_layout.addRow("Dossier de sortie :", output_row)

        db_row = QHBoxLayout()
        self._db_path = QLineEdit()
        self._db_path.setPlaceholderText("./gdpr-pseudo.db")
        self._db_path.textChanged.connect(lambda t: self._save("default_db_path", t))
        db_browse = QPushButton("Parcourir...")
        db_browse.setObjectName("secondaryButton")
        db_browse.clicked.connect(self._browse_db_path)
        db_row.addWidget(self._db_path)
        db_row.addWidget(db_browse)
        processing_layout.addRow("Base de données :", db_row)

        layout.addWidget(processing_group)

        # -- Traitement par lot --
        batch_group = QGroupBox("Traitement par lot")
        batch_layout = QFormLayout(batch_group)

        validation_row = QHBoxLayout()
        self._validation_per_doc = QRadioButton("Par document")
        self._validation_global = QRadioButton("Globale")
        self._validation_per_doc.toggled.connect(
            lambda c: self._save("batch_validation_mode", "per_document") if c else None
        )
        self._validation_global.toggled.connect(
            lambda c: self._save("batch_validation_mode", "global") if c else None
        )
        validation_row.addWidget(self._validation_per_doc)
        validation_row.addWidget(self._validation_global)
        validation_row.addStretch()
        batch_layout.addRow("Mode de validation :", validation_row)

        self._continue_on_error = QCheckBox("Continuer en cas d'erreur")
        self._continue_on_error.toggled.connect(
            lambda c: self._save("continue_on_error", c)
        )
        batch_layout.addRow("", self._continue_on_error)

        layout.addWidget(batch_group)

        # -- Avancé --
        advanced_group = QGroupBox("Avancé")
        advanced_layout = QFormLayout(advanced_group)

        self._welcome_toggle = QCheckBox("Afficher l'écran de bienvenue au démarrage")
        self._welcome_toggle.toggled.connect(
            lambda c: self._save("welcome_shown", not c)
        )
        advanced_layout.addRow("", self._welcome_toggle)

        self._hints_toggle = QCheckBox("Afficher les conseils de validation")
        self._hints_toggle.toggled.connect(
            lambda c: self._save("validation_hints_shown", not c)
        )
        advanced_layout.addRow("", self._hints_toggle)

        layout.addWidget(advanced_group)

        # -- Raccourcis clavier (read-only) --
        shortcuts_group = QGroupBox("Raccourcis clavier")
        shortcuts_layout = QVBoxLayout(shortcuts_group)
        shortcuts_data = [
            ("Ctrl+O", "Ouvrir un document"),
            ("Ctrl+Shift+O", "Ouvrir un dossier"),
            ("Ctrl+,", "Paramètres"),
            ("Ctrl+Q", "Quitter"),
            ("F1", "Raccourcis clavier"),
            ("F11", "Plein écran"),
        ]
        for key, desc in shortcuts_data:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setStyleSheet(
                "font-family: monospace; font-weight: bold; min-width: 120px;"
            )
            row.addWidget(key_label)
            row.addWidget(QLabel(desc))
            row.addStretch()
            shortcuts_layout.addLayout(row)
        layout.addWidget(shortcuts_group)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _load_values(self) -> None:
        """Load current config values into UI widgets."""
        theme = self._config.get("theme", "system")
        if theme == "light":
            self._theme_light.setChecked(True)
        elif theme == "dark":
            self._theme_dark.setChecked(True)
        else:
            self._theme_system.setChecked(True)

        lang = self._config.get("language", "fr")
        idx = self._language_combo.findData(lang)
        if idx >= 0:
            self._language_combo.setCurrentIndex(idx)

        self._output_dir.setText(self._config.get("default_output_dir", ""))
        self._db_path.setText(self._config.get("default_db_path", ""))

        batch_mode = self._config.get("batch_validation_mode", "per_document")
        if batch_mode == "global":
            self._validation_global.setChecked(True)
        else:
            self._validation_per_doc.setChecked(True)

        self._continue_on_error.setChecked(self._config.get("continue_on_error", True))
        self._welcome_toggle.setChecked(not self._config.get("welcome_shown", False))
        self._hints_toggle.setChecked(
            not self._config.get("validation_hints_shown", False)
        )

    def _save(self, key: str, value: object) -> None:
        """Save a single setting and persist."""
        self._config[key] = value
        save_gui_config(self._config)

        # Apply theme change immediately
        if key == "theme":
            self._main_window._set_theme(str(value))

    def _on_language_changed(self, index: int) -> None:
        lang = self._language_combo.itemData(index)
        if lang:
            self._save("language", lang)
            Toast.show_message(
                "Langue enregistrée — redémarrez l'application pour appliquer.",
                self._main_window,
                duration_ms=4000,
            )

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if folder:
            self._output_dir.setText(folder)

    def _browse_db_path(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Base de données",
            "",
            "SQLite (*.db);;Tous (*)",
        )
        if filepath:
            self._db_path.setText(filepath)
