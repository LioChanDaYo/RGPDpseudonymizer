"""Entity-highlighted document editor for validation screen.

Read-only QTextEdit subclass that displays document text with color-coded
entity highlights, click detection, context menus, and keyboard navigation.
"""

from __future__ import annotations

import bisect
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QHelpEvent,
    QKeyEvent,
    QMouseEvent,
    QTextCharFormat,
    QTextCursor,
    QTextLine,
)
from PySide6.QtWidgets import QMenu, QTextEdit, QToolTip

from gdpr_pseudonymizer.gui.i18n import qarg

if TYPE_CHECKING:
    from gdpr_pseudonymizer.gui.models.validation_state import GUIValidationState
    from gdpr_pseudonymizer.validation.models import EntityReview

# ── Entity color scheme (color-blind safe palette - AC3) ──────────────

_LIGHT_COLORS: dict[str, tuple[str, str]] = {
    "PERSON": ("#BBDEFB", "#0D47A1"),  # Blue - unchanged
    "LOCATION": ("#FFE0B2", "#E65100"),  # Orange (was green) - color-blind safe
    "ORG": ("#E1BEE7", "#6A1B9A"),  # Purple (was orange) - color-blind safe
}

_DARK_COLORS: dict[str, tuple[str, str]] = {
    "PERSON": ("#1A237E", "#90CAF9"),  # Blue - unchanged
    "LOCATION": ("#BF360C", "#FFCC80"),  # Orange (was green) - color-blind safe
    "ORG": ("#4A148C", "#CE93D8"),  # Purple (was orange) - color-blind safe
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
        self.setAccessibleName(self.tr("\u00c9diteur de document"))
        self.setAccessibleDescription(
            self.tr(
                "Affiche le document avec les entit\u00e9s surlign\u00e9es en couleur"
            )
        )

        self._validation_state: GUIValidationState | None = None
        # Sorted list of (start_pos, end_pos, entity_id) for click detection
        self._entity_ranges: list[tuple[int, int, str]] = []
        # Story 15.1 (H.2): (start, end, entity_id) of each highlight drawn
        # for a row, for the hover text
        self._shown_ranges: list[tuple[int, int, str]] = []
        self._hide_rejected = False
        self._hide_confirmed = False
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

    def set_hide_confirmed(self, hide: bool) -> None:
        """Toggle hiding of confirmed/known entity highlights."""
        self._hide_confirmed = hide
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
    # Accessibility Support (AC2)
    # ------------------------------------------------------------------

    def _announce_current_entity(self) -> None:
        """Announce current entity to screen readers (AC2 - Task 3.1)."""
        if not self._nav_mode or not (0 <= self._nav_index < len(self._entity_ranges)):
            return

        _start, _end, entity_id = self._entity_ranges[self._nav_index]
        if not self._validation_state:
            return

        review = self._validation_state.get_review(entity_id)
        if not review:
            return

        # Build accessible announcement
        entity_text = review.entity.text
        entity_type = review.entity.entity_type
        state_str = review.state.value

        # Translate entity type and state for announcements
        type_name = self._type_label(entity_type)

        state_name = {
            "pending": self.tr("en attente"),
            "confirmed": self.tr("accepté"),
            "rejected": self.tr("rejeté"),
            "modified": self.tr("modifié"),
            "added": self.tr("ajouté"),
        }.get(state_str, state_str)

        # Format: "Type: Name (Status)"
        announcement = f"{type_name}: {entity_text} ({state_name})"

        # Update accessible description for screen reader
        self.setAccessibleDescription(announcement)

        # Trigger accessibility update event
        try:
            from PySide6.QtGui import QAccessible, QAccessibleEvent

            event = QAccessibleEvent(self, QAccessible.Event.NameChanged)
            QAccessible.updateAccessibility(event)
        except ImportError:
            pass  # Qt < 6.5

    # ------------------------------------------------------------------
    # Highlight engine
    # ------------------------------------------------------------------

    def _rebuild_entity_ranges(self) -> None:
        """Rebuild sorted entity ranges from validation state.

        Includes variant occurrences so ALL instances of grouped entities
        are highlighted, not just the canonical form.
        """
        if self._validation_state is None:
            self._entity_ranges = []
            return
        ranges = self._validation_state.get_all_entity_ranges()
        ranges.sort(key=lambda r: r[0])
        self._entity_ranges = ranges
        self._nav_entity_ids = [r[2] for r in ranges]

    def _apply_highlights(self) -> None:
        """Apply extra selections for all entities."""
        self._shown_ranges = []
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

            # Hide confirmed/added/known entities when toggle is on (AC8, AC9)
            is_known = self._validation_state.is_entity_known(entity_id)
            is_confirmed = review.state in (
                EntityReviewState.CONFIRMED,
                EntityReviewState.ADDED,
            )
            if (is_confirmed or is_known) and self._hide_confirmed:
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

            # Tooltip: pseudonym + type + confidence + cell reference
            fmt.setToolTip(self._tooltip_block(entity_id, review))
            # Story 15.1 (H.2): the range drawn for the row, for the hover
            self._shown_ranges.append((start, end, entity_id))

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
    # Story 15.1: the hover text (Fix design H; Lionel's Q4)
    # ------------------------------------------------------------------

    def _type_label(self, entity_type: str) -> str:
        """The type's label (« Personne », « Lieu », « Organisation »);
        any other type is shown as its code."""
        return {
            "PERSON": self.tr("Personne"),
            "LOCATION": self.tr("Lieu"),
            "ORG": self.tr("Organisation"),
        }.get(entity_type, entity_type)

    def _tooltip_block(self, entity_id: str, review: EntityReview) -> str:
        """A row's block of the hover text: type and text, « → » pseudonym,
        confidence, and the cell when there is one (H.1)."""
        if self._validation_state is None:
            return ""
        pseudonym = self._validation_state.get_pseudonym(entity_id)
        confidence = review.entity.confidence
        conf_str = f"{confidence:.0%}" if confidence is not None else "N/A"
        context_line = ""
        if review.entity.context_label:
            context_line = f"\n[{review.entity.context_label}]"
        # Story 15.1 (Lionel's Q2, text 1): the type's label, then the text
        first_line = qarg(
            self.tr("%1 : %2"),
            self._type_label(review.entity.entity_type),
            review.entity.text,
        )
        return (
            f"{first_line}\n"
            f"→ {pseudonym}\n"
            + qarg(self.tr("Confiance : %1"), conf_str)
            + context_line
        )

    def _not_written_line(self, writer: EntityReview) -> str:
        """The last line of a block whose pseudonym is not written at the
        pointer, naming the row written there (N3; Lionel's Q2, text 4)."""
        return qarg(
            self.tr(
                "Pseudonyme non écrit ici : c'est celui de « %1 » (%2) qui est écrit."
            ),
            writer.entity.text,
            self._type_label(writer.entity.entity_type),
        )

    def _char_box(self, position: int) -> tuple[float, float, float, float] | None:
        """(left, right, top, bottom) of character ``position`` in the
        viewport, or None for the end of a paragraph or of the document.

        The position comes from ``cursorRect``; the width from the
        character's own visual line (``QTextLine.cursorToX``), so the last
        character of a wrapped line keeps its own box."""
        document = self.document()
        if position < 0 or position >= document.characterCount() - 1:
            return None
        block = document.findBlock(position)
        offset = position - block.position()
        if offset >= block.length() - 1:
            return None
        layout = block.layout()
        if layout is None:
            return None
        line = layout.lineForTextPosition(offset)
        if not line.isValid():
            return None
        cursor = QTextCursor(document)
        cursor.setPosition(position)
        rect = self.cursorRect(cursor)
        left = self._line_x(line, offset)
        right = self._line_x(line, offset + 1)
        x = float(rect.x())
        top = float(rect.top())
        return (x, x + (right - left), top, top + line.height())

    @staticmethod
    def _line_x(line: QTextLine, offset: int) -> float:
        """``QTextLine.cursorToX`` as a number (PySide6 may return it with
        the position it was given)."""
        value: object = line.cursorToX(offset)
        if isinstance(value, tuple):
            value = value[0]
        return float(value) if isinstance(value, int | float) else 0.0

    def _char_at(self, point: QPoint) -> int | None:
        """The character under ``point`` (viewport coordinates), or None
        over blank space (H.3).

        ``cursorForPosition`` gives the nearest boundary; of the characters
        on each side of it, the one whose box holds the point."""
        boundary = self.cursorForPosition(point).position()
        for position in (boundary - 1, boundary):
            box = self._char_box(position)
            if box is None:
                continue
            left, right, top, bottom = box
            if left <= point.x() < right and top <= point.y() < bottom:
                return position
        return None

    def _hover_text(self, position: int) -> str:
        """The hover text at character ``position``: the block of each row
        highlighted there, in the order of the ranges, separated by a blank
        line; a block whose pseudonym is not the one the end would write at
        that character ends with N3 (H.4). Empty when no row is there."""
        state = self._validation_state
        if state is None:
            return ""
        ids: list[str] = []
        for start, end, entity_id in self._shown_ranges:
            if start <= position < end and entity_id not in ids:
                ids.append(entity_id)
        writer_id = state.writer_at(position) if ids else None
        writer = state.get_review(writer_id) if writer_id is not None else None
        blocks: list[str] = []
        for entity_id in ids:
            review = state.get_review(entity_id)
            if review is None:
                continue
            block = self._tooltip_block(entity_id, review)
            if writer is not None and entity_id != writer_id:
                block += "\n" + self._not_written_line(writer)
            blocks.append(block)
        return "\n\n".join(blocks)

    def viewportEvent(self, event: QEvent) -> bool:
        """Answer a tooltip request over the document itself (H.4): the
        highlights are ``ExtraSelection`` formats, whose hover text
        ``QTextEdit`` never shows."""
        if event.type() == QEvent.Type.ToolTip and isinstance(event, QHelpEvent):
            position = self._char_at(event.pos())
            text = self._hover_text(position) if position is not None else ""
            if not text:
                QToolTip.hideText()
                event.ignore()
                return True
            QToolTip.showText(event.globalPos(), text, self.viewport())
            return True
        return super().viewportEvent(event)

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
        action_accept = menu.addAction(self.tr("Accepter"))
        action_accept.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "accept")
        )

        action_reject = menu.addAction(self.tr("Rejeter"))
        action_reject.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "reject")
        )

        menu.addSeparator()

        action_modify = menu.addAction(self.tr("Modifier le texte..."))
        action_modify.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "modify_text")
        )

        action_pseudo = menu.addAction(self.tr("Changer le pseudonyme"))
        action_pseudo.triggered.connect(
            lambda: self.entity_action_requested.emit(entity_id, "change_pseudonym")
        )

        # Change type submenu
        type_menu = menu.addMenu(self.tr("Changer le type"))
        for type_label, type_val in [
            (self.tr("Personne"), "PERSON"),
            (self.tr("Lieu"), "LOCATION"),
            (self.tr("Organisation"), "ORG"),
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
        add_menu = menu.addMenu(self.tr("Ajouter comme entit\u00e9"))
        for type_label, type_val in [
            (self.tr("Personne"), "PERSON"),
            (self.tr("Lieu"), "LOCATION"),
            (self.tr("Organisation"), "ORG"),
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
            self._announce_current_entity()  # AC2 - announce to screen readers

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
