"""Linear workflow step indicator widget.

Custom QWidget with paintEvent() override showing 4-step progress.
Single-doc: Sélection -> Analyse -> Validation -> Résultat
Batch:      Sélection -> Traitement -> Validation -> Résumé
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class StepState(Enum):
    """State of an individual step."""

    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"


class StepMode(Enum):
    """Workflow mode."""

    SINGLE = "single"
    BATCH = "batch"


SINGLE_STEPS = ["Sélection", "Analyse", "Validation", "Résultat"]
BATCH_STEPS = ["Sélection", "Traitement", "Validation", "Résumé"]


class StepIndicator(QWidget):
    """Horizontal step indicator bar."""

    CIRCLE_RADIUS = 14
    LINE_HEIGHT = 2
    STEP_SPACING = 40

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stepIndicator")
        self.setFixedHeight(56)

        self._mode = StepMode.SINGLE
        self._current_step = 0  # 0-indexed

        # Accessibility support (AC2 - Task 3.3)
        self.setAccessibleName(self.tr("Indicateur de progression"))
        self._update_accessible_text()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_mode(self, mode: StepMode) -> None:
        """Switch between single-doc and batch modes."""
        self._mode = mode
        self._current_step = 0
        self._update_accessible_text()
        self.update()

    def set_step(self, index: int) -> None:
        """Set the active step (0-indexed)."""
        steps = self._steps()
        self._current_step = max(0, min(index, len(steps) - 1))
        self._update_accessible_text()
        self.update()

    def current_step(self) -> int:
        """Return current step index."""
        return self._current_step

    def mode(self) -> StepMode:
        """Return current mode."""
        return self._mode

    def step_count(self) -> int:
        """Return number of steps in current mode."""
        return len(self._steps())

    def step_state(self, index: int) -> StepState:
        """Return the state of a given step."""
        if index < self._current_step:
            return StepState.COMPLETED
        if index == self._current_step:
            return StepState.ACTIVE
        return StepState.UPCOMING

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        steps = self._steps()
        n = len(steps)
        w = self.width()
        h = self.height()
        y_center = h // 2

        # Calculate positions
        total_width = w - 80
        if n <= 1:
            positions = [w // 2]
        else:
            spacing = total_width / (n - 1)
            positions = [int(40 + i * spacing) for i in range(n)]

        # Draw connecting lines
        for i in range(n - 1):
            x1 = positions[i] + self.CIRCLE_RADIUS + 4
            x2 = positions[i + 1] - self.CIRCLE_RADIUS - 4
            if i < self._current_step:
                pen = QPen(QColor("#1565C0"), self.LINE_HEIGHT)
            else:
                pen = QPen(QColor("#E0E0E0"), self.LINE_HEIGHT)
            painter.setPen(pen)
            painter.drawLine(x1, y_center - 4, x2, y_center - 4)

        # Draw steps
        for i, label in enumerate(steps):
            x = positions[i]
            state = self.step_state(i)
            self._draw_step(painter, x, y_center, label, state)

        painter.end()

    def _draw_step(
        self,
        painter: QPainter,
        x: int,
        y: int,
        label: str,
        state: StepState,
    ) -> None:
        r = self.CIRCLE_RADIUS
        cy = y - 4  # circle vertical center

        if state == StepState.COMPLETED:
            # Filled circle with checkmark
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#1565C0"))
            painter.drawEllipse(x - r, cy - r, r * 2, r * 2)
            # Checkmark
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.drawLine(x - 5, cy, x - 1, cy + 4)
            painter.drawLine(x - 1, cy + 4, x + 6, cy - 4)
            # Label
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#1565C0"))

        elif state == StepState.ACTIVE:
            # Filled accent circle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#1565C0"))
            painter.drawEllipse(x - r, cy - r, r * 2, r * 2)
            # Step number
            painter.setPen(QColor("#FFFFFF"))
            num_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(num_font)
            painter.drawText(
                QRect(x - r, cy - r, r * 2, r * 2),
                Qt.AlignmentFlag.AlignCenter,
                str(self._steps().index(label) + 1),
            )
            # Label
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#1565C0"))

        else:
            # Empty circle
            painter.setPen(QPen(QColor("#E0E0E0"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(x - r, cy - r, r * 2, r * 2)
            # Step number
            num_font = QFont("Segoe UI", 9)
            painter.setFont(num_font)
            painter.setPen(QColor("#9E9E9E"))
            painter.drawText(
                QRect(x - r, cy - r, r * 2, r * 2),
                Qt.AlignmentFlag.AlignCenter,
                str(self._steps().index(label) + 1),
            )
            # Label
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            painter.setPen(QColor("#9E9E9E"))

        # Draw label below circle
        text_rect = QRect(x - 60, cy + r + 4, 120, 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.update()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_accessible_text(self) -> None:
        """Update accessible description for screen readers (AC2 - Task 3.3)."""
        steps = self._steps()
        if 0 <= self._current_step < len(steps):
            current_label = steps[self._current_step]
            accessible_desc = self.tr("Étape {step} sur {total}: {label}").format(
                step=self._current_step + 1, total=len(steps), label=current_label
            )
            self.setAccessibleDescription(accessible_desc)

    def _steps(self) -> list[str]:
        if self._mode == StepMode.BATCH:
            return [
                self.tr("S\u00e9lection"),
                self.tr("Traitement"),
                self.tr("Validation"),
                self.tr("R\u00e9sum\u00e9"),
            ]
        return [
            self.tr("S\u00e9lection"),
            self.tr("Analyse"),
            self.tr("Validation"),
            self.tr("R\u00e9sultat"),
        ]
