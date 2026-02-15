"""Unit tests for ValidationWorkflow._get_pseudonym title preservation
and batch operations feedback (Story 5.6, AC2).
"""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import ValidationSession
from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow


def make_assigner(pseudonym: str) -> Callable[[DetectedEntity], str]:
    """Create a pseudonym assigner that returns a fixed pseudonym."""

    def assigner(entity: DetectedEntity) -> str:
        return pseudonym

    return assigner


class TestGetPseudonymTitlePreservation:
    """Test suite for title preservation in _get_pseudonym."""

    @pytest.fixture
    def workflow(self) -> ValidationWorkflow:
        """Create a ValidationWorkflow instance."""
        return ValidationWorkflow()

    def _create_entity(self, text: str, entity_type: str = "PERSON") -> DetectedEntity:
        """Create a DetectedEntity for testing."""
        return DetectedEntity(
            text=text,
            entity_type=entity_type,
            start_pos=0,
            end_pos=len(text),
            confidence=0.9,
            source="spacy",
        )

    def test_preserves_maitre_title(self, workflow: ValidationWorkflow) -> None:
        """Test Maître title is preserved in pseudonym."""
        entity = self._create_entity("Maître Mercier")

        result = workflow._get_pseudonym(entity, make_assigner("Tessier"))

        assert result == "Maître Tessier"

    def test_preserves_me_title(self, workflow: ValidationWorkflow) -> None:
        """Test Me title is preserved in pseudonym."""
        entity = self._create_entity("Me Mercier")

        result = workflow._get_pseudonym(entity, make_assigner("Tessier"))

        assert result == "Me Tessier"

    def test_preserves_me_with_period_title(self, workflow: ValidationWorkflow) -> None:
        """Test Me. title with period is preserved in pseudonym."""
        entity = self._create_entity("Me. Dubois")

        result = workflow._get_pseudonym(entity, make_assigner("Martin"))

        assert result == "Me. Martin"

    def test_preserves_m_title(self, workflow: ValidationWorkflow) -> None:
        """Test M. title is preserved in pseudonym."""
        entity = self._create_entity("M. Dupont")

        result = workflow._get_pseudonym(entity, make_assigner("Laurent"))

        assert result == "M. Laurent"

    def test_preserves_mme_title(self, workflow: ValidationWorkflow) -> None:
        """Test Mme title is preserved in pseudonym."""
        entity = self._create_entity("Mme Rousseau")

        result = workflow._get_pseudonym(entity, make_assigner("Auréliane Brás"))

        assert result == "Mme Auréliane Brás"

    def test_preserves_dr_title(self, workflow: ValidationWorkflow) -> None:
        """Test Dr. title is preserved in pseudonym."""
        entity = self._create_entity("Dr. Martin")

        result = workflow._get_pseudonym(entity, make_assigner("Dubois"))

        assert result == "Dr. Dubois"

    def test_no_title_returns_plain_pseudonym(
        self, workflow: ValidationWorkflow
    ) -> None:
        """Test entity without title returns plain pseudonym."""
        entity = self._create_entity("Jean Dupont")

        result = workflow._get_pseudonym(entity, make_assigner("Pierre Martin"))

        assert result == "Pierre Martin"

    def test_org_entity_no_title_preservation(
        self, workflow: ValidationWorkflow
    ) -> None:
        """Test ORG entities don't get title preservation."""
        entity = self._create_entity("M. Dupont SA", "ORG")

        result = workflow._get_pseudonym(entity, make_assigner("Acme Corp"))

        # ORG entities should not have title preservation
        assert result == "Acme Corp"

    def test_location_entity_no_title_preservation(
        self, workflow: ValidationWorkflow
    ) -> None:
        """Test LOCATION entities don't get title preservation."""
        entity = self._create_entity("Paris", "LOCATION")

        result = workflow._get_pseudonym(entity, make_assigner("Coruscant"))

        assert result == "Coruscant"

    def test_placeholder_when_no_assigner(self, workflow: ValidationWorkflow) -> None:
        """Test placeholder returned when no assigner provided."""
        entity = self._create_entity("Maître Mercier")

        result = workflow._get_pseudonym(entity, None)

        assert result == "[PERSON_Maître Mer]"

    def test_case_insensitive_title_matching(
        self, workflow: ValidationWorkflow
    ) -> None:
        """Test title matching is case-insensitive."""
        entity = self._create_entity("MAÎTRE DUBOIS")

        result = workflow._get_pseudonym(entity, make_assigner("Martin"))

        # Should still preserve the title (case-insensitive match)
        assert "MAÎTRE" in result
        assert "Martin" in result

    def test_maitre_full_name(self, workflow: ValidationWorkflow) -> None:
        """Test Maître title with full name (first + last)."""
        entity = self._create_entity("Maître Antoine Mercier")

        result = workflow._get_pseudonym(entity, make_assigner("Pierre Tessier"))

        assert result == "Maître Pierre Tessier"


def _make_entity(
    text: str, entity_type: str = "PERSON", start_pos: int = 0
) -> DetectedEntity:
    """Create a DetectedEntity for batch tests."""
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start_pos,
        end_pos=start_pos + len(text),
        confidence=0.9,
        source="spacy",
    )


