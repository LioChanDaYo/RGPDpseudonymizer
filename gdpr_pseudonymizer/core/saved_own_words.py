"""Saved pseudonyms that hold a word of their own name (Story 11.7).

Before Story 11.6, the library drew a new name's pseudonym without looking at
the name, so a saved row can hold one of its own words (« Élodie Martin »
saved as « Élodie Lucas »). Such a row is written again in every later
document, and its part passes to every name that shares that first or last
name. This module finds those rows (read-only, no document needed) and
replaces them at the user's request.

- ``find_own_word_rows``: the rows whose pseudonym holds a word of their own
  name, by Story 11.6's rule (``own_word``). A place or an organisation is
  reported only when the shared part is its whole pseudonym, its whole name
  or holds a place of its library (Lionel, "report only real leaks"). Rows
  of theme ``custom`` and ``neutral_id`` are skipped.
- ``plan_replacement``: the rows a replacement changes. One real first name
  keeps one pseudonym first name, one real last name one last name (Story
  2.8, Story 10.11 Q-D), so a person's leaking part moves on every person row
  that holds it for the same real word in that role.
- ``replace_own_word_rows``: under ``pseudonym_lock``, the plan computed
  again from the rows read there, one new value drawn per group under Story
  11.6's rule and this story's refusals, every row written in one commit,
  one ``REPLACEMENT`` audit entry that holds no name. The old value is freed
  (Lionel, "forget").

Nothing here logs or raises a name, a pseudonym or a word.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from gdpr_pseudonymizer.core.custom_pseudonym import (
    CUSTOM_THEME,
    fold,
    holds_words,
    own_word,
    real_name_check,
    takes_custom_value,
    untracked_custom_values,
)
from gdpr_pseudonymizer.data.database import pseudonym_lock
from gdpr_pseudonymizer.data.models import Entity, Operation
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    MappingRepository,
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.utils.logger import get_logger

if TYPE_CHECKING:
    from gdpr_pseudonymizer.data.database import DatabaseSession
    from gdpr_pseudonymizer.pseudonym.library_manager import (
        LibraryBasedPseudonymManager,
    )

logger = get_logger(__name__)

# Themes the check skips: a custom pseudonym is refused when it holds a word
# of its own name (Story 10.16); a neutral_id pseudonym is an identifier.
SKIPPED_THEMES = frozenset({CUSTOM_THEME, "neutral_id"})

# The reasons a replacement stops without writing anything
STOP_NOT_FOUND = "not_found"
STOP_CUSTOM_ROW = "custom_row"
STOP_CHANGED = "changed"
STOP_EXHAUSTED = "exhausted"
STOP_SHAPE = "shape"

_PERSON_FALLBACK = re.compile(r"^Person-\d+$")
_FIRST, _LAST = "first", "last"


@dataclass(frozen=True)
class OwnWordRow:
    """A saved row the check finds: its id, its type and the word found."""

    entity_id: str
    entity_type: str
    word: str


@dataclass(frozen=True)
class _Group:
    """Rows that change together. ``role`` is "first" or "last" for a
    person's part, None for a row replaced whole (a place, an organisation,
    a person row with no stored parts)."""

    role: str | None
    lead_id: str
    member_ids: tuple[str, ...]


@dataclass
class ReplacementPlan:
    """What a replacement changes: the rows that leak (``leaking``, with the
    word found), the other rows that change with them (``others``, ids), or
    the reason it stops (``stop_reason``; ``stop_ids``: the row it concerns
    and, for a custom row, the custom row)."""

    leaking: list[OwnWordRow] = field(default_factory=list)
    others: list[str] = field(default_factory=list)
    groups: list[_Group] = field(default_factory=list)
    stop_reason: str | None = None
    stop_ids: tuple[str, ...] = ()

    @property
    def changed_ids(self) -> frozenset[str]:
        """Every row the replacement changes."""
        return frozenset(row.entity_id for row in self.leaking) | frozenset(self.others)


@dataclass(frozen=True)
class ReplacedRow:
    """One changed row, for the screen only (never logged)."""

    entity_id: str
    entity_type: str
    name: str
    old: str
    new: str


@dataclass
class ReplacementResult:
    """The outcome: the changed rows, or why nothing was written."""

    plan: ReplacementPlan
    changes: list[ReplacedRow] = field(default_factory=list)
    stop_reason: str | None = None
    operation_id: str | None = None


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------


def _new_manager() -> LibraryBasedPseudonymManager:
    # Imported here: the library manager imports this package's helpers
    from gdpr_pseudonymizer.pseudonym.library_manager import (
        LibraryBasedPseudonymManager,
    )

    return LibraryBasedPseudonymManager()


def _library_places(theme: str) -> list[str]:
    """The places of the pseudonym library of ``theme`` (none if it has no
    library)."""
    manager = _new_manager()
    try:
        manager.load_library(theme)
    except (FileNotFoundError, ValueError):
        return []
    if manager.theme == "neutral_id":
        return []
    return manager._flatten_location_list(manager.locations)


def find_own_word_rows(rows: Iterable[Entity]) -> list[OwnWordRow]:
    """The saved rows whose pseudonym holds a word of their own name (Story
    11.7, AC1), in the order given. Pure: reads no database; the places of
    each theme's library are read once per call."""
    places_of: dict[str, list[str]] = {}
    found: list[OwnWordRow] = []
    for row in rows:
        if row.theme in SKIPPED_THEMES or not row.pseudonym_full:
            continue
        keep: Callable[[str], bool] | None = None
        if row.entity_type != "PERSON":
            if row.theme not in places_of:
                places_of[row.theme] = _library_places(row.theme)
            keep = _real_leak(row, places_of[row.theme])
        word = own_word(row.pseudonym_full, row.full_name, keep)
        if word is not None:
            found.append(OwnWordRow(row.id, row.entity_type, word))
    return found


