"""Database management screen for entity listing, search, deletion, and export.

Provides Article 17 RGPD-compliant entity deletion with audit logging.
All database operations run on background threads via DatabaseWorker.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.accessibility.focus_manager import (
    setup_focus_order_database,
)
from gdpr_pseudonymizer.gui.config import (
    add_recent_database,
    save_gui_config,
)
from gdpr_pseudonymizer.gui.i18n import qarg
from gdpr_pseudonymizer.gui.widgets.toast import Toast
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.data.models import Entity
    from gdpr_pseudonymizer.gui.main_window import MainWindow
    from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

logger = get_logger(__name__)

# Entity type display info
ENTITY_TYPE_LABELS: dict[str, str] = {
    "PERSON": "\U0001f464",  # 👤
    "LOCATION": "\U0001f4cd",  # 📍
    "ORG": "\U0001f3e2",  # 🏢
}

# Threshold: use background thread for search/filter above this count
_SEARCH_BACKGROUND_THRESHOLD = 200


class DatabaseScreen(QWidget):
    """Database management screen with entity listing, search, delete, export."""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._config = main_window.config

        self._entities: list[Entity] = []
        self._db_path = ""
        self._passphrase = ""
        self._selected_ids: set[str] = set()

        # Worker lifecycle
        self._current_worker: DatabaseWorker | None = None
        self._is_non_cancellable_op = False

        self._build_ui()

        # Debounced search timer (persistent, restartable)
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._apply_filters)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_context(self, **kwargs: Any) -> None:
        """Accept navigation context."""
        pass

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        self._back_btn = QPushButton()
        self._back_btn.setObjectName("secondaryButton")
        self._back_btn.clicked.connect(lambda: self._main_window.navigate_to("home"))
        header.addWidget(self._back_btn)
        header.addStretch()
        self._title = QLabel()
        self._title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(self._title)
        header.addStretch()
        layout.addLayout(header)

        # Database path
        db_row = QHBoxLayout()
        self._db_label = QLabel()
        self._db_label.setStyleSheet("font-weight: bold;")
        db_row.addWidget(self._db_label)

        self._db_combo = QComboBox()
        self._db_combo.setEditable(True)
        self._db_combo.setMinimumWidth(300)
        self._db_combo.setAccessibleName(self.tr("Chemin de la base de données"))
        self._db_combo.setAccessibleDescription(
            self.tr(
                "Sélectionner ou saisir le chemin vers le fichier de base de données"
            )
        )
        db_row.addWidget(self._db_combo, stretch=1)

        self._browse_btn = QPushButton()
        self._browse_btn.setObjectName("secondaryButton")
        self._browse_btn.clicked.connect(self._browse_db)
        self._browse_btn.setAccessibleName(self.tr("Parcourir les fichiers"))
        self._browse_btn.setAccessibleDescription(
            self.tr(
                "Ouvrir un dialogue pour sélectionner un fichier de base de données"
            )
        )
        db_row.addWidget(self._browse_btn)

        self._open_btn = QPushButton()
        self._open_btn.clicked.connect(self._open_database)
        self._open_btn.setAccessibleName(self.tr("Ouvrir la base de données"))
        self._open_btn.setAccessibleDescription(
            self.tr("Charger et afficher le contenu de la base de données sélectionnée")
        )
        db_row.addWidget(self._open_btn)

        layout.addLayout(db_row)

        # DB info line
        self._info_label = QLabel("")
        self._info_label.setObjectName("secondaryLabel")
        layout.addWidget(self._info_label)

        # Loading indicator (hidden by default)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate by default
        self._progress_bar.setVisible(False)
        self._progress_bar.setAccessibleName(self.tr("Indicateur de chargement"))
        self._progress_bar.setAccessibleDescription(
            self.tr("Opération en cours sur la base de données")
        )
        layout.addWidget(self._progress_bar)

        # Search + filter row
        filter_row = QHBoxLayout()
        self._search_field = QLineEdit()
        self._search_field.textChanged.connect(self._on_search_changed)
        self._search_field.setAccessibleName(self.tr("Recherche dans la base"))
        self._search_field.setAccessibleDescription(
            self.tr("Filtrer les entités par nom ou pseudonyme")
        )
        filter_row.addWidget(self._search_field, stretch=1)

        self._type_filter = QComboBox()
        self._type_filter.addItem("", "")
        self._type_filter.addItem("", "PERSON")
        self._type_filter.addItem("", "LOCATION")
        self._type_filter.addItem("", "ORG")
        self._type_filter.currentIndexChanged.connect(self._on_filter_changed)
        self._type_filter.setAccessibleName(self.tr("Filtre par type d'entité"))
        self._type_filter.setAccessibleDescription(
            self.tr("Filtrer les entités par type: Personne, Lieu, ou Organisation")
        )
        filter_row.addWidget(self._type_filter)

        layout.addLayout(filter_row)

        # Entity table
        self._entity_table = QTableWidget(0, 4)
        self._entity_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._entity_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._entity_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._entity_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self._entity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._entity_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._entity_table.cellChanged.connect(self._on_cell_changed)
        self._entity_table.setAccessibleName(self.tr("Table des correspondances"))
        self._entity_table.setAccessibleDescription(
            self.tr("Affiche les entités stockées avec leurs pseudonymes")
        )
        layout.addWidget(self._entity_table, stretch=1)

        # Status + action bar
        action_row = QHBoxLayout()

        self._status_label = QLabel("")
        self._status_label.setObjectName("secondaryLabel")
        action_row.addWidget(self._status_label)

        action_row.addStretch()

        self._delete_btn = QPushButton()
        self._delete_btn.setObjectName("secondaryButton")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete_selected)
        self._delete_btn.setAccessibleName(
            self.tr("Supprimer les entités sélectionnées")
        )
        self._delete_btn.setAccessibleDescription(
            self.tr(
                "Supprimer définitivement les entités cochées de la base de données"
            )
        )
        action_row.addWidget(self._delete_btn)

        self._export_btn = QPushButton()
        self._export_btn.setObjectName("secondaryButton")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        self._export_btn.setAccessibleName(self.tr("Exporter en CSV"))
        self._export_btn.setAccessibleDescription(
            self.tr("Exporter toutes les correspondances dans un fichier CSV")
        )
        action_row.addWidget(self._export_btn)

        layout.addLayout(action_row)

        # Populate recent databases
        self._populate_recent_databases()

        # Set translatable text
        self.retranslateUi()

        # Configure keyboard navigation
        setup_focus_order_database(self)

    def retranslateUi(self) -> None:
        """Re-set all translatable static UI text."""
        self._back_btn.setText(self.tr("\u25c0 Retour"))
        self._title.setText(self.tr("Base de correspondances"))
        self._db_label.setText(self.tr("Base de données :"))
        self._browse_btn.setText(self.tr("Parcourir..."))
        self._open_btn.setText(self.tr("Ouvrir"))
        self._search_field.setPlaceholderText(
            self.tr("Rechercher une entité ou un pseudonyme...")
        )
        self._type_filter.setItemText(0, self.tr("Tous les types"))
        self._type_filter.setItemText(1, "\U0001f464 PERSON")
        self._type_filter.setItemText(2, "\U0001f4cd LOCATION")
        self._type_filter.setItemText(3, "\U0001f3e2 ORG")
        self._entity_table.setHorizontalHeaderLabels(
            [
                "",
                self.tr("Type"),
                self.tr("Entité originale"),
                self.tr("Pseudonyme"),
            ]
        )
        self._status_label.setText(self.tr("0 correspondances"))
        self._delete_btn.setText(self.tr("Supprimer la sélection (0)"))
        self._export_btn.setText(self.tr("Exporter"))
        # Loading indicator i18n
        self._progress_bar.setAccessibleName(self.tr("Indicateur de chargement"))
        self._progress_bar.setAccessibleDescription(
            self.tr("Opération en cours sur la base de données")
        )

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Worker Lifecycle
    # ------------------------------------------------------------------

    def _cancel_current_worker(self) -> None:
        """Cancel the in-flight worker and discard its signals."""
        if self._current_worker is not None:
            self._current_worker.cancel()
            try:
                self._current_worker.signals.finished.disconnect()
            except (RuntimeError, SystemError):
                pass
            try:
                self._current_worker.signals.error.disconnect()
            except (RuntimeError, SystemError):
                pass
            try:
                self._current_worker.signals.progress.disconnect()
            except (RuntimeError, SystemError):
                pass
            self._current_worker = None

    def _start_worker(
        self,
        worker: DatabaseWorker,
        *,
        non_cancellable: bool = False,
    ) -> None:
        """Submit a worker to the global thread pool.

        Args:
            worker: The DatabaseWorker to run.
            non_cancellable: If True, disable interactive controls during operation.
        """
        from PySide6.QtCore import QThreadPool

        self._cancel_current_worker()
        self._current_worker = worker
        self._is_non_cancellable_op = non_cancellable

        # Show loading indicator
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(True)

        # Connect progress to update the bar
        worker.signals.progress.connect(self._on_progress)

        if non_cancellable:
            self._search_field.setEnabled(False)
            self._type_filter.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._export_btn.setEnabled(False)

        QThreadPool.globalInstance().start(worker)

    def _on_progress(self, percent: int, message: str) -> None:
        """Update progress bar from worker signal."""
        if percent >= 0:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(percent)
        else:
            self._progress_bar.setRange(0, 0)

    def _finish_operation(self) -> None:
        """Common cleanup after a worker operation completes."""
        self._progress_bar.setVisible(False)
        self._current_worker = None

        if self._is_non_cancellable_op:
            self._search_field.setEnabled(True)
            self._type_filter.setEnabled(True)
            # Re-enable buttons based on state
            self._update_status()
            self._export_btn.setEnabled(len(self._entities) > 0)
            self._is_non_cancellable_op = False

    # ------------------------------------------------------------------
    # Database Connection
    # ------------------------------------------------------------------

    def _populate_recent_databases(self) -> None:
        self._db_combo.clear()
        recent = self._config.get("recent_databases", [])
        for db_path in recent:
            self._db_combo.addItem(db_path)

        default_db = self._config.get("default_db_path", "")
        if default_db and default_db not in recent:
            self._db_combo.insertItem(0, default_db)

    def _browse_db(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner une base de correspondances"),
            "",
            self.tr("SQLite (*.db);;Tous (*)"),
        )
        if filepath:
            self._db_combo.setCurrentText(filepath)
            self._open_database()

    def _open_database(self) -> None:
        db_path = self._db_combo.currentText().strip()
        if not db_path:
            Toast.show_message(
                self.tr("Veuillez sélectionner une base de données."),
                self._main_window,
                duration_ms=3000,
            )
            return

        if not Path(db_path).exists():
            Toast.show_message(
                self.tr("La base de données n'existe pas."),
                self._main_window,
                duration_ms=3000,
            )
            return

        # Check passphrase cache
        cached = self._main_window.cached_passphrase
        if cached is not None and cached[0] == db_path:
            self._db_path = db_path
            self._passphrase = cached[1]
            self._load_entities()
            return

        # Prompt passphrase
        from gdpr_pseudonymizer.gui.widgets.passphrase_dialog import PassphraseDialog

        dialog = PassphraseDialog(
            file_directory=str(Path(db_path).parent),
            config=self._config,
            parent=self._main_window,
        )
        # Pre-select the known database path so the user only enters passphrase
        combo = dialog.db_combo
        insert_idx = max(0, combo.count() - 2)  # before special items
        combo.blockSignals(True)
        combo.insertItem(insert_idx, db_path, db_path)
        combo.setCurrentIndex(insert_idx)
        combo.blockSignals(False)

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        result = dialog.get_result()
        if result is None:
            return

        _, passphrase, remember = result
        if remember:
            self._main_window.cached_passphrase = (db_path, passphrase)

        self._db_path = db_path
        self._passphrase = passphrase

        # Add to recent databases
        add_recent_database(db_path, self._config)
        save_gui_config(self._config)
        self._populate_recent_databases()

        self._load_entities()

    # ------------------------------------------------------------------
    # Load Entities (Background)
    # ------------------------------------------------------------------

    def _load_entities(self) -> None:
        """Load all entities from the database on a background thread."""
        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        worker = DatabaseWorker("list", self._db_path, self._passphrase)
        worker.signals.finished.connect(self._on_entities_loaded)
        worker.signals.error.connect(self._on_db_error)
        self._start_worker(worker)

    def _on_entities_loaded(self, result: Any) -> None:
        """Handle successful entity load from background worker."""
        from gdpr_pseudonymizer.gui.workers.database_worker import ListEntitiesResult

        self._finish_operation()

        if not isinstance(result, ListEntitiesResult):
            return

        self._entities = result.entities

        self._info_label.setText(
            qarg(
                self.tr("Créée le %1 — %2 entités — Dernière opération : %3"),
                result.db_created_str,
                str(result.entity_count),
                result.last_op_str,
            )
        )
        self._export_btn.setEnabled(len(self._entities) > 0)
        self._populate_entity_table()

    def _on_db_error(self, message: str) -> None:
        """Handle error from any background database worker."""
        # Check passphrase flag before _finish_operation clears the worker ref
        is_passphrase_error = (
            self._current_worker is not None
            and self._current_worker.is_passphrase_error
        )

        self._finish_operation()

        # Clear cached passphrase on passphrase errors (flag-based, not string)
        if is_passphrase_error:
            if (
                self._main_window.cached_passphrase is not None
                and self._main_window.cached_passphrase[0] == self._db_path
            ):
                self._main_window.cached_passphrase = None

        Toast.show_message(message, self._main_window, duration_ms=4000)

    def _populate_entity_table(self, entities: list[Entity] | None = None) -> None:
        """Fill the entity table with (filtered) entities."""
        if entities is None:
            entities = self._entities

        self._entity_table.blockSignals(True)
        self._entity_table.setRowCount(len(entities))
        self._selected_ids.clear()

        for row, entity in enumerate(entities):
            # Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            check_item.setCheckState(Qt.CheckState.Unchecked)
            check_item.setData(Qt.ItemDataRole.UserRole, entity.id)
            self._entity_table.setItem(row, 0, check_item)

            # Type icon
            icon = ENTITY_TYPE_LABELS.get(entity.entity_type, "?")
            type_item = QTableWidgetItem(f"{icon} {entity.entity_type}")
            self._entity_table.setItem(row, 1, type_item)

            # Entity name
            self._entity_table.setItem(row, 2, QTableWidgetItem(entity.full_name))

            # Pseudonym
            self._entity_table.setItem(row, 3, QTableWidgetItem(entity.pseudonym_full))

        self._entity_table.blockSignals(False)
        self._update_status()

    # ------------------------------------------------------------------
    # Search / Filter
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str) -> None:
        self._search_timer.start()  # restart the 300ms countdown

    def _on_filter_changed(self, _index: int) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        search = self._search_field.text().strip()
        type_filter = self._type_filter.currentData()

        if not search and not type_filter:
            self._populate_entity_table()
            return

        # Use background worker for large datasets
        if len(self._entities) > _SEARCH_BACKGROUND_THRESHOLD:
            self._apply_filters_background(search, type_filter)
        else:
            self._apply_filters_inline(search, type_filter)

    def _apply_filters_inline(self, search: str, type_filter: str) -> None:
        """In-memory filtering for small datasets (GUI thread)."""
        filtered = self._entities
        if type_filter:
            filtered = [e for e in filtered if e.entity_type == type_filter]
        if search:
            search_lower = search.lower()
            filtered = [
                e
                for e in filtered
                if search_lower in e.full_name.lower()
                or search_lower in e.pseudonym_full.lower()
            ]
        self._populate_entity_table(filtered)

    def _apply_filters_background(self, search: str, type_filter: str) -> None:
        """Background filtering for large datasets (worker thread)."""
        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        worker = DatabaseWorker(
            "search",
            entities=list(self._entities),  # shallow copy for thread safety
            search_text=search,
            type_filter=type_filter,
        )
        worker.signals.finished.connect(self._on_search_complete)
        worker.signals.error.connect(self._on_db_error)
        self._start_worker(worker)

    def _on_search_complete(self, filtered_entities: Any) -> None:
        """Handle search results from background worker."""
        self._finish_operation()
        if isinstance(filtered_entities, list):
            self._populate_entity_table(filtered_entities)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_cell_changed(self, row: int, column: int) -> None:
        if column != 0:
            return
        item = self._entity_table.item(row, 0)
        if item is None:
            return
        entity_id = item.data(Qt.ItemDataRole.UserRole)
        if entity_id is None:
            return

        if item.checkState() == Qt.CheckState.Checked:
            self._selected_ids.add(entity_id)
        else:
            self._selected_ids.discard(entity_id)

        self._update_status()

    def _update_status(self) -> None:
        total = self._entity_table.rowCount()
        selected = len(self._selected_ids)
        self._status_label.setText(
            qarg(
                self.tr("%1 correspondances — %2 sélectionnées"),
                str(total),
                str(selected),
            )
        )
        self._delete_btn.setText(
            qarg(self.tr("Supprimer la sélection (%1)"), str(selected))
        )
        self._delete_btn.setEnabled(selected > 0)

    # ------------------------------------------------------------------
    # Deletion (Article 17 RGPD) — Background
    # ------------------------------------------------------------------

    def _delete_selected(self) -> None:
        if not self._selected_ids:
            return

        # Build confirmation list
        selected_entities = [e for e in self._entities if e.id in self._selected_ids]
        entity_lines = "\n".join(
            f"  \u2022 {e.full_name} \u2192 {e.pseudonym_full}"
            for e in selected_entities
        )
        count = len(selected_entities)

        from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog

        dlg = ConfirmDialog.destructive(
            qarg(self.tr("Supprimer %1 correspondances ?"), str(count)),
            qarg(
                self.tr(
                    "Les correspondances suivantes seront supprimées "
                    "de façon irréversible (Article 17 RGPD) :\n\n"
                    "%1"
                ),
                entity_lines,
            ),
            qarg(self.tr("Supprimer (%1)"), str(count)),
            parent=self._main_window,
        )
        if not dlg.exec():
            return

        # Submit deletion to background worker
        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        worker = DatabaseWorker(
            "delete",
            self._db_path,
            self._passphrase,
            entity_ids=list(self._selected_ids),
        )
        worker.signals.finished.connect(self._on_delete_complete)
        worker.signals.error.connect(self._on_db_error)
        self._start_worker(worker, non_cancellable=True)

    def _on_delete_complete(self, deleted_count: Any) -> None:
        """Handle deletion completion from background worker."""
        self._finish_operation()
        Toast.show_message(
            qarg(
                self.tr("%1 correspondance(s) supprimée(s)"),
                str(deleted_count),
            ),
            self._main_window,
        )
        # Reload entities
        self._load_entities()

    # ------------------------------------------------------------------
    # Export — Background
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Exporter les entités"),
            "entities_export.csv",
            self.tr("CSV (*.csv);;Tous (*)"),
        )
        if not filepath:
            return

        from gdpr_pseudonymizer.gui.workers.database_worker import DatabaseWorker

        worker = DatabaseWorker(
            "export",
            filepath=filepath,
            entities=list(self._entities),
        )
        worker.signals.finished.connect(self._on_export_complete)
        worker.signals.error.connect(self._on_db_error)
        self._start_worker(worker, non_cancellable=True)

    def _on_export_complete(self, _result: Any) -> None:
        """Handle CSV export completion."""
        self._finish_operation()
        Toast.show_message(self.tr("Export CSV terminé."), self._main_window)

    # -- Test accessors --

    @property
    def db_combo(self) -> QComboBox:
        return self._db_combo

    @property
    def open_button(self) -> QPushButton:
        return self._open_btn

    @property
    def search_field(self) -> QLineEdit:
        return self._search_field

    @property
    def type_filter(self) -> QComboBox:
        return self._type_filter

    @property
    def entity_table(self) -> QTableWidget:
        return self._entity_table

    @property
    def delete_button(self) -> QPushButton:
        return self._delete_btn

    @property
    def export_button(self) -> QPushButton:
        return self._export_btn

    @property
    def status_label(self) -> QLabel:
        return self._status_label

    @property
    def info_label(self) -> QLabel:
        return self._info_label

    @property
    def progress_bar(self) -> QProgressBar:
        return self._progress_bar
