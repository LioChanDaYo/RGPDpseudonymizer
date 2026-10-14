"""Story 10.9: a desktop-app edit applies to every occurrence of the name.

A review row stands for every occurrence of its name (the variant map of the
detection worker; one row per occurrence in batch validation). These tests
drive the real detection worker (only ``detect_entities`` is replaced), the
real variant grouping, the real ``build_pseudonym_previews`` on a temporary
database, the real ``GUIValidationState`` and the real ``finalize_document``.

T1-T7 reproduce a text edit reaching one occurrence only (AC1); T11-T12 a
type change reaching one occurrence only (AC9); T8-T9 guard what must not
change (AC6). T10, the CLI guard, is in
``tests/unit/test_validation_edit_every_occurrence.py``. Invented names only
(AC8). No assertion names a key format, so the same tests hold before and
after the fix. Each test asserts its preconditions first, so an expected
failure can only come from the behaviour under test.
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

NAME = "Quentrel Zorbalia"
TITLED_NAME = "Dr Quentrel Zorbalia"
EDIT = "Quentrel Zorbalia Quentrix"

# PERSON "Quentrel Zorbalia" at 0 and 63.
GROUP_TEXT = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
# PERSON "Quentrel Zorbalia" at 0 and 72; the edit is found at both places.
EXT_TEXT = (
    "Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia Quentrix."
)
# PERSON "Quentrel Zorbalia" at 0 and 72; the edit is absent at 72.
FALLBACK_TEXT = (
    "Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia."
)
# PERSON "Dr Quentrel Zorbalia" at 0 and 66; the edit drops the title.
SHRINK_TEXT = (
    "Dr Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Dr Quentrel Zorbalia."
)
# PERSON "Quentrel Zorbalia" at 0 and "Dr Quentrel Zorbalia" at 63: one row.
VARIANT_TEXT = (
    "Quentrel Zorbalia rejoint le projet. "
    "Le contrat est signé avec Dr Quentrel Zorbalia."
)
# PERSON "Quentrel Zorbalia" at 0 only.
SINGLE_TEXT = "Quentrel Zorbalia rejoint le projet."

CONFIRMED = EntityReviewState.CONFIRMED
MODIFIED = EntityReviewState.MODIFIED
PENDING = EntityReviewState.PENDING


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _entity(
    document_text: str, name: str, nth: int, entity_type: str = "PERSON"
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
        source="spacy",
    )


def _two_places(document_text: str, name: str = NAME) -> list[DetectedEntity]:
    return [_entity(document_text, name, 0), _entity(document_text, name, 1)]


def _variant() -> list[DetectedEntity]:
    return [_entity(VARIANT_TEXT, NAME, 0), _entity(VARIANT_TEXT, TITLED_NAME, 0)]


def _detect(
    db_path: str, document_text: str, entities: list[DetectedEntity]
) -> DetectionResult:
    """Run the real DetectionWorker synchronously, detection replaced only."""
    finished: list[object] = []
    errors: list[str] = []
    worker = DetectionWorker(
        file_path="zorbalia.txt", db_path=db_path, passphrase=PASSPHRASE
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
    # Precondition: the worker emitted ``finished`` exactly once, no ``error``.
    assert errors == []
    assert len(finished) == 1
    result = finished[0]
    assert isinstance(result, DetectionResult)
    return result


def _single_row(
    result: DetectionResult, expected_spans: list[tuple[int, int]]
) -> tuple[GUIValidationState, EntityReview]:
    """Single-document state; preconditions: one row, its variant entry."""
    assert result.variant_occurrences is not None
    [occurrences] = list(result.variant_occurrences.values())
    assert [(o.start_pos, o.end_pos) for o in occurrences] == expected_spans
    state = GUIValidationState()
    state.init_from_detection_result(result)
    rows = state.get_all_entities()
    assert len(rows) == 1
    row = rows[0]
    return state, row


def _batch_rows(
    main_window: MainWindow,
    db_path: str,
    document_text: str,
    entities: list[DetectedEntity],
) -> tuple[GUIValidationState, list[EntityReview]]:
    """Batch-screen state (one row per occurrence); preconditions: two PENDING."""
    main_window.navigate_to("batch")
    batch_screen = main_window.stack.currentWidget()
    assert isinstance(batch_screen, BatchScreen)
    # Normally set by _launch_worker before the worker starts.
    batch_screen._db_path = db_path
    batch_screen._passphrase = PASSPHRASE
    batch_screen._validation_contexts = {}

    batch_screen._on_validation_required(entities, document_text, 0, 1)

    validation_screen = main_window.stack.currentWidget()
    assert isinstance(validation_screen, ValidationScreen)
    state = validation_screen.validation_state
    assert state is not None
    rows = sorted(state.get_all_entities(), key=lambda r: r.entity.start_pos)
    assert len(rows) == 2
    assert [r.state for r in rows] == [PENDING, PENDING]
    return state, rows


def _sent(entities: list[DetectedEntity]) -> list[tuple[str, int, int, str]]:
    return sorted((e.entity_type, e.start_pos, e.end_pos, e.text) for e in entities)


def _finalize(
    db_path: str,
    tmp_path: Path,
    document_text: str,
    entities: list[DetectedEntity],
) -> str:
    output = tmp_path / "zorbalia_out.txt"
    result = DocumentProcessor(
        db_path=db_path, passphrase=PASSPHRASE
    ).finalize_document(document_text, entities, str(output))
    assert result.success
    return output.read_text(encoding="utf-8")


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "mappings.db")
    init_database(path, PASSPHRASE)
    return path


# ----------------------------------------------------------------------
# T1-T7: a text edit reaches every occurrence (AC1)
# ----------------------------------------------------------------------


def test_edit_applies_to_every_occurrence(
    qtbot, db_path: str, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    """T1 (AC1, the probe case): the edit is sent at both places."""
    result = _detect(db_path, EXT_TEXT, _two_places(EXT_TEXT))
    state, row = _single_row(result, [(0, 17), (72, 89)])
    state.accept_entity(row.entity_id)

    state.modify_entity_text(row.entity_id, EDIT, 0, 26)

    expanded = state.expand_validated_entities()
    assert _sent(expanded) == [
        ("PERSON", 0, 26, EDIT),
        ("PERSON", 72, 98, EDIT),
    ]
    output = _finalize(db_path, tmp_path, EXT_TEXT, expanded)
    for part in ("Quentrel", "Zorbalia", "Quentrix"):
        assert part not in output


def test_edit_absent_at_a_place_keeps_its_span(
    qtbot, db_path: str, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    """T2 (AC1): where the edited text is absent, the detected span is sent."""
    result = _detect(db_path, FALLBACK_TEXT, _two_places(FALLBACK_TEXT))
    state, row = _single_row(result, [(0, 17), (72, 89)])
    state.accept_entity(row.entity_id)

    state.modify_entity_text(row.entity_id, EDIT, 0, 26)

    expanded = state.expand_validated_entities()
    assert _sent(expanded) == [
        ("PERSON", 0, 26, EDIT),
        ("PERSON", 72, 89, EDIT),
    ]
    output = _finalize(db_path, tmp_path, FALLBACK_TEXT, expanded)
    for part in ("Quentrel", "Zorbalia"):
        assert part not in output


def test_edit_moves_each_span(
    qtbot, db_path: str, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    """T3 (AC1): dropping the title moves the span at every place."""
    result = _detect(db_path, SHRINK_TEXT, _two_places(SHRINK_TEXT, TITLED_NAME))
    state, row = _single_row(result, [(0, 20), (66, 86)])
    state.accept_entity(row.entity_id)

    state.modify_entity_text(row.entity_id, NAME, 3, 20)

    expanded = state.expand_validated_entities()
    assert _sent(expanded) == [
        ("PERSON", 3, 20, NAME),
        ("PERSON", 69, 86, NAME),
    ]
    output = _finalize(db_path, tmp_path, SHRINK_TEXT, expanded)
    assert output.count("Dr ") == 2
    for part in ("Quentrel", "Zorbalia"):
        assert part not in output


def test_one_undo_reverts_the_whole_edit(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T4 (AC1): one undo reverts the edit at every place; redo re-applies it."""
    result = _detect(db_path, EXT_TEXT, _two_places(EXT_TEXT))
    state, row = _single_row(result, [(0, 17), (72, 89)])
    state.accept_entity(row.entity_id)
    edited = [("PERSON", 0, 26, EDIT), ("PERSON", 72, 98, EDIT)]

    state.modify_entity_text(row.entity_id, EDIT, 0, 26)

    assert _sent(state.expand_validated_entities()) == edited

    state.undo_stack.undo()
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 0, 17, NAME),
        ("PERSON", 72, 89, NAME),
    ]
    assert row.state == CONFIRMED
    assert row.user_modification is None

    state.undo_stack.redo()
    assert _sent(state.expand_validated_entities()) == edited