def _real_leak(row: Entity, places: Sequence[str]) -> Callable[[str], bool]:
    """Lionel's "report only real leaks" for a place or an organisation: a
    shared run is kept when it is the whole pseudonym, the whole name, or
    holds a place of the library as consecutive whole words."""
    whole = {fold(row.pseudonym_full), fold(row.full_name)}

    def keep(run: str) -> bool:
        if fold(run) in whole:
            return True
        return any(holds_words(run, place) for place in places if place.strip())

    return keep


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


def _real_word(row: Entity, role: str) -> str | None:
    """A person row's real word in ``role``; a one-word row has its word in
    both roles (``untracked_custom_values``' reading)."""
    if row.first_name and row.last_name:
        return row.first_name if role == _FIRST else row.last_name
    return row.first_name or row.last_name


def _part(row: Entity, role: str) -> str | None:
    return row.pseudonym_first if role == _FIRST else row.pseudonym_last


def _members(rows: Sequence[Entity], role: str, word: str, part: str) -> list[str]:
    """Every person row whose real word in ``role`` and part in ``role`` fold
    to those of the leaking row."""
    folded_word, folded_part = fold(word), fold(part)
    members: list[str] = []
    for row in rows:
        if row.entity_type != "PERSON" or row.theme == "neutral_id":
            continue
        real = _real_word(row, role)
        stored = _part(row, role)
        if (
            real
            and stored
            and fold(real) == folded_word
            and fold(stored) == folded_part
        ):
            members.append(row.id)
    return members


def plan_replacement(
    rows: Sequence[Entity], entity_ids: Collection[str] | None
) -> ReplacementPlan:
    """The groups that replacing ``entity_ids`` (None: every row found)
    changes, from ``rows`` (every saved row). Pure."""
    by_id = {row.id: row for row in rows}
    found = {own.entity_id: own for own in find_own_word_rows(rows)}
    plan = ReplacementPlan()
    if entity_ids is None:
        asked = list(found)
    else:
        asked = list(dict.fromkeys(entity_ids))
        missing = [entity_id for entity_id in asked if entity_id not in found]
        if missing:
            plan.stop_reason = STOP_NOT_FOUND
            plan.stop_ids = (missing[0],)
            return plan

    seen_groups: set[tuple[str | None, str, str]] = set()
    for entity_id in asked:
        row = by_id[entity_id]
        for group in _groups_of(rows, row):
            key = (
                group.role,
                fold(_real_word(row, group.role) or "") if group.role else row.id,
                fold(_part(row, group.role) or "") if group.role else "",
            )
            if key in seen_groups:
                continue
            seen_groups.add(key)
            plan.groups.append(group)
        if not any(entity_id in group.member_ids for group in plan.groups):
            # A person row with parts whose leak is in no part: its pseudonym
            # cannot be recomposed from its parts
            plan.stop_reason = STOP_SHAPE
            plan.stop_ids = (entity_id,)
            return plan

    changed: list[str] = []
    for group in plan.groups:
        for member_id in group.member_ids:
            member = by_id[member_id]
            if member.theme == CUSTOM_THEME:
                plan.stop_reason = STOP_CUSTOM_ROW
                plan.stop_ids = (group.lead_id, member_id)
                return plan
            if member_id not in changed:
                changed.append(member_id)
    plan.leaking = [found[entity_id] for entity_id in changed if entity_id in found]
    plan.others = [entity_id for entity_id in changed if entity_id not in found]
    return plan


