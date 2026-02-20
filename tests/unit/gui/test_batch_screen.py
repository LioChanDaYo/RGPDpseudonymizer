"""Tests for BatchScreen."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
from gdpr_pseudonymizer.gui.workers.batch_worker import BatchResult, DocumentResult


@pytest.fixture()
def batch_screen(main_window):  # type: ignore[no-untyped-def]
    """Get the batch screen from main_window fixture."""
    idx = main_window._screens["batch"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, BatchScreen)
    return screen


class TestFileDiscovery:
    """Tests for file discovery in selection phase."""

    def test_discover_supported_files(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.csv").write_text("c")

        batch_screen.folder_input.setText(str(tmp_path))

        assert batch_screen.file_table.rowCount() == 2
        assert batch_screen.start_button.isEnabled()

    def test_excludes_pseudonymized(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        (tmp_path / "doc.txt").write_text("content")
        (tmp_path / "doc_pseudonymized.txt").write_text("content")

        batch_screen.folder_input.setText(str(tmp_path))

        assert batch_screen.file_table.rowCount() == 1

    def test_empty_folder_disables_start(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        batch_screen.folder_input.setText(str(tmp_path))
        assert not batch_screen.start_button.isEnabled()

    def test_file_count_label(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "c.txt").write_text("c")

        batch_screen.folder_input.setText(str(tmp_path))

        assert "3" in batch_screen.file_count_label.text()


class TestAddFiles:
    """Tests for _add_files() multi-file selection."""

    def test_add_files_appends_to_list(self, batch_screen, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.md"
        f1.write_text("a")
        f2.write_text("b")

        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.screens.batch.QFileDialog.getOpenFileNames",
            lambda *a, **kw: ([str(f1), str(f2)], ""),
        )

        batch_screen._add_files()

        assert len(batch_screen._files) == 2
        assert batch_screen.file_table.rowCount() == 2
        assert batch_screen.start_button.isEnabled()

    def test_add_files_excludes_pseudonymized(self, batch_screen, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "doc.txt"
        f2 = tmp_path / "doc_pseudonymized.txt"
        f1.write_text("a")
        f2.write_text("b")

        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.screens.batch.QFileDialog.getOpenFileNames",
            lambda *a, **kw: ([str(f1), str(f2)], ""),
        )

        batch_screen._add_files()

        assert len(batch_screen._files) == 1

    def test_add_files_no_duplicates(self, batch_screen, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
        f1 = tmp_path / "a.txt"
        f1.write_text("a")

        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.screens.batch.QFileDialog.getOpenFileNames",
            lambda *a, **kw: ([str(f1)], ""),
        )

        batch_screen._add_files()
        batch_screen._add_files()  # Add same file again

        assert len(batch_screen._files) == 1


class TestOutputDirPrePopulation:
    """Tests for output directory pre-population from config."""

    def test_output_dir_from_config(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        (tmp_path / "a.txt").write_text("a")
        batch_screen._config["default_output_dir"] = str(tmp_path / "custom_output")

        batch_screen.folder_input.setText(str(tmp_path))

        assert batch_screen.output_input.text() == str(tmp_path / "custom_output")

    def test_output_dir_default_subfolder(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        (tmp_path / "a.txt").write_text("a")

        batch_screen.folder_input.setText(str(tmp_path))

        expected = str(tmp_path / "_pseudonymized")
        assert batch_screen.output_input.text() == expected


class TestBatchScreenSetContext:
    """Tests for set_context navigation data passing."""

    def test_set_context_populates_folder(self, batch_screen, tmp_path):  # type: ignore[no-untyped-def]
        (tmp_path / "test.txt").write_text("content")
        batch_screen.set_context(folder_path=str(tmp_path))

        assert batch_screen.folder_input.text() == str(tmp_path)
        assert batch_screen.file_table.rowCount() >= 1


class TestBatchProgressDisplay:
    """Tests for progress display updates."""

    def test_progress_bar_updates(self, batch_screen, qtbot):  # type: ignore[no-untyped-def]
        batch_screen._files = [Path("a.txt"), Path("b.txt")]
        batch_screen._batch_start_time = 1.0

        batch_screen._on_progress(50, "DOC_DONE:0")

        assert batch_screen.progress_bar.value() == 50
        assert "1/2" in batch_screen.progress_label.text()

    def test_eta_displayed(self, batch_screen, qtbot):  # type: ignore[no-untyped-def]
        import time

        batch_screen._files = [Path("a.txt"), Path("b.txt")]
        batch_screen._batch_start_time = time.time() - 5  # 5 seconds ago

        batch_screen._on_progress(50, "DOC_DONE:0")

        assert batch_screen.eta_label.text() != ""


class TestBatchSummaryDisplay:
    """Tests for summary phase."""

    def test_summary_displays_results(self, batch_screen, qtbot):  # type: ignore[no-untyped-def]
        result = BatchResult(
            total_files=3,
            successful_files=2,
            failed_files=1,
            total_entities=10,
            new_entities=6,
            reused_entities=4,
            total_time_seconds=15.0,
            per_document_results=[
                DocumentResult(
                    index=0,
                    filename="a.txt",
                    success=True,
                    entities_detected=5,
                    processing_time=5.0,
                ),
                DocumentResult(
                    index=1,
                    filename="b.txt",
                    success=True,
                    entities_detected=5,
                    processing_time=5.0,
                ),
                DocumentResult(
                    index=2,
                    filename="c.txt",
                    success=False,
                    processing_time=5.0,
                    error_message="File error",
                ),
            ],
        )

        batch_screen._files = [Path("a.txt"), Path("b.txt"), Path("c.txt")]
        batch_screen._show_summary(result)

        assert batch_screen.phases.currentIndex() == 2
        assert batch_screen.summary_table.rowCount() == 3


class TestBatchExport:
    """Tests for report export."""

    def test_export_report(self, batch_screen, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
        output_file = str(tmp_path / "report.txt")

        batch_screen._batch_result = BatchResult(
            total_files=1,
            successful_files=1,
            total_entities=3,
            new_entities=2,
            reused_entities=1,
            total_time_seconds=5.0,
            per_document_results=[
                DocumentResult(
                    index=0,
                    filename="test.txt",
                    success=True,
                    entities_detected=3,
                    processing_time=5.0,
                ),
            ],
        )

        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.screens.batch.QFileDialog.getSaveFileName",
            lambda *a, **kw: (output_file, ""),
        )

        batch_screen._export_report()

        content = Path(output_file).read_text(encoding="utf-8")
        assert "test.txt" in content
        assert "3 entités" in content or "3" in content


class TestProgressStatusTransitions:
    """Tests for per-document status transitions in the progress table."""

    def test_first_doc_shows_en_cours_on_initial_progress(self, batch_screen, qtbot):  # type: ignore[no-untyped-def]
        batch_screen._files = [Path("a.txt"), Path("b.txt")]
        batch_screen._batch_start_time = 1.0

        # Initialize doc table
        from PySide6.QtWidgets import QTableWidgetItem

        batch_screen.doc_table.setRowCount(2)
        for row in range(2):
            batch_screen.doc_table.setItem(row, 3, QTableWidgetItem("En attente"))

        # Non-DOC_DONE message marks first doc as "En cours"
        batch_screen._on_progress(0, "Chargement du modèle...")

        assert batch_screen.doc_table.item(0, 3).text() == "En cours"

    def test_doc_done_transitions_to_traite(self, batch_screen, qtbot):  # type: ignore[no-untyped-def]
        batch_screen._files = [Path("a.txt"), Path("b.txt")]
        batch_screen._batch_start_time = 1.0
        batch_screen._worker = MagicMock()

        from PySide6.QtWidgets import QTableWidgetItem

        batch_screen.doc_table.setRowCount(2)
        for row in range(2):
            batch_screen.doc_table.setItem(row, 3, QTableWidgetItem("En attente"))

        batch_screen._on_progress(50, "DOC_DONE:0")

        assert batch_screen.doc_table.item(0, 3).text() == "Traité"
        # Next doc should be "En cours"
        assert batch_screen.doc_table.item(1, 3).text() == "En cours"


class TestPauseCancel:
    """Tests for pause/cancel button state."""

    def test_pause_toggles_text(self, batch_screen, qtbot):  # type: ignore[no-untyped-def]
        batch_screen._worker = MagicMock()
        assert batch_screen.pause_button.text() == "Suspendre"

        batch_screen._toggle_pause()
        assert batch_screen.pause_button.text() == "Reprendre"
        assert batch_screen._is_paused is True

        batch_screen._toggle_pause()
        assert batch_screen.pause_button.text() == "Suspendre"
        assert batch_screen._is_paused is False

    def test_cancel_shows_confirmation_dialog(self, batch_screen, qtbot, monkeypatch):  # type: ignore[no-untyped-def]
        batch_screen._worker = MagicMock()

        dialog_shown = False

        def mock_destructive(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal dialog_shown
            dialog_shown = True
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = False  # User cancels the dialog
            return mock_dlg

        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.widgets.confirm_dialog.ConfirmDialog.destructive",
            staticmethod(mock_destructive),
        )

        batch_screen._cancel_batch()

        assert dialog_shown
        batch_screen._worker.cancel.assert_not_called()

    def test_cancel_confirmed_calls_worker_cancel(self, batch_screen, qtbot, monkeypatch):  # type: ignore[no-untyped-def]
        batch_screen._worker = MagicMock()

        monkeypatch.setattr(
            "gdpr_pseudonymizer.gui.widgets.confirm_dialog.ConfirmDialog.destructive",
            staticmethod(lambda *a, **kw: MagicMock(exec=MagicMock(return_value=True))),
        )

        batch_screen._cancel_batch()

        batch_screen._worker.cancel.assert_called_once()