def test_highlights_match_what_is_sent(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T5 (AC1): the highlight ranges are exactly the spans sent."""
    result = _detect(db_path, EXT_TEXT, _two_places(EXT_TEXT))
    state, row = _single_row(result, [(0, 17), (72, 89)])
    state.accept_entity(row.entity_id)

    state.modify_entity_text(row.entity_id, EDIT, 0, 26)

    assert set(state.get_all_entity_ranges()) == {
        (0, 26, row.entity_id),
        (72, 98, row.entity_id),
    }


def test_batch_edit_applies_to_every_row(
    qtbot, main_window: MainWindow, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T6 (AC1): in batch validation the edit reaches every row of the name."""
    state, rows = _batch_rows(main_window, db_path, EXT_TEXT, _two_places(EXT_TEXT))

    state.modify_entity_text(rows[0].entity_id, EDIT, 0, 26)

    assert [(r.state, r.user_modification) for r in rows] == [
        (MODIFIED, EDIT),
        (MODIFIED, EDIT),
    ]
    assert _sent(state.get_validated_entities()) == [
        ("PERSON", 0, 26, EDIT),
        ("PERSON", 72, 98, EDIT),
    ]

    state.undo_stack.undo()
    assert [(r.state, r.user_modification) for r in rows] == [
        (PENDING, None),
        (PENDING, None),
    ]
    assert state.get_validated_entities() == []


def test_dialog_edit_on_two_spellings(
    qtbot,  # type: ignore[no-untyped-def]
    main_window: MainWindow,
    db_path: str,
    tmp_path: Path,
) -> None:
    """T7 (AC1): the edit dialog places the edit on the row, then every place."""
    result = _detect(db_path, VARIANT_TEXT, _variant())
    assert result.variant_occurrences is not None
    [occurrences] = list(result.variant_occurrences.values())
    assert [(o.start_pos, o.end_pos) for o in occurrences] == [(0, 17), (63, 83)]
    idx = main_window._screens.get("validation")
    assert idx is not None
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, ValidationScreen)
    screen.start_validation(result)
    state = screen.validation_state
    assert state is not None
    rows = state.get_all_entities()
    assert len(rows) == 1
    row = rows[0]
    assert (row.entity.start_pos, row.entity.end_pos) == (63, 83)
    state.accept_entity(row.entity_id)

    with patch(
        "gdpr_pseudonymizer.gui.screens.validation.QInputDialog.getText",
        return_value=(NAME, True),
    ) as get_text:
        screen._show_modify_text_dialog(row.entity_id)
    assert get_text.call_count == 1

    expanded = state.expand_validated_entities()
    assert _sent(expanded) == [
        ("PERSON", 0, 17, NAME),
        ("PERSON", 66, 83, NAME),
    ]
    output = _finalize(db_path, tmp_path, VARIANT_TEXT, expanded)
    assert output.count("Dr ") == 1
    for part in ("Quentrel", "Zorbalia"):
        assert part not in output


