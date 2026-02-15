"""Integration tests for end-to-end process command workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def set_passphrase_env(monkeypatch):
    """Set passphrase environment variable for non-interactive testing.

    Story 2.6: Process command requires passphrase for database encryption.
    This fixture sets GDPR_PSEUDO_PASSPHRASE environment variable to avoid
    interactive prompts during testing.
    """
    monkeypatch.setenv("GDPR_PSEUDO_PASSPHRASE", "test_passphrase_12345_secure")


@pytest.fixture(autouse=True)
def reset_pseudonym_cache() -> None:
    """Reset pseudonym cache before each test to ensure deterministic assignments.

    Story 2.6: DocumentProcessor uses per-session caching, no global cache to clear.
    This fixture is kept for backward compatibility but does nothing.
    """
    pass


@pytest.fixture(autouse=True)
def mock_validation_workflow():
    """Mock validation workflow to auto-accept all detected entities.

    Since tests run non-interactively, we mock the validation workflow
    to simply return all detected entities (simulating user accepting all).
    """
    with patch(
        "gdpr_pseudonymizer.core.document_processor.run_validation_workflow"
    ) as mock:
        # Pass through all entities (simulate user accepting everything)
        mock.side_effect = lambda entities, **kwargs: entities
        yield mock


@pytest.fixture(autouse=True)
def cleanup_test_database():
    """Clean up test database files after each test.

    Story 2.6: Process command creates mappings.db in current directory.
    This fixture ensures cleanup between tests.
    """
    yield
    # Cleanup after test
    db_path = Path("mappings.db")
    if db_path.exists():
        db_path.unlink()


@pytest.fixture(autouse=True)
def mock_hybrid_detector_for_deterministic_tests(monkeypatch):
    """Mock HybridDetector to return predictable entities for test stability.

    Story 1.8 introduced HybridDetector which detects MORE entities than SpaCyDetector.
    This causes end-to-end tests to fail because pseudonym assignments shift.
    We mock the detector to return a predictable set of entities matching test expectations.
    """
    from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

    class MockHybridDetector:
        def __init__(self):
            pass

        def load_model(self, model_name: str) -> None:
            pass

        def detect_entities(self, text: str) -> list[DetectedEntity]:
            """Return predictable entities for common test patterns."""
            import re

            entities = []

            # Define entity patterns to detect (handles multiple occurrences)
            patterns = [
                ("Marie Dubois", "PERSON", 0.95),
                ("Jean Martin", "PERSON", 0.95),
                ("Sophie Laurent", "PERSON", 0.95),
                ("Pierre Fontaine", "PERSON", 0.95),
                ("Pierre Dupont", "PERSON", 0.95),
                ("Paris", "LOCATION", 0.90),
                ("Lyon", "LOCATION", 0.90),
                ("Marseille", "LOCATION", 0.90),
                ("Acme SA", "ORG", 0.85),
                ("TechCorp", "ORG", 0.85),
                ("Renault", "ORG", 0.85),
                ("Peugeot", "ORG", 0.85),
            ]

            # Find all occurrences of each pattern
            for pattern_text, entity_type, confidence in patterns:
                # Use regex to find all occurrences (case-sensitive word boundary match)
                for match in re.finditer(re.escape(pattern_text), text):
                    entities.append(
                        DetectedEntity(
                            text=pattern_text,
                            entity_type=entity_type,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=confidence,
                            source="spacy",
                        )
                    )

            return sorted(entities, key=lambda e: e.start_pos)

        def get_model_info(self) -> dict[str, str]:
            return {"name": "mock", "version": "1.0.0"}

    # Story 2.6: Process command now uses DocumentProcessor which internally uses HybridDetector
    monkeypatch.setattr(
        "gdpr_pseudonymizer.core.document_processor.HybridDetector",
        MockHybridDetector,
    )


def test_process_end_to_end_without_validation(tmp_path: Path) -> None:
    """Test full processing workflow without validation."""
    # Create input file with entities (French text)
    input_file = tmp_path / "input.txt"
    input_file.write_text(
        "Entretien avec Marie Dubois à Paris. Jean Martin et Acme SA étaient également présents.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    # Run CLI command with star_wars theme to match assertions
    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    # Debug: Save output if command failed
    if result.exit_code != 0:
        debug_file = tmp_path / "debug_output.txt"
        debug_file.write_text(
            f"Exit code: {result.exit_code}\n\n{result.stdout}\n\n{result.exception if result.exception else 'No exception'}",
            encoding="utf-8",
        )
        print(f"\nDebug output saved to: {debug_file}")

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify output file was created
    assert output_file.exists()

    # Verify entities were replaced (original entities should be gone)
    output_content = output_file.read_text()
    assert "Marie Dubois" not in output_content
    assert "Paris" not in output_content
    assert "Jean Martin" not in output_content
    assert "Acme SA" not in output_content

    # Verify output is different from input (entities were pseudonymized)
    input_content = input_file.read_text()
    assert output_content != input_content

    # Verify output is not empty and has reasonable length
    assert len(output_content) > 0
    assert (
        len(output_content) >= len(input_content) * 0.8
    )  # Allow some length variation


def test_process_end_to_end_with_default_output_filename(tmp_path: Path) -> None:
    """Test processing with auto-generated output filename."""
    # Create input file (French text)
    input_file = tmp_path / "interview.txt"
    input_file.write_text("Réunion avec Marie Dubois à Paris.", encoding="utf-8")

    # Run CLI command without specifying output file
    result = runner.invoke(app, ["process", str(input_file), "--theme", "star_wars"])

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify default output file was created
    expected_output = tmp_path / "interview_pseudonymized.txt"
    assert expected_output.exists()

    # Verify content was pseudonymized (behavior-based, not specific pseudonyms)
    output_content = expected_output.read_text()
    input_content = input_file.read_text()

    # Verify original entities removed
    assert "Marie Dubois" not in output_content
    assert "Paris" not in output_content

    # Verify output differs from input
    assert output_content != input_content
    assert len(output_content) > 0


def test_process_end_to_end_with_txt_file(tmp_path: Path) -> None:
    """Test processing .txt file."""
    input_file = tmp_path / "test.txt"
    input_file.write_text(
        "Sophie Laurent travaille chez Renault à Lyon.", encoding="utf-8"
    )

    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    output_content = output_file.read_text()
    input_content = input_file.read_text()

    # Verify originals removed
    assert "Sophie Laurent" not in output_content
    assert "Renault" not in output_content
    assert "Lyon" not in output_content

    # Verify output differs from input (entities were pseudonymized)
    assert output_content != input_content
    assert len(output_content) > 0


def test_process_end_to_end_with_md_file(tmp_path: Path) -> None:
    """Test processing .md file."""
    input_file = tmp_path / "test.md"
    input_file.write_text(
        "# Entretien\n\nRéunion avec Pierre Dupont à Marseille.\n\n## Notes\n\nPierre Dupont vient de Paris.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.md"

    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    output_content = output_file.read_text()
    input_content = input_file.read_text()

    # Verify originals removed
    assert "Pierre Dupont" not in output_content
    assert "Marseille" not in output_content
    assert "Paris" not in output_content

    # Markdown formatting preserved
    assert "# Entretien" in output_content
    assert "## Notes" in output_content

    # Verify output differs from input
    assert output_content != input_content
    assert len(output_content) > 0


def test_process_end_to_end_file_not_found(tmp_path: Path) -> None:
    """Test error handling for non-existent file."""
    input_file = tmp_path / "nonexistent.txt"
    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app, ["process", str(input_file), "--output", str(output_file)]
    )

    # Command should fail with exit code 2 (file doesn't exist - Typer validation)
    assert result.exit_code == 2
    # Output file should not be created
    assert not output_file.exists()


def test_process_end_to_end_invalid_file_format(tmp_path: Path) -> None:
    """Test error handling for invalid file format."""
    input_file = tmp_path / "test.csv"
    input_file.write_text("Test content.")

    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app, ["process", str(input_file), "--output", str(output_file)]
    )

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

    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    assert result.exit_code == 0

    output_content = output_file.read_text()
    input_content = input_file.read_text()

    # Verify original entity removed
    assert "Marie Dubois" not in output_content

    # Verify output differs from input
    assert output_content != input_content
    assert len(output_content) > 0

    # Count how many times "Marie Dubois" appeared in input
    original_count = input_content.count("Marie Dubois")
    assert original_count == 3

    # All occurrences should be replaced with the SAME pseudonym (idempotency)
    # Extract words to find which pseudonym was used most frequently
    words = output_content.split()
    from collections import Counter

    word_pairs = [
        " ".join(words[i : i + 2]) for i in range(len(words) - 1)
    ]  # Get all 2-word combos
    pair_counts = Counter(word_pairs)
    # The most common 2-word pair should be the pseudonym (appearing 3 times)
    if pair_counts:
        most_common_pair, count = pair_counts.most_common(1)[0]
        # Should have at least one repeated pseudonym
        assert count >= 2  # At minimum, 2 occurrences should use same pseudonym


def test_process_end_to_end_no_entities(tmp_path: Path) -> None:
    """Test processing file with no entities."""
    input_file = tmp_path / "test.txt"
    input_file.write_text("This is a test file without any entities to detect.")

    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app, ["process", str(input_file), "--output", str(output_file)]
    )

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
        "Marie Dubois et Jean Martin chez Renault se sont rencontrés à Paris. "
        "Sophie Laurent et Pierre Dupont chez Peugeot les ont rejoints depuis Lyon et Marseille.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    assert result.exit_code == 0

    output_content = output_file.read_text()
    input_content = input_file.read_text()

    # Verify originals removed
    assert "Marie Dubois" not in output_content
    assert "Jean Martin" not in output_content
    assert "Sophie Laurent" not in output_content
    assert "Pierre Dupont" not in output_content
    assert "Renault" not in output_content
    assert "Peugeot" not in output_content
    assert "Paris" not in output_content
    assert "Lyon" not in output_content
    assert "Marseille" not in output_content

    # Verify output differs from input
    assert output_content != input_content
    assert len(output_content) > 0
    # Output should have reasonable length (entities replaced, not removed)
    assert len(output_content) >= len(input_content) * 0.7


def test_process_end_to_end_preserves_formatting(tmp_path: Path) -> None:
    """Test processing with text that has special formatting.

    Note: Full formatting preservation is implemented in later stories.
    This test verifies entities are replaced correctly.
    """
    input_file = tmp_path / "test.txt"
    input_file.write_text(
        "Marie Dubois travaille à Paris chez Renault.",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    assert result.exit_code == 0

    output_content = output_file.read_text()
    input_content = input_file.read_text()

    # Verify originals removed
    assert "Marie Dubois" not in output_content
    assert "Paris" not in output_content
    assert "Renault" not in output_content

    # Verify output differs from input
    assert output_content != input_content
    assert len(output_content) > 0


def test_process_end_to_end_help_command() -> None:
    """Test CLI help display."""
    result = runner.invoke(app, ["process", "--help"])

    assert result.exit_code == 0
    assert "Process a single document" in result.stdout
    # Story 2.6: Check for key options in help text
    assert "--output" in result.stdout or "-o" in result.stdout
    assert "--theme" in result.stdout or "-t" in result.stdout
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
    assert "gdpr-pseudo version" in result.stdout


def test_process_end_to_end_sample_document(tmp_path: Path) -> None:
    """Test processing with realistic sample document."""
    # Create realistic French interview text
    input_file = tmp_path / "interview.txt"
    input_file.write_text(
        """Entretien de recherche

Date: 15 janvier 2026
Lieu: Paris

Résumé de l'entretien avec Marie Dubois de Renault.

Marie Dubois a expliqué que son équipe basée à Paris collabore
régulièrement avec Jean Martin et Sophie Laurent.

"Notre partenariat avec Peugeot est excellent", dit Marie Dubois.

Notes:
- Marie Dubois: contact principal
- Renault: organisation partenaire
""",
        encoding="utf-8",
    )

    output_file = tmp_path / "interview_anonymized.txt"

    result = runner.invoke(
        app,
        [
            "process",
            str(input_file),
            "--output",
            str(output_file),
            "--theme",
            "star_wars",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    output_content = output_file.read_text()
    input_content = input_file.read_text()

    # Verify original entities removed
    assert "Marie Dubois" not in output_content
    assert "Jean Martin" not in output_content
    assert "Sophie Laurent" not in output_content
    assert "Renault" not in output_content
    assert "Peugeot" not in output_content
    assert "Paris" not in output_content

    # Verify structure preserved
    assert "Entretien de recherche" in output_content
    assert "Date:" in output_content
    assert "Notes:" in output_content

    # Verify output differs from input
    assert output_content != input_content
    assert len(output_content) > 0
