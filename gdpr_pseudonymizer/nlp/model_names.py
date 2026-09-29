"""
spaCy model name resolution

Lightweight on purpose: imported by CLI config validation, so it must not
import spaCy.
"""

from __future__ import annotations

import re

DEFAULT_SPACY_MODEL = "fr_core_news_lg"

# spaCy package names: language code + underscore-separated parts
# (fr_core_news_lg, en_core_web_trf, xx_ent_wiki_sm). Strict on purpose: the
# name is passed to `python -m spacy download` when the model is missing.
_SPACY_PACKAGE_NAME = re.compile(r"^[a-z]{2,3}(_[a-z0-9]+)+$")


def is_spacy_package_name(name: str) -> bool:
    """Check if a string is a well-formed spaCy model package name.

    Args:
        name: Candidate model name (e.g., "en_core_web_trf")

    Returns:
        True if the name looks like a spaCy package name
    """
    return bool(_SPACY_PACKAGE_NAME.match(name))


def resolve_spacy_model(model_name: str) -> str:
    """Map a configured model value to the spaCy package to load.

    The legacy backend name "spacy" (and any other non-package value) maps to
    the default French model, so existing configurations keep working.

    Args:
        model_name: Value from config or --model (e.g., "spacy", "en_core_web_trf")

    Returns:
        spaCy package name to load
    """
    if is_spacy_package_name(model_name):
        return model_name
    return DEFAULT_SPACY_MODEL
