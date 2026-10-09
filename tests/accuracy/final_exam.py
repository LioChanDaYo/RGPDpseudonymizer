"""Final-exam loading and scoring (Story 10.6 PR B, AC8, B3.4).

The final exam is scored only in the ``final_exam`` job of ``accuracy.yaml``
(one manual dispatch), or locally on the dummy fixture. The folder named by
``FINAL_EXAM_DIR`` holds ``documents/``, ``annotations/`` and
``manifest.json``; nothing else is read.

Output is aggregate only: 12 point lines (all documents, then the planted
half, then the natural half, each Overall, PERSON, LOCATION, ORG), each
followed by its ``[CI95 FINAL-EXAM …]`` line. No per-document number, no
entity text. Any error while loading or scoring a document is re-raised as
``RuntimeError("<ExceptionClass> on <id>")`` with no chained cause, so a
public CI log never shows document text (Dev Notes "Error Output").

When ``ACCURACY_LOG_LEVEL`` is set, the root logger is set to that level at
import, so no detector log below it is emitted in the ``final_exam`` job.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from tests.accuracy import bootstrap
from tests.accuracy.conftest import (
    DocumentResult,
    _score_documents,
    compute_metrics,
    load_annotations,
)

LOG_LEVEL_ENV = "ACCURACY_LOG_LEVEL"
DIR_ENV = "FINAL_EXAM_DIR"
EXPECTED_DOCS_ENV = "FINAL_EXAM_EXPECTED_DOCS"
FORCE_FAILURE_ENV = "FINAL_EXAM_FORCE_FAILURE"
HALVES = ("planted", "natural")
ENTITY_TYPES = ("PERSON", "LOCATION", "ORG")


def apply_log_level(env: Mapping[str, str] = os.environ) -> None:
    """Set the root logger to ``$ACCURACY_LOG_LEVEL`` when it is set."""
    level = env.get(LOG_LEVEL_ENV, "").strip().upper()
    if level:
        logging.getLogger().setLevel(level)


apply_log_level()


@dataclass(frozen=True)
class Manifest:
    target: str
    halves: dict[str, str]  # document id -> "planted" | "natural"


def final_exam_root(env: Mapping[str, str] = os.environ) -> Path | None:
    value = env.get(DIR_ENV, "").strip()
    return Path(value) if value else None


def load_manifest(root: Path) -> Manifest:
    try:
        data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        halves = {str(d["id"]): str(d["half"]) for d in data["documents"]}
        target = str(data["target"])
    except Exception as exc:
        raise RuntimeError(f"{type(exc).__name__} on manifest") from None
    if any(h not in HALVES for h in halves.values()):
        raise RuntimeError("ValueError on manifest")
    return Manifest(target=target, halves=halves)


def expected_docs(manifest: Manifest, env: Mapping[str, str] = os.environ) -> int:
    value = env.get(EXPECTED_DOCS_ENV, "").strip()
    return int(value) if value else len(manifest.halves)


def force_failure(manifest: Manifest, env: Mapping[str, str] = os.environ) -> bool:
    """Honoured only on the dummy fixture (B8.5)."""
    return manifest.target == "dummy" and env.get(FORCE_FAILURE_ENV, "") == "1"


def score_final_exam(
    detector: object, root: Path, manifest: Manifest
) -> list[tuple[str, DocumentResult]]:
    """(half, result) per document, in id order. Errors name the document only."""
    stems = sorted(p.stem for p in (root / "documents").glob("*.txt"))
    if stems != sorted(manifest.halves):
        raise RuntimeError("ManifestMismatch on documents")
    scored: list[tuple[str, DocumentResult]] = []
    for doc_id in sorted(manifest.halves):
        try:
            text = (root / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
            truth = load_annotations(root / "annotations" / f"{doc_id}.json")
            (result,) = _score_documents(
                detector, [(f"{doc_id}.txt", text, truth)]  # type: ignore[arg-type]
            )
        except Exception as exc:
            raise RuntimeError(f"{type(exc).__name__} on {doc_id}") from None
        scored.append((manifest.halves[doc_id], result))
    return scored


def _point_line(
    label: str, results: list[DocumentResult], entity_type: str | None
) -> str:
    tp = fp = fn = 0
    for r in results:
        counts = bootstrap.doc_counts(r)[entity_type or "Overall"]
        tp, fp, fn = tp + counts[0], fp + counts[1], fn + counts[2]
    m = compute_metrics(tp, fp, fn)
    line = (
        f"[{label} {entity_type or 'Overall'}] P={m.precision:.4f} R={m.recall:.4f} "
        f"F1={m.f1:.4f} TP={m.tp} FP={m.fp} FN={m.fn}"
    )
    if entity_type is None:
        line += f" FN%={m.fn_rate:.2f} FP%={m.fp_rate:.2f}"
    return line


def report_lines(scored: list[tuple[str, DocumentResult]]) -> list[str]:
    """The 12 point lines, each followed by its CI95 line."""
    groups = [("FINAL-EXAM", [r for _, r in scored])] + [
        (f"FINAL-EXAM {half.upper()}", [r for h, r in scored if h == half])
        for half in HALVES
    ]
    lines: list[str] = []
    for scope, results in groups:
        ranges = bootstrap.bootstrap_ranges([bootstrap.doc_counts(r) for r in results])
        for label in bootstrap.LABELS:
            lines.append(
                _point_line(scope, results, None if label == "Overall" else label)
            )
            lines.append(bootstrap.format_ci95_line(ranges[label], scope=scope))
    return lines
