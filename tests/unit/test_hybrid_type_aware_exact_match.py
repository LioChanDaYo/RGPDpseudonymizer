"""spaCy-free unit tests for Story 10.3c (type-aware exact match in the merge).

Slice M, R-MX (AC1, AC4): an exact match (same span, or same text once titles
are stripped) skips the regex entity only when both detections have the same
type. With different types both are kept, the regex entity is flagged
``is_ambiguous`` and the debug event ``cross_type_exact_match`` records the
decision with types, match kind and offsets only.

Unmarked on purpose (not ``spacy``, not ``slow``): ``HybridDetector()`` loads
no spaCy model; ``_merge_entities`` gets synthetic lists and
``detect_entities`` runs with stubbed detectors. Names are invented (AC8);
the other words are generic words of the rules or main-corpus words.

Slice P, R-HYPH-FN (AC3): on a different-type exact match, a PERSON whose
title-stripped text is one hyphenated compound with no known first name is
skipped, as before 10.3c. The name dictionary is injected (monkeypatch).
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from gdpr_pseudonymizer.nlp import hybrid_detector as hd
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary

EVENT = "cross_type_exact_match"
EVENT_FIELDS = {
    "regex_type",
    "spacy_type",
    "match",
    "regex_start",
    "regex_end",
    "spacy_start",
    "spacy_end",
    "decision",
    "rule",
}


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


def _at(
    doc: str, text: str, entity_type: str, source: str, start: int | None = None
) -> DetectedEntity:
    begin = doc.index(text) if start is None else start
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=begin,
        end_pos=begin + len(text),
        source=source,
    )


def _keys(entities: list[DetectedEntity]) -> list[tuple[Any, ...]]:
    return sorted(
        (e.text, e.entity_type, e.start_pos, e.end_pos, e.source, e.is_ambiguous)
        for e in entities
    )


def _stub_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    detector: HybridDetector,
    spacy_entities: list[DetectedEntity],
    regex_entities: list[DetectedEntity],
) -> None:
    """``detect_entities`` without spaCy: both detectors return fresh copies of
    fixed lists."""
    monkeypatch.setattr(
        detector.spacy_detector,
        "detect_entities",
        lambda text: [dataclasses.replace(e) for e in spacy_entities],
    )
    monkeypatch.setattr(
        detector.regex_matcher,
        "match_entities",
        lambda text, spacy_doc=None: [dataclasses.replace(e) for e in regex_entities],
    )
    detector._model_loaded = True


def _assert_no_text(fields: dict[str, Any], *texts: str) -> None:
    assert set(fields) == EVENT_FIELDS
    assert "text" not in fields
    for value in fields.values():
        assert value not in texts
        if isinstance(value, str):
            assert not any(t in value for t in texts)


# ---------------------------------------------------------------------------
# AC4: the four cases of the epic
# ---------------------------------------------------------------------------


class TestTypeAwareExactMatch:
    def test_same_text_different_types_keeps_both(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Le siège Zorbaville pour le projet"
        spacy_org = _at(doc, "Zorbaville", "ORG", "spacy")
        regex_loc = _at(doc, "Zorbaville", "LOCATION", "regex")
        out = detector._merge_entities([spacy_org], [regex_loc], doc)
        assert _keys(out) == [
            ("Zorbaville", "LOCATION", 9, 19, "regex", True),
            ("Zorbaville", "ORG", 9, 19, "spacy", False),
        ]
        (fields,) = log.named(EVENT)
        assert fields == {
            "regex_type": "LOCATION",
            "spacy_type": "ORG",
            "match": "span",
            "regex_start": 9,
            "regex_end": 19,
            "spacy_start": 9,
            "spacy_end": 19,
            "decision": "kept_both",
            "rule": "type_aware_exact_match",
        }
        _assert_no_text(fields, "Zorbaville")
        assert log.named("duplicate_entity_removed") == []

    def test_same_span_different_types_and_texts_keeps_both(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        # _match_full_names rebuilds the text with one space; spaCy keeps the
        # raw slice (here a no-break space)
        doc = "Contact Zorbalia\u00a0Quentrel pour le projet"
        spacy_org = _at(doc, "Zorbalia\u00a0Quentrel", "ORG", "spacy")
        regex_person = dataclasses.replace(
            spacy_org, text="Zorbalia Quentrel", entity_type="PERSON", source="regex"
        )
        out = detector._merge_entities([spacy_org], [regex_person], doc)
        assert sorted((e.entity_type, e.source, e.is_ambiguous) for e in out) == [
            ("ORG", "spacy", False),
            ("PERSON", "regex", True),
        ]
        (fields,) = log.named(EVENT)
        assert fields["match"] == "span"
        _assert_no_text(fields, "Zorbalia Quentrel", "Zorbalia\u00a0Quentrel")

    def test_title_normalized_match_different_types_keeps_both(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Contact Dr Zorbalia pour le projet"
        regex_person = _at(doc, "Dr Zorbalia", "PERSON", "regex")
        spacy_org = _at(doc, "Zorbalia", "ORG", "spacy")
        out = detector._merge_entities([spacy_org], [regex_person], doc)
        assert _keys(out) == [
            ("Dr Zorbalia", "PERSON", 8, 19, "regex", True),
            ("Zorbalia", "ORG", 11, 19, "spacy", False),
        ]
        (fields,) = log.named(EVENT)
        assert fields["match"] == "normalized_text"
        assert (fields["regex_start"], fields["regex_end"]) == (8, 19)
        assert (fields["spacy_start"], fields["spacy_end"]) == (11, 19)
        _assert_no_text(fields, "Dr Zorbalia", "Zorbalia")

    def test_same_text_same_type_skips_regex_as_before(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Le siège Zorbaville pour le projet"
        spacy_loc = _at(doc, "Zorbaville", "LOCATION", "spacy")
        regex_loc = _at(doc, "Zorbaville", "LOCATION", "regex")
        out = detector._merge_entities([spacy_loc], [regex_loc], doc)
        assert _keys(out) == [("Zorbaville", "LOCATION", 9, 19, "spacy", False)]
        assert regex_loc.is_ambiguous is False
        assert len(log.named("duplicate_entity_removed")) == 1
        assert log.named(EVENT) == []

    def test_title_normalized_same_type_skips_regex_as_before(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Contact Dr Zorbalia pour le projet"
        regex_person = _at(doc, "Dr Zorbalia", "PERSON", "regex")
        spacy_person = _at(doc, "Zorbalia", "PERSON", "spacy")
        out = detector._merge_entities([spacy_person], [regex_person], doc)
        assert _keys(out) == [("Zorbalia", "PERSON", 11, 19, "spacy", False)]
        assert log.named(EVENT) == []


# ---------------------------------------------------------------------------
# The Cabinet special case and the partial-overlap branches are unchanged
# ---------------------------------------------------------------------------


class TestUnchangedBranches:
    def test_cabinet_exact_pair_keeps_both(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Document: Cabinet Zorbalia pour Quentrix"
        regex_org = _at(doc, "Cabinet Zorbalia", "ORG", "regex")
        spacy_person = _at(doc, "Cabinet Zorbalia", "PERSON", "spacy")
        out = detector._merge_entities([spacy_person], [regex_org], doc)
        assert _keys(out) == [
            ("Cabinet Zorbalia", "ORG", 10, 26, "regex", True),
            ("Cabinet Zorbalia", "PERSON", 10, 26, "spacy", False),
        ]
        assert log.named("org_supersedes_person") == []
        (fields,) = log.named(EVENT)
        assert (fields["regex_type"], fields["spacy_type"]) == ("ORG", "PERSON")
        assert fields["match"] == "span"

    def test_cabinet_normalized_text_pair_keeps_both(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Document: Cabinet Zorbalia pour Quentrix"
        spacy_person = _at(doc, "Cabinet Zorbalia", "PERSON", "spacy")
        regex_org = _at(doc, "Cabinet Zorbalia ", "ORG", "regex")
        out = detector._merge_entities([spacy_person], [regex_org], doc)
        assert sorted((e.entity_type, e.source, e.is_ambiguous) for e in out) == [
            ("ORG", "regex", True),
            ("PERSON", "spacy", False),
        ]
        assert log.named("org_supersedes_person") == []
        (fields,) = log.named(EVENT)
        assert fields["match"] == "normalized_text"

    def test_cabinet_containment_still_removes_the_person(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Document: Cabinet Zorbalia & Quentrix pour Quentrel"
        regex_org = _at(doc, "Cabinet Zorbalia & Quentrix", "ORG", "regex")
        spacy_person = _at(doc, "Cabinet Zorbalia", "PERSON", "spacy")
        out = detector._merge_entities([spacy_person], [regex_org], doc)
        assert _keys(out) == [
            ("Cabinet Zorbalia & Quentrix", "ORG", 10, 37, "regex", False)
        ]
        assert len(log.named("org_supersedes_person")) == 1
        assert log.named(EVENT) == []

    def test_different_type_partial_overlap_unchanged(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Le siège Zorbtech Zorbaville pour le projet"
        spacy_org = _at(doc, "Zorbtech Zorbaville", "ORG", "spacy")
        regex_loc = _at(doc, "Zorbaville", "LOCATION", "regex")
        out = detector._merge_entities([spacy_org], [regex_loc], doc)
        assert sorted((e.entity_type, e.source, e.is_ambiguous) for e in out) == [
            ("LOCATION", "regex", True),
            ("ORG", "spacy", False),
        ]
        (fields,) = log.named("ambiguous_entity_added")
        assert fields["reason"] == "partial_overlap"
        assert log.named(EVENT) == []

    def test_kept_candidate_still_goes_through_the_post_filters(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        # a kept regex LOCATION whose whole text is a stoplist entry is dropped
        # by _filter_location_noise, as any LOCATION would be
        doc = "Point 3: Constat pour le projet"
        spacy_org = _at(doc, "Constat", "ORG", "spacy")
        regex_loc = _at(doc, "Constat", "LOCATION", "regex")
        out = detector._merge_entities([spacy_org], [regex_loc], doc)
        assert _keys(out) == [("Constat", "ORG", 9, 16, "spacy", False)]
        assert len(log.named(EVENT)) == 1


# ---------------------------------------------------------------------------
# Order, guarded re-merge, QA MX-001
# ---------------------------------------------------------------------------


class TestOrderAndPipeline:
    @staticmethod
    def _pair(doc: str) -> tuple[DetectedEntity, DetectedEntity, DetectedEntity]:
        regex_person = _at(doc, "Dr Zorbalia", "PERSON", "regex")
        spacy_org = _at(doc, "Zorbalia", "ORG", "spacy")  # exact by normalized text
        spacy_person = _at(doc, "Dr Zorbalia", "PERSON", "spacy")  # exact by span
        return regex_person, spacy_org, spacy_person

    def test_first_overlapping_spacy_entity_decides_different_type_first(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Contact Dr Zorbalia pour le projet"
        regex_person, spacy_org, spacy_person = self._pair(doc)
        detector._merge_entities([spacy_org, spacy_person], [regex_person], doc)
        assert regex_person.is_ambiguous is True
        assert [f["decision"] for f in log.named(EVENT)] == ["kept_both"]
        assert log.named("duplicate_entity_removed") == []

    def test_first_overlapping_spacy_entity_decides_same_type_first(
        self, detector: HybridDetector, log: _LogRecorder
    ) -> None:
        doc = "Contact Dr Zorbalia pour le projet"
        regex_person, spacy_org, spacy_person = self._pair(doc)
        out = detector._merge_entities([spacy_person, spacy_org], [regex_person], doc)
        assert regex_person.is_ambiguous is False
        assert all(e.source == "spacy" for e in out)
        assert log.named(EVENT) == []
        assert len(log.named("duplicate_entity_removed")) == 1

    def test_guarded_remerge_flags_like_a_single_merge(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # the comma trim of the PERSON is refused (Zorbtech is not covered),
        # so detect_entities merges a second time from pristine regex copies
        doc = "Contact: Zorbalia Quentrel, Directeur de Zorbtech\nLe siège Zorbaville\n"
        person = _at(doc, "Zorbalia Quentrel, Directeur de Zorbtech", "PERSON", "spacy")
        spacy_org = _at(doc, "Zorbaville", "ORG", "spacy")
        regex_loc = _at(doc, "Zorbaville", "LOCATION", "regex")
        _stub_pipeline(monkeypatch, detector, [person, spacy_org], [regex_loc])
        out = detector.detect_entities(doc)
        assert {g["rule"] for g in log.named("person_boundary_refused")} == {
            "trailing_role_comma"
        }
        # one event per merge: the first merge and the guarded re-merge
        assert [f["decision"] for f in log.named(EVENT)] == ["kept_both"] * 2
        single = detector._merge_entities(
            [dataclasses.replace(person), dataclasses.replace(spacy_org)],
            [dataclasses.replace(regex_loc)],
            doc,
        )
        assert _keys(out) == _keys(single)
        assert [(e.entity_type, e.source) for e in out if e.is_ambiguous] == [
            ("LOCATION", "regex")
        ]

    def test_mx001_trimmed_person_equal_to_an_org_is_kept(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # the regex PERSON is trimmed before the merge into the exact span of
        # a spaCy ORG; before 10.3c the type-blind exact match dropped it
        doc = "Contact: Zorbalia Quentrel, Responsable technique\n"
        regex_person = _at(
            doc, "Zorbalia Quentrel, Responsable technique", "PERSON", "regex"
        )
        spacy_org = _at(doc, "Zorbalia Quentrel", "ORG", "spacy")
        _stub_pipeline(monkeypatch, detector, [spacy_org], [regex_person])
        out = detector.detect_entities(doc)
        assert _keys(out) == [
            ("Zorbalia Quentrel", "ORG", 9, 26, "spacy", False),
            ("Zorbalia Quentrel", "PERSON", 9, 26, "regex", True),
        ]
        (fields,) = log.named(EVENT)
        assert fields["match"] == "span"


# ---------------------------------------------------------------------------
# Slice P: R-HYPH-FN (AC3)
# ---------------------------------------------------------------------------


@pytest.fixture
def first_names(monkeypatch: pytest.MonkeyPatch) -> NameDictionary:
    """An injected name dictionary; tests add first names to it."""
    names = NameDictionary()
    names.first_names = set()
    names.last_names = set()
    monkeypatch.setattr(hd, "_default_name_dictionary", lambda: names)
    return names


class TestHyphenNoFirstName:
    @pytest.mark.parametrize("spacy_type", ["ORG", "LOCATION"])
    def test_hyphenated_person_without_first_name_is_skipped(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        first_names: NameDictionary,
        spacy_type: str,
    ) -> None:
        doc = "Le siège Zorbal-Quentrac pour le projet"
        spacy_entity = _at(doc, "Zorbal-Quentrac", spacy_type, "spacy")
        regex_person = _at(doc, "Zorbal-Quentrac", "PERSON", "regex")
        out = detector._merge_entities([spacy_entity], [regex_person], doc)
        assert _keys(out) == [("Zorbal-Quentrac", spacy_type, 9, 24, "spacy", False)]
        assert regex_person.is_ambiguous is False
        (fields,) = log.named(EVENT)
        assert (fields["decision"], fields["rule"]) == (
            "regex_skipped",
            "hyphen_no_known_first_name",
        )
        assert (fields["regex_type"], fields["spacy_type"]) == ("PERSON", spacy_type)
        _assert_no_text(fields, "Zorbal-Quentrac")

    def test_titled_hyphenated_person_is_skipped(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        first_names: NameDictionary,
    ) -> None:
        doc = "Contact Dr Zorbal-Quentrac pour le projet"
        regex_person = _at(doc, "Dr Zorbal-Quentrac", "PERSON", "regex")
        spacy_org = _at(doc, "Zorbal-Quentrac", "ORG", "spacy")
        out = detector._merge_entities([spacy_org], [regex_person], doc)
        assert _keys(out) == [("Zorbal-Quentrac", "ORG", 11, 26, "spacy", False)]
        (fields,) = log.named(EVENT)
        assert fields["match"] == "normalized_text"
        assert fields["decision"] == "regex_skipped"

    @pytest.mark.parametrize("known", ["Zorbal", "Quentrac"])
    def test_a_known_first_name_part_keeps_both(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        first_names: NameDictionary,
        known: str,
    ) -> None:
        first_names.first_names = {known}
        doc = "Le siège Zorbal-Quentrac pour le projet"
        spacy_org = _at(doc, "Zorbal-Quentrac", "ORG", "spacy")
        regex_person = _at(doc, "Zorbal-Quentrac", "PERSON", "regex")
        out = detector._merge_entities([spacy_org], [regex_person], doc)
        assert _keys(out) == [
            ("Zorbal-Quentrac", "ORG", 9, 24, "spacy", False),
            ("Zorbal-Quentrac", "PERSON", 9, 24, "regex", True),
        ]
        (fields,) = log.named(EVENT)
        assert (fields["decision"], fields["rule"]) == (
            "kept_both",
            "type_aware_exact_match",
        )

    @pytest.mark.parametrize(
        ("text", "regex_type"),
        [
            ("Zorbalia Quentrel", "PERSON"),  # several words: not the shape
            ("Zorbal-Quentrac-Zorbia", "PERSON"),  # three parts: not the shape
            ("Zorbal-Quentrac", "LOCATION"),  # not a PERSON
        ],
    )
    def test_other_shapes_and_types_keep_both(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        first_names: NameDictionary,
        text: str,
        regex_type: str,
    ) -> None:
        doc = f"Le siège {text} pour le projet"
        spacy_org = _at(doc, text, "ORG", "spacy")
        regex_entity = _at(doc, text, regex_type, "regex")
        out = detector._merge_entities([spacy_org], [regex_entity], doc)
        assert sorted((e.entity_type, e.source, e.is_ambiguous) for e in out) == sorted(
            [("ORG", "spacy", False), (regex_type, "regex", True)]
        )
        assert [f["decision"] for f in log.named(EVENT)] == ["kept_both"]

    def test_same_type_pair_is_unchanged(
        self,
        detector: HybridDetector,
        log: _LogRecorder,
        first_names: NameDictionary,
    ) -> None:
        doc = "Le siège Zorbal-Quentrac pour le projet"
        spacy_person = _at(doc, "Zorbal-Quentrac", "PERSON", "spacy")
        regex_person = _at(doc, "Zorbal-Quentrac", "PERSON", "regex")
        out = detector._merge_entities([spacy_person], [regex_person], doc)
        assert _keys(out) == [("Zorbal-Quentrac", "PERSON", 9, 24, "spacy", False)]
        assert log.named(EVENT) == []
        assert len(log.named("duplicate_entity_removed")) == 1
