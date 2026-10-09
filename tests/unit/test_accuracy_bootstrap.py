"""Unit tests for the accuracy bootstrap (Story 10.6 PR A, AC1-AC3).

Covers ``tests/accuracy/bootstrap.py`` and ``scripts/accuracy_paired_delta.py``
on synthetic counts with invented document names. No detection model and no
corpus file is loaded.
"""

from __future__ import annotations

import importlib.util
import json
import random
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from tests.accuracy import bootstrap
from tests.accuracy.conftest import compute_metrics

SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "accuracy_paired_delta.py"
)

Counts = tuple[int, int, int]
NAMES = ["zorbalia_01.txt", "quentrix_02.txt", "zorbaville_03.txt", "quentrel_04.txt"]

# Canonical extraction patterns of the existing lines (story Dev Notes E1-E4).
E1 = re.compile(r"^\[(Overall|PERSON|LOCATION|ORG)\] ")
E2 = re.compile(r"^\[HELD-OUT (Overall|PERSON|LOCATION|ORG)\] ")
E3 = [re.compile(r"\[Overall\]"), re.compile(r"\[PERSON\]")]
E3 += [re.compile(r"\[LOCATION\]"), re.compile(r"\[ORG\]")]
E4 = [re.compile(r"^\[HELD-OUT"), re.compile(r"\[HELD-OUT")]


def _doc(
    person: Counts = (0, 0, 0),
    location: Counts = (0, 0, 0),
    org: Counts = (0, 0, 0),
) -> dict[str, Counts]:
    """Per-label counts of one document; Overall is the sum of the types."""
    overall = (
        person[0] + location[0] + org[0],
        person[1] + location[1] + org[1],
        person[2] + location[2] + org[2],
    )
    return {"Overall": overall, "PERSON": person, "LOCATION": location, "ORG": org}


# Four invented documents with uneven counts (golden lines below).
DOCS = [
    _doc((5, 1, 2), (2, 1, 0), (1, 2, 3)),
    _doc((3, 0, 1), (0, 0, 1), (0, 1, 1)),
    _doc((4, 2, 0), (1, 0, 1), (2, 0, 2)),
    _doc((6, 1, 1), (0, 1, 0), (0, 0, 0)),
]
# The same documents with one FP fewer per type wherever there was one.
FEWER_FP = [
    _doc(
        *(
            (tp, max(fp - 1, 0), fn)
            for tp, fp, fn in (d["PERSON"], d["LOCATION"], d["ORG"])
        )
    )
    for d in DOCS
]

GOLDEN_DOCS = [
    "[CI95 Overall] P=[0.6818,0.7714] R=[0.5714,0.7778] F1=[0.6286,0.7647] "
    "unit=document docs=4 resamples=10000 seed=20261008 "
    "undef_P=0 undef_R=0 undef_F1=0",
    "[CI95 PERSON] P=[0.7143,0.9333] R=[0.7273,0.9375] F1=[0.7826,0.8571] "
    "unit=document docs=4 resamples=10000 seed=20261008 "
    "undef_P=0 undef_R=0 undef_F1=0",
    "[CI95 LOCATION] P=[0.0000,1.0000] R=[0.0000,1.0000] F1=[0.0000,0.7500] "
    "unit=document docs=4 resamples=10000 seed=20261008 "
    "undef_P=40 undef_R=38 undef_F1=78",
    "[CI95 ORG] P=[0.0000,1.0000] R=[0.0000,0.5000] F1=[0.0000,0.6667] "
    "unit=document docs=4 resamples=10000 seed=20261008 "
    "undef_P=38 undef_R=38 undef_F1=38",
]


