"""The word before a place (Story 13.1, mechanism 1 and 2).

``word_before`` reads the word right before a place, or at the head of its
span, as one of ``place_names``' words; ``draw_words`` gives each place of a
document the one word its draw uses: the first epic word of its
occurrences in document order, else the first of Lionel's Q4 (b) words,
else no such word. No logging.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping

from gdpr_pseudonymizer.core.custom_pseudonym import NameKey
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.place_names import (
    DE,
    DU,
    EN,
    EPIC_WORDS,
    LA,
    LE,
    LES,
    NO_WORD,
    Q4_WORDS,
    REGION,
    A,
    D,
    L,
)

_APOSTROPHES = "'’"

# The words at the head of a span: those _compute_replacement_prefix keeps
# as a prefix, each followed by a space (as FRENCH_PREPOSITION_PATTERN
# requires), and a lone capital « A »; « d' », « l' » (either apostrophe)
# are read before them
_SPAN_HEAD = re.compile(r"(aux|au|du|des|de|à|en)\s", re.IGNORECASE)
_SPAN_HEAD_A = re.compile(r"A\s")

# A word read before the place, capitals ignored (a lone capital « A » is
# read apart: a lowercase « a » is the verb)
_WORDS = {
    "à": A,
    "en": EN,
    "de": DE,
    "du": DU,
    "au": DU,
    "le": LE,
    "la": LA,
    "les": LES,
    "des": LES,
    "aux": LES,
    "région": REGION,
}


def _word(run: str) -> str:
    if run == "A":
        return A
    return _WORDS.get(unicodedata.normalize("NFC", run).lower(), NO_WORD)


def word_before(text: str, start: int, end: int) -> str:
    """The word before the place at ``text[start:end]``, as a
    ``place_names`` word (``NO_WORD`` when none of them stands there).

    A word at the head of the span is read first (« en Vellionie »); then
    the text before the span, across spaces, tabs and line breaks. A
    position outside the text reads as no such word.
    """
    if start < 0 or end > len(text) or start > end:
        return NO_WORD
    span = text[start:end].lstrip()
    if len(span) > 1 and span[1] in _APOSTROPHES and span[0] in "dDlL":
        return D if span[0] in "dD" else L
    head = _SPAN_HEAD.match(span)
    if head is not None:
        return _word(head.group(1))
    if _SPAN_HEAD_A.match(span):
        return A
    i = start
    while i > 0 and text[i - 1].isspace():
        i -= 1
    if i > 0 and text[i - 1] in _APOSTROPHES:
        j = i - 1
        if j > 0 and text[j - 1] in "dDlL" and (j == 1 or not text[j - 2].isalpha()):
            return D if text[j - 1] in "dD" else L
        return NO_WORD
    j = i
    while j > 0 and text[j - 1].isalpha():
        j -= 1
    return _word(text[j:i])


def draw_words(
    entities: Iterable[DetectedEntity],
    document_text: str,
    cells: Mapping[str, str] | None = None,
) -> dict[NameKey, str]:
    """Each place's word (mechanism 2), keyed by (mapping key, "LOCATION").

    An occurrence is read in its own cell when ``cells`` holds its
    ``context_label``, else in ``document_text``. Occurrences are taken in
    document order (the cell's index in ``cells``, then the position). A
    place's word is the first epic word of its occurrences; if none has
    one, the first Q4 word; else no such word.
    """
    order = {label: index for index, label in enumerate(cells or {})}
    places = [entity for entity in entities if entity.entity_type == "LOCATION"]

    def position(entity: DetectedEntity) -> tuple[int, int]:
        label = entity.context_label
        return (order.get(label, 0) if label is not None else 0, entity.start_pos)

    words: dict[NameKey, list[str]] = {}
    for entity in sorted(places, key=position):
        label = entity.context_label
        text = (
            cells[label]
            if cells is not None and label is not None and label in cells
            else document_text
        )
        name = (mapping_key(entity.text, "LOCATION"), "LOCATION")
        words.setdefault(name, []).append(
            word_before(text, entity.start_pos, entity.end_pos)
        )
    chosen: dict[NameKey, str] = {}
    for name, read in words.items():
        epic = [word for word in read if word in EPIC_WORDS]
        q4 = [word for word in read if word in Q4_WORDS]
        chosen[name] = epic[0] if epic else q4[0] if q4 else NO_WORD
    return chosen
