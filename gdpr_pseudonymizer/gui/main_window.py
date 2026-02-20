"""Main application window with menu bar, navigation, and status bar."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMenuBar,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.widgets.step_indicator import StepIndicator


class MainWindow(QMainWindow):
    """Primary application window."""

    MINIMUM_WIDTH = 900
    MINIMUM_HEIGHT = 600
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        from gdpr_pseudonymizer.gui.config import load_gui_config, save_gui_config

        self._config = config if config is not None else load_gui_config()
        self._save_config = save_gui_config

        self.setWindowTitle("GDPR Pseudonymizer")
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        # Central layout: step indicator + stacked widget
        from gdpr_pseudonymizer.gui.widgets.step_indicator import StepIndicator

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._step_indicator = StepIndicator()
        central_layout.addWidget(self._step_indicator)

        self._stack = QStackedWidget()
        central_layout.addWidget(self._stack)

        self.setCentralWidget(central)

        # Build UI components
        self._build_menu_bar()
        self._build_status_bar()

        # Session passphrase cache: (db_path, passphrase) — cleared on exit
        self._cached_passphrase: tuple[str, str] | None = None

        # Screens added later via add_screen()
        self._screens: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_screen(self, name: str, widget: QWidget) -> None:
        """Register a screen widget with a name."""
        idx = self._stack.addWidget(widget)
        self._screens[name] = idx

    def navigate_to(self, name: str, **kwargs: Any) -> None:
        """Switch to a named screen, optionally passing context data."""
        if name in self._screens:
            idx = self._screens[name]
            widget = self._stack.widget(idx)
            if kwargs and hasattr(widget, "set_context"):
                widget.set_context(**kwargs)
            self._stack.setCurrentIndex(idx)

    def current_screen_name(self) -> str:
        """Return the name of the currently displayed screen."""
        idx = self._stack.currentIndex()
        for name, i in self._screens.items():
            if i == idx:
                return name
        return ""

    @property
    def stack(self) -> QStackedWidget:
        """Access the stacked widget for testing."""
        return self._stack

    @property
    def step_indicator(self) -> StepIndicator:
        """Access the step indicator for testing."""

        return self._step_indicator

    @property
    def config(self) -> dict[str, Any]:
        """Access current config."""
        return self._config

    @property
    def cached_passphrase(self) -> tuple[str, str] | None:
        """Session passphrase cache: (db_path, passphrase)."""
        return self._cached_passphrase

    @cached_passphrase.setter
    def cached_passphrase(self, value: tuple[str, str] | None) -> None:
        self._cached_passphrase = value

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar: QMenuBar = self.menuBar()

        # -- Fichier --
        file_menu = menu_bar.addMenu("Fichier")

        self._action_open = QAction("Ouvrir un document...", self)
        self._action_open.setShortcut(QKeySequence("Ctrl+O"))
        self._action_open.triggered.connect(self._on_open_file)
        file_menu.addAction(self._action_open)

        self._action_open_folder = QAction("Ouvrir un dossier...", self)
        self._action_open_folder.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self._action_open_folder.triggered.connect(self._on_open_folder)
        file_menu.addAction(self._action_open_folder)

        self._recent_menu = file_menu.addMenu("Fichiers récents")
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        action_quit = QAction("Quitter", self)
        action_quit.setShortcut(QKeySequence("Ctrl+Q"))
        action_quit.triggered.connect(self.close)
        file_menu.addAction(action_quit)

        # -- Affichage --
        view_menu = menu_bar.addMenu("Affichage")

        self._action_theme_light = QAction("Thème clair", self)
        self._action_theme_light.triggered.connect(lambda: self._set_theme("light"))
        view_menu.addAction(self._action_theme_light)

        self._action_theme_dark = QAction("Thème sombre", self)
        self._action_theme_dark.triggered.connect(lambda: self._set_theme("dark"))
        view_menu.addAction(self._action_theme_dark)

        view_menu.addSeparator()

        self._action_entity_panel = QAction("Panneau des entités", self)
        self._action_entity_panel.setEnabled(False)
        view_menu.addAction(self._action_entity_panel)

        # -- Outils --
        tools_menu = menu_bar.addMenu("Outils")

        action_db = QAction("Base de correspondances...", self)
        action_db.triggered.connect(lambda: self.navigate_to("database"))
        tools_menu.addAction(action_db)

        action_settings = QAction("Paramètres...", self)
        action_settings.setShortcut(QKeySequence("Ctrl+,"))
        action_settings.triggered.connect(lambda: self.navigate_to("settings"))
        tools_menu.addAction(action_settings)

        # -- Aide --
        help_menu = menu_bar.addMenu("Aide")

        action_shortcuts = QAction("Raccourcis clavier...", self)
        action_shortcuts.setShortcut(QKeySequence("F1"))
        action_shortcuts.triggered.connect(self._show_shortcuts)
        help_menu.addAction(action_shortcuts)

        action_about = QAction("À propos", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)

        # -- Global shortcuts --
        self._action_fullscreen = QAction("Plein écran", self)
        self._action_fullscreen.setShortcut(QKeySequence("F11"))
        self._action_fullscreen.triggered.connect(self._toggle_fullscreen)
        self.addAction(self._action_fullscreen)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        status_bar: QStatusBar = self.statusBar()
        status_bar.showMessage("Prêt")

        self._theme_toggle_btn = QToolButton()
        self._theme_toggle_btn.setObjectName("themeToggleButton")
        self._update_theme_toggle_icon()
        self._theme_toggle_btn.clicked.connect(self._toggle_theme)
        status_bar.addPermanentWidget(self._theme_toggle_btn)

    def _update_theme_toggle_icon(self) -> None:
        current = self._config.get("theme", "system")
        if current == "dark":
            self._theme_toggle_btn.setText("\u2600")  # ☀ sun
            self._theme_toggle_btn.setToolTip("Passer au thème clair")
        else:
            self._theme_toggle_btn.setText("\U0001f319")  # 🌙 moon
            self._theme_toggle_btn.setToolTip("Passer au thème sombre")

    # ------------------------------------------------------------------
    # Theme management
    # ------------------------------------------------------------------

    def _set_theme(self, theme: str) -> None:
        self._config["theme"] = theme
        self._save_config(self._config)
        self._apply_theme()
        self._update_theme_toggle_icon()

    def _toggle_theme(self) -> None:
        current = self._config.get("theme", "system")
        new_theme = "light" if current == "dark" else "dark"
        self._set_theme(new_theme)

    def _apply_theme(self) -> None:
        """Load and apply QSS theme file."""
        theme = self._config.get("theme", "system")
        if theme == "system":
            theme = "light"
        themes_dir = Path(__file__).parent / "resources" / "themes"
        qss_file = themes_dir / f"{theme}.qss"
        if qss_file.exists():
            with open(qss_file, encoding="utf-8") as f:
                qss = f.read()
            app = self._get_app()
            if app is not None:
                app.setStyleSheet(qss)

    def apply_initial_theme(self) -> None:
        """Apply theme at startup. Called after window is shown."""
        self._apply_theme()

    @staticmethod
    def _get_app() -> Any:
        from PySide6.QtWidgets import QApplication

        return QApplication.instance()

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent = self._config.get("recent_files", [])
        if not recent:
            action = QAction("(aucun fichier récent)", self)
            action.setEnabled(False)
            self._recent_menu.addAction(action)
            return
        for filepath in recent:
            action = QAction(filepath, self)
            action.triggered.connect(
                lambda checked=False, fp=filepath: self._open_recent(fp)
            )
            self._recent_menu.addAction(action)

    def _open_recent(self, filepath: str) -> None:
        """Handle opening a recent file."""
        p = Path(filepath)
        if not p.exists():
            # Will be handled by home screen
            pass
        self._notify_file_selected(filepath)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_file(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un document",
            "",
            "Documents (*.txt *.md *.pdf *.docx);;Tous (*)",
        )
        if filepath:
            self._notify_file_selected(filepath)

    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Ouvrir un dossier",
        )
        if folder:
            self.navigate_to("batch", folder_path=folder)

    def _notify_file_selected(self, filepath: str) -> None:
        """Route file selection through the home screen's processing flow."""
        from gdpr_pseudonymizer.gui.config import add_recent_file

        add_recent_file(filepath, self._config)
        self._save_config(self._config)
        self._rebuild_recent_menu()

        # Delegate to home screen's file selection handler
        home_idx = self._screens.get("home")
        if home_idx is not None:
            widget = self._stack.widget(home_idx)
            from gdpr_pseudonymizer.gui.screens.home import HomeScreen

            if isinstance(widget, HomeScreen):
                widget._on_file_selected(filepath)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _show_shortcuts(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        shortcuts = (
            "Raccourcis clavier\n\n"
            "Ctrl+O\tOuvrir un document\n"
            "Ctrl+Shift+O\tOuvrir un dossier\n"
            "Ctrl+,\tParamètres\n"
            "Ctrl+Q\tQuitter\n"
            "F1\tRaccourcis clavier\n"
            "F11\tPlein écran\n"
        )
        QMessageBox.information(self, "Raccourcis clavier", shortcuts)

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "À propos",
            "<h3>GDPR Pseudonymizer</h3>"
            "<p>Version 2.0.0</p>"
            "<p>Outil de pseudonymisation conforme au RGPD "
            "pour les documents en français.</p>"
            "<p>Licence MIT</p>"
            '<p><a href="https://github.com/LioChanDaYo/RGPDpseudonymizer">'
            "GitHub</a></p>",
        )
