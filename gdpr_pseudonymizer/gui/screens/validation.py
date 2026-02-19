"""Validation screen with entity editor, sidebar panel, and action bar.

Split-pane layout: 65% EntityEditor (left), 35% EntityPanel (right).
Manages bidirectional sync, context menu actions, undo/redo, bulk actions,
find bar, finalization flow, and first-use contextual hints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.gui.widgets.entity_panel import EntityPanel
from gdpr_pseudonymizer.gui.widgets.step_indicator import StepMode
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow
    from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult

logger = get_logger(__name__)


class ValidationScreen(QWidget):
    """Screen for interactive entity validation before pseudonymization."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._validation_state: GUIValidationState | None = None
        self._detection_result: DetectionResult | None = None

        self._build_ui()
        self._connect_shortcuts()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter: editor | panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._editor = EntityEditor(self)
        self._panel = EntityPanel(self)

        self._splitter.addWidget(self._editor)
        self._splitter.addWidget(self._panel)
        self._splitter.setStretchFactor(0, 65)
        self._splitter.setStretchFactor(1, 35)

        layout.addWidget(self._splitter, stretch=1)

        # Finalization progress (hidden by default)
        self._finalize_progress = QProgressBar()
        self._finalize_progress.setMaximum(100)
        self._finalize_progress.setVisible(False)
        layout.addWidget(self._finalize_progress)

        self._finalize_label = QLabel("")
        self._finalize_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._finalize_label.setVisible(False)
        layout.addWidget(self._finalize_label)

        # Bottom action bar
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 8, 16, 8)

        self._back_btn = QPushButton("\u25c0 Retour")
        self._back_btn.setObjectName("secondaryButton")
        self._back_btn.clicked.connect(self._on_back)
        action_layout.addWidget(self._back_btn)

        action_layout.addStretch()

        # Status summary
        self._status_label = QLabel("")
        self._status_label.setObjectName("secondaryLabel")
        action_layout.addWidget(self._status_label)

        action_layout.addStretch()

        self._finalize_btn = QPushButton("Finaliser \u25b6")
        self._finalize_btn.clicked.connect(self._on_finalize)
        action_layout.addWidget(self._finalize_btn)

        layout.addWidget(action_bar)

        # Wire signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Wire bidirectional sync between editor and panel."""
        # Editor -> Panel
        self._editor.entity_selected.connect(self._panel.highlight_entity)

        # Panel -> Editor
        self._panel.entity_clicked.connect(self._editor.scroll_to_entity)

        # Entity actions from editor context menu
        self._editor.entity_action_requested.connect(self._handle_entity_action)

        # Add entity from editor text selection
        self._editor.add_entity_requested.connect(self._handle_add_entity)

        # Bulk actions from panel
        self._panel.bulk_action_requested.connect(self._handle_bulk_action)

        # Hide rejected toggle
        self._panel.hide_rejected_checkbox.toggled.connect(
            self._editor.set_hide_rejected
        )

    def _connect_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the validation screen."""
        # Undo / Redo
        self._undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self._undo_shortcut.activated.connect(self._on_undo)

        self._redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self._redo_shortcut.activated.connect(self._on_redo)

        self._redo_shortcut2 = QShortcut(QKeySequence("Ctrl+Y"), self)
        self._redo_shortcut2.activated.connect(self._on_redo)

        # Find
        self._find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._find_shortcut.activated.connect(self._on_find)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_validation(self, detection_result: DetectionResult) -> None:
        """Initialize validation with detection results.

        Args:
            detection_result: Result from DetectionWorker
        """
        self._detection_result = detection_result

        # Create validation state
        self._validation_state = GUIValidationState(self)
        self._validation_state.init_from_detection_result(detection_result)

        # Classify known entities
        self._validation_state.classify_known_entities(
            detection_result.db_path, detection_result.passphrase
        )

        # Wire state change signals
        self._validation_state.state_changed.connect(self._on_entity_state_changed)
        self._validation_state.entity_added.connect(self._on_entity_added)
        self._validation_state.entity_removed.connect(self._on_entity_removed)

        # Populate widgets
        self._editor.set_validation_state(self._validation_state)
        self._panel.set_validation_state(self._validation_state)

        # Step indicator
        self._main_window.step_indicator.set_mode(StepMode.SINGLE)
        self._main_window.step_indicator.set_step(2)

        # Update status bar
        self._update_status_label()

        # Hide finalization progress
        self._finalize_progress.setVisible(False)
        self._finalize_label.setVisible(False)
        self._finalize_btn.setEnabled(True)
        self._back_btn.setEnabled(True)

        # First-use hints
        self._maybe_show_hints()

    @property
    def editor(self) -> EntityEditor:
        return self._editor

    @property
    def panel(self) -> EntityPanel:
        return self._panel

    @property
    def validation_state(self) -> GUIValidationState | None:
        return self._validation_state

    @property
    def splitter(self) -> QSplitter:
        return self._splitter

    @property
    def back_button(self) -> QPushButton:
        return self._back_btn

    @property
    def finalize_button(self) -> QPushButton:
        return self._finalize_btn

    @property
    def status_label(self) -> QLabel:
        return self._status_label

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------

    def _handle_entity_action(self, entity_id: str, action: str) -> None:
        """Route entity actions from editor/navigation to validation state."""
        if self._validation_state is None:
            return

        if action == "accept":
            self._validation_state.accept_entity(entity_id)
        elif action == "reject":
            self._validation_state.reject_entity(entity_id)
        elif action == "modify_text":
            self._show_modify_text_dialog(entity_id)
        elif action == "change_pseudonym":
            self._show_change_pseudonym_dialog(entity_id)
        elif action.startswith("change_type:"):
            new_type = action.split(":", 1)[1]
            self._validation_state.change_entity_type(entity_id, new_type)

    def _handle_add_entity(
        self, entity_type: str, start_pos: int, end_pos: int
    ) -> None:
        """Handle 'Add as entity' from editor text selection."""
        if self._validation_state is None:
            return
        doc_text = self._validation_state.session.document_text
        text = doc_text[start_pos:end_pos]
        self._validation_state.add_entity(text, entity_type, start_pos, end_pos)

    def _handle_bulk_action(self, action: str, entity_ids: list[str]) -> None:
        """Route bulk actions from panel to validation state."""
        if self._validation_state is None:
            return

        from gdpr_pseudonymizer.gui.widgets.toast import Toast

        if action == "accept":
            self._validation_state.bulk_accept(entity_ids)
            Toast.show_message(
                f"{len(entity_ids)} entités acceptées",
                self._main_window,
            )
        elif action == "reject":
            self._validation_state.bulk_reject(entity_ids)
            Toast.show_message(
                f"{len(entity_ids)} entités rejetées",
                self._main_window,
            )
        elif action.startswith("accept_type:"):
            entity_type = action.split(":", 1)[1]
            self._validation_state.accept_all_of_type(entity_type)
            Toast.show_message(
                f"Toutes les entités {entity_type} acceptées",
                self._main_window,
            )
        elif action == "accept_known":
            self._validation_state.accept_all_known()
            Toast.show_message(
                "Entités déjà connues acceptées",
                self._main_window,
            )

    # ------------------------------------------------------------------
    # State change handlers
    # ------------------------------------------------------------------

    def _on_entity_state_changed(self, entity_id: str) -> None:
        """Update both widgets when an entity's state changes."""
        self._editor.refresh_entity(entity_id)
        self._panel.update_entity_row(entity_id)
        self._update_status_label()

    def _on_entity_added(self, entity_id: str) -> None:
        """Refresh both widgets after entity added."""
        self._editor.refresh_all()
        self._panel.populate()
        self._update_status_label()

    def _on_entity_removed(self, entity_id: str) -> None:
        """Refresh both widgets after entity removed (undo of add)."""
        self._editor.refresh_all()
        self._panel.populate()
        self._update_status_label()

    def _update_status_label(self) -> None:
        """Update the status bar summary text."""
        if self._validation_state is None:
            return
        summary = self._validation_state.get_summary()
        total = summary["total"]
        reviewed = (
            summary["accepted"]
            + summary["rejected"]
            + summary["modified"]
            + summary["added"]
        )
        self._status_label.setText(
            f"{reviewed}/{total} entités traitées | "
            f"{summary['accepted']} acceptées, "
            f"{summary['rejected']} rejetées, "
            f"{summary['modified']} modifiées"
        )

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _show_modify_text_dialog(self, entity_id: str) -> None:
        """Show dialog to modify entity text (EDGE-001: dialog-based)."""
        if self._validation_state is None:
            return
        review = self._validation_state.get_review(entity_id)
        if review is None:
            return

        text, ok = QInputDialog.getText(
            self,
            "Modifier le texte de l'entité",
            "Nouveau texte :",
            text=review.entity.text,
        )
        if ok and text and text != review.entity.text:
            # Find new text near original position
            doc_text = self._validation_state.session.document_text
            search_start = max(0, review.entity.start_pos - 200)
            search_end = min(len(doc_text), review.entity.end_pos + 200)
            search_region = doc_text[search_start:search_end]
            idx = search_region.find(text)
            if idx >= 0:
                new_start = search_start + idx
                new_end = new_start + len(text)
            else:
                new_start = review.entity.start_pos
                new_end = new_start + len(text)
            self._validation_state.modify_entity_text(
                entity_id, text, new_start, new_end
            )

    def _show_change_pseudonym_dialog(self, entity_id: str) -> None:
        """Show dialog to change pseudonym."""
        if self._validation_state is None:
            return
        current = self._validation_state.get_pseudonym(entity_id)
        text, ok = QInputDialog.getText(
            self,
            "Changer le pseudonyme",
            "Nouveau pseudonyme :",
            text=current,
        )
        if ok and text:
            self._validation_state.change_pseudonym(entity_id, text)

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _on_undo(self) -> None:
        if self._validation_state:
            self._validation_state.undo_stack.undo()
            from gdpr_pseudonymizer.gui.widgets.toast import Toast

            Toast.show_message("Annulé", self._main_window, duration_ms=1500)

    def _on_redo(self) -> None:
        if self._validation_state:
            self._validation_state.undo_stack.redo()
            from gdpr_pseudonymizer.gui.widgets.toast import Toast

            Toast.show_message("Rétabli", self._main_window, duration_ms=1500)

    # ------------------------------------------------------------------
    # Find
    # ------------------------------------------------------------------

    def _on_find(self) -> None:
        """Focus the panel's find field."""
        self._panel.find_field.setFocus()
        self._panel.find_field.selectAll()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        """Navigate back to processing with confirmation."""
        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        dlg = ConfirmDialog.proceeding(
            "Retour à l'analyse",
            "Vos modifications de validation seront perdues. Continuer ?",
            "Continuer",
            parent=self._main_window,
        )
        if dlg.exec():
            self._main_window.step_indicator.set_step(1)
            self._main_window.navigate_to("processing")

    def _on_finalize(self) -> None:
        """Trigger finalization flow with summary confirmation."""
        if self._validation_state is None:
            return

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        summary = self._validation_state.get_summary()
        msg = (
            f"Vous avez accepté {summary['accepted']} entités, "
            f"rejeté {summary['rejected']}, "
            f"ajouté {summary['added']} manuellement "
            f"et modifié {summary['modified']} pseudonymes.\n\n"
            "Continuer avec la pseudonymisation ?"
        )

        dlg = ConfirmDialog.proceeding(
            "Résumé de validation",
            msg,
            "Confirmer",
            parent=self._main_window,
        )
        if not dlg.exec():
            return

        # Start finalization
        self._start_finalization()

    def _start_finalization(self) -> None:
        """Launch FinalizationWorker with validated entities."""
        if self._validation_state is None or self._detection_result is None:
            return

        from gdpr_pseudonymizer.gui.workers.finalization_worker import (
            FinalizationWorker,
        )

        validated = self._validation_state.get_validated_entities()

        self._finalize_btn.setEnabled(False)
        self._back_btn.setEnabled(False)
        self._finalize_progress.setVisible(True)
        self._finalize_progress.setValue(0)
        self._finalize_label.setVisible(True)
        self._finalize_label.setText("Pseudonymisation en cours...")

        worker = FinalizationWorker(
            validated_entities=validated,
            document_text=self._validation_state.session.document_text,
            db_path=self._detection_result.db_path,
            passphrase=self._detection_result.passphrase,
            theme=self._detection_result.theme,
            input_path=self._detection_result.input_file,
        )
        worker.signals.progress.connect(self._on_finalize_progress)
        worker.signals.finished.connect(self._on_finalize_finished)
        worker.signals.error.connect(self._on_finalize_error)

        QThreadPool.globalInstance().start(worker)

    def _on_finalize_progress(self, percent: int, phase: str) -> None:
        if percent >= 0:
            self._finalize_progress.setValue(percent)
        self._finalize_label.setText(phase)

    def _on_finalize_finished(self, result: object) -> None:
        """Finalization completed — navigate to results."""
        from gdpr_pseudonymizer.gui.workers.processing_worker import GUIProcessingResult

        if not isinstance(result, GUIProcessingResult):
            return

        self._finalize_progress.setVisible(False)
        self._finalize_label.setVisible(False)

        self._main_window.step_indicator.set_step(3)

        # Navigate to results screen
        results_idx = self._main_window._screens.get("results")
        if results_idx is not None:
            widget = self._main_window.stack.widget(results_idx)
            from gdpr_pseudonymizer.gui.screens.results import ResultsScreen

            if isinstance(widget, ResultsScreen):
                widget.show_results(
                    result=result,
                    content=result.pseudonymized_content,
                    entity_mappings=result.entity_mappings,
                    original_path=(
                        self._detection_result.input_file
                        if self._detection_result
                        else ""
                    ),
                    temp_path=result.output_file,
                )
        self._main_window.navigate_to("results")

    def _on_finalize_error(self, error_msg: str) -> None:
        """Finalization failed — show error, re-enable buttons."""
        self._finalize_progress.setVisible(False)
        self._finalize_label.setVisible(False)
        self._finalize_btn.setEnabled(True)
        self._back_btn.setEnabled(True)

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        ConfirmDialog.informational(
            "Erreur de pseudonymisation",
            error_msg,
            parent=self._main_window,
        ).exec()

    # ------------------------------------------------------------------
    # First-use hints
    # ------------------------------------------------------------------

    def _maybe_show_hints(self) -> None:
        """Show first-use contextual hints if not already shown."""
        config = self._main_window.config
        if config.get("validation_hints_shown", False):
            return

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        msg = (
            "• Les entités sont surlignées en couleur dans votre document\n"
            "• Vérifiez chaque entité dans le panneau à droite : "
            "accepter, rejeter ou modifier\n"
            "• Cliquez 'Finaliser' quand vous avez terminé la vérification"
        )
        dlg = ConfirmDialog.informational(
            "Bienvenue dans la validation",
            msg,
            dismiss_label="Compris",
            parent=self._main_window,
        )
        dlg.exec()

        config["validation_hints_shown"] = True
        from gdpr_pseudonymizer.gui.config import save_gui_config

        save_gui_config(config)
