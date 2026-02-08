"""Single-document performance benchmarks for NFR1 validation.

Validates that processing 2-5K word documents completes in <30 seconds
on standard hardware (4-core CPU, 8GB RAM).

Story 4.5 - AC1, AC7
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.data.database import init_database

NFR1_THRESHOLD_SECONDS = 30.0


def _fresh_processor(tmp_path: Path, suffix: str) -> DocumentProcessor:
    """Create a fresh DocumentProcessor with its own database."""
    db_path = str(tmp_path / f"bench_{suffix}.db")
    passphrase = "perf_test_passphrase_12345"
    init_database(db_path, passphrase)
    return DocumentProcessor(
        db_path=db_path,
        passphrase=passphrase,
        theme="neutral",
        model_name="spacy",
    )


def _process_document(
    processor: DocumentProcessor,
    input_path: Path,
    output_dir: Path,
) -> ProcessingResult:
    """Process a single document and return the result."""
    output_path = output_dir / f"{input_path.stem}_pseudonymized.txt"
    return processor.process_document(
        str(input_path),
        str(output_path),
        skip_validation=True,
    )


@pytest.mark.slow
@pytest.mark.benchmark(group="single-document")
class TestSingleDocumentBenchmark:
    """NFR1: Single-document processing performance benchmarks.

    Configuration: warmup_iterations=1, min_rounds=34 per document size.
    3 sizes x 34 rounds = 102 total runs (satisfies AC1 "100 test runs").
    """

    def test_single_document_2k_words(
        self,
        benchmark,  # type: ignore[no-untyped-def]
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """NFR1: Process ~2000-word document in <30 seconds."""
        input_path = performance_test_docs["2k"]
        assert input_path.exists(), f"Test document not found: {input_path}"

        processor = _fresh_processor(tmp_path, "2k")

        benchmark.extra_info["document_words"] = "~2000"
        benchmark.extra_info["entity_density"] = "low"

        # Use pedantic mode for precise control over rounds
        result = benchmark.pedantic(
            _process_document,
            args=(processor, input_path, tmp_path),
            warmup_rounds=1,
            rounds=34,
            iterations=1,
        )

        assert result.success, f"Processing failed: {result.error_message}"
        assert benchmark.stats["mean"] < NFR1_THRESHOLD_SECONDS, (
            f"NFR1 FAIL: Mean processing time {benchmark.stats['mean']:.2f}s "
            f"exceeds {NFR1_THRESHOLD_SECONDS}s threshold"
        )

    def test_single_document_3500_words(
        self,
        benchmark,  # type: ignore[no-untyped-def]
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """NFR1: Process ~3500-word document in <30 seconds."""
        input_path = performance_test_docs["3500"]
        assert input_path.exists(), f"Test document not found: {input_path}"

        processor = _fresh_processor(tmp_path, "3500")

        benchmark.extra_info["document_words"] = "~3500"
        benchmark.extra_info["entity_density"] = "medium"

        result = benchmark.pedantic(
            _process_document,
            args=(processor, input_path, tmp_path),
            warmup_rounds=1,
            rounds=34,
            iterations=1,
        )

        assert result.success, f"Processing failed: {result.error_message}"
        assert benchmark.stats["mean"] < NFR1_THRESHOLD_SECONDS, (
            f"NFR1 FAIL: Mean processing time {benchmark.stats['mean']:.2f}s "
            f"exceeds {NFR1_THRESHOLD_SECONDS}s threshold"
        )

    def test_single_document_5k_words(
        self,
        benchmark,  # type: ignore[no-untyped-def]
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """NFR1: Process ~5000-word document in <30 seconds."""
        input_path = performance_test_docs["5k"]
        assert input_path.exists(), f"Test document not found: {input_path}"

        processor = _fresh_processor(tmp_path, "5k")

        benchmark.extra_info["document_words"] = "~5000"
        benchmark.extra_info["entity_density"] = "high"

        result = benchmark.pedantic(
            _process_document,
            args=(processor, input_path, tmp_path),
            warmup_rounds=1,
            rounds=34,
            iterations=1,
        )

        assert result.success, f"Processing failed: {result.error_message}"
        assert benchmark.stats["mean"] < NFR1_THRESHOLD_SECONDS, (
            f"NFR1 FAIL: Mean processing time {benchmark.stats['mean']:.2f}s "
            f"exceeds {NFR1_THRESHOLD_SECONDS}s threshold"
        )


@pytest.mark.slow
class TestSingleDocumentTimingBreakdown:
    """Record processing time breakdown for performance analysis."""

    def test_processing_time_breakdown(
        self,
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Measure NLP detection, DB ops, file I/O, and replacement time."""
        input_path = performance_test_docs["3500"]
        assert input_path.exists()

        processor = _fresh_processor(tmp_path, "breakdown")
        output_path = tmp_path / "breakdown_output.txt"

        # Process once and capture the overall timing from the result
        start = time.perf_counter()
        result = processor.process_document(
            str(input_path),
            str(output_path),
            skip_validation=True,
        )
        total_time = time.perf_counter() - start

        assert result.success, f"Processing failed: {result.error_message}"

        # Record baseline performance metrics
        print(f"\n{'='*60}")
        print("PROCESSING TIME BREAKDOWN (3500-word document)")
        print(f"{'='*60}")
        print(f"  Total processing time: {total_time:.3f}s")
        print(f"  Result reported time:  {result.processing_time_seconds:.3f}s")
        print(f"  Entities detected:     {result.entities_detected}")
        print(f"  Entities new:          {result.entities_new}")
        print(f"  Entities reused:       {result.entities_reused}")
        print(f"{'='*60}")

        # Baseline documentation
        assert (
            result.processing_time_seconds < NFR1_THRESHOLD_SECONDS
        ), f"NFR1 FAIL: {result.processing_time_seconds:.2f}s > {NFR1_THRESHOLD_SECONDS}s"