def _stub_draw(indices: list[int]) -> tuple[list[int], bootstrap.Draw]:
    """A draw that always returns *indices*; the list records each n asked."""
    calls: list[int] = []

    def draw(rng: random.Random, n: int) -> list[int]:
        calls.append(n)
        return list(indices)

    return calls, draw


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("accuracy_paired_delta", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _point_lines(per_doc: list[dict[str, Counts]]) -> list[str]:
    """The four main-corpus point lines, in the accuracy suite's format."""
    lines = []
    for label in bootstrap.LABELS:
        tp, fp, fn = (sum(d[label][k] for d in per_doc) for k in range(3))
        m = compute_metrics(tp, fp, fn)
        line = (
            f"[{label}] P={m.precision:.4f} R={m.recall:.4f} F1={m.f1:.4f} "
            f"TP={tp} FP={fp} FN={fn}"
        )
        if label == "Overall":
            line += f" FN%={m.fn_rate:.2f} FP%={m.fp_rate:.2f}"
        lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Percentile rule, counting, resampling
# ---------------------------------------------------------------------------


class TestPercentileIndices:
    @pytest.mark.parametrize(
        ("m", "expected"),
        [(10_000, (250, 9749)), (40, (1, 38)), (7, (0, 6)), (1, (0, 0))],
    )
    def test_indices(self, m: int, expected: tuple[int, int]) -> None:
        assert bootstrap.percentile_indices(m) == expected

    def test_zero_values_rejected(self) -> None:
        with pytest.raises(ValueError):
            bootstrap.percentile_indices(0)


class TestDocCounts:
    def test_counts_follow_aggregate_rules(self) -> None:
        def ent(entity_type: str) -> SimpleNamespace:
            return SimpleNamespace(entity_type=entity_type)

        result = SimpleNamespace(
            true_positives=[
                (ent("PERSON"), ent("PERSON")),
                (ent("ORG"), ent("ORG")),
                (ent("PERSON"), ent("PERSON")),
            ],
            false_positives=[ent("LOCATION"), ent("ORG")],
            false_negatives=[ent("ORG"), ent("ORG"), ent("PERSON")],
        )
        assert bootstrap.doc_counts(result) == {
            "Overall": (3, 2, 3),
            "PERSON": (2, 0, 1),
            "LOCATION": (0, 1, 0),
            "ORG": (1, 1, 2),
        }


class TestBootstrapRanges:
    def test_deterministic(self) -> None:
        first = bootstrap.bootstrap_ranges(DOCS)
        second = bootstrap.bootstrap_ranges(DOCS)
        assert [bootstrap.format_ci95_line(first[x]) for x in bootstrap.LABELS] == [
            bootstrap.format_ci95_line(second[x]) for x in bootstrap.LABELS
        ]

    def test_identical_documents_collapse_to_point(self) -> None:
        one = _doc((3, 1, 2), (2, 2, 1), (1, 3, 4))
        ranges = bootstrap.bootstrap_ranges([one, dict(one), dict(one)])
        for label in bootstrap.LABELS:
            tp, fp, fn = (3 * one[label][k] for k in range(3))
            m = compute_metrics(tp, fp, fn)
            r = ranges[label]
            assert (r.precision.lo, r.precision.hi) == (m.precision, m.precision)
            assert (r.recall.lo, r.recall.hi) == (m.recall, m.recall)
            assert (r.f1.lo, r.f1.hi) == (m.f1, m.f1)
            assert r.precision.undefined == r.recall.undefined == r.f1.undefined == 0

    def test_resampling_is_with_replacement(self) -> None:
        docs = [_doc((1, 1, 0)), _doc((0, 0, 2)), _doc((5, 0, 0))]
        calls, draw = _stub_draw([0, 0, 1])
        ranges = bootstrap.bootstrap_ranges(docs, resamples=1, draw=draw)
        # Document 0 counted twice: PERSON (2, 2, 2) -> P = R = 0.5.
        person = ranges["PERSON"]
        assert (person.precision.lo, person.precision.hi) == (0.5, 0.5)
        assert (person.recall.lo, person.recall.hi) == (0.5, 0.5)
        assert calls == [3]

    def test_one_draw_per_resample_shared_by_labels(self) -> None:
        calls, draw = _stub_draw([0, 1, 2, 3])
        bootstrap.bootstrap_ranges(DOCS, resamples=5, draw=draw)
        assert calls == [4] * 5

    def test_defined_values_equal_compute_metrics(self) -> None:
        docs = [_doc((3, 2, 4)), _doc((1, 0, 0)), _doc((0, 5, 5))]
        _, draw = _stub_draw([0, 1, 1])
        ranges = bootstrap.bootstrap_ranges(docs, resamples=1, draw=draw)
        m = compute_metrics(5, 2, 4)
        person = ranges["PERSON"]
        assert person.precision.lo == person.precision.hi == m.precision
        assert person.recall.lo == person.recall.hi == m.recall
        assert person.f1.lo == person.f1.hi == m.f1

    def test_metric_values_undefined_before_compute_metrics(self) -> None:
        assert bootstrap.metric_values(0, 0, 3) == (None, 0.0, None)
        assert bootstrap.metric_values(0, 3, 0) == (0.0, None, None)
        assert bootstrap.metric_values(0, 0, 0) == (None, None, None)
        m = compute_metrics(4, 1, 3)
        assert bootstrap.metric_values(4, 1, 3) == (m.precision, m.recall, m.f1)

    def test_label_predicted_in_one_document_only(self) -> None:
        # ORG predicted only in document 0; documents 1 and 2 only miss one.
        docs = [_doc(org=(2, 2, 0)), _doc(org=(0, 0, 1)), _doc(org=(0, 0, 1))]
        org = bootstrap.bootstrap_ranges(docs)["ORG"]
        assert 0 < org.precision.undefined < bootstrap.RESAMPLES
        # Every defined resample has P = 0.5; counting the undefined ones as
        # 0.0 would pull the lower bound to 0.0.
        assert (org.precision.lo, org.precision.hi) == (0.5, 0.5)
        assert org.recall.undefined == 0
        assert org.f1.undefined == org.precision.undefined

    def test_label_absent_everywhere_is_not_available(self) -> None:
        docs = [_doc((1, 0, 1)), _doc((2, 1, 0))]
        ranges = bootstrap.bootstrap_ranges(docs)
        line = bootstrap.format_ci95_line(ranges["LOCATION"])
        assert "P=[n/a] R=[n/a] F1=[n/a]" in line
        n = bootstrap.RESAMPLES
        assert f"undef_P={n} undef_R={n} undef_F1={n}" in line

    def test_zero_tp_keeps_f1_zero(self) -> None:
        docs = [_doc(org=(0, 1, 1)), _doc(org=(0, 2, 1))]
        org = bootstrap.bootstrap_ranges(docs)["ORG"]
        assert (org.f1.lo, org.f1.hi) == (0.0, 0.0)
        assert org.f1.undefined == 0

    def test_empty_input_rejected(self) -> None:
        with pytest.raises(ValueError):
            bootstrap.bootstrap_ranges([])


# ---------------------------------------------------------------------------
# Line format and labels
# ---------------------------------------------------------------------------


class TestLineFormat:
    def test_golden_hand_checked(self) -> None:
        same = [_doc((2, 0, 1), (1, 1, 0)), _doc((2, 0, 1), (1, 1, 0))]
        ranges = bootstrap.bootstrap_ranges(same)
        tail = "unit=document docs=2 resamples=10000 seed=20261008 "
        assert bootstrap.format_ci95_line(ranges["PERSON"]) == (
            "[CI95 PERSON] P=[1.0000,1.0000] R=[0.6667,0.6667] "
            "F1=[0.8000,0.8000] " + tail + "undef_P=0 undef_R=0 undef_F1=0"
        )
        assert bootstrap.format_ci95_line(ranges["ORG"], scope="HELD-OUT") == (
            "[CI95 HELD-OUT ORG] P=[n/a] R=[n/a] F1=[n/a] "
            + tail
            + "undef_P=10000 undef_R=10000 undef_F1=10000"
        )

    def test_golden_resampled(self) -> None:
        ranges = bootstrap.bootstrap_ranges(DOCS)
        main = [bootstrap.format_ci95_line(ranges[x]) for x in bootstrap.LABELS]
        assert main == GOLDEN_DOCS
        held = [
            bootstrap.format_ci95_line(ranges[x], scope="HELD-OUT")
            for x in bootstrap.LABELS
        ]
        assert held == [g.replace("[CI95 ", "[CI95 HELD-OUT ", 1) for g in GOLDEN_DOCS]

    def test_new_labels_match_no_existing_extraction_pattern(self) -> None:
        ranges = bootstrap.bootstrap_ranges(DOCS)
        lines = [
            bootstrap.format_ci95_line(ranges[x], scope=scope)
            for scope in ("", "HELD-OUT")
            for x in bootstrap.LABELS
        ]
        assert len(lines) == 8
        for line in lines:
            assert line.startswith("[CI95 ")
            assert not E1.match(line) and not E2.match(line)
            assert not any(p.search(line) for p in E3 + E4)


# ---------------------------------------------------------------------------
# Main-corpus per-document JSON
# ---------------------------------------------------------------------------


class TestPerDocumentJson:
    def test_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "run.json"
        bootstrap.write_per_document_json(path, NAMES, DOCS, "424242", "abc1234")
        raw = path.read_bytes()
        assert raw.endswith(b"}\n") and b"\r" not in raw
        data = json.loads(raw.decode("utf-8"))
        assert data["schema_version"] == 1
        assert data["corpus"] == "main"
        assert data["labels"] == ["Overall", "PERSON", "LOCATION", "ORG"]
        assert data["bootstrap"] == {
            "unit": "document",
            "method": "percentile",
            "confidence": 95,
            "resamples": 10000,
            "seed": 20261008,
        }
        assert data["documents"][0]["doc"] == NAMES[0]
        assert data["documents"][0]["ORG"] == {"tp": 1, "fp": 2, "fn": 3}
        run = bootstrap.read_per_document_json(path)
        assert (run.run_id, run.commit) == ("424242", "abc1234")
        assert list(run.names) == NAMES
        assert list(run.counts) == DOCS
        for label in bootstrap.LABELS:
            for k in range(3):
                assert sum(d[label][k] for d in run.counts) == sum(
                    d[label][k] for d in DOCS
                )

    def test_null_metadata(self, tmp_path: Path) -> None:
        path = tmp_path / "run.json"
        bootstrap.write_per_document_json(path, NAMES, DOCS, None, None)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["run_id"] is None and data["commit"] is None

    @pytest.mark.parametrize(
        ("key", "value"),
        [("corpus", "held_out"), ("schema_version", 2), ("labels", ["Overall"])],
    )
    def test_reader_rejects_other_files(
        self, tmp_path: Path, key: str, value: object
    ) -> None:
        path = tmp_path / "run.json"
        bootstrap.write_per_document_json(path, NAMES, DOCS, None, None)
        data = json.loads(path.read_text(encoding="utf-8"))
        data[key] = value
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError):
            bootstrap.read_per_document_json(path)

    def test_target_path_and_metadata_from_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ACCURACY_PER_DOC_JSON", raising=False)
        monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
        monkeypatch.delenv("GITHUB_SHA", raising=False)
        assert bootstrap.per_document_json_path(tmp_path) == (
            tmp_path / "accuracy-per-document.json"
        )
        assert bootstrap.github_run_metadata() == (None, None)
        target = tmp_path / "elsewhere.json"
        monkeypatch.setenv("ACCURACY_PER_DOC_JSON", str(target))
        monkeypatch.setenv("GITHUB_RUN_ID", "424242")
        monkeypatch.setenv("GITHUB_SHA", "abc1234")
        assert bootstrap.per_document_json_path(tmp_path) == target
        assert bootstrap.github_run_metadata() == ("424242", "abc1234")


