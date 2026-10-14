"""Story 10.7: the core keys its lookups and per-run caches on (text, type).

AC1 (one row and one pseudonym per (key, type)), AC2 (the validation preview,
the known/unknown split before validation, ``_resolve_pseudonyms`` and their
caches are type-aware; ``_check_component_match`` is unchanged) and the AC1
precisions (one span with both types, two rows for one key never share a
pseudonym). Every test uses a real temporary database and the real pseudonym
engine (theme ``star_wars``, whose person, place and organisation lists do not
overlap), through ``_build_pseudonym_assigner``, ``_run_validation``,
``_resolve_pseudonyms`` and ``process_document``. Invented names only (AC11).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DuplicateEntityError
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
)
from gdpr_pseudonymizer.pseudonym.library_manager import (
    LibraryBasedPseudonymManager,
)
from tests.unit.pre_10_7_database import (
    LegacyRow,
    build_pre_10_7_database,
    read_schema_version,
)

PASSPHRASE = "zorbalia_core_pass_123!"
THEME = "star_wars"


def _entity(text: str, entity_type: str, start: int) -> DetectedEntity:
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
        confidence=0.9,
        source="spacy",
    )


def _stored(
    entity_type: str,
    full_name: str,
    pseudonym: str,
    **components: Any,
) -> Entity:
    return Entity(
        entity_type=entity_type,
        full_name=full_name,
        pseudonym_full=pseudonym,
        theme=THEME,
        **components,
    )


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "mappings.db"
    init_database(str(path), PASSPHRASE)
    return path


def _store(db_path: Path, *entities: Entity) -> None:
    with open_database(str(db_path), PASSPHRASE) as session:
        repo = SQLiteMappingRepository(session)
        for entity in entities:
            repo.save(entity)


def _rows(db_path: Path, full_name: str) -> list[tuple[str, str]]:
    """(type, pseudonym) of every stored row of one text, sorted."""
    with open_database(str(db_path), PASSPHRASE) as session:
        return sorted(
            (e.entity_type, e.pseudonym_full)
            for e in SQLiteMappingRepository(session).find_all()
            if e.full_name == full_name
        )


def _processor(db_path: Path) -> DocumentProcessor:
    return DocumentProcessor(db_path=str(db_path), passphrase=PASSPHRASE, theme=THEME)


class _ReviewRecorder:
    """Stands in for the interactive review: records and confirms every entity."""

    def __init__(self) -> None:
        self.reviewed: list[DetectedEntity] = []

    def __call__(
        self,
        entities: list[DetectedEntity],
        document_text: str,
        document_path: str = "",
        pseudonym_assigner: Any = None,
    ) -> list[DetectedEntity]:
        self.reviewed.extend(entities)
        return list(entities)


def _validate(
    db_path: Path, detected: list[DetectedEntity], text: str
) -> tuple[list[DetectedEntity], list[DetectedEntity]]:
    """(entities sent to review, validated list) through _run_validation."""
    processor = _processor(db_path)
    recorder = _ReviewRecorder()
    with open_database(str(db_path), PASSPHRASE) as session:
        ctx = processor._init_processing_context(session)
        assigner = processor._build_pseudonym_assigner(ctx)
        with patch(
            "gdpr_pseudonymizer.core.document_processor.run_validation_workflow",
            side_effect=recorder,
        ):
            validated = processor._run_validation(
                ctx=ctx,
                detected_entities=detected,
                document_text=text,
                input_path="zorbaville.txt",
                skip_validation=False,
                pseudonym_assigner=assigner,
            )
    return recorder.reviewed, validated


def _resolve(db_path: Path, validated: list[DetectedEntity]) -> list[str]:
    """Pseudonym given to each validated entity, in order (rows are saved)."""
    processor = _processor(db_path)
    with open_database(str(db_path), PASSPHRASE) as session:
        ctx = processor._init_processing_context(session)
        result = processor._resolve_pseudonyms(ctx, validated)
    by_span = {(start, end): text for start, end, text in result.replacements}
    assert len(result.replacements) == len(validated)
    return [by_span[(e.start_pos, e.end_pos)] for e in validated]


class TestPreview:
    """AC2: the validation preview and its cache key on (key, type)."""

    def test_two_types_get_two_previews_in_one_run(self, db_path: Path) -> None:
        processor = _processor(db_path)
        with open_database(str(db_path), PASSPHRASE) as session:
            ctx = processor._init_processing_context(session)
            assigner = processor._build_pseudonym_assigner(ctx)
            location = assigner(_entity("Zorbaville", "LOCATION", 0))
            org = assigner(_entity("Zorbaville", "ORG", 20))
            # The cache keeps both
            location_again = assigner(_entity("Zorbaville", "LOCATION", 40))
            org_again = assigner(_entity("Zorbaville", "ORG", 60))

        assert location != org
        assert location_again == location
        assert org_again == org

    def test_stored_row_previews_its_own_type_only(self, db_path: Path) -> None:
        _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrel"))
        processor = _processor(db_path)
        with open_database(str(db_path), PASSPHRASE) as session:
            ctx = processor._init_processing_context(session)
            assigner = processor._build_pseudonym_assigner(ctx)
            location = assigner(_entity("Zorbaville", "LOCATION", 0))
            org = assigner(_entity("Zorbaville", "ORG", 20))

        assert location == "Quentrel"
        assert org != "Quentrel"


class TestKnownSplit:
    """AC2: a text known only under another type reaches validation."""

    TEXT = "Zorbaville a signé avec Zorbaville."

    def test_known_under_other_type_is_not_auto_accepted(self, db_path: Path) -> None:
        _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrel"))
        org = _entity("Zorbaville", "ORG", 0)
        location = _entity("Zorbaville", "LOCATION", 24)

        reviewed, validated = _validate(db_path, [org, location], self.TEXT)

        assert reviewed == [org]
        assert validated == [location, org]

    def test_same_text_and_type_is_still_auto_accepted(self, db_path: Path) -> None:
        _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrel"))
        location = _entity("Zorbaville", "LOCATION", 24)

        reviewed, validated = _validate(db_path, [location], self.TEXT)

        assert reviewed == []
        assert validated == [location]

    def test_pre_10_7_file_is_converted_then_split_by_type(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "pre_10_7.db"
        build_pre_10_7_database(
            db_path, PASSPHRASE, [LegacyRow("LOCATION", "Zorbaville", "Quentrel")]
        )
        org = _entity("Zorbaville", "ORG", 0)
        location = _entity("Zorbaville", "LOCATION", 24)

        reviewed, validated = _validate(db_path, [org, location], self.TEXT)

        assert read_schema_version(db_path) == "1.1.0"
        assert reviewed == [org]
        assert validated == [location, org]


class TestResolution:
    """AC1, AC2: _resolve_pseudonyms and its per-run cache key on (key, type)."""

    def test_both_types_in_one_document(self, db_path: Path) -> None:
        validated = [
            _entity("Zorbaville", "LOCATION", 0),
            _entity("Zorbaville", "ORG", 20),
            _entity("Zorbaville", "LOCATION", 40),
            _entity("Zorbaville", "ORG", 60),
        ]

        pseudonyms = _resolve(db_path, validated)

        location, org = pseudonyms[0], pseudonyms[1]
        assert location != org
        assert pseudonyms == [location, org, location, org]
        assert _rows(db_path, "Zorbaville") == sorted(
            [("LOCATION", location), ("ORG", org)]
        )

    def test_same_text_and_type_reuses_one_row(self, db_path: Path) -> None:
        validated = [
            _entity("Zorbaville", "LOCATION", 0),
            _entity("Zorbaville", "LOCATION", 20),
        ]

        first_run = _resolve(db_path, validated)
        second_run = _resolve(db_path, validated[:1])

        assert first_run[0] == first_run[1]
        assert second_run == first_run[:1]
        assert _rows(db_path, "Zorbaville") == [("LOCATION", first_run[0])]

    def test_stored_type_keeps_its_pseudonym_new_type_gets_its_own(
        self, db_path: Path
    ) -> None:
        _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrel"))
        validated = [
            _entity("Zorbaville", "ORG", 0),
            _entity("Zorbaville", "LOCATION", 20),
        ]

        org, location = _resolve(db_path, validated)

        assert location == "Quentrel"
        assert org != "Quentrel"
        assert _rows(db_path, "Zorbaville") == sorted(
            [("LOCATION", "Quentrel"), ("ORG", org)]
        )

    def test_one_span_both_types_first_in_validated_list_wins(
        self, db_path: Path
    ) -> None:
        """AC1 precision: a known type comes before a newly reviewed one."""
        _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrel"))
        text = "Zorbaville est loin."
        org = _entity("Zorbaville", "ORG", 0)
        location = _entity("Zorbaville", "LOCATION", 0)
        _reviewed, validated = _validate(db_path, [org, location], text)
        processor = _processor(db_path)

        with open_database(str(db_path), PASSPHRASE) as session:
            ctx = processor._init_processing_context(session)
            result = processor._resolve_pseudonyms(ctx, validated)
        output = processor._apply_replacements(text, result.replacements)

        assert output == "Quentrel est loin."
        rows = _rows(db_path, "Zorbaville")
        assert [t for t, _p in rows] == ["LOCATION", "ORG"]
        assert rows[1][1] != "Quentrel"

    @pytest.mark.parametrize("order", ["location_first", "person_first"])
    def test_two_rows_of_one_key_never_share_a_pseudonym(
        self, order: str, db_path: Path
    ) -> None:
        """AC1 precision, pinned: a standalone PERSON component is reused
        without the library's used-pseudonym check
        (``_handle_standalone_component``). Here the place list is made to
        return that same component, so both types would get it."""
        _store(
            db_path,
            _stored(
                "PERSON",
                "Zorbalia Quentrix",
                "Quentrel Zorbtech",
                first_name="Zorbalia",
                last_name="Quentrix",
                pseudonym_first="Quentrel",
                pseudonym_last="Zorbtech",
            ),
        )
        location = _entity("Zorbalia", "LOCATION", 0)
        person = _entity("Zorbalia", "PERSON", 20)
        validated = (
            [location, person] if order == "location_first" else [person, location]
        )
        real_standalone = CompositionalPseudonymEngine._handle_standalone_component

        with (
            patch.object(
                LibraryBasedPseudonymManager,
                "_select_location",
                return_value="Quentrel",
            ),
            patch.object(
                CompositionalPseudonymEngine,
                "_handle_standalone_component",
                autospec=True,
                side_effect=real_standalone,
            ) as standalone,
        ):
            pseudonyms = _resolve(db_path, validated)

        rows = _rows(db_path, "Zorbalia")
        assert [t for t, _p in rows] == ["LOCATION", "PERSON"]
        assert rows[0][1] != rows[1][1]
        assert pseudonyms[0] != pseudonyms[1]
        assert standalone.call_count == 1

    def test_component_match_unchanged_with_other_type_present(
        self, db_path: Path
    ) -> None:
        """AC2: a PERSON first name after a PERSON full name in the same run
        still reuses the component while a LOCATION with the same text is there."""
        validated = [
            _entity("Zorbalia Quentrix", "PERSON", 0),
            _entity("Zorbalia", "LOCATION", 30),
            _entity("Zorbalia", "PERSON", 50),
        ]

        full, location, first_name = _resolve(db_path, validated)

        with open_database(str(db_path), PASSPHRASE) as session:
            stored_full = [
                e
                for e in SQLiteMappingRepository(session).find_all()
                if e.full_name == "Zorbalia Quentrix"
            ]
        assert len(stored_full) == 1
        assert first_name == stored_full[0].pseudonym_first
        assert full == stored_full[0].pseudonym_full
        assert location != first_name
        assert [t for t, _p in _rows(db_path, "Zorbalia")] == ["LOCATION"]


class TestSkipValidation:
    """AC2: the skip_validation path (batch workers) resolves by type, no review."""

    def test_process_document_gives_one_pseudonym_per_type(
        self, db_path: Path, tmp_path: Path
    ) -> None:
        text = "Zorbaville a signé avec Zorbaville."
        input_path = tmp_path / "zorbaville.txt"
        output_path = tmp_path / "zorbaville_out.txt"
        input_path.write_text(text, encoding="utf-8")
        org = _entity("Zorbaville", "ORG", 0)
        location = _entity("Zorbaville", "LOCATION", 24)
        processor = _processor(db_path)
        recorder = _ReviewRecorder()

        with (
            patch.object(
                DocumentProcessor,
                "_detect_and_filter_entities",
                return_value=[org, location],
            ),
            patch.object(
                DocumentProcessor, "_get_model_version", return_value="test-model"
            ),
            patch(
                "gdpr_pseudonymizer.core.document_processor.run_validation_workflow",
                side_effect=recorder,
            ),
        ):
            result = processor.process_document(
                str(input_path), str(output_path), skip_validation=True
            )

        assert result.success, result.error_message
        assert recorder.reviewed == []
        rows = _rows(db_path, "Zorbaville")
        assert [t for t, _p in rows] == ["LOCATION", "ORG"]
        location_pseudonym, org_pseudonym = rows[0][1], rows[1][1]
        assert location_pseudonym != org_pseudonym
        expected = f"{org_pseudonym} a signé avec {location_pseudonym}."
        assert output_path.read_text(encoding="utf-8") == expected


def test_store_helper_rejects_same_text_same_type(db_path: Path) -> None:
    """The fixtures above rely on one row per (text, type), as before."""
    _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrel"))
    with pytest.raises(DuplicateEntityError):
        _store(db_path, _stored("LOCATION", "Zorbaville", "Quentrix"))
