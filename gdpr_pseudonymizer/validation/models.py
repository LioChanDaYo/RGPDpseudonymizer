"""Validation data models for human-in-the-loop entity review."""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import TypeAlias

from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.utils.text_form import not_after_word, not_before_word

# Story 10.15: the source of a place added by hand with [A], the marker the
# desktop app already gives a row added by hand.
ADDED_BY_HAND_SOURCE = "manual"

# Story 10.15 v1.4/v1.5 (AC1 and AC14 (d), Lionel's Q4 applied to
# corrections): the source of every place a correction made with [E] reaches.
CORRECTED_BY_HAND_SOURCE = "corrected"

# The places the user typed, added with [A] or corrected with [E]: each is
# widened over a name it partly overlaps before the document is written.
TYPED_SOURCES = frozenset({ADDED_BY_HAND_SOURCE, CORRECTED_BY_HAND_SOURCE})

# Stories 10.17 and 10.19: the forms of a name, one rule for the command line
# and the desktop app (moved here unchanged from gui/models/validation_state.py,
# where Story 10.17 wrote them). A place of a name is a whole word (Story 10.15,
# AC14 (a), Lionel's Q3): the character just before and just after it (when
# there is one) is neither a word character nor a hyphen (-, U+2010, U+2011),
# a hyphen joins words; Story 10.20 (AC4): nor a combining mark, which belongs
# to its word.


def fold(text: str) -> str:
    """``text`` with each character's accents set aside, one character for one.

    A character whose decomposition without its combining marks is not one
    character is kept as it is, so a position in the folded text is the same
    position in ``text``.
    """
    folded: list[str] = []
    for char in text:
        bare = "".join(
            part
            for part in unicodedata.normalize("NFD", char)
            if not unicodedata.combining(part)
        )
        folded.append(bare if len(bare) == 1 else char)
    return "".join(folded)


def is_form(place: str, text: str) -> bool:
    """Whether ``place`` is written as a form of the name ``text`` (Story
    10.17, AC13 (a); Lionel, 2026-10-19, "A: Fix, capitals only", in the PO's
    wording, and his 10.19 Q3, "A: Reach it too").

    The same letters as ``text``, whatever their capitals, except a place
    written entirely in small letters (no capital letter in it), unless it is
    exactly ``text``. In a place written entirely in capitals (no small letter
    in it), accents are set aside too: « HELENE » and « HELÈNE » are forms of
    « Hélène », « Helene » and « hélène » are not.
    """
    if place == text:
        return True
    if not any(char.isupper() for char in place):
        return False
    if place.lower() == text.lower():
        return True
    if any(char.islower() for char in place):
        return False
    return fold(place).lower() == fold(text).lower()


def whole_word_places(text: str, document_text: str) -> list[tuple[int, int]]:
    """The places of the name ``text`` in ``document_text`` (Story 10.17,
    AC13 (a)): every whole-word form of it (``is_form``), read left to right,
    not overlapping each other. An empty text has no place.

    A whole word (Lionel's 10.15 Q3, "A: Hyphen joins"; Story 10.20, AC4):
    the character just before and just after it (when there is one) is
    neither a word character, a combining mark nor a hyphen (-, U+2010,
    U+2011); an apostrophe is not a word character. The rule is the
    product's one (``not_after_word``, ``not_before_word``).

    The search runs on the folded document, case-insensitively; each place it
    finds is kept only if the text written there is a form of ``text``.
    """
    if not text:
        return []
    folded = fold(document_text)
    pattern = re.compile(
        not_after_word() + re.escape(fold(text)) + not_before_word(), re.IGNORECASE
    )
    places: list[tuple[int, int]] = []
    position = 0
    while True:
        match = pattern.search(folded, position)
        if match is None:
            return places
        start, end = match.span()
        if is_form(document_text[start:end], text):
            places.append((start, end))
            position = end
        else:
            position = start + 1


def _all_forms(texts: Iterable[str], names: Iterable[str]) -> bool:
    """Whether every text of ``texts`` is a form of one of ``names``."""
    candidates = list(names)
    return all(any(is_form(text, name) for name in candidates) for text in texts)


