"""Tests for BatchWorker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from gdpr_pseudonymizer.gui.workers.batch_worker import (
    BatchResult,
    BatchWorker,
    collect_files,
)


class TestCollectFiles:
    """Tests for the collect_files utility."""

    def test_collects_supported_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.pdf").write_bytes(b"c")
        (tmp_path / "d.docx").write_bytes(b"d")
        (tmp_path / "e.csv").write_text("e")

        files = collect_files(tmp_path)
        names = {f.name for f in files}
        assert names == {"a.txt", "b.md", "c.pdf", "d.docx"}

    def test_excludes_pseudonymized(self, tmp_path: Path) -> None:
        (tmp_path / "doc.txt").write_text("content")
        (tmp_path / "doc_pseudonymized.txt").write_text("content")

        files = collect_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "doc.txt"

    def test_empty_directory(self, tmp_path: Path) -> None:
        files = collect_files(tmp_path)
        assert files == []

    def test_single_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        files = collect_files(f)
        assert len(files) == 1

    def test_recursive(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("a")
        (sub / "b.txt").write_text("b")

        files_flat = collect_files(tmp_path, recursive=False)
        files_recursive = collect_files(tmp_path, recursive=True)

        assert len(files_flat) == 1
        assert len(files_recursive) == 2


class TestBatchWorkerSuccess:
    """Test batch worker with successful processing."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_finished_with_batch_result(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        # Create test files
        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir()
        f1.write_text("Document A")
        f2 = tmp_path / "input" / "b.txt"
        f2.write_text("Document B")

        output_dir = tmp_path / "output"

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            input_file="",
            output_file="",
            entities_detected=5,
            entities_new=3,
            entities_reused=2,
            processing_time_seconds=1.0,
        )
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1, f2],
            output_dir=output_dir,
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
        )

        results = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        batch = results[0]
        assert isinstance(batch, BatchResult)
        assert batch.total_files == 2
        assert batch.successful_files == 2
        assert batch.failed_files == 0
        assert batch.total_entities == 10
        assert batch.new_entities == 6

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_progress_for_each_doc(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir()
        f1.write_text("A")

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = ProcessingResult(
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
        )

        progress_msgs: list[str] = []
        worker.signals.progress.connect(lambda p, m: progress_msgs.append(m))

        worker.run()

        assert any("DOC_DONE:" in m for m in progress_msgs)


class TestBatchWorkerFailure:
    """Test error handling."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_continue_on_error(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir()
        f1.write_text("A")
        f2 = tmp_path / "input" / "b.txt"
        f2.write_text("B")

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("File error")
            return ProcessingResult(
                success=True,
                input_file="",
                output_file="",
                entities_detected=1,
                entities_new=1,
                entities_reused=0,
                processing_time_seconds=0.1,
            )

        mock_processor.process_document.side_effect = side_effect
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1, f2],
            output_dir=tmp_path / "output",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            continue_on_error=True,
        )

        results = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        batch = results[0]
        assert batch.failed_files == 1
        assert batch.successful_files == 1

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_stop_on_error(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir()
        f1.write_text("A")
        f2 = tmp_path / "input" / "b.txt"
        f2.write_text("B")

        mock_processor = MagicMock()
        mock_processor.process_document.side_effect = Exception("Fatal")
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1, f2],
            output_dir=tmp_path / "output",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
            continue_on_error=False,
        )

        results = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        batch = results[0]
        assert batch.failed_files == 1
        # Second file not processed because stop-on-error
        assert batch.successful_files == 0


class TestBatchWorkerPauseCancel:
    """Test pause and cancel flags."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_cancel_stops_processing(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "input" / "a.txt"
        f1.parent.mkdir()
        f1.write_text("A")
        f2 = tmp_path / "input" / "b.txt"
        f2.write_text("B")

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()

        def side_effect(*args, **kwargs):
            # Cancel after first doc
            worker.cancel()
            return ProcessingResult(
                success=True,
                input_file="",
                output_file="",
                entities_detected=1,
                entities_new=1,
                entities_reused=0,
                processing_time_seconds=0.1,
            )

        mock_processor.process_document.side_effect = side_effect
        mock_dp_cls.return_value = mock_processor

        worker = BatchWorker(
            files=[f1, f2],
            output_dir=tmp_path / "output",
            db_path=str(tmp_path / "test.db"),
            passphrase="test_passphrase_12345",
        )

        results = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        batch = results[0]
        # Only first doc processed before cancel took effect
        assert batch.successful_files == 1
        assert len(batch.per_document_results) == 1
