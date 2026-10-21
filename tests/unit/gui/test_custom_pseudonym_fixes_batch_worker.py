"""Story 10.16: a custom pseudonym follows the current name, in desktop batch
review through the real batch worker (T14; Codex release review #7).

Each test drives the real ``BatchScreen``, ``ValidationScreen`` and
``BatchWorker`` thread; only ``DocumentProcessor._detect_and_filter_entities``
is replaced (Story 10.10's harness, as in Story 10.11's
``test_custom_pseudonym_batch_worker.py``). The correction, the type change
and the pseudonym go through ``ValidationScreen._handle_entity_action``, with
``QInputDialog.getText`` replaced and the messages recorded from
``ConfirmDialog.informational``. The assertions run after the worker has
finished, on the written file and the stored rows.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict ``xfail(raises=AssertionError)`` never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names only.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QInputDialog

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import EntityReviewState

# _launch_worker disconnects two slots that are not connected yet
# (batch.py:699-708). PySide6 warns instead of raising RuntimeError there, and
# pytest.ini turns warnings into errors, so exactly those two warnings are
# filtered (as in Story 10.10's test_batch_review_real_worker.py). This is a
# warnings filter, not a skip.
pytestmark = pytest.mark.filterwarnings(
    r"ignore:Failed to disconnect \(<bound method BatchScreen\.(_on_validation_complete|_do_cancel) :RuntimeWarning"
)

PASSPHRASE = "zorbalia_pass_A_123!"
WAIT_MS = 60000
PENDING = EntityReviewState.PENDING

QZ = "Quentrel Zorbalia"
TITLED = "M. Quentrel Zorbalia"
CORRECTED = "Quentrel Zorbalia Quovan"
CUSTOM = "Xantor Vellion"

DOC_CORR = (
    "Quentrel Zorbalia Quovan a signé le contrat. "
    "Le contrat est avec M. Quentrel Zorbalia."
)
DOC_TYPE = (
    "Quentrel Zorbalia a signé le contrat. Le contrat est avec M. Quentrel Zorbalia."
)


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test with "PRE: ..." (``pytest.fail``
    raises ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _words(text: str) -> list[str]:
    """The folded whole words of ``text`` (accents and capitals ignored)."""
    decomposed = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.findall(r"\w+", folded.casefold())


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    pre(text[start : start + len(name)] == name, f"slice {name!r}")
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _replacements(output: str, source: str, spans: list[tuple[int, int]]) -> list[str]:
    """The string written in place of each span (in span order); every other
    character of the source unchanged."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    if match is None:
        pytest.fail(f"PRE: text damaged or a span not replaced: {output!r}")
    return list(match.groups())


def _stored(db: str, key: str, entity_type: str) -> tuple[Any, ...] | None:
    """(full_name, first_name, last_name, pseudonym_full, pseudonym_first,
    pseudonym_last) of the stored row of (key, type), or None."""
    with open_database(db, PASSPHRASE) as session:
        row = SQLiteMappingRepository(session).find_by_full_name_and_type(
            key, entity_type
        )
        if row is None:
            return None
        return (
            row.full_name,
            row.first_name,
            row.last_name,
            row.pseudonym_full,
            row.pseudonym_first,
            row.pseudonym_last,
        )


