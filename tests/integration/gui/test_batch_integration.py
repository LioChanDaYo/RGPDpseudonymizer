"""Integration test for batch processing flow.

Tests the end-to-end signal flow from BatchScreen through BatchWorker
with mock DocumentProcessor.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.gui.screens.batch import BatchScreen


@pytest.fixture()
def batch_screen(integration_window):  # type: ignore[no-untyped-def]
    """Get BatchScreen from the integration window."""
    idx = integration_window._screens["batch"]
    screen = integration_window.stack.widget(idx)
    assert isinstance(screen, BatchScreen)
    # Pre-cache passphrase for integration tests
    integration_window.cached_passphrase = ("test.db", "test_passphrase_12345")
    return screen


class TestBatchEndToEnd:
    """End-to-end batch processing with mock processor."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_batch_flow_select_process_summary(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        # Create test files
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "a.txt").write_text("Document A avec Jean Dupont.")
        (input_dir / "b.txt").write_text("Document B avec Marie Martin.")

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            input_file="",
            output_file="",
            entities_detected=3,
            entities_new=2,
            entities_reused=1,
            processing_time_seconds=1.0,
        )
        mock_dp_cls.return_value = mock_processor

        # Phase 0: Select folder
        batch_screen.set_context(folder_path=str(input_dir))
        assert batch_screen.phases.currentIndex() == 0
        assert batch_screen.file_table.rowCount() == 2
        assert batch_screen.start_button.isEnabled()

        # Phase 1: Start processing — this calls _launch_worker
        output_dir = tmp_path / "output"
        batch_screen.output_input.setText(str(output_dir))

        # Directly launch the worker (bypass passphrase dialog since we have cache)
        batch_screen._launch_worker("test.db", "test_passphrase_12345")

        # Worker runs synchronously in test (QThreadPool not started for unit test)
        # We need to wait for the finished signal
        # Instead, manually run the worker synchronously
        if batch_screen._worker is not None:
            batch_screen._worker.run()

        # Verify that the finished callback was invoked
        # (It should have switched to summary phase)
        assert batch_screen.phases.currentIndex() == 2

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_config_persistence_across_transitions(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path
    ):  # type: ignore[no-untyped-def]
        """Verify config settings are passed to BatchWorker."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "a.txt").write_text("Test")

        from gdpr_pseudonymizer.core.document_processor import ProcessingResult

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            input_file="",
            output_file="",
            entities_detected=1,
            entities_new=1,
            entities_reused=0,
            processing_time_seconds=0.5,
        )
        mock_dp_cls.return_value = mock_processor

        # Set batch screen config
        batch_screen._config["default_theme"] = "star_wars"
        batch_screen._config["continue_on_error"] = False

        batch_screen.set_context(folder_path=str(input_dir))
        batch_screen.output_input.setText(str(tmp_path / "output"))
        batch_screen._launch_worker("test.db", "test_passphrase_12345")

        # Verify worker was created with correct config
        worker = batch_screen._worker
        assert worker._theme == "star_wars"
        assert worker._continue_on_error is False
