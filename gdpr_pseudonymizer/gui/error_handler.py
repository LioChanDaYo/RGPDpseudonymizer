"""Global exception handler for the GUI application.

Overrides sys.excepthook to catch unhandled exceptions,
log them via structlog, and show a user-friendly dialog.
"""

from __future__ import annotations

import sys
import traceback
from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow


def install_exception_handler(main_window: MainWindow) -> None:
    """Install a global exception handler that shows an error dialog."""

    def _handler(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        # Log via structlog
        from gdpr_pseudonymizer.utils.logger import get_logger

        logger = get_logger("gui.error_handler")
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error(
            "unhandled_exception",
            exception_type=exc_type.__name__,
            traceback_summary=tb_text[:500],
        )

        # Show user-friendly dialog
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                main_window,
                "Erreur inattendue",
                "Une erreur inattendue s'est produite.\n\n"
                f"Type : {exc_type.__name__}\n"
                "L'application va revenir à l'écran d'accueil.",
            )
            main_window.navigate_to("home")
        except Exception:
            # If the dialog itself fails, at least print
            traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler
