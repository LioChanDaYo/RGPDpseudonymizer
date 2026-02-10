"""Tests for centralized French pattern utilities."""

from __future__ import annotations

from gdpr_pseudonymizer.utils.french_patterns import (
    strip_french_prepositions,
    strip_french_titles,
)


class TestStripFrenchTitles:
    """Tests for strip_french_titles()."""

    def test_strip_docteur(self) -> None:
        assert strip_french_titles("Docteur Dupont") == "Dupont"

    def test_strip_dr_with_period(self) -> None:
        assert strip_french_titles("Dr. Marie Dubois") == "Marie Dubois"

    def test_strip_dr_without_period(self) -> None:
        assert strip_french_titles("Dr Marie Dubois") == "Marie Dubois"

    def test_strip_professeur(self) -> None:
        assert strip_french_titles("Professeur Martin") == "Martin"

    def test_strip_pr_abbreviated(self) -> None:
        assert strip_french_titles("Pr. Martin") == "Martin"

    def test_strip_madame(self) -> None:
        assert strip_french_titles("Madame Fontaine") == "Fontaine"

    def test_strip_mme_abbreviated(self) -> None:
        assert strip_french_titles("Mme. Fontaine") == "Fontaine"

    def test_strip_monsieur(self) -> None:
        assert strip_french_titles("Monsieur Lefèvre") == "Lefèvre"

    def test_strip_m_abbreviated(self) -> None:
        assert strip_french_titles("M. Lefèvre") == "Lefèvre"

    def test_strip_mademoiselle(self) -> None:
        assert strip_french_titles("Mademoiselle Rousseau") == "Rousseau"

    def test_strip_maitre(self) -> None:
        assert strip_french_titles("Maître Duval") == "Duval"

    def test_strip_me_abbreviated(self) -> None:
        assert strip_french_titles("Me. Duval") == "Duval"

    def test_strip_multiple_titles(self) -> None:
        """Multiple stacked titles should all be removed."""
        assert strip_french_titles("Dr. Pr. Marie Dubois") == "Marie Dubois"

    def test_no_title(self) -> None:
        """Text without titles should be unchanged."""
        assert strip_french_titles("Marie Dubois") == "Marie Dubois"

    def test_empty_string(self) -> None:
        assert strip_french_titles("") == ""

    def test_case_insensitive(self) -> None:
        assert strip_french_titles("DOCTEUR DUPONT") == "DUPONT"

    def test_does_not_strip_partial_match(self) -> None:
        """'Dr' in 'Drapeau' should NOT be stripped (negative lookahead)."""
        assert strip_french_titles("Drapeau") == "Drapeau"


class TestStripFrenchPrepositions:
    """Tests for strip_french_prepositions()."""

    def test_strip_a_accent(self) -> None:
        assert strip_french_prepositions("à Paris") == "Paris"

    def test_strip_au(self) -> None:
        assert strip_french_prepositions("au Brésil") == "Brésil"

    def test_strip_aux(self) -> None:
        assert strip_french_prepositions("aux Antilles") == "Antilles"

    def test_strip_en(self) -> None:
        assert strip_french_prepositions("en France") == "France"

    def test_strip_de(self) -> None:
        assert strip_french_prepositions("de Paris") == "Paris"

    def test_strip_du(self) -> None:
        assert strip_french_prepositions("du Nord") == "Nord"

    def test_strip_des(self) -> None:
        assert strip_french_prepositions("des Champs-Élysées") == "Champs-Élysées"

    def test_strip_d_apostrophe(self) -> None:
        assert strip_french_prepositions("d'Europe") == "Europe"

    def test_strip_l_apostrophe(self) -> None:
        assert strip_french_prepositions("l'Europe") == "Europe"

    def test_no_preposition(self) -> None:
        """Text without prepositions should be unchanged."""
        assert strip_french_prepositions("Paris") == "Paris"

    def test_preserves_la_article(self) -> None:
        """'la' is an article, not a preposition — must NOT be stripped."""
        assert strip_french_prepositions("la Rochelle") == "la Rochelle"

    def test_preserves_le_article(self) -> None:
        """'le' is an article, not a preposition — must NOT be stripped."""
        assert strip_french_prepositions("le Mans") == "le Mans"

    def test_preserves_les_article(self) -> None:
        """'les' is an article, not a preposition — must NOT be stripped."""
        assert strip_french_prepositions("les Ulis") == "les Ulis"

    def test_empty_string(self) -> None:
        assert strip_french_prepositions("") == ""

    def test_leading_whitespace_stripped(self) -> None:
        assert strip_french_prepositions("  à Paris") == "Paris"

    def test_case_insensitive(self) -> None:
        assert strip_french_prepositions("EN France") == "France"
