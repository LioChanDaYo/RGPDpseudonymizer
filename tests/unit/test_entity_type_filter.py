"""Tests for selective entity type processing (--entity-types filter)."""

from __future__ import annotations

import re

from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


def test_process_help_shows_entity_types_option() -> None:
    """Verify process --help mentions --entity-types."""
    result = runner.invoke(app, ["process", "--help"])
    assert result.exit_code == 0
    assert "--entity-types" in _strip_ansi(result.output)


def test_batch_help_shows_entity_types_option() -> None:
    """Verify batch --help mentions --entity-types."""
    result = runner.invoke(app, ["batch", "--help"])
    assert result.exit_code == 0
    assert "--entity-types" in _strip_ansi(result.output)


class TestEntityTypeFiltering:
    """Unit tests for entity type filtering logic."""

    def test_filter_single_type(self) -> None:
        """Filter with single type keeps only that type."""
        entities = [
            DetectedEntity(text="Marie", entity_type="PERSON", start_pos=0, end_pos=5),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=10, end_pos=15
            ),
            DetectedEntity(text="ACME", entity_type="ORG", start_pos=20, end_pos=24),
        ]
        allowed = {"PERSON"}
        filtered = [e for e in entities if e.entity_type in allowed]
        assert len(filtered) == 1
        assert filtered[0].entity_type == "PERSON"

    def test_filter_multiple_types(self) -> None:
        """Filter with multiple types keeps all matching."""
        entities = [
            DetectedEntity(text="Marie", entity_type="PERSON", start_pos=0, end_pos=5),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=10, end_pos=15
            ),
            DetectedEntity(text="ACME", entity_type="ORG", start_pos=20, end_pos=24),
        ]
        allowed = {"PERSON", "ORG"}
        filtered = [e for e in entities if e.entity_type in allowed]
        assert len(filtered) == 2
        types = {e.entity_type for e in filtered}
        assert types == {"PERSON", "ORG"}

    def test_filter_all_types(self) -> None:
        """Filter with all types keeps everything."""
        entities = [
            DetectedEntity(text="Marie", entity_type="PERSON", start_pos=0, end_pos=5),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=10, end_pos=15
            ),
        ]
        allowed = {"PERSON", "LOCATION", "ORG"}
        filtered = [e for e in entities if e.entity_type in allowed]
        assert len(filtered) == 2

    def test_no_filter_keeps_all(self) -> None:
        """No filter (None) keeps all entities."""
        entities = [
            DetectedEntity(text="Marie", entity_type="PERSON", start_pos=0, end_pos=5),
            DetectedEntity(
                text="Paris", entity_type="LOCATION", start_pos=10, end_pos=15
            ),
        ]
        entity_type_filter = None
        if entity_type_filter:
            filtered = [e for e in entities if e.entity_type in entity_type_filter]
        else:
            filtered = entities
        assert len(filtered) == 2
