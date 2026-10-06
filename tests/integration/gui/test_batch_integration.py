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


@pytest.fixture()
def thread_pool():  # type: ignore[no-untyped-def]
    """Keep BatchWorker off the global QThreadPool (TEST-002).

    ``_launch_worker`` hands the worker to ``QThreadPool.globalInstance()``.
    Left alone, that background run outlives the test: once the test's
    patches are undone it uses the real DocumentProcessor and init_database,
    creates its DB relative to the CWD, and can call into mocks owned by the
    next test on the same xdist worker. Tests run the worker synchronously
    instead, so nothing survives teardown.
    """
    with patch("gdpr_pseudonymizer.gui.screens.batch.QThreadPool") as mock_pool:
        yield mock_pool


class TestBatchEndToEnd:
    """End-to-end batch processing with mock processor."""

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_batch_flow_select_process_summary(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path, thread_pool
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
        batch_screen._launch_worker(str(tmp_path / "test.db"), "test_passphrase_12345")

        # The pool is mocked: the worker was handed over but not started.
        # Run it synchronously so it finishes before the test's patches unwind.
        worker = batch_screen._worker
        assert worker is not None
        thread_pool.globalInstance.return_value.start.assert_called_once_with(worker)
        worker.run()

        # Verify that the finished callback was invoked
        # (It should have switched to summary phase)
        assert batch_screen.phases.currentIndex() == 2

    @patch("gdpr_pseudonymizer.data.database.init_database")
    @patch("gdpr_pseudonymizer.core.document_processor.DocumentProcessor")
    def test_config_persistence_across_transitions(
        self, mock_dp_cls, mock_init_db, batch_screen, qtbot, tmp_path, thread_pool
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
        batch_screen._launch_worker(str(tmp_path / "test.db"), "test_passphrase_12345")

        # Verify worker was created with correct config (never started: the
        # pool is mocked, so no background run leaks past teardown)
        worker = batch_screen._worker
        thread_pool.globalInstance.return_value.start.assert_called_once_with(worker)
        assert worker._theme == "star_wars"
        assert worker._continue_on_error is False
