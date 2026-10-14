"""Story 10.10: rows added by hand, corrections and group actions (T6-T10, T13-T24).

Batch validation is driven through the batch screen's ``_on_validation_required``
(one row per detection), without the batch worker thread, as Story 10.8's batch
test does. Single-document validation goes through the real ``DetectionWorker``
run synchronously, with detection replaced (one row per found name). Each test
asserts its preconditions (messages start with "PRE:") before the behaviour
under test; the first assertion after them is the expected failure on the
unfixed code. Invented names only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.workers.detection_worker import (
    DetectionResult,
    DetectionWorker,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

PASSPHRASE = "zorbalia_pass_A_123!"

PENDING = EntityReviewState.PENDING
CONFIRMED = EntityReviewState.CONFIRMED
REJECTED = EntityReviewState.REJECTED
MODIFIED = EntityReviewState.MODIFIED
ADDED = EntityReviewState.ADDED

H_TEXT = "Zorbaville a signé à Zorbaville. Zorbaville."

NAME = "Quentrel Zorbalia"
EDIT = "Quentrel Zorbalia Quentrix"
THREE = (
    "Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia Quentrix. "
    "Le projet est signé avec Quentrel Zorbalia Quentrix."
)
P3 = [THREE.find(NAME), THREE.find(NAME, 1), THREE.rfind(NAME)]  # 0, 72, 125
EDITED = [(p, p + len(EDIT)) for p in P3]

SAINT = "Zorbal a signé avec Zorbal. Le projet est à Saint-Zorbal."
PS = [0, SAINT.find("Zorbal", 1), SAINT.find("Saint-Zorbal") + 6]

_XFAIL = "Story 10.10: reproduces {} on the unfixed batch review; fixed in Task 2"


def _xfail(failure: str) -> pytest.MarkDecorator:
    return pytest.mark.xfail(
        strict=True, raises=AssertionError, reason=_XFAIL.format(failure)
    )


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    assert text[start : start + len(name)] == name, "PRE: entity slice"
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _spans(entities: list[DetectedEntity]) -> list[tuple[str, int, int]]:
    return sorted((e.entity_type, e.start_pos, e.end_pos) for e in entities)


def _new_db(tmp_path: Path) -> str:
    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    return db


def _store_known_zorbal(tmp_path: Path, db: str) -> None:
    """Store "Zorbal" in the mapping database as an earlier document would."""
    result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
        "Zorbal.", [_at("Zorbal.", "Zorbal", "PERSON", 0)], str(tmp_path / "prev.txt")
    )
    assert result.success, "PRE: known name stored"


def _batch_state(
    main_window: Any, db: str, text: str, entities: list[DetectedEntity]
) -> GUIValidationState:
    """Batch validation of one document through the batch screen (one row per
    detection)."""
    from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

    main_window.navigate_to("batch")
    bs = main_window.stack.currentWidget()
    assert isinstance(bs, BatchScreen), "PRE: batch screen"
    bs._db_path, bs._passphrase, bs._validation_contexts = db, PASSPHRASE, {}
    bs._on_validation_required(
        [DetectedEntity(**vars(e)) for e in entities], text, 0, 1
    )
    state = main_window.stack.currentWidget().validation_state
    assert state is not None, "PRE: review shown"
    assert len(state.get_all_entities()) == len(entities), "PRE: one row each"
    return state


def _single_state(
    db: str, text: str, entities: list[DetectedEntity]
) -> GUIValidationState:
    """Single-document validation through the real DetectionWorker run
    synchronously (one row per found name)."""
    finished: list[object] = []
    worker = DetectionWorker(
        file_path="document.txt", db_path=db, passphrase=PASSPHRASE
    )
    worker.setAutoDelete(False)
    worker.signals.finished.connect(finished.append)
    with patch.object(
        DocumentProcessor, "detect_entities", return_value=(text, entities)
    ):
        worker.run()
    assert len(finished) == 1, "PRE: detection finished once"
    result = finished[0]
    assert isinstance(result, DetectionResult), "PRE: detection result"
    state = GUIValidationState()
    state.init_from_detection_result(result)
    return state


def _write(tmp_path: Path, db: str, text: str, entities: list[DetectedEntity]) -> str:
    output = tmp_path / "written.txt"
    result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
        text, entities, str(output)
    )
    assert result.success
    return output.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# PRE-003: accept and reject on a row added by hand
# ---------------------------------------------------------------------------


def _h_entities() -> list[DetectedEntity]:
    return [_at(H_TEXT, "Zorbaville", "ORG", 0), _at(H_TEXT, "Zorbaville", "ORG", 21)]


@_xfail("a reject on a hand-added row rejecting the detected rows (PRE-003)")
def test_reject_on_added_row_acts_on_it_only(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC3 (QA's probe H): rejecting a row added by hand rejects that row only."""
    db = _new_db(tmp_path)
    state = _batch_state(main_window, db, H_TEXT, _h_entities())
    d0, d21 = state.get_all_entities()
    state.accept_entity(d0.entity_id)
    assert [d0.state, d21.state] == [CONFIRMED, CONFIRMED], "PRE: accepted"
    added = state.add_entity("Zorbaville", "ORG", 33, 43)
    assert state.get_review(added).state == ADDED, "PRE: added"
    state.reject_entity(added)
    assert [d0.state, d21.state] == [CONFIRMED, CONFIRMED]  # expected failure
    assert state.get_review(added).state == REJECTED
    validated = state.get_validated_entities()
    assert _spans(validated) == [("ORG", 0, 10), ("ORG", 21, 31)]
    written = _write(tmp_path, db, H_TEXT, validated)
    match = re.fullmatch(r"(.+?) a signé à (.+?)\. Zorbaville\.", written)
    assert match is not None, written
    assert all("Zorbaville" not in g for g in match.groups()), written
    state.undo_stack.undo()
    assert state.get_review(added).state == ADDED
    assert [d0.state, d21.state] == [CONFIRMED, CONFIRMED]


