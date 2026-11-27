"""spaCy-free unit tests for Story 14.1 (a lone first name in a short text).

The rule Lionel chose (Q6, "yes, wherever it stands alone"): a word that
starts with a capital and is a first name of the default pseudonym library
or of ``french_names.json`` becomes a PERSON wherever it stands alone. It
stands alone unless a PERSON already holds it, or a place or organisation
holds it together with another word of the same line that is not a title.

Unmarked as ``spacy`` on purpose: ``HybridDetector()`` loads no spaCy model,
and ``detect_entities`` runs with stubbed detectors (Story 10.4's pattern).
Names are invented (Zorbalia, Zorbàlia, Quentrel, Quentrix, Zorbtech) and
injected into the rule's list through its loader and into the name
dictionary; the other words occur in the main-corpus text, except the
greeting "Salut", which Lionel approved (Story 14.1, Q3 (b)).
"""

from __future__ import annotations

import json

import pytest

from gdpr_pseudonymizer.nlp import hybrid_detector as hd
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary
from gdpr_pseudonymizer.resources import FRENCH_NAMES_PATH, PSEUDONYMS_DIR

INVENTED_FIRST_NAMES = {"Zorbalia", "Quentrel"}
# The rule's list holds folded names (accents removed, case-folded)
INVENTED_LIST = frozenset({"zorbalia", "quentrel"})


@pytest.fixture
def detector() -> HybridDetector:
    return HybridDetector()


