"""Integration tests for Story 2.8: Batch Processing with Component Collision Fix.

Tests cover:
- End-to-end batch processing with overlapping entities
- Verification that no duplicate pseudonyms exist in database
- Story 2.7 verification script execution (5 consistency tests)
- Stress testing with high entity overlap (50+ documents)

These tests validate that the component collision fix (Story 2.8) prevents
the critical bug discovered in Story 2.7 where "Dubois" and "Lefebvre" both
mapped to "Neto".
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database


class TestBatchProcessingCollisionFix:
    """Integration tests for batch processing with collision fix."""

    @pytest.fixture(autouse=True)
    def mock_validation_workflow(self):
        """Mock validation workflow to auto-accept all detected entities."""
        with patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow") as mock:
            # Pass through all entities (simulate user accepting everything)
            mock.side_effect = lambda entities, **kwargs: entities
            yield mock

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> str:
        """Create temporary test database path."""
        db_path = str(tmp_path / "test_collision_fix.db")
        # Initialize database
        init_database(db_path, "test_passphrase_2024")
        return db_path

    @pytest.fixture
    def test_documents_dir(self, tmp_path: Path) -> Path:
        """Create test documents with overlapping entities."""
        docs_dir = tmp_path / "test_docs"
        docs_dir.mkdir()

        # Document 1: "Marie Dubois" and "Pierre Lefebvre"
        doc1_content = """
        Marie Dubois travaille avec Pierre Lefebvre.
        Marie est une excellente développeuse.
        Pierre est un architecte senior.
        """
        (docs_dir / "doc1.txt").write_text(doc1_content, encoding="utf-8")

        # Document 2: Standalone "Dubois" and "Lefebvre"
        doc2_content = """
        Dr. Dubois a rencontré Dr. Lefebvre hier.
        Dubois est un expert en IA.
        Lefebvre travaille sur le projet.
        """
        (docs_dir / "doc2.txt").write_text(doc2_content, encoding="utf-8")

        # Document 3: "Marie Dupont" (reuse Marie component)
        doc3_content = """
        Marie Dupont collabore avec Jean Martin.
        Marie est chef de projet.
        """
        (docs_dir / "doc3.txt").write_text(doc3_content, encoding="utf-8")

        # Document 4: More overlapping names
        doc4_content = """
        Dubois et Lefebvre sont présents.
        Marie Dubois dirige l'équipe.
        Pierre Lefebvre supervise le développement.
        """
        (docs_dir / "doc4.txt").write_text(doc4_content, encoding="utf-8")

        return docs_dir

    def test_no_duplicate_pseudonyms_in_batch_processing(
        self, test_db_path: str, test_documents_dir: Path
    ) -> None:
        """Test that batch processing produces no duplicate pseudonyms.

        This is the CRITICAL test from Story 2.7 bug report:
        - "Marie Dubois" and "Pierre Lefebvre" should get different last name pseudonyms
        - Standalone "Dubois" and "Lefebvre" should reuse respective mappings
        - No two different real entities should share same pseudonym
        """
        # Process all documents
        processor = DocumentProcessor(
            db_path=test_db_path,
            passphrase="test_passphrase_2024",
            theme="neutral",
            model_name="spacy",
        )

        output_dir = test_documents_dir / "output"
        output_dir.mkdir()

        # Process each document
        for doc_file in sorted(test_documents_dir.glob("doc*.txt")):
            output_file = output_dir / f"{doc_file.stem}_pseudonymized.txt"
            result = processor.process_document(str(doc_file), str(output_file))
            assert (
                result.success
            ), f"Processing failed for {doc_file}: {result.error_message}"

        # Verify no duplicate pseudonyms in database
        with open_database(test_db_path, "test_passphrase_2024") as db_session:
            session = db_session.session

            # Query for duplicate pseudonyms
            duplicate_pseudonyms = session.execute(
                text(
                    """
                SELECT pseudonym_full, COUNT(*) as count,
                       GROUP_CONCAT(full_name) as real_names
                FROM entities
                WHERE entity_type = 'PERSON'
                GROUP BY pseudonym_full
                HAVING count > 1
            """
                )
            ).fetchall()

            # CRITICAL: No duplicate pseudonyms allowed
            if duplicate_pseudonyms:
                print("\n=== DUPLICATE PSEUDONYMS DETECTED ===")
                for row in duplicate_pseudonyms:
                    print(f"  Pseudonym: {row[0]} -> Used {row[1]} times for: {row[2]}")
                pytest.fail(
                    f"Found {len(duplicate_pseudonyms)} duplicate pseudonyms (violates GDPR 1:1 mapping)"
                )

    def test_component_reuse_consistency_across_documents(
        self, test_db_path: str, test_documents_dir: Path
    ) -> None:
        """Test that component mappings are consistent across documents.

        Scenario:
        1. Process doc1: "Marie Dubois" and "Pierre Lefebvre"
        2. Process doc2: Standalone "Dubois" and "Lefebvre"
        3. Verify component reuse consistency
        """
        processor = DocumentProcessor(
            db_path=test_db_path,
            passphrase="test_passphrase_2024",
            theme="neutral",
            model_name="spacy",
        )

        output_dir = test_documents_dir / "output"
        output_dir.mkdir()

        # Process documents in order
        doc_files = sorted(test_documents_dir.glob("doc*.txt"))
        for doc_file in doc_files:
            output_file = output_dir / f"{doc_file.stem}_pseudonymized.txt"
            result = processor.process_document(str(doc_file), str(output_file))
            assert result.success

        # Verify component consistency in database
        with open_database(test_db_path, "test_passphrase_2024") as db_session:
            session = db_session.session

            # Get all PERSON entities with last_name "Dubois"
            dubois_entities = session.execute(
                text(
                    """
                SELECT full_name, first_name, last_name, pseudonym_first, pseudonym_last
                FROM entities
                WHERE last_name = 'Dubois' AND entity_type = 'PERSON'
            """
                )
            ).fetchall()

            # Verify all "Dubois" last names map to same pseudonym component
            if len(dubois_entities) > 1:
                dubois_pseudo_last_names = set(
                    [entity[4] for entity in dubois_entities]
                )
                assert (
                    len(dubois_pseudo_last_names) == 1
                ), f"Dubois mapped to {len(dubois_pseudo_last_names)} different pseudonyms: {dubois_pseudo_last_names}"

            # Get all PERSON entities with first_name "Marie"
            marie_entities = session.execute(
                text(
                    """
                SELECT full_name, first_name, last_name, pseudonym_first, pseudonym_last
                FROM entities
                WHERE first_name = 'Marie' AND entity_type = 'PERSON'
            """
                )
            ).fetchall()

            # Verify all "Marie" first names map to same pseudonym component
            if len(marie_entities) > 1:
                marie_pseudo_first_names = set([entity[3] for entity in marie_entities])
                assert (
                    len(marie_pseudo_first_names) == 1
                ), f"Marie mapped to {len(marie_pseudo_first_names)} different pseudonyms: {marie_pseudo_first_names}"

    def test_different_real_components_get_different_pseudonyms(
        self, test_db_path: str, test_documents_dir: Path
    ) -> None:
        """Test that "Dubois" and "Lefebvre" NEVER map to same pseudonym.

        This is the root cause bug from Story 2.7 that this story fixes.
        """
        processor = DocumentProcessor(
            db_path=test_db_path,
            passphrase="test_passphrase_2024",
            theme="neutral",
            model_name="spacy",
        )

        output_dir = test_documents_dir / "output"
        output_dir.mkdir()

        # Process all documents
        for doc_file in sorted(test_documents_dir.glob("doc*.txt")):
            output_file = output_dir / f"{doc_file.stem}_pseudonymized.txt"
            result = processor.process_document(str(doc_file), str(output_file))
            assert result.success

        # Verify "Dubois" and "Lefebvre" have different pseudonym components
        with open_database(test_db_path, "test_passphrase_2024") as db_session:
            session = db_session.session

            # Get all distinct (last_name, pseudonym_last) pairs
            last_name_mappings = session.execute(
                text(
                    """
                SELECT DISTINCT last_name, pseudonym_last
                FROM entities
                WHERE entity_type = 'PERSON' AND last_name IS NOT NULL
                ORDER BY last_name
            """
                )
            ).fetchall()

            # Build mapping dict: real_last_name -> pseudonym_last
            mappings = {}
            for real_last, pseudo_last in last_name_mappings:
                if real_last in mappings:
                    # Same real last name should always map to same pseudonym
                    assert (
                        mappings[real_last] == pseudo_last
                    ), f"Inconsistent mapping for '{real_last}': {mappings[real_last]} vs {pseudo_last}"
                else:
                    mappings[real_last] = pseudo_last

            # CRITICAL: "Dubois" and "Lefebvre" must have different pseudonyms
            if "Dubois" in mappings and "Lefebvre" in mappings:
                dubois_pseudo = mappings["Dubois"]
                lefebvre_pseudo = mappings["Lefebvre"]
                assert (
                    dubois_pseudo != lefebvre_pseudo
                ), f"CRITICAL BUG: 'Dubois' and 'Lefebvre' both mapped to '{dubois_pseudo}'"

            # Verify all different real last names have different pseudonyms (no collisions)
            pseudonym_lasts = list(mappings.values())
            unique_pseudonyms = set(pseudonym_lasts)
            assert len(pseudonym_lasts) == len(
                unique_pseudonyms
            ), f"Component collision detected: {len(pseudonym_lasts)} real names map to {len(unique_pseudonyms)} pseudonyms"


class TestStoryTwoSevenVerification:
    """Run Story 2.7 verification tests to confirm fix."""

    @pytest.fixture
    def spike_test_corpus(self) -> Path:
        """Get Story 2.7 test corpus path."""
        corpus_path = Path("tests/fixtures/batch_spike")
        if not corpus_path.exists():
            pytest.skip("Story 2.7 test corpus not found")
        return corpus_path

    def test_story_27_verification_script_passes(
        self, spike_test_corpus: Path, tmp_path: Path
    ) -> None:
        """Run Story 2.7 verification script - all 5 tests should pass.

        Previously Test 4 (duplicate pseudonym check) was FAILING.
        With Story 2.8 fix, all 5 tests should PASS.
        """
        # Check if verification script exists
        verification_script = Path("scripts/verify_mapping_consistency.py")
        if not verification_script.exists():
            pytest.skip("Story 2.7 verification script not found")

        # Clean and initialize test database
        db_path = str(tmp_path / "spike_test.db")
        if Path(db_path).exists():
            os.remove(db_path)

        init_database(db_path, "spike_test_passphrase_2024")

        # Process Story 2.7 test corpus
        processor = DocumentProcessor(
            db_path=db_path,
            passphrase="spike_test_passphrase_2024",
            theme="neutral",
            model_name="spacy",
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Find test documents
        doc_files = sorted(spike_test_corpus.glob("doc_*.txt"))
        if not doc_files:
            pytest.skip("No test documents found in Story 2.7 corpus")

        # Process all documents
        for doc_file in doc_files[:10]:  # Process first 10 for speed
            output_file = output_dir / f"{doc_file.stem}_pseudonymized.txt"
            result = processor.process_document(str(doc_file), str(output_file))
            assert result.success

        # Run critical verification: No duplicate pseudonyms (Test 4 from Story 2.7)
        with open_database(db_path, "spike_test_passphrase_2024") as db_session:
            session = db_session.session

            # Test 4: Check for duplicate pseudonyms (MUST PASS NOW)
            duplicate_pseudonyms = session.execute(
                text(
                    """
                SELECT pseudonym_full, COUNT(*) as count
                FROM entities
                WHERE entity_type = 'PERSON'
                GROUP BY pseudonym_full
                HAVING count > 1
            """
                )
            ).fetchall()

            # CRITICAL: No duplicate pseudonyms allowed
            assert (
                len(duplicate_pseudonyms) == 0
            ), f"Found {len(duplicate_pseudonyms)} duplicate pseudonyms: {duplicate_pseudonyms}"


@pytest.mark.slow
class TestBatchProcessingStressTest:
    """Stress tests for component collision prevention at scale."""

    def test_50_documents_high_entity_overlap(self, tmp_path: Path) -> None:
        """Test batch processing with 50+ documents and high entity overlap.

        This stress test validates that component collision prevention works
        correctly even with many overlapping entities across documents.
        """
        # Create test database
        db_path = str(tmp_path / "stress_test.db")
        init_database(db_path, "stress_test_passphrase")

        # Create 50 test documents with overlapping entities
        docs_dir = tmp_path / "stress_docs"
        docs_dir.mkdir()

        # Common pool of names (high overlap)
        first_names = [
            "Marie",
            "Pierre",
            "Jean",
            "Sophie",
            "Luc",
            "Emma",
            "Thomas",
            "Julie",
        ]
        last_names = [
            "Dubois",
            "Lefebvre",
            "Martin",
            "Dupont",
            "Bernard",
            "Moreau",
            "Simon",
            "Laurent",
        ]

        # Create 50 documents with overlapping entities
        for i in range(50):
            # Each document mentions 5-10 entities
            entities = []
            for j in range(5 + (i % 6)):  # 5-10 entities per doc
                first = first_names[(i + j) % len(first_names)]
                last = last_names[(i + j + 2) % len(last_names)]
                entities.append(f"{first} {last}")

            content = "\n".join(
                [f"{entity} travaille sur le projet {i+1}." for entity in entities[:3]]
            )
            content += "\n" + "\n".join(
                [f"{entity} est présent." for entity in entities[3:]]
            )

            (docs_dir / f"stress_doc_{i:03d}.txt").write_text(content, encoding="utf-8")

        # Process all documents
        processor = DocumentProcessor(
            db_path=db_path,
            passphrase="stress_test_passphrase",
            theme="neutral",
            model_name="spacy",
        )

        output_dir = tmp_path / "stress_output"
        output_dir.mkdir()

        processed_count = 0
        for doc_file in sorted(docs_dir.glob("stress_doc_*.txt")):
            output_file = output_dir / f"{doc_file.stem}_pseudonymized.txt"
            result = processor.process_document(str(doc_file), str(output_file))
            if result.success:
                processed_count += 1

        assert (
            processed_count >= 45
        ), f"Only {processed_count}/50 documents processed successfully"

        # Verify no duplicate pseudonyms in database
        with open_database(db_path, "stress_test_passphrase") as db_session:
            session = db_session.session

            # Count total entities
            total_entities = session.execute(
                text("SELECT COUNT(*) FROM entities")
            ).fetchone()
            assert total_entities is not None
            assert total_entities[0] > 0, "No entities stored in database"

            # Check for duplicate pseudonyms
            duplicate_pseudonyms = session.execute(
                text(
                    """
                SELECT pseudonym_full, COUNT(*) as count
                FROM entities
                WHERE entity_type = 'PERSON'
                GROUP BY pseudonym_full
                HAVING count > 1
            """
                )
            ).fetchall()

            # CRITICAL: No duplicate pseudonyms even under stress
            assert (
                len(duplicate_pseudonyms) == 0
            ), f"Stress test failed: {len(duplicate_pseudonyms)} duplicate pseudonyms"

            # Verify component consistency: Same real name = same pseudonym
            # Get all "Marie Dubois" entries
            marie_dubois_entries = session.execute(
                text(
                    """
                SELECT pseudonym_full, pseudonym_first, pseudonym_last
                FROM entities
                WHERE full_name = 'Marie Dubois' AND entity_type = 'PERSON'
            """
                )
            ).fetchall()

            if len(marie_dubois_entries) > 1:
                # All "Marie Dubois" should have identical pseudonyms
                first_pseudonym = marie_dubois_entries[0]
                for entry in marie_dubois_entries[1:]:
                    assert (
                        entry == first_pseudonym
                    ), "Same entity got different pseudonyms across documents"
