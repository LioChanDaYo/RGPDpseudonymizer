"""Unit tests for tabular_reader — structured Excel/CSV reading."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from gdpr_pseudonymizer.utils.tabular_reader import (
    read_csv_structured,
    read_excel_structured,
)


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


def test_read_excel_structured_cell_refs(tmp_path: Path) -> None:
    """Verify CellData has correct sheet_name, row, column, cell_ref."""
    xlsx = tmp_path / "test.xlsx"
    _create_xlsx(xlsx, {"Personnel": [["Alice", "Dupont"], ["Jean", "Martin"]]})

    doc = read_excel_structured(str(xlsx))

    assert len(doc.cells) == 4
    assert doc.sheet_names == ["Personnel"]

    # First cell: Personnel!A1
    c = doc.cells[0]
    assert c.sheet_name == "Personnel"
    assert c.row == 1
    assert c.column == 1
    assert c.column_letter == "A"
    assert c.value == "Alice"
    assert c.cell_ref == "Personnel!A1"

    # Second cell: Personnel!B1
    c = doc.cells[1]
    assert c.cell_ref == "Personnel!B1"
    assert c.value == "Dupont"

    # Third cell: Personnel!A2
    c = doc.cells[2]
    assert c.cell_ref == "Personnel!A2"
    assert c.value == "Jean"


def test_read_csv_structured_cell_refs(tmp_path: Path) -> None:
    """Verify CSV cells get Sheet1 as sheet_name."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Alice,Dupont\nJean,Martin\n", encoding="utf-8")

    doc = read_csv_structured(str(csv_file))

    assert len(doc.cells) == 4
    assert doc.sheet_names == ["Sheet1"]

    c = doc.cells[0]
    assert c.sheet_name == "Sheet1"
    assert c.cell_ref == "Sheet1!A1"
    assert c.value == "Alice"

    c = doc.cells[1]
    assert c.cell_ref == "Sheet1!B1"
    assert c.value == "Dupont"


def test_tabular_document_metadata(tmp_path: Path) -> None:
    """Verify row_count, column_count, source_format."""
    xlsx = tmp_path / "meta.xlsx"
    _create_xlsx(xlsx, {"Sheet1": [["A", "B", "C"], ["D", "E", "F"]]})

    doc = read_excel_structured(str(xlsx))

    assert doc.row_count == 2
    assert doc.column_count == 3
    assert doc.source_format == "xlsx"


def test_read_csv_structured_metadata(tmp_path: Path) -> None:
    """Verify CSV metadata."""
    csv_file = tmp_path / "meta.csv"
    csv_file.write_text("a,b,c\nd,e,f\ng,h,i\n", encoding="utf-8")

    doc = read_csv_structured(str(csv_file))

    assert doc.row_count == 3
    assert doc.column_count == 3
    assert doc.source_format == "csv"


def test_read_csv_structured_empty(tmp_path: Path) -> None:
    """Verify empty CSV returns empty TabularDocument."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    doc = read_csv_structured(str(csv_file))

    assert doc.cells == []
    assert doc.row_count == 0
    assert doc.column_count == 0
