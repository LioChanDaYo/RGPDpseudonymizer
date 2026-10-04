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


def annotation_errors(text: str, data: object, where: str) -> list[str]:
    """Return integrity errors for one annotation file (empty list = valid).

    Messages carry the location (set/stem, entry index, offsets) only, never
    entity text.
    """
    errors: list[str] = []
    if not isinstance(data, dict) or set(data) != {"document_name", "entities"}:
        return [f"{where}: top-level keys"]
    if data["document_name"] != f"{where.split('/')[-1]}.txt":
        errors.append(f"{where}: document_name")
    entities = data["entities"]
    if not isinstance(entities, list):
        return errors + [f"{where}: entities is not a list"]

    seen: set[tuple[str, str, int, int]] = set()
    valid: list[dict[str, object]] = []
    for i, e in enumerate(entities):
        at = f"{where} entry {i}"
        if not isinstance(e, dict) or set(e) != ENTITY_KEYS:
            errors.append(f"{at}: keys")
            continue
        start, end, etype = e["start_pos"], e["end_pos"], e["entity_type"]
        span = f"{at} [{start}:{end}]"
        if etype not in ENTITY_TYPES:
            errors.append(f"{span}: unknown entity_type")
        if not (isinstance(start, int) and isinstance(end, int)):
            errors.append(f"{span}: offsets")
            continue
        if not 0 <= start < end <= len(text):
            errors.append(f"{span}: offsets out of range")
            continue
        if text[start:end] != e["entity_text"]:
            errors.append(f"{span}: text/offset mismatch")
        if e["entity_text"] != str(e["entity_text"]).strip():
            errors.append(f"{span}: leading or trailing whitespace")
        key = (str(e["entity_text"]), str(etype), start, end)
        if key in seen:
            errors.append(f"{span}: exact duplicate")
        seen.add(key)
        valid.append(e)

    # Overlaps: same type never (G5); cross type only LOCATION inside ORG (G7).
    for i, a in enumerate(valid):
        for b in valid[i + 1 :]:
            a_start, a_end = int(str(a["start_pos"])), int(str(a["end_pos"]))
            b_start, b_end = int(str(b["start_pos"])), int(str(b["end_pos"]))
            if not (a_start < b_end and b_start < a_end):
                continue
            pair = (
                f"{where} [{a_start}:{a_end}] {a['entity_type']} / "
                f"[{b_start}:{b_end}] {b['entity_type']}"
            )
            if a["entity_type"] == b["entity_type"]:
                errors.append(f"{pair}: same-type overlap")
                continue
            org, loc = (a, b) if a["entity_type"] == "ORG" else (b, a)
            nested = (
                org["entity_type"] == "ORG"
                and loc["entity_type"] == "LOCATION"
                and int(str(org["start_pos"])) <= int(str(loc["start_pos"]))
                and int(str(loc["end_pos"])) <= int(str(org["end_pos"]))
            )
            if not nested:
                errors.append(
                    f"{pair}: cross-type overlap other than LOCATION inside ORG"
                )
    return errors


@pytest.mark.parametrize(
    ("set_name", "ann_path"),
    ANNOTATION_FILES,
    ids=[f"{s}/{p.stem}" for s, p in ANNOTATION_FILES],
)
def test_annotation_file_integrity(set_name: str, ann_path: Path) -> None:
    text_dirs, _ = ANNOTATION_SETS[set_name]
    stem = ann_path.stem
    text = _text_paths(text_dirs)[stem].read_text(encoding="utf-8")  # LF-normalized
    data = json.loads(ann_path.read_text(encoding="utf-8"))
    errors = annotation_errors(text, data, f"{set_name}/{stem}")
    assert not errors, "; ".join(errors)


# ---------------------------------------------------------------------------
# Negative self-tests (QA TEST-002): the checker fires on bad input.
# Synthetic text only; no corpus or held-out strings.
# ---------------------------------------------------------------------------

_SYNTH_TEXT = "Zorvik Quandel travaille chez Plimtex Varnoz depuis longtemps."


def _ent(text: str, etype: str, start: int) -> dict[str, object]:
    return {
        "entity_text": _SYNTH_TEXT[start : start + len(text)],
        "entity_type": etype,
        "start_pos": start,
        "end_pos": start + len(text),
    }


def _doc(*entities: dict[str, object]) -> dict[str, object]:
    return {"document_name": "synthetic.txt", "entities": list(entities)}


def test_checker_accepts_valid_synthetic_document() -> None:
    org = _ent("Plimtex Varnoz", "ORG", 30)
    nested_loc = _ent("Varnoz", "LOCATION", 38)
    person = _ent("Zorvik Quandel", "PERSON", 0)
    assert (
        annotation_errors(_SYNTH_TEXT, _doc(person, org, nested_loc), "t/synthetic")
        == []
    )


def test_checker_rejects_same_type_overlap() -> None:
    a = _ent("Zorvik Quandel", "PERSON", 0)
    b = _ent("Quandel", "PERSON", 7)
    errors = annotation_errors(_SYNTH_TEXT, _doc(a, b), "t/synthetic")
    assert any("same-type overlap" in e for e in errors)


def test_checker_rejects_cross_type_overlap_other_than_location_in_org() -> None:
    org = _ent("Plimtex Varnoz", "ORG", 30)
    person_inside_org = _ent("Plimtex", "PERSON", 30)
    errors = annotation_errors(_SYNTH_TEXT, _doc(org, person_inside_org), "t/synthetic")
    assert any("cross-type overlap" in e for e in errors)


def test_checker_rejects_location_straddling_org_boundary() -> None:
    org = _ent("Plimtex", "ORG", 30)
    loc = _ent("tex Varnoz", "LOCATION", 34)
    errors = annotation_errors(_SYNTH_TEXT, _doc(org, loc), "t/synthetic")
    assert any("cross-type overlap" in e for e in errors)


def test_checker_rejects_offset_mismatch_and_padding() -> None:
    bad_offsets = {**_ent("Zorvik", "PERSON", 0), "entity_text": "Quandel"}
    padded = _ent("Plimtex ", "ORG", 30)
    errors = annotation_errors(_SYNTH_TEXT, _doc(bad_offsets, padded), "t/synthetic")
    assert any("text/offset mismatch" in e for e in errors)
    assert any("whitespace" in e for e in errors)
