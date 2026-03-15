"""Structured readers for tabular file formats (Excel, CSV).

Preserves cell location metadata for cell-aware NER processing.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from gdpr_pseudonymizer.exceptions import FileProcessingError
from gdpr_pseudonymizer.utils.file_handler import HAS_OPENPYXL
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


def _column_letter(col_index: int) -> str:
    """Convert 1-based column index to Excel-style letter (1=A, 27=AA, etc.)."""
    result = ""
    while col_index > 0:
        col_index, remainder = divmod(col_index - 1, 26)
        result = chr(65 + remainder) + result
    return result


@dataclass
class CellData:
    """Represents a single cell with location metadata.

    Attributes:
        sheet_name: Sheet name (e.g., "Sheet1"); for CSV always "Sheet1"
        row: 1-based row number
        column: 1-based column number
        column_letter: Excel-style column letter (e.g., "A", "B", "AA")
        value: Cell text content
        cell_ref: Full cell reference (e.g., "Sheet1!B3")
    """

    sheet_name: str
    row: int
    column: int
    column_letter: str
    value: str
    cell_ref: str


@dataclass
class TabularDocument:
    """Represents a tabular document with cell-level metadata.

    Attributes:
        cells: List of non-empty cell data objects
        sheet_names: Ordered list of sheet names
        row_count: Total number of rows across all sheets
        column_count: Maximum number of columns across all sheets
        source_format: Original file format ("xlsx" or "csv")
    """

    cells: list[CellData]
    sheet_names: list[str]
    row_count: int
    column_count: int
    source_format: str


def read_excel_structured(file_path: str) -> TabularDocument:
    """Read an Excel file into a TabularDocument with cell location metadata.

    Args:
        file_path: Path to .xlsx file

    Returns:
        TabularDocument with all non-empty cells and their references

    Raises:
        FileProcessingError: If openpyxl not installed, file corrupt, or unreadable
    """
    if not HAS_OPENPYXL:
        raise FileProcessingError(
            "Excel support requires 'openpyxl'. "
            "Install with: pip install gdpr-pseudonymizer[excel]"
        )

    import openpyxl  # type: ignore[import-untyped]

    path = Path(file_path)

    if path.suffix.lower() == ".xls":
        raise FileProcessingError(
            "Binary .xls format is not supported. Please convert to .xlsx."
        )

    try:
        wb = openpyxl.load_workbook(str(path), data_only=True)
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg:
            raise FileProcessingError(
                f"Excel file is password-protected: {file_path}. "
                "Please provide an unprotected file."
            ) from e
        raise FileProcessingError(f"Cannot read Excel file {file_path}: {e}") from e

    try:
        cells: list[CellData] = []
        sheet_names: list[str] = []
        max_row = 0
        max_col = 0

        for sheet in wb.worksheets:
            sheet_names.append(sheet.title)
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        col_letter = _column_letter(cell.column)
                        cell_ref = f"{sheet.title}!{col_letter}{cell.row}"
                        cells.append(
                            CellData(
                                sheet_name=sheet.title,
                                row=cell.row,
                                column=cell.column,
                                column_letter=col_letter,
                                value=str(cell.value),
                                cell_ref=cell_ref,
                            )
                        )
                        if cell.row > max_row:
                            max_row = cell.row
                        if cell.column > max_col:
                            max_col = cell.column

        if len(cells) > 100_000:
            logger.warning(
                "large_excel_file",
                file=file_path,
                non_empty_cells=len(cells),
                message=(
                    "This Excel file contains more than 100,000 non-empty cells. "
                    "Processing may consume significant memory."
                ),
            )

        return TabularDocument(
            cells=cells,
            sheet_names=sheet_names,
            row_count=max_row,
            column_count=max_col,
            source_format="xlsx",
        )
    finally:
        wb.close()


def read_csv_structured(file_path: str) -> TabularDocument:
    """Read a CSV file into a TabularDocument with cell location metadata.

    Auto-detects encoding (UTF-8, then Latin-1 fallback) and delimiter.

    Args:
        file_path: Path to CSV file

    Returns:
        TabularDocument with all non-empty cells and their references

    Raises:
        FileProcessingError: If file cannot be read
    """
    path = Path(file_path)

    try:
        raw_bytes = path.read_bytes()
    except PermissionError as e:
        raise FileProcessingError(f"Permission denied: {file_path}") from e
    except OSError as e:
        raise FileProcessingError(f"Cannot read file {file_path}: {e}") from e

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = raw_bytes.decode("latin-1")

    if not content.strip():
        return TabularDocument(
            cells=[],
            sheet_names=["Sheet1"],
            row_count=0,
            column_count=0,
            source_format="csv",
        )

    # Auto-detect delimiter
    sample = content[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample)
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    cells: list[CellData] = []
    max_col = 0
    row_num = 0

    for row_idx, row in enumerate(reader, start=1):
        row_num = row_idx
        for col_idx, value in enumerate(row, start=1):
            if value.strip():
                col_letter = _column_letter(col_idx)
                cell_ref = f"Sheet1!{col_letter}{row_idx}"
                cells.append(
                    CellData(
                        sheet_name="Sheet1",
                        row=row_idx,
                        column=col_idx,
                        column_letter=col_letter,
                        value=value,
                        cell_ref=cell_ref,
                    )
                )
                if col_idx > max_col:
                    max_col = col_idx

    return TabularDocument(
        cells=cells,
        sheet_names=["Sheet1"],
        row_count=row_num,
        column_count=max_col,
        source_format="csv",
    )
