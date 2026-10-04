"""Re-measure findings F1/F2 and dry-run the Story 10.2 rules on a dump.

Story 10.2, Tasks 1.3-1.5 (adapted from the out-of-repo ``size.py``).
Pure Python over a detection dump written by
``scripts/accuracy_dump_detections.py``: no spaCy model is loaded.
Main corpus only (``_load_corpus_documents()``; never the held-out loader).
Imports ``tests.accuracy.conftest`` read-only (G4 scope).

The counts printed here are local attribution numbers (Product Constraint 6):
they belong in the story's "Re-measured Sizes" table only, never in the QA
report, CHANGELOG or PR body.

The role list and the overlap rule below are the Task 2 frozen text. The
product code (Tasks 3 and 6) implements the same text from the story.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_size_findings.py <dump.json> [--examples N]
"""

from __future__ import annotations

import collections
import io
import json
import logging
import re
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import structlog  # noqa: E402

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity  # noqa: E402
from gdpr_pseudonymizer.resources import FRENCH_GEOGRAPHY_PATH  # noqa: E402
from gdpr_pseudonymizer.utils.french_patterns import (  # noqa: E402
    strip_french_prepositions,
    strip_french_titles,
)
from tests.accuracy.conftest import (  # noqa: E402
    GroundTruthEntity,
    _load_corpus_documents,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")
Doc = tuple[str, str, list[GroundTruthEntity], list[DetectedEntity]]

# ---------------------------------------------------------------------------
# AC3 role list (Task 2.2 frozen list; mirrored in the story Dev Notes)
# ---------------------------------------------------------------------------

ACRONYMS = [
    # English C-suite titles
    "CEO",
    "CTO",
    "CFO",
    "COO",
    "CIO",
    "CDO",
    "CSO",
    "CISO",
    "CMO",
    "CPO",
    "CHRO",
    # French role acronyms
    "DSI",
    "DAF",
    "DRH",
    "DPO",
    "RSSI",
    "PDG",
    "DGA",
    # internal governance bodies
    "COMEX",
    "CODIR",
]
VP_PREFIXES = [
    "VP",
    "Vice-président",
    "Vice-présidente",
    "Vice President",
    "Vice-President",
]
VP_FUNCTIONS = [
    "Engineering",
    "Sales",
    "Marketing",
    "Finance",
    "Operations",
    "Product",
    "Products",
    "Technology",
    "Tech",
    "Legal",
    "HR",
    "People",
    "Strategy",
    "Business",
    "Development",
    "Communications",
    "Procurement",
    "Purchasing",
    "Research",
    "R&D",
    "Data",
    "IT",
    "Digital",
    "Innovation",
    "Security",
    "Compliance",
    "Risk",
    "Audit",
    "Quality",
    "Customer",
    "Success",
    "Partnerships",
    "Supply",
    "Chain",
    "Logistics",
    "Manufacturing",
    "Ventes",
    "Ingénierie",
    "Produit",
    "Produits",
    "Opérations",
    "RH",
    "Communication",
    "Juridique",
    "Achats",
    "Technique",
    "Technologie",
    "Commercial",
    "Commerciale",
    "Stratégie",
    "Développement",
    "Recherche",
    "Informatique",
    "Numérique",
    "Sécurité",
    "Conformité",
    "Risques",
    "Qualité",
    "Partenariats",
    "Logistique",
    "Production",
    "Clients",
    "Ressources",
    "Humaines",
    "Financier",
    "Financière",
    "Affaires",
    "Publiques",
    "Public",
    "Affairs",
    "Relations",
    "Investisseurs",
    "Investor",
]
VP_REGIONS = [
    "Europe",
    "Afrique",
    "Africa",
    "Asie",
    "Asia",
    "Amérique",
    "Amériques",
    "Americas",
    "Océanie",
    "Oceania",
    "International",
    "Monde",
    "Global",
    "Worldwide",
    "Nord",
    "North",
    "Sud",
    "South",
    "Est",
    "East",
    "Ouest",
    "West",
    "France",
]
CONNECTORS = ["de", "du", "des", "d'", "et", "&", "/"]


def _geo_region_words() -> list[str]:
    data = json.loads(FRENCH_GEOGRAPHY_PATH.read_text(encoding="utf-8"))
    return list(data["countries_and_international"]) + list(data["regions"])


def _tokens(text: str) -> list[str]:
    """Whitespace tokens, with "/" and the elision "d'" split off.

    "&" is a connector only as a standalone token ("Sales & Marketing");
    inside a word ("R&D") it stays part of the word.
    """
    text = text.replace("/", " / ")
    text = re.sub(r"(?i)\b(d')", r"\1 ", text)
    return text.split()


class RoleMatcher:
    def __init__(self) -> None:
        self.acronyms = set(ACRONYMS)
        self.functions = {w.casefold() for w in VP_FUNCTIONS}
        self.connectors = {w.casefold() for w in CONNECTORS}
        regions = VP_REGIONS + _geo_region_words()
        self.region_phrases = sorted(
            {tuple(t.casefold() for t in _tokens(r)) for r in regions},
            key=len,
            reverse=True,
        )

    def _prefix_rest(self, t: str) -> str | None:
        for p in VP_PREFIXES:
            if p == "VP":
                if t == "VP":
                    return ""
                if t.startswith("VP "):
                    return t[3:]
            else:
                if t.casefold() == p.casefold():
                    return ""
                if t.casefold().startswith(p.casefold() + " "):
                    return t[len(p) + 1 :]
        return None

    def match(self, text: str) -> str | None:
        """Return 'role_acronym', 'vp_bare', 'vp_function', 'vp_region' or None."""
        t = " ".join(strip_french_titles(text).split())
        if t in self.acronyms:
            return "role_acronym"
        rest = self._prefix_rest(t)
        if rest is None:
            return None
        if rest == "":
            return "vp_bare"
        toks = [x.casefold() for x in _tokens(rest)]
        i = 0
        has_func = has_region = False
        while i < len(toks):
            for phrase in self.region_phrases:
                if tuple(toks[i : i + len(phrase)]) == phrase:
                    has_region = True
                    i += len(phrase)
                    break
            else:
                if toks[i] in self.functions:
                    has_func = True
                elif toks[i] not in self.connectors:
                    return None
                i += 1
        if has_region:
            return "vp_region"
        if has_func:
            return "vp_function"
        return None


# ---------------------------------------------------------------------------
# AC1 same-type overlap rule (Task 2.1 frozen text)
# ---------------------------------------------------------------------------


def norm(e: DetectedEntity) -> str:
    t = strip_french_titles(e.text)
    if e.entity_type == "LOCATION":
        t = strip_french_prepositions(t)
    return t


def key(e: DetectedEntity) -> str:
    return " ".join(norm(e).lower().split())


def core(e: DetectedEntity) -> tuple[int, int]:
    n = norm(e)
    i = e.text.find(n) if n else -1
    if i >= 0:
        return (e.start_pos + i, e.start_pos + i + len(n))
    return (e.start_pos, e.end_pos)


def raw_overlap(a: DetectedEntity, b: DetectedEntity) -> bool:
    return a.start_pos < b.end_pos and b.start_pos < a.end_pos


def _contains(o: tuple[int, int], i: tuple[int, int]) -> bool:
    return o[0] <= i[0] and i[1] <= o[1]


def added_tokens(outer: DetectedEntity, inner: DetectedEntity) -> list[str]:
    """Whitespace tokens of the outer core lying outside the inner core."""
    oc, ic = core(outer), core(inner)
    off = outer.start_pos
    left = outer.text[oc[0] - off : ic[0] - off]
    right = outer.text[ic[1] - off : oc[1] - off]
    return left.split() + right.split()


def c1_inner_wins(outer: DetectedEntity, inner: DetectedEntity) -> bool:
    toks = added_tokens(outer, inner)
    return bool(toks) and all(
        not any(ch.isupper() or ch.isdigit() for ch in tok) for tok in toks
    )


def relation(a: DetectedEntity, b: DetectedEntity) -> str:
    ca, cb = core(a), core(b)
    if ca == cb or key(a) == key(b):
        return "equal"
    if not (ca[0] < cb[1] and cb[0] < ca[1]):
        return "cores_disjoint"
    if _contains(ca, cb) or _contains(cb, ca):
        return "containment"
    return "partial"


def c2_inner_wins(outer: DetectedEntity, inner: DetectedEntity) -> bool:
    """Candidate C2 (Task 1.7): the outer core adds a line break to the inner."""
    oc, ic = core(outer), core(inner)
    off = outer.start_pos
    added = (
        outer.text[oc[0] - off : ic[0] - off] + outer.text[ic[1] - off : oc[1] - off]
    )
    return "\n" in added


# Variants dry-run in Task 1.5/1.7. "default" is the epic rule.
VARIANTS = {
    "default": (),
    "default + C1": ("C1",),
    "default + C2": ("C2",),
    "default + C1 + C2": ("C1", "C2"),
    "equal-only (no containment/partial drops)": ("EQ",),
}


def decide(
    a: DetectedEntity, b: DetectedEntity, mode: tuple[str, ...] = ()
) -> tuple[DetectedEntity | None, str]:
    """Pairwise decision. ``a`` precedes ``b`` in the walk order.

    Returns (winner, reason); winner None means both are kept.
    """
    rel = relation(a, b)
    if rel == "cores_disjoint":
        return None, "cores_disjoint"
    if "EQ" in mode and rel != "equal":
        return None, "kept_both"
    if rel == "containment":
        outer, inner = (a, b) if _contains(core(a), core(b)) else (b, a)
        if "C1" in mode and c1_inner_wins(outer, inner):
            return inner, "containment_inner_preferred"
        if "C2" in mode and c2_inner_wins(outer, inner):
            return inner, "containment_inner_preferred_linebreak"
        return outer, "containment"
    if rel == "partial":
        if a.source != b.source:
            return (a if a.source == "spacy" else b), "partial_overlap_spacy_preferred"
        la, lb = core(a)[1] - core(a)[0], core(b)[1] - core(b)[0]
        if la != lb:
            return (a if la > lb else b), "partial_overlap_longer"
    # tie (equal, or same-source partial with equal core length)
    if a.source != b.source:
        return (a if a.source == "spacy" else b), "tie"
    ra, rb = a.end_pos - a.start_pos, b.end_pos - b.start_pos
    if ra != rb:
        return (a if ra > rb else b), "tie"
    if a.start_pos != b.start_pos:
        return (a if a.start_pos < b.start_pos else b), "tie"
    return a, "tie"


Drop = tuple[DetectedEntity, DetectedEntity, str]  # (kept, dropped, reason)


def dedup(
    ents: list[DetectedEntity], mode: tuple[str, ...] = ()
) -> tuple[list[DetectedEntity], list[Drop]]:
    order = sorted(ents, key=lambda e: (e.start_pos, -e.end_pos, e.source != "spacy"))
    kept: list[DetectedEntity] = []
    drops: list[Drop] = []
    for x in order:
        rivals = [
            k
            for k in kept
            if k.entity_type == x.entity_type
            and raw_overlap(k, x)
            and decide(k, x, mode)[0] is not None
        ]
        lost_to = None
        for k in rivals:
            w, reason = decide(k, x, mode)
            if w is k:
                lost_to = (k, reason)
                break
        if lost_to is not None:
            drops.append((lost_to[0], x, lost_to[1]))
            continue
        for k in rivals:
            _, reason = decide(k, x, mode)
            kept.remove(k)
            drops.append((x, k, reason))
        kept.append(x)
    kept.sort(key=lambda e: e.start_pos)
    return kept, drops


def loss_pattern(outer: DetectedEntity, inner: DetectedEntity, toks: list[str]) -> str:
    """Containment-loss pattern (Task 1.5 (i)-(iv); "other" sub-classified)."""
    off = outer.start_pos
    oc, ic = core(outer), core(inner)
    left = outer.text[oc[0] - off : ic[0] - off]
    right = outer.text[ic[1] - off : oc[1] - off]
    if inner.entity_type == "LOCATION" and re.match(
        r"^\s*(dans|près de|ville de)\s", outer.text, re.IGNORECASE
    ):
        return "(i) unstripped prefix"
    if (
        inner.entity_type == "LOCATION"
        and toks
        and all(re.fullmatch(r"\d+(?:e|er|ème|eme)?", t) for t in toks)
    ):
        return "(ii) arrondissement (A6)"
    if (
        inner.entity_type == "PERSON"
        and re.match(r"^\s*,\s*\S", right)
        and "\n" not in right
    ):
        return "(iii) trailing ', Role' (10.3)"
    if "\n" in left + right:
        return "(iv-a) other: outer span runs across a line break"
    if re.match(r"^\s*(?:-|\)|:|\):)", right) or (
        inner.entity_type == "PERSON" and right.strip() and not left.strip()
    ):
        return "(iv-b) other: outer adds a trailing role/label word on the same line"
    if inner.entity_type in ("ORG", "PERSON") and (
        len(outer.text) > 40 or re.search(r"[,.] ", outer.text)
    ):
        return "(iv-c) other: run-on outer span (clause/list swallowed)"
    if inner.entity_type == "LOCATION":
        return "(iv-d) other: place inside an org-like name typed LOCATION"
    return "(iv-e) other: leading word added"


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def load(dump_path: Path) -> list[Doc]:
    dump = json.loads(dump_path.read_text(encoding="utf-8"))
    docs: list[Doc] = []
    for name, text, gt in _load_corpus_documents():
        dets = [
            DetectedEntity(
                text=d["text"],
                entity_type=d["type"],
                start_pos=d["start"],
                end_pos=d["end"],
                source=d["source"],
                is_ambiguous=d["is_ambiguous"],
            )
            for d in dump[name]
        ]
        docs.append((name, text, gt, dets))
    return docs


def score(docs: Iterable[tuple[list[GroundTruthEntity], list[DetectedEntity]]]):
    tot = {t: [0, 0, 0] for t in TYPES}
    for gt, dets in docs:
        tp, fp, fn = match_entities(dets, gt)
        for t in TYPES:
            tot[t][0] += sum(1 for d, _ in tp if d.entity_type == t)
            tot[t][1] += sum(1 for d in fp if d.entity_type == t)
            tot[t][2] += sum(1 for g in fn if g.entity_type == t)
    tot["Overall"] = [sum(tot[t][i] for t in TYPES) for i in range(3)]
    return tot


def prf(tp: int, fp: int, fn: int) -> str:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return f"P={p:.4f} R={r:.4f} F1={f:.4f}"


def print_delta(label: str, base, new) -> None:
    print(f"\n### {label}")
    for t in ("Overall",) + TYPES:
        b, n = base[t], new[t]
        print(
            f"  [{t}] TP={n[0]} ({n[0]-b[0]:+d}) FP={n[1]} ({n[1]-b[1]:+d}) "
            f"FN={n[2]} ({n[2]-b[2]:+d})  projected {prf(*n)}"
        )


def ident(e: DetectedEntity) -> tuple[str, str, int, int]:
    return (e.text, e.entity_type, e.start_pos, e.end_pos)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = sys.argv[1:]
    n_ex = 5
    if "--examples" in args:
        i = args.index("--examples")
        n_ex = int(args[i + 1])
        del args[i : i + 2]
    if len(args) != 1:
        sys.exit("usage: accuracy_size_findings.py <dump.json> [--examples N]")
    docs = load(Path(args[0]))
    base = score((gt, d) for _, _, gt, d in docs)
    print("## Baseline (dump re-scored)")
    for t in ("Overall",) + TYPES:
        print(
            f"  [{t}] TP={base[t][0]} FP={base[t][1]} FN={base[t][2]} {prf(*base[t])}"
        )
    print(f"  detections={sum(len(d) for *_, d in docs)}")

    # baseline TP map: detection identity -> annotation
    base_tp: dict[tuple[str, tuple[str, str, int, int]], GroundTruthEntity] = {}
    base_fp: dict[str, list[DetectedEntity]] = {}
    for name, _, gt, dets in docs:
        tp, fp, _ = match_entities(dets, gt)
        for d, g in tp:
            base_tp[(name, ident(d))] = g
        base_fp[name] = fp

    # ---- 1.3 F1 re-measure ------------------------------------------------
    print("\n## 1.3 F1: FP overlapping a same-type TP detection (size.py definition)")
    f1_type: collections.Counter[str] = collections.Counter()
    f1_src: collections.Counter[str] = collections.Counter()
    f1_rel: collections.Counter[str] = collections.Counter()
    f1_log: collections.Counter[str] = collections.Counter()
    for name, _, gt, dets in docs:
        tps = [d for d in dets if (name, ident(d)) in base_tp]
        spacy_sorted = sorted(
            (d for d in dets if d.source == "spacy"), key=lambda e: e.start_pos
        )
        for x in base_fp[name]:
            partners = [
                t for t in tps if t.entity_type == x.entity_type and raw_overlap(t, x)
            ]
            if not partners:
                continue
            f1_type[x.entity_type] += 1
            p = max(
                partners,
                key=lambda t: min(t.end_pos, x.end_pos) - max(t.start_pos, x.start_pos),
            )
            src = "/".join(sorted((x.source, p.source)))
            f1_src[src] += 1
            rel = relation(p, x)
            if rel == "containment":
                rel = (
                    "containment (FP contains TP)"
                    if _contains(core(x), core(p))
                    else "containment (TP contains FP)"
                )
            f1_rel[rel] += 1
            # merge loop logs partial_overlap on (regex r, first overlapping spaCy s)
            logged = False
            if {x.source, p.source} == {"spacy", "regex"}:
                r = x if x.source == "regex" else p
                s = p if r is x else x
                first = next((e for e in spacy_sorted if raw_overlap(e, r)), None)
                logged = r.is_ambiguous and first is s
            f1_log["logged partial_overlap" if logged else "not logged"] += 1
    print(f"  total={sum(f1_type.values())} per type={dict(f1_type)}")
    print(f"  by pair source={dict(f1_src)}")
    print(f"  by relation (normalized cores)={dict(f1_rel)}")
    print(f"  by merge-loop log={dict(f1_log)}")

    # ---- 1.4 F2 re-measure ------------------------------------------------
    rm = RoleMatcher()
    print("\n## 1.4 F2: ORG detections matched by the AC3 list")
    grp_fp: collections.Counter[str] = collections.Counter()
    grp_tp: collections.Counter[str] = collections.Counter()
    term_fp: collections.Counter[str] = collections.Counter()
    tp_hits: list[tuple[str, str]] = []
    missed: collections.Counter[str] = collections.Counter()
    role_word = re.compile(
        r"\b(?:" + "|".join(ACRONYMS) + r"|VP|Vice[- ]pr[ée]sident)\b"
    )
    for name, _, gt, dets in docs:
        for d in dets:
            if d.entity_type != "ORG":
                continue
            g = rm.match(d.text)
            is_tp = (name, ident(d)) in base_tp
            if g:
                (grp_tp if is_tp else grp_fp)[g] += 1
                if not is_tp:
                    term_fp[" ".join(strip_french_titles(d.text).split())] += 1
                else:
                    tp_hits.append((d.text, name))
            elif not is_tp and role_word.search(d.text):
                missed[d.text] += 1
    print(f"  ORG FP dropped={sum(grp_fp.values())} by group={dict(grp_fp)}")
    print(f"  ORG TP dropped={sum(grp_tp.values())} by group={dict(grp_tp)}")
    for t, n in tp_hits:
        print(f"    TP HIT: {t!r} in {n}")
    print("  FP by matched text:")
    for t, n in term_fp.most_common():
        print(f"    {n:3} {t!r}")
    print(f"  role-like ORG FP the whole-span rule misses={sum(missed.values())}")
    for t, n in missed.most_common():
        print(f"    {n:3} {t!r}")

    # ---- role filter dry-run ---------------------------------------------
    def role_filter(dets: list[DetectedEntity]) -> list[DetectedEntity]:
        return [d for d in dets if not (d.entity_type == "ORG" and rm.match(d.text))]

    filtered = [(n, tx, gt, role_filter(d)) for n, tx, gt, d in docs]
    after_role = score((gt, d) for _, _, gt, d in filtered)
    print_delta("Dry-run: role filter only (vs baseline)", base, after_role)

    # ---- 1.5 dedup dry-runs ----------------------------------------------
    for label, mode in VARIANTS.items():
        out: list[tuple[list[GroundTruthEntity], list[DetectedEntity]]] = []
        all_drops: list[tuple[str, str, Drop]] = []
        for name, text, gt, dets in filtered:
            kept, drops = dedup(dets, mode)
            out.append((gt, kept))
            all_drops += [(name, text, dr) for dr in drops]
        after = score(out)
        print_delta(
            f"Dry-run: role filter + dedup {label} (vs role filter only)",
            after_role,
            after,
        )
        print_delta(f"Dry-run: role filter + dedup {label} (vs baseline)", base, after)
        reasons = collections.Counter(dr[2] for *_, dr in all_drops)
        print(f"  drops={len(all_drops)} by reason={dict(reasons)}")

        # post-rule matching, per doc, to classify lost TPs
        post_matched: dict[str, set[int]] = {}
        for (name, *_), (gt, kept) in zip(filtered, out):
            tp, _, _ = match_entities(kept, gt)
            post_matched[name] = {id(g) for _, g in tp}
        cls: collections.Counter[str] = collections.Counter()
        cont_pat: dict[str, list[str]] = collections.defaultdict(list)
        lost_rows: list[str] = []
        for name, text, (kept_e, dropped, reason) in all_drops:
            g = base_tp.get((name, ident(dropped)))
            if g is None:
                continue
            at_position = (
                g.start_pos < dropped.end_pos and dropped.start_pos < g.end_pos
            )
            now_fn = id(g) not in post_matched[name]
            kind = ("position" if at_position else "cross-position") + (
                " -> FN" if now_fn else " -> taken over"
            )
            cls[f"{dropped.entity_type} {kind}"] += 1
            lost_rows.append(
                f"    [{dropped.entity_type}] {kind}: kept {kept_e.text!r}({kept_e.source}) "
                f"dropped {dropped.text!r}({dropped.source}) reason={reason} doc={name}"
            )
            if reason.startswith("containment") and now_fn:
                outer = kept_e
                toks = (
                    added_tokens(outer, dropped)
                    if _contains(core(outer), core(dropped))
                    else []
                )
                pat = loss_pattern(outer, dropped, toks)
                cont_pat[pat].append(f"{outer.text!r} > {dropped.text!r} ({name})")
        print(f"  dropped baseline TPs={sum(cls.values())} classification={dict(cls)}")
        if mode in ((), ("C1",)):
            for row in lost_rows:
                print(row)
        print("  containment losses (dropped TP -> FN) by pattern:")
        for pat in sorted(cont_pat):
            rows = cont_pat[pat]
            print(f"    {pat}: {len(rows)}")
            for r in rows[:n_ex]:
                print(f"      {r}")


if __name__ == "__main__":
    main()
