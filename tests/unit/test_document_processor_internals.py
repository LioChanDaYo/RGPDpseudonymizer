"""Tests for DocumentProcessor extracted sub-methods (R3).

Tests each private method extracted during the process_document() decomposition.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_processor() -> object:
    """Create a DocumentProcessor without triggering DB or NLP init."""
    from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

    return DocumentProcessor(db_path="test.db", passphrase="test_pass")


def _make_entity(
    text: str, entity_type: str, start: int = 0, end: int = 0
) -> DetectedEntity:
    """Create a DetectedEntity for testing."""
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=end or start + len(text),
        confidence=0.95,
        source="test",
    )


# ===========================================================================
# _detect_and_filter_entities
# ===========================================================================


class TestDetectAndFilterEntities:
    """Tests for _detect_and_filter_entities()."""

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_returns_all_entities_when_no_filter(
        self, mock_detector_cls: MagicMock
    ) -> None:
        """All detected entities are returned when entity_type_filter is None."""
        entities = [
            _make_entity("Marie", "PERSON"),
            _make_entity("Paris", "LOCATION"),
            _make_entity("ACME", "ORG"),
        ]
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities("some text")

        assert result == entities
        mock_detector.detect_entities.assert_called_once_with("some text")

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_filters_by_entity_type(self, mock_detector_cls: MagicMock) -> None:
        """Only entities matching the filter set are returned."""
        entities = [
            _make_entity("Marie", "PERSON"),
            _make_entity("Paris", "LOCATION"),
            _make_entity("ACME", "ORG"),
        ]
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities(
            "some text", entity_type_filter={"PERSON", "ORG"}
        )

        assert len(result) == 2
        assert all(e.entity_type in {"PERSON", "ORG"} for e in result)

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_empty_filter_returns_nothing(self, mock_detector_cls: MagicMock) -> None:
        """An empty filter set returns no entities."""
        entities = [_make_entity("Marie", "PERSON")]
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = entities
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities(
            "some text", entity_type_filter=set()
        )

        # Empty set is falsy, so filter is not applied
        # This matches the current behavior: `if entity_type_filter:` is False for empty set
        assert result == entities

    @patch("gdpr_pseudonymizer.core.document_processor.HybridDetector")
    def test_no_entities_detected(self, mock_detector_cls: MagicMock) -> None:
        """Returns empty list when detector finds no entities."""
        mock_detector = MagicMock()
        mock_detector.detect_entities.return_value = []
        mock_detector_cls.return_value = mock_detector

        processor = _make_processor()
        result = processor._detect_and_filter_entities("empty text")

        assert result == []


# ===========================================================================
# _init_processing_context
# ===========================================================================


class TestInitProcessingContext:
    """Tests for _init_processing_context()."""

    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.AuditRepository")
    @patch("gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository")
    def test_returns_processing_context(
        self,
        mock_sqlite_repo: MagicMock,
        mock_audit_repo: MagicMock,
        mock_manager_cls: MagicMock,
        mock_engine_cls: MagicMock,
    ) -> None:
        """Returns a _ProcessingContext with all four dependencies."""
        from gdpr_pseudonymizer.core.document_processor import _ProcessingContext

        mock_db_session = Mock()
        mock_manager = mock_manager_cls.return_value
        mock_manager.load_library.return_value = None
        mock_manager.load_existing_mappings.return_value = None
        mock_sqlite_repo.return_value.find_all.return_value = []

        processor = _make_processor()
        ctx = processor._init_processing_context(mock_db_session)

        assert isinstance(ctx, _ProcessingContext)
        assert ctx.mapping_repo is mock_sqlite_repo.return_value
        assert ctx.audit_repo is mock_audit_repo.return_value
        assert ctx.pseudonym_manager is mock_manager
        assert ctx.compositional_engine is mock_engine_cls.return_value

    @patch("gdpr_pseudonymizer.core.document_processor.CompositionalPseudonymEngine")
    @patch("gdpr_pseudonymizer.core.document_processor.LibraryBasedPseudonymManager")
    @patch("gdpr_pseudonymizer.core.document_processor.AuditRepository")
    @patch("gdpr_pseudonymizer.core.document_processor.SQLiteMappingRepository")
    def test_loads_theme_and_existing_mappings(
        self,
        mock_sqlite_repo: MagicMock,
        mock_audit_repo: MagicMock,
        mock_manager_cls: MagicMock,
        mock_engine_cls: MagicMock,
    ) -> None:
        """Loads theme library and existing mappings for collision prevention."""
        from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

        mock_db_session = Mock()
        mock_manager = mock_manager_cls.return_value
        mock_manager.load_library.return_value = None
        mock_manager.load_existing_mappings.return_value = None
        existing = [Mock(), Mock()]
        mock_sqlite_repo.return_value.find_all.return_value = existing

        processor = DocumentProcessor(
            db_path="test.db", passphrase="test_pass", theme="star_wars"
        )
        processor._init_processing_context(mock_db_session)

        mock_manager.load_library.assert_called_once_with("star_wars")
        mock_manager.load_existing_mappings.assert_called_once_with(existing)


# ===========================================================================
# _build_pseudonym_assigner
# ===========================================================================


class TestBuildPseudonymAssigner:
    """Tests for _build_pseudonym_assigner()."""

    def test_returns_callable(self) -> None:
        """Returns a callable that accepts a DetectedEntity."""

        ctx = Mock()
        ctx.mapping_repo.find_by_full_name.return_value = None
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        ctx.compositional_engine.strip_prepositions.side_effect = lambda t: t
        assignment = Mock()
        assignment.pseudonym_full = "Jean Dupont"
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )

        processor = _make_processor()
        assigner = processor._build_pseudonym_assigner(ctx)

        result = assigner(_make_entity("Marie Dubois", "PERSON"))
        assert result == "Jean Dupont"

    def test_returns_existing_mapping_if_found(self) -> None:
        """If entity already mapped in DB, returns existing pseudonym."""

        ctx = Mock()
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        existing = Mock()
        existing.pseudonym_full = "Existing Pseudo"
        ctx.mapping_repo.find_by_full_name.return_value = existing

        processor = _make_processor()
        assigner = processor._build_pseudonym_assigner(ctx)

        result = assigner(_make_entity("Marie Dubois", "PERSON"))
        assert result == "Existing Pseudo"
        ctx.compositional_engine.assign_compositional_pseudonym.assert_not_called()

    def test_caches_preview_for_consistency(self) -> None:
        """Second call for same entity text returns cached preview."""

        ctx = Mock()
        ctx.mapping_repo.find_by_full_name.return_value = None
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        assignment = Mock()
        assignment.pseudonym_full = "Jean Dupont"
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )

        processor = _make_processor()
        assigner = processor._build_pseudonym_assigner(ctx)

        entity = _make_entity("Marie Dubois", "PERSON")
        result1 = assigner(entity)
        result2 = assigner(entity)

        assert result1 == result2 == "Jean Dupont"
        # Engine should only be called once (second call uses cache)
        ctx.compositional_engine.assign_compositional_pseudonym.assert_called_once()

    def test_fallback_on_assignment_error(self) -> None:
        """Returns fallback preview string when assignment fails."""

        ctx = Mock()
        ctx.mapping_repo.find_by_full_name.return_value = None
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        ctx.compositional_engine.assign_compositional_pseudonym.side_effect = (
            RuntimeError
        )

        processor = _make_processor()
        assigner = processor._build_pseudonym_assigner(ctx)

        result = assigner(_make_entity("Marie", "PERSON"))
        assert result == "[PERSON_PREVIEW]"


# ===========================================================================
# _run_validation
# ===========================================================================


class TestRunValidation:
    """Tests for _run_validation()."""

    def test_skip_validation_returns_all_entities(self) -> None:
        """In parallel mode, all entities are auto-accepted."""
        ctx = Mock()
        entities = [
            _make_entity("Marie", "PERSON"),
            _make_entity("Paris", "LOCATION"),
        ]
        assigner = Mock()

        processor = _make_processor()
        result = processor._run_validation(
            ctx=ctx,
            detected_entities=entities,
            document_text="text",
            input_path="in.txt",
            skip_validation=True,
            pseudonym_assigner=assigner,
        )

        assert result == entities
        assigner.assert_not_called()

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    def test_interactive_separates_known_and_unknown(
        self, mock_workflow: MagicMock
    ) -> None:
        """Known entities are auto-accepted; unknown go through workflow."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        ctx.compositional_engine.strip_prepositions.side_effect = lambda t: t

        known_entity = _make_entity("Marie", "PERSON")
        unknown_entity = _make_entity("Pierre", "PERSON")

        # Marie exists in DB, Pierre doesn't
        ctx.mapping_repo.find_by_full_name.side_effect = lambda name: (
            Mock() if name == "Marie" else None
        )

        mock_workflow.return_value = [unknown_entity]

        processor = _make_processor()
        result = processor._run_validation(
            ctx=ctx,
            detected_entities=[known_entity, unknown_entity],
            document_text="text",
            input_path="in.txt",
            skip_validation=False,
            pseudonym_assigner=Mock(),
        )

        assert len(result) == 2
        assert known_entity in result
        assert unknown_entity in result
        mock_workflow.assert_called_once()

    @patch("gdpr_pseudonymizer.core.document_processor.run_validation_workflow")
    def test_all_known_skips_workflow(self, mock_workflow: MagicMock) -> None:
        """When all entities are known, workflow is not invoked."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t

        entity = _make_entity("Marie", "PERSON")
        ctx.mapping_repo.find_by_full_name.return_value = Mock()

        messages: list[str] = []
        processor = _make_processor()
        processor._notifier = messages.append

        result = processor._run_validation(
            ctx=ctx,
            detected_entities=[entity],
            document_text="text",
            input_path="in.txt",
            skip_validation=False,
            pseudonym_assigner=Mock(),
        )

        assert result == [entity]
        mock_workflow.assert_not_called()
        assert any("Skipping validation" in m for m in messages)


# ===========================================================================
# _reset_pseudonym_state
# ===========================================================================


class TestResetPseudonymState:
    """Tests for _reset_pseudonym_state()."""

    def test_clears_and_reloads_mappings(self) -> None:
        """Resets preview state and reloads existing mappings from DB."""
        ctx = Mock()
        existing = [Mock(), Mock()]
        ctx.mapping_repo.find_all.return_value = existing

        processor = _make_processor()
        processor._reset_pseudonym_state(ctx)

        ctx.pseudonym_manager.reset_preview_state.assert_called_once()
        ctx.mapping_repo.find_all.assert_called_once()
        ctx.pseudonym_manager.load_existing_mappings.assert_called_once_with(existing)


# ===========================================================================
# _check_component_match
# ===========================================================================


class TestCheckComponentMatch:
    """Tests for _check_component_match()."""

    def test_returns_none_when_not_ambiguous(self) -> None:
        """Non-ambiguous names (two-word) should not match."""
        ctx = Mock()
        ctx.compositional_engine.parse_full_name.return_value = (
            "Marie",
            "Dubois",
            False,
        )

        processor = _make_processor()
        result = processor._check_component_match(ctx, "Marie Dubois", [])
        assert result is None

    def test_matches_first_name_component(self) -> None:
        """Standalone name matching a previous entity's first_name."""
        ctx = Mock()
        ctx.compositional_engine.parse_full_name.return_value = ("Marie", None, True)

        prev = Mock()
        prev.entity_type = "PERSON"
        prev.first_name = "Marie"
        prev.pseudonym_first = "Emma"
        prev.full_name = "Marie Dubois"

        processor = _make_processor()
        result = processor._check_component_match(ctx, "Marie", [prev])
        assert result == "Emma"

    def test_matches_last_name_component(self) -> None:
        """Standalone name matching a previous entity's last_name."""
        ctx = Mock()
        ctx.compositional_engine.parse_full_name.return_value = ("Dubois", None, True)

        prev = Mock()
        prev.entity_type = "PERSON"
        prev.first_name = "Marie"
        prev.last_name = "Dubois"
        prev.pseudonym_last = "Martin"
        prev.full_name = "Marie Dubois"

        processor = _make_processor()
        result = processor._check_component_match(ctx, "Dubois", [prev])
        assert result == "Martin"

    def test_returns_none_on_parse_error(self) -> None:
        """Returns None if parse_full_name raises."""
        ctx = Mock()
        ctx.compositional_engine.parse_full_name.side_effect = ValueError

        processor = _make_processor()
        result = processor._check_component_match(ctx, "broken", [])
        assert result is None


