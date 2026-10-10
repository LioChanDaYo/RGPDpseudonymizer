"""Final-exam fingerprints and ledger check (Story 10.6 PR B, B3.2).

The final-exam set is not encrypted (Q5 reversed, Lionel 2026-10-09). Its
sha256 fingerprints are recorded at the freeze (B7.3) and checked when the
plain files are committed (B11.1) and before the one scored run (AC8).

Sub-commands::

    record --root <dir> --include <path>... --out <file> [--append]
    check --root <dir> --record <file>
    ledger-check --ledger <RUNS.md>

* ``record`` writes a ``sha256sum``-format list (``<hex>  <relative path>``,
  sorted by path, LF line endings) of every file under the included paths.
  With ``--append`` it keeps the existing lines byte for byte and adds the
  new ones after them. It prints only counts and the list file's own sha256.
* ``check`` verifies every listed file. It also reports a listed file that is
  missing and a file under a listed folder that is not listed. It prints
  ``OK <count>``, or one ``MISMATCH <relative path>`` line per problem and
  exits 1.
* ``ledger-check`` fails (exit 1) on a ``scored`` row or a malformed table.

Every error prints ``ERROR - <ExceptionClass>`` only, never a message or a
traceback (Dev Notes "Error Output"). Standard library only, no key.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

LEDGER_HEADER = (
    "| Run ID | Commit | Date (UTC) | Target | Status | Approved by | Note |"
)
LEDGER_STATUSES = ("scored", "infra-failure", "rerun")
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


class LedgerError(Exception):
    """The ledger table is malformed."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_files(root: Path, includes: list[str]) -> list[str]:
    """Relative POSIX paths of every file under the included paths, sorted."""
    paths: set[str] = set()
    for inc in includes:
        target = root / inc
        if target.is_file():
            paths.add(target.relative_to(root).as_posix())
        elif target.is_dir():
            for p in target.rglob("*"):
                if p.is_file():
                    paths.add(p.relative_to(root).as_posix())
        else:
            raise FileNotFoundError(inc)
    return sorted(paths)


def fingerprint_lines(root: Path, rel_paths: list[str]) -> list[str]:
    return [f"{file_sha256(root / rel)}  {rel}\n" for rel in rel_paths]


def parse_record(text: str) -> list[tuple[str, str]]:
    """Return (sha256, relative path) for every line of a record."""
    entries: list[tuple[str, str]] = []
    for line in text.split("\n"):
        if not line:
            continue
        digest, sep, rel = line.partition("  ")
        if not sep or not re.fullmatch(r"[0-9a-f]{64}", digest) or not rel:
            raise ValueError("bad record line")
        entries.append((digest, rel))
    return entries


def record(root: Path, includes: list[str], out: Path, append: bool) -> int:
    rel_paths = collect_files(root, includes)
    existing = ""
    if append:
        existing = out.read_text(encoding="utf-8")
        listed = {rel for _, rel in parse_record(existing)}
        if listed & set(rel_paths):
            raise ValueError("path already recorded")
        if existing and not existing.endswith("\n"):
            raise ValueError("record does not end with a newline")
    lines = fingerprint_lines(root, rel_paths)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(existing + "".join(lines))
    total = len(parse_record(out.read_text(encoding="utf-8")))
    print(f"recorded={len(lines)} total={total} record_sha256={file_sha256(out)}")
    return 0


def check(root: Path, record_path: Path) -> int:
    entries = parse_record(record_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    listed = {rel for _, rel in entries}
    for digest, rel in entries:
        target = root / rel
        if not target.is_file() or file_sha256(target) != digest:
            problems.append(rel)
    folders = {rel.split("/", 1)[0] for rel in listed if "/" in rel}
    for folder in sorted(folders):
        for rel in collect_files(root, [folder]):
            if rel not in listed:
                problems.append(rel)
    if problems:
        for rel in sorted(set(problems)):
            print(f"MISMATCH {rel}")
        return 1
    print(f"OK {len(entries)}")
    return 0


def _cells(line: str) -> list[str]:
    if not (line.startswith("|") and line.endswith("|")):
        raise LedgerError
    return [c.strip() for c in line[1:-1].split("|")]


def ledger_rows(text: str) -> list[list[str]]:
    """Parse the ledger table. Raises ``LedgerError`` if it is malformed."""
    lines = text.split("\n")
    headers = [i for i, line in enumerate(lines) if line.strip() == LEDGER_HEADER]
    if len(headers) != 1:
        raise LedgerError
    i = headers[0]
    if i + 1 >= len(lines):
        raise LedgerError
    sep = _cells(lines[i + 1].strip())
    if len(sep) != 7 or not all(_SEPARATOR_CELL.match(c) for c in sep):
        raise LedgerError
    rows: list[list[str]] = []
    for line in lines[i + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = _cells(stripped)
        if len(cells) != 7 or cells[4] not in LEDGER_STATUSES:
            raise LedgerError
        rows.append(cells)
    return rows


def ledger_check(ledger: Path) -> int:
    rows = ledger_rows(ledger.read_text(encoding="utf-8"))
    scored = sum(1 for r in rows if r[4] == "scored")
    print(f"ledger rows={len(rows)} scored={scored}")
    return 1 if scored else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="final_exam_fingerprints")
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--root", required=True, type=Path)
    rec.add_argument("--include", required=True, nargs="+")
    rec.add_argument("--out", required=True, type=Path)
    rec.add_argument("--append", action="store_true")
    chk = sub.add_parser("check")
    chk.add_argument("--root", required=True, type=Path)
    chk.add_argument("--record", required=True, type=Path)
    led = sub.add_parser("ledger-check")
    led.add_argument("--ledger", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "record":
            return record(args.root, args.include, args.out, args.append)
        if args.command == "check":
            return check(args.root, args.record)
        return ledger_check(args.ledger)
    except Exception as exc:  # noqa: BLE001 - print the class only (Error Output)
        print(f"ERROR - {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
