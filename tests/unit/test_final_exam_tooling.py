"""Unit tests for the final-exam tooling (Story 10.6 PR B, B3.7).

Invented strings only (Zorbalia, Quentrix, Zorbaville, Quentrel, Zorbal, and
the dummy fixture's invented names). No spaCy model is loaded: scoring uses a
stub detector.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import re
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest
import structlog

from gdpr_pseudonymizer.utils.logger import configure_logging
from tests.accuracy import final_exam

ROOT = Path(__file__).resolve().parent.parent.parent
DUMMY = ROOT / "tests" / "fixtures" / "final_exam_dummy"
REAL_LEDGER = ROOT / "tests" / "test_corpus" / "final_exam" / "RUNS.md"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fp = _load("final_exam_fingerprints")
adj = _load("final_exam_adjudication")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _is_utf8_lf(path: Path) -> bool:
    data = path.read_bytes()
    data.decode("utf-8")
    return b"\r" not in data


def _dummy_strings() -> set[str]:
    strings: set[str] = set()
    for path in (DUMMY / "annotations").glob("*.json"):
        for e in json.loads(path.read_text(encoding="utf-8"))["entities"]:
            strings.add(e["entity_text"])
    return strings


# ---------------------------------------------------------------------------
# Fingerprints: record, check, append
# ---------------------------------------------------------------------------


def _tree(root: Path) -> None:
    _write(root / "documents" / "dummy_01.txt", "Zorbalia Quentrel\n")
    _write(root / "documents" / "dummy_02.txt", "Quentrix Zorbaville\n")
    _write(root / "manifest.json", '{"documents": []}\n')


def _record(root: Path, out: Path, *includes: str, append: bool = False) -> int:
    args = ["record", "--root", str(root), "--include", *includes, "--out", str(out)]
    return int(fp.main(args + (["--append"] if append else [])))


def _check(root: Path, record: Path) -> int:
    return int(fp.main(["check", "--root", str(root), "--record", str(record)]))


def test_record_check_round_trip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _tree(tmp_path)
    record = tmp_path / "freeze.sha256"
    assert _record(tmp_path, record, "documents", "manifest.json") == 0
    assert _check(tmp_path, record) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "OK 3"
    assert _is_utf8_lf(record)
    assert [line.split("  ")[1] for line in record.read_text().splitlines()] == [
        "documents/dummy_01.txt",
        "documents/dummy_02.txt",
        "manifest.json",
    ]


@pytest.mark.parametrize("change", ["edit", "missing", "unlisted"])
def test_check_reports_each_problem_by_path_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], change: str
) -> None:
    _tree(tmp_path)
    record = tmp_path / "freeze.sha256"
    _record(tmp_path, record, "documents", "manifest.json")
    capsys.readouterr()
    if change == "edit":
        _write(tmp_path / "documents" / "dummy_01.txt", "Zorbalia Quentrex\n")
        expected = "MISMATCH documents/dummy_01.txt"
    elif change == "missing":
        (tmp_path / "documents" / "dummy_02.txt").unlink()
        expected = "MISMATCH documents/dummy_02.txt"
    else:
        _write(tmp_path / "documents" / "dummy_03.txt", "Zorbal\n")
        expected = "MISMATCH documents/dummy_03.txt"
    assert _check(tmp_path, record) == 1
    out = capsys.readouterr().out
    assert out.splitlines() == [expected]
    assert "Zorba" not in out and "Quentr" not in out


def test_append_keeps_existing_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _tree(tmp_path)
    record = tmp_path / "FINGERPRINTS.sha256"
    _record(tmp_path, record, "documents")
    before = record.read_bytes()
    assert _record(tmp_path, record, "manifest.json", append=True) == 0
    after = record.read_bytes()
    assert after.startswith(before) and after.count(b"\n") == 3
    capsys.readouterr()
    assert _record(tmp_path, record, "manifest.json", append=True) == 1
    assert capsys.readouterr().out.strip() == "ERROR - ValueError"
    assert record.read_bytes() == after


def test_dummy_fixture_fingerprints_match() -> None:
    assert _check(DUMMY, DUMMY / "FINGERPRINTS.sha256") == 0


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def _ledger(path: Path, rows: list[str], header: str = fp.LEDGER_HEADER) -> Path:
    _write(
        path,
        "# Ledger\n\n" + header + "\n|---|---|---|---|---|---|---|\n" + "".join(rows),
    )
    return path


def test_ledger_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    infra = (
        "| 101 | abc1234 | 2026-10-09 | real | infra-failure | B14.1 | runner lost |\n"
    )
    scored = "| 102 | abc1234 | 2026-10-09 | real | scored | B14.1 | - |\n"
    empty = _ledger(tmp_path / "a.md", [])
    one_infra = _ledger(tmp_path / "b.md", [infra])
    one_scored = _ledger(tmp_path / "c.md", [infra, scored])
    bad_status = _ledger(tmp_path / "d.md", [infra.replace("infra-failure", "done")])
    no_header = _ledger(tmp_path / "e.md", [], header="| Run | Commit |")
    assert fp.main(["ledger-check", "--ledger", str(empty)]) == 0
    assert fp.main(["ledger-check", "--ledger", str(one_infra)]) == 0
    assert fp.main(["ledger-check", "--ledger", str(one_scored)]) == 1
    capsys.readouterr()
    assert fp.main(["ledger-check", "--ledger", str(bad_status)]) == 1
    assert fp.main(["ledger-check", "--ledger", str(no_header)]) == 1
    assert capsys.readouterr().out.splitlines() == ["ERROR - LedgerError"] * 2


def test_committed_ledgers_are_valid() -> None:
    assert fp.main(["ledger-check", "--ledger", str(DUMMY / "RUNS.md")]) == 0
    for ledger in (DUMMY / "RUNS.md", REAL_LEDGER):
        if ledger.exists():
            rows = fp.ledger_rows(ledger.read_text(encoding="utf-8"))
            assert sum(1 for r in rows if r[4] == "scored") <= 1


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------

DOC = (
    "Bonjour Zorbalia,\n"
    "Le site Quentrix  Zorbaville ouvre. \n"
    'Merci, l\'équipe "Zorbal".\n'
)
TAGGED = (
    "Bonjour ⟦PERSON|Zorbalia⟧,\n"
    "Le site ⟦ORG|Quentrix ⟦LOCATION|Zorbaville⟧⟧ ouvre.\n"
    "Merci, l’équipe “⟦ORG|Zorbal⟧”.\n"
)


def _entities(ann: dict[str, object]) -> list[tuple[str, str, int, int]]:
    return [
        (e["entity_text"], e["entity_type"], e["start_pos"], e["end_pos"])  # type: ignore[index]
        for e in ann["entities"]  # type: ignore[attr-defined]
    ]


def test_convert_aligns_tolerated_differences_and_nesting() -> None:
    ann, tolerated, flags = adj.convert_one(
        "dummy_01.txt", DOC, TAGGED + "REAL-PERSONS: none\n"
    )
    assert flags == []
    # whitespace runs: "  " vs " " (2), " \n" vs "\n" (2), NBSP vs " " (1);
    # apostrophe (1); two double quotes (2); the missing final newline (1).
    assert tolerated == 9
    org_start = DOC.index("Quentrix")
    assert _entities(ann) == [
        ("Zorbalia", "PERSON", 8, 16),
        ("Quentrix  Zorbaville", "ORG", org_start, org_start + 20),
        ("Zorbaville", "LOCATION", org_start + 10, org_start + 20),
        ("Zorbal", "ORG", DOC.index('Zorbal"'), DOC.index('Zorbal"') + 6),
    ]
    for text, _, start, end in _entities(ann):
        assert DOC[start:end] == text


@pytest.mark.parametrize(
    "tagged",
    [
        TAGGED.replace("Bonjour", "Bonjoor"),
        TAGGED.replace("Le site", "Le site 2"),
        TAGGED.replace("ouvre.", "ouvre bien."),
    ],
)
def test_convert_rejects_changed_text(tagged: str) -> None:
    with pytest.raises(adj.FormatFailureError) as info:
        adj.convert_one("dummy_01.txt", DOC, tagged + "REAL-PERSONS: none\n")
    assert info.value.kind == "CopyMismatch"


@pytest.mark.parametrize("value", ["none", "None", "NONE.", "none!"])
def test_real_persons_none_variants(value: str) -> None:
    _, _, flags = adj.convert_one(
        "dummy_01.txt", DOC, TAGGED + f"REAL-PERSONS: {value}\n"
    )
    assert flags == []


def test_real_persons_other_text_is_a_flag() -> None:
    raw = TAGGED + "REAL-PERSONS:\nQuentrel Zorbalia\n"
    _, _, flags = adj.convert_one("dummy_01.txt", DOC, raw)
    assert flags == ["Quentrel Zorbalia"]


@pytest.mark.parametrize(
    ("raw", "kind"),
    [
        (TAGGED, "NoRealPersonsLine"),
        (TAGGED.replace("PERSON|", "PERS|") + "REAL-PERSONS: none\n", "BadTag"),
        (
            TAGGED.replace("Zorbalia⟧", "Zorbalia") + "REAL-PERSONS: none\n",
            "UnbalancedTag",
        ),
    ],
)
def test_convert_format_failures(raw: str, kind: str) -> None:
    with pytest.raises(adj.FormatFailureError) as info:
        adj.convert_one("dummy_01.txt", DOC, raw)
    assert info.value.kind == kind


def test_convert_command_writes_lf_and_prints_no_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "docs" / "dummy_01.txt", DOC)
    _write(tmp_path / "raw" / "dummy_01.txt", TAGGED + "REAL-PERSONS: none\n")
    _write(tmp_path / "docs" / "dummy_02.txt", DOC)
    _write(
        tmp_path / "raw" / "dummy_02.txt",
        TAGGED.replace("Zorbal⟧", "Zorbol⟧") + "REAL-PERSONS:\nQuentrel Zorbalia\n",
    )
    args = ["convert", "--docs", str(tmp_path / "docs"), "--raw", str(tmp_path / "raw")]
    args += ["--out", str(tmp_path / "out"), "--flags", str(tmp_path / "flags.json")]
    assert adj.main(args) == 2
    out = capsys.readouterr().out
    assert out.splitlines()[:2] == [
        "dummy_01 ok tolerated=9 flags=0",
        "dummy_02 FAIL CopyMismatch",
    ]
    assert "Zorba" not in out and "Quentr" not in out
    assert _is_utf8_lf(tmp_path / "out" / "dummy_01.json")
    assert not (tmp_path / "out" / "dummy_02.json").exists()


def test_next_step_caps_replacements() -> None:
    assert adj.next_step(0, 0) == "ok"
    assert adj.next_step(1, 0) == "rerun"
    assert adj.next_step(2, 0) == "replace"
    # the replacement fails too, after its own re-run: count-only choice for Lionel
    assert adj.next_step(1, 1) == "rerun"
    assert adj.next_step(2, 1) == "ask-lionel"


# ---------------------------------------------------------------------------
# agreement, view, merge, report
# ---------------------------------------------------------------------------


def test_agreement_on_the_dummy_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    # Hand-checked: ann_b retypes one PERSON as ORG (type), cuts one PERSON
    # short (boundary) and misses one ORG (one-sided). 32 A spans, 31 B spans,
    # 29 matched: F1 = 58 / 63.
    args = ["agreement", "--a", str(DUMMY / "ann_a"), "--b", str(DUMMY / "ann_b")]
    assert adj.main(args) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "[AGREEMENT Overall] F1=0.9206 matched=29 a_only=3 b_only=2"
    assert "[DISAGREEMENTS] total=3 type=1 boundary=1 other=0 one-sided=1" in out
    assert not any("Zorba" in line or "Quentr" in line for line in out)


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    for name in ("documents", "ann_a", "ann_b"):
        shutil.copytree(DUMMY / name, ws / name)
    shutil.copy(DUMMY / "manifest.json", ws / "manifest.json")
    return ws


def _view_bytes(ws: Path) -> list[bytes]:
    names = (
        "adjudication_view.html",
        "decisions.tsv",
        "occurrences.tsv",
        "spotcheck_view.html",
        "spotcheck.tsv",
    )
    return [(ws / n).read_bytes() for n in names]


def test_spotcheck_draw_is_deterministic_and_stratified() -> None:
    halves = {f"dummy_0{i}": ("planted" if i < 3 else "natural") for i in range(1, 5)}
    first = adj.spotcheck_documents(halves)
    assert first == adj.spotcheck_documents(halves)
    assert halves[first[0]] == "planted" and halves[first[1]] == "natural"
    assert len(set(first)) == 3


def _set_groups(ws: Path, codes: dict[str, str], default: str = "") -> None:
    rows = (ws / "decisions.tsv").read_text(encoding="utf-8").splitlines()
    filled = [rows[0]]
    for r in rows[1:]:
        gid, cls, count = r.split("\t")[:3]
        filled.append("\t".join([gid, cls, count, codes.get(gid, default), ""]))
    _write(ws / "decisions.tsv", "\n".join(filled) + "\n")


def _set_occurrences(ws: Path, codes: dict[str, str]) -> None:
    rows = (ws / "occurrences.tsv").read_text(encoding="utf-8").splitlines()
    filled = [rows[0]]
    for r in rows[1:]:
        did, gid, cls = r.split("\t")[:3]
        filled.append("\t".join([did, gid, cls, codes.get(did, ""), ""]))
    _write(ws / "occurrences.tsv", "\n".join(filled) + "\n")


def _set_spotcheck(ws: Path, spot: str = "NONE") -> None:
    srows = (ws / "spotcheck.tsv").read_text(encoding="utf-8").splitlines()
    sfilled = [srows[0]] + [r.split("\t")[0] + f"\t{spot}\t" for r in srows[1:]]
    _write(ws / "spotcheck.tsv", "\n".join(sfilled) + "\n")


def _fill(ws: Path, decision: str, spot: str = "NONE") -> None:
    _set_groups(ws, {}, default=decision)
    _set_spotcheck(ws, spot)


def test_view_and_merge_are_deterministic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _workspace(tmp_path)
    assert adj.main(["view", "--workspace", str(ws)]) == 0
    first = _view_bytes(ws)
    assert adj.main(["view", "--workspace", str(ws)]) == 0
    assert _view_bytes(ws) == first
    # the dummy fixture's three disagreements are all different: three groups
    assert len((ws / "decisions.tsv").read_text().splitlines()) == 4
    assert len((ws / "occurrences.tsv").read_text().splitlines()) == 4
    _fill(ws, "A")
    assert adj.main(["merge", "--workspace", str(ws)]) == 0
    merged = {p.name: p.read_bytes() for p in (ws / "annotations").glob("*.json")}
    assert adj.main(["merge", "--workspace", str(ws)]) == 0
    assert {
        p.name: p.read_bytes() for p in (ws / "annotations").glob("*.json")
    } == merged
    for name in merged:
        a = json.loads((ws / "ann_a" / name).read_text(encoding="utf-8"))
        m = json.loads(merged[name].decode("utf-8"))
        assert _entities(m) == _entities(a)
        assert _is_utf8_lf(ws / "annotations" / name)
    out = capsys.readouterr().out
    assert "Zorba" not in out and "Quentr" not in out


@pytest.mark.parametrize(
    "decision", ["", "MAYBE", "BOTH", "FIX:PERSON:Quentrix Zorbaland"]
)
def test_merge_rejects_bad_decisions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], decision: str
) -> None:
    ws = _workspace(tmp_path)
    adj.main(["view", "--workspace", str(ws)])
    _fill(ws, decision)
    capsys.readouterr()
    assert adj.main(["merge", "--workspace", str(ws)]) == 1
    assert capsys.readouterr().out.strip() == "ERROR - DecisionError"


def test_merge_fix_and_spotcheck_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _workspace(tmp_path)
    adj.main(["view", "--workspace", str(ws)])
    # dummy_01, in order of first occurrence: g001 type, g002 boundary, g003 one-sided.
    rows = (ws / "decisions.tsv").read_text(encoding="utf-8").splitlines()
    assert [r.split("\t")[1] for r in rows[1:]] == ["type", "boundary", "one-sided"]
    _set_groups(
        ws, {"g001": "A", "g002": "FIX:PERSON:Zorbalia QUENTREL", "g003": "NONE"}
    )
    spot_docs = sorted(adj.spotcheck_documents(adj.load_manifest(ws)))
    target = "dummy_03" if "dummy_03" in spot_docs else spot_docs[0]
    rows = ["document\tcorrection\tnote"] + [
        f"{d}\tNONE\t" for d in spot_docs if d != target
    ]
    rows.append(f"{target}\tMISSING:ORG:NOTE INTERNE\t")
    _write(ws / "spotcheck.tsv", "\n".join(rows) + "\n")
    capsys.readouterr()
    assert adj.main(["merge", "--workspace", str(ws)]) == 0
    out = capsys.readouterr().out
    assert "A=1 FIX=1 NONE=1" in out
    if target == "dummy_03":
        assert "MISSING=1" in out and "missing_occurrences_added=1" in out
    assert adj.main(["report", "--workspace", str(ws)]) == 0
    report = capsys.readouterr().out
    assert "[GROUPS] groups=3 single=3 multi=0 split=0" in report
    assert "[SPOT-CHECK] documents=3" in report
    assert "Zorba" not in report and "Quentr" not in report


# ---------------------------------------------------------------------------
# Grouped adjudication (story precision, 2026-10-10), invented text only
# ---------------------------------------------------------------------------

_GROUP_DOCS = {
    "grp_01": (
        "planted",
        "Bonjour Zorvane.\nLe site de Zorbaville ouvre.\nQuentrix signe avec Zorbaville.\n",
        [
            ("Zorvane", "PERSON", 0),
            ("Zorbaville", "LOCATION", 0),
            ("Quentrix", "ORG", 0),
            ("Zorbaville", "LOCATION", 1),
        ],
        [("Zorvane", "PERSON", 0), ("Quentrix", "LOCATION", 0)],
    ),
    "grp_02": (
        "natural",
        "Zorbaville accueille Quentrix.\n",
        [("Zorbaville", "LOCATION", 0), ("Quentrix", "ORG", 0)],
        [("Quentrix", "LOCATION", 0)],
    ),
    "grp_03": (
        "natural",
        "Tralvio Zendrak arrive.\n",
        [("Tralvio Zendrak", "PERSON", 0)],
        [("Tralvio Zendrak", "PERSON", 0)],
    ),
}


def _spans(text: str, specs: list[tuple[str, str, int]]) -> list[dict[str, object]]:
    out = []
    for needle, etype, nth in specs:
        start = -1
        for _ in range(nth + 1):
            start = text.index(needle, start + 1)
        out.append(
            {
                "entity_text": needle,
                "entity_type": etype,
                "start_pos": start,
                "end_pos": start + len(needle),
            }
        )
    return sorted(out, key=lambda e: (e["start_pos"], e["end_pos"]))  # type: ignore[arg-type,return-value]


def _group_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "gws"
    documents = []
    for doc_id, (half, text, a, b) in _GROUP_DOCS.items():
        _write(ws / "documents" / f"{doc_id}.txt", text)
        for folder, specs in (("ann_a", a), ("ann_b", b)):
            _write(
                ws / folder / f"{doc_id}.json",
                json.dumps(
                    {"document_name": f"{doc_id}.txt", "entities": _spans(text, specs)}
                ),
            )
        documents.append({"id": doc_id, "half": half})
    _write(
        ws / "manifest.json", json.dumps({"target": "dummy", "documents": documents})
    )
    return ws


def _types(ws: Path, doc_id: str) -> list[tuple[str, str]]:
    data = json.loads(
        (ws / "annotations" / f"{doc_id}.json").read_text(encoding="utf-8")
    )
    return [(e["entity_text"], e["entity_type"]) for e in data["entities"]]


def test_identical_disagreements_are_grouped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _group_workspace(tmp_path)
    assert adj.main(["view", "--workspace", str(ws)]) == 0
    out = capsys.readouterr().out
    assert "view disagreements=5 groups=2 single=0 multi=2" in out
    assert "Zorba" not in out and "Quentr" not in out
    assert (ws / "decisions.tsv").read_text(encoding="utf-8").splitlines() == [
        "group\tclass\tcount\tdecision\tnote",
        "g001\tone-sided\t3\t\t",
        "g002\ttype\t2\t\t",
    ]
    occurrences = (ws / "occurrences.tsv").read_text(encoding="utf-8").splitlines()
    assert [r.split("\t")[1] for r in occurrences[1:]] == ["g001"] * 3 + ["g002"] * 2
    view = (ws / "adjudication_view.html").read_text(encoding="utf-8")
    assert (
        "3 occurrences</h2>" in view and "<summary>All 3 occurrences</summary>" in view
    )
    assert view.count("<details>") == 1  # g002 has two occurrences, both shown
    groups, _ = adj.build_groups(ws)
    assert adj.group_counts(groups) == (2, 0, 2)


def test_group_decision_applies_to_every_occurrence(tmp_path: Path) -> None:
    ws = _group_workspace(tmp_path)
    adj.main(["view", "--workspace", str(ws)])
    _set_groups(ws, {"g001": "A", "g002": "B"})
    _set_spotcheck(ws)
    assert adj.main(["merge", "--workspace", str(ws)]) == 0
    assert _types(ws, "grp_01") == [
        ("Zorvane", "PERSON"),
        ("Zorbaville", "LOCATION"),
        ("Quentrix", "LOCATION"),
        ("Zorbaville", "LOCATION"),
    ]
    assert _types(ws, "grp_02") == [
        ("Zorbaville", "LOCATION"),
        ("Quentrix", "LOCATION"),
    ]


def test_split_group_decides_per_occurrence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _group_workspace(tmp_path)
    adj.main(["view", "--workspace", str(ws)])
    _set_groups(ws, {"g001": "SPLIT", "g002": "A"})
    _set_occurrences(
        ws, {"grp_01-d001": "A", "grp_01-d003": "A", "grp_02-d001": "NONE"}
    )
    _set_spotcheck(ws)
    capsys.readouterr()
    assert adj.main(["merge", "--workspace", str(ws)]) == 0
    assert "A=4 NONE=1" in capsys.readouterr().out
    assert _types(ws, "grp_02") == [("Quentrix", "ORG")]
    assert adj.main(["report", "--workspace", str(ws)]) == 0
    assert "[GROUPS] groups=2 single=0 multi=2 split=1" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("groups", "occurrences"),
    [
        ({"g001": "SPLIT", "g002": "A"}, {"grp_01-d001": "A", "grp_01-d003": "A"}),
        ({"g001": "A", "g002": "A"}, {"grp_02-d001": "NONE"}),
        (
            {"g001": "SPLIT", "g002": "A"},
            {"grp_01-d001": "A", "grp_01-d003": "A", "grp_02-d001": "SPLIT"},
        ),
        ({"g001": "A", "g002": "BOTH"}, {}),
        ({"g001": "A"}, {}),
    ],
)
def test_grouped_merge_rejects_inconsistent_decisions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    groups: dict[str, str],
    occurrences: dict[str, str],
) -> None:
    ws = _group_workspace(tmp_path)
    adj.main(["view", "--workspace", str(ws)])
    _set_groups(ws, groups)
    _set_occurrences(ws, occurrences)
    _set_spotcheck(ws)
    capsys.readouterr()
    assert adj.main(["merge", "--workspace", str(ws)]) == 1
    assert capsys.readouterr().out.strip() == "ERROR - DecisionError"


# ---------------------------------------------------------------------------
# Error output (Dev Notes "Error Output")
# ---------------------------------------------------------------------------


def test_script_errors_print_the_class_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object) -> None:
        raise ValueError("Zorbalia Quentrel, Zorbaville")

    _write(tmp_path / "docs" / "dummy_01.txt", DOC)
    _write(tmp_path / "raw" / "dummy_01.txt", TAGGED)
    monkeypatch.setattr(adj, "convert_one", boom)
    args = ["convert", "--docs", str(tmp_path / "docs"), "--raw", str(tmp_path / "raw")]
    args += ["--out", str(tmp_path / "out"), "--flags", str(tmp_path / "flags.json")]
    adj.main(args)
    monkeypatch.setattr(adj, "cmd_agreement", boom)
    adj.main(["agreement", "--a", str(tmp_path), "--b", str(tmp_path)])
    monkeypatch.setattr(fp, "record", boom)
    fp.main(
        [
            "record",
            "--root",
            str(tmp_path),
            "--include",
            "docs",
            "--out",
            str(tmp_path / "r"),
        ]
    )
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert "ERROR dummy_01 ValueError" in lines
    assert lines.count("ERROR - ValueError") == 2
    assert "Zorba" not in captured.out + captured.err


class _StubDetector:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def detect_entities(self, text: str) -> list[object]:
        if self.error is not None:
            raise self.error
        return []


def test_scoring_error_names_the_document_only() -> None:
    manifest = final_exam.load_manifest(DUMMY)
    detector = _StubDetector(ValueError("Zorbalia Quentrel"))
    with pytest.raises(RuntimeError) as info:
        final_exam.score_final_exam(detector, DUMMY, manifest)
    assert str(info.value) == "ValueError on dummy_01"
    assert info.value.__cause__ is None and info.value.__suppress_context__


def test_report_lines_are_aggregate_only() -> None:
    manifest = final_exam.load_manifest(DUMMY)
    scored = final_exam.score_final_exam(_StubDetector(), DUMMY, manifest)
    lines = final_exam.report_lines(scored)
    assert len(lines) == 24
    assert lines[0].startswith("[FINAL-EXAM Overall] P=")
    assert lines[1].startswith("[CI95 FINAL-EXAM Overall] P=")
    assert any(line.startswith("[CI95 FINAL-EXAM PLANTED ORG] ") for line in lines)
    assert sum("docs=4 " in line for line in lines) == 4
    assert sum("docs=2 " in line for line in lines) == 8
    text = "\n".join(lines)
    assert not any(s in text for s in _dummy_strings())


def test_force_failure_only_on_the_dummy() -> None:
    dummy = final_exam.load_manifest(DUMMY)
    real = final_exam.Manifest(target="real", halves=dummy.halves)
    env = {final_exam.FORCE_FAILURE_ENV: "1"}
    assert final_exam.force_failure(dummy, env)
    assert not final_exam.force_failure(real, env)
    assert not final_exam.force_failure(dummy, {})


def test_log_level_silences_detector_errors(capfd: pytest.CaptureFixture[str]) -> None:
    root = logging.getLogger()
    old = root.level
    configure_logging("WARNING")
    try:
        final_exam.apply_log_level({final_exam.LOG_LEVEL_ENV: "CRITICAL"})
        structlog.get_logger("gdpr_pseudonymizer.nlp.spacy_detector").error(
            "entity_detection_failed", error="Zorbalia Quentrel"
        )
        logging.getLogger("gdpr_pseudonymizer").error("Zorbaville")
        out, err = capfd.readouterr()
        assert "Zorba" not in out + err
    finally:
        root.setLevel(old)


def test_new_labels_match_no_regular_extraction_pattern() -> None:
    lines = final_exam.report_lines(
        final_exam.score_final_exam(
            _StubDetector(), DUMMY, final_exam.load_manifest(DUMMY)
        )
    )
    patterns = [
        r"^\[(Overall|PERSON|LOCATION|ORG)\] ",
        r"^\[HELD-OUT (Overall|PERSON|LOCATION|ORG)\] ",
        r"\[Overall\]",
        r"\[PERSON\]",
        r"\[LOCATION\]",
        r"\[ORG\]",
        r"\[HELD-OUT",
    ]
    for line in lines:
        assert not any(re.search(p, line) for p in patterns)
    assert sum(1 for line in lines if re.match(r"^\[FINAL-EXAM", line)) == 12
