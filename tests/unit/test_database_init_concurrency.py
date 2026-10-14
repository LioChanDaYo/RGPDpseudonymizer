"""Cross-process tests for init_database (Story 10.5, AC3).

Two ``spawn`` processes initialize the same new database. T9 orders them with
three events, so the interleaving is deterministic; T10 starts them together
behind a ``Barrier(2)``, 20 times, each time in its own temporary directory.

Each child wraps only its ``init_database`` call and reports
``("result", ...)``. Everything around it (imports, hooks, barrier and event
waits) reports ``("harness", ...)``, and the parent turns any harness report,
a missing report or a child that did not exit into a ``RuntimeError`` before it
asserts anything. Timeouts are hang guards only: there is no sleep and no
elapsed-time assert.

The worker functions live at module level so that a ``spawn`` child can import
them.
"""

from __future__ import annotations

import multiprocessing
import queue
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.unit.test_database import PASS_A, PASS_B, _assert_winner_db

RACE_ITERATIONS = 20
CHILD_WAIT_TIMEOUT = 60  # hang guard for barrier and event waits in a child
QUEUE_TIMEOUT = 120  # hang guard for each report the parent waits for
JOIN_TIMEOUT = 60  # hang guard for a child to exit after its last report
ALREADY_EXISTS = "Database already exists"
PASSPHRASES = {"A": PASS_A, "B": PASS_B}


def _call_init(
    init_database: Callable[[str, str], None], db_path: str, passphrase: str
) -> BaseException | None:
    """Run init_database and return what it raised (None on success)."""
    try:
        init_database(db_path, passphrase)
    except BaseException as exc:
        return exc
    return None


def _describe(outcome: BaseException | None) -> tuple[str, str, str]:
    """(type name or "ok", message, cause type name) of an outcome."""
    if outcome is None:
        return ("ok", "", "")
    cause = outcome.__cause__
    cause_name = type(cause).__name__ if cause is not None else ""
    return (type(outcome).__name__, str(outcome), cause_name)


def _forced_role_a(
    db_path: str, b_checked: Any, a_created: Any, b_done: Any, results: Any
) -> None:
    """A: waits until B is past the fast path, then initializes.

    A's schema step runs for real, then A sets ``a_created`` (its file exists)
    and waits until B is done before it goes on.
    """
    hang_guard: list[str] = []
    try:
        from gdpr_pseudonymizer.data.database import init_database
        from gdpr_pseudonymizer.data.models import Base

        real_create_all = Base.metadata.create_all

        def create_all_then_wait(*args: Any, **kwargs: Any) -> None:
            real_create_all(*args, **kwargs)
            a_created.set()
            if not b_done.wait(timeout=CHILD_WAIT_TIMEOUT):
                hang_guard.append("hang guard: B never finished")
                raise RuntimeError(hang_guard[-1])

        if not b_checked.wait(timeout=CHILD_WAIT_TIMEOUT):
            raise RuntimeError("hang guard: B never passed the fast path")
        with patch.object(
            Base.metadata, "create_all", side_effect=create_all_then_wait
        ):
            outcome = _call_init(init_database, db_path, PASS_A)
        if hang_guard:
            raise RuntimeError(hang_guard[-1])
        report: tuple[str, ...] = ("result", "A", *_describe(outcome))
    except BaseException as exc:
        report = ("harness", "A", repr(exc))
    results.put(report)


def _forced_role_b(
    db_path: str, b_checked: Any, a_created: Any, b_done: Any, results: Any
) -> None:
    """B: passes the fast path, then waits until A's file exists before going on."""
    hang_guard: list[str] = []
    try:
        try:
            from gdpr_pseudonymizer.data.database import init_database
            from gdpr_pseudonymizer.data.encryption import EncryptionService

            real_generate_salt = EncryptionService.generate_salt

            def checked_then_wait() -> bytes:
                # generate_salt runs right after init_database's existence check.
                b_checked.set()
                if not a_created.wait(timeout=CHILD_WAIT_TIMEOUT):
                    hang_guard.append("hang guard: A never created its file")
                    raise RuntimeError(hang_guard[-1])
                return real_generate_salt()

            with patch.object(
                EncryptionService, "generate_salt", side_effect=checked_then_wait
            ):
                outcome = _call_init(init_database, db_path, PASS_B)
            if hang_guard:
                raise RuntimeError(hang_guard[-1])
            report: tuple[str, ...] = ("result", "B", *_describe(outcome))
        except BaseException as exc:
            report = ("harness", "B", repr(exc))
    finally:
        b_done.set()
    results.put(report)


