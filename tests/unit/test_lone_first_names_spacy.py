"""Story 14.1 with the real spaCy model: lone first names in short texts.

The sample's first names are read from the default pseudonym library at run
time and are never written here; a failure gives counts and positions in the
sample, never a name. A name is "missed" when no PERSON, LOCATION or ORG
detection overlaps its characters.
"""

from __future__ import annotations

import json

import pytest

from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.nlp.model_names import resolve_spacy_model
from gdpr_pseudonymizer.resources import PSEUDONYMS_DIR

pytestmark = pytest.mark.spacy

SHORT_TEXTS = {
    "merci": "Merci {} pour votre aide.",
    "reponse": "Réponse de {} : d'accord.",
    "cordialement": "Cordialement,\n{}",
    "email": "Bonjour,\nLe rapport est prêt, {} a signé le contrat.",
}
TITLE_TEXT = "Le rapport de M. {} est prêt."


@pytest.fixture(scope="module")
def detector() -> HybridDetector:
    model = resolve_spacy_model("spacy")
    detector = HybridDetector(default_model=model)
    detector.load_model(model)
    return detector


def _library() -> dict[str, list[str]]:
    data = json.loads((PSEUDONYMS_DIR / "neutral.json").read_text(encoding="utf-8"))
    first_names: dict[str, list[str]] = data["first_names"]
    return first_names


def _short_text_sample() -> list[str]:
    """The first 50 male and the first 50 female names, in file order."""
    library = _library()
    return library["male"][:50] + library["female"][:50]


def _title_sample() -> list[str]:
    """The first 100 names, male then female, in file order."""
    library = _library()
    return (library["male"] + library["female"])[:100]


@pytest.mark.parametrize("sentence", list(SHORT_TEXTS))
def test_sample_names_in_short_texts(detector: HybridDetector, sentence: str) -> None:
    template = SHORT_TEXTS[sentence]
    start = template.index("{}")
    missed = []
    for position, name in enumerate(_short_text_sample()):
        end = start + len(name)
        found = detector.detect_entities(template.format(name))
        if not any(
            e.entity_type in ("PERSON", "LOCATION", "ORG")
            and e.start_pos < end
            and start < e.end_pos
            for e in found
        ):
            missed.append(position)
    assert not missed, f"{len(missed)} of 100 sample names missed"


def test_title_kept_whole(detector: HybridDetector) -> None:
    """« M. X » kept whole: every name that has a PERSON starting at « M. »
    without the rule keeps it with the rule, and the rule puts no PERSON on
    X alone. "Without the rule" is the same detector with the rule switched
    off, so the control reads today's spaCy on every platform."""
    title_at = TITLE_TEXT.index("M.")
    start = TITLE_TEXT.index("{}")

    def readings() -> tuple[set[int], set[int]]:
        whole: set[int] = set()
        alone: set[int] = set()
        for position, name in enumerate(_title_sample()):
            end = start + len(name)
            persons = [
                e
                for e in detector.detect_entities(TITLE_TEXT.format(name))
                if e.entity_type == "PERSON"
            ]
            if any(e.start_pos == title_at and e.end_pos >= end for e in persons):
                whole.add(position)
            if any(e.start_pos == start for e in persons):
                alone.add(position)
        return whole, alone

    with pytest.MonkeyPatch.context() as patch:
        # raising=False: before Story 14.1 there is no rule to switch off
        patch.setattr(detector, "_lone_first_names", lambda *args: [], raising=False)
        whole_without, alone_without = readings()
    whole_with, alone_with = readings()

    assert whole_without
    assert whole_without <= whole_with, sorted(whole_without - whole_with)
    assert alone_with <= alone_without, sorted(alone_with - alone_without)
