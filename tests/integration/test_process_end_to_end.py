"""Integration tests for end-to-end process command workflow."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app

runner = CliRunner()


def test_process_end_to_end_without_validation(tmp_path: Path) -> None:
    """Test full processing workflow without validation."""
    # Create input file with entities (French text)
    input_file = tmp_path / "input.txt"
    input_file.write_text(
        "Entretien avec Marie Dubois à Paris. Jean Martin et Acme SA étaient également présents.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    # Run CLI command
    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify output file was created
    assert output_file.exists()

    # Verify entities were replaced
    output_content = output_file.read_text()
    assert "Leia Organa" in output_content
    assert "Coruscant" in output_content
    assert "Luke Skywalker" in output_content
    assert "Rebel Alliance" in output_content

    # Verify original entities were removed
    assert "Marie Dubois" not in output_content
    assert "Paris" not in output_content
    assert "Jean Martin" not in output_content
    assert "Acme SA" not in output_content


def test_process_end_to_end_with_default_output_filename(tmp_path: Path) -> None:
    """Test processing with auto-generated output filename."""
    # Create input file (French text)
    input_file = tmp_path / "interview.txt"
    input_file.write_text("Réunion avec Marie Dubois à Paris.", encoding="utf-8")

    # Run CLI command without specifying output file
    result = runner.invoke(app, ["process", str(input_file)])

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify default output file was created
    expected_output = tmp_path / "interview_pseudonymized.txt"
    assert expected_output.exists()

    # Verify content was pseudonymized
    output_content = expected_output.read_text()
    assert "Leia Organa" in output_content
    assert "Coruscant" in output_content
    assert "Marie Dubois" not in output_content


def test_process_end_to_end_with_txt_file(tmp_path: Path) -> None:
    """Test processing .txt file."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("Sophie Laurent travaille chez TechCorp à Lyon.", encoding="utf-8")

    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()

    output_content = output_file.read_text()
    assert "Rey" in output_content
    assert "Galactic Empire" in output_content
    assert "Naboo" in output_content


