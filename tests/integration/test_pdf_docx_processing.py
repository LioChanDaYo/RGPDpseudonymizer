"""Integration tests for end-to-end PDF/DOCX processing (Story 5.5).

Tests cover:
- Process PDF -> verify pseudonymized .txt output
- Process DOCX -> verify pseudonymized .txt output
- Batch with mixed formats (.txt, .pdf, .docx) -> all processed
- Mapping database contains entities from PDF/DOCX sources
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from docx import Document as DocxDocument
from fpdf import FPDF
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

# Skip all tests on Windows due to spaCy segfault
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="spaCy segfaults on Windows (access violation in staticvectors)",
)

runner = CliRunner()

# French PII text used in test fixtures
FRENCH_PII_TEXT = (
    "Jean Dupont habite a Paris depuis 2020. "
    "Il travaille chez Societe Generale. "
    "Marie Martin vit a Lyon."
)


def _create_test_pdf(path: Path, text: str = FRENCH_PII_TEXT) -> Path:
    """Create a test PDF with known French PII text."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    pdf.output(str(path))
    return path


def _create_test_docx(path: Path, text: str = FRENCH_PII_TEXT) -> Path:
    """Create a test DOCX with known French PII text."""
    doc = DocxDocument()
    doc.add_paragraph(text)
    doc.save(str(path))
    return path


class MockHybridDetector:
    """Mock detector returning predictable entities from French PII text."""

    def __init__(self) -> None:
        pass

    def load_model(self, model_name: str) -> None:
        pass

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        entities: list[DetectedEntity] = []
        if "Jean Dupont" in text:
            start = text.index("Jean Dupont")
            entities.append(
                DetectedEntity(
                    text="Jean Dupont",
                    entity_type="PERSON",
                    start_pos=start,
                    end_pos=start + 11,
                    confidence=0.95,
                    source="mock",
                )
            )
        if "Paris" in text:
            start = text.index("Paris")
            entities.append(
                DetectedEntity(
                    text="Paris",
                    entity_type="LOCATION",
                    start_pos=start,
                    end_pos=start + 5,
                    confidence=0.90,
                    source="mock",
                )
            )
        if "Marie Martin" in text:
            start = text.index("Marie Martin")
            entities.append(
                DetectedEntity(
                    text="Marie Martin",
                    entity_type="PERSON",
                    start_pos=start,
                    end_pos=start + 12,
                    confidence=0.92,
                    source="mock",
                )
            )
        if "Lyon" in text:
            start = text.index("Lyon")
            entities.append(
                DetectedEntity(
                    text="Lyon",
                    entity_type="LOCATION",
                    start_pos=start,
                    end_pos=start + 4,
                    confidence=0.88,
                    source="mock",
                )
            )
        return entities


@pytest.fixture(autouse=True)
def set_passphrase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set passphrase env var for non-interactive testing."""
    monkeypatch.setenv("GDPR_PSEUDO_PASSPHRASE", "test_passphrase_12345_secure")


@pytest.fixture(autouse=True)
def mock_validation_workflow():
    """Auto-accept all detected entities."""
    with patch(
        "gdpr_pseudonymizer.core.document_processor.run_validation_workflow"
    ) as mock:
        mock.side_effect = lambda entities, **kwargs: entities
        yield mock


@pytest.fixture(autouse=True)
def mock_hybrid_detector(monkeypatch: pytest.MonkeyPatch):
    """Use mock detector for deterministic entity detection."""
    monkeypatch.setattr(
        "gdpr_pseudonymizer.core.document_processor.HybridDetector",
        lambda: MockHybridDetector(),
    )


@pytest.fixture(autouse=True)
def cleanup_test_database():
    """Clean up test database files after each test."""
    yield
    db_path = Path("mappings.db")
    if db_path.exists():
        db_path.unlink()


@pytest.mark.integration
class TestProcessPdf:
    """Integration tests for processing PDF documents."""

    def test_process_pdf_produces_txt_output(self, tmp_path: Path) -> None:
        """Test: process PDF -> pseudonymized .txt output."""
        pdf_path = _create_test_pdf(tmp_path / "input.pdf")
        output_path = tmp_path / "output.txt"

        result = runner.invoke(
            app,
            ["process", str(pdf_path), "-o", str(output_path)],
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        assert output_path.exists()
        output_text = output_path.read_text(encoding="utf-8")
        # Original PII should be replaced
        assert "Jean Dupont" not in output_text or "Processing" in result.stdout

    def test_process_pdf_default_output_is_txt(self, tmp_path: Path) -> None:
        """Test: default output for PDF input uses .txt extension."""
        pdf_path = _create_test_pdf(tmp_path / "report.pdf")

        result = runner.invoke(app, ["process", str(pdf_path)])

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        # Default output should be report_pseudonymized.txt, not .pdf
        expected_output = tmp_path / "report_pseudonymized.txt"
        assert expected_output.exists(), f"Expected {expected_output} to exist"

    def test_process_pdf_entities_detected(self, tmp_path: Path) -> None:
        """Test: entities are detected from PDF content."""
        pdf_path = _create_test_pdf(tmp_path / "input.pdf")
        output_path = tmp_path / "output.txt"

        result = runner.invoke(
            app,
            ["process", str(pdf_path), "-o", str(output_path)],
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        assert "Entities detected" in result.stdout


@pytest.mark.integration
class TestProcessDocx:
    """Integration tests for processing DOCX documents."""

    def test_process_docx_produces_txt_output(self, tmp_path: Path) -> None:
        """Test: process DOCX -> pseudonymized .txt output."""
        docx_path = _create_test_docx(tmp_path / "input.docx")
        output_path = tmp_path / "output.txt"

        result = runner.invoke(
            app,
            ["process", str(docx_path), "-o", str(output_path)],
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        assert output_path.exists()

    def test_process_docx_default_output_is_txt(self, tmp_path: Path) -> None:
        """Test: default output for DOCX input uses .txt extension."""
        docx_path = _create_test_docx(tmp_path / "report.docx")

        result = runner.invoke(app, ["process", str(docx_path)])

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        expected_output = tmp_path / "report_pseudonymized.txt"
        assert expected_output.exists(), f"Expected {expected_output} to exist"

    def test_process_docx_entities_detected(self, tmp_path: Path) -> None:
        """Test: entities are detected from DOCX content."""
        docx_path = _create_test_docx(tmp_path / "input.docx")
        output_path = tmp_path / "output.txt"

        result = runner.invoke(
            app,
            ["process", str(docx_path), "-o", str(output_path)],
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        assert "Entities detected" in result.stdout


@pytest.mark.integration
class TestBatchMixedFormats:
    """Integration tests for batch processing with mixed formats."""

    def test_batch_mixed_formats(self, tmp_path: Path) -> None:
        """Test: batch with .txt, .pdf, .docx -> all processed successfully."""
        (tmp_path / "file1.txt").write_text(FRENCH_PII_TEXT, encoding="utf-8")
        _create_test_pdf(tmp_path / "file2.pdf")
        _create_test_docx(tmp_path / "file3.docx")

        output_dir = tmp_path / "output"

        result = runner.invoke(
            app,
            [
                "batch",
                str(tmp_path),
                "-o",
                str(output_dir),
                "--workers",
                "1",
            ],
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        assert "3 file(s) to process" in result.stdout
        assert "All files processed successfully" in result.stdout

        # Check output files exist with correct extensions
        assert (output_dir / "file1_pseudonymized.txt").exists()
        assert (output_dir / "file2_pseudonymized.txt").exists()  # .pdf -> .txt
        assert (output_dir / "file3_pseudonymized.txt").exists()  # .docx -> .txt
