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
            {
                "entity_type": "ORG",
                "source": "spacy",
                "reason": "role_acronym",
                "places_emitted": 0,
            },
            {
                "entity_type": "ORG",
                "source": "regex",
                "reason": "vp_form",
                "places_emitted": 1,
            },
        ]


class TestRoleFilterKeepsPlace:
    """Lionel, PR #81 review: a dropped "VP + place" keeps the place."""

    def test_vp_region_emits_location(self, detector: HybridDetector) -> None:
        doc = "Notre VP Europe arrive."
        role = _ent("VP Europe", "ORG", 6, "spacy")
        merged = detector._merge_entities([role], [], doc)
        assert [(e.text, e.entity_type, e.start_pos, e.end_pos) for e in merged] == [
            ("Europe", "LOCATION", 9, 15)
        ]
        assert doc[9:15] == "Europe"

    def test_vp_function_emits_nothing(self, detector: HybridDetector) -> None:
        role = _ent("VP Engineering", "ORG", 0, "spacy")
        assert detector._merge_entities([role], [], "VP Engineering") == []

    def test_role_acronym_emits_nothing(self, detector: HybridDetector) -> None:
        assert detector._merge_entities([_ent("CTO", "ORG", 0)], [], "CTO") == []

    def test_invented_region_from_geography_emitted(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(hd, "_load_geography_region_words", lambda: ["Zorbalie"])
        load_org_role_filter.cache_clear()
        doc = "VP Ventes Zorbalie"
        merged = detector._merge_entities([_ent(doc, "ORG", 0, "regex")], [], doc)
        assert [(e.text, e.entity_type, e.start_pos) for e in merged] == [
            ("Zorbalie", "LOCATION", 10)
        ]
        assert merged[0].source == "regex"

    def test_places_joined_by_de_form_one_place(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            hd, "_load_geography_region_words", lambda: ["Zorbalie", "Quentrie"]
        )
        load_org_role_filter.cache_clear()
        doc = "VP Zorbalie du Nord et Quentrie"
        merged = detector._merge_entities([_ent(doc, "ORG", 0, "spacy")], [], doc)
        assert [e.text for e in merged] == ["Zorbalie du Nord", "Quentrie"]
        assert all(e.entity_type == "LOCATION" for e in merged)

    def test_place_offsets_follow_document_whitespace(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(hd, "_load_geography_region_words", lambda: ["Zorbalie"])
        load_org_role_filter.cache_clear()
        doc = "VP  Sales\nZorbalie"
        # entity text whitespace-normalized, as some regex matches are
        role = _ent("VP Sales Zorbalie", "ORG", 0, "regex", end=len(doc))
        merged = detector._merge_entities([], [role], doc)
        assert [(e.text, e.start_pos, e.end_pos) for e in merged] == [
            ("Zorbalie", 10, 18)
        ]

    def test_place_never_matched_inside_a_longer_word(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # QA REL-001: invented lower-case region "ente" also occurs inside
        # "Ventes"; the emitted span must be the standalone word.
        monkeypatch.setattr(hd, "_load_geography_region_words", lambda: ["ente"])
        load_org_role_filter.cache_clear()
        doc = "VP Ventes ente"
        merged = detector._merge_entities([_ent(doc, "ORG", 0, "spacy")], [], doc)
        assert [(e.text, e.start_pos, e.end_pos) for e in merged] == [("ente", 10, 14)]

    def test_adjacent_places_without_connector_are_separate(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # QA REQ-002: only de/du/des/d' join places.
        monkeypatch.setattr(
            hd, "_load_geography_region_words", lambda: ["Zorbalie", "Quentrie"]
        )
        load_org_role_filter.cache_clear()
        doc = "VP Zorbalie Quentrie"
        merged = detector._merge_entities([_ent(doc, "ORG", 0, "spacy")], [], doc)
        assert [e.text for e in merged] == ["Zorbalie", "Quentrie"]

    def test_emitted_place_deduplicated_with_existing_location(
        self, detector: HybridDetector
    ) -> None:
        doc = "VP Europe"
        role = _ent("VP Europe", "ORG", 0, "spacy")
        place = _ent("Europe", "LOCATION", 3, "regex")
        merged = detector._merge_entities([role], [place], doc)
        assert [(e.text, e.entity_type) for e in merged] == [("Europe", "LOCATION")]


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


# ---------------------------------------------------------------------------
# Same-type overlap dedup (AC1, AC2)
# ---------------------------------------------------------------------------

DEDUP_FIELDS = {
    "entity_type",
    "reason",
    "kept_source",
    "dropped_source",
    "kept_start",
    "kept_end",
    "dropped_start",
    "dropped_end",
}


class TestSameTypeDedup:
    def test_containment_spacy_short_inside_regex_long(
        self, detector: HybridDetector
    ) -> None:
        short = _ent("Zorbalia", "PERSON", 0, "spacy")
        long = _ent("Zorbalia Quentin", "PERSON", 0, "regex")
        assert detector._merge_entities([short], [long]) == [long]

    def test_containment_regex_short_inside_spacy_long(
        self, detector: HybridDetector
    ) -> None:
        long = _ent("Zorbalia Quentin", "PERSON", 0, "spacy")
        short = _ent("Quentin", "PERSON", 9, "regex")
        assert detector._merge_entities([long], [short]) == [long]

    def test_partial_overlap_spacy_vs_regex_emits_union(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Zorbalia Quentin Vardel"
        spacy_e = _ent("Zorbalia Quentin", "PERSON", 0, "spacy")
        regex_e = _ent("Quentin Vardel", "PERSON", 9, "regex")
        merged = detector._merge_entities([spacy_e], [regex_e], doc)
        assert [(e.text, e.start_pos, e.end_pos, e.source) for e in merged] == [
            ("Zorbalia Quentin Vardel", 0, 23, "merged")
        ]
        assert merged[0].entity_type == "PERSON"
        assert merged[0].is_ambiguous is False
        assert log.named("ambiguous_entity_added") == []
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"partial_overlap_union"}

    def test_partial_overlap_regex_vs_regex_emits_union(
        self, detector: HybridDetector
    ) -> None:
        a = _ent("Zorbalia Quentin", "PERSON", 0)
        b = _ent("Quentin Vardelmorr", "PERSON", 9)
        merged = detector._merge_entities([], [a, b])
        assert [(e.text, e.start_pos, e.end_pos) for e in merged] == [
            ("Zorbalia Quentin Vardelmorr", 0, 27)
        ]

    def test_union_text_is_sliced_from_the_document(
        self, detector: HybridDetector
    ) -> None:
        doc = "Zorbalia  Quentin\tVardel"
        # regex text whitespace-normalized; the union must use the document
        a = _ent("Zorbalia Quentin", "PERSON", 0, "regex", end=17)
        b = _ent("Quentin Vardel", "PERSON", 10, "regex", end=24)
        merged = detector._merge_entities([], [a, b], doc)
        assert merged[0].text == doc[0:24]

    def test_same_source_tie_keeps_earliest_start(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        # Equal cores ("Zorb"), equal raw length, both regex → earliest start.
        a = _ent("Dr Zorb", "PERSON", 0)
        b = _ent("Zorb Me", "PERSON", 3)
        assert detector._merge_entities([], [b, a]) == [a]
        assert log.named("same_type_overlap_resolved")[0]["reason"] == "tie"

    def test_title_variant_is_a_tie_longer_raw_span_kept(
        self, detector: HybridDetector
    ) -> None:
        titled = _ent("Dr Zorbalia Quentin", "PERSON", 0)
        bare = _ent("Zorbalia Quentin", "PERSON", 3)
        assert detector._merge_entities([], [bare, titled]) == [titled]

    def test_preposition_variant_location_is_a_tie(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        with_prep = _ent("à Zorbaville", "LOCATION", 10)
        bare = _ent("Zorbaville", "LOCATION", 12)
        assert detector._merge_entities([], [bare, with_prep]) == [with_prep]
        assert log.named("same_type_overlap_resolved")[0]["reason"] == "tie"

    def test_preposition_rule_does_not_apply_to_person(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        # "à" is not stripped from PERSON: this is containment, not a tie.
        with_prep = _ent("à Quentin", "PERSON", 0)
        bare = _ent("Quentin", "PERSON", 2)
        detector._merge_entities([], [with_prep, bare])
        assert log.named("same_type_overlap_resolved")[0]["reason"] != "tie"

    def test_different_types_partial_overlap_untouched(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        person = _ent("Zorbalia Quentin", "PERSON", 0, "spacy")
        org = _ent("Quentin Holding", "ORG", 9, "regex")
        merged = detector._merge_entities([person], [org])
        assert merged == [person, org]
        assert org.is_ambiguous is True
        assert [e["reason"] for e in log.named("ambiguous_entity_added")] == [
            "partial_overlap"
        ]
        assert log.named("same_type_overlap_resolved") == []

    def test_location_nested_in_org_keeps_both(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        org = _ent("Quentrix Zorbaville", "ORG", 0, "spacy")
        place = _ent("Zorbaville", "LOCATION", 9, "regex")
        assert detector._merge_entities([org], [place]) == [org, place]
        assert log.named("same_type_overlap_resolved") == []

    def test_cores_disjoint_keeps_both(self, detector: HybridDetector) -> None:
        # Raw spans touch only through the title: cores are disjoint.
        a = _ent("Quentin Mme", "PERSON", 0, end=11)
        b = _ent("Mme Zorbalia", "PERSON", 8)
        assert detector._merge_entities([], [a, b]) == [a, b]

    def test_chain_a_in_b_b_partial_c(self, detector: HybridDetector) -> None:
        # A ⊂ B, B partially overlaps C. Walk order B, C, A: B and C become
        # their union, which then contains A.
        doc = "Zorbalia Quentin Vardel"
        a = _ent("Quentin", "PERSON", 9, "regex")
        b = _ent("Zorbalia Quentin", "PERSON", 0, "spacy")
        c = _ent("Quentin Vardel", "PERSON", 9, "regex")
        merged = detector._merge_entities([b], [a, c], doc)
        assert [(e.text, e.source) for e in merged] == [
            ("Zorbalia Quentin Vardel", "merged")
        ]

    def test_c1_lowercase_prefix_keeps_inner(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        outer = _ent("près de Zorbaville", "LOCATION", 0, "regex")
        inner = _ent("Zorbaville", "LOCATION", 8, "spacy")
        assert detector._merge_entities([inner], [outer]) == [inner]
        assert log.named("same_type_overlap_resolved")[0]["reason"] == (
            "containment_inner_preferred"
        )

    def test_c1_digit_token_keeps_outer(self, detector: HybridDetector) -> None:
        outer = _ent("Zorbaville 3ème", "LOCATION", 0, "regex")
        inner = _ent("Zorbaville", "LOCATION", 0, "spacy")
        assert detector._merge_entities([inner], [outer]) == [outer]

    def test_c1_uppercase_token_keeps_outer(self, detector: HybridDetector) -> None:
        outer = _ent("Zorbalia Quentin", "PERSON", 0, "regex")
        inner = _ent("Zorbalia", "PERSON", 0, "spacy")
        assert detector._merge_entities([inner], [outer]) == [outer]

    def test_c2_outer_trimmed_at_line_break(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Zorbalia Quentin Vardel\nDirectrice"
        outer = _ent(doc, "PERSON", 0, "spacy")
        inner = _ent("Zorbalia Quentin", "PERSON", 0, "regex")
        merged = detector._merge_entities([outer], [inner], doc)
        assert [(e.text, e.start_pos, e.end_pos, e.source) for e in merged] == [
            ("Zorbalia Quentin Vardel", 0, 23, "spacy")
        ]
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"containment_outer_trimmed_linebreak"}

    def test_c2_trim_drops_trailing_spaces(self, detector: HybridDetector) -> None:
        doc = "Zorbalia Quentin  \nRapport"
        outer = _ent(doc, "PERSON", 0, "spacy")
        inner = _ent("Quentin", "PERSON", 9, "regex")
        merged = detector._merge_entities([outer], [inner], doc)
        assert [(e.text, e.end_pos) for e in merged] == [("Zorbalia Quentin", 16)]

    def test_c2_falls_back_to_normal_rules(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        # The line break comes before the inner span: the trimmed outer
        # ("Rapport") no longer contains it, so containment keeps the outer.
        doc = "Rapport\nZorbalia Quentin"
        outer = _ent(doc, "PERSON", 0, "spacy")
        inner = _ent("Zorbalia Quentin", "PERSON", 8, "regex")
        assert detector._merge_entities([outer], [inner], doc) == [outer]
        assert log.named("same_type_overlap_resolved")[0]["reason"] == "containment"

    def test_dedup_log_fields_and_no_entity_text(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        long = _ent("Zorbalia Quentin", "PERSON", 0, "spacy")
        short = _ent("Quentin", "PERSON", 9, "regex")
        detector._merge_entities([long], [short])
        (event,) = log.named("same_type_overlap_resolved")
        assert set(event) == DEDUP_FIELDS
        assert event == {
            "entity_type": "PERSON",
            "reason": "containment",
            "kept_source": "spacy",
            "dropped_source": "regex",
            "kept_start": 0,
            "kept_end": 16,
            "dropped_start": 9,
            "dropped_end": 16,
        }

    def test_invariant_no_same_type_overlapping_cores(
        self, detector: HybridDetector
    ) -> None:
        import random

        rng = random.Random(102)
        words = ["Zorbalia", "Quentin", "Vardel", "Mme", "à", "près", "de", "x"]
        for _ in range(300):
            spacy_list: list[DetectedEntity] = []
            regex_list: list[DetectedEntity] = []
            for _ in range(rng.randint(1, 6)):
                text = " ".join(rng.choice(words) for _ in range(rng.randint(1, 3)))
                start = rng.randint(0, 20)
                etype = rng.choice(["PERSON", "LOCATION", "ORG"])
                source = rng.choice(["spacy", "regex"])
                e = _ent(text, etype, start, source)
                (spacy_list if source == "spacy" else regex_list).append(e)
            merged = detector._merge_entities(spacy_list, regex_list)
            for i, e1 in enumerate(merged):
                for e2 in merged[i + 1 :]:
                    if e1.entity_type != e2.entity_type:
                        continue
                    if not (e1.start_pos < e2.end_pos and e2.start_pos < e1.end_pos):
                        continue
                    c1, c2 = detector._dedup_core(e1), detector._dedup_core(e2)
                    assert not (c1[0] < c2[1] and c2[0] < c1[1]), (e1, e2)

    def test_invariant_dedup_never_uncovers_name_characters(
        self, detector: HybridDetector
    ) -> None:
        """Coverage invariant (Lionel, PR #81 review), on random overlaps.

        Every character that carries a name (an upper-case letter or a digit
        inside an input entity's normalized core) stays covered by an output
        entity of the same type. Documents have no line break here; the C2
        trim is covered by its own tests. C1 only drops tokens without an
        upper-case letter or digit, so it never uncovers such a character.
        """
        import random

        rng = random.Random(81)
        words = ["Zorbalia", "Quentin", "Vardel", "Morrix", "à", "de", "près", "x7"]
        for _ in range(400):
            tokens = [rng.choice(words) for _ in range(rng.randint(3, 9))]
            doc = " ".join(tokens)
            starts = [0]
            for tok in tokens[:-1]:
                starts.append(starts[-1] + len(tok) + 1)
            entities: list[DetectedEntity] = []
            for _ in range(rng.randint(2, 6)):
                i = rng.randrange(len(tokens))
                j = rng.randint(i + 1, min(len(tokens), i + 4))
                start = starts[i]
                end = starts[j - 1] + len(tokens[j - 1])
                entities.append(
                    _ent(
                        doc[start:end],
                        rng.choice(["PERSON", "LOCATION"]),
                        start,
                        rng.choice(["spacy", "regex"]),
                    )
                )
            out = detector._dedup_same_type_overlaps(list(entities), doc)
            for e in entities:
                c0, c1 = detector._dedup_core(e)
                for pos in range(c0, c1):
                    if not (doc[pos].isupper() or doc[pos].isdigit()):
                        continue
                    assert any(
                        k.entity_type == e.entity_type
                        and k.start_pos <= pos < k.end_pos
                        for k in out
                    ), (doc, e, out)

    def test_large_input_uses_an_active_window(self, detector: HybridDetector) -> None:
        """QA PERF-001: the walk scales linearly, not quadratically.

        Pairs of overlapping same-type entities along a long document. Going
        from 1,500 to 6,000 pairs (4x) costs about 4x with the active window
        and about 16x with a full scan of the kept list. The ratio is used
        instead of an absolute time, so slow or instrumented CI legs do not
        make the test flaky.
        """
        import time

        def run(pairs: int) -> float:
            entities: list[DetectedEntity] = []
            for i in range(pairs):
                base = i * 40
                entities.append(_ent("Zorbalia Quentin", "PERSON", base, "spacy"))
                entities.append(_ent("Quentin", "PERSON", base + 9, "regex"))
            start = time.perf_counter()
            out = detector._dedup_same_type_overlaps(entities)
            elapsed = time.perf_counter() - start
            assert len(out) == pairs
            assert all(e.text == "Zorbalia Quentin" for e in out)
            return elapsed

        run(500)  # warm-up
        small = min(run(1_500) for _ in range(2))
        large = min(run(6_000) for _ in range(2))
        assert large / small < 10, (small, large)

    def test_window_keeps_rechecking_retired_entities_after_a_union(
        self, detector: HybridDetector
    ) -> None:
        """A union that starts before the walk position is compared again
        with retired entities that reach into it (same result as a full scan).
        """
        doc = "Zorbalia Quentin Vardel Morrix"
        a = _ent("Zorbalia Quentin", "PERSON", 0, "spacy")  # [0, 16)
        b = _ent("Quentin Vardel", "PERSON", 9, "regex")  # [9, 23) partial with a
        c = _ent("Vardel Morrix", "PERSON", 17, "regex")  # [17, 30) partial with b
        out = detector._dedup_same_type_overlaps([a, b, c], doc)
        assert [(e.text, e.start_pos, e.end_pos) for e in out] == [
            ("Zorbalia Quentin Vardel Morrix", 0, 30)
        ]


class TestOrgSegmentTrim:
    """V3 (Lionel 2026-10-04) with its guard (Lionel 2026-10-05).

    ORG spans are cut at clause boundaries, but a cut may only discard text
    with no capitalised word; titles and sentence-start words are excepted.
    """

    @staticmethod
    def _contain(
        detector: HybridDetector, doc: str, inner_text: str
    ) -> list[DetectedEntity]:
        outer = _ent(doc, "ORG", 0, "regex")
        inner = _ent(inner_text, "ORG", doc.index(inner_text), "spacy")
        return detector._merge_entities([inner], [outer], doc)

    @pytest.mark.parametrize(
        ("doc", "kept"),
        [
            ("Quentrix SA, lot 42", "Quentrix SA"),  # comma
            ("Quentrix SA; lot 42", "Quentrix SA"),  # semicolon
            ("Quentrix SA: lot 42", "Quentrix SA"),  # colon
            ("le lot 42 est prêt. Quentrix SA", "Quentrix SA"),  # sentence period
        ],
    )
    def test_each_boundary_kind_cuts_the_outer_org(
        self, detector: HybridDetector, log: _LogRecorder, doc: str, kept: str
    ) -> None:
        merged = self._contain(detector, doc, "Quentrix SA")
        assert [(e.text, e.start_pos) for e in merged] == [(kept, doc.index(kept))]
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"containment_outer_trimmed_boundary"}

    def test_line_break_keeps_the_c2_trim(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        # The V3 cut would discard "Rapport" (capitalised): the guard falls
        # back to the run-C behaviour, here the C2 trim at the line break.
        merged = self._contain(detector, "Quentrix SA\nRapport annuel", "Quentrix SA")
        assert [e.text for e in merged] == ["Quentrix SA"]
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"containment_outer_trimmed_linebreak"}

    @pytest.mark.parametrize(
        "doc",
        [
            "Contact Dr. Quentrix SA",  # title before the period
            "Groupe QTX. Quentrix SA",  # all-caps word before the period
            "Le no. Quentrix SA",  # word shorter than three letters
        ],
    )
    def test_period_guard_keeps_the_outer_org(
        self, detector: HybridDetector, doc: str
    ) -> None:
        assert [e.text for e in self._contain(detector, doc, "Quentrix SA")] == [doc]

    @pytest.mark.parametrize("abbrev", ["Corp.", "Inc.", "Cie.", "Ltd.", "Co."])
    def test_abbreviation_period_is_not_a_sentence_end(
        self, detector: HybridDetector, abbrev: str
    ) -> None:
        # REL-002: a capitalised word of at most 4 letters + "." + a
        # capitalised word is an abbreviation; the name stays whole.
        doc = f"Zorb {abbrev} Holding Quentrix"
        merged = self._contain(detector, doc, "Holding Quentrix")
        assert [e.text for e in merged] == [doc]

    def test_list_of_orgs_keeps_all_names_covered(
        self, detector: HybridDetector
    ) -> None:
        # QA V3-001 / Lionel's guard: only one name is detected on its own;
        # the cut would discard the other two, so it is refused.
        doc = "Quentrix SA, Zorbalia Conseil, et Vardel Group"
        merged = self._contain(detector, doc, "Zorbalia Conseil")
        assert [e.text for e in merged] == [doc]
        for name in ("Quentrix SA", "Zorbalia Conseil", "Vardel Group"):
            pos = doc.index(name)
            assert any(e.start_pos <= pos < e.end_pos for e in merged), name

    def test_signature_block_is_not_cut(self, detector: HybridDetector) -> None:
        doc = "Cordialement,\n\nZorbalia Quentin\nDirectrice\nQuentrix SA"
        merged = self._contain(detector, doc, "Quentrix SA")
        pos = doc.index("Zorbalia")
        assert any(e.start_pos <= pos < e.end_pos for e in merged)

    def test_title_is_not_a_name(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Quentrix SA à Zorbaville, notamment le Dr"
        merged = self._contain(detector, doc, "Quentrix SA")
        assert [e.text for e in merged] == ["Quentrix SA à Zorbaville"]
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"containment_outer_trimmed_boundary"}

    def test_sentence_start_word_may_be_discarded(
        self, detector: HybridDetector
    ) -> None:
        doc = "Quentrix SA fournit. Merci"
        merged = self._contain(detector, doc, "Quentrix SA")
        assert [e.text for e in merged] == ["Quentrix SA fournit"]

    def test_guard_fallback_keeps_the_run_c_result(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Quentrix SA, Zorbalia Conseil"
        merged = self._contain(detector, doc, "Zorbalia Conseil")
        assert [e.text for e in merged] == [doc]
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"containment"}

    def test_union_trimmed_at_a_boundary(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Quentrix Holding SA, siège 12"
        regex_e = _ent("Quentrix Holding SA", "ORG", 0, "regex")
        spacy_e = _ent("Holding SA, siège 12", "ORG", 9, "spacy")
        merged = detector._merge_entities([spacy_e], [regex_e], doc)
        assert [(e.text, e.start_pos, e.source) for e in merged] == [
            ("Quentrix Holding SA", 0, "merged")
        ]
        reasons = {e["reason"] for e in log.named("same_type_overlap_resolved")}
        assert reasons == {"partial_overlap_union_trimmed"}

    def test_union_cut_refused_when_it_drops_a_name(
        self, detector: HybridDetector
    ) -> None:
        doc = "Quentrix Holding SA\nSiège Zorbaville"
        regex_e = _ent("Quentrix Holding SA", "ORG", 0, "regex")
        spacy_e = _ent("Holding SA\nSiège Zorbaville", "ORG", 9, "spacy")
        merged = detector._merge_entities([spacy_e], [regex_e], doc)
        assert [e.text for e in merged] == [doc]

    def test_person_last_first_is_not_cut(self, detector: HybridDetector) -> None:
        doc = "Quentin, Zorbalia"
        outer = _ent(doc, "PERSON", 0, "regex")
        inner = _ent("Zorbalia", "PERSON", 9, "spacy")
        merged = detector._merge_entities([inner], [outer], doc)
        assert [e.text for e in merged] == ["Quentin, Zorbalia"]

    def test_location_is_not_cut(self, detector: HybridDetector) -> None:
        doc = "Zorbaville, Quentrie"
        outer = _ent(doc, "LOCATION", 0, "regex")
        inner = _ent("Quentrie", "LOCATION", 12, "spacy")
        merged = detector._merge_entities([inner], [outer], doc)
        assert [e.text for e in merged] == [doc]

    def test_anchor_crossing_a_boundary_is_not_cut(
        self, detector: HybridDetector
    ) -> None:
        doc = "Groupe Quentrix, Zorbalia et associés"
        merged = self._contain(detector, doc, "Quentrix, Zorbalia")
        assert [e.text for e in merged] == [doc]

    def test_former_gap_chain_cut_keeps_absorbed_name(
        self, detector: HybridDetector
    ) -> None:
        # Was a strict xfail (known V3 gap); fixed by the guard.
        doc = "Groupe, Quentrix, Zorbalia Conseil"
        outer = _ent(doc, "ORG", 0, "regex")
        absorbed = _ent("Groupe, Quentrix", "ORG", 0, "spacy")
        later = _ent("Zorbalia Conseil", "ORG", 18, "spacy")
        out = detector._dedup_same_type_overlaps([outer, absorbed, later], doc)
        q = doc.index("Quentrix")
        assert any(k.start_pos <= q < k.end_pos for k in out)

    def test_former_gap_union_cut_keeps_a_name(self, detector: HybridDetector) -> None:
        # Was a strict xfail (known V3 gap); fixed by the guard.
        doc = "Quentrix, Zorbalia Group"
        a = _ent("Quentrix, Zorbalia", "ORG", 0, "regex")
        b = _ent("Zorbalia Group", "ORG", 10, "spacy")
        out = detector._dedup_same_type_overlaps([a, b], doc)
        assert any(k.start_pos <= 0 < k.end_pos for k in out)

    def test_invariant_v3_never_uncovers_a_capital_letter(
        self, detector: HybridDetector
    ) -> None:
        """Random ORG overlaps with clause punctuation (no line break, no
        period): every upper-case letter inside an input core stays covered
        by an ORG output span. Exercises containment, C1, union and the
        guarded V3 cut and union cut."""
        import random

        rng = random.Random(5)
        words = ["Quentrix", "SA", "Zorbalia", "Group", "et", "notre", "lot", "x9"]
        seps = [" ", " ", ", ", "; ", ": "]
        for _ in range(500):
            tokens = [rng.choice(words) for _ in range(rng.randint(3, 8))]
            doc = tokens[0]
            starts = [0]
            for tok in tokens[1:]:
                doc += rng.choice(seps)
                starts.append(len(doc))
                doc += tok
            entities: list[DetectedEntity] = []
            for _ in range(rng.randint(2, 5)):
                i = rng.randrange(len(tokens))
                j = rng.randint(i + 1, min(len(tokens), i + 4))
                start, end = starts[i], starts[j - 1] + len(tokens[j - 1])
                entities.append(
                    _ent(doc[start:end], "ORG", start, rng.choice(["spacy", "regex"]))
                )
            out = detector._dedup_same_type_overlaps(list(entities), doc)
            for e in entities:
                c0, c1 = detector._dedup_core(e)
                for pos in range(c0, c1):
                    if doc[pos].isupper():
                        assert any(k.start_pos <= pos < k.end_pos for k in out), (
                            doc,
                            e,
                            out,
                        )
