"""Fixtures for NER accuracy validation tests.

Provides session-scoped fixtures for corpus loading, detector initialization,
and pre-computed detection results to avoid redundant model loading.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.utils.logger import configure_logging

# Configure structlog to use stdlib logging with WARNING level.
# This prevents Unicode encoding errors on Windows (cp1252) when structlog
# attempts to print debug messages containing French diacritics/symbols.
configure_logging("WARNING")

CORPUS_DIR = Path(__file__).parent.parent / "test_corpus"
ANNOTATIONS_DIR = CORPUS_DIR / "annotations"
INTERVIEWS_DIR = CORPUS_DIR / "interview_transcripts"
BUSINESS_DIR = CORPUS_DIR / "business_documents"


@dataclass
class GroundTruthEntity:
    """A single ground-truth annotated entity."""

    text: str
    entity_type: str
    start_pos: int
    end_pos: int


@dataclass
class DocumentResult:
    """Detection results for a single document."""

    doc_name: str
    detected: list[DetectedEntity]
    ground_truth: list[GroundTruthEntity]
    true_positives: list[tuple[DetectedEntity, GroundTruthEntity]] = field(
        default_factory=list
    )
    false_positives: list[DetectedEntity] = field(default_factory=list)
    false_negatives: list[GroundTruthEntity] = field(default_factory=list)


@dataclass
class AccuracyMetrics:
    """Aggregated accuracy metrics."""

    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    fn_rate: float
    fp_rate: float


def load_annotations(annotation_path: Path) -> list[GroundTruthEntity]:
    """Load ground-truth annotations from a JSON file."""
    with open(annotation_path, encoding="utf-8") as f:
        data = json.load(f)
    return [
        GroundTruthEntity(
            text=e["entity_text"],
            entity_type=e["entity_type"],
            start_pos=e["start_pos"],
            end_pos=e["end_pos"],
        )
        for e in data["entities"]
    ]


def match_entities(
    detected: list[DetectedEntity],
    ground_truth: list[GroundTruthEntity],
) -> tuple[
    list[tuple[DetectedEntity, GroundTruthEntity]],
    list[DetectedEntity],
    list[GroundTruthEntity],
]:
    """Match detected entities against ground truth using text + type matching.

    Uses case-insensitive, whitespace-normalized text comparison combined with
    entity type matching.  When the same text appears multiple times, position
    proximity is used as a tiebreaker.  Each entity is matched at most once.

    Returns:
        (true_positive_pairs, false_positives, false_negatives)
    """
    available = list(detected)
    tp_pairs: list[tuple[DetectedEntity, GroundTruthEntity]] = []
    fn_list: list[GroundTruthEntity] = []

    for gt in ground_truth:
        gt_text = " ".join(gt.text.lower().split())
        best_match: DetectedEntity | None = None
        best_distance = float("inf")

        for det in available:
            det_text = " ".join(det.text.lower().split())
            if det_text == gt_text and det.entity_type == gt.entity_type:
                distance = abs(det.start_pos - gt.start_pos)
                if distance < best_distance:
                    best_match = det
                    best_distance = distance

        if best_match is not None:
            tp_pairs.append((best_match, gt))
            available.remove(best_match)
        else:
            fn_list.append(gt)

    return tp_pairs, available, fn_list


def compute_metrics(tp: int, fp: int, fn: int) -> AccuracyMetrics:
    """Compute precision, recall, F1, FN rate, and FP rate."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    fn_rate = fn / (tp + fn) * 100 if (tp + fn) > 0 else 0.0
    fp_rate = fp / (tp + fp) * 100 if (tp + fp) > 0 else 0.0
    return AccuracyMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        fn_rate=fn_rate,
        fp_rate=fp_rate,
    )


def _load_corpus_documents() -> list[tuple[str, str, list[GroundTruthEntity]]]:
    """Load all document texts paired with their annotations.

    Returns:
        List of (doc_name, text, ground_truth) tuples.
    """
    docs: list[tuple[str, str, list[GroundTruthEntity]]] = []
    for subdir in (INTERVIEWS_DIR, BUSINESS_DIR):
        if not subdir.exists():
            continue
        for txt_path in sorted(subdir.glob("*.txt")):
            ann_path = ANNOTATIONS_DIR / f"{txt_path.stem}.json"
            if not ann_path.exists():
                continue
            text = txt_path.read_text(encoding="utf-8")
            annotations = load_annotations(ann_path)
            docs.append((txt_path.name, text, annotations))
    return docs


# ---------------------------------------------------------------------------
# Session-scoped fixtures (heavy lifting done once per test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def hybrid_detector() -> HybridDetector:
    """Session-scoped HybridDetector with model loaded."""
    detector = HybridDetector()
    detector.load_model("fr_core_news_lg")
    return detector


@pytest.fixture(scope="session")
def corpus_results(hybrid_detector: HybridDetector) -> list[DocumentResult]:
    """Run detection on all 25 documents and compute matching results."""
    docs = _load_corpus_documents()
    results: list[DocumentResult] = []
    for doc_name, text, ground_truth in docs:
        detected = hybrid_detector.detect_entities(text)
        tp_pairs, fp_list, fn_list = match_entities(detected, ground_truth)
        results.append(
            DocumentResult(
                doc_name=doc_name,
                detected=detected,
                ground_truth=ground_truth,
                true_positives=tp_pairs,
                false_positives=fp_list,
                false_negatives=fn_list,
            )
        )
    return results
