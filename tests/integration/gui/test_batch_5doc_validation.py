"""Integration test for batch validation workflow — 5 documents (AC2).

Tests end-to-end: 5 input files → batch processing with validation →
accept entities per document → verify all outputs and progress counts.
Uses mock DocumentProcessor with real validation state.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
from gdpr_pseudonymizer.gui.workers.batch_worker import BatchResult, BatchWorker
from gdpr_pseudonymizer.gui.workers.signals import BatchValidationSignals

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _wait_for_nth_validation(
    worker: BatchWorker,
    signal_list: list[int],
    n: int,
    timeout: float = 15.0,
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


# ------------------------------------------------------------------
# AC2: 5-document batch validation workflow
# ------------------------------------------------------------------


class TestBatch5DocumentValidation:
    """End-to-end: 5 docs → validate each → finalize → all outputs written."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_five_docs_validated_and_finalized(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        # Create 5 input files with distinct content
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        file_names = ["alpha.txt", "beta.txt", "gamma.txt", "delta.txt", "epsilon.txt"]
        files = []
        for name in file_names:
            f = input_dir / name
            f.write_text(
                f"Document {name} contient Jean Dupont a Paris.",
                encoding="utf-8",
            )
            files.append(f)

        # NB: start_pos/end_pos are synthetic — they don't match actual
        # positions in the generated text because NLP detection is mocked.
        entities = [
            DetectedEntity(
                text="Jean Dupont",
                entity_type="PERSON",
                start_pos=20,
                end_pos=31,
                confidence=0.95,
                source="spacy",
            ),
            DetectedEntity(
                text="Paris",
                entity_type="LOCATION",
                start_pos=45,
                end_pos=50,
                confidence=0.97,
                source="spacy",
            ),
        ]

        mock_processor = MagicMock()
        mock_processor._detect_and_filter_entities.return_value = entities

        def fake_finalize(document_text, validated_entities, output_path):  # type: ignore[no-untyped-def]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(f"Pseudonymized: {document_text[:30]}")
            return ProcessingResult(
                success=True,
                input_file="",
                output_file=output_path,
                entities_detected=2,
                entities_new=2,
                entities_reused=0,
                processing_time_seconds=0.1,
            )

        mock_processor.finalize_document.side_effect = fake_finalize
        mock_dp_cls.return_value = mock_processor

        # Create worker with validation enabled
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
        progress_updates: list[tuple[int, str]] = []

        worker.signals.validation_required.connect(
            lambda ents, text, idx, total: doc_indices.append(idx),
            Qt.DirectConnection,
        )
        worker.signals.finished.connect(
            lambda r: results.append(r), Qt.DirectConnection
        )
        worker.signals.progress.connect(
            lambda pct, msg: progress_updates.append((pct, msg)),
            Qt.DirectConnection,
        )

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        # Validate all 5 documents one by one
        for doc_num in range(1, 6):
            _wait_for_nth_validation(worker, doc_indices, n=doc_num)
            worker.submit_validation_result(entities)

        thread.join(timeout=30)
        assert not thread.is_alive(), "Worker thread did not finish"

        # Verify all 5 docs triggered validation
        assert doc_indices == [0, 1, 2, 3, 4]

        # Verify batch result
        assert len(results) == 1
        batch_result = results[0]
        assert batch_result.successful_files == 5
        assert batch_result.failed_files == 0
        assert batch_result.total_entities == 10  # 2 entities × 5 docs

        # Verify all output files exist
        for name in file_names:
            stem = Path(name).stem
            out_file = output_dir / f"{stem}_pseudonymized.txt"
            assert out_file.exists(), f"Output {out_file.name} not found"

        # finalize_document called 5 times
        assert mock_processor.finalize_document.call_count == 5

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_batch_progress_shows_correct_document_counts(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """AC2 subtask 3.3: progress reports correct doc counts (1/5 through 5/5)."""
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        files = []
        for i in range(5):
            f = input_dir / f"doc{i}.txt"
            f.write_text(f"Document {i} avec Marie Martin.", encoding="utf-8")
            files.append(f)

        entities = [
            DetectedEntity(
                text="Marie Martin",
                entity_type="PERSON",
                start_pos=14,
                end_pos=26,
                confidence=0.92,
                source="spacy",
            ),
        ]

        mock_processor = MagicMock()
        mock_processor._detect_and_filter_entities.return_value = entities

        def fake_finalize(document_text, validated_entities, output_path):  # type: ignore[no-untyped-def]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("Pseudonymized content")
            return ProcessingResult(
                success=True,
                input_file="",
                output_file=output_path,
                entities_detected=1,
                entities_new=1,
                entities_reused=0,
                processing_time_seconds=0.1,
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

        doc_indices: list[int] = []
        total_docs_reported: list[int] = []

        worker.signals.validation_required.connect(
            lambda ents, text, idx, total: (
                doc_indices.append(idx),
                total_docs_reported.append(total),
            ),
            Qt.DirectConnection,
        )

        results: list[BatchResult] = []
        worker.signals.finished.connect(
            lambda r: results.append(r), Qt.DirectConnection
        )

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        for doc_num in range(1, 6):
            _wait_for_nth_validation(worker, doc_indices, n=doc_num)
            worker.submit_validation_result(entities)

        thread.join(timeout=30)
        assert not thread.is_alive()

        # Each validation signal should report total_docs = 5
        assert all(
            t == 5 for t in total_docs_reported
        ), f"Expected total=5 for all, got {total_docs_reported}"

        # Doc indices should be sequential 0..4
        assert doc_indices == [0, 1, 2, 3, 4]

        # All 5 outputs should exist
        for i in range(5):
            assert (output_dir / f"doc{i}_pseudonymized.txt").exists()
