"""Tests for DropZone widget: drag events, file validation, signals."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.gui.widgets.drop_zone import DropZone


class TestDropZoneCreation:
    """Widget creation and properties."""

    def test_creates_widget(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dz = DropZone()
        qtbot.addWidget(dz)
        assert dz.objectName() == "dropZone"

    def test_accepts_drops(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dz = DropZone()
        qtbot.addWidget(dz)
        assert dz.acceptDrops()

    def test_minimum_height(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dz = DropZone()
        qtbot.addWidget(dz)
        assert dz.minimumHeight() == 200


class TestFileValidation:
    """File type validation."""

    @pytest.mark.parametrize("ext", [".txt", ".md", ".pdf", ".docx"])
    def test_supported_extensions(self, ext: str) -> None:
        assert DropZone.is_supported_file(f"test{ext}")

    @pytest.mark.parametrize("ext", [".exe", ".py", ".jpg", ".csv"])
    def test_unsupported_extensions(self, ext: str) -> None:
        assert not DropZone.is_supported_file(f"test{ext}")

    def test_case_insensitive(self) -> None:
        assert DropZone.is_supported_file("test.TXT")
        assert DropZone.is_supported_file("test.Md")

    def test_supported_extensions_set(self) -> None:
        exts = DropZone.supported_extensions()
        assert exts == {".txt", ".md", ".pdf", ".docx"}


class TestClickToBrowse:
    """Click-to-browse functionality."""

    def test_click_triggers_file_dialog(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dz = DropZone()
        qtbot.addWidget(dz)

        with patch.object(dz, "_open_file_dialog") as mock:
            from PySide6.QtCore import QEvent, QPoint, Qt
            from PySide6.QtGui import QMouseEvent

            event = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                QPoint(10, 10),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            dz.mousePressEvent(event)
            mock.assert_called_once()

    def test_file_selected_signal(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dz = DropZone()
        qtbot.addWidget(dz)

        with qtbot.waitSignal(dz.file_selected, timeout=1000) as blocker:
            dz.file_selected.emit("/tmp/test.txt")
        assert blocker.args == ["/tmp/test.txt"]

    def test_multi_file_dropped_signal(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dz = DropZone()
        qtbot.addWidget(dz)

        with qtbot.waitSignal(dz.multi_file_dropped, timeout=1000):
            dz.multi_file_dropped.emit()