def _groups_of(rows: Sequence[Entity], row: Entity) -> list[_Group]:
    """The groups a found row starts: one per leaking part of a person with
    stored parts, else the row alone."""
    if row.entity_type != "PERSON" or not (row.pseudonym_first or row.pseudonym_last):
        return [_Group(None, row.id, (row.id,))]
    groups: list[_Group] = []
    for role in (_FIRST, _LAST):
        part = _part(row, role)
        real = _real_word(row, role)
        if not part or not real or own_word(part, row.full_name) is None:
            continue
        groups.append(_Group(role, row.id, tuple(_members(rows, role, real, part))))
    return groups


# ---------------------------------------------------------------------------
# The replacement
# ---------------------------------------------------------------------------


def _copy(row: Entity) -> Entity:
    """A detached copy of a saved row, changed in memory as groups are
    drawn."""
    return Entity(
        id=row.id,
        entity_type=row.entity_type,
        first_name=row.first_name,
        last_name=row.last_name,
        full_name=row.full_name,
        pseudonym_full=row.pseudonym_full,
        pseudonym_first=row.pseudonym_first,
        pseudonym_last=row.pseudonym_last,
        first_seen_timestamp=row.first_seen_timestamp,
        gender=row.gender,
        confidence_score=row.confidence_score,
        theme=row.theme,
        is_ambiguous=row.is_ambiguous,
        ambiguity_reason=row.ambiguity_reason,
    )


def _recomposed(row: Entity, role: str, value: str) -> Entity | None:
    """The row with ``value`` as its part in ``role``, its full pseudonym
    recomposed; None if its full pseudonym is not its parts."""
    old = _part(row, role)
    first, last = row.pseudonym_first, row.pseudonym_last
    if first and last and row.pseudonym_full == f"{first} {last}":
        first, last = (value, last) if role == _FIRST else (first, value)
        full = f"{first} {last}"
    elif old and fold(row.pseudonym_full) == fold(old):
        full = value
        first, last = (value, last) if role == _FIRST else (first, value)
    else:
        return None
    new = _copy(row)
    new.pseudonym_full, new.pseudonym_first, new.pseudonym_last = full, first, last
    return new


def _draw_group(
    group: _Group, current: dict[str, Entity]
) -> tuple[dict[str, Entity] | None, str | None]:
    """The group's rows with one new value, drawn on the rows as the earlier
    groups left them (``current``); or (None, stop reason)."""
    lead = current[group.lead_id]
    members = [current[member_id] for member_id in group.member_ids]
    outside = [row for row_id, row in current.items() if row_id not in group.member_ids]
    every = list(current.values())

    if group.role is not None:
        role = group.role
        old = _part(lead, role) or ""
        recomposable = [_recomposed(member, role, old) for member in members]
        if any(row is None for row in recomposable):
            return None, STOP_SHAPE

    manager = _new_manager()
    manager.load_library(lead.theme)
    manager.load_existing_mappings(outside)

    names_check = real_name_check("", [row.full_name for row in every])
    saved_parts = {
        fold(part)
        for row in every
        for part in (row.pseudonym_first, row.pseudonym_last)
        if part
    }
    saved_fulls = {fold(row.pseudonym_full) for row in every if row.pseudonym_full}
    reserved = untracked_custom_values(every)

    def refused_rows(new_rows: Iterable[Entity | None]) -> bool:
        for new in new_rows:
            if new is None or fold(new.pseudonym_full) in saved_fulls:
                return True
            if takes_custom_value(new, reserved):
                return True
        return False

    changed: dict[str, Entity] = {}
    if group.role is not None:
        role = group.role

        def check(value: str) -> bool:
            if names_check(value) or fold(value) in saved_parts:
                return True
            return refused_rows(_recomposed(member, role, value) for member in members)

        other = _part(lead, _LAST if role == _FIRST else _FIRST) or "-"
        manager.set_real_name_check(check)
        try:
            assignment = manager.assign_pseudonym(
                "PERSON",
                gender=lead.gender,
                existing_first=None if role == _FIRST else other,
                existing_last=other if role == _FIRST else None,
            )
        except RuntimeError:
            return None, STOP_EXHAUSTED
        value = (
            assignment.pseudonym_first if role == _FIRST else assignment.pseudonym_last
        )
        if not value or _PERSON_FALLBACK.match(value) or check(value):
            return None, STOP_EXHAUSTED
        for member in members:
            new = _recomposed(member, role, value)
            if new is None:
                return None, STOP_SHAPE
            changed[member.id] = new
        return changed, None

    # A row replaced whole: a place, an organisation, a person with no parts
    def whole_check(value: str) -> bool:
        if names_check(value):
            return True
        if lead.entity_type == "PERSON" and fold(value) in saved_parts:
            return True
        return fold(value) in saved_fulls or fold(value) in reserved

    manager.set_real_name_check(whole_check)
    try:
        assignment = manager.assign_pseudonym(lead.entity_type, gender=lead.gender)
    except RuntimeError:
        return None, STOP_EXHAUSTED
    full = assignment.pseudonym_full
    if lead.entity_type == "PERSON" and (
        _PERSON_FALLBACK.match(full) or fold(full) in saved_fulls
    ):
        return None, STOP_EXHAUSTED
    new = _copy(lead)
    new.pseudonym_full = full
    # A person drawn whole keeps no parts, as _assign_untaken_pseudonym does
    new.pseudonym_first = None
    new.pseudonym_last = None
    changed[lead.id] = new
    return changed, None


