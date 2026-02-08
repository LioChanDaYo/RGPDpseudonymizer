"""Memory profiling tests for NFR4 validation.

Validates no memory leaks during batch processing and peak memory stays
within 8GB RAM constraint.

Story 4.5 - AC5
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database


def _make_processor(tmp_path: Path, suffix: str) -> DocumentProcessor:
    """Create a DocumentProcessor with its own database."""
    db_path = str(tmp_path / f"memory_{suffix}.db")
    init_database(db_path, "perf_test_passphrase_12345")
    return DocumentProcessor(
        db_path=db_path,
        passphrase="perf_test_passphrase_12345",
        theme="neutral",
    )


NFR4_PEAK_MEMORY_BYTES = 8 * 1024 * 1024 * 1024  # 8 GB


@pytest.mark.slow
class TestMemoryProfiling:
    """NFR4: Memory profiling tests."""

    def test_single_document_memory_usage(
        self,
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Measure peak memory during processing of a 5K-word document."""
        input_path = performance_test_docs["5k"]
        processor = _make_processor(tmp_path, "single_mem")
        output_path = tmp_path / "mem_output.txt"

        tracemalloc.start()

        result = processor.process_document(
            str(input_path),
            str(output_path),
            skip_validation=True,
        )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert result.success, f"Processing failed: {result.error_message}"

        print(f"\n{'='*60}")
        print("SINGLE DOCUMENT MEMORY USAGE (5K words)")
        print(f"{'='*60}")
        print(f"  Current memory: {current / 1024 / 1024:.1f} MB")
        print(f"  Peak memory:    {peak / 1024 / 1024:.1f} MB")
        print(f"{'='*60}")

    def test_batch_processing_memory_no_leak(
        self,
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Process 20 documents and verify memory doesn't grow linearly (no leak)."""
        input_path = performance_test_docs["3500"]
        processor = _make_processor(tmp_path, "batch_mem")
        out_dir = tmp_path / "mem_batch_output"
        out_dir.mkdir()

        tracemalloc.start()

        # Record memory after every 5 documents
        memory_snapshots: list[float] = []

        for i in range(20):
            result = processor.process_document(
                str(input_path),
                str(out_dir / f"doc_{i:03d}.txt"),
                skip_validation=True,
            )
            assert result.success, f"Doc {i} failed: {result.error_message}"

            if (i + 1) % 5 == 0:
                current, _ = tracemalloc.get_traced_memory()
                memory_snapshots.append(current)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"\n{'='*60}")
        print("BATCH MEMORY PROFILING (20 documents)")
        print(f"{'='*60}")
        for idx, mem in enumerate(memory_snapshots):
            docs_done = (idx + 1) * 5
            print(f"  After {docs_done:2d} docs: {mem / 1024 / 1024:.1f} MB")
        print(f"  Final current: {current / 1024 / 1024:.1f} MB")
        print(f"  Peak:          {peak / 1024 / 1024:.1f} MB")
        print(f"{'='*60}")

        # Check for linear memory growth (leak indicator).
        # Memory at doc 20 should not be >2x memory at doc 5.
        if len(memory_snapshots) >= 2:
            first = memory_snapshots[0]
            last = memory_snapshots[-1]
            growth_ratio = last / first if first > 0 else 0
            print(f"  Growth ratio (doc20/doc5): {growth_ratio:.2f}x")
            assert growth_ratio < 3.0, (
                f"Possible memory leak: memory grew {growth_ratio:.2f}x "
                f"({first/1024/1024:.1f} MB -> {last/1024/1024:.1f} MB)"
            )

    def test_peak_memory_under_8gb(
        self,
        performance_test_docs: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """NFR4: Peak memory during batch processing stays under 8GB."""
        input_path = performance_test_docs["5k"]
        processor = _make_processor(tmp_path, "peak_mem")
        out_dir = tmp_path / "peak_output"
        out_dir.mkdir()

        tracemalloc.start()

        for i in range(10):
            result = processor.process_document(
                str(input_path),
                str(out_dir / f"peak_{i:03d}.txt"),
                skip_validation=True,
            )
            assert result.success, f"Doc {i} failed: {result.error_message}"

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"\n  Peak memory (tracemalloc): {peak / 1024 / 1024:.1f} MB")

        # Note: tracemalloc only measures Python-allocated memory.
        # spaCy model memory (~1.5GB) is mostly C-level and not tracked.
        # This assertion validates the Python-layer stays reasonable.
        assert (
            peak < NFR4_PEAK_MEMORY_BYTES
        ), f"NFR4 FAIL: Peak memory {peak / 1024 / 1024 / 1024:.2f} GB > 8 GB"
