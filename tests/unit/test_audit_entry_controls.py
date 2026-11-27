"""Story 17.1: the audit rows of the command line, pinned before the desktop
app writes its own (controls K1, K2, K6a, K6b, K7, K8), and the no-Qt parts
of the desktop harness (``tests/unit/gui/test_desktop_audit_entry.py``).

Written by the BMAD dev agent (Claude), tests first. Every test here is a
control: it passes on the unfixed code and must keep passing after the fix
(the command line's rows do not change).

Detection is ``_StandIn``, installed in place of ``HybridDetector`` (the real
``_get_detector`` stays and caches one stand-in per processor). Its model
reports « not loaded » until that same detector has detected, as spaCy does,
then ``fr_core_news_zz-9.9.9``; so a processor that never detected reads
``fr_not_loaded-unknown``, as the real one does. Files are read by the real
``read_file`` (PDF and DOCX written with ``fpdf`` and ``python-docx``).

The command line's review is ``DocumentProcessor.process_document`` with its
interactive review, every group confirmed (Story 15.1's patches). Invented
names and main-corpus words only. No spaCy model, no Qt.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import gdpr_pseudonymizer
import gdpr_pseudonymizer.core.document_processor as processor_module
from gdpr_pseudonymizer.cli.commands.batch import _process_single_document_worker
from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.workflow import ADD_MISSED_NAME_QUESTION
from tests.unit.test_custom_pseudonym_fixes_cli import PASSPHRASE, pre
from tests.unit.test_parallel_saved_pseudonym import (
    _settings,  # noqa: F401 - autouse fixture: no settings file read or written
)
from tests.unit.test_review_rows_written import (
    LOCATION,
    ORG,
    ORG_NAME,
    PERSON,
    PLACE,
    ZQ,
)

ROOT = Path(__file__).resolve().parents[2]

# Story 15.1's invented names, in Story 15.1's words (S1 to S4)
DOC = f"{ZQ} travaille à {PLACE}. {ORG_NAME} a signé le contrat de {ZQ}."
NAMES = [(ZQ, PERSON), (PLACE, LOCATION), (ORG_NAME, ORG)]
# An invented token and invented names: the sanitizer redacts both
FAIL_MSG = f"E171 'Zorbal' {ZQ}"
REDACTED = "E171 '[REDACTED]' [REDACTED]"
INVENTED = ["Zorbal", "Quentrix", PLACE, ORG_NAME]

NOT_LOADED = "fr_not_loaded-unknown"
STAND_IN_VERSION = "fr_core_news_zz-9.9.9"
FORMATS = [".txt", ".md", ".pdf", ".docx"]
FORMAT_IDS = ["txt", "md", "pdf", "docx"]

# The 12 fields of an operation, in the export's order (audit_repository.py)
KEYS = [
    "id",
    "timestamp",
    "operation_type",
    "files_processed",
    "model_name",
    "model_version",
    "theme_selected",
    "user_modifications",
    "entity_count",
    "processing_time_seconds",
    "success",
    "error_message",
]
NOT_COMPARED = ("id", "timestamp", "processing_time_seconds", "files_processed")


# --- The package under test --------------------------------------------------


def pre_package(root: Path, modules: list[str]) -> None:
    """PRE: the package and the test helper modules come from ``root``, the
    test file's own checkout (Task 0.2)."""
    files = {"gdpr_pseudonymizer": gdpr_pseudonymizer.__file__}
    for name in modules:
        module = sys.modules.get(name)
        pre(module is not None, f"{name} imported")
        files[name] = getattr(module, "__file__", None)
    for name, file in files.items():
        pre(
            file is not None and Path(file).resolve().is_relative_to(root),
            f"{name} from {file}, not under {root}",
        )


@pytest.fixture(autouse=True)
def _package() -> None:
    pre_package(
        ROOT,
        [
            "tests.unit.test_review_rows_written",
            "tests.unit.test_custom_pseudonym_fixes_cli",
            "tests.unit.test_parallel_saved_pseudonym",
        ],
    )


# --- The stand-in detector ---------------------------------------------------


class _LazyModel:
    """The model's info as spaCy's: « not loaded » until it has detected."""

    def __init__(self) -> None:
        self.loaded = False

    def get_model_info(self) -> dict[str, str]:
        if not self.loaded:
            return {
                "name": "not_loaded",
                "version": "unknown",
                "library": "spacy",
                "language": "fr",
            }
        return {
            "name": "core_news_zz",
            "version": "9.9.9",
            "library": "spacy",
            "language": "fr",
        }


