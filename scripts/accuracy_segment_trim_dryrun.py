"""Dry-run of the candidate "segment trim" fix (not adopted; Lionel decides).

Story 10.2, Lionel's HOLD (2026-10-04). Main corpus only: uses the baseline
detection dump and ``_load_corpus_documents()``; never held-out data. Local
attribution counts, story only (Product Constraint 6).

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_segment_trim_dryrun.py <baseline_dump.json>
"""

import collections
import dataclasses
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import accuracy_size_findings as m

from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

ORIG = (
    HybridDetector._resolve_same_type_pair_base.__func__
)  # without V3 (V3 is in the product since 10.2)
TITLES = {"mme", "mlle", "prof", "dr", "pr", "me", "m"}
BOUND = re.compile(r"\n|[,;:](?=\s)|\.(?=\s+\S)")


def boundaries(raw):
    """Boundary (start, end) offsets: line break, , ; : before space, sentence period."""
    out = []
    for mt in BOUND.finditer(raw):
        if mt.group() == ".":
            word = re.search(r"([A-Za-zÀ-ÿ]+)$", raw[: mt.start()])
            w = word.group(1) if word else ""
            if len(w) < 3 or w.lower() in TITLES or w.isupper():
                continue
        out.append((mt.start(), mt.end()))
    return out


def segment(cls, ent, anchor, text):
    """Sub-span of ent between the clause boundaries around anchor (core), or None."""
    raw = cls._slice(ent, text)
    a0, a1 = anchor[0] - ent.start_pos, anchor[1] - ent.start_pos
    bs = boundaries(raw)
    left = max([e for s, e in bs if e <= a0], default=0)
    right = min([s for s, e in bs if s >= a1], default=len(raw))
    if any(s < a1 and e > a0 for s, e in bs):
        return None  # anchor itself crosses a boundary
    seg = raw[left:right]
    lstrip = len(seg) - len(seg.lstrip())
    seg = seg.strip()
    if not seg or (left == 0 and right == len(raw)):
        return None
    start = ent.start_pos + left + lstrip
    return dataclasses.replace(ent, text=seg, start_pos=start, end_pos=start + len(seg))


def make(types, union_too):
    def resolve(cls, a, b, text=None):
        res, reason = ORIG(cls, a, b, text)
        if a.entity_type not in types:
            return res, reason
        if reason in ("containment", "containment_outer_trimmed_linebreak"):
            ca, cb = cls._dedup_core(a), cls._dedup_core(b)
            outer, inner = (a, b) if (ca[0] <= cb[0] and cb[1] <= ca[1]) else (b, a)
            seg = segment(cls, outer, cls._dedup_core(inner), text)
            if seg is not None:
                sc, ic = cls._dedup_core(seg), cls._dedup_core(inner)
                if sc[0] <= ic[0] and ic[1] <= sc[1]:
                    return seg, "containment_outer_trimmed_boundary"
        if union_too and reason == "partial_overlap_union":
            ca, cb = cls._dedup_core(a), cls._dedup_core(b)
            anchor = (max(ca[0], cb[0]), min(ca[1], cb[1]))
            seg = segment(cls, res, anchor, text)
            if seg is not None:
                return seg, "partial_overlap_union_trimmed"
        return res, reason

    return classmethod(resolve)


if __name__ == "__main__":
    docs = m.load(Path(sys.argv[1]))
    base = m.score((gt, d) for _, _, gt, d in docs)
    base_dets = {n: d for n, _, _, d in docs}

    def run(label, patch):
        HybridDetector._resolve_same_type_pair = patch
        det = HybridDetector()
        out = []
        for name, text, gt, dets in docs:
            out.append(
                (
                    name,
                    text,
                    gt,
                    det._dedup_same_type_overlaps(
                        det._filter_org_roles(list(dets), text), text
                    ),
                )
            )
        r = m.score((gt, k) for _, _, gt, k in out)
        return r, out

    run_c, out_c = run("run C", classmethod(ORIG))

    def report(label, r, out):
        print(f"\n### {label}")
        for t in ("Overall", "PERSON", "LOCATION", "ORG"):
            print(
                f"  [{t}] TP={r[t][0]} FP={r[t][1]} FN={r[t][2]} | vs baseline FN {r[t][2]-base[t][2]:+d} FP {r[t][1]-base[t][1]:+d} | vs run C FN {r[t][2]-run_c[t][2]:+d} FP {r[t][1]-run_c[t][1]:+d} | {m.prf(*r[t])}"
            )
        cov = collections.Counter()
        lost = []
        for name, text, gt, kept in out:
            _, _, fn0 = m.match_entities(base_dets[name], gt)
            fn0 = {id(g) for g in fn0}
            _, _, fn1 = m.match_entities(kept, gt)
            for g in fn1:
                if id(g) in fn0:
                    continue
                same = any(
                    k.entity_type == g.entity_type
                    and k.start_pos <= g.start_pos
                    and g.end_pos <= k.end_pos
                    for k in kept
                )
                anyt = any(
                    k.start_pos <= g.start_pos and g.end_pos <= k.end_pos for k in kept
                )
                cov[
                    (
                        g.entity_type,
                        (
                            "still covered same type"
                            if same
                            else "other type only" if anyt else "UNCOVERED"
                        ),
                    )
                ] += 1
            for g in gt:
                was = any(
                    d.start_pos <= g.start_pos and g.end_pos <= d.end_pos
                    for d in base_dets[name]
                )
                now = any(
                    k.start_pos <= g.start_pos and g.end_pos <= k.end_pos for k in kept
                )
                if was and not now:
                    lost.append(f"{g.entity_type} {g.text!r} @{g.start_pos} {name}")
        print("  new-miss coverage:", dict(sorted(cov.items())))
        print(f"  annotations covered in baseline, not after: {len(lost)}")
        for line in lost:
            print("    ", line)

    report("run C (current code)", run_c, out_c)
    for label, types, u in [
        ("V1 segment trim, ORG only", {"ORG"}, False),
        ("V2 segment trim, all types", {"ORG", "PERSON", "LOCATION"}, False),
        ("V3 segment trim + union trim, ORG only", {"ORG"}, True),
        (
            "V4 segment trim + union trim, all types",
            {"ORG", "PERSON", "LOCATION"},
            True,
        ),
    ]:
        r, out = run(label, make(types, u))
        report(label, r, out)
    HybridDetector._resolve_same_type_pair = classmethod(ORIG)
