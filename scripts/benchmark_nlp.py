"""
NLP Benchmark Script for GDPR Pseudonymizer

This script benchmarks NLP library performance against ground truth annotations.
It calculates precision, recall, and F1 scores per entity type.

Usage:
    python scripts/benchmark_nlp.py --library spacy
    python scripts/benchmark_nlp.py --library stanza --verbose
    python scripts/benchmark_nlp.py --library spacy --performance

NOTE: Typer CLI framework will be added in proper project setup (Epic 0).
      This version uses argparse for Story 1.2 deliverable.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
import argparse
from dataclasses import dataclass
from collections import defaultdict
import time
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gdpr_pseudonymizer.nlp.entity_detector import EntityDetector
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.nlp.stanza_detector import StanzaDetector


@dataclass
class Entity:
    """Represents a named entity."""

    text: str
    type: str
    start: int
    end: int


@dataclass
class MetricsResult:
    """Metrics for entity detection."""

    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def load_document(doc_path: Path) -> str:
    """Load document text from file.

    Args:
        doc_path: Path to document file

    Returns:
        Document text content
    """
    with open(doc_path, "r", encoding="utf-8") as f:
        return f.read()


def load_annotations(annotation_path: Path) -> List[Entity]:
    """Load ground truth annotations from JSON file.

    Args:
        annotation_path: Path to annotation JSON file

    Returns:
        List of Entity objects
    """
    with open(annotation_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = []
    for entity_data in data["entities"]:
        entities.append(
            Entity(
                text=entity_data["entity_text"],
                type=entity_data["entity_type"],
                start=entity_data["start_pos"],
                end=entity_data["end_pos"],
            )
        )

    return entities


def load_corpus(corpus_dir: Path) -> Dict[str, Tuple[str, List[Entity]]]:
    """Load all documents and annotations from corpus directory.

    Args:
        corpus_dir: Path to test corpus directory

    Returns:
        Dictionary mapping document names to (text, entities) tuples
    """
    corpus = {}
    annotations_dir = corpus_dir / "annotations"

    # Load interview transcripts
    interviews_dir = corpus_dir / "interview_transcripts"
    if interviews_dir.exists():
        for doc_path in sorted(interviews_dir.glob("*.txt")):
            annotation_path = annotations_dir / f"{doc_path.stem}.json"
            if annotation_path.exists():
                text = load_document(doc_path)
                entities = load_annotations(annotation_path)
                corpus[doc_path.name] = (text, entities)

    # Load business documents
    business_dir = corpus_dir / "business_documents"
    if business_dir.exists():
        for doc_path in sorted(business_dir.glob("*.txt")):
            annotation_path = annotations_dir / f"{doc_path.stem}.json"
            if annotation_path.exists():
                text = load_document(doc_path)
                entities = load_annotations(annotation_path)
                corpus[doc_path.name] = (text, entities)

    return corpus


def run_ner(text: str, detector: EntityDetector) -> List[Entity]:
    """Run NER on text using specified detector.

    Args:
        text: Document text
        detector: EntityDetector implementation (spaCy or Stanza)

    Returns:
        List of Entity objects
    """
    detected = detector.detect_entities(text)

    # Convert DetectedEntity to Entity format for metrics
    entities = []
    for ent in detected:
        entities.append(
            Entity(
                text=ent.text,
                type=ent.entity_type,
                start=ent.start_pos,
                end=ent.end_pos,
            )
        )

    return entities


def calculate_metrics(
    predicted: List[Entity], ground_truth: List[Entity], entity_type: str
) -> MetricsResult:
    """Calculate precision, recall, and F1 for a specific entity type.

    Args:
        predicted: List of predicted entities
        ground_truth: List of ground truth entities
        entity_type: Entity type to evaluate (PERSON, LOCATION, ORG)

    Returns:
        MetricsResult with calculated metrics
    """
    # Filter entities by type
    pred_entities = {(e.start, e.end) for e in predicted if e.type == entity_type}
    true_entities = {(e.start, e.end) for e in ground_truth if e.type == entity_type}

    # Calculate metrics
    true_positives = len(pred_entities & true_entities)
    false_positives = len(pred_entities - true_entities)
    false_negatives = len(true_entities - pred_entities)

    # Calculate precision
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )

    # Calculate recall
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )

    # Calculate F1 score
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return MetricsResult(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def aggregate_metrics(metrics_list: List[MetricsResult]) -> MetricsResult:
    """Aggregate metrics across multiple documents.

    Args:
        metrics_list: List of MetricsResult objects

    Returns:
        Aggregated MetricsResult
    """
    total_tp = sum(m.true_positives for m in metrics_list)
    total_fp = sum(m.false_positives for m in metrics_list)
    total_fn = sum(m.false_negatives for m in metrics_list)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return MetricsResult(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn,
    )


def create_detector(library: str) -> Optional[EntityDetector]:
    """Create detector instance for specified library.

    Args:
        library: Library name (spacy or stanza)

    Returns:
        EntityDetector instance or None
    """
    if library == "spacy":
        return SpaCyDetector()
    elif library == "stanza":
        return StanzaDetector()
    else:
        return None


def main():
    """Main function to run NLP benchmark."""
    parser = argparse.ArgumentParser(
        description="Benchmark NLP library performance against ground truth corpus"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("tests/test_corpus"),
        help="Path to test corpus directory",
    )
    parser.add_argument(
        "--library",
        type=str,
        required=True,
        choices=["spacy", "stanza"],
        help="NLP library to use",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show per-document results"
    )
    parser.add_argument(
        "--performance",
        "-p",
        action="store_true",
        help="Measure performance metrics (time, memory)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("NLP BENCHMARK - GDPR Pseudonymizer")
    print("=" * 60)
    print()

    # Load corpus
    print(f"Loading corpus from: {args.corpus}")
    corpus_data = load_corpus(args.corpus)
    print(f"Loaded {len(corpus_data)} documents")
    print()

    if len(corpus_data) == 0:
        print("Error: No documents found in corpus")
        return 1

    # Create detector
    print(f"Initializing {args.library.upper()} detector...")
    detector = create_detector(args.library)
    if detector is None:
        print(f"Error: Unknown library '{args.library}'")
        return 1

    # Measure model loading time if performance flag set
    load_start_time = time.time() if args.performance else None

    # Initialize metrics storage
    entity_types = ["PERSON", "LOCATION", "ORG"]
    all_metrics = defaultdict(list)
    processing_times = []

    # Process each document
    print(f"Running NER with library: {args.library}")
    print()

    for doc_name, (text, ground_truth) in corpus_data.items():
        # Measure processing time if performance flag set
        doc_start_time = time.time() if args.performance else None

        # Run NER
        predicted = run_ner(text, detector)

        # Record processing time
        if args.performance and doc_start_time is not None:
            doc_time = time.time() - doc_start_time
            processing_times.append(doc_time)

        # Calculate metrics per entity type
        for entity_type in entity_types:
            metrics = calculate_metrics(predicted, ground_truth, entity_type)
            all_metrics[entity_type].append(metrics)

        if args.verbose:
            if args.performance and doc_start_time is not None:
                print(f"Processed: {doc_name} ({doc_time:.3f}s)")
            else:
                print(f"Processed: {doc_name}")

    # Aggregate and display results
    print("=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print()

    for entity_type in entity_types:
        aggregated = aggregate_metrics(all_metrics[entity_type])

        print(f"{entity_type}:")
        print(f"  Precision: {aggregated.precision:.4f}")
        print(f"  Recall:    {aggregated.recall:.4f}")
        print(f"  F1 Score:  {aggregated.f1:.4f}")
        print(
            f"  TP: {aggregated.true_positives}, FP: {aggregated.false_positives}, FN: {aggregated.false_negatives}"
        )
        print()

    # Calculate overall metrics
    all_metrics_combined = []
    for metrics_list in all_metrics.values():
        all_metrics_combined.extend(metrics_list)

    overall = aggregate_metrics(all_metrics_combined)
    print("OVERALL:")
    print(f"  Precision: {overall.precision:.4f}")
    print(f"  Recall:    {overall.recall:.4f}")
    print(f"  F1 Score:  {overall.f1:.4f}")
    print()

    # Display performance metrics if requested
    if args.performance and processing_times:
        print("=" * 60)
        print("PERFORMANCE METRICS")
        print("=" * 60)
        print()

        avg_time = sum(processing_times) / len(processing_times)
        total_time = sum(processing_times)
        model_load_time = (
            time.time() - load_start_time - total_time if load_start_time else 0
        )

        print(f"Model Loading Time: {model_load_time:.3f}s")
        print(f"Average Processing Time per Document: {avg_time:.3f}s")
        print(f"Total Processing Time: {total_time:.3f}s")
        print(f"Documents Processed: {len(processing_times)}")
        print()

        # Model info
        model_info = detector.get_model_info()
        print("Model Information:")
        print(f"  Library: {model_info['library']}")
        print(f"  Name: {model_info['name']}")
        print(f"  Version: {model_info['version']}")
        print(f"  Language: {model_info['language']}")
        print()

    # Check if meets >=85% F1 threshold
    print("=" * 60)
    if overall.f1 >= 0.85:
        print(
            f"PASS: {args.library.upper()} meets >=85% F1 threshold ({overall.f1:.4f})"
        )
    else:
        print(
            f"FAIL: {args.library.upper()} does not meet >=85% F1 threshold ({overall.f1:.4f})"
        )
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
