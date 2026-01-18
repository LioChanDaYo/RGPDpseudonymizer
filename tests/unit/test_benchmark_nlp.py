"""
Unit tests for benchmark_nlp.py

Tests corpus loading, metrics calculation, and aggregation functions.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from benchmark_nlp import (
    Entity,
    MetricsResult,
    aggregate_metrics,
    calculate_metrics,
    load_annotations,
    load_corpus,
    load_document,
)


class TestEntityClass:
    """Tests for Entity dataclass."""

    def test_entity_creation(self):
        """Test creating an Entity object."""
        entity = Entity(text="Marie Dubois", type="PERSON", start=10, end=22)

        assert entity.text == "Marie Dubois"
        assert entity.type == "PERSON"
        assert entity.start == 10
        assert entity.end == 22


class TestMetricsResultClass:
    """Tests for MetricsResult dataclass."""

    def test_metrics_result_creation(self):
        """Test creating a MetricsResult object."""
        metrics = MetricsResult(
            precision=0.85,
            recall=0.90,
            f1=0.874,
            true_positives=85,
            false_positives=15,
            false_negatives=10,
        )

        assert metrics.precision == 0.85
        assert metrics.recall == 0.90
        assert metrics.f1 == 0.874
        assert metrics.true_positives == 85
        assert metrics.false_positives == 15
        assert metrics.false_negatives == 10


class TestLoadDocument:
    """Tests for load_document function."""

    def test_load_simple_document(self):
        """Test loading a simple text document."""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".txt"
        ) as f:
            f.write("Test document content")
            temp_path = Path(f.name)

        try:
            content = load_document(temp_path)
            assert content == "Test document content"
        finally:
            temp_path.unlink()

    def test_load_utf8_document(self):
        """Test loading UTF-8 document with French characters."""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".txt"
        ) as f:
            f.write("François Élisabeth été")
            temp_path = Path(f.name)

        try:
            content = load_document(temp_path)
            assert content == "François Élisabeth été"
        finally:
            temp_path.unlink()


class TestLoadAnnotations:
    """Tests for load_annotations function."""

    def test_load_valid_annotations(self):
        """Test loading valid annotation JSON file."""
        annotation_data = {
            "document_name": "test.txt",
            "entities": [
                {
                    "entity_text": "Marie Dubois",
                    "entity_type": "PERSON",
                    "start_pos": 0,
                    "end_pos": 12,
                },
                {
                    "entity_text": "Paris",
                    "entity_type": "LOCATION",
                    "start_pos": 20,
                    "end_pos": 25,
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".json"
        ) as f:
            json.dump(annotation_data, f)
            temp_path = Path(f.name)

        try:
            entities = load_annotations(temp_path)
            assert len(entities) == 2

            assert entities[0].text == "Marie Dubois"
            assert entities[0].type == "PERSON"
            assert entities[0].start == 0
            assert entities[0].end == 12

            assert entities[1].text == "Paris"
            assert entities[1].type == "LOCATION"
            assert entities[1].start == 20
            assert entities[1].end == 25
        finally:
            temp_path.unlink()

    def test_load_empty_annotations(self):
        """Test loading annotation file with no entities."""
        annotation_data = {"document_name": "test.txt", "entities": []}

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".json"
        ) as f:
            json.dump(annotation_data, f)
            temp_path = Path(f.name)

        try:
            entities = load_annotations(temp_path)
            assert len(entities) == 0
        finally:
            temp_path.unlink()


class TestCalculateMetrics:
    """Tests for calculate_metrics function."""

    def test_perfect_prediction(self):
        """Test metrics when prediction matches ground truth perfectly."""
        predicted = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("Paris", "LOCATION", 10, 15),
        ]
        ground_truth = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("Paris", "LOCATION", 10, 15),
        ]

        metrics = calculate_metrics(predicted, ground_truth, "PERSON")

        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0
        assert metrics.true_positives == 1
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0

    def test_no_predictions(self):
        """Test metrics when no entities are predicted."""
        predicted = []
        ground_truth = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("Jean", "PERSON", 10, 14),
        ]

        metrics = calculate_metrics(predicted, ground_truth, "PERSON")

        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1 == 0.0
        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 2

    def test_partial_prediction(self):
        """Test metrics with partial correct predictions."""
        predicted = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("John", "PERSON", 10, 14),  # False positive
        ]
        ground_truth = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("Jean", "PERSON", 20, 24),  # Missed
        ]

        metrics = calculate_metrics(predicted, ground_truth, "PERSON")

        assert metrics.precision == 0.5  # 1 TP / (1 TP + 1 FP)
        assert metrics.recall == 0.5  # 1 TP / (1 TP + 1 FN)
        assert metrics.f1 == 0.5  # 2 * (0.5 * 0.5) / (0.5 + 0.5)
        assert metrics.true_positives == 1
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 1

    def test_filter_by_entity_type(self):
        """Test that metrics only consider specified entity type."""
        predicted = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("Paris", "LOCATION", 10, 15),
        ]
        ground_truth = [
            Entity("Marie", "PERSON", 0, 5),
            Entity("Paris", "LOCATION", 10, 15),
            Entity("London", "LOCATION", 20, 26),
        ]

        # Test PERSON metrics
        person_metrics = calculate_metrics(predicted, ground_truth, "PERSON")
        assert person_metrics.precision == 1.0
        assert person_metrics.recall == 1.0
        assert person_metrics.true_positives == 1

        # Test LOCATION metrics (missing one)
        location_metrics = calculate_metrics(predicted, ground_truth, "LOCATION")
        assert location_metrics.precision == 1.0
        assert location_metrics.recall == 0.5  # Found 1 of 2
        assert location_metrics.true_positives == 1
        assert location_metrics.false_negatives == 1

    def test_all_false_positives(self):
        """Test metrics when all predictions are wrong."""
        predicted = [
            Entity("Wrong1", "PERSON", 0, 6),
            Entity("Wrong2", "PERSON", 10, 16),
        ]
        ground_truth = [
            Entity("Correct1", "PERSON", 20, 28),
        ]

        metrics = calculate_metrics(predicted, ground_truth, "PERSON")

        assert metrics.precision == 0.0  # 0 TP / (0 TP + 2 FP)
        assert metrics.recall == 0.0  # 0 TP / (0 TP + 1 FN)
        assert metrics.f1 == 0.0
        assert metrics.true_positives == 0
        assert metrics.false_positives == 2
        assert metrics.false_negatives == 1


class TestAggregateMetrics:
    """Tests for aggregate_metrics function."""

    def test_aggregate_single_metric(self):
        """Test aggregating a single MetricsResult."""
        metrics_list = [
            MetricsResult(
                precision=0.8,
                recall=0.9,
                f1=0.85,
                true_positives=80,
                false_positives=20,
                false_negatives=10,
            )
        ]

        aggregated = aggregate_metrics(metrics_list)

        # Should recalculate from TP/FP/FN
        assert aggregated.true_positives == 80
        assert aggregated.false_positives == 20
        assert aggregated.false_negatives == 10
        assert aggregated.precision == 0.8  # 80 / (80 + 20)
        assert aggregated.recall == 80 / 90  # 80 / (80 + 10)

    def test_aggregate_multiple_metrics(self):
        """Test aggregating multiple MetricsResult objects."""
        metrics_list = [
            MetricsResult(
                precision=1.0,
                recall=1.0,
                f1=1.0,
                true_positives=10,
                false_positives=0,
                false_negatives=0,
            ),
            MetricsResult(
                precision=0.5,
                recall=1.0,
                f1=0.667,
                true_positives=5,
                false_positives=5,
                false_negatives=0,
            ),
        ]

        aggregated = aggregate_metrics(metrics_list)

        # Total: TP=15, FP=5, FN=0
        assert aggregated.true_positives == 15
        assert aggregated.false_positives == 5
        assert aggregated.false_negatives == 0
        assert aggregated.precision == 0.75  # 15 / (15 + 5)
        assert aggregated.recall == 1.0  # 15 / (15 + 0)
        assert aggregated.f1 == 2 * (0.75 * 1.0) / (0.75 + 1.0)  # ~0.857

    def test_aggregate_all_zeros(self):
        """Test aggregating metrics with all zeros."""
        metrics_list = [
            MetricsResult(
                precision=0.0,
                recall=0.0,
                f1=0.0,
                true_positives=0,
                false_positives=0,
                false_negatives=10,
            ),
            MetricsResult(
                precision=0.0,
                recall=0.0,
                f1=0.0,
                true_positives=0,
                false_positives=0,
                false_negatives=5,
            ),
        ]

        aggregated = aggregate_metrics(metrics_list)

        assert aggregated.true_positives == 0
        assert aggregated.false_positives == 0
        assert aggregated.false_negatives == 15
        assert aggregated.precision == 0.0
        assert aggregated.recall == 0.0
        assert aggregated.f1 == 0.0


class TestLoadCorpus:
    """Tests for load_corpus function."""

    def test_load_corpus_structure(self):
        """Test loading corpus with proper directory structure."""
        # Create temporary directory structure
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create subdirectories
            (temp_dir / "interview_transcripts").mkdir()
            (temp_dir / "business_documents").mkdir()
            (temp_dir / "annotations").mkdir()

            # Create a test document
            doc_path = temp_dir / "interview_transcripts" / "test_01.txt"
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write("Marie Dubois works in Paris.")

            # Create corresponding annotation
            annotation_data = {
                "document_name": "test_01.txt",
                "entities": [
                    {
                        "entity_text": "Marie Dubois",
                        "entity_type": "PERSON",
                        "start_pos": 0,
                        "end_pos": 12,
                    },
                    {
                        "entity_text": "Paris",
                        "entity_type": "LOCATION",
                        "start_pos": 23,
                        "end_pos": 28,
                    },
                ],
            }
            annotation_path = temp_dir / "annotations" / "test_01.json"
            with open(annotation_path, "w", encoding="utf-8") as f:
                json.dump(annotation_data, f)

            # Load corpus
            corpus = load_corpus(temp_dir)

            assert len(corpus) == 1
            assert "test_01.txt" in corpus

            text, entities = corpus["test_01.txt"]
            assert text == "Marie Dubois works in Paris."
            assert len(entities) == 2
            assert entities[0].text == "Marie Dubois"
            assert entities[1].text == "Paris"

        finally:
            shutil.rmtree(temp_dir)

    def test_load_corpus_missing_annotations(self):
        """Test loading corpus when annotation file is missing."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            (temp_dir / "interview_transcripts").mkdir()
            (temp_dir / "annotations").mkdir()

            # Create document without annotation
            doc_path = temp_dir / "interview_transcripts" / "test_no_annot.txt"
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write("Test content")

            corpus = load_corpus(temp_dir)

            # Should not include document without annotation
            assert len(corpus) == 0

        finally:
            shutil.rmtree(temp_dir)

    def test_load_empty_corpus(self):
        """Test loading corpus from empty directory."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            (temp_dir / "interview_transcripts").mkdir()
            (temp_dir / "business_documents").mkdir()
            (temp_dir / "annotations").mkdir()

            corpus = load_corpus(temp_dir)
            assert len(corpus) == 0

        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Run tests with pytest if available, otherwise print message
    try:
        import pytest

        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not installed. Install with: pip install pytest")
        print("Running basic checks...")

        # Run a few basic tests manually
        test = TestCalculateMetrics()
        test.test_perfect_prediction()
        print("[OK] test_perfect_prediction passed")

        test.test_no_predictions()
        print("[OK] test_no_predictions passed")

        test.test_partial_prediction()
        print("[OK] test_partial_prediction passed")

        print("\nBasic tests passed! Install pytest for full test suite.")
