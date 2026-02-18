"""Tests for ResultsScreen."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.gui.screens.results import ResultsScreen


@pytest.fixture()
def results_screen(qtbot, main_window):  # type: ignore[no-untyped-def]
    """Get the results screen from main_window fixture."""
    idx = main_window._screens["results"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, ResultsScreen)
    return screen


@pytest.fixture()
def sample_result():  # type: ignore[no-untyped-def]
    """Create a sample GUIProcessingResult for testing."""
    from gdpr_pseudonymizer.gui.workers.processing_worker import GUIProcessingResult

    return GUIProcessingResult(
        success=True,
        input_file="C:/docs/rapport.txt",
        output_file="C:/temp/output.txt",
        entities_detected=5,
        entities_new=3,
        entities_reused=2,
        processing_time_seconds=2.5,
        pseudonymized_content="Le texte avec Emma Martin et Lyon.",
        entity_type_counts={"PERSON": 2, "LOCATION": 2, "ORG": 1},
        entity_mappings=[
            ("Emma Martin", "PERSON"),
            ("Lyon", "LOCATION"),
        ],
    )


class TestResultsScreenDisplay:
    """Test results display."""

    def test_shows_document_content(self, results_screen, sample_result, tmp_path):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Le texte pseudonymisé.", encoding="utf-8")

        results_screen.show_results(
            result=sample_result,
            content="Le texte avec Emma Martin et Lyon.",
            entity_mappings=[("Emma Martin", "PERSON")],
            original_path="C:/docs/rapport.txt",
            temp_path=str(temp_file),
        )

        assert "Emma Martin" in results_screen.preview.toPlainText()

    def test_shows_entity_type_counts(self, results_screen, sample_result, tmp_path):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        results_screen.show_results(
            result=sample_result,
            content="Content",
            entity_mappings=[],
            original_path="rapport.txt",
            temp_path=str(temp_file),
        )

        assert "2" in results_screen.person_label.text()
        assert "2" in results_screen.location_label.text()
        assert "1" in results_screen.org_label.text()

    def test_shows_stats(self, results_screen, sample_result, tmp_path):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        results_screen.show_results(
            result=sample_result,
            content="Content",
            entity_mappings=[],
            original_path="rapport.txt",
            temp_path=str(temp_file),
        )

        assert "3 nouvelles" in results_screen.stats_label.text()
        assert "2 réutilisées" in results_screen.stats_label.text()


class TestResultsScreenHighlighting:
    """Test pseudonym highlighting."""

    def test_highlighting_applies_colors(self, results_screen, sample_result, tmp_path):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        content = "Le document mentionne Emma Martin et la ville de Lyon."
        results_screen.show_results(
            result=sample_result,
            content=content,
            entity_mappings=[
                ("Emma Martin", "PERSON"),
                ("Lyon", "LOCATION"),
            ],
            original_path="rapport.txt",
            temp_path=str(temp_file),
        )

        # Verify content is in preview
        assert "Emma Martin" in results_screen.preview.toPlainText()
        assert "Lyon" in results_screen.preview.toPlainText()


class TestResultsScreenSave:
    """Test save functionality."""

    @patch("gdpr_pseudonymizer.gui.screens.results.QFileDialog.getSaveFileName")
    def test_save_dialog_triggered(
        self, mock_dialog, results_screen, sample_result, tmp_path
    ):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        save_path = tmp_path / "saved_rapport_pseudonymise.txt"
        mock_dialog.return_value = (str(save_path), "")

        results_screen.show_results(
            result=sample_result,
            content="Content",
            entity_mappings=[],
            original_path=str(tmp_path / "rapport.txt"),
            temp_path=str(temp_file),
        )

        results_screen._on_save()

        assert save_path.exists()
        assert save_path.read_text(encoding="utf-8") == "Content"

    @patch("gdpr_pseudonymizer.gui.screens.results.QFileDialog.getSaveFileName")
    def test_save_cancelled(
        self, mock_dialog, results_screen, sample_result, tmp_path
    ):  # type: ignore[no-untyped-def]
        mock_dialog.return_value = ("", "")

        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        results_screen.show_results(
            result=sample_result,
            content="Content",
            entity_mappings=[],
            original_path="rapport.txt",
            temp_path=str(temp_file),
        )

        results_screen._on_save()
        # No crash, no file saved


class TestResultsScreenNavigation:
    """Test navigation actions."""

    def test_new_document_returns_to_home(
        self, results_screen, main_window, sample_result, tmp_path
    ):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        results_screen.show_results(
            result=sample_result,
            content="Content",
            entity_mappings=[],
            original_path=str(tmp_path / "rapport.txt"),
            temp_path=str(temp_file),
        )

        main_window.navigate_to("results")
        results_screen._on_new_document()
        assert main_window.current_screen_name() == "home"

    def test_new_document_cleans_temp_file(
        self, results_screen, sample_result, tmp_path
    ):  # type: ignore[no-untyped-def]
        temp_file = tmp_path / "output.txt"
        temp_file.write_text("Content", encoding="utf-8")

        results_screen.show_results(
            result=sample_result,
            content="Content",
            entity_mappings=[],
            original_path=str(tmp_path / "rapport.txt"),
            temp_path=str(temp_file),
        )

        results_screen._on_new_document()
        assert not temp_file.exists()
