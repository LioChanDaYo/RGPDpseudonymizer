"""Story 10.7: mapping rows keyed on (text, type) in the repository.

AC1 (two rows and two pseudonyms for one text under two types, one row for
the same text and type), AC3 (a new database writes the new schema version and
the (text, type) key) and AC4 (lookups by text and type, every row of a text,
the deletion of every row of a text, the race fallback). Invented names only
(AC11).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    MappingRepository,
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DuplicateEntityError
from tests.unit.pre_10_7_database import read_schema_version, unique_index_columns

PASSPHRASE = "zorbalia_repo_pass_123!"

NEW_SCHEMA_VERSION = "1.1.0"  # Story 10.7, AC3 (Task 2.2)


def _entity(entity_type: str, full_name: str, pseudonym: str) -> Entity:
    return Entity(
        entity_type=entity_type,
        full_name=full_name,
        pseudonym_full=pseudonym,
        theme="neutral",
    )


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "mappings.db"
    init_database(str(path), PASSPHRASE)
    return path


def _save_or_none(repo: SQLiteMappingRepository, entity: Entity) -> Entity | None:
    """Save, or None if the text is rejected as a duplicate."""
    try:
        return repo.save(entity)
    except DuplicateEntityError:
        return None


class TestTwoTypesOneText:
    """AC1: one row and one pseudonym per (text, type)."""

    def test_save_same_text_two_types_gives_two_rows(self, db_path: Path) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))
            org = _save_or_none(repo, _entity("ORG", "Zorbaville", "Zorbtech"))

            assert org is not None, "the ORG row was rejected as a duplicate text"
            rows = sorted(
                (e.entity_type, e.pseudonym_full)
                for e in repo.find_all()
                if e.full_name == "Zorbaville"
            )
        assert rows == [("LOCATION", "Quentrel"), ("ORG", "Zorbtech")]

    def test_save_same_text_same_type_is_still_a_duplicate(self, db_path: Path) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))
            with pytest.raises(DuplicateEntityError):
                repo.save(_entity("LOCATION", "Zorbaville", "Zorbtech"))
            assert len(repo.find_all()) == 1

    def test_find_by_full_name_and_type_returns_each_row(self, db_path: Path) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))
            _save_or_none(repo, _entity("ORG", "Zorbaville", "Zorbtech"))

            location = repo.find_by_full_name_and_type("Zorbaville", "LOCATION")
            org = repo.find_by_full_name_and_type("Zorbaville", "ORG")
            person = repo.find_by_full_name_and_type("Zorbaville", "PERSON")

        assert location is not None and location.pseudonym_full == "Quentrel"
        assert org is not None and org.pseudonym_full == "Zorbtech"
        assert person is None

    def test_find_all_by_full_name_returns_every_row(self, db_path: Path) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))
            _save_or_none(repo, _entity("ORG", "Zorbaville", "Zorbtech"))
            repo.save(_entity("PERSON", "Zorbalia", "Quentrix"))

            rows = repo.find_all_by_full_name("Zorbaville")
            missing = repo.find_all_by_full_name("Quentrel")

        assert sorted((e.entity_type, e.full_name) for e in rows) == [
            ("LOCATION", "Zorbaville"),
            ("ORG", "Zorbaville"),
        ]
        assert missing == []


class TestDeletionByText:
    """AC4: deleting by text removes every row of the text, never one only."""

    def test_delete_entities_by_full_name_deletes_every_row(
        self, db_path: Path
    ) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))
            _save_or_none(repo, _entity("ORG", "Zorbaville", "Zorbtech"))
            repo.save(_entity("PERSON", "Zorbalia", "Quentrix"))

            deleted = repo.delete_entities_by_full_name("Zorbaville")
            remaining = [(e.entity_type, e.full_name) for e in repo.find_all()]

        assert sorted((e.entity_type, e.pseudonym_full) for e in deleted) == [
            ("LOCATION", "Quentrel"),
            ("ORG", "Zorbtech"),
        ]
        assert remaining == [("PERSON", "Zorbalia")]

    def test_delete_entities_by_full_name_unknown_text(self, db_path: Path) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("PERSON", "Zorbalia", "Quentrix"))
            deleted = repo.delete_entities_by_full_name("Zorbaville")
            assert deleted == []
            assert len(repo.find_all()) == 1

    def test_text_only_and_one_row_methods_are_gone(self) -> None:
        """No caller can look a text up without its type or erase part of a name."""
        assert not hasattr(MappingRepository, "find_by_full_name")
        assert not hasattr(MappingRepository, "delete_entity_by_full_name")
        assert not hasattr(SQLiteMappingRepository, "find_by_full_name")
        assert not hasattr(SQLiteMappingRepository, "delete_entity_by_full_name")


class TestRaceFallback:
    """AC4: the save_batch race fallback looks rows up by (text, type)."""

    def test_fallback_returns_the_stored_row_of_the_same_type(
        self, db_path: Path
    ) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))

            saved = repo.save_batch([_entity("LOCATION", "Zorbaville", "Zorbtech")])

            assert [(e.entity_type, e.pseudonym_full) for e in saved] == [
                ("LOCATION", "Quentrel")
            ]
            assert len(repo.find_all()) == 1

    def test_fallback_saves_a_text_stored_under_another_type_only(
        self, db_path: Path
    ) -> None:
        with open_database(str(db_path), PASSPHRASE) as session:
            repo = SQLiteMappingRepository(session)
            repo.save(_entity("LOCATION", "Zorbaville", "Quentrel"))

            # The LOCATION duplicate makes the batch insert fail, so each
            # entity goes through the one-by-one fallback.
            saved = repo.save_batch(
                [
                    _entity("LOCATION", "Zorbaville", "Zorbtech"),
                    _entity("ORG", "Zorbaville", "Quentrix"),
                ]
            )
            rows = sorted(
                (e.entity_type, e.pseudonym_full)
                for e in repo.find_all()
                if e.full_name == "Zorbaville"
            )

        assert [(e.entity_type, e.pseudonym_full) for e in saved] == [
            ("LOCATION", "Quentrel"),
            ("ORG", "Quentrix"),
        ]
        assert rows == [("LOCATION", "Quentrel"), ("ORG", "Quentrix")]


class TestNewDatabase:
    """AC3: a database created by 10.7 has the new version and the (text, type) key."""

    def test_new_database_schema_version_and_unique_key(self, db_path: Path) -> None:
        assert read_schema_version(db_path) == NEW_SCHEMA_VERSION
        assert unique_index_columns(db_path) == [["full_name", "entity_type"]]
