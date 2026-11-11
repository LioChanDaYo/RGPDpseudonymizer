"""Story 11.6: the pseudonym libraries hold each name once, in one list
(T19, T20, T23; AC14, AC16; Lionel's decisions of 2026-11-10).

Written by the BMAD dev agent (Claude). Values are compared folded
(``core.custom_pseudonym.fold``: capitals and accents ignored, repeated
spaces as one). An assertion names the lists of a duplicate, never its
value. Code placeholders only (« Name000 », « Last000 »...).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gdpr_pseudonymizer.core.custom_pseudonym import fold
from gdpr_pseudonymizer.pseudonym.library_manager import (
    LibraryBasedPseudonymManager,
)

REPO = Path(__file__).resolve().parents[2]
PACKAGE_LIBRARIES = REPO / "gdpr_pseudonymizer" / "resources" / "pseudonyms"
DATA_LIBRARIES = REPO / "data" / "pseudonyms"
THEMES = ["neutral", "star_wars", "lotr"]


def _lists(library: dict[str, Any]) -> Iterator[tuple[str, list[str]]]:
    """Every list of a library, with its label."""
    for gender in ("male", "female", "neutral"):
        yield f"first_names.{gender}", library["first_names"][gender]
    yield "last_names", library["last_names"]
    for category, values in library["locations"].items():
        yield f"locations.{category}", values
    for category, values in library["organizations"].items():
        yield f"organizations.{category}", values


@pytest.mark.parametrize("theme", THEMES)
def test_no_duplicate_in_pseudonym_library(theme: str) -> None:
    """T19 (AC14): no two entries of a library fold alike, within a list or
    across the first names, last names, places and organisations."""
    library = json.loads((PACKAGE_LIBRARIES / f"{theme}.json").read_text("utf-8"))
    first_list: dict[str, str] = {}
    duplicates: list[tuple[str, str]] = []
    for label, values in _lists(library):
        for value in values:
            key = fold(value)
            if key in first_list:
                duplicates.append((first_list[key], label))
            else:
                first_list[key] = label
    assert not duplicates, (  # expected failure
        f"{len(duplicates)} folded duplicates; the first between "
        f"{duplicates[0][0]} and {duplicates[0][1]}"
    )


@pytest.mark.parametrize("theme", THEMES)
def test_pseudonym_library_copies_identical(theme: str) -> None:
    """T20 (a control; AC14): the two copies of each library are
    byte-identical."""
    package = (PACKAGE_LIBRARIES / f"{theme}.json").read_bytes()
    data = (DATA_LIBRARIES / f"{theme}.json").read_bytes()
    assert package == data


def test_library_floor_counts_distinct_names(tmp_path: Path) -> None:
    """T23 (AC16): 500 last-name entries of which 499 are distinct do not
    meet the floor of 500 last names."""
    names = [f"Name{index:03d}" for index in range(600)]
    last_names = [f"Last{index:03d}" for index in range(499)] + ["Last000"]
    library = {
        "theme": "distinct",
        "data_sources": [],
        "first_names": {"male": names[:300], "female": names[300:], "neutral": []},
        "last_names": last_names,
        "locations": {
            "cities": [f"City{index:02d}" for index in range(50)],
            "countries": [f"Country{index:02d}" for index in range(20)],
            "regions": [f"Region{index:02d}" for index in range(10)],
        },
        "organizations": {
            "companies": [f"Company{index:02d}" for index in range(20)],
            "agencies": [f"Agency{index:02d}" for index in range(10)],
            "institutions": [f"Institution{index:02d}" for index in range(5)],
        },
    }
    path = tmp_path / "pseudonyms" / "distinct.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(library), encoding="utf-8")
    manager = LibraryBasedPseudonymManager()
    refused: str | None = None
    # try/except, not pytest.raises: on the unfixed code pytest.raises would
    # fail with pytest's Failed, which strict xfail(raises=AssertionError)
    # reports as a plain failure (PO v1.8)
    with patch("gdpr_pseudonymizer.resources.PSEUDONYMS_DIR", tmp_path / "pseudonyms"):
        try:
            manager.load_library("distinct")
        except ValueError as error:
            refused = str(error)
    assert refused is not None, "loaded"  # expected failure
    assert "Insufficient last names" in refused, refused
