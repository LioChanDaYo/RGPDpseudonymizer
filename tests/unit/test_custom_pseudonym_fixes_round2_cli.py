"""Story 10.16, round 2: a separate accent mark in the custom pseudonym checks,
in the command line and finalization (T18-T24; Codex's review of 463481a, the
orchestrator's ruling).

Written by the BMAD dev agent (Claude). CR = the real ``gdpr-pseudo process``
and ``batch --workers 1`` commands through ``CliRunner``, on a database made
by the real ``init`` command, as Story 10.15's harness
(``test_cli_corrections_hand_added.py``): detection is replaced by a fake that
finds the names given, the keys, the typed texts and the yes/no answers come
from lists, and the warnings shown and each ``ProcessingResult`` are recorded.
CO = ``DocumentProcessor.finalize_document``.

The texts are written composed in this file. Each test builds its forms at
run time with ``unicodedata.normalize``: ``[name_decomposed]`` the document
(and so every name in it) in NFD and the typed pseudonym in NFC;
``[pseudonym_decomposed]`` the reverse; ``[both_decomposed]`` both NFD. No
combining mark is written in this file.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). A refusal when the pseudonym is set is
asserted as exactly one warning, not empty; the finalization error is
Lionel's approved text, byte for byte. Invented names and main-corpus words
only. No spaCy model, no Qt.
"""

from __future__ import annotations

import dataclasses
import re
import unicodedata
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import readchar
from rich.prompt import Confirm, Prompt
from typer.testing import CliRunner

import gdpr_pseudonymizer.pseudonym.library_manager as library_module
import gdpr_pseudonymizer.validation.workflow as workflow_module
from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from tests.unit.test_custom_pseudonym_fixes_cli import (
    IN_DOCUMENT,
    PASSPHRASE,
    _at,
    _finalize,
    _fold,
    _new_db,
    _one_warning,
    _replacements,
    _row_count,
    _store_first_doc,
    _stored,
    _words,
    pre,
)

ENV = {"GDPR_PSEUDO_PASSPHRASE": PASSPHRASE}
ENTER = "\r"
SPACE = " "
MAX_KEYS = 60
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

NAME_DECOMPOSED = "name_decomposed"
PSEUDONYM_DECOMPOSED = "pseudonym_decomposed"
BOTH_DECOMPOSED = "both_decomposed"
FORMS = [NAME_DECOMPOSED, PSEUDONYM_DECOMPOSED, BOTH_DECOMPOSED]
MODES = ["process", "batch"]

SET_DOC = "quentrel zórbalia a signé le contrat."
SET_NAME = "quentrel zórbalia"
SHARED = "Xantor Zórbalia"
NOT_SHARED = "Xantor Véllion"
ADD_DOC = "quentrel quovan a signé avec quovix et zórbalia."
ADDED = "zórbalia"
QC_DOC = "Zórbaville a signé avec quentrel quovan."
QC_NAME = "quentrel quovan"
QC_PSEUDO = "Xantor Zórbaville"
PLACE_DOC = "Le contrat est signé à Zorbaville."
ORG_DOC = "Le contrat est signé avec Zorbaville."
OFFERED_WHOLE = "Xántor Véllion"
REJECTED_OWN = "quentrel zorbalia a signé avec quovan."
REJECTED_OTHER = "quentrix a signé avec zorbix velmar."

Form = Callable[[str], str]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


def _forms(form: str) -> tuple[Form, Form]:
    """(the document's form, the typed pseudonym's form)."""
    document = _nfd if form in (NAME_DECOMPOSED, BOTH_DECOMPOSED) else _nfc
    typed = _nfd if form in (PSEUDONYM_DECOMPOSED, BOTH_DECOMPOSED) else _nfc
    return document, typed


