"""Tests for Toast notification widget."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from gdpr_pseudonymizer.gui.widgets.toast import Toast


@pytest.fixture(autouse=True)
def _clear_toasts() -> None:
    """Ensure clean toast state between tests."""
    Toast.clear_all()


class TestToastCreation:
    """Toast widget creation."""

    def test_creates_toast(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        toast = Toast("Test message", parent)
        qtbot.addWidget(toast)
        assert toast.text() == "Test message"

    def test_toast_object_name(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        parent = QWidget()
        qtbot.addWidget(parent)
        toast = Toast("Test", parent)
        qtbot.addWidget(toast)
        assert toast.objectName() == "toast"


class TestToastDisplay:
    """Toast show/dismiss behavior."""

    def test_show_toast(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()
        _toast = Toast.show_message("Hello", parent)
        assert Toast.active_count() == 1

    def test_max_two_visible(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()
        Toast.show_message("One", parent)
        Toast.show_message("Two", parent)
        Toast.show_message("Three", parent)
        assert Toast.active_count() == 2

    def test_clear_all(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()
        Toast.show_message("A", parent)
        Toast.show_message("B", parent)
        Toast.clear_all()
        assert Toast.active_count() == 0

    def test_configurable_duration(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        toast = Toast("Test", parent, duration_ms=5000)
        assert toast._duration_ms == 5000