# ---------------------------------------------------------------------------
# Paired delta and the script
# ---------------------------------------------------------------------------


class TestPairedDelta:
    def test_identical_runs_give_zero_deltas(self) -> None:
        deltas = bootstrap.paired_delta_ranges(DOCS, DOCS)
        for label in bootstrap.LABELS:
            line = bootstrap.format_paired_delta_line(deltas[label])
            assert line.startswith(f"[PAIRED-DELTA {label}] dP=+0.0000 ")
            assert "excludes_0=P:no,R:no,F1:no" in line
            d = deltas[label]
            for metric in (d.precision, d.recall, d.f1):
                assert metric.point == 0.0
                assert metric.lo in (0.0, None) and metric.hi in (0.0, None)

    def test_fewer_false_positives_everywhere(self) -> None:
        overall = bootstrap.paired_delta_ranges(DOCS, FEWER_FP)["Overall"]
        assert overall.precision.lo is not None and overall.precision.lo > 0
        assert overall.precision.excludes_zero
        assert overall.recall.point == 0.0 and not overall.recall.excludes_zero
        line = bootstrap.format_paired_delta_line(
            bootstrap.paired_delta_ranges(DOCS, FEWER_FP)["Overall"]
        )
        assert "excludes_0=P:yes,R:no,F1:yes" in line

    def test_same_draw_for_both_runs(self) -> None:
        calls, draw = _stub_draw([0, 0, 0, 0])
        deltas = bootstrap.paired_delta_ranges(DOCS, FEWER_FP, resamples=3, draw=draw)
        assert calls == [4, 4, 4]
        # Only document 0 drawn, for both runs: PERSON P goes from 5/6 to 5/5.
        person = deltas["PERSON"].precision
        assert person.lo == person.hi == pytest.approx(1.0 - 5 / 6)

    def test_misaligned_runs_rejected(self) -> None:
        with pytest.raises(ValueError):
            bootstrap.paired_delta_ranges(DOCS, DOCS[:3])


