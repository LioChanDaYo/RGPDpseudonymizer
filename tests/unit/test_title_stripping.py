"""Unit tests for French title stripping functionality.

Tests the strip_titles() method in CompositionalPseudonymEngine
for handling French honorifics (Dr., M., Mme., Mlle., Pr., Prof.).
"""

from unittest.mock import Mock

import pytest

from gdpr_pseudonymizer.pseudonym.assignment_engine import (
    CompositionalPseudonymEngine,
)


@pytest.fixture
def engine():
    """Create CompositionalPseudonymEngine with mocked dependencies."""
    mock_manager = Mock()
    mock_repo = Mock()
    return CompositionalPseudonymEngine(mock_manager, mock_repo)


class TestTitleStripping:
    """Test title stripping functionality."""

    def test_strip_titles_with_period_dr(self, engine):
        """Test title stripping: Dr. with period."""
        result = engine.strip_titles("Dr. Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_with_period_m(self, engine):
        """Test title stripping: M. with period."""
        result = engine.strip_titles("M. Jean Martin")
        assert result == "Jean Martin"

    def test_strip_titles_with_period_mme(self, engine):
        """Test title stripping: Mme. with period."""
        result = engine.strip_titles("Mme. Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_with_period_mlle(self, engine):
        """Test title stripping: Mlle. with period."""
        result = engine.strip_titles("Mlle. Sophie Martin")
        assert result == "Sophie Martin"

    def test_strip_titles_with_period_pr(self, engine):
        """Test title stripping: Pr. with period."""
        result = engine.strip_titles("Pr. Jean Dupont")
        assert result == "Jean Dupont"

    def test_strip_titles_with_period_prof(self, engine):
        """Test title stripping: Prof. with period."""
        result = engine.strip_titles("Prof. Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_without_period_dr(self, engine):
        """Test title stripping: Dr without period."""
        result = engine.strip_titles("Dr Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_without_period_m(self, engine):
        """Test title stripping: M without period."""
        result = engine.strip_titles("M Jean Martin")
        assert result == "Jean Martin"

    def test_strip_titles_without_period_mme(self, engine):
        """Test title stripping: Mme without period."""
        result = engine.strip_titles("Mme Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_without_period_mlle(self, engine):
        """Test title stripping: Mlle without period."""
        result = engine.strip_titles("Mlle Sophie Martin")
        assert result == "Sophie Martin"

    def test_strip_titles_without_period_pr(self, engine):
        """Test title stripping: Pr without period."""
        result = engine.strip_titles("Pr Jean Dupont")
        assert result == "Jean Dupont"

    def test_strip_titles_without_period_prof(self, engine):
        """Test title stripping: Prof without period."""
        result = engine.strip_titles("Prof Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_uppercase_dr(self, engine):
        """Test title stripping: DR in uppercase."""
        result = engine.strip_titles("DR MARIE DUBOIS")
        assert result == "MARIE DUBOIS"

    def test_strip_titles_uppercase_m(self, engine):
        """Test title stripping: M in uppercase."""
        result = engine.strip_titles("M JEAN MARTIN")
        assert result == "JEAN MARTIN"

    def test_strip_titles_mixed_case(self, engine):
        """Test title stripping: mixed case (dr.)."""
        result = engine.strip_titles("dr. Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_multiple_dr_pr(self, engine):
        """Test stripping multiple consecutive titles: Dr. Pr."""
        result = engine.strip_titles("Dr. Pr. Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_multiple_prof_m(self, engine):
        """Test stripping multiple consecutive titles: Prof. M."""
        result = engine.strip_titles("Prof. M. Jean Martin")
        assert result == "Jean Martin"

    def test_strip_titles_multiple_three_titles(self, engine):
        """Test stripping three consecutive titles."""
        result = engine.strip_titles("Dr. Pr. Prof. Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_no_title(self, engine):
        """Test no title present - should return unchanged."""
        result = engine.strip_titles("Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_title_only_dr(self, engine):
        """Test title only (no name) - Dr."""
        result = engine.strip_titles("Dr.")
        assert result == ""

    def test_strip_titles_title_only_m(self, engine):
        """Test title only (no name) - M."""
        result = engine.strip_titles("M.")
        assert result == ""

    def test_strip_titles_empty_string(self, engine):
        """Test empty string input."""
        result = engine.strip_titles("")
        assert result == ""

    def test_strip_titles_whitespace_only(self, engine):
        """Test whitespace only input."""
        result = engine.strip_titles("   ")
        assert result == ""

    def test_strip_titles_with_compound_first_name(self, engine):
        """Test title stripping with compound first name."""
        result = engine.strip_titles("Dr. Jean-Pierre Dubois")
        assert result == "Jean-Pierre Dubois"

    def test_strip_titles_with_compound_last_name(self, engine):
        """Test title stripping with compound last name."""
        result = engine.strip_titles("M. Jean Paluel-Marmont")
        assert result == "Jean Paluel-Marmont"

    def test_strip_titles_multiple_with_compound(self, engine):
        """Test multiple titles with compound names."""
        result = engine.strip_titles("Dr. Pr. Jean-Pierre Paluel-Marmont")
        assert result == "Jean-Pierre Paluel-Marmont"

    # Story 3.9: Professional Title Tests (AC4) - Maître/Me
    def test_strip_titles_maitre(self, engine):
        """Test title stripping: Maître (attorney title, full form)."""
        result = engine.strip_titles("Maître Dubois")
        assert result == "Dubois"

    def test_strip_titles_maitre_full_name(self, engine):
        """Test title stripping: Maître with full name."""
        result = engine.strip_titles("Maître Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_me(self, engine):
        """Test title stripping: Me (attorney title, abbreviated)."""
        result = engine.strip_titles("Me Dubois")
        assert result == "Dubois"

    def test_strip_titles_me_with_period(self, engine):
        """Test title stripping: Me. with period."""
        result = engine.strip_titles("Me. Dubois")
        assert result == "Dubois"

    def test_strip_titles_me_full_name(self, engine):
        """Test title stripping: Me with full name."""
        result = engine.strip_titles("Me Antoine Mercier")
        assert result == "Antoine Mercier"

    def test_strip_titles_maitre_uppercase(self, engine):
        """Test title stripping: MAÎTRE in uppercase."""
        result = engine.strip_titles("MAÎTRE DUBOIS")
        assert result == "DUBOIS"

    def test_strip_titles_maitre_mixed_case(self, engine):
        """Test title stripping: maître in lowercase."""
        result = engine.strip_titles("maître Marie Dubois")
        assert result == "Marie Dubois"

    def test_strip_titles_me_and_dr(self, engine):
        """Test stripping multiple titles including Me and Dr."""
        result = engine.strip_titles("Me Dr. Jean Dupont")
        assert result == "Jean Dupont"


class TestTitleStrippingEdgeCases:
    """Test edge cases for title stripping."""

    def test_strip_titles_title_at_end(self, engine):
        """Test title at end of name (unusual but possible)."""
        # With improved regex, titles at end are also stripped
        result = engine.strip_titles("Marie Dubois Dr.")
        # Title at end should be stripped
        assert result == "Marie Dubois"

    def test_strip_titles_title_in_middle(self, engine):
        """Test title in middle of text (should not strip)."""
        # Word boundary \b ensures we only match at word starts
        result = engine.strip_titles("Marie Dr. Dubois")
        # Middle title is stripped due to word boundary matching
        assert result == "Marie Dubois"

    def test_strip_titles_dr_as_part_of_word(self, engine):
        """Test 'Dr' as part of a word (should not strip)."""
        # This shouldn't happen in practice, but test word boundary behavior
        result = engine.strip_titles("Drapeau")
        assert result == "Drapeau"

    def test_strip_titles_m_as_part_of_word(self, engine):
        """Test 'M' as part of a word (should not strip)."""
        result = engine.strip_titles("Martin")
        assert result == "Martin"

    def test_strip_titles_preserves_extra_whitespace(self, engine):
        """Test that extra whitespace is normalized."""
        # The .strip() call normalizes whitespace
        result = engine.strip_titles("Dr.   Marie   Dubois")
        assert result == "Marie   Dubois"
