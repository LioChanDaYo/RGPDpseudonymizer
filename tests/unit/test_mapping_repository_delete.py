"""Unit tests for MappingRepository delete and search methods (Story 5.1)."""

from __future__ import annotations

from pathlib import Path

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)


def _create_test_entity(**overrides: object) -> Entity:
    """Create a test entity with sensible defaults."""
    defaults = {
        "entity_type": "PERSON",
        "first_name": "Marie",
        "last_name": "Dupont",
        "full_name": "Marie Dupont",
        "pseudonym_first": "Leia",
        "pseudonym_last": "Organa",
        "pseudonym_full": "Leia Organa",
        "theme": "star_wars",
        "gender": "female",
        "confidence_score": 0.92,
    }
    defaults.update(overrides)
    return Entity(**defaults)


class TestDeleteEntityByFullName:
    """Tests for delete_entity_by_full_name()."""

    def test_delete_existing_entity_returns_decrypted(self, tmp_path: Path) -> None:
        """Deleting an existing entity returns the decrypted entity."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(_create_test_entity())

            deleted = repo.delete_entity_by_full_name("Marie Dupont")

            assert deleted is not None
            assert deleted.full_name == "Marie Dupont"
            assert deleted.pseudonym_full == "Leia Organa"
            assert deleted.entity_type == "PERSON"

    def test_delete_entity_actually_removes_from_database(self, tmp_path: Path) -> None:
        """After deletion, entity is no longer findable."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(_create_test_entity())

            repo.delete_entity_by_full_name("Marie Dupont")

            assert repo.find_by_full_name("Marie Dupont") is None
            assert len(repo.find_all()) == 0

    def test_delete_nonexistent_returns_none(self, tmp_path: Path) -> None:
        """Deleting a nonexistent entity returns None."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            result = repo.delete_entity_by_full_name("Nobody")
            assert result is None

    def test_delete_does_not_affect_other_entities(self, tmp_path: Path) -> None:
        """Deleting one entity leaves others intact."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(
                _create_test_entity(
                    full_name="Marie Dupont", first_name="Marie", last_name="Dupont"
                )
            )
            repo.save(
                _create_test_entity(
                    full_name="Jean Martin",
                    first_name="Jean",
                    last_name="Martin",
                    pseudonym_first="Luke",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Luke Skywalker",
                )
            )

            repo.delete_entity_by_full_name("Marie Dupont")

            remaining = repo.find_all()
            assert len(remaining) == 1
            assert remaining[0].full_name == "Jean Martin"


class TestDeleteEntityById:
    """Tests for delete_entity_by_id()."""

    def test_delete_by_id_success(self, tmp_path: Path) -> None:
        """Deleting by ID returns decrypted entity."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            saved = repo.save(_create_test_entity())

            deleted = repo.delete_entity_by_id(saved.id)

            assert deleted is not None
            assert deleted.full_name == "Marie Dupont"
            assert deleted.id == saved.id

    def test_delete_by_id_removes_from_database(self, tmp_path: Path) -> None:
        """After deletion by ID, entity is gone."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            saved = repo.save(_create_test_entity())

            repo.delete_entity_by_id(saved.id)

            assert repo.find_by_full_name("Marie Dupont") is None

    def test_delete_by_id_not_found(self, tmp_path: Path) -> None:
        """Deleting by nonexistent ID returns None."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)

            result = repo.delete_entity_by_id("nonexistent-uuid")
            assert result is None

    def test_delete_by_id_returns_decrypted_for_audit(self, tmp_path: Path) -> None:
        """Returned entity has all decrypted fields for audit logging."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            saved = repo.save(_create_test_entity())

            deleted = repo.delete_entity_by_id(saved.id)

            assert deleted is not None
            assert deleted.first_name == "Marie"
            assert deleted.last_name == "Dupont"
            assert deleted.pseudonym_first == "Leia"
            assert deleted.pseudonym_last == "Organa"
            assert deleted.theme == "star_wars"


class TestSearchEntities:
    """Tests for search_entities()."""

    def test_search_all_returns_all(self, tmp_path: Path) -> None:
        """No filters returns all entities."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(
                _create_test_entity(
                    full_name="Marie Dupont", first_name="Marie", last_name="Dupont"
                )
            )
            repo.save(
                _create_test_entity(
                    full_name="Jean Martin",
                    first_name="Jean",
                    last_name="Martin",
                    pseudonym_first="Luke",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Luke Skywalker",
                )
            )

            results = repo.search_entities()
            assert len(results) == 2

    def test_search_by_name_substring(self, tmp_path: Path) -> None:
        """Search filters by case-insensitive substring match on name."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(
                _create_test_entity(
                    full_name="Marie Dupont", first_name="Marie", last_name="Dupont"
                )
            )
            repo.save(
                _create_test_entity(
                    full_name="Jean Martin",
                    first_name="Jean",
                    last_name="Martin",
                    pseudonym_first="Luke",
                    pseudonym_last="Skywalker",
                    pseudonym_full="Luke Skywalker",
                )
            )

            results = repo.search_entities(search_term="dupont")
            assert len(results) == 1
            assert results[0].full_name == "Marie Dupont"

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        """Search is case-insensitive."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(_create_test_entity())

            results = repo.search_entities(search_term="MARIE")
            assert len(results) == 1

    def test_search_by_pseudonym(self, tmp_path: Path) -> None:
        """Search also matches pseudonym names."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(_create_test_entity())

            results = repo.search_entities(search_term="leia")
            assert len(results) == 1

    def test_search_by_type(self, tmp_path: Path) -> None:
        """Type filter restricts results."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(_create_test_entity())
            repo.save(
                _create_test_entity(
                    entity_type="LOCATION",
                    full_name="Paris",
                    first_name=None,
                    last_name=None,
                    pseudonym_first=None,
                    pseudonym_last=None,
                    pseudonym_full="Coruscant",
                    gender=None,
                )
            )

            results = repo.search_entities(entity_type="PERSON")
            assert len(results) == 1
            assert results[0].entity_type == "PERSON"

    def test_search_no_results(self, tmp_path: Path) -> None:
        """Search with no matches returns empty list."""
        db_path = tmp_path / "test.db"
        passphrase = "test_passphrase_123!"
        init_database(str(db_path), passphrase)

        with open_database(str(db_path), passphrase) as db_session:
            repo = SQLiteMappingRepository(db_session)
            repo.save(_create_test_entity())

            results = repo.search_entities(search_term="zzz_nonexistent")
            assert len(results) == 0
