"""Story 10.8: the desktop app keys each candidate by text, start and type.

Since Story 10.3c one span can be kept with two types (ORG and LOCATION
"Zorbaville" at 0). These tests drive the real detection worker (only
``detect_entities`` is replaced), the real variant grouping, the real
``build_pseudonym_previews`` on a temporary database, the real
``GUIValidationState`` and the real ``finalize_document``.

T1-T8 reproduce the same-span pair collisions (AC1-AC4); T10-T12 guard what
must not change (AC9). T9 is in ``tests/unit/test_preview_keys_type_aware.py``.
Invented names only (AC11). No assertion names a key format, so the same
tests hold before and after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.gui.main_window import MainWindow
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReview, EntityReviewState

PASSPHRASE = "zorbalia_pass_A_123!"

# Pair: ORG "Zorbaville" at 0 and at 21, LOCATION "Zorbaville" at 0.
PAIR_TEXT = "Zorbaville a signé à Zorbaville."
PAIR_NAME = "Zorbaville"
PAIR_ORDERS = ["org_first", "location_first"]

# Preview pair: PERSON and ORG "Dr Zorbalia" at 0.
PREVIEW_TEXT = "Dr Zorbalia a signé."
PREVIEW_NAME = "Dr Zorbalia"
PREVIEW_ORDERS = ["person_first", "org_first"]

# Single-type group: PERSON "Quentrel Zorbalia" at 0 and at 63.
GROUP_TEXT = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
GROUP_NAME = "Quentrel Zorbalia"

CONFIRMED = EntityReviewState.CONFIRMED
PENDING = EntityReviewState.PENDING
REJECTED = EntityReviewState.REJECTED


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _entity(
    document_text: str,
    name: str,
    entity_type: str,
    nth: int,
    source: str = "spacy",
    is_ambiguous: bool = False,
) -> DetectedEntity:
    """The nth occurrence of ``name`` in ``document_text`` (0-based)."""
    start = -1
    for _ in range(nth + 1):
        start = document_text.find(name, start + 1)
    end = start + len(name)
    assert start >= 0
    assert document_text[start:end] == name
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=end,
        confidence=0.9,
        source=source,
        is_ambiguous=is_ambiguous,
    )


def _pair(order: str) -> list[DetectedEntity]:
    org_0 = _entity(PAIR_TEXT, PAIR_NAME, "ORG", 0)
    org_21 = _entity(PAIR_TEXT, PAIR_NAME, "ORG", 1)
    location_0 = _entity(
        PAIR_TEXT, PAIR_NAME, "LOCATION", 0, source="regex", is_ambiguous=True
    )
    if order == "org_first":
        return [org_0, org_21, location_0]
    return [location_0, org_0, org_21]


def _preview_pair(order: str) -> list[DetectedEntity]:
    person = _entity(PREVIEW_TEXT, PREVIEW_NAME, "PERSON", 0)
    org = _entity(
        PREVIEW_TEXT, PREVIEW_NAME, "ORG", 0, source="regex", is_ambiguous=True
    )
    if order == "person_first":
        return [person, org]
    return [org, person]


def _group() -> list[DetectedEntity]:
    return [
        _entity(GROUP_TEXT, GROUP_NAME, "PERSON", 0),
        _entity(GROUP_TEXT, GROUP_NAME, "PERSON", 1),
    ]


def _detect(
    db_path: str, document_text: str, entities: list[DetectedEntity]
) -> DetectionResult:
    """Run the real DetectionWorker synchronously, detection replaced only."""
    finished: list[object] = []
    errors: list[str] = []
    worker = DetectionWorker(
        file_path="zorbaville.txt", db_path=db_path, passphrase=PASSPHRASE
    )
    worker.setAutoDelete(False)
    worker.signals.finished.connect(finished.append)
    worker.signals.error.connect(errors.append)
    with patch.object(
        DocumentProcessor,
        "detect_entities",
        return_value=(document_text, list(entities)),
    ):
        worker.run()
    # Precondition: the worker emitted ``finished`` once and no ``error``.
    assert errors == []
    assert len(finished) == 1
    result = finished[0]
    assert isinstance(result, DetectionResult)
    return result


def _state(result: DetectionResult) -> GUIValidationState:
    state = GUIValidationState()
    state.init_from_detection_result(result)
    return state


def _rows_by_type(state: GUIValidationState) -> dict[str, EntityReview]:
    """One review row per type (the canonical rows of a same-span pair)."""
    rows: dict[str, EntityReview] = {}
    for review in state.get_all_entities():
        assert review.entity.entity_type not in rows
        rows[review.entity.entity_type] = review
    return rows


def _spans(entities: list[DetectedEntity]) -> list[tuple[str, int, int]]:
    return sorted((e.entity_type, e.start_pos, e.end_pos) for e in entities)


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "mappings.db")
    init_database(path, PASSPHRASE)
    return path


# ----------------------------------------------------------------------
# T1-T8: same-span pair collisions (fail on the unfixed keys)
# ----------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces the pair's occurrences dropped or retyped at "
        "finalization on the unfixed keys; fixed in Task 2"
    ),
)
@pytest.mark.parametrize("order", PAIR_ORDERS)
def test_pair_confirmed_finalizes_every_occurrence(
    qtbot, db_path: str, tmp_path: Path, order: str  # type: ignore[no-untyped-def]
) -> None:
    """T1 (AC2): both rows accepted send every occurrence once, own type."""
    state = _state(_detect(db_path, PAIR_TEXT, _pair(order)))
    rows = _rows_by_type(state)
    state.accept_entity(rows["ORG"].entity_id)
    state.accept_entity(rows["LOCATION"].entity_id)

    expanded = state.expand_validated_entities()
    assert _spans(expanded) == [
        ("LOCATION", 0, 10),
        ("ORG", 0, 10),
        ("ORG", 21, 31),
    ]

    output = tmp_path / "zorbaville_out.txt"
    result = DocumentProcessor(
        db_path=db_path, passphrase=PASSPHRASE
    ).finalize_document(PAIR_TEXT, expanded, str(output))
    assert result.success
    assert PAIR_NAME not in output.read_text(encoding="utf-8")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces a LOCATION reject reaching the ORG row on the "
        "unfixed keys; fixed in Task 2"
    ),
)
@pytest.mark.parametrize("order", PAIR_ORDERS)
def test_reject_location_keeps_org(
    qtbot, db_path: str, order: str  # type: ignore[no-untyped-def]
) -> None:
    """T2 (AC3): rejecting the LOCATION row leaves the ORG row as it is."""
    state = _state(_detect(db_path, PAIR_TEXT, _pair(order)))
    rows = _rows_by_type(state)
    org, location = rows["ORG"], rows["LOCATION"]

    state.reject_entity(location.entity_id)
    assert org.state == PENDING

    state.accept_entity(org.entity_id)
    assert org.state == CONFIRMED
    assert location.state == REJECTED
    assert _spans(state.expand_validated_entities()) == [
        ("ORG", 0, 10),
        ("ORG", 21, 31),
    ]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces an ORG reject reaching the LOCATION row on the "
        "unfixed keys; fixed in Task 2"
    ),
)
@pytest.mark.parametrize("order", PAIR_ORDERS)
def test_reject_org_keeps_location(
    qtbot, db_path: str, order: str  # type: ignore[no-untyped-def]
) -> None:
    """T3 (AC3): rejecting the ORG row leaves the LOCATION row as it is."""
    state = _state(_detect(db_path, PAIR_TEXT, _pair(order)))
    rows = _rows_by_type(state)
    org, location = rows["ORG"], rows["LOCATION"]

    state.reject_entity(org.entity_id)
    assert location.state == PENDING

    state.accept_entity(location.entity_id)
    assert _spans(state.expand_validated_entities()) == [("LOCATION", 0, 10)]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces an undo restoring both types of the pair on "
        "the unfixed keys; fixed in Task 2"
    ),
)
def test_undo_restores_only_that_type(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T4 (AC3): undo of one group action restores only that type's group."""
    state = _state(_detect(db_path, PAIR_TEXT, _pair("org_first")))
    rows = _rows_by_type(state)
    org, location = rows["ORG"], rows["LOCATION"]

    state.reject_entity(location.entity_id)
    state.accept_entity(org.entity_id)
    state.undo_stack.undo()

    assert org.state == PENDING
    assert location.state == REJECTED


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces one variant-map entry for the pair on the "
        "unfixed keys; fixed in Task 2"
    ),
)
@pytest.mark.parametrize("order", PAIR_ORDERS)
def test_variant_map_and_ranges_per_type(
    qtbot, db_path: str, order: str  # type: ignore[no-untyped-def]
) -> None:
    """T5 (AC4): one variant entry per type; each occurrence maps to its row."""
    result = _detect(db_path, PAIR_TEXT, _pair(order))
    assert result.variant_occurrences is not None
    assert len(result.variant_occurrences) == 2

    state = _state(result)
    type_by_id = {r.entity_id: r.entity.entity_type for r in state.get_all_entities()}
    ranges = state.get_all_entity_ranges()
    assert len(ranges) == 3
    assert {(start, end, type_by_id[eid]) for start, end, eid in ranges} == {
        (0, 10, "ORG"),
        (21, 31, "ORG"),
        (0, 10, "LOCATION"),
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces a reject reaching the other type at another "
        "place on the unfixed keys; fixed in Task 2"
    ),
)
def test_same_text_two_types_two_places(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T6 (AC1, AC3): one text, two types at two places, two groups."""
    entities = [
        _entity(PAIR_TEXT, PAIR_NAME, "ORG", 0),
        _entity(PAIR_TEXT, PAIR_NAME, "LOCATION", 1),
    ]
    state = _state(_detect(db_path, PAIR_TEXT, entities))
    rows = _rows_by_type(state)

    state.reject_entity(rows["LOCATION"].entity_id)
    assert rows["ORG"].state == PENDING


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces one preview string for both rows of the pair "
        "on the unfixed keys; fixed in Task 2"
    ),
)
@pytest.mark.parametrize("order", PREVIEW_ORDERS)
def test_each_row_shows_its_own_preview(
    qtbot, db_path: str, order: str  # type: ignore[no-untyped-def]
) -> None:
    """T7 (AC1): each row gets its own preview entry, title included.

    No assertion on the base pseudonym: it becomes type-aware with Story 10.7.
    """
    state = _state(_detect(db_path, PREVIEW_TEXT, _preview_pair(order)))
    rows = _rows_by_type(state)
    person_preview = rows["PERSON"].suggested_pseudonym or ""
    org_preview = rows["ORG"].suggested_pseudonym or ""
    # Precondition: previews were built (they fail silently to ``{}``).
    assert person_preview != ""
    assert org_preview != ""

    assert person_preview.startswith("Dr ")
    assert not org_preview.startswith("Dr ")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces a batch reject reaching every row of the text "
        "on the unfixed keys; fixed in Task 2"
    ),
)
def test_batch_path_reject_one_type_keeps_the_other(
    qtbot, main_window: MainWindow, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T8 (AC1, AC3): the batch screen's raw rows, one group per type."""
    main_window.navigate_to("batch")
    batch_screen = main_window.stack.currentWidget()
    assert isinstance(batch_screen, BatchScreen)
    # Normally set by _launch_worker before the worker starts.
    batch_screen._db_path = db_path
    batch_screen._passphrase = PASSPHRASE
    batch_screen._validation_contexts = {}

    batch_screen._on_validation_required(_pair("org_first"), PAIR_TEXT, 0, 1)

    validation_screen = main_window.stack.currentWidget()
    assert isinstance(validation_screen, ValidationScreen)
    state = validation_screen.validation_state
    assert state is not None
    reviews = state.get_all_entities()
    assert len(reviews) == 3
    # Precondition: previews were built (they fail silently to ``{}``).
    assert all(r.suggested_pseudonym for r in reviews)
    location = next(r for r in reviews if r.entity.entity_type == "LOCATION")
    orgs = sorted(
        (r for r in reviews if r.entity.entity_type == "ORG"),
        key=lambda r: r.entity.start_pos,
    )
    assert len(orgs) == 2

    state.reject_entity(location.entity_id)
    assert [r.state for r in orgs] == [PENDING, PENDING]

    state.accept_entity(orgs[0].entity_id)
    assert [r.state for r in orgs] == [CONFIRMED, CONFIRMED]
    assert location.state == REJECTED
    assert _spans(state.get_validated_entities()) == [
        ("ORG", 0, 10),
        ("ORG", 21, 31),
    ]


# ----------------------------------------------------------------------
# T10-T12: guards (pass before and after the fix)
# ----------------------------------------------------------------------


def test_type_change_still_expands_every_occurrence(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T10 (AC9): a retyped row still sends and highlights its group."""
    state = _state(_detect(db_path, GROUP_TEXT, _group()))
    (row,) = state.get_all_entities()

    state.change_entity_type(row.entity_id, "ORG")

    assert sorted(e.start_pos for e in state.expand_validated_entities()) == [0, 63]
    assert sorted(start for start, _, _ in state.get_all_entity_ranges()) == [0, 63]


def test_custom_pseudonym_still_expands_every_occurrence(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T11 (AC9): a row with a custom pseudonym still sends its group."""
    state = _state(_detect(db_path, GROUP_TEXT, _group()))
    (row,) = state.get_all_entities()

    state.change_pseudonym(row.entity_id, "Quentrix Zorbal")

    assert sorted(e.start_pos for e in state.expand_validated_entities()) == [0, 63]


def test_single_type_group_unchanged(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T12 (AC9): a single-type group behaves as before."""
    state = _state(_detect(db_path, GROUP_TEXT, _group()))
    (row,) = state.get_all_entities()

    state.accept_entity(row.entity_id)

    assert row.suggested_pseudonym
    assert sorted(e.start_pos for e in state.expand_validated_entities()) == [0, 63]
    assert sorted(start for start, _, _ in state.get_all_entity_ranges()) == [0, 63]
