"""Story 10.22: two documents saving at once write only the saved pseudonym.

Written by the BMAD dev agent (Claude). Each test drives the real
``DocumentProcessor`` paths on a real database: two documents, each in its own
thread (named ``A`` and ``B``) with its own ``DocumentProcessor``, so its own
connection. ``process_document(..., skip_validation=True)`` is what each
worker of the parallel ``gdpr-pseudo batch`` calls; ``finalize_document`` is
what the desktop app's reviews call. Detection is replaced by a stand-in that
finds the names given; the library's draw is fixed per thread.

Two saves held together (``held_pair``): document ``A`` reaches its save,
then, unless it already holds the database's write lock, waits there until
``B`` has run its whole document. On the unfixed code ``B`` saves first and
``A``'s save comes second. When ``A`` holds the lock at its save (the fix),
``B`` cannot save before it, so ``A`` goes on.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``. The first ``assert`` after them is the expected failure on the
unfixed code (``# expected failure``). Invented names and main-corpus words
only. No spaCy model, no Qt.
"""

from __future__ import annotations

import csv
import re
import secrets
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import gdpr_pseudonymizer.cli.commands.import_mappings as import_module
import gdpr_pseudonymizer.core.document_processor as processor_module
import gdpr_pseudonymizer.pseudonym.library_manager as library_module
import gdpr_pseudonymizer.validation.workflow as workflow_module
from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import DatabaseError
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _new_db,
    _replacements,
    pre,
)

ZQ = "Zorbal Quentrix"
ZM = "Zorbal Mestrix"
VM = "Vorlan Mestrix"
CUSTOM = "Xantor Vellion"
PERSON = "PERSON"

# How long A waits for B to enter its reload (settle=True), the bound that
# only stops a hang, and how long another connection holds the write lock:
# past SQLite's default 5 s wait
SETTLE = 3.0
WAIT = 120.0
HOLD = 6.0
SOURCE_PASSPHRASE = "zorbalia_source_pass_123!"

DOC_A = f"{ZQ} a signé le contrat."
DOC_B = f"Le contrat avec {ZQ}."

# Lionel's approved finalization refusals (10.11 Q-A), byte for byte
NAME_NOW_STORED = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "the name now has a pseudonym in the mapping database. Nothing was written."
)
NOW_ANOTHER_NAMES = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "it, or a part of it, is now used for another name. Nothing was written."
)


XFAIL_REVIEW_1 = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.22, Codex review 1: not fixed yet",
)


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No user or project settings file is read or written."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "gdpr_pseudonymizer.gui.config._config_path",
        lambda: tmp_path / ".gdpr-pseudo.yaml",
    )


# --- Detection and the library's draw ---------------------------------------


def _found(text: str, names: list[tuple[str, str]]) -> list[DetectedEntity]:
    """Every whole-word place of each (name, type); a place inside a longer
    one found is left out."""
    found = [
        DetectedEntity(
            text=name,
            entity_type=entity_type,
            start_pos=match.start(),
            end_pos=match.end(),
            confidence=0.9,
            source="spacy",
        )
        for name, entity_type in names
        for match in re.finditer(rf"(?<!\w){re.escape(name)}(?!\w)", text)
    ]
    kept = [
        entity
        for entity in found
        if not any(
            other.start_pos <= entity.start_pos
            and entity.end_pos <= other.end_pos
            and other.end_pos - other.start_pos > entity.end_pos - entity.start_pos
            for other in found
        )
    ]
    return sorted(kept, key=lambda entity: entity.start_pos)


def _spans(text: str, names: list[tuple[str, str]]) -> list[tuple[int, int]]:
    return [(entity.start_pos, entity.end_pos) for entity in _found(text, names)]


class _Detector:
    def __init__(self, names: list[tuple[str, str]]) -> None:
        self.names = names

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        return _found(text, self.names)


@contextmanager
def _detection(names: list[tuple[str, str]]) -> Iterator[None]:
    """Detection replaced: the text path and the spreadsheet path (one call
    per cell) both find the names given."""
    with patch.object(
        DocumentProcessor, "_get_detector", lambda self: _Detector(names)
    ):
        yield


