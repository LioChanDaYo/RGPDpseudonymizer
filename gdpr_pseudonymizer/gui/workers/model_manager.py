"""spaCy model detection and background download.

ModelManager checks if the NLP model is installed.
ModelDownloadWorker downloads it in a background thread with progress signals.
"""

from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import QRunnable

from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)

SPACY_MODEL = "fr_core_news_lg"


class ModelManager:
    """Utility class for spaCy model detection."""

    @staticmethod
    def is_model_installed(model_name: str = SPACY_MODEL) -> bool:
        """Check if a spaCy model is installed.

        Args:
            model_name: spaCy model package name.

        Returns:
            True if the model is installed.
        """
        try:
            import spacy.util

            return spacy.util.is_package(model_name)
        except Exception:
            return False


class ModelDownloadWorker(QRunnable):
    """Background worker to download a spaCy model via subprocess.

    Emits progress signals during download. On failure, emits an error signal
    with a user-friendly French message.
    """

    def __init__(self, model_name: str = SPACY_MODEL) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._model_name = model_name
        self.setAutoDelete(True)

    def run(self) -> None:
        """Execute model download in background thread."""
        self.signals.progress.emit(
            -1,
            "Première utilisation : téléchargement du modèle "
            "linguistique (541 Mo) \u2014 ce téléchargement "
            "n'a lieu qu'une seule fois",
        )

        try:
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", self._model_name],
                capture_output=True,
                text=True,
                timeout=600,  # 10 min timeout
            )

            if result.returncode == 0:
                logger.info("spacy_model_downloaded", model=self._model_name)
                self.signals.finished.emit(True)
            else:
                logger.error(
                    "spacy_model_download_failed",
                    returncode=result.returncode,
                    stderr=result.stderr[:500] if result.stderr else "",
                )
                self.signals.error.emit(
                    "Le modèle linguistique n'a pas pu être téléchargé. "
                    "Vérifiez votre connexion internet."
                )
        except subprocess.TimeoutExpired:
            logger.error("spacy_model_download_timeout", model=self._model_name)
            self.signals.error.emit(
                "Le téléchargement du modèle a expiré. "
                "Vérifiez votre connexion internet et réessayez."
            )
        except Exception as e:
            logger.error("spacy_model_download_error", error=str(e))
            self.signals.error.emit(
                "Le modèle linguistique n'a pas pu être téléchargé. "
                "Vérifiez votre connexion internet."
            )
