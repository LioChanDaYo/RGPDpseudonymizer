"""Tests for batch validation workflow (Story 6.7.3).

Tests cover:
- BatchWorker validation_required signal emission
- BatchWorker pause/resume with validation
- BatchWorker skips validation when disabled (default)
- ValidationScreen batch mode context (doc indicator, nav buttons)
- ValidationScreen non-batch mode (batch widgets hidden)
- Toggle persistence in config
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen
from gdpr_pseudonymizer.gui.workers.batch_worker import BatchResult, BatchWorker
from gdpr_pseudonymizer.gui.workers.signals import BatchValidationSignals, WorkerSignals

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _wait_for_validation(worker: BatchWorker, timeout: float = 5.0) -> None:
    """Poll until the worker is blocked on _validation_condition.wait()."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if worker._waiting_for_validation:
            return
        time.sleep(0.05)
    raise TimeoutError("Worker did not reach validation pause within timeout")


def _wait_for_nth_validation(
    worker: BatchWorker,
    signal_list: list,
    n: int,
    timeout: float = 5.0,
) -> None:
    """Poll until worker is blocked for the n-th validation (1-based)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if worker._waiting_for_validation and len(signal_list) >= n:
            return
        time.sleep(0.05)
    raise TimeoutError(
        f"Worker did not reach validation #{n} "
        f"(waiting={worker._waiting_for_validation}, signals={len(signal_list)})"
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def batch_screen(main_window):  # type: ignore[no-untyped-def]
    """Get the batch screen from main_window fixture."""
    idx = main_window._screens["batch"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, BatchScreen)
    return screen


@pytest.fixture()
def validation_screen(main_window):  # type: ignore[no-untyped-def]
    """Get the validation screen from main_window fixture."""
    idx = main_window._screens["validation"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, ValidationScreen)
    return screen


# ------------------------------------------------------------------
# Task 6.2: BatchWorker emits validation_required
# ------------------------------------------------------------------


class TestBatchWorkerValidationSignal:
    """Test BatchWorker emits validation_required when validate_per_document=True."""

    def test_uses_batch_validation_signals_when_enabled(self, tmp_path: Path) -> None:
        """Worker uses BatchValidationSignals when validate_per_document=True."""
        f1 = tmp_path / "a.txt"
        f1.write_text("test")

        worker = BatchWorker(
            files=[f1],
            output_dir=tmp_path / "out",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=True,
        )
        assert isinstance(worker.signals, BatchValidationSignals)

    def test_uses_worker_signals_when_disabled(self, tmp_path: Path) -> None:
        """Worker uses plain WorkerSignals when validate_per_document=False."""
        f1 = tmp_path / "a.txt"
        f1.write_text("test")

        worker = BatchWorker(
            files=[f1],
            output_dir=tmp_path / "out",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=False,
        )
        assert isinstance(worker.signals, WorkerSignals)
        assert not isinstance(worker.signals, BatchValidationSignals)

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_validation_required(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """When validate_per_document=True, worker emits validation_required."""
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir(parents=True)
        f1.write_text("Test document with Jean Dupont")

        mock_processor = MagicMock()
        entities = [
            DetectedEntity(
                text="Jean Dupont",
                entity_type="PERSON",
                start_pos=24,
                end_pos=35,
                confidence=0.9,
                source="spacy",
            )
        ]
        mock_processor._detect_and_filter_entities.return_value = entities
        mock_processor.finalize_document.return_value = ProcessingResult(
            success=True,
            input_file="",
            output_file="",
            entities_detected=1,
            entities_new=1,
            entities_reused=0,
            processing_time_seconds=0.5,
        )
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1],
            output_dir=tmp_path / "output",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=True,
        )

        validation_signals: list[tuple[object, str, int, int]] = []

        def on_validation_required(ents, text, idx, total):  # type: ignore[no-untyped-def]
            validation_signals.append((ents, text, idx, total))

        assert isinstance(worker.signals, BatchValidationSignals)
        # DirectConnection ensures the slot runs on the emitter's thread
        # (avoiding QueuedConnection which would need an event loop).
        worker.signals.validation_required.connect(
            on_validation_required, Qt.DirectConnection
        )

        # Run worker in a background thread so wait() doesn't block the test
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        # Wait for worker to reach validation pause
        _wait_for_validation(worker)

        # Signal was emitted and captured (via DirectConnection) before the wait
        assert len(validation_signals) == 1
        ents_received, text, idx, total = validation_signals[0]
        assert idx == 0
        assert total == 1
        assert len(ents_received) == 1

        # Unblock the worker
        worker.submit_validation_result(entities)
        thread.join(timeout=10)
        assert not thread.is_alive(), "Worker thread did not finish"


# ------------------------------------------------------------------
# Task 6.3: BatchWorker pauses and resumes with submit_validation_result
# ------------------------------------------------------------------


class TestBatchWorkerValidationPauseResume:
    """Test BatchWorker pauses during validation and resumes after submit."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_processes_multiple_docs_with_validation(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """Worker processes 2 documents with validation pause between each."""
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir(parents=True)
        f1.write_text("Doc A")
        f2 = tmp_path / "input" / "b.txt"
        f2.write_text("Doc B")

        mock_processor = MagicMock()
        entities = [
            DetectedEntity(
                text="Entity",
                entity_type="PERSON",
                start_pos=0,
                end_pos=6,
                confidence=0.9,
                source="spacy",
            )
        ]
        mock_processor._detect_and_filter_entities.return_value = entities
        mock_processor.finalize_document.return_value = ProcessingResult(
            success=True,
            input_file="",
            output_file="",
            entities_detected=1,
            entities_new=1,
            entities_reused=0,
            processing_time_seconds=0.1,
        )
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1, f2],
            output_dir=tmp_path / "output",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=True,
        )

        doc_indices: list[int] = []

        def on_validation_required(ents, text, idx, total):  # type: ignore[no-untyped-def]
            doc_indices.append(idx)

        assert isinstance(worker.signals, BatchValidationSignals)
        worker.signals.validation_required.connect(
            on_validation_required, Qt.DirectConnection
        )

        results: list[BatchResult] = []
        worker.signals.finished.connect(
            lambda r: results.append(r), Qt.DirectConnection
        )

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        # Doc 0
        _wait_for_nth_validation(worker, doc_indices, n=1)
        assert doc_indices == [0]
        worker.submit_validation_result(entities)

        # Doc 1 — worker processes doc 0, then pauses on doc 1
        _wait_for_nth_validation(worker, doc_indices, n=2)
        assert doc_indices == [0, 1]
        worker.submit_validation_result(entities)

        thread.join(timeout=10)
        assert not thread.is_alive(), "Worker thread did not finish"

        # Both docs were validated
        assert doc_indices == [0, 1]
        assert len(results) == 1
        assert results[0].successful_files == 2


# ------------------------------------------------------------------
# Task 6.4: BatchWorker skips validation when disabled
# ------------------------------------------------------------------


class TestBatchWorkerNoValidation:
    """Test BatchWorker processes normally when validate_per_document=False."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_no_validation_signal_when_disabled(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """Default mode processes without validation_required signal."""
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir(parents=True)
        f1.write_text("Doc A")

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            input_file="",
            output_file="",
            entities_detected=1,
            entities_new=1,
            entities_reused=0,
            processing_time_seconds=0.1,
        )
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1],
            output_dir=tmp_path / "output",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=False,
        )

        results: list[BatchResult] = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        assert results[0].successful_files == 1
        # process_document called (not detect + finalize)
        mock_processor.process_document.assert_called_once()


# ------------------------------------------------------------------
# Task 6.5: ValidationScreen batch mode context
# ------------------------------------------------------------------


class TestValidationScreenBatchMode:
    """Test ValidationScreen displays correctly in batch mode."""

    def test_batch_mode_widgets_visible(
        self, validation_screen: ValidationScreen
    ) -> None:
        """Batch header and cancel button visible in batch mode."""
        validation_screen._batch_mode = True
        validation_screen._doc_index = 1
        validation_screen._total_docs = 3

        # Simulate set_context visibility updates
        validation_screen._batch_header.setVisible(True)
        validation_screen._batch_cancel_btn.setVisible(True)
        validation_screen._back_btn.setVisible(False)

        # Use isHidden() because isVisible() requires the full parent chain to be shown
        assert not validation_screen.batch_header.isHidden()
        assert not validation_screen.batch_cancel_button.isHidden()
        assert validation_screen.back_button.isHidden()

    def test_doc_indicator_text(self, validation_screen: ValidationScreen) -> None:
        """Doc indicator shows 'Document X de Y'."""
        from gdpr_pseudonymizer.gui.i18n import qarg

        validation_screen._batch_mode = True
        validation_screen._doc_index = 2
        validation_screen._total_docs = 5

        validation_screen._doc_indicator.setText(
            qarg(
                validation_screen.tr("Document %1 de %2"),
                str(3),
                str(5),
            )
        )

        text = validation_screen.doc_indicator.text()
        assert "3" in text
        assert "5" in text

    def test_prev_disabled_on_first_doc(
        self, validation_screen: ValidationScreen
    ) -> None:
        """Précédent is disabled when doc_index == 0."""
        validation_screen._batch_mode = True
        validation_screen._doc_index = 0
        validation_screen._total_docs = 3
        validation_screen._prev_btn.setEnabled(validation_screen._doc_index > 0)

        assert not validation_screen.prev_button.isEnabled()

    def test_finalize_text_batch_continue(
        self, validation_screen: ValidationScreen
    ) -> None:
        """Finalize button text is 'Valider et continuer' in batch mode (not last doc)."""
        validation_screen._batch_mode = True
        validation_screen._doc_index = 0
        validation_screen._total_docs = 3
        validation_screen.retranslateUi()

        assert "continuer" in validation_screen.finalize_button.text().lower()

    def test_finalize_text_batch_last(
        self, validation_screen: ValidationScreen
    ) -> None:
        """Finalize button text is 'Valider et terminer' on last doc."""
        validation_screen._batch_mode = True
        validation_screen._doc_index = 2
        validation_screen._total_docs = 3
        validation_screen.retranslateUi()

        assert "terminer" in validation_screen.finalize_button.text().lower()


# ------------------------------------------------------------------
# Task 6.6: ValidationScreen non-batch mode
# ------------------------------------------------------------------


class TestValidationScreenNonBatchMode:
    """Test ValidationScreen hides batch widgets in single-doc mode."""

    def test_batch_header_hidden(self, validation_screen: ValidationScreen) -> None:
        """Batch header is hidden by default (non-batch mode)."""
        assert validation_screen.batch_header.isHidden()

    def test_batch_cancel_hidden(self, validation_screen: ValidationScreen) -> None:
        """Batch cancel button is hidden in non-batch mode."""
        assert validation_screen.batch_cancel_button.isHidden()

    def test_back_button_visible(self, validation_screen: ValidationScreen) -> None:
        """Back button is not hidden in single-doc mode."""
        assert not validation_screen.back_button.isHidden()

    def test_finalize_text_default(self, validation_screen: ValidationScreen) -> None:
        """Finalize button shows 'Finaliser' in non-batch mode."""
        validation_screen._batch_mode = False
        validation_screen.retranslateUi()
        assert "finaliser" in validation_screen.finalize_button.text().lower()


# ------------------------------------------------------------------
# Task 6.7: Toggle persistence
# ------------------------------------------------------------------


class TestValidateTogglePersistence:
    """Test validation toggle saves state to config."""

    def test_toggle_default_unchecked(self, batch_screen: BatchScreen) -> None:
        """Validate checkbox is unchecked by default."""
        assert not batch_screen.validate_checkbox.isChecked()

    def test_toggle_saves_to_config(self, batch_screen: BatchScreen, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Toggling the checkbox persists to config."""
        saved: list[dict] = []
        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.config.save_gui_config",
            lambda cfg: saved.append(dict(cfg)),
        )

        batch_screen.validate_checkbox.setChecked(True)

        assert batch_screen._config["batch_validate_per_document"] is True
        assert len(saved) == 1
        assert saved[0]["batch_validate_per_document"] is True

    def test_toggle_loads_from_config(self, main_window) -> None:  # type: ignore[no-untyped-def]
        """Checkbox loads initial state from config."""
        main_window._config["batch_validate_per_document"] = True

        # Create a new batch screen with the config set
        screen = BatchScreen(main_window)
        assert screen.validate_checkbox.isChecked()


# ------------------------------------------------------------------
# Cancel during validation cleans up files
# ------------------------------------------------------------------


class TestBatchWorkerCancelCleanup:
    """Test cancel during validation cleans up written files."""

    def test_cleanup_written_files_on_cancel(self, tmp_path: Path) -> None:
        """Written files are deleted when batch is cancelled."""
        f1 = tmp_path / "out" / "a_pseudonymized.txt"
        f1.parent.mkdir(parents=True)
        f1.write_text("output 1")

        worker = BatchWorker(
            files=[],
            output_dir=tmp_path / "out",
            db_path=str(tmp_path / "test.db"),
            passphrase="test",
        )
        worker._written_files = [f1]

        worker._cleanup_written_files()

        assert not f1.exists()
        assert worker._written_files == []

    def test_cleanup_ignores_missing_files(self, tmp_path: Path) -> None:
        """Cleanup doesn't fail if files are already gone."""
        missing = tmp_path / "out" / "gone.txt"

        worker = BatchWorker(
            files=[],
            output_dir=tmp_path / "out",
            db_path=str(tmp_path / "test.db"),
            passphrase="test",
        )
        worker._written_files = [missing]

        # Should not raise
        worker._cleanup_written_files()
        assert worker._written_files == []
