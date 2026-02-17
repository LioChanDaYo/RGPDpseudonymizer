"""Lightweight toast notification widget.

Position: top-right of main window, below step indicator.
Max 2 visible simultaneously. Slide-in from right + fade-out.
Auto-dismiss with configurable duration (default 3s).
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import QLabel, QWidget


class Toast(QLabel):
    """Single toast notification."""

    _active_toasts: ClassVar[list[Toast]] = []
    MAX_VISIBLE = 2

    def __init__(
        self,
        message: str,
        parent: QWidget,
        duration_ms: int = 3000,
    ) -> None:
        super().__init__(message, parent)
        self.setObjectName("toast")
        self.setWordWrap(True)
        self.setFixedWidth(300)
        self.adjustSize()
        self.setMinimumHeight(40)
        self._duration_ms = duration_ms

        # Style
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def show_toast(self) -> None:
        """Display this toast, managing the active toast list."""
        # Evict oldest if at capacity
        while len(Toast._active_toasts) >= self.MAX_VISIBLE:
            old = Toast._active_toasts.pop(0)
            old._dismiss_immediately()

        Toast._active_toasts.append(self)
        self._position_toast()
        self.show()
        self.raise_()

        # Slide in animation
        self._slide_in()

        # Auto-dismiss timer
        QTimer.singleShot(self._duration_ms, self._fade_out)

    def _position_toast(self) -> None:
        """Position toast in top-right, stacked below existing toasts."""
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 16
        x = parent.width() - self.width() - margin
        # Stack below other active toasts
        index = Toast._active_toasts.index(self)
        y = 60 + index * (self.height() + 8)  # below step indicator
        self.move(x, y)

    def _slide_in(self) -> None:
        """Animate slide from right."""
        parent = self.parentWidget()
        if parent is None:
            return
        start_x = parent.width()
        end_x = self.x()
        self.move(start_x, self.y())

        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(300)
        self._anim.setStartValue(self.pos())
        from PySide6.QtCore import QPoint

        self._anim.setEndValue(QPoint(end_x, self.y()))
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _fade_out(self) -> None:
        """Dismiss with fade out."""
        self._dismiss_immediately()

    def _dismiss_immediately(self) -> None:
        """Remove toast without animation."""
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        try:
            self.hide()
            self.deleteLater()
        except RuntimeError:
            pass  # C++ object already deleted

    @classmethod
    def show_message(
        cls,
        message: str,
        parent: QWidget,
        duration_ms: int = 3000,
    ) -> Toast:
        """Convenience factory: create and show a toast."""
        toast = cls(message, parent, duration_ms)
        toast.show_toast()
        return toast

    @classmethod
    def active_count(cls) -> int:
        """Number of currently active toasts."""
        return len(cls._active_toasts)

    @classmethod
    def clear_all(cls) -> None:
        """Dismiss all active toasts."""
        for toast in list(cls._active_toasts):
            toast._dismiss_immediately()