class TestScript:
    def _write(
        self,
        path: Path,
        names: list[str],
        docs: list[dict[str, Counts]],
        run_id: str = "424242",
    ) -> Path:
        bootstrap.write_per_document_json(path, names, docs, run_id, "abc1234")
        return path

    def test_import_has_no_side_effect_on_stdout(self) -> None:
        before = sys.stdout
        _load_script()
        assert sys.stdout is before

    def test_delta_identical(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        script = _load_script()
        a = self._write(tmp_path / "a.json", NAMES, DOCS)
        assert script.main(["delta", str(a), str(a)]) == 0
        out = capsys.readouterr().out.splitlines()
        assert out[0] == "baseline run_id=424242 commit=abc1234"
        assert out[1] == "candidate run_id=424242 commit=abc1234"
        assert len(out) == 6
        assert all("excludes_0=P:no,R:no,F1:no" in line for line in out[2:])

    def test_delta_aligns_reordered_documents_by_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        script = _load_script()
        base = self._write(tmp_path / "base.json", NAMES, DOCS)
        cand = self._write(tmp_path / "cand.json", NAMES, FEWER_FP, run_id="434343")
        order = [2, 0, 3, 1]
        shuffled = self._write(
            tmp_path / "shuffled.json",
            [NAMES[i] for i in order],
            [FEWER_FP[i] for i in order],
            run_id="434343",
        )
        assert script.main(["delta", str(base), str(cand)]) == 0
        in_order = capsys.readouterr().out
        assert script.main(["delta", str(base), str(shuffled)]) == 0
        assert capsys.readouterr().out == in_order
        assert "excludes_0=P:yes" in in_order

    def test_delta_different_names_exit_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        script = _load_script()
        base = self._write(tmp_path / "base.json", NAMES, DOCS)
        other = self._write(
            tmp_path / "other.json", NAMES[:3] + ["zorbalia_05.txt"], DOCS
        )
        assert script.main(["delta", str(base), str(other)]) == 2
        assert "[PAIRED-DELTA" not in capsys.readouterr().out

    def test_delta_wrong_corpus_exit_2(self, tmp_path: Path) -> None:
        script = _load_script()
        base = self._write(tmp_path / "base.json", NAMES, DOCS)
        data = json.loads(base.read_text(encoding="utf-8"))
        data["corpus"] = "held_out"
        other = tmp_path / "other.json"
        other.write_text(json.dumps(data), encoding="utf-8")
        assert script.main(["delta", str(base), str(other)]) == 2

    def _artifact(self, docs: list[dict[str, Counts]]) -> str:
        ranges = bootstrap.bootstrap_ranges(docs)
        ci95 = [bootstrap.format_ci95_line(ranges[x]) for x in bootstrap.LABELS]
        held = [
            bootstrap.format_ci95_line(ranges[x], scope="HELD-OUT")
            for x in bootstrap.LABELS
        ]
        point = _point_lines(docs)
        return "\n".join(
            ["header", point[0], "PASSED", *point[1:], "PASSED", *ci95, *held, ""]
        )

    def test_recompute_lines_match(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        script = _load_script()
        run = self._write(tmp_path / "run.json", NAMES, DOCS)
        text = tmp_path / "accuracy-output.txt"
        text.write_text(self._artifact(DOCS), encoding="utf-8")
        assert script.main(["recompute", str(run), "--lines", str(text)]) == 0
        out = capsys.readouterr().out
        assert out.splitlines()[1:5] == GOLDEN_DOCS
        assert out.rstrip().endswith("recompute: match")

    def test_recompute_one_changed_digit_fails(self, tmp_path: Path) -> None:
        script = _load_script()
        run = self._write(tmp_path / "run.json", NAMES, DOCS)
        artifact = self._artifact(DOCS)
        assert "P=[0.7143,0.9333]" in artifact
        text = tmp_path / "accuracy-output.txt"
        text.write_text(
            artifact.replace("P=[0.7143,0.9333]", "P=[0.7143,0.9334]", 1),
            encoding="utf-8",
        )
        assert script.main(["recompute", str(run), "--lines", str(text)]) == 1

    def test_recompute_sum_mismatch_fails(self, tmp_path: Path) -> None:
        script = _load_script()
        run = self._write(tmp_path / "run.json", NAMES, DOCS)
        artifact = self._artifact(DOCS)
        point = _point_lines(DOCS)[3]
        text = tmp_path / "accuracy-output.txt"
        text.write_text(
            artifact.replace(point, point.replace(" FN=6", " FN=7")), encoding="utf-8"
        )
        assert script.main(["recompute", str(run), "--lines", str(text)]) == 1

    def test_recompute_without_lines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        script = _load_script()
        run = self._write(tmp_path / "run.json", NAMES, DOCS)
        assert script.main(["recompute", str(run)]) == 0
        assert capsys.readouterr().out.splitlines()[1:] == GOLDEN_DOCS
