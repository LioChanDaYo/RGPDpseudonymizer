"""Story 10.8: pseudonym previews key each candidate by text, start and type.

T9 (AC1): ``build_pseudonym_previews`` gives each type of a same-span pair
its own entry, title included. Real temporary database, no Qt, no spaCy model.
Invented names only (AC11). No assertion names a key format.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity

PASSPHRASE = "zorbalia_pass_A_123!"
PREVIEW_TEXT = "Dr Zorbalia a signé."
PREVIEW_NAME = "Dr Zorbalia"


def _preview_pair(order: str) -> list[DetectedEntity]:
    start = PREVIEW_TEXT.find(PREVIEW_NAME)
    end = start + len(PREVIEW_NAME)
    assert PREVIEW_TEXT[start:end] == PREVIEW_NAME
    person = DetectedEntity(
        text=PREVIEW_NAME,
        entity_type="PERSON",
        start_pos=start,
        end_pos=end,
        confidence=0.9,
        source="spacy",
    )
    org = DetectedEntity(
        text=PREVIEW_NAME,
        entity_type="ORG",
        start_pos=start,
        end_pos=end,
        confidence=0.9,
        source="regex",
        is_ambiguous=True,
    )
    if order == "person_first":
        return [person, org]
    return [org, person]


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "mappings.db")
    init_database(path, PASSPHRASE)
    return path


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.8: reproduces one preview entry for the pair on the unfixed "
        "keys; fixed in Task 2"
    ),
)
@pytest.mark.parametrize("order", ["person_first", "org_first"])
def test_build_pseudonym_previews_one_entry_per_type(db_path: str, order: str) -> None:
    """T9 (AC1): two entries, and exactly one carries the "Dr " title."""
    processor = DocumentProcessor(db_path=db_path, passphrase=PASSPHRASE)
    previews = processor.build_pseudonym_previews(_preview_pair(order))

    assert len(previews) == 2
    assert sorted(value.startswith("Dr ") for value in previews.values()) == [
        False,
        True,
    ]
