"""Attribute every new miss of one type (baseline -> current code) to the rule that caused it.

Story 10.2, Lionel's HOLD (2026-10-04). Main corpus only: uses the baseline
detection dump and ``_load_corpus_documents()``; never held-out data. Local
attribution counts, story only (Product Constraint 6).

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_org_loss_attribution.py <baseline_dump.json> [TYPE] [V3]
"""

import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import accuracy_size_findings as m

from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

TYPE = sys.argv[2] if len(sys.argv) > 2 else "ORG"
if len(sys.argv) > 3 and sys.argv[3] == "V3":
    import accuracy_segment_trim_dryrun as segment_fix

    HybridDetector._resolve_same_type_pair = segment_fix.make({"ORG"}, True)
docs = m.load(Path(sys.argv[1]))
events = []
orig_log = HybridDetector._log_dedup


def rec(kept, dropped, reason):
    events.append((kept, dropped, reason))


HybridDetector._log_dedup = staticmethod(rec)
det = HybridDetector()
rows = []
for name, text, gt, dets in docs:
    tp0, _, fn0 = m.match_entities(dets, gt)
    base_match = {id(g): d for d, g in tp0}
    events.clear()
    roles = det._filter_org_roles(list(dets), text)
    role_dropped = [d for d in dets if d.entity_type == "ORG" and d not in roles]
    out = det._dedup_same_type_overlaps(list(roles), text)
    dev = list(events)
    tp1, _, fn1 = m.match_entities(out, gt)
    fn0i = {id(g) for g in fn0}
    for g in fn1:
        if g.entity_type != TYPE or id(g) in fn0i:
            continue
        d = base_match[id(g)]
        if any(d is r for r in role_dropped):
            rule, winner = "role filter", "-"
        else:
            # follow d through dedup events to its final fate
            cur, rule, winner = d, None, None
            seen = 0
            while seen < 20:
                seen += 1
                ev = [e for e in dev if e[1] is cur]
                if not ev:
                    break
                kept, _, reason = ev[0]
                rule = rule or reason
                winner = kept
                if any(kept is o for o in out):
                    break
                cur = kept
            if rule is None:
                rule = "kept (scorer re-pairing)"
                winner = d
        still_same = any(
            k.entity_type == g.entity_type
            and k.start_pos <= g.start_pos
            and g.end_pos <= k.end_pos
            for k in out
        )
        still_any = any(
            k.start_pos <= g.start_pos and g.end_pos <= k.end_pos for k in out
        )
        cov = (
            "same-type" if still_same else ("other type" if still_any else "UNCOVERED")
        )
        wtxt = (
            winner
            if isinstance(winner, str)
            else repr(winner.text) + f" [{winner.source}]"
        )
        rows.append(
            (
                rule,
                name,
                g.text,
                g.start_pos,
                wtxt,
                cov,
                repr(d.text) + f" [{d.source}]",
            )
        )
for r in sorted(rows):
    print(
        f"{r[0]:38s} | {r[1]:24s} | {r[2]!r} @{r[3]} | baseline TP det {r[6]} | won: {r[4]} | covered: {r[5]}"
    )
print("COUNT", collections.Counter(r[0] for r in rows), "total", len(rows))
