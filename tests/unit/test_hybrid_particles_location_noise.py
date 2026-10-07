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


# ---------------------------------------------------------------------------
# Slice C: LOCATION noise (AC1, AC2, fragment of AC3)
# ---------------------------------------------------------------------------


def _locations(detector: HybridDetector, doc: str, *spans: str) -> list[str]:
    entities = [_at(doc, s, "LOCATION") for s in spans]
    out = detector._merge_entities(entities, [], doc)
    return [e.text for e in out if e.entity_type == "LOCATION"]


class TestLocationNoise:
    @pytest.mark.parametrize(
        "word", ["CONFORME", "CC", "Équipe", "Constat", "SecNumCloud", "Pentest"]
    )
    def test_stoplist_word_is_dropped(
        self, detector: HybridDetector, word: str
    ) -> None:
        doc = f"Point 3: {word} pour le projet"
        assert _locations(detector, doc, word) == []

    @pytest.mark.parametrize(
        "place",
        ["PARIS", "BOSTON", "ZORBAVILLE", "Zorbaville", "US", "USA", "UK", "UE", "EU"],
    )
    def test_real_and_unknown_places_are_kept(
        self, detector: HybridDetector, place: str
    ) -> None:
        # absence from the geography dictionary is never evidence (AC1)
        doc = f"Bureau: {place} pour le projet"
        assert _locations(detector, doc, place) == [place]

    @pytest.mark.parametrize("fragment", ["à Dr", "à M"])
    def test_fragment_is_dropped(self, detector: HybridDetector, fragment: str) -> None:
        doc = f"Il a parlé {fragment}. Zorbal pour le projet"
        assert _locations(detector, doc, fragment) == []

    def test_place_after_a_preposition_is_kept(self, detector: HybridDetector) -> None:
        doc = "Il travaille à Zorbaville depuis mars"
        assert _locations(detector, doc, "à Zorbaville") == ["à Zorbaville"]

    def test_multi_word_place_with_a_stoplist_word_is_kept(
        self, detector: HybridDetector
    ) -> None:
        doc = "Le siège Équipe Zorbaville pour le projet"
        assert _locations(detector, doc, "Équipe Zorbaville") == ["Équipe Zorbaville"]

    def test_stoplist_piece_cut_by_r_split_is_dropped(
        self, detector: HybridDetector
    ) -> None:
        doc = "Zorbaville\nCONFORME"
        assert _locations(detector, doc, doc) == ["Zorbaville"]

    def test_company_typed_as_place_is_kept(self, detector: HybridDetector) -> None:
        # AC3 (Lionel 2026-10-07): no lexicon, no in-document evidence, so a
        # company typed LOCATION stays covered as it is
        doc = "Quentrix a signé. Le cabinet Quentrix aussi."
        place = _ent("Quentrix", "LOCATION", doc.rindex("Quentrix"))
        org = _ent("Quentrix", "ORG", 0)
        out = detector._merge_entities([place, org], [], doc)
        assert sorted((e.entity_type, e.start_pos) for e in out) == [
            ("LOCATION", doc.rindex("Quentrix")),
            ("ORG", 0),
        ]

    def test_other_types_are_untouched(self, detector: HybridDetector) -> None:
        doc = "CONFORME pour le projet"
        out = detector._merge_entities([_at(doc, "CONFORME", "ORG")], [], doc)
        assert [e.text for e in out] == ["CONFORME"]

    def test_noise_log_has_no_entity_text(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log = _LogRecorder()
        monkeypatch.setattr(hd, "logger", log)
        doc = "Point 3: CONFORME, à Dr, Équipe"
        _locations(detector, doc, "CONFORME", "à Dr", "Équipe")
        events = [f for e, f in log.events if e == "location_noise_filtered"]
        assert sorted(f["reason"] for f in events) == [
            "allcaps_common_word",
            "common_noun",
            "fragment",
        ]
        assert all(
            set(f) == {"reason", "action", "source", "start", "end"} for f in events
        )


class TestLocationNoiseResource:
    def test_every_entry_has_a_why(self) -> None:
        from gdpr_pseudonymizer.resources import LOCATION_NOISE_FILTER_PATH

        data = yaml.safe_load(LOCATION_NOISE_FILTER_PATH.read_text(encoding="utf-8"))
        assert data["terms"]
        for entry in data["terms"]:
            assert entry["term"] and entry["why"], entry

    def test_stoplist_holds_no_place(self) -> None:
        stoplist = hd.load_location_noise_filter()
        assert not stoplist & hd._geography_folded()
        assert not stoplist & {
            "us",
            "usa",
            "uk",
            "ue",
            "eu",
            "nord",
            "sud",
            "est",
        }


# ---------------------------------------------------------------------------
# QA fixes (gate CONCERNS, Lionel 2026-10-07): WJ-001, REQ-001, REQ-002,
# COV-001, PERF-001
# ---------------------------------------------------------------------------


class TestWrappedNameLineStartWords:
    """WJ-001: Le, La, De, Du, Des are not particles at the start of the
    next line; the other particles still join."""

    def _persons(self, detector: HybridDetector, doc: str) -> list[str]:
        out = detector._merge_entities([_at(doc, "Zorbalia", "PERSON")], [], doc)
        return [e.text for e in out if e.entity_type == "PERSON"]

    @pytest.mark.parametrize(
        "next_line",
        [
            "Le Comité a validé le projet",
            "La Direction a validé le projet",
            "Des Zorbs ont validé le projet",
            "Du Quentrix a validé le projet",
            "De Quentrix a validé le projet",
        ],
    )
    def test_article_at_the_line_start_is_not_joined(
        self, detector: HybridDetector, next_line: str
    ) -> None:
        doc = f"le contrat est signé par Zorbalia\n{next_line}"
        assert self._persons(detector, doc) == ["Zorbalia"]

    @pytest.mark.parametrize(
        ("next_line", "joined"),
        [
            ("Di Quentrix, avec le projet", "Zorbalia\nDi Quentrix"),
            ("Da Quentrix, avec le projet", "Zorbalia\nDa Quentrix"),
            ("Dos Quentrix, avec le projet", "Zorbalia\nDos Quentrix"),
            ("von Quentrix, avec le projet", "Zorbalia\nvon Quentrix"),
            ("de Quentrix, avec le projet", "Zorbalia\nde Quentrix"),
        ],
    )
    def test_other_particles_still_join(
        self, detector: HybridDetector, next_line: str, joined: str
    ) -> None:
        doc = f"le contrat est signé par Zorbalia\n{next_line}"
        assert self._persons(detector, doc) == [joined]

    def test_capitalised_article_before_the_break_still_joins(
        self, detector: HybridDetector
    ) -> None:
        doc = "le contrat est signé par Zorbalia Le\nQuentrix, avec le projet"
        assert self._persons(detector, doc) == ["Zorbalia Le\nQuentrix"]


class TestParticleRefinements:
    @pytest.mark.parametrize(
        "doc",
        [
            "pour Zorbalia le Directeur a signé",
            "avec Zorbalia la Présidente du projet",
        ],
    )
    def test_role_word_after_an_article_is_no_surname(
        self, detector: HybridDetector, doc: str
    ) -> None:
        # REQ-001 (GUIDELINES P6)
        assert _fix(detector, doc, _at(doc, "Zorbalia", "PERSON")) == "Zorbalia"

    def test_article_surname_still_extends(self, detector: HybridDetector) -> None:
        doc = "pour Zorbalia le Quentrix a signé"
        assert _fix(detector, doc, _at(doc, "Zorbalia", "PERSON")) == (
            "Zorbalia le Quentrix"
        )

    def test_contracted_place_is_not_absorbed(self, detector: HybridDetector) -> None:
        # REQ-002: "du Havre" is "de" + "Le Havre", a dictionary place
        doc = "pour Zorbalia du Havre a signé"
        assert _fix(detector, doc, _at(doc, "Zorbalia", "PERSON")) == "Zorbalia"

    @pytest.mark.parametrize(
        ("doc", "place"),
        [
            ("pour Zorbalia de La Zorbelle a signé", "la zorbelle"),
            ("pour Zorbalia de Le Zorbmans a signé", "le zorbmans"),
            ("pour Zorbalia des Zorbières a signé", "les zorbières"),
        ],
    )
    def test_place_inside_the_chain_is_not_absorbed(
        self,
        detector: HybridDetector,
        monkeypatch: pytest.MonkeyPatch,
        doc: str,
        place: str,
    ) -> None:
        # REQ-002, with an invented place injected into the dictionary
        monkeypatch.setattr(hd, "_geography_folded", lambda: frozenset({place}))
        assert _fix(detector, doc, _at(doc, "Zorbalia", "PERSON")) == "Zorbalia"

    def test_trailing_particle_search_scales_linearly(
        self, detector: HybridDetector
    ) -> None:
        # PERF-001: a span ending in a long particle run; the search looks at
        # the last few tokens only. A ratio, not an absolute time.
        blocked = hd._SpanIndex([])

        def run(n: int) -> float:
            doc = "Zorbal" + " le" * n + " Quentrix"
            entity = _ent(doc[: -len(" Quentrix")], "PERSON", 0)
            best = float("inf")
            for _ in range(3):
                start = time.perf_counter()
                for _ in range(20):
                    HybridDetector._extend_particles(entity, doc, blocked)
                best = min(best, time.perf_counter() - start)
            return best

        run(1_000)  # warm-up
        small = run(5_000)
        large = run(20_000)
        assert large / small < 10, (small, large)


class TestCommaRoleGuard:
    """COV-001: ", <role>" is guarded like " - <role>"."""

    def test_comma_role_trimmed_when_the_org_is_covered(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: Zorbalia Quentrel, Directeur de Zorbtech\n"
        person = _at(doc, "Zorbalia Quentrel, Directeur de Zorbtech", "PERSON")
        org = _at(doc, "Zorbtech", "ORG", "regex")
        _stub_pipeline(monkeypatch, detector, [person], [org])
        out = detector.detect_entities(doc)
        assert [e.text for e in out if e.entity_type == "PERSON"] == [
            "Zorbalia Quentrel"
        ]

    def test_comma_role_kept_when_the_org_is_uncovered(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: Zorbalia Quentrel, Directeur de Zorbtech\n"
        person = _at(doc, "Zorbalia Quentrel, Directeur de Zorbtech", "PERSON")
        _stub_pipeline(monkeypatch, detector, [person], [])
        out = detector.detect_entities(doc)
        assert [e.text for e in out if e.entity_type == "PERSON"] == [
            "Zorbalia Quentrel, Directeur de Zorbtech"
        ]

    def test_comma_role_without_capitalised_tail_needs_no_cover(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: Zorbalia Quentrel, Responsable technique\n"
        person = _at(doc, "Zorbalia Quentrel, Responsable technique", "PERSON")
        _stub_pipeline(monkeypatch, detector, [person], [])
        out = detector.detect_entities(doc)
        assert [e.text for e in out if e.entity_type == "PERSON"] == [
            "Zorbalia Quentrel"
        ]

    def test_late_comma_trim_is_guarded(self, detector: HybridDetector) -> None:
        doc = "Contact: Zorbalia Quentrel, Directeur de Zorbtech"
        person = _at(doc, "Zorbalia Quentrel, Directeur de Zorbtech", "PERSON")
        out = detector._trim_roles_late([person], doc)
        assert [e.text for e in out] == ["Zorbalia Quentrel, Directeur de Zorbtech"]
