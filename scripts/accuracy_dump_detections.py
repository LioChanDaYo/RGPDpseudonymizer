"""Dump main-corpus detections to JSON and check they reproduce a CI run.

Story 10.2, Task 1.1/1.2 (adapted from the out-of-repo ``dump_detections.py``).
Main corpus only: calls ``_load_corpus_documents()`` and never the held-out
loader. Imports ``tests.accuracy.conftest`` read-only (G4 scope).

The dump is an attribution tool, not a metric source (gate G1): it is written
outside the repository and must not be committed.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_dump_detections.py <out.json>
"""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import structlog  # noqa: E402

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))

from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector  # noqa: E402
from tests.accuracy.conftest import (  # noqa: E402
    _load_corpus_documents,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: accuracy_dump_detections.py <out.json>")
    out_path = Path(sys.argv[1]).resolve()
    if REPO_ROOT in out_path.parents:
        sys.exit("refusing to write the dump inside the repository")

    det = HybridDetector()
    det.load_model("fr_core_news_lg")

    dump: dict[str, list[dict[str, object]]] = {}
    totals = {t: [0, 0, 0] for t in TYPES}
    for name, text, gt in _load_corpus_documents():
        detected = det.detect_entities(text)
        dump[name] = [
            {
                "text": d.text,
                "type": d.entity_type,
                "start": d.start_pos,
                "end": d.end_pos,
                "source": d.source,
                "is_ambiguous": d.is_ambiguous,
            }
            for d in detected
        ]
        tp, fp, fn = match_entities(detected, gt)
        for t in TYPES:
            totals[t][0] += sum(1 for d, _ in tp if d.entity_type == t)
            totals[t][1] += sum(1 for d in fp if d.entity_type == t)
            totals[t][2] += sum(1 for g in fn if g.entity_type == t)

    out_path.write_text(
        json.dumps(dump, ensure_ascii=False, indent=0), encoding="utf-8"
    )
    n = sum(len(v) for v in dump.values())
    tp_all = sum(v[0] for v in totals.values())
    fp_all = sum(v[1] for v in totals.values())
    fn_all = sum(v[2] for v in totals.values())
    print(f"docs={len(dump)} detections={n} -> {out_path}")
    print(f"[Overall] TP={tp_all} FP={fp_all} FN={fn_all}")
    for t in TYPES:
        print(f"[{t}] TP={totals[t][0]} FP={totals[t][1]} FN={totals[t][2]}")


if __name__ == "__main__":
    main()
