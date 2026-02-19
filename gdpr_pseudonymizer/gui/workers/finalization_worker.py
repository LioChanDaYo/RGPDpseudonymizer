"""Background worker for document finalization (Phase 2).

Takes validated entities and produces the pseudonymized document.
Runs DocumentProcessor.finalize_document() in a QThreadPool thread.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QRunnable

from gdpr_pseudonymizer.gui.workers.processing_worker import GUIProcessingResult
from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

logger = get_logger(__name__)


class FinalizationWorker(QRunnable):
    """Background worker that finalizes pseudonymization after validation.

    Constructor takes validated entities, document text, and DB credentials.
    Produces a GUIProcessingResult compatible with the ResultsScreen.

    On success: emits ``finished`` with a ``GUIProcessingResult``.
    On failure: emits ``error`` with a user-friendly French message.
    """

    def __init__(
        self,
        validated_entities: list[DetectedEntity],
        document_text: str,
        db_path: str,
        passphrase: str,
        theme: str,
        input_path: str,
    ) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._validated_entities = validated_entities
        self._document_text = document_text
        self._db_path = db_path
        self._passphrase = passphrase
        self._theme = theme
        self._input_path = input_path
        self._cancelled = False
        self._output_path = ""
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cancellation of the worker."""
        self._cancelled = True

    @property
    def output_path(self) -> str:
        """Temp output file path (set during run)."""
        return self._output_path

    def run(self) -> None:
        """Execute finalization in background thread."""
        try:
            self._run_finalization()
        except Exception as e:
            logger.error("finalization_worker_unexpected", error=str(e))
            self.signals.error.emit(
                "Une erreur inattendue s'est produite lors de la finalisation."
            )

    def _run_finalization(self) -> None:
        """Internal finalization logic with progress emission."""
        from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

        self.signals.progress.emit(10, "Résolution des pseudonymes...")

        if self._cancelled:
            return

        # Create temp output file
        suffix = Path(self._input_path).suffix or ".txt"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        self._output_path = tmp.name
        tmp.close()

        self.signals.progress.emit(30, "Application des remplacements...")

        if self._cancelled:
            return

        try:
            processor = DocumentProcessor(
                db_path=self._db_path,
                passphrase=self._passphrase,
                theme=self._theme,
            )
            result = processor.finalize_document(
                document_text=self._document_text,
                validated_entities=self._validated_entities,
                output_path=self._output_path,
            )
        except Exception as e:
            error_str = str(e)
            logger.error("finalization_failed", error=error_str)
            self.signals.error.emit(
                "Une erreur s'est produite lors de la pseudonymisation."
            )
            return

        if not result.success:
            error_msg = result.error_message or "Erreur de finalisation inconnue."
            self.signals.error.emit(error_msg)
            return

        if self._cancelled:
            return

        self.signals.progress.emit(90, "Finalisation...")

        # Read pseudonymized content
        pseudonymized_content = Path(self._output_path).read_text(encoding="utf-8")

        # Count entity types from validated entities (not DB — fixes DATA-001)
        entity_type_counts: dict[str, int] = {}
        entity_mappings: list[tuple[str, str]] = []
        for entity in self._validated_entities:
            t = entity.entity_type
            entity_type_counts[t] = entity_type_counts.get(t, 0) + 1

        self.signals.progress.emit(100, "Terminé")

        gui_result = GUIProcessingResult(
            success=True,
            input_file=self._input_path,
            output_file=self._output_path,
            entities_detected=result.entities_detected,
            entities_new=result.entities_new,
            entities_reused=result.entities_reused,
            processing_time_seconds=result.processing_time_seconds,
            pseudonymized_content=pseudonymized_content,
            entity_type_counts=entity_type_counts,
            entity_mappings=entity_mappings,
        )
        self.signals.finished.emit(gui_result)
