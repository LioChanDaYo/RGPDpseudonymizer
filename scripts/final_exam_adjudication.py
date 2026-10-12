"""Final-exam annotation tooling (Story 10.6 PR B, B3.1).

Sub-commands (Dev Notes "PR B Design")::

    convert --docs <dir> --raw <dir> --out <dir> --flags <file> [<id>...]
    agreement --a <dir> --b <dir>
    view --workspace <dir>
    merge --workspace <dir> [--g5-keep-longer]
    report --workspace <dir> [--g5-keep-longer]
    guard-report --workspace <dir> --annotations <dir>
    serve --workspace <dir> [--port 8765] [--open] [--guidelines <GUIDELINES.md>]

Every sub-command prints ids, paths, counts and hashes only, never document
or annotation text. Every error prints ``ERROR <id> <ExceptionClass>`` (the
id is ``-`` when no document is involved) and exits 1, with no traceback and
no message text (Dev Notes "Error Output"). Files are written UTF-8 with LF.

Isolation: agents run these commands on the final-exam workspace but never
open the files they write there (``view`` and ``guard-report`` outputs are
opened by Lionel only).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import socket
import sys
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity  # noqa: E402
from tests.accuracy.conftest import (  # noqa: E402
    GroundTruthEntity,
    _match_key,
    compute_metrics,
    load_annotations,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")
TAG_OPEN = "⟦"  # ⟦
TAG_CLOSE = "⟧"  # ⟧
REAL_PERSONS = "REAL-PERSONS:"
APOSTROPHES = frozenset("'’‘ʼ")
DOUBLE_QUOTES = frozenset('"“”„')
_NONE = re.compile(r"none[\s.!]*", re.IGNORECASE)
SPOTCHECK_SEED = 20261008
CLASSES = ("type", "boundary", "other", "one-sided")


class FormatFailureError(Exception):
    """A model output that ``convert`` cannot use (B6.1)."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class AnonymousError(Exception):
    """An error that names only an anonymous place: a group id (``gNNN``), a
    disagreement id (``fe_NN-dKKK``), a document id, or a TSV file name and
    line number. Its message is never printed (QA ADJ-003)."""

    def __init__(self, reason: str, where: str = "-") -> None:
        super().__init__(reason)
        self.where = where


class DecisionError(AnonymousError):
    """An empty, unknown or inapplicable adjudication code (B10.1)."""


class G5Error(AnonymousError):
    """Same-type spans that overlap after the merge (GUIDELINES G5)."""


class OverwriteError(AnonymousError):
    """``view`` would overwrite a decision file without ``--force`` (QA ADJ-002)."""


@dataclass(frozen=True)
class Span:
    doc: str
    start: int
    end: int
    etype: str
    text: str

    def sort_key(self) -> tuple[str, int, int, str]:
        return (self.doc, self.start, self.end, self.etype)