def _cases(modes: Sequence[str]) -> list[Any]:
    """Each mode with each form (on 463481a every case but
    ``[both_decomposed]`` failed; both sides are cut alike there)."""
    return [
        pytest.param(
            mode,
            form,
            id=f"{mode}-{form}",
        )
        for mode in modes
        for form in FORMS
    ]


# ---------------------------------------------------------------------------
# CR harness (copied from Story 10.15's test_cli_corrections_hand_added.py,
# with the warnings and the results recorded)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The command reads no user or project settings file."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """A new database, made by the real ``init`` command."""
    path = tmp_path / "mappings.db"
    result = CliRunner().invoke(
        app, ["init", "--db", str(path)], env=ENV, catch_exceptions=False
    )
    pre(result.exit_code == 0 and path.is_file(), "init made the database")
    return path


class FakeDetector:
    """Finds every occurrence of each (name, type) given, and drops an
    occurrence that lies inside a longer one it found."""

    def __init__(self, names: Sequence[tuple[str, str]]) -> None:
        self.names = list(names)

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        found: list[DetectedEntity] = []
        for name, entity_type in self.names:
            # Story 10.20 (AC1): the reader returns the document composed, so
            # each name is looked for in its composed and decomposed spellings
            for form in dict.fromkeys((_nfc(name), _nfd(name))):
                start = text.find(form)
                while start != -1:
                    found.append(
                        DetectedEntity(
                            text=form,
                            entity_type=entity_type,
                            start_pos=start,
                            end_pos=start + len(form),
                            confidence=0.9,
                            source="spacy",
                        )
                    )
                    start = text.find(form, start + 1)
        return [
            entity
            for entity in found
            if not any(
                other.start_pos <= entity.start_pos
                and entity.end_pos <= other.end_pos
                and other.end_pos - other.start_pos > entity.end_pos - entity.start_pos
                for other in found
            )
        ]


class Keys:
    """``readchar.readkey``: the keys in order, then Space."""

    def __init__(self, keys: Sequence[str]) -> None:
        self.keys = list(keys)
        self.read = 0

    def __call__(self) -> str:
        self.read += 1
        if self.read > MAX_KEYS:
            raise RuntimeError("more than 60 keys read")
        return self.keys.pop(0) if self.keys else SPACE


class Typed:
    """``Prompt.ask``: the typed texts in order."""

    def __init__(self, texts: Sequence[str]) -> None:
        self.texts = list(texts)

    def __call__(self, prompt: Any, *args: Any, **kwargs: Any) -> str:
        if not self.texts:
            raise RuntimeError("no typed text left")
        return self.texts.pop(0)


