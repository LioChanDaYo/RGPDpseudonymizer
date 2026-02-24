"""Settings screen with preferences management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.config import save_gui_config

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
        self._back_btn = QPushButton()
        self._back_btn.setObjectName("secondaryButton")
        self._back_btn.clicked.connect(lambda: self._main_window.navigate_to("home"))
        header.addWidget(self._back_btn)
        header.addStretch()
        self._title = QLabel()
        self._title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(self._title)
        header.addStretch()
        outer.addLayout(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 16, 40, 24)
        layout.setSpacing(16)

        # -- Apparence --
        self._appearance_group = QGroupBox()
        appearance_layout = QFormLayout(self._appearance_group)

        theme_row = QHBoxLayout()
        self._theme_light = QRadioButton()
        self._theme_dark = QRadioButton()
        self._theme_system = QRadioButton()
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
        self._theme_label = QLabel()
        appearance_layout.addRow(self._theme_label, theme_row)

        lang_row = QHBoxLayout()
        self._language_combo = QComboBox()
        self._language_combo.addItem("Français", "fr")
        self._language_combo.addItem("English", "en")
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self._language_combo)
        lang_row.addStretch()
        self._lang_label = QLabel()
        appearance_layout.addRow(self._lang_label, lang_row)

        layout.addWidget(self._appearance_group)

        # -- Traitement --
        self._processing_group = QGroupBox()
        processing_layout = QFormLayout(self._processing_group)

        output_row = QHBoxLayout()
        self._output_dir = QLineEdit()
        self._output_dir.textChanged.connect(
            lambda t: self._save("default_output_dir", t)
        )
        self._output_browse = QPushButton()
        self._output_browse.setObjectName("secondaryButton")
        self._output_browse.clicked.connect(self._browse_output_dir)
        output_row.addWidget(self._output_dir)
        output_row.addWidget(self._output_browse)
        self._output_dir_label = QLabel()
        processing_layout.addRow(self._output_dir_label, output_row)

        db_row = QHBoxLayout()
        self._db_path = QLineEdit()
        self._db_path.textChanged.connect(lambda t: self._save("default_db_path", t))
        self._db_browse = QPushButton()
        self._db_browse.setObjectName("secondaryButton")
        self._db_browse.clicked.connect(self._browse_db_path)
        db_row.addWidget(self._db_path)
        db_row.addWidget(self._db_browse)
        self._db_path_label = QLabel()
        processing_layout.addRow(self._db_path_label, db_row)

        self._default_theme_combo = QComboBox()
        self._default_theme_combo.addItem("", "neutral")
        self._default_theme_combo.addItem("Star Wars", "star_wars")
        self._default_theme_combo.addItem("", "lotr")
        self._default_theme_combo.currentIndexChanged.connect(
            self._on_default_theme_changed
        )
        self._default_theme_label = QLabel()
        processing_layout.addRow(self._default_theme_label, self._default_theme_combo)

        layout.addWidget(self._processing_group)

        # -- Traitement par lot --
        self._batch_group = QGroupBox()
        batch_layout = QFormLayout(self._batch_group)

        validation_row = QHBoxLayout()
        self._validation_per_doc = QRadioButton()
        self._validation_global = QRadioButton()
        self._validation_per_doc.toggled.connect(
            lambda c: self._save("batch_validation_mode", "per_document") if c else None
        )
        self._validation_global.toggled.connect(
            lambda c: self._save("batch_validation_mode", "global") if c else None
        )
        validation_row.addWidget(self._validation_per_doc)
        validation_row.addWidget(self._validation_global)
        validation_row.addStretch()
        self._validation_mode_label = QLabel()
        batch_layout.addRow(self._validation_mode_label, validation_row)

        self._continue_on_error = QCheckBox()
        self._continue_on_error.toggled.connect(
            lambda c: self._save("continue_on_error", c)
        )
        batch_layout.addRow("", self._continue_on_error)

        self._workers_spinner = QSpinBox()
        self._workers_spinner.setMinimum(1)
        self._workers_spinner.setMaximum(8)
        self._workers_spinner.valueChanged.connect(
            lambda v: self._save("batch_workers", v)
        )
        self._workers_label = QLabel()
        batch_layout.addRow(self._workers_label, self._workers_spinner)

        layout.addWidget(self._batch_group)

        # -- Avancé --
        self._advanced_group = QGroupBox()
        advanced_layout = QFormLayout(self._advanced_group)

        self._welcome_toggle = QCheckBox()
        self._welcome_toggle.toggled.connect(
            lambda c: self._save("welcome_shown", not c)
        )
        advanced_layout.addRow("", self._welcome_toggle)

        self._hints_toggle = QCheckBox()
        self._hints_toggle.toggled.connect(
            lambda c: self._save("validation_hints_shown", not c)
        )
        advanced_layout.addRow("", self._hints_toggle)

        layout.addWidget(self._advanced_group)

        # -- Raccourcis clavier (read-only) --
        self._shortcuts_group = QGroupBox()
        self._shortcuts_layout = QVBoxLayout(self._shortcuts_group)
        # Store shortcut description labels for retranslation
        self._shortcut_desc_labels: list[QLabel] = []
        shortcuts_data = [
            ("Ctrl+O", "Ouvrir un document"),
            ("Ctrl+Shift+O", "Ouvrir un dossier"),
            ("Ctrl+,", "Paramètres"),
            ("Ctrl+Q", "Quitter"),
            ("F1", "Raccourcis clavier"),
            ("F11", "Plein écran"),
        ]
        self._shortcuts_data = shortcuts_data
        for key, _desc in shortcuts_data:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setStyleSheet(
                "font-family: monospace; font-weight: bold; min-width: 120px;"
            )
            row.addWidget(key_label)
            desc_label = QLabel()
            row.addWidget(desc_label)
            self._shortcut_desc_labels.append(desc_label)
            row.addStretch()
            self._shortcuts_layout.addLayout(row)
        layout.addWidget(self._shortcuts_group)

        layout.addStretch()
        scroll.setWidget(content)
        # QScrollArea.setWidget() forces autoFillBackground(True) on content,
        # which paints black when QSS overrides the native palette. Disable it.
        content.setAutoFillBackground(False)
        outer.addWidget(scroll)

        # Set translatable text
        self.retranslateUi()

    def retranslateUi(self) -> None:
        """Re-set all translatable static UI text."""
        self._back_btn.setText(self.tr("\u2190 Retour"))
        self._title.setText(self.tr("Paramètres"))

        # Apparence
        self._appearance_group.setTitle(self.tr("Apparence"))
        self._theme_label.setText(self.tr("Thème :"))
        self._theme_light.setText(self.tr("Clair"))
        self._theme_dark.setText(self.tr("Sombre"))
        self._theme_system.setText(self.tr("Système"))
        self._lang_label.setText(self.tr("Langue :"))

        # Traitement
        self._processing_group.setTitle(self.tr("Traitement"))
        self._output_dir_label.setText(self.tr("Dossier de sortie :"))
        self._output_dir.setPlaceholderText(
            self.tr("Même dossier que le fichier source")
        )
        self._output_browse.setText(self.tr("Parcourir..."))
        self._db_path_label.setText(self.tr("Base de données :"))
        self._db_path.setPlaceholderText("./gdpr-pseudo.db")
        self._db_browse.setText(self.tr("Parcourir..."))
        self._default_theme_label.setText(self.tr("Thème de pseudonymes par défaut :"))
        self._default_theme_combo.setItemText(0, self.tr("Neutre (INSEE)"))
        # Star Wars is a proper noun -- no translation needed
        self._default_theme_combo.setItemText(1, "Star Wars")
        self._default_theme_combo.setItemText(2, self.tr("Le Seigneur des Anneaux"))

        # Traitement par lot
        self._batch_group.setTitle(self.tr("Traitement par lot"))
        self._validation_mode_label.setText(self.tr("Mode de validation :"))
        self._validation_per_doc.setText(self.tr("Par document"))
        self._validation_global.setText(self.tr("Globale"))
        self._continue_on_error.setText(self.tr("Continuer en cas d'erreur"))
        self._workers_label.setText(self.tr("Nombre de workers :"))
        self._workers_spinner.setToolTip(
            self.tr("Nombre de workers pour le traitement en ligne de commande")
        )

        # Avancé
        self._advanced_group.setTitle(self.tr("Avancé"))
        self._welcome_toggle.setText(
            self.tr("Afficher l'écran de bienvenue au démarrage")
        )
        self._hints_toggle.setText(self.tr("Afficher les conseils de validation"))

        # Raccourcis clavier
        self._shortcuts_group.setTitle(self.tr("Raccourcis clavier"))
        shortcut_descriptions = [
            self.tr("Ouvrir un document"),
            self.tr("Ouvrir un dossier"),
            self.tr("Paramètres"),
            self.tr("Quitter"),
            self.tr("Raccourcis clavier"),
            self.tr("Plein écran"),
        ]
        for lbl, desc in zip(self._shortcut_desc_labels, shortcut_descriptions):
            lbl.setText(desc)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

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

        self._workers_spinner.setValue(self._config.get("batch_workers", 4))

        default_theme = self._config.get("default_theme", "neutral")
        theme_idx = self._default_theme_combo.findData(default_theme)
        if theme_idx >= 0:
            self._default_theme_combo.setCurrentIndex(theme_idx)

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

    def _on_default_theme_changed(self, index: int) -> None:
        theme_value = self._default_theme_combo.itemData(index)
        if theme_value:
            self._save("default_theme", theme_value)

    def _on_language_changed(self, index: int) -> None:
        lang = self._language_combo.itemData(index)
        if lang:
            self._save("language", lang)
            from PySide6.QtWidgets import QApplication

            from gdpr_pseudonymizer.gui.i18n import switch_language

            app = QApplication.instance()
            if app is not None:
                switch_language(app, lang)

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Dossier de sortie"))
        if folder:
            self._output_dir.setText(folder)

    def _browse_db_path(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Base de données"),
            "",
            self.tr("SQLite (*.db);;Tous (*)"),
        )
        if filepath:
            self._db_path.setText(filepath)
