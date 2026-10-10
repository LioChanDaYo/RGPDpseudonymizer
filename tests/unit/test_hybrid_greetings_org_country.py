"""spaCy-free unit tests for Story 10.4 (greetings, organisation + place).

Slice O (organisation + place, AC4): R-OPC merges an ORG and the listed place
that follows it, the place keeping its own LOCATION.

Slice A (carried losses, AC5): R-ACR ties an all-caps token to the initials of
an ORG of the same document; R-FN-DOC offers a first name used alone when the
document names that person in full.

Slice S (salutations, AC1-AC3):
- R-SAL-SPLIT: "X, Y" on a salutation line, both known first names → two
  PERSONs (AC1);
- R-SAL-BARE: a known first name alone on a salutation line, or after a
  greeting, thanks or compliment opener → PERSON (AC2);
- AC3: nothing changes off a salutation line.

Unmarked on purpose: ``HybridDetector()`` loads no spaCy model, and
``detect_entities`` runs with stubbed detectors. Names are invented
(Zorbalia, Quentrel, Quentrix, Zorbaville, Zorbtech) and injected into the
name dictionary; the other words occur in the main-corpus text (AC10).
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from gdpr_pseudonymizer.nlp import hybrid_detector as hd
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import (
    HybridDetector,
    load_place_abbreviations,
    load_salutations,
)
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary
from gdpr_pseudonymizer.resources import PLACE_ABBREVIATIONS_PATH, SALUTATIONS_PATH

INVENTED_FIRST_NAMES = {"Zorbalia", "Quentrel"}


@pytest.fixture
def detector() -> HybridDetector:
    return HybridDetector()


@pytest.fixture
def first_names(monkeypatch: pytest.MonkeyPatch) -> NameDictionary:
    """The name dictionary, reduced to invented first names."""
    names = NameDictionary()
    names.first_names = set(INVENTED_FIRST_NAMES)
    names.last_names = set()
    monkeypatch.setattr(hd, "_default_name_dictionary", lambda: names)
    return names


def _at(
    doc: str, text: str, entity_type: str, source: str = "spacy", nth: int = 0
) -> DetectedEntity:
    start = -1
    for _ in range(nth + 1):
        start = doc.index(text, start + 1)
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
        source=source,
    )


def _stub_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    detector: HybridDetector,
    spacy_entities: list[DetectedEntity],
    regex_entities: list[DetectedEntity],
) -> None:
    """``detect_entities`` without spaCy: both detectors return fixed lists."""
    monkeypatch.setattr(
        detector.spacy_detector,
        "detect_entities",
        lambda text: [DetectedEntity(**vars(e)) for e in spacy_entities],
    )
    monkeypatch.setattr(
        detector.regex_matcher,
        "match_entities",
        lambda text, spacy_doc=None: [
            DetectedEntity(**vars(e)) for e in regex_entities
        ],
    )
    detector._model_loaded = True


def _detect(
    monkeypatch: pytest.MonkeyPatch,
    detector: HybridDetector,
    doc: str,
    spacy_entities: list[DetectedEntity] | None = None,
    regex_entities: list[DetectedEntity] | None = None,
) -> list[tuple[str, str, int]]:
    _stub_pipeline(monkeypatch, detector, spacy_entities or [], regex_entities or [])
    return [(e.text, e.entity_type, e.start_pos) for e in detector.detect_entities(doc)]


def _persons(found: list[tuple[str, str, int]]) -> list[str]:
    return [text for text, entity_type, _ in found if entity_type == "PERSON"]


class _LogRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def _record(self, event: str, **fields: Any) -> None:
        self.events.append((event, fields))

    debug = info = warning = error = _record


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------


class TestSalutationResource:
    def test_every_opener_has_a_kind_and_a_why(self) -> None:
        data = yaml.safe_load(SALUTATIONS_PATH.read_text(encoding="utf-8"))
        assert data["openers"]
        for entry in data["openers"]:
            assert entry["term"] and entry["why"], entry
            assert entry["kind"] in ("greeting", "thanks", "compliment"), entry

    def test_compliment_and_thanks_openers_are_in_scope(self) -> None:
        kinds = {kind for _term, kind in load_salutations().openers}
        assert {"greeting", "thanks", "compliment"} <= kinds

    def test_max_line_length(self) -> None:
        assert load_salutations().max_line_length == 40


# ---------------------------------------------------------------------------
# Salutation lines (AC precisions)
# ---------------------------------------------------------------------------


class TestSalutationLines:
    @pytest.mark.parametrize(
        ("doc", "shape", "kind", "names"),
        [
            ("Zorbalia,", 1, "names", ["Zorbalia"]),
            ("   Zorbalia ,  ", 1, "names", ["Zorbalia"]),
            ("Zorbalia, Quentrel,", 1, "names", ["Zorbalia", "Quentrel"]),
            ("Bonjour Zorbalia,", 2, "greeting", ["Zorbalia"]),
            ("Bonjour Zorbalia, Quentrel,", 2, "greeting", ["Zorbalia", "Quentrel"]),
            ("Merci Zorbalia.", 2, "thanks", ["Zorbalia"]),
            ("Bonne initiative Zorbalia.", 2, "compliment", ["Zorbalia"]),
            ("Félicitations Zorbalia!", 2, "compliment", ["Zorbalia"]),
            ("Bonjour Zorbalia", 2, "greeting", ["Zorbalia"]),
        ],
    )
    def test_shapes(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        doc: str,
        shape: int,
        kind: str,
        names: list[str],
    ) -> None:
        (line,) = detector._salutation_lines(doc)
        assert (line.shape, line.kind) == (shape, kind)
        assert [doc[a:b] for a, b in line.names] == names

    @pytest.mark.parametrize(
        "doc",
        [
            "Le rapport de Zorbalia, Quentrel est prêt.",  # running text
            "Zorbalia, Quentrix,",  # Quentrix is not a known first name
            "zorbalia,",  # not capitalised in the text
            "Bonjour à tous,",  # no name after the opener
            "Pour le comité, Bonjour Zorbalia.",  # opener not at the line start
            "Merci Zorbalia pour le rapport.",  # a word follows the name
            "Bonjourzorbalia,",
        ],
    )
    def test_not_a_salutation_line(
        self, detector: HybridDetector, first_names: NameDictionary, doc: str
    ) -> None:
        assert detector._salutation_lines(doc) == []

    def test_shape_1_length_limit(
        self, detector: HybridDetector, first_names: NameDictionary
    ) -> None:
        first_names.first_names |= {"Zorbaliandrinettissima", "Quentrelissandroulette"}
        doc = "Zorbaliandrinettissima, Quentrelissandroulette,"
        assert len(doc) > load_salutations().max_line_length
        assert detector._salutation_lines(doc) == []

    def test_shape_2_has_no_length_limit(
        self, detector: HybridDetector, first_names: NameDictionary
    ) -> None:
        # PO validation S1: the compliment line goes on after the name
        doc = (
            "Bonne initiative Zorbalia. J'ajoute à la boucle Quentrix et le comité "
            "pour la suite du projet de Zorbaville."
        )
        assert len(doc) > 80
        (line,) = detector._salutation_lines(doc)
        assert [doc[a:b] for a, b in line.names] == ["Zorbalia"]

    def test_each_line_is_read_on_its_own(
        self, detector: HybridDetector, first_names: NameDictionary
    ) -> None:
        doc = "Objet: rapport\n\nZorbalia,\n\nLe rapport est prêt.\nMerci Quentrel.\n"
        lines = detector._salutation_lines(doc)
        assert [doc[n[0][0] : n[0][1]] for n in (ln.names for ln in lines)] == [
            "Zorbalia",
            "Quentrel",
        ]


# ---------------------------------------------------------------------------
# R-SAL-SPLIT (AC1)
# ---------------------------------------------------------------------------


class TestSalutationSplit:
    @pytest.mark.parametrize(
        "doc",
        ["Zorbalia, Quentrel,\n\nLe rapport est prêt.", "Bonjour Zorbalia, Quentrel,"],
    )
    def test_regex_pair_on_a_salutation_line_is_split(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
        doc: str,
    ) -> None:
        pair = _at(doc, "Zorbalia, Quentrel", "PERSON", source="regex")
        found = _detect(monkeypatch, detector, doc, regex_entities=[pair])
        assert _persons(found) == ["Zorbalia", "Quentrel"]

    def test_spacy_pair_on_a_salutation_line_is_split(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Zorbalia, Quentrel,"
        pair = _at(doc, "Zorbalia, Quentrel", "PERSON")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[pair])
        assert found == [("Zorbalia", "PERSON", 0), ("Quentrel", "PERSON", 10)]

    def test_pieces_keep_source_and_are_not_flagged(
        self, detector: HybridDetector, first_names: NameDictionary
    ) -> None:
        doc = "Zorbalia, Quentrel,"
        pair = _at(doc, "Zorbalia, Quentrel", "PERSON", source="regex")
        pair.is_ambiguous = True
        lines = detector._salutation_lines(doc)
        out, _ = detector._split_salutation_pairs([pair], [], doc, lines)
        assert [(e.text, e.source, e.is_ambiguous) for e in out] == [
            ("Zorbalia", "regex", False),
            ("Quentrel", "regex", False),
        ]

    def test_second_part_not_a_first_name_is_unchanged(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # GUIDELINES Q2: a genuine "Last, First" stays one PERSON
        doc = "Quentrix, Zorbalia,"
        pair = _at(doc, "Quentrix, Zorbalia", "PERSON", source="regex")
        found = _detect(monkeypatch, detector, doc, regex_entities=[pair])
        assert _persons(found) == ["Quentrix, Zorbalia"]

    def test_pair_in_running_text_is_unchanged(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Le dossier de Zorbalia, Quentrel est prêt."
        pair = _at(doc, "Zorbalia, Quentrel", "PERSON", source="regex")
        found = _detect(monkeypatch, detector, doc, regex_entities=[pair])
        assert _persons(found) == ["Zorbalia, Quentrel"]

    def test_pair_on_an_over_long_line_is_unchanged(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first_names.first_names |= {"Zorbaliandrinettissima", "Quentrelissandroulette"}
        doc = "Zorbaliandrinettissima, Quentrelissandroulette,"
        pair = _at(doc, doc[:-1], "PERSON", source="regex")
        found = _detect(monkeypatch, detector, doc, regex_entities=[pair])
        assert _persons(found) == [doc[:-1]]

    def test_last_first_names_pattern_is_unchanged(
        self, first_names: NameDictionary
    ) -> None:
        # AC1: the YAML pattern still checks the part after the comma only
        matcher = hd.RegexMatcher()
        matcher.load_patterns()
        matcher.name_dictionary = first_names
        doc = "Quentrix, Zorbalia"
        assert [e.text for e in matcher.match_entities(doc)] == ["Quentrix, Zorbalia"]
        assert matcher.match_entities("Zorbalia, Quentrix") == []

    def test_guards_are_reindexed(
        self, detector: HybridDetector, first_names: NameDictionary
    ) -> None:
        doc = "Zorbalia, Quentrel,\nQuentrix Zorbtech"
        pair = _at(doc, "Zorbalia, Quentrel", "PERSON", source="regex")
        other = _at(doc, "Quentrix Zorbtech", "PERSON", source="regex")
        guard = hd._RoleGuard(1, other, ((0, 1),), "trailing_role_dash")
        lines = detector._salutation_lines(doc)
        out, guards = detector._split_salutation_pairs(
            [pair, other], [guard], doc, lines
        )
        assert [e.text for e in out] == ["Zorbalia", "Quentrel", "Quentrix Zorbtech"]
        assert guards[0].index == 2 and out[guards[0].index] is other


# ---------------------------------------------------------------------------
# R-SAL-BARE (AC2)
# ---------------------------------------------------------------------------


class TestSalutationBareName:
    @pytest.mark.parametrize(
        ("doc", "name"),
        [
            ("Zorbalia,\n\nLe rapport est prêt.", "Zorbalia"),
            ("Bonjour Zorbalia,\n\nLe rapport est prêt.", "Zorbalia"),
            ("Merci Zorbalia.", "Zorbalia"),
            ("Bonne initiative Zorbalia.", "Zorbalia"),
            (
                "Bonne initiative Zorbalia. J'ajoute à la boucle le comité pour la "
                "suite du projet et du rapport de Zorbaville.",
                "Zorbalia",
            ),
        ],
    )
    def test_bare_first_name_is_detected(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
        doc: str,
        name: str,
    ) -> None:
        found = _detect(monkeypatch, detector, doc)
        assert (name, "PERSON", doc.index(name)) in found

    def test_new_detection_is_a_regex_person(
        self, detector: HybridDetector, first_names: NameDictionary
    ) -> None:
        doc = "Merci Zorbalia."
        (entity,) = detector._salutation_names(
            doc, detector._salutation_lines(doc), [], []
        )
        assert (entity.text, entity.source, entity.confidence) == (
            "Zorbalia",
            "regex",
            0.80,
        )

    def test_opener_in_the_middle_of_a_line_does_not_fire(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Pour le comité, Merci Zorbalia."
        assert _detect(monkeypatch, detector, doc) == []

    def test_name_found_by_spacy_is_not_duplicated(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Bonjour Zorbalia,"
        found = _detect(
            monkeypatch,
            detector,
            doc,
            spacy_entities=[_at(doc, "Zorbalia", "PERSON")],
        )
        assert found == [("Zorbalia", "PERSON", 8)]

    def test_two_names_after_an_opener(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Bonjour Zorbalia, Quentrel,"
        assert _persons(_detect(monkeypatch, detector, doc)) == [
            "Zorbalia",
            "Quentrel",
        ]


# ---------------------------------------------------------------------------
# AC3: nothing changes off a salutation line
# ---------------------------------------------------------------------------


class TestRunningText:
    @pytest.mark.parametrize(
        "doc",
        [
            "Le rapport de Pierre et du comité est prêt.",
            "Une pierre sur le bureau du comité.",
            "Une page blanche pour le rapport.",
            "Blanche, la page du rapport reste sur le bureau.",
            "Pierre après pierre, le projet reste solide.",
        ],
    )
    def test_real_first_names_in_running_text(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch, doc: str
    ) -> None:
        # the real name dictionary: "Pierre" and "Blanche" are first names
        assert detector._known_first_name("Pierre")
        assert detector._known_first_name("Blanche")
        assert detector._salutation_lines(doc) == []
        assert _detect(monkeypatch, detector, doc) == []

    def test_invented_first_names_in_running_text(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = (
            "Le rapport de Zorbalia et du comité est prêt.\n"
            "Quentrel, le comité et le bureau.\n"
        )
        spacy_entities = [_at(doc, "Zorbalia", "PERSON")]
        regex_entities = [_at(doc, "Quentrel", "PERSON", source="regex")]
        with_rules = _detect(monkeypatch, detector, doc, spacy_entities, regex_entities)
        monkeypatch.setattr(HybridDetector, "_salutation_lines", lambda self, text: [])
        without_rules = _detect(
            monkeypatch, detector, doc, spacy_entities, regex_entities
        )
        assert with_rules == without_rules


# ---------------------------------------------------------------------------
# Logging: offsets and enums only
# ---------------------------------------------------------------------------


class TestSalutationEvents:
    def test_events_carry_no_entity_text(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        recorder = _LogRecorder()
        monkeypatch.setattr(hd, "logger", recorder)
        doc = "Zorbalia, Quentrel,\nMerci Zorbalia."
        pair = _at(doc, "Zorbalia, Quentrel", "PERSON", source="regex")
        _detect(monkeypatch, detector, doc, regex_entities=[pair])
        events = {
            name: fields
            for name, fields in recorder.events
            if name.startswith("salutation_")
        }
        assert set(events) == {"salutation_name_added", "salutation_name_split"}
        assert events["salutation_name_added"] == {
            "shape": 2,
            "opener_kind": "thanks",
            "start": 26,
            "end": 34,
        }
        for fields in events.values():
            assert "text" not in fields
            for value in fields.values():
                assert not (isinstance(value, str) and "Zorbalia" in value)


# ---------------------------------------------------------------------------
# Slice O: R-OPC, organisation + place (AC4)
# ---------------------------------------------------------------------------


def _types(found: list[tuple[str, str, int]]) -> list[tuple[str, str]]:
    return [(text, entity_type) for text, entity_type, _ in found]


class TestPlaceAbbreviationResource:
    def test_the_five_abbreviations_with_a_why(self) -> None:
        data = yaml.safe_load(PLACE_ABBREVIATIONS_PATH.read_text(encoding="utf-8"))
        assert [e["term"] for e in data["terms"]] == ["UK", "US", "USA", "UE", "EU"]
        for entry in data["terms"]:
            assert entry["why"], entry
        assert load_place_abbreviations() == ("UK", "US", "USA", "UE", "EU")

    def test_scope_and_compass_words_are_not_places(self) -> None:
        places = {phrase for phrase, _source in hd._org_place_phrases()}
        assert {"France", "Europe", "Paris", "UK"} <= places
        assert not places & {"Monde", "Nord", "International", "Sud"}


class TestOrgPlaceMerge:
    @pytest.mark.parametrize(
        ("doc", "place"),
        [
            ("Zorbtech France et le comité.", "France"),  # country
            ("Zorbtech Europe et le comité.", "Europe"),  # vp_regions place
            ("Zorbtech Paris et le comité.", "Paris"),  # city
            ("Zorbtech UK et le comité.", "UK"),  # abbreviation
            ("Zorbtech Hauts-de-France et le comité.", "Hauts-de-France"),  # region
        ],
    )
    def test_org_and_place_are_merged_with_a_nested_location(
        self,
        detector: HybridDetector,
        monkeypatch: pytest.MonkeyPatch,
        doc: str,
        place: str,
    ) -> None:
        found = _detect(
            monkeypatch, detector, doc, spacy_entities=[_at(doc, "Zorbtech", "ORG")]
        )
        assert _types(found) == [(f"Zorbtech {place}", "ORG"), (place, "LOCATION")]

    def test_existing_location_is_kept(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Le rapport de Zorbtech France est prêt."
        spacy_entities = [_at(doc, "Zorbtech", "ORG"), _at(doc, "France", "LOCATION")]
        found = _detect(monkeypatch, detector, doc, spacy_entities=spacy_entities)
        assert found == [
            ("Zorbtech France", "ORG", 14),
            ("France", "LOCATION", 23),
        ]
        merged = detector._merge_org_places(
            [DetectedEntity(**vars(e)) for e in spacy_entities], doc
        )
        assert [(e.text, e.source) for e in merged] == [
            ("Zorbtech France", "spacy"),
            ("France", "spacy"),
        ]

    @pytest.mark.parametrize(
        "doc",
        [
            "Zorbtech Uk et le comité.",  # an abbreviation matches in capitals only
            "Zorbtech france et le comité.",  # the place starts with a capital
            "Zorbtech Monde et le comité.",  # scope word
            "Zorbtech Nord et le comité.",  # compass word
            "Zorbtech\nFrance et le comité.",  # a line break
            "Zorbtech  France et le comité.",  # two spaces
            "Zorbtech Parisoval et le comité.",  # a letter follows the place
            "Zorbtech de France et le comité.",  # a connector
        ],
    )
    def test_not_merged(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch, doc: str
    ) -> None:
        found = _detect(
            monkeypatch, detector, doc, spacy_entities=[_at(doc, "Zorbtech", "ORG")]
        )
        assert ("Zorbtech", "ORG") in _types(found)
        assert not [t for t, ty in _types(found) if ty == "ORG" and t != "Zorbtech"]

    def test_role_and_place_are_never_merged(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # AC4: the role filter drops "VP" and "VP Europe" first; the place of a
        # dropped VP form is kept as a LOCATION (Story 10.2)
        doc = "Le VP Europe et le VP Europe."
        spacy_entities = [
            _at(doc, "VP", "ORG"),
            _at(doc, "VP Europe", "ORG", nth=1),
        ]
        found = _detect(monkeypatch, detector, doc, spacy_entities=spacy_entities)
        assert [ty for _t, ty in _types(found)] == ["LOCATION"]
        assert _types(found) == [("Europe", "LOCATION")]

    def test_merged_text_that_is_a_role_is_not_merged(
        self, detector: HybridDetector
    ) -> None:
        # even when the ORG piece reaches the merge, "VP Sales Europe" is a role
        doc = "VP Sales Europe"
        piece = _at(doc, "VP Sales", "ORG")
        assert detector._merge_org_places([piece], doc) == [piece]

    def test_without_text_nothing_changes(self, detector: HybridDetector) -> None:
        piece = _at("Zorbtech France", "Zorbtech", "ORG")
        assert detector._merge_org_places([piece], None) == [piece]

    def test_guarded_re_merge_gives_the_same_output(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Contact: Zorbalia Quentrel - Lead QUENTRIX\nZorbtech France\n"
        person = _at(doc, "Zorbalia Quentrel - Lead QUENTRIX", "PERSON")
        spacy_entities = [person, _at(doc, "Zorbtech", "ORG")]
        found = _detect(monkeypatch, detector, doc, spacy_entities=spacy_entities)
        # the dash-role trim is refused (QUENTRIX is covered by nothing), so the
        # document is merged twice; the organisation and its place appear once
        assert ("Zorbalia Quentrel - Lead QUENTRIX", "PERSON") in _types(found)
        assert _types(found).count(("Zorbtech France", "ORG")) == 1
        assert _types(found).count(("France", "LOCATION")) == 1

    def test_event_carries_no_entity_text(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorder = _LogRecorder()
        monkeypatch.setattr(hd, "logger", recorder)
        doc = "Zorbtech UK et le comité."
        _detect(
            monkeypatch, detector, doc, spacy_entities=[_at(doc, "Zorbtech", "ORG")]
        )
        merged = [f for name, f in recorder.events if name == "org_place_merged"]
        assert len(merged) == 1
        fields = merged[0]
        assert fields == {
            "source": "spacy",
            "org_start": 0,
            "org_end": 8,
            "place_start": 9,
            "place_end": 11,
            "place_source": "abbreviation",
            "location_emitted": True,
        }


# ---------------------------------------------------------------------------
# Slice A: R-ACR ("BRS") and R-FN-DOC ("Pierre") (AC5)
# ---------------------------------------------------------------------------


class TestOrgAcronym:
    def test_initials(self) -> None:
        assert hd._org_initials("Zorbal Régionale Quentrix") == "ZRQ"
        assert hd._org_initials("Zorbal de la Quentrix") == "ZQ"
        assert hd._org_initials("Zorbal d'Quentrix Vardel") == "ZQV"
        assert hd._org_initials("Zorbal & Quentrix") == "ZQ"
        assert hd._org_initials("Dr Zorbal Quentrix") == "ZQ"
        assert hd._org_initials("Zorbtech") is None
        assert hd._org_initials("Zorbtech technique") is None

    def test_acronym_of_an_org_of_the_document(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = (
            "Le rapport de Zorbal Régionale Quentrix est prêt.\n"
            "   - Participants ZRQ: le comité.\n"
            "ZRQ et le comité.\n"
        )
        org = _at(doc, "Zorbal Régionale Quentrix", "ORG")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[org])
        assert [s for t, ty, s in found if t == "ZRQ" and ty == "ORG"] == [
            doc.index("ZRQ"),
            doc.index("ZRQ", doc.index("ZRQ") + 1),
        ]

    @pytest.mark.parametrize(
        "line",
        [
            "Référence: PROP-2024-ZRQ-001",  # inside a reference code
            "ZRQs et le comité.",  # joined to a letter
            "zrq et le comité.",  # not all caps
        ],
    )
    def test_no_fire(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch, line: str
    ) -> None:
        doc = f"Le rapport de Zorbal Régionale Quentrix est prêt.\n{line}\n"
        org = _at(doc, "Zorbal Régionale Quentrix", "ORG")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[org])
        assert _types(found) == [("Zorbal Régionale Quentrix", "ORG")]

    def test_no_org_with_these_initials(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Le rapport est prêt.\nZRQ et le comité.\n"
        assert _detect(monkeypatch, detector, doc) == []

    @pytest.mark.parametrize(
        ("org", "token"),
        [("Corbal Ezran Oquel", "CEO"), ("Vardel Pemmon", "VP")],
    )
    def test_role_tokens_are_skipped(
        self,
        detector: HybridDetector,
        monkeypatch: pytest.MonkeyPatch,
        org: str,
        token: str,
    ) -> None:
        # a role acronym, or a VP prefix (refined rule, Lionel STOP R Q3)
        doc = f"Le rapport de {org} est prêt.\nLe {token} et le comité.\n"
        found = _detect(
            monkeypatch, detector, doc, spacy_entities=[_at(doc, org, "ORG")]
        )
        assert _types(found) == [(org, "ORG")]

    def test_covered_token_is_left_alone(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Le rapport de Zorbal Régionale Quentrix est prêt.\nZRQ Zorbtech.\n"
        spacy_entities = [
            _at(doc, "Zorbal Régionale Quentrix", "ORG"),
            _at(doc, "ZRQ Zorbtech", "ORG"),
        ]
        found = _detect(monkeypatch, detector, doc, spacy_entities=spacy_entities)
        assert ("ZRQ", "ORG") not in _types(found)

    def test_accents_are_folded(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = "Le rapport de Ébral Zorbtech est prêt.\nEZ et le comité.\n"
        found = _detect(
            monkeypatch,
            detector,
            doc,
            spacy_entities=[_at(doc, "Ébral Zorbtech", "ORG")],
        )
        assert ("EZ", "ORG") in _types(found)


class TestDocumentFirstName:
    def test_first_name_alone_after_the_full_name(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = (
            "Mme Zorbalia Quentrel rejoint le comité.\n   Zorbalia rejoint le bureau.\n"
        )
        person = _at(doc, "Mme Zorbalia Quentrel", "PERSON")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[person])
        assert ("Zorbalia", "PERSON", doc.index("   Zorbalia") + 3) in found

    def test_no_full_name_no_fire(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Le rapport est prêt.\n   Zorbalia rejoint le bureau.\n"
        assert _detect(monkeypatch, detector, doc) == []

    def test_one_token_person_does_not_seed(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = "Zorbalia rejoint le comité.\nZorbalia rejoint le bureau.\n"
        person = _at(doc, "Zorbalia", "PERSON")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[person])
        assert _persons(found) == ["Zorbalia"]

    def test_lower_case_and_covered_words_do_not_fire(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        doc = (
            "Zorbalia Quentrel rejoint le comité.\n"
            "Le bureau de zorbalia.\n"
            "Zorbalia Zorbtech et le comité.\n"
        )
        spacy_entities = [
            _at(doc, "Zorbalia Quentrel", "PERSON"),
            _at(doc, "Zorbalia Zorbtech", "ORG"),
        ]
        found = _detect(monkeypatch, detector, doc, spacy_entities=spacy_entities)
        assert _persons(found) == ["Zorbalia Quentrel"]

    @pytest.mark.parametrize(
        "doc",
        [
            "Pierre après pierre, le projet reste solide.",
            "Le rapport de Pierre et du comité est prêt.",
            "Blanche, la page du rapport reste sur le bureau.",
            "Une pierre sur le bureau du comité.",
            "Une page blanche pour le rapport.",
        ],
    )
    def test_common_words_in_a_document_naming_no_such_person(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch, doc: str
    ) -> None:
        # AC3 as read for AC5 ("never on a common-word use"); real dictionary
        doc = f"M. Zorbalia Quentrel a signé le rapport.\n{doc}\n"
        person = _at(doc, "M. Zorbalia Quentrel", "PERSON")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[person])
        assert _persons(found) == ["M. Zorbalia Quentrel"]

    def test_accepted_residual(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Lionel, STOP R Q2: a capitalised common word that is the first name
        # of a person named in the same document is offered (one more line to
        # reject, never a leak); the lower-case word is not
        doc = (
            "M. Pierre Quentrel a signé le rapport.\n"
            "Pierre après pierre, le projet reste solide.\n"
        )
        person = _at(doc, "M. Pierre Quentrel", "PERSON")
        found = _detect(monkeypatch, detector, doc, spacy_entities=[person])
        assert _persons(found) == ["M. Pierre Quentrel", "Pierre"]

    def test_events_carry_no_entity_text(
        self,
        detector: HybridDetector,
        first_names: NameDictionary,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        recorder = _LogRecorder()
        monkeypatch.setattr(hd, "logger", recorder)
        doc = "Zorbalia Quentrel de Zorbal Régionale Quentrix.\n" "Zorbalia et ZRQ.\n"
        spacy_entities = [
            _at(doc, "Zorbalia Quentrel", "PERSON"),
            _at(doc, "Zorbal Régionale Quentrix", "ORG"),
        ]
        _detect(monkeypatch, detector, doc, spacy_entities=spacy_entities)
        events = dict(
            (name, fields)
            for name, fields in recorder.events
            if name in ("org_acronym_added", "document_first_name_added")
        )
        assert events["org_acronym_added"] == {
            "start": 60,
            "end": 63,
            "org_start": 21,
            "org_end": 46,
        }
        assert events["document_first_name_added"] == {
            "start": 48,
            "end": 56,
            "person_start": 0,
            "person_end": 17,
        }
