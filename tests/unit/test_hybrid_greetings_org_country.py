"""spaCy-free unit tests for Story 10.4 (greetings, organisation + place).

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
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector, load_salutations
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary
from gdpr_pseudonymizer.resources import SALUTATIONS_PATH

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
