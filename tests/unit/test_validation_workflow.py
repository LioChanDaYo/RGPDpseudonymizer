"""Unit tests for ValidationWorkflow._get_pseudonym title preservation."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
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
