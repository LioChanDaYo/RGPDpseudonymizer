"""Tests for ModelManager and ModelDownloadWorker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from gdpr_pseudonymizer.gui.workers.model_manager import (
    ModelDownloadWorker,
    ModelManager,
)


class TestModelManager:
    """Test spaCy model installation check."""

    @patch("spacy.util.is_package")
    def test_model_installed(self, mock_is_package):  # type: ignore[no-untyped-def]
        mock_is_package.return_value = True
        assert ModelManager.is_model_installed("fr_core_news_lg") is True
        mock_is_package.assert_called_once_with("fr_core_news_lg")

    @patch("spacy.util.is_package")
    def test_model_not_installed(self, mock_is_package):  # type: ignore[no-untyped-def]
        mock_is_package.return_value = False
        assert ModelManager.is_model_installed("fr_core_news_lg") is False

    @patch(
        "spacy.util.is_package",
        side_effect=ImportError,
    )
    def test_model_check_import_error(self, mock_is_package):  # type: ignore[no-untyped-def]
        assert ModelManager.is_model_installed() is False


class TestModelDownloadWorker:
    """Test background model download worker."""

    @patch("gdpr_pseudonymizer.gui.workers.model_manager.subprocess.run")
    def test_download_success(self, mock_run, qtbot):  # type: ignore[no-untyped-def]
        mock_run.return_value = MagicMock(returncode=0)

        worker = ModelDownloadWorker()
        finished_results = []
        worker.signals.finished.connect(lambda r: finished_results.append(r))

        worker.run()

        assert len(finished_results) == 1
        assert finished_results[0] is True

    @patch("gdpr_pseudonymizer.gui.workers.model_manager.subprocess.run")
    def test_download_failure(self, mock_run, qtbot):  # type: ignore[no-untyped-def]
        mock_run.return_value = MagicMock(returncode=1, stderr="Error occurred")

        worker = ModelDownloadWorker()
        error_results = []
        worker.signals.error.connect(lambda msg: error_results.append(msg))

        worker.run()

        assert len(error_results) == 1
        assert "téléchargé" in error_results[0]

    @patch("gdpr_pseudonymizer.gui.workers.model_manager.subprocess.run")
    def test_download_emits_progress(self, mock_run, qtbot):  # type: ignore[no-untyped-def]
        mock_run.return_value = MagicMock(returncode=0)

        worker = ModelDownloadWorker()
        progress_messages = []
        worker.signals.progress.connect(lambda p, m: progress_messages.append(m))

        worker.run()

        assert len(progress_messages) >= 1
        assert "téléchargement" in progress_messages[0].lower()

    @patch(
        "gdpr_pseudonymizer.gui.workers.model_manager.subprocess.run",
        side_effect=Exception("Network error"),
    )
    def test_download_exception(self, mock_run, qtbot):  # type: ignore[no-untyped-def]
        worker = ModelDownloadWorker()
        error_results = []
        worker.signals.error.connect(lambda msg: error_results.append(msg))

        worker.run()

        assert len(error_results) == 1
        assert "connexion" in error_results[0].lower()