class Answers:
    """``Confirm.ask``: yes to every question; records each question."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def __call__(self, prompt: Any, *args: Any, **kwargs: Any) -> bool:
        self.asked.append(str(prompt))
        return True


@dataclasses.dataclass
class CliRun:
    """One command run: its exit code and output, the warnings shown, the
    ``ProcessingResult`` of each document, the texts left untyped and the
    path the document is written to."""

    exit_code: int
    shown: str
    warnings: list[str]
    results: list[ProcessingResult]
    typed_left: int
    output: Path


def _cli(
    tmp_path: Path,
    db: Path,
    mode: str,
    text: str,
    names: Sequence[tuple[str, str]],
    keys: Sequence[str],
    typed: Sequence[str],
) -> CliRun:
    """One real ``process`` run (``in/doc.txt`` to ``doc_out.txt``) or
    ``batch --workers 1`` run (the folder ``in`` to ``out/``)."""
    source_dir = tmp_path / "in"
    source_dir.mkdir(exist_ok=True)
    source = source_dir / "doc.txt"
    source.write_text(text, encoding="utf-8")
    if mode == "process":
        output = tmp_path / "doc_out.txt"
        args = ["process", str(source), "--db", str(db), "-o", str(output)]
    else:
        output = tmp_path / "out" / "doc_pseudonymized.txt"
        args = [
            "batch",
            str(source_dir),
            "--db",
            str(db),
            "--output",
            str(tmp_path / "out"),
            "--workers",
            "1",
        ]
    detector = FakeDetector(names)
    typed_texts = Typed(typed)
    warnings: list[str] = []
    results: list[ProcessingResult] = []
    real_warning = workflow_module.display_warning_message
    real_process = DocumentProcessor.process_document

    def warning(message: Any) -> Any:
        warnings.append(str(message))
        return real_warning(message)

    def process(self: Any, *args: Any, **kwargs: Any) -> ProcessingResult:
        result = real_process(self, *args, **kwargs)
        results.append(result)
        return result

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(DocumentProcessor, "_get_detector", new=lambda self: detector)
        )
        stack.enter_context(
            patch.object(
                DocumentProcessor,
                "_detect_and_filter_entities",
                new=lambda self, text, entity_type_filter=None: (
                    detector.detect_entities(text)
                ),
            )
        )
        stack.enter_context(
            patch.object(DocumentProcessor, "process_document", process)
        )
        stack.enter_context(
            patch.object(workflow_module, "display_warning_message", warning)
        )
        stack.enter_context(patch.object(readchar, "readkey", new=Keys(keys)))
        stack.enter_context(patch.object(Prompt, "ask", new=typed_texts))
        stack.enter_context(patch.object(Confirm, "ask", new=Answers()))
        result = CliRunner().invoke(app, args, env=ENV, catch_exceptions=False)
    return CliRun(
        result.exit_code,
        _ANSI.sub("", result.output),
        warnings,
        results,
        len(typed_texts.texts),
        output,
    )


def _text_of(path: Path) -> str:
    """The text written at ``path``, for an assertion's message."""
    return path.read_text(encoding="utf-8")


@contextmanager
def _first_call_offers(method: str, offered: str) -> Iterator[dict[str, int]]:
    """The library's ``method`` (``_select_location`` or
    ``_select_organization``) gets ``offered`` from the first
    ``secrets.choice`` of its first call; later calls are real (T41's way,
    without a real word). Yields the number of offers."""
    original = getattr(library_module.LibraryBasedPseudonymManager, method)
    real_choice = library_module.secrets.choice
    offers = {"n": 0, "calls": 0}

    def offering(self: Any, *args: Any, **kwargs: Any) -> Any:
        offers["calls"] += 1
        if offers["calls"] > 1:
            return original(self, *args, **kwargs)
        choices = {"n": 0}

        def choice(seq: Any) -> Any:
            choices["n"] += 1
            if choices["n"] == 1:
                offers["n"] += 1
                return offered
            return real_choice(seq)

        with patch.object(library_module.secrets, "choice", choice):
            return original(self, *args, **kwargs)

    with patch.object(library_module.LibraryBasedPseudonymManager, method, offering):
        yield offers


# ---------------------------------------------------------------------------
# A separate accent mark when the pseudonym is set (T18), and when the name is
# marked after it (T19); the guards (T20); the document's words (T21)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode, form", _cases(MODES))
def test_cli_accents_refused_when_set(
    tmp_path: Path, db: Path, mode: str, form: str
) -> None:
    """T18 (AC1, round 2): [C] "Xantor Zórbalia" on « quentrel zórbalia » is
    refused with one warning whether the name, the pseudonym or both are
    written with a separate accent mark; the name is written with a
    generated pseudonym and stored so."""
    document, typed_form = _forms(form)
    text, name = document(SET_DOC), document(SET_NAME)
    run = _cli(
        tmp_path,
        db,
        mode,
        text,
        [(name, "PERSON")],
        [ENTER, "c", SPACE],
        [typed_form(SHARED)],
    )
    pre(len(run.results) == 1, f"one document processed: {run.shown!r}")
    pre(run.typed_left == 0, "every text typed")
    assert _one_warning(run.warnings), run.warnings  # expected failure
    pre(run.output.exists(), "written")
    written = run.output.read_text(encoding="utf-8")
    (place,) = _replacements(written, _nfc(text), [(0, len(_nfc(name)))])
    assert not {"quentrel", "zorbalia"} & set(_words(place)), written
    stored = _stored(str(db), name, "PERSON")
    assert stored is not None and stored[3] == place, stored