@_xfail("an accept on a hand-added row accepting the detected rows (PRE-003)")
def test_accept_on_added_row_acts_on_it_only(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC3: accepting a row added by hand accepts that row only."""
    state = _batch_state(main_window, _new_db(tmp_path), H_TEXT, _h_entities())
    d0, d21 = state.get_all_entities()
    assert [d0.state, d21.state] == [PENDING, PENDING], "PRE: pending"
    added = state.add_entity("Zorbaville", "ORG", 33, 43)
    assert state.get_review(added).state == ADDED, "PRE: added"
    state.accept_entity(added)
    assert [d0.state, d21.state] == [PENDING, PENDING]  # expected failure
    assert state.get_review(added).state == CONFIRMED
    assert _spans(state.get_validated_entities()) == [("ORG", 33, 43)]


def test_detected_group_excludes_added_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC3, AC8 guard: a detected row's group never includes a hand-added row."""
    state = _batch_state(main_window, _new_db(tmp_path), H_TEXT, _h_entities())
    d0, d21 = state.get_all_entities()
    added = state.add_entity("Zorbaville", "ORG", 33, 43)
    assert state.get_review(added).state == ADDED, "PRE: added"
    state.reject_entity(d0.entity_id)
    assert [d0.state, d21.state] == [REJECTED, REJECTED]
    assert state.get_review(added).state == ADDED


def test_single_document_added_row_unchanged(  # type: ignore[no-untyped-def]
    qtbot, tmp_path
) -> None:
    """AC8 guard: single-document validation keeps today's behaviour for a row
    added by hand."""
    state = _single_state(_new_db(tmp_path), H_TEXT, _h_entities())
    reviews = state.get_all_entities()
    assert len(reviews) == 1, "PRE: one found row"
    (row,) = reviews
    state.accept_entity(row.entity_id)
    added = state.add_entity("Zorbaville", "ORG", 33, 43)
    assert state.get_review(added).state == ADDED, "PRE: added"
    state.reject_entity(added)
    assert row.state == CONFIRMED
    assert _spans(state.expand_validated_entities()) == [
        ("ORG", 0, 10),
        ("ORG", 21, 31),
    ]


def test_edit_and_type_change_on_added_row_reach_every_row_of_the_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC3's edit rule, AC13 (Lionel's Q3): a correction and a type change on a
    row added by hand reach every row of the name."""
    state = _batch_state(main_window, _new_db(tmp_path), H_TEXT, _h_entities())
    d0, d21 = state.get_all_entities()
    state.accept_entity(d0.entity_id)
    added = state.add_entity("Zorbaville", "ORG", 33, 43)
    hand = state.get_review(added)
    assert [d0.state, d21.state, hand.state] == [
        CONFIRMED,
        CONFIRMED,
        ADDED,
    ], "PRE: states"
    state.modify_entity_text(added, "Zorbaville.", 33, 44)
    state.change_entity_type(added, "LOCATION")
    assert [
        (
            r.entity.entity_type,
            r.user_modification,
            r.entity.start_pos,
            r.entity.end_pos,
        )
        for r in (d0, d21, hand)
    ] == [
        ("LOCATION", "Zorbaville.", 0, 10),
        ("LOCATION", "Zorbaville.", 21, 32),
        ("LOCATION", "Zorbaville.", 33, 44),
    ]
    state.undo_stack.undo()
    assert [r.entity.entity_type for r in (d0, d21, hand)] == ["ORG", "ORG", "ORG"]


# ---------------------------------------------------------------------------
# AC13: a correction reaches every place of the name (Lionel's Q3)
# ---------------------------------------------------------------------------


def _three(
    mode: str, main_window: Any, tmp_path: Path
) -> tuple[str, GUIValidationState, Any, str]:
    """THREE: the detector finds the name at 0 and 72 and misses 125, which is
    added by hand; the found rows are accepted."""
    db = _new_db(tmp_path)
    entities = [_at(THREE, NAME, "PERSON", P3[0]), _at(THREE, NAME, "PERSON", P3[1])]
    if mode == "batch":
        state = _batch_state(main_window, db, THREE, entities)
    else:
        state = _single_state(db, THREE, entities)
        assert len(state.get_all_entities()) == 1, "PRE: one found row"
    for review in state.get_all_entities():
        state.accept_entity(review.entity_id)
    found = state.get_all_entities()[0]
    assert found.state == CONFIRMED, "PRE: found row accepted"
    added = state.add_entity(NAME, "PERSON", P3[2], P3[2] + len(NAME))
    assert state.get_review(added).state == ADDED, "PRE: added"
    return db, state, found, added


def _sent(mode: str, state: GUIValidationState) -> list[DetectedEntity]:
    if mode == "single":
        return state.expand_validated_entities()
    return state.get_validated_entities()


def _one_pseudonym_everywhere(written: str) -> bool:
    match = re.fullmatch(
        r"(.+?) rejoint le projet\. Le contrat est signé avec (.+?)\. "
        r"Le projet est signé avec (.+?)\.",
        written,
    )
    if match is None or len(set(match.groups())) != 1:
        return False
    return not any(p in written for p in ("Quentrel", "Zorbalia", "Quentrix"))


@_xfail("a correction on a found name not reaching the added place (AC13)")
@pytest.mark.parametrize("mode", ["single", "batch"])
def test_edit_on_found_name_reaches_added_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, mode
) -> None:
    """AC13 (QA's P05e): correcting a found name reaches the place added by hand."""
    db, state, found, added = _three(mode, main_window, tmp_path)
    state.modify_entity_text(found.entity_id, EDIT, P3[0], P3[0] + len(EDIT))
    sent = _sent(mode, state)
    assert sorted((e.start_pos, e.end_pos) for e in sent) == EDITED  # expected failure
    written = _write(tmp_path, db, THREE, sent)
    assert _one_pseudonym_everywhere(written), written


@pytest.mark.parametrize("mode", ["single", "batch"])
def test_edit_on_added_place_reaches_found_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, mode
) -> None:
    """AC13 (QA's P05d): correcting the place added by hand reaches the found
    name."""
    db, state, found, added = _three(mode, main_window, tmp_path)
    state.modify_entity_text(added, EDIT, P3[2], P3[2] + len(EDIT))
    sent = _sent(mode, state)
    assert sorted((e.start_pos, e.end_pos) for e in sent) == EDITED
    written = _write(tmp_path, db, THREE, sent)
    assert _one_pseudonym_everywhere(written), written


