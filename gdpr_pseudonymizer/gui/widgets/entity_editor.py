"""Entity-highlighted document editor for validation screen.

Read-only QTextEdit subclass that displays document text with color-coded
entity highlights, click detection, context menus, and keyboard navigation.
"""

from __future__ import annotations

import bisect
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QMenu, QTextEdit

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
    from gdpr_pseudonymizer.validation.models import EntityReview

# ── Entity color scheme ──────────────────────────────────────────────

_LIGHT_COLORS: dict[str, tuple[str, str]] = {
    "PERSON": ("#BBDEFB", "#0D47A1"),
    "LOCATION": ("#C8E6C9", "#1B5E20"),
    "ORG": ("#FFE0B2", "#E65100"),
}

_DARK_COLORS: dict[str, tuple[str, str]] = {
    "PERSON": ("#1A237E", "#90CAF9"),
    "LOCATION": ("#1B5E20", "#A5D6A7"),
    "ORG": ("#BF360C", "#FFCC80"),
}

_REJECTED_LIGHT = ("#FFCDD2", "#B71C1C")
_REJECTED_DARK = ("#4E342E", "#FFCDD2")


class EntityEditor(QTextEdit):
    """Read-only document editor with entity highlights and navigation.

    Signals:
        entitySelected(str): emitted when an entity is clicked, carries entity_id
        entityActionRequested(str, str): entity_id + action name
        addEntityRequested(str, int, int): entity_type, start_pos, end_pos
    """

    entity_selected = Signal(str)
    entity_action_requested = Signal(str, str)
    add_entity_requested = Signal(str, int, int)

    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)  # type: ignore[call-overload]
        self.setReadOnly(True)
        self.setMinimumWidth(400)
        self.setFont(QFont("Consolas", 11))
        self.setAccessibleName("Éditeur de document")
        self.setAccessibleDescription(
            "Affiche le document avec les entités surlignées en couleur"
        )

        self._validation_state: GUIValidationState | None = None
        # Sorted list of (start_pos, end_pos, entity_id) for click detection
        self._entity_ranges: list[tuple[int, int, str]] = []
        self._hide_rejected = False
        self._dark_theme = False

        # Navigation mode state
        self._nav_mode = False
        self._nav_index = -1  # index into _entity_ranges of focused entity
        self._nav_entity_ids: list[str] = []  # ordered entity_ids for navigation

        # Zoom
        self._zoom_pct = 100

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_validation_state(self, state: GUIValidationState) -> None:
        """Bind to a GUIValidationState and display its document."""
        self._validation_state = state
        self.setPlainText(state.session.document_text)
        self._rebuild_entity_ranges()
        self._apply_highlights()

    def set_dark_theme(self, dark: bool) -> None:
        """Switch between light and dark entity color scheme."""
        self._dark_theme = dark
        self._apply_highlights()

    def set_hide_rejected(self, hide: bool) -> None:
        """Toggle hiding of rejected entity highlights."""
        self._hide_rejected = hide
        self._apply_highlights()

    def refresh_entity(self, entity_id: str) -> None:
        """Re-apply highlights after a single entity's state changed."""
        self._apply_highlights()

    def refresh_all(self) -> None:
        """Full highlight rebuild (after add/remove entity)."""
        self._rebuild_entity_ranges()
        self._apply_highlights()

    def scroll_to_entity(self, entity_id: str) -> None:
        """Smooth-scroll to an entity's position in the document."""
        for start, _end, eid in self._entity_ranges:
            if eid == entity_id:
                cursor = self.textCursor()
                cursor.setPosition(start)
                self.setTextCursor(cursor)
                self.ensureCursorVisible()
                break

    @property
    def nav_mode(self) -> bool:
        return self._nav_mode

    # ------------------------------------------------------------------
    # Highlight engine
    # ------------------------------------------------------------------

    def _rebuild_entity_ranges(self) -> None:
        """Rebuild sorted entity ranges from validation state."""
        if self._validation_state is None:
            self._entity_ranges = []
            return
        ranges: list[tuple[int, int, str]] = []
        for review in self._validation_state.get_all_entities():
            ranges.append(
                (
                    review.entity.start_pos,
                    review.entity.end_pos,
                    review.entity_id,
                )
            )
        ranges.sort(key=lambda r: r[0])
        self._entity_ranges = ranges
        self._nav_entity_ids = [r[2] for r in ranges]

    def _apply_highlights(self) -> None:
        """Apply extra selections for all entities."""
        if self._validation_state is None:
            self.setExtraSelections([])
            return

        from gdpr_pseudonymizer.validation.models import EntityReviewState

        colors = _DARK_COLORS if self._dark_theme else _LIGHT_COLORS
        rejected_colors = _REJECTED_DARK if self._dark_theme else _REJECTED_LIGHT

        selections: list[QTextEdit.ExtraSelection] = []

        for start, end, entity_id in self._entity_ranges:
            review = self._validation_state.get_review(entity_id)
            if review is None:
                continue

            is_rejected = review.state == EntityReviewState.REJECTED
            if is_rejected and self._hide_rejected:
                continue

            # Determine colors
            if is_rejected:
                bg_hex, fg_hex = rejected_colors
            else:
                bg_hex, fg_hex = colors.get(
                    review.entity.entity_type, ("#E0E0E0", "#424242")
                )

            fmt = QTextCharFormat()
            bg_color = QColor(bg_hex)

            # Known (auto-accepted) entities at 50% opacity
            is_known = self._validation_state.is_entity_known(entity_id)
            if is_known and not is_rejected:
                bg_color.setAlpha(128)

            fmt.setBackground(bg_color)
            fmt.setForeground(QColor(fg_hex))

            if is_rejected:
                fmt.setFontStrikeOut(True)

            # BUG-UX-003 fix: Add green underline for accepted/known entities
            is_accepted = review.state in (
                EntityReviewState.CONFIRMED,
                EntityReviewState.ADDED,
            )
            if (is_accepted or is_known) and not is_rejected:
                underline_color = "#2E7D32" if not self._dark_theme else "#66BB6A"
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
                fmt.setUnderlineColor(QColor(underline_color))

            # Tooltip: pseudonym + type + confidence
            pseudonym = self._validation_state.get_pseudonym(entity_id)
            confidence = review.entity.confidence
            conf_str = f"{confidence:.0%}" if confidence is not None else "N/A"
            tooltip = (
                f"{review.entity.entity_type}: {review.entity.text}\n"
                f"→ {pseudonym}\n"
                f"Confiance: {conf_str}"
            )
            fmt.setToolTip(tooltip)

            # Build extra selection
            sel = QTextEdit.ExtraSelection()
            cursor = self.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cursor  # type: ignore[attr-defined]
            sel.format = fmt  # type: ignore[attr-defined]
            selections.append(sel)

        # Add navigation focus highlight
        if self._nav_mode and 0 <= self._nav_index < len(self._entity_ranges):
            start, end, _eid = self._entity_ranges[self._nav_index]
            fmt = QTextCharFormat()
            fmt.setProperty(QTextCharFormat.Property.OutlinePen, True)
            fmt.setBackground(QColor("#1565C0"))
            fmt.setForeground(QColor("#FFFFFF"))
            sel = QTextEdit.ExtraSelection()
            cursor = self.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cursor  # type: ignore[attr-defined]
            sel.format = fmt  # type: ignore[attr-defined]
            selections.append(sel)

        self.setExtraSelections(selections)

    # ------------------------------------------------------------------
    # Click detection via binary search
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Detect clicks on entities using binary search."""
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        entity_id = self._entity_at_position(pos)
        if entity_id:
            self.entity_selected.emit(entity_id)

    def _entity_at_position(self, pos: int) -> str | None:
        """Find entity_id at document character position using bisect."""
        if not self._entity_ranges:
            return None
        starts = [r[0] for r in self._entity_ranges]
        idx = bisect.bisect_right(starts, pos) - 1
        if idx >= 0:
            start, end, entity_id = self._entity_ranges[idx]
            if start <= pos < end:
                return entity_id
        return None

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event: object) -> None:
        """Show entity-specific or add-entity context menu."""
        from PySide6.QtGui import QContextMenuEvent

        if not isinstance(event, QContextMenuEvent):
            return

        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        entity_id = self._entity_at_position(pos)

        menu = QMenu(self)

        if entity_id and self._validation_state:
            # Entity context menu
            review = self._validation_state.get_review(entity_id)
            if review:
                self._build_entity_context_menu(menu, entity_id, review)
        else:
            # Check for text selection — "Add as entity"
            tc = self.textCursor()
            if tc.hasSelection():
                sel_start = tc.selectionStart()
                sel_end = tc.selectionEnd()
                # Only show if selection doesn't overlap existing entity
                if not self._selection_overlaps_entity(sel_start, sel_end):
                    self._build_add_entity_menu(menu, sel_start, sel_end)
                else:
                    return  # no menu
            else:
                return  # no menu

        if menu.actions():
            menu.exec(event.globalPos())

    def _build_entity_context_menu(
        self, menu: QMenu, entity_id: str, review: EntityReview
    ) -> None:
        """Populate context menu for an existing entity."""
        action_accept = menu.addAction("Accepter")
        action_accept.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "accept")
        )

        action_reject = menu.addAction("Rejeter")
        action_reject.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "reject")
        )

        menu.addSeparator()

        action_modify = menu.addAction("Modifier le texte...")
        action_modify.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "modify_text")
        )

        action_pseudo = menu.addAction("Changer le pseudonyme")
        action_pseudo.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "change_pseudonym")
        )

        # Change type submenu
        type_menu = menu.addMenu("Changer le type")
        for type_label, type_val in [
            ("Personne", "PERSON"),
            ("Lieu", "LOCATION"),
            ("Organisation", "ORG"),
        ]:
            if type_val != review.entity.entity_type:
                action = type_menu.addAction(type_label)
                action.triggered.connect(
                    lambda checked=False, t=type_val: self.entity_action_requested.emit(
                        entity_id, f"change_type:{t}"
                    )
                )

    def _build_add_entity_menu(self, menu: QMenu, sel_start: int, sel_end: int) -> None:
        """Populate 'Add as entity' submenu for selected text."""
        add_menu = menu.addMenu("Ajouter comme entité")
        for type_label, type_val in [
            ("Personne", "PERSON"),
            ("Lieu", "LOCATION"),
            ("Organisation", "ORG"),
        ]:
            action = add_menu.addAction(type_label)
            action.triggered.connect(
                lambda checked=False, t=type_val: self.add_entity_requested.emit(
                    t, sel_start, sel_end
                )
            )

    def _selection_overlaps_entity(self, sel_start: int, sel_end: int) -> bool:
        """Check if a text selection overlaps any existing entity."""
        for start, end, _eid in self._entity_ranges:
            if sel_start < end and sel_end > start:
                return True
        return False

    # ------------------------------------------------------------------
    # Keyboard navigation mode (AC7)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle navigation mode keys."""
        key = event.key()

        if not self._nav_mode:
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self._enter_nav_mode()
                return
            # Zoom
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
                    self._zoom_in()
                    return
                if key == Qt.Key.Key_Minus:
                    self._zoom_out()
                    return
            super().keyPressEvent(event)
            return

        # In navigation mode
        if key == Qt.Key.Key_Escape:
            self._exit_nav_mode()
            return
        if key == Qt.Key.Key_Tab:
            self._nav_next()
            return
        if key == Qt.Key.Key_Backtab:  # Shift+Tab
            self._nav_prev()
            return
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._nav_accept_current()
            return
        if key == Qt.Key.Key_Delete:
            self._nav_reject_current()
            return
        if (
            key == Qt.Key.Key_F10
            and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            self._nav_open_context_menu()
            return
        if key == Qt.Key.Key_Menu:
            self._nav_open_context_menu()
            return

        super().keyPressEvent(event)

    def _enter_nav_mode(self) -> None:
        """Enter entity navigation mode, focus first pending entity."""
        if not self._entity_ranges or self._validation_state is None:
            return
        self._nav_mode = True
        self.setStyleSheet("border: 2px solid #1565C0;")

        # Find first pending entity
        from gdpr_pseudonymizer.validation.models import EntityReviewState

        for i, (_s, _e, eid) in enumerate(self._entity_ranges):
            review = self._validation_state.get_review(eid)
            if review and review.state == EntityReviewState.PENDING:
                self._nav_index = i
                self._scroll_to_nav_entity()
                self._apply_highlights()
                return

        # No pending — focus first entity
        self._nav_index = 0
        self._scroll_to_nav_entity()
        self._apply_highlights()

    def _exit_nav_mode(self) -> None:
        """Exit navigation mode."""
        self._nav_mode = False
        self._nav_index = -1
        self.setStyleSheet("")
        self._apply_highlights()

    def _nav_next(self) -> None:
        """Move to next entity in navigation mode."""
        if not self._entity_ranges:
            return
        self._nav_index = (self._nav_index + 1) % len(self._entity_ranges)
        self._scroll_to_nav_entity()
        self._apply_highlights()

    def _nav_prev(self) -> None:
        """Move to previous entity in navigation mode."""
        if not self._entity_ranges:
            return
        self._nav_index = (self._nav_index - 1) % len(self._entity_ranges)
        self._scroll_to_nav_entity()
        self._apply_highlights()

    def _scroll_to_nav_entity(self) -> None:
        """Scroll to the currently focused navigation entity."""
        if 0 <= self._nav_index < len(self._entity_ranges):
            start, _end, entity_id = self._entity_ranges[self._nav_index]
            cursor = self.textCursor()
            cursor.setPosition(start)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            self.entity_selected.emit(entity_id)

    def _nav_accept_current(self) -> None:
        """Accept focused entity and advance to next pending."""
        if 0 <= self._nav_index < len(self._entity_ranges):
            _s, _e, entity_id = self._entity_ranges[self._nav_index]
            self.entity_action_requested.emit(entity_id, "accept")
            self._nav_advance_to_next_pending()

    def _nav_reject_current(self) -> None:
        """Reject focused entity and advance to next pending."""
        if 0 <= self._nav_index < len(self._entity_ranges):
            _s, _e, entity_id = self._entity_ranges[self._nav_index]
            self.entity_action_requested.emit(entity_id, "reject")
            self._nav_advance_to_next_pending()

    def _nav_advance_to_next_pending(self) -> None:
        """Advance navigation index to the next pending entity."""
        if self._validation_state is None or not self._entity_ranges:
            return

        from gdpr_pseudonymizer.validation.models import EntityReviewState

        start_idx = (self._nav_index + 1) % len(self._entity_ranges)
        for offset in range(len(self._entity_ranges)):
            idx = (start_idx + offset) % len(self._entity_ranges)
            _s, _e, eid = self._entity_ranges[idx]
            review = self._validation_state.get_review(eid)
            if review and review.state == EntityReviewState.PENDING:
                self._nav_index = idx
                self._scroll_to_nav_entity()
                self._apply_highlights()
                return

        # No more pending — stay on current
        self._apply_highlights()

    def _nav_open_context_menu(self) -> None:
        """Open context menu for the currently focused navigation entity."""
        if 0 <= self._nav_index < len(self._entity_ranges):
            start, _end, entity_id = self._entity_ranges[self._nav_index]
            review = (
                self._validation_state.get_review(entity_id)
                if self._validation_state
                else None
            )
            if review:
                menu = QMenu(self)
                self._build_entity_context_menu(menu, entity_id, review)
                # Position near the entity text
                cursor = self.textCursor()
                cursor.setPosition(start)
                rect = self.cursorRect(cursor)
                menu.exec(self.mapToGlobal(rect.bottomLeft()))

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _zoom_in(self) -> None:
        if self._zoom_pct < 200:
            self._zoom_pct += 10
            self.zoomIn(1)

    def _zoom_out(self) -> None:
        if self._zoom_pct > 70:
            self._zoom_pct -= 10
            self.zoomOut(1)