class _StandIn:
    """Replaces ``HybridDetector``: every place of each invented name."""

    fail = False
    delay = 0.0

    def __init__(self, default_model: str | None = None) -> None:
        self.spacy_detector = _LazyModel()

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        if _StandIn.delay:
            time.sleep(_StandIn.delay)
        if _StandIn.fail:
            raise RuntimeError(FAIL_MSG)
        self.spacy_detector.loaded = True
        found = [
            DetectedEntity(
                text=name,
                entity_type=entity_type,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.9,
                source="spacy",
            )
            for name, entity_type in NAMES
            for match in re.finditer(re.escape(name), text)
        ]
        return sorted(found, key=lambda entity: entity.start_pos)


def install_stand_in(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_StandIn]]:
    """``_StandIn`` in place of ``HybridDetector``, its switches reset before
    and after the test."""
    _StandIn.fail = False
    _StandIn.delay = 0.0
    monkeypatch.setattr(processor_module, "HybridDetector", _StandIn)
    try:
        yield _StandIn
    finally:
        _StandIn.fail = False
        _StandIn.delay = 0.0


@pytest.fixture
def stand_in(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_StandIn]]:
    yield from install_stand_in(monkeypatch)


# --- Files, databases, rows ---------------------------------------------------


def write_doc(path: Path, text: str = DOC) -> Path:
    """``text`` as ``path``'s format (.txt, .md, .pdf, .docx)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".pdf":
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text)
        pdf.output(str(path))
    elif path.suffix == ".docx":
        from docx import Document

        document = Document()
        document.add_paragraph(text)
        document.save(str(path))
    else:
        path.write_text(text, encoding="utf-8")
    return path


def fresh_db(path: Path, passphrase: str = PASSPHRASE) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    init_database(str(path), passphrase)
    return str(path)


def rows_of(db: str, passphrase: str = PASSPHRASE) -> list[dict[str, Any]]:
    """Every operation of ``db`` as a dict of its 12 fields, oldest first."""
    with open_database(db, passphrase) as session:
        operations = AuditRepository(session.session).find_operations()
        found = [{key: getattr(op, key) for key in KEYS} for op in operations]
    return sorted(found, key=lambda row: row["timestamp"])


def compared(row: dict[str, Any]) -> dict[str, Any]:
    """The fields a desktop row must share with the CLI's (AC3)."""
    return {key: value for key, value in row.items() if key not in NOT_COMPARED}


def failing_write() -> Any:
    """``write_file`` refuses the write, with the invented names in its error."""
    return patch.object(processor_module, "write_file", side_effect=OSError(FAIL_MSG))


@contextmanager
def cli_review(
    confirmation: Callable[..., bool] = lambda *a, **k: True,
) -> Iterator[None]:
    """Story 15.1's command-line review: every group confirmed, nothing
    waits on a key."""
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "gdpr_pseudonymizer.validation.ui.readchar.readkey", return_value="\r"
            )
        )
        stack.enter_context(
            patch(
                "gdpr_pseudonymizer.validation.workflow.get_user_action",
                return_value="confirm",
            )
        )
        stack.enter_context(
            patch(
                "gdpr_pseudonymizer.validation.workflow.get_confirmation",
                side_effect=confirmation,
            )
        )
        yield


def cli_rows(db: str, path: Path) -> list[dict[str, Any]]:
    """The rows of one CLI ``process`` with its review on ``db`` (a fresh
    database), every group confirmed."""
    output = Path(db).with_name("out.txt")
    with cli_review():
        DocumentProcessor(
            db_path=db, passphrase=PASSPHRASE, theme="neutral"
        ).process_document(str(path), str(output))
    return rows_of(db)


def k1_row(path: Path) -> dict[str, Any]:
    """K1's row for ``path``, without id, timestamp and time."""
    return {
        "operation_type": "PROCESS",
        "files_processed": [str(path)],
        "model_name": "spacy",
        "model_version": STAND_IN_VERSION,
        "theme_selected": "neutral",
        "user_modifications": None,
        "entity_count": 4,
        "success": True,
        "error_message": None,
    }


def _timeless(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in ("id", "timestamp", "processing_time_seconds")
    }


# --- K1, K2: the CLI's rows ---------------------------------------------------


