"""Database management screen for entity listing, search, deletion, and export.

Provides Article 17 RGPD-compliant entity deletion with audit logging.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
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

logger = get_logger(__name__)

# Entity type display info
ENTITY_TYPE_LABELS: dict[str, str] = {
    "PERSON": "\U0001f464",  # 👤
    "LOCATION": "\U0001f4cd",  # 📍
    "ORG": "\U0001f3e2",  # 🏢
}


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

        self._build_ui()

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
        db_row.addWidget(self._db_combo, stretch=1)

        self._browse_btn = QPushButton()
        self._browse_btn.setObjectName("secondaryButton")
        self._browse_btn.clicked.connect(self._browse_db)
        db_row.addWidget(self._browse_btn)

        self._open_btn = QPushButton()
        self._open_btn.clicked.connect(self._open_database)
        db_row.addWidget(self._open_btn)

        layout.addLayout(db_row)

        # DB info line
        self._info_label = QLabel("")
        self._info_label.setObjectName("secondaryLabel")
        layout.addWidget(self._info_label)

        # Search + filter row
        filter_row = QHBoxLayout()
        self._search_field = QLineEdit()
        self._search_field.textChanged.connect(self._on_search_changed)
        filter_row.addWidget(self._search_field, stretch=1)

        self._type_filter = QComboBox()
        self._type_filter.addItem("", "")
        self._type_filter.addItem("", "PERSON")
        self._type_filter.addItem("", "LOCATION")
        self._type_filter.addItem("", "ORG")
        self._type_filter.currentIndexChanged.connect(self._on_filter_changed)
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
        action_row.addWidget(self._delete_btn)

        self._export_btn = QPushButton()
        self._export_btn.setObjectName("secondaryButton")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        action_row.addWidget(self._export_btn)

        layout.addLayout(action_row)

        # Populate recent databases
        self._populate_recent_databases()

        # Set translatable text
        self.retranslateUi()

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

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

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

    def _load_entities(self) -> None:
        """Load all entities from the database."""
        try:
            from gdpr_pseudonymizer.data.database import open_database
            from gdpr_pseudonymizer.data.repositories.mapping_repository import (
                SQLiteMappingRepository,
            )

            with open_database(self._db_path, self._passphrase) as db_session:
                repo = SQLiteMappingRepository(db_session)
                self._entities = repo.find_all()

                # Get DB info
                db_file = Path(self._db_path)
                created = datetime.fromtimestamp(db_file.stat().st_ctime)
                created_str = created.strftime("%d/%m/%Y")

                from gdpr_pseudonymizer.data.repositories.audit_repository import (
                    AuditRepository,
                )

                audit_repo = AuditRepository(db_session.session)
                last_ops = audit_repo.find_operations(limit=1)
                if last_ops:
                    last_op_time = last_ops[0].timestamp
                    # DB stores naive UTC timestamps; make aware for subtraction
                    if last_op_time.tzinfo is None:
                        last_op_time = last_op_time.replace(tzinfo=timezone.utc)
                    delta = datetime.now(timezone.utc) - last_op_time
                    if delta.days == 0:
                        last_op_str = self.tr("aujourd'hui")
                    elif delta.days == 1:
                        last_op_str = self.tr("hier")
                    else:
                        last_op_str = qarg(self.tr("il y a %1 jours"), str(delta.days))
                else:
                    last_op_str = self.tr("aucune")

            self._info_label.setText(
                qarg(
                    self.tr("Créée le %1 — %2 entités — Dernière opération : %3"),
                    created_str,
                    str(len(self._entities)),
                    last_op_str,
                )
            )
            self._export_btn.setEnabled(len(self._entities) > 0)
            self._populate_entity_table()

        except ValueError:
            # Clear cached passphrase so user can retry
            if (
                self._main_window.cached_passphrase is not None
                and self._main_window.cached_passphrase[0] == self._db_path
            ):
                self._main_window.cached_passphrase = None
            Toast.show_message(
                self.tr("Phrase secrète incorrecte."),
                self._main_window,
                duration_ms=4000,
            )
        except Exception as e:
            logger.error("db_load_failed", error=str(e))
            Toast.show_message(
                self.tr("Impossible d'ouvrir la base de données."),
                self._main_window,
                duration_ms=4000,
            )

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
        self._apply_filters()

    def _on_filter_changed(self, _index: int) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        search = self._search_field.text().strip()
        type_filter = self._type_filter.currentData()

        if not search and not type_filter:
            self._populate_entity_table()
            return

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
    # Deletion (Article 17 RGPD)
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

        # Perform deletion
        try:
            from gdpr_pseudonymizer.data.database import open_database
            from gdpr_pseudonymizer.data.models import Operation
            from gdpr_pseudonymizer.data.repositories.audit_repository import (
                AuditRepository,
            )
            from gdpr_pseudonymizer.data.repositories.mapping_repository import (
                SQLiteMappingRepository,
            )

            deleted_count = 0
            with open_database(self._db_path, self._passphrase) as db_session:
                repo = SQLiteMappingRepository(db_session)
                audit_repo = AuditRepository(db_session.session)

                for entity_id in list(self._selected_ids):
                    deleted = repo.delete_entity_by_id(entity_id)
                    if deleted:
                        deleted_count += 1

                # Log ERASURE operation
                audit_repo.log_operation(
                    Operation(
                        operation_type="ERASURE",
                        files_processed=[],
                        model_name="gui",
                        model_version="1.0",
                        theme_selected="",
                        entity_count=deleted_count,
                        processing_time_seconds=0.0,
                        success=True,
                    )
                )

            Toast.show_message(
                qarg(
                    self.tr("%1 correspondance(s) supprimée(s)"),
                    str(deleted_count),
                ),
                self._main_window,
            )

            # Reload entities
            self._load_entities()

        except Exception as e:
            logger.error("entity_deletion_failed", error=str(e))
            Toast.show_message(
                self.tr("Erreur lors de la suppression."),
                self._main_window,
                duration_ms=4000,
            )

    # ------------------------------------------------------------------
    # Export
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

        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "entity_id",
                        "entity_type",
                        "full_name",
                        "pseudonym_full",
                        "first_seen",
                    ]
                )
                for entity in self._entities:
                    ts = ""
                    if entity.first_seen_timestamp:
                        ts = entity.first_seen_timestamp.isoformat()
                    writer.writerow(
                        [
                            entity.id[:8] if entity.id else "",
                            entity.entity_type,
                            entity.full_name,
                            entity.pseudonym_full,
                            ts,
                        ]
                    )

            Toast.show_message(self.tr("Export CSV terminé."), self._main_window)

        except OSError as e:
            logger.error("csv_export_failed", error=str(e))
            Toast.show_message(
                self.tr("Erreur lors de l'export."),
                self._main_window,
                duration_ms=4000,
            )

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