@_xfail("a type change on a found name not reaching the added place (AC13)")
@pytest.mark.parametrize("mode", ["single", "batch"])
def test_type_change_on_found_name_reaches_added_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, mode
) -> None:
    """AC13: a type change on a found name reaches the place added by hand, and
    the retyped added place stays in the name's group for the next correction."""
    db, state, found, added = _three(mode, main_window, tmp_path)
    state.change_entity_type(found.entity_id, "ORG")
    types_after_type_change = [e.entity_type for e in _sent(mode, state)]
    state.modify_entity_text(found.entity_id, EDIT, P3[0], P3[0] + len(EDIT))
    sent = _sent(mode, state)
    assert types_after_type_change == ["ORG", "ORG", "ORG"]  # expected failure
    assert sorted((e.entity_type, e.start_pos, e.end_pos) for e in sent) == [
        ("ORG", start, end) for start, end in EDITED
    ]
    written = _write(tmp_path, db, THREE, sent)
    assert _one_pseudonym_everywhere(written), written


@pytest.mark.parametrize(
    "case", ["single_hand_rejected", "batch_hand_rejected", "batch_found_rejected"]
)
def test_correction_skips_a_rejected_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, case
) -> None:
    """AC13 (Lionel, 2026-10-14; 10.9's rule kept): a correction never reaches
    another place the user rejected on its own."""
    mode = "single" if case.startswith("single") else "batch"
    db, state, found, added = _three(mode, main_window, tmp_path)
    if case == "batch_found_rejected":
        rejected = state.get_all_entities()[1]
        assert rejected.entity.start_pos == P3[1], "PRE: the found row at 72"
        state.bulk_reject([rejected.entity_id])  # "reject the selection"
        assert (rejected.state, found.state) == (REJECTED, CONFIRMED), "PRE: rejected"
        state.modify_entity_text(added, EDIT, P3[2], P3[2] + len(EDIT))
        corrected = [EDITED[0], EDITED[2]]
        shape = (
            r"(.+?) rejoint le projet\. Le contrat est signé avec "
            r"Quentrel Zorbalia Quentrix\. Le projet est signé avec (.+?)\."
        )
    else:
        rejected = state.get_review(added)
        state.bulk_reject([added])  # "reject the selection"
        assert (rejected.state, found.state) == (REJECTED, CONFIRMED), "PRE: rejected"
        state.modify_entity_text(found.entity_id, EDIT, P3[0], P3[0] + len(EDIT))
        corrected = [EDITED[0], EDITED[1]]
        shape = (
            r"(.+?) rejoint le projet\. Le contrat est signé avec (.+?)\. "
            r"Le projet est signé avec Quentrel Zorbalia Quentrix\."
        )
    assert (rejected.state, rejected.user_modification) == (REJECTED, None)
    sent = _sent(mode, state)
    assert sorted((e.start_pos, e.end_pos) for e in sent) == corrected
    written = _write(tmp_path, db, THREE, sent)
    match = re.fullmatch(shape, written)
    assert match is not None, written
    assert len(set(match.groups())) == 1, written
    assert all("Quentr" not in g and "orbal" not in g for g in match.groups()), written