def test_k1_cli_process_writes_one_row(  # type: ignore[no-untyped-def]
    tmp_path, stand_in
) -> None:
    path = write_doc(tmp_path / "doc.txt")
    rows = cli_rows(fresh_db(tmp_path / "mappings.db"), path)
    assert [_timeless(row) for row in rows] == [k1_row(path)]


@pytest.mark.parametrize("failure", ["write", "read", "detection"])
def test_k2_cli_failure_rows(  # type: ignore[no-untyped-def]
    tmp_path, stand_in, failure: str
) -> None:
    db = fresh_db(tmp_path / "mappings.db")
    if failure == "write":
        path = write_doc(tmp_path / "doc.txt")
        with failing_write():
            rows = cli_rows(db, path)
        version, error = STAND_IN_VERSION, f"OSError: {REDACTED}"
    elif failure == "read":
        path = tmp_path / "doc9.txt"
        pre(not path.exists(), "doc9.txt missing")
        rows = cli_rows(db, path)
        version, error = NOT_LOADED, f"FileProcessingError: File not found: {path}"
    else:
        path = write_doc(tmp_path / "doc.txt")
        stand_in.fail = True
        rows = cli_rows(db, path)
        version, error = NOT_LOADED, f"RuntimeError: {REDACTED}"
    assert [_timeless(row) for row in rows] == [
        {
            **k1_row(path),
            "model_version": version,
            "entity_count": 0,
            "success": False,
            "error_message": error,
        }
    ]


# --- K6a, K6b: the CLI batch, sequential and parallel -------------------------


def test_k6a_cli_batch_sequential_one_row_per_file(  # type: ignore[no-untyped-def]
    tmp_path, stand_in
) -> None:
    folder = tmp_path / "in"
    paths = [write_doc(folder / f"doc{index}.txt") for index in range(2)]
    db = tmp_path / "mappings.db"
    # doc1 holds no new name on this database, so the CLI asks whether to add
    # a name the detector missed: answered no (PO, measured)
    with cli_review(lambda question, *a, **k: question != ADD_MISSED_NAME_QUESTION):
        result = CliRunner().invoke(
            app,
            [
                "batch",
                str(folder),
                "--db",
                str(db),
                "--output",
                str(tmp_path / "out"),
                "--workers",
                "1",
            ],
            env={"GDPR_PSEUDO_PASSPHRASE": PASSPHRASE},
            catch_exceptions=False,
        )
    pre(result.exit_code == 0, f"batch exit code {result.exit_code}")
    rows = rows_of(str(db))
    assert [_timeless(row) for row in rows] == [k1_row(path) for path in paths]


def test_k6b_cli_batch_parallel_worker_one_row_per_file(  # type: ignore[no-untyped-def]
    tmp_path, stand_in
) -> None:
    paths = [write_doc(tmp_path / "in" / f"doc{index}.txt") for index in range(2)]
    db = fresh_db(tmp_path / "mappings.db")
    (tmp_path / "out").mkdir()
    for path in paths:
        outcome = _process_single_document_worker(
            (
                str(path),
                str(tmp_path / "out" / path.name),
                db,
                PASSPHRASE,
                "neutral",
                "spacy",
                None,
            )
        )
        pre(outcome["success"], f"{path.name} written: {outcome}")
    assert [_timeless(row) for row in rows_of(db)] == [k1_row(path) for path in paths]


# --- K7: the harness's model version ------------------------------------------


def test_k7_stand_in_reports_the_version_after_detection(  # type: ignore[no-untyped-def]
    stand_in,
) -> None:
    processor = DocumentProcessor(db_path="", passphrase=PASSPHRASE)
    assert processor._get_model_version() == NOT_LOADED
    processor._detect_and_filter_entities(DOC)
    assert processor._get_model_version() == STAND_IN_VERSION


# --- K8: the export's keys ----------------------------------------------------


def test_k8_export_keys_unchanged(tmp_path, stand_in) -> None:  # type: ignore[no-untyped-def]
    path = write_doc(tmp_path / "doc.txt")
    db = fresh_db(tmp_path / "mappings.db")
    pre(len(cli_rows(db, path)) == 1, "K1's row")
    json_path, csv_path = tmp_path / "audit.json", tmp_path / "audit.csv"
    with open_database(db, PASSPHRASE) as session:
        repository = AuditRepository(session.session)
        repository.export_to_json(str(json_path))
        repository.export_to_csv(str(csv_path))
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    assert exported["export_metadata"]["schema_version"] == "1.0.0"
    assert [list(op) for op in exported["operations"]] == [KEYS]
    with csv_path.open(encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == KEYS
