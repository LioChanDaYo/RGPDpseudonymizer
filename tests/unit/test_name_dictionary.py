"""
Unit tests for NameDictionary
"""

from pathlib import Path

import pytest

from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary


class TestNameDictionary:
    """Test suite for NameDictionary class."""

    @pytest.fixture
    def dictionary(self) -> NameDictionary:
        """Create and load a NameDictionary instance."""
        name_dict = NameDictionary()
        name_dict.load()
        return name_dict

    def test_load_dictionary_success(self, dictionary: NameDictionary) -> None:
        """Test successful dictionary loading."""
        assert len(dictionary.first_names) > 0
        assert len(dictionary.last_names) > 0

    def test_load_dictionary_file_not_found(self) -> None:
        """Test error handling when dictionary file doesn't exist."""
        name_dict = NameDictionary(dictionary_path="nonexistent.json")
        with pytest.raises(FileNotFoundError):
            name_dict.load()

    def test_is_first_name_valid(self, dictionary: NameDictionary) -> None:
        """Test first name recognition for valid names."""
        assert dictionary.is_first_name("Marie")
        assert dictionary.is_first_name("Jean")
        assert dictionary.is_first_name("Pierre")

    def test_is_first_name_case_insensitive(self, dictionary: NameDictionary) -> None:
        """Test case-insensitive first name lookup."""
        assert dictionary.is_first_name("marie")
        assert dictionary.is_first_name("JEAN")
        assert dictionary.is_first_name("Pierre")

    def test_is_first_name_invalid(self, dictionary: NameDictionary) -> None:
        """Test first name recognition for invalid names."""
        assert not dictionary.is_first_name("XyzAbc")
        assert not dictionary.is_first_name("NotARealName")

    def test_is_last_name_valid(self, dictionary: NameDictionary) -> None:
        """Test last name recognition for valid names."""
        assert dictionary.is_last_name("Martin")
        assert dictionary.is_last_name("Dubois")
        assert dictionary.is_last_name("Bernard")

    def test_is_last_name_case_insensitive(self, dictionary: NameDictionary) -> None:
        """Test case-insensitive last name lookup."""
        assert dictionary.is_last_name("martin")
        assert dictionary.is_last_name("DUBOIS")
        assert dictionary.is_last_name("Bernard")

    def test_is_last_name_invalid(self, dictionary: NameDictionary) -> None:
        """Test last name recognition for invalid names."""
        assert not dictionary.is_last_name("XyzAbc")
        assert not dictionary.is_last_name("NotARealName")

    def test_is_full_name_valid(self, dictionary: NameDictionary) -> None:
        """Test full name validation for valid combinations."""
        assert dictionary.is_full_name("Marie", "Dubois")
        assert dictionary.is_full_name("Jean", "Martin")
        assert dictionary.is_full_name("Pierre", "Bernard")

    def test_is_full_name_invalid_first(self, dictionary: NameDictionary) -> None:
        """Test full name validation with invalid first name."""
        assert not dictionary.is_full_name("XyzAbc", "Martin")

    def test_is_full_name_invalid_last(self, dictionary: NameDictionary) -> None:
        """Test full name validation with invalid last name."""
        assert not dictionary.is_full_name("Marie", "XyzAbc")

    def test_is_full_name_both_invalid(self, dictionary: NameDictionary) -> None:
        """Test full name validation with both names invalid."""
        assert not dictionary.is_full_name("XyzAbc", "NotReal")

    def test_get_stats(self, dictionary: NameDictionary) -> None:
        """Test dictionary statistics retrieval."""
        stats = dictionary.get_stats()
        assert "first_names_count" in stats
        assert "last_names_count" in stats
        assert stats["first_names_count"] > 0
        assert stats["last_names_count"] > 0

    def test_french_accents_handling(self, dictionary: NameDictionary) -> None:
        """Test handling of French accented characters."""
        assert dictionary.is_first_name("François")
        assert dictionary.is_first_name("André")
        assert dictionary.is_first_name("René")
