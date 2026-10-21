"""One form for accented letters, and words that keep their accent marks
(Story 10.20).

Some documents store an accented letter as its plain letter followed by a
separate accent mark (Unicode NFD); on screen it looks the same as the usual
single letter (Unicode NFC). The readers, the typed texts and every
comparison with saved names use the composed form (``composed``), so both
spellings are one text.

A combining mark is not a word character (``\\w``), and NFC cannot join a
mark to a letter that has no composed form (« x » + U+0301). Wherever the
product cuts text into words outside the detector, a word is a run of word
characters and combining marks (``word_pattern``, ``not_after_word``,
``not_before_word``), so a mark never ends a word.

This module imports nothing of the package.
"""

from __future__ import annotations

import functools
import re
import sys
import unicodedata


def composed(text: str) -> str:
    """``text`` in composed form (Unicode NFC). Compatibility forms (NFKC:
    ligatures, full-width letters) are not changed."""
    return unicodedata.normalize("NFC", text)


def is_mark(char: str) -> bool:
    """Whether ``char`` is a combining mark: its canonical combining class is
    not 0 (every accent of French has one)."""
    return unicodedata.combining(char) != 0


def _escaped(code: int) -> str:
    return f"\\u{code:04x}" if code <= 0xFFFF else f"\\U{code:08x}"


@functools.cache
def mark_class() -> str:
    """The body of a regex character class holding every combining mark of
    the running Python's Unicode database (``is_mark``), as escaped ranges.

    Built once, on first use, from the same database as ``\\w``.
    """
    ranges: list[tuple[int, int]] = []
    for code in range(sys.maxunicode + 1):
        if unicodedata.combining(chr(code)):
            if ranges and ranges[-1][1] == code - 1:
                ranges[-1] = (ranges[-1][0], code)
            else:
                ranges.append((code, code))
    return "".join(
        _escaped(start) if start == end else f"{_escaped(start)}-{_escaped(end)}"
        for start, end in ranges
    )


@functools.cache
def word_pattern() -> re.Pattern[str]:
    """A word: a run of word characters and combining marks."""
    return re.compile(f"[\\w{mark_class()}]+")


def not_after_word() -> str:
    """A lookbehind: the character before is neither a word character, a
    combining mark nor a hyphen (-, U+2010, U+2011; a hyphen joins words,
    Story 10.15)."""
    return f"(?<![\\w{mark_class()}\\-‐‑])"


def not_before_word() -> str:
    """A lookahead: the character after is neither a word character, a
    combining mark nor a hyphen (-, U+2010, U+2011)."""
    return f"(?![\\w{mark_class()}\\-‐‑])"
