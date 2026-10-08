"""Document-level bootstrap confidence ranges for the accuracy suite.

Story 10.6 PR A (AC1, AC3). Resampling is by document, with replacement,
because entities in one document are not independent. Each resample re-sums
TP/FP/FN over the drawn documents and recomputes P/R/F1 with the scorer's own
``compute_metrics``; the range is the percentile interval of the defined
values. The resample count and the seed are fixed, so the output is
deterministic.

Undefined metrics: P is undefined when TP + FP = 0 in a resample, R when
TP + FN = 0, F1 when P or R is undefined. An undefined resample is left out of
that metric's distribution and counted (``undef_P``, ``undef_R``,
``undef_F1``). ``compute_metrics`` returns 0.0 for a zero denominator, so the
decision is made before calling it.

The per-document JSON (``accuracy-per-document.json``) is written for the main
corpus only. There is no held-out or final-exam counterpart: held-out counts
stay in memory inside the held-out test and are reduced to aggregate lines.

Standard library only, plus ``compute_metrics``. No spaCy model, no logging.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from tests.accuracy.conftest import compute_metrics

RESAMPLES = 10_000
SEED = 20261008
CONFIDENCE = 95
LABELS = ("Overall", "PERSON", "LOCATION", "ORG")
ENTITY_TYPES = ("PERSON", "LOCATION", "ORG")

SCHEMA_VERSION = 1
PER_DOC_JSON_ENV = "ACCURACY_PER_DOC_JSON"
PER_DOC_JSON_NAME = "accuracy-per-document.json"
BOOTSTRAP_BLOCK: dict[str, Any] = {
    "unit": "document",
    "method": "percentile",
    "confidence": CONFIDENCE,
    "resamples": RESAMPLES,
    "seed": SEED,
}

Counts = tuple[int, int, int]
"""(TP, FP, FN) for one label."""

DocCounts = Mapping[str, Counts]
"""Label -> (TP, FP, FN) for one document."""

Draw = Callable[[random.Random, int], list[int]]


class EntityLike(Protocol):
    @property
    def entity_type(self) -> str: ...


class ScoredDocument(Protocol):
    """Anything with the three match lists of ``DocumentResult``."""

    @property
    def true_positives(self) -> Sequence[tuple[EntityLike, EntityLike]]: ...

    @property
    def false_positives(self) -> Sequence[EntityLike]: ...

    @property
    def false_negatives(self) -> Sequence[EntityLike]: ...


@dataclass(frozen=True)
class MetricRange:
    """Percentile range of one metric; ``lo``/``hi`` are None when no
    resample is defined."""

    lo: float | None
    hi: float | None
    undefined: int


@dataclass(frozen=True)
class LabelRanges:
    label: str
    docs: int
    resamples: int
    seed: int
    precision: MetricRange
    recall: MetricRange
    f1: MetricRange


@dataclass(frozen=True)
class DeltaRange:
    """Point delta (candidate - baseline) and the paired percentile range."""

    point: float
    lo: float | None
    hi: float | None
    undefined: int

    @property
    def excludes_zero(self) -> bool:
        if self.lo is None or self.hi is None:
            return False
        return self.lo > 0 or self.hi < 0


@dataclass(frozen=True)
class LabelDelta:
    label: str
    docs: int
    resamples: int
    seed: int
    precision: DeltaRange
    recall: DeltaRange
    f1: DeltaRange


@dataclass(frozen=True)
class PerDocumentRun:
    """Contents of an ``accuracy-per-document.json`` file."""

    run_id: str | None
    commit: str | None
    bootstrap: dict[str, Any]
    names: tuple[str, ...]
    counts: tuple[dict[str, Counts], ...]


# ---------------------------------------------------------------------------
# Counting and resampling
# ---------------------------------------------------------------------------


def doc_counts(result: ScoredDocument) -> dict[str, Counts]:
    """Per-label (TP, FP, FN) of one document, counted as ``_aggregate`` does.

    Overall uses the lengths of the three lists. Per type, TP is counted on the
    ground-truth type of each pair, FP on the detection type, FN on the
    ground-truth type.
    """
    counts: dict[str, Counts] = {
        "Overall": (
            len(result.true_positives),
            len(result.false_positives),
            len(result.false_negatives),
        )
    }
    for entity_type in ENTITY_TYPES:
        counts[entity_type] = (
            sum(1 for _, gt in result.true_positives if gt.entity_type == entity_type),
            sum(1 for d in result.false_positives if d.entity_type == entity_type),
            sum(1 for g in result.false_negatives if g.entity_type == entity_type),
        )
    return counts


def draw_indices(rng: random.Random, n: int) -> list[int]:
    """One resample: n document indices drawn with replacement."""
    return [rng.randrange(n) for _ in range(n)]


def metric_values(
    tp: int, fp: int, fn: int
) -> tuple[float | None, float | None, float | None]:
    """(P, R, F1) for summed counts, None where the metric is undefined.

    Defined values come from ``compute_metrics``. When P and R are both
    defined and TP = 0, F1 is 0.0 and is kept.
    """
    m = compute_metrics(tp, fp, fn)
    precision = m.precision if tp + fp > 0 else None
    recall = m.recall if tp + fn > 0 else None
    f1 = m.f1 if precision is not None and recall is not None else None
    return precision, recall, f1


def percentile_indices(m: int) -> tuple[int, int]:
    """Indices of the 2.5% and 97.5% bounds in m sorted values (integers only)."""
    if m <= 0:
        raise ValueError("percentile_indices needs at least one value")
    return (25 * m) // 1000, (975 * m + 999) // 1000 - 1


def _percentile_range(values: list[float], undefined: int) -> MetricRange:
    if not values:
        return MetricRange(None, None, undefined)
    ordered = sorted(values)
    lo_i, hi_i = percentile_indices(len(ordered))
    return MetricRange(ordered[lo_i], ordered[hi_i], undefined)


def _columns(
    per_doc: Sequence[DocCounts], label: str
) -> tuple[list[int], list[int], list[int]]:
    return (
        [d[label][0] for d in per_doc],
        [d[label][1] for d in per_doc],
        [d[label][2] for d in per_doc],
    )


def _summed(columns: tuple[list[int], list[int], list[int]], idx: list[int]) -> Counts:
    tps, fps, fns = columns
    return (
        sum(tps[i] for i in idx),
        sum(fps[i] for i in idx),
        sum(fns[i] for i in idx),
    )


def bootstrap_ranges(
    per_doc: Sequence[DocCounts],
    labels: Sequence[str] = LABELS,
    resamples: int = RESAMPLES,
    seed: int = SEED,
    draw: Draw = draw_indices,
) -> dict[str, LabelRanges]:
    """95% percentile ranges of P, R and F1 for each label.

    One fresh ``random.Random(seed)`` per call; one draw of document indices
    per resample, shared by every label.
    """
    n = len(per_doc)
    if n == 0:
        raise ValueError("bootstrap_ranges needs at least one document")
    columns = {label: _columns(per_doc, label) for label in labels}
    values: dict[str, list[list[float]]] = {label: [[], [], []] for label in labels}
    undefined = {label: [0, 0, 0] for label in labels}
    rng = random.Random(seed)
    for _ in range(resamples):
        idx = draw(rng, n)
        for label in labels:
            for k, v in enumerate(metric_values(*_summed(columns[label], idx))):
                if v is None:
                    undefined[label][k] += 1
                else:
                    values[label][k].append(v)
    return {
        label: LabelRanges(
            label=label,
            docs=n,
            resamples=resamples,
            seed=seed,
            precision=_percentile_range(values[label][0], undefined[label][0]),
            recall=_percentile_range(values[label][1], undefined[label][1]),
            f1=_percentile_range(values[label][2], undefined[label][2]),
        )
        for label in labels
    }


def paired_delta_ranges(
    baseline: Sequence[DocCounts],
    candidate: Sequence[DocCounts],
    labels: Sequence[str] = LABELS,
    resamples: int = RESAMPLES,
    seed: int = SEED,
    draw: Draw = draw_indices,
) -> dict[str, LabelDelta]:
    """Paired bootstrap of candidate - baseline over the same documents.

    ``baseline[i]`` and ``candidate[i]`` must be the same document. The same
    index draw serves both runs and every label. A resample where either side
    is undefined is left out of that metric's distribution and counted.
    """
    n = len(baseline)
    if n == 0 or len(candidate) != n:
        raise ValueError("paired_delta_ranges needs two aligned, non-empty runs")
    base_cols = {label: _columns(baseline, label) for label in labels}
    cand_cols = {label: _columns(candidate, label) for label in labels}
    deltas: dict[str, list[list[float]]] = {label: [[], [], []] for label in labels}
    undefined = {label: [0, 0, 0] for label in labels}
    rng = random.Random(seed)
    all_idx = list(range(n))
    for _ in range(resamples):
        idx = draw(rng, n)
        for label in labels:
            base = metric_values(*_summed(base_cols[label], idx))
            cand = metric_values(*_summed(cand_cols[label], idx))
            for k in range(3):
                b, c = base[k], cand[k]
                if b is None or c is None:
                    undefined[label][k] += 1
                else:
                    deltas[label][k].append(c - b)
    result: dict[str, LabelDelta] = {}
    for label in labels:
        mb = compute_metrics(*_summed(base_cols[label], all_idx))
        mc = compute_metrics(*_summed(cand_cols[label], all_idx))
        points = (
            mc.precision - mb.precision,
            mc.recall - mb.recall,
            mc.f1 - mb.f1,
        )
        ranges = [
            _percentile_range(deltas[label][k], undefined[label][k]) for k in range(3)
        ]
        p, r, f = (
            DeltaRange(points[k], ranges[k].lo, ranges[k].hi, ranges[k].undefined)
            for k in range(3)
        )
        result[label] = LabelDelta(label, n, resamples, seed, p, r, f)
    return result


# ---------------------------------------------------------------------------
# Line formatters
# ---------------------------------------------------------------------------


def _fmt_range(r: MetricRange) -> str:
    if r.lo is None or r.hi is None:
        return "[n/a]"
    return f"[{r.lo:.4f},{r.hi:.4f}]"


def format_ci95_line(ranges: LabelRanges, scope: str = "") -> str:
    """One ``[CI95 …]`` line. ``scope`` is "" (main corpus) or e.g. "HELD-OUT"."""
    label = f"{scope} {ranges.label}" if scope else ranges.label
    return (
        f"[CI95 {label}] P={_fmt_range(ranges.precision)} "
        f"R={_fmt_range(ranges.recall)} F1={_fmt_range(ranges.f1)} "
        f"unit=document docs={ranges.docs} resamples={ranges.resamples} "
        f"seed={ranges.seed} undef_P={ranges.precision.undefined} "
        f"undef_R={ranges.recall.undefined} undef_F1={ranges.f1.undefined}"
    )


def _fmt_delta(d: DeltaRange) -> str:
    if d.lo is None or d.hi is None:
        bounds = "[n/a]"
    else:
        bounds = f"[{d.lo:+.4f},{d.hi:+.4f}]"
    return f"{d.point:+.4f} {bounds}"


def _yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def format_paired_delta_line(delta: LabelDelta) -> str:
    """One ``[PAIRED-DELTA …]`` line (script output, never in the artifact)."""
    return (
        f"[PAIRED-DELTA {delta.label}] dP={_fmt_delta(delta.precision)} "
        f"dR={_fmt_delta(delta.recall)} dF1={_fmt_delta(delta.f1)} "
        f"unit=document docs={delta.docs} resamples={delta.resamples} "
        f"seed={delta.seed} undef_P={delta.precision.undefined} "
        f"undef_R={delta.recall.undefined} undef_F1={delta.f1.undefined} "
        f"excludes_0=P:{_yes_no(delta.precision.excludes_zero)},"
        f"R:{_yes_no(delta.recall.excludes_zero)},"
        f"F1:{_yes_no(delta.f1.excludes_zero)}"
    )


# ---------------------------------------------------------------------------
# Main-corpus per-document JSON (AC3)
# ---------------------------------------------------------------------------


def per_document_json_path(default_dir: Path) -> Path:
    """``$ACCURACY_PER_DOC_JSON`` when set (CI), else a file in *default_dir*."""
    target = os.environ.get(PER_DOC_JSON_ENV)
    return Path(target) if target else default_dir / PER_DOC_JSON_NAME


def github_run_metadata() -> tuple[str | None, str | None]:
    """(run id, commit) from ``GITHUB_RUN_ID`` / ``GITHUB_SHA``, or None."""
    return (
        os.environ.get("GITHUB_RUN_ID") or None,
        os.environ.get("GITHUB_SHA") or None,
    )


def write_per_document_json(
    path: Path,
    names: Sequence[str],
    per_doc: Sequence[DocCounts],
    run_id: str | None,
    commit: str | None,
) -> None:
    """Write the main-corpus per-document counts (documents in loader order)."""
    if len(names) != len(per_doc):
        raise ValueError("names and per_doc differ in length")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "corpus": "main",
        "run_id": run_id,
        "commit": commit,
        "bootstrap": dict(BOOTSTRAP_BLOCK),
        "labels": list(LABELS),
        "documents": [
            {
                "doc": name,
                **{
                    label: {
                        "tp": counts[label][0],
                        "fp": counts[label][1],
                        "fn": counts[label][2],
                    }
                    for label in LABELS
                },
            }
            for name, counts in zip(names, per_doc)
        ],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _int(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{what} is not a non-negative integer")
    return value


def read_per_document_json(path: Path) -> PerDocumentRun:
    """Read and validate an ``accuracy-per-document.json`` file.

    Raises ``ValueError`` when the schema version, the corpus, the labels or
    a document entry is not as written by ``write_per_document_json``.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version is not {SCHEMA_VERSION}")
    if data.get("corpus") != "main":
        raise ValueError('corpus is not "main"')
    if data.get("labels") != list(LABELS):
        raise ValueError("labels differ from " + ",".join(LABELS))
    block = data.get("bootstrap")
    if not isinstance(block, dict):
        raise ValueError("bootstrap block missing")
    if _int(block.get("resamples"), "bootstrap.resamples") == 0:
        raise ValueError("bootstrap.resamples is 0")
    _int(block.get("seed"), "bootstrap.seed")
    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("documents missing or empty")
    names: list[str] = []
    counts: list[dict[str, Counts]] = []
    for i, entry in enumerate(documents):
        if not isinstance(entry, dict) or not isinstance(entry.get("doc"), str):
            raise ValueError(f"document {i} has no name")
        doc: dict[str, Counts] = {}
        for label in LABELS:
            c = entry.get(label)
            if not isinstance(c, dict):
                raise ValueError(f"document {i} has no {label} counts")
            doc[label] = (
                _int(c.get("tp"), f"document {i} {label} tp"),
                _int(c.get("fp"), f"document {i} {label} fp"),
                _int(c.get("fn"), f"document {i} {label} fn"),
            )
        names.append(entry["doc"])
        counts.append(doc)
    if len(set(names)) != len(names):
        raise ValueError("duplicate document names")
    run_id = data.get("run_id")
    commit = data.get("commit")
    return PerDocumentRun(
        run_id=None if run_id is None else str(run_id),
        commit=None if commit is None else str(commit),
        bootstrap=dict(block),
        names=tuple(names),
        counts=tuple(counts),
    )
