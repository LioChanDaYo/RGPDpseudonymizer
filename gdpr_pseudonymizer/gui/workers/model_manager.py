"""spaCy model detection and background download.

ModelManager checks if the NLP model is installed.
ModelDownloadWorker downloads it in a background thread with progress signals.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRunnable

from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)

SPACY_MODEL = "fr_core_news_lg"


def _is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


class ModelManager:
    """Utility class for spaCy model detection."""

    @staticmethod
    def is_model_installed(model_name: str = SPACY_MODEL) -> bool:
        """Check if a spaCy model is installed.

        In frozen (PyInstaller) bundles the model is pre-bundled — check for
        its directory inside ``sys._MEIPASS``.  In normal Python environments
        fall back to ``spacy.util.is_package()``.

        Args:
            model_name: spaCy model package name.

        Returns:
            True if the model is installed.
        """
        if _is_frozen():
            bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
            return (bundle_dir / model_name / "meta.json").exists()

        try:
            import spacy.util

            return spacy.util.is_package(model_name)
        except Exception:
            return False


class ModelDownloadWorker(QRunnable):
    """Background worker to download a spaCy model via subprocess.

    Emits progress signals during download. On failure, emits an error signal
    with a user-friendly French message.

    In frozen (PyInstaller) bundles, downloading is impossible because
    ``sys.executable`` is the bundled exe, not a Python interpreter. The
    model must be pre-bundled; if it is missing the worker emits an error.
    """

    def __init__(self, model_name: str = SPACY_MODEL) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._model_name = model_name
        self.setAutoDelete(True)

    def run(self) -> None:
        """Execute model download in background thread."""
        if _is_frozen():
            logger.error("spacy_model_missing_in_frozen_bundle", model=self._model_name)
            self.signals.error.emit(
                "Le modèle linguistique n'est pas inclus dans cette "
                "distribution. Veuillez réinstaller l'application."
            )
            return

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
