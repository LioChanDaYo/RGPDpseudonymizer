"""Document processor for single-document pseudonymization workflow.

This module orchestrates the complete pseudonymization workflow by integrating:
- NLP entity detection (HybridDetector)
- Compositional pseudonym assignment (CompositionalPseudonymEngine)
- Encrypted entity storage (MappingRepository)
- Audit logging (AuditRepository)
- File I/O with exclusion zones (file_handler)

This is the core workflow implementation for Story 2.6.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from gdpr_pseudonymizer.core.custom_pseudonym import (
    CUSTOM_THEME,
    CustomReservations,
    NameKey,
    PseudonymChecker,
    Refusal,
    check_custom_pseudonym,
    custom_entity_fields,
    document_words,
    finalization_message,
    fold,
    real_name_check,
    takes_custom_value,
    untracked_custom_values,
)
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.core.saved_own_words import count_own_word_rows
from gdpr_pseudonymizer.data.database import (
    DatabaseSession,
    open_database,
    pseudonym_lock,
)
from gdpr_pseudonymizer.data.models import Entity, Operation
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    MappingRepository,
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import CustomPseudonymError, SpreadsheetCellError
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.nlp.model_names import resolve_spacy_model
from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
)
from gdpr_pseudonymizer.pseudonym.gender_detector import GenderDetector
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager
from gdpr_pseudonymizer.utils.file_handler import (
    get_file_extension,
    read_file,
    write_file,
)
from gdpr_pseudonymizer.utils.logger import get_logger
from gdpr_pseudonymizer.utils.tabular_reader import (
    TabularDocument,
    read_csv_structured,
    read_excel_structured,
)
from gdpr_pseudonymizer.utils.text_form import mark_class
from gdpr_pseudonymizer.validation.models import (
    TYPED_SOURCES,
    CandidateKey,
    candidate_key,
)
from gdpr_pseudonymizer.validation.workflow import (
    ask_for_missed_names,
    run_validation_workflow,
)

# Configure logging (NO sensitive data)
logger = get_logger(__name__)

# Story 10.15 (AC4, Lionel's approved Q1 text): a validated name of a
# spreadsheet matches no cell. ``_sanitize_error_message`` puts the class
# name in front; the text names no name and no cell. Kept on one line so that
# it can be checked byte for byte.
SPREADSHEET_CELL_ERROR = "A name you validated could not be placed in its cell in the Excel or CSV file, so it would have stayed in plain text. No output was written for this file and no pseudonym was stored. Please report this problem."


@dataclass(frozen=True)
class PseudonymProposal:
    """A pseudonym the review showed for a name not yet stored (Story 11.5)."""

    entity_type: str  # the type it was drawn for
    theme: str  # the theme it was drawn from
    pseudonym_full: str  # without a title
    pseudonym_first: str | None
    pseudonym_last: str | None
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


@dataclass(frozen=True)
class ChangedPseudonym:
    """A name written with another pseudonym than the one shown (Story 11.5)."""

    name: str  # the mapping key of the name sent
    entity_type: str
    shown: str
    written: str


# Story 11.5: a pseudonym shown for a name, with the name and the confidence
# its saved row would carry, in the order the names are checked
_OrderedProposal = tuple[NameKey, PseudonymProposal, float | None]


@dataclass
class ProcessingResult:
    """Result of document processing operation.

    Attributes:
        success: Whether processing completed successfully
        input_file: Input file path
        output_file: Output file path
        entities_detected: Total number of entities detected
        entities_new: Number of newly assigned pseudonyms
        entities_reused: Number of reused pseudonyms (idempotency)
        processing_time_seconds: Total processing time in seconds
        error_message: Error description if processing failed
        entity_type_counts: Per-type entity counts from this document
        own_word_rows: Saved rows whose pseudonym holds a word of their own
            name, counted once this document is written (Story 11.7), the
            rows it saved included
        pseudonyms_changed: The pseudonyms the review showed that could not
            be written, each with the one written (Story 11.5); empty when
            every pseudonym shown was written, and without a review
    """

    success: bool
    input_file: str
    output_file: str
    entities_detected: int
    entities_new: int
    entities_reused: int
    processing_time_seconds: float
    error_message: str | None = None
    entity_type_counts: dict[str, int] | None = None
    own_word_rows: int = 0
    pseudonyms_changed: list[ChangedPseudonym] = field(default_factory=list)


@dataclass
class _ProcessingContext:
    """Bundle of dependencies initialized per-document processing.

    Groups the repositories and engines that are created once per
    process_document() call and shared across all sub-methods.
    """

    mapping_repo: MappingRepository
    audit_repo: AuditRepository
    pseudonym_manager: LibraryBasedPseudonymManager
    compositional_engine: CompositionalPseudonymEngine


@dataclass
class _ResolveResult:
    """Result of entity pseudonym resolution."""

    replacements: list[tuple[int, int, str]]
    entities_new: int
    entities_reused: int
    entity_type_counts: dict[str, int]
    # Story 11.7: the rows this document saved (for the notice's count)
    saved_entities: list[Entity] = field(default_factory=list)
    # Story 11.5: the pseudonyms shown that could not be written
    pseudonyms_changed: list[ChangedPseudonym] = field(default_factory=list)


class DocumentProcessor:
    """Orchestrates single-document pseudonymization workflow.

    This processor integrates all Epic 2 components to provide a complete
    production-ready pseudonymization workflow with idempotency, compositional
    logic, encrypted storage, and comprehensive audit logging.

    Example:
        >>> processor = DocumentProcessor(
        ...     db_path="mappings.db",
        ...     passphrase="my_secure_passphrase",
        ...     theme="neutral",
        ...     model_name="spacy"
        ... )
        >>> result = processor.process_document("input.txt", "output.txt")
        >>> print(f"Processed {result.entities_detected} entities in {result.processing_time_seconds}s")
    """

    def __init__(
        self,
        db_path: str,
        passphrase: str,
        theme: str = "neutral",
        model_name: str = "spacy",
        notifier: Callable[[str], None] | None = None,
    ):
        """Initialize document processor with database and configuration.

        Args:
            db_path: Path to SQLite database file
            passphrase: Encryption passphrase for database access
            theme: Pseudonym library theme (neutral/star_wars/lotr)
            model_name: NLP model: "spacy" (default French model) or a spaCy
                package name (e.g., "en_core_web_trf")
            notifier: Optional callback for user-facing messages.
                     Decouples core from CLI presentation layer.

        Raises:
            ValueError: If passphrase invalid or database cannot be opened
            FileNotFoundError: If database file doesn't exist
        """
        self.db_path = db_path
        self.passphrase = passphrase
        self.theme = theme
        self.model_name = model_name
        self._notifier = notifier or (lambda msg: None)

        # Database session will be created per operation (context manager pattern)
        self._db_session: DatabaseSession | None = None

        # NLP detector (initialized lazily)
        self._detector: HybridDetector | None = None

        # Story 10.11 (AC3, AC19): folded values a generated pseudonym must
        # not take: every beginning and ending of a person's custom
        # pseudonym, each with the real words that own it in their role
        # (Story 10.16, Codex #6; ``untracked_custom_values``). Set per
        # document by _reset_pseudonym_state, and again when this run's
        # custom pseudonyms are registered.
        self._custom_taken: CustomReservations = {}

    def _get_detector(self) -> HybridDetector:
        """Get or initialize hybrid entity detector.

        Returns:
            HybridDetector instance

        Raises:
            OSError: If spaCy model not installed
        """
        if self._detector is None:
            self._detector = HybridDetector(
                default_model=resolve_spacy_model(self.model_name)
            )
        return self._detector

    def _detect_and_filter_entities(
        self,
        document_text: str,
        entity_type_filter: set[str] | None = None,
    ) -> list[DetectedEntity]:
        """Detect entities in document text and apply optional type filter.

        Args:
            document_text: The document text to analyze
            entity_type_filter: Optional set of entity types to keep

        Returns:
            List of detected (and optionally filtered) entities
        """
        logger.info("detecting_entities", model=self.model_name)
        detector = self._get_detector()
        detected_entities = detector.detect_entities(document_text)

        if entity_type_filter:
            pre_filter_count = len(detected_entities)
            detected_entities = [
                e for e in detected_entities if e.entity_type in entity_type_filter
            ]
            logger.info(
                "entity_type_filter_applied",
                allowed_types=sorted(entity_type_filter),
                pre_filter_count=pre_filter_count,
                post_filter_count=len(detected_entities),
            )

        logger.info(
            "entities_detected",
            count=len(detected_entities),
            unique_count=len(set(e.text for e in detected_entities)),
        )

        return detected_entities

    @staticmethod
    def _normalize_entity_text(ctx: _ProcessingContext, entity: DetectedEntity) -> str:
        """Normalize entity text into the mapping key.

        Applies strip_titles for all entities, then strip_prepositions
        for LOCATION entities, then collapses every whitespace run (line
        breaks, tabs, no-break spaces, repeated spaces) to one space, so a
        name hard-wrapped over a line break gets the same key as its one-line
        spelling (10.3a QA REL-001). A key with single spaces only is
        unchanged. Used for DB lookups and pseudonym assignment, by the
        validation preview and the known-entity check, and by the desktop
        app's known-entity check, so they all agree: they all call
        ``mapping_key`` (Story 10.7). A mapping row is identified by this key
        and the entity type.

        Args:
            ctx: Processing context (unused; kept for the callers)
            entity: Detected entity to normalize

        Returns:
            Stripped entity text ready for lookup/assignment
        """
        return mapping_key(entity.text, entity.entity_type)

    def _build_pseudonym_assigner(
        self,
        ctx: _ProcessingContext,
        proposals: dict[NameKey, PseudonymProposal] | None = None,
    ) -> Callable[[DetectedEntity], str]:
        """Build a closure that generates pseudonym previews for validation.

        The returned callable looks up existing mappings first, then generates
        new pseudonyms via the compositional engine. An internal cache ensures
        consistent component reuse within a single validation session.

        Args:
            ctx: Processing context with repos and engine
            proposals: When given, each new pseudonym drawn is recorded there,
                keyed by (mapping key, type), in the order drawn (Story 11.5:
                what the review showed, kept at the end if still free). A
                stored name's pseudonym and the fallback are not recorded.

        Returns:
            Callable that maps DetectedEntity -> pseudonym preview string
        """
        # Keyed on (mapping key, entity type): each type of a text gets its
        # own preview (Story 10.7, AC2)
        preview_cache: dict[tuple[str, str], str] = {}

        def pseudonym_assigner(entity: DetectedEntity) -> str:
            entity_text_stripped = DocumentProcessor._normalize_entity_text(ctx, entity)

            existing_entity = ctx.mapping_repo.find_by_full_name_and_type(
                entity_text_stripped, entity.entity_type
            )
            if existing_entity:
                return existing_entity.pseudonym_full

            cache_key = (entity_text_stripped, entity.entity_type)
            if cache_key in preview_cache:
                return preview_cache[cache_key]

            try:
                assignment = ctx.compositional_engine.assign_compositional_pseudonym(
                    entity_text=entity_text_stripped,
                    entity_type=entity.entity_type,
                    gender=None,
                )
                preview_cache[cache_key] = assignment.pseudonym_full
                if proposals is not None:
                    proposals.setdefault(
                        cache_key,
                        PseudonymProposal(
                            entity_type=entity.entity_type,
                            theme=self.theme,
                            pseudonym_full=assignment.pseudonym_full,
                            pseudonym_first=assignment.pseudonym_first,
                            pseudonym_last=assignment.pseudonym_last,
                            is_ambiguous=assignment.is_ambiguous,
                            ambiguity_reason=assignment.ambiguity_reason,
                        ),
                    )
                return assignment.pseudonym_full
            except (ValueError, RuntimeError) as e:
                logger.warning(
                    "pseudonym_preview_fallback",
                    entity_type=entity.entity_type,
                    error_type=type(e).__name__,
                )
                return f"[{entity.entity_type}_PREVIEW]"

        return pseudonym_assigner

    def _run_validation(
        self,
        ctx: _ProcessingContext,
        detected_entities: list[DetectedEntity],
        document_text: str,
        input_path: str,
        skip_validation: bool,
        pseudonym_assigner: Callable[[DetectedEntity], str],
        custom_pseudonyms: dict[NameKey, str] | None = None,
        cells: dict[str, str] | None = None,
        types_selected: bool = False,
        shown_names: dict[NameKey, list[NameKey]] | None = None,
        on_custom_set: Callable[[Mapping[NameKey, str]], None] | None = None,
    ) -> list[DetectedEntity]:
        """Run entity validation workflow (interactive or auto-accept).

        ``custom_pseudonyms``, when given, is filled with the custom
        pseudonyms the user set in the review (Story 10.11), keyed by
        (mapping key, type) of the name sent. ``shown_names``, when given,
        is filled with the names each name sent was shown for, and
        ``on_custom_set`` is called after each custom pseudonym set (Story
        11.5; ``run_validation_workflow``). ``cells`` (cell reference ->
        cell text) is given for a spreadsheet, whose entities' positions
        point into their cells (Story 10.15); None for a text document.
        The places the user typed (added with [A] or corrected with [E]) are
        widened over the other names sent (``_widen_added_places``).

        When nothing is left to review (no name found, or only names already
        stored under the same type), the command line asks whether to add a
        name the detector missed (``ask_for_missed_names``, Story 10.18);
        ``types_selected`` (``--entity-types`` given) chooses its lines.
        """
        if skip_validation:
            logger.info(
                "validation_skipped",
                auto_accepted_count=len(detected_entities),
                reason="parallel_mode",
            )
            return detected_entities

        # Separate entities into known (auto-accept) and unknown (need validation).
        # Known means stored under the same type (Story 10.7, AC2): a text
        # stored only under another type reaches validation.
        known_entities: list[DetectedEntity] = []
        unknown_entities: list[DetectedEntity] = []

        for entity in detected_entities:
            entity_text_stripped = self._normalize_entity_text(ctx, entity)

            existing = ctx.mapping_repo.find_by_full_name_and_type(
                entity_text_stripped, entity.entity_type
            )
            if existing:
                known_entities.append(entity)
            else:
                unknown_entities.append(entity)

        if known_entities:
            auto_accept_count = len(known_entities)
            unique_known = len(set(e.text for e in known_entities))
            self._notifier(
                f"Auto-accepted {auto_accept_count} known entities "
                f"({unique_known} unique) with existing mappings"
            )
            logger.info(
                "auto_accepted_known_entities",
                auto_accepted_count=auto_accept_count,
                unique_count=unique_known,
            )

        try:
            if unknown_entities:
                validated_unknown = run_validation_workflow(
                    entities=unknown_entities,
                    document_text=document_text,
                    document_path=input_path,
                    pseudonym_assigner=pseudonym_assigner,
                    pseudonym_checker=self._build_custom_pseudonym_checker(
                        ctx, document_text, known_entities=known_entities
                    ),
                    custom_pseudonyms=custom_pseudonyms,
                    # Names known in the mapping database are written without review.
                    sent_without_review=known_entities,
                    cells=cells,
                    shown_names=shown_names,
                    on_custom_set=on_custom_set,
                )
            else:
                # Story 10.18: nothing is left to review; the command line
                # asks whether to add a name the detector missed. The names
                # added are widened below with the stored names (10.15's F1).
                validated_unknown = ask_for_missed_names(
                    document_text,
                    input_path,
                    nothing_found=not detected_entities,
                    cells=cells,
                    types_selected=types_selected,
                )

            # Story 10.15 (AC14 (d)): over every name sent, stored names
            # accepted without review included
            validated_entities = self._widen_added_places(
                known_entities + validated_unknown
            )
            logger.info(
                "validation_complete",
                validated_count=len(validated_entities),
                original_count=len(detected_entities),
                auto_accepted=len(known_entities),
                user_validated=len(validated_unknown),
            )
            return validated_entities
        except KeyboardInterrupt:
            logger.info("validation_cancelled", reason="user_interrupt")
            raise

    @staticmethod
    def _widen_added_places(entities: list[DetectedEntity]) -> list[DetectedEntity]:
        """Widen each place the user typed over the names it partly overlaps
        (Story 10.15, AC14 (d), Lionel's Q4; v1.4/v1.5: corrections too).

        A typed place (its source is in ``TYPED_SOURCES``: added with [A], or
        any place a correction made with [E] reaches) that partly overlaps
        another name of the list in the same text or cell (they overlap and
        neither span holds the other) is widened to cover both, again until
        it partly overlaps no other span of the list, the other typed places'
        widened spans included. Its text and type are kept, so the whole span
        is written with the typed name's pseudonym and nothing of either name
        stays in plain text there. Typed places are taken in the order of the
        list: when two of them partly overlap each other, the first widens
        over the second, which then lies inside it and is covered by it. They
        end with the same span only when a third name widens both to the
        same union; the writer then keeps the first of the two in the list,
        its sort being stable. Either way the first in the list gives the
        pseudonym. Every other entity, and the order, are unchanged.
        """
        spans = [(entity.start_pos, entity.end_pos) for entity in entities]
        typed = [
            index
            for index, entity in enumerate(entities)
            if entity.source in TYPED_SOURCES
        ]
        changed = True
        while changed:
            changed = False
            for index in typed:
                start, end = spans[index]
                label = entities[index].context_label
                for other_index, (other_start, other_end) in enumerate(spans):
                    if (
                        other_index == index
                        or entities[other_index].context_label != label
                    ):
                        continue
                    overlaps = other_start < end and start < other_end
                    holds = start <= other_start and other_end <= end
                    held = other_start <= start and end <= other_end
                    if overlaps and not holds and not held:
                        start, end = min(start, other_start), max(end, other_end)
                        changed = True
                spans[index] = (start, end)
        return [
            (
                entity
                if (start, end) == (entity.start_pos, entity.end_pos)
                else replace(entity, start_pos=start, end_pos=end)
            )
            for entity, (start, end) in zip(entities, spans)
        ]

    @staticmethod
    def _check_cells(
        tabular_doc: TabularDocument, validated_entities: list[DetectedEntity]
    ) -> None:
        """Check that every validated name of a spreadsheet matches a cell
        (Story 10.15, AC4), before any pseudonym is stored.

        A name matches a cell when its ``context_label`` is the reference of
        a cell of the document and its span lies inside that cell's text.

        Raises:
            SpreadsheetCellError: If one does not. Neither the log event nor
                the message names a name, a cell or a position.
        """
        cell_texts = {cell.cell_ref: cell.value for cell in tabular_doc.cells}
        for entity in validated_entities:
            label = entity.context_label
            cell_text = cell_texts.get(label) if label is not None else None
            if cell_text is None or not (
                0 <= entity.start_pos < entity.end_pos <= len(cell_text)
            ):
                logger.error("tabular_entity_without_cell")
                raise SpreadsheetCellError(SPREADSHEET_CELL_ERROR)

    @staticmethod
    def _build_custom_pseudonym_checker(
        ctx: _ProcessingContext,
        document_text: str,
        known_entities: list[DetectedEntity] | None = None,
    ) -> PseudonymChecker:
        """The command line's check of a custom pseudonym when it is set
        (Story 10.11): the stored rows are read at each check.

        Story 10.16 (Codex #8): the review's names (every name not rejected,
        from the [C] branch) and the names known in the mapping database
        (``known_entities``, sent to the file without review) count whatever
        their capitals, so a pseudonym accepted here is not refused at
        finalization."""
        known_names = [
            DocumentProcessor._normalize_entity_text(ctx, entity)
            for entity in known_entities or []
        ]

        def checker(
            name: str,
            entity_type: str,
            pseudonym: str,
            other_customs: Mapping[NameKey, str],
            review_names: Iterable[str],
        ) -> Refusal | None:
            return check_custom_pseudonym(
                ctx.mapping_repo.find_all(),
                name,
                entity_type,
                pseudonym,
                document_text,
                other_customs,
                review_names=[*review_names, *known_names],
            )

        return checker

    def _register_custom_pseudonyms(
        self,
        ctx: _ProcessingContext,
        custom_pseudonyms: dict[NameKey, str],
        document_text: str,
        entity_cache: dict[tuple[str, str], str],
        new_entities: list[Entity],
        sent_names: Iterable[str] = (),
    ) -> set[NameKey]:
        """Check every custom pseudonym again, then register it first (10.11).

        The last check: the database may have changed since the pseudonym
        was set, and ``sent_names`` (the mapping keys of the names sent)
        count whatever their capitals (Story 10.16, Codex #8). A refusal
        raises before anything is saved or written. Then
        each name gets its new row (saved with the run's other new rows),
        the library marks its pseudonym and its bound parts as used, the
        values a generated pseudonym must not take are kept (AC19), and the
        run's cache holds it, so every
        occurrence of the name takes it and a lone first or last name of the
        run takes the matching part.

        Returns:
            The names registered (their first occurrence counts as new)

        Raises:
            CustomPseudonymError: If a custom pseudonym breaks a rule
        """
        if not custom_pseudonyms:
            return set()
        stored = ctx.mapping_repo.find_all()
        self._check_custom_pseudonyms(
            stored, custom_pseudonyms, document_text, sent_names
        )
        return self._register_custom_rows(
            ctx, custom_pseudonyms, stored, entity_cache, new_entities
        )

    @staticmethod
    def _check_custom_pseudonyms(
        stored: list[Entity],
        custom_pseudonyms: Mapping[NameKey, str],
        document_text: str,
        sent_names: Iterable[str] = (),
    ) -> None:
        """The last check of every custom pseudonym (Story 10.11), against
        the stored rows given.

        Raises:
            CustomPseudonymError: If a custom pseudonym breaks a rule
        """
        names = sorted(custom_pseudonyms)
        words = document_words(document_text)  # read once (QA PERF-001, PO A5)
        sent = list(sent_names)
        for name in names:
            others = {k: v for k, v in custom_pseudonyms.items() if k != name}
            refusal = check_custom_pseudonym(
                stored,
                name[0],
                name[1],
                custom_pseudonyms[name],
                document_text,
                others,
                words,
                review_names=sent,
            )
            if refusal is not None:
                logger.warning("custom_pseudonym_refused", reason=refusal.reason.value)
                raise CustomPseudonymError(finalization_message(refusal))

    def _register_custom_rows(
        self,
        ctx: _ProcessingContext,
        custom_pseudonyms: Mapping[NameKey, str],
        stored: list[Entity],
        entity_cache: dict[tuple[str, str], str],
        new_entities: list[Entity],
    ) -> set[NameKey]:
        """Register every custom pseudonym first (Story 10.11), the stored
        rows given: each name gets its new row, the library marks its
        pseudonym and its bound parts as used, the values a generated
        pseudonym must not take are kept (AC19), and the run's cache holds
        it. Story 11.5: shared by the end (after its check) and the review's
        update (without it).

        Returns:
            The names registered
        """
        if not custom_pseudonyms:
            return set()
        names = sorted(custom_pseudonyms)
        custom_rows: list[Entity] = []
        for name in names:
            text, entity_type = name
            pseudonym = custom_pseudonyms[name]
            row = Entity(
                entity_type=entity_type,
                full_name=text,
                pseudonym_full=pseudonym,
                first_seen_timestamp=datetime.now(UTC),
                theme=CUSTOM_THEME,
                **custom_entity_fields(
                    text, entity_type, pseudonym, stored, custom_pseudonyms
                ),
            )
            ctx.pseudonym_manager.load_existing_mappings([row])
            entity_cache[name] = pseudonym
            new_entities.append(row)
            custom_rows.append(row)
        # With every stored row, so that a value a real word already has as
        # its part is not kept (QA GUARD-001, AC19)
        self._custom_taken = untracked_custom_values([*stored, *custom_rows])
        logger.info("custom_pseudonyms_registered", count=len(names))
        return set(names)

    def _check_component_match(
        self,
        ctx: _ProcessingContext,
        entity_text_stripped: str,
        new_entities: list[Entity],
    ) -> str | None:
        """Check if a standalone PERSON name matches a component of a previously processed entity.

        For example, if "Dubois" is encountered after "Marie Dubois" was already
        processed (but not yet saved to DB), this finds the matching component
        pseudonym from new_entities.

        Args:
            ctx: Processing context with compositional engine
            entity_text_stripped: Stripped entity text to match
            new_entities: Previously processed new entities in this document

        Returns:
            Matching pseudonym component string, or None if no match found
        """
        try:
            parsed_first, parsed_last, is_ambiguous = (
                ctx.compositional_engine.parse_full_name(entity_text_stripped)
            )
        except (TypeError, ValueError):
            return None

        if not (is_ambiguous and parsed_first and not parsed_last):
            return None

        for prev_entity in new_entities:
            if prev_entity.entity_type != "PERSON":
                continue
            if prev_entity.first_name == parsed_first:
                logger.debug(
                    "component_matched_in_batch",
                    component=parsed_first,
                    component_type="first_name",
                    matched_entity=prev_entity.full_name,
                )
                return prev_entity.pseudonym_first
            if prev_entity.last_name == parsed_first:
                logger.debug(
                    "component_matched_in_batch",
                    component=parsed_first,
                    component_type="last_name",
                    matched_entity=prev_entity.full_name,
                )
                return prev_entity.pseudonym_last

        return None

    def _compute_replacement_prefix(
        self,
        ctx: _ProcessingContext,
        entity: DetectedEntity,
    ) -> str:
        """Compute the title/preposition prefix to preserve in replacement text.

        Ensures "Dr. Marie Dubois" -> "Dr. Emma Martin" (not "Emma Martin")
        and "à Paris" -> "à Lyon" (not "Lyon").

        Args:
            ctx: Processing context with compositional engine
            entity: Original detected entity

        Returns:
            Prefix string to prepend to the pseudonym (empty if none)
        """
        original_text = entity.text
        if entity.entity_type == "PERSON":
            stripped = ctx.compositional_engine.strip_titles(original_text)
            if stripped != original_text:
                prefix_end = original_text.find(stripped)
                if prefix_end > 0:
                    return original_text[:prefix_end]
        elif entity.entity_type == "LOCATION":
            temp_stripped = ctx.compositional_engine.strip_titles(original_text)
            stripped = ctx.compositional_engine.strip_prepositions(temp_stripped)
            if stripped != temp_stripped:
                prefix_end = temp_stripped.find(stripped)
                if prefix_end > 0:
                    return temp_stripped[:prefix_end]
        return ""

    def _assign_new_pseudonym(
        self,
        ctx: _ProcessingContext,
        entity: DetectedEntity,
        entity_text_stripped: str,
    ) -> tuple[str, Entity]:
        """Assign a new compositional pseudonym and create the Entity record."""
        assignment = ctx.compositional_engine.assign_compositional_pseudonym(
            entity_text=entity_text_stripped,
            entity_type=entity.entity_type,
            gender=None,
        )
        original_first = None
        original_last = None
        detected_gender = None
        if entity.entity_type == "PERSON":
            original_first, original_last, _ = ctx.compositional_engine.parse_full_name(
                entity_text_stripped
            )
            if ctx.compositional_engine.gender_detector is not None:
                detected_gender = ctx.compositional_engine.gender_detector.detect_gender_from_full_name(
                    entity_text_stripped, entity.entity_type
                )
        new_entity = Entity(
            entity_type=entity.entity_type,
            first_name=original_first,
            last_name=original_last,
            full_name=entity_text_stripped,
            pseudonym_first=assignment.pseudonym_first,
            pseudonym_last=assignment.pseudonym_last,
            pseudonym_full=assignment.pseudonym_full,
            first_seen_timestamp=datetime.now(UTC),
            gender=detected_gender,
            confidence_score=(
                entity.confidence if hasattr(entity, "confidence") else None
            ),
            theme=self.theme,
            is_ambiguous=assignment.is_ambiguous,
            ambiguity_reason=assignment.ambiguity_reason,
        )
        return assignment.pseudonym_full, new_entity

    @staticmethod
    def _pseudonyms_of_other_types(
        ctx: _ProcessingContext,
        entity_text_stripped: str,
        entity_type: str,
        entity_cache: dict[tuple[str, str], str],
    ) -> set[str]:
        """Pseudonyms a mapping key already has under other types (Story 10.7).

        Stored rows of the key under another type, and this run's pseudonyms
        of the key under another type.
        """
        taken = {
            stored.pseudonym_full
            for stored in ctx.mapping_repo.find_all_by_full_name(entity_text_stripped)
            if stored.entity_type != entity_type
        }
        taken.update(
            pseudonym
            for (key, key_type), pseudonym in entity_cache.items()
            if key == entity_text_stripped and key_type != entity_type
        )
        return taken

    def _uses_custom_part(self, new_entity: Entity) -> bool:
        """Whether a generated pseudonym, or one of its parts, is a value of a
        custom pseudonym that it must not take (Story 10.11, AC3, AC19): in
        another role or for another real word, whatever the spelling (Story
        10.16, Codex #6; ``takes_custom_value``)."""
        return takes_custom_value(new_entity, self._custom_taken)

    @staticmethod
    def _assign_untaken_pseudonym(
        ctx: _ProcessingContext,
        new_entity: Entity,
        taken: set[str],
        custom_taken: CustomReservations | None = None,
    ) -> tuple[str, Entity]:
        """Give a new row a pseudonym that its key has under no other type.

        Story 10.7, AC1: two rows of one key never share a pseudonym. A
        standalone PERSON component reuses a stored component without the
        library's used-pseudonym check (``_handle_standalone_component``), so
        it can equal the pseudonym of the same text under another type when
        the library's name and place lists overlap. The row then gets a fresh
        pseudonym from the library, whose collision check skips every
        pseudonym it has handed out, and keeps no component link (so the
        stored component mapping of the name is not changed).

        Story 10.11 (AC3): a draw whose pseudonym or part is in
        ``custom_taken`` (the values of custom pseudonyms, folded; AC19) is
        drawn again too: the draw keeps no component link, so it owns none of
        them (Story 10.16).

        Raises:
            RuntimeError: If the library gives no untaken pseudonym
        """
        custom_taken = custom_taken or {}
        for _attempt in range(len(taken) + len(custom_taken) + 1):
            assignment = ctx.pseudonym_manager.assign_pseudonym(
                entity_type=new_entity.entity_type, gender=None
            )
            parts = (
                assignment.pseudonym_full,
                assignment.pseudonym_first,
                assignment.pseudonym_last,
            )
            if assignment.pseudonym_full not in taken and not any(
                part and fold(part) in custom_taken for part in parts
            ):
                break
        else:
            raise RuntimeError("no pseudonym left that differs from the other types")
        logger.info(
            "pseudonym_reassigned_for_type",
            entity_type=new_entity.entity_type,
            other_types=len(taken),
        )
        untaken = Entity(
            entity_type=new_entity.entity_type,
            first_name=None,
            last_name=None,
            full_name=new_entity.full_name,
            pseudonym_first=None,
            pseudonym_last=None,
            pseudonym_full=assignment.pseudonym_full,
            first_seen_timestamp=new_entity.first_seen_timestamp,
            gender=new_entity.gender,
            confidence_score=new_entity.confidence_score,
            theme=new_entity.theme,
            is_ambiguous=new_entity.is_ambiguous,
            ambiguity_reason=new_entity.ambiguity_reason,
        )
        return assignment.pseudonym_full, untaken

    def _part_accepted(
        self,
        ctx: _ProcessingContext,
        part: str | None,
        real: str | None,
        kind: str,
    ) -> bool:
        """Whether a person's proposed part is what a draw would give now
        (Story 11.5, B.5 condition 7): the part the real word already has,
        when it has one (kept for consistency, not checked further, as in a
        draw); otherwise a part the library's one acceptance check accepts."""
        if not part:
            return False
        if real:
            existing = ctx.compositional_engine.find_standalone_components(real, kind)
            if existing is not None:
                return part == existing
        return ctx.pseudonym_manager.accepts_value(part, kind, real)

    def _proposal_row(
        self,
        ctx: _ProcessingContext,
        name: NameKey,
        proposal: PseudonymProposal,
        confidence: float | None,
        entity_cache: dict[tuple[str, str], str],
        new_entities: list[Entity],
    ) -> Entity | None:
        """The row a pseudonym shown for ``name`` is saved with when a draw
        at this moment would accept it, else None (Story 11.5, AC5; Fix
        design B.5's nine conditions)."""
        text, entity_type = name
        engine = ctx.compositional_engine
        manager = ctx.pseudonym_manager
        if name in entity_cache:
            return None
        if ctx.mapping_repo.find_by_full_name_and_type(text, entity_type):
            return None
        if proposal.entity_type != entity_type or proposal.theme != self.theme:
            return None
        if manager.is_used(proposal.pseudonym_full):
            return None
        if proposal.pseudonym_full in self._pseudonyms_of_other_types(
            ctx, text, entity_type, entity_cache
        ):
            return None
        original_first = original_last = None
        gender = None
        if entity_type == "PERSON":
            if self._check_component_match(ctx, text, new_entities) is not None:
                # A lone name matched within the run: the loop resolves it
                return None
            original_first, original_last, is_ambiguous = engine.parse_full_name(text)
            if self.theme != "neutral_id":
                if is_ambiguous and original_first and not original_last:
                    accepted = self._lone_name_accepted(ctx, original_first, proposal)
                else:
                    accepted = self._part_accepted(
                        ctx, proposal.pseudonym_first, original_first, "first_name"
                    ) and self._part_accepted(
                        ctx, proposal.pseudonym_last, original_last, "last_name"
                    )
                if not accepted:
                    return None
            if engine.gender_detector is not None:
                gender = engine.gender_detector.detect_gender_from_full_name(
                    text, entity_type
                )
        elif self.theme != "neutral_id" and not manager.accepts_value(
            proposal.pseudonym_full, entity_type
        ):
            return None
        row = Entity(
            entity_type=entity_type,
            first_name=original_first,
            last_name=original_last,
            full_name=text,
            pseudonym_first=proposal.pseudonym_first,
            pseudonym_last=proposal.pseudonym_last,
            pseudonym_full=proposal.pseudonym_full,
            first_seen_timestamp=datetime.now(UTC),
            gender=gender,
            confidence_score=confidence,
            theme=self.theme,
            is_ambiguous=proposal.is_ambiguous,
            ambiguity_reason=proposal.ambiguity_reason,
        )
        if takes_custom_value(row, self._custom_taken):
            return None
        return row

    @staticmethod
    def _lone_name_accepted(
        ctx: _ProcessingContext, word: str, proposal: PseudonymProposal
    ) -> bool:
        """A one-word person name's proposal, as ``_handle_standalone_component``
        would draw it now: an existing first-name part, else an existing
        last-name part, must equal it; with none, its first part must be
        accepted for the word as a real first name and its last part with no
        real last name (Story 11.5)."""
        engine = ctx.compositional_engine
        for kind in ("first_name", "last_name"):
            existing = engine.find_standalone_components(word, kind)
            if existing:
                return proposal.pseudonym_full == existing
        manager = ctx.pseudonym_manager
        return bool(
            proposal.pseudonym_first
            and proposal.pseudonym_last
            and manager.accepts_value(proposal.pseudonym_first, "first_name", word)
            and manager.accepts_value(proposal.pseudonym_last, "last_name", None)
        )

    def _register_proposals(
        self,
        ctx: _ProcessingContext,
        ordered: Sequence[_OrderedProposal],
        entity_cache: dict[tuple[str, str], str],
        new_entities: list[Entity],
    ) -> set[NameKey]:
        """Keep each pseudonym shown that is still free (Story 11.5, AC5),
        in the order given (the names' first places): its row joins the
        run's new rows and the library marks it and its parts as used, so a
        later name is checked against it. Draws nothing.

        Returns:
            The names kept (their first occurrence counts as new)
        """
        kept: set[NameKey] = set()
        for name, proposal, confidence in ordered:
            row = self._proposal_row(
                ctx, name, proposal, confidence, entity_cache, new_entities
            )
            if row is None:
                continue
            ctx.pseudonym_manager.load_existing_mappings([row])
            entity_cache[name] = proposal.pseudonym_full
            new_entities.append(row)
            kept.add(name)
        return kept

    @staticmethod
    def _sent_in_order(
        ctx: _ProcessingContext, validated_entities: list[DetectedEntity]
    ) -> list[tuple[NameKey, float | None]]:
        """Each name sent once, in the order of its first place in the list
        (the order the per-occurrence loop resolves names in)."""
        seen: dict[NameKey, float | None] = {}
        for entity in validated_entities:
            name = (
                DocumentProcessor._normalize_entity_text(ctx, entity),
                entity.entity_type,
            )
            seen.setdefault(name, getattr(entity, "confidence", None))
        return list(seen.items())

    @staticmethod
    def _changed_pseudonyms(
        names: Sequence[NameKey],
        proposals: Mapping[NameKey, Sequence[PseudonymProposal]],
        entity_cache: Mapping[tuple[str, str], str],
        customs: Mapping[NameKey, str],
    ) -> list[ChangedPseudonym]:
        """Every pseudonym shown for a name sent that differs from the one
        written for it, in the order of the names' first places (AC6)."""
        changed: list[ChangedPseudonym] = []
        for name in names:
            if name in customs or name not in entity_cache:
                continue
            written = entity_cache[name]
            shown: list[str] = []
            for proposal in proposals.get(name, ()):
                if proposal.pseudonym_full not in shown:
                    shown.append(proposal.pseudonym_full)
            changed.extend(
                ChangedPseudonym(
                    name=name[0], entity_type=name[1], shown=value, written=written
                )
                for value in shown
                if value != written
            )
        return changed

    def _resolve_pseudonyms(
        self,
        ctx: _ProcessingContext,
        validated_entities: list[DetectedEntity],
        custom_pseudonyms: dict[NameKey, str] | None = None,
        document_text: str = "",
        proposals: Mapping[NameKey, Sequence[PseudonymProposal]] | None = None,
    ) -> _ResolveResult:
        """Resolve pseudonyms for all validated entities.

        Story 10.11: the custom pseudonyms the user set, keyed by (mapping
        key, type), are checked again and registered before any occurrence
        is resolved (``_register_custom_pseudonyms``); ``document_text`` is
        the text their real-name check reads.

        Story 11.5: ``proposals`` holds, for each name sent, the pseudonyms
        the review showed for it, in the order of its rows or groups. The
        first is kept when a draw at this moment would accept it
        (``_register_proposals``, after the custom pseudonyms); any other
        name is resolved as before. Each pseudonym shown that differs from
        the one written is listed in the result's ``pseudonyms_changed``.
        """
        logger.info(
            "starting_entity_processing",
            validated_count=len(validated_entities),
        )
        replacements: list[tuple[int, int, str]] = []
        new_entities: list[Entity] = []
        # Keyed on (mapping key, entity type): one row and one pseudonym per
        # pair (Story 10.7, AC1, AC2)
        entity_cache: dict[tuple[str, str], str] = {}
        entities_new = 0
        entities_reused = 0
        type_counts: dict[str, int] = {}
        # Story 10.16 (Codex #8): the names sent count in the custom
        # pseudonyms' real-name check. Story 11.6: also the drawn pseudonyms'
        # real-name check, so always
        sent_names = [
            self._normalize_entity_text(ctx, entity) for entity in validated_entities
        ]
        ctx.pseudonym_manager.set_real_name_check(
            real_name_check(document_text, sent_names)
        )
        # Story 10.11: custom names whose first occurrence is still to come
        custom_unseen = self._register_custom_pseudonyms(
            ctx,
            custom_pseudonyms or {},
            document_text,
            entity_cache,
            new_entities,
            sent_names=sent_names,
        )
        # Story 11.5: the pseudonyms the review showed, kept when still free
        sent_in_order = self._sent_in_order(ctx, validated_entities)
        kept: set[NameKey] = set()
        if proposals:
            kept = self._register_proposals(
                ctx,
                [
                    (name, proposals[name][0], confidence)
                    for name, confidence in sent_in_order
                    if proposals.get(name)
                ],
                entity_cache,
                new_entities,
            )
            custom_unseen |= kept

        for entity in validated_entities:
            logger.debug(
                "processing_entity",
                entity_text=entity.text,
                entity_type=entity.entity_type,
            )
            entity_text_stripped = self._normalize_entity_text(ctx, entity)
            type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1
            cache_key = (entity_text_stripped, entity.entity_type)

            if cache_key in entity_cache:
                pseudonym = entity_cache[cache_key]
                if cache_key in custom_unseen:
                    # A custom pseudonym's first occurrence counts as new
                    custom_unseen.discard(cache_key)
                    entities_new += 1
                else:
                    entities_reused += 1
            else:
                existing_entity = ctx.mapping_repo.find_by_full_name_and_type(
                    entity_text_stripped, entity.entity_type
                )
                if existing_entity:
                    pseudonym = existing_entity.pseudonym_full
                    entity_cache[cache_key] = pseudonym
                    entities_reused += 1
                else:
                    # Pseudonyms this text already has under other types: a new
                    # one must differ from them (Story 10.7, AC1)
                    taken = self._pseudonyms_of_other_types(
                        ctx, entity_text_stripped, entity.entity_type, entity_cache
                    )
                    component_match = (
                        self._check_component_match(
                            ctx, entity_text_stripped, new_entities
                        )
                        if entity.entity_type == "PERSON"
                        else None
                    )
                    if component_match and component_match not in taken:
                        pseudonym = component_match
                        entity_cache[cache_key] = pseudonym
                        entities_reused += 1
                    else:
                        pseudonym, new_entity = self._assign_new_pseudonym(
                            ctx, entity, entity_text_stripped
                        )
                        if pseudonym in taken or self._uses_custom_part(new_entity):
                            pseudonym, new_entity = self._assign_untaken_pseudonym(
                                ctx, new_entity, taken, self._custom_taken
                            )
                        entity_cache[cache_key] = pseudonym
                        new_entities.append(new_entity)
                        entities_new += 1

            prefix = self._compute_replacement_prefix(ctx, entity)
            replacements.append((entity.start_pos, entity.end_pos, prefix + pseudonym))

        if new_entities:
            try:
                ctx.mapping_repo.save_batch(new_entities)
                logger.info("entities_saved_batch", count=len(new_entities))
            except Exception as e:
                logger.error(
                    "batch_save_failed",
                    error=self._sanitize_error_message(e),
                    entity_count=len(new_entities),
                )
                raise

        changed = (
            self._changed_pseudonyms(
                [name for name, _ in sent_in_order],
                proposals,
                entity_cache,
                custom_pseudonyms or {},
            )
            if proposals
            else []
        )
        if proposals:
            logger.info(
                "review_pseudonyms_resolved",
                kept=len(kept),
                changed=len(changed),
            )
        return _ResolveResult(
            replacements=replacements,
            entities_new=entities_new,
            entities_reused=entities_reused,
            entity_type_counts=type_counts,
            saved_entities=list(new_entities),
            pseudonyms_changed=changed,
        )

    @staticmethod
    def _apply_replacements(
        document_text: str,
        replacements: list[tuple[int, int, str]],
    ) -> str:
        """Deduplicate overlapping replacements and apply to document text.

        Overlapping spans are resolved by keeping the first (longest) span
        in sorted order. Replacements are applied from end to start to
        preserve character positions.

        Args:
            document_text: Original document text
            replacements: List of (start_pos, end_pos, pseudonym) tuples

        Returns:
            Document text with all replacements applied
        """
        # Deduplicate overlapping replacements
        deduplicated: list[tuple[int, int, str]] = []
        sorted_repls = sorted(replacements, key=lambda x: (x[0], -x[1]))

        for start, end, pseudo in sorted_repls:
            overlaps = any(not (end <= ks or start >= ke) for ks, ke, _ in deduplicated)
            if not overlaps:
                deduplicated.append((start, end, pseudo))

        logger.debug(
            "replacements_deduplicated",
            original_count=len(replacements),
            deduplicated_count=len(deduplicated),
        )

        # Apply from end to start to preserve positions
        result = document_text
        for start_pos, end_pos, pseudonym in sorted(
            deduplicated, key=lambda x: x[0], reverse=True
        ):
            result = result[:start_pos] + pseudonym + result[end_pos:]

        return result

    @staticmethod
    def _set_real_name_check(
        ctx: _ProcessingContext,
        document_text: str,
        entities: Iterable[DetectedEntity],
    ) -> None:
        """Story 11.5 (AC8): Story 11.6's real-name check, set before the
        review's draws from the document and the names detected, so the
        list never shows a value a draw at the end would refuse for them."""
        ctx.pseudonym_manager.set_real_name_check(
            real_name_check(
                document_text,
                [DocumentProcessor._normalize_entity_text(ctx, e) for e in entities],
            )
        )

    def _rebase_preview_context(
        self,
        ctx: _ProcessingContext,
        stored: list[Entity],
        customs: Mapping[NameKey, str],
        ordered: Sequence[_OrderedProposal],
    ) -> tuple[dict[tuple[str, str], str], list[Entity]]:
        """Rebuild a review's context as the end would see it now (Story
        11.5, B.8 and C): the stored rows, the custom pseudonyms (registered
        without their re-check: each was checked when it was set; a refusal
        is the end's to raise) and the pseudonyms shown that are still free.
        Draws nothing, saves nothing.

        Returns:
            The run's cache and new rows of the custom pseudonyms and the
            pseudonyms kept
        """
        ctx.pseudonym_manager.reset_preview_state()
        ctx.pseudonym_manager.load_existing_mappings(stored)
        self._custom_taken = untracked_custom_values(stored)
        entity_cache: dict[tuple[str, str], str] = {}
        new_entities: list[Entity] = []
        self._register_custom_rows(ctx, customs, stored, entity_cache, new_entities)
        self._register_proposals(ctx, ordered, entity_cache, new_entities)
        return entity_cache, new_entities

    def _build_custom_set_hook(
        self,
        ctx: _ProcessingContext,
        recorded: Mapping[NameKey, PseudonymProposal],
    ) -> Callable[[Mapping[NameKey, str]], None]:
        """The command line's hook after [C] (Story 11.5, AC21): the review's
        context is rebased on the stored rows, the custom pseudonyms set and
        the pseudonyms shown still free (in the order drawn), so every group
        displayed later is drawn as the end would draw it. No lock, no save,
        no text."""

        def on_custom_set(customs: Mapping[NameKey, str]) -> None:
            stored = ctx.mapping_repo.find_all()
            self._rebase_preview_context(
                ctx,
                stored,
                customs,
                [
                    (name, proposal, None)
                    for name, proposal in recorded.items()
                    if name not in customs
                ],
            )

        return on_custom_set

    @staticmethod
    def _review_proposals(
        shown_names: Mapping[NameKey, list[NameKey]],
        recorded: Mapping[NameKey, PseudonymProposal],
        custom_pseudonyms: Mapping[NameKey, str],
    ) -> dict[NameKey, list[PseudonymProposal]]:
        """The pseudonyms the command line's review showed for each name
        sent with no custom pseudonym, in the order of its groups (Story
        11.5, B.6)."""
        proposals: dict[NameKey, list[PseudonymProposal]] = {}
        for sent, drawn_fors in shown_names.items():
            if sent in custom_pseudonyms:
                continue
            shown: list[PseudonymProposal] = []
            for drawn_for in drawn_fors:
                proposal = recorded.get(drawn_for)
                if proposal is not None and proposal not in shown:
                    shown.append(proposal)
            if shown:
                proposals[sent] = shown
        return proposals

    def refresh_review_proposals(
        self,
        document_text: str,
        names: Sequence[NameKey],
        customs: Mapping[NameKey, str],
        proposals: Mapping[NameKey, PseudonymProposal],
    ) -> dict[NameKey, PseudonymProposal | str]:
        """What the end would write now for the review's names, without
        writing anything (Story 11.5, AC19; the desktop list's update after a
        type change or a custom pseudonym).

        Args:
            document_text: The document's text (the real-name check reads it)
            names: Every name of the review not rejected, each once, in the
                order of its first place in the document
            customs: The custom pseudonym of each name that has one
            proposals: The pseudonym each name currently shows (its
                proposal)

        Returns:
            Only the names whose value changes: a name stored now gives its
            stored pseudonym, any other a new proposal, drawn as a draw at
            the end would draw it
        """
        refreshed: dict[NameKey, PseudonymProposal | str] = {}
        with open_database(self.db_path, self.passphrase) as db_session:
            ctx = self._init_processing_context(db_session)
            ctx.pseudonym_manager.set_real_name_check(
                real_name_check(document_text, [name[0] for name in names])
            )
            stored = ctx.mapping_repo.find_all()
            entity_cache, _ = self._rebase_preview_context(
                ctx,
                stored,
                customs,
                [
                    (name, proposals[name], None)
                    for name in names
                    if name in proposals and name not in customs
                ],
            )
            recorded: dict[NameKey, PseudonymProposal] = {}
            assigner = self._build_pseudonym_assigner(ctx, proposals=recorded)
            for name in names:
                if name in customs or name in entity_cache:
                    continue
                current = proposals.get(name)
                stored_row = ctx.mapping_repo.find_by_full_name_and_type(*name)
                value: PseudonymProposal | str
                if stored_row is not None:
                    value = stored_row.pseudonym_full
                    if current is None or current.pseudonym_full != value:
                        refreshed[name] = value
                    continue
                shown = assigner(
                    DetectedEntity(
                        text=name[0],
                        entity_type=name[1],
                        start_pos=0,
                        end_pos=len(name[0]),
                    )
                )
                value = recorded.get(name, shown)
                if value != current:
                    refreshed[name] = value
        logger.info("review_pseudonyms_refreshed", redrawn=len(refreshed))
        return refreshed

    def _reset_pseudonym_state(self, ctx: _ProcessingContext) -> list[Entity]:
        """Reset pseudonym manager after validation preview.

        The validation preview generates pseudonyms that are never saved.
        This clears that state and reloads genuine DB mappings to prevent
        collision false positives during actual processing.

        Args:
            ctx: Processing context with pseudonym_manager and mapping_repo

        Returns:
            The saved rows it read (Story 11.7: the notice's count reads them
            once the lock is released, with no second read)
        """
        ctx.pseudonym_manager.reset_preview_state()
        existing_entities = ctx.mapping_repo.find_all()
        ctx.pseudonym_manager.load_existing_mappings(existing_entities)
        # Story 10.11 (AC3, AC19): the stored custom values not to generate
        self._custom_taken = untracked_custom_values(existing_entities)
        logger.info(
            "pseudonym_manager_reset_after_validation",
            existing_mappings_reloaded=len(existing_entities),
        )
        return existing_entities

    @staticmethod
    def _own_word_count(
        existing_rows: Iterable[Entity] | None, resolve_result: _ResolveResult
    ) -> int:
        """Story 11.7: the saved rows whose pseudonym holds a word of their
        own name, the rows this document saved included (the notice when a
        document is written). Run after the lock is released, on the rows
        already read. The notice never stops a written document: a failure
        counts 0."""
        try:
            rows = list(existing_rows or []) + list(resolve_result.saved_entities)
            return count_own_word_rows(rows)
        except Exception as e:  # noqa: BLE001 - the notice only
            logger.warning("saved_own_words_check_failed", error_type=type(e).__name__)
            return 0

    def _init_processing_context(
        self, db_session: DatabaseSession
    ) -> _ProcessingContext:
        """Initialize repositories and engines for document processing.

        Creates the mapping/audit repositories and the pseudonym
        manager/engine, loading existing mappings to prevent collisions.

        Args:
            db_session: Open database session

        Returns:
            _ProcessingContext with all initialized dependencies
        """
        mapping_repo: MappingRepository = SQLiteMappingRepository(db_session)
        audit_repo = AuditRepository(db_session.session)

        pseudonym_manager = LibraryBasedPseudonymManager()
        pseudonym_manager.load_library(self.theme)

        existing_entities = mapping_repo.find_all()
        pseudonym_manager.load_existing_mappings(existing_entities)

        gender_detector = GenderDetector()
        gender_detector.load()

        compositional_engine = CompositionalPseudonymEngine(
            pseudonym_manager=pseudonym_manager,
            mapping_repository=mapping_repo,
            gender_detector=gender_detector,
        )

        return _ProcessingContext(
            mapping_repo=mapping_repo,
            audit_repo=audit_repo,
            pseudonym_manager=pseudonym_manager,
            compositional_engine=compositional_engine,
        )

    def _log_success_operation(
        self,
        ctx: _ProcessingContext,
        input_path: str,
        validated_entities: list[DetectedEntity],
        processing_time: float,
    ) -> None:
        """Log successful processing operation to audit trail."""
        operation = Operation(
            operation_type="PROCESS",
            files_processed=[input_path],
            model_name=self.model_name,
            model_version=self._get_model_version(),
            theme_selected=self.theme,
            entity_count=len(validated_entities),
            processing_time_seconds=processing_time,
            success=True,
            error_message=None,
        )
        ctx.audit_repo.log_operation(operation)

    @staticmethod
    def _sanitize_error_message(error: Exception) -> str:
        """Sanitize exception message to strip potential PII before logging.

        Removes quoted strings and entity-like patterns (capitalized word
        sequences) from the error text while preserving the exception type
        name and generic error structure for diagnostics.

        Args:
            error: The caught exception

        Returns:
            Sanitized string safe for logging and audit storage
        """
        error_type = type(error).__name__
        message = str(error)

        # Strip single-quoted strings (e.g., 'Jean Dupont')
        message = re.sub(r"'[^']*'", "'[REDACTED]'", message)
        # Strip double-quoted strings (e.g., "Jean Dupont")
        message = re.sub(r'"[^"]*"', '"[REDACTED]"', message)
        # Strip sequences of 2+ capitalized words that look like names
        # (e.g., "Jean Pierre Dupont" but not "Cannot parse"). Story 10.20
        # (AC4): a combining mark is part of its word, so a name holding a
        # mark with no composed letter is redacted whole.
        marks = mark_class()
        message = re.sub(
            rf"\b[A-ZÀ-Ÿ][a-zà-ÿ{marks}]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ{marks}]+){{1,}}"
            rf"(?![\w{marks}])",
            "[REDACTED]",
            message,
        )

        return f"{error_type}: {message}"

    def _handle_processing_error(
        self,
        error: Exception,
        input_path: str,
        output_path: str,
        start_time: float,
    ) -> ProcessingResult:
        """Format error, log to audit trail, and return failure result."""
        processing_time = time.time() - start_time
        error_message = self._sanitize_error_message(error)
        logger.error("processing_error", error=error_message)
        self._log_failed_operation(
            input_path, error_message, processing_time, detected_entities=[]
        )
        return ProcessingResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            entities_detected=0,
            entities_new=0,
            entities_reused=0,
            processing_time_seconds=processing_time,
            error_message=error_message,
        )

    def detect_entities(
        self,
        input_path: str,
        entity_type_filter: set[str] | None = None,
    ) -> tuple[str, list[DetectedEntity]]:
        """Phase 1: Read file and run NLP detection only.

        Returns document text and detected entities without performing
        pseudonymization. Used by GUI DetectionWorker to split the pipeline.

        Args:
            input_path: Path to document to process
            entity_type_filter: Optional set of entity types to keep

        Returns:
            Tuple of (document_text, detected_entities)

        Raises:
            FileProcessingError: If file cannot be read
            OSError: If NLP model not available
        """
        document_text = read_file(input_path)
        detected_entities = self._detect_and_filter_entities(
            document_text, entity_type_filter
        )
        return document_text, detected_entities

    def build_pseudonym_previews(
        self,
        detected_entities: list[DetectedEntity],
        document_text: str = "",
        proposals: dict[CandidateKey, PseudonymProposal] | None = None,
    ) -> dict[CandidateKey, str]:
        """Generate pseudonym previews for detected entities.

        Opens a database session to look up existing mappings and generate
        new pseudonyms via the compositional engine.

        Preserves title prefixes in pseudonyms to match entity.text
        (e.g., "Dr. Jean Dupont" → "Dr. Luke Skywalker").

        Story 11.5: Story 11.6's real-name check is set first, from
        ``document_text`` and the names detected (AC8), so no preview is a
        value a draw at the end would refuse for them.

        Args:
            detected_entities: Entities from detect_entities()
            document_text: The document's text (empty: the names alone)
            proposals: When given, filled with each new name's pseudonym, by
                the entity's candidate key (Story 11.5: kept at the end if
                still free)

        Returns:
            Dict mapping each candidate's key (text, start_pos, entity_type),
            from ``candidate_key``, to its pseudonym preview string
        """
        import re

        from gdpr_pseudonymizer.utils.french_patterns import FRENCH_TITLE_PATTERN

        with open_database(self.db_path, self.passphrase) as db_session:
            ctx = self._init_processing_context(db_session)
            self._set_real_name_check(ctx, document_text, detected_entities)
            recorded: dict[NameKey, PseudonymProposal] = {}
            assigner = self._build_pseudonym_assigner(ctx, proposals=recorded)
            previews: dict[CandidateKey, str] = {}
            for entity in detected_entities:
                key = candidate_key(entity)
                base_pseudonym = assigner(entity)
                if proposals is not None:
                    proposal = recorded.get(
                        (self._normalize_entity_text(ctx, entity), entity.entity_type)
                    )
                    if proposal is not None:
                        proposals[key] = proposal

                # Preserve title prefix for PERSON entities (same logic as CLI)
                if entity.entity_type == "PERSON":
                    title_match = re.match(
                        FRENCH_TITLE_PATTERN, entity.text, re.IGNORECASE
                    )
                    if title_match:
                        title_prefix = title_match.group(0).rstrip()
                        previews[key] = f"{title_prefix} {base_pseudonym}"
                    else:
                        previews[key] = base_pseudonym
                else:
                    previews[key] = base_pseudonym

            return previews

    def finalize_document(
        self,
        document_text: str,
        validated_entities: list[DetectedEntity],
        output_path: str,
        custom_pseudonyms: dict[NameKey, str] | None = None,
        proposals: Mapping[NameKey, Sequence[PseudonymProposal]] | None = None,
    ) -> ProcessingResult:
        """Phase 2: Resolve pseudonyms, apply replacements, write output.

        Takes validated entities (after user review) and produces the
        pseudonymized document. Used by GUI FinalizationWorker.

        Args:
            document_text: Original document text
            validated_entities: Entities approved by user (rejected excluded)
            output_path: Path to write pseudonymized output
            custom_pseudonyms: The custom pseudonyms set in the review, keyed
                by (mapping key, type) of the name sent (Story 10.11)
            proposals: The pseudonyms the review showed for each name sent,
                in the order of its rows (Story 11.5)

        Returns:
            ProcessingResult with success/failure details
        """
        start_time = time.time()
        try:
            with open_database(self.db_path, self.passphrase) as db_session:
                ctx = self._init_processing_context(db_session)
                # Story 10.22: the pseudonyms are chosen and saved under the
                # database's write lock, one document at a time
                with pseudonym_lock(db_session):
                    existing_rows = self._reset_pseudonym_state(ctx)
                    resolve_result = self._resolve_pseudonyms(
                        ctx,
                        validated_entities,
                        custom_pseudonyms=custom_pseudonyms,
                        document_text=document_text,
                        proposals=proposals,
                    )
                pseudonymized_text = self._apply_replacements(
                    document_text, resolve_result.replacements
                )
                write_file(output_path, pseudonymized_text)
                processing_time = time.time() - start_time
                return ProcessingResult(
                    success=True,
                    input_file="",
                    output_file=output_path,
                    entities_detected=len(validated_entities),
                    entities_new=resolve_result.entities_new,
                    entities_reused=resolve_result.entities_reused,
                    processing_time_seconds=processing_time,
                    entity_type_counts=resolve_result.entity_type_counts,
                    own_word_rows=self._own_word_count(existing_rows, resolve_result),
                    pseudonyms_changed=resolve_result.pseudonyms_changed,
                )
        except Exception as e:
            return self._handle_processing_error(e, "", output_path, start_time)

    def process_document(
        self,
        input_path: str,
        output_path: str,
        skip_validation: bool = False,
        entity_type_filter: set[str] | None = None,
    ) -> ProcessingResult:
        """Process single document with complete pseudonymization workflow."""
        # Route tabular files through the cell-aware pipeline
        ext = get_file_extension(input_path)
        if ext in (".xlsx", ".csv"):
            return self._process_document_tabular(
                input_path, output_path, skip_validation, entity_type_filter
            )

        start_time = time.time()
        try:
            document_text = read_file(input_path)
            detected_entities = self._detect_and_filter_entities(
                document_text, entity_type_filter
            )
            with open_database(self.db_path, self.passphrase) as db_session:
                ctx = self._init_processing_context(db_session)
                # Story 11.5: what the review shows is what a draw at the end
                # would accept (AC8), and is kept at the end if still free
                if not skip_validation:
                    self._set_real_name_check(ctx, document_text, detected_entities)
                recorded: dict[NameKey, PseudonymProposal] = {}
                shown_names: dict[NameKey, list[NameKey]] = {}
                pseudonym_assigner = self._build_pseudonym_assigner(
                    ctx, proposals=recorded
                )
                custom_pseudonyms: dict[NameKey, str] = {}
                validated_entities = self._run_validation(
                    ctx=ctx,
                    detected_entities=detected_entities,
                    document_text=document_text,
                    input_path=input_path,
                    skip_validation=skip_validation,
                    pseudonym_assigner=pseudonym_assigner,
                    custom_pseudonyms=custom_pseudonyms,
                    types_selected=entity_type_filter is not None,
                    shown_names=shown_names,
                    on_custom_set=self._build_custom_set_hook(ctx, recorded),
                )
                proposals = self._review_proposals(
                    shown_names, recorded, custom_pseudonyms
                )
                # Story 10.22: the pseudonyms are chosen and saved under the
                # database's write lock, one document at a time
                with pseudonym_lock(db_session):
                    existing_rows = self._reset_pseudonym_state(ctx)
                    resolve_result = self._resolve_pseudonyms(
                        ctx,
                        validated_entities,
                        custom_pseudonyms=custom_pseudonyms,
                        document_text=document_text,
                        proposals=proposals,
                    )
                pseudonymized_text = self._apply_replacements(
                    document_text, resolve_result.replacements
                )
                write_file(output_path, pseudonymized_text)
                processing_time = time.time() - start_time
                self._log_success_operation(
                    ctx, input_path, validated_entities, processing_time
                )
                return ProcessingResult(
                    success=True,
                    input_file=input_path,
                    output_file=output_path,
                    entities_detected=len(validated_entities),
                    entities_new=resolve_result.entities_new,
                    entities_reused=resolve_result.entities_reused,
                    processing_time_seconds=processing_time,
                    entity_type_counts=resolve_result.entity_type_counts,
                    own_word_rows=self._own_word_count(existing_rows, resolve_result),
                    pseudonyms_changed=resolve_result.pseudonyms_changed,
                )
        except Exception as e:
            return self._handle_processing_error(e, input_path, output_path, start_time)

    def _process_document_tabular(
        self,
        input_path: str,
        output_path: str,
        skip_validation: bool = False,
        entity_type_filter: set[str] | None = None,
    ) -> ProcessingResult:
        """Process tabular document (Excel/CSV) through cell-aware pipeline."""
        start_time = time.time()
        try:
            tabular_doc, detected_entities = self.detect_entities_tabular(
                input_path, entity_type_filter
            )

            # For tabular files, build a flat text representation for validation display
            document_text = "\n".join(cell.value for cell in tabular_doc.cells)

            with open_database(self.db_path, self.passphrase) as db_session:
                ctx = self._init_processing_context(db_session)
                # Story 11.5: what the review shows is what a draw at the end
                # would accept (AC8), and is kept at the end if still free
                if not skip_validation:
                    self._set_real_name_check(ctx, document_text, detected_entities)
                recorded: dict[NameKey, PseudonymProposal] = {}
                shown_names: dict[NameKey, list[NameKey]] = {}
                pseudonym_assigner = self._build_pseudonym_assigner(
                    ctx, proposals=recorded
                )
                custom_pseudonyms: dict[NameKey, str] = {}
                validated_entities = self._run_validation(
                    ctx=ctx,
                    detected_entities=detected_entities,
                    document_text=document_text,
                    input_path=input_path,
                    skip_validation=skip_validation,
                    pseudonym_assigner=pseudonym_assigner,
                    custom_pseudonyms=custom_pseudonyms,
                    cells={cell.cell_ref: cell.value for cell in tabular_doc.cells},
                    types_selected=entity_type_filter is not None,
                    shown_names=shown_names,
                    on_custom_set=self._build_custom_set_hook(ctx, recorded),
                )
                proposals = self._review_proposals(
                    shown_names, recorded, custom_pseudonyms
                )
                # Story 10.15 (AC4): every name has its cell, before any
                # pseudonym is stored
                self._check_cells(tabular_doc, validated_entities)
                # Story 10.22: the pseudonyms are chosen and saved under the
                # database's write lock, one document at a time
                with pseudonym_lock(db_session):
                    existing_rows = self._reset_pseudonym_state(ctx)
                    resolve_result = self._resolve_pseudonyms(
                        ctx,
                        validated_entities,
                        custom_pseudonyms=custom_pseudonyms,
                        document_text=document_text,
                        proposals=proposals,
                    )

                self._apply_tabular_replacements(
                    tabular_doc,
                    validated_entities,
                    resolve_result.replacements,
                    output_path,
                )

                processing_time = time.time() - start_time
                self._log_success_operation(
                    ctx, input_path, validated_entities, processing_time
                )
                return ProcessingResult(
                    success=True,
                    input_file=input_path,
                    output_file=output_path,
                    entities_detected=len(validated_entities),
                    entities_new=resolve_result.entities_new,
                    entities_reused=resolve_result.entities_reused,
                    processing_time_seconds=processing_time,
                    entity_type_counts=resolve_result.entity_type_counts,
                    own_word_rows=self._own_word_count(existing_rows, resolve_result),
                    pseudonyms_changed=resolve_result.pseudonyms_changed,
                )
        except Exception as e:
            return self._handle_processing_error(e, input_path, output_path, start_time)

    def detect_entities_tabular(
        self,
        input_path: str,
        entity_type_filter: set[str] | None = None,
    ) -> tuple[TabularDocument, list[DetectedEntity]]:
        """Detect entities in a tabular file (Excel/CSV), preserving cell references.

        Each cell is processed as an independent text unit through the NER pipeline.
        Resulting entities have `context_label` set to the cell reference
        (e.g., "Sheet1!B3") and `start_pos`/`end_pos` relative to cell text.

        Args:
            input_path: Path to .xlsx or .csv file
            entity_type_filter: Optional set of entity types to keep

        Returns:
            Tuple of (TabularDocument, list of detected entities with cell refs)

        Raises:
            FileProcessingError: If file cannot be read
        """
        ext = get_file_extension(input_path)
        if ext == ".xlsx":
            tabular_doc = read_excel_structured(input_path)
        else:
            tabular_doc = read_csv_structured(input_path)

        all_entities: list[DetectedEntity] = []
        detector = self._get_detector()

        for cell in tabular_doc.cells:
            if not cell.value.strip():
                continue
            cell_entities = detector.detect_entities(cell.value)
            for entity in cell_entities:
                entity.context_label = cell.cell_ref
                all_entities.append(entity)

        if entity_type_filter:
            all_entities = [
                e for e in all_entities if e.entity_type in entity_type_filter
            ]

        logger.info(
            "tabular_entities_detected",
            count=len(all_entities),
            cells_processed=len(tabular_doc.cells),
            source_format=tabular_doc.source_format,
        )

        return tabular_doc, all_entities

    def finalize_document_tabular(
        self,
        tabular_doc: TabularDocument,
        validated_entities: list[DetectedEntity],
        output_path: str,
        input_path: str = "",
    ) -> ProcessingResult:
        """Apply pseudonym replacements to tabular document and write output.

        Matches entities to cells via `context_label`, applies text replacements
        within each cell, then writes the result in the appropriate format.

        Args:
            tabular_doc: Original tabular document with cell data
            validated_entities: Entities approved by user
            output_path: Path to write pseudonymized output
            input_path: Original input file path (for result metadata)

        Returns:
            ProcessingResult with success/failure details
        """
        start_time = time.time()
        try:
            with open_database(self.db_path, self.passphrase) as db_session:
                ctx = self._init_processing_context(db_session)
                # Story 10.15 (AC4): every name has its cell, before any
                # pseudonym is stored
                self._check_cells(tabular_doc, validated_entities)
                # Story 10.22: the pseudonyms are chosen and saved under the
                # database's write lock, one document at a time
                with pseudonym_lock(db_session):
                    existing_rows = self._reset_pseudonym_state(ctx)
                    resolve_result = self._resolve_pseudonyms(ctx, validated_entities)

                self._apply_tabular_replacements(
                    tabular_doc,
                    validated_entities,
                    resolve_result.replacements,
                    output_path,
                )

                processing_time = time.time() - start_time
                return ProcessingResult(
                    success=True,
                    input_file=input_path,
                    output_file=output_path,
                    entities_detected=len(validated_entities),
                    entities_new=resolve_result.entities_new,
                    entities_reused=resolve_result.entities_reused,
                    processing_time_seconds=processing_time,
                    entity_type_counts=resolve_result.entity_type_counts,
                    own_word_rows=self._own_word_count(existing_rows, resolve_result),
                    pseudonyms_changed=resolve_result.pseudonyms_changed,
                )
        except Exception as e:
            return self._handle_processing_error(e, input_path, output_path, start_time)

    def _apply_tabular_replacements(
        self,
        tabular_doc: TabularDocument,
        validated_entities: list[DetectedEntity],
        replacements: list[tuple[int, int, str]],
        output_path: str,
    ) -> None:
        """Apply pseudonym replacements to tabular cells and write output.

        Groups replacements by cell_ref, applies them per cell,
        then writes the result in the format matching the output extension.

        Args:
            tabular_doc: Document with cell data (modified in place)
            validated_entities: Entities with context_label for cell matching
            replacements: List of (start, end, pseudonym) tuples
            output_path: Output file path (extension determines format)
        """
        from gdpr_pseudonymizer.utils.tabular_writer import (
            write_csv,
            write_excel,
            write_tabular_as_text,
        )

        # Group replacements by cell_ref
        cell_replacements: dict[str, list[tuple[int, int, str]]] = {}
        for entity, (start, end, pseudo) in zip(validated_entities, replacements):
            ref = entity.context_label or ""
            if ref not in cell_replacements:
                cell_replacements[ref] = []
            cell_replacements[ref].append((start, end, pseudo))

        # Apply replacements within each cell
        for cell in tabular_doc.cells:
            if cell.cell_ref in cell_replacements:
                cell.value = self._apply_replacements(
                    cell.value, cell_replacements[cell.cell_ref]
                )

        # Write output based on extension
        out_ext = get_file_extension(output_path)
        if out_ext == ".xlsx":
            write_excel(tabular_doc, output_path)
        elif out_ext == ".csv":
            write_csv(tabular_doc, output_path)
        else:
            write_tabular_as_text(tabular_doc, output_path)

    def _get_model_version(self) -> str:
        """Get NLP model version string.

        Returns:
            Model version (e.g., "fr_core_news_lg-3.8.0")
        """
        model = resolve_spacy_model(self.model_name)
        try:
            info = self._get_detector().spacy_detector.get_model_info()
            if isinstance(info, dict) and "version" in info:
                # spaCy meta names omit the language prefix ("core_news_lg")
                lang, name = info.get("language", ""), info.get("name", "")
                if lang and not name.startswith(f"{lang}_"):
                    name = f"{lang}_{name}"
                return f"{name}-{info['version']}"
        except (OSError, AttributeError, ImportError) as e:
            logger.warning(
                "model_version_unavailable",
                error_type=type(e).__name__,
            )
        return f"{model}-unknown"

    def _log_failed_operation(
        self,
        input_path: str,
        error_message: str,
        processing_time: float,
        detected_entities: list[DetectedEntity],
    ) -> None:
        """Log failed operation to audit trail.

        Args:
            input_path: Input file path
            error_message: Error description
            processing_time: Processing time before failure
            detected_entities: Entities detected before failure (may be empty)
        """
        try:
            with open_database(self.db_path, self.passphrase) as db_session:
                audit_repo = AuditRepository(db_session.session)
                operation = Operation(
                    operation_type="PROCESS",
                    files_processed=[input_path],
                    model_name=self.model_name,
                    model_version=self._get_model_version(),
                    theme_selected=self.theme,
                    entity_count=len(detected_entities),
                    processing_time_seconds=processing_time,
                    success=False,
                    error_message=error_message,
                )
                audit_repo.log_operation(operation)
        except Exception as e:
            # Audit logging failed - log to application logger but don't propagate
            logger.error("audit_logging_failed", error=self._sanitize_error_message(e))