# ---------------------------------------------------------------------------
# AC14: group actions keep the decisions made on one place (Lionel, Q5-Q7)
# ---------------------------------------------------------------------------


def _saint_entities() -> list[DetectedEntity]:
    return [_at(SAINT, "Zorbal", "PERSON", p) for p in PS]


def _saint_batch(
    main_window: Any, tmp_path: Path, known: bool = False
) -> tuple[str, GUIValidationState, Any, Any, Any]:
    """SAINT in batch validation: rows 1, 2 and 3 (row 3 is Saint-Zorbal)."""
    db = _new_db(tmp_path)
    if known:
        _store_known_zorbal(tmp_path, db)
    state = _batch_state(main_window, db, SAINT, _saint_entities())
    r1, r2, r3 = state.get_all_entities()
    assert [r.entity.start_pos for r in (r1, r2, r3)] == PS, "PRE: three rows"
    return db, state, r1, r2, r3


def _saint_single(tmp_path: Path, known: bool = False) -> tuple[str, Any, Any]:
    """SAINT in single-document validation, the first two places detected."""
    db = _new_db(tmp_path)
    if known:
        _store_known_zorbal(tmp_path, db)
    state = _single_state(db, SAINT, _saint_entities()[:2])
    if known:
        state.classify_known_entities(db, PASSPHRASE)
    reviews = state.get_all_entities()
    assert len(reviews) == 1, "PRE: one found row"
    return db, state, reviews[0]


