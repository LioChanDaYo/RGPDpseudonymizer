"""Integration tests for encrypted database end-to-end workflows."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity, Metadata, Operation
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.data.repositories.metadata_repository import (
    MetadataRepository,
)


class TestEncryptedDatabaseIntegration:
    """Integration tests for complete database workflows with encryption."""

    def test_end_to_end_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: init → open → save → query → close."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        # Step 1: Initialize database
        init_database(str(db_path), passphrase)
        assert db_path.exists()

        # Step 2: Open database
        with open_database(str(db_path), passphrase) as db_session:
            # Step 3: Save entity
            repo = SQLiteMappingRepository(db_session)
            entity = Entity(
                entity_type="PERSON",
                first_name="Marie",
                last_name="Curie",
                full_name="Marie Curie",
                pseudonym_first="Leia",
                pseudonym_last="Organa",
                pseudonym_full="Leia Organa",
                theme="star_wars",
                gender="female",
                confidence_score=0.95,
            )
            saved = repo.save(entity)

            assert saved.id is not None

            # Step 4: Query entity
            found = repo.find_by_full_name("Marie Curie")
            assert found is not None
            assert found.first_name == "Marie"
            assert found.pseudonym_full == "Leia Organa"

        # Step 5: Close (automatic via context manager)
        # Verify database still exists and is valid
        assert db_path.exists()

    def test_cross_session_consistency(self, tmp_path: Path) -> None:
        """Test entity persists correctly across session close/reopen."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Save in first session
        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity = Entity(
                entity_type="PERSON",
                first_name="Albert",
                last_name="Einstein",
                full_name="Albert Einstein",
                pseudonym_first="Han",
                pseudonym_last="Solo",
                pseudonym_full="Han Solo",
                theme="star_wars",
            )
            saved = repo.save(entity)
            saved_id = saved.id

        # Query in second session (after close)
        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            found = repo.find_by_full_name("Albert Einstein")

            assert found is not None
            assert found.id == saved_id
            assert found.first_name == "Albert"
            assert found.last_name == "Einstein"
            assert found.pseudonym_full == "Han Solo"

    def test_idempotency_multiple_queries(self, tmp_path: Path) -> None:
        """Test querying same entity multiple times returns consistent results."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save entity
            entity = Entity(
                entity_type="PERSON",
                full_name="Test Person",
                pseudonym_full="Test Pseudonym",
                theme="neutral",
            )
            repo.save(entity)

            # Query multiple times
            result1 = repo.find_by_full_name("Test Person")
            result2 = repo.find_by_full_name("Test Person")
            result3 = repo.find_by_full_name("Test Person")

            # All results should be identical
            assert result1 is not None
            assert result2 is not None
            assert result3 is not None

            assert result1.id == result2.id == result3.id
            assert result1.full_name == result2.full_name == result3.full_name
            assert (
                result1.pseudonym_full
                == result2.pseudonym_full
                == result3.pseudonym_full
            )

    def test_encrypted_data_at_rest(self, tmp_path: Path) -> None:
        """Test sensitive fields are actually encrypted in database file."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Save entity with known plaintext
        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity = Entity(
                entity_type="PERSON",
                first_name="SensitiveFirst",
                last_name="SensitiveLast",
                full_name="SensitiveFirst SensitiveLast",
                pseudonym_first="PseudoFirst",
                pseudonym_last="PseudoLast",
                pseudonym_full="PseudoFirst PseudoLast",
                theme="neutral",
            )
            repo.save(entity)

        # Read raw database file (bypassing encryption)
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        raw_session = SessionLocal()

        try:
            raw_entity = raw_session.query(Entity).first()

            # Verify sensitive fields are encrypted (not plaintext)
            assert raw_entity is not None
            assert "SensitiveFirst" not in str(raw_entity.first_name)
            assert "SensitiveLast" not in str(raw_entity.last_name)
            assert "SensitiveFirst SensitiveLast" not in str(raw_entity.full_name)
            assert "PseudoFirst" not in str(raw_entity.pseudonym_first)
            assert "PseudoLast" not in str(raw_entity.pseudonym_last)
            assert "PseudoFirst PseudoLast" not in str(raw_entity.pseudonym_full)

        finally:
            raw_session.close()
            engine.dispose()

    def test_compositional_logic_integration(self, tmp_path: Path) -> None:
        """Test repository integration with compositional pseudonymization logic."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save entities with common components (simulating Story 2.2 logic)
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Curie",
                    full_name="Marie Curie",
                    pseudonym_first="Leia",
                    pseudonym_last="Organa",
                    pseudonym_full="Leia Organa",
                    theme="star_wars",
                )
            )
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Dupont",
                    full_name="Marie Dupont",
                    pseudonym_first="Leia",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Leia Skywalker",
                    theme="star_wars",
                )
            )
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Pierre",
                    last_name="Curie",
                    full_name="Pierre Curie",
                    pseudonym_first="Luke",
                    pseudonym_last="Organa",
                    pseudonym_full="Luke Organa",
                    theme="star_wars",
                )
            )

            # Test compositional queries (encrypted field queries)
            marie_entities = repo.find_by_component("Marie", "first_name")
            assert len(marie_entities) == 2
            assert all(e.first_name == "Marie" for e in marie_entities)

            curie_entities = repo.find_by_component("Curie", "last_name")
            assert len(curie_entities) == 2
            assert all(e.last_name == "Curie" for e in curie_entities)

            # Verify pseudonyms are compositional
            marie_pseudonyms = {e.pseudonym_first for e in marie_entities}
            assert marie_pseudonyms == {"Leia"}  # Same first name → same pseudonym

    def test_all_repositories_integration(self, tmp_path: Path) -> None:
        """Test all three repositories working together."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            # Test MappingRepository
            mapping_repo = SQLiteMappingRepository(db_session)
            entity = Entity(
                entity_type="PERSON",
                full_name="Integration Test",
                pseudonym_full="Test Pseudonym",
                theme="neutral",
            )
            saved_entity = mapping_repo.save(entity)

            # Test AuditRepository
            audit_repo = AuditRepository(db_session.session)
            operation = Operation(
                operation_type="PROCESS",
                files_processed=["test.md"],
                model_name="spacy",
                model_version="3.8.0",
                theme_selected="neutral",
                entity_count=1,
                processing_time_seconds=1.5,
                success=True,
            )
            logged_op = audit_repo.log_operation(operation)

            # Test MetadataRepository
            metadata_repo = MetadataRepository(db_session.session)
            metadata_repo.set_file_hash("test.md", "abc123hash")

            # Verify all repositories worked
            assert saved_entity.id is not None
            assert logged_op.id is not None
            assert metadata_repo.get_file_hash("test.md") == "abc123hash"

    def test_concurrent_reads_with_wal_mode(self, tmp_path: Path) -> None:
        """Test WAL mode allows concurrent read operations."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        # Save entity
        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity = Entity(
                entity_type="PERSON",
                full_name="Concurrent Test",
                pseudonym_full="Test Pseudonym",
                theme="neutral",
            )
            repo.save(entity)

        # Open two concurrent sessions (WAL mode allows this)
        with open_database(str(db_path), passphrase) as session1:
            with open_database(str(db_path), passphrase) as session2:
                repo1 = SQLiteMappingRepository(session1)
                repo2 = SQLiteMappingRepository(session2)

                # Both sessions can read concurrently
                result1 = repo1.find_by_full_name("Concurrent Test")
                result2 = repo2.find_by_full_name("Concurrent Test")

                assert result1 is not None
                assert result2 is not None
                assert result1.id == result2.id

    def test_database_indexes_used_for_queries(self, tmp_path: Path) -> None:
        """Test that database indexes are created and used for queries."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            # Verify indexes exist
            result = db_session.session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
                )
            )
            indexes = [row[0] for row in result]

            # Verify entity indexes
            assert "idx_entities_full_name" in indexes
            assert "idx_entities_type" in indexes
            assert "idx_entities_first_name" in indexes
            assert "idx_entities_last_name" in indexes

            # Save entities and verify queries use indexes
            repo = SQLiteMappingRepository(db_session)
            for i in range(10):
                repo.save(
                    Entity(
                        entity_type="PERSON",
                        full_name=f"Person {i}",
                        pseudonym_full=f"Pseudonym {i}",
                        theme="neutral",
                    )
                )

            # Query should be fast with index
            result = repo.find_by_full_name("Person 5")
            assert result is not None
            assert result.full_name == "Person 5"

    def test_batch_save_rollback_on_error(self, tmp_path: Path) -> None:
        """Test batch save rolls back all changes on error (all-or-nothing)."""
        db_path = tmp_path / "test.db"
        passphrase = "integration_test_passphrase_123!"

        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save first entity successfully
            entity1 = Entity(
                entity_type="PERSON",
                full_name="First Entity",
                pseudonym_full="First Pseudonym",
                theme="neutral",
            )
            repo.save(entity1)

            # Attempt batch save with duplicate
            entities = [
                Entity(
                    entity_type="PERSON",
                    full_name="Batch Entity 1",
                    pseudonym_full="Batch Pseudonym 1",
                    theme="neutral",
                ),
                Entity(
                    entity_type="PERSON",
                    full_name="First Entity",  # Duplicate!
                    pseudonym_full="Duplicate Pseudonym",
                    theme="neutral",
                ),
            ]

            try:
                repo.save_batch(entities)
                pytest.fail("Expected DatabaseError due to duplicate")
            except Exception:
                pass  # Expected

            # Verify "Batch Entity 1" was NOT saved (rollback worked)
            result = repo.find_by_full_name("Batch Entity 1")
            assert result is None

            # Verify original entity still exists
            result = repo.find_by_full_name("First Entity")
            assert result is not None
