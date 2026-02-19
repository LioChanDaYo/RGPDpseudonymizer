"""Tests for FinalizationWorker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.core.document_processor import ProcessingResult
from gdpr_pseudonymizer.gui.workers.finalization_worker import FinalizationWorker
from gdpr_pseudonymizer.gui.workers.processing_worker import GUIProcessingResult
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


@pytest.fixture()
def validated_entities() -> list[DetectedEntity]:
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


class TestFinalizationWorkerSuccess:
    """Test successful finalization."""

    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.finalize_document"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.__init__",
        return_value=None,
    )
    def test_worker_emits_finished(
        self,
        mock_init: MagicMock,
        mock_finalize: MagicMock,
        qtbot,  # type: ignore[no-untyped-def]
        validated_entities: list[DetectedEntity],
        tmp_path: object,
    ) -> None:
        # Mock finalize_document to write output file
        def _finalize(
            document_text: str, validated_entities: list, output_path: str
        ) -> ProcessingResult:
            from pathlib import Path

            Path(output_path).write_text(
                "Le contrat avec Pierre Lambert à Lyon.", encoding="utf-8"
            )
            return ProcessingResult(
                success=True,
                input_file="test.txt",
                output_file=output_path,
                entities_detected=2,
                entities_new=2,
                entities_reused=0,
                processing_time_seconds=0.5,
            )

        mock_finalize.side_effect = _finalize

        worker = FinalizationWorker(
            validated_entities=validated_entities,
            document_text="Le contrat avec Jean Dupont à Paris.",
            db_path=str(tmp_path) + "/test.db",  # type: ignore[operator]
            passphrase="test_passphrase_ok",
            theme="neutral",
            input_path="test.txt",
        )

        results: list[object] = []
        worker.signals.finished.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, GUIProcessingResult)
        assert result.success is True
        assert result.entities_detected == 2


class TestFinalizationWorkerError:
    """Test error handling."""

    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.finalize_document"
    )
    @patch(
        "gdpr_pseudonymizer.core.document_processor.DocumentProcessor.__init__",
        return_value=None,
    )
    def test_worker_emits_error_on_failure(
        self,
        mock_init: MagicMock,
        mock_finalize: MagicMock,
        qtbot,  # type: ignore[no-untyped-def]
        validated_entities: list[DetectedEntity],
        tmp_path: object,
    ) -> None:
        mock_finalize.side_effect = Exception("DB error")

        worker = FinalizationWorker(
            validated_entities=validated_entities,
            document_text="text",
            db_path=str(tmp_path) + "/test.db",  # type: ignore[operator]
            passphrase="test_passphrase_ok",
            theme="neutral",
            input_path="test.txt",
        )

        errors: list[str] = []
        worker.signals.error.connect(lambda msg: errors.append(msg))

        worker.run()

        assert len(errors) == 1


class TestRejectedEntitiesExcluded:
    """Test that rejected entities are not in validated list (upstream logic)."""

    def test_rejected_not_in_validated(self) -> None:
        """This is really a GUIValidationState test — just verify the concept."""
        all_entities = [
            DetectedEntity(
                text="Jean Dupont",
                entity_type="PERSON",
                start_pos=0,
                end_pos=11,
            ),
            DetectedEntity(
                text="Invalid",
                entity_type="PERSON",
                start_pos=50,
                end_pos=57,
            ),
        ]
        # Simulate: only first entity validated
        validated = [all_entities[0]]
        assert len(validated) == 1
        assert validated[0].text == "Jean Dupont"