def _saint_shape(written: str, marks: str) -> bool:
    """``marks``: one letter per place, 'P' pseudonymized (one pseudonym for
    all), 'Z' left as "Zorbal"."""
    pattern = SAINT
    for start, mark in sorted(zip(PS, marks), reverse=True):
        pattern = (
            pattern[:start]
            + ("\x00" if mark == "P" else "Zorbal")
            + pattern[start + 6 :]
        )
    regex = re.escape(pattern).replace("\x00", "(.+?)")
    match = re.fullmatch(regex, written)
    return (
        match is not None
        and len(set(match.groups())) <= 1
        and all("orbal" not in g for g in match.groups())
    )


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            "batch_rejected_alone",
            marks=_xfail("a group accept re-accepting a place rejected on its own"),
        ),
        "batch_clicked_rejected_row",
        "single_hand_rejected",
    ],
)
def test_group_accept_skips_a_rejected_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, case
) -> None:
    """AC14 (b) (Lionel, 2026-10-14, "Skip rejected (Rec.)"): a group accept
    skips another place rejected on its own; the row clicked is always
    accepted."""
    if case.startswith("batch"):
        db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path)
        state.accept_entity(r1.entity_id)
        state.bulk_reject([r3.entity_id])  # Saint-Zorbal alone
        assert [r1.state, r2.state, r3.state] == [
            CONFIRMED,
            CONFIRMED,
            REJECTED,
        ], "PRE: Saint-Zorbal rejected alone"
        clicked = r1 if case == "batch_rejected_alone" else r3
        state.accept_entity(clicked.entity_id)
        if case == "batch_rejected_alone":
            assert r3.state == REJECTED  # expected failure
            marks = "PPZ"
        else:
            assert r3.state == CONFIRMED  # the row clicked is always accepted
            marks = "PPP"
        assert [r1.state, r2.state] == [CONFIRMED, CONFIRMED]
        sent = state.get_validated_entities()
    else:
        db, state, found = _saint_single(tmp_path)
        hand = state.add_entity("Zorbal", "PERSON", PS[2], PS[2] + 6)
        assert state.get_review(hand).state == ADDED, "PRE: added"
        state.accept_entity(found.entity_id)
        state.bulk_reject([hand])
        assert state.get_review(hand).state == REJECTED, "PRE: hand row rejected"
        state.accept_entity(found.entity_id)
        assert state.get_review(hand).state == REJECTED
        assert found.state == CONFIRMED
        marks = "PPZ"
        sent = state.expand_validated_entities()
    written = _write(tmp_path, db, SAINT, sent)
    assert _saint_shape(written, marks), written


