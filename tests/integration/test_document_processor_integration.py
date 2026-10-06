"""Integration tests for DocumentProcessor with real SQLite repository.

Uses a real SQLiteMappingRepository (not mocks) to exercise the full
process_document workflow: detection -> pseudonym assignment -> DB save -> output.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

TEST_PASSPHRASE = "integration_test_passphrase_123!"
INPUT_TEXT = "Marie Dubois habite à Paris."


def _entity(text: str, entity_type: str, input_text: str) -> DetectedEntity:
    """Build a mocked detection whose span is derived from the input text."""
    start = input_text.index(text)
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
    )


def _detected_entities(input_text: str) -> list[DetectedEntity]:
    return [
        _entity("Marie Dubois", "PERSON", input_text),
        _entity("Paris", "LOCATION", input_text),
    ]


class TestDocumentProcessorIntegration:
    """End-to-end integration tests with real database."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> str:
        path = str(tmp_path / "integration_test.db")
        init_database(path, TEST_PASSPHRASE)
        return path

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    def test_full_workflow_detection_to_output(
        self,
        mock_write_file: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        db_path: str,
        tmp_path: Path,
    ) -> None:
        """End-to-end: detect entities -> assign pseudonyms -> save to DB -> write output."""
        input_text = INPUT_TEXT
        mock_read_file.return_value = input_text

        detected_entities = _detected_entities(input_text)
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = detected_entities
        mock_detector.nlp = Mock()
        mock_detector.nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0"}
        mock_detector_class.return_value = mock_detector

        processor = DocumentProcessor(
            db_path=db_path,
            passphrase=TEST_PASSPHRASE,
            theme="neutral",
        )
        result = processor.process_document(
            input_path="input.txt",
            output_path=str(tmp_path / "output.txt"),
            skip_validation=True,
        )

        # Verify success
        assert result.success is True
        assert result.entities_detected == 2
        assert result.entities_new == 2
        assert result.entities_reused == 0

        # Verify entities are saved in the real database
        with open_database(db_path, TEST_PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            person = repo.find_by_full_name("Marie Dubois")
            assert person is not None
            assert person.entity_type == "PERSON"
            assert person.pseudonym_full is not None

            location = repo.find_by_full_name("Paris")
            assert location is not None
            assert location.entity_type == "LOCATION"
            assert location.pseudonym_full is not None
            person_pseudonym = person.pseudonym_full
            location_pseudonym = location.pseudonym_full

        # Verify each original span was replaced by its mapped pseudonym and
        # the surrounding text is intact. Pseudonyms are random, so compare
        # against the expected structure rather than checking that a word
        # such as "Paris" never appears (a pseudonym surname can be "Paris").
        mock_write_file.assert_called_once()
        written_text = mock_write_file.call_args[0][1]
        assert written_text == f"{person_pseudonym} habite à {location_pseudonym}."
        assert "habite à Paris" not in written_text

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    @patch("gdpr_pseudonymizer.core.document_processor.read_file")
    @patch("gdpr_pseudonymizer.core.document_processor.write_file")
    def test_idempotency_no_duplicates(
        self,
        mock_write_file: Mock,
        mock_read_file: Mock,
        mock_detector_class: Mock,
        db_path: str,
        tmp_path: Path,
    ) -> None:
        """Process same document twice: verify reuse, no duplicate entities."""
        input_text = INPUT_TEXT
        mock_read_file.return_value = input_text

        detected_entities = _detected_entities(input_text)
        mock_detector = Mock()
        mock_detector.detect_entities.return_value = detected_entities
        mock_detector.nlp = Mock()
        mock_detector.nlp.meta = {"name": "fr_core_news_lg", "version": "3.8.0"}
        mock_detector_class.return_value = mock_detector

        processor = DocumentProcessor(
            db_path=db_path,
            passphrase=TEST_PASSPHRASE,
            theme="neutral",
        )

        # First pass
        result1 = processor.process_document(
            "input.txt", str(tmp_path / "output1.txt"), skip_validation=True
        )
        assert result1.success is True
        assert result1.entities_new == 2

        # Second pass — same entities should be reused
        result2 = processor.process_document(
            "input.txt", str(tmp_path / "output2.txt"), skip_validation=True
        )
        assert result2.success is True
        assert result2.entities_new == 0
        assert result2.entities_reused == 2

        # Both outputs should have the same pseudonyms
        call1_text = mock_write_file.call_args_list[0][0][1]
        call2_text = mock_write_file.call_args_list[1][0][1]
        assert call1_text == call2_text

        # Database should have exactly 2 entities (not 4)
        with open_database(db_path, TEST_PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            all_entities = repo.find_all()
            assert len(all_entities) == 2


# QA REL-001 (10.3a follow-up): a name hard-wrapped over a line break, joined
# by W-JOIN, must get the same mapping key, so the same pseudonym, as its
# one-line spelling. Invented names; the other words are main-corpus words.
ONE_LINE = "le contrat est signé par Zorbalia Quentrix, avec le projet"
WRAPPED = "le contrat est signé par Zorbalia\nQuentrix, avec le projet"


def _wrap_detections(text: str) -> list[DetectedEntity]:
    """Stub only spaCy: the real merge, W-JOIN included, builds the spans.

    spaCy sees "Zorbalia Quentrix" on one line and only "Zorbalia" before a
    line break, as in a hard-wrapped PDF extraction.
    """
    spacy_like = [
        DetectedEntity(
            text=match.group(),
            entity_type="PERSON",
            start_pos=match.start(),
            end_pos=match.end(),
        )
        for match in re.finditer(r"Zorbalia(?: Quentrix)?", text)
    ]
    return HybridDetector()._merge_entities(spacy_like, [], text)


class TestWrappedNamePseudonymKey:
    """End to end through DocumentProcessor with a temporary database."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> str:
        path = str(tmp_path / "wrapped_key.db")
        init_database(path, TEST_PASSPHRASE)
        return path

    @staticmethod
    def _process(
        db_path: str,
        tmp_path: Path,
        text: str,
        name: str,
        detections: list[DetectedEntity] | None = None,
    ) -> tuple[ProcessingResult, str]:
        if detections is None:
            detections = _wrap_detections(text)
        with (
            patch(
                "gdpr_pseudonymizer.core.document_processor.HybridDetector"
            ) as detector_class,
            patch(
                "gdpr_pseudonymizer.core.document_processor.read_file",
                return_value=text,
            ),
            patch("gdpr_pseudonymizer.core.document_processor.write_file") as write,
        ):
            detector = Mock()
            detector.detect_entities.return_value = detections
            detector_class.return_value = detector
            result = DocumentProcessor(
                db_path=db_path, passphrase=TEST_PASSPHRASE, theme="neutral"
            ).process_document(
                input_path=f"{name}.txt",
                output_path=str(tmp_path / f"{name}.out.txt"),
                skip_validation=True,
            )
        return result, write.call_args[0][1]

    @staticmethod
    def _stored(db_path: str) -> list[tuple[str, str]]:
        with open_database(db_path, TEST_PASSPHRASE) as db_session:
            repo = SQLiteMappingRepository(db_session)
            return [(e.full_name, e.pseudonym_full) for e in repo.find_all()]

    @staticmethod
    def _store_org(db_path: str, full_name: str, pseudonym: str) -> None:
        with open_database(db_path, TEST_PASSPHRASE) as db_session:
            SQLiteMappingRepository(db_session).save(
                Entity(
                    entity_type="ORG",
                    full_name=full_name,
                    pseudonym_full=pseudonym,
                    theme="neutral",
                )
            )

    def test_wrap_detection_keeps_the_line_break(self) -> None:
        # Precondition of the tests below: W-JOIN makes a span with "\n".
        texts = [e.text for e in _wrap_detections(f"{ONE_LINE}\n{WRAPPED}")]
        assert texts == ["Zorbalia Quentrix", "Zorbalia\nQuentrix"]

    def test_both_spellings_in_one_document_share_one_pseudonym(
        self, db_path: str, tmp_path: Path
    ) -> None:
        result, written = self._process(
            db_path, tmp_path, f"{ONE_LINE}\n{WRAPPED}", "doc"
        )
        assert result.success is True
        assert (result.entities_new, result.entities_reused) == (1, 1)
        [(full_name, pseudonym)] = self._stored(db_path)
        assert full_name == "Zorbalia Quentrix"
        assert written.count(pseudonym) == 2
        assert "Zorbalia" not in written and "Quentrix" not in written

    def test_wrapped_spelling_reuses_a_stored_one_line_mapping(
        self, db_path: str, tmp_path: Path
    ) -> None:
        # Continuity: a mapping stored from the one-line spelling (a key the
        # whitespace collapse leaves unchanged) still resolves, and the
        # wrapped spelling in a later document resolves to it too.
        first, _ = self._process(db_path, tmp_path, ONE_LINE, "first")
        assert first.entities_new == 1
        [(full_name, pseudonym)] = self._stored(db_path)
        assert full_name == "Zorbalia Quentrix"

        second, written = self._process(db_path, tmp_path, WRAPPED, "second")
        assert (second.entities_new, second.entities_reused) == (0, 1)
        assert written.count(pseudonym) == 1
        assert self._stored(db_path) == [("Zorbalia Quentrix", pseudonym)]

        third, written = self._process(db_path, tmp_path, ONE_LINE, "third")
        assert (third.entities_new, third.entities_reused) == (0, 1)
        assert written.count(pseudonym) == 1

    def test_pre_fix_key_with_unusual_spacing_gets_one_stable_new_mapping(
        self, db_path: str, tmp_path: Path
    ) -> None:
        # Accepted upgrade behaviour (Lionel 2026-10-07, no fallback lookup):
        # a row stored before the fix under a key with unusual spacing (here a
        # no-break space) is not reused. The name gets one new single-space
        # mapping once, and that mapping is stable from then on, whichever
        # spelling a later document uses. The old row stays in the database.
        legacy = "Quentrix\u00a0Vardel"
        self._store_org(db_path, legacy, "Morrix Conseil")
        prefix, suffix = "le contrat est signé par ", ", avec le projet"

        def run(name: str, doc: str) -> tuple[int, int, str]:
            text = f"{prefix}{name}{suffix}"
            result, written = self._process(
                db_path, tmp_path, text, doc, [_entity(name, "ORG", text)]
            )
            assert written.startswith(prefix) and written.endswith(suffix)
            pseudonym = written[len(prefix) : len(written) - len(suffix)]
            return result.entities_new, result.entities_reused, pseudonym

        new, reused, pseudonym = run(legacy, "upgrade")
        assert (new, reused) == (1, 0)
        assert pseudonym != "Morrix Conseil"
        assert sorted(self._stored(db_path)) == sorted(
            [(legacy, "Morrix Conseil"), ("Quentrix Vardel", pseudonym)]
        )

        assert run(legacy, "again") == (0, 1, pseudonym)
        assert run("Quentrix Vardel", "one_space") == (0, 1, pseudonym)
        assert len(self._stored(db_path)) == 2
