"""Processing screen with progress display and entity summary.

Shows file processing progress with three phases, spaCy model download
if needed, entity summary after completion, and navigation to results.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt, QThreadPool
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.accessibility.focus_manager import (
    setup_focus_order_processing,
)
from gdpr_pseudonymizer.gui.i18n import qarg
from gdpr_pseudonymizer.gui.widgets.step_indicator import StepMode
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow
    from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
    from gdpr_pseudonymizer.gui.workers.processing_worker import GUIProcessingResult

logger = get_logger(__name__)


class ProcessingScreen(QWidget):
    """Screen showing document processing progress and entity summary."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._result: GUIProcessingResult | None = None
        self._detection_result: DetectionResult | None = None
        self._file_path = ""
        self._db_path = ""
        self._passphrase = ""
        self._is_processing = False

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # File info header
        self._file_header = QLabel("")
        self._file_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._file_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_header)

        self._file_info = QLabel("")
        self._file_info.setObjectName("secondaryLabel")
        self._file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_info)

        layout.addSpacing(16)

        # Progress area
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        # Accessibility support (AC2 - Task 3.5)
        self._progress_bar.setAccessibleName(self.tr("Progression de l'analyse"))
        self._progress_bar.setAccessibleDescription(
            self.tr(
                "Barre de progression indiquant l'avancement de la détection des entités"
            )
        )
        layout.addWidget(self._progress_bar)

        self._phase_label = QLabel()
        self._phase_label.setObjectName("secondaryLabel")
        self._phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._phase_label)

        self._time_estimate_label = QLabel("")
        self._time_estimate_label.setObjectName("secondaryLabel")
        self._time_estimate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_estimate_label.setStyleSheet("font-size: 11px; font-style: italic;")
        layout.addWidget(self._time_estimate_label)

        layout.addSpacing(16)

        # Entity summary panel (hidden until processing completes)
        self._summary_panel = QWidget()
        summary_layout = QVBoxLayout(self._summary_panel)
        summary_layout.setContentsMargins(16, 16, 16, 16)

        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary_label.setStyleSheet("font-size: 14px;")
        summary_layout.addWidget(self._summary_label)

        self._summary_panel.setVisible(False)
        layout.addWidget(self._summary_panel)

        # Warning panel for zero entities (hidden by default)
        self._warning_panel = QWidget()
        self._warning_panel.setObjectName("warningPanel")
        warning_layout = QVBoxLayout(self._warning_panel)
        warning_layout.setContentsMargins(16, 16, 16, 16)

        self._warning_label = QLabel()
        self._warning_label.setWordWrap(True)
        self._warning_label.setObjectName("warningLabel")
        self._warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_layout.addWidget(self._warning_label)

        self._warning_panel.setVisible(False)
        layout.addWidget(self._warning_panel)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.clicked.connect(self._on_cancel)
        # Accessibility support (AC2 - Task 4.2)
        self._cancel_btn.setAccessibleName(self.tr("Annuler le traitement"))
        self._cancel_btn.setAccessibleDescription(
            self.tr("Annule le traitement en cours et retourne à l'écran d'accueil")
        )
        btn_layout.addWidget(self._cancel_btn)

        self._continue_btn = QPushButton()
        self._continue_btn.clicked.connect(self._on_continue)
        self._continue_btn.setVisible(False)
        # Accessibility support (AC2 - Task 4.2)
        self._continue_btn.setAccessibleName(self.tr("Continuer vers la validation"))
        self._continue_btn.setAccessibleDescription(
            self.tr("Passe à l'étape de validation des entités détectées")
        )
        btn_layout.addWidget(self._continue_btn)

        layout.addLayout(btn_layout)

        # Set all translatable text
        self.retranslateUi()

        # Configure keyboard navigation
        setup_focus_order_processing(self)

    def retranslateUi(self) -> None:
        """Re-set all translatable UI text."""
        self._phase_label.setText(self.tr("En attente..."))
        self._warning_label.setText(
            self.tr(
                "Aucune entité détectée. Le document ne contient peut-être pas "
                "de données personnelles, ou le format n'est pas supporté pour "
                "l'analyse NLP."
            )
        )
        self._cancel_btn.setText(self.tr("Annuler"))
        self._continue_btn.setText(self.tr("Continuer \u25b6"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def start_processing(
        self,
        file_path: str,
        db_path: str,
        passphrase: str,
    ) -> None:
        """Begin processing a document.

        Args:
            file_path: Path to document to process.
            db_path: Path to mapping database.
            passphrase: Database passphrase.
        """
        self._file_path = file_path
        self._db_path = db_path
        self._passphrase = passphrase
        self._result = None
        self._is_processing = True

        # Reset UI
        self._progress_bar.setValue(0)
        self._phase_label.setText(self.tr("Initialisation..."))
        self._summary_panel.setVisible(False)
        self._warning_panel.setVisible(False)
        self._continue_btn.setVisible(False)
        self._cancel_btn.setEnabled(True)

        # File info
        filename = os.path.basename(file_path)
        self._file_header.setText(filename)

        try:
            size_bytes = os.path.getsize(file_path)
            size_str = _format_file_size(size_bytes)
            time_est = max(1, size_bytes // 5000)
            self._file_info.setText(f"{size_str}")
            self._time_estimate_label.setText(
                qarg(self.tr("Temps estimé : ~%1s"), str(time_est))
            )
        except OSError:
            self._file_info.setText("")
            self._time_estimate_label.setText("")

        # Step indicator
        self._main_window.step_indicator.set_mode(StepMode.SINGLE)
        self._main_window.step_indicator.set_step(1)

        # Check spaCy model and start processing
        self._check_model_and_process()

    def _check_model_and_process(self) -> None:
        """Check if spaCy model is installed, download if needed, then process."""
        from gdpr_pseudonymizer.gui.workers.model_manager import ModelManager

        if ModelManager.is_model_installed():
            self._start_processing_worker()
        else:
            self._download_model_then_process()

    def _download_model_then_process(self) -> None:
        """Download spaCy model, then start processing on success."""
        from gdpr_pseudonymizer.gui.workers.model_manager import ModelDownloadWorker

        worker = ModelDownloadWorker()
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_model_downloaded)
        worker.signals.error.connect(self._on_model_download_error)

        QThreadPool.globalInstance().start(worker)

    def _on_model_downloaded(self, _result: object) -> None:
        """Model downloaded successfully — start processing."""
        self._start_processing_worker()

    def _on_model_download_error(self, error_msg: str) -> None:
        """Model download failed — show error and return to home."""
        self._is_processing = False
        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        ConfirmDialog.informational(
            self.tr("Erreur de téléchargement"),
            error_msg,
            parent=self._main_window,
        ).exec()
        self._main_window.navigate_to("home")

    def _start_processing_worker(self) -> None:
        """Launch the detection worker (Phase 1 only)."""
        from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionWorker

        worker = DetectionWorker(
            file_path=self._file_path,
            db_path=self._db_path,
            passphrase=self._passphrase,
        )
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)

        QThreadPool.globalInstance().start(worker)

    def _on_progress(self, percent: int, phase: str) -> None:
        """Update progress bar and phase label."""
        if percent >= 0:
            self._progress_bar.setMaximum(100)
            self._progress_bar.setValue(percent)
        else:
            # Indeterminate
            self._progress_bar.setMaximum(0)
        self._phase_label.setText(phase)

    def _on_finished(self, result: object) -> None:
        """Detection completed successfully."""
        from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult

        if not isinstance(result, DetectionResult):
            return

        self._detection_result = result
        self._is_processing = False

        # Update progress to 100%
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(100)
        self._phase_label.setText(self.tr("Analyse terminée"))
        self._time_estimate_label.setText("")

        # Show entity summary
        n_entities = len(result.detected_entities)
        if n_entities == 0:
            self._warning_panel.setVisible(True)
        else:
            counts = result.entity_type_counts
            persons = counts.get("PERSON", 0)
            locations = counts.get("LOCATION", 0)
            orgs = counts.get("ORG", 0)
            self._summary_label.setText(
                qarg(
                    self.tr(
                        "Nous avons trouvé <b>%1 noms de personnes</b>, "
                        "<b>%2 lieux</b> et "
                        "<b>%3 organisations</b> dans votre document."
                    ),
                    str(persons),
                    str(locations),
                    str(orgs),
                )
            )
            self._summary_panel.setVisible(True)

        # Show continue button
        self._continue_btn.setVisible(True)
        self._cancel_btn.setEnabled(True)

    def _on_error(self, error_msg: str) -> None:
        """Processing failed — show error and return to home."""
        self._is_processing = False
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._phase_label.setText(self.tr("Erreur"))

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        ConfirmDialog.informational(
            self.tr("Erreur de traitement"),
            error_msg,
            parent=self._main_window,
        ).exec()
        self._main_window.navigate_to("home")

    def _on_cancel(self) -> None:
        """Cancel processing and return to home."""
        self._is_processing = False
        self._main_window.navigate_to("home")
        self._main_window.step_indicator.set_step(0)

    def _on_continue(self) -> None:
        """Navigate to validation screen with detection result."""
        if self._detection_result is None:
            return

        # Get the validation screen and start validation
        val_idx = self._main_window._screens.get("validation")
        if val_idx is not None:
            widget = self._main_window.stack.widget(val_idx)
            from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

            if isinstance(widget, ValidationScreen):
                widget.start_validation(self._detection_result)
        self._main_window.navigate_to("validation")

    # -- Test accessors --

    @property
    def progress_bar(self) -> QProgressBar:
        return self._progress_bar

    @property
    def phase_label(self) -> QLabel:
        return self._phase_label

    @property
    def summary_panel(self) -> QWidget:
        return self._summary_panel

    @property
    def summary_label(self) -> QLabel:
        return self._summary_label

    @property
    def warning_panel(self) -> QWidget:
        return self._warning_panel

    @property
    def continue_button(self) -> QPushButton:
        return self._continue_btn

    @property
    def cancel_button(self) -> QPushButton:
        return self._cancel_btn

    @property
    def is_processing(self) -> bool:
        return self._is_processing


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable French format."""
    if size_bytes < 1024:
        return f"{size_bytes} o"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} Ko"
    return f"{size_bytes / (1024 * 1024):.1f} Mo"
