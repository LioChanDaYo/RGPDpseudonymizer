"""Internationalization infrastructure for the GUI.

Provides QTranslator management, language switching, and auto-detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QLocale, QTranslator

# Directory containing .ts / .qm translation files
_I18N_DIR = Path(__file__).parent

# Module-level reference to the active translator (kept alive to prevent GC)
_current_translator: QTranslator | None = None

# Supported language codes
SUPPORTED_LANGUAGES: list[str] = ["fr", "en"]
DEFAULT_LANGUAGE = "fr"


def available_languages() -> list[str]:
    """Return list of supported language codes."""
    return list(SUPPORTED_LANGUAGES)


def detect_language(config: dict[str, Any] | None = None) -> str:
    """Detect the preferred language.

    Priority:
    1. Explicit ``language`` key in *config* (from .gdpr-pseudo.yaml)
    2. System locale via ``QLocale``
    3. Fallback to French (default)
    """
    # 1. Config override
    if config:
        lang: str = config.get("language", "")
        if lang in SUPPORTED_LANGUAGES:
            return lang

    # 2. System locale
    system_lang = QLocale.system().language()
    if system_lang == QLocale.Language.French:
        return "fr"
    if system_lang == QLocale.Language.English:
        return "en"

    # 3. Default
    return DEFAULT_LANGUAGE


def install_translator(app: QCoreApplication, language: str) -> bool:
    """Install a QTranslator for *language* on *app*.

    Returns ``True`` if the translator was loaded successfully or if the
    language is French (source language — no translation file needed).
    """
    global _current_translator

    # French is the source language — no translation needed
    if language == "fr":
        _current_translator = None
        return True

    translator = QTranslator(app)
    qm_path = _I18N_DIR / f"{language}.qm"

    if qm_path.exists() and translator.load(str(qm_path)):
        app.installTranslator(translator)
        _current_translator = translator
        return True

    # .qm not found — try loading from .ts directly (development fallback)
    ts_path = _I18N_DIR / f"{language}.ts"
    if ts_path.exists() and translator.load(str(ts_path)):
        app.installTranslator(translator)
        _current_translator = translator
        return True

    return False


def qarg(template: str, *args: str) -> str:
    """Mimic ``QString::arg()`` for PySide6 translated strings.

    PySide6's ``QObject.tr()`` returns a plain Python ``str`` which lacks
    the ``arg()`` method available on C++ ``QString``.  This helper
    performs the same ``%1``, ``%2``, ... placeholder substitution.

    Usage::

        qarg(self.tr("%1 fichier(s) sur %2"), str(count), str(total))
    """
    result = template
    for i, value in enumerate(args, start=1):
        result = result.replace(f"%{i}", value)
    return result


def switch_language(app: QCoreApplication, language: str) -> bool:
    """Switch the application language at runtime.

    Removes any existing translator, installs the new one, and posts a
    ``LanguageChange`` event so all widgets can call ``retranslateUi()``.
    """
    global _current_translator

    # Remove current translator
    if _current_translator is not None:
        app.removeTranslator(_current_translator)
        _current_translator = None

    return install_translator(app, language)