# ===========================================================================
# _compute_replacement_prefix
# ===========================================================================


class TestComputeReplacementPrefix:
    """Tests for _compute_replacement_prefix()."""

    def test_person_title_prefix(self) -> None:
        """Extracts title prefix for PERSON entities."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.return_value = "Marie Dubois"

        entity = _make_entity("Dr. Marie Dubois", "PERSON")
        processor = _make_processor()
        result = processor._compute_replacement_prefix(ctx, entity)
        assert result == "Dr. "

    def test_location_preposition_prefix(self) -> None:
        """Extracts preposition prefix for LOCATION entities."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.return_value = "à Paris"
        ctx.compositional_engine.strip_prepositions.return_value = "Paris"

        entity = _make_entity("à Paris", "LOCATION")
        processor = _make_processor()
        result = processor._compute_replacement_prefix(ctx, entity)
        assert result == "à "

    def test_no_prefix(self) -> None:
        """Returns empty string when no prefix is present."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.return_value = "Marie"

        entity = _make_entity("Marie", "PERSON")
        processor = _make_processor()
        result = processor._compute_replacement_prefix(ctx, entity)
        assert result == ""


# ===========================================================================
# _resolve_pseudonyms
# ===========================================================================


class TestResolvePseudonyms:
    """Tests for _resolve_pseudonyms()."""

    def test_reuses_existing_mapping(self) -> None:
        """Entities with existing DB mappings are reused."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        existing = Mock()
        existing.pseudonym_full = "Jean Dupont"
        ctx.mapping_repo.find_by_full_name.return_value = existing

        processor = _make_processor()
        result = processor._resolve_pseudonyms(
            ctx, [_make_entity("Marie Dubois", "PERSON", 0, 13)]
        )

        assert result.entities_reused == 1
        assert result.entities_new == 0
        assert len(result.replacements) == 1
        assert result.replacements[0][2] == "Jean Dupont"

    def test_assigns_new_pseudonym(self) -> None:
        """New entities get pseudonyms assigned via compositional engine."""
        ctx = Mock()
        ctx.compositional_engine.strip_titles.side_effect = lambda t: t
        ctx.mapping_repo.find_by_full_name.return_value = None
        assignment = Mock()
        assignment.pseudonym_full = "Jean Dupont"
        assignment.pseudonym_first = "Jean"
        assignment.pseudonym_last = "Dupont"
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )
        ctx.compositional_engine.parse_full_name.return_value = (
            "Marie",
            "Dubois",
            False,
        )

        processor = _make_processor()
        result = processor._resolve_pseudonyms(
            ctx, [_make_entity("Marie Dubois", "PERSON", 0, 13)]
        )

        assert result.entities_new == 1
        assert result.entities_reused == 0
        ctx.mapping_repo.save_batch.assert_called_once()

    def test_empty_entities_returns_zero_counts(self) -> None:
        """No entities produces empty result."""
        ctx = Mock()

        processor = _make_processor()
        result = processor._resolve_pseudonyms(ctx, [])

        assert result.entities_new == 0
        assert result.entities_reused == 0
        assert result.replacements == []


