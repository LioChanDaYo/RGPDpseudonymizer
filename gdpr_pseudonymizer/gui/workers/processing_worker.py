"""Background worker for document pseudonymization.

Runs DocumentProcessor in a QThreadPool thread, emitting progress signals
for each processing phase. Produces a ProcessingResult plus pseudonymized
content and entity type breakdown on success.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRunnable

from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GUIProcessingResult:
    """Extended result for GUI display, wrapping the core ProcessingResult."""

    success: bool
    input_file: str
    output_file: str
    entities_detected: int
    entities_new: int
    entities_reused: int
    processing_time_seconds: float
    pseudonymized_content: str
    entity_type_counts: dict[str, int]
    entity_mappings: list[tuple[str, str]]  # (pseudonym_full, entity_type)
    error_message: str | None = None


class ProcessingWorker(QRunnable):
    """Background worker that runs the pseudonymization pipeline.

    Constructor takes file_path, db_path, passphrase, and optional theme.
    Emits progress signals during the three processing phases.

    On success: emits ``finished`` with a ``GUIProcessingResult``.
    On failure: emits ``error`` with a user-friendly message.
    """

    def __init__(
        self,
        file_path: str,
        db_path: str,
        passphrase: str,
        theme: str = "neutral",
    ) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._file_path = file_path
        self._db_path = db_path
        self._passphrase = passphrase
        self._theme = theme
        self._output_path = ""
        self.setAutoDelete(True)

    @property
    def output_path(self) -> str:
        """Temp output file path (set during run)."""
        return self._output_path

    def run(self) -> None:
        """Execute processing in background thread."""
        try:
            self._run_processing()
        except Exception as e:
            logger.error("processing_worker_unexpected", error=str(e))
            self.signals.error.emit(
                "Une erreur inattendue s'est produite lors du traitement."
            )

    def _run_processing(self) -> None:
        """Internal processing logic with progress emission."""
        from gdpr_pseudonymizer.core.document_processor import (
            DocumentProcessor,
        )
        from gdpr_pseudonymizer.data.database import (
            init_database,
        )
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        # Phase 1: Reading file
        self.signals.progress.emit(5, "Lecture du fichier...")

        # Create mapping database if it doesn't exist yet
        if not Path(self._db_path).exists():
            try:
                self.signals.progress.emit(
                    8, "Création de la base de correspondances..."
                )
                init_database(self._db_path, self._passphrase)
            except ValueError as e:
                error_str = str(e)
                if "12" in error_str or "passphrase" in error_str.lower():
                    self.signals.error.emit(
                        "La phrase secrète doit contenir au moins 12 caractères."
                    )
                else:
                    self.signals.error.emit(error_str)
                return
            except Exception as e:
                logger.error("db_init_failed", error=str(e))
                self.signals.error.emit(
                    "Impossible de créer la base de correspondances."
                )
                return

        # Create temp output file
        suffix = ".txt"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        self._output_path = tmp.name
        tmp.close()

        # Phase 2: Model loading message (emitted before processor init)
        self.signals.progress.emit(
            15,
            "Chargement du modèle linguistique...",
        )

        def _on_notify(msg: str) -> None:
            """Forward core processor messages as progress signals."""
            self.signals.progress.emit(-1, msg)

        # Phase 3: Processing
        self.signals.progress.emit(40, "Détection des entités (NLP)...")

        try:
            processor = DocumentProcessor(
                db_path=self._db_path,
                passphrase=self._passphrase,
                theme=self._theme,
                notifier=_on_notify,
            )
            result = processor.process_document(
                input_path=self._file_path,
                output_path=self._output_path,
                skip_validation=True,
            )
        except FileProcessingError as e:
            error_msg = str(e)
            if "protégé" in error_msg.lower() or "password" in error_msg.lower():
                self.signals.error.emit(
                    "Ce PDF est protégé par mot de passe. "
                    "Veuillez le déverrouiller avant traitement."
                )
            elif "corrompu" in error_msg.lower() or "corrupt" in error_msg.lower():
                self.signals.error.emit(
                    "Impossible de lire ce fichier. Il est peut-être corrompu."
                )
            else:
                self.signals.error.emit(error_msg)
            return
        except Exception as e:
            error_str = str(e)
            if "canary" in error_str.lower() or "passphrase" in error_str.lower():
                self.signals.error.emit(
                    "Phrase secrète incorrecte. Veuillez réessayer."
                )
            else:
                logger.error("processing_failed", error=error_str)
                self.signals.error.emit("Une erreur s'est produite lors du traitement.")
            return

        if not result.success:
            error_msg = result.error_message or "Erreur de traitement inconnue."
            # Map known error patterns to French messages
            if "aucun texte" in error_msg.lower() or "empty" in error_msg.lower():
                self.signals.error.emit(
                    "Le document ne contient aucun texte exploitable."
                )
            else:
                self.signals.error.emit(error_msg)
            return

        self.signals.progress.emit(90, "Finalisation...")

        # Read pseudonymized content
        pseudonymized_content = Path(self._output_path).read_text(encoding="utf-8")

        # Use per-document entity type counts from ProcessingResult (DATA-001 fix)
        entity_type_counts = result.entity_type_counts or {}
        entity_mappings: list[tuple[str, str]] = []

        self.signals.progress.emit(100, "Terminé")

        gui_result = GUIProcessingResult(
            success=True,
            input_file=self._file_path,
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