@pytest.fixture
def invented_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule's list and the name dictionary, reduced to invented names.

    ``raising=False``: the loader does not exist before Story 14.1, so a
    marked case fails at its assert, never at an ``AttributeError``.
    """
    names = NameDictionary()
    names.first_names = set(INVENTED_FIRST_NAMES)
    names.last_names = set()
    monkeypatch.setattr(hd, "_default_name_dictionary", lambda: names)
    monkeypatch.setattr(
        hd, "load_lone_first_names", lambda: INVENTED_LIST, raising=False
    )


def _at(doc: str, text: str, entity_type: str, source: str = "spacy") -> DetectedEntity:
    start = doc.index(text)
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
    spacy_entities: list[tuple[str, str]],
    regex_entities: list[tuple[str, str]],
) -> list[DetectedEntity]:
    _stub_pipeline(
        monkeypatch,
        detector,
        [_at(doc, text, entity_type) for text, entity_type in spacy_entities],
        [_at(doc, text, entity_type, "regex") for text, entity_type in regex_entities],
    )
    return detector.detect_entities(doc)


# ---------------------------------------------------------------------------
# L1: a lone first name is found
# ---------------------------------------------------------------------------

# case: (text, spaCy entities, regex entities, the names that become PERSONs)
FOUND: dict[
    str, tuple[str, list[tuple[str, str]], list[tuple[str, str]], list[str]]
] = {
    "merci": ("Merci Zorbalia pour votre aide.", [], [], ["Zorbalia"]),
    "reponse": ("Réponse de Zorbalia : d'accord.", [], [], ["Zorbalia"]),
    "cordialement": ("Cordialement,\nZorbalia", [], [], ["Zorbalia"]),
    "email": (
        "Bonjour,\nLe rapport est prêt, Zorbalia a signé le contrat.",
        [],
        [],
        ["Zorbalia"],
    ),
    # Accents ignored: the list holds "zorbalia"
    "accent": ("Merci Zorbàlia pour votre aide.", [], [], ["Zorbàlia"]),
    "sentence_start": ("Zorbalia a signé le contrat.", [], [], ["Zorbalia"]),
    # No detection holds "M. Zorbalia": the title is not a name
    "after_title": ("Le rapport de M. Zorbalia est prêt.", [], [], ["Zorbalia"]),
    "dash": ("— Zorbalia", [], [], ["Zorbalia"]),
    "salut": ("Salut Zorbalia,", [], [], ["Zorbalia"]),
    "capitals": ("ZORBALIA a signé le contrat.", [], [], ["ZORBALIA"]),
    "two_names": (
        "Merci Zorbalia et Quentrel pour votre aide.",
        [],
        [],
        ["Zorbalia", "Quentrel"],
    ),
    # A word on the next line is not part of the name
    "next_line_role": (
        "Cordialement,\nZorbalia\nResponsable du projet",
        [("Zorbalia\nResponsable", "ORG")],
        [],
        ["Zorbalia"],
    ),
    # A title is not another word of the name (PO v1.7)
    "title_in_an_org": (
        "Le Dr Zorbalia a signé le contrat.",
        [("Dr Zorbalia", "ORG")],
        [],
        ["Zorbalia"],
    ),
    # Lionel's Q4: a name already found as a place also gets a person
    "on_a_place": (
        "Réponse de Zorbalia : d'accord.",
        [("Zorbalia", "LOCATION")],
        [],
        ["Zorbalia"],
    ),
}


@pytest.mark.parametrize("case", list(FOUND))
def test_lone_first_name_found(
    monkeypatch: pytest.MonkeyPatch,
    detector: HybridDetector,
    invented_names: None,
    case: str,
) -> None:
    doc, spacy_entities, regex_entities, names = FOUND[case]
    found = _detect(monkeypatch, detector, doc, spacy_entities, regex_entities)
    persons = sorted(
        (e.text, e.start_pos, e.end_pos, e.source)
        for e in found
        if e.entity_type == "PERSON"
    )
    assert persons == sorted(
        (name, doc.index(name), doc.index(name) + len(name), "regex") for name in names
    )
    if case == "on_a_place":
        # The place stays, and the merge flags the person on its exact span
        places = [(e.text, e.start_pos) for e in found if e.entity_type == "LOCATION"]
        assert places == [("Zorbalia", doc.index("Zorbalia"))]
        assert all(e.is_ambiguous for e in found if e.entity_type == "PERSON")


# ---------------------------------------------------------------------------
# L2: what stays as it is (controls)
# ---------------------------------------------------------------------------

# case: (text, spaCy entities, regex entities, expected PERSONs, kept type)
STAYS: dict[
    str,
    tuple[str, list[tuple[str, str]], list[tuple[str, str]], list[str], str | None],
] = {
    # A PERSON holds the name: the title stays with it
    "in_a_person": (
        "Le rapport de M. Zorbalia est prêt.",
        [],
        [("M. Zorbalia", "PERSON")],
        ["M. Zorbalia"],
        None,
    ),
    # Part of a longer organisation name on its line
    "in_a_longer_org": (
        "Le contrat avec Zorbtech Zorbalia est signé.",
        [("Zorbtech Zorbalia", "ORG")],
        [],
        [],
        "ORG",
    ),
    # Known limitation: spaCy's span swallows the greeting; the name stays
    # replaced as part of the organisation, with no person row
    "swallowed_greeting": (
        "Salut Zorbalia,",
        [("Salut Zorbalia", "ORG")],
        [],
        [],
        "ORG",
    ),
    "lowercase": ("merci zorbalia pour votre aide.", [], [], [], None),
    "not_listed": ("Merci Quentrix pour votre aide.", [], [], [], None),
    "compound": ("Merci Zorbalia-Quentrix pour votre aide.", [], [], [], None),
    # An article is another word of the place name (PO v1.7)
    "article_place": (
        "Le contrat avec La Zorbalia est signé.",
        [("La Zorbalia", "LOCATION")],
        [],
        [],
        "LOCATION",
    ),
}


@pytest.mark.parametrize("case", list(STAYS))
def test_stays_as_today(
    monkeypatch: pytest.MonkeyPatch,
    detector: HybridDetector,
    invented_names: None,
    case: str,
) -> None:
    doc, spacy_entities, regex_entities, persons, kept = STAYS[case]
    found = _detect(monkeypatch, detector, doc, spacy_entities, regex_entities)
    assert [e.text for e in found if e.entity_type == "PERSON"] == persons
    if kept is not None:
        assert any(e.entity_type == kept for e in found)


# ---------------------------------------------------------------------------
# L4: the rule itself leaves a name a PERSON holds
# ---------------------------------------------------------------------------


def test_rule_leaves_a_name_a_person_holds(
    detector: HybridDetector, invented_names: None
) -> None:
    """Called directly: through ``detect_entities`` the merge keeps the longer
    of two nested PERSONs, which would hide a missing person guard."""
    rule = getattr(detector, "_lone_first_names", None)
    assert rule is not None
    doc = "Le rapport de M. Zorbalia est prêt."
    assert rule(doc, [], [_at(doc, "M. Zorbalia", "PERSON", "regex")]) == []
    doc = "Merci Zorbalia Quentrel pour votre aide."
    assert rule(doc, [_at(doc, "Zorbalia Quentrel", "PERSON")], []) == []


# ---------------------------------------------------------------------------
# L3: the list is its own, the union of both files
# ---------------------------------------------------------------------------


def test_list_is_the_union_of_both_files() -> None:
    loader = getattr(hd, "load_lone_first_names", None)
    assert loader is not None
    library = json.loads((PSEUDONYMS_DIR / "neutral.json").read_text(encoding="utf-8"))
    french = json.loads(FRENCH_NAMES_PATH.read_text(encoding="utf-8"))["first_names"]
    expected = {
        hd._fold(name) for names in library["first_names"].values() for name in names
    } | {hd._fold(name) for name in french}
    assert loader() == expected
    # The name dictionary is unchanged: the list is never merged into it
    assert hd._default_name_dictionary().first_names == set(french)
