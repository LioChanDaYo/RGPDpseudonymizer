"""Story 11.2: custom pseudonyms refused at finalization, in the desktop
review (T8).

Two names of one document share a real first name, « Xantor »: « Dravin
Brontel » is set for « Xantor Velmar » and « Dravin Le Vorlan » for « Xantor
Quentrel », in either order. The review splits the particle surname after
« Dravin », because the other custom pseudonym already gives « Xantor » the
part « Dravin » (MW-001 (b)). Finalization used to split it with the stored
parts only, so both were refused there and nothing was written; in the other
order, the second was refused when it was set.

SD = single document, through the harness of Story 10.16's
``test_custom_pseudonym_fixes_review.py``: the real ``DetectionWorker`` run
synchronously with detection replaced, the real ``ValidationScreen`` and the
real ``FinalizationWorker``; the change-pseudonym dialog through
``_show_change_pseudonym_dialog`` with ``QInputDialog.getText`` replaced, the
messages recorded from ``ConfirmDialog.informational`` (no modal dialog), and
the written text read from the results screen.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict expected-failure marker never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names and main-corpus words only.
"""

from __future__ import annotations

from typing import Any

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from tests.unit.gui.test_custom_pseudonym_fixes_review import (
    _at,
    _Dialogs,
    _new_db,
    _replacements,
    _Single,
    _spans,
    _stored,
    pre,
)

VELMAR = "Xantor Velmar"
QUENTREL = "Xantor Quentrel"
PLAIN = "Dravin Brontel"
PARTICLE = "Dravin Le Vorlan"

DOC = (
    "Présents : Xantor Velmar et Xantor Quentrel. " "Xantor Velmar a signé le contrat."
)


def _entities() -> list[DetectedEntity]:
    """Both places of « Xantor Velmar » and the place of « Xantor
    Quentrel »."""
    first = DOC.find(VELMAR)
    return [
        _at(DOC, VELMAR, "PERSON", first),
        _at(DOC, QUENTREL, "PERSON", DOC.find(QUENTREL)),
        _at(DOC, VELMAR, "PERSON", DOC.find(VELMAR, first + 1)),
    ]


@pytest.mark.parametrize("order", ["velmar_first", "quentrel_first"])
def test_desktop_shared_first_name_particle_surname_written(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, order
) -> None:
    """T8 (AC1): the change-pseudonym dialog with « Dravin Brontel » on
    « Xantor Velmar » and « Dravin Le Vorlan » on « Xantor Quentrel », in either
    order: no message at either set, finalization succeeds, both are written
    at their places and stored with the parts the review used."""
    dialogs = _Dialogs(monkeypatch)
    db = _new_db(tmp_path)
    entities = _entities()
    sd = _Single(qtbot, main_window, tmp_path, db, DOC, entities)
    sets = [(VELMAR, PLAIN), (QUENTREL, PARTICLE)]
    if order == "quentrel_first":
        sets.reverse()
    rows: dict[str, Any] = {name: sd.row(name) for name, _ in sets}
    for name, custom in sets:
        sd.dialog(monkeypatch, rows[name].entity_id, custom)
        assert dialogs.calls == [], dialogs.calls  # expected (quentrel_first)
        pre(rows[name].custom_pseudonym == custom, f"{custom!r} set on {name!r}")
    sd.accept_pending()
    written = sd.finalize(dialogs)
    assert written is not None, dialogs.calls  # expected failure (velmar_first)
    spans = _spans(entities)
    replaced = _replacements(written, DOC, spans)
    places = [replaced[spans.index((e.start_pos, e.end_pos))] for e in entities]
    assert places == [PLAIN, PARTICLE, PLAIN], written
    assert _stored(db, VELMAR, "PERSON") == (
        VELMAR,
        "Xantor",
        "Velmar",
        PLAIN,
        "Dravin",
        "Brontel",
    )
    assert _stored(db, QUENTREL, "PERSON") == (
        QUENTREL,
        "Xantor",
        "Quentrel",
        PARTICLE,
        "Dravin",
        "Le Vorlan",
    )
