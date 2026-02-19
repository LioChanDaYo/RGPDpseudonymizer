"""Tests for DetectionWorker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


@pytest.fixture()
def mock_entities() -> list[DetectedEntity]:
    return [
        DetectedEntity(
            text="Jean Dupont",
            entity_type="PERSON",
            start_pos=0,
            end_pos=11,
            confidence=0.95,
            source="spacy",
        ),
        DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=20,
            end_pos=25,
            confidence=0.98,
            source="spacy",
        ),
    ]


class TestDetectionWorkerSuccess:
    """Test successful detection flow."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.build_pseudonym_previews"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.detect_entities"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.__init__",
        return_value=None,
    )
    def test_worker_emits_finished(
        self,
        mock_init: MagicMock,
        mock_detect: MagicMock,
        mock_previews: MagicMock,
        mock_init_db: MagicMock,
        qtbot,  # type: ignore[no-untyped-def]
        mock_entities: list[DetectedEntity],
        tmp_path: object,
    ) -> None:
        mock_detect.return_value = (
            "Le contrat avec Jean Dupont à Paris.",
            mock_entities,
        )
        mock_previews.return_value = {
            "Jean Dupont_0": "Pierre Lambert",
            "Paris_20": "Lyon",
        }

        db_path = str(tmp_path) + "/test.db"  # type: ignore[operator]
        worker = DetectionWorker(
            file_path="test.txt",
            db_path=db_path,
            passphrase="test_passphrase_ok",
        )

        results: list[object] = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, DetectionResult)
        assert len(result.detected_entities) == 2
        assert result.entity_type_counts == {"PERSON": 1, "LOCATION": 1}

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.build_pseudonym_previews"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.detect_entities"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.__init__",
        return_value=None,
    )
    def test_worker_emits_progress(
        self,
        mock_init: MagicMock,
        mock_detect: MagicMock,
        mock_previews: MagicMock,
        mock_init_db: MagicMock,
        qtbot,  # type: ignore[no-untyped-def]
        mock_entities: list[DetectedEntity],
        tmp_path: object,
    ) -> None:
        mock_detect.return_value = ("text", mock_entities)
        mock_previews.return_value = {}

        db_path = str(tmp_path) + "/test.db"  # type: ignore[operator]
        worker = DetectionWorker(
            file_path="test.txt",
            db_path=db_path,
            passphrase="test_passphrase_ok",
        )

        progress_signals: list[tuple[int, str]] = []
        worker.signals.progress.connect(lambda p, s: progress_signals.append((p, s)))

        worker.run()

        # Should have multiple progress updates
        assert len(progress_signals) >= 3
        # Last should be 100%
        assert progress_signals[-1][0] == 100


class TestDetectionWorkerError:
    """Test error handling."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.detect_entities"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.__init__",
        return_value=None,
    )
    def test_worker_emits_error_on_failure(
        self,
        mock_init: MagicMock,
        mock_detect: MagicMock,
        mock_init_db: MagicMock,
        qtbot,  # type: ignore[no-untyped-def]
        tmp_path: object,
    ) -> None:
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        mock_detect.side_effect = FileProcessingError("File not found")

        db_path = str(tmp_path) + "/test.db"  # type: ignore[operator]
        worker = DetectionWorker(
            file_path="nonexistent.txt",
            db_path=db_path,
            passphrase="test_passphrase_ok",
        )

        errors: list[str] = []
        worker.signals.error.connect(lambda msg: errors.append(msg))

        worker.run()

        assert len(errors) == 1


class TestDetectionWorkerCancellation:
    """Test cancellation flag."""

    def test_cancellation_stops_early(
        self,
        qtbot,  # type: ignore[no-untyped-def]
        tmp_path: object,
    ) -> None:
        db_path = str(tmp_path) + "/test.db"  # type: ignore[operator]
        worker = DetectionWorker(
            file_path="test.txt",
            db_path=db_path,
            passphrase="test_passphrase_ok",
        )

        worker.cancel()

        results: list[object] = []
        errors: list[str] = []
        worker.signals.finished.connect(lambda r: results.append(r))
        worker.signals.error.connect(lambda msg: errors.append(msg))

        worker.run()

        # Should not emit finished or error (cancelled before DB init)
        assert len(results) == 0
        assert len(errors) == 0
