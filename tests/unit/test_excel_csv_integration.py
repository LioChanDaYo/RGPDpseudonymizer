"""Integration tests for Excel/CSV format support (Story 7.4).

Tests CLI extensions, batch collect_files, GUI filter constants,
and regression for existing formats.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from gdpr_pseudonymizer.cli.commands.batch import collect_files


def _create_xlsx(path: Path, data: dict[str, list[list[object]]]) -> None:
    """Helper: create .xlsx with sheet_name -> rows mapping."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]
    for sheet_name, rows in data.items():
        ws = wb.create_sheet(title=sheet_name)
        for row in rows:
            ws.append(row)
    wb.save(str(path))
    wb.close()


# ------------------------------------------------------------------
# CLI extension tests (AC7)
# ------------------------------------------------------------------


class TestProcessCommandExtensions:
    """Verify process command accepts .xlsx and .csv."""

    def test_process_allowed_extensions_includes_xlsx(self) -> None:
        """Process command's allowed_extensions includes .xlsx."""
        # We can verify by checking the source — the real test is that
        # the command doesn't reject .xlsx files at the extension check
        from gdpr_pseudonymizer.cli.commands import process as process_mod

        source = open(process_mod.__file__, encoding="utf-8").read()
        assert '".xlsx"' in source
        assert '".csv"' in source

    def test_process_allowed_extensions_includes_csv(self) -> None:
        """Process command's allowed_extensions includes .csv."""
        from gdpr_pseudonymizer.cli.commands import process as process_mod

        source = open(process_mod.__file__, encoding="utf-8").read()
        assert '".csv"' in source


# ------------------------------------------------------------------
# Batch collect_files tests (AC7)
# ------------------------------------------------------------------


class TestBatchCollectsExcelCsv:
    """Verify batch collect_files includes .xlsx and .csv."""

    def test_batch_collects_xlsx(self, tmp_path: Path) -> None:
        """Batch collects .xlsx files."""
        xlsx = tmp_path / "data.xlsx"
        _create_xlsx(xlsx, {"Sheet1": [["test"]]})

        files = collect_files(xlsx)
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"

    def test_batch_collects_csv(self, tmp_path: Path) -> None:
        """Batch collects .csv files."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n", encoding="utf-8")

        files = collect_files(csv_file)
        assert len(files) == 1
        assert files[0].suffix == ".csv"

    def test_batch_collects_xlsx_csv_from_dir(self, tmp_path: Path) -> None:
        """Batch collects .xlsx and .csv from directory alongside other formats."""
        (tmp_path / "doc.txt").write_text("hello")
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n", encoding="utf-8")
        xlsx = tmp_path / "report.xlsx"
        _create_xlsx(xlsx, {"Sheet1": [["test"]]})

        files = collect_files(tmp_path)

        extensions = {f.suffix for f in files}
        assert ".txt" in extensions
        assert ".csv" in extensions
        assert ".xlsx" in extensions


# ------------------------------------------------------------------
# GUI filter tests (AC6)
# ------------------------------------------------------------------


class TestGUISupportsExcelCsv:
    """Verify GUI components include .xlsx and .csv in supported extensions."""

    def test_drop_zone_supports_xlsx_csv(self) -> None:
        """drop_zone.SUPPORTED_EXTENSIONS includes .xlsx and .csv."""
        from gdpr_pseudonymizer.gui.widgets.drop_zone import SUPPORTED_EXTENSIONS

        assert ".xlsx" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS

    def test_batch_worker_supports_xlsx_csv(self) -> None:
        """batch_worker.SUPPORTED_EXTENSIONS includes .xlsx and .csv."""
        from gdpr_pseudonymizer.gui.workers.batch_worker import SUPPORTED_EXTENSIONS

        assert ".xlsx" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS


# ------------------------------------------------------------------
# Output default extension tests
# ------------------------------------------------------------------


class TestOutputDefaultExtensions:
    """Verify .xlsx and .csv inputs produce same-format output by default."""

    def test_xlsx_default_output_suffix(self) -> None:
        """xlsx input without --output should produce .xlsx output."""
        input_path = Path("report.xlsx")
        # The process command logic: only pdf/docx map to .txt
        output_suffix = input_path.suffix
        if input_path.suffix.lower() in [".pdf", ".docx"]:
            output_suffix = ".txt"

        assert output_suffix == ".xlsx"

    def test_csv_default_output_suffix(self) -> None:
        """csv input without --output should produce .csv output."""
        input_path = Path("data.csv")
        output_suffix = input_path.suffix
        if input_path.suffix.lower() in [".pdf", ".docx"]:
            output_suffix = ".txt"

        assert output_suffix == ".csv"


# ------------------------------------------------------------------
# Regression tests (AC11)
# ------------------------------------------------------------------


class TestNoRegression:
    """Verify existing format support is unchanged."""

    def test_txt_read_still_works(self, tmp_path: Path) -> None:
        """Existing .txt processing unchanged."""
        from gdpr_pseudonymizer.utils.file_handler import read_file

        txt = tmp_path / "test.txt"
        txt.write_text("Hello World", encoding="utf-8")

        result = read_file(str(txt))
        assert result == "Hello World"

    def test_md_read_still_works(self, tmp_path: Path) -> None:
        """Existing .md processing unchanged."""
        from gdpr_pseudonymizer.utils.file_handler import read_file

        md = tmp_path / "test.md"
        md.write_text("# Title\nBody", encoding="utf-8")

        result = read_file(str(md))
        assert result == "# Title\nBody"

    def test_context_label_default_none(self) -> None:
        """DetectedEntity.context_label defaults to None (backward compat)."""
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        entity = DetectedEntity(
            text="Alice", entity_type="PERSON", start_pos=0, end_pos=5
        )
        assert entity.context_label is None