# ----------------------------------------------------------------------
# T8-T9: guards (pass before and after the fix, AC6)
# ----------------------------------------------------------------------


def test_single_place_edit_unchanged(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T8 (AC6): an edit of a name found at one place behaves as before."""
    result = _detect(db_path, SINGLE_TEXT, [_entity(SINGLE_TEXT, NAME, 0)])
    state, row = _single_row(result, [(0, 17)])
    state.accept_entity(row.entity_id)
    edit = "Quentrel Zorbalia rejoint"

    state.modify_entity_text(row.entity_id, edit, 0, 25)

    assert _sent(state.expand_validated_entities()) == [("PERSON", 0, 25, edit)]
    assert [(start, end) for start, end, _ in state.get_all_entity_ranges()] == [
        (0, 25)
    ]


def test_edit_then_reject_sends_nothing(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T9 (AC6): an edit followed by a reject sends nothing."""
    result = _detect(db_path, EXT_TEXT, _two_places(EXT_TEXT))
    state, row = _single_row(result, [(0, 17), (72, 89)])

    state.modify_entity_text(row.entity_id, EDIT, 0, 26)
    state.reject_entity(row.entity_id)

    assert state.expand_validated_entities() == []
    assert state.get_validated_entities() == []


# ----------------------------------------------------------------------
# T11-T12: a type change reaches every occurrence (AC9)
# ----------------------------------------------------------------------


def test_type_change_applies_to_every_occurrence(
    qtbot, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T11 (AC9): a type change is sent at both places; one undo reverts it."""
    result = _detect(db_path, GROUP_TEXT, _two_places(GROUP_TEXT))
    state, row = _single_row(result, [(0, 17), (63, 80)])
    state.accept_entity(row.entity_id)

    state.change_entity_type(row.entity_id, "ORG")

    assert _sent(state.expand_validated_entities()) == [
        ("ORG", 0, 17, NAME),
        ("ORG", 63, 80, NAME),
    ]

    state.undo_stack.undo()
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 0, 17, NAME),
        ("PERSON", 63, 80, NAME),
    ]


def test_batch_type_change_applies_to_every_row(
    qtbot, main_window: MainWindow, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T12 (AC9): in batch validation the type change reaches every row."""
    state, rows = _batch_rows(main_window, db_path, GROUP_TEXT, _two_places(GROUP_TEXT))

    state.change_entity_type(rows[0].entity_id, "ORG")

    assert [(r.entity.entity_type, r.state) for r in rows] == [
        ("ORG", MODIFIED),
        ("ORG", MODIFIED),
    ]

    state.undo_stack.undo()
    assert [(r.entity.entity_type, r.state) for r in rows] == [
        ("PERSON", PENDING),
        ("PERSON", PENDING),
    ]


# ----------------------------------------------------------------------
# T13-T16: amendment after QA (UX-001, UI-001): a second edit builds on the
# first, and the editor's highlights follow every change
# ----------------------------------------------------------------------

TITLED_EDIT = "Dr Quentrel Zorbalia Quentrix"
NAME_PARTS = ("Quentrel", "Zorbalia", "Quentrix")

# PERSON "Quentrel Zorbalia" at 3 and 78; the title is at both places.
TITLED_TEXT = (
    "Dr Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Dr Quentrel Zorbalia Quentrix."
)
# PERSON "Quentrel Zorbalia" at 3 and 75; the title is at the first place only.
ONE_TITLE_TEXT = (
    "Dr Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia Quentrix."
)


def _screen_row(
    main_window: MainWindow,
    result: DetectionResult,
    expected_spans: list[tuple[int, int]],
) -> tuple[ValidationScreen, GUIValidationState, EntityReview]:
    """The real validation screen; preconditions: one row, its variant entry."""
    assert result.variant_occurrences is not None
    [occurrences] = list(result.variant_occurrences.values())
    assert [(o.start_pos, o.end_pos) for o in occurrences] == expected_spans
    idx = main_window._screens.get("validation")
    assert idx is not None
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, ValidationScreen)
    screen.start_validation(result)
    state = screen.validation_state
    assert state is not None
    rows = state.get_all_entities()
    assert len(rows) == 1
    return screen, state, rows[0]


def _dialog(
    screen: ValidationScreen,
    entity_id: str,
    *,
    typed: str | None = None,
    prefix: str = "",
    ok: bool = True,
) -> str:
    """Open the real edit dialog once; return what it showed (the pre-fill).

    The user's reply is ``typed`` when given, else ``prefix`` followed by
    what the dialog shows; ``ok=False`` is Cancel. Precondition: the patched
    ``getText`` was called exactly once (a missed patch opens a modal dialog).
    """
    shown: list[str] = []

    def _get_text(*args: object, **kwargs: object) -> tuple[str, bool]:
        text = kwargs.get("text")
        assert isinstance(text, str)
        shown.append(text)
        return (typed if typed is not None else prefix + text), ok

    with patch(
        "gdpr_pseudonymizer.gui.screens.validation.QInputDialog.getText",
        side_effect=_get_text,
    ) as get_text:
        screen._show_modify_text_dialog(entity_id)
    assert get_text.call_count == 1
    return shown[0]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.9 amendment: reproduces QA UX-001 on 9c5dee2; fixed in Task 9",
)
def test_second_dialog_edit_builds_on_the_first(
    qtbot,  # type: ignore[no-untyped-def]
    main_window: MainWindow,
    db_path: str,
    tmp_path: Path,
) -> None:
    """T13 (AC10, UX-001): the dialog re-opens on the edit and builds on it."""
    result = _detect(db_path, TITLED_TEXT, _two_places(TITLED_TEXT))
    screen, state, row = _screen_row(main_window, result, [(3, 20), (78, 95)])
    state.accept_entity(row.entity_id)
    # Edit 1: the user types the longer name.
    assert _dialog(screen, row.entity_id, typed=EDIT) == NAME
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 3, 29, EDIT),
        ("PERSON", 78, 104, EDIT),
    ]

    # Edit 2: the user adds the title to what the dialog shows.
    prefill = _dialog(screen, row.entity_id, prefix="Dr ")

    assert prefill == EDIT
    expanded = state.expand_validated_entities()
    assert _sent(expanded) == [
        ("PERSON", 0, 29, TITLED_EDIT),
        ("PERSON", 75, 104, TITLED_EDIT),
    ]
    output = _finalize(db_path, tmp_path, TITLED_TEXT, expanded)
    for part in NAME_PARTS:
        assert part not in output
    # OK on the unchanged text changes nothing.
    index = state.undo_stack.index()
    assert _dialog(screen, row.entity_id) == TITLED_EDIT
    assert state.undo_stack.index() == index
    # After an undo the dialog opens on whatever text is current (Cancel).
    state.undo_stack.undo()
    assert _dialog(screen, row.entity_id, ok=False) == EDIT
    state.undo_stack.undo()
    assert _dialog(screen, row.entity_id, ok=False) == NAME


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.9 amendment: reproduces QA UI-001 on 9c5dee2; fixed in Task 9",
)
def test_editor_highlights_follow_every_change(
    qtbot, main_window: MainWindow, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T14 (AC1 highlights, AC7; UI-001): the editor's ranges follow the state."""
    result = _detect(db_path, EXT_TEXT, _two_places(EXT_TEXT))
    screen, state, row = _screen_row(main_window, result, [(0, 17), (72, 89)])
    state.accept_entity(row.entity_id)
    second_quentrix = EXT_TEXT.find("Quentrix", 72)

    def editor_ranges() -> list[tuple[int, int]]:
        return sorted((start, end) for start, end, _ in screen.editor._entity_ranges)

    def sent_spans() -> list[tuple[int, int]]:
        return sorted(
            (e.start_pos, e.end_pos) for e in state.expand_validated_entities()
        )

    assert editor_ranges() == [(0, 17), (72, 89)]
    _dialog(screen, row.entity_id, typed=EDIT)
    assert sent_spans() == [(0, 26), (72, 98)]

    assert editor_ranges() == [(0, 26), (72, 98)]
    assert screen.editor._entity_at_position(second_quentrix) == row.entity_id

    screen._handle_entity_action(row.entity_id, "change_type:ORG")
    assert editor_ranges() == sent_spans() == [(0, 26), (72, 98)]
    state.undo_stack.undo()  # the type change
    assert editor_ranges() == sent_spans() == [(0, 26), (72, 98)]
    state.undo_stack.undo()  # the edit
    assert editor_ranges() == sent_spans() == [(0, 17), (72, 89)]
    assert screen.editor._entity_at_position(second_quentrix) is None
    state.undo_stack.redo()  # the edit again
    assert editor_ranges() == sent_spans() == [(0, 26), (72, 98)]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.9 amendment: reproduces QA UX-001 on 9c5dee2; fixed in Task 9",
)
def test_second_edit_absent_at_a_place_keeps_the_first_edit(
    qtbot, db_path: str, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    """T15 (AC10, UX-001): a place keeps the first edit's span, not the detected one."""
    from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow

    result = _detect(db_path, ONE_TITLE_TEXT, _two_places(ONE_TITLE_TEXT))
    state, row = _single_row(result, [(3, 20), (75, 92)])
    state.accept_entity(row.entity_id)
    state.modify_entity_text(row.entity_id, EDIT, 3, 29)
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 3, 29, EDIT),
        ("PERSON", 75, 101, EDIT),
    ]
    span = ValidationWorkflow._locate_modified_span(
        ONE_TITLE_TEXT, row.entity, TITLED_EDIT
    )
    assert span == (0, 29)

    state.modify_entity_text(row.entity_id, TITLED_EDIT, *span)

    expanded = state.expand_validated_entities()
    assert _sent(expanded) == [
        ("PERSON", 0, 29, TITLED_EDIT),
        ("PERSON", 75, 101, TITLED_EDIT),
    ]
    assert sorted((s, e) for s, e, _ in state.get_all_entity_ranges()) == [
        (0, 29),
        (75, 101),
    ]
    output = _finalize(db_path, tmp_path, ONE_TITLE_TEXT, expanded)
    for part in NAME_PARTS:
        assert part not in output

    state.undo_stack.undo()
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 3, 29, EDIT),
        ("PERSON", 75, 101, EDIT),
    ]
    state.undo_stack.undo()
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 3, 20, NAME),
        ("PERSON", 75, 92, NAME),
    ]
    state.undo_stack.redo()
    state.undo_stack.redo()
    assert _sent(state.expand_validated_entities()) == [
        ("PERSON", 0, 29, TITLED_EDIT),
        ("PERSON", 75, 101, TITLED_EDIT),
    ]


