"""spaCy-free unit tests for Story 10.3b (particles, roles, LOCATION noise).

Slice B (PERSON boundaries, before the merge):
- R-PART: surname particles (AC4), with the P4 / Q12 negatives;
- R-MC: Mc/Mac surnames (AC5);
- R-ROLE: trailing roles (AC6, AC9), and R-ROLE-LATE after W-JOIN;
- R-WJP: W-JOIN reads the same frozen particle list.

Unmarked on purpose: ``HybridDetector()`` and ``RegexMatcher()`` load no
spaCy model; ``detect_entities`` is exercised with stubbed detectors. Names
are invented; the other words are the generic words of the rules
(particles, role words, title words, legal forms) or main-corpus words
(AC12).
"""

from __future__ import annotations

import time
from typing import Any

import pytest
import yaml

from gdpr_pseudonymizer.nlp import hybrid_detector as hd
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import (
    HybridDetector,
    load_person_boundaries,
)
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher
from gdpr_pseudonymizer.resources import PERSON_BOUNDARIES_PATH


@pytest.fixture(scope="module")
def matcher() -> RegexMatcher:
    m = RegexMatcher()
    m.load_patterns()
    return m


@pytest.fixture
def detector() -> HybridDetector:
    return HybridDetector()


def _ent(
    text: str, entity_type: str, start: int, source: str = "spacy"
) -> DetectedEntity:
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
        source=source,
    )


def _at(doc: str, text: str, entity_type: str, source: str = "spacy") -> DetectedEntity:
    return _ent(text, entity_type, doc.index(text), source)


def _fix(
    detector: HybridDetector,
    doc: str,
    entity: DetectedEntity,
    blockers: list[tuple[int, int]] | None = None,
) -> str:
    out, _ = detector._fix_person_boundaries([entity], doc, blockers or [])
    return out[0].text


def _stub_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    detector: HybridDetector,
    spacy_entities: list[DetectedEntity],
    regex_entities: list[DetectedEntity],
) -> None:
    """``detect_entities`` without spaCy: both detectors return fixed lists."""
    monkeypatch.setattr(
        detector.spacy_detector, "detect_entities", lambda text: list(spacy_entities)
    )
    monkeypatch.setattr(
        detector.regex_matcher,
        "match_entities",
        lambda text, spacy_doc=None: list(regex_entities),
    )
    detector._model_loaded = True


class _LogRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def _record(self, event: str, **fields: Any) -> None:
        self.events.append((event, fields))

    debug = info = warning = error = _record


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------


class TestPersonBoundariesResource:
    def test_every_entry_has_a_why(self) -> None:
        data = yaml.safe_load(PERSON_BOUNDARIES_PATH.read_text(encoding="utf-8"))
        for section in ("particles", "role_words"):
            assert data[section]
            for entry in data[section]:
                assert entry["term"] and entry["why"], entry

    def test_allcaps_particles_are_derived(self) -> None:
        lists = load_person_boundaries()
        assert "LE" in lists.allcaps_particles and "VAN" in lists.allcaps_particles
        assert "DELLA" in lists.allcaps_particles
        assert all(p.isupper() for p in lists.allcaps_particles)

    def test_role_words_hold_no_known_first_name(self) -> None:
        names = NameDictionary()
        names.load()
        assert not [
            w for w in load_person_boundaries().role_words if names.is_first_name(w)
        ]


# ---------------------------------------------------------------------------
# R-PART (AC4)
# ---------------------------------------------------------------------------


