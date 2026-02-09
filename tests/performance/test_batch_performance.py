"""Batch performance tests for NFR2 validation.

Validates that processing 50-document batches completes in <30 minutes.

Story 4.5 - AC2, AC7
"""

from __future__ import annotations

import random
import time
from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database

NFR2_THRESHOLD_SECONDS = 1800.0  # 30 minutes

# French text fragments for generating test documents at runtime.
_PARAGRAPHS = [
    (
        "Le directeur général a présenté les résultats trimestriels lors de la "
        "réunion du comité exécutif. Les chiffres montrent une progression de "
        "huit pour cent par rapport à la même période de l'année précédente. "
        "Cette croissance est principalement portée par les activités commerciales "
        "sur le marché national, avec une contribution notable des filiales "
        "régionales."
    ),
    (
        "L'équipe de recherche et développement a finalisé les essais du nouveau "
        "prototype. Les tests en conditions réelles ont confirmé les performances "
        "attendues, avec une amélioration significative de la fiabilité par rapport "
        "à la version précédente. Le passage en production est prévu pour le "
        "trimestre prochain."
    ),
    (
        "La direction des ressources humaines a lancé un programme de formation "
        "ambitieux destiné à renforcer les compétences numériques de l'ensemble "
        "des collaborateurs. Ce programme comprend des modules en ligne, des "
        "ateliers pratiques et un accompagnement personnalisé pour les managers."
    ),
    (
        "Le département logistique a optimisé les flux de distribution en "
        "rationalisant les entrepôts régionaux et en déployant un nouveau système "
        "de gestion des stocks. Les délais de livraison ont été réduits de trois "
        "jours en moyenne, améliorant significativement la satisfaction client."
    ),
    (
        "Le service juridique a finalisé la revue de conformité réglementaire. "
        "L'audit interne n'a révélé aucune non-conformité majeure. Quelques "
        "ajustements mineurs ont été recommandés et seront mis en œuvre au cours "
        "du prochain trimestre dans le cadre du plan d'amélioration continue."
    ),
]

_FRENCH_FIRST_NAMES = [
    "Marie",
    "Pierre",
    "Sophie",
    "Jean",
    "Claire",
    "François",
    "Nathalie",
    "Thomas",
    "Isabelle",
    "Nicolas",
    "Catherine",
    "Olivier",
    "Sandrine",
    "Thierry",
    "Véronique",
    "Christophe",
    "Élise",
    "Patrick",
    "Audrey",
    "Bruno",
    "Hélène",
    "Antoine",
    "Lucie",
    "Julien",
    "Rachida",
]

_FRENCH_LAST_NAMES = [
    "Dupont",
    "Martin",
    "Bernard",
    "Petit",
    "Moreau",
    "Leroy",
    "Roux",
    "Garnier",
    "Lambert",
    "Faure",
    "Gauthier",
    "Marchand",
    "Perrin",
    "Blanc",
    "Rousseau",
    "Lemaire",
    "Dufour",
    "Vincent",
    "Mercier",
    "Chartier",
    "Lefèvre",
    "Morel",
    "Renard",
    "Delacroix",
    "Beaumont",
]

_LOCATIONS = ["Paris", "Lyon", "Toulouse", "Marseille", "Nantes", "Bordeaux"]


def _generate_document(word_target: int, rng: random.Random) -> str:
    """Generate a realistic French text document of approximately *word_target* words."""
    lines: list[str] = []
    word_count = 0

    # Header
    first = rng.choice(_FRENCH_FIRST_NAMES)
    last = rng.choice(_FRENCH_LAST_NAMES)
    loc = rng.choice(_LOCATIONS)
    header = f"Rapport de {first} {last} — Département de {loc}\n\n"
    lines.append(header)
    word_count += len(header.split())

    while word_count < word_target:
        # Occasionally inject a person name sentence
        if rng.random() < 0.25:
            fn = rng.choice(_FRENCH_FIRST_NAMES)
            ln = rng.choice(_FRENCH_LAST_NAMES)
            sentence = f"M. {fn} {ln} a contribué à ce dossier. "
            lines.append(sentence)
            word_count += len(sentence.split())

        para = rng.choice(_PARAGRAPHS)
        lines.append(para + "\n\n")
        word_count += len(para.split())

    return "".join(lines)


@pytest.fixture(scope="session")
def batch_documents(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    """Generate 50 test documents at runtime (not stored in repo)."""
    docs_dir = tmp_path_factory.mktemp("batch_docs")
    rng = random.Random(42)  # deterministic
    docs: list[Path] = []
    for i in range(50):
        word_target = rng.randint(2000, 5000)
        text = _generate_document(word_target, rng)
        doc_path = docs_dir / f"batch_doc_{i:03d}.txt"
        doc_path.write_text(text, encoding="utf-8")
        docs.append(doc_path)
    return docs


def _run_batch(
    docs: list[Path],
    tmp_path: Path,
    run_id: int,
) -> tuple[float, list[float]]:
    """Process a batch and return (total_seconds, per_doc_times)."""
    db_path = str(tmp_path / f"batch_run_{run_id}.db")
    init_database(db_path, "perf_test_passphrase_12345")
    processor = DocumentProcessor(
        db_path=db_path,
        passphrase="perf_test_passphrase_12345",
        theme="neutral",
    )
    out_dir = tmp_path / f"output_run_{run_id}"
    out_dir.mkdir(exist_ok=True)

    per_doc: list[float] = []
    batch_start = time.perf_counter()
    for doc in docs:
        t0 = time.perf_counter()
        result = processor.process_document(
            str(doc),
            str(out_dir / doc.name),
            skip_validation=True,
        )
        per_doc.append(time.perf_counter() - t0)
        assert result.success, f"Batch doc failed: {doc.name} — {result.error_message}"
    total = time.perf_counter() - batch_start
    return total, per_doc


@pytest.mark.slow
@pytest.mark.benchmark(group="batch")
class TestBatchPerformance:
    """NFR2: Batch processing performance tests."""

    def test_batch_50_documents_under_30min(
        self,
        batch_documents: list[Path],
        tmp_path: Path,
    ) -> None:
        """NFR2: Process 50-document batch in <30 minutes (1 CI iteration)."""
        total, per_doc = _run_batch(batch_documents, tmp_path, run_id=0)

        per_doc_sorted = sorted(per_doc)
        n = len(per_doc_sorted)
        p50 = per_doc_sorted[n // 2]
        p95 = per_doc_sorted[int(n * 0.95)]
        p99 = per_doc_sorted[int(n * 0.99)]
        avg = sum(per_doc) / n

        print(f"\n{'='*60}")
        print("BATCH PERFORMANCE (50 documents, 1 run)")
        print(f"{'='*60}")
        print(f"  Total time: {total:.1f}s ({total/60:.1f} min)")
        print(f"  Avg/doc:    {avg:.2f}s")
        print(f"  p50:        {p50:.2f}s")
        print(f"  p95:        {p95:.2f}s")
        print(f"  p99:        {p99:.2f}s")
        print(f"  Throughput: {n / total * 60:.1f} docs/min")
        print(f"{'='*60}")

        assert total < NFR2_THRESHOLD_SECONDS, (
            f"NFR2 FAIL: Batch took {total:.1f}s ({total/60:.1f} min), "
            f"threshold is {NFR2_THRESHOLD_SECONDS/60:.0f} min"
        )

    def test_batch_throughput_docs_per_minute(
        self,
        batch_documents: list[Path],
        tmp_path: Path,
    ) -> None:
        """Measure and report batch throughput."""
        total, per_doc = _run_batch(batch_documents, tmp_path, run_id=1)
        throughput = len(batch_documents) / total * 60

        print(f"\nThroughput: {throughput:.1f} documents/minute")
        # No hard assertion — informational metric
        assert total > 0