@_xfail("a group reject rejecting a place decided on its own (Q5)")
@pytest.mark.parametrize("case", ["batch_ticked_accept", "batch_own_pseudonym"])
def test_group_reject_skips_a_place_decided_on_its_own(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, case
) -> None:
    """AC14 (c) (Lionel's Q5, "Skip your own (Rec.)"): a group reject skips a
    place accepted or corrected on its own."""
    db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path)
    if case == "batch_ticked_accept":
        state.bulk_accept([r1.entity_id])  # the person's place, ticked in the list
        assert [r1.state, r2.state, r3.state] == [
            CONFIRMED,
            PENDING,
            PENDING,
        ], "PRE: accepted alone"
        expected = [CONFIRMED, REJECTED, REJECTED]
    else:
        state.accept_entity(r1.entity_id)  # the group
        state.change_pseudonym(r1.entity_id, "Xantor Vellion")  # that place alone
        assert [r1.state, r2.state, r3.state] == [
            MODIFIED,
            CONFIRMED,
            CONFIRMED,
        ], "PRE: own pseudonym"
        expected = [MODIFIED, REJECTED, REJECTED]
    state.reject_entity(r2.entity_id)  # the group reject, from another row
    assert [r1.state, r2.state, r3.state] == expected  # expected failure
    written = _write(tmp_path, db, SAINT, state.get_validated_entities())
    assert _saint_shape(written, "PZZ"), written


@pytest.mark.parametrize("from_row", ["same_row", "other_row"])
def test_group_reject_after_group_accept_rejects_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, from_row
) -> None:
    """AC14 (c) guard (Lionel's Q5 preview): accept the group, then reject the
    group, and every place is rejected."""
    db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path)
    state.accept_entity(r1.entity_id)
    assert [r1.state, r2.state, r3.state] == [CONFIRMED] * 3, "PRE: group accepted"
    state.reject_entity((r1 if from_row == "same_row" else r2).entity_id)
    assert [r1.state, r2.state, r3.state] == [REJECTED] * 3
    sent = state.get_validated_entities()
    assert sent == []
    assert _write(tmp_path, db, SAINT, sent) == SAINT


@_xfail("'Accepter les déjà connues' accepting rejected or corrected places (Q6)")
@pytest.mark.parametrize("mode", ["batch", "single"])
def test_accept_all_known_skips_rejected_and_corrected_places(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, mode
) -> None:
    """AC14 (e) (Lionel's Q6, "Skip rejected (Rec.)"): "Accepter les déjà
    connues" leaves rejected and corrected places as they are."""
    if mode == "batch":
        db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path, known=True)
        assert all(
            state.is_entity_known(r.entity_id) for r in (r1, r2, r3)
        ), "PRE: known"
        assert [r1.state, r2.state, r3.state] == [CONFIRMED] * 3, "PRE: accepted"
        state.bulk_reject([r3.entity_id])  # Saint-Zorbal alone
        state.change_entity_type(r1.entity_id, "ORG")  # reaches rows 1 and 2
        assert [r1.state, r2.state, r3.state] == [
            MODIFIED,
            MODIFIED,
            REJECTED,
        ], "PRE: decided"
        state.accept_all_known()
        assert [r1.state, r2.state, r3.state] == [
            MODIFIED,
            MODIFIED,
            REJECTED,
        ]  # expected failure
        assert [r.entity.entity_type for r in (r1, r2, r3)] == ["ORG", "ORG", "PERSON"]
        written = _write(tmp_path, db, SAINT, state.get_validated_entities())
        assert _saint_shape(written, "PPZ"), written
    else:
        db, state, found = _saint_single(tmp_path, known=True)
        assert state.is_entity_known(found.entity_id), "PRE: known"
        assert found.state == CONFIRMED, "PRE: accepted"
        state.reject_entity(found.entity_id)
        assert found.state == REJECTED, "PRE: rejected"
        state.accept_all_known()
        assert found.state == REJECTED  # expected failure
        sent = state.expand_validated_entities()
        assert sent == []
        assert _write(tmp_path, db, SAINT, sent) == SAINT


