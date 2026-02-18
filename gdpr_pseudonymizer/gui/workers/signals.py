"""Reusable worker signal definitions for QRunnable-based background tasks.

QRunnable cannot inherit from QObject, so workers create a WorkerSignals
instance as an attribute and emit signals through it (bridge pattern).

Signals are emitted from the worker thread and received on the GUI thread
via the Qt event loop — thread-safety is guaranteed by the signal/slot mechanism.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """Reusable signal bridge for QRunnable workers.

    Attributes:
        progress: Emitted during processing with (percent, phase_label).
                  percent=-1 means indeterminate progress.
        finished: Emitted on success with the result object.
        error: Emitted on failure with a user-friendly error message.
    """

    progress = Signal(int, str)
    finished = Signal(object)
    error = Signal(str)
