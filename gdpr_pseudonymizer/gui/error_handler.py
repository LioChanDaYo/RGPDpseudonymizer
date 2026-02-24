"""Global exception handler for the GUI application.

Overrides sys.excepthook to catch unhandled exceptions,
log them via structlog, and show a user-friendly dialog.
"""

from __future__ import annotations

import sys
import traceback
from types import TracebackType
from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication

from gdpr_pseudonymizer.gui.i18n import qarg

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow

_tr = QCoreApplication.translate


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
                _tr("ErrorHandler", "Erreur inattendue"),
                qarg(
                    _tr(
                        "ErrorHandler",
                        "Une erreur inattendue s'est produite.\n\n"
                        "Type : %1\n"
                        "L'application va revenir à l'écran d'accueil.",
                    ),
                    exc_type.__name__,
                ),
            )
            main_window.navigate_to("home")
        except Exception:
            # If the dialog itself fails, at least print
            traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler
