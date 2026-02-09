"""Fixtures for performance and stability tests.

Provides session-scoped fixtures for DocumentProcessor, test documents,
and temporary database/output directories.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.utils.logger import configure_logging

# Suppress structlog output to WARNING to avoid Windows cp1252 encoding errors
# with French diacritics in debug output (same fix as accuracy conftest).
configure_logging("WARNING")

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "performance"


@pytest.fixture(scope="session")
def performance_test_docs() -> dict[str, Path]:
    """Paths to the three performance test documents."""
    return {
        "2k": FIXTURES_DIR / "sample_2000_words.txt",
        "3500": FIXTURES_DIR / "sample_3500_words.txt",
        "5k": FIXTURES_DIR / "sample_5000_words.txt",
    }


@pytest.fixture()
def test_db(tmp_path: Path) -> str:
    """Create and initialise a temporary test database."""
    db_path = str(tmp_path / "perf_test.db")
    init_database(db_path, "perf_test_passphrase_12345")
    return db_path


@pytest.fixture()
def processor(test_db: str) -> DocumentProcessor:
    """Initialised DocumentProcessor with test database."""
    return DocumentProcessor(
        db_path=test_db,
        passphrase="perf_test_passphrase_12345",
        theme="neutral",
        model_name="spacy",
    )


@pytest.fixture(autouse=True)
def mock_validation_workflow():
    """Auto-accept all entities (skip interactive validation prompts)."""
    with patch(
        "gdpr_pseudonymizer.core.document_processor.run_validation_workflow"
    ) as mock:
        mock.side_effect = lambda entities, **kwargs: entities
        yield mock
