"""Re-measure the type-blind exact match and dry-run the Story 10.3c rules.

Story 10.3c, Tasks 1.1-1.9. Main corpus only: calls ``_load_corpus_documents()``
and never the held-out loader. Imports ``tests.accuracy.conftest`` and
``tests.accuracy.bootstrap`` read-only (G4 scope). No product code is changed:
every candidate rule is patched in this script only, on one
``HybridDetector`` instance, and every document goes through the real
``detect_entities`` (both ``_fix_person_boundaries`` calls, the guarded
re-merge, R-SPLIT late, W-JOIN and R-ROLE-LATE all run).

What is patched (instance attributes, so the class is untouched):

- ``regex_matcher.match_entities``: the same code, recording the category
  that produced each regex entity (checked against the original output);
- ``_fix_person_boundaries``: the original, recording reshaped PERSON spans
  (the QA MX-001 shape);
- ``_refused_guards``: the original, recording every guarded trim and
  whether it was refused (Task 1.8);
- ``_merge_entities``: a copy of the product method whose merge loop takes a
  rule (``base`` = today's code, ``mx``, ``mxcab``, ``mxall``), the AC3
  candidates (R-HYPH-GEO, R-HYPH-FN) and an input-order option (Task 1.6).
  The post-filters after the loop are the product's, called unchanged.

The ``base`` run must reproduce the baseline dump byte for byte
(``scripts/accuracy_dump_detections.py``); otherwise the script stops.

Reuses the 10.3a helpers of ``scripts/accuracy_runon_dryrun.py`` (net
per-type delta, lost/gained TP classification, coverage levels 1/2/2b), as
``scripts/accuracy_particles_noise_dryrun.py`` (10.3b) does.

The counts printed here are local attribution numbers (Product Constraint 6):
they belong in the story only, never in the QA report, CHANGELOG or PR body.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_type_aware_match_dryrun.py <baseline_dump.json> <out_dir>
"""

from __future__ import annotations

import collections
import json
import re
import sys
import types
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# 10.3a helpers (this import also configures structlog and stdout)
import accuracy_runon_dryrun as ro  # noqa: E402

