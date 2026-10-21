"""Validation screen with entity editor, sidebar panel, and action bar.

Split-pane layout: 65% EntityEditor (left), 35% EntityPanel (right).
Manages bidirectional sync, context menu actions, undo/redo, bulk actions,
find bar, finalization flow, and first-use contextual hints.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt, QThreadPool, Signal
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

from gdpr_pseudonymizer.core.custom_pseudonym import (
    CustomPseudonymRefusal,
    Refusal,
    normalize_custom_pseudonym,
)
from gdpr_pseudonymizer.gui.accessibility.focus_manager import (
    setup_focus_order_validation,
)
from gdpr_pseudonymizer.gui.i18n import qarg
from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
from gdpr_pseudonymizer.gui.widgets.entity_editor import EntityEditor
from gdpr_pseudonymizer.gui.widgets.entity_panel import EntityPanel
from gdpr_pseudonymizer.gui.widgets.step_indicator import StepMode
from gdpr_pseudonymizer.utils.logger import get_logger
from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.main_window import MainWindow
    from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
    from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
    from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

logger = get_logger(__name__)


class ValidationScreen(QWidget):
    """Screen for interactive entity validation before pseudonymization."""

    # Signals for batch mode orchestration: (document index, validated list,
    # custom pseudonyms of the names sent; Story 10.11; the batch run, Story
    # 10.14, an object so that a context without one still emits)
    validation_complete = Signal(int, object, object, object)
    batch_cancel_requested = Signal()

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._validation_state: GUIValidationState | None = None
        self._detection_result: DetectionResult | None = None

        # Batch mode state
        self._batch_mode = False
        self._doc_index = 0
        self._total_docs = 0
        # Story 10.14: the batch run of the document shown (None outside one),
        # and whether a single document is being written.
        self._run_id: int | None = None
        self._finalizing = False

        self._build_ui()
        self._connect_shortcuts()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Batch mode header bar (hidden in single-doc mode)
        self._batch_header = QWidget()
        batch_header_layout = QHBoxLayout(self._batch_header)
        batch_header_layout.setContentsMargins(16, 8, 16, 8)

        self._prev_btn = QPushButton()
        self._prev_btn.setObjectName("secondaryButton")
        self._prev_btn.clicked.connect(self._on_prev_doc)
        self._prev_btn.setAccessibleName(self.tr("Document précédent"))
        self._prev_btn.setAccessibleDescription(
            self.tr("Affiche le document précédemment validé")
        )
        batch_header_layout.addWidget(self._prev_btn)

        batch_header_layout.addStretch()

        self._doc_indicator = QLabel("")
        self._doc_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._doc_indicator.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._doc_indicator.setAccessibleName(self.tr("Indicateur de document"))
        self._doc_indicator.setAccessibleDescription(
            self.tr("Affiche le numéro du document en cours dans le lot")
        )
        batch_header_layout.addWidget(self._doc_indicator)

        batch_header_layout.addStretch()

        self._next_btn = QPushButton()
        self._next_btn.setObjectName("secondaryButton")
        self._next_btn.clicked.connect(self._on_next_doc)
        self._next_btn.setAccessibleName(self.tr("Document suivant"))
        self._next_btn.setAccessibleDescription(
            self.tr("Affiche le document suivant déjà validé")
        )
        batch_header_layout.addWidget(self._next_btn)

        self._batch_header.setVisible(False)
        layout.addWidget(self._batch_header)

        # Batch mode line under the header (Story 10.10): shown only on a
        # document other than the one the batch waits on.
        self._batch_notice = QLabel("")
        self._batch_notice.setObjectName("batchDocumentNotice")
        self._batch_notice.setWordWrap(True)
        self._batch_notice.setContentsMargins(16, 0, 16, 8)
        self._batch_notice.setVisible(False)
        layout.addWidget(self._batch_notice)

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
        # Accessibility support (AC2 - Task 3.5)
        self._finalize_progress.setAccessibleName(
            self.tr("Progression de la finalisation")
        )
        self._finalize_progress.setAccessibleDescription(
            self.tr(
                "Barre de progression indiquant l'avancement de la génération du document final"
            )
        )
        layout.addWidget(self._finalize_progress)

        self._finalize_label = QLabel("")
        self._finalize_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._finalize_label.setVisible(False)
        layout.addWidget(self._finalize_label)

        # Bottom action bar
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 8, 16, 8)

        # "Annuler le lot" button — batch mode only (Task 3.6)
        self._batch_cancel_btn = QPushButton()
        self._batch_cancel_btn.setObjectName("secondaryButton")
        self._batch_cancel_btn.clicked.connect(self._on_batch_cancel)
        self._batch_cancel_btn.setAccessibleName(self.tr("Annuler le lot"))
        self._batch_cancel_btn.setAccessibleDescription(
            self.tr("Annule l'ensemble du traitement par lot")
        )
        self._batch_cancel_btn.setVisible(False)
        action_layout.addWidget(self._batch_cancel_btn)

        self._back_btn = QPushButton()
        self._back_btn.setObjectName("secondaryButton")
        self._back_btn.clicked.connect(self._on_back)
        # Accessibility support (AC2 - Task 4.2)
        self._back_btn.setAccessibleName(self.tr("Retour à l'analyse"))
        self._back_btn.setAccessibleDescription(
            self.tr("Retourne à l'écran d'analyse (les modifications seront perdues)")
        )
        action_layout.addWidget(self._back_btn)

        action_layout.addStretch()

        # Status summary
        self._status_label = QLabel("")
        self._status_label.setObjectName("secondaryLabel")
        action_layout.addWidget(self._status_label)

        action_layout.addStretch()

        self._finalize_btn = QPushButton()
        self._finalize_btn.clicked.connect(self._on_finalize)
        # Accessibility support (AC2 - Task 4.2)
        self._finalize_btn.setAccessibleName(self.tr("Finaliser la pseudonymisation"))
        self._finalize_btn.setAccessibleDescription(
            self.tr("Lance la pseudonymisation du document avec les entités validées")
        )
        action_layout.addWidget(self._finalize_btn)

        layout.addWidget(action_bar)

        # Wire signals
        self._connect_signals()

        # Set translatable text
        self.retranslateUi()

        # Configure keyboard navigation
        setup_focus_order_validation(self)

    def retranslateUi(self) -> None:
        """Re-set all translatable static UI text."""
        self._back_btn.setText(self.tr("\u25c0 Retour"))

        # Batch mode navigation buttons
        self._prev_btn.setText(self.tr("\u25c0 Précédent"))
        self._next_btn.setText(self.tr("Suivant \u25b6"))
        self._batch_cancel_btn.setText(self.tr("Annuler le lot"))
        # Text approved by Lionel on 2026-10-14 (Story 10.10 AC12).
        self._batch_notice.setText(
            self.tr(
                "Ce document a déjà été validé. Les modifications faites ici "
                "ne seront pas appliquées. Revenez au document en attente de "
                "validation avec le bouton Suivant."
            )
        )

        # Finalize button text depends on batch mode state (CODE-003)
        if self._batch_mode:
            if self._doc_index >= self._total_docs - 1:
                self._finalize_btn.setText(self.tr("Valider et terminer \u25b6"))
            else:
                self._finalize_btn.setText(self.tr("Valider et continuer \u25b6"))
        else:
            self._finalize_btn.setText(self.tr("Finaliser \u25b6"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

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

        # Hide rejected toggle (both editor highlights and panel list)
        self._panel.hide_rejected_checkbox.toggled.connect(
            self._editor.set_hide_rejected
        )
        self._panel.hide_rejected_checkbox.toggled.connect(
            self._panel.set_hide_rejected
        )

        # Hide confirmed toggle (both editor highlights and panel list)
        self._panel.hide_confirmed_checkbox.toggled.connect(
            self._editor.set_hide_confirmed
        )
        self._panel.hide_confirmed_checkbox.toggled.connect(
            self._panel.set_hide_confirmed
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

        # Bulk actions (AC1)
        # Note: Tab/Shift+Tab, Enter, Delete handled by EntityEditor navigation mode
        self._accept_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        self._accept_all_shortcut.activated.connect(self._on_accept_all)

        self._reject_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        self._reject_all_shortcut.activated.connect(self._on_reject_all)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_validation(self, detection_result: DetectionResult) -> None:
        """Initialize validation of a single document with detection results.

        This is the single-document entry (``processing.py``: Ctrl+O, the
        recent files, the home screen). It leaves any batch mode left by an
        earlier or a waiting batch first, so the document's list goes to its
        own finalization and never to the batch screen (Story 10.10 AC11).

        Args:
            detection_result: Result from DetectionWorker
        """
        self._batch_mode = False
        self._run_id = None
        self._batch_header.setVisible(False)
        self._batch_cancel_btn.setVisible(False)
        self._batch_notice.setVisible(False)
        self._back_btn.setVisible(True)
        self.retranslateUi()
        self._begin_review(detection_result)

    def _begin_review(self, detection_result: DetectionResult) -> None:
        """Build a new review state for a document and show it."""
        self._detection_result = detection_result

        # Create validation state
        self._validation_state = GUIValidationState(self)
        self._validation_state.init_from_detection_result(
            detection_result, rows_per_place=self._batch_mode
        )

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
        self._set_review_enabled(True)

        # First-use hints
        self._maybe_show_hints()

    def set_context(self, **kwargs: object) -> None:
        """Accept navigation context for batch mode validation.

        Supported kwargs:
            entities: list[DetectedEntity]
            document_text: str
            document_path: str
            pseudonym_previews: dict[CandidateKey, str] (from candidate_key)
            db_path: str
            passphrase: str
            batch_mode: bool (default False)
            doc_index: int (0-based)
            total_docs: int
        """
        from typing import Any

        kw: dict[str, Any] = dict(kwargs)

        self._batch_mode = bool(kw.get("batch_mode", False))
        self._doc_index = int(kw.get("doc_index", 0))
        self._total_docs = int(kw.get("total_docs", 0))
        # Story 10.14: the batch run the document belongs to
        run_id = kw.get("run_id")
        self._run_id = run_id if self._batch_mode and isinstance(run_id, int) else None

        # Update batch mode widget visibility
        self._batch_header.setVisible(self._batch_mode)
        self._batch_cancel_btn.setVisible(self._batch_mode)
        self._back_btn.setVisible(not self._batch_mode)

        if self._batch_mode:
            # Update doc indicator and navigation button visibility
            self._update_batch_nav_state()

        # Update finalize button text
        self.retranslateUi()

        # Build a DetectionResult-like object for start_validation
        entities = kw.get("entities", [])
        document_text = str(kw.get("document_text", ""))
        document_path = str(kw.get("document_path", ""))
        pseudonym_previews = kw.get("pseudonym_previews", {})
        db_path = str(kw.get("db_path", ""))
        passphrase = str(kw.get("passphrase", ""))

        from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult

        detection_result = DetectionResult(
            detected_entities=entities,
            document_text=document_text,
            input_file=document_path,
            db_path=db_path,
            passphrase=passphrase,
            theme=self._main_window.config.get("default_theme", "neutral"),
            pseudonym_previews=pseudonym_previews,
            entity_type_counts={},
            detection_time_seconds=0.0,
        )

        # Story 10.10: in batch mode each document keeps its review state for
        # the batch run. A document shown before is re-attached as it was left
        # (decisions, memory of each row, undo history), with no rebuild and
        # no known-entity pass; a document shown for the first time is built
        # and kept.
        batch = self._batch_screen() if self._batch_mode else None
        kept = (
            batch.review_state(self._doc_index, self._run_id)
            if batch is not None
            else None
        )
        if kept is not None:
            self._attach_review(kept, detection_result)
        else:
            self._begin_review(detection_result)
            if batch is not None and self._validation_state is not None:
                batch.store_review_state(
                    self._doc_index, self._validation_state, self._run_id
                )
        self._apply_batch_document_rule()

        # Reconfigure focus order with batch widgets
        setup_focus_order_validation(self)

    def _attach_review(
        self, state: GUIValidationState, detection_result: DetectionResult
    ) -> None:
        """Show a document's kept review state again (Story 10.10).

        The state's signals were connected once, when it was built.
        """
        self._detection_result = detection_result
        self._validation_state = state
        self._editor.set_validation_state(state)
        self._panel.set_validation_state(state)
        self._update_status_label()
        self._finalize_progress.setVisible(False)
        self._finalize_label.setVisible(False)
        self._back_btn.setEnabled(True)
        self._set_review_enabled(True)

    def _batch_screen(self) -> BatchScreen | None:
        """The main window's batch screen, if there is one."""
        batch_idx = self._main_window._screens.get("batch")
        if batch_idx is None:
            return None
        widget = self._main_window.stack.widget(batch_idx)
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

        return widget if isinstance(widget, BatchScreen) else None

    def _is_awaiting_document(self) -> bool:
        """Whether the shown review is the one the batch worker waits on.

        The shown document must be the waiting one, and the review shown
        must be the one the batch screen keeps for it (the identity guard),
        so a single document shown with stale batch fields is refused too
        (Story 10.10 AC1). Story 10.14: the document's run must be the current
        run.
        """
        batch = self._batch_screen()
        return (
            batch is not None
            and self._validation_state is not None
            and (self._run_id is None or self._run_id == batch.run_id)
            and batch.awaiting_doc_index == self._doc_index
            and batch.review_state(self._doc_index, self._run_id)
            is self._validation_state
        )

    def _apply_batch_document_rule(self) -> None:
        """Only the waiting document can be validated (Story 10.10 AC1).

        On any other document of the batch, the finalize button is disabled
        and the line under the header says why; its actions stay available
        and their changes stay with that document's review.
        """
        if not self._batch_mode:
            self._batch_notice.setVisible(False)
            return
        awaiting = self._is_awaiting_document()
        self._finalize_btn.setEnabled(awaiting)
        self._batch_notice.setVisible(not awaiting)

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

    @property
    def batch_mode(self) -> bool:
        return self._batch_mode

    @property
    def doc_index(self) -> int:
        return self._doc_index

    @property
    def total_docs(self) -> int:
        return self._total_docs

    @property
    def doc_indicator(self) -> QLabel:
        return self._doc_indicator

    @property
    def prev_button(self) -> QPushButton:
        return self._prev_btn

    @property
    def next_button(self) -> QPushButton:
        return self._next_btn

    @property
    def batch_cancel_button(self) -> QPushButton:
        return self._batch_cancel_btn

    @property
    def batch_header(self) -> QWidget:
        return self._batch_header

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------

    def _handle_entity_action(self, entity_id: str, action: str) -> None:
        """Route entity actions from editor/navigation to validation state."""
        # Story 10.14 AC5: nothing reaches the review while it is written.
        if self._validation_state is None or self._finalizing:
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
        if self._validation_state is None or self._finalizing:
            return
        doc_text = self._validation_state.session.document_text
        text = doc_text[start_pos:end_pos]
        self._validation_state.add_entity(text, entity_type, start_pos, end_pos)

    def _handle_bulk_action(
        self, action: str, entity_ids: list[str], alone: bool = True
    ) -> None:
        """Route bulk actions from panel to validation state.

        ``alone`` (Story 10.10): whether each accepted or rejected row's
        decision is the user's own, made on that place. True for the rows
        ticked in the list and for Ctrl+Shift+R (the default; Lionel,
        2026-10-14, "Stay rejected"); Ctrl+Shift+A passes False, so its
        accepts follow the group.
        """
        if self._validation_state is None or self._finalizing:
            return

        from gdpr_pseudonymizer.gui.widgets.toast import Toast

        if action == "accept":
            self._validation_state.bulk_accept(entity_ids, alone=alone)
            Toast.show_message(
                qarg(self.tr("%1 entités acceptées"), str(len(entity_ids))),
                self._main_window,
            )
        elif action == "reject":
            self._validation_state.bulk_reject(entity_ids, alone=alone)
            Toast.show_message(
                qarg(self.tr("%1 entités rejetées"), str(len(entity_ids))),
                self._main_window,
            )
        elif action.startswith("accept_type:"):
            entity_type = action.split(":", 1)[1]
            self._validation_state.accept_all_of_type(entity_type)
            Toast.show_message(
                qarg(self.tr("Toutes les entités %1 acceptées"), entity_type),
                self._main_window,
            )
        elif action == "accept_known":
            self._validation_state.accept_all_known()
            Toast.show_message(
                self.tr("Entités déjà connues acceptées"),
                self._main_window,
            )

    # ------------------------------------------------------------------
    # State change handlers
    # ------------------------------------------------------------------

    def _on_entity_state_changed(self, entity_id: str) -> None:
        """Update both widgets when an entity's state changes."""
        self._editor.refresh_all()
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
            qarg(
                self.tr(
                    "%1/%2 entités traitées | "
                    "%3 acceptées, "
                    "%4 rejetées, "
                    "%5 modifiées"
                ),
                str(reviewed),
                str(total),
                str(summary["accepted"]),
                str(summary["rejected"]),
                str(summary["modified"]),
            )
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

        current = review.user_modification or review.entity.text
        text, ok = QInputDialog.getText(
            self,
            self.tr("Modifier le texte de l'entité"),
            self.tr("Nouveau texte :"),
            text=current,
        )
        if ok and text and text != current:
            # The CLI's rule (Story 10.9): the edited text where it overlaps
            # the row's span, else the row's own span.
            doc_text = self._validation_state.session.document_text
            new_start, new_end = ValidationWorkflow._locate_modified_span(
                doc_text, review.entity, text
            )
            self._validation_state.modify_entity_text(
                entity_id, text, new_start, new_end
            )

    def _show_change_pseudonym_dialog(self, entity_id: str) -> None:
        """Show dialog to change pseudonym.

        Story 10.11: the pseudonym is normalized like a mapping key and
        checked (Lionel's Q1, Q2, Q-C, Q-D) against the mapping database,
        this document and the review's other custom pseudonyms. A refused
        pseudonym changes nothing; a message says why (Lionel's Q-A). OK on
        the pre-filled value without a change does nothing (Lionel's Q-H).
        """
        if self._validation_state is None:
            return
        current = self._validation_state.get_pseudonym(entity_id)
        text, ok = QInputDialog.getText(
            self,
            self.tr("Changer le pseudonyme"),
            self.tr("Nouveau pseudonyme :"),
            text=current,
        )
        if not (ok and text):
            return
        review = self._validation_state.get_review(entity_id)
        if review is None:
            return
        pseudonym = normalize_custom_pseudonym(text, review.entity.entity_type)
        if not pseudonym:
            return
        # Lionel's Q-H (AC21): OK on the pre-filled pseudonym without a change
        # works like Cancel, compared in the form that would be stored and
        # written (extra spaces or a title are no change; capitals are)
        if pseudonym == normalize_custom_pseudonym(current, review.entity.entity_type):
            return
        detection = self._detection_result
        refusal = self._validation_state.custom_pseudonym_refusal(
            entity_id,
            pseudonym,
            detection.db_path if detection is not None else "",
            detection.passphrase if detection is not None else "",
        )
        if refusal is not None:
            from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

            ConfirmDialog.informational(
                self.tr("Changer le pseudonyme"),
                self._custom_refusal_text(refusal),
                parent=self._main_window,
            ).exec()
            return
        self._validation_state.change_pseudonym(entity_id, pseudonym)

    def _custom_refusal_text(self, refusal: Refusal) -> str:
        """The message of a refused custom pseudonym (Story 10.11).

        The texts Lionel approved on 2026-10-15 (Q-A), with their
        placeholders: the stored pseudonym (Q1); the real first or last
        name, its part and an example (Q-D); the pseudonym and the other
        name (Q2); the pseudonym and the word or words found (Q-C).
        """
        if refusal.reason is CustomPseudonymRefusal.ALREADY_STORED:
            return qarg(
                self.tr(
                    "Ce nom a déjà un pseudonyme enregistré dans votre base de "
                    "correspondances : « %1 ». Ce pseudonyme est conservé. Pour "
                    "en choisir un autre, supprimez ce nom de la base (menu "
                    "Outils › Base de correspondances...), puis traitez à "
                    "nouveau le document."
                ),
                refusal.other,
            )
        if refusal.reason is CustomPseudonymRefusal.PART_BOUND:
            if refusal.kind == "first":
                template = self.tr(
                    "Le prénom « %1 » est déjà remplacé par « %2 ». Votre "
                    "pseudonyme doit donc avoir « %2 » pour prénom, par "
                    "exemple « %3 »."
                )
            else:
                template = self.tr(
                    "Le nom de famille « %1 » est déjà remplacé par « %2 ». "
                    "Votre pseudonyme doit donc avoir « %2 » pour nom de "
                    "famille, par exemple « %3 »."
                )
            return qarg(template, refusal.other, refusal.required, refusal.example)
        if refusal.reason is CustomPseudonymRefusal.PSEUDONYM_TAKEN:
            return qarg(
                self.tr(
                    "« %1 » (ou une partie de ce pseudonyme) est déjà utilisé "
                    "pour un autre nom : « %2 ». Deux noms différents ne "
                    "peuvent pas partager un pseudonyme : choisissez-en un "
                    "autre."
                ),
                refusal.pseudonym,
                refusal.other,
            )
        return qarg(
            self.tr(
                "« %2 » figure dans ce document ou dans votre base de "
                "correspondances : « %1 » pourrait être pris pour un vrai nom. "
                "Choisissez-en un autre."
            ),
            refusal.pseudonym,
            refusal.other,
        )

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _on_undo(self) -> None:
        if self._validation_state and not self._finalizing:
            self._validation_state.undo_stack.undo()
            from gdpr_pseudonymizer.gui.widgets.toast import Toast

            Toast.show_message(self.tr("Annulé"), self._main_window, duration_ms=1500)

    def _on_redo(self) -> None:
        if self._validation_state and not self._finalizing:
            self._validation_state.undo_stack.redo()
            from gdpr_pseudonymizer.gui.widgets.toast import Toast

            Toast.show_message(self.tr("Rétabli"), self._main_window, duration_ms=1500)

    # ------------------------------------------------------------------
    # Find
    # ------------------------------------------------------------------

    def _on_find(self) -> None:
        """Focus the panel's find field."""
        self._panel.find_field.setFocus()
        self._panel.find_field.selectAll()

    # ------------------------------------------------------------------
    # Bulk entity actions
    # ------------------------------------------------------------------

    def _on_accept_all(self) -> None:
        """Accept all pending entities (Ctrl+Shift+A)."""
        if self._validation_state is None:
            return

        from gdpr_pseudonymizer.validation.models import EntityReviewState

        # Get all pending entity IDs
        pending_ids = [
            review.entity_id
            for review in self._validation_state.get_all_entities()
            if review.state == EntityReviewState.PENDING
        ]

        if not pending_ids:
            return

        # Story 10.10: these accepts follow the group (not the user's own).
        self._handle_bulk_action("accept", pending_ids, alone=False)

    def _on_reject_all(self) -> None:
        """Reject all pending entities (Ctrl+Shift+R)."""
        if self._validation_state is None:
            return

        from gdpr_pseudonymizer.validation.models import EntityReviewState

        # Get all pending entity IDs
        pending_ids = [
            review.entity_id
            for review in self._validation_state.get_all_entities()
            if review.state == EntityReviewState.PENDING
        ]

        if not pending_ids:
            return

        self._handle_bulk_action("reject", pending_ids)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        """Navigate back to processing with confirmation."""
        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        dlg = ConfirmDialog.proceeding(
            self.tr("Retour à l'analyse"),
            self.tr("Vos modifications de validation seront perdues. Continuer ?"),
            self.tr("Continuer"),
            parent=self._main_window,
        )
        if dlg.exec():
            self._main_window.step_indicator.set_step(1)
            self._main_window.navigate_to("processing")

    def _on_prev_doc(self) -> None:
        """Navigate to previously validated document (batch mode).

        Reloads the full cached context (entities, document text, previews)
        into the editor/panel via set_context().
        """
        if not self._batch_mode or self._doc_index <= 0:
            return

        batch_idx = self._main_window._screens.get("batch")
        if batch_idx is not None:
            widget = self._main_window.stack.widget(batch_idx)
            from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

            if isinstance(widget, BatchScreen):
                prev_idx = self._doc_index - 1
                cached_ctx = widget._validation_contexts.get(prev_idx)
                if cached_ctx is not None:
                    self.set_context(**cached_ctx)

    def _on_next_doc(self) -> None:
        """Navigate forward through already-validated documents (batch mode).

        Reloads the full cached context (entities, document text, previews)
        into the editor/panel via set_context().
        """
        if not self._batch_mode:
            return

        batch_idx = self._main_window._screens.get("batch")
        if batch_idx is not None:
            widget = self._main_window.stack.widget(batch_idx)
            from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

            if isinstance(widget, BatchScreen):
                next_idx = self._doc_index + 1
                cached_ctx = widget._validation_contexts.get(next_idx)
                if cached_ctx is not None:
                    self.set_context(**cached_ctx)

    def _on_batch_cancel(self) -> None:
        """Cancel entire batch from ValidationScreen."""
        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        dlg = ConfirmDialog.destructive(
            self.tr("Annuler le lot"),
            self.tr(
                "Tous les documents traités seront annulés. "
                "Aucun fichier de sortie ne sera conservé."
            ),
            self.tr("Annuler le lot"),
            parent=self._main_window,
        )
        if dlg.exec():
            self.batch_cancel_requested.emit()

    def _update_batch_nav_state(self) -> None:
        """Update doc indicator and button visibility for current batch position."""
        self._doc_indicator.setText(
            qarg(
                self.tr("Document %1 de %2"),
                str(self._doc_index + 1),
                str(self._total_docs),
            )
        )
        self._prev_btn.setVisible(self._doc_index > 0)

        # Suivant is visible only if next doc has cached context (navigated backward)
        batch_idx = self._main_window._screens.get("batch")
        next_has_cache = False
        if batch_idx is not None:
            widget = self._main_window.stack.widget(batch_idx)
            from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

            if isinstance(widget, BatchScreen):
                next_has_cache = (self._doc_index + 1) in widget._validation_contexts

        self._next_btn.setVisible(next_has_cache)

        # Update finalize button text
        self.retranslateUi()

    def _on_finalize(self) -> None:
        """Trigger finalization flow or emit validation_complete in batch mode."""
        if self._validation_state is None:
            return

        if self._batch_mode:
            # In batch mode: emit the document's index and its validated
            # entities for BatchScreen orchestration. Only the document the
            # worker waits on can be validated (Story 10.10 AC1): a guard
            # behind the disabled button.
            if not self._is_awaiting_document():
                return
            validated = self._validation_state.get_validated_entities()
            if not self._confirm_names_left_in_clear(validated):
                return
            # Story 10.11: the custom pseudonyms of the names sent go with
            # the list (passed on to finalization only when there is one).
            # Story 10.14 AC4: copies made when the user confirms, of the list
            # the warning's count read, so nothing done in the kept review
            # afterwards changes them; the run goes with them (AC3).
            self.validation_complete.emit(
                self._doc_index,
                copy.deepcopy(validated),
                copy.deepcopy(self._validation_state.get_custom_pseudonyms()),
                self._run_id,
            )
            return

        if not self._confirm_names_left_in_clear(
            self._validation_state.expand_validated_entities()
        ):
            return

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        summary = self._validation_state.get_summary()
        msg = qarg(
            self.tr(
                "Vous avez accepté %1 entités, "
                "rejeté %2, "
                "ajouté %3 manuellement "
                "et modifié %4 pseudonymes.\n\n"
                "Continuer avec la pseudonymisation ?"
            ),
            str(summary["accepted"]),
            str(summary["rejected"]),
            str(summary["added"]),
            str(summary["modified"]),
        )

        dlg = ConfirmDialog.proceeding(
            self.tr("Résumé de validation"),
            msg,
            self.tr("Confirmer"),
            parent=self._main_window,
        )
        if not dlg.exec():
            return

        # Start finalization
        self._start_finalization()

    def _confirm_names_left_in_clear(self, sent: list[DetectedEntity]) -> bool:
        """Confirm pending names for Story 10.13 AC2, AC3 and AC5.

        Texts approved by Lionel on 2026-10-16.
        """
        if self._validation_state is None:
            return False
        count = self._validation_state.names_left_in_clear(sent)
        if count == 0:
            return True

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        dlg = ConfirmDialog(
            title=self.tr("Noms encore à vérifier"),
            message=qarg(
                self.tr(
                    "Noms encore à vérifier dans ce document : %1.\n"
                    "Un nom ni accepté ni rejeté n'est pas pseudonymisé : "
                    "il reste en clair dans le fichier de sortie.\n"
                    "Continuer quand même ?"
                ),
                str(count),
            ),
            confirm_label=self.tr("Continuer quand même"),
            cancel_label=self.tr("Annuler"),
            parent=self._main_window,
        )
        return bool(dlg.exec())

    def _start_finalization(self) -> None:
        """Launch FinalizationWorker with validated entities."""
        if self._validation_state is None or self._detection_result is None:
            return

        from gdpr_pseudonymizer.gui.workers.finalization_worker import (
            FinalizationWorker,
        )

        # Expand canonical entities back to ALL variant occurrences so
        # every position in the document gets pseudonymized (not just canonical).
        # Story 10.14 AC4: copies made when the user confirms, so an edit, an
        # undo or a type change made while the document is written cannot
        # change what is written.
        validated = copy.deepcopy(self._validation_state.expand_validated_entities())
        customs = copy.deepcopy(self._validation_state.get_custom_pseudonyms())

        self._finalize_btn.setEnabled(False)
        self._back_btn.setEnabled(False)
        # Story 10.14 AC5: the review cannot change while it is written.
        self._set_review_enabled(False)
        self._finalize_progress.setVisible(True)
        self._finalize_progress.setValue(0)
        self._finalize_label.setVisible(True)
        self._finalize_label.setText(self.tr("Pseudonymisation en cours..."))

        worker = FinalizationWorker(
            validated_entities=validated,
            document_text=self._validation_state.session.document_text,
            db_path=self._detection_result.db_path,
            passphrase=self._detection_result.passphrase,
            theme=self._detection_result.theme,
            input_path=self._detection_result.input_file,
            custom_pseudonyms=customs,
        )
        worker.signals.progress.connect(self._on_finalize_progress)
        worker.signals.finished.connect(self._on_finalize_finished)
        worker.signals.error.connect(self._on_finalize_error)

        QThreadPool.globalInstance().start(worker)

    def _set_review_enabled(self, enabled: bool) -> None:
        """Enable or disable the review while a single document is written.

        Story 10.14 AC5: the editor, the list and the screen's six shortcuts
        are disabled with "Finaliser" and "Retour", and enabled again if the
        finalization fails or when a review is shown.
        """
        self._finalizing = not enabled
        self._editor.setEnabled(enabled)
        self._panel.setEnabled(enabled)
        for shortcut in (
            self._undo_shortcut,
            self._redo_shortcut,
            self._redo_shortcut2,
            self._find_shortcut,
            self._accept_all_shortcut,
            self._reject_all_shortcut,
        ):
            shortcut.setEnabled(enabled)

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
        self._set_review_enabled(True)

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        ConfirmDialog.informational(
            self.tr("Erreur de pseudonymisation"),
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

        msg = self.tr(
            "• Les entités sont surlignées en couleur dans votre document\n"
            "• Vérifiez chaque entité dans le panneau à droite : "
            "accepter, rejeter ou modifier\n"
            "• Cliquez 'Finaliser' quand vous avez terminé la vérification"
        )
        dlg = ConfirmDialog.informational(
            self.tr("Bienvenue dans la validation"),
            msg,
            dismiss_label=self.tr("Compris"),
            parent=self._main_window,
        )
        dlg.exec()

        config["validation_hints_shown"] = True
        from gdpr_pseudonymizer.gui.config import save_gui_config

        save_gui_config(config)
