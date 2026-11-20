"""Story 13.1: the desktop review shows a place pseudonym that fits the word
before the place, and writes it (P11, P12).

Written by the BMAD dev agent (Claude), tests first. SD = single document
(the real ``DetectionWorker``, ``ValidationScreen`` and ``FinalizationWorker``)
and BW = a real batch run, both Story 11.5's harnesses
(``test_review_list_written_pseudonym_review``). The library's draw is Story
11.5's stand-in (each list walked from its first value), so a review that
loses the word shows the first city. The names a word allows are read with
``_pool`` (``tests/unit/test_place_word.py``), with every draw real.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names only.
"""

from __future__ import annotations

from typing import Any

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from tests.unit.gui.test_review_list_written_pseudonym_review import (
    _at,
    _Batch,
    _Dialogs,
    _Ends,
    _new_db,
    _one_row,
    _Single,
    _spans,
)
from tests.unit.test_custom_pseudonym_fixes_cli import _replacements, pre
from tests.unit.test_place_word import (
    EN_TEXT,
    FIRST,
    LOCATION,
    ORG,
    THEME,
    V,
    _en_names,
    _list,
)
from tests.unit.test_review_list_written_pseudonym import _Draws, install_draws

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 11.5's test_review_list_written_pseudonym_review.py).
# This is a warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

SITE_TEXT = f"Le site est en {V}."
LATER_TEXT = f"{V} a signé le contrat. Le site est en {V}."
PREVIEW_TEXT = f"{V} a signé le contrat. {EN_TEXT}"


@pytest.fixture
def draws(monkeypatch: pytest.MonkeyPatch) -> _Draws:
    return install_draws(monkeypatch)


def _every(text: str, entity_type: str) -> list[DetectedEntity]:
    """Every place of « Vellionie » in ``text``, as ``entity_type``."""
    starts = [i for i in range(len(text)) if text.startswith(V, i)]
    pre(bool(starts), f"{V!r} in {text!r}")
    return [_at(text, V, entity_type, start) for start in starts]


def _fits(value: str) -> bool:
    """A feminine region: what follows « en »."""
    return value in _list(THEME, "countries") and value in _en_names()


@FIRST
@pytest.mark.parametrize("case", ["single", "batch", "single_later_word"])
def test_desktop_retyped_place_fits_the_word(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws, case
) -> None:
    """P11 (AC1, AC7): a name found as an organisation and retyped as a place
    shows, at once, a name of its word (« en »: a feminine region), read at
    every place the end receives; it is written, and nothing is reported."""
    _en_names()  # read before the review, with every draw real
    ends = _Ends(monkeypatch)
    text = LATER_TEXT if case == "single_later_word" else SITE_TEXT
    entities = _every(text, ORG)
    if case == "batch":
        batch = _Batch(qtbot, main_window, tmp_path, text, entities)

        def body(record: dict[str, Any]) -> None:
            state = batch.wait_doc()
            row = _one_row(state)
            state.change_entity_type(row.entity_id, LOCATION)
            record["shown"] = state.get_pseudonym(row.entity_id)
            batch.accept_pending_and_validate()

        shown = str(batch.run(body).get("shown", ""))
        output = batch.output()
    else:
        dialogs = _Dialogs(monkeypatch)
        sd = _Single(qtbot, main_window, tmp_path, _new_db(tmp_path), text, entities)
        row = sd.row(V)
        sd.state.change_entity_type(row.entity_id, LOCATION)
        shown = sd.state.get_pseudonym(row.entity_id)
        output = sd.finalize(dialogs)
    pre(bool(shown), "the row shows a pseudonym")
    assert _fits(shown), shown  # expected failure
    assert _replacements(output, text, _spans(entities)) == [shown] * len(entities)
    assert ends.changed() == []


@FIRST
@pytest.mark.parametrize("case", ["single", "batch"])
def test_desktop_preview_reads_every_place(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, draws, case
) -> None:
    """P12 (AC1, AC7): the place's first preview, before any action, is a
    name of its word, read at every place detected (single document: the
    first place has no word, the second « en »); it is written, and nothing
    is reported."""
    _en_names()  # read before the review, with every draw real
    ends = _Ends(monkeypatch)
    text = PREVIEW_TEXT if case == "single" else EN_TEXT
    entities = _every(text, LOCATION)
    if case == "batch":
        batch = _Batch(qtbot, main_window, tmp_path, text, entities)

        def body(record: dict[str, Any]) -> None:
            state = batch.wait_doc()
            record["shown"] = state.get_pseudonym(_one_row(state).entity_id)
            batch.accept_pending_and_validate()

        shown = str(batch.run(body).get("shown", ""))
        output = batch.output()
    else:
        dialogs = _Dialogs(monkeypatch)
        sd = _Single(qtbot, main_window, tmp_path, _new_db(tmp_path), text, entities)
        shown = sd.shown(V)
        output = sd.finalize(dialogs)
    pre(bool(shown), "the row shows a pseudonym")
    assert _fits(shown), shown  # expected failure
    assert _replacements(output, text, _spans(entities)) == [shown] * len(entities)
    assert ends.changed() == []