from gdpr_pseudonymizer.nlp import hybrid_detector as hd  # noqa: E402
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity  # noqa: E402
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector  # noqa: E402
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher  # noqa: E402
from gdpr_pseudonymizer.utils.french_patterns import (  # noqa: E402
    strip_french_titles,
)
from tests.accuracy import bootstrap  # noqa: E402
from tests.accuracy.conftest import (  # noqa: E402
    _load_corpus_documents,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")
_U = "A-ZÀ-ÖØ-ÞĀ-ſ"
_L = "a-zß-öø-ÿĀ-ſ"
# R-HYPH-FN shape: the compound_names pattern (detection_patterns.yaml:32),
# two capitalised words joined by one hyphen, on the title-stripped text
COMPOUND_SHAPE = re.compile(f"[{_U}][{_L}]+-[{_U}][{_L}]+")
ORG_PREFIXES = ("Cabinet", "Société", "Entreprise", "Groupe", "Compagnie")

DEFAULT_CFG: dict[str, Any] = {
    "rule": "base",  # base | mx | mxcab | mxall
    "geo": False,  # R-HYPH-GEO
    "fn": False,  # R-HYPH-FN
    "rev_spacy": False,
    "rev_regex": False,
    "verify_match": False,
}
CFG: dict[str, Any] = dict(DEFAULT_CFG)
CUR: dict[str, Any] = {}

Key = tuple[int, int, str, str]


def key(e: DetectedEntity) -> Key:
    return (e.start_pos, e.end_pos, e.entity_type, e.text)


def canon(dets: list[DetectedEntity]) -> list[tuple[Any, ...]]:
    return sorted(
        (e.text, e.entity_type, e.start_pos, e.end_pos, e.source, e.is_ambiguous)
        for e in dets
    )


# ---------------------------------------------------------------------------
# Recording wrappers (no behaviour change)
# ---------------------------------------------------------------------------

_ORIG_MATCH = RegexMatcher.match_entities
_ORIG_FIX = HybridDetector._fix_person_boundaries
_ORIG_REFUSED = HybridDetector._refused_guards


def _rec_match(
    self: RegexMatcher, text: str, spacy_doc: Any | None = None
) -> list[DetectedEntity]:
    """``RegexMatcher.match_entities`` (regex_matcher.py:162-213), recording
    the category of each kept entity."""
    entities: list[DetectedEntity] = []
    cat: dict[int, str] = {}
    for category, pattern_list in self.patterns.items():
        for pattern_def in pattern_list:
            for match in pattern_def["regex"].finditer(text):
                if pattern_def[
                    "require_known_first_name"
                ] and not self._has_known_first_name(match):
                    continue
                entity = DetectedEntity(
                    text=match.group(0),
                    entity_type=pattern_def["entity_type"],
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=pattern_def["confidence"],
                    source="regex",
                )
                entities.append(entity)
                cat[id(entity)] = category
    if self.name_dictionary and self._is_full_names_enabled():
        for entity in self._match_full_names(text):
            entities.append(entity)
            cat[id(entity)] = "full_names"
    if self.geography_dictionary and self._is_geography_enabled():
        for entity in self._match_geography(text, spacy_doc=spacy_doc):
            entities.append(entity)
            cat[id(entity)] = "geography_dictionary"
    out = self._deduplicate_entities(entities)
    CUR["cat"].update({key(e): cat[id(e)] for e in out})
    if CFG["verify_match"]:
        orig = _ORIG_MATCH(self, text, spacy_doc)
        mine = [(key(e), e.confidence, e.source) for e in out]
        theirs = [(key(e), e.confidence, e.source) for e in orig]
        if mine != theirs:
            CUR["match_mismatch"].append(CUR["doc"])
    return out


def _rec_fix(
    self: HybridDetector,
    entities: list[DetectedEntity],
    text: str,
    blockers: list[tuple[int, int]],
) -> tuple[list[DetectedEntity], list[Any]]:
    out, guards = _ORIG_FIX(self, entities, text, blockers)
    for old, new in zip(entities, out):
        if key(old) != key(new):
            CUR["reshaped"][(new.source, key(new))] = key(old)
    return out, guards


def _rec_refused(guards: list[Any], kept: Any) -> dict[int, DetectedEntity]:
    refused = _ORIG_REFUSED(guards, kept)
    for g in guards:
        CUR["guards"].append(
            (
                CUR["merge_no"],
                g.rule,
                g.original.source,
                g.original.start_pos,
                g.original.end_pos,
                g.original.text,
                g.index in refused,
            )
        )
    return refused


# ---------------------------------------------------------------------------
# The merge, with the candidate rules (Dev Notes "Candidate Rules")
# ---------------------------------------------------------------------------


def _match_kind(r: DetectedEntity, s: DetectedEntity) -> str:
    if r.start_pos == s.start_pos and r.end_pos == s.end_pos:
        return "span"
    return "normalized_text"


def _event(
    self: HybridDetector,
    kind: str,
    r: DetectedEntity,
    s: DetectedEntity,
    rules: list[str] | None = None,
) -> None:
    orig_r = CUR["reshaped"].get(("regex", key(r)))
    CUR["events"].append(
        {
            "merge": CUR["merge_no"],
            "kind": kind,
            "rtype": r.entity_type,
            "rtext": r.text,
            "rstart": r.start_pos,
            "rend": r.end_pos,
            "stype": s.entity_type,
            "stext": s.text,
            "sstart": s.start_pos,
            "send": s.end_pos,
            "match": _match_kind(r, s),
            "category": CUR["cat"].get(orig_r or key(r), "?"),
            "reshaped_r": orig_r is not None,
            "reshaped_s": ("spacy", key(s)) in CUR["reshaped"],
            "cabinet": self._should_prefer_regex_org(r, s),
            "rules": rules or [],
            "rkey": key(r),
            "skey": key(s),
        }
    )


def _ac3_fires(self: HybridDetector, r: DetectedEntity, s: DetectedEntity) -> list[str]:
    fires: list[str] = []
    if r.entity_type != "PERSON":
        return fires
    core = strip_french_titles(r.text)
    if (
        CFG["geo"]
        and s.entity_type in ("LOCATION", "ORG")
        and core.casefold() in hd._geography_folded()
    ):
        fires.append("R-HYPH-GEO")
    if (
        CFG["fn"]
        and COMPOUND_SHAPE.fullmatch(core)
        and not any(self._known_first_name(p) for p in core.split("-"))
    ):
        fires.append("R-HYPH-FN")
    return fires


def _step2(
    self: HybridDetector,
    r: DetectedEntity,
    s: DetectedEntity,
    merged: list[DetectedEntity],
) -> None:
    """R-MX step 2: different-type exact match, keep both (unless an AC3
    candidate restores today's skip)."""
    fires = _ac3_fires(self, r, s)
    if fires:
        _event(self, "ac3_skip", r, s, fires)
        return
    r.is_ambiguous = True
    merged.append(r)
    _event(self, "kept_diff", r, s)


def _branch(
    self: HybridDetector, r: DetectedEntity, s: DetectedEntity, rule: str
) -> str:
    """The branch the merge loop would take if ``s`` were the first overlap."""
    if self._is_exact_match(s, r):
        if r.entity_type == s.entity_type or rule == "base":
            return "skip"
        if rule != "mxcab" or not self._should_prefer_regex_org(r, s):
            return "keep_flagged(exact)"
    if self._should_prefer_regex_org(r, s):
        return "cabinet"
    if r.entity_type != s.entity_type:
        return "keep_flagged(partial)"
    return "keep(same-type partial)"


def _merge_variant(  # noqa: C901
    self: HybridDetector,
    spacy_entities: list[DetectedEntity],
    regex_entities: list[DetectedEntity],
    text: str | None = None,
) -> list[DetectedEntity]:
    """``HybridDetector._merge_entities`` (hybrid_detector.py:667-790) with the
    10.3c candidate rules in the merge loop; the post-filters are unchanged."""
    CUR["merge_no"] += 1
    if CFG["rev_spacy"]:
        spacy_entities = list(reversed(spacy_entities))
    if CFG["rev_regex"]:
        regex_entities = list(reversed(regex_entities))
    rule = CFG["rule"]

    merged: list[DetectedEntity] = list(spacy_entities)
    entities_to_remove: list[DetectedEntity] = []

    for regex_entity in regex_entities:
        overlapping = [s for s in spacy_entities if self._has_overlap(s, regex_entity)]
        if not overlapping:
            merged.append(regex_entity)
            continue
        if len(overlapping) > 1:
            CUR["multi"].append(
                (
                    CUR["merge_no"],
                    key(regex_entity),
                    [_branch(self, regex_entity, s, rule) for s in overlapping],
                )
            )
        exact = False
        if rule == "mxall":
            exacts = [s for s in overlapping if self._is_exact_match(s, regex_entity)]
            same = [s for s in exacts if s.entity_type == regex_entity.entity_type]
            if same:
                _event(self, "skip_same", regex_entity, same[0])
                continue
            if exacts:
                _step2(self, regex_entity, exacts[0], merged)
                continue
            spacy_entity = overlapping[0]
        else:
            # today: the first overlapping spaCy entity decides
            spacy_entity = overlapping[0]
            exact = self._is_exact_match(spacy_entity, regex_entity)
            if exact:
                same_type = spacy_entity.entity_type == regex_entity.entity_type
                if rule == "base" or same_type:
                    _event(
                        self,
                        "skip_same" if same_type else "skip_diff",
                        regex_entity,
                        spacy_entity,
                    )
                    continue
                if rule == "mx":
                    _step2(self, regex_entity, spacy_entity, merged)
                    continue
                # mxcab: falls through into today's branches
        if self._should_prefer_regex_org(regex_entity, spacy_entity):
            entities_to_remove.append(spacy_entity)
            merged.append(regex_entity)
            if exact:
                _event(self, "cab_removed", regex_entity, spacy_entity)
            continue
        if regex_entity.entity_type != spacy_entity.entity_type:
            regex_entity.is_ambiguous = True
            merged.append(regex_entity)
            if exact:
                _event(self, "kept_diff", regex_entity, spacy_entity)
            continue
        merged.append(regex_entity)

    # ---- unchanged from here (hybrid_detector.py:750-790) ----
    for entity in entities_to_remove:
        if entity in merged:
            merged.remove(entity)
    merged = self._filter_title_only_entities(merged)
    merged = self._filter_label_words(merged)
    merged = self._filter_location_noise(merged, text)
    merged = self._filter_org_roles(merged, text)
    merged = self._dedup_same_type_overlaps(merged, text)
    merged, split_count = self._split_at_line_breaks(merged, text)
    if split_count:
        merged = self._filter_title_only_entities(merged)
        merged = self._filter_label_words(merged)
        merged = self._filter_location_noise(merged, text)
        merged = self._filter_org_roles(merged, text)
        merged = self._dedup_same_type_overlaps(merged, text)
    if text is not None:
        merged = self._join_wrapped_names(merged, text)
        merged = self._trim_roles_late(merged, text)
    merged.sort(key=lambda e: e.start_pos)
    return merged


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class Result:
    """One dry-run: detections per document, plus the per-document records
    of the last merge (events, guards)."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.dets: dict[str, list[DetectedEntity]] = {}
        self.events: dict[str, list[dict[str, Any]]] = {}
        self.all_events: dict[str, list[dict[str, Any]]] = {}
        self.guards: dict[str, list[tuple[Any, ...]]] = {}
        self.merges: dict[str, int] = {}
        self.multi: dict[str, list[tuple[Any, ...]]] = {}


def run(det: HybridDetector, docs: list[Any], label: str, **cfg: Any) -> Result:
    CFG.clear()
    CFG.update(DEFAULT_CFG)
    CFG.update(cfg)
    res = Result(label)
    for name, text, _gt in docs:
        CUR.update(
            doc=name,
            merge_no=0,
            cat={},
            reshaped={},
            events=[],
            guards=[],
            multi=[],
            match_mismatch=CUR.get("match_mismatch", []),
        )
        res.dets[name] = det.detect_entities(text)
        last = CUR["merge_no"]
        res.merges[name] = last
        res.all_events[name] = list(CUR["events"])
        res.events[name] = [e for e in CUR["events"] if e["merge"] == last]
        res.guards[name] = list(CUR["guards"])
        res.multi[name] = [m for m in CUR["multi"] if m[0] == last]
    CFG.clear()
    CFG.update(DEFAULT_CFG)
    return res


def dump_json(res: Result) -> str:
    dump = {
        name: [
            {
                "text": d.text,
                "type": d.entity_type,
                "start": d.start_pos,
                "end": d.end_pos,
                "source": d.source,
                "is_ambiguous": d.is_ambiguous,
            }
            for d in dets
        ]
        for name, dets in res.dets.items()
    }
    return json.dumps(dump, ensure_ascii=False, indent=0)


def write_per_doc(path: Path, docs: list[Any], res: Result) -> None:
    names, per_doc = [], []
    for name, _text, gt in docs:
        tp, fp, fn = match_entities(res.dets[name], gt)
        scored = types.SimpleNamespace(
            true_positives=tp, false_positives=fp, false_negatives=fn
        )
        names.append(name)
        per_doc.append(bootstrap.doc_counts(scored))
    bootstrap.write_per_document_json(path, names, per_doc, None, None)


def n_flagged(res: Result) -> int:
    return sum(e.is_ambiguous for dets in res.dets.values() for e in dets)


def ev_line(name: str, e: dict[str, Any]) -> str:
    return (
        f"    [{name}] merge#{e['merge']} {e['kind']}: regex {e['rtype']} "
        f"{e['rtext']!r} @{e['rstart']}-{e['rend']} ({e['category']}"
        f"{', reshaped' if e['reshaped_r'] else ''}) vs spaCy {e['stype']} "
        f"{e['stext']!r} @{e['sstart']}-{e['send']}"
        f"{' (reshaped)' if e['reshaped_s'] else ''} match={e['match']}"
        f"{' CABINET' if e['cabinet'] else ''}"
        f"{' rules=' + ','.join(e['rules']) if e['rules'] else ''}"
    )


def gt_at(gt: list[Any], start: int, end: int) -> list[str]:
    return [
        f"{g.entity_type} {g.text!r} @{g.start_pos}"
        for g in gt
        if g.start_pos < end and start < g.end_pos
    ]


def partner_report(res: Result, docs: list[Any], log: list[str]) -> tuple[int, int]:
    """Flagged regex entities kept by an exact match (last merge) whose spaCy
    partner is not in the output any more, and kept ones themselves gone."""
    lost_partner = 0
    gone = 0
    for name, _text, _gt in docs:
        out = {(key(e), e.source) for e in res.dets[name]}
        for e in res.events[name]:
            if e["kind"] != "kept_diff":
                continue
            r_in = (e["rkey"], "regex") in out
            s_in = (e["skey"], "spacy") in out
            if not r_in:
                gone += 1
                log.append(f"  kept regex entity not in the output: {ev_line(name, e)}")
            if not s_in:
                lost_partner += 1
                log.append(f"  spaCy partner not in the output: {ev_line(name, e)}")
    return lost_partner, gone


def order_dependent(
    real: Result, others: list[Result]
) -> tuple[set[str], dict[str, set[tuple[Any, ...]]]]:
    docs_dep: set[str] = set()
    diffs: dict[str, set[tuple[Any, ...]]] = collections.defaultdict(set)
    for name in real.dets:
        a = canon(real.dets[name])
        for o in others:
            b = canon(o.dets[name])
            if a != b:
                docs_dep.add(name)
                diffs[name] |= set(a) ^ set(b)
    return docs_dep, diffs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: C901
    if len(sys.argv) != 3:
        sys.exit(
            "usage: accuracy_type_aware_match_dryrun.py <baseline_dump.json> <out_dir>"
        )
    dump_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    if REPO_ROOT in out_dir.parents or out_dir == REPO_ROOT:
        sys.exit("refusing to write inside the repository")
    out_dir.mkdir(parents=True, exist_ok=True)

    det = HybridDetector()
    det.load_model("fr_core_news_lg")
    det.regex_matcher.match_entities = types.MethodType(  # type: ignore[method-assign]
        _rec_match, det.regex_matcher
    )
    det._fix_person_boundaries = types.MethodType(_rec_fix, det)  # type: ignore[method-assign]
    det._refused_guards = _rec_refused  # type: ignore[method-assign,assignment]
    det._merge_entities = types.MethodType(_merge_variant, det)  # type: ignore[method-assign]

    docs = _load_corpus_documents()
    gts = {n: gt for n, _t, gt in docs}
    log: list[str] = []
    table: list[str] = []

    # --- 1.1 base run reproduces the baseline dump -------------------------
    CUR["match_mismatch"] = []
    base = run(det, docs, "base", verify_match=True)
    base_text = dump_json(base)
    (out_dir / "dump_base.json").write_text(base_text, encoding="utf-8")
    identical = base_text == dump_path.read_text(encoding="utf-8")
    btot, base_pairs = ro.tally(docs, base.dets)
    n_det = sum(len(v) for v in base.dets.values())
    log.append(
        f"# 1.1 base run: {n_det} detections; byte-identical to {dump_path.name}: "
        f"{identical}; regex-category recorder mismatches: "
        f"{len(CUR['match_mismatch'])}"
    )
    log.append(f"  tally: {btot}")
    if not identical or CUR["match_mismatch"]:
        print("\n".join(log))
        sys.exit("base run does not reproduce the baseline dump: stop")
    write_per_doc(out_dir / "perdoc_base.json", docs, base)
    log.append("# 1.2 local per-document JSON: perdoc_base.json (run `delta`)")
    base_run = ro.Run("base", base.dets)

    def row(label: str, res: Result, rep: dict[str, Any], fires: str) -> None:
        d = rep["delta"]
        p, r, f = ro.prf(*rep["tot"]["Overall"])
        cells = " | ".join(f"{d[t][0]:+d}/{d[t][1]:+d}/{d[t][2]:+d}" for t in TYPES)
        fn = "/".join(str(rep["tot"][t][2]) for t in ("Overall",) + TYPES)
        table.append(
            f"| {label} | {cells} | {p:.4f} / {r:.4f} / {f:.4f} | {rep['l2']} | "
            f"{rep['l2b']} | {rep['l1_chars']} ({rep['l1_in_gt']}) / "
            f"{rep['l1_spans']} | {n_flagged(res)} | {fires} | FN {fn} |"
        )

    bp, br, bf = ro.prf(*btot["Overall"])
    table.append(
        f"| base | {btot['PERSON']} {btot['LOCATION']} {btot['ORG']} | "
        f"{bp:.4f} / {br:.4f} / {bf:.4f} | - | - | - | "
        f"{n_flagged(base)} | - | FN {btot['Overall'][2]}/"
        f"{btot['PERSON'][2]}/{btot['LOCATION'][2]}/{btot['ORG'][2]} |"
    )

    # --- 1.3 inventory --------------------------------------------------------
    log.append("\n# 1.3 exact-match skips today (base code)")
    inv: collections.Counter[tuple[str, ...]] = collections.Counter()
    merges = collections.Counter(base.merges.values())
    log.append(f"  merges per document: {dict(merges)}")
    diff_rows: list[str] = []
    mx001: list[str] = []
    cabinet: list[str] = []
    for name, _t, _g in docs:
        for e in base.all_events[name]:
            if not e["kind"].startswith("skip"):
                continue
            pair = f"{e['rtype']}->{e['stype']}"
            same = "same-type" if e["kind"] == "skip_same" else "different-type"
            final = "final merge" if e["merge"] == base.merges[name] else "1st merge"
            inv[(same, pair, e["match"], e["category"], final)] += 1
            if e["kind"] == "skip_diff":
                diff_rows.append(ev_line(name, e) + f" [{final}]")
            if e["reshaped_r"] or e["reshaped_s"]:
                mx001.append(ev_line(name, e) + f" [{final}]")
            if e["cabinet"]:
                cabinet.append(ev_line(name, e) + f" [{final}]")
    for k, v in sorted(inv.items()):
        log.append(f"  {v:4d}  {' | '.join(k)}")
    by_pair: collections.Counter[tuple[str, str]] = collections.Counter()
    for k, v in inv.items():
        by_pair[(k[0], k[1])] += v
    log.append("  by type pair (all merges):")
    for k, v in sorted(by_pair.items()):
        log.append(f"  {v:4d}  {k[0]} {k[1]}")
    log.append(f"  different-type cases ({len(diff_rows)}):")
    log.extend(diff_rows)
    log.append(f"  reshaped by _fix_person_boundaries (MX-001 shapes): {len(mx001)}")
    log.extend(mx001)
    log.append(f"  Cabinet pairs (_should_prefer_regex_org true): {len(cabinet)}")
    log.extend(cabinet)

    def evaluate(label: str, res: Result, fires_kind: str | None = None) -> None:
        (out_dir / f"dump_{label}.json").write_text(dump_json(res), encoding="utf-8")
        write_per_doc(out_dir / f"perdoc_{label}.json", docs, res)
        rep = ro.report(docs, base_run, ro.Run(label, res.dets), base_pairs, log)
        log.append(
            f"  flagged (is_ambiguous): base {n_flagged(base)} -> {n_flagged(res)}"
        )
        kept = [
            ev_line(n, e)
            for n, _t, _g in docs
            for e in res.events[n]
            if e["kind"] == "kept_diff"
        ]
        log.append(f"  kept different-type exact pairs (final merge): {len(kept)}")
        log.extend(kept)
        cab = [
            ev_line(n, e)
            for n, _t, _g in docs
            for e in res.events[n]
            if e["kind"] == "cab_removed"
        ]
        if cab:
            log.append(f"  Cabinet special case on exact pairs: {len(cab)}")
            log.extend(cab)
        lost_partner, gone = partner_report(res, docs, log)
        log.append(
            f"  kept pairs whose spaCy partner is gone from the output: "
            f"{lost_partner}; whose regex entity is gone: {gone}"
        )
        fires = "-"
        if fires_kind:
            fl = [
                (n, e)
                for n, _t, _g in docs
                for e in res.events[n]
                if e["kind"] == "ac3_skip"
            ]
            non_target = 0
            log.append(f"  AC3 fires (final merge): {len(fl)}")
            for n, e in fl:
                at = gt_at(gts[n], e["rstart"], e["rend"])
                person = any(a.startswith("PERSON") for a in at)
                hyph = bool(COMPOUND_SHAPE.fullmatch(strip_french_titles(e["rtext"])))
                nt = person or not hyph
                non_target += nt
                log.append(
                    ev_line(n, e)
                    + f" GT={at or 'none'}"
                    + (" NON-TARGET" if nt else "")
                )
            fires = f"{len(fl)} fires, {non_target} non-target"
        row(label, res, rep, fires)

    # --- 1.4 R-MX ------------------------------------------------------------
    mx = run(det, docs, "R-MX", rule="mx")
    evaluate("R-MX", mx)

    # --- 1.5 R-MX-CAB (information only) -------------------------------------
    mxcab = run(det, docs, "R-MX-CAB", rule="mxcab")
    evaluate("R-MX-CAB", mxcab)

    # --- 1.6 order check -----------------------------------------------------
    log.append("\n# 1.6 order check (lists reversed after both boundary fixes)")
    base_rs = run(det, docs, "base_rs", rev_spacy=True)
    base_rr = run(det, docs, "base_rr", rev_regex=True)
    mx_rs = run(det, docs, "mx_rs", rule="mx", rev_spacy=True)
    mx_rr = run(det, docs, "mx_rr", rule="mx", rev_regex=True)
    for res in (base, mx):
        multi = [(n, m) for n in res.multi for m in res.multi[n]]
        split = [(n, m) for n, m in multi if len(set(m[2])) > 1]
        log.append(
            f"  {res.label}: regex entities overlapping 2+ spaCy entities (final "
            f"merge): {len(multi)}; whose branch depends on which one is first: "
            f"{len(split)}"
        )
        for n, m in split:
            log.append(f"    [{n}] regex {m[1]}: branches in list order {m[2]}")
    dep_base, diff_base = order_dependent(base, [base_rs, base_rr])
    dep_mx, diff_mx = order_dependent(mx, [mx_rs, mx_rr])
    new_docs = sorted(dep_mx - dep_base)
    log.append(f"  order-dependent documents, base: {len(dep_base)} {sorted(dep_base)}")
    log.append(f"  order-dependent documents, R-MX: {len(dep_mx)} {sorted(dep_mx)}")
    log.append(f"  NEW (R-MX but not base): {len(new_docs)} {new_docs}")
    extra = {
        n: diff_mx[n] - diff_base.get(n, set())
        for n in diff_mx
        if diff_mx[n] - diff_base.get(n, set())
    }
    log.append(
        f"  detection-level differences under R-MX not seen under base: "
        f"{sum(len(v) for v in extra.values())} in {len(extra)} documents"
    )
    for n, v in sorted(extra.items()):
        for t in sorted(v):
            log.append(f"    [{n}] {t}")
    mxall = run(det, docs, "R-MX-ALL", rule="mxall")
    mxall_rs = run(det, docs, "mxall_rs", rule="mxall", rev_spacy=True)
    mxall_rr = run(det, docs, "mxall_rr", rule="mxall", rev_regex=True)
    dep_all, diff_all = order_dependent(mxall, [mxall_rs, mxall_rr])
    eq_all = all(canon(mxall.dets[n]) == canon(mx.dets[n]) for n in mx.dets)
    new_all = sorted(dep_all - dep_base)
    log.append(
        f"  R-MX-ALL real order equals R-MX: {eq_all}; order-dependent: "
        f"{len(dep_all)}; new vs base: {len(new_all)} {new_all}"
    )
    adopt = bool(new_docs) and eq_all and not new_all
    log.append(f"  R-MX-ALL adopted: {adopt}")
    if new_docs or not eq_all:
        evaluate("R-MX-ALL", mxall)

    # --- 1.7 AC3 candidates --------------------------------------------------
    rule = "mxall" if adopt else "mx"
    for label, geo, fn in (
        ("R-MX+R-HYPH-GEO", True, False),
        ("R-MX+R-HYPH-FN", False, True),
        ("R-MX+R-HYPH-GEO+R-HYPH-FN", True, True),
    ):
        res = run(det, docs, label, rule=rule, geo=geo, fn=fn)
        evaluate(label, res, fires_kind="ac3")

    # --- 1.8 guard interplay -------------------------------------------------
    log.append("\n# 1.8 guarded role trims (final merge decision), base vs R-MX")

    def guard_set(res: Result) -> dict[str, set[tuple[Any, ...]]]:
        out: dict[str, set[tuple[Any, ...]]] = {}
        for n in res.guards:
            # the decision is taken after the first merge
            out[n] = {g[1:] for g in res.guards[n] if g[0] == 1}
        return out

    gb, gm = guard_set(base), guard_set(mx)
    n_guards = sum(len(v) for v in gb.values())
    n_refused = sum(1 for v in gb.values() for g in v if g[-1])
    log.append(f"  guarded trims (base): {n_guards}, refused: {n_refused}")
    for label, gs in (("base", gb), ("R-MX", gm)):
        for n in sorted(gs):
            for g in sorted(gs[n]):
                log.append(f"    {label} [{n}] {g}")
    changed = 0
    for n in sorted(gb):
        for g in sorted(gb[n] ^ gm.get(n, set())):
            changed += 1
            side = "base" if g in gb[n] else "R-MX"
            log.append(f"    [{n}] {side}: {g}")
    log.append(f"  guard outcomes that differ: {changed} (each case appears per side)")

    (out_dir / "dryrun_report.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    hdr = (
        "| Rule | PERSON ΔTP/ΔFP/ΔFN | LOCATION | ORG | P / R / F1 (local) | L2 | "
        "L2b | L1 chars (in GT) / spans | Flagged | Fires (non-target) | "
        "projected FN O/P/L/Org |"
    )
    (out_dir / "dryrun_table.md").write_text(
        hdr + "\n" + "\n".join(table) + "\n", encoding="utf-8"
    )
    print("\n".join(log[:3]))
    print(hdr)
    print("\n".join(table))
    print(f"-> {out_dir / 'dryrun_report.txt'}")


if __name__ == "__main__":
    main()