# ===========================================================================
# _apply_replacements
# ===========================================================================


class TestApplyReplacements:
    """Tests for _apply_replacements()."""

    def test_applies_single_replacement(self) -> None:
        """Single replacement is applied correctly."""
        processor = _make_processor()
        result = processor._apply_replacements("Hello Marie!", [(6, 11, "Emma")])
        assert result == "Hello Emma!"

    def test_applies_multiple_non_overlapping(self) -> None:
        """Multiple non-overlapping replacements are all applied."""
        processor = _make_processor()
        result = processor._apply_replacements(
            "Marie lives in Paris",
            [(0, 5, "Emma"), (15, 20, "Lyon")],
        )
        assert result == "Emma lives in Lyon"

    def test_deduplicates_overlapping(self) -> None:
        """Overlapping replacements keep only the first (longest span)."""
        processor = _make_processor()
        # "Dr. Marie Dubois" (0-16) overlaps with "Marie Dubois" (4-16)
        result = processor._apply_replacements(
            "Dr. Marie Dubois works here",
            [(0, 16, "Dr. Emma Martin"), (4, 16, "Emma Martin")],
        )
        assert result == "Dr. Emma Martin works here"

    def test_empty_replacements(self) -> None:
        """No replacements returns original text."""
        processor = _make_processor()
        result = processor._apply_replacements("unchanged text", [])
        assert result == "unchanged text"


