"""Batch Processing Scalability Spike - Story 2.7

This script validates batch processing architecture using multiprocessing
before Epic 3 implementation. Tests parallelism, mapping table consistency,
and identifies architectural issues.

Design:
- Process-based parallelism (multiprocessing.Pool) for spaCy thread-safety
- Worker pool size: min(cpu_count(), 4) to balance performance vs memory
- Each worker loads separate spaCy model and database connection
- Measures sequential vs parallel performance

Usage:
    poetry run python scripts/batch_processing_spike.py

Expected Results:
- Speedup: 2-3x with 4 workers (not linear due to SQLite write serialization)
- Memory: ~2GB (4 workers × 500MB spaCy model)
- Mapping consistency: Same entity gets same pseudonym across documents
"""

import os
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database


def process_single_document(args: tuple[str, str, str, str, str]) -> dict[str, Any]:
    """Worker function: Process single document using DocumentProcessor.

    Args:
        args: Tuple of (input_path, output_path, db_path, passphrase, theme)

    Returns:
        Dictionary with processing results:
        - success: bool
        - doc: input document path
        - result: ProcessingResult if successful
        - error: error message if failed
    """
    input_path, output_path, db_path, passphrase, theme = args

    try:
        # Each worker initializes its own DocumentProcessor
        # (separate SQLite connection, spaCy model load, encryption service)
        processor = DocumentProcessor(
            db_path=db_path, passphrase=passphrase, theme=theme, model_name="spacy"
        )

        # Process document
        result = processor.process_document(input_path, output_path)

        return {
            "success": True,
            "doc": input_path,
            "result": result,
            "entities_detected": result.entities_detected,
            "entities_new": result.entities_new,
            "entities_reused": result.entities_reused,
            "processing_time": result.processing_time_seconds,
        }
    except Exception as e:
        return {"success": False, "doc": input_path, "error": str(e)}


def batch_process_sequential(
    document_paths: list[str],
    output_dir: str,
    db_path: str,
    passphrase: str,
    theme: str = "neutral",
) -> tuple[list[dict[str, Any]], float]:
    """Process documents sequentially (baseline for comparison).

    Args:
        document_paths: List of input document paths
        output_dir: Output directory for pseudonymized documents
        db_path: Path to SQLite database
        passphrase: Encryption passphrase
        theme: Pseudonym library theme

    Returns:
        Tuple of (results list, total processing time)
    """
    print("\n=== Sequential Processing (Baseline) ===")
    print(f"Processing {len(document_paths)} documents one-by-one...")

    # Prepare arguments
    args_list = [
        (
            doc_path,
            str(
                Path(output_dir) / f"{Path(doc_path).stem}_sequential_pseudonymized.txt"
            ),
            db_path,
            passphrase,
            theme,
        )
        for doc_path in document_paths
    ]

    # Process documents sequentially
    start_time = time.time()
    results = []
    for i, args in enumerate(args_list, 1):
        print(f"  [{i}/{len(args_list)}] Processing {Path(args[0]).name}...")
        result = process_single_document(args)
        results.append(result)
        if result["success"]:
            print(
                f"    [OK] Success: {result['entities_detected']} entities "
                f"({result['entities_new']} new, {result['entities_reused']} reused) "
                f"in {result['processing_time']:.2f}s"
            )
        else:
            print(f"    [FAIL] Failed: {result['error']}")

    elapsed_time = time.time() - start_time

    # Summary
    successful = sum(1 for r in results if r["success"])
    total_entities = sum(r.get("entities_detected", 0) for r in results if r["success"])
    total_new = sum(r.get("entities_new", 0) for r in results if r["success"])
    total_reused = sum(r.get("entities_reused", 0) for r in results if r["success"])

    print("\nSequential Results:")
    print(f"  Successful: {successful}/{len(results)}")
    print(
        f"  Total entities: {total_entities} ({total_new} new, {total_reused} reused)"
    )
    print(f"  Total time: {elapsed_time:.2f}s")
    print(f"  Avg per doc: {elapsed_time / len(results):.2f}s")

    return results, elapsed_time


