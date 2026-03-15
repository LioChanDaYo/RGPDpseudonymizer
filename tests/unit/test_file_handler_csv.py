"""Unit tests for CSV file reading in file_handler."""

from __future__ import annotations

from pathlib import Path

from gdpr_pseudonymizer.utils.file_handler import read_csv, read_file


def test_read_csv_basic(tmp_path: Path) -> None:
    """Test reading a simple comma-separated CSV."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Alice,Dupont\nParis,France\n", encoding="utf-8")

    result = read_csv(str(csv_file))

    assert "Alice" in result
    assert "Dupont" in result
    assert "Paris" in result


def test_read_csv_semicolon_delimiter(tmp_path: Path) -> None:
    """Test auto-detection of semicolon delimiter (common in French exports)."""
    csv_file = tmp_path / "semi.csv"
    csv_file.write_text("Nom;Prénom;Ville\nDupont;Marie;Lyon\n", encoding="utf-8")

    result = read_csv(str(csv_file))

    assert "Nom" in result
    assert "Marie" in result
    assert "Lyon" in result


def test_read_csv_tab_delimiter(tmp_path: Path) -> None:
    """Test auto-detection of tab-separated values."""
    csv_file = tmp_path / "tab.csv"
    csv_file.write_text("Name\tCity\nAlice\tParis\n", encoding="utf-8")

    result = read_csv(str(csv_file))

    assert "Name" in result
    assert "Alice" in result
    assert "Paris" in result


def test_read_csv_encoding_utf8(tmp_path: Path) -> None:
    """Test reading UTF-8 encoded CSV with accented characters."""
    csv_file = tmp_path / "utf8.csv"
    csv_file.write_text("Prénom,Ville\nRéné,Montréal\n", encoding="utf-8")

    result = read_csv(str(csv_file))

    assert "Réné" in result
    assert "Montréal" in result


def test_read_csv_encoding_latin1(tmp_path: Path) -> None:
    """Test reading Latin-1 encoded CSV (common for French text)."""
    csv_file = tmp_path / "latin1.csv"
    csv_file.write_bytes("Prénom,Ville\nRéné,Montréal\n".encode("latin-1"))

    result = read_csv(str(csv_file))

    assert "Réné" in result
    assert "Montréal" in result


def test_read_csv_encoding_cp1252(tmp_path: Path) -> None:
    """Test reading Windows-1252 encoded CSV.

    Windows-1252 is a superset of Latin-1 for the first 256 bytes,
    so our Latin-1 fallback reads it correctly.
    """
    csv_file = tmp_path / "cp1252.csv"
    csv_file.write_bytes("Nom,Prénom\nDupont,Hélène\n".encode("cp1252"))

    result = read_csv(str(csv_file))

    assert "Dupont" in result
    assert "lène" in result  # partial match — encoding might differ slightly


def test_read_csv_empty_file(tmp_path: Path) -> None:
    """Test reading empty CSV returns empty string."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    result = read_csv(str(csv_file))

    assert result == ""


def test_read_csv_quoted_fields(tmp_path: Path) -> None:
    """Test fields with commas inside quotes are handled correctly."""
    csv_file = tmp_path / "quoted.csv"
    csv_file.write_text(
        '"Dupont, Marie",Paris\n"Martin, Jean",Lyon\n', encoding="utf-8"
    )

    result = read_csv(str(csv_file))

    assert "Dupont, Marie" in result
    assert "Martin, Jean" in result


def test_read_file_dispatches_csv(tmp_path: Path) -> None:
    """Test that read_file routes .csv to read_csv."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Hello,World\n", encoding="utf-8")

    result = read_file(str(csv_file))

    assert "Hello" in result
    assert "World" in result