def write_text(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _is_space(c: str) -> bool:
    return c.isspace()


# ---------------------------------------------------------------------------
# convert (B6.1)
# ---------------------------------------------------------------------------


def split_output(raw: str) -> tuple[str, list[str]]:
    """Split a tagged output into (tagged document, real-person flags)."""
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    marker = [
        i
        for i, line in enumerate(lines)
        if line.strip().upper().startswith(REAL_PERSONS)
    ]
    if not marker:
        raise FormatFailureError("NoRealPersonsLine")
    i = marker[-1]
    first = lines[i].strip()[len(REAL_PERSONS) :]
    items = [s.strip() for s in [first, *lines[i + 1 :]] if s.strip()]
    if not items or (len(items) == 1 and _NONE.fullmatch(items[0])):
        flags: list[str] = []
    else:
        flags = items
    return "\n".join(lines[:i]), flags


def parse_tags(tagged: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Strip ``⟦TYPE|…⟧`` tags (nesting allowed) and return (text, spans)."""
    out: list[str] = []
    stack: list[tuple[str, int]] = []
    spans: list[tuple[str, int, int]] = []
    i = 0
    while i < len(tagged):
        c = tagged[i]
        if c == TAG_OPEN:
            bar = tagged.find("|", i + 1)
            if bar < 0 or tagged[i + 1 : bar] not in TYPES:
                raise FormatFailureError("BadTag")
            stack.append((tagged[i + 1 : bar], len(out)))
            i = bar + 1
            continue
        if c == TAG_CLOSE:
            if not stack:
                raise FormatFailureError("UnbalancedTag")
            etype, start = stack.pop()
            spans.append((etype, start, len(out)))
            i += 1
            continue
        out.append(c)
        i += 1
    if stack:
        raise FormatFailureError("UnbalancedTag")
    return "".join(out), spans


def align(plain: str, doc: str) -> tuple[list[int], int]:
    """Copy check of ``plain`` (untagged output) against ``doc``.

    Tolerated: a whitespace run against a whitespace run of any length (this
    covers trailing spaces, U+00A0 and U+202F), a run missing on one side at
    the very end, and apostrophe or double-quote variants. Anything else is a
    ``FormatFailureError``. Returns, for each index of ``plain``, the matching
    index of ``doc`` (``-1`` for whitespace), and the tolerated-character count.
    """
    mapping = [-1] * len(plain)
    tolerated = 0
    i = j = 0
    while i < len(plain) and j < len(doc):
        a, b = plain[i], doc[j]
        if _is_space(a) or _is_space(b):
            if not (_is_space(a) and _is_space(b)):
                raise FormatFailureError("CopyMismatch")
            i2, j2 = i, j
            while i2 < len(plain) and _is_space(plain[i2]):
                i2 += 1
            while j2 < len(doc) and _is_space(doc[j2]):
                j2 += 1
            if plain[i:i2] != doc[j:j2]:
                tolerated += max(i2 - i, j2 - j)
            i, j = i2, j2
            continue
        if a == b:
            pass
        elif (a in APOSTROPHES and b in APOSTROPHES) or (
            a in DOUBLE_QUOTES and b in DOUBLE_QUOTES
        ):
            tolerated += 1
        else:
            raise FormatFailureError("CopyMismatch")
        mapping[i] = j
        i += 1
        j += 1
    rest_plain, rest_doc = plain[i:], doc[j:]
    if rest_plain.strip() or rest_doc.strip():
        raise FormatFailureError("CopyMismatch")
    if rest_plain != rest_doc:
        tolerated += max(len(rest_plain), len(rest_doc))
    return mapping, tolerated


def convert_one(
    doc_name: str, doc: str, raw: str
) -> tuple[dict[str, object], int, list[str]]:
    """Return (annotation JSON, tolerated-character count, real-person flags)."""
    tagged, flags = split_output(raw)
    plain, spans = parse_tags(tagged)
    mapping, tolerated = align(plain, doc)
    seen: set[tuple[int, int, str]] = set()
    entities: list[dict[str, object]] = []
    for etype, s, e in spans:
        inner = [k for k in range(s, e) if mapping[k] >= 0]
        if not inner:
            raise FormatFailureError("EmptySpan")
        start, end = mapping[inner[0]], mapping[inner[-1]] + 1
        if (start, end, etype) in seen:
            continue
        seen.add((start, end, etype))
        entities.append(
            {
                "entity_text": doc[start:end],
                "entity_type": etype,
                "start_pos": start,
                "end_pos": end,
            }
        )
    entities.sort(key=lambda x: (x["start_pos"], x["end_pos"], x["entity_type"]))  # type: ignore[arg-type,return-value]
    return {"document_name": doc_name, "entities": entities}, tolerated, flags


def cmd_convert(
    docs: Path, raw: Path, out: Path, flags_path: Path, ids: list[str]
) -> int:
    out.mkdir(parents=True, exist_ok=True)
    wanted = ids or sorted(p.stem for p in raw.glob("*.txt"))
    flags_all: dict[str, list[str]] = {}
    if flags_path.exists():
        flags_all = json.loads(flags_path.read_text(encoding="utf-8"))
    ok = failed = flagged = tolerated_total = 0
    type_totals = {t: 0 for t in TYPES}
    for doc_id in wanted:
        try:
            doc = (docs / f"{doc_id}.txt").read_text(encoding="utf-8")
            raw_text = (raw / f"{doc_id}.txt").read_text(encoding="utf-8")
            ann, tolerated, flags = convert_one(f"{doc_id}.txt", doc, raw_text)
        except FormatFailureError as exc:
            print(f"{doc_id} FAIL {exc.kind}")
            failed += 1
            continue
        except Exception as exc:  # noqa: BLE001 - class only (Error Output)
            print(f"ERROR {doc_id} {type(exc).__name__}")
            failed += 1
            continue
        write_json(out / f"{doc_id}.json", ann)
        flags_all[doc_id] = flags
        for e in ann["entities"]:  # type: ignore[union-attr]
            type_totals[e["entity_type"]] += 1  # type: ignore[index]
        tolerated_total += tolerated
        flagged += 1 if flags else 0
        ok += 1
        print(f"{doc_id} ok tolerated={tolerated} flags={len(flags)}")
    write_json(flags_path, dict(sorted(flags_all.items())))
    totals = " ".join(f"{t}={type_totals[t]}" for t in TYPES)
    print(
        f"convert ok={ok} failed={failed} flagged_docs={flagged} "
        f"tolerated_chars={tolerated_total} entities: {totals}"
    )
    return 0 if failed == 0 else 2


def next_step(failures: int, replacements: int) -> str:
    """B6.1 for one plan row and one annotator, after ``failures`` format failures
    on the row's current document, with ``replacements`` replacements used.

    ``ok`` (no failure), ``rerun`` (first failure: re-run that annotator once),
    ``replace`` (still failing: a new document from the same plan row, annotated
    by both), or ``ask-lionel`` (the one replacement is used: Lionel gets a
    count-only choice, one more replacement or drop the row).
    """
    if failures <= 0:
        return "ok"
    if failures == 1:
        return "rerun"
    return "replace" if replacements == 0 else "ask-lionel"


# ---------------------------------------------------------------------------
# agreement (B6.3) and disagreement classes
# ---------------------------------------------------------------------------


def load_spans(doc_id: str, path: Path) -> list[Span]:
    return [
        Span(doc_id, e.start_pos, e.end_pos, e.entity_type, e.text)
        for e in load_annotations(path)
    ]


def _overlap(a: Span, b: Span) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start))


def _pair_by_overlap(
    a_free: list[Span], b_free: list[Span], same_type: bool
) -> list[tuple[Span, Span]]:
    pairs: list[tuple[Span, Span]] = []
    for a in list(a_free):
        best: Span | None = None
        best_overlap = 0
        for b in b_free:
            if b.doc != a.doc:
                continue
            ov = _overlap(a, b)
            if ov == 0:
                continue
            if same_type:
                if b.etype != a.etype or _match_key(a.text, a.etype) == _match_key(
                    b.text, b.etype
                ):
                    continue
            if ov > best_overlap:
                best, best_overlap = b, ov
        if best is not None:
            pairs.append((a, best))
            a_free.remove(a)
            b_free.remove(best)
    return pairs


def classify(
    a_unmatched: list[Span], b_unmatched: list[Span]
) -> list[tuple[str, Span | None, Span | None]]:
    """Pair unmatched spans into disagreements, in the story's fixed order."""
    a_free = sorted(a_unmatched, key=Span.sort_key)
    b_free = sorted(b_unmatched, key=Span.sort_key)
    result: list[tuple[str, Span | None, Span | None]] = []
    for a in list(a_free):
        for b in b_free:
            if (b.doc, b.start, b.end) == (
                a.doc,
                a.start,
                a.end,
            ) and b.etype != a.etype:
                result.append(("type", a, b))
                a_free.remove(a)
                b_free.remove(b)
                break
    result += [("boundary", a, b) for a, b in _pair_by_overlap(a_free, b_free, True)]
    result += [("other", a, b) for a, b in _pair_by_overlap(a_free, b_free, False)]
    result += [("one-sided", a, None) for a in a_free]
    result += [("one-sided", None, b) for b in b_free]
    return result


@dataclass
class Comparison:
    matched: list[tuple[Span, Span]]
    a_unmatched: list[Span]
    b_unmatched: list[Span]


def compare(doc_id: str, a: list[Span], b: list[Span]) -> Comparison:
    """Match B (candidate) against A (reference) with the scorer's matching."""
    gt = [GroundTruthEntity(s.text, s.etype, s.start, s.end) for s in a]
    det = [
        DetectedEntity(
            text=s.text, entity_type=s.etype, start_pos=s.start, end_pos=s.end
        )
        for s in b
    ]
    tp, fp, fn = match_entities(det, gt)

    def to_span(e: GroundTruthEntity | DetectedEntity) -> Span:
        return Span(doc_id, e.start_pos, e.end_pos, e.entity_type, e.text)

    return Comparison(
        matched=[(to_span(g), to_span(d)) for d, g in tp],
        a_unmatched=[to_span(g) for g in fn],
        b_unmatched=[to_span(d) for d in fp],
    )


def paired_ids(a_dir: Path, b_dir: Path) -> list[str]:
    a_ids = sorted(p.stem for p in a_dir.glob("*.json"))
    b_ids = sorted(p.stem for p in b_dir.glob("*.json"))
    if a_ids != b_ids or not a_ids:
        raise ValueError("annotator folders differ")
    return a_ids


def agreement_lines(a_dir: Path, b_dir: Path) -> list[str]:
    counts = {t: [0, 0, 0] for t in TYPES}  # matched, b_only, a_only
    a_totals = {t: 0 for t in TYPES}
    b_totals = {t: 0 for t in TYPES}
    classes = {c: 0 for c in CLASSES}
    ids = paired_ids(a_dir, b_dir)
    for doc_id in ids:
        a = load_spans(doc_id, a_dir / f"{doc_id}.json")
        b = load_spans(doc_id, b_dir / f"{doc_id}.json")
        for s in a:
            a_totals[s.etype] += 1
        for s in b:
            b_totals[s.etype] += 1
        cmp = compare(doc_id, a, b)
        for ga, _ in cmp.matched:
            counts[ga.etype][0] += 1
        for sb in cmp.b_unmatched:
            counts[sb.etype][1] += 1
        for sa in cmp.a_unmatched:
            counts[sa.etype][2] += 1
        for cls, _, _ in classify(cmp.a_unmatched, cmp.b_unmatched):
            classes[cls] += 1
    lines = []
    total = [sum(counts[t][k] for t in TYPES) for k in range(3)]
    for label, (m, bo, ao) in [("Overall", total), *[(t, counts[t]) for t in TYPES]]:
        f1 = compute_metrics(m, bo, ao).f1
        lines.append(
            f"[AGREEMENT {label}] F1={f1:.4f} matched={m} a_only={ao} b_only={bo}"
        )
    lines.append(
        "[DISAGREEMENTS] total="
        + str(sum(classes.values()))
        + " "
        + " ".join(f"{c}={classes[c]}" for c in CLASSES)
    )
    lines.append(
        "[ENTITIES A] "
        + " ".join(f"{t}={a_totals[t]}" for t in TYPES)
        + f" total={sum(a_totals.values())}"
    )
    lines.append(
        "[ENTITIES B] "
        + " ".join(f"{t}={b_totals[t]}" for t in TYPES)
        + f" total={sum(b_totals.values())}"
    )
    lines.append(f"docs={len(ids)}")
    return lines


def cmd_agreement(a_dir: Path, b_dir: Path) -> int:
    for line in agreement_lines(a_dir, b_dir):
        print(line)
    return 0


# ---------------------------------------------------------------------------
# view, merge and report (B9, B10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Disagreement:
    did: str
    cls: str
    a: Span | None
    b: Span | None

    @property
    def start(self) -> int:
        return min(s.start for s in (self.a, self.b) if s is not None)

    @property
    def end(self) -> int:
        return max(s.end for s in (self.a, self.b) if s is not None)


def load_manifest(workspace: Path) -> dict[str, str]:
    """Return {document id: half} from ``manifest.json``."""
    data = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    return {d["id"]: d["half"] for d in data["documents"]}


def doc_ids(workspace: Path) -> list[str]:
    ids = paired_ids(workspace / "ann_a", workspace / "ann_b")
    if sorted(load_manifest(workspace)) != ids:
        raise ValueError("manifest and annotations differ")
    return ids


def doc_state(
    workspace: Path, doc_id: str
) -> tuple[str, list[Span], list[Disagreement]]:
    """Document text, agreed spans (A's side of each match) and disagreements."""
    text = (workspace / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
    a = load_spans(doc_id, workspace / "ann_a" / f"{doc_id}.json")
    b = load_spans(doc_id, workspace / "ann_b" / f"{doc_id}.json")
    cmp = compare(doc_id, a, b)
    agreed = sorted((sa for sa, _ in cmp.matched), key=Span.sort_key)
    raw = classify(cmp.a_unmatched, cmp.b_unmatched)

    def order(item: tuple[str, Span | None, Span | None]) -> tuple[int, int, int, str]:
        cls, sa, sb = item
        spans = [s for s in (sa, sb) if s is not None]
        return (
            min(s.start for s in spans),
            max(s.end for s in spans),
            CLASSES.index(cls),
            "".join(s.etype for s in spans),
        )

    disagreements = [
        Disagreement(f"{doc_id}-d{k:03d}", cls, sa, sb)
        for k, (cls, sa, sb) in enumerate(sorted(raw, key=order), start=1)
    ]
    return text, agreed, disagreements


def agreed_ids(doc_id: str, agreed: list[Span]) -> dict[str, Span]:
    return {f"{doc_id}-a{k:03d}": s for k, s in enumerate(agreed, start=1)}


SPLIT = "SPLIT"
DECISIONS_HEADER = "group\tclass\tcount\tdecision\tnote"
OCCURRENCES_HEADER = "id\tgroup\tclass\tdecision\tnote"
GroupKey = tuple[str, str, str, str, str]


@dataclass(frozen=True)
class Group:
    """Identical disagreements, decided once (story precision, 2026-10-10)."""

    gid: str
    key: GroupKey
    members: tuple[Disagreement, ...]

    @property
    def cls(self) -> str:
        return self.key[4]


def group_key(d: Disagreement) -> GroupKey:
    """(A's normalized string, A's type, B's normalized string, B's type, class).

    Strings are normalized with the scorer's ``_match_key``; a missing side is
    ``-``. For a ``type`` or ``one-sided`` disagreement this is one string.
    """
    a_key, a_type = (_match_key(d.a.text, d.a.etype), d.a.etype) if d.a else ("-", "-")
    b_key, b_type = (_match_key(d.b.text, d.b.etype), d.b.etype) if d.b else ("-", "-")
    return (a_key, a_type, b_key, b_type, d.cls)


def build_groups(workspace: Path) -> tuple[list[Group], dict[str, str]]:
    """Groups in order of first occurrence, and the text of each document."""
    members: dict[GroupKey, list[Disagreement]] = {}
    texts: dict[str, str] = {}
    for doc_id in doc_ids(workspace):
        text, _, disagreements = doc_state(workspace, doc_id)
        texts[doc_id] = text
        for d in disagreements:
            members.setdefault(group_key(d), []).append(d)
    width = max(3, len(str(len(members))))
    groups = [
        Group(f"g{k:0{width}d}", key, tuple(found))
        for k, (key, found) in enumerate(members.items(), start=1)
    ]
    return groups, texts


def group_counts(groups: list[Group]) -> tuple[int, int, int]:
    """(groups, groups with one occurrence, groups with more than one)."""
    single = sum(1 for g in groups if len(g.members) == 1)
    return len(groups), single, len(groups) - single


def context_window(text: str, start: int, end: int) -> tuple[int, int]:
    """From the start of the line before ``start`` to the end of the line after ``end``."""
    line_start = text.rfind("\n", 0, start)
    line_start = text.rfind("\n", 0, max(line_start, 0)) + 1 if line_start > 0 else 0
    line_end = text.find("\n", end)
    if line_end >= 0:
        nxt = text.find("\n", line_end + 1)
        line_end = len(text) if nxt < 0 else nxt
    else:
        line_end = len(text)
    return line_start, line_end


def spotcheck_documents(halves: dict[str, str]) -> list[str]:
    """3 documents: 1 planted, 1 natural, then 1 of the rest (B9.2, AC5)."""
    rng = random.Random(SPOTCHECK_SEED)
    planted = rng.choice(sorted(i for i, h in halves.items() if h == "planted"))
    natural = rng.choice(sorted(i for i, h in halves.items() if h == "natural"))
    rest = rng.choice(sorted(set(halves) - {planted, natural}))
    return [planted, natural, rest]


_CSS = (
    "body{font-family:sans-serif;margin:1.5em;max-width:60em}"
    "pre{white-space:pre-wrap;background:#f6f6f6;padding:.6em;border:1px solid #ddd}"
    "mark.a{background:#cfe8ff}mark.b{background:#ffe2b8}mark.g{background:#d8f5d0}"
    "sup{font-size:.7em;color:#555}h2{margin-top:2em}table{border-collapse:collapse}"
    "td,th{border:1px solid #ccc;padding:.2em .5em;text-align:left}"
)


def _html_page(title: str, body: list[str]) -> str:
    return (
        '<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>{_CSS}</style></head><body>\n"
        + "\n".join(body)
        + "\n</body></html>\n"
    )


def _marked(text: str, lo: int, hi: int, span: Span | None, css: str) -> str:
    if span is None:
        return f"<pre>{html.escape(text[lo:hi])}</pre><p><em>no span</em></p>"
    return (
        "<pre>"
        + html.escape(text[lo : span.start])
        + f'<mark class="{css}">{html.escape(text[span.start:span.end])}</mark>'
        + f"<sup>{span.etype}</sup>"
        + html.escape(text[span.end : hi])
        + "</pre>"
    )


def _marked_all(text: str, spans: dict[str, Span]) -> str:
    """Whole text with non-crossing spans marked (crossing ones are in the table)."""
    opened: list[tuple[int, int]] = []
    events: list[tuple[int, int, int, str]] = []
    for sid, s in sorted(
        spans.items(), key=lambda kv: (kv[1].start, -kv[1].end, kv[0])
    ):
        if any(o_start < s.start < o_end < s.end for o_start, o_end in opened):
            continue
        n = len(opened)
        opened.append((s.start, s.end))
        events.append((s.start, 1, n, '<mark class="g">'))
        events.append((s.end, 0, -n, f"</mark><sup>{sid[-4:]} {s.etype}</sup>"))
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    out, pos = [], 0
    for offset, _, _, tag in events:
        out.append(html.escape(text[pos:offset]))
        out.append(tag)
        pos = offset
    out.append(html.escape(text[pos:]))
    return "<pre>" + "".join(out) + "</pre>"


SNIPPET_CHARS = 80


def snippet_window(text: str, d: Disagreement) -> tuple[int, int]:
    """The disagreement's line(s), cut to SNIPPET_CHARS on each side."""
    line_start = text.rfind("\n", 0, d.start) + 1
    line_end = text.find("\n", d.end)
    line_end = len(text) if line_end < 0 else line_end
    return max(line_start, d.start - SNIPPET_CHARS), min(
        line_end, d.end + SNIPPET_CHARS
    )


def _occurrence_html(text: str, d: Disagreement) -> str:
    lo, hi = snippet_window(text, d)
    return (
        f"<p><b>{d.did}</b></p>"
        + "<p>A</p>"
        + _marked(text, lo, hi, d.a, "a")
        + "<p>B</p>"
        + _marked(text, lo, hi, d.b, "b")
    )


DECISION_FILES = ("decisions.tsv", "occurrences.tsv", "spotcheck.tsv")


def cmd_view(workspace: Path, force: bool = False) -> int:
    if not force:
        for name in DECISION_FILES:
            if (workspace / name).exists():
                raise OverwriteError("decision file exists", where=name)
    halves = load_manifest(workspace)
    groups, texts = build_groups(workspace)
    view: list[str] = ["<h1>Final exam: disagreements, grouped</h1>"]
    decisions = [DECISIONS_HEADER]
    occurrences = [OCCURRENCES_HEADER]
    total = 0
    for g in groups:
        a_type, b_type = g.key[1], g.key[3]
        n = len(g.members)
        view.append(
            f"<h2>{g.gid} ({g.cls}): A {a_type if a_type != '-' else 'none'}, "
            f"B {b_type if b_type != '-' else 'none'}, "
            f"{n} occurrence{'s' if n > 1 else ''}</h2>"
        )
        for d in g.members[:2]:
            view.append(_occurrence_html(texts[d.did.split("-")[0]], d))
        if n > 2:
            view.append(f"<details><summary>All {n} occurrences</summary>")
            for d in g.members:
                view.append(_occurrence_html(texts[d.did.split("-")[0]], d))
            view.append("</details>")
        decisions.append(f"{g.gid}\t{g.cls}\t{n}\t\t")
        for d in g.members:
            occurrences.append(f"{d.did}\t{g.gid}\t{g.cls}\t\t")
        total += n
    write_text(workspace / "adjudication_view.html", _html_page("Adjudication", view))
    write_text(workspace / "decisions.tsv", "\n".join(decisions) + "\n")
    write_text(workspace / "occurrences.tsv", "\n".join(occurrences) + "\n")
    spot = spotcheck_documents(halves)
    sview: list[str] = ["<h1>Final exam: spot-check (agreed spans)</h1>"]
    srows = ["document\tcorrection\tnote"]
    agreed_total = 0
    for doc_id in sorted(spot):
        text, agreed, _ = doc_state(workspace, doc_id)
        named = agreed_ids(doc_id, agreed)
        agreed_total += len(named)
        sview.append(f"<h2>{doc_id}</h2>" + _marked_all(text, named))
        sview.append("<table><tr><th>id</th><th>type</th><th>text</th></tr>")
        for sid, s in named.items():
            sview.append(
                f"<tr><td>{sid}</td><td>{s.etype}</td><td>{html.escape(s.text)}</td></tr>"
            )
        sview.append("</table>")
        srows.append(f"{doc_id}\t\t")
    write_text(workspace / "spotcheck_view.html", _html_page("Spot-check", sview))
    write_text(workspace / "spotcheck.tsv", "\n".join(srows) + "\n")
    n_groups, single, multi = group_counts(groups)
    print(
        f"view disagreements={total} groups={n_groups} single={single} multi={multi} "
        f"written={workspace / 'adjudication_view.html'}"
    )
    print(
        f"view decisions={workspace / 'decisions.tsv'} {workspace / 'occurrences.tsv'}"
    )
    print(
        f"view spotcheck_documents={len(spot)} agreed_spans={agreed_total} "
        f"written={workspace / 'spotcheck_view.html'} {workspace / 'spotcheck.tsv'}"
    )
    return 0


def read_tsv(path: Path, header: str) -> list[tuple[str, list[str]]]:
    """(``<file>:<line>``, cells) per non-empty row. Read as ``utf-8-sig``, so a
    byte-order mark added by an editor does not break the header (QA ADJ-003)."""
    lines = path.read_text(encoding="utf-8-sig").replace("\r", "").split("\n")
    if lines[0] != header:
        raise DecisionError("bad header", where=f"{path.name}:1")
    return [
        (f"{path.name}:{n}", line.split("\t"))
        for n, line in enumerate(lines[1:], start=2)
        if line.strip()
    ]


def _occurrences(text: str, needle: str) -> list[int]:
    found, i = [], text.find(needle)
    while needle and i >= 0:
        found.append(i)
        i = text.find(needle, i + 1)
    return found


def _whole_word(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    return not before.isalnum() and not after.isalnum()


def _parse_type(value: str) -> str:
    if value not in TYPES:
        raise DecisionError("unknown type")
    return value


G5_REASON = "G5: two spans of the same type cannot overlap"


def apply_decision(
    text: str, d: Disagreement, code: str, allow_both_boundary: bool = False
) -> list[Span]:
    """The spans one decision keeps. ``BOTH`` is refused on a ``type`` group
    (two types on one span) and on a ``boundary`` group (G5), unless the merge
    runs with Lionel's 2026-10-12 rule (``--g5-keep-longer``)."""
    if code == "BOTH" and d.cls == "boundary" and not allow_both_boundary:
        raise DecisionError(G5_REASON, where=d.did)
    if code == "A" and d.a is not None:
        return [d.a]
    if code == "B" and d.b is not None:
        return [d.b]
    if code == "BOTH" and d.a is not None and d.b is not None and d.cls != "type":
        return [d.a, d.b]
    if code == "NONE":
        return []
    if code.startswith("FIX:"):
        _, etype, needle = code.split(":", 2)
        etype = _parse_type(etype)
        lo, hi = context_window(text, d.start, d.end)
        # The FIX span must overlap its own disagreement (QA ADJ-001): a group's
        # occurrences share a normalized key, not the raw text, so a FIX text may
        # exist only on a neighbouring line. Then the group must be split.
        hits = [
            i
            for i in _occurrences(text, needle)
            if lo <= i
            and i + len(needle) <= hi
            and i < d.end
            and d.start < i + len(needle)
        ]
        if not hits:
            raise DecisionError(
                "FIX text does not overlap its disagreement", where=d.did
            )
        i = min(hits, key=lambda h: (abs(h - d.start), h))
        doc_id = d.did.split("-")[0]
        return [Span(doc_id, i, i + len(needle), etype, needle)]
    raise DecisionError("unknown or inapplicable code", where=d.did)


def apply_spotcheck(
    text: str, doc_id: str, spans: list[Span], named: dict[str, Span], code: str
) -> tuple[list[Span], str, int]:
    """Apply one spot-check correction. Returns (spans, class, occurrences added)."""
    if code == "NONE":
        return spans, "none", 0
    kind, _, rest = code.partition(":")
    if kind == "MISSING":
        etype, _, needle = rest.partition(":")
        etype = _parse_type(etype)
        nth = None
        m = re.fullmatch(r"(.*)@(\d+)", needle)
        if m:
            needle, nth = m.group(1), int(m.group(2))
        free = [
            i
            for i in _occurrences(text, needle)
            if _whole_word(text, i, i + len(needle))
            and not any(s.start < i + len(needle) and i < s.end for s in spans)
        ]
        if nth is not None:
            free = free[nth - 1 : nth] if 0 < nth <= len(free) else []
        if not free:
            raise DecisionError("MISSING text not found")
        added = [Span(doc_id, i, i + len(needle), etype, needle) for i in free]
        return spans + added, "MISSING", len(added)
    if kind in ("REMOVE", "RETYPE", "BOUNDARY"):
        sid, _, value = rest.partition(":")
        if sid not in named or named[sid] not in spans:
            raise DecisionError("unknown agreed id")
        target = named[sid]
        kept = [s for s in spans if s != target]
        if kind == "REMOVE" and not value:
            return kept, "REMOVE", 0
        if kind == "RETYPE":
            etype = _parse_type(value)
            return (
                kept + [Span(doc_id, target.start, target.end, etype, target.text)],
                "RETYPE",
                0,
            )
        if kind == "BOUNDARY" and value:
            hits = [
                i
                for i in _occurrences(text, value)
                if i < target.end and target.start < i + len(value)
            ]
            if not hits:
                raise DecisionError("BOUNDARY text does not overlap")
            i = min(hits, key=lambda h: (abs(h - target.start), h))
            return (
                kept + [Span(doc_id, i, i + len(value), target.etype, value)],
                "BOUNDARY",
                0,
            )
    raise DecisionError("unknown spot-check code")


SPOT_CLASSES = ("MISSING", "REMOVE", "RETYPE", "BOUNDARY")


def read_decisions(workspace: Path, groups: list[Group]) -> dict[str, str]:
    """The code that applies to each disagreement id (B10.1, grouped)."""
    by_gid = {g.gid: g for g in groups}
    group_codes: dict[str, str] = {}
    for where, row in read_tsv(workspace / "decisions.tsv", DECISIONS_HEADER):
        if len(row) < 4 or row[0] not in by_gid or row[0] in group_codes:
            raise DecisionError("unknown or duplicate group", where=where)
        if not row[3].strip():
            raise DecisionError("empty group decision", where=row[0])
        group_codes[row[0]] = row[3].strip()
    missing = sorted(set(by_gid) - set(group_codes))
    if missing:
        raise DecisionError("group without a decision", where=missing[0])
    member_gid = {d.did: g.gid for g in groups for d in g.members}
    occurrence_codes: dict[str, str] = {}
    for where, row in read_tsv(workspace / "occurrences.tsv", OCCURRENCES_HEADER):
        if (
            len(row) < 2
            or member_gid.get(row[0]) != row[1]
            or row[0] in occurrence_codes
        ):
            raise DecisionError("unknown or duplicate occurrence", where=where)
        occurrence_codes[row[0]] = row[3].strip() if len(row) > 3 else ""
    decisions: dict[str, str] = {}
    for g in groups:
        split = group_codes[g.gid] == SPLIT
        for d in g.members:
            own = occurrence_codes.get(d.did, "")
            if split and (not own or own == SPLIT):
                raise DecisionError("split group, undecided occurrence", where=d.did)
            if not split and own:
                raise DecisionError("occurrence code, unsplit group", where=d.did)
            decisions[d.did] = own if split else group_codes[g.gid]
    return decisions


@dataclass
class G5Stats:
    """Counts of the G5 step: same-type spans nested in a longer one, dropped."""

    resolved: dict[str, int]
    origins: dict[str, int]
    groups: set[str]
    duplicates: int = 0

    @property
    def total(self) -> int:
        return sum(self.resolved.values())


G5_ORIGINS = ("both_boundary", "b_one_sided", "other")
Origin = tuple[str, str, str]  # (group id, applied code, class)


def _overlaps(a: Span, b: Span) -> bool:
    return a.start < b.end and b.start < a.end


def same_type_overlaps(spans: list[Span]) -> int:
    """Count of same-type overlapping pairs (G5); a separate check."""
    return sum(
        1
        for i, a in enumerate(spans)
        for b in spans[i + 1 :]
        if a.etype == b.etype and _overlaps(a, b)
    )


def _origin_kind(dropped: Origin | None, kept: Origin | None) -> str:
    if dropped and kept and dropped[0] == kept[0] and dropped[1] == "BOTH":
        return "both_boundary" if dropped[2] == "boundary" else "other"
    if any(o and o[1] == "B" and o[2] == "one-sided" for o in (dropped, kept)):
        return "b_one_sided"
    return "other"


def resolve_g5(
    spans_by_doc: dict[str, list[Span]],
    origin: dict[tuple[str, int, int, str], Origin],
    keep_longer: bool,
) -> tuple[dict[str, list[Span]], G5Stats]:
    """GUIDELINES G5 after every decision (Lionel, 2026-10-12, "Keep the longer one").

    Per document and type, a span inside a longer same-type span is dropped and
    the longer one kept (with ``keep_longer``; otherwise it is refused). A
    partial same-type overlap is always refused. Cross-type overlaps (G7) are
    untouched. Errors name anonymous group ids only (``agreed`` for spans both
    annotators had).
    """
    stats = G5Stats({t: 0 for t in TYPES}, {k: 0 for k in G5_ORIGINS}, set())
    partial: set[str] = set()
    partial_n = 0
    nested: set[str] = set()
    nested_n = 0
    out: dict[str, list[Span]] = {}

    def gid(doc: str, s: Span) -> str:
        o = origin.get((doc, s.start, s.end, s.etype))
        return o[0] if o else "agreed"

    for doc in sorted(spans_by_doc):
        spans = spans_by_doc[doc]
        kept_all: list[Span] = [s for s in spans if s.etype not in TYPES]
        for etype in TYPES:
            same = [s for s in spans if s.etype == etype]
            container: dict[Span, Span] = {}
            for s in same:
                around = [
                    o
                    for o in same
                    if o.start <= s.start
                    and s.end <= o.end
                    and (o.start, o.end) != (s.start, s.end)
                ]
                if around:
                    container[s] = min(
                        around, key=lambda o: (o.end - o.start, o.start, o.end)
                    )
            for s, c in sorted(container.items(), key=lambda kv: kv[0].sort_key()):
                if not keep_longer:
                    nested_n += 1
                    nested.update({gid(doc, s), gid(doc, c)})
                    continue
                o_s = origin.get((doc, s.start, s.end, s.etype))
                o_c = origin.get((doc, c.start, c.end, c.etype))
                stats.resolved[etype] += 1
                stats.origins[_origin_kind(o_s, o_c)] += 1
                stats.groups.update(o[0] for o in (o_s, o_c) if o)
            kept = [s for s in same if s not in container] if keep_longer else same
            for i, a in enumerate(kept):
                for b in kept[i + 1 :]:
                    if _overlaps(a, b) and a not in container and b not in container:
                        inside = (a.start <= b.start and b.end <= a.end) or (
                            b.start <= a.start and a.end <= b.end
                        )
                        if not inside:
                            partial_n += 1
                            partial.update({gid(doc, a), gid(doc, b)})
            kept_all += kept
        out[doc] = sorted(kept_all, key=Span.sort_key)
    if partial_n:
        raise G5Error(
            "partial same-type overlap",
            where=f"partial={partial_n}:{','.join(sorted(partial))}",
        )
    if nested_n:
        raise G5Error(
            "nested same-type spans",
            where=f"nested={nested_n}:{','.join(sorted(nested))}",
        )
    if keep_longer and any(same_type_overlaps(s) for s in out.values()):
        raise G5Error("G5 check failed after resolution", where="g5")
    return out, stats


def merge_workspace(
    workspace: Path, g5_keep_longer: bool = False
) -> tuple[dict[str, list[Span]], dict[str, int], dict[str, int], int, G5Stats]:
    """Adjudicated spans per document, decision counts (per disagreement),
    spot-check counts, MISSING occurrences added and the G5 step's counts."""
    ids = doc_ids(workspace)
    halves = load_manifest(workspace)
    groups, _ = build_groups(workspace)
    decisions = read_decisions(workspace, groups)
    gid_of = {d.did: g.gid for g in groups for d in g.members}
    cls_of = {d.did: g.cls for g in groups for d in g.members}
    spot_rows = read_tsv(workspace / "spotcheck.tsv", "document\tcorrection\tnote")
    spot_docs = sorted(spotcheck_documents(halves))
    spot_codes: dict[str, list[tuple[str, str]]] = {d: [] for d in spot_docs}
    for where, row in spot_rows:
        if len(row) < 2 or row[0] not in spot_codes or not row[1].strip():
            raise DecisionError("empty or unknown spot-check row", where=where)
        spot_codes[row[0]].append((where, row[1].strip()))
    for doc_id, codes in spot_codes.items():
        if not codes:
            raise DecisionError("spot-check document without a row", where=doc_id)
    code_counts: dict[str, int] = {}
    spot_counts = {c: 0 for c in SPOT_CLASSES}
    missing_added = 0
    duplicates = 0
    merged: dict[str, list[Span]] = {}
    origin: dict[tuple[str, int, int, str], Origin] = {}
    for doc_id in ids:
        text, agreed, disagreements = doc_state(workspace, doc_id)
        spans = list(agreed)
        agreed_keys = {(s.start, s.end, s.etype) for s in agreed}
        for d in disagreements:
            code = decisions[d.did]
            try:
                kept = apply_decision(text, d, code, allow_both_boundary=g5_keep_longer)
            except DecisionError as exc:
                raise DecisionError(
                    "decision refused", f"{gid_of[d.did]}/{d.did}"
                ) from exc
            key = code.split(":", 1)[0]
            code_counts[key] = code_counts.get(key, 0) + 1
            for s in kept:
                if (s.start, s.end, s.etype) not in agreed_keys:
                    origin.setdefault(
                        (doc_id, s.start, s.end, s.etype),
                        (gid_of[d.did], key, cls_of[d.did]),
                    )
            spans += kept
        named = agreed_ids(doc_id, agreed)
        for where, code in spot_codes.get(doc_id, []):
            try:
                spans, cls, added = apply_spotcheck(text, doc_id, spans, named, code)
            except DecisionError as exc:
                raise DecisionError("spot-check code refused", where=where) from exc
            if cls in spot_counts:
                spot_counts[cls] += 1
            missing_added += added
        unique = {(s.start, s.end, s.etype): s for s in spans}
        duplicates += len(spans) - len(unique)
        merged[doc_id] = sorted(unique.values(), key=Span.sort_key)
    result, g5 = resolve_g5(merged, origin, g5_keep_longer)
    g5.duplicates = duplicates
    return result, code_counts, spot_counts, missing_added, g5


def g5_line(g5: G5Stats) -> str:
    return (
        f"[G5] resolved={g5.total} "
        + " ".join(f"{t}={g5.resolved[t]}" for t in TYPES)
        + " "
        + " ".join(f"{k}={g5.origins[k]}" for k in G5_ORIGINS)
        + f" duplicates_collapsed={g5.duplicates} groups={len(g5.groups)}"
        + (" " + " ".join(sorted(g5.groups)) if g5.groups else "")
    )


def cmd_merge(workspace: Path, g5_keep_longer: bool = False) -> int:
    result, code_counts, spot_counts, missing_added, g5 = merge_workspace(
        workspace, g5_keep_longer
    )
    out = workspace / "annotations"
    out.mkdir(exist_ok=True)
    totals = {t: 0 for t in TYPES}
    for doc_id, spans in result.items():
        text = (workspace / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
        entities = []
        for s in spans:
            if text[s.start : s.end] != s.text:
                raise ValueError("span text mismatch")
            entities.append(
                {
                    "entity_text": s.text,
                    "entity_type": s.etype,
                    "start_pos": s.start,
                    "end_pos": s.end,
                }
            )
            totals[s.etype] += 1
        write_json(
            out / f"{doc_id}.json",
            {"document_name": f"{doc_id}.txt", "entities": entities},
        )
    print(f"merge docs={len(result)} " + " ".join(f"{t}={totals[t]}" for t in TYPES))
    print(
        "merge decisions "
        + " ".join(f"{k}={v}" for k, v in sorted(code_counts.items()))
    )
    print(
        "merge spotcheck "
        + " ".join(f"{k}={v}" for k, v in spot_counts.items())
        + f" missing_occurrences_added={missing_added}"
    )
    print("merge " + g5_line(g5))
    return 0


def cmd_report(workspace: Path, g5_keep_longer: bool = False) -> int:
    for line in agreement_lines(workspace / "ann_a", workspace / "ann_b"):
        print(line)
    _, code_counts, spot_counts, missing_added, g5 = merge_workspace(
        workspace, g5_keep_longer
    )
    groups, _ = build_groups(workspace)
    n_groups, single, multi = group_counts(groups)
    split = sum(
        1
        for _, row in read_tsv(workspace / "decisions.tsv", DECISIONS_HEADER)
        if row[3].strip() == SPLIT
    )
    print(f"[GROUPS] groups={n_groups} single={single} multi={multi} split={split}")
    print("[DECISIONS] " + " ".join(f"{k}={v}" for k, v in sorted(code_counts.items())))
    print(
        f"[SPOT-CHECK] documents=3 shared_errors={sum(spot_counts.values())} "
        + " ".join(f"{k}={v}" for k, v in spot_counts.items())
        + f" missing_occurrences_added={missing_added}"
    )
    print(g5_line(g5))
    return 0


def cmd_guard_report(workspace: Path, annotations: Path) -> int:
    from tests.unit.test_final_exam_leakage import (
        final_exam_leaks,
        final_exam_only_keys,
        string_hash,
    )

    keys = final_exam_only_keys(annotations)
    by_hash = {string_hash(k): k for k in keys}
    hits = final_exam_leaks(keys)
    lines = ["path\tsha256\tstring"] + [f"{p}\t{h}\t{by_hash[h]}" for p, h in hits]
    path = workspace / "guard_hits.txt"
    write_text(path, "\n".join(lines) + "\n")
    print(f"guard-report hits={len(hits)} written={path}")
    return 0


# ---------------------------------------------------------------------------
# serve: one group at a time in the browser (story precision, 2026-10-12)
# ---------------------------------------------------------------------------
#
# A local, stdlib-only server for Lionel's adjudication. It reads and writes
# the same decisions.tsv, occurrences.tsv and spotcheck.tsv as the TSV route,
# with the same groups, ids and refusal rules (apply_decision,
# apply_spotcheck), so `merge` is unchanged. It prints its URL and request
# counts only; an error prints its class and an anonymous id, never text.

DEFAULT_PORT = 8765
PORT_TRIES = 20
GUIDELINES_PATH = REPO_ROOT / "tests" / "test_corpus" / "annotations" / "GUIDELINES.md"
SPOT_HEADER = "document\tcorrection\tnote"
SPOT_DONE = "NONE"


def atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to a temporary file next to ``path``, then replace it.

    A crash before the replace leaves ``path`` as it was; a stale temporary
    file is overwritten by the next write and never read.
    """
    tmp = path.with_name(f".{path.name}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def clean_note(note: str) -> str:
    """One line, no tab: a note must not break the TSV."""
    return " ".join(str(note).replace("\t", " ").split())


def _rows_text(header: str, rows: list[list[str]]) -> str:
    return "\n".join([header] + ["\t".join(r) for r in rows]) + "\n"


def _pad(cells: list[str], n: int) -> list[str]:
    return (cells + [""] * n)[:n]


def guidelines_html(path: Path) -> str:
    """A small Markdown renderer for GUIDELINES.md (headings, lists, tables,
    bold, inline code). The file holds rules only, no exam content."""

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

    out: list[str] = []
    in_list = in_table = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if in_list and not stripped.startswith("- "):
            out.append("</ul>")
            in_list = False
        if in_table and not stripped.startswith("|"):
            out.append("</table>")
            in_table = False
        if not stripped:
            continue
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            out.append(f"<h{level}>{inline(stripped.lstrip('#').strip())}</h{level}>")
        elif stripped.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
            out.append(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>"
            )
        elif stripped == "---":
            out.append("<hr>")
        else:
            out.append(f"<p>{inline(stripped)}</p>")
    if in_list:
        out.append("</ul>")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


class AdjudicationApp:
    """The adjudication state behind ``serve``: the workspace's groups and the
    three decision files, resumed from whatever they already contain."""

    def __init__(self, workspace: Path, guidelines: Path = GUIDELINES_PATH) -> None:
        self.workspace = workspace
        self.guidelines = guidelines
        self.groups, self.texts = build_groups(workspace)
        self.by_gid = {g.gid: g for g in self.groups}
        self.by_did = {d.did: (g, d) for g in self.groups for d in g.members}
        self.requests = 0
        self.saves = 0
        self.dec_rows = self._load(
            "decisions.tsv", DECISIONS_HEADER, 5, [g.gid for g in self.groups]
        )
        self.occ_rows = self._load(
            "occurrences.tsv",
            OCCURRENCES_HEADER,
            5,
            [d.did for g in self.groups for d in g.members],
        )
        halves = load_manifest(workspace)
        self.spot_docs = sorted(spotcheck_documents(halves))
        self.spot_rows = [
            _pad(cells, 3)
            for _, cells in read_tsv(workspace / "spotcheck.tsv", SPOT_HEADER)
        ]
        if any(r[0] not in self.spot_docs for r in self.spot_rows):
            raise DecisionError("unknown spot-check document", where="spotcheck.tsv")
        self.spot_named: dict[str, dict[str, Span]] = {}
        for doc_id in self.spot_docs:
            _, agreed, _ = doc_state(workspace, doc_id)
            self.spot_named[doc_id] = agreed_ids(doc_id, agreed)
            self.texts.setdefault(
                doc_id,
                (workspace / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8"),
            )

    def _load(
        self, name: str, header: str, width: int, expected: list[str]
    ) -> dict[str, list[str]]:
        """Rows keyed by their first cell, in file order; the ids must be exactly
        the ones `view` wrote."""
        rows: dict[str, list[str]] = {}
        for where, cells in read_tsv(self.workspace / name, header):
            cells = _pad(cells, width)
            if cells[0] in rows:
                raise DecisionError("duplicate row", where=where)
            rows[cells[0]] = cells
        if list(rows) != expected:
            raise DecisionError("rows differ from the view", where=name)
        return rows

    # -- decisions --------------------------------------------------------

    def _check(self, members: tuple[Disagreement, ...], code: str, note: str) -> None:
        if code in ("", SPLIT):
            return
        if code == "?":
            if not note:
                raise DecisionError("a note is required with ?", where=members[0].did)
            return
        for d in members:
            if code == "BOTH" and d.cls == "boundary":
                raise DecisionError(G5_REASON, where=d.did)
            if code == "BOTH" and d.cls == "type":
                raise DecisionError(
                    "BOTH is not allowed on a type group: one span cannot have two types",
                    where=d.did,
                )
            if code in ("A", "BOTH") and d.a is None:
                raise DecisionError("A has no span here", where=d.did)
            if code in ("B", "BOTH") and d.b is None:
                raise DecisionError("B has no span here", where=d.did)
            apply_decision(self.texts[d.did.split("-")[0]], d, code)

    def _occurrence_done(self, did: str) -> bool:
        code = self.occ_rows[did][3]
        return bool(code) and code != "?"

    def _group_done(self, g: Group) -> bool:
        code = self.dec_rows[g.gid][3]
        if code == SPLIT:
            return all(self._occurrence_done(d.did) for d in g.members)
        return bool(code) and code != "?"

    def progress(self) -> dict[str, int]:
        unsure = sum(1 for r in self.dec_rows.values() if r[3] == "?")
        unsure += sum(
            1
            for g in self.groups
            if self.dec_rows[g.gid][3] == SPLIT
            for d in g.members
            if self.occ_rows[d.did][3] == "?"
        )
        return {
            "decided": sum(1 for g in self.groups if self._group_done(g)),
            "total": len(self.groups),
            "unsure": unsure,
            "spot_finished": sum(1 for d in self.spot_docs if self._spot_finished(d)),
            "spot_total": len(self.spot_docs),
        }

    def _write_decisions(self) -> None:
        atomic_write_text(
            self.workspace / "decisions.tsv",
            _rows_text(DECISIONS_HEADER, list(self.dec_rows.values())),
        )
        atomic_write_text(
            self.workspace / "occurrences.tsv",
            _rows_text(OCCURRENCES_HEADER, list(self.occ_rows.values())),
        )
        self.saves += 1

    def set_group(self, gid: str, code: str, note: str) -> dict[str, object]:
        if gid not in self.by_gid:
            raise DecisionError("unknown group", where="-")
        g = self.by_gid[gid]
        code, note = str(code).strip(), clean_note(note)
        self._check(g.members, code, note)
        self.dec_rows[gid][3] = code
        self.dec_rows[gid][4] = note
        if code != SPLIT:
            for d in g.members:
                self.occ_rows[d.did][3] = ""
        self._write_decisions()
        return self.group_json(g)

    def set_occurrence(self, did: str, code: str, note: str) -> dict[str, object]:
        if did not in self.by_did:
            raise DecisionError("unknown occurrence", where="-")
        g, d = self.by_did[did]
        if self.dec_rows[g.gid][3] != SPLIT:
            raise DecisionError("the group is not split", where=did)
        code, note = str(code).strip(), clean_note(note)
        if code == SPLIT:
            raise DecisionError("SPLIT is not an occurrence code", where=did)
        self._check((d,), code, note)
        self.occ_rows[did][3] = code
        self.occ_rows[did][4] = note
        self._write_decisions()
        return self.group_json(g)

    # -- spot-check -------------------------------------------------------

    def _spot_finished(self, doc_id: str) -> bool:
        codes = [r[1] for r in self.spot_rows if r[0] == doc_id]
        return bool(codes) and all(codes)

    def set_spotcheck(
        self, doc_id: str, corrections: list[dict[str, str]], finished: bool
    ) -> dict[str, object]:
        """Replace one document's rows. Until it is finished, the document keeps
        an empty row, which `merge` refuses; finished with no finding is NONE."""
        if doc_id not in self.spot_docs:
            raise DecisionError("unknown spot-check document", where="-")
        rows = [
            [doc_id, str(c.get("code", "")).strip(), clean_note(c.get("note", ""))]
            for c in corrections
        ]
        if any(not r[1] or r[1] == SPOT_DONE for r in rows):
            raise DecisionError("empty or NONE correction", where=doc_id)
        spans = list(self.spot_named[doc_id].values())
        for n, r in enumerate(rows, start=1):
            try:
                spans, _, _ = apply_spotcheck(
                    self.texts[doc_id], doc_id, spans, self.spot_named[doc_id], r[1]
                )
            except DecisionError as exc:
                raise DecisionError(exc.args[0], where=f"{doc_id}#{n}") from exc
        if finished and not rows:
            rows = [[doc_id, SPOT_DONE, ""]]
        elif not finished:
            rows.append([doc_id, "", ""])
        others = {d: [r for r in self.spot_rows if r[0] == d] for d in self.spot_docs}
        others[doc_id] = rows
        self.spot_rows = [r for d in self.spot_docs for r in others[d]]
        atomic_write_text(
            self.workspace / "spotcheck.tsv", _rows_text(SPOT_HEADER, self.spot_rows)
        )
        self.saves += 1
        return self.spot_json(doc_id)

    # -- JSON for the page --------------------------------------------------

    def _occurrence_json(self, d: Disagreement) -> dict[str, object]:
        text = self.texts[d.did.split("-")[0]]
        lo, hi = snippet_window(text, d)
        clo, chi = context_window(text, d.start, d.end)

        def rel(s: Span | None, base: int) -> list[int] | None:
            return None if s is None else [s.start - base, s.end - base]

        return {
            "did": d.did,
            "doc": d.did.split("-")[0],
            "a_text": d.a.text if d.a else None,
            "b_text": d.b.text if d.b else None,
            "a_type": d.a.etype if d.a else None,
            "b_type": d.b.etype if d.b else None,
            "snip": {"text": text[lo:hi], "a": rel(d.a, lo), "b": rel(d.b, lo)},
            "ctx": {"text": text[clo:chi], "start": d.start - clo, "end": d.end - clo},
            "decision": self.occ_rows[d.did][3],
            "note": self.occ_rows[d.did][4],
        }

    def group_json(self, g: Group) -> dict[str, object]:
        first = g.members[0]
        return {
            "gid": g.gid,
            "cls": g.cls,
            "count": len(g.members),
            "a_type": g.key[1] if g.key[1] != "-" else None,
            "b_type": g.key[3] if g.key[3] != "-" else None,
            "a_text": first.a.text if first.a else None,
            "b_text": first.b.text if first.b else None,
            "decision": self.dec_rows[g.gid][3],
            "note": self.dec_rows[g.gid][4],
            "done": self._group_done(g),
            "occurrences": [self._occurrence_json(d) for d in g.members],
        }

    def spot_json(self, doc_id: str) -> dict[str, object]:
        rows = [r for r in self.spot_rows if r[0] == doc_id]
        return {
            "doc": doc_id,
            "text": self.texts[doc_id],
            "spans": [
                {
                    "id": sid,
                    "start": s.start,
                    "end": s.end,
                    "type": s.etype,
                    "text": s.text,
                }
                for sid, s in self.spot_named[doc_id].items()
            ],
            "corrections": [
                {"code": r[1], "note": r[2]} for r in rows if r[1] and r[1] != SPOT_DONE
            ],
            "finished": self._spot_finished(doc_id),
        }

    def state(self) -> dict[str, object]:
        return {
            "groups": [self.group_json(g) for g in self.groups],
            "spot": [self.spot_json(d) for d in self.spot_docs],
            "progress": self.progress(),
            "types": list(TYPES),
        }


class _Handler(BaseHTTPRequestHandler):
    server_version = "FinalExamAdjudication/1"
    app: AdjudicationApp
    origins: frozenset[str]

    def log_message(self, fmt: str, *args: object) -> None:
        """No request lines: paths and bodies are never printed."""

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: object) -> None:
        self._send(
            status,
            json.dumps(data, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _allowed(self) -> bool:
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        hosts = {o.split("//", 1)[1] for o in self.origins}
        return host in hosts and (origin is None or origin in self.origins)

    def _count(self) -> None:
        app = self.app
        app.requests += 1
        if app.requests % 25 == 0:
            print(f"requests={app.requests} saves={app.saves}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        self._count()
        if not self._allowed():
            self._json(403, {"error": "Forbidden"})
            return
        try:
            if self.path == "/":
                self._send(200, UI_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(200, self.app.state())
            elif self.path == "/api/guidelines":
                body = guidelines_html(self.app.guidelines).encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
            else:
                self._json(404, {"error": "NotFound"})
        except Exception as exc:  # noqa: BLE001 - class only (Error Output)
            print(f"ERROR - {type(exc).__name__}", flush=True)
            self._json(500, {"error": type(exc).__name__})

    def do_POST(self) -> None:  # noqa: N802
        self._count()
        if not self._allowed():
            self._json(403, {"error": "Forbidden"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            app = self.app
            if self.path == "/api/group":
                group = app.set_group(
                    data["gid"], data["decision"], data.get("note", "")
                )
                self._json(200, {"group": group, "progress": app.progress()})
            elif self.path == "/api/occurrence":
                group = app.set_occurrence(
                    data["did"], data["decision"], data.get("note", "")
                )
                self._json(200, {"group": group, "progress": app.progress()})
            elif self.path == "/api/spotcheck":
                doc = app.set_spotcheck(
                    data["doc"],
                    list(data.get("corrections", [])),
                    bool(data["finished"]),
                )
                self._json(200, {"doc": doc, "progress": app.progress()})
            else:
                self._json(404, {"error": "NotFound"})
        except AnonymousError as exc:
            print(f"ERROR {exc.where} {type(exc).__name__}", flush=True)
            self._json(
                400,
                {
                    "error": type(exc).__name__,
                    "where": exc.where,
                    "reason": exc.args[0],
                },
            )
        except Exception as exc:  # noqa: BLE001 - class only (Error Output)
            print(f"ERROR - {type(exc).__name__}", flush=True)
            self._json(500, {"error": type(exc).__name__})


class _Server(HTTPServer):
    """No port sharing: with SO_REUSEADDR, Windows would let a second server
    bind a port already in use, and the fallback would never happen."""

    allow_reuse_address = False

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(app: AdjudicationApp, port: int = DEFAULT_PORT) -> HTTPServer:
    """Bind 127.0.0.1 on ``port``, or the next free one (``port=0``: any)."""
    last: OSError | None = None
    for candidate in [0] if port == 0 else range(port, port + PORT_TRIES):
        try:
            server = _Server(("127.0.0.1", candidate), _Handler)
        except OSError as exc:
            last = exc
            continue
        bound = server.server_address[1]
        handler = type(
            "Handler",
            (_Handler,),
            {
                "app": app,
                "origins": frozenset(
                    {f"http://127.0.0.1:{bound}", f"http://localhost:{bound}"}
                ),
            },
        )
        server.RequestHandlerClass = handler
        return server
    raise last if last else OSError("no free port")


def cmd_serve(workspace: Path, port: int, open_browser: bool, guidelines: Path) -> int:
    app = AdjudicationApp(workspace, guidelines)
    server = make_server(app, port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"serve url={url}", flush=True)
    print("Close this window (or press Ctrl+C) to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print(f"stopped requests={app.requests} saves={app.saves}", flush=True)
    return 0


UI_HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Final exam adjudication</title>
<style>
:root { --a: #cfe8ff; --a-strong: #2b7bd6; --b: #ffe2b8; --b-strong: #d9822b; --g: #d8f5d0; --ink: #1d1f24; --muted: #646a73; --line: #d9dce1; --bg: #f7f8fa; --ok: #2e8b57; --warn: #b54708; }
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
header { display: flex; gap: 12px; align-items: center; padding: 10px 16px; background: #fff; border-bottom: 1px solid var(--line); position: sticky; top: 0; z-index: 5; flex-wrap: wrap; }
header .tabs button { font-size: 15px; padding: 6px 14px; border: 1px solid var(--line); background: #fff; border-radius: 6px; cursor: pointer; }
header .tabs button.on { background: var(--ink); color: #fff; }
#progress { font-weight: 600; }
#status { color: var(--muted); font-size: 14px; min-width: 120px; }
#status.err { color: var(--warn); font-weight: 600; }
.spacer { flex: 1; }
main { max-width: 1100px; margin: 0 auto; padding: 16px; }
.card { background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 16px; margin-bottom: 14px; }
.head { display: flex; gap: 14px; align-items: baseline; flex-wrap: wrap; }
.gid { font-size: 22px; font-weight: 700; }
.pill { font-size: 13px; padding: 2px 8px; border-radius: 99px; background: #eef0f3; }
.decision { font-size: 15px; }
.decision b { font-size: 18px; }
.sides { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.side { border-radius: 8px; padding: 12px; }
.side.a { background: var(--a); }
.side.b { background: var(--b); }
.side .who { font-size: 13px; color: var(--muted); }
.side .txt { font-size: 24px; font-weight: 600; word-break: break-word; }
.side .typ { font-size: 16px; font-weight: 600; }
.side.none .txt { color: var(--muted); font-weight: 400; font-style: italic; }
.occ { border-top: 1px solid var(--line); padding: 8px 0; }
.occ .id { font-size: 12px; color: var(--muted); }
.occ .line { font-family: ui-monospace, Consolas, monospace; font-size: 14px; white-space: pre-wrap; margin: 2px 0; }
.occ .lab { display: inline-block; width: 18px; font-weight: 700; }
mark.a { background: var(--a); outline: 2px solid var(--a-strong); }
mark.b { background: var(--b); outline: 2px solid var(--b-strong); }
mark.g { background: var(--g); }
mark.cur { outline: 3px solid var(--ink); }
mark.r { background: #f6c9c9; text-decoration: line-through; }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.buttons button { font-size: 17px; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--line); background: #fff; cursor: pointer; min-width: 92px; }
.buttons button:hover:not(:disabled) { background: #eef0f3; }
.buttons button:disabled { opacity: 0.45; cursor: not-allowed; }
.buttons button.chosen { background: var(--ink); color: #fff; }
.buttons .k { display: block; font-size: 11px; color: var(--muted); }
.buttons button.chosen .k { color: #ccc; }
.why { font-size: 13px; color: var(--warn); margin-top: 6px; }
textarea { width: 100%; font: inherit; font-size: 15px; padding: 8px; border-radius: 6px; border: 1px solid var(--line); min-height: 44px; }
.nav { display: flex; gap: 8px; align-items: center; justify-content: space-between; margin-top: 10px; }
.small { font-size: 13px; color: var(--muted); }
#guide { position: fixed; top: 54px; right: 0; bottom: 0; width: min(560px, 92vw); overflow: auto; background: #fff; border-left: 1px solid var(--line); padding: 12px 18px; z-index: 6; font-size: 14px; }
#guide table { border-collapse: collapse; } #guide td { border: 1px solid var(--line); padding: 2px 6px; vertical-align: top; }
#modal { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 10; }
#modal .box { background: #fff; border-radius: 10px; padding: 18px; width: min(640px, 94vw); }
#modal input[type=text] { width: 100%; font-size: 18px; padding: 8px; }
.doctext { font-family: ui-monospace, Consolas, monospace; font-size: 14px; white-space: pre-wrap; max-height: 60vh; overflow: auto; border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: #fff; }
.spotgrid { display: grid; grid-template-columns: 3fr 2fr; gap: 14px; }
.list li { margin: 4px 0; }
[hidden] { display: none !important; }
</style>
</head>
<body>
<header>
  <div class="tabs"><button id="tab-dis" class="on">Disagreements</button> <button id="tab-spot">Spot-check</button></div>
  <span id="progress"></span>
  <span class="spacer"></span>
  <span id="status">loading…</span>
  <div class="tabs"><button id="btn-guide">Guidelines (G)</button></div>
</header>
<main id="main"></main>
<aside id="guide" hidden></aside>
<div id="modal" hidden></div>
<script>
"use strict";
let S = null;            // state from the server
let mode = "dis";        // "dis" | "split" | "spot"
let gi = 0;              // current group
let oi = 0;              // current occurrence (split mode)
let showAll = false;
let sdoc = 0, sspan = 0; // spot-check position
let modalKeys = null;    // key handler while a dialog is open
const TYPES = ["PERSON", "LOCATION", "ORG"];
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

function status(msg, err) { const el = $("status"); el.textContent = msg; el.className = err ? "err" : ""; }

async function api(path, body) {
  const opts = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)};
  const r = await fetch(path, opts);
  let data = {};
  try { data = await r.json(); } catch (e) { data = {error: "BadResponse"}; }
  return {ok: r.ok, data};
}

function refusal(d) { return (d.reason ? d.reason : d.error || "refused") + (d.where && d.where !== "-" ? " (" + d.where + ")" : ""); }

function isDone(g) {
  if (g.decision === "SPLIT") return g.occurrences.every((o) => o.decision && o.decision !== "?");
  return !!g.decision && g.decision !== "?";
}

function showProgress() {
  const p = S.progress;
  $("progress").textContent = `${p.decided}/${p.total} decided` + (p.unsure ? ` · ${p.unsure} unsure` : "") + ` · spot-check ${p.spot_finished}/${p.spot_total}`;
}

async function load() {
  const r = await api("/api/state");
  if (!r.ok) { status("could not load: " + refusal(r.data), true); return; }
  S = r.data;
  const first = S.groups.findIndex((g) => !isDone(g));
  gi = first >= 0 ? first : 0;
  showProgress();
  status("ready");
  render();
}

function render() {
  $("tab-dis").className = mode === "spot" ? "" : "on";
  $("tab-spot").className = mode === "spot" ? "on" : "";
  if (mode === "spot") return renderSpot();
  if (!S.groups.length) { $("main").innerHTML = '<div class="card">No disagreement.</div>'; return; }
  if (mode === "split") return renderSplit();
  renderGroup();
}

function sideHtml(label, cls, text, type) {
  if (text === null || text === undefined) return `<div class="side ${cls} none"><div class="who">${label}</div><div class="txt">no span</div></div>`;
  return `<div class="side ${cls}"><div class="who">${label}</div><div class="txt">${esc(text)}</div><div class="typ">${esc(type)}</div></div>`;
}

function snipLine(snip, range, cls) {
  const t = snip.text;
  if (!range) return esc(t) + ' <span class="small">(no span)</span>';
  const [s, e] = [Math.max(0, range[0]), Math.min(t.length, range[1])];
  return esc(t.slice(0, s)) + `<mark class="${cls}">` + esc(t.slice(s, e)) + "</mark>" + esc(t.slice(e));
}

function occHtml(o, extra) {
  return `<div class="occ"><div class="id">${esc(o.did)}${extra || ""}</div>` +
    `<div class="line"><span class="lab">A</span>${snipLine(o.snip, o.snip.a, "a")}</div>` +
    `<div class="line"><span class="lab">B</span>${snipLine(o.snip, o.snip.b, "b")}</div></div>`;
}

function btn(id, label, key, opts) {
  const o = opts || {};
  return `<button id="${id}" ${o.disabled ? "disabled" : ""} class="${o.chosen ? "chosen" : ""}" title="${esc(o.why || "")}">${label}<span class="k">${key}</span></button>`;
}

function availability(subject) {
  // subject: a group or one occurrence; both carry a_text / b_text
  const isType = (mode === "split" ? S.groups[gi].cls : subject.cls) === "type";
  return {
    A: subject.a_text === null ? "A has no span here" : "",
    B: subject.b_text === null ? "B has no span here" : "",
    BOTH: isType ? "BOTH is not allowed on a type group: one span cannot have two types"
      : (mode === "split" ? S.groups[gi].cls : subject.cls) === "boundary" ? "G5: two spans of the same type cannot overlap"
      : (subject.a_text === null || subject.b_text === null) ? "BOTH needs a span on each side" : "",
  };
}

function decisionButtons(current, av, withSplit) {
  let h = '<div class="buttons">';
  h += btn("d-A", "A", "A or 1", {disabled: !!av.A, why: av.A, chosen: current === "A"});
  h += btn("d-B", "B", "B or 2", {disabled: !!av.B, why: av.B, chosen: current === "B"});
  h += btn("d-BOTH", "BOTH", "3", {disabled: !!av.BOTH, why: av.BOTH, chosen: current === "BOTH"});
  h += btn("d-NONE", "NONE", "N or 0", {chosen: current === "NONE"});
  h += btn("d-FIX", "FIX…", "F", {chosen: current.startsWith("FIX:")});
  if (withSplit) h += btn("d-SPLIT", "SPLIT", "S", {chosen: current === "SPLIT"});
  h += btn("d-UNSURE", "Unsure ?", "?", {chosen: current === "?"});
  h += btn("d-CLEAR", "Clear", "Backspace", {disabled: !current});
  h += "</div>";
  const why = [av.A, av.B, av.BOTH].filter(Boolean);
  if (why.length) h += `<div class="why">${why.map(esc).join(" · ")}</div>`;
  return h;
}

function renderGroup() {
  const g = S.groups[gi];
  const av = availability(g);
  let h = `<div class="card"><div class="head"><span class="gid">${esc(g.gid)}</span><span class="pill">${esc(g.cls)}</span>` +
    `<span class="pill">${g.count} occurrence${g.count > 1 ? "s" : ""}</span>` +
    `<span class="decision">decision: <b>${g.decision ? esc(g.decision) : "—"}</b>${isDone(g) ? " ✓" : ""}</span>` +
    `<span class="spacer"></span><span class="small">group ${gi + 1} of ${S.groups.length}</span></div>`;
  h += `<div class="sides">${sideHtml("A", "a", g.a_text, g.a_type)}${sideHtml("B", "b", g.b_text, g.b_type)}</div>`;
  h += decisionButtons(g.decision, av, true);
  h += `<div style="margin-top:10px"><label class="small" for="note">Note (Tab), optional; required with ?</label><textarea id="note" placeholder="rule ids only, e.g. L1, Q4">${esc(g.note)}</textarea></div>`;
  h += '<div class="nav">' + btn("n-prev", "← Previous", "←") + btn("n-und", "Next undecided", "U") + btn("n-next", "Next →", "→") + "</div></div>";
  h += '<div class="card"><div class="small">Occurrences (A in blue, B in orange)</div>';
  const shown = showAll || g.occurrences.length <= 3 ? g.occurrences : g.occurrences.slice(0, 3);
  shown.forEach((o) => { h += occHtml(o, g.decision === "SPLIT" ? ` · ${o.decision ? esc(o.decision) : "undecided"}` : ""); });
  if (shown.length < g.occurrences.length) h += `<div class="buttons">${btn("n-all", `Show all ${g.occurrences.length}`, "")}</div>`;
  h += "</div>";
  $("main").innerHTML = h;
  wireDecisionButtons(false);
  $("n-prev").onclick = () => go(-1);
  $("n-next").onclick = () => go(1);
  $("n-und").onclick = nextUndecided;
  if ($("n-all")) $("n-all").onclick = () => { showAll = true; render(); };
  $("note").onblur = saveNoteIfDecided;
}

function renderSplit() {
  const g = S.groups[gi];
  const o = g.occurrences[oi];
  const av = availability(o);
  let h = `<div class="card"><div class="head"><span class="gid">${esc(g.gid)} · SPLIT</span><span class="pill">${esc(g.cls)}</span>` +
    `<span class="pill">occurrence ${oi + 1} of ${g.occurrences.length}</span>` +
    `<span class="decision">decision: <b>${o.decision ? esc(o.decision) : "—"}</b></span>` +
    `<span class="spacer"></span>${btn("s-back", "Back to the group", "Esc")}</div>`;
  h += `<div class="sides">${sideHtml("A", "a", o.a_text, o.a_type)}${sideHtml("B", "b", o.b_text, o.b_type)}</div>`;
  h += occHtml(o, "");
  h += decisionButtons(o.decision, av, false);
  h += `<div style="margin-top:10px"><label class="small" for="note">Note (Tab), optional; required with ?</label><textarea id="note">${esc(o.note)}</textarea></div>`;
  h += '<div class="nav">' + btn("n-prev", "← Previous", "←") + btn("n-next", "Next →", "→") + "</div></div>";
  $("main").innerHTML = h;
  wireDecisionButtons(true);
  $("n-prev").onclick = () => { oi = Math.max(0, oi - 1); render(); };
  $("n-next").onclick = () => { oi = Math.min(g.occurrences.length - 1, oi + 1); render(); };
  $("s-back").onclick = leaveSplit;
  $("note").onblur = saveNoteIfDecided;
}

function wireDecisionButtons(split) {
  const on = (id, f) => { const el = $(id); if (el) el.onclick = f; };
  on("d-A", () => decide("A", true));
  on("d-B", () => decide("B", true));
  on("d-BOTH", () => decide("BOTH", true));
  on("d-NONE", () => decide("NONE", true));
  on("d-FIX", openFix);
  on("d-SPLIT", enterSplit);
  on("d-UNSURE", () => decide("?", false));
  on("d-CLEAR", () => decide("", false));
}

function noteValue() { const el = $("note"); return el ? el.value.trim() : ""; }

async function decide(code, advance) {
  const g = S.groups[gi];
  const note = noteValue();
  if (code === "?" && !note) { status("write a note first: ? needs one", true); $("note").focus(); return; }
  if (mode !== "split" && g.decision === "SPLIT" && code !== "SPLIT" && g.occurrences.some((o) => o.decision)
      && !window.confirm("This clears the per-occurrence decisions of this group. Continue?")) return;
  let r;
  if (mode === "split") r = await api("/api/occurrence", {did: g.occurrences[oi].did, decision: code, note});
  else r = await api("/api/group", {gid: g.gid, decision: code, note});
  if (!r.ok) { status("refused: " + refusal(r.data), true); return; }
  S.groups[gi] = r.data.group;
  S.progress = r.data.progress;
  showProgress();
  status(code ? `saved ${mode === "split" ? r.data.group.occurrences[oi].did : g.gid}: ${code}` : "cleared");
  if (advance) {
    if (mode === "split") {
      const occ = S.groups[gi].occurrences;
      const next = occ.findIndex((o, k) => k > oi && !(o.decision && o.decision !== "?"));
      const any = occ.findIndex((o) => !(o.decision && o.decision !== "?"));
      if (next >= 0) oi = next; else if (any >= 0) oi = any; else { mode = "dis"; showAll = false; nextUndecided(); return; }
    } else { nextUndecided(); return; }
  }
  render();
}

async function saveNoteIfDecided() {
  const g = S.groups[gi];
  const cur = mode === "split" ? g.occurrences[oi] : g;
  const note = noteValue();
  if (!cur.decision || note === cur.note) return;
  const r = mode === "split"
    ? await api("/api/occurrence", {did: cur.did, decision: cur.decision, note})
    : await api("/api/group", {gid: g.gid, decision: cur.decision, note});
  if (!r.ok) { status("note refused: " + refusal(r.data), true); return; }
  S.groups[gi] = r.data.group;
  status("note saved");
}

function go(step) {
  gi = (gi + step + S.groups.length) % S.groups.length;
  showAll = false;
  render();
  window.scrollTo(0, 0);
}

function nextUndecided() {
  const n = S.groups.length;
  for (let k = 1; k <= n; k++) {
    const j = (gi + k) % n;
    if (!isDone(S.groups[j])) { gi = j; showAll = false; render(); window.scrollTo(0, 0); return; }
  }
  status("every group is decided");
  render();
}

async function enterSplit() {
  const g = S.groups[gi];
  if (g.decision !== "SPLIT") {
    const r = await api("/api/group", {gid: g.gid, decision: "SPLIT", note: noteValue()});
    if (!r.ok) { status("refused: " + refusal(r.data), true); return; }
    S.groups[gi] = r.data.group;
    S.progress = r.data.progress;
    showProgress();
  }
  mode = "split";
  const first = S.groups[gi].occurrences.findIndex((o) => !(o.decision && o.decision !== "?"));
  oi = first >= 0 ? first : 0;
  status("split: decide each occurrence");
  render();
}

function leaveSplit() { mode = "dis"; render(); }

// ---- FIX dialog --------------------------------------------------------

function overlapsAll(text, occs) {
  // mirrors the merge: the text must occur in the context and overlap the disagreement
  const bad = [];
  occs.forEach((o) => {
    const c = o.ctx.text;
    let i = c.indexOf(text), hit = false;
    while (text && i >= 0) { if (i < o.ctx.end && i + text.length > o.ctx.start) { hit = true; break; } i = c.indexOf(text, i + 1); }
    if (!hit) bad.push(o.did);
  });
  return bad;
}

function openFix() {
  const g = S.groups[gi];
  const subject = mode === "split" ? g.occurrences[oi] : g;
  const targets = mode === "split" ? [g.occurrences[oi]] : g.occurrences;
  let type = subject.a_type || subject.b_type || "PERSON";
  const box = $("modal");
  box.innerHTML = `<div class="box"><h3>FIX: annotate the right text</h3>` +
    `<div class="buttons">${TYPES.map((t, k) => btn("t-" + t, t, ["P", "L", "O"][k], {chosen: t === type})).join("")}</div>` +
    `<p class="small">Text, exactly as in the document (case, accents, spaces):</p><input type="text" id="fix-text">` +
    `<div class="buttons">${btn("fix-a", "Use A's text", "", {disabled: subject.a_text === null})}${btn("fix-b", "Use B's text", "", {disabled: subject.b_text === null})}</div>` +
    `<div id="fix-check" class="small"></div>` +
    `<div class="buttons">${btn("fix-ok", "Save FIX", "Enter")}${mode === "split" ? "" : btn("fix-split", "Switch to SPLIT", "")}${btn("fix-cancel", "Cancel", "Esc")}</div></div>`;
  box.hidden = false;
  const input = $("fix-text");
  input.value = subject.a_text !== null ? subject.a_text : (subject.b_text || "");
  const check = () => {
    const bad = overlapsAll(input.value, targets);
    const el = $("fix-check");
    if (!input.value) { el.textContent = "type the text"; el.className = "why"; return false; }
    if (bad.length) { el.textContent = `not found over ${bad.length} of ${targets.length} occurrence(s) (${bad.slice(0, 5).join(", ")}${bad.length > 5 ? "…" : ""}): ` + (mode === "split" ? "change the text" : "split the group"); el.className = "why"; return false; }
    el.textContent = `matches all ${targets.length} occurrence(s)`; el.className = "small"; return true;
  };
  const setType = (t) => { type = t; TYPES.forEach((x) => { $("t-" + x).className = x === t ? "chosen" : ""; }); };
  TYPES.forEach((t) => { $("t-" + t).onclick = () => setType(t); });
  $("fix-a").onclick = () => { input.value = subject.a_text; check(); };
  $("fix-b").onclick = () => { input.value = subject.b_text; check(); };
  input.oninput = check;
  const close = () => { box.hidden = true; box.innerHTML = ""; modalKeys = null; };
  const save = async () => { if (!check()) return; close(); await decide(`FIX:${type}:${input.value}`, true); };
  $("fix-ok").onclick = save;
  $("fix-cancel").onclick = close;
  if ($("fix-split")) $("fix-split").onclick = async () => { close(); await enterSplit(); };
  modalKeys = (e) => {
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Enter") { e.preventDefault(); save(); }
    else if (document.activeElement !== input) {
      const t = {p: "PERSON", l: "LOCATION", o: "ORG"}[e.key.toLowerCase()];
      if (t) { e.preventDefault(); setType(t); }
    }
  };
  check();
  input.focus();
  input.select();
}

// ---- spot-check --------------------------------------------------------

function verdicts(doc) {
  // span id -> {kind, value}; plus the MISSING list
  const v = {}, missing = [];
  doc.corrections.forEach((c) => {
    const [kind, ...rest] = c.code.split(":");
    if (kind === "MISSING") missing.push(c.code);
    else if (kind === "REMOVE") v[rest[0]] = {kind, value: ""};
    else if (kind === "RETYPE") v[rest[0]] = {kind, value: rest[1]};
    else if (kind === "BOUNDARY") v[rest[0]] = {kind, value: rest.slice(1).join(":")};
  });
  return {v, missing};
}

function corrections(doc, v, missing) {
  const out = [];
  doc.spans.forEach((s) => {
    const x = v[s.id];
    if (!x) return;
    if (x.kind === "REMOVE") out.push({code: `REMOVE:${s.id}`, note: ""});
    if (x.kind === "RETYPE") out.push({code: `RETYPE:${s.id}:${x.value}`, note: ""});
    if (x.kind === "BOUNDARY") out.push({code: `BOUNDARY:${s.id}:${x.value}`, note: ""});
  });
  missing.forEach((m) => out.push({code: m, note: ""}));
  return out;
}

async function saveSpot(v, missing, finished) {
  const doc = S.spot[sdoc];
  const r = await api("/api/spotcheck", {doc: doc.doc, corrections: corrections(doc, v, missing), finished});
  if (!r.ok) { status("refused: " + refusal(r.data), true); return false; }
  S.spot[sdoc] = r.data.doc;
  S.progress = r.data.progress;
  showProgress();
  status(finished ? `${doc.doc} finished` : "saved");
  return true;
}

function renderSpot() {
  if (!S.spot.length) { $("main").innerHTML = '<div class="card">No spot-check document.</div>'; return; }
  const doc = S.spot[sdoc];
  sspan = Math.min(sspan, Math.max(0, doc.spans.length - 1));
  const {v, missing} = verdicts(doc);
  const cur = doc.spans[sspan];
  // document pane with every agreed span marked
  let pos = 0, body = "";
  doc.spans.forEach((s, k) => {
    if (s.start < pos) return; // nested or crossing spans: listed on the right only
    const x = v[s.id];
    const cls = "g" + (k === sspan ? " cur" : "") + (x && x.kind === "REMOVE" ? " r" : "");
    body += esc(doc.text.slice(pos, s.start)) + `<mark class="${cls}" id="span-${k}">${esc(doc.text.slice(s.start, s.end))}</mark>`;
    pos = s.end;
  });
  body += esc(doc.text.slice(pos));
  let h = '<div class="card"><div class="head">' +
    S.spot.map((d, k) => btn("doc-" + k, `${esc(d.doc)}${d.finished ? " ✓" : ""}`, k === sdoc ? "current" : "", {chosen: k === sdoc})).join("") +
    '<span class="spacer"></span><span class="small">Look for mistakes both annotators made.</span></div></div>';
  h += `<div class="spotgrid"><div><div class="doctext" id="doctext">${body}</div>` +
    `<div class="buttons">${btn("m-add", "Add MISSING from selection", "M")}</div></div><div class="card">`;
  if (cur) {
    const x = v[cur.id];
    h += `<div class="head"><span class="gid">${esc(cur.id)}</span><span class="pill">${esc(cur.type)}</span><span class="small">span ${sspan + 1} of ${doc.spans.length}</span></div>` +
      `<div class="side ${x && x.kind === "REMOVE" ? "" : "a"}" style="margin-top:10px"><div class="txt">${esc(cur.text)}</div></div>` +
      `<p>verdict: <b>${x ? esc(x.kind + (x.value ? " " + x.value : "")) : "OK"}</b></p>` +
      '<div class="buttons">' + btn("v-ok", "OK, next", "Enter or →") + btn("v-r", "Remove", "R", {chosen: x && x.kind === "REMOVE"}) +
      btn("v-t", "Retype…", "T", {chosen: x && x.kind === "RETYPE"}) + btn("v-x", "Boundary…", "X", {chosen: x && x.kind === "BOUNDARY"}) +
      btn("v-clear", "Clear", "Backspace", {disabled: !x}) + btn("v-prev", "← Previous", "←") + "</div>";
  } else h += "<p>No agreed span in this document.</p>";
  h += `<h4>MISSING (${missing.length})</h4><ul class="list">` + missing.map((m, k) => `<li>${esc(m)} <button id="miss-${k}">remove</button></li>`).join("") + "</ul>";
  h += `<div class="buttons">${btn("v-done", doc.finished ? "Finished ✓ (save again)" : "Finish this document", "D")}</div>` +
    '<p class="small">A document counts only when you press Finish. No finding: just Finish, it writes NONE.</p></div></div>';
  $("main").innerHTML = h;
  S.spot.forEach((d, k) => { $("doc-" + k).onclick = () => { sdoc = k; sspan = 0; render(); }; });
  const el = $("span-" + sspan);
  if (el) el.scrollIntoView({block: "center"});
  const on = (id, f) => { const b = $(id); if (b) b.onclick = f; };
  on("v-ok", spotNext);
  on("v-r", () => setVerdict({kind: "REMOVE", value: ""}));
  on("v-t", openRetype);
  on("v-x", openBoundary);
  on("v-clear", () => setVerdict(null));
  on("v-prev", () => { sspan = Math.max(0, sspan - 1); render(); });
  on("v-done", finishDoc);
  on("m-add", addMissing);
  missing.forEach((m, k) => on("miss-" + k, async () => { const x = verdicts(doc); x.missing.splice(k, 1); await saveSpot(x.v, x.missing, doc.finished); render(); }));
}

function spotNext() {
  const doc = S.spot[sdoc];
  if (sspan < doc.spans.length - 1) { sspan += 1; render(); }
  else status("last span: press Finish (D) when this document is done");
}

async function setVerdict(x) {
  const doc = S.spot[sdoc];
  const cur = doc.spans[sspan];
  if (!cur) return;
  const st = verdicts(doc);
  if (x) st.v[cur.id] = x; else delete st.v[cur.id];
  if (await saveSpot(st.v, st.missing, doc.finished) && x) spotNext(); else render();
}

function typeDialog(title, onPick) {
  const box = $("modal");
  box.innerHTML = `<div class="box"><h3>${esc(title)}</h3><div class="buttons">${TYPES.map((t, k) => btn("t-" + t, t, ["P", "L", "O"][k])).join("")}${btn("t-cancel", "Cancel", "Esc")}</div></div>`;
  box.hidden = false;
  const close = () => { box.hidden = true; box.innerHTML = ""; modalKeys = null; };
  TYPES.forEach((t) => { $("t-" + t).onclick = () => { close(); onPick(t); }; });
  $("t-cancel").onclick = close;
  modalKeys = (e) => {
    const t = {p: "PERSON", l: "LOCATION", o: "ORG"}[e.key.toLowerCase()];
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (t) { e.preventDefault(); close(); onPick(t); }
  };
}

function openRetype() {
  const cur = S.spot[sdoc].spans[sspan];
  if (cur) typeDialog(`Retype ${cur.id} to:`, (t) => setVerdict({kind: "RETYPE", value: t}));
}

function textDialog(title, value, onSave) {
  const box = $("modal");
  box.innerHTML = `<div class="box"><h3>${esc(title)}</h3><input type="text" id="dlg-text"><div class="buttons">${btn("dlg-ok", "Save", "Enter")}${btn("dlg-cancel", "Cancel", "Esc")}</div></div>`;
  box.hidden = false;
  const input = $("dlg-text");
  input.value = value;
  const close = () => { box.hidden = true; box.innerHTML = ""; modalKeys = null; };
  const save = () => { const v = input.value; if (!v) return; close(); onSave(v); };
  $("dlg-ok").onclick = save;
  $("dlg-cancel").onclick = close;
  modalKeys = (e) => {
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Enter") { e.preventDefault(); save(); }
  };
  input.focus();
  input.select();
}

function openBoundary() {
  const cur = S.spot[sdoc].spans[sspan];
  if (cur) textDialog(`Right extent for ${cur.id} (exact text, overlapping it):`, cur.text, (t) => setVerdict({kind: "BOUNDARY", value: t}));
}

function addMissing() {
  const sel = window.getSelection();
  const text = sel ? sel.toString() : "";
  const doc = S.spot[sdoc];
  if (!text.trim() || !$("doctext").contains(sel.anchorNode)) { status("select the missing text in the document first", true); return; }
  if (doc.text.indexOf(text) < 0) { status("the selection must be plain document text", true); return; }
  typeDialog("MISSING: type of the selected text", async (t) => {
    const st = verdicts(doc);
    const code = `MISSING:${t}:${text}`;
    if (!st.missing.includes(code)) st.missing.push(code);
    await saveSpot(st.v, st.missing, doc.finished);
    render();
  });
}

async function finishDoc() {
  const doc = S.spot[sdoc];
  const st = verdicts(doc);
  if (await saveSpot(st.v, st.missing, true)) {
    const next = S.spot.findIndex((d) => !d.finished);
    if (next >= 0) { sdoc = next; sspan = 0; }
  }
  render();
}

// ---- guidelines, tabs, keys --------------------------------------------

async function toggleGuide() {
  const g = $("guide");
  if (g.hidden && !g.dataset.loaded) {
    const r = await fetch("/api/guidelines");
    g.innerHTML = r.ok ? await r.text() : "<p>could not load the guidelines</p>";
    g.dataset.loaded = "1";
  }
  g.hidden = !g.hidden;
}

$("btn-guide").onclick = toggleGuide;
$("tab-dis").onclick = () => { mode = "dis"; render(); };
$("tab-spot").onclick = () => { mode = "spot"; render(); };

document.addEventListener("keydown", (e) => {
  if (!S) return;
  if (modalKeys) { modalKeys(e); return; }
  const typing = document.activeElement && ["TEXTAREA", "INPUT"].includes(document.activeElement.tagName);
  if (typing) { if (e.key === "Escape") document.activeElement.blur(); return; }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key;
  if (k === "g" || k === "G") { e.preventDefault(); toggleGuide(); return; }
  if (mode === "spot") {
    const map = {Enter: spotNext, ArrowRight: spotNext, ArrowLeft: () => { sspan = Math.max(0, sspan - 1); render(); },
      r: () => setVerdict({kind: "REMOVE", value: ""}), t: openRetype, x: openBoundary, m: addMissing,
      d: finishDoc, Backspace: () => setVerdict(null)};
    const f = map[k] || map[k.toLowerCase()];
    if (f) { e.preventDefault(); f(); }
    return;
  }
  const g = S.groups[gi];
  const subject = mode === "split" ? g.occurrences[oi] : g;
  const av = availability(subject);
  const guarded = (code) => { if (av[code]) status(av[code], true); else decide(code, true); };
  const map = {
    ArrowLeft: () => (mode === "split" ? (oi = Math.max(0, oi - 1), render()) : go(-1)),
    ArrowRight: () => (mode === "split" ? (oi = Math.min(g.occurrences.length - 1, oi + 1), render()) : go(1)),
    a: () => guarded("A"), "1": () => guarded("A"),
    b: () => guarded("B"), "2": () => guarded("B"),
    "3": () => guarded("BOTH"),
    n: () => decide("NONE", true), "0": () => decide("NONE", true),
    f: openFix,
    "?": () => decide("?", false),
    Backspace: () => decide("", false),
    Tab: () => $("note").focus(),
    Escape: () => (mode === "split" ? leaveSplit() : null),
  };
  if (mode === "dis") { map.s = enterSplit; map.u = nextUndecided; }
  const f = map[k] || map[k.toLowerCase()];
  if (f) { e.preventDefault(); f(); }
});

load();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="final_exam_adjudication")
    sub = parser.add_subparsers(dest="command", required=True)
    conv = sub.add_parser("convert")
    conv.add_argument("--docs", required=True, type=Path)
    conv.add_argument("--raw", required=True, type=Path)
    conv.add_argument("--out", required=True, type=Path)
    conv.add_argument("--flags", required=True, type=Path)
    conv.add_argument("ids", nargs="*")
    agr = sub.add_parser("agreement")
    agr.add_argument("--a", required=True, type=Path)
    agr.add_argument("--b", required=True, type=Path)
    for name in ("view", "merge", "report"):
        sp = sub.add_parser(name)
        sp.add_argument("--workspace", required=True, type=Path)
        if name == "view":
            sp.add_argument(
                "--force",
                action="store_true",
                help="overwrite decisions.tsv, occurrences.tsv and spotcheck.tsv",
            )
        else:
            sp.add_argument(
                "--g5-keep-longer",
                action="store_true",
                help="G5: keep the longer of nested same-type spans (Lionel, 2026-10-12)",
            )
    srv = sub.add_parser("serve")
    srv.add_argument("--workspace", required=True, type=Path)
    srv.add_argument("--port", type=int, default=DEFAULT_PORT)
    srv.add_argument("--open", action="store_true", help="open the default browser")
    srv.add_argument("--guidelines", type=Path, default=GUIDELINES_PATH)
    grd = sub.add_parser("guard-report")
    grd.add_argument("--workspace", required=True, type=Path)
    grd.add_argument(
        "--annotations",
        type=Path,
        default=REPO_ROOT / "tests" / "test_corpus" / "final_exam" / "annotations",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "convert":
            return cmd_convert(args.docs, args.raw, args.out, args.flags, args.ids)
        if args.command == "agreement":
            return cmd_agreement(args.a, args.b)
        if args.command == "view":
            return cmd_view(args.workspace, args.force)
        if args.command == "merge":
            return cmd_merge(args.workspace, args.g5_keep_longer)
        if args.command == "report":
            return cmd_report(args.workspace, args.g5_keep_longer)
        if args.command == "serve":
            return cmd_serve(args.workspace, args.port, args.open, args.guidelines)
        if args.command == "guard-report":
            return cmd_guard_report(args.workspace, args.annotations)
        raise ValueError("unknown command")
    except AnonymousError as exc:
        # an anonymous id or a file name and line, never the message (ADJ-003)
        print(f"ERROR {exc.where} {type(exc).__name__}")
        return 1
    except Exception as exc:  # noqa: BLE001 - class only (Error Output)
        print(f"ERROR - {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
