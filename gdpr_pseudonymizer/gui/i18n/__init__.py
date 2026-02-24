"""Internationalization support for the GUI.

Re-exports public API from the translator module.
"""

from gdpr_pseudonymizer.gui.i18n.translator import (
    available_languages,
    detect_language,
    install_translator,
    qarg,
    switch_language,
)

__all__ = [
    "available_languages",
    "detect_language",
    "install_translator",
    "qarg",
    "switch_language",
]
