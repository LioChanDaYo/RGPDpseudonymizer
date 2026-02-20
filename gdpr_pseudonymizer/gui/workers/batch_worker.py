"""Background worker for batch document processing.

Processes multiple documents sequentially in a QThreadPool thread.
Emits progress signals for each document and supports pause/cancel.
Supports per-document and global validation modes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QMutex, QRunnable, QWaitCondition

from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)

# Same as CLI
SUPPORTED_EXTENSIONS = [".txt", ".md", ".pdf", ".docx"]


@dataclass
class BatchResult:
    """Result of batch processing (mirrors CLI BatchResult)."""

    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_entities: int = 0
    new_entities: int = 0
    reused_entities: int = 0
    total_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    per_document_results: list[DocumentResult] = field(default_factory=list)


@dataclass
class DocumentResult:
    """Per-document result emitted via document_completed signal."""

    index: int
    filename: str
    success: bool
    entities_detected: int = 0
    entities_new: int = 0
    entities_reused: int = 0
    processing_time: float = 0.0
    error_message: str = ""


def collect_files(input_path: Path, recursive: bool = False) -> list[Path]:
    """Collect supported files from a path, excluding pseudonymized outputs.

    Args:
        input_path: Directory or file path.
        recursive: Search subdirectories.

    Returns:
        Sorted list of supported file paths.
    """
    files: list[Path] = []

    if input_path.is_file():
        if (
            input_path.suffix.lower() in SUPPORTED_EXTENSIONS
            and "_pseudonymized" not in input_path.stem
        ):
            files.append(input_path)
    elif input_path.is_dir():
        pattern = "**/*" if recursive else "*"
        for ext in SUPPORTED_EXTENSIONS:
            for file_path in input_path.glob(f"{pattern}{ext}"):
                if "_pseudonymized" not in file_path.stem:
                    files.append(file_path)

    return sorted(files)


class BatchWorker(QRunnable):
    """Background worker for sequential batch document processing.

    Processes each document using DocumentProcessor, emitting progress signals.
    Supports pause, cancel, and continue-on-error modes.
    """

    def __init__(
        self,
        files: list[Path],
        output_dir: Path,
        db_path: str,
        passphrase: str,
        theme: str = "neutral",
        continue_on_error: bool = True,
        validation_mode: str = "per_document",
    ) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._files = files
        self._output_dir = output_dir
        self._db_path = db_path
        self._passphrase = passphrase
        self._theme = theme
        self._continue_on_error = continue_on_error
        self._validation_mode = validation_mode

        self._cancelled = False
        self._paused = False
        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()

        self.setAutoDelete(True)

    def pause(self) -> None:
        """Pause processing after current document finishes."""
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()

    def resume(self) -> None:
        """Resume paused processing."""
        self._mutex.lock()
        self._paused = False
        self._mutex.unlock()
        self._pause_condition.wakeAll()

    def cancel(self) -> None:
        """Cancel processing after current document finishes."""
        self._cancelled = True
        # Also wake from pause so cancel takes effect
        self.resume()

    def run(self) -> None:
        """Execute batch processing in background thread."""
        try:
            self._run_batch()
        except Exception as e:
            logger.error("batch_worker_unexpected", error=str(e))
            self.signals.error.emit(
                "Une erreur inattendue s'est produite lors du traitement par lot."
            )

    def _run_batch(self) -> None:
        """Internal batch processing loop."""
        from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
        from gdpr_pseudonymizer.data.database import init_database
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        batch_result = BatchResult(total_files=len(self._files))
        start_time = time.time()

        # Ensure output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Init DB if needed
        if not Path(self._db_path).exists():
            try:
                self.signals.progress.emit(
                    0, "Création de la base de correspondances..."
                )
                init_database(self._db_path, self._passphrase)
            except Exception as e:
                self.signals.error.emit(
                    f"Impossible de créer la base de correspondances : {e}"
                )
                return

        # Create processor
        self.signals.progress.emit(0, "Chargement du modèle linguistique...")
        try:
            processor = DocumentProcessor(
                db_path=self._db_path,
                passphrase=self._passphrase,
                theme=self._theme,
            )
        except Exception as e:
            error_str = str(e)
            if "canary" in error_str.lower() or "passphrase" in error_str.lower():
                self.signals.error.emit(
                    "Phrase secrète incorrecte. Veuillez réessayer."
                )
            else:
                logger.error("batch_processor_init_failed", error=error_str)
                self.signals.error.emit(
                    "Impossible d'initialiser le processeur de documents."
                )
            return

        for idx, file_path in enumerate(self._files):
            if self._cancelled:
                break

            # Check pause
            self._mutex.lock()
            while self._paused and not self._cancelled:
                self._pause_condition.wait(self._mutex)
            self._mutex.unlock()

            if self._cancelled:
                break

            doc_start = time.time()
            filename = file_path.name
            percent = int((idx / len(self._files)) * 100)
            self.signals.progress.emit(percent, filename)

            # Build output path
            out_suffix = file_path.suffix
            if file_path.suffix.lower() in [".pdf", ".docx"]:
                out_suffix = ".txt"
            output_file = (
                self._output_dir / f"{file_path.stem}_pseudonymized{out_suffix}"
            )

            doc_result = DocumentResult(index=idx, filename=filename, success=False)

            try:
                result = processor.process_document(
                    input_path=str(file_path),
                    output_path=str(output_file),
                    skip_validation=True,
                )

                doc_time = time.time() - doc_start

                if result.success:
                    doc_result.success = True
                    doc_result.entities_detected = result.entities_detected
                    doc_result.entities_new = result.entities_new
                    doc_result.entities_reused = result.entities_reused
                    doc_result.processing_time = doc_time

                    batch_result.successful_files += 1
                    batch_result.total_entities += result.entities_detected
                    batch_result.new_entities += result.entities_new
                    batch_result.reused_entities += result.entities_reused
                else:
                    doc_result.error_message = result.error_message or "Erreur inconnue"
                    batch_result.failed_files += 1
                    batch_result.errors.append(
                        f"{filename}: {doc_result.error_message}"
                    )

            except FileProcessingError as e:
                doc_time = time.time() - doc_start
                doc_result.error_message = str(e)
                doc_result.processing_time = doc_time
                batch_result.failed_files += 1
                batch_result.errors.append(f"{filename}: {e}")
                logger.error("batch_file_error", file=str(file_path), error=str(e))

            except Exception as e:
                doc_time = time.time() - doc_start
                doc_result.error_message = str(e)
                doc_result.processing_time = doc_time
                batch_result.failed_files += 1
                batch_result.errors.append(f"{filename}: {e}")
                logger.error("batch_file_error", file=str(file_path), error=str(e))

            batch_result.per_document_results.append(doc_result)

            # Emit progress with document info encoded in the message
            done = idx + 1
            total_percent = int((done / len(self._files)) * 100)
            self.signals.progress.emit(total_percent, f"DOC_DONE:{idx}")

            if not doc_result.success and not self._continue_on_error:
                break

        batch_result.total_time_seconds = time.time() - start_time
        self.signals.finished.emit(batch_result)
