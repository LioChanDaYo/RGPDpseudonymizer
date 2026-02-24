"""CLI internationalization using gettext.

Provides lazy gettext strings so that ``--lang`` (eager callback)
can set the target language **before** click/Typer renders help text.

Usage in CLI modules::

    from gdpr_pseudonymizer.cli.i18n import _, set_language

    @app.command(help=_("Process a single document"))
    def process(...):
        ...

Language detection priority:
    1. ``--lang`` flag (set via eager callback before help rendering)
    2. ``GDPR_PSEUDO_LANG`` environment variable
    3. System locale (``locale.getdefaultlocale()``)
    4. Default: English
"""

from __future__ import annotations

import gettext
import locale
import os
from pathlib import Path
from typing import Any

# Directory containing locale/<lang>/LC_MESSAGES/cli.mo
_LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"

# Supported languages
SUPPORTED_LANGUAGES = ("fr", "en")
DEFAULT_LANGUAGE = "en"

# Module state
_current_language: str = DEFAULT_LANGUAGE
_translations: gettext.NullTranslations | None = None


def _detect_language() -> str:
    """Detect CLI language from environment or system locale."""
    # 1. GDPR_PSEUDO_LANG environment variable
    env_lang = os.environ.get("GDPR_PSEUDO_LANG", "")
    if env_lang in SUPPORTED_LANGUAGES:
        return env_lang

    # 2. System locale
    try:
        sys_locale, _ = locale.getdefaultlocale()
        if sys_locale and sys_locale.startswith("fr"):
            return "fr"
    except (ValueError, AttributeError):
        pass

    # 3. Default to English
    return DEFAULT_LANGUAGE


def set_language(lang: str) -> None:
    """Set the active gettext language for CLI strings.

    Args:
        lang: Language code ("fr" or "en").
    """
    global _current_language, _translations

    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    _current_language = lang

    if lang == "en":
        _translations = gettext.NullTranslations()
    else:
        try:
            _translations = gettext.translation(
                "cli",
                localedir=str(_LOCALE_DIR),
                languages=[lang],
            )
        except FileNotFoundError:
            _translations = gettext.NullTranslations()


def get_language() -> str:
    """Return the current active language code."""
    return _current_language


def _gettext(message: str) -> str:
    """Translate *message* using the current active translations."""
    if _translations is None:
        return message
    return _translations.gettext(message)


class _LazyString:
    """Lazy gettext proxy — resolves translation at access time.

    This allows ``--lang`` (eager Typer callback) to change the language
    **after** module import but **before** click reads help strings.
    """

    __slots__ = ("_msg",)

    def __init__(self, msg: str) -> None:
        self._msg = msg

    # --- Core string protocol -------------------------------------------------

    def __str__(self) -> str:
        return _gettext(self._msg)

    def __repr__(self) -> str:
        return f"_LazyString({self._msg!r})"

    def __len__(self) -> int:
        return len(str(self))

    def __bool__(self) -> bool:
        return bool(self._msg)

    def __contains__(self, item: str) -> bool:
        return item in str(self)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._msg)

    # --- String concatenation -------------------------------------------------

    def __add__(self, other: Any) -> str:
        return str(self) + str(other)

    def __radd__(self, other: Any) -> str:
        return str(other) + str(self)

    def __mod__(self, other: Any) -> str:
        result: str = str(self) % other
        return result

    def __format__(self, format_spec: str) -> str:
        return format(str(self), format_spec)

    # --- Delegate all other str methods to the resolved value -----------------

    def __getattr__(self, name: str) -> Any:
        return getattr(str(self), name)


def _(message: str) -> str:
    """Mark *message* for translation.

    Returns a lazy proxy that resolves to the translated string when
    ``str()`` or any string method is called on it.

    The return type is annotated as ``str`` for mypy compatibility with
    Typer's ``help=`` parameter, but the actual runtime type is
    ``_LazyString`` (a str-like proxy).
    """
    return _LazyString(message)  # type: ignore[return-value]


def _lang_from_argv() -> str | None:
    """Pre-scan ``sys.argv`` for ``--lang <code>`` before Typer parses it.

    This is necessary because Typer 0.9.x eager callbacks fire *after*
    subcommand help is rendered, so ``--lang`` must be processed at
    import time for ``--help`` translations to work.
    """
    import sys

    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            candidate = argv[i + 1]
            if candidate in SUPPORTED_LANGUAGES:
                return candidate
        elif arg.startswith("--lang="):
            candidate = arg.split("=", 1)[1]
            if candidate in SUPPORTED_LANGUAGES:
                return candidate
    return None


# Initialize language on import
# Priority: 1) --lang from argv  2) env var / system locale
set_language(_lang_from_argv() or _detect_language())
