"""Unit tests for neutral_id theme integration in LibraryBasedPseudonymManager."""

from __future__ import annotations

from types import SimpleNamespace

from gdpr_pseudonymizer.pseudonym.library_manager import (
    LibraryBasedPseudonymManager,
)


class TestLoadLibraryNeutralId:
    """Tests for loading the neutral_id theme."""

    def test_load_library_neutral_id(self) -> None:
        """load_library('neutral_id') sets theme and initialises generator."""
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral_id")

        assert manager.theme == "neutral_id"
        assert manager._neutral_id_generator is not None
        # No JSON library loaded — lists stay empty
        assert manager.last_names == []


class TestAssignNeutralIdPseudonym:
    """Tests for neutral_id pseudonym assignment."""

    def _make_manager(self) -> LibraryBasedPseudonymManager:
        manager = LibraryBasedPseudonymManager()
        manager.load_library("neutral_id")
        return manager

    def test_assign_neutral_id_person_compound(self) -> None:
        """Compound PERSON name → PER-001 with -P and -N components."""
        manager = self._make_manager()
        result = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Marie", last_name="Dupont"
        )
        assert result.pseudonym_full == "PER-001"
        assert result.pseudonym_first == "PER-001-P"
        assert result.pseudonym_last == "PER-001-N"
        assert result.theme == "neutral_id"
        assert result.exhaustion_percentage == 0.0

    def test_assign_neutral_id_person_single(self) -> None:
        """Single PERSON name → PER-001 with no components."""
        manager = self._make_manager()
        result = manager.assign_pseudonym(entity_type="PERSON", first_name="Marie")
        assert result.pseudonym_full == "PER-001"
        assert result.pseudonym_first is None
        assert result.pseudonym_last is None

    def test_assign_neutral_id_location(self) -> None:
        """LOCATION → LOC-001."""
        manager = self._make_manager()
        result = manager.assign_pseudonym(entity_type="LOCATION")
        assert result.pseudonym_full == "LOC-001"
        assert result.pseudonym_first is None
        assert result.pseudonym_last is None

    def test_assign_neutral_id_org(self) -> None:
        """ORG → ORG-001."""
        manager = self._make_manager()
        result = manager.assign_pseudonym(entity_type="ORG")
        assert result.pseudonym_full == "ORG-001"

    def test_neutral_id_exhaustion_zero(self) -> None:
        """check_exhaustion() always returns 0.0 for neutral_id."""
        manager = self._make_manager()
        manager.assign_pseudonym(entity_type="PERSON", first_name="A", last_name="B")
        manager.assign_pseudonym(entity_type="LOCATION")
        assert manager.check_exhaustion() == 0.0

    def test_neutral_id_compositional_reuse(self) -> None:
        """Standalone 'Marie' after compound 'Marie Dupont' gets PER-002, not PER-001-P."""
        manager = self._make_manager()
        # Compound name first
        r1 = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Marie", last_name="Dupont"
        )
        assert r1.pseudonym_full == "PER-001"

        # Same first name standalone — should get its own identifier
        r2 = manager.assign_pseudonym(entity_type="PERSON", first_name="Marie")
        assert r2.pseudonym_full == "PER-002"

    def test_neutral_id_existing_mappings_restore_counter(self) -> None:
        """Loading existing PER-003 mapping → next assignment is PER-004."""
        manager = self._make_manager()

        # Simulate existing entities from database
        existing = [
            SimpleNamespace(
                entity_type="PERSON",
                first_name="Alice",
                last_name="Martin",
                pseudonym_full="PER-003",
                pseudonym_first="PER-003-P",
                pseudonym_last="PER-003-N",
            ),
            SimpleNamespace(
                entity_type="LOCATION",
                first_name=None,
                last_name=None,
                pseudonym_full="LOC-002",
                pseudonym_first=None,
                pseudonym_last=None,
            ),
        ]
        manager.load_existing_mappings(existing)

        # Next PERSON should be PER-004
        result = manager.assign_pseudonym(
            entity_type="PERSON", first_name="Bob", last_name="Leroy"
        )
        assert result.pseudonym_full == "PER-004"

        # Next LOCATION should be LOC-003
        result_loc = manager.assign_pseudonym(entity_type="LOCATION")
        assert result_loc.pseudonym_full == "LOC-003"

    def test_neutral_id_sequential_multiple(self) -> None:
        """Multiple assignments across types maintain correct counters."""
        manager = self._make_manager()
        assert (
            manager.assign_pseudonym(
                entity_type="PERSON", first_name="A", last_name="B"
            ).pseudonym_full
            == "PER-001"
        )
        assert manager.assign_pseudonym(entity_type="ORG").pseudonym_full == "ORG-001"
        assert (
            manager.assign_pseudonym(
                entity_type="PERSON", first_name="C", last_name="D"
            ).pseudonym_full
            == "PER-002"
        )
        assert (
            manager.assign_pseudonym(entity_type="LOCATION").pseudonym_full == "LOC-001"
        )
        assert manager.assign_pseudonym(entity_type="ORG").pseudonym_full == "ORG-002"
