"""Which library places fit the word before a place (Story 13.1).

The French lists L1 to L6 of Story 13.1, approved by Lionel word for word on
2026-11-20, with his Q4 (b), Q5 (b), R1 and R2: the names never drawn (L1),
the gender of the `neutral` regions (L2), the names each word draws, tier by
tier (L3, L3b), which list of a theme plays the city and which the region
(L4), and how a first letter is classed (L5).

Pure functions over a theme's place lists, read at draw time from the loaded
library: tiers keep the library's own order (key order, then list order).
No logging.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence

from gdpr_pseudonymizer.core.custom_pseudonym import fold

# The words before a place, valued as the words themselves (Story 13.1,
# mechanism 1): the epic's words...
A = "à"
EN = "en"
DE = "de"
D = "d'"
DU = "du"  # « du » and « au »
NO_WORD = ""
# ... and Lionel's Q4 (b) words
LE = "le"
LA = "la"
L = "l'"
LES = "les"  # « les », « des » and « aux »
REGION = "région"

EPIC_WORDS = (A, EN, DE, D, DU)
Q4_WORDS = (LE, LA, L, LES, REGION)

_CITY = "city"
_REGION = "region"

# L4: which list of a theme is city-like and which region-like
_ROLES: dict[str, dict[str, str]] = {
    "neutral": {"cities": _CITY, "countries": _REGION, "regions": _REGION},
    "star_wars": {"cities": _CITY, "planets": _REGION, "regions": _REGION},
    "lotr": {"cities": _CITY, "planets": _CITY, "regions": _REGION},
}

# L1: a name that starts with one of these (folded) is never drawn
_ARTICLES = ("le ", "la ", "les ", "l'", "the ")

# L2: the `neutral` regions that are masculine (the 4 of the library and
# Lionel's Q5 (b) 15) or plural; every other `neutral` region is feminine
_MASCULINE = frozenset(
    fold(name)
    for name in (
        "Grand Est",
        "Centre-Val de Loire",
        "Languedoc",
        "Limousin",
        "Berry",
        "Poitou",
        "Périgord",
        "Quercy",
        "Vexin",
        "Beaujolais",
        "Gévaudan",
        "Rouergue",
        "Nivernais",
        "Médoc",
        "Cotentin",
        "Velay",
        "Béarn",
        "Roussillon",
        "Vercors",
    )
)
_PLURAL = frozenset(fold(name) for name in ("Hauts-de-France", "Pays de la Loire"))

_VOWELS = "aeiou"


@functools.lru_cache(maxsize=4096)
def _folded(name: str) -> str:
    """The comparison form of a name, the typographic apostrophe read as
    the straight one."""
    return fold(name.replace("’", "'"))


def has_article(name: str) -> bool:
    """L1: the name starts with « Le », « La », « Les », « L' » or « The »
    followed by a word."""
    return _folded(name).startswith(_ARTICLES)


def starts_with_vowel(name: str) -> bool:
    """L5: « a », « e », « i », « o », « u » are vowels, accents ignored;
    « h » is a consonant; « y » is a vowel before a consonant and a
    consonant before a vowel. Anything else (a digit) counts as a
    consonant."""
    folded = _folded(name).lstrip()
    if not folded:
        return False
    first = folded[0]
    if first == "y":
        return len(folded) > 1 and folded[1].isalpha() and folded[1] not in _VOWELS
    return first in _VOWELS


def _roles(theme: str | None) -> dict[str, str]:
    return _ROLES.get(theme or "", {})


def _role(theme: str | None, key: str) -> str:
    """A list's role: L4's, else `cities` city-like and any other list
    region-like."""
    return _roles(theme).get(key, _CITY if key == "cities" else _REGION)


def _names(theme: str | None, locations: Mapping[str, object], role: str) -> list[str]:
    """The names of every list of that role, in the library's order,
    without the names L1 never draws."""
    names: list[str] = []
    for key, values in locations.items():
        if _role(theme, key) != role or not isinstance(values, Sequence):
            continue
        names.extend(
            value
            for value in values
            if isinstance(value, str) and not has_article(value)
        )
    return names


def _split(names: Sequence[str], vowel: bool) -> list[list[str]]:
    """The names of that letter class, then the others."""
    same = [name for name in names if starts_with_vowel(name) == vowel]
    other = [name for name in names if starts_with_vowel(name) != vowel]
    return [same, other]


def _of_class(names: Sequence[str], vowel: bool) -> list[str]:
    return [name for name in names if starts_with_vowel(name) == vowel]


def draw_tiers(
    theme: str | None,
    locations: Mapping[str, object],
    place_word: str | None,
    real_place: str | None,
) -> list[list[str]]:
    """The names a new place may get after ``place_word``, tier by tier, the
    first tier first (L3, L3b, L4, with the PO's note on « du » and « au »).

    ``place_word`` None (or any other value) is no such word;
    ``real_place`` None counts as starting with a consonant. For one of
    Q4's words, its own tiers come first, then the no-word row's tiers
    without the names already in an earlier tier. Empty tiers are dropped.
    """
    word = place_word if place_word in EPIC_WORDS + Q4_WORDS else NO_WORD
    vowel = starts_with_vowel(real_place) if real_place else False
    cities = _names(theme, locations, _CITY)
    regions = _names(theme, locations, _REGION)
    if theme == "neutral":
        masculine = [name for name in regions if _folded(name) in _MASCULINE]
        plural = [name for name in regions if _folded(name) in _PLURAL]
        feminine = [
            name
            for name in regions
            if _folded(name) not in _MASCULINE and _folded(name) not in _PLURAL
        ]
    else:
        # Invented names have no French gender (L4)
        masculine, plural, feminine = list(regions), list(regions), list(regions)

    no_word = _split(cities, vowel) + _split(regions, vowel)
    tiers: list[list[str]]
    if word == A:
        tiers = _split(cities, vowel)
    elif word == EN:
        tiers = _split(feminine, vowel)
    elif word == DE:
        tiers = [_of_class(cities, False), _of_class(feminine, False)]
    elif word == D:
        tiers = [_of_class(cities, True), _of_class(feminine, True)]
    elif word == DU:
        tiers = [_of_class(masculine, False)]
    elif word == NO_WORD:
        tiers = no_word
    else:
        if word in (LE, LA):
            own = (
                [masculine if word == LE else _of_class(feminine, False)]
                if theme == "neutral"
                else [_of_class(regions, False)]
            )
        elif word == L:
            own = [_of_class(regions, True)]
        elif word == LES:
            own = [plural] if theme == "neutral" else _split(regions, vowel)
        else:  # REGION
            own = _split(regions, vowel)
        tried = {name for tier in own for name in tier}
        tiers = own + [[name for name in tier if name not in tried] for tier in no_word]
    return [tier for tier in tiers if tier]


def fits(
    theme: str | None,
    locations: Mapping[str, object],
    value: str,
    place_word: str | None,
) -> bool:
    """Whether ``value`` is one of the names a draw after ``place_word`` may
    give (any letter class). After one of Q4's words this is every name L1
    does not exclude, as a draw that fell back to the no-word row gives."""
    return any(value in tier for tier in draw_tiers(theme, locations, place_word, None))
