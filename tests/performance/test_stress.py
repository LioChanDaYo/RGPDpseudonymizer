"""Stress tests for AC6 validation.

Tests behavior under extreme load: 100-document batch, large documents,
and high entity density.

Story 4.5 - AC6
"""

from __future__ import annotations

import random
import time
from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database

# Reuse text generation helpers from batch test module.
from tests.performance.test_batch_performance import (
    _FRENCH_FIRST_NAMES,
    _FRENCH_LAST_NAMES,
    _LOCATIONS,
    _PARAGRAPHS,
    _generate_document,
)


def _make_processor(tmp_path: Path, suffix: str) -> DocumentProcessor:
    db_path = str(tmp_path / f"stress_{suffix}.db")
    init_database(db_path, "perf_test_passphrase_12345")
    return DocumentProcessor(
        db_path=db_path,
        passphrase="perf_test_passphrase_12345",
        theme="neutral",
    )


@pytest.fixture(scope="session")
def stress_100_documents(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    """Generate 100 test documents at runtime (1K-5K words each)."""
    docs_dir = tmp_path_factory.mktemp("stress_docs")
    rng = random.Random(99)
    docs: list[Path] = []
    for i in range(100):
        word_target = rng.randint(1000, 5000)
        text = _generate_document(word_target, rng)
        doc_path = docs_dir / f"stress_doc_{i:03d}.txt"
        doc_path.write_text(text, encoding="utf-8")
        docs.append(doc_path)
    return docs


def _generate_large_document(word_target: int) -> str:
    """Generate a single large document."""
    rng = random.Random(77)
    return _generate_document(word_target, rng)


def _generate_high_entity_document() -> str:
    """Generate a document with 100+ entities."""
    rng = random.Random(55)
    lines: list[str] = [
        "RAPPORT DE SYNTHÈSE — Participants à la conférence\n\n",
    ]
    # Generate 40+ unique PERSON entity mentions
    used_names: list[str] = []
    for i in range(45):
        fn = rng.choice(_FRENCH_FIRST_NAMES)
        ln = rng.choice(_FRENCH_LAST_NAMES)
        name = f"{fn} {ln}"
        used_names.append(name)
        loc = rng.choice(_LOCATIONS)
        lines.append(
            f"M. {name} de {loc} a présenté ses travaux sur les systèmes "
            f"industriels avancés. {name} collabore avec plusieurs instituts "
            f"de recherche basés à {loc}.\n\n"
        )

    # Add more mentions of the same people for duplicate detection
    for name in used_names[:30]:
        loc = rng.choice(_LOCATIONS)
        lines.append(
            f"Lors de la table ronde, {name} a insisté sur l'importance "
            f"de la collaboration entre les équipes de {loc}.\n\n"
        )

    # Add some filler paragraphs
    for _ in range(5):
        lines.append(rng.choice(_PARAGRAPHS) + "\n\n")

    return "".join(lines)


@pytest.mark.slow
class TestStress:
    """AC6: Stress testing — extreme load conditions."""

    def test_100_document_batch_completes_or_fails_gracefully(
        self,
        stress_100_documents: list[Path],
        tmp_path: Path,
    ) -> None:
        """Process 100-document batch: must complete or fail gracefully."""
        processor = _make_processor(tmp_path, "batch100")
        out_dir = tmp_path / "stress_output"
        out_dir.mkdir()

        successes = 0
        failures = 0
        per_doc_times: list[float] = []

        start = time.perf_counter()
        for doc in stress_100_documents:
            t0 = time.perf_counter()
            try:
                result = processor.process_document(
                    str(doc),
                    str(out_dir / doc.name),
                    skip_validation=True,
                )
                per_doc_times.append(time.perf_counter() - t0)
                if result.success:
                    successes += 1
                else:
                    failures += 1
                    # Graceful failure: result.success=False with error_message
                    assert (
                        result.error_message is not None
                    ), f"Failed without error message: {doc.name}"
            except Exception as exc:
                per_doc_times.append(time.perf_counter() - t0)
                failures += 1
                # Record but don't assert — we want to process all docs
                print(f"  Unhandled exception on {doc.name}: {exc}")

        total = time.perf_counter() - start

        print(f"\n{'='*60}")
        print("100-DOCUMENT STRESS TEST")
        print(f"{'='*60}")
        print(f"  Total time:  {total:.1f}s ({total/60:.1f} min)")
        print(f"  Successes:   {successes}")
        print(f"  Failures:    {failures}")
        if per_doc_times:
            print(f"  Avg/doc:     {sum(per_doc_times)/len(per_doc_times):.2f}s")
            print(f"  Max/doc:     {max(per_doc_times):.2f}s")
        print(f"{'='*60}")

        # At least 90% should succeed (graceful failure is OK for some)
        assert (
            successes >= 90
        ), f"Too many failures: {failures}/100 ({failures}% failure rate)"

    def test_large_document_10k_words(self, tmp_path: Path) -> None:
        """Process a single 10K-word document."""
        processor = _make_processor(tmp_path, "large10k")
        text = _generate_large_document(10000)
        input_path = tmp_path / "large_10k.txt"
        input_path.write_text(text, encoding="utf-8")
        output_path = tmp_path / "large_10k_output.txt"

        start = time.perf_counter()
        result = processor.process_document(
            str(input_path),
            str(output_path),
            skip_validation=True,
        )
        elapsed = time.perf_counter() - start

        print(
            f"\n  10K-word document: {elapsed:.2f}s, "
            f"{result.entities_detected} entities"
        )

        assert result.success, f"Processing failed: {result.error_message}"

    def test_high_entity_density_document(self, tmp_path: Path) -> None:
        """Process a document with 100+ entities."""
        processor = _make_processor(tmp_path, "high_density")
        text = _generate_high_entity_document()
        input_path = tmp_path / "high_entity.txt"
        input_path.write_text(text, encoding="utf-8")
        output_path = tmp_path / "high_entity_output.txt"

        start = time.perf_counter()
        result = processor.process_document(
            str(input_path),
            str(output_path),
            skip_validation=True,
        )
        elapsed = time.perf_counter() - start

        print(
            f"\n  High entity density: {elapsed:.2f}s, "
            f"{result.entities_detected} entities detected"
        )

        assert result.success, f"Processing failed: {result.error_message}"
        # Should detect many entities given the dense input
        assert (
            result.entities_detected >= 50
        ), f"Expected 50+ entities, got {result.entities_detected}"