class _Dialogs:
    """Records ``ConfirmDialog.informational`` calls instead of showing them."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[tuple[str, str]] = []
        recorder = self

        class _Shown:
            def exec(self) -> int:
                return 0

        def informational(  # type: ignore[no-untyped-def]
            cls, title, message, dismiss_label="", parent=None
        ):
            recorder.calls.append((str(title), str(message)))
            return _Shown()

        monkeypatch.setattr(ConfirmDialog, "informational", classmethod(informational))


class _Batch:
    """A real batch run with validation per document; only detection replaced
    (Story 10.10's harness, test_batch_review_real_worker.py)."""

    def __init__(
        self,
        qtbot: Any,
        main_window: Any,
        tmp_path: Path,
        docs: list[tuple[str, list[DetectedEntity]]],
    ) -> None:
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        self.qtbot = qtbot
        self.mw = main_window
        source_dir = tmp_path / "in"
        source_dir.mkdir()
        self.out = tmp_path / "out"
        self.db = str(tmp_path / "mappings.db")
        init_database(self.db, PASSPHRASE)
        self._by_text: dict[str, list[DetectedEntity]] = {}
        files: list[Path] = []
        for index, (text, entities) in enumerate(docs):
            path = source_dir / f"doc{index}.txt"
            path.write_text(text, encoding="utf-8")
            files.append(path)
            self._by_text[text] = entities
        main_window.show()
        main_window.navigate_to("batch")
        self.bs = main_window.stack.currentWidget()
        pre(isinstance(self.bs, BatchScreen), "batch screen")
        self.vs = main_window.stack.widget(main_window._screens["validation"])
        pre(isinstance(self.vs, ValidationScreen), "validation screen")
        self.bs._files = files
        self.bs._output_input.setText(str(self.out))
        self.bs._validate_checkbox.setChecked(True)

    def _detect(self, text: str) -> list[DetectedEntity]:
        return [DetectedEntity(**vars(e)) for e in self._by_text[text]]

    def run(self, body: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Run the batch; ``body`` drives it. Returns what ``body`` recorded."""
        record: dict[str, Any] = {}
        with patch.object(
            DocumentProcessor, "_detect_and_filter_entities", side_effect=self._detect
        ):
            self.bs._launch_worker(self.db, PASSPHRASE)
            try:
                body(record)
                self.qtbot.waitUntil(lambda: self.bs._worker is None, timeout=WAIT_MS)
            finally:
                if self.bs._worker is not None:
                    self.bs._worker.cancel()
                    self.qtbot.waitUntil(
                        lambda: self.bs._worker is None, timeout=WAIT_MS
                    )
        return record

    def wait_doc(self, index: int) -> Any:
        """Wait until document ``index`` is waiting; return its review state."""
        vs, bs = self.vs, self.bs
        self.qtbot.waitUntil(
            lambda: self.mw.stack.currentWidget() is vs
            and vs.doc_index == index
            and vs.validation_state is not None
            and bs._worker is not None
            and bs._worker._waiting_for_validation,
            timeout=WAIT_MS,
        )
        return vs.validation_state

    def action(
        self, monkeypatch: pytest.MonkeyPatch, entity_id: str, action: str, text: str
    ) -> None:
        """A row's action through the screen, the user typing ``text`` in
        the dialog it opens."""
        monkeypatch.setattr(
            QInputDialog, "getText", staticmethod(lambda *a, **k: (text, True))
        )
        self.vs._handle_entity_action(entity_id, action)

    def accept_pending_and_validate(self) -> None:
        state = self.vs.validation_state
        for review in state.get_all_entities():
            if review.state == PENDING:
                state.accept_entity(review.entity_id)
        self.vs.finalize_button.click()


@pytest.mark.parametrize("case", ["corrected", "retyped"])
def test_batch_custom_follows_the_current_name(  # type: ignore[no-untyped-def]
    qtbot, main_window, tmp_path, monkeypatch, case
) -> None:
    """T14 (AC3, #7): the first place of the name is corrected into another
    name (or retyped ORG); "Xantor Vellion" set on « M. Quentrel Zorbalia »
    then reaches that place only, and the document is written: the titled
    place takes the pseudonym, the first place its own generated one, and
    each name its own row."""
    dialogs = _Dialogs(monkeypatch)
    corrected = case == "corrected"
    text = DOC_CORR if corrected else DOC_TYPE
    first = _at(text, QZ, "PERSON", 0)
    titled = _at(text, TITLED, "PERSON", text.find(TITLED))
    batch = _Batch(qtbot, main_window, tmp_path, [(text, [first, titled])])

    def body(record: dict[str, Any]) -> None:
        state = batch.wait_doc(0)
        rows = {r.entity.start_pos: r for r in state.get_all_entities()}
        pre(sorted(rows) == [first.start_pos, titled.start_pos], "two rows")
        r1, r2 = rows[first.start_pos], rows[titled.start_pos]
        if corrected:
            batch.action(monkeypatch, r1.entity_id, "modify_text", CORRECTED)
            pre(
                r1.user_modification == CORRECTED and r2.user_modification is None,
                "the first row corrected, the titled row not",
            )
        else:
            batch.action(monkeypatch, r1.entity_id, "change_type:ORG", "")
            pre(
                r1.entity.entity_type == "ORG" and r2.entity.entity_type == "PERSON",
                "the first row retyped ORG, the titled row not",
            )
        batch.action(monkeypatch, r2.entity_id, "change_pseudonym", CUSTOM)
        pre(
            dialogs.calls == [] and r2.custom_pseudonym == CUSTOM,
            f"set on the titled row without a message: {dialogs.calls!r}",
        )
        record["customs"] = [r1.custom_pseudonym, r2.custom_pseudonym]
        batch.accept_pending_and_validate()

    record = batch.run(body)
    output = batch.out / "doc0_pseudonymized.txt"
    assert output.exists(), dialogs.calls  # expected failure
    first_end = len(CORRECTED) if corrected else len(QZ)
    spans = [(0, first_end), (titled.start_pos, titled.end_pos)]
    first_place, titled_place = _replacements(
        output.read_text(encoding="utf-8"), text, spans
    )
    assert titled_place == f"M. {CUSTOM}", titled_place
    assert first_place != CUSTOM, first_place
    assert not {"quentrel", "zorbalia", "quovan"} & set(_words(first_place))
    assert record["customs"] == [None, CUSTOM], record
    assert _stored(batch.db, QZ, "PERSON") == (
        QZ,
        "Quentrel",
        "Zorbalia",
        CUSTOM,
        "Xantor",
        "Vellion",
    )
    first_name = (CORRECTED, "PERSON") if corrected else (QZ, "ORG")
    stored = _stored(batch.db, *first_name)
    assert stored is not None and stored[3] == first_place, stored
