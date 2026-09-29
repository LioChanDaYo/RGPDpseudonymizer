"""
Unit tests for spaCy model name resolution
"""

import pytest

from gdpr_pseudonymizer.nlp.model_names import (
    DEFAULT_SPACY_MODEL,
    is_spacy_package_name,
    resolve_spacy_model,
)


@pytest.mark.parametrize(
    "name",
    ["fr_core_news_lg", "en_core_web_trf", "en_core_web_sm", "xx_ent_wiki_sm"],
)
def test_valid_package_names(name: str) -> None:
    """Real spaCy package names are accepted."""
    assert is_spacy_package_name(name)


@pytest.mark.parametrize(
    "name",
    ["spacy", "gui", "unknown_model", "--upgrade", "en core web", "EN_core_web", ""],
)
def test_invalid_package_names(name: str) -> None:
    """Backend names, flags and malformed names are rejected."""
    assert not is_spacy_package_name(name)


def test_resolve_legacy_spacy_to_default() -> None:
    """The legacy backend value "spacy" keeps selecting the French model."""
    assert resolve_spacy_model("spacy") == DEFAULT_SPACY_MODEL == "fr_core_news_lg"


def test_resolve_package_name_passes_through() -> None:
    """A spaCy package name selects that model."""
    assert resolve_spacy_model("en_core_web_trf") == "en_core_web_trf"
