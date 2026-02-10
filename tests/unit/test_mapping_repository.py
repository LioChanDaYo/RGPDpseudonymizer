"""Unit tests for SQLiteMappingRepository with encryption."""

from pathlib import Path

import pytest

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DuplicateEntityError


class TestSQLiteMappingRepository:
    """Test suite for SQLiteMappingRepository."""

    def test_save_encrypts_and_persists_entity(self, tmp_path: Path) -> None:
        """Test save() encrypts sensitive fields and persists entity."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            entity = Entity(
                entity_type="PERSON",
                first_name="Marie",
                last_name="Dubois",
                full_name="Marie Dubois",
                pseudonym_first="Leia",
                pseudonym_last="Organa",
                pseudonym_full="Leia Organa",
                theme="star_wars",
                gender="female",
                confidence_score=0.95,
            )

            saved = repo.save(entity)

            # Verify ID generated
            assert saved.id is not None

            # Verify plaintext fields returned
            assert saved.first_name == "Marie"
            assert saved.last_name == "Dubois"
            assert saved.full_name == "Marie Dubois"
            assert saved.pseudonym_first == "Leia"
            assert saved.pseudonym_last == "Organa"
            assert saved.pseudonym_full == "Leia Organa"

            # Verify metadata fields
            assert saved.entity_type == "PERSON"
            assert saved.theme == "star_wars"
            assert saved.gender == "female"
            assert saved.confidence_score == 0.95

    def test_find_by_full_name_returns_decrypted_entity(self, tmp_path: Path) -> None:
        """Test find_by_full_name() returns entity with decrypted fields."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save entity
            entity = Entity(
                entity_type="PERSON",
                first_name="Jean",
                last_name="Martin",
                full_name="Jean Martin",
                pseudonym_first="Luke",
                pseudonym_last="Skywalker",
                pseudonym_full="Luke Skywalker",
                theme="star_wars",
            )
            repo.save(entity)

            # Find by full name
            found = repo.find_by_full_name("Jean Martin")

            assert found is not None
            assert found.first_name == "Jean"
            assert found.last_name == "Martin"
            assert found.full_name == "Jean Martin"
            assert found.pseudonym_full == "Luke Skywalker"

    def test_find_by_full_name_returns_none_for_nonexistent(
        self, tmp_path: Path
    ) -> None:
        """Test find_by_full_name() returns None for non-existent entity."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            found = repo.find_by_full_name("Nonexistent Person")
            assert found is None

    def test_find_by_component_first_name(self, tmp_path: Path) -> None:
        """Test find_by_component() finds entities by encrypted first name."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save multiple entities with same first name
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Dupont",
                    full_name="Marie Dupont",
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
                    last_name="Martin",
                    full_name="Marie Martin",
                    pseudonym_first="Leia",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Leia Skywalker",
                    theme="star_wars",
                )
            )

            # Find by first name component
            entities = repo.find_by_component("Marie", "first_name")

            assert len(entities) == 2
            assert all(e.first_name == "Marie" for e in entities)
            assert {e.last_name for e in entities} == {"Dupont", "Martin"}

    def test_find_by_component_last_name(self, tmp_path: Path) -> None:
        """Test find_by_component() finds entities by encrypted last name."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save entities with same last name
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Jean",
                    last_name="Dubois",
                    full_name="Jean Dubois",
                    pseudonym_first="Luke",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Luke Skywalker",
                    theme="star_wars",
                )
            )
            repo.save(
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Dubois",
                    full_name="Marie Dubois",
                    pseudonym_first="Leia",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Leia Skywalker",
                    theme="star_wars",
                )
            )

            # Find by last name component
            entities = repo.find_by_component("Dubois", "last_name")

            assert len(entities) == 2
            assert all(e.last_name == "Dubois" for e in entities)
            assert {e.first_name for e in entities} == {"Jean", "Marie"}

    def test_find_by_component_invalid_type_raises_error(self, tmp_path: Path) -> None:
        """Test find_by_component() raises ValueError for invalid component_type."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            with pytest.raises(ValueError, match="Invalid component_type"):
                repo.find_by_component("Test", "invalid_type")

    def test_save_batch_persists_multiple_entities(self, tmp_path: Path) -> None:
        """Test save_batch() persists multiple entities in single transaction."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            entities = [
                Entity(
                    entity_type="PERSON",
                    first_name="Marie",
                    last_name="Curie",
                    full_name="Marie Curie",
                    pseudonym_first="Leia",
                    pseudonym_last="Organa",
                    pseudonym_full="Leia Organa",
                    theme="star_wars",
                ),
                Entity(
                    entity_type="PERSON",
                    first_name="Pierre",
                    last_name="Curie",
                    full_name="Pierre Curie",
                    pseudonym_first="Luke",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Luke Skywalker",
                    theme="star_wars",
                ),
                Entity(
                    entity_type="PERSON",
                    first_name="Albert",
                    last_name="Einstein",
                    full_name="Albert Einstein",
                    pseudonym_first="Han",
                    pseudonym_last="Solo",
                    pseudonym_full="Han Solo",
                    theme="star_wars",
                ),
            ]

            saved = repo.save_batch(entities)

            # Verify all saved
            assert len(saved) == 3
            assert all(e.id is not None for e in saved)

            # Verify decrypted fields
            assert saved[0].full_name == "Marie Curie"
            assert saved[1].full_name == "Pierre Curie"
            assert saved[2].full_name == "Albert Einstein"

    def test_find_all_with_no_filters(self, tmp_path: Path) -> None:
        """Test find_all() returns all entities when no filters applied."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save multiple entities
            repo.save(
                Entity(
                    entity_type="PERSON",
                    full_name="Person One",
                    pseudonym_full="Pseudonym One",
                    theme="neutral",
                )
            )
            repo.save(
                Entity(
                    entity_type="LOCATION",
                    full_name="Location One",
                    pseudonym_full="Place One",
                    theme="neutral",
                )
            )

            entities = repo.find_all()
            assert len(entities) >= 2  # May have more from other tests

    def test_find_all_filter_by_entity_type(self, tmp_path: Path) -> None:
        """Test find_all() filters by entity_type correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save different entity types
            repo.save(
                Entity(
                    entity_type="PERSON",
                    full_name="Person One",
                    pseudonym_full="Pseudonym One",
                    theme="neutral",
                )
            )
            repo.save(
                Entity(
                    entity_type="LOCATION",
                    full_name="Location One",
                    pseudonym_full="Place One",
                    theme="neutral",
                )
            )

            persons = repo.find_all(entity_type="PERSON")
            locations = repo.find_all(entity_type="LOCATION")

            assert all(e.entity_type == "PERSON" for e in persons)
            assert all(e.entity_type == "LOCATION" for e in locations)

    def test_find_all_filter_by_is_ambiguous(self, tmp_path: Path) -> None:
        """Test find_all() filters by is_ambiguous correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save ambiguous and non-ambiguous entities
            repo.save(
                Entity(
                    entity_type="PERSON",
                    full_name="Ambiguous Person",
                    pseudonym_full="Pseudonym One",
                    theme="neutral",
                    is_ambiguous=True,
                    ambiguity_reason="Multiple matches",
                )
            )
            repo.save(
                Entity(
                    entity_type="PERSON",
                    full_name="Clear Person",
                    pseudonym_full="Pseudonym Two",
                    theme="neutral",
                    is_ambiguous=False,
                )
            )

            ambiguous = repo.find_all(is_ambiguous=True)
            clear = repo.find_all(is_ambiguous=False)

            assert all(e.is_ambiguous for e in ambiguous)
            assert all(not e.is_ambiguous for e in clear)

    def test_save_duplicate_full_name_raises_error(self, tmp_path: Path) -> None:
        """Test saving entity with duplicate full_name raises DuplicateEntityError."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save first entity
            entity1 = Entity(
                entity_type="PERSON",
                full_name="Duplicate Name",
                pseudonym_full="Pseudonym One",
                theme="neutral",
            )
            repo.save(entity1)

            # Attempt to save entity with same full_name
            entity2 = Entity(
                entity_type="PERSON",
                full_name="Duplicate Name",
                pseudonym_full="Pseudonym Two",
                theme="neutral",
            )

            with pytest.raises(DuplicateEntityError, match="already exists"):
                repo.save(entity2)

    def test_encrypted_values_in_database(self, tmp_path: Path) -> None:
        """Test that sensitive fields are actually encrypted in database."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            # Save entity
            entity = Entity(
                entity_type="PERSON",
                first_name="SecretFirst",
                last_name="SecretLast",
                full_name="SecretFirst SecretLast",
                pseudonym_first="PseudoFirst",
                pseudonym_last="PseudoLast",
                pseudonym_full="PseudoFirst PseudoLast",
                theme="neutral",
            )
            repo.save(entity)

            # Query raw database (bypassing repository)
            raw_entity = db_session.session.query(Entity).first()

            # Verify fields are encrypted (not plaintext)
            assert "SecretFirst" not in str(raw_entity.first_name)
            assert "SecretLast" not in str(raw_entity.last_name)
            assert "SecretFirst SecretLast" not in str(raw_entity.full_name)
            assert "PseudoFirst" not in str(raw_entity.pseudonym_first)
            assert "PseudoLast" not in str(raw_entity.pseudonym_last)
            assert "PseudoFirst PseudoLast" not in str(raw_entity.pseudonym_full)

    def test_cross_session_consistency(self, tmp_path: Path) -> None:
        """Test entity saved in one session can be queried in another."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        # Save in first session
        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            entity = Entity(
                entity_type="PERSON",
                full_name="Cross Session Test",
                pseudonym_full="Test Pseudonym",
                theme="neutral",
            )
            repo.save(entity)

        # Query in second session
        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            found = repo.find_by_full_name("Cross Session Test")

            assert found is not None
            assert found.full_name == "Cross Session Test"
            assert found.pseudonym_full == "Test Pseudonym"

    def test_save_with_none_optional_fields(self, tmp_path: Path) -> None:
        """Test save handles None values in optional fields correctly."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            entity = Entity(
                entity_type="LOCATION",
                first_name=None,  # LOCATION doesn't have first/last names
                last_name=None,
                full_name="Paris",
                pseudonym_first=None,
                pseudonym_last=None,
                pseudonym_full="Coruscant",
                theme="star_wars",
                gender=None,
                confidence_score=None,
                ambiguity_reason=None,
            )

            saved = repo.save(entity)

            assert saved.first_name is None
            assert saved.last_name is None
            assert saved.full_name == "Paris"
            assert saved.pseudonym_full == "Coruscant"