def replace_own_word_rows(
    db_session: DatabaseSession,
    entity_ids: Collection[str] | None,
    confirmed: frozenset[str] | None,
) -> ReplacementResult:
    """Replace the found rows ``entity_ids`` (None: every row found) and the
    rows that share their parts, under the lock, in one commit (Story 11.7,
    AC6, AC7).

    ``confirmed``: the rows the user saw change; when the rows read under
    the lock give another set, nothing is written (``"changed"``).
    """
    start = time.monotonic()
    repo: MappingRepository = SQLiteMappingRepository(db_session)
    with pseudonym_lock(db_session):
        rows = repo.find_all()
        plan = plan_replacement(rows, entity_ids)
        if plan.stop_reason is not None:
            return ReplacementResult(plan, stop_reason=plan.stop_reason)
        if confirmed is not None and plan.changed_ids != frozenset(confirmed):
            return ReplacementResult(plan, stop_reason=STOP_CHANGED)

        current = {row.id: _copy(row) for row in rows}
        for group in plan.groups:
            changed, stop = _draw_group(group, current)
            if changed is None:
                return ReplacementResult(plan, stop_reason=stop)
            current.update(changed)

        before = {row.id: row for row in rows}
        order = [row.id for row in rows if row.id in plan.changed_ids]
        changes = [
            (
                row_id,
                current[row_id].pseudonym_full,
                current[row_id].pseudonym_first,
                current[row_id].pseudonym_last,
            )
            for row_id in order
        ]
        repo.replace_pseudonyms(changes)

    replaced = [
        ReplacedRow(
            row_id,
            before[row_id].entity_type,
            before[row_id].full_name,
            before[row_id].pseudonym_full,
            current[row_id].pseudonym_full,
        )
        for row_id in order
    ]
    themes = sorted({before[row_id].theme for row_id in order})
    operation = Operation(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(UTC),
        operation_type="REPLACEMENT",
        files_processed=[],
        user_modifications={
            # Story 10.12: the unencrypted operations table keeps no name
            "replaced_entity_ids": order,
            "replaced_entity_types": [before[row_id].entity_type for row_id in order],
            "count": len(order),
        },
        model_name="N/A",
        model_version="N/A",
        theme_selected=",".join(themes),
        entity_count=len(order),
        processing_time_seconds=round(time.monotonic() - start, 3),
        success=True,
    )
    AuditRepository(db_session.session).log_operation(operation)
    logger.info("saved_own_words_replaced", groups=len(plan.groups), rows=len(order))
    return ReplacementResult(plan, changes=replaced, operation_id=operation.id)


def count_own_word_rows(rows: Iterable[Entity]) -> int:
    """The number of rows the check finds (the notice after a document is
    written)."""
    count = len(find_own_word_rows(rows))
    logger.info("saved_own_words_found", count=count)
    return count


def notice_line(count: int) -> str:
    """The command line's note after ``process`` or ``batch`` when the
    database holds such rows (Story 11.7, C18)."""
    if count == 1:
        held = "1 saved pseudonym holds"
    else:
        held = f"{count} saved pseudonyms hold"
    return (
        f"Note: {held} a word of their own name. "
        "See 'gdpr-pseudo validate-mappings --own-words'."
    )


def own_word_rows_of(result: object) -> int:
    """The notice's count carried by a processing result (``own_word_rows``);
    0 when the result has none (a result built elsewhere)."""
    count = getattr(result, "own_word_rows", 0)
    return count if isinstance(count, int) and not isinstance(count, bool) else 0
