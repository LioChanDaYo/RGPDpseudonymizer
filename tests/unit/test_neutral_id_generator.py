"""Unit tests for NeutralIdPseudonymGenerator."""

from __future__ import annotations

import pytest

from gdpr_pseudonymizer.pseudonym.neutral_id_generator import (
    NeutralIdPseudonymGenerator,
)


class TestNeutralIdPseudonymGenerator:
    """Tests for counter-based pseudonym generation."""

    def test_generate_person_sequential(self) -> None:
        """PER counter increments sequentially."""
        gen = NeutralIdPseudonymGenerator()
        assert gen.generate("PERSON") == "PER-001"
        assert gen.generate("PERSON") == "PER-002"
        assert gen.generate("PERSON") == "PER-003"

    def test_generate_location_sequential(self) -> None:
        """LOC counter increments sequentially."""
        gen = NeutralIdPseudonymGenerator()
        assert gen.generate("LOCATION") == "LOC-001"
        assert gen.generate("LOCATION") == "LOC-002"

    def test_generate_org_sequential(self) -> None:
        """ORG counter increments sequentially."""
        gen = NeutralIdPseudonymGenerator()
        assert gen.generate("ORG") == "ORG-001"
        assert gen.generate("ORG") == "ORG-002"

    def test_counters_independent_per_type(self) -> None:
        """Each entity type has its own independent counter."""
        gen = NeutralIdPseudonymGenerator()
        assert gen.generate("PERSON") == "PER-001"
        assert gen.generate("LOCATION") == "LOC-001"
        assert gen.generate("ORG") == "ORG-001"
        assert gen.generate("PERSON") == "PER-002"
        assert gen.generate("LOCATION") == "LOC-002"

    def test_reset_clears_all_counters(self) -> None:
        """After reset, counters start from 001 again."""
        gen = NeutralIdPseudonymGenerator()
        gen.generate("PERSON")
        gen.generate("LOCATION")
        gen.generate("ORG")

        gen.reset()

        assert gen.generate("PERSON") == "PER-001"
        assert gen.generate("LOCATION") == "LOC-001"
        assert gen.generate("ORG") == "ORG-001"

    def test_set_counter_resumes_from_value(self) -> None:
        """set_counter(5) means next generate returns 006."""
        gen = NeutralIdPseudonymGenerator()
        gen.set_counter("PERSON", 5)
        assert gen.generate("PERSON") == "PER-006"

    def test_zero_padding_format(self) -> None:
        """Counter values are zero-padded to 3 digits."""
        gen = NeutralIdPseudonymGenerator()
        assert gen.generate("PERSON") == "PER-001"

        gen.set_counter("PERSON", 98)
        assert gen.generate("PERSON") == "PER-099"

        assert gen.generate("PERSON") == "PER-100"

    def test_counter_overflow_four_digits(self) -> None:
        """Counter gracefully exceeds 3 digits at 1000."""
        gen = NeutralIdPseudonymGenerator()
        gen.set_counter("PERSON", 998)
        assert gen.generate("PERSON") == "PER-999"
        assert gen.generate("PERSON") == "PER-1000"

    def test_generate_unknown_entity_type_raises(self) -> None:
        """Unknown entity type raises ValueError."""
        gen = NeutralIdPseudonymGenerator()
        with pytest.raises(ValueError, match="Unknown entity_type"):
            gen.generate("UNKNOWN")

    def test_set_counter_unknown_entity_type_raises(self) -> None:
        """set_counter with unknown entity type raises ValueError."""
        gen = NeutralIdPseudonymGenerator()
        with pytest.raises(ValueError, match="Unknown entity_type"):
            gen.set_counter("UNKNOWN", 5)