def test_process_end_to_end_with_md_file(tmp_path: Path) -> None:
    """Test processing .md file."""
    input_file = tmp_path / "test.md"
    input_file.write_text(
        "# Entretien\n\nRéunion avec Pierre Dupont à Marseille.\n\n## Notes\n\nPierre Dupont vient de Paris.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.md"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()

    output_content = output_file.read_text()
    assert "Han Solo" in output_content
    assert "Tatooine" in output_content
    # Markdown formatting preserved
    assert "# Entretien" in output_content
    assert "## Notes" in output_content


def test_process_end_to_end_file_not_found(tmp_path: Path) -> None:
    """Test error handling for non-existent file."""
    input_file = tmp_path / "nonexistent.txt"
    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    # Command should fail with exit code 2 (file doesn't exist - Typer validation)
    assert result.exit_code == 2
    # Output file should not be created
    assert not output_file.exists()


def test_process_end_to_end_invalid_file_format(tmp_path: Path) -> None:
    """Test error handling for invalid file format."""
    input_file = tmp_path / "test.docx"
    input_file.write_text("Test content.")

    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    # Command should fail with exit code 1 (invalid format)
    assert result.exit_code == 1
    assert "Invalid File Format" in result.stdout or "not supported" in result.stdout


def test_process_end_to_end_multiple_occurrences(tmp_path: Path) -> None:
    """Test processing with multiple occurrences of same entity."""
    input_file = tmp_path / "test.txt"
    input_file.write_text(
        "Marie Dubois a rencontré Marie Dubois. Marie Dubois travaille chez Acme SA.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    assert result.exit_code == 0

    output_content = output_file.read_text()
    # All three occurrences should be replaced
    assert output_content.count("Leia Organa") == 3
    assert "Marie Dubois" not in output_content


def test_process_end_to_end_no_entities(tmp_path: Path) -> None:
    """Test processing file with no entities."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("This is a test file without any entities to detect.")

    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    # Command should succeed
    assert result.exit_code == 0
    assert output_file.exists()

    # Content should be unchanged
    output_content = output_file.read_text()
    assert output_content == "This is a test file without any entities to detect."


def test_process_end_to_end_all_entity_types(tmp_path: Path) -> None:
    """Test processing with PERSON, LOCATION, and ORG entities."""
    input_file = tmp_path / "test.txt"
    input_file.write_text(
        "Marie Dubois et Jean Martin de Acme SA se sont rencontrés à Paris. "
        "Sophie Laurent et Pierre Dupont de TechCorp les ont rejoints depuis Lyon et Marseille.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    assert result.exit_code == 0

    output_content = output_file.read_text()

    # Verify all entity types replaced
    # PERSON entities
    assert "Leia Organa" in output_content
    assert "Luke Skywalker" in output_content
    assert "Rey" in output_content
    assert "Han Solo" in output_content

    # ORG entities
    assert "Rebel Alliance" in output_content
    assert "Galactic Empire" in output_content

    # LOCATION entities
    assert "Coruscant" in output_content
    assert "Naboo" in output_content
    assert "Tatooine" in output_content


def test_process_end_to_end_preserves_formatting(tmp_path: Path) -> None:
    """Test processing preserves text formatting."""
    input_file = tmp_path / "test.txt"
    input_file.write_text(
        "Ligne 1: Marie Dubois\n\nLigne 3: Paris\n\n\tIndenté: Acme SA\n",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    assert result.exit_code == 0

    output_content = output_file.read_text()

    # Verify formatting preserved
    assert "\n\n" in output_content  # Double newlines preserved
    assert "\n\t" in output_content  # Tab indentation preserved
    assert output_content.startswith("Ligne 1:")


def test_process_end_to_end_help_command() -> None:
    """Test CLI help display."""
    result = runner.invoke(app, ["process", "--help"])

    assert result.exit_code == 0
    assert "Process a single document" in result.stdout
    assert (
        "validate" in result.stdout
    )  # Check for "validate" without dashes (handles ANSI formatting)
    assert "INPUT_FILE" in result.stdout or "input-file" in result.stdout


def test_process_end_to_end_main_help() -> None:
    """Test main CLI help display."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "gdpr-pseudo" in result.stdout or "GDPR" in result.stdout
    assert "process" in result.stdout


def test_process_end_to_end_version() -> None:
    """Test version display."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_process_end_to_end_sample_document(tmp_path: Path) -> None:
    """Test processing with realistic sample document."""
    # Create realistic French interview text
    input_file = tmp_path / "interview.txt"
    input_file.write_text(
        """Entretien de recherche

Date: 15 janvier 2026
Lieu: Paris

Résumé de l'entretien avec Marie Dubois de Acme SA.

Marie Dubois a expliqué que son équipe basée à Paris collabore
régulièrement avec Jean Martin et Sophie Laurent.

"Notre partenariat avec TechCorp est excellent", dit Marie Dubois.

Notes:
- Marie Dubois: contact principal
- Acme SA: organisation partenaire
""",
        encoding="utf-8",
    )

    output_file = tmp_path / "interview_anonymized.txt"

    result = runner.invoke(app, ["process", str(input_file), str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()

    output_content = output_file.read_text()

    # Verify all sensitive entities replaced
    assert "Marie Dubois" not in output_content
    assert "Jean Martin" not in output_content
    assert "Sophie Laurent" not in output_content
    assert "Acme SA" not in output_content
    assert "TechCorp" not in output_content
    assert "Paris" not in output_content

    # Verify pseudonyms present
    assert "Leia Organa" in output_content
    assert "Luke Skywalker" in output_content
    assert "Rey" in output_content
    assert "Rebel Alliance" in output_content
    assert "Galactic Empire" in output_content
    assert "Coruscant" in output_content

    # Verify structure preserved
    assert "Entretien de recherche" in output_content
    assert "Date:" in output_content
    assert "Notes:" in output_content
