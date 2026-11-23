"""Story 15.1: every desktop review row matches what is written, and the
review document's hover text shows (G1 to G7, H1, H2, H4; controls GK1,
GK2, H0, H3).

Written by the BMAD dev agent (Claude), tests first. Single document: Story
11.5's ``_Single`` (the real ``DetectionWorker`` run synchronously with
detection replaced, the real ``ValidationScreen`` and ``FinalizationWorker``).
Batch: Story 11.5's ``_Batch`` (a real batch run through the real
``BatchWorker`` thread, only detection replaced). The review state's new
interfaces are reached through ``_not_written`` and ``_writer_at``, which
return the string ``"absent"`` where the state has no such method.

The hover: a real ``EntityEditor`` (``resize(700, 300)``, ``show()``) bound
to the review state, and a ``QHelpEvent`` of type ``ToolTip`` sent to its
viewport, the way Qt sends it; the tooltip is read back with
``QToolTip.isVisible()`` and ``QToolTip.text()``. The point is the middle of
a character strictly inside a name (``_mid``), never a boundary. The tooltip
is one object per process and ``QToolTip.hideText()`` only starts a timer,
so each hover first hides it and waits until it is hidden, and an autouse
fixture does the same at teardown.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and main-corpus words
only.
"""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QTextEdit, QToolTip

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from tests.unit.gui.test_review_list_written_pseudonym_review import (
    _Batch,
    _Dialogs,
    _new_db,
    _Single,
)
from tests.unit.test_custom_pseudonym_fixes_cli import _replacements, pre
from tests.unit.test_review_list_written_pseudonym import (
    _Draws,
    _row,
    install_draws,
)
from tests.unit.test_review_rows_written import (
    AT_ORG,
    AT_PLACE,
    LOCATION,
    ORG,
    ORG_NAME,
    ORG_PLACE,
    ORG_ZORBAL,
    PERSON,
    S1,
    S1_ORDERS,
    S1_PLACE_FIRST,
    S2,
    S2_SPANS,
    S3,
    S3_SPANS,
    S4,
    S4_SPANS,
    ZORBAL,
    ZQ,
    Span,
    _entities,
    _mark,
    _names,
    _prefix,
    _today,
)

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 11.5's test_review_list_written_pseudonym_review.py).
# This is a warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

ABSENT = "absent"
S6 = "Zorbal\nRéponse de Zorbal : d'accord."
S6_SPANS: list[Span] = [(ZORBAL, PERSON, 0)]
ZORBAL_SPAN = (11, 17)
HINT = "Zorbal Quentrix"


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


@pytest.fixture(autouse=True)
def _tooltip_hidden(qtbot: Any) -> Any:
    """The tooltip is one per process: hidden at teardown, and waited for,
    so the next test starts without one."""
    yield
    QToolTip.hideText()
    qtbot.waitUntil(lambda: not QToolTip.isVisible(), timeout=2000)


# ---------------------------------------------------------------------------
# Helpers (preconditions with pre)
# ---------------------------------------------------------------------------


def _not_written(state: GUIValidationState, entity_id: str) -> Any:
    """``state.not_written(entity_id)`` (Fix design B.1), or ``"absent"``
    where the state has no such method."""
    method = getattr(state, "not_written", None)
    return ABSENT if method is None else method(entity_id)


def _writer_at(state: GUIValidationState, position: int) -> Any:
    """``state.writer_at(position)`` (Fix design B.1), or ``"absent"``."""
    method = getattr(state, "writer_at", None)
    return ABSENT if method is None else method(position)


def _rows(state: GUIValidationState) -> dict[tuple[str, str], Any]:
    """The rows by (text, type); PRE that no two share both."""
    rows: dict[tuple[str, str], Any] = {}
    for review in state.get_all_entities():
        key = (review.entity.text, review.entity.entity_type)
        pre(key not in rows, f"one row {key!r}")
        rows[key] = review
    return rows


def _accept_all(state: GUIValidationState) -> None:
    for review in state.get_all_entities():
        if review.state.value == "pending":
            state.accept_entity(review.entity_id)


def _single(
    qtbot: Any,
    main_window: Any,
    tmp_path: Any,
    db: str,
    text: str,
    spans: list[Span],
) -> _Single:
    return _Single(qtbot, main_window, tmp_path, db, text, _entities(text, spans))


