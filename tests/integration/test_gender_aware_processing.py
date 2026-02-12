"""Integration test for gender-aware pseudonym processing (Story 5.2, Task 5.2.10).

End-to-end test verifying:
- Gender detection integrated into processing pipeline
- Female names get female pseudonyms
- Male names get male pseudonyms
- Unknown names get valid pseudonyms from combined list
- Entity.gender field populated in database
- Compound names handled correctly
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager


class TestGenderAwareProcessing:
    """Integration tests for gender-aware pseudonym assignment pipeline."""

    @pytest.fixture(autouse=True)
    def mock_validation_workflow(self):
        """Mock validation workflow to auto-accept all detected entities."""
        with patch(
            "gdpr_pseudonymizer.core.document_processor.run_validation_workflow"
        ) as mock:
            mock.side_effect = lambda entities, **kwargs: entities
            yield mock

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> str:
        db_path = tmp_path / "test_mappings.db"
        passphrase = "test_passphrase_12345"
        init_database(str(db_path), passphrase)
        return str(db_path)

    @pytest.fixture
    def library(self) -> LibraryBasedPseudonymManager:
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral")
        return manager

    def _make_entities(self, text: str) -> list[DetectedEntity]:
        """Create mock detected entities from known positions in test document."""
        entities = []
        # Find each known name in the text and create entity
        names = [
            ("Marie Dupont", "PERSON"),
            ("Jean Martin", "PERSON"),
            ("Marie-Claire Dubois", "PERSON"),
            ("Xyzabcdef Noname", "PERSON"),
            ("Paris", "LOCATION"),
        ]
        for name, etype in names:
            idx = text.find(name)
            if idx >= 0:
                entities.append(
                    DetectedEntity(
                        text=name,
                        entity_type=etype,
                        start_pos=idx,
                        end_pos=idx + len(name),
                        confidence=0.95,
                        source="test",
                    )
                )
        return entities

    def test_gender_matched_pseudonyms(
        self, test_db: str, tmp_path: Path, library: LibraryBasedPseudonymManager
    ) -> None:
        """Process document -> verify female/male names get gender-matched pseudonyms."""
        passphrase = "test_passphrase_12345"

        # Create test document with known names
        doc_text = (
            "Marie Dupont a rencontré Jean Martin à Paris. "
            "Marie-Claire Dubois était aussi présente. "
            "Xyzabcdef Noname n'est pas connu."
        )
        input_file = tmp_path / "input.txt"
        input_file.write_text(doc_text, encoding="utf-8")
        output_file = tmp_path / "output.txt"

        detected = self._make_entities(doc_text)

        with patch(
            "gdpr_pseudonymizer.core.document_processor.HybridDetector"
        ) as mock_detector_cls:
            mock_detector = mock_detector_cls.return_value
            mock_detector.detect_entities.return_value = detected

            processor = DocumentProcessor(
                db_path=test_db,
                passphrase=passphrase,
                theme="neutral",
            )
            result = processor.process_document(
                str(input_file), str(output_file), skip_validation=True
            )

        assert result.success is True
        assert result.entities_detected == len(detected)

        # Verify gender in database entities
        with open_database(test_db, passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Marie Dupont should have gender="female"
            marie = repo.find_by_full_name("Marie Dupont")
            assert marie is not None
            assert marie.gender == "female"

            # Jean Martin should have gender="male"
            jean = repo.find_by_full_name("Jean Martin")
            assert jean is not None
            assert jean.gender == "male"

            # Marie-Claire Dubois should have gender="female" (compound, first component)
            mc = repo.find_by_full_name("Marie-Claire Dubois")
            assert mc is not None
            assert mc.gender == "female"

            # Unknown name should have gender=None
            unknown = repo.find_by_full_name("Xyzabcdef Noname")
            assert unknown is not None
            assert unknown.gender is None

            # Paris (LOCATION) should have gender=None
            paris = repo.find_by_full_name("Paris")
            assert paris is not None
            assert paris.gender is None

    def test_female_pseudonym_from_female_library(
        self, test_db: str, tmp_path: Path, library: LibraryBasedPseudonymManager
    ) -> None:
        """Female name should get a pseudonym first name from the female list."""
        passphrase = "test_passphrase_12345"

        doc_text = "Marie Dupont travaille ici."
        input_file = tmp_path / "input.txt"
        input_file.write_text(doc_text, encoding="utf-8")
        output_file = tmp_path / "output.txt"

        detected = [
            DetectedEntity(
                text="Marie Dupont",
                entity_type="PERSON",
                start_pos=0,
                end_pos=12,
                confidence=0.95,
                source="test",
            )
        ]

        with patch(
            "gdpr_pseudonymizer.core.document_processor.HybridDetector"
        ) as mock_detector_cls:
            mock_detector = mock_detector_cls.return_value
            mock_detector.detect_entities.return_value = detected

            processor = DocumentProcessor(
                db_path=test_db,
                passphrase=passphrase,
                theme="neutral",
            )
            processor.process_document(
                str(input_file), str(output_file), skip_validation=True
            )

        # Verify the pseudonym first name comes from the female list
        with open_database(test_db, passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity = repo.find_by_full_name("Marie Dupont")
            assert entity is not None
            assert entity.pseudonym_first in library.first_names["female"]

    def test_male_pseudonym_from_male_library(
        self, test_db: str, tmp_path: Path, library: LibraryBasedPseudonymManager
    ) -> None:
        """Male name should get a pseudonym first name from the male list."""
        passphrase = "test_passphrase_12345"

        doc_text = "Jean Martin travaille ici."
        input_file = tmp_path / "input.txt"
        input_file.write_text(doc_text, encoding="utf-8")
        output_file = tmp_path / "output.txt"

        detected = [
            DetectedEntity(
                text="Jean Martin",
                entity_type="PERSON",
                start_pos=0,
                end_pos=11,
                confidence=0.95,
                source="test",
            )
        ]

        with patch(
            "gdpr_pseudonymizer.core.document_processor.HybridDetector"
        ) as mock_detector_cls:
            mock_detector = mock_detector_cls.return_value
            mock_detector.detect_entities.return_value = detected

            processor = DocumentProcessor(
                db_path=test_db,
                passphrase=passphrase,
                theme="neutral",
            )
            processor.process_document(
                str(input_file), str(output_file), skip_validation=True
            )

        with open_database(test_db, passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity = repo.find_by_full_name("Jean Martin")
            assert entity is not None
            assert entity.pseudonym_first in library.first_names["male"]
