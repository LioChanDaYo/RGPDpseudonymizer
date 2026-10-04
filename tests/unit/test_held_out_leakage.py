"""Held-out leakage guard (Story 10.1, Task 5.5b).

Fails if a held-out-only entity string shows up in the detector resources
(``gdpr_pseudonymizer/resources/**``) or in the unit tests (``tests/unit/**``).
That would mean a detector rule or test was fitted to the held-out set.

* "Held-out-only" means a string from the held-out annotations that does not
  occur in the main-corpus texts.
* Matching is case-insensitive, on whole tokens, after the scorer's
  normalization (``_match_key`` in ``tests/accuracy/conftest.py``,
  reimplemented here so this test never imports spaCy).
* Hits that already existed when the set was created (Story 10.1) are
  allowlisted in ``held_out_leakage_allowlist.json`` by (file path, sha256):
  the same string in any other file still fails (QA TEST-001). Only hashes
  are stored, so no held-out text lives outside ``tests/test_corpus/held_out/``. Adding to the allowlist needs
  Lionel's recorded approval in the story that does it.
* Failure messages report file paths and hashes, never the string.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = ROOT / "tests" / "test_corpus"
HELD_OUT_ANNOTATIONS = CORPUS_DIR / "held_out" / "annotations"
MAIN_TEXT_DIRS = (
    CORPUS_DIR / "interview_transcripts",
    CORPUS_DIR / "business_documents",
)
SEARCH_TREES = (ROOT / "gdpr_pseudonymizer" / "resources", ROOT / "tests" / "unit")
ALLOWLIST_PATH = Path(__file__).resolve().parent / "held_out_leakage_allowlist.json"

# Same patterns as gdpr_pseudonymizer/utils/french_patterns.py (copied, not
# imported, to keep this test independent of the package under test).
_TITLE = re.compile(
    r"\b(?:Docteur|Professeur|Madame|Monsieur|Mademoiselle|Maître|Dr\.?|Pr\.?"
    r"|Prof\.?|M\.?|Mme\.?|Mlle\.?|Me\.?)(?!\w)\s*",
    re.IGNORECASE,
)
_PREPOSITION = re.compile(
    r"^[\s]*(?:(?:d'|l')|(?:aux|au|des|du|de|à|en)\s+)", re.IGNORECASE
)
_TOKEN = re.compile(r"\w+")


def match_key(text: str, entity_type: str) -> str:
    """Scorer normalization: strip titles (and prepositions for LOCATION)."""
    while True:
        stripped = _TITLE.sub("", text).strip()
        if stripped == text:
            break
        text = stripped
    if entity_type == "LOCATION":
        text = _PREPOSITION.sub("", text).strip()
    return " ".join(text.lower().split())


def token_string(text: str) -> str:
    """Lower-cased whole tokens, space-separated and space-padded."""
    return " " + " ".join(_TOKEN.findall(text.lower())) + " "


def string_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def held_out_only_keys() -> set[str]:
    main = token_string(
        " ".join(
            p.read_text(encoding="utf-8")
            for d in MAIN_TEXT_DIRS
            for p in sorted(d.glob("*.txt"))
        )
    )
    keys: set[str] = set()
    for path in sorted(HELD_OUT_ANNOTATIONS.glob("*.json")):
        for e in json.loads(path.read_text(encoding="utf-8"))["entities"]:
            key = match_key(e["entity_text"], e["entity_type"])
            if token_string(key).strip() and token_string(key) not in main:
                keys.add(key)
    return keys


def _searched_files(
    trees: tuple[Path, ...] = SEARCH_TREES, exclude: Path = ALLOWLIST_PATH
) -> list[Path]:
    files = []
    for tree in trees:
        for p in sorted(tree.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p != exclude:
                files.append(p)
    return files


def find_leaks(
    keys: set[str] | None = None,
    trees: tuple[Path, ...] = SEARCH_TREES,
    root: Path = ROOT,
) -> list[tuple[str, str]]:
    """Return (file path relative to *root*, sha256 of key) for every hit."""
    if keys is None:
        keys = held_out_only_keys()
    hits: list[tuple[str, str]] = []
    for path in _searched_files(trees):
        try:
            content = token_string(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        for key in keys:
            if token_string(key) in content:
                hits.append((path.relative_to(root).as_posix(), string_hash(key)))
    return hits


def load_allowlist(path: Path = ALLOWLIST_PATH) -> set[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(e["path"], e["sha256"]) for e in data["entries"]}


def unallowed_leaks(
    hits: list[tuple[str, str]], allowlist: set[tuple[str, str]]
) -> list[tuple[str, str]]:
    return sorted({hit for hit in hits if hit not in allowlist})


def test_held_out_set_has_held_out_only_strings() -> None:
    assert len(held_out_only_keys()) > 0, "no held-out-only strings found"


def test_no_held_out_only_string_in_resources_or_unit_tests() -> None:
    leaks = unallowed_leaks(find_leaks(), load_allowlist())
    assert not leaks, (
        "Held-out-only strings found outside tests/test_corpus/held_out/ "
        "(path, sha256 of the normalized string): "
        + "; ".join(f"{p} {h}" for p, h in leaks)
    )


# ---------------------------------------------------------------------------
# Negative self-tests (QA TEST-002), synthetic strings only.
# ---------------------------------------------------------------------------

_SYNTH_KEY = match_key("Zorvik Quandel", "PERSON")


def test_guard_fires_on_planted_string_in_new_resource_file(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "new_lexicon.json").write_text(
        '{"names": ["ZORVIK  quandel"]}', encoding="utf-8"
    )
    hits = find_leaks({_SYNTH_KEY}, (resources,), tmp_path)
    assert unallowed_leaks(hits, set()) == [
        ("resources/new_lexicon.json", string_hash(_SYNTH_KEY))
    ]


def test_guard_ignores_partial_token_match(tmp_path: Path) -> None:
    (tmp_path / "words.txt").write_text("zorvikquandel", encoding="utf-8")
    assert find_leaks({_SYNTH_KEY}, (tmp_path,), tmp_path) == []


def test_allowlist_is_per_file(tmp_path: Path) -> None:
    for name in ("old.json", "new.json"):
        (tmp_path / name).write_text("Zorvik Quandel", encoding="utf-8")
    hits = find_leaks({_SYNTH_KEY}, (tmp_path,), tmp_path)
    allow = {("old.json", string_hash(_SYNTH_KEY))}
    assert unallowed_leaks(hits, allow) == [("new.json", string_hash(_SYNTH_KEY))]