class _Received:
    """Records the list each ``_resolve_pseudonyms`` call receives (the
    list the end writes from)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.lists: list[list[DetectedEntity]] = []
        real = DocumentProcessor._resolve_pseudonyms
        recorder = self

        def resolve(
            self: Any, ctx: Any, entities: list[DetectedEntity], *a: Any, **k: Any
        ) -> Any:
            recorder.lists.append([DetectedEntity(**vars(e)) for e in entities])
            return real(self, ctx, entities, *a, **k)

        monkeypatch.setattr(DocumentProcessor, "_resolve_pseudonyms", resolve)

    def one(self) -> list[DetectedEntity]:
        pre(len(self.lists) == 1, f"the end ran once: {len(self.lists)}")
        return self.lists[0]


# --- The hover --------------------------------------------------------------


def _editor(qtbot: Any, state: GUIValidationState) -> EntityEditor:
    """A real review document bound to ``state``, shown."""
    editor = EntityEditor()
    qtbot.addWidget(editor)
    editor.resize(700, 300)
    editor.set_validation_state(state)
    editor.show()
    QApplication.processEvents()
    return editor


def _rect(editor: QTextEdit, position: int) -> Any:
    cursor = QTextCursor(editor.document())
    cursor.setPosition(position)
    return editor.cursorRect(cursor)


def _mid(editor: QTextEdit, position: int) -> QPoint:
    """The middle of character ``position``: x halfway between the cursor
    rectangles at ``position`` and ``position + 1``, y the centre of the
    first. PRE: both on one line."""
    here, after = _rect(editor, position), _rect(editor, position + 1)
    pre(here.top() == after.top(), f"character {position} on one line")
    return QPoint((here.x() + after.x()) // 2, here.center().y())


def _hover(qtbot: Any, editor: QTextEdit, point: QPoint) -> tuple[bool, str]:
    """Hide the tooltip and wait until it is hidden, then send the ToolTip
    event at ``point`` to the viewport; (visible, text) after it."""
    QToolTip.hideText()
    qtbot.waitUntil(lambda: not QToolTip.isVisible(), timeout=2000)
    viewport = editor.viewport()
    QApplication.sendEvent(
        viewport, QHelpEvent(QEvent.Type.ToolTip, point, viewport.mapToGlobal(point))
    )
    QApplication.processEvents()
    return QToolTip.isVisible(), QToolTip.text()


def _format_blocks(editor: EntityEditor, position: int) -> list[str]:
    """The hover text each highlight at ``position`` sets on its format
    (``fmt.setToolTip``): its row's block, the type, text, pseudonym,
    confidence and cell lines, in the editor's own words."""
    return [
        selection.format.toolTip()
        for selection in editor.extraSelections()
        if selection.cursor.selectionStart()
        <= position
        < selection.cursor.selectionEnd()
        and selection.format.toolTip()
    ]


def _block_line(entity_type: str, text: str) -> str:
    """The first line of a row's block today (``entity_editor.py:274``)."""
    return f"{entity_type}: {text}"


# ---------------------------------------------------------------------------
# G1 to G7: the review state marks the row not written
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", ["single_place_first", "single_person_first", "batch_place_first"]
)
def test_row_not_written_is_marked(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws, case
) -> None:
    """G1 (AC1, AC5): « Réponse de Zorbal : d'accord. », a place and a
    person « Zorbal » on the same span, every row accepted: the row the end
    does not write (the second sent) has ``not_written`` 1 of 1 with the
    other as ``by``; the row written has None, and the file holds its
    pseudonym."""
    mode, order = case.split("_", 1)
    spans = S1_ORDERS[order]
    first, second = spans[0][1], spans[1][1]
    record: dict[str, Any] = {}

    def read(state: GUIValidationState) -> None:
        _accept_all(state)
        rows = _rows(state)
        record["lost"] = _not_written(state, rows[(ZORBAL, second)].entity_id)
        record["kept"] = _not_written(state, rows[(ZORBAL, first)].entity_id)
        record["shown"] = state.get_pseudonym(rows[(ZORBAL, first)].entity_id)

    if mode == "single":
        dialogs = _Dialogs(monkeypatch)
        sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S1, spans)
        read(sd.state)
        written = sd.finalize(dialogs)
    else:
        batch = _Batch(qtbot, main_window, tmp_path, S1, _entities(S1, spans))

        def body(_: dict[str, Any]) -> None:
            read(batch.wait_doc())
            batch.vs.finalize_button.click()

        batch.run(body)
        pre("shown" in record, f"the review was read: {sorted(record)}")
        written = batch.output()
    assert _mark(record["lost"]) == (1, 1, ((ZORBAL, first),))  # expected failure
    assert record["kept"] is None
    assert _replacements(written, S1, [ZORBAL_SPAN]) == [record["shown"]]