@pytest.mark.parametrize(
    "case",
    [
        "all_back",
        pytest.param(
            "own_rejected_stays",
            marks=_xfail("a group accept re-accepting a place rejected on its own"),
        ),
    ],
)
def test_group_accept_brings_back_places_rejected_by_the_group(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, case
) -> None:
    """AC14 (b) (Lionel's Q7, "Whole group back (Rec.)"): a group accept brings
    back the places rejected only by a group reject."""
    db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path)
    if case == "own_rejected_stays":
        state.bulk_reject([r3.entity_id])  # Saint-Zorbal on its own, earlier
        assert [r1.state, r2.state, r3.state] == [
            PENDING,
            PENDING,
            REJECTED,
        ], "PRE: rejected on its own"
    state.reject_entity(r2.entity_id)  # the group reject made by mistake
    assert [r1.state, r2.state, r3.state] == [REJECTED] * 3, "PRE: all rejected"
    state.accept_entity(r1.entity_id)
    if case == "all_back":
        assert [r1.state, r2.state, r3.state] == [CONFIRMED] * 3
        marks = "PPP"
    else:
        assert [r1.state, r2.state, r3.state] == [
            CONFIRMED,
            CONFIRMED,
            REJECTED,
        ]  # expected failure
        marks = "PPZ"
    written = _write(tmp_path, db, SAINT, state.get_validated_entities())
    assert _saint_shape(written, marks), written


@_xfail("a correction skipping a place rejected only by its group (Q7)")
def test_correction_reaches_places_rejected_by_the_group(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path
) -> None:
    """AC13, AC14 (d) (Lionel's Q7): a correction reaches a place rejected only
    with its group, never a place rejected on its own."""
    db, state, found, added = _three("batch", main_window, tmp_path)
    f0, f72 = state.get_all_entities()[:2]
    assert (f0.entity.start_pos, f72.entity.start_pos) == (P3[0], P3[1]), "PRE: rows"
    state.bulk_reject([f72.entity_id])  # the place at 72, on its own
    state.reject_entity(f0.entity_id)  # then the found group
    hand = state.get_review(added)
    assert [f0.state, f72.state, hand.state] == [
        REJECTED,
        REJECTED,
        ADDED,
    ], "PRE: rejected"
    state.modify_entity_text(added, EDIT, P3[2], P3[2] + len(EDIT))
    assert [f0.state, f72.state, hand.state] == [
        MODIFIED,
        REJECTED,
        MODIFIED,
    ]  # expected failure
    sent = state.get_validated_entities()
    assert sorted((e.start_pos, e.end_pos) for e in sent) == [EDITED[0], EDITED[2]]
    written = _write(tmp_path, db, THREE, sent)
    match = re.fullmatch(
        r"(.+?) rejoint le projet\. Le contrat est signé avec "
        r"Quentrel Zorbalia Quentrix\. Le projet est signé avec (.+?)\.",
        written,
    )
    assert match is not None, written
    assert len(set(match.groups())) == 1, written
    assert all("Quentr" not in g and "orbal" not in g for g in match.groups()), written


