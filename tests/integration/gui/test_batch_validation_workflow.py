"""Integration test for batch validation workflow (Story 6.7.3).

Tests the end-to-end signal flow:
  BatchScreen → BatchWorker (threaded) → ValidationScreen → submit → finalize

Uses mock DocumentProcessor with real file I/O.
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
from gdpr_pseudonymizer.gui.workers.signals import BatchValidationSignals

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _wait_for_validation(worker: BatchWorker, timeout: float = 10.0) -> None:
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
    timeout: float = 10.0,
) -> None:
    """Poll until worker is blocked for the n-th validation (1-based)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if worker._waiting_for_validation and len(signal_list) >= n:
            return
        time.sleep(0.05)
    raise TimeoutError(
        f"Did not reach validation #{n} "
        f"(waiting={worker._waiting_for_validation}, signals={len(signal_list)})"
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def batch_screen(integration_window):  # type: ignore[no-untyped-def]
    """Get BatchScreen from the integration window."""
    idx = integration_window._screens["batch"]
    screen = integration_window.stack.widget(idx)
    assert isinstance(screen, BatchScreen)
    integration_window.cached_passphrase = ("test.db", "test_passphrase_12345")
    return screen


@pytest.fixture()
def validation_screen(integration_window):  # type: ignore[no-untyped-def]
    """Get ValidationScreen from the integration window."""
    idx = integration_window._screens["validation"]
    screen = integration_window.stack.widget(idx)
    assert isinstance(screen, ValidationScreen)
    return screen


# ------------------------------------------------------------------
# 7.2: End-to-end 3-document validation workflow
# ------------------------------------------------------------------


class TestBatchValidationEndToEnd:
    """End-to-end: 3 docs → validate each → finalize → all outputs written."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_three_docs_validated_and_finalized(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        # Create 3 input files
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        files = []
        for name in ["a.txt", "b.txt", "c.txt"]:
            f = input_dir / name
            f.write_text(f"Document {name} avec Jean Dupont et Paris.")
            files.append(f)

        entities = [
            DetectedEntity(
                text="Jean Dupont",
                entity_type="PERSON",
                start_pos=15,
                end_pos=26,
                confidence=0.95,
                source="spacy",
            ),
        ]

        mock_processor = MagicMock()
        mock_processor._detect_and_filter_entities.return_value = entities

        # finalize_document creates the output file as a side effect
        def fake_finalize(document_text, validated_entities, output_path):  # type: ignore[no-untyped-def]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(f"Pseudonymized: {document_text[:20]}")
            return ProcessingResult(
                success=True,
                input_file="",
                output_file=output_path,
                entities_detected=1,
                entities_new=1,
                entities_reused=0,
                processing_time_seconds=0.2,
            )

        mock_processor.finalize_document.side_effect = fake_finalize
        mock_dp_cls.return_value = mock_processor

        # Create worker directly with validation enabled
        worker = BatchWorker(
            files=files,
            output_dir=output_dir,
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=True,
        )

        assert isinstance(worker.signals, BatchValidationSignals)

        # Track signals
        doc_indices: list[int] = []
        results: list[BatchResult] = []

        worker.signals.validation_required.connect(
            lambda ents, text, idx, total: doc_indices.append(idx),
            Qt.DirectConnection,
        )
        worker.signals.finished.connect(
            lambda r: results.append(r), Qt.DirectConnection
        )

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        # Validate all 3 documents
        for doc_num in range(1, 4):
            _wait_for_nth_validation(worker, doc_indices, n=doc_num)
            worker.submit_validation_result(entities)

        thread.join(timeout=15)
        assert not thread.is_alive(), "Worker thread did not finish"

        # Verify all 3 docs processed
        assert doc_indices == [0, 1, 2]
        assert len(results) == 1
        batch_result = results[0]
        assert batch_result.successful_files == 3
        assert batch_result.failed_files == 0
        assert batch_result.total_entities == 3

        # Verify output files exist
        for name in ["a", "b", "c"]:
            out_file = output_dir / f"{name}_pseudonymized.txt"
            assert out_file.exists(), f"Output {out_file.name} not found"

        # finalize_document called 3 times
        assert mock_processor.finalize_document.call_count == 3


# ------------------------------------------------------------------
# 7.3: Cancel during validation — cleanup
# ------------------------------------------------------------------


class TestBatchValidationCancelDuringValidation:
    """Cancel during doc 2 validation → doc 1 output cleaned up."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_cancel_cleans_up_written_files(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        files = []
        for name in ["a.txt", "b.txt", "c.txt"]:
            f = input_dir / name
            f.write_text(f"Document {name} avec Marie Martin.")
            files.append(f)

        entities = [
            DetectedEntity(
                text="Marie Martin",
                entity_type="PERSON",
                start_pos=15,
                end_pos=27,
                confidence=0.92,
                source="spacy",
            ),
        ]

        mock_processor = MagicMock()
        mock_processor._detect_and_filter_entities.return_value = entities

        def fake_finalize(document_text, validated_entities, output_path):  # type: ignore[no-untyped-def]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(f"Pseudonymized: {document_text[:20]}")
            return ProcessingResult(
                success=True,
                input_file="",
                output_file=output_path,
                entities_detected=1,
                entities_new=1,
                entities_reused=0,
                processing_time_seconds=0.2,
            )

        mock_processor.finalize_document.side_effect = fake_finalize
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=files,
            output_dir=output_dir,
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            validate_per_document=True,
        )

        assert isinstance(worker.signals, BatchValidationSignals)

        doc_indices: list[int] = []
        results: list[BatchResult] = []

        worker.signals.validation_required.connect(
            lambda ents, text, idx, total: doc_indices.append(idx),
            Qt.DirectConnection,
        )
        worker.signals.finished.connect(
            lambda r: results.append(r), Qt.DirectConnection
        )

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        # Doc 0: validate normally
        _wait_for_nth_validation(worker, doc_indices, n=1)
        worker.submit_validation_result(entities)

        # Doc 1: wait for validation, then CANCEL
        _wait_for_nth_validation(worker, doc_indices, n=2)

        # At this point, doc 0 output should exist (written by finalize)
        doc0_out = output_dir / "a_pseudonymized.txt"
        assert doc0_out.exists(), "Doc 0 output should exist before cancel"

        # Cancel the batch
        worker.cancel()

        thread.join(timeout=15)
        assert not thread.is_alive(), "Worker thread did not finish"

        # Verify cleanup: doc 0 output should be removed
        assert not doc0_out.exists(), "Doc 0 output should be cleaned up after cancel"

        # No partial outputs for doc 1 or doc 2
        assert not (output_dir / "b_pseudonymized.txt").exists()
        assert not (output_dir / "c_pseudonymized.txt").exists()

        # Batch result should reflect cancellation
        assert len(results) == 1
        batch_result = results[0]
        # Only doc 0 was fully processed before cancel
        assert batch_result.successful_files == 1
