"""Batch processing screen with file selection, progress dashboard, and summary.

Three-phase screen using QStackedWidget:
  0 = Selection (file discovery + output dir)
  1 = Processing (progress dashboard with pause/cancel)
  2 = Summary (batch results + export)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.widgets.step_indicator import StepMode
from gdpr_pseudonymizer.gui.widgets.toast import Toast
from gdpr_pseudonymizer.gui.workers.batch_worker import (
    BatchResult,
    collect_files,
)
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow

logger = get_logger(__name__)


class BatchScreen(QWidget):
    """Batch processing screen: selection -> processing -> summary."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._config = main_window.config

        self._files: list[Path] = []
        self._worker: Any = None
        self._batch_start_time: float = 0.0
        self._docs_completed: int = 0
        self._is_paused: bool = False

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_context(self, **kwargs: Any) -> None:
        """Accept navigation context (e.g., folder_path from home screen)."""
        folder_path = kwargs.get("folder_path")
        if folder_path:
            self._folder_input.setText(str(folder_path))
            self._discover_files()
        self._phases.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._phases = QStackedWidget()
        self._phases.addWidget(self._build_selection_phase())
        self._phases.addWidget(self._build_processing_phase())
        self._phases.addWidget(self._build_summary_phase())
        layout.addWidget(self._phases)

    # -- Phase 0: Selection --

    def _build_selection_phase(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        back_btn = QPushButton("\u25c0 Retour")
        back_btn.setObjectName("secondaryButton")
        back_btn.clicked.connect(lambda: self._main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addStretch()
        title = QLabel("Traitement par lot")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Folder input
        folder_row = QHBoxLayout()
        folder_label = QLabel("Dossier source :")
        folder_label.setStyleSheet("font-weight: bold;")
        folder_row.addWidget(folder_label)

        self._folder_input = QLineEdit()
        self._folder_input.setPlaceholderText("Sélectionnez un dossier...")
        self._folder_input.textChanged.connect(lambda _: self._discover_files())
        folder_row.addWidget(self._folder_input, stretch=1)

        browse_btn = QPushButton("Parcourir...")
        browse_btn.setObjectName("secondaryButton")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)

        add_files_btn = QPushButton("Ajouter des fichiers")
        add_files_btn.setObjectName("secondaryButton")
        add_files_btn.clicked.connect(self._add_files)
        folder_row.addWidget(add_files_btn)

        layout.addLayout(folder_row)

        # File count
        self._file_count_label = QLabel("")
        self._file_count_label.setObjectName("secondaryLabel")
        layout.addWidget(self._file_count_label)

        # File list table
        self._file_table = QTableWidget(0, 3)
        self._file_table.setHorizontalHeaderLabels(["Fichier", "Taille", "Format"])
        self._file_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._file_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._file_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._file_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._file_table, stretch=1)

        # Output directory
        output_row = QHBoxLayout()
        output_label = QLabel("Dossier de sortie :")
        output_label.setStyleSheet("font-weight: bold;")
        output_row.addWidget(output_label)

        self._output_input = QLineEdit()
        self._output_input.setPlaceholderText("_pseudonymized/ (par défaut)")
        output_row.addWidget(self._output_input, stretch=1)

        output_browse = QPushButton("Parcourir...")
        output_browse.setObjectName("secondaryButton")
        output_browse.clicked.connect(self._browse_output)
        output_row.addWidget(output_browse)
        layout.addLayout(output_row)

        # Start button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._start_btn = QPushButton("Démarrer le traitement")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_batch)
        btn_row.addWidget(self._start_btn)
        layout.addLayout(btn_row)

        return page

    # -- Phase 1: Processing --

    def _build_processing_phase(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Traitement en cours")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Overall progress
        self._progress_label = QLabel("0/0 (0%)")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(100)
        layout.addWidget(self._progress_bar)

        # ETA
        self._eta_label = QLabel("")
        self._eta_label.setObjectName("secondaryLabel")
        self._eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._eta_label)

        # Per-document table
        self._doc_table = QTableWidget(0, 4)
        self._doc_table.setHorizontalHeaderLabels(["#", "Fichier", "Entités", "Statut"])
        self._doc_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._doc_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._doc_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._doc_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._doc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._doc_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        layout.addWidget(self._doc_table, stretch=1)

        # Controls
        ctrl_row = QHBoxLayout()
        ctrl_row.addStretch()

        self._pause_btn = QPushButton("Suspendre")
        self._pause_btn.setObjectName("secondaryButton")
        self._pause_btn.clicked.connect(self._toggle_pause)
        ctrl_row.addWidget(self._pause_btn)

        self._cancel_btn = QPushButton("Annuler le lot")
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.clicked.connect(self._cancel_batch)
        ctrl_row.addWidget(self._cancel_btn)

        layout.addLayout(ctrl_row)

        return page

    # -- Phase 2: Summary --

    def _build_summary_phase(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        title = QLabel("Résumé du traitement")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Summary cards
        cards = QHBoxLayout()
        self._card_docs = self._make_card("Documents", "0")
        self._card_entities = self._make_card("Entités", "0")
        self._card_new = self._make_card("Nouvelles", "0")
        self._card_reused = self._make_card("Réutilisées", "0")
        self._card_errors = self._make_card("Erreurs", "0")
        cards.addWidget(self._card_docs)
        cards.addWidget(self._card_entities)
        cards.addWidget(self._card_new)
        cards.addWidget(self._card_reused)
        cards.addWidget(self._card_errors)
        layout.addLayout(cards)

        # Per-document results table
        self._summary_table = QTableWidget(0, 4)
        self._summary_table.setHorizontalHeaderLabels(
            ["Fichier", "Entités", "Temps", "Statut"]
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._summary_table, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._export_btn = QPushButton("Exporter le rapport")
        self._export_btn.setObjectName("secondaryButton")
        self._export_btn.clicked.connect(self._export_report)
        btn_row.addWidget(self._export_btn)

        home_btn = QPushButton("Retour à l'accueil")
        home_btn.clicked.connect(self._go_home)
        btn_row.addWidget(home_btn)

        layout.addLayout(btn_row)

        return page

    @staticmethod
    def _make_card(label: str, value: str) -> QWidget:
        card = QWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        val = QLabel(value)
        val.setObjectName("cardValue")
        val.setStyleSheet("font-size: 24px; font-weight: bold;")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(val)
        lbl = QLabel(label)
        lbl.setObjectName("secondaryLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl)
        return card

    # ------------------------------------------------------------------
    # Selection Phase Logic
    # ------------------------------------------------------------------

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        if folder:
            self._folder_input.setText(folder)

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Ajouter des fichiers",
            "",
            "Documents (*.txt *.md *.pdf *.docx);;Tous (*)",
        )
        if files:
            for f in files:
                p = Path(f)
                if p not in self._files and "_pseudonymized" not in p.stem:
                    self._files.append(p)
            self._update_file_table()
            self._start_btn.setEnabled(len(self._files) > 0)

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if folder:
            self._output_input.setText(folder)

    def _discover_files(self) -> None:
        folder_text = self._folder_input.text().strip()
        if not folder_text:
            self._files = []
            self._update_file_table()
            self._start_btn.setEnabled(False)
            return

        folder = Path(folder_text)
        if folder.is_dir():
            self._files = collect_files(folder)
            self._update_file_table()
            self._start_btn.setEnabled(len(self._files) > 0)

            # Pre-populate output dir
            if not self._output_input.text().strip():
                default_output = self._config.get("default_output_dir", "")
                if not default_output:
                    default_output = str(folder / "_pseudonymized")
                self._output_input.setText(default_output)
        else:
            self._files = []
            self._update_file_table()
            self._start_btn.setEnabled(False)

    def _update_file_table(self) -> None:
        self._file_table.setRowCount(len(self._files))
        supported_count = 0
        for row, fp in enumerate(self._files):
            name_item = QTableWidgetItem(fp.name)
            try:
                size = fp.stat().st_size
                if size < 1024:
                    size_str = f"{size} o"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} Ko"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} Mo"
            except OSError:
                size_str = "?"
            size_item = QTableWidgetItem(size_str)
            fmt_item = QTableWidgetItem(fp.suffix.upper().lstrip("."))

            self._file_table.setItem(row, 0, name_item)
            self._file_table.setItem(row, 1, size_item)
            self._file_table.setItem(row, 2, fmt_item)
            supported_count += 1

        self._file_count_label.setText(f"{supported_count} fichier(s) supporté(s)")

    # ------------------------------------------------------------------
    # Processing Phase Logic
    # ------------------------------------------------------------------

    def _start_batch(self) -> None:
        if not self._files:
            return

        # Prompt for passphrase
        cached = self._main_window.cached_passphrase
        if cached is not None:
            db_path, passphrase = cached
            self._launch_worker(db_path, passphrase)
            return

        file_dir = self._folder_input.text().strip() or str(Path.home())

        from gdpr_pseudonymizer.gui.widgets.passphrase_dialog import PassphraseDialog

        dialog = PassphraseDialog(
            file_directory=file_dir,
            config=self._config,
            parent=self._main_window,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        result = dialog.get_result()
        if result is None:
            return

        db_path, passphrase, remember = result
        if remember:
            self._main_window.cached_passphrase = (db_path, passphrase)

        self._launch_worker(db_path, passphrase)

    def _launch_worker(self, db_path: str, passphrase: str) -> None:
        from gdpr_pseudonymizer.gui.workers.batch_worker import BatchWorker

        # Determine output dir
        output_text = self._output_input.text().strip()
        if output_text:
            output_dir = Path(output_text)
        else:
            folder = self._folder_input.text().strip()
            output_dir = Path(folder) / "_pseudonymized" if folder else Path(".")

        theme = self._config.get("default_theme", "neutral")
        continue_on_error = self._config.get("continue_on_error", True)
        validation_mode = self._config.get("batch_validation_mode", "per_document")

        # Switch to processing phase
        self._phases.setCurrentIndex(1)
        self._main_window.step_indicator.set_mode(StepMode.BATCH)
        self._main_window.step_indicator.set_step(1)

        # Initialize progress table
        self._docs_completed = 0
        self._batch_start_time = time.time()
        self._doc_table.setRowCount(len(self._files))
        for row, fp in enumerate(self._files):
            self._doc_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self._doc_table.setItem(row, 1, QTableWidgetItem(fp.name))
            self._doc_table.setItem(row, 2, QTableWidgetItem(""))
            status_item = QTableWidgetItem("En attente")
            status_item.setForeground(Qt.GlobalColor.gray)
            self._doc_table.setItem(row, 3, status_item)

        self._progress_bar.setValue(0)
        self._progress_label.setText(f"0/{len(self._files)} (0%)")
        self._eta_label.setText("")
        self._pause_btn.setText("Suspendre")
        self._is_paused = False

        # Create and start worker
        self._worker = BatchWorker(
            files=self._files,
            output_dir=output_dir,
            db_path=db_path,
            passphrase=passphrase,
            theme=theme,
            continue_on_error=continue_on_error,
            validation_mode=validation_mode,
        )
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)

        QThreadPool.globalInstance().start(self._worker)

    def _on_progress(self, percent: int, message: str) -> None:
        """Handle progress signal from worker."""
        self._progress_bar.setValue(percent)

        if message.startswith("DOC_DONE:"):
            # Document completed
            idx = int(message.split(":")[1])
            self._docs_completed = idx + 1
            total = len(self._files)
            self._progress_label.setText(f"{self._docs_completed}/{total} ({percent}%)")

            # Update ETA
            elapsed = time.time() - self._batch_start_time
            if self._docs_completed > 0:
                avg_per_doc = elapsed / self._docs_completed
                remaining = (total - self._docs_completed) * avg_per_doc
                if remaining < 60:
                    eta_str = f"~{int(remaining)} secondes"
                else:
                    eta_str = f"~{int(remaining / 60)} minutes"
                self._eta_label.setText(f"Temps estimé restant : {eta_str}")

            # Update document table row
            if self._worker is not None:
                status_item = QTableWidgetItem("Traité")
                status_item.setForeground(Qt.GlobalColor.darkGreen)
                self._doc_table.setItem(idx, 3, status_item)

            # Mark next document as "En cours"
            if self._docs_completed < total:
                status_item = QTableWidgetItem("En cours")
                status_item.setForeground(Qt.GlobalColor.blue)
                self._doc_table.setItem(self._docs_completed, 3, status_item)
        else:
            # Pre-processing message (e.g., loading model)
            if self._docs_completed == 0 and self._files:
                status_item = QTableWidgetItem("En cours")
                status_item.setForeground(Qt.GlobalColor.blue)
                self._doc_table.setItem(0, 3, status_item)

    def _on_finished(self, result: object) -> None:
        """Handle batch completion."""
        if not isinstance(result, BatchResult):
            return

        self._worker = None
        self._batch_result = result

        # Update doc table with final results
        for doc_res in result.per_document_results:
            if doc_res.success:
                entities = str(doc_res.entities_detected)
                self._doc_table.setItem(doc_res.index, 2, QTableWidgetItem(entities))
                status_item = QTableWidgetItem("Traité")
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item = QTableWidgetItem("Erreur")
                status_item.setForeground(Qt.GlobalColor.red)
                status_item.setToolTip(doc_res.error_message)
            self._doc_table.setItem(doc_res.index, 3, status_item)

        self._progress_bar.setValue(100)
        self._progress_label.setText(f"{len(self._files)}/{len(self._files)} (100%)")
        self._eta_label.setText("")

        # Show summary
        self._show_summary(result)

    def _on_error(self, error_msg: str) -> None:
        """Handle fatal worker error."""
        self._worker = None

        # Clear cached passphrase on auth errors so user can retry
        if "passphrase" in error_msg.lower() or "decrypt" in error_msg.lower():
            self._main_window.cached_passphrase = None

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        ConfirmDialog.informational(
            "Erreur de traitement",
            error_msg,
            parent=self._main_window,
        ).exec()

        self._phases.setCurrentIndex(0)

    def _toggle_pause(self) -> None:
        if self._worker is None:
            return

        if not self._is_paused:
            self._worker.pause()
            self._is_paused = True
            self._pause_btn.setText("Reprendre")
            self._eta_label.setText("Traitement suspendu")
        else:
            self._worker.resume()
            self._is_paused = False
            self._pause_btn.setText("Suspendre")
            self._eta_label.setText("")

    def _cancel_batch(self) -> None:
        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        dlg = ConfirmDialog.destructive(
            "Annuler le traitement",
            "Les documents déjà traités seront conservés.",
            "Annuler le lot",
            parent=self._main_window,
        )
        if dlg.exec():
            if self._worker is not None:
                self._worker.cancel()

    # ------------------------------------------------------------------
    # Summary Phase Logic
    # ------------------------------------------------------------------

    def _show_summary(self, result: BatchResult) -> None:
        self._phases.setCurrentIndex(2)
        self._main_window.step_indicator.set_step(3)

        # Update cards
        self._update_card(self._card_docs, str(result.successful_files))
        self._update_card(self._card_entities, str(result.total_entities))
        self._update_card(self._card_new, str(result.new_entities))
        self._update_card(self._card_reused, str(result.reused_entities))
        self._update_card(self._card_errors, str(result.failed_files))

        # Update summary table
        self._summary_table.setRowCount(len(result.per_document_results))
        for row, doc_res in enumerate(result.per_document_results):
            time_str = f"{doc_res.processing_time:.1f}s"

            self._summary_table.setItem(row, 0, QTableWidgetItem(doc_res.filename))
            self._summary_table.setItem(
                row, 1, QTableWidgetItem(str(doc_res.entities_detected))
            )
            self._summary_table.setItem(row, 2, QTableWidgetItem(time_str))

            if doc_res.success:
                status_item = QTableWidgetItem("Traité")
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item = QTableWidgetItem("Erreur")
                status_item.setForeground(Qt.GlobalColor.red)
                status_item.setToolTip(doc_res.error_message)
            self._summary_table.setItem(row, 3, status_item)

    @staticmethod
    def _update_card(card: QWidget, value: str) -> None:
        val_label = card.layout().itemAt(0).widget()
        if isinstance(val_label, QLabel):
            val_label.setText(value)

    def _export_report(self) -> None:
        if not hasattr(self, "_batch_result"):
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le rapport",
            "batch_report.txt",
            "Texte (*.txt);;Tous (*)",
        )
        if not filepath:
            return

        result = self._batch_result
        lines = [
            "GDPR Pseudonymizer — Rapport de traitement par lot",
            "=" * 50,
            "",
            f"Documents traités : {result.successful_files}/{result.total_files}",
            f"Entités détectées : {result.total_entities}",
            f"  - Nouvelles : {result.new_entities}",
            f"  - Réutilisées : {result.reused_entities}",
            f"Erreurs : {result.failed_files}",
            f"Temps total : {result.total_time_seconds:.1f}s",
            "",
            "Détails par document :",
            "-" * 40,
        ]

        for doc_res in result.per_document_results:
            status = "OK" if doc_res.success else "ERREUR"
            line = (
                f"  {doc_res.filename}: {status} | "
                f"{doc_res.entities_detected} entités | "
                f"{doc_res.processing_time:.1f}s"
            )
            if not doc_res.success:
                line += f" | {doc_res.error_message}"
            lines.append(line)

        if result.errors:
            lines.extend(["", "Erreurs :", "-" * 40])
            for err in result.errors:
                lines.append(f"  • {err}")

        try:
            Path(filepath).write_text("\n".join(lines), encoding="utf-8")
            Toast.show_message("Rapport exporté.", self._main_window)
        except OSError:
            Toast.show_message(
                "Erreur lors de l'export.", self._main_window, duration_ms=4000
            )

    def _go_home(self) -> None:
        self._main_window.step_indicator.set_step(0)
        self._main_window.navigate_to("home")

    # -- Test accessors --

    @property
    def phases(self) -> QStackedWidget:
        return self._phases

    @property
    def folder_input(self) -> QLineEdit:
        return self._folder_input

    @property
    def output_input(self) -> QLineEdit:
        return self._output_input

    @property
    def file_table(self) -> QTableWidget:
        return self._file_table

    @property
    def start_button(self) -> QPushButton:
        return self._start_btn

    @property
    def progress_bar(self) -> QProgressBar:
        return self._progress_bar

    @property
    def progress_label(self) -> QLabel:
        return self._progress_label

    @property
    def eta_label(self) -> QLabel:
        return self._eta_label

    @property
    def doc_table(self) -> QTableWidget:
        return self._doc_table

    @property
    def pause_button(self) -> QPushButton:
        return self._pause_btn

    @property
    def cancel_button(self) -> QPushButton:
        return self._cancel_btn

    @property
    def summary_table(self) -> QTableWidget:
        return self._summary_table

    @property
    def export_button(self) -> QPushButton:
        return self._export_btn

    @property
    def file_count_label(self) -> QLabel:
        return self._file_count_label
