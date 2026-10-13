"""Final-exam leakage guard (Story 10.6 PR B, AC7, B3.3).

The plain-text sibling of ``test_held_out_leakage.py``. It fails if a
final-exam-only entity string shows up in the detector resources
(``gdpr_pseudonymizer/resources/**``) or in the unit tests (``tests/unit/**``).

* "Final-exam-only" means a string from the committed final-exam annotations
  (``tests/test_corpus/final_exam/annotations/``) that does not occur in the
  main-corpus texts, normalized as the scorer does (``match_key``).
* Matching, the search trees and the per-file allowlist (path, sha256 of the
  key) are the held-out guard's own. The allowlist lives in
  ``final_exam_leakage_allowlist.json``; every entry needs Lionel's recorded
  approval (B11.2). Hits inside that file are dropped.
* Failure messages report file paths and hashes, never the string.
* Until the final exam is committed (B11), the guard skips.

Only helper names are imported from the held-out guard, never a ``test_*``
function, so pytest does not collect the held-out tests twice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.test_held_out_leakage import (
    MAIN_TEXT_DIRS,
    ROOT,
    SEARCH_TREES,
    find_leaks,
    load_allowlist,
    match_key,
    string_hash,
    token_string,
    unallowed_leaks,
)

FINAL_EXAM_ANNOTATIONS = ROOT / "tests" / "test_corpus" / "final_exam" / "annotations"
FINAL_EXAM_ALLOWLIST = (
    Path(__file__).resolve().parent / "final_exam_leakage_allowlist.json"
)


def final_exam_committed(annotations_dir: Path = FINAL_EXAM_ANNOTATIONS) -> bool:
    """The guard runs once the final-exam annotations are committed (B11)."""
    return annotations_dir.is_dir()


def final_exam_only_keys(
    annotations_dir: Path = FINAL_EXAM_ANNOTATIONS,
    main_text_dirs: tuple[Path, ...] = MAIN_TEXT_DIRS,
) -> set[str]:
    """Normalized final-exam strings whose tokens do not occur in the main corpus."""
    main = token_string(
        " ".join(
            p.read_text(encoding="utf-8")
            for d in main_text_dirs
            for p in sorted(d.glob("*.txt"))
        )
    )
    keys: set[str] = set()
    for path in sorted(annotations_dir.glob("*.json")):
        for e in json.loads(path.read_text(encoding="utf-8"))["entities"]:
            key = match_key(e["entity_text"], e["entity_type"])
            if token_string(key).strip() and token_string(key) not in main:
                keys.add(key)
    return keys


def final_exam_leaks(
    keys: set[str],
    trees: tuple[Path, ...] = SEARCH_TREES,
    root: Path = ROOT,
    allowlist_path: Path = FINAL_EXAM_ALLOWLIST,
) -> list[tuple[str, str]]:
    """Unallowed (path, sha256 of key) hits, without hits inside the allowlist."""
    own = (
        allowlist_path.resolve().relative_to(root.resolve()).as_posix()
        if allowlist_path.resolve().is_relative_to(root.resolve())
        else None
    )
    hits = [hit for hit in find_leaks(keys, trees, root) if hit[0] != own]
    allowlist = load_allowlist(allowlist_path) if allowlist_path.exists() else set()
    return unallowed_leaks(hits, allowlist)


@pytest.mark.skipif(
    not final_exam_committed(), reason="final exam not committed yet (B11)"
)
def test_final_exam_set_has_final_exam_only_strings() -> None:
    assert len(final_exam_only_keys()) > 0, "no final-exam-only strings found"


@pytest.mark.skipif(
    not final_exam_committed(), reason="final exam not committed yet (B11)"
)
def test_no_final_exam_only_string_in_resources_or_unit_tests() -> None:
    leaks = final_exam_leaks(final_exam_only_keys())
    assert not leaks, (
        "Final-exam-only strings found in resources or unit tests "
        "(path, sha256 of the normalized string): "
        + "; ".join(f"{p} {h}" for p, h in leaks)
    )


# ---------------------------------------------------------------------------
# Self-tests, invented strings only.
# ---------------------------------------------------------------------------

_KEY = match_key("Zorbalia Quentrel", "PERSON")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _annotation(path: Path, entities: list[tuple[str, str]]) -> None:
    _write(
        path,
        json.dumps(
            {
                "document_name": path.stem + ".txt",
                "entities": [
                    {"entity_text": t, "entity_type": k, "start_pos": 0, "end_pos": 1}
                    for t, k in entities
                ],
            }
        ),
    )


def test_guard_states(tmp_path: Path) -> None:
    assert not final_exam_committed(tmp_path / "final_exam" / "annotations")
    (tmp_path / "final_exam" / "annotations").mkdir(parents=True)
    assert final_exam_committed(tmp_path / "final_exam" / "annotations")


def test_final_exam_only_rule(tmp_path: Path) -> None:
    _write(tmp_path / "main" / "a.txt", "Quentrix SA ouvre un site à Zorbaville.")
    _annotation(
        tmp_path / "ann" / "dummy_01.json",
        [
            ("Mme Zorbalia Quentrel", "PERSON"),
            ("Quentrix SA", "ORG"),
            ("à Zorbaville", "LOCATION"),
        ],
    )
    keys = final_exam_only_keys(tmp_path / "ann", (tmp_path / "main",))
    assert keys == {"zorbalia quentrel"}


def test_guard_fires_on_planted_string(tmp_path: Path) -> None:
    _write(tmp_path / "resources" / "lexicon.json", '{"names": ["ZORBALIA  quentrel"]}')
    hits = final_exam_leaks(
        {_KEY}, (tmp_path / "resources",), tmp_path, tmp_path / "x.json"
    )
    assert hits == [("resources/lexicon.json", string_hash(_KEY))]


def test_guard_ignores_partial_token_match(tmp_path: Path) -> None:
    _write(tmp_path / "words.txt", "zorbaliaquentrel")
    assert final_exam_leaks({_KEY}, (tmp_path,), tmp_path, tmp_path / "x.json") == []


def test_guard_key_spanning_punctuation_fires(tmp_path: Path) -> None:
    key = match_key("Quentrix-Zorbal", "ORG")
    _write(tmp_path / "words.txt", "voir quentrix zorbal ici")
    hits = final_exam_leaks({key}, (tmp_path,), tmp_path, tmp_path / "x.json")
    assert hits == [("words.txt", string_hash(key))]


def test_allowlist_is_per_file(tmp_path: Path) -> None:
    for name in ("old.json", "new.json"):
        _write(tmp_path / name, "Zorbalia Quentrel")
    allow = tmp_path / "allow" / "final_exam_leakage_allowlist.json"
    _write(
        allow,
        json.dumps({"entries": [{"path": "old.json", "sha256": string_hash(_KEY)}]}),
    )
    hits = final_exam_leaks({_KEY}, (tmp_path,), tmp_path, allow)
    assert hits == [("new.json", string_hash(_KEY))]


def test_hits_inside_own_allowlist_are_dropped(tmp_path: Path) -> None:
    allow = tmp_path / "final_exam_leakage_allowlist.json"
    _write(allow, json.dumps({"entries": [], "note": "Zorbalia Quentrel"}))
    assert final_exam_leaks({_KEY}, (tmp_path,), tmp_path, allow) == []


def test_module_imports_no_held_out_test_function() -> None:
    imported = [
        name
        for name, value in globals().items()
        if name.startswith("test_")
        and getattr(value, "__module__", "") == "tests.unit.test_held_out_leakage"
    ]
    assert imported == []