@dataclass
class EntityGroup:
    """Group of entities with same text and type (including variant forms).

    Enables deduplication by grouping multiple occurrences of the same entity
    (e.g., 10 instances of "Marie Dubois" as PERSON) for single user validation.
    Also supports variant grouping where different text forms of the same
    real-world entity (e.g., "Marie Dubois", "Pr. Dubois", "Dubois") are
    merged into a single validation item.

    Attributes:
        unique_key: Tuple of (canonical_text, entity_type) identifying the group
        occurrences: List of DetectedEntity instances across all variant forms
        variant_texts: Set of unique text forms in this group
        canonical_entity: The representative entity (longest/most complete form)
        current_context_index: Index for context cycling (0-based)
    """

    unique_key: tuple[str, str]
    occurrences: list[DetectedEntity] = field(default_factory=list)
    variant_texts: set[str] = field(default_factory=set)
    canonical_entity: DetectedEntity | None = None
    current_context_index: int = 0

    @property
    def text(self) -> str:
        """Get canonical entity text from unique key."""
        return self.unique_key[0]

    @property
    def entity_type(self) -> str:
        """Get entity type from unique key."""
        return self.unique_key[1]

    @property
    def count(self) -> int:
        """Get number of occurrences in this group."""
        return len(self.occurrences)

    @property
    def has_variants(self) -> bool:
        """Whether this group contains multiple text forms."""
        return len(self.variant_texts) > 1

    @property
    def non_canonical_variants(self) -> list[str]:
        """Get variant texts excluding the canonical form."""
        canonical = self.text
        return sorted(v for v in self.variant_texts if v != canonical)

    def get_representative_entity(self) -> DetectedEntity:
        """Get canonical entity for display.

        Returns the canonical entity (longest form) for primary display.

        Returns:
            Canonical entity if set, otherwise entity at current context index
        """
        if self.canonical_entity is not None:
            return self.canonical_entity
        return self.occurrences[self.current_context_index]

    def get_current_context_entity(self) -> DetectedEntity:
        """Get entity at current context index (for context snippet display).

        Returns:
            Entity at current context index
        """
        return self.occurrences[self.current_context_index]

    def cycle_context(self) -> None:
        """Move to next context in group (cycles back to start)."""
        self.current_context_index = (self.current_context_index + 1) % self.count


CandidateKey: TypeAlias = tuple[str, int, str]  # (text, start_pos, entity_type)


def candidate_key(entity: DetectedEntity) -> CandidateKey:
    """Per-run key of one candidate in the desktop app: text, start and type.

    Keys the pseudonym preview map, the variant occurrence map and (as its
    text and type) the same-text group of one desktop validation, so the two
    types of a same-span pair stay separate candidates (Story 10.8). The
    group key ``(text, entity_type)`` has the shape of
    ``EntityGroup.unique_key``. This is not the mapping-database key.
    """
    return (entity.text, entity.start_pos, entity.entity_type)


# Story 10.13: (cell, start, end), with an empty cell outside spreadsheets.
Place: TypeAlias = tuple[str, int, int]
NameOfReview: TypeAlias = tuple[str, str]  # (text, type)


def place_of(entity: DetectedEntity) -> Place:
    """Locate an occurrence for Story 10.13 (Lionel's decision, 2026-10-16)."""
    return (entity.context_label or "", entity.start_pos, entity.end_pos)


def written_places(sent: Iterable[DetectedEntity]) -> list[Place]:
    """Apply finalization's overlap rule per cell for Story 10.13.

    Lionel's decision of 2026-10-16 counts only spans actually replaced:
    earlier starts win, with longer spans first when starts are equal.
    """
    kept_by_cell: dict[str, list[Place]] = {}
    for place in sorted(
        (place_of(entity) for entity in sent),
        key=lambda item: (item[0], item[1], -item[2]),
    ):
        cell, start, end = place
        kept = kept_by_cell.setdefault(cell, [])
        if not any(not (end <= other[1] or start >= other[2]) for other in kept):
            kept.append(place)
    return [place for kept in kept_by_cell.values() for place in kept]


