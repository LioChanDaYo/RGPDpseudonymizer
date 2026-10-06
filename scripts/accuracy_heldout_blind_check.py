"""Held-out-blind string check (Story 10.3a AC11, PO validation 2026-10-06).

A real (non-invented) string may go into a new test or resource only if it
occurs in the main-corpus text, or if Lionel approves it. "Occurs" is the
leakage guard's own comparison: case-insensitive whole tokens
(``token_string`` in ``tests/unit/test_held_out_leakage.py``), over the
guard's ``MAIN_TEXT_DIRS`` only. This script never reads ``held_out/``.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_heldout_blind_check.py <string> [<string> ...]
    poetry run python scripts/accuracy_heldout_blind_check.py --file <one string per line>
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tests.unit.test_held_out_leakage import (  # noqa: E402
    MAIN_TEXT_DIRS,
    token_string,
)


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["--file"] and len(args) == 2:
        strings = [
            s.strip()
            for s in Path(args[1]).read_text(encoding="utf-8").splitlines()
            if s.strip()
        ]
    elif args:
        strings = args
    else:
        sys.exit(__doc__)
    main_text = token_string(
        " ".join(
            p.read_text(encoding="utf-8")
            for d in MAIN_TEXT_DIRS
            for p in sorted(d.glob("*.txt"))
        )
    )
    missing = [s for s in strings if token_string(s) not in main_text]
    print(f"checked={len(strings)} not_in_main_corpus={len(missing)}")
    for s in missing:
        print(f"  NEEDS APPROVAL: {s!r}")


if __name__ == "__main__":
    main()
