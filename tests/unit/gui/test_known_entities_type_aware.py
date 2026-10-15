"""Story 10.7, AC4: the desktop app's known-entity check keys on (key, type).

``GUIValidationState.classify_known_entities`` marks a review as known only
when its text, normalized with the core's key function, is stored under the
review's own type. A pre-10.7 file is converted first; a conversion that
cannot be made leaves every review pending (PO S7). Real temporary databases.
Invented names only (AC11).
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState
from tests.unit.pre_10_7_database import (
    LegacyRow,
    build_pre_10_7_database,
    read_schema_version,
)

PASSPHRASE = "zorbalia_gui_pass_123!"
TEXT = "Zorbaville et Dr Zorbalia ont signé à Zorbaville."


def _entity(text: str, entity_type: str) -> DetectedEntity:
    start = TEXT.find(text)
    if entity_type == "LOCATION":
        start = TEXT.rfind(text)
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
        confidence=0.9,
        source="spacy",
    )


def _state(db_path: Path, entities: list[DetectedEntity]) -> GUIValidationState:
    state = GUIValidationState()
    state.init_from_detection_result(
        DetectionResult(
            document_text=TEXT,
            detected_entities=entities,
            pseudonym_previews={},
            entity_type_counts={},
            db_path=str(db_path),
            passphrase=PASSPHRASE,
            theme="neutral",
            input_file="zorbaville.txt",
            detection_time_seconds=0.0,
        )
    )
    state.classify_known_entities(str(db_path), PASSPHRASE)
    return state


def _known(state: GUIValidationState) -> list[tuple[str, str, EntityReviewState]]:
    """(text, type, state) of each review marked known, sorted."""
    return sorted(
        (r.entity.text, r.entity.entity_type, r.state)
        for r in state.get_all_entities()
        if state.is_entity_known(r.entity_id)
    )


def _new_db(tmp_path: Path, *rows: tuple[str, str, str]) -> Path:
    path = tmp_path / "mappings.db"
    init_database(str(path), PASSPHRASE)
    with open_database(str(path), PASSPHRASE) as session:
        repo = SQLiteMappingRepository(session)
        for entity_type, name, pseudonym in rows:
            repo.save(
                Entity(
                    entity_type=entity_type,
                    full_name=name,
                    pseudonym_full=pseudonym,
                    theme="neutral",
                )
            )
    return path


def test_stored_location_does_not_mark_org_known(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    db_path = _new_db(tmp_path, ("LOCATION", "Zorbaville", "Quentrel"))
    org = _entity("Zorbaville", "ORG")
    location = _entity("Zorbaville", "LOCATION")

    state = _state(db_path, [org, location])

    assert _known(state) == [
        ("Zorbaville", "LOCATION", EntityReviewState.CONFIRMED),
    ]
    org_review = next(
        r for r in state.get_all_entities() if r.entity.entity_type == "ORG"
    )
    assert org_review.state == EntityReviewState.PENDING
    location_review = next(
        r for r in state.get_all_entities() if r.entity.entity_type == "LOCATION"
    )
    assert location_review.suggested_pseudonym == "Quentrel"


def test_titled_form_is_known_with_the_core_key(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    db_path = _new_db(tmp_path, ("PERSON", "Zorbalia", "Quentrix"))
    titled = _entity("Dr Zorbalia", "PERSON")

    state = _state(db_path, [titled])

    assert _known(state) == [("Dr Zorbalia", "PERSON", EntityReviewState.CONFIRMED)]
    assert state.get_all_entities()[0].suggested_pseudonym == "Quentrix"


def test_pre_10_7_file_is_converted_first(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "pre_10_7.db"
    build_pre_10_7_database(
        db_path, PASSPHRASE, [LegacyRow("LOCATION", "Zorbaville", "Quentrel")]
    )

    state = _state(
        db_path, [_entity("Zorbaville", "ORG"), _entity("Zorbaville", "LOCATION")]
    )

    assert read_schema_version(db_path) == "1.1.0"
    assert _known(state) == [
        ("Zorbaville", "LOCATION", EntityReviewState.CONFIRMED),
    ]


def test_failed_conversion_leaves_every_review_pending(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "pre_10_7.db"
    build_pre_10_7_database(
        db_path, PASSPHRASE, [LegacyRow("LOCATION", "Zorbaville", "Quentrel")]
    )
    bytes_before = db_path.read_bytes()
    db_path.chmod(stat.S_IREAD)
    try:
        try:
            with open(db_path, "r+b"):
                pass
        except OSError:
            pass
        else:
            pytest.skip("the file stays writable here (e.g. running as root)")

        state = _state(
            db_path, [_entity("Zorbaville", "ORG"), _entity("Zorbaville", "LOCATION")]
        )
    finally:
        db_path.chmod(stat.S_IREAD | stat.S_IWRITE)

    assert _known(state) == []
    assert {r.state for r in state.get_all_entities()} == {EntityReviewState.PENDING}
    assert db_path.read_bytes() == bytes_before
    assert read_schema_version(db_path) == "1.0.0"