class _Draws:
    """The library's ``secrets``: in thread A, ``choice`` returns ``seq[0]``,
    ``seq[1]``... in order; in thread B ``seq[-1]``, ``seq[-2]``... or, with
    ``same=True``, the same order as A. Any other thread draws as today."""

    def __init__(self, same: bool) -> None:
        self.same = same
        self.count = {"A": 0, "B": 0}

    def choice(self, seq: Any) -> Any:
        name = threading.current_thread().name
        if name not in self.count:
            return secrets.choice(seq)
        k = self.count[name]
        self.count[name] += 1
        if name == "B" and not self.same:
            return seq[-1 - (k % len(seq))]
        return seq[k % len(seq)]


@contextmanager
def _draws(same: bool = False) -> Iterator[None]:
    with patch.object(library_module, "secrets", _Draws(same)):
        yield


# --- Two saves held together ------------------------------------------------


def _write_lock_held(db: str) -> bool:
    """Whether another connection holds the database's write lock now."""
    probe = sqlite3.connect(db, timeout=0, isolation_level=None)
    try:
        probe.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as error:
        if "locked" in str(error):
            return True
        raise
    else:
        probe.execute("ROLLBACK")
        return False
    finally:
        probe.close()


def _db_of(repo: SQLiteMappingRepository) -> str:
    return str(repo._session.get_bind().url.database)


def held_pair(
    run_a: Callable[[], ProcessingResult],
    run_b: Callable[[], ProcessingResult],
    settle: bool = False,
) -> tuple[ProcessingResult, ProcessingResult]:
    """Run A in thread A and B in thread B, their saves held together.

    ``save_batch`` is wrapped. In thread A only, before the real save: when no
    other connection holds the write lock (the unfixed code), A waits until B
    has finished; when one does (A holds it), A goes on at once, and with
    ``settle=True`` first waits up to SETTLE seconds for B to enter
    ``_reset_pseudonym_state`` (wrapped too, a signal only). B starts only
    once A has reached its save.
    """
    real_save = SQLiteMappingRepository.save_batch
    real_reset = DocumentProcessor._reset_pseudonym_state
    a_at_save = threading.Event()
    b_reloading = threading.Event()
    b_done = threading.Event()
    results: dict[str, Any] = {}

    def reset(self: Any, ctx: Any) -> Any:
        if threading.current_thread().name == "B":
            b_reloading.set()
        return real_reset(self, ctx)

    def save(self: Any, entities: Any) -> Any:
        if threading.current_thread().name == "A" and not a_at_save.is_set():
            locked = _write_lock_held(_db_of(self))
            a_at_save.set()
            if not locked:
                pre(b_done.wait(WAIT), "B finished while A waited at its save")
            elif settle:
                b_reloading.wait(SETTLE)
        return real_save(self, entities)

    def thread_a() -> None:
        try:
            results["A"] = run_a()
        except BaseException as error:  # noqa: BLE001 - shown by the PRE below
            results["A"] = error

    def thread_b() -> None:
        try:
            results["B"] = run_b()
        except BaseException as error:  # noqa: BLE001 - shown by the PRE below
            results["B"] = error
        finally:
            b_done.set()

    with (
        patch.object(SQLiteMappingRepository, "save_batch", save),
        patch.object(DocumentProcessor, "_reset_pseudonym_state", reset),
    ):
        a = threading.Thread(target=thread_a, name="A")
        a.start()
        pre(a_at_save.wait(WAIT), "A reached its save")
        b = threading.Thread(target=thread_b, name="B")
        b.start()
        b.join(WAIT)
        a.join(WAIT)
        pre(not a.is_alive() and not b.is_alive(), "both documents finished")
    for key in ("A", "B"):
        pre(
            isinstance(results.get(key), ProcessingResult),
            f"{key} returned a ProcessingResult: {results.get(key)!r}",
        )
    return results["A"], results["B"]


# --- The documents ----------------------------------------------------------


def _process(
    db: str,
    folder: Path,
    tag: str,
    text: str,
    suffix: str = ".txt",
    theme: str = "neutral",
) -> Callable[[], ProcessingResult]:
    """``process_document(..., skip_validation=True)``: a parallel-batch
    worker. A ``.csv`` holds one header cell « nom » and one cell of text."""
    source = folder / f"{tag}{suffix}"
    if suffix == ".csv":
        source.write_text(f"nom\n{text}\n", encoding="utf-8")
    else:
        source.write_text(text, encoding="utf-8")
    output = folder / f"{tag}_out{suffix}"

    def run() -> ProcessingResult:
        processor = DocumentProcessor(db_path=db, passphrase=PASSPHRASE, theme=theme)
        return processor.process_document(
            str(source), str(output), skip_validation=True
        )

    return run


