"""Unit tests for GenderDetector (Story 5.2, Task 5.2.7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gdpr_pseudonymizer.pseudonym.gender_detector import GenderDetector


@pytest.fixture
def detector() -> GenderDetector:
    """Return a loaded GenderDetector using bundled data."""
    d = GenderDetector()
    d.load()
    return d


@pytest.fixture
def custom_lookup(tmp_path: Path) -> Path:
    """Create a minimal custom lookup file for testing."""
    data = {
        "data_sources": [],
        "male": ["Jean", "Pierre", "Louis"],
        "female": ["Marie", "Claire", "Sophie"],
        "ambiguous": ["Camille", "Dominique"],
    }
    path = tmp_path / "test_lookup.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestGenderDetectorLoad:
    """Tests for loading gender lookup dictionary."""

    def test_load_success(self) -> None:
        detector = GenderDetector()
        detector.load()
        assert detector._loaded is True
        assert len(detector._male_names) > 0
        assert len(detector._female_names) > 0

    def test_load_custom_path(self, custom_lookup: Path) -> None:
        detector = GenderDetector(lookup_path=str(custom_lookup))
        detector.load()
        assert detector._loaded is True
        assert len(detector._male_names) == 3
        assert len(detector._female_names) == 3
        assert len(detector._ambiguous_names) == 2

    def test_load_invalid_path(self, tmp_path: Path) -> None:
        detector = GenderDetector(lookup_path=str(tmp_path / "nonexistent.json"))
        with pytest.raises(FileNotFoundError, match="Gender lookup file not found"):
            detector.load()

    def test_lazy_load_on_first_detect(self) -> None:
        detector = GenderDetector()
        assert detector._loaded is False
        # First call triggers lazy load
        result = detector.detect_gender("Jean")
        assert detector._loaded is True
        assert result == "male"


class TestGenderDetectorDetect:
    """Tests for gender detection from first names."""

    def test_detect_male_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Jean") == "male"

    def test_detect_female_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Marie") == "female"

    def test_detect_unknown_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Xyzabc") is None

    def test_detect_ambiguous_name_camille(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Camille") is None

    def test_detect_ambiguous_name_dominique(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Dominique") is None

    def test_detect_ambiguous_name_claude(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Claude") is None

    def test_case_insensitive_uppercase(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("MARIE") == "female"

    def test_case_insensitive_lowercase(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("jean") == "male"

    def test_case_insensitive_mixed(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("mArIe") == "female"

    def test_empty_string(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("") is None

    def test_whitespace_only(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("   ") is None

    def test_name_with_leading_trailing_spaces(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("  Marie  ") == "female"


class TestGenderDetectorCompoundNames:
    """Tests for compound name handling (AC4)."""

    def test_compound_male_jean_pierre(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Jean-Pierre") == "male"

    def test_compound_female_marie_claire(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Marie-Claire") == "female"

    def test_compound_first_component_wins(self, detector: GenderDetector) -> None:
        # Jean-Marie: first component "Jean" is male
        assert detector.detect_gender("Jean-Marie") == "male"

    def test_compound_unknown_first_component(self, detector: GenderDetector) -> None:
        assert detector.detect_gender("Xyzabc-Marie") is None

    def test_compound_ambiguous_first_component(self, detector: GenderDetector) -> None:
        # Camille is ambiguous -> None
        assert detector.detect_gender("Camille-Rose") is None


class TestGenderDetectorFullName:
    """Tests for gender detection from full entity names."""

    def test_person_female_full_name(self, detector: GenderDetector) -> None:
        assert (
            detector.detect_gender_from_full_name("Marie Dupont", "PERSON") == "female"
        )

    def test_person_male_full_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("Jean Martin", "PERSON") == "male"

    def test_person_unknown_full_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("Xyzabc Smith", "PERSON") is None

    def test_location_returns_none(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("Paris", "LOCATION") is None

    def test_org_returns_none(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("Acme Corp", "ORG") is None

    def test_empty_full_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("", "PERSON") is None

    def test_whitespace_full_name(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("   ", "PERSON") is None

    def test_compound_first_name_in_full_name(self, detector: GenderDetector) -> None:
        assert (
            detector.detect_gender_from_full_name("Marie-Claire Dubois", "PERSON")
            == "female"
        )

    def test_single_name_person(self, detector: GenderDetector) -> None:
        assert detector.detect_gender_from_full_name("Marie", "PERSON") == "female"
