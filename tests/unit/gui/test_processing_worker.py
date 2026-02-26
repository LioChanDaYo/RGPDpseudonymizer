"""Tests for ProcessingWorker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.gui.workers.processing_worker import (
    GUIProcessingResult,
    ProcessingWorker,
)


@pytest.fixture()
def mock_processor_success(tmp_path):  # type: ignore[no-untyped-def]
    """Mock DocumentProcessor returning a successful result."""
    from gdpr_pseudonymizer.core.document_processor import ProcessingResult

    output_content = "Le texte pseudonymisé de Jean Martin."

    def mock_process(input_path, output_path, skip_validation=False):
        # Write pseudonymized content to output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_content)
        return ProcessingResult(
            success=True,
            input_file=input_path,
            output_file=output_path,
            entities_detected=3,
            entities_new=2,
            entities_reused=1,
            processing_time_seconds=1.5,
        )

    return mock_process


class TestProcessingWorkerSuccess:
    """Test successful processing."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.data.database.open_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_finished_on_success(
        self,
        mock_dp_cls,
        mock_open_db,
        mock_init_db,
        qtbot,
        tmp_path,
        mock_processor_success,
    ):  # type: ignore[no-untyped-def]
        input_file = tmp_path / "test.txt"
        input_file.write_text("Contenu de test avec Jean Dupont.", encoding="utf-8")

        mock_processor = MagicMock()
        mock_processor.process_document = mock_processor_success
        mock_dp_cls.return_value = mock_processor

        mock_session = MagicMock()
        mock_open_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_open_db.return_value.__exit__ = MagicMock(return_value=False)

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        finished_results = []
        worker.signals.finished.connect(lambda r: finished_results.append(r))

        worker.run()

        assert len(finished_results) == 1
        result = finished_results[0]
        assert isinstance(result, GUIProcessingResult)
        assert result.success is True
        assert result.entities_detected == 3

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.data.database.open_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_progress_signals(
        self,
        mock_dp_cls,
        mock_open_db,
        mock_init_db,
        qtbot,
        tmp_path,
        mock_processor_success,
    ):  # type: ignore[no-untyped-def]
        input_file = tmp_path / "test.txt"
        input_file.write_text("Test content.", encoding="utf-8")

        mock_processor = MagicMock()
        mock_processor.process_document = mock_processor_success
        mock_dp_cls.return_value = mock_processor

        mock_session = MagicMock()
        mock_open_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_open_db.return_value.__exit__ = MagicMock(return_value=False)

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        progress_phases = []
        worker.signals.progress.connect(lambda p, m: progress_phases.append(m))

        worker.run()

        assert len(progress_phases) >= 4
        assert any("Lecture" in p for p in progress_phases)
        assert any("base" in p.lower() for p in progress_phases)
        assert any("modèle" in p.lower() for p in progress_phases)
        assert any("Détection" in p or "entités" in p.lower() for p in progress_phases)


class TestProcessingWorkerEntityCounts:
    """Test DATA-001 fix: per-document entity type counts from ProcessingResult."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_entity_type_counts_come_from_result_not_db(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """Verify entity_type_counts in GUIProcessingResult come from ProcessingResult,
        not from a separate DB query (DATA-001 fix)."""
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        input_file = tmp_path / "test.txt"
        input_file.write_text("Marie Dubois habite à Paris.", encoding="utf-8")

        expected_counts = {"PERSON": 1, "LOCATION": 1}
        output_content = "Leia Organa habite à Coruscant."

        def mock_process(input_path, output_path, skip_validation=False):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_content)
            return ProcessingResult(
                success=True,
                input_file=input_path,
                output_file=output_path,
                entities_detected=2,
                entities_new=2,
                entities_reused=0,
                processing_time_seconds=0.5,
                entity_type_counts=expected_counts,
            )

        mock_processor = MagicMock()
        mock_processor.process_document = mock_process
        mock_dp_cls.return_value = mock_processor

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        finished_results = []
        worker.signals.finished.connect(lambda r: finished_results.append(r))

        worker.run()

        assert len(finished_results) == 1
        result = finished_results[0]
        assert isinstance(result, GUIProcessingResult)
        assert result.entity_type_counts == expected_counts
        assert result.entity_type_counts.get("PERSON") == 1
        assert result.entity_type_counts.get("LOCATION") == 1

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_entity_type_counts_none_fallback(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """Verify graceful fallback when entity_type_counts is None (CLI path)."""
        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        input_file = tmp_path / "test.txt"
        input_file.write_text("Some text.", encoding="utf-8")

        def mock_process(input_path, output_path, skip_validation=False):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("output")
            return ProcessingResult(
                success=True,
                input_file=input_path,
                output_file=output_path,
                entities_detected=0,
                entities_new=0,
                entities_reused=0,
                processing_time_seconds=0.1,
                # entity_type_counts not set => None
            )

        mock_processor = MagicMock()
        mock_processor.process_document = mock_process
        mock_dp_cls.return_value = mock_processor

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        finished_results = []
        worker.signals.finished.connect(lambda r: finished_results.append(r))

        worker.run()

        assert len(finished_results) == 1
        result = finished_results[0]
        assert result.entity_type_counts == {}


class TestProcessingWorkerFailure:
    """Test processing failure scenarios."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_error_on_processing_failure(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        input_file = tmp_path / "test.txt"
        input_file.write_text("Test content.", encoding="utf-8")

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = ProcessingResult(
            success=False,
            input_file=str(input_file),
            output_file="",
            entities_detected=0,
            entities_new=0,
            entities_reused=0,
            processing_time_seconds=0.1,
            error_message="Test error",
        )
        mock_dp_cls.return_value = mock_processor

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        error_results = []
        worker.signals.error.connect(lambda msg: error_results.append(msg))

        worker.run()

        assert len(error_results) == 1

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_emits_error_on_exception(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        input_file = tmp_path / "test.txt"
        input_file.write_text("Test content.", encoding="utf-8")

        mock_dp_cls.side_effect = Exception("Unexpected error")

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        error_results = []
        worker.signals.error.connect(lambda msg: error_results.append(msg))

        worker.run()

        assert len(error_results) == 1

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_handles_file_processing_error(
        self, mock_dp_cls, mock_init_db, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        input_file = tmp_path / "test.txt"
        input_file.write_text("Test content.", encoding="utf-8")

        from gdpr_pseudonymizer.exceptions import FileProcessingError

        mock_dp_cls.return_value.process_document.side_effect = FileProcessingError(
            "File is corrupt"
        )

        worker = ProcessingWorker(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="test_pass",
        )

        error_results = []
        worker.signals.error.connect(lambda msg: error_results.append(msg))

        worker.run()

        assert len(error_results) == 1
