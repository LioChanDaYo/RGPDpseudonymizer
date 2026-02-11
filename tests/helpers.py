"""Shared test helpers.

Common utility functions used across test modules.
"""

from __future__ import annotations

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for reliable string matching.

    Rich adds color codes to output, which can break substring assertions.
    This helper removes those codes so tests can match plain text.
    """
    return _ANSI_RE.sub("", text)