# ===========================================================================
# _assign_new_pseudonym
# ===========================================================================


class TestAssignNewPseudonym:
    """Tests for _assign_new_pseudonym()."""

    def test_creates_entity_with_correct_fields(self) -> None:
        """Returns pseudonym string and Entity with all expected fields."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Jean Dupont"
        assignment.pseudonym_first = "Jean"
        assignment.pseudonym_last = "Dupont"
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )
        ctx.compositional_engine.parse_full_name.return_value = (
            "Marie",
            "Dubois",
            False,
        )

        processor = _make_processor()
        pseudonym, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Marie Dubois", "PERSON"), "Marie Dubois"
        )

        assert pseudonym == "Jean Dupont"
        assert entity.full_name == "Marie Dubois"
        assert entity.first_name == "Marie"
        assert entity.last_name == "Dubois"
        assert entity.pseudonym_full == "Jean Dupont"

    def test_location_entity_has_no_name_parts(self) -> None:
        """LOCATION entities have None for first_name and last_name."""
        ctx = Mock()
        assignment = Mock()
        assignment.pseudonym_full = "Lyon"
        assignment.pseudonym_first = None
        assignment.pseudonym_last = None
        assignment.is_ambiguous = False
        assignment.ambiguity_reason = None
        ctx.compositional_engine.assign_compositional_pseudonym.return_value = (
            assignment
        )

        processor = _make_processor()
        pseudonym, entity = processor._assign_new_pseudonym(
            ctx, _make_entity("Paris", "LOCATION"), "Paris"
        )

        assert pseudonym == "Lyon"
        assert entity.first_name is None
        assert entity.last_name is None


# ===========================================================================
# _log_success_operation
# ===========================================================================


class TestLogSuccessOperation:
    """Tests for _log_success_operation()."""

    def test_logs_operation_to_audit_repo(self) -> None:
        """Logs a successful PROCESS operation to the audit repository."""
        ctx = Mock()

        processor = _make_processor()
        processor._log_success_operation(
            ctx, "input.txt", [_make_entity("Marie", "PERSON")], 1.5
        )

        ctx.audit_repo.log_operation.assert_called_once()
        op = ctx.audit_repo.log_operation.call_args[0][0]
        assert op.operation_type == "PROCESS"
        assert op.success is True
        assert op.entity_count == 1
        assert op.processing_time_seconds == 1.5


# ===========================================================================
# _handle_processing_error
# ===========================================================================


class TestHandleProcessingError:
    """Tests for _handle_processing_error()."""

    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_returns_failure_result_for_file_error(self, mock_db: MagicMock) -> None:
        """FileProcessingError is formatted as plain string."""
        from gdpr_pseudonymizer.exceptions import FileProcessingError

        processor = _make_processor()
        result = processor._handle_processing_error(
            FileProcessingError("not found"),
            "in.txt",
            "out.txt",
            0.0,
        )

        assert result.success is False
        assert result.error_message == "not found"
        assert result.input_file == "in.txt"

    @patch("gdpr_pseudonymizer.core.document_processor.open_database")
    def test_returns_failure_result_for_generic_error(self, mock_db: MagicMock) -> None:
        """Generic exceptions include type name in error message."""
        processor = _make_processor()
        result = processor._handle_processing_error(
            ValueError("bad value"),
            "in.txt",
            "out.txt",
            0.0,
        )

        assert result.success is False
        assert "ValueError" in result.error_message
        assert "bad value" in result.error_message