def test_batch_second_edit_absent_at_a_place_keeps_the_first_edit(
    qtbot, main_window: MainWindow, db_path: str  # type: ignore[no-untyped-def]
) -> None:
    """T16 (AC10, guard): in batch each row already keeps the first edit's span."""
    from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow

    state, rows = _batch_rows(
        main_window, db_path, ONE_TITLE_TEXT, _two_places(ONE_TITLE_TEXT)
    )
    state.modify_entity_text(rows[0].entity_id, EDIT, 3, 29)
    assert _sent(state.get_validated_entities()) == [
        ("PERSON", 3, 29, EDIT),
        ("PERSON", 75, 101, EDIT),
    ]
    span = ValidationWorkflow._locate_modified_span(
        ONE_TITLE_TEXT, rows[0].entity, TITLED_EDIT
    )
    assert span == (0, 29)

    state.modify_entity_text(rows[0].entity_id, TITLED_EDIT, *span)

    assert _sent(state.get_validated_entities()) == [
        ("PERSON", 0, 29, TITLED_EDIT),
        ("PERSON", 75, 101, TITLED_EDIT),
    ]
    state.undo_stack.undo()
    assert _sent(state.get_validated_entities()) == [
        ("PERSON", 3, 29, EDIT),
        ("PERSON", 75, 101, EDIT),
    ]