@pytest.mark.parametrize("mode, form", _cases(MODES))
def test_cli_accents_name_added_after_the_pseudonym(
    tmp_path: Path, db: Path, mode: str, form: str
) -> None:
    """T19 (AC1, AC5; Lionel's 10.16 Q1): [C] "Xantor Zórbalia" on
    « quentrel quovan », then « zórbalia » added with [A]: the run fails with
    Lionel's new reason, whichever side is written with a separate accent
    mark; no file, no row."""
    document, typed_form = _forms(form)
    text = document(ADD_DOC)
    names = [(document("quentrel quovan"), "PERSON"), (document("quovix"), "PERSON")]
    run = _cli(
        tmp_path,
        db,
        mode,
        text,
        names,
        [ENTER, "c", "a", SPACE],
        [typed_form(SHARED), document(ADDED), "PERSON"],
    )
    pre(run.warnings == [], f"no warning: {run.warnings!r}")
    pre(len(run.results) == 1, f"one document processed: {run.shown!r}")
    pre(run.typed_left == 0, "every text typed")
    assert not run.output.exists(), _text_of(run.output)  # expected failure
    assert run.results[0].error_message == IN_DOCUMENT, run.results[0].error_message
    assert run.exit_code != 0
    assert _row_count(str(db)) == 0


@pytest.mark.parametrize("mode, form", [(m, f) for m in MODES for f in FORMS])
def test_cli_accents_without_shared_word_accepted(
    tmp_path: Path, db: Path, mode: str, form: str
) -> None:
    """T20 (a guard): "Xantor Véllion" shares no word with « quentrel
    zórbalia »: accepted without a warning in every form, written as typed
    and stored under the name as the document writes it."""
    document, typed_form = _forms(form)
    text, name, typed = document(SET_DOC), document(SET_NAME), typed_form(NOT_SHARED)
    run = _cli(tmp_path, db, mode, text, [(name, "PERSON")], [ENTER, "c"], [typed])
    pre(len(run.results) == 1, f"one document processed: {run.shown!r}")
    pre(run.typed_left == 0, "every text typed")
    assert run.warnings == [], run.warnings
    assert run.output.read_text(encoding="utf-8") == _nfc(typed + text[len(name) :])
    stored = _stored(str(db), name, "PERSON")
    assert stored is not None and stored[3] == _nfc(typed), stored


@pytest.mark.parametrize("mode, form", _cases(["process"]))
def test_cli_accents_capitalised_document_word(
    tmp_path: Path, db: Path, mode: str, form: str
) -> None:
    """T21 (AC1, round 2; Lionel's Q-C): next to « Zórbaville », capitalised
    and not detected, "Xantor Zórbaville" is refused with one warning
    whichever side is written with a separate accent mark."""
    document, typed_form = _forms(form)
    text, name = document(QC_DOC), document(QC_NAME)
    start = _nfc(text).find(_nfc(name))
    run = _cli(
        tmp_path,
        db,
        mode,
        text,
        [(name, "PERSON")],
        [ENTER, "c", SPACE],
        [typed_form(QC_PSEUDO)],
    )
    pre(len(run.results) == 1, f"one document processed: {run.shown!r}")
    pre(run.typed_left == 0, "every text typed")
    assert _one_warning(run.warnings), run.warnings  # expected failure
    pre(run.output.exists(), "written")
    written = run.output.read_text(encoding="utf-8")
    (place,) = _replacements(written, _nfc(text), [(start, start + len(_nfc(name)))])
    assert "zorbaville" not in _words(place), written


