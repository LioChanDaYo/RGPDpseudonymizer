"""Final-exam annotation tooling (Story 10.6 PR B, B3.1).

Sub-commands (Dev Notes "PR B Design")::

    convert --docs <dir> --raw <dir> --out <dir> --flags <file> [<id>...]
    agreement --a <dir> --b <dir>
    view --workspace <dir>
    merge --workspace <dir>
    report --workspace <dir>
    guard-report --workspace <dir> --annotations <dir>

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
import random
import re
import sys
from dataclasses import dataclass
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


def apply_decision(text: str, d: Disagreement, code: str) -> list[Span]:
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


def merge_workspace(
    workspace: Path,
) -> tuple[dict[str, list[Span]], dict[str, int], dict[str, int], int]:
    """Adjudicated spans per document, decision counts (per disagreement),
    spot-check counts and MISSING occurrences added."""
    ids = doc_ids(workspace)
    halves = load_manifest(workspace)
    groups, _ = build_groups(workspace)
    decisions = read_decisions(workspace, groups)
    gid_of = {d.did: g.gid for g in groups for d in g.members}
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
    result: dict[str, list[Span]] = {}
    for doc_id in ids:
        text, agreed, disagreements = doc_state(workspace, doc_id)
        spans = list(agreed)
        for d in disagreements:
            code = decisions[d.did]
            try:
                spans += apply_decision(text, d, code)
            except DecisionError as exc:
                raise DecisionError(
                    "decision refused", f"{gid_of[d.did]}/{d.did}"
                ) from exc
            key = code.split(":", 1)[0]
            code_counts[key] = code_counts.get(key, 0) + 1
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
        result[doc_id] = sorted(unique.values(), key=Span.sort_key)
    return result, code_counts, spot_counts, missing_added


def cmd_merge(workspace: Path) -> int:
    result, code_counts, spot_counts, missing_added = merge_workspace(workspace)
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
    return 0


def cmd_report(workspace: Path) -> int:
    for line in agreement_lines(workspace / "ann_a", workspace / "ann_b"):
        print(line)
    _, code_counts, spot_counts, missing_added = merge_workspace(workspace)
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
            return cmd_merge(args.workspace)
        if args.command == "report":
            return cmd_report(args.workspace)
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