@_xfail("undo and redo losing the decisions made on one place (Q5-Q7)")
@pytest.mark.parametrize("case", ["undo_clears", "undo_restores", "undo_correction"])
def test_undo_and_redo_restore_the_memory(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, case
) -> None:
    """AC14 (a): undo and redo restore, for each row, whether its decision was
    made on that place alone."""
    db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path)
    undo_stack = state.undo_stack
    seen: list[list[str]] = []

    def record() -> None:
        seen.append([r.state.value for r in (r1, r2, r3)])

    assert [r1.state, r2.state, r3.state] == [PENDING] * 3, "PRE: all pending"
    c, p, r, m = "confirmed", "pending", "rejected", "modified"
    if case == "undo_clears":
        state.bulk_accept([r1.entity_id])  # row 1 accepted on its own
        record()
        state.reject_entity(r2.entity_id)  # row 1 skipped
        record()
        undo_stack.undo()
        record()
        undo_stack.redo()
        record()
        undo_stack.undo()
        undo_stack.undo()  # row 1's own accept undone
        record()
        state.accept_entity(r2.entity_id)  # the group, from row 2
        record()
        state.reject_entity(r3.entity_id)  # every place: row 1 follows the group
        record()
        undo_stack.undo()
        undo_stack.undo()
        record()
        undo_stack.redo()
        undo_stack.redo()
        record()
        expected = [
            [c, p, p],
            [c, r, r],
            [c, p, p],
            [c, r, r],
            [p, p, p],
            [c, c, c],
            [r, r, r],
            [p, p, p],
            [r, r, r],
        ]
        marks = "ZZZ"
    elif case == "undo_restores":
        state.bulk_accept([r1.entity_id])  # row 1 accepted on its own
        record()
        state.reject_entity(r1.entity_id)  # its own group reject: row 1 follows
        record()
        undo_stack.undo()  # row 1 accepted on its own again
        record()
        state.reject_entity(r2.entity_id)  # row 1 skipped
        record()
        expected = [[c, p, p], [r, r, r], [c, p, p], [c, r, r]]
        marks = "PZZ"
    else:
        state.accept_entity(r1.entity_id)  # the group
        record()
        state.bulk_reject([r3.entity_id])  # Saint-Zorbal rejected on its own
        record()
        state.modify_entity_text(  # a correction from row 3: every row
            r3.entity_id, "Saint-Zorbal", PS[2] - 6, PS[2] + 6
        )
        record()
        undo_stack.undo()  # row 3 rejected on its own again
        record()
        state.accept_entity(r1.entity_id)  # the group, from row 1: row 3 skipped
        record()
        expected = [[c, c, c], [c, c, r], [m, m, m], [c, c, r], [c, c, r]]
        marks = "PPZ"
    assert seen == expected  # expected failure
    written = _write(tmp_path, db, SAINT, state.get_validated_entities())
    assert _saint_shape(written, marks), written


@pytest.mark.parametrize(
    "then",
    [
        "correction",
        pytest.param(
            "group_accept",
            marks=_xfail("a group accept reaching places rejected with Ctrl+Shift+R"),
        ),
    ],
)
def test_places_rejected_with_ctrl_shift_r_stay_rejected(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, then
) -> None:
    """AC14 (a), (f) (Lionel, 2026-10-14, "Stay rejected (Rec.)"): a place
    rejected with Ctrl+Shift+R counts as rejected by the user."""
    db, state, r1, r2, r3 = _saint_batch(main_window, tmp_path)
    vs = main_window.stack.currentWidget()
    state.bulk_accept([r1.entity_id])  # the person's place, ticked in the list
    vs._on_reject_all()  # Ctrl+Shift+R: the places still to review
    assert [r1.state, r2.state, r3.state] == [
        CONFIRMED,
        REJECTED,
        REJECTED,
    ], "PRE: the rest rejected"
    if then == "correction":
        state.modify_entity_text(r1.entity_id, "Zorbal a", 0, 8)
        expected = [MODIFIED, REJECTED, REJECTED]
        shape = r"(.+?) signé avec Zorbal\. Le projet est à Saint-Zorbal\."
    else:
        state.accept_entity(r1.entity_id)  # "Accepter" on the person's row again
        expected = [CONFIRMED, REJECTED, REJECTED]
        shape = r"(.+?) a signé avec Zorbal\. Le projet est à Saint-Zorbal\."
    assert [r1.state, r2.state, r3.state] == expected  # expected failure
    written = _write(tmp_path, db, SAINT, state.get_validated_entities())
    match = re.fullmatch(shape, written)
    assert match is not None, written
    assert "orbal" not in match.group(1), written