def batch_process_parallel(
    document_paths: list[str],
    output_dir: str,
    db_path: str,
    passphrase: str,
    theme: str = "neutral",
    num_workers: int | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """Process documents in parallel using multiprocessing pool.

    Args:
        document_paths: List of input document paths
        output_dir: Output directory for pseudonymized documents
        db_path: Path to SQLite database
        passphrase: Encryption passphrase
        theme: Pseudonym library theme
        num_workers: Number of worker processes (default: min(cpu_count(), 4))

    Returns:
        Tuple of (results list, total processing time)
    """
    if num_workers is None:
        num_workers = min(cpu_count(), 4)

    print(f"\n=== Parallel Processing ({num_workers} workers) ===")
    print(f"Processing {len(document_paths)} documents in parallel...")
    print(f"Worker count: {num_workers} (CPU count: {cpu_count()})")

    # Prepare arguments
    args_list = [
        (
            doc_path,
            str(Path(output_dir) / f"{Path(doc_path).stem}_parallel_pseudonymized.txt"),
            db_path,
            passphrase,
            theme,
        )
        for doc_path in document_paths
    ]

    # Process in parallel
    start_time = time.time()
    with Pool(processes=num_workers) as pool:
        results = pool.map(process_single_document, args_list)
    elapsed_time = time.time() - start_time

    # Print individual results
    print("\nIndividual Results:")
    for i, result in enumerate(results, 1):
        doc_name = Path(result["doc"]).name
        if result["success"]:
            print(
                f"  [{i}] {doc_name}: {result['entities_detected']} entities "
                f"({result['entities_new']} new, {result['entities_reused']} reused) "
                f"in {result['processing_time']:.2f}s"
            )
        else:
            print(f"  [{i}] {doc_name}: FAILED - {result['error']}")

    # Summary
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    total_entities = sum(r.get("entities_detected", 0) for r in results if r["success"])
    total_new = sum(r.get("entities_new", 0) for r in results if r["success"])
    total_reused = sum(r.get("entities_reused", 0) for r in results if r["success"])

    print("\nParallel Results:")
    print(f"  Successful: {successful}/{len(results)}")
    if failed > 0:
        print(f"  Failed: {failed}")
    print(
        f"  Total entities: {total_entities} ({total_new} new, {total_reused} reused)"
    )
    print(f"  Total time: {elapsed_time:.2f}s")
    print(f"  Avg per doc: {elapsed_time / len(results):.2f}s")
    print(f"  Throughput: {len(results) / elapsed_time:.2f} docs/sec")

    return results, elapsed_time


def compare_performance(
    sequential_time: float, parallel_time: float, num_workers: int
) -> None:
    """Print performance comparison between sequential and parallel processing.

    Args:
        sequential_time: Sequential processing time in seconds
        parallel_time: Parallel processing time in seconds
        num_workers: Number of parallel workers
    """
    speedup = sequential_time / parallel_time
    efficiency = speedup / num_workers * 100

    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    print(f"Sequential time:  {sequential_time:.2f}s")
    print(f"Parallel time:    {parallel_time:.2f}s ({num_workers} workers)")
    print(f"Speedup:          {speedup:.2f}x")
    print(f"Parallel efficiency: {efficiency:.1f}%")
    print()

    if speedup >= 2.0:
        print("[OK] Target achieved: Speedup >= 2x")
    elif speedup >= 1.5:
        print("[WARN] Moderate speedup: 1.5x-2x (acceptable but below target)")
    else:
        print("[FAIL] Low speedup: < 1.5x (investigate bottlenecks)")

    print()
    print("Expected speedup: 2-3x (not linear due to SQLite write serialization)")
    print("=" * 60)


def main() -> None:
    """Main spike execution: test sequential vs parallel batch processing."""
    print("=" * 60)
    print("BATCH PROCESSING SCALABILITY SPIKE - STORY 2.7")
    print("=" * 60)

    # Configuration
    test_corpus_dir = Path("tests/fixtures/batch_spike")
    output_dir = Path("tests/fixtures/batch_spike/output")
    db_path = "tests/fixtures/batch_spike/spike_test.db"
    passphrase = "spike_test_passphrase_2024"
    theme = "neutral"

    # Validate test corpus exists
    if not test_corpus_dir.exists():
        print(f"\n[ERROR] Test corpus directory not found: {test_corpus_dir}")
        print("  Run Task 2 to create test documents first.")
        return

    # Find all test documents
    document_paths = sorted(
        [str(p) for p in test_corpus_dir.glob("doc_*.txt") if p.is_file()]
    )

    if not document_paths:
        print(f"\n[ERROR] No test documents found in {test_corpus_dir}")
        print("  Expected files: doc_001.txt, doc_002.txt, ..., doc_010.txt")
        return

    print("\nConfiguration:")
    print(f"  Test corpus: {test_corpus_dir}")
    print(f"  Documents: {len(document_paths)}")
    print(f"  Database: {db_path}")
    print(f"  Theme: {theme}")
    print(f"  CPU count: {cpu_count()}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean previous database to ensure fresh test
    if os.path.exists(db_path):
        print(f"\n  Removing previous test database: {db_path}")
        os.remove(db_path)
    # Also remove WAL and SHM files if they exist
    for ext in ["-wal", "-shm"]:
        wal_file = db_path + ext
        if os.path.exists(wal_file):
            os.remove(wal_file)

    # Initialize fresh database
    print(f"  Initializing database: {db_path}")
    init_database(db_path, passphrase)

    # ========================================
    # Test 1: Sequential Processing (Baseline)
    # ========================================
    seq_results, seq_time = batch_process_sequential(
        document_paths, str(output_dir), db_path, passphrase, theme
    )

    # ========================================
    # Test 2: Parallel Processing
    # ========================================
    # Clean database again for parallel test
    if os.path.exists(db_path):
        os.remove(db_path)
    for ext in ["-wal", "-shm"]:
        wal_file = db_path + ext
        if os.path.exists(wal_file):
            os.remove(wal_file)

    # Initialize fresh database for parallel test
    print(f"\n  Initializing database for parallel test: {db_path}")
    init_database(db_path, passphrase)

    parallel_results, parallel_time = batch_process_parallel(
        document_paths, str(output_dir), db_path, passphrase, theme
    )

    # ========================================
    # Test 3: Performance Comparison
    # ========================================
    num_workers = min(cpu_count(), 4)
    compare_performance(seq_time, parallel_time, num_workers)

    # ========================================
    # Next Steps
    # ========================================
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("Task 3: Verify mapping table consistency")
    print("  - Query database for duplicate entity mappings")
    print("  - Verify same entity gets same pseudonym across documents")
    print()
    print("Task 4: Detailed performance measurement")
    print("  - Test with different worker counts (1, 2, 4, cpu_count)")
    print("  - Measure per-document breakdown (NLP, DB, I/O time)")
    print()
    print("Task 5: Identify architectural issues")
    print("  - Monitor memory usage (spaCy model duplication)")
    print("  - Check database lock contention (SQLite WAL mode)")
    print("  - Measure worker process spawn overhead")
    print("=" * 60)


if __name__ == "__main__":
    main()
