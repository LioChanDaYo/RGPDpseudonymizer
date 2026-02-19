"""Tests for ProcessingScreen."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen


@pytest.fixture()
def processing_screen(qtbot, main_window):  # type: ignore[no-untyped-def]
    """Get the processing screen from main_window fixture."""
    idx = main_window._screens["processing"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, ProcessingScreen)
    return screen


class TestProcessingScreenUI:
    """Test processing screen UI elements."""

    def test_screen_has_progress_bar(self, processing_screen):  # type: ignore[no-untyped-def]
        assert processing_screen.progress_bar is not None
        assert processing_screen.progress_bar.minimum() == 0
        assert processing_screen.progress_bar.maximum() == 100

    def test_screen_has_phase_label(self, processing_screen):  # type: ignore[no-untyped-def]
        assert processing_screen.phase_label is not None

    def test_continue_button_hidden_initially(self, processing_screen):  # type: ignore[no-untyped-def]
        # isHidden checks the widget's own state, not parent visibility
        assert processing_screen.continue_button.isHidden()

    def test_cancel_button_visible(self, processing_screen):  # type: ignore[no-untyped-def]
        assert processing_screen.cancel_button is not None


class TestProcessingScreenProgress:
    """Test progress updates."""

    def test_progress_update(self, processing_screen):  # type: ignore[no-untyped-def]
        processing_screen._on_progress(50, "Détection des entités...")
        assert processing_screen.progress_bar.value() == 50
        assert processing_screen.phase_label.text() == "Détection des entités..."

    def test_indeterminate_progress(self, processing_screen):  # type: ignore[no-untyped-def]
        processing_screen._on_progress(-1, "Downloading model...")
        assert processing_screen.progress_bar.maximum() == 0


class TestProcessingScreenResults:
    """Test entity summary display after detection."""

    def test_entity_summary_shown(self, processing_screen):  # type: ignore[no-untyped-def]
        from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        entities = [
            DetectedEntity(text="Jean", entity_type="PERSON", start_pos=0, end_pos=4),
            DetectedEntity(
                text="Marie", entity_type="PERSON", start_pos=10, end_pos=15
            ),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=20, end_pos=25
            ),
            DetectedEntity(
                text="Lyon", entity_type="LOCATION", start_pos=30, end_pos=34
            ),
            DetectedEntity(text="ACME", entity_type="ORG", start_pos=40, end_pos=44),
        ]
        result = DetectionResult(
            document_text="Test document text",
            detected_entities=entities,
            pseudonym_previews={},
            entity_type_counts={"PERSON": 2, "LOCATION": 2, "ORG": 1},
            db_path="test.db",
            passphrase="test_pass_secure",
            theme="neutral",
            input_file="test.txt",
            detection_time_seconds=2.5,
        )

        processing_screen._on_finished(result)

        # Use isHidden() to check widget's own visibility state
        assert not processing_screen.summary_panel.isHidden()
        assert processing_screen.warning_panel.isHidden()
        assert not processing_screen.continue_button.isHidden()
        assert "2 noms de personnes" in processing_screen.summary_label.text()
        assert "2 lieux" in processing_screen.summary_label.text()
        assert "1 organisations" in processing_screen.summary_label.text()

    def test_zero_entity_warning(self, processing_screen):  # type: ignore[no-untyped-def]
        from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult

        result = DetectionResult(
            document_text="Empty document",
            detected_entities=[],
            pseudonym_previews={},
            entity_type_counts={},
            db_path="test.db",
            passphrase="test_pass_secure",
            theme="neutral",
            input_file="test.txt",
            detection_time_seconds=1.0,
        )

        processing_screen._on_finished(result)

        assert not processing_screen.warning_panel.isHidden()
        assert processing_screen.summary_panel.isHidden()
        assert not processing_screen.continue_button.isHidden()


class TestProcessingScreenNavigation:
    """Test navigation actions."""

    def test_cancel_returns_to_home(self, processing_screen, main_window):  # type: ignore[no-untyped-def]
        main_window.navigate_to("processing")
        processing_screen._on_cancel()
        assert main_window.current_screen_name() == "home"

    def test_continue_navigates_to_validation(self, processing_screen, main_window):  # type: ignore[no-untyped-def]
        from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
        from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

        entities = [
            DetectedEntity(text="Jean", entity_type="PERSON", start_pos=0, end_pos=4),
        ]
        result = DetectionResult(
            document_text="Le contrat avec Jean.",
            detected_entities=entities,
            pseudonym_previews={"Jean_0": "Pierre"},
            entity_type_counts={"PERSON": 1},
            db_path="test.db",
            passphrase="test_pass_secure",
            theme="neutral",
            input_file="test.txt",
            detection_time_seconds=1.0,
        )

        processing_screen._on_finished(result)
        processing_screen._on_continue()
        assert main_window.current_screen_name() == "validation"


class TestProcessingScreenStartProcessing:
    """Test start_processing method."""

    @patch(
        "gdpr_pseudonymizer.gui.workers.model_manager.ModelManager.is_model_installed"
    )
    @patch("gdpr_pseudonymizer.gui.screens.processing.QThreadPool")
    def test_start_processing_resets_ui(
        self, mock_pool, mock_model_check, processing_screen, tmp_path
    ):  # type: ignore[no-untyped-def]
        mock_model_check.return_value = True
        mock_pool.globalInstance.return_value = MagicMock()

        input_file = tmp_path / "test.txt"
        input_file.write_text("Test content", encoding="utf-8")

        processing_screen.start_processing(
            file_path=str(input_file),
            db_path=str(tmp_path / "test.db"),
            passphrase="pass",
        )

        assert processing_screen.continue_button.isHidden()
        assert processing_screen.summary_panel.isHidden()
