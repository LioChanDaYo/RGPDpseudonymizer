"""Entity sidebar panel for validation screen.

Displays a grouped entity list with status icons, checkboxes for
multi-selection, and bulk action buttons. Syncs bidirectionally
with EntityEditor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gdpr_pseudonymizer.gui.i18n import qarg

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
    from gdpr_pseudonymizer.validation.models import EntityReview

# Status icon mapping
_STATUS_ICONS: dict[str, str] = {
    "pending": "\u25cb",  # ○
    "confirmed": "\u2713",  # ✓
    "rejected": "\u2717",  # ✗
    "modified": "\u270e",  # ✎
    "added": "\u2713",  # ✓ (same as confirmed for display)
}

# Entity type display names and section headers
_TYPE_ORDER = ["PERSON", "LOCATION", "ORG"]
_TYPE_DISPLAY: dict[str, str] = {
    "PERSON": "PERSONNES",
    "LOCATION": "LIEUX",
    "ORG": "ORGANISATIONS",
}


class EntityPanel(QWidget):
    """Sidebar panel showing grouped entity list and bulk actions.

    Signals:
        entityClicked(str): entity_id when a row is clicked
        bulkActionRequested(str, list): action name + list of entity_ids
        selectionChanged(list): currently checked entity_ids
    """

    entity_clicked = Signal(str)
    bulk_action_requested = Signal(str, list)
    selection_changed = Signal(list)

    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.setMinimumWidth(250)
        self.setMaximumWidth(600)

        self._validation_state: GUIValidationState | None = None
        # Map list row index -> entity_id (skip section headers)
        self._row_entity_map: dict[int, str] = {}
        # Map entity_id -> list row index
        self._entity_row_map: dict[str, int] = {}
        # Checked entity_ids
        self._checked_ids: set[str] = set()
        self._filter_text = ""

        self._build_ui()
        self.retranslateUi()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header bar
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 8, 4)

        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._pending_label = QLabel()
        self._pending_label.setObjectName("pendingLabel")
        header_layout.addWidget(self._pending_label)

        layout.addWidget(header)

        # Hide rejected checkbox
        self._hide_rejected_cb = QCheckBox()
        self._hide_rejected_cb.setContentsMargins(8, 0, 8, 0)
        layout.addWidget(self._hide_rejected_cb)

        # Find field
        self._find_field = QLineEdit()
        self._find_field.setClearButtonEnabled(True)
        self._find_field.textChanged.connect(self._on_filter_changed)
        self._find_field.setContentsMargins(8, 0, 8, 0)
        layout.addWidget(self._find_field)

        # Entity list
        self._list_widget = QListWidget()
        self._list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        self._list_widget.setSpacing(2)
        # BUG-UX-002 fix: Checkbox styling now in global theme files
        # (resources/themes/light.qss and dark.qss)
        layout.addWidget(self._list_widget, stretch=1)

        # Bulk actions bar
        bulk_bar = QWidget()
        bulk_layout = QVBoxLayout(bulk_bar)
        bulk_layout.setContentsMargins(8, 4, 8, 8)
        bulk_layout.setSpacing(4)

        self._accept_sel_btn = QPushButton()
        self._accept_sel_btn.clicked.connect(self._on_bulk_accept)
        bulk_layout.addWidget(self._accept_sel_btn)

        self._reject_sel_btn = QPushButton()
        self._reject_sel_btn.setObjectName("secondaryButton")
        self._reject_sel_btn.clicked.connect(self._on_bulk_reject)
        bulk_layout.addWidget(self._reject_sel_btn)

        self._accept_type_btn = QPushButton()
        self._accept_type_btn.clicked.connect(self._on_accept_all_type)
        self._accept_type_btn.setObjectName("secondaryButton")
        bulk_layout.addWidget(self._accept_type_btn)

        self._accept_known_btn = QPushButton()
        self._accept_known_btn.clicked.connect(self._on_accept_known)
        self._accept_known_btn.setObjectName("secondaryButton")
        bulk_layout.addWidget(self._accept_known_btn)

        layout.addWidget(bulk_bar)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def _type_display(self, entity_type: str) -> str:
        """Return translated display name for an entity type."""
        return {
            "PERSON": self.tr("PERSONNES"),
            "LOCATION": self.tr("LIEUX"),
            "ORG": self.tr("ORGANISATIONS"),
        }.get(entity_type, entity_type)

    def retranslateUi(self) -> None:
        """Re-set all translatable UI text."""
        self._title_label.setText(self.tr("Entit\u00e9s (0)"))
        self._pending_label.setText(self.tr("Reste : 0"))
        self._hide_rejected_cb.setText(self.tr("Masquer les rejet\u00e9es"))
        self._find_field.setPlaceholderText(self.tr("Filtrer les entit\u00e9s..."))
        self._accept_known_btn.setText(self.tr("Accepter les d\u00e9j\u00e0 connues"))
        self._accept_type_btn.setText(
            qarg(self.tr("Tout accepter : %1"), self.tr("PERSONNES"))
        )
        self._update_bulk_button_counts()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_validation_state(self, state: GUIValidationState) -> None:
        """Bind to validation state and populate entity list."""
        self._validation_state = state
        self._checked_ids.clear()
        self.populate()

    def populate(self) -> None:
        """Rebuild the entity list from current validation state."""
        self._list_widget.clear()
        self._row_entity_map.clear()
        self._entity_row_map.clear()

        if self._validation_state is None:
            return

        total = 0
        for entity_type in _TYPE_ORDER:
            reviews = self._validation_state.get_entities_by_type(entity_type)
            if not reviews:
                continue

            # Filter
            if self._filter_text:
                reviews = [
                    r
                    for r in reviews
                    if self._filter_text.lower() in r.entity.text.lower()
                ]

            if not reviews:
                continue

            total += len(reviews)

            # Section header
            display = self._type_display(entity_type)
            header_item = QListWidgetItem(
                f"\u2500\u2500 {display} ({len(reviews)}) \u2500\u2500"
            )
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_font = QFont()
            header_font.setBold(True)
            header_font.setPointSize(10)
            header_item.setFont(header_font)
            header_item.setForeground(QColor("#757575"))
            self._list_widget.addItem(header_item)

            for review in reviews:
                row_idx = self._list_widget.count()
                item = self._create_entity_item(review)
                self._list_widget.addItem(item)
                self._row_entity_map[row_idx] = review.entity_id
                self._entity_row_map[review.entity_id] = row_idx

        self._title_label.setText(qarg(self.tr("Entit\u00e9s (%1)"), str(total)))
        self._update_pending_counter()
        self._update_bulk_button_counts()

    def highlight_entity(self, entity_id: str) -> None:
        """Scroll to and highlight an entity row."""
        row = self._entity_row_map.get(entity_id)
        if row is not None:
            item = self._list_widget.item(row)
            if item:
                self._list_widget.scrollToItem(item)
                self._list_widget.setCurrentItem(item)

    def update_entity_row(self, entity_id: str) -> None:
        """Update a single entity row after state change."""
        row = self._entity_row_map.get(entity_id)
        if row is None or self._validation_state is None:
            return
        review = self._validation_state.get_review(entity_id)
        if review is None:
            return
        item = self._list_widget.item(row)
        if item:
            status_icon = _STATUS_ICONS.get(review.state.value, "?")
            pseudonym = self._validation_state.get_pseudonym(entity_id)
            is_known = self._validation_state.is_entity_known(entity_id)
            known_badge = "  " + self.tr("d\u00e9j\u00e0 connu") if is_known else ""
            text = (
                f"{status_icon} {review.entity.text}{known_badge}\n"
                f"      \u2192 {pseudonym}"
            )
            item.setText(text)
        self._update_pending_counter()
        self._update_bulk_button_counts()

    @property
    def hide_rejected_checkbox(self) -> QCheckBox:
        return self._hide_rejected_cb

    @property
    def list_widget(self) -> QListWidget:
        return self._list_widget

    @property
    def find_field(self) -> QLineEdit:
        return self._find_field

    @property
    def accept_selection_button(self) -> QPushButton:
        return self._accept_sel_btn

    @property
    def reject_selection_button(self) -> QPushButton:
        return self._reject_sel_btn

    @property
    def accept_type_button(self) -> QPushButton:
        return self._accept_type_btn

    @property
    def accept_known_button(self) -> QPushButton:
        return self._accept_known_btn

    @property
    def title_label(self) -> QLabel:
        return self._title_label

    @property
    def pending_label(self) -> QLabel:
        return self._pending_label

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_entity_item(self, review: EntityReview) -> QListWidgetItem:
        """Create a QListWidgetItem for an entity."""
        status_icon = _STATUS_ICONS.get(review.state.value, "?")
        pseudonym = ""
        if self._validation_state:
            pseudonym = self._validation_state.get_pseudonym(review.entity_id)
        is_known = (
            self._validation_state.is_entity_known(review.entity_id)
            if self._validation_state
            else False
        )
        known_badge = "  " + self.tr("d\u00e9j\u00e0 connu") if is_known else ""

        text = (
            f"{status_icon} {review.entity.text}{known_badge}\n"
            f"      \u2192 {pseudonym}"
        )

        item = QListWidgetItem(text)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        checked = review.entity_id in self._checked_ids
        item.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        return item

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle entity row click — emit signal and update check state."""
        row = self._list_widget.row(item)
        entity_id = self._row_entity_map.get(row)
        if entity_id is None:
            return

        # Update checked state
        if item.checkState() == Qt.CheckState.Checked:
            self._checked_ids.add(entity_id)
        else:
            self._checked_ids.discard(entity_id)

        self._update_bulk_button_counts()
        self.selection_changed.emit(list(self._checked_ids))
        self.entity_clicked.emit(entity_id)

    def _on_filter_changed(self, text: str) -> None:
        """Re-populate when filter text changes."""
        self._filter_text = text
        self.populate()

    def _update_pending_counter(self) -> None:
        """Update 'Reste : X' label."""
        if self._validation_state is None:
            return
        pending = self._validation_state.get_pending_count()
        if pending == 0:
            self._pending_label.setText(self.tr("Toutes v\u00e9rifi\u00e9es"))
            self._pending_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        else:
            self._pending_label.setText(qarg(self.tr("Reste : %1"), str(pending)))
            self._pending_label.setStyleSheet("")

    def _update_bulk_button_counts(self) -> None:
        """Update bulk action button labels with current counts."""
        n = len(self._checked_ids)
        self._accept_sel_btn.setText(
            qarg(self.tr("Accepter la s\u00e9lection (%1)"), str(n))
        )
        self._reject_sel_btn.setText(
            qarg(self.tr("Rejeter la s\u00e9lection (%1)"), str(n))
        )
        self._accept_sel_btn.setEnabled(n > 0)
        self._reject_sel_btn.setEnabled(n > 0)

    def _clear_all_checkboxes(self) -> None:
        """Uncheck all entity checkboxes in the list."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(Qt.CheckState.Unchecked)

    # ------------------------------------------------------------------
    # Bulk action slots
    # ------------------------------------------------------------------

    def _on_bulk_accept(self) -> None:
        ids = list(self._checked_ids)
        if ids:
            self.bulk_action_requested.emit("accept", ids)
            self._checked_ids.clear()
            self._clear_all_checkboxes()
            self._update_bulk_button_counts()

    def _on_bulk_reject(self) -> None:
        ids = list(self._checked_ids)
        if ids:
            self.bulk_action_requested.emit("reject", ids)
            self._checked_ids.clear()
            self._clear_all_checkboxes()
            self._update_bulk_button_counts()

    def _on_accept_all_type(self) -> None:
        """Accept all pending of the first visible type section."""
        if self._validation_state is None:
            return
        for entity_type in _TYPE_ORDER:
            reviews = self._validation_state.get_entities_by_type(entity_type)
            from gdpr_pseudonymizer.validation.models import EntityReviewState

            pending = [
                r.entity_id for r in reviews if r.state == EntityReviewState.PENDING
            ]
            if pending:
                self.bulk_action_requested.emit(f"accept_type:{entity_type}", pending)
                return

    def _on_accept_known(self) -> None:
        """Accept all known entities."""
        self.bulk_action_requested.emit("accept_known", [])
