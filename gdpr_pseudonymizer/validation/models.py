"""Validation data models for human-in-the-loop entity review."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypeAlias

from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


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
    """

    document_path: str
    document_text: str
    entities: list[DetectedEntity] = field(default_factory=list)
    context_cache: dict[str, str] = field(default_factory=dict)
    user_decisions: list[UserDecision] = field(default_factory=list)
    current_index: int = 0
    current_entity_type: str = "PERSON"
    _entity_reviews: list[EntityReview] = field(default_factory=list)

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

        Recorded as a modification: text and span are kept, only the type
        changes. The entity retyped is the one the review sends: an earlier
        correction is kept (Story 10.11, AC11, PO F2).

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
            entity,
            DetectedEntity(
                text=sent.text,
                entity_type=new_type,
                start_pos=sent.start_pos,
                end_pos=sent.end_pos,
                confidence=sent.confidence,
                gender=sent.gender,
                is_ambiguous=False,
                source=sent.source,
            ),
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
        (Story 10.11, AC11), else the detected entity."""
        if review.modified_entity is not None:
            return review.modified_entity
        if review.state == EntityReviewState.MODIFIED and review.user_modification:
            return DetectedEntity(
                text=review.user_modification,
                entity_type=review.entity.entity_type,
                start_pos=review.entity.start_pos,
                end_pos=review.entity.end_pos,
                confidence=review.entity.confidence,
                gender=review.entity.gender,
                is_ambiguous=review.entity.is_ambiguous,
            )
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
        return sorted(groups, key=lambda g: g.occurrences[0].start_pos)

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
