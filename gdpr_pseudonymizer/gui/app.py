"""GUI application entry point.

Launches the PySide6-based desktop interface.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

    from gdpr_pseudonymizer.gui.main_window import MainWindow


def main() -> None:
    """Application entry point — called by gdpr-pseudo-gui script."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 is required for the GUI.\n"
            "Install with:\n"
            "  - Poetry (development): poetry install --extras gui\n"
            "  - pip (PyPI):          pip install gdpr-pseudonymizer[gui]",
            file=sys.stderr,
        )
        raise SystemExit(1)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QSplashScreen

    from gdpr_pseudonymizer.gui.config import load_gui_config
    from gdpr_pseudonymizer.gui.error_handler import install_exception_handler
    from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

    configure_logging("INFO")
    logger = get_logger(__name__)
    logger.info("gui_starting")

    app = QApplication(sys.argv)
    app.setApplicationName("GDPR Pseudonymizer")
    app.setApplicationVersion("2.0.0")

    # High-DPI is automatic in Qt6, no attribute needed

    # -- Application icon --
    from pathlib import Path

    from PySide6.QtGui import QIcon

    icon_dir = Path(__file__).parent / "resources" / "icons"
    icon = QIcon()
    for size in (16, 32, 48, 256, 512):
        png_path = icon_dir / f"icon_{size}.png"
        if png_path.exists():
            icon.addFile(str(png_path))
    if not icon.isNull():
        app.setWindowIcon(icon)

    # -- Splash screen --
    splash_pixmap = _create_splash_pixmap()
    splash = QSplashScreen(splash_pixmap)
    splash.show()
    app.processEvents()

    # -- Build main window while splash is shown --
    config = load_gui_config()

    from gdpr_pseudonymizer.gui.main_window import MainWindow

    window = MainWindow(config=config)

    # Install global exception handler
    install_exception_handler(window)

    # Register screens
    _register_screens(window)

    logger.info("gui_screens_registered")

    # Minimum splash duration: 1.5s
    def _show_main() -> None:
        splash.finish(window)
        window.show()
        window.apply_initial_theme()
        logger.info("gui_ready")

    QTimer.singleShot(1500, _show_main)

    # Maximum splash duration: 5s safety
    QTimer.singleShot(5000, lambda: splash.close())

    sys.exit(app.exec())


def _create_splash_pixmap() -> QPixmap:
    """Create a simple splash screen pixmap programmatically."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap

    width, height = 400, 300
    pixmap = QPixmap(width, height)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background gradient
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0, QColor("#1565C0"))
    gradient.setColorAt(1, QColor("#0D47A1"))
    painter.fillRect(0, 0, width, height, gradient)

    # Title
    painter.setPen(QColor("#FFFFFF"))
    title_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(
        0, 80, width, 50, Qt.AlignmentFlag.AlignCenter, "GDPR Pseudonymizer"
    )

    # Version
    ver_font = QFont("Segoe UI", 12)
    painter.setFont(ver_font)
    painter.drawText(0, 140, width, 30, Qt.AlignmentFlag.AlignCenter, "v2.0.0")

    # Loading text
    loading_font = QFont("Segoe UI", 10)
    painter.setFont(loading_font)
    painter.setPen(QColor("#B3D4FC"))
    painter.drawText(0, 250, width, 30, Qt.AlignmentFlag.AlignCenter, "Chargement...")

    painter.end()
    return pixmap


def _register_screens(window: MainWindow) -> None:
    """Register all screen widgets with the main window."""
    from gdpr_pseudonymizer.gui.screens.home import HomeScreen
    from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen
    from gdpr_pseudonymizer.gui.screens.results import ResultsScreen
    from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen
    from gdpr_pseudonymizer.gui.screens.stub import StubScreen
    from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

    window.add_screen("home", HomeScreen(window))
    window.add_screen("settings", SettingsScreen(window))
    window.add_screen("processing", ProcessingScreen(window))
    window.add_screen("validation", ValidationScreen(window))
    window.add_screen("results", ResultsScreen(window))
    window.add_screen("batch", StubScreen("Traitement par lot", window))
    window.add_screen("database", StubScreen("Base de correspondances", window))

    window.navigate_to("home")


if __name__ == "__main__":
    main()
