"""Crash/error rate tests for NFR6 validation.

Validates that unexpected error rate is <10% across 1000+ operations.

Story 4.5 - AC4
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database


def _make_processor(tmp_path: Path, suffix: str) -> DocumentProcessor:
    """Create a DocumentProcessor with its own database."""
    db_path = str(tmp_path / f"stability_{suffix}.db")
    init_database(db_path, "perf_test_passphrase_12345")
    return DocumentProcessor(
        db_path=db_path,
        passphrase="perf_test_passphrase_12345",
        theme="neutral",
    )


def _write_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.slow
class TestStability:
    """NFR6: Error rate < 10% for valid operations across 1000+ ops."""

    def test_error_rate_across_operations(self, tmp_path: Path) -> None:
        """Run 1000+ operations and measure unexpected error rate."""
        total_ops = 0
        expected_errors = 0
        unexpected_errors = 0
        error_details: list[str] = []

        processor = _make_processor(tmp_path, "stability")
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        # --- Category 1: Valid file processing (400 operations) ---
        valid_doc = _write_file(
            tmp_path / "valid.txt",
            "Marie Dupont travaille à Paris avec Pierre Martin. "
            "Sophie Bernard dirige le département de Lyon.\n",
        )
        for i in range(400):
            result = processor.process_document(
                str(valid_doc),
                str(out_dir / f"valid_out_{i}.txt"),
                skip_validation=True,
            )
            total_ops += 1
            if not result.success:
                unexpected_errors += 1
                error_details.append(f"valid_doc[{i}]: {result.error_message}")

        # --- Category 2: Empty file processing (100 operations) ---
        # Empty files are a valid edge case. Both success (0 entities) and
        # graceful failure are acceptable — neither counts as unexpected.
        empty_doc = _write_file(tmp_path / "empty.txt", "")
        for i in range(100):
            result = processor.process_document(
                str(empty_doc),
                str(out_dir / f"empty_out_{i}.txt"),
                skip_validation=True,
            )
            total_ops += 1
            if not result.success:
                expected_errors += 1

        # --- Category 3: Non-existent file processing (100 operations) ---
        for i in range(100):
            result = processor.process_document(
                str(tmp_path / f"nonexistent_{i}.txt"),
                str(out_dir / f"nonexist_out_{i}.txt"),
                skip_validation=True,
            )
            total_ops += 1
            # Expected error: file not found. Shouldn't crash.
            if not result.success:
                expected_errors += 1
            else:
                # If it somehow succeeds on a nonexistent file, that's unexpected
                unexpected_errors += 1
                error_details.append(f"nonexistent[{i}]: succeeded unexpectedly")

        # --- Category 4: Minimal content files (200 operations) ---
        minimal_doc = _write_file(tmp_path / "minimal.txt", "Bonjour.\n")
        for i in range(200):
            result = processor.process_document(
                str(minimal_doc),
                str(out_dir / f"minimal_out_{i}.txt"),
                skip_validation=True,
            )
            total_ops += 1
            if not result.success:
                unexpected_errors += 1
                error_details.append(f"minimal[{i}]: {result.error_message}")

        # --- Category 5: Unicode/special character files (100 operations) ---
        unicode_doc = _write_file(
            tmp_path / "unicode.txt",
            "L'employée Hélène Müller-Straße a rencontré M. François Lécuyer "
            "à Château-Thierry. Les résultats sont encourageants — très positifs.\n",
        )
        for i in range(100):
            result = processor.process_document(
                str(unicode_doc),
                str(out_dir / f"unicode_out_{i}.txt"),
                skip_validation=True,
            )
            total_ops += 1
            if not result.success:
                unexpected_errors += 1
                error_details.append(f"unicode[{i}]: {result.error_message}")

        # --- Category 6: Repeated processing same file (100 operations) ---
        # Tests idempotency under load
        for i in range(100):
            result = processor.process_document(
                str(valid_doc),
                str(out_dir / f"repeat_out_{i}.txt"),
                skip_validation=True,
            )
            total_ops += 1
            if not result.success:
                unexpected_errors += 1
                error_details.append(f"repeat[{i}]: {result.error_message}")

        # --- Results ---
        error_rate = (unexpected_errors / total_ops) * 100

        print(f"\n{'='*60}")
        print(f"STABILITY TEST RESULTS ({total_ops} operations)")
        print(f"{'='*60}")
        print(f"  Total operations:     {total_ops}")
        print(f"  Expected errors:      {expected_errors}")
        print(f"  Unexpected errors:    {unexpected_errors}")
        print(f"  Error rate:           {error_rate:.2f}%")
        print(f"{'='*60}")

        if error_details:
            print("\nError details (first 20):")
            for detail in error_details[:20]:
                print(f"  - {detail}")

        assert total_ops >= 1000, f"Need 1000+ ops, got {total_ops}"
        assert error_rate < 10.0, (
            f"NFR6 FAIL: Error rate {error_rate:.2f}% >= 10% "
            f"({unexpected_errors} unexpected errors / {total_ops} ops)"
        )