class TestParticles:
    @pytest.mark.parametrize(
        ("doc", "span", "expected"),
        [
            (
                "M. Jean-Zorbal Le Quentrix a signé.",
                "M. Jean-Zorbal Le",
                "M. Jean-Zorbal Le Quentrix",
            ),
            (
                "Mme Zorbalia van der Zorb a signé.",
                "Mme Zorbalia",
                "Mme Zorbalia van der Zorb",
            ),
            ("avec Zorbal de Quentrac hier", "Zorbal", "Zorbal de Quentrac"),
            ("avec Zorbal du Quentrac hier", "Zorbal", "Zorbal du Quentrac"),
            ("avec Zorbal d'Quentrac hier", "Zorbal", "Zorbal d'Quentrac"),
            ("avec Zorbal d’Quentrac hier", "Zorbal", "Zorbal d’Quentrac"),
            ("avec Zorbal von Quentrac hier", "Zorbal", "Zorbal von Quentrac"),
            ("avec Zorbal Di Quentrac hier", "Zorbal", "Zorbal Di Quentrac"),
            ("avec Zorbal Della Quentrac hier", "Zorbal", "Zorbal Della Quentrac"),
            ("avec Zorbal ten Quentrac hier", "Zorbal", "Zorbal ten Quentrac"),
            (
                "avec Zorbal de Quentrac-Vardel hier",
                "Zorbal",
                "Zorbal de Quentrac-Vardel",
            ),
        ],
    )
    def test_particle_surname_is_added(
        self, detector: HybridDetector, doc: str, span: str, expected: str
    ) -> None:
        assert _fix(detector, doc, _at(doc, span, "PERSON", "regex")) == expected

    def test_no_break_space_keeps_the_document_slice(
        self, detector: HybridDetector
    ) -> None:
        doc = "avec Zorbal Le Quentrix hier"
        fixed = _fix(detector, doc, _at(doc, "Zorbal", "PERSON"))
        assert fixed == "Zorbal Le Quentrix"
        # the mapping key collapses whitespace (PR #86): same key as the
        # plain-space spelling
        assert " ".join(fixed.split()) == "Zorbal Le Quentrix"

    def test_allcaps_surname_after_a_capitalised_particle(
        self, detector: HybridDetector
    ) -> None:
        doc = "avec Zorbal LE QUENTRIX hier"
        assert _fix(detector, doc, _at(doc, "Zorbal", "PERSON")) == "Zorbal LE QUENTRIX"
        doc = "avec Zorbal Le QUENTRIX hier"
        assert _fix(detector, doc, _at(doc, "Zorbal", "PERSON")) == "Zorbal Le QUENTRIX"

    @pytest.mark.parametrize(
        ("doc", "span"),
        [
            # all-caps after lower-case du: an acronym ORG
            ("avec Zorbal du ZORBNET hier", "Zorbal"),
            # more than one capitalised token after the particles (P4 negative)
            ("avec Zorbal de la Zorb Tech Zorbaville hier", "Zorbal"),
            # a particle not followed by a capitalised surname
            ("Zorbalia de la séance", "Zorbalia"),
            # the surname is on the next line: W-JOIN's case, not this rule's
            ("avec Zorbal de\nQuentrac hier", "Zorbal"),
            ("avec Zorbal\nde Quentrac hier", "Zorbal"),
        ],
    )
    def test_no_extension(self, detector: HybridDetector, doc: str, span: str) -> None:
        assert _fix(detector, doc, _at(doc, span, "PERSON")) == span

    def test_org_detection_blocks_the_extension(self, detector: HybridDetector) -> None:
        doc = "Zorbalia Quentrel de Quentrix SA a signé"
        org = doc.index("Quentrix SA")
        person = _at(doc, "Zorbalia Quentrel", "PERSON")
        assert _fix(detector, doc, person, [(org, org + len("Quentrix SA"))]) == (
            "Zorbalia Quentrel"
        )

    def test_dictionary_place_blocks_the_extension(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(hd, "_geography_folded", lambda: frozenset({"zorbaville"}))
        doc = "Zorbalia Quentrel de Zorbaville a signé"
        assert _fix(detector, doc, _at(doc, "Zorbalia Quentrel", "PERSON")) == (
            "Zorbalia Quentrel"
        )

    @pytest.mark.parametrize("org_source", ["spacy", "regex"])
    def test_blockers_come_from_both_sources(
        self,
        detector: HybridDetector,
        monkeypatch: pytest.MonkeyPatch,
        org_source: str,
    ) -> None:
        doc = "Contact: Zorbalia Quentrel de Quentrix a signé"
        person = _at(doc, "Zorbalia Quentrel", "PERSON", "spacy")
        org = _at(doc, "Quentrix", "ORG", org_source)
        spacy_list = [person] + ([org] if org_source == "spacy" else [])
        regex_list = [org] if org_source == "regex" else []
        _stub_pipeline(monkeypatch, detector, spacy_list, regex_list)
        persons = [
            e.text for e in detector.detect_entities(doc) if e.entity_type == "PERSON"
        ]
        assert persons == ["Zorbalia Quentrel"]

    def test_particle_extension_through_the_pipeline(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: M. Jean-Zorbal Le Quentrix a signé"
        regex_person = _at(doc, "M. Jean-Zorbal Le", "PERSON", "regex")
        _stub_pipeline(monkeypatch, detector, [], [regex_person])
        persons = [
            e.text for e in detector.detect_entities(doc) if e.entity_type == "PERSON"
        ]
        assert persons == ["M. Jean-Zorbal Le Quentrix"]


# ---------------------------------------------------------------------------
# R-MC (AC5)
# ---------------------------------------------------------------------------


class TestMcMac:
    def test_titles_pattern_keeps_mc_whole(self, matcher: RegexMatcher) -> None:
        persons = [
            e.text
            for e in matcher.match_entities("Mme Sarah McZorbal a signé.")
            if e.entity_type == "PERSON"
        ]
        assert "Mme Sarah McZorbal" in persons
        persons = [
            e.text
            for e in matcher.match_entities("M. MacZorbal a signé.")
            if e.entity_type == "PERSON"
        ]
        assert "M. MacZorbal" in persons

    def test_span_ending_in_bare_mc_is_completed(
        self, detector: HybridDetector
    ) -> None:
        doc = "avec Zorbalia McZorbal hier"
        span = _ent("Zorbalia Mc", "PERSON", doc.index("Zorbalia"))
        assert _fix(detector, doc, span) == "Zorbalia McZorbal"

    def test_mac_as_an_ordinary_word_is_no_person(self, matcher: RegexMatcher) -> None:
        assert not [
            e
            for e in matcher.match_entities("Il travaille sur un Mac.")
            if e.entity_type == "PERSON"
        ]

    def test_mac_surname_starting_lower_case_stays_a_plain_token(
        self, matcher: RegexMatcher
    ) -> None:
        persons = [
            e.text
            for e in matcher.match_entities("M. Macquentrix a signé.")
            if e.entity_type == "PERSON"
        ]
        assert "M. Macquentrix" in persons

    def test_titles_pattern_is_linear_on_adversarial_lines(
        self, matcher: RegexMatcher
    ) -> None:
        regex = matcher.patterns["titles"][0]["regex"]
        for line in (
            ("M. McZorbal Mac " * 4000)[:50_000],
            ("Mme Zorbal Le Quentrix, " * 2500)[:50_000],
        ):
            start = time.perf_counter()
            for _ in regex.finditer(line):
                pass
            assert time.perf_counter() - start < 2.0


# ---------------------------------------------------------------------------
# R-ROLE (AC6, AC9) and R-ROLE-LATE
# ---------------------------------------------------------------------------


class TestTrailingRoles:
    @pytest.mark.parametrize(
        ("doc", "span", "expected"),
        [
            (
                "Zorbalia Quentrel, Responsable technique",
                "Zorbalia Quentrel, Responsable technique",
                "Zorbalia Quentrel",
            ),
            (
                "Zorbalia Quentrel, Directeur des Zorbs",
                "Zorbalia Quentrel, Directeur des Zorbs",
                "Zorbalia Quentrel",
            ),
            (
                "Mme Zorbalia Quentrel DRH",
                "Mme Zorbalia Quentrel DRH",
                "Mme Zorbalia Quentrel",
            ),
            (
                "(Mme Zorbalia Quentrel): oui",
                "Mme Zorbalia Quentrel):",
                "Mme Zorbalia Quentrel",
            ),
            (
                "Zorbalia Quentrel - Lead",
                "Zorbalia Quentrel - Lead",
                "Zorbalia Quentrel",
            ),
        ],
    )
    def test_trailing_role_is_trimmed(
        self, detector: HybridDetector, doc: str, span: str, expected: str
    ) -> None:
        assert _fix(detector, doc, _at(doc, span, "PERSON")) == expected

    def test_last_first_is_kept(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        names = NameDictionary()
        names.first_names = {"Zorbalia", "Responsable"}
        names.last_names = set()
        monkeypatch.setattr(hd, "_default_name_dictionary", lambda: names)
        doc = "Quentrix, Zorbalia"
        assert _fix(detector, doc, _at(doc, doc, "PERSON")) == doc
        # Q2 check: a word after the comma that is a known first name is
        # never cut, even if it also looks like a role word
        doc = "Quentrix, Responsable"
        assert _fix(detector, doc, _at(doc, doc, "PERSON")) == doc

    def test_role_acronym_must_follow_a_letter_on_the_same_line(
        self, detector: HybridDetector
    ) -> None:
        doc = "Zorbalia Quentrel\n- CTO"
        assert _fix(detector, doc, _at(doc, doc, "PERSON")) == doc
        doc = "Zorbalia Quentrel - DRH"
        assert _fix(detector, doc, _at(doc, doc, "PERSON")) == doc

    def test_multi_line_span_is_not_trimmed_before_the_merge(
        self, detector: HybridDetector
    ) -> None:
        doc = "Zorbalia Quentrel):\n- Zorbsecurity"
        assert _fix(detector, doc, _at(doc, doc, "PERSON")) == doc

    def test_dash_role_trimmed_when_the_org_is_covered(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: Zorbalia Quentrel - Lead QUENTRIX\n"
        person = _at(doc, "Zorbalia Quentrel - Lead QUENTRIX", "PERSON")
        org = _at(doc, "QUENTRIX", "ORG", "regex")
        _stub_pipeline(monkeypatch, detector, [person], [org])
        out = detector.detect_entities(doc)
        assert [e.text for e in out if e.entity_type == "PERSON"] == [
            "Zorbalia Quentrel"
        ]

    def test_dash_role_not_trimmed_when_the_org_is_uncovered(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: Zorbalia Quentrel - Lead QUENTRIX\n"
        person = _at(doc, "Zorbalia Quentrel - Lead QUENTRIX", "PERSON")
        _stub_pipeline(monkeypatch, detector, [person], [])
        out = detector.detect_entities(doc)
        assert [e.text for e in out if e.entity_type == "PERSON"] == [
            "Zorbalia Quentrel - Lead QUENTRIX"
        ]

    def test_role_trim_after_w_join_and_dedup(self, detector: HybridDetector) -> None:
        # A two-line spaCy span is left alone before the merge; the C2 trim
        # keeps "Zorbalia Quentrel):", and R-ROLE-LATE strips the glued "):".
        doc = "Équipe (Mme Zorbalia Quentrel):\n- Zorbsecurity"
        outer = _at(doc, "Zorbalia Quentrel):\n- Zorbsecurity", "PERSON", "spacy")
        inner = _at(doc, "Zorbalia Quentrel", "PERSON", "regex")
        out = detector._merge_entities([outer], [inner], doc)
        assert [e.text for e in out if e.entity_type == "PERSON"] == [
            "Zorbalia Quentrel"
        ]

    def test_late_dash_trim_is_guarded(self, detector: HybridDetector) -> None:
        doc = "Contact: Zorbalia Quentrel - Lead QUENTRIX"
        person = _at(doc, "Zorbalia Quentrel - Lead QUENTRIX", "PERSON")
        out = detector._trim_roles_late([person], doc)
        assert [e.text for e in out] == ["Zorbalia Quentrel - Lead QUENTRIX"]
        org = _at(doc, "QUENTRIX", "ORG", "regex")
        out = detector._trim_roles_late([person, org], doc)
        assert sorted(e.text for e in out) == ["QUENTRIX", "Zorbalia Quentrel"]

    def test_boundary_log_has_no_entity_text(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log = _LogRecorder()
        monkeypatch.setattr(hd, "logger", log)
        doc = "M. Jean-Zorbal Le Quentrix a signé"
        _fix(detector, doc, _at(doc, "M. Jean-Zorbal Le", "PERSON", "regex"))
        doc = "Zorbalia Quentrel, Responsable technique"
        _fix(detector, doc, _at(doc, doc, "PERSON"))
        fixed = [f for e, f in log.events if e == "person_boundary_fixed"]
        assert fixed and all(
            set(f) == {"rule", "source", "old_start", "old_end", "new_start", "new_end"}
            for f in fixed
        )
        assert {f["rule"] for f in fixed} == {"particle", "trailing_role_comma"}


# ---------------------------------------------------------------------------
# R-WJP: W-JOIN reads the frozen particle list
# ---------------------------------------------------------------------------


class TestWrappedNameParticles:
    def _persons(self, detector: HybridDetector, doc: str, name: str) -> list[str]:
        out = detector._merge_entities([_at(doc, name, "PERSON")], [], doc)
        return [e.text for e in out if e.entity_type == "PERSON"]

    def test_wrapped_name_with_an_approved_particle_is_joined(
        self, detector: HybridDetector
    ) -> None:
        doc = "le contrat est signé par Zorbalia Di\nQuentrix, avec le projet"
        assert self._persons(detector, doc, "Zorbalia") == ["Zorbalia Di\nQuentrix"]
        doc = "le contrat est signé par Zorbalia\nvon Quentrix, avec le projet"
        assert self._persons(detector, doc, "Zorbalia") == ["Zorbalia\nvon Quentrix"]

    def test_wrapped_particle_name_needs_a_single_line_break(
        self, detector: HybridDetector
    ) -> None:
        doc = "le contrat est signé par Zorbalia Di\n\nQuentrix, avec le projet"
        assert self._persons(detector, doc, "Zorbalia") == ["Zorbalia"]

    def test_wrap_pattern_is_built_from_the_resource(self) -> None:
        pattern = hd._wrap_re().pattern
        for particle in load_person_boundaries().particles:
            assert particle in pattern