def _race_worker(
    label: str, passphrase: str, paths: Sequence[str], barrier: Any, results: Any
) -> None:
    """One long-lived racer: for each path, wait at the barrier, then initialize."""
    try:
        from gdpr_pseudonymizer.data.database import init_database
    except BaseException as exc:
        results.put(("harness", label, repr(exc)))
        return
    for index, db_path in enumerate(paths):
        try:
            barrier.wait(timeout=CHILD_WAIT_TIMEOUT)
        except BaseException as exc:
            results.put(("harness", label, f"iteration {index}: {exc!r}"))
            return
        outcome = _call_init(init_database, db_path, passphrase)
        results.put(("result", label, index, *_describe(outcome)))


def _run_children(
    processes: Sequence[Any], results: Any, expected: int
) -> list[tuple[Any, ...]]:
    """Start the children, collect ``expected`` reports, and reap the children.

    Raises RuntimeError (never AssertionError) on a harness report, a missing
    report or a child that did not exit cleanly.
    """
    started: list[Any] = []
    reports: list[tuple[Any, ...]] = []
    try:
        for process in processes:
            process.start()
            started.append(process)
        while len(reports) < expected:
            try:
                report = results.get(timeout=QUEUE_TIMEOUT)
            except queue.Empty:
                raise RuntimeError(
                    f"hang guard: {len(reports)} of {expected} reports arrived"
                ) from None
            if report[0] != "result":
                raise RuntimeError(f"harness error in a child: {report!r}")
            reports.append(report)
        for process in started:
            process.join(timeout=JOIN_TIMEOUT)
            if process.exitcode is None:
                raise RuntimeError(f"hang guard: {process.name} did not exit")
            if process.exitcode != 0:
                raise RuntimeError(
                    f"{process.name} exited with code {process.exitcode}"
                )
    finally:
        for process in started:
            if process.is_alive():
                process.terminate()
            process.join()
            process.close()
        results.close()
        results.join_thread()
    return reports


def test_concurrent_init_forced_interleaving(tmp_path: Path) -> None:
    """T9: B passes the fast path before A creates the file; A must win."""
    db_path = tmp_path / "mappings.db"
    context = multiprocessing.get_context("spawn")
    b_checked, a_created, b_done = context.Event(), context.Event(), context.Event()
    results = context.Queue()
    args = (str(db_path), b_checked, a_created, b_done, results)
    processes = [
        context.Process(target=_forced_role_a, args=args, name="role-A"),
        context.Process(target=_forced_role_b, args=args, name="role-B"),
    ]

    reports = _run_children(processes, results, expected=2)

    outcomes = {report[1]: report[2:] for report in reports}
    assert outcomes["A"] == ("ok", "", ""), outcomes
    kind, message, cause = outcomes["B"]
    assert kind == "ValueError", outcomes
    assert message.startswith(ALREADY_EXISTS), outcomes
    assert cause == "FileExistsError", outcomes
    _assert_winner_db(db_path, PASS_A, PASS_B)


def _race_iteration_problem(
    db_path: Path, outcomes: dict[str, tuple[str, str, str]]
) -> str | None:
    """None if the iteration meets AC3, else what went wrong."""
    if sorted(outcomes) != ["A", "B"]:
        return f"outcomes {outcomes}"
    winners = [label for label, outcome in outcomes.items() if outcome[0] == "ok"]
    if len(winners) != 1:
        return f"{len(winners)} successes: {outcomes}"
    winner = winners[0]
    loser = "B" if winner == "A" else "A"
    kind, message, _cause = outcomes[loser]
    if kind != "ValueError" or not message.startswith(ALREADY_EXISTS):
        return f"loser {loser} raised {kind}: {message[:160]}"
    try:
        _assert_winner_db(db_path, PASSPHRASES[winner], PASSPHRASES[loser])
    except AssertionError as exc:
        return f"winner {winner}'s database: {exc}"
    return None


def test_concurrent_init_race_loop(tmp_path: Path) -> None:
    """T10 (AC3): 20 barrier-started races, each with exactly one winner."""
    paths = []
    for index in range(RACE_ITERATIONS):
        iteration_dir = tmp_path / f"iteration_{index:02d}"
        iteration_dir.mkdir()
        paths.append(str(iteration_dir / "mappings.db"))
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=_race_worker,
            args=(label, PASSPHRASES[label], paths, barrier, results),
            name=f"racer-{label}",
        )
        for label in ("A", "B")
    ]

    reports = _run_children(processes, results, expected=2 * RACE_ITERATIONS)

    by_iteration: dict[int, dict[str, tuple[str, str, str]]] = {}
    for _kind, label, index, outcome_kind, message, cause in reports:
        by_iteration.setdefault(index, {})[label] = (outcome_kind, message, cause)
    failures = []
    for index, db_path in enumerate(paths):
        problem = _race_iteration_problem(Path(db_path), by_iteration.get(index, {}))
        if problem is not None:
            failures.append(f"iteration {index:02d}: {problem}")
    assert (
        not failures
    ), f"{len(failures)} of {RACE_ITERATIONS} iterations failed AC3:\n" + "\n".join(
        failures
    )