def _desktop(
    db: str,
    folder: Path,
    tag: str,
    text: str,
    names: list[tuple[str, str]],
    custom: dict[tuple[str, str], str] | None = None,
) -> Callable[[], ProcessingResult]:
    """``finalize_document``: the desktop app's single-document and batch
    reviews, with the custom pseudonyms set there."""
    output = folder / f"{tag}_out.txt"
    custom_pseudonyms = (
        {
            (mapping_key(name, etype), etype): value
            for (name, etype), value in custom.items()
        }
        if custom
        else None
    )

    def run() -> ProcessingResult:
        return DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
            text, _found(text, names), str(output), custom_pseudonyms=custom_pseudonyms
        )

    return run


def _output(folder: Path, tag: str, suffix: str = ".txt") -> str | None:
    """The output file's text (a ``.csv``: its one text cell), or None."""
    path = folder / f"{tag}_out{suffix}"
    if not path.exists():
        return None
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            cells = [row for row in csv.reader(handle) if row]
        pre(len(cells) == 2 and len(cells[1]) == 1, f"one text cell: {cells}")
        return cells[1][0]
    return path.read_text(encoding="utf-8")


def _written(
    folder: Path,
    tag: str,
    source: str,
    names: list[tuple[str, str]],
    suffix: str = ".txt",
) -> list[str]:
    """The string written at each place of ``names`` in the output."""
    output = _output(folder, tag, suffix)
    if output is None:
        pytest.fail(f"PRE: {tag}'s output file written")
    return _replacements(output, source, _spans(source, names))


def _saved(db: str) -> list[Entity]:
    """Every saved row (``find_all``), read on a new connection."""
    with open_database(db, PASSPHRASE) as session:
        return list(SQLiteMappingRepository(session).find_all())


def _rows_of(db: str, name: str) -> list[Entity]:
    return [row for row in _saved(db) if row.full_name == name]


# --- The expected failures --------------------------------------------------