def test_mark_goes_when_the_written_row_is_rejected(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws
) -> None:
    """G2 (AC1, AC6): S1 with the place first, every row accepted: the
    person row is marked; the place row rejected, the mark is gone at once
    and the file holds the person row's pseudonym."""
    dialogs = _Dialogs(monkeypatch)
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S1, S1_PLACE_FIRST)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    place, person = rows[(ZORBAL, LOCATION)], rows[(ZORBAL, PERSON)]
    before = _mark(_not_written(sd.state, person.entity_id))
    assert before == (1, 1, ((ZORBAL, LOCATION),))  # expected failure
    sd.state.reject_entity(place.entity_id)
    assert _not_written(sd.state, person.entity_id) is None
    shown = sd.state.get_pseudonym(person.entity_id)
    assert _replacements(sd.finalize(dialogs), S1, [ZORBAL_SPAN]) == [shown]


def test_organisation_under_a_place_with_its_preposition_is_marked(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """G3 (AC1): S2, single: the organisation « Zorbtech » under the place
    « à Zorbtech » is marked, by the place."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S2, S2_SPANS)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    lost = _mark(_not_written(sd.state, rows[(ORG_NAME, ORG)].entity_id))
    assert lost == (1, 1, ((AT_ORG, LOCATION),))  # expected failure
    assert _not_written(sd.state, rows[(AT_ORG, LOCATION)].entity_id) is None


def test_row_not_written_at_some_places_is_marked(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """G4 (AC1): S3, single: the place row (« à Zorbaville », two places) is
    not written at its second place, inside « Zorbtech Zorbaville »; the
    row written at each place is its own at the first, the organisation's
    at the second."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S3, S3_SPANS)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    pre(
        sorted(rows) == sorted([(AT_PLACE, LOCATION), (ORG_PLACE, ORG)]),
        f"one place row, one organisation row: {sorted(rows)}",
    )
    place, org = rows[(AT_PLACE, LOCATION)], rows[(ORG_PLACE, ORG)]
    lost = _mark(_not_written(sd.state, place.entity_id))
    assert lost == (1, 2, ((ORG_PLACE, ORG),))  # expected failure
    first_place = S3.index("Zorbaville") + 3
    second_place = S3.index("Zorbaville", S3.index(ORG_NAME)) + 3
    assert _writer_at(sd.state, first_place) == place.entity_id
    assert _writer_at(sd.state, second_place) == org.entity_id


def test_batch_worker_marks_and_saves_only_the_name_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """G5 (AC1, AC12): S1 with the place first through the real batch
    worker: the person row is marked, and only the place is saved."""
    batch = _Batch(qtbot, main_window, tmp_path, S1, _entities(S1, S1_PLACE_FIRST))
    record: dict[str, Any] = {}

    def body(_: dict[str, Any]) -> None:
        state = batch.wait_doc()
        _accept_all(state)
        record["lost"] = _not_written(state, _rows(state)[(ZORBAL, PERSON)].entity_id)
        batch.vs.finalize_button.click()

    batch.run(body)
    pre("lost" in record, f"the review was read: {sorted(record)}")
    pre(batch.output() != S1, "the document was written")
    assert _mark(record["lost"]) == (1, 1, ((ZORBAL, LOCATION),))  # expected failure
    assert _names(batch.db) == [(ZORBAL, LOCATION)]


