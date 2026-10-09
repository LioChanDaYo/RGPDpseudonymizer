"""Paired bootstrap delta and CI95 recompute from accuracy-per-document.json.

Story 10.6 PR A (AC3; AC10 G2). A thin wrapper over
``tests/accuracy/bootstrap.py``. It reads only the files it is given: the
main-corpus ``accuracy-per-document.json`` (and ``accuracy-output.txt``) of a
CI ``accuracy-results`` artifact. There is no held-out counterpart.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_paired_delta.py delta <baseline.json> <candidate.json>
    poetry run python scripts/accuracy_paired_delta.py recompute <run.json> [--lines <accuracy-output.txt>]

``delta`` checks that both files are main-corpus schema-1 files with the same
bootstrap block and the same document names (matched by name, resampled in the
baseline file's order), prints both run IDs and commits, then four
``[PAIRED-DELTA …]`` lines (candidate - baseline). Exit code 2 on a mismatch.

``recompute`` recomputes the four ``[CI95 …]`` main-corpus lines with the
seed and resample count recorded in the JSON. With ``--lines`` it also compares
them byte for byte with the artifact's lines, and checks the JSON's sums
against the TP/FP/FN of the ``[Overall]``, ``[PERSON]``, ``[LOCATION]`` and
``[ORG]`` lines. Exit code 1 on any difference, 2 on an invalid input.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.accuracy.bootstrap import (  # noqa: E402
    LABELS,
    PerDocumentRun,
    bootstrap_ranges,
    format_ci95_line,
    format_paired_delta_line,
    paired_delta_ranges,
    read_per_document_json,
)

_POINT_LINE = re.compile(
    r"^\[(Overall|PERSON|LOCATION|ORG)\] .*?\bTP=(\d+) FP=(\d+) FN=(\d+)(?: |$)"
)


class _InputError(Exception):
    """An input file is missing, unreadable or not a valid main-corpus file."""


def _load(path: Path) -> PerDocumentRun:
    try:
        return read_per_document_json(path)
    except (OSError, ValueError) as exc:
        raise _InputError(f"{path.name}: {exc}") from None


def _fmt(value: str | None) -> str:
    return "null" if value is None else value


def _delta(baseline_path: Path, candidate_path: Path) -> int:
    baseline = _load(baseline_path)
    candidate = _load(candidate_path)
    if baseline.bootstrap != candidate.bootstrap:
        raise _InputError("bootstrap blocks differ")
    if set(baseline.names) != set(candidate.names):
        raise _InputError(
            f"document names differ ({len(set(baseline.names) ^ set(candidate.names))}"
            " names in one file only)"
        )
    by_name = dict(zip(candidate.names, candidate.counts))
    aligned = [by_name[name] for name in baseline.names]
    deltas = paired_delta_ranges(
        baseline.counts,
        aligned,
        resamples=int(baseline.bootstrap["resamples"]),
        seed=int(baseline.bootstrap["seed"]),
    )
    print(f"baseline run_id={_fmt(baseline.run_id)} commit={_fmt(baseline.commit)}")
    print(f"candidate run_id={_fmt(candidate.run_id)} commit={_fmt(candidate.commit)}")
    for label in LABELS:
        print(format_paired_delta_line(deltas[label]))
    return 0


def _recompute(run_path: Path, lines_path: Path | None) -> int:
    run = _load(run_path)
    ranges = bootstrap_ranges(
        run.counts,
        resamples=int(run.bootstrap["resamples"]),
        seed=int(run.bootstrap["seed"]),
    )
    recomputed = {label: format_ci95_line(ranges[label]) for label in LABELS}
    print(f"run run_id={_fmt(run.run_id)} commit={_fmt(run.commit)}")
    for label in LABELS:
        print(recomputed[label])
    if lines_path is None:
        return 0

    try:
        artifact = lines_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise _InputError(f"{lines_path.name}: {exc}") from None
    differences = 0
    for label in LABELS:
        prefix = f"[CI95 {label}] "
        found = [line for line in artifact if line.startswith(prefix)]
        if found == [recomputed[label]]:
            print(f"match   [CI95 {label}]")
        else:
            differences += 1
            print(f"DIFFERS [CI95 {label}] ({len(found)} artifact line(s))")

    points: dict[str, list[tuple[int, int, int]]] = {label: [] for label in LABELS}
    for line in artifact:
        m = _POINT_LINE.match(line)
        if m:
            points[m.group(1)].append(
                (int(m.group(2)), int(m.group(3)), int(m.group(4)))
            )
    for label in LABELS:
        sums = tuple(sum(doc[label][k] for doc in run.counts) for k in range(3))
        if points[label] == [sums]:
            print(f"match   sums {label} TP={sums[0]} FP={sums[1]} FN={sums[2]}")
        else:
            differences += 1
            print(
                f"DIFFERS sums {label} JSON TP={sums[0]} FP={sums[1]} FN={sums[2]}, "
                f"artifact {points[label]}"
            )

    if differences:
        print(f"recompute: {differences} difference(s)")
        return 1
    print("recompute: match")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="accuracy_paired_delta.py",
        description="Paired bootstrap delta / CI95 recompute (Story 10.6 PR A).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_delta = sub.add_parser("delta", help="paired delta, candidate - baseline")
    p_delta.add_argument("baseline", type=Path)
    p_delta.add_argument("candidate", type=Path)
    p_re = sub.add_parser("recompute", help="recompute the main-corpus CI95 lines")
    p_re.add_argument("run", type=Path)
    p_re.add_argument("--lines", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "delta":
            return _delta(args.baseline, args.candidate)
        return _recompute(args.run, args.lines)
    except _InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
