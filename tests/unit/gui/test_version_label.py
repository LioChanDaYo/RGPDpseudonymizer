"""Story 11.4: the desktop app shows the installed version (T8-T10).

Written by the BMAD dev agent (Claude). The splash screen, « À propos » and
the application's version showed a hardcoded "2.0.0" whatever the installed
version. The package version is read with ``importlib.metadata``, replaced
here by the invented "9.8.7" (or by a missing package), so no test depends on
the version installed in the environment.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``).
"""

from __future__ import annotations

import importlib.metadata
from typing import Any

import pytest

_VERSION = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 11.4 tests first: version label",
)

FAKE = "9.8.7"
PACKAGE = "gdpr-pseudonymizer"


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test with "PRE: ..." (``pytest.fail``
    raises ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _fake_version(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``importlib.metadata.version`` gives ``value`` for the package, or
    raises ``PackageNotFoundError`` when ``value`` is None; any other name
    gets the real answer."""
    real = importlib.metadata.version

    def fake(name: str) -> str:
        if name == PACKAGE:
            if value is None:
                raise importlib.metadata.PackageNotFoundError(name)
            return value
        return real(name)

    monkeypatch.setattr(importlib.metadata, "version", fake)


@_VERSION
@pytest.mark.parametrize(
    "value,shown", [(FAKE, FAKE), (None, "?")], ids=["metadata", "fallback"]
)
def test_about_shows_package_version(main_window, monkeypatch, value, shown):  # type: ignore[no-untyped-def]
    """T8 (AC7): « À propos » shows the package version, or "?"."""
    from PySide6.QtWidgets import QMessageBox

    _fake_version(monkeypatch, value)
    texts: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "about",
        staticmethod(lambda parent, title, text: texts.append(str(text))),
    )
    main_window._show_about()
    pre(len(texts) == 1, f"« À propos » shown once: {texts}")
    assert f"<p>Version {shown}</p>" in texts[0]  # expected failure


@_VERSION
def test_splash_shows_package_version(qapp, monkeypatch):  # type: ignore[no-untyped-def]
    """T9 (AC7): the splash screen shows the package version."""
    from PySide6 import QtGui

    from gdpr_pseudonymizer.gui import app as app_module

    _fake_version(monkeypatch, FAKE)
    drawn: list[str] = []

    class _SpyPainter(QtGui.QPainter):
        def drawText(self, *args: Any) -> Any:  # type: ignore[override]  # noqa: N802
            drawn.extend(a for a in args if isinstance(a, str))
            return super().drawText(*args)

    monkeypatch.setattr(QtGui, "QPainter", _SpyPainter)
    app_module._create_splash_pixmap()
    pre("GDPR Pseudonymizer" in drawn, f"the splash drawn through the spy: {drawn}")
    assert f"v{FAKE}" in drawn  # expected failure


@_VERSION
def test_application_version(monkeypatch):  # type: ignore[no-untyped-def]
    """T10 (AC7): the application's version is the package version."""
    from PySide6 import QtWidgets

    import gdpr_pseudonymizer.utils.logger as logger_module
    from gdpr_pseudonymizer.gui import app as app_module

    _fake_version(monkeypatch, FAKE)
    seen: list[str] = []

    class _StopError(Exception):
        pass

    class _FakeApp:
        def __init__(self, argv: Any) -> None:
            pass

        def setApplicationName(self, name: str) -> None:  # noqa: N802
            pass

        def setApplicationVersion(self, version: str) -> None:  # noqa: N802
            seen.append(version)
            raise _StopError

    # A context, so that pytest-qt's teardown sees the real QApplication.
    with monkeypatch.context() as m:
        m.setattr(QtWidgets, "QApplication", _FakeApp)
        m.setattr(logger_module, "configure_logging", lambda *a, **k: None)
        with pytest.raises(_StopError):
            app_module.main()
    assert seen == [FAKE]  # expected failure