# ---------------------------------------------------------------------------
# Codex's P2: the whole-value clause of the generation guard (T22, CO)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["location", "org"])
def test_generation_whole_value_never_another_spelling(
    tmp_path: Path, kind: str
) -> None:
    """T22 (a guard; Codex's P2, QA's TEST-003): after "Xantor Vellion" is
    stored, a place or an organisation offered "Xántor Véllion" by the
    library is drawn again: neither the written replacement nor its stored
    row is that value, folded."""
    database = _new_db(tmp_path)
    _store_first_doc(tmp_path, database)
    text, entity_type, method = (
        (PLACE_DOC, "LOCATION", "_select_location")
        if kind == "location"
        else (ORG_DOC, "ORG", "_select_organization")
    )
    entity = _at(text, "Zorbaville", entity_type)
    output = tmp_path / "later.txt"
    with _first_call_offers(method, OFFERED_WHOLE) as offers:
        result = _finalize(database, text, [entity], output)
    pre(offers["n"] == 1, f"{OFFERED_WHOLE!r} offered once")
    pre(result.success, "a success")
    (written,) = _replacements(
        output.read_text(encoding="utf-8"), text, [(entity.start_pos, entity.end_pos)]
    )
    assert _fold(written) != "xantor vellion", written
    stored = _stored(database, "Zorbaville", entity_type)
    assert stored is not None and stored[3] == written, stored


# ---------------------------------------------------------------------------
# QA's TEST-001 and TEST-002 in the command line (T23, T24)
# ---------------------------------------------------------------------------


def test_cli_rejected_name_own_surname_refused(tmp_path: Path, db: Path) -> None:
    """T23 (a guard; QA's TEST-001, n1): the name a pseudonym replaces always
    counts, even after it was rejected: [R], [P] back, [C] "Xantor Zorbalia"
    gets one warning, and the name is written with a generated pseudonym."""
    names = [("quentrel zorbalia", "PERSON"), ("quovan", "PERSON")]
    run = _cli(
        tmp_path,
        db,
        "process",
        REJECTED_OWN,
        names,
        [ENTER, "r", "p", "c", SPACE, SPACE],
        ["Xantor Zorbalia"],
    )
    pre(len(run.results) == 1, f"one document processed: {run.shown!r}")
    pre(run.typed_left == 0, "every text typed")
    assert _one_warning(run.warnings), run.warnings
    assert run.output.exists()
    written = run.output.read_text(encoding="utf-8")
    name = _at(REJECTED_OWN, "quentrel zorbalia", "PERSON", 0)
    other = _at(REJECTED_OWN, "quovan", "PERSON")
    place = _replacements(
        written,
        REJECTED_OWN,
        [(name.start_pos, name.end_pos), (other.start_pos, other.end_pos)],
    )[0]
    assert not {"quentrel", "zorbalia"} & set(_words(place)), written
    stored = _stored(str(db), "quentrel zorbalia", "PERSON")
    assert stored is not None and stored[3] == place, stored


def test_cli_rejected_name_does_not_count(tmp_path: Path, db: Path) -> None:
    """T24 (a guard; QA's TEST-002, n3): a name rejected in the command-line
    review does not count: "Xantor Quentrix" on « zorbix velmar », after
    « quentrix » was rejected, is accepted and written."""
    names = [("quentrix", "PERSON"), ("zorbix velmar", "PERSON")]
    run = _cli(
        tmp_path,
        db,
        "process",
        REJECTED_OTHER,
        names,
        [ENTER, "r", "c"],
        ["Xantor Quentrix"],
    )
    pre(len(run.results) == 1, f"one document processed: {run.shown!r}")
    pre(run.typed_left == 0, "every text typed")
    assert run.warnings == [], run.warnings
    assert run.output.read_text(encoding="utf-8") == (
        "quentrix a signé avec Xantor Quentrix."
    )
    stored = _stored(str(db), "zorbix velmar", "PERSON")
    assert stored is not None and stored[3] == "Xantor Quentrix", stored