def test_undo_brings_the_mark_back(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """G6 (AC1): S1 with the place first, every row accepted: the place row
    rejected, then the reject undone: the person row is marked again."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S1, S1_PLACE_FIRST)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    place, person = rows[(ZORBAL, LOCATION)], rows[(ZORBAL, PERSON)]
    sd.state.reject_entity(place.entity_id)
    sd.state.undo_stack.undo()
    pre(place.state.value == "confirmed", f"undone: {place.state.value}")
    after = _mark(_not_written(sd.state, person.entity_id))
    assert after == (1, 1, ((ZORBAL, LOCATION),))  # expected failure


def test_crossing_row_is_not_marked(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """G7 (AC1, the crossing rule): S4, single, every row accepted: the
    person « Zorbal Quentrix » is written over « Quentrix », so it is not
    marked; the organisation is written over « Zorbal » (12), the person
    over « Quentrix » (20)."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S4, S4_SPANS)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    org, person = rows[(ORG_ZORBAL, ORG)], rows[(ZQ, PERSON)]
    assert _not_written(sd.state, person.entity_id) is None  # expected failure
    assert _writer_at(sd.state, 12) == org.entity_id
    assert _writer_at(sd.state, 20) == person.entity_id


# ---------------------------------------------------------------------------
# H1, H2, H4: the review document's hover text shows (Lionel's Q4)
# ---------------------------------------------------------------------------


def test_hover_shows_both_rows_of_one_text(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """H1 (AC15): S1 with the place first, single, every row accepted: a
    hover over « Zorbal » shows both rows' blocks; a hover over the right
    half of its last letter shows the same."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S1, S1_PLACE_FIRST)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    shown = {key: sd.state.get_pseudonym(row.entity_id) for key, row in rows.items()}
    editor = _editor(qtbot, sd.state)
    blocks = _format_blocks(editor, 14)
    pre(len(blocks) == 2, f"two highlighted rows at « Zorbal »: {len(blocks)}")
    visible, text = _hover(qtbot, editor, _mid(editor, 14))
    assert visible  # expected failure
    for key in ((ZORBAL, LOCATION), (ZORBAL, PERSON)):
        assert _block_line(key[1], ZORBAL) in text
        assert f"→ {shown[key]}" in text
    assert "90%" in text
    for block in blocks:
        assert block in text
    last = QPoint(_rect(editor, 17).x() - 1, _rect(editor, 16).center().y())
    pre(
        editor.cursorForPosition(last).position() == 17,
        f"the point maps to the end boundary: {editor.cursorForPosition(last).position()}",
    )
    assert _hover(qtbot, editor, last) == (True, text)


def test_hover_shows_every_row_at_the_character(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """H2 (AC15): S3, single: over « Zorbaville » inside « Zorbtech
    Zorbaville », the organisation's and the place's blocks; over
    « Zorbtech », the organisation's only; over the first « Zorbaville »,
    the place's only."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S3, S3_SPANS)
    _accept_all(sd.state)
    pre(
        sorted(_rows(sd.state)) == sorted([(AT_PLACE, LOCATION), (ORG_PLACE, ORG)]),
        "one place row, one organisation row",
    )
    editor = _editor(qtbot, sd.state)
    org_line = _block_line(ORG, ORG_PLACE)
    place_line = _block_line(LOCATION, AT_PLACE)
    inside = S3.index("Zorbaville", S3.index(ORG_NAME)) + 4
    visible, text = _hover(qtbot, editor, _mid(editor, inside))
    assert visible  # expected failure
    assert org_line in text and place_line in text
    visible, text = _hover(qtbot, editor, _mid(editor, S3.index(ORG_NAME) + 3))
    assert visible and org_line in text and place_line not in text
    visible, text = _hover(qtbot, editor, _mid(editor, S3.index("Zorbaville") + 3))
    assert visible and place_line in text and org_line not in text


def test_hover_leaves_out_hidden_rows(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """H4 (AC15): S1 with the place first, single: the place row rejected
    and rejected rows hidden, a hover over « Zorbal » shows the person's
    block only."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S1, S1_PLACE_FIRST)
    _accept_all(sd.state)
    rows = _rows(sd.state)
    editor = _editor(qtbot, sd.state)
    sd.state.reject_entity(rows[(ZORBAL, LOCATION)].entity_id)
    editor.refresh_all()
    editor.set_hide_rejected(True)
    visible, text = _hover(qtbot, editor, _mid(editor, 14))
    assert visible  # expected failure
    assert _block_line(PERSON, ZORBAL) in text
    assert _block_line(LOCATION, ZORBAL) not in text


# ---------------------------------------------------------------------------
# Controls (unmarked; pass on the base and the head)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", ["place_first", "partial_place"])
def test_desktop_written_spans_and_types_unchanged(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws, case
) -> None:
    """GK1 (AC6): single, every row accepted (S1 with the place first, S3):
    the spans written and their types are those today's rule gives over the
    list the end receives."""
    text, spans = {
        "place_first": (S1, S1_PLACE_FIRST),
        "partial_place": (S3, S3_SPANS),
    }[case]
    dialogs = _Dialogs(monkeypatch)
    received = _Received(monkeypatch)
    db = _new_db(tmp_path)
    sd = _single(qtbot, main_window, tmp_path, db, text, spans)
    written_text = sd.finalize(dialogs)
    sent = received.one()
    kept = sorted(
        (sent[i] for i in _today([(e.start_pos, e.end_pos) for e in sent])),
        key=lambda entity: entity.start_pos,
    )
    expected = [
        _prefix(entity) + _row(db, entity.text, entity.entity_type).pseudonym_full
        for entity in kept
    ]
    written = _replacements(
        written_text, text, [(e.start_pos, e.end_pos) for e in kept]
    )
    assert written == expected


def test_batch_rejecting_the_written_row_writes_the_other(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """GK2 (AC6): S1 with the place first, batch: the place row rejected,
    the person row's pseudonym is written."""
    batch = _Batch(qtbot, main_window, tmp_path, S1, _entities(S1, S1_PLACE_FIRST))
    record: dict[str, Any] = {}

    def body(_: dict[str, Any]) -> None:
        state = batch.wait_doc()
        rows = _rows(state)
        state.reject_entity(rows[(ZORBAL, LOCATION)].entity_id)
        _accept_all(state)
        record["shown"] = state.get_pseudonym(rows[(ZORBAL, PERSON)].entity_id)
        batch.vs.finalize_button.click()

    batch.run(body)
    pre("shown" in record, f"the review was read: {sorted(record)}")
    written = _replacements(batch.output(), S1, [ZORBAL_SPAN])
    assert written == [record["shown"]]
    assert (ZORBAL, PERSON) in _names(batch.db)


def test_hover_shows_a_tooltip_of_the_document_format(qtbot) -> None:  # type: ignore[no-untyped-def]
    """H0 (AC15, the leg's own proof): a plain ``QTextEdit`` holding S1 with
    a tooltip on the document's own character format over « Zorbal »: a
    hover there shows it. So a leg that passes this can show a tooltip.

    Run with no application style sheet. A test that shows the main window
    leaves the theme's style sheet on the application; it pads the editor
    (viewport at (10, 8)), and Qt reads a document format's tooltip at the
    pointer moved by that offset, below this one-line text."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        pytest.fail("PRE: a QApplication")
    sheet = app.styleSheet()
    app.setStyleSheet("")
    try:
        editor = QTextEdit()
        qtbot.addWidget(editor)
        editor.resize(700, 300)
        editor.setPlainText(S1)
        editor.show()
        QApplication.processEvents()
        cursor = editor.textCursor()
        cursor.setPosition(ZORBAL_SPAN[0])
        cursor.setPosition(ZORBAL_SPAN[1], QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setToolTip(HINT)
        cursor.mergeCharFormat(fmt)
        hovered = _hover(qtbot, editor, _mid(editor, 14))
    finally:
        app.setStyleSheet(sheet)
    assert hovered == (True, HINT)


def test_no_tooltip_without_a_row(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, draws
) -> None:
    """H3 (AC15): S6 (line 1 is « Zorbal », a row): no tooltip over
    « Réponse » (no row), nor 40 pixels right of line 1's end."""
    sd = _single(qtbot, main_window, tmp_path, _new_db(tmp_path), S6, S6_SPANS)
    _accept_all(sd.state)
    editor = _editor(qtbot, sd.state)
    visible, _ = _hover(qtbot, editor, _mid(editor, S6.index("Réponse") + 2))
    assert not visible
    end = _rect(editor, len(ZORBAL))
    visible, _ = _hover(qtbot, editor, QPoint(end.x() + 40, end.center().y()))
    assert not visible