class TestBatchFeedbackMessages:
    """Test suite for batch accept/reject feedback with entity counts (AC2)."""

    def _build_session_with_persons(
        self, names: list[str], document_text: str = ""
    ) -> ValidationSession:
        """Build a session with PERSON entities."""
        if not document_text:
            document_text = " ".join(names)
        session = ValidationSession(
            document_path="test.txt",
            document_text=document_text,
        )
        offset = 0
        for name in names:
            entity = _make_entity(name, "PERSON", start_pos=offset)
            session.add_entity(entity)
            offset += len(name) + 1
        return session

    @patch("gdpr_pseudonymizer.validation.workflow.get_user_action")
    @patch("gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True)
    @patch("gdpr_pseudonymizer.validation.workflow.display_success_message")
    @patch("gdpr_pseudonymizer.validation.workflow.display_info_message")
    def test_batch_accept_shows_affected_count(
        self,
        mock_info: MagicMock,
        mock_success: MagicMock,
        mock_confirm: MagicMock,
        mock_action: MagicMock,
    ) -> None:
        """Batch accept feedback includes count of affected entities."""
        session = self._build_session_with_persons(
            ["Alice", "Bob", "Claire", "David", "Eve"]
        )
        # Simulate: first action is batch_accept
        mock_action.return_value = "batch_accept"

        workflow = ValidationWorkflow()
        workflow._review_entities_by_type(session, make_assigner("X"))

        # Batch accept uses display_success_message (green)
        accept_calls = [
            call for call in mock_success.call_args_list if "Accepted all" in str(call)
        ]
        assert len(accept_calls) >= 1
        msg = str(accept_calls[0])
        assert "Accepted all" in msg
        assert "PERSON" in msg
        assert "total occurrences" in msg

    @patch("gdpr_pseudonymizer.validation.workflow.get_user_action")
    @patch("gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True)
    @patch("gdpr_pseudonymizer.validation.workflow.display_info_message")
    def test_batch_reject_shows_affected_count(
        self,
        mock_info: MagicMock,
        mock_confirm: MagicMock,
        mock_action: MagicMock,
    ) -> None:
        """Batch reject feedback includes count of affected entities."""
        session = self._build_session_with_persons(["Alice", "Bob", "Claire"])
        mock_action.return_value = "batch_reject"

        workflow = ValidationWorkflow()
        workflow._review_entities_by_type(session, make_assigner("X"))

        reject_calls = [
            call for call in mock_info.call_args_list if "Rejected all" in str(call)
        ]
        assert len(reject_calls) >= 1
        msg = str(reject_calls[0])
        assert "✗ Rejected all" in msg
        assert "PERSON" in msg
        assert "total occurrences" in msg

    @patch("gdpr_pseudonymizer.validation.workflow.get_user_action")
    @patch("gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True)
    @patch("gdpr_pseudonymizer.validation.workflow.display_success_message")
    @patch("gdpr_pseudonymizer.validation.workflow.display_info_message")
    def test_batch_accept_excludes_already_decided(
        self,
        mock_info: MagicMock,
        mock_success: MagicMock,
        mock_confirm: MagicMock,
        mock_action: MagicMock,
    ) -> None:
        """Batch accept only counts entities not already decided."""
        session = self._build_session_with_persons(
            ["Alice", "Bob", "Claire", "David", "Eve"]
        )
        # Pre-decide 2 entities (Alice and Bob)
        session.mark_confirmed(session.entities[0])
        session.mark_rejected(session.entities[1])

        mock_action.return_value = "batch_accept"

        workflow = ValidationWorkflow()
        workflow._review_entities_by_type(session, make_assigner("X"))

        accept_calls = [
            call for call in mock_success.call_args_list if "Accepted all" in str(call)
        ]
        assert len(accept_calls) >= 1
        msg = str(accept_calls[0])
        # Should show 3 affected (5 total - 2 already decided)
        assert "3 PERSON" in msg

    @patch("gdpr_pseudonymizer.validation.workflow.get_user_action")
    @patch("gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True)
    @patch("gdpr_pseudonymizer.validation.workflow.display_info_message")
    def test_batch_reject_excludes_already_decided(
        self,
        mock_info: MagicMock,
        mock_confirm: MagicMock,
        mock_action: MagicMock,
    ) -> None:
        """Batch reject only counts entities not already decided."""
        session = self._build_session_with_persons(
            ["Alice", "Bob", "Claire", "David", "Eve"]
        )
        # Pre-decide 2 entities (Alice and Bob)
        session.mark_confirmed(session.entities[0])
        session.mark_rejected(session.entities[1])

        mock_action.return_value = "batch_reject"

        workflow = ValidationWorkflow()
        workflow._review_entities_by_type(session, make_assigner("X"))

        reject_calls = [
            call for call in mock_info.call_args_list if "Rejected all" in str(call)
        ]
        assert len(reject_calls) >= 1
        msg = str(reject_calls[0])
        # Should show 3 affected (5 total - 2 already decided)
        assert "3 PERSON" in msg
