"""Story 10.7, AC3: two processes open one pre-10.7 file at once.

Two ``spawn`` processes open the same pre-10.7 file, ordered with events as in
Story 10.5's cross-process tests (no sleep, no elapsed-time assert):

1. A opens the file and starts converting it. Inside its transaction, with the
   write lock held, A sets ``a_in_transaction`` and waits for ``b_waiting``.
2. B waits for ``a_in_transaction``, then opens the file. Its check before the
   transaction still sees the pre-10.7 file (A has not committed). Right before
   its own ``BEGIN IMMEDIATE`` (which waits for A's lock) B sets ``b_waiting``.
3. A commits. B gets the lock, checks the file again, finds it converted and
   changes nothing.

Each child reports ``("result", label, converted, outcome, message)``; anything
else is a harness error that the parent turns into a ``RuntimeError``.
Invented names only (AC11).
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.unit.pre_10_7_database import (
    LegacyRow,
    build_pre_10_7_database,
    read_entity_rows,
    read_schema_version,
    unique_index_columns,
)
from tests.unit.test_database_init_concurrency import _run_children

PASSPHRASE = "zorbalia_race_pass_123!"
CHILD_WAIT_TIMEOUT = 60  # hang guard for event waits in a child
NEW_VERSION = "1.1.0"

ROWS = (
    LegacyRow("LOCATION", "Zorbaville", "Quentrel"),
    LegacyRow("ORG", "Zorbtech", "Quentrix Holding"),
)


def _open_and_record(db_path: str, recorded: list[bool]) -> tuple[str, str]:
    """Open the file once; (outcome type or "ok", message)."""
    from gdpr_pseudonymizer.data import database

    real_ensure = database._ensure_current_schema

    def recording_ensure(path: str) -> bool:
        converted = real_ensure(path)
        recorded.append(converted)
        return converted

    try:
        with patch.object(
            database, "_ensure_current_schema", side_effect=recording_ensure
        ):
            with database.open_database(db_path, PASSPHRASE):
                pass
    except Exception as exc:
        return (type(exc).__name__, str(exc))
    return ("ok", "")


def _role_a(db_path: str, a_in_transaction: Any, b_waiting: Any, results: Any) -> None:
    """A: converts, and waits inside its transaction until B is about to lock."""
    hang_guard: list[str] = []
    try:
        from gdpr_pseudonymizer.data import database

        real_write = database._write_schema_version

        def write_then_wait(conn: Any, version: str) -> None:
            real_write(conn, version)
            a_in_transaction.set()
            if not b_waiting.wait(timeout=CHILD_WAIT_TIMEOUT):
                hang_guard.append("hang guard: B never reached its lock")
                raise RuntimeError(hang_guard[-1])

        recorded: list[bool] = []
        with patch.object(
            database, "_write_schema_version", side_effect=write_then_wait
        ):
            outcome = _open_and_record(db_path, recorded)
        if hang_guard:
            raise RuntimeError(hang_guard[-1])
        converted = recorded[0] if recorded else None
        report: tuple[Any, ...] = ("result", "A", converted, *outcome)
    except BaseException as exc:
        report = ("harness", "A", repr(exc))
    finally:
        a_in_transaction.set()
    results.put(report)


def _role_b(db_path: str, a_in_transaction: Any, b_waiting: Any, results: Any) -> None:
    """B: opens while A holds the lock, and must find the file converted."""
    try:
        try:
            from gdpr_pseudonymizer.data import database

            if not a_in_transaction.wait(timeout=CHILD_WAIT_TIMEOUT):
                raise RuntimeError("hang guard: A never started converting")
            real_begin = database._begin_immediate

            def signal_then_begin(conn: Any) -> None:
                b_waiting.set()
                real_begin(conn)

            recorded: list[bool] = []
            with patch.object(
                database, "_begin_immediate", side_effect=signal_then_begin
            ):
                outcome = _open_and_record(db_path, recorded)
            converted = recorded[0] if recorded else None
            report: tuple[Any, ...] = ("result", "B", converted, *outcome)
        except BaseException as exc:
            report = ("harness", "B", repr(exc))
    finally:
        b_waiting.set()
    results.put(report)


def test_two_processes_open_one_pre_10_7_file(tmp_path: Path) -> None:
    db_path = tmp_path / "pre_10_7.db"
    build_pre_10_7_database(db_path, PASSPHRASE, ROWS)
    rows_before = read_entity_rows(db_path)
    context = multiprocessing.get_context("spawn")
    a_in_transaction, b_waiting = context.Event(), context.Event()
    results = context.Queue()
    args = (str(db_path), a_in_transaction, b_waiting, results)
    processes = [
        context.Process(target=_role_a, args=args, name="opener-A"),
        context.Process(target=_role_b, args=args, name="opener-B"),
    ]

    reports = _run_children(processes, results, expected=2)

    outcomes = {report[1]: report[2:] for report in reports}
    assert outcomes["A"] == (True, "ok", ""), outcomes
    assert outcomes["B"] == (False, "ok", ""), outcomes
    assert read_schema_version(db_path) == NEW_VERSION
    assert unique_index_columns(db_path) == [["full_name", "entity_type"]]
    assert read_entity_rows(db_path) == rows_before
