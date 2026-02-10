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

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from gdpr_pseudonymizer.data.database import DatabaseSession, open_database
from gdpr_pseudonymizer.data.models import Entity, Operation
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    MappingRepository,
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.exceptions import FileProcessingError
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
)
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager
from gdpr_pseudonymizer.utils.file_handler import read_file, write_file
from gdpr_pseudonymizer.utils.logger import get_logger
from gdpr_pseudonymizer.validation.workflow import run_validation_workflow

# Configure logging (NO sensitive data)
logger = get_logger(__name__)


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
    """

    success: bool
    input_file: str
    output_file: str
    entities_detected: int
    entities_new: int
    entities_reused: int
    processing_time_seconds: float
    error_message: str | None = None


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
            model_name: NLP model name (spacy)
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

    def _get_detector(self) -> HybridDetector:
        """Get or initialize hybrid entity detector.

        Returns:
            HybridDetector instance

        Raises:
            OSError: If spaCy model not installed
        """
        if self._detector is None:
            self._detector = HybridDetector()
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

    def _build_pseudonym_assigner(
        self, ctx: _ProcessingContext
    ) -> Callable[[DetectedEntity], str]:
        """Build a closure that generates pseudonym previews for validation.

        The returned callable looks up existing mappings first, then generates
        new pseudonyms via the compositional engine. An internal cache ensures
        consistent component reuse within a single validation session.

        Args:
            ctx: Processing context with repos and engine

        Returns:
            Callable that maps DetectedEntity -> pseudonym preview string
        """
        preview_cache: dict[str, str] = {}

        def pseudonym_assigner(entity: DetectedEntity) -> str:
            entity_text_stripped = ctx.compositional_engine.strip_titles(entity.text)
            if entity.entity_type == "LOCATION":
                entity_text_stripped = ctx.compositional_engine.strip_prepositions(
                    entity_text_stripped
                )

            existing_entity = ctx.mapping_repo.find_by_full_name(entity_text_stripped)
            if existing_entity:
                return existing_entity.pseudonym_full

            if entity_text_stripped in preview_cache:
                return preview_cache[entity_text_stripped]

            try:
                assignment = ctx.compositional_engine.assign_compositional_pseudonym(
                    entity_text=entity_text_stripped,
                    entity_type=entity.entity_type,
                    gender=None,
                )
                preview_cache[entity_text_stripped] = assignment.pseudonym_full
                return assignment.pseudonym_full
            except Exception:
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
    ) -> list[DetectedEntity]:
        """Run entity validation workflow (interactive or auto-accept)."""
        if skip_validation:
            logger.info(
                "validation_skipped",
                auto_accepted_count=len(detected_entities),
                reason="parallel_mode",
            )
            return detected_entities

        # Separate entities into known (auto-accept) and unknown (need validation)
        known_entities: list[DetectedEntity] = []
        unknown_entities: list[DetectedEntity] = []

        for entity in detected_entities:
            entity_text_stripped = ctx.compositional_engine.strip_titles(entity.text)
            if entity.entity_type == "LOCATION":
                entity_text_stripped = ctx.compositional_engine.strip_prepositions(
                    entity_text_stripped
                )

            existing = ctx.mapping_repo.find_by_full_name(entity_text_stripped)
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
                )
            else:
                validated_unknown = []
                self._notifier(
                    "All entities have existing mappings. Skipping validation."
                )

            validated_entities = known_entities + validated_unknown
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
        if entity.entity_type == "PERSON":
            original_first, original_last, _ = ctx.compositional_engine.parse_full_name(
                entity_text_stripped
            )
        new_entity = Entity(
            entity_type=entity.entity_type,
            first_name=original_first,
            last_name=original_last,
            full_name=entity_text_stripped,
            pseudonym_first=assignment.pseudonym_first,
            pseudonym_last=assignment.pseudonym_last,
            pseudonym_full=assignment.pseudonym_full,
            first_seen_timestamp=datetime.now(timezone.utc),
            gender=None,
            confidence_score=(
                entity.confidence if hasattr(entity, "confidence") else None
            ),
            theme=self.theme,
            is_ambiguous=assignment.is_ambiguous,
            ambiguity_reason=assignment.ambiguity_reason,
        )
        return assignment.pseudonym_full, new_entity

    def _resolve_pseudonyms(
        self,
        ctx: _ProcessingContext,
        validated_entities: list[DetectedEntity],
    ) -> _ResolveResult:
        """Resolve pseudonyms for all validated entities."""
        logger.info(
            "starting_entity_processing",
            validated_count=len(validated_entities),
        )
        replacements: list[tuple[int, int, str]] = []
        new_entities: list[Entity] = []
        entity_cache: dict[str, str] = {}
        entities_new = 0
        entities_reused = 0

        for entity in validated_entities:
            logger.debug(
                "processing_entity",
                entity_text=entity.text,
                entity_type=entity.entity_type,
            )
            entity_text_stripped = ctx.compositional_engine.strip_titles(entity.text)
            if entity.entity_type == "LOCATION":
                entity_text_stripped = ctx.compositional_engine.strip_prepositions(
                    entity_text_stripped
                )

            if entity_text_stripped in entity_cache:
                pseudonym = entity_cache[entity_text_stripped]
                entities_reused += 1
            else:
                existing_entity = ctx.mapping_repo.find_by_full_name(
                    entity_text_stripped
                )
                if existing_entity:
                    pseudonym = existing_entity.pseudonym_full
                    entity_cache[entity_text_stripped] = pseudonym
                    entities_reused += 1
                else:
                    component_match = (
                        self._check_component_match(
                            ctx, entity_text_stripped, new_entities
                        )
                        if entity.entity_type == "PERSON"
                        else None
                    )
                    if component_match:
                        pseudonym = component_match
                        entity_cache[entity_text_stripped] = pseudonym
                        entities_reused += 1
                    else:
                        pseudonym, new_entity = self._assign_new_pseudonym(
                            ctx, entity, entity_text_stripped
                        )
                        entity_cache[entity_text_stripped] = pseudonym
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
                    error=str(e),
                    entity_count=len(new_entities),
                )
                raise

        return _ResolveResult(
            replacements=replacements,
            entities_new=entities_new,
            entities_reused=entities_reused,
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

    def _reset_pseudonym_state(self, ctx: _ProcessingContext) -> None:
        """Reset pseudonym manager after validation preview.

        The validation preview generates pseudonyms that are never saved.
        This clears that state and reloads genuine DB mappings to prevent
        collision false positives during actual processing.

        Args:
            ctx: Processing context with pseudonym_manager and mapping_repo
        """
        ctx.pseudonym_manager.reset_preview_state()
        existing_entities = ctx.mapping_repo.find_all()
        ctx.pseudonym_manager.load_existing_mappings(existing_entities)
        logger.info(
            "pseudonym_manager_reset_after_validation",
            existing_mappings_reloaded=len(existing_entities),
        )

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

        compositional_engine = CompositionalPseudonymEngine(
            pseudonym_manager=pseudonym_manager,
            mapping_repository=mapping_repo,
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

    def _handle_processing_error(
        self,
        error: Exception,
        input_path: str,
        output_path: str,
        start_time: float,
    ) -> ProcessingResult:
        """Format error, log to audit trail, and return failure result."""
        processing_time = time.time() - start_time
        error_message = (
            str(error)
            if isinstance(error, FileProcessingError)
            else f"{type(error).__name__}: {error}"
        )
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

    def process_document(
        self,
        input_path: str,
        output_path: str,
        skip_validation: bool = False,
        entity_type_filter: set[str] | None = None,
    ) -> ProcessingResult:
        """Process single document with complete pseudonymization workflow."""
        start_time = time.time()
        try:
            document_text = read_file(input_path)
            detected_entities = self._detect_and_filter_entities(
                document_text, entity_type_filter
            )
            with open_database(self.db_path, self.passphrase) as db_session:
                ctx = self._init_processing_context(db_session)
                pseudonym_assigner = self._build_pseudonym_assigner(ctx)
                validated_entities = self._run_validation(
                    ctx=ctx,
                    detected_entities=detected_entities,
                    document_text=document_text,
                    input_path=input_path,
                    skip_validation=skip_validation,
                    pseudonym_assigner=pseudonym_assigner,
                )
                self._reset_pseudonym_state(ctx)
                resolve_result = self._resolve_pseudonyms(ctx, validated_entities)
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
                )
        except Exception as e:
            return self._handle_processing_error(e, input_path, output_path, start_time)

    def _get_model_version(self) -> str:
        """Get NLP model version string.

        Returns:
            Model version (e.g., "fr_core_news_lg-3.8.0")
        """
        if self.model_name == "spacy":
            try:
                detector = self._get_detector()
                if hasattr(detector, "nlp") and detector.nlp is not None:
                    # Extract model name and version from spaCy meta
                    meta = detector.nlp.meta
                    return (
                        f"{meta.get('name', 'unknown')}-{meta.get('version', '0.0.0')}"
                    )
            except Exception:
                pass
        return f"{self.model_name}-unknown"

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
            logger.error("audit_logging_failed", error=str(e))
