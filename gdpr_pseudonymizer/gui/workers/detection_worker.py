"""Background worker for NLP entity detection (Phase 1).

Runs DocumentProcessor.detect_entities() + build_pseudonym_previews() in a
QThreadPool thread. Produces a DetectionResult for the validation screen.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QRunnable

from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

logger = get_logger(__name__)


@dataclass
class DetectionResult:
    """Result of NLP detection phase for GUI validation."""

    document_text: str
    detected_entities: list[DetectedEntity]
    pseudonym_previews: dict[str, str]
    entity_type_counts: dict[str, int]
    db_path: str
    passphrase: str
    theme: str
    input_file: str
    detection_time_seconds: float


class DetectionWorker(QRunnable):
    """Background worker that runs NLP detection only (no pseudonymization).

    Constructor takes file_path, db_path, passphrase, and optional theme.
    Emits progress signals during detection phases.

    On success: emits ``finished`` with a ``DetectionResult``.
    On failure: emits ``error`` with a user-friendly French message.
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
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cancellation of the worker."""
        self._cancelled = True

    def run(self) -> None:
        """Execute detection in background thread."""
        try:
            self._run_detection()
        except Exception as e:
            logger.error("detection_worker_unexpected", error=str(e))
            self.signals.error.emit(
                "Une erreur inattendue s'est produite lors de l'analyse."
            )

    def _run_detection(self) -> None:
        """Internal detection logic with progress emission."""
        from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
        from gdpr_pseudonymizer.data.database import init_database
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        start_time = time.time()

        # Phase 1: Reading file (0-10%)
        self.signals.progress.emit(5, "Lecture du fichier...")

        if self._cancelled:
            return

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

        if self._cancelled:
            return

        # Phase 2: NLP detection (10-80%)
        self.signals.progress.emit(15, "Chargement du modèle linguistique...")

        try:
            processor = DocumentProcessor(
                db_path=self._db_path,
                passphrase=self._passphrase,
                theme=self._theme,
            )

            self.signals.progress.emit(40, "Détection des entités (NLP)...")

            if self._cancelled:
                return

            document_text, detected_entities = processor.detect_entities(
                input_path=self._file_path,
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
                logger.error("detection_failed", error=error_str)
                self.signals.error.emit("Une erreur s'est produite lors de l'analyse.")
            return

        if self._cancelled:
            return

        # Phase 3: Build pseudonym previews (80-100%)
        self.signals.progress.emit(85, "Génération des pseudonymes...")

        try:
            pseudonym_previews = processor.build_pseudonym_previews(detected_entities)
        except Exception as e:
            logger.error("preview_generation_failed", error=str(e))
            # Non-fatal: proceed with empty previews
            pseudonym_previews = {}

        if self._cancelled:
            return

        # Count entity types from detection results (not DB — fixes DATA-001)
        entity_type_counts: dict[str, int] = {}
        for entity in detected_entities:
            t = entity.entity_type
            entity_type_counts[t] = entity_type_counts.get(t, 0) + 1

        detection_time = time.time() - start_time

        self.signals.progress.emit(100, "Analyse terminée")

        result = DetectionResult(
            document_text=document_text,
            detected_entities=detected_entities,
            pseudonym_previews=pseudonym_previews,
            entity_type_counts=entity_type_counts,
            db_path=self._db_path,
            passphrase=self._passphrase,
            theme=self._theme,
            input_file=self._file_path,
            detection_time_seconds=detection_time,
        )
        self.signals.finished.emit(result)