def count_names_left_in_clear(
    pending: Iterable[tuple[NameOfReview, Iterable[Place]]],
    sent: Iterable[DetectedEntity],
) -> int:
    """Count distinct pending names left in clear for Story 10.13.

    Per Lionel's decision of 2026-10-16, a place is covered only by one
    containing written span in the same cell, regardless of entity type.
    """
    written = written_places(sent)
    uncovered_names: set[NameOfReview] = set()
    for name, places in pending:
        for cell, start, end in places:
            covered = any(
                cell == written_cell and written_start <= start and end <= written_end
                for written_cell, written_start, written_end in written
            )
            if not covered:
                uncovered_names.add(name)
                break
    return len(uncovered_names)


class EntityReviewState(Enum):
    """State of entity review in validation workflow.

    Attributes:
        PENDING: Entity awaiting user review
        CONFIRMED: Entity confirmed as correct by user
        REJECTED: Entity rejected as false positive
        MODIFIED: Entity text modified by user
        ADDED: Entity manually added by user
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    MODIFIED = "modified"
    ADDED = "added"


@dataclass
class UserDecision:
    """Records a user's decision about an entity.

    Attributes:
        entity_id: UUID of the detected entity
        action: User action (CONFIRM, REJECT, MODIFY, ADD, CHANGE_PSEUDONYM)
        original_entity: Original detected entity
        modified_entity: Modified entity if action is MODIFY or ADD
        new_pseudonym: Custom pseudonym if action is CHANGE_PSEUDONYM
        timestamp: ISO format timestamp of decision
    """

    entity_id: str
    action: str
    original_entity: DetectedEntity | None = None
    modified_entity: DetectedEntity | None = None
    new_pseudonym: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EntityReview:
    """Entity review state for validation workflow.

    Tracks the user's review decision for a single detected entity,
    including any modifications or rejections.

    Attributes:
        entity: Detected entity from NLP processing
        entity_id: Unique identifier for this entity
        state: Current review state
        user_modification: Modified entity text if state is MODIFIED
        modified_entity: Full modified entity (text, span, type) if MODIFIED
        suggested_pseudonym: Suggested pseudonym for display (optional)
        custom_pseudonym: User-provided custom pseudonym override
    """

    entity: DetectedEntity
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: EntityReviewState = EntityReviewState.PENDING
    user_modification: str | None = None
    modified_entity: DetectedEntity | None = None
    suggested_pseudonym: str | None = None
    custom_pseudonym: str | None = None


@dataclass
class ValidationSession:
    """Manages validation state for a document.

    Coordinates the human-in-the-loop validation workflow, tracking
    which entities have been reviewed and storing user decisions.

    Attributes:
        document_path: Path to document being validated
        document_text: Full document text content
        entities: List of detected entities being reviewed
        context_cache: Cached context snippets for fast display
        user_decisions: List of all user decisions
        current_index: Index of entity currently being reviewed
        current_entity_type: Current entity type being reviewed
        cell_texts: Cell reference -> cell text of a spreadsheet; empty for
            a text document (Story 10.15)
    """

    document_path: str
    document_text: str
    entities: list[DetectedEntity] = field(default_factory=list)
    context_cache: dict[str, str] = field(default_factory=dict)
    user_decisions: list[UserDecision] = field(default_factory=list)
    current_index: int = 0
    current_entity_type: str = "PERSON"
    _entity_reviews: list[EntityReview] = field(default_factory=list)
    cell_texts: dict[str, str] = field(default_factory=dict)

    def text_of(self, entity: DetectedEntity) -> str:
        """The text an entity's positions point into (Story 10.15, AC2).

        On a spreadsheet, the text of the entity's own cell; otherwise the
        document text.
        """
        label = entity.context_label
        if label is not None and label in self.cell_texts:
            return self.cell_texts[label]
        return self.document_text

    def places_of(self, text: str, entity_type: str) -> list[DetectedEntity]:
        """Every place of a name added by hand (Story 10.15, AC14 (a); Story
        10.19, AC1 and AC2).

        A place is a whole-word form of the text (``whole_word_places``): the
        text typed, or the same letters whatever their capitals, never a word
        written entirely in small letters unless it is exactly the text
        typed, and in a word written entirely in capitals the same letters
        once accents are set aside (Lionel, 2026-10-19, and his 10.19 Q3).
        Neither the character before a place nor the one after it is a word
        character, a combining mark (Story 10.20) or a hyphen. Each cell of a
        spreadsheet is searched on its own, so a place carries its cell and
        its position in the cell; a text document is searched as one text.
        Places are read left to right and never overlap each other. Each
        place carries the text as typed and is marked
        ``ADDED_BY_HAND_SOURCE``.
        """
        units: list[tuple[str | None, str]] = (
            [(label, cell_text) for label, cell_text in self.cell_texts.items()]
            if self.cell_texts
            else [(None, self.document_text)]
        )
        return [
            DetectedEntity(
                text=text,
                entity_type=entity_type,
                start_pos=start,
                end_pos=end,
                confidence=None,
                gender=None,
                is_ambiguous=False,
                source=ADDED_BY_HAND_SOURCE,
                context_label=label,
            )
            for label, unit in units
            for start, end in whole_word_places(text, unit)
        ]

    def is_listed_place(self, place: DetectedEntity) -> bool:
        """Whether a place is already in the review (Story 10.15, AC14 (b)).

        True when a review holds an entity with the same type, span and cell
        whose text is a form of the place's text (Story 10.19, AC2: a found
        « ZORBAL » for an added « Zorbal »): a place the detector found, which
        keeps its own decision, or a place added by an earlier [A].
        """
        return any(
            is_form(review.entity.text, place.text)
            and review.entity.entity_type == place.entity_type
            and review.entity.start_pos == place.start_pos
            and review.entity.end_pos == place.end_pos
            and review.entity.context_label == place.context_label
            for review in self._entity_reviews
        )

    def add_entity(self, entity: DetectedEntity) -> None:
        """Add detected entity to validation session.

        Args:
            entity: Entity detected by NLP engine
        """
        self.entities.append(entity)
        self._entity_reviews.append(
            EntityReview(entity=entity, state=EntityReviewState.PENDING)
        )

    def get_entity_review(self, entity: DetectedEntity) -> EntityReview | None:
        """Get EntityReview for a given DetectedEntity.

        Args:
            entity: Entity to find review for

        Returns:
            EntityReview if found, None otherwise
        """
        for review in self._entity_reviews:
            if review.entity == entity:
                return review
        return None

    def get_pending_entities(self) -> list[DetectedEntity]:
        """Get all entities that have not been reviewed yet.

        Returns:
            List of entities with PENDING state
        """
        decided_ids = {d.entity_id for d in self.user_decisions}
        return [
            review.entity
            for review in self._entity_reviews
            if review.entity_id not in decided_ids
        ]

    def mark_confirmed(self, entity: DetectedEntity) -> None:
        """Mark entity as confirmed by user.

        Args:
            entity: Entity to confirm
        """
        review = self.get_entity_review(entity)
        if review:
            review.state = EntityReviewState.CONFIRMED
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="CONFIRM",
                    original_entity=entity,
                )
            )

    def mark_rejected(self, entity: DetectedEntity) -> None:
        """Mark entity as rejected (false positive).

        Args:
            entity: Entity to reject
        """
        review = self.get_entity_review(entity)
        if review:
            review.state = EntityReviewState.REJECTED
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="REJECT",
                    original_entity=entity,
                )
            )

    def mark_modified(self, original: DetectedEntity, modified: DetectedEntity) -> None:
        """Mark entity as modified by user.

        Args:
            original: Original detected entity
            modified: Modified entity (corrected text, span or type)
        """
        review = self.get_entity_review(original)
        if review:
            review.state = EntityReviewState.MODIFIED
            review.user_modification = modified.text
            review.modified_entity = modified
            # Story 10.11 (Lionel's Q-E): a custom pseudonym belongs to the
            # name it was set on; correcting the name or its type removes it.
            review.custom_pseudonym = None
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="MODIFY",
                    original_entity=original,
                    modified_entity=modified,
                )
            )

    def add_manual_entity(self, new_entity: DetectedEntity) -> None:
        """Add manually added entity to session.

        Args:
            new_entity: Entity manually added by user
        """
        self.entities.append(new_entity)
        review = EntityReview(entity=new_entity, state=EntityReviewState.ADDED)
        self._entity_reviews.append(review)
        self.user_decisions.append(
            UserDecision(
                entity_id=review.entity_id,
                action="ADD",
                modified_entity=new_entity,
            )
        )

    def change_entity_type(self, entity: DetectedEntity, new_type: str) -> None:
        """Change the type of an entity (e.g., a person detected as LOCATION).

        Recorded as a modification: text, span and cell are kept, only the
        type changes (Story 10.15, AC1). The entity retyped is the one the
        review sends: an earlier correction is kept (Story 10.11, AC11, PO F2).

        Args:
            entity: Entity to retype
            new_type: New entity type (PERSON, LOCATION, or ORG)
        """
        review = self.get_entity_review(entity)
        sent = (
            review.modified_entity
            if review is not None and review.modified_entity is not None
            else entity
        )
        self.mark_modified(
            entity, replace(sent, entity_type=new_type, is_ambiguous=False)
        )

    def change_pseudonym(self, entity: DetectedEntity, new_pseudonym: str) -> None:
        """Change pseudonym for an entity.

        Args:
            entity: Entity to change pseudonym for
            new_pseudonym: Custom pseudonym
        """
        review = self.get_entity_review(entity)
        if review:
            review.custom_pseudonym = new_pseudonym
            review.state = EntityReviewState.CONFIRMED
            self.user_decisions.append(
                UserDecision(
                    entity_id=review.entity_id,
                    action="CHANGE_PSEUDONYM",
                    original_entity=entity,
                    new_pseudonym=new_pseudonym,
                )
            )

    def get_validated_entities(self) -> list[DetectedEntity]:
        """Get final list of validated entities after user review.

        Each entity follows its last decision (Story 10.11, AC11): one whose
        current state is confirmed or modified is sent, with its correction
        whenever it has one; rejected and pending ones are not, and an
        earlier reject no longer counts. Manually added entities are
        included.

        Returns:
            List of validated entities ready for pseudonymization
        """
        added_entities = [
            d.modified_entity
            for d in self.user_decisions
            if d.action == "ADD" and d.modified_entity
        ]

        validated = []
        for review in self._entity_reviews:
            if review.state not in (
                EntityReviewState.CONFIRMED,
                EntityReviewState.MODIFIED,
            ):
                continue
            validated.append(self._sent_entity(review))

        return validated + added_entities

    @staticmethod
    def _sent_entity(review: EntityReview) -> DetectedEntity:
        """The entity a kept review sends: its correction whenever it has one
        (Story 10.11, AC11), else the detected entity. A corrected text
        without a corrected entity keeps the detected entity's span and cell
        (Story 10.15, AC1)."""
        if review.modified_entity is not None:
            return review.modified_entity
        if review.state == EntityReviewState.MODIFIED and review.user_modification:
            return replace(review.entity, text=review.user_modification)
        return review.entity

    def get_custom_pseudonyms(self) -> dict[tuple[str, str], str]:
        """Custom pseudonym of each name sent for finalization (Story 10.11).

        Keyed by the mapping key of the entity a kept review sends and its
        type; the first review of a name that holds one gives it.
        """
        customs: dict[tuple[str, str], str] = {}
        for review in self._entity_reviews:
            if not review.custom_pseudonym:
                continue
            if review.state not in (
                EntityReviewState.CONFIRMED,
                EntityReviewState.MODIFIED,
            ):
                continue
            sent = self._sent_entity(review)
            name = (mapping_key(sent.text, sent.entity_type), sent.entity_type)
            customs.setdefault(name, review.custom_pseudonym)
        return customs

    def get_entity_groups(self, entity_type: str | None = None) -> list[EntityGroup]:
        """Get entities grouped by variant forms of the same real-world entity.

        Uses variant-aware grouping to merge different text forms of the same
        entity (e.g., "Marie Dubois" / "Pr. Dubois" / "Dubois") into single
        review items. Falls back to exact-match grouping for unknown types.

        Args:
            entity_type: Filter by entity type (PERSON, LOCATION, ORG) or None for all

        Returns:
            List of EntityGroup objects sorted by first occurrence position
        """
        from gdpr_pseudonymizer.nlp.entity_grouping import group_entity_variants

        # Filter entities by type if requested
        filtered_entities = [
            e
            for e in self.entities
            if entity_type is None or e.entity_type == entity_type
        ]

        # Use variant-aware grouping
        variant_groups = group_entity_variants(filtered_entities)

        # Convert to EntityGroup objects
        groups = [
            EntityGroup(
                unique_key=(canonical.text, canonical.entity_type),
                occurrences=occurrences,
                variant_texts=variant_texts,
                canonical_entity=canonical,
            )
            for canonical, occurrences, variant_texts in variant_groups
        ]

        # Sort groups by position of first occurrence
        groups = sorted(groups, key=lambda g: g.occurrences[0].start_pos)
        return sorted(
            self._join_forms(groups), key=lambda g: g.occurrences[0].start_pos
        )

    def _join_forms(self, groups: list[EntityGroup]) -> list[EntityGroup]:
        """The groups, those that are forms of one name joined (Story 10.19,
        AC3; the PO's M2 on v1.1).

        Taken left to right, a group joins the first kept group of the same
        type when every text of one (its key and its variant texts) is a form
        of a text of the other (``is_form``), either way round: « Vorlène »
        and « VORLENE » are one name. Each group is compared with its own
        texts only, never with texts an earlier join gave it, so a join never
        chains (the orchestrator's ruling on the PO's v1.2 M1): with
        « Vorlène », and « VORLENE » grouped with « Vorlene », the two stay
        apart. The joined group keeps the first group's key and canonical
        entity, takes both groups' places in the order of the session's
        entities, and the union of their variant texts.
        """
        order = {id(entity): index for index, entity in enumerate(self.entities)}
        kept: list[tuple[EntityGroup, set[str]]] = []
        for group in groups:
            texts = {group.unique_key[0], *group.variant_texts}
            for first, first_texts in kept:
                if first.unique_key[1] != group.unique_key[1]:
                    continue
                if _all_forms(texts, first_texts) or _all_forms(first_texts, texts):
                    first.occurrences = sorted(
                        [*first.occurrences, *group.occurrences],
                        key=lambda entity: order.get(id(entity), len(order)),
                    )
                    first.variant_texts = first.variant_texts | group.variant_texts
                    break
            else:
                kept.append((group, texts))
        return [group for group, _ in kept]

    def names_left_in_clear(
        self, sent_without_review: Iterable[DetectedEntity] = ()
    ) -> int:
        """Count pending review groups left in clear for Story 10.13.

        Lionel's decision of 2026-10-16 includes pending occurrences only
        and counts coverage by validated entities and names sent without review.

        Args:
            sent_without_review: Known entities written without review.
        """
        pending: list[tuple[NameOfReview, list[Place]]] = []
        for group in self.get_entity_groups():
            places: list[Place] = []
            for entity in group.occurrences:
                review = self.get_entity_review(entity)
                if review is not None and review.state == EntityReviewState.PENDING:
                    places.append(place_of(entity))
            if places:
                pending.append((group.unique_key, places))
        return count_names_left_in_clear(
            pending, [*self.get_validated_entities(), *sent_without_review]
        )

    def get_summary_stats(self) -> dict[str, int]:
        """Get summary statistics of validation decisions.

        Returns:
            Dictionary with counts of confirmed, rejected, modified, added entities,
            including unique entity counts for deduplication display
        """
        confirmed = sum(1 for d in self.user_decisions if d.action == "CONFIRM")
        rejected = sum(1 for d in self.user_decisions if d.action == "REJECT")
        modified = sum(1 for d in self.user_decisions if d.action == "MODIFY")
        added = sum(1 for d in self.user_decisions if d.action == "ADD")
        changed_pseudonym = sum(
            1 for d in self.user_decisions if d.action == "CHANGE_PSEUDONYM"
        )

        # Calculate unique entity count
        unique_count = len(self.get_entity_groups())

        return {
            "confirmed": confirmed,
            "rejected": rejected,
            "modified": modified,
            "added": added,
            "changed_pseudonym": changed_pseudonym,
            "total": len(self.entities),
            "unique": unique_count,
        }