@pytest.mark.parametrize("suffix", [".txt", ".csv"], ids=["txt", "csv"])
def test_two_workers_same_name_write_the_saved_pseudonym(
    tmp_path: Path, suffix: str
) -> None:
    """T1 (AC1, AC2): two workers meet one new name; each output carries the
    pseudonym of the one row saved."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON)]
    with _detection(names), _draws():
        a, b = held_pair(
            _process(db, tmp_path, "a", DOC_A, suffix),
            _process(db, tmp_path, "b", DOC_B, suffix),
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = _rows_of(db, ZQ)
    pre(len(saved) == 1, f"one saved row for {ZQ}: {len(saved)}")
    written_a = _written(tmp_path, "a", DOC_A, names, suffix)
    written_b = _written(tmp_path, "b", DOC_B, names, suffix)
    expected = [saved[0].pseudonym_full]
    assert (written_a, written_b) == (expected, expected)  # expected failure


@pytest.mark.parametrize(
    ("name", "entity_type"),
    [("Zorbaville", "LOCATION"), ("Zorbtech", "ORG")],
    ids=["LOCATION", "ORG"],
)
def test_two_workers_place_and_organisation(
    tmp_path: Path, name: str, entity_type: str
) -> None:
    """T2 (AC2): as T1, for a place and an organisation."""
    db = _new_db(tmp_path)
    names = [(name, entity_type)]
    doc_a, doc_b = f"{name} a signé le contrat.", f"Le contrat avec {name}."
    with _detection(names), _draws():
        a, b = held_pair(
            _process(db, tmp_path, "a", doc_a), _process(db, tmp_path, "b", doc_b)
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = _rows_of(db, name)
    pre(len(saved) == 1, f"one saved row for {name}: {len(saved)}")
    written_a = _written(tmp_path, "a", doc_a, names)
    written_b = _written(tmp_path, "b", doc_b, names)
    expected = [saved[0].pseudonym_full]
    assert (written_a, written_b) == (expected, expected)  # expected failure


def test_last_name_alone_takes_the_saved_last_name(tmp_path: Path) -> None:
    """T3 (AC2): a last name written alone takes the saved row's last-name
    part."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), ("Quentrix", PERSON)]
    doc_a = f"{ZQ} a signé le contrat. Signé : Quentrix."
    with _detection(names), _draws():
        a, b = held_pair(
            _process(db, tmp_path, "a", doc_a), _process(db, tmp_path, "b", DOC_B)
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = _rows_of(db, ZQ)
    pre(
        len(saved) == 1 and saved[0].last_name == "Quentrix",
        f"one saved row for {ZQ}, its last name Quentrix: {len(saved)}",
    )
    written_a = _written(tmp_path, "a", doc_a, names)
    expected = [saved[0].pseudonym_full, saved[0].pseudonym_last]
    assert written_a == expected  # expected failure


def test_one_first_name_one_first_name_pseudonym(tmp_path: Path) -> None:
    """T4 (AC2): two full names with one real first name are saved with one
    first-name part."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), (ZM, PERSON)]
    doc_a, doc_b = f"{ZQ} a signé le contrat.", f"{ZM} a signé le contrat."
    with _detection(names), _draws():
        a, b = held_pair(
            _process(db, tmp_path, "a", doc_a), _process(db, tmp_path, "b", doc_b)
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = {row.full_name: row for row in _saved(db)}
    pre(set(saved) == {ZQ, ZM}, f"two saved rows: {sorted(saved)}")
    pre(
        saved[ZQ].first_name == "Zorbal" and saved[ZM].first_name == "Zorbal",
        "first name Zorbal in both rows",
    )
    assert saved[ZQ].pseudonym_first == saved[ZM].pseudonym_first  # expected failure
    assert _written(tmp_path, "a", doc_a, names) == [saved[ZQ].pseudonym_full]
    assert _written(tmp_path, "b", doc_b, names) == [saved[ZM].pseudonym_full]


@pytest.mark.parametrize("theme", ["neutral_id", "neutral"])
def test_two_people_never_share_a_pseudonym(tmp_path: Path, theme: str) -> None:
    """T5 (AC5, Lionel's Q2): two different people saved at once never share a
    pseudonym. ``neutral_id``: the counters, no draw stand-in; the default
    theme: both workers draw the same values."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), (VM, PERSON)]
    doc_a, doc_b = f"{ZQ} a signé le contrat.", f"{VM} a signé le contrat."
    draw: AbstractContextManager[Any] = (
        _draws(same=True) if theme == "neutral" else nullcontext()
    )
    with draw, _detection(names):
        a, b = held_pair(
            _process(db, tmp_path, "a", doc_a, theme=theme),
            _process(db, tmp_path, "b", doc_b, theme=theme),
            settle=True,
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = {row.full_name: row for row in _saved(db)}
    pre(set(saved) == {ZQ, VM}, f"two saved rows: {sorted(saved)}")
    assert saved[ZQ].pseudonym_full != saved[VM].pseudonym_full  # expected failure
    if theme == "neutral":
        assert saved[ZQ].pseudonym_first != saved[VM].pseudonym_first
        assert saved[ZQ].pseudonym_last != saved[VM].pseudonym_last
    assert _written(tmp_path, "a", doc_a, names) == [saved[ZQ].pseudonym_full]
    assert _written(tmp_path, "b", doc_b, names) == [saved[VM].pseudonym_full]


def test_desktop_document_then_worker(tmp_path: Path) -> None:
    """T6 (AC2, Lionel's Q1): a desktop finalization, then a batch worker, on
    one database."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON)]
    with _detection(names), _draws():
        a, b = held_pair(
            _desktop(db, tmp_path, "a", DOC_A, names),
            _process(db, tmp_path, "b", DOC_B),
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = _rows_of(db, ZQ)
    pre(len(saved) == 1, f"one saved row for {ZQ}: {len(saved)}")
    written_a = _written(tmp_path, "a", DOC_A, names)
    written_b = _written(tmp_path, "b", DOC_B, names)
    expected = [saved[0].pseudonym_full]
    assert (written_a, written_b) == (expected, expected)  # expected failure


def test_custom_pseudonym_saved_first_is_written_by_the_worker(tmp_path: Path) -> None:
    """T7 (AC2, AC4, Lionel's Q1): the desktop saves a custom pseudonym; the
    worker that meets the name at the same moment writes it too."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON)]
    with _detection(names), _draws():
        a, b = held_pair(
            _desktop(db, tmp_path, "a", DOC_A, names, {(ZQ, PERSON): CUSTOM}),
            _process(db, tmp_path, "b", DOC_B),
        )
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = _rows_of(db, ZQ)
    pre(len(saved) == 1, f"one saved row for {ZQ}: {len(saved)}")
    written_a = _written(tmp_path, "a", DOC_A, names)
    expected = (CUSTOM, [CUSTOM])
    assert (saved[0].pseudonym_full, written_a) == expected  # expected failure
    assert _written(tmp_path, "b", DOC_B, names) == [CUSTOM]


def test_custom_pseudonym_after_a_worker_is_refused(tmp_path: Path) -> None:
    """T8 (AC4, Lionel's Q1): a worker saves the name first; the desktop's
    custom pseudonym for it is refused with 10.11's text, nothing written."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON)]
    with _detection(names), _draws():
        a, b = held_pair(
            _process(db, tmp_path, "a", DOC_A),
            _desktop(db, tmp_path, "b", DOC_B, names, {(ZQ, PERSON): CUSTOM}),
        )
    pre(a.success, f"A written: {a.error_message}")
    saved = _rows_of(db, ZQ)
    pre(len(saved) == 1, f"one saved row for {ZQ}: {len(saved)}")
    written_a = _written(tmp_path, "a", DOC_A, names)
    assert written_a == [saved[0].pseudonym_full]  # expected failure
    assert (b.success, b.error_message, _output(tmp_path, "b")) == (
        False,
        NAME_NOW_STORED,
        None,
    )


def test_two_names_one_custom_pseudonym(tmp_path: Path) -> None:
    """T9 (AC4, Lionel's Q1): two desktop finalizations give one custom
    pseudonym to two names; the second is refused with 10.11's text."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), (VM, PERSON)]
    doc_a, doc_b = f"{ZQ} a signé le contrat.", f"{VM} a signé le contrat."
    with _detection(names), _draws():
        a, b = held_pair(
            _desktop(db, tmp_path, "a", doc_a, names, {(ZQ, PERSON): CUSTOM}),
            _desktop(db, tmp_path, "b", doc_b, names, {(VM, PERSON): CUSTOM}),
        )
    pre(a.success, f"A written: {a.error_message}")
    holders = sorted(
        row.full_name for row in _saved(db) if row.pseudonym_full == CUSTOM
    )
    assert holders == [ZQ]  # expected failure
    assert (b.success, b.error_message, _output(tmp_path, "b")) == (
        False,
        NOW_ANOTHER_NAMES,
        None,
    )


# --- Codex review 1: the command line's other writers -----------------------


def _db_with(path: Path, passphrase: str, *rows: tuple[str, str, str]) -> str:
    """A new database holding the (type, name, pseudonym) rows given."""
    init_database(str(path), passphrase)
    with open_database(str(path), passphrase) as session:
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
    return str(path)


class _Recorder:
    """A logger that records every call: (level, event, keywords)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __getattr__(self, level: str) -> Callable[..., None]:
        def record(event: str, *args: Any, **kwargs: Any) -> None:
            self.calls.append((level, event, kwargs))

        return record


class _LockHolder:
    """Another connection that takes the database's write lock, then holds it
    HOLD seconds from the moment the command attempts its write (``attempt``,
    set just before that write), or until released. Neither the hold nor
    the write depends on the threads' start-up time."""

    def __init__(self, db: str) -> None:
        self.db = db
        self.acquired = threading.Event()
        self.attempt = threading.Event()
        self.release = threading.Event()
        self.thread = threading.Thread(target=self._hold, name="holder")

    def _hold(self) -> None:
        connection = sqlite3.connect(self.db, timeout=WAIT, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            self.acquired.set()
            if self.attempt.wait(WAIT):
                self.release.wait(HOLD)
            connection.execute("COMMIT")
        finally:
            connection.close()

    def start(self, what: str) -> None:
        """Start the holder; return once it holds the write lock."""
        self.thread.start()
        pre(self.acquired.wait(WAIT), f"another connection took the lock {what}")

    def attempting(self) -> None:
        """Called just before the command's write: the hold starts now."""
        pre(self.acquired.is_set(), "the lock is held before the write")
        self.attempt.set()

    def stop(self) -> None:
        self.release.set()
        if self.thread.is_alive():
            self.thread.join(WAIT)


def _import(source: str, target: str) -> Any:
    return CliRunner().invoke(
        app,
        [
            "import-mappings",
            source,
            "--db",
            target,
            "--passphrase",
            PASSPHRASE,
            "--source-passphrase",
            SOURCE_PASSPHRASE,
        ],
    )


@XFAIL_REVIEW_1
def test_import_error_logs_no_name(tmp_path: Path) -> None:
    """T10 (P0, AC4): a row that `import-mappings` fails to save is logged
    by its type, never by its name."""
    source = _db_with(tmp_path / "source.db", SOURCE_PASSPHRASE, (PERSON, ZQ, CUSTOM))
    target = _db_with(tmp_path / "target.db", PASSPHRASE)
    recorder = _Recorder()

    def failing_save(self: Any, entity: Any) -> Any:
        raise DatabaseError("Database operation failed: database is locked")

    with (
        patch.object(import_module, "logger", recorder),
        patch.object(SQLiteMappingRepository, "save", failing_save),
    ):
        result = _import(source, target)
    errors = [call for call in recorder.calls if call[1] == "import_entity_error"]
    pre(
        len(errors) == 1,
        f"one import_entity_error recorded: {recorder.calls} {result.output}",
    )
    recorded = repr(recorder.calls)
    assert "Zorbal" not in recorded and "Quentrix" not in recorded  # expected failure
    assert errors[0][2].get("entity_type") == PERSON


@XFAIL_REVIEW_1
def test_deletion_behind_a_held_lock_keeps_its_record(tmp_path: Path) -> None:
    """T11 (P1, AC3): after `delete-mapping` has deleted the row, another
    connection takes the write lock and holds it 6 s from the moment the
    ERASURE record's write begins; the record waits for it and is written."""
    db = _db_with(tmp_path / "mappings.db", PASSPHRASE, (PERSON, ZQ, CUSTOM))
    real_delete = SQLiteMappingRepository.delete_entities_by_full_name_any_capitals
    real_log = AuditRepository.log_operation
    holder = _LockHolder(db)

    def delete_then_lock(self: Any, name: str) -> Any:
        deleted = real_delete(self, name)
        holder.start("after the deletion")
        return deleted

    def log_when_held(self: Any, operation: Any) -> Any:
        if not holder.attempt.is_set():
            holder.attempting()
        return real_log(self, operation)

    try:
        with (
            patch.object(
                SQLiteMappingRepository,
                "delete_entities_by_full_name_any_capitals",
                delete_then_lock,
            ),
            patch.object(AuditRepository, "log_operation", log_when_held),
        ):
            result = CliRunner().invoke(
                app,
                [
                    "delete-mapping",
                    ZQ,
                    "--db",
                    db,
                    "--passphrase",
                    PASSPHRASE,
                    "--force",
                    "--reason",
                    "REQ-1",
                ],
            )
    finally:
        holder.stop()
    pre(holder.attempt.is_set(), f"the ERASURE record was attempted: {result.output}")
    left = _saved(db)
    pre(left == [], f"the row is deleted: {[row.full_name for row in left]}")
    connection = sqlite3.connect(db)
    try:
        erasures = connection.execute(
            "SELECT id FROM operations WHERE operation_type = 'ERASURE'"
        ).fetchall()
    finally:
        connection.close()
    assert len(erasures) == 1, (result.exit_code, result.output)  # expected failure
    assert result.exit_code == 0


@XFAIL_REVIEW_1
def test_import_behind_a_held_lock_completes(tmp_path: Path) -> None:
    """T12 (P1, QA's LOCK-1022-01; AC3): before `import-mappings` saves its
    first row, another connection takes the target's write lock and holds it
    6 s from the moment that save begins; the import waits and saves the
    row."""
    source = _db_with(tmp_path / "source.db", SOURCE_PASSPHRASE, (PERSON, ZQ, CUSTOM))
    target = _db_with(tmp_path / "target.db", PASSPHRASE)
    real_save = SQLiteMappingRepository.save
    holder = _LockHolder(target)

    def lock_then_save(self: Any, entity: Any) -> Any:
        if not holder.acquired.is_set():
            holder.start("before the first save")
            holder.attempting()
        return real_save(self, entity)

    try:
        with patch.object(SQLiteMappingRepository, "save", lock_then_save):
            result = _import(source, target)
    finally:
        holder.stop()
    pre(holder.attempt.is_set(), f"the first save was attempted: {result.output}")
    names = [row.full_name for row in _saved(target)]
    assert names == [ZQ], (result.exit_code, result.output)  # expected failure
    assert result.exit_code == 0


# --- The guards -------------------------------------------------------------


def test_one_after_the_other_unchanged(tmp_path: Path) -> None:
    """G1 (AC4): documents run one after the other, as on 0be4073."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON), ("Quentrix", PERSON)]
    doc_a = f"{ZQ} a signé le contrat. Signé : Quentrix."
    with _detection(names):
        a = _process(db, tmp_path, "a", doc_a)()
        b = _process(db, tmp_path, "b", DOC_B)()
    pre(a.success and b.success, f"both written: {a.error_message} {b.error_message}")
    saved = _rows_of(db, ZQ)
    assert len(saved) == 1
    assert _written(tmp_path, "a", doc_a, names) == [
        saved[0].pseudonym_full,
        saved[0].pseudonym_last,
    ]
    assert _written(tmp_path, "b", DOC_B, names) == [saved[0].pseudonym_full]


def test_a_document_waits_longer_than_five_seconds(tmp_path: Path) -> None:
    """G2 (AC3): A's save waits until B asks for the lock, then is held 6 s,
    past SQLite's default 5 s wait; B is written too."""
    db = _new_db(tmp_path)
    names = [(ZQ, PERSON)]
    real_save = SQLiteMappingRepository.save_batch
    real_lock = processor_module.pseudonym_lock
    a_at_save = threading.Event()
    b_asks = threading.Event()
    results: dict[str, Any] = {}

    def lock(db_session: Any) -> Any:
        if threading.current_thread().name == "B":
            b_asks.set()
        return real_lock(db_session)

    def slow_save(self: Any, entities: Any) -> Any:
        if threading.current_thread().name == "A" and not a_at_save.is_set():
            a_at_save.set()
            pre(b_asks.wait(WAIT), "B asked for the lock")
            threading.Event().wait(HOLD)
        return real_save(self, entities)

    def runner(key: str, run: Callable[[], ProcessingResult]) -> Callable[[], None]:
        def target() -> None:
            try:
                results[key] = run()
            except BaseException as error:  # noqa: BLE001 - shown by the PRE
                results[key] = error

        return target

    with (
        _detection(names),
        patch.object(SQLiteMappingRepository, "save_batch", slow_save),
        patch.object(processor_module, "pseudonym_lock", lock),
    ):
        a = threading.Thread(
            target=runner("A", _process(db, tmp_path, "a", DOC_A)), name="A"
        )
        a.start()
        pre(a_at_save.wait(WAIT), "A reached its save")
        b = threading.Thread(
            target=runner("B", _process(db, tmp_path, "b", DOC_B)), name="B"
        )
        b.start()
        b.join(WAIT)
        a.join(WAIT)
    for key in ("A", "B"):
        pre(
            isinstance(results.get(key), ProcessingResult),
            f"{key} returned a ProcessingResult: {results.get(key)!r}",
        )
    assert (results["A"].success, results["B"].success) == (True, True), (
        results["A"].error_message,
        results["B"].error_message,
    )


def test_the_command_line_review_holds_no_lock(tmp_path: Path) -> None:
    """G3 (AC3): while the command line's review waits for a key, another
    document on the same database is saved and written."""
    db = _new_db(tmp_path)
    source = tmp_path / "a.txt"
    source.write_text(DOC_A, encoding="utf-8")
    doc_b = f"{VM} a signé."
    other: dict[str, Any] = {}

    def first_key(*args: Any, **kwargs: Any) -> str:
        if "B" not in other:
            run_b = _desktop(db, tmp_path, "b", doc_b, [(VM, PERSON)])
            thread = threading.Thread(
                target=lambda: other.__setitem__("B", run_b()), name="B"
            )
            thread.start()
            thread.join(30)
            other.setdefault("B", None)
        return "confirm"

    with (
        _detection([(ZQ, PERSON), (VM, PERSON)]),
        patch("gdpr_pseudonymizer.validation.ui.readchar.readkey", return_value="\r"),
        patch.object(workflow_module, "get_user_action", side_effect=first_key),
        patch.object(workflow_module, "get_confirmation", return_value=True),
    ):
        result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).process_document(
            str(source), str(tmp_path / "a_out.txt")
        )
    pre(result.success, f"A written: {result.error_message}")
    pre("B" in other, "the review asked for a key")
    returned = other["B"]
    assert returned is not None and returned.success
    assert _output(tmp_path, "b") is not None
