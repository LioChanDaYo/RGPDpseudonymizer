"""Integrity checks for the NER benchmark annotations (Story 10.1, Task 5.5).

Covers the main corpus (``tests/test_corpus/annotations``) and the held-out
set (``tests/test_corpus/held_out/annotations``). Runs in normal CI: it reads
JSON and text files only and never imports ``tests.accuracy.conftest``
(which pulls in spaCy).

Failure messages carry file stems and offsets only, never entity text, so a
held-out failure cannot leak held-out strings into CI logs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CORPUS_DIR = Path(__file__).resolve().parent.parent / "test_corpus"

# set name -> (text directories, annotation directory)
ANNOTATION_SETS: dict[str, tuple[tuple[Path, ...], Path]] = {
    "main": (
        (
            CORPUS_DIR / "interview_transcripts",
            CORPUS_DIR / "business_documents",
        ),
        CORPUS_DIR / "annotations",
    ),
    "held_out": (
        (CORPUS_DIR / "held_out" / "documents",),
        CORPUS_DIR / "held_out" / "annotations",
    ),
}

ENTITY_TYPES = {"PERSON", "LOCATION", "ORG"}
ENTITY_KEYS = {"entity_text", "entity_type", "start_pos", "end_pos"}


def _text_paths(text_dirs: tuple[Path, ...]) -> dict[str, Path]:
    return {p.stem: p for d in text_dirs if d.exists() for p in d.glob("*.txt")}


def _annotation_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for set_name, (_, ann_dir) in ANNOTATION_SETS.items():
        files.extend((set_name, p) for p in sorted(ann_dir.glob("*.json")))
    return files


ANNOTATION_FILES = _annotation_files()


def test_annotation_sets_are_not_empty() -> None:
    counts = {name: 0 for name in ANNOTATION_SETS}
    for set_name, _ in ANNOTATION_FILES:
        counts[set_name] += 1
    assert counts["main"] == 25, f"main corpus: expected 25 files, got {counts}"
    assert counts["held_out"] >= 5, f"held-out: expected >= 5 files, got {counts}"


@pytest.mark.parametrize("set_name", sorted(ANNOTATION_SETS))
def test_every_text_has_annotations_and_vice_versa(set_name: str) -> None:
    text_dirs, ann_dir = ANNOTATION_SETS[set_name]
    texts = set(_text_paths(text_dirs))
    anns = {p.stem for p in ann_dir.glob("*.json")}
    assert texts == anns, (
        f"{set_name}: texts without annotations {sorted(texts - anns)}, "
        f"annotations without texts {sorted(anns - texts)}"
    )


@pytest.mark.parametrize(
    ("set_name", "ann_path"),
    ANNOTATION_FILES,
    ids=[f"{s}/{p.stem}" for s, p in ANNOTATION_FILES],
)
def test_annotation_file_integrity(set_name: str, ann_path: Path) -> None:
    text_dirs, _ = ANNOTATION_SETS[set_name]
    stem = ann_path.stem
    text_path = _text_paths(text_dirs)[stem]
    text = text_path.read_text(encoding="utf-8")  # LF-normalized, as the scorer
    data = json.loads(ann_path.read_text(encoding="utf-8"))
    where = f"{set_name}/{stem}"

    assert set(data) == {"document_name", "entities"}, f"{where}: top-level keys"
    assert data["document_name"] == f"{stem}.txt", f"{where}: document_name"
    entities = data["entities"]
    assert isinstance(entities, list), f"{where}: entities is not a list"

    seen: set[tuple[str, str, int, int]] = set()
    for i, e in enumerate(entities):
        at = f"{where} entry {i}"
        assert set(e) == ENTITY_KEYS, f"{at}: keys"
        start, end, etype = e["start_pos"], e["end_pos"], e["entity_type"]
        span = f"{at} [{start}:{end}]"
        assert etype in ENTITY_TYPES, f"{span}: unknown entity_type"
        assert isinstance(start, int) and isinstance(end, int), f"{span}: offsets"
        assert 0 <= start < end <= len(text), f"{span}: offsets out of range"
        assert text[start:end] == e["entity_text"], f"{span}: text/offset mismatch"
        assert (
            e["entity_text"] == e["entity_text"].strip()
        ), f"{span}: leading or trailing whitespace"
        key = (e["entity_text"], etype, start, end)
        assert key not in seen, f"{span}: exact duplicate"
        seen.add(key)

    # Overlaps: same type never (G5); cross type only LOCATION inside ORG (G7).
    for i, a in enumerate(entities):
        for j in range(i + 1, len(entities)):
            b = entities[j]
            if not (a["start_pos"] < b["end_pos"] and b["start_pos"] < a["end_pos"]):
                continue
            pair = (
                f"{where} [{a['start_pos']}:{a['end_pos']}] {a['entity_type']} / "
                f"[{b['start_pos']}:{b['end_pos']}] {b['entity_type']}"
            )
            assert a["entity_type"] != b["entity_type"], f"{pair}: same-type overlap"
            org, loc = (a, b) if a["entity_type"] == "ORG" else (b, a)
            assert (
                org["entity_type"] == "ORG"
                and loc["entity_type"] == "LOCATION"
                and org["start_pos"] <= loc["start_pos"]
                and loc["end_pos"] <= org["end_pos"]
            ), f"{pair}: cross-type overlap other than LOCATION inside ORG"
