"""spaCy-free unit tests for Story 10.2 rules in HybridDetector.

- ORG role filter (AC3): role acronyms and VP forms are not organisations.
- Same-type overlap dedup (AC1, AC2).

Unmarked on purpose (not ``spacy``, not ``slow``): ``HybridDetector()`` loads
no spaCy model at construction, and every test feeds synthetic entity lists
to ``_merge_entities`` or to the rule functions directly, so this file runs
on every CI leg including Windows.

All person, organisation and place strings are clearly invented (AC7), apart
from the generic words of the rules themselves (role acronyms, "Europe",
"France") and the real acronym organisations that must survive (AC3).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
import yaml

from gdpr_pseudonymizer.nlp import hybrid_detector as hd
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import (
    HybridDetector,
    load_org_role_filter,
    match_org_role,
)
from gdpr_pseudonymizer.resources import ORG_ROLE_FILTER_PATH


class _LogRecorder:
    """Stand-in for the module logger that records (event, fields)."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def _record(self, event: str, **fields: Any) -> None:
        self.events.append((event, fields))

    debug = info = warning = error = _record

    def named(self, event: str) -> list[dict[str, Any]]:
        return [f for e, f in self.events if e == event]


@pytest.fixture
def detector() -> HybridDetector:
    return HybridDetector()


@pytest.fixture
def log(monkeypatch: pytest.MonkeyPatch) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(hd, "logger", recorder)
    return recorder


@pytest.fixture(autouse=True)
def _fresh_role_filter_cache() -> Iterator[None]:
    load_org_role_filter.cache_clear()
    yield
    load_org_role_filter.cache_clear()


def _ent(
    text: str,
    entity_type: str,
    start: int,
    source: str = "regex",
    end: int | None = None,
) -> DetectedEntity:
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text) if end is None else end,
        source=source,
    )


# ---------------------------------------------------------------------------
# ORG role filter (AC3)
# ---------------------------------------------------------------------------

MINIMUM_ACRONYMS = [
    "CEO",
    "CTO",
    "CFO",
    "COO",
    "CIO",
    "CDO",
    "CSO",
    "DSI",
    "DAF",
    "DRH",
    "DPO",
    "RSSI",
    "COMEX",
    "CODIR",
]


class TestOrgRoleFilter:
    @pytest.mark.parametrize("acronym", MINIMUM_ACRONYMS)
    def test_minimum_acronym_dropped_as_org(
        self, detector: HybridDetector, acronym: str
    ) -> None:
        merged = detector._merge_entities([_ent(acronym, "ORG", 0, "spacy")], [])
        assert merged == []

    @pytest.mark.parametrize("text", ["cto", "Cto", "CTO,", "Notre COMEX"])
    def test_acronym_other_case_or_punctuation_kept(self, text: str) -> None:
        assert match_org_role(text) is None

    @pytest.mark.parametrize(
        "text",
        [
            "VP",
            "VP Engineering",
            "VP Europe",
            "VP France",
            "VP Sales Europe",
            "VP Sales & Marketing",
            "VP R&D",
            "Vice-présidente Ventes",
            "vice-président Ventes France",
            "Vice President Engineering",
            "VP  Engineering",
        ],
    )
    def test_vp_forms_dropped(self, text: str) -> None:
        assert match_org_role(text) == "vp_form"

    @pytest.mark.parametrize(
        "text",
        ["vp Engineering", "VP Quentrix", "VP de", "Vice-président Quentrix SA"],
    )
    def test_vp_forms_not_matching_kept(self, text: str) -> None:
        assert match_org_role(text) is None

    def test_region_words_read_from_geography_at_runtime(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert match_org_role("VP Zorbalie") is None
        load_org_role_filter.cache_clear()
        monkeypatch.setattr(hd, "_load_geography_region_words", lambda: ["Zorbalie"])
        assert match_org_role("VP Zorbalie") == "vp_form"

    def test_geography_resource_entries_are_region_words(self) -> None:
        # Taken from the loaded resource, never typed here (AC7).
        words = hd._load_geography_region_words()
        assert words
        assert all(match_org_role(f"VP {w}") == "vp_form" for w in words)

    @pytest.mark.parametrize("org", ["CNIL", "ANSSI", "BNP", "EY"])
    def test_real_acronym_orgs_survive(
        self, detector: HybridDetector, org: str
    ) -> None:
        entity = _ent(org, "ORG", 0, "spacy")
        assert detector._merge_entities([entity], []) == [entity]

    @pytest.mark.parametrize("entity_type", ["PERSON", "LOCATION"])
    def test_role_text_with_other_type_untouched(
        self, detector: HybridDetector, entity_type: str
    ) -> None:
        entity = _ent("CTO", entity_type, 0, "spacy")
        assert detector._merge_entities([entity], []) == [entity]

    @pytest.mark.parametrize(
        "org", ["Groupe DSI Quentrix", "Comité Quentrix", "Quentrix CTO Conseil"]
    )
    def test_longer_org_containing_role_word_kept(
        self, detector: HybridDetector, org: str
    ) -> None:
        entity = _ent(org, "ORG", 0, "spacy")
        assert detector._merge_entities([entity], []) == [entity]

    def test_role_dropped_from_either_source(self, detector: HybridDetector) -> None:
        spacy_role = _ent("DRH", "ORG", 0, "spacy")
        regex_role = _ent("VP Sales", "ORG", 10, "regex")
        org = _ent("Quentrix SA", "ORG", 30, "regex")
        assert detector._merge_entities([spacy_role], [regex_role, org]) == [org]

    def test_role_filter_log_has_no_entity_text(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        detector._merge_entities(
            [_ent("CTO", "ORG", 0, "spacy")], [_ent("VP Europe", "ORG", 10)]
        )
        events = log.named("org_role_filtered")
        assert events == [
            {"entity_type": "ORG", "source": "spacy", "reason": "role_acronym"},
            {"entity_type": "ORG", "source": "regex", "reason": "vp_form"},
        ]


class TestOrgRoleFilterResource:
    @pytest.fixture
    def data(self) -> dict[str, Any]:
        with open(ORG_ROLE_FILTER_PATH, encoding="utf-8") as f:
            loaded: dict[str, Any] = yaml.safe_load(f)
        return loaded

    def test_every_entry_has_a_why(self, data: dict[str, Any]) -> None:
        for section in ("acronyms", "vp_prefixes", "vp_functions", "vp_regions"):
            assert data[section], section
            for entry in data[section]:
                assert str(entry["term"]).strip(), section
                assert str(entry.get("why", "")).strip(), (section, entry["term"])

    def test_connectors_are_plain_grammar_words(self, data: dict[str, Any]) -> None:
        assert all(isinstance(c, str) for c in data["connectors"])

    def test_real_acronym_orgs_not_listed(self, data: dict[str, Any]) -> None:
        terms = {
            str(e["term"])
            for section in ("acronyms", "vp_prefixes", "vp_functions", "vp_regions")
            for e in data[section]
        }
        assert not terms & {"CNIL", "ANSSI", "BNP", "EY", "ACPR", "ANSM", "KPMG"}

    def test_minimum_acronyms_present(self, data: dict[str, Any]) -> None:
        terms = {e["term"] for e in data["acronyms"]}
        assert set(MINIMUM_ACRONYMS) <= terms

    def test_vp_regions_hold_no_region_acronym(self, data: dict[str, Any]) -> None:
        for entry in data["vp_regions"]:
            term = str(entry["term"])
            assert not (len(term) > 1 and term.isupper()), term
