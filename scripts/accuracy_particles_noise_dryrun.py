"""Re-measure F6/F7 and dry-run the Story 10.3b candidate rules.

Story 10.3b, Tasks 1.2-1.8. Main corpus only: calls ``_load_corpus_documents()``
and never the held-out loader. Imports ``tests.accuracy.conftest`` read-only
(G4 scope). No product code is changed: every candidate rule is patched in
this script only (pre-merge list edits, monkeypatched methods, modified
copies of ``detection_patterns.yaml`` written outside the repository).

Reuses the 10.3a helpers of ``scripts/accuracy_runon_dryrun.py`` (pre-merge
capture, re-merge, net per-type delta, lost/gained TP classification,
coverage levels 1/2/2b).

The counts printed here are local attribution numbers (Product Constraint 6):
they belong in the story only, never in the QA report, CHANGELOG or PR body.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_particles_noise_dryrun.py <baseline_dump.json> <out_dir>
"""

from __future__ import annotations

import collections
import copy
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# 10.3a helpers (this import also configures structlog and stdout)
import accuracy_runon_dryrun as ro  # noqa: E402

from gdpr_pseudonymizer.nlp import hybrid_detector as hd  # noqa: E402
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity  # noqa: E402
from gdpr_pseudonymizer.nlp.hybrid_detector import (  # noqa: E402
    HybridDetector,
    load_org_role_filter,
    match_org_role,
)
from gdpr_pseudonymizer.nlp.regex_matcher import HSPACE  # noqa: E402
from gdpr_pseudonymizer.resources import (  # noqa: E402
    DETECTION_PATTERNS_PATH,
    FRENCH_GEOGRAPHY_PATH,
)
from gdpr_pseudonymizer.utils.french_patterns import (  # noqa: E402
    strip_french_prepositions,
    strip_french_titles,
)
from tests.accuracy.conftest import (  # noqa: E402
    _load_corpus_documents,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")
_U = "A-ZÀ-ÖØ-ÞĀ-ſ"
_L = "a-zß-öø-ÿĀ-ſ"

# ---------------------------------------------------------------------------
# Draft lists (Task 2 freezes them; every entry needs a generic `why`)
# ---------------------------------------------------------------------------

# AC4 particles. Lower-case and capitalised forms; all-caps forms are derived
# from the capitalised ones. "d'" is the glued elision, handled apart.
PARTICLES_LOWER = [
    "le",
    "la",
    "de",
    "du",
    "des",
    "van",
    "von",
    "der",
    "den",
    "ter",
    "ten",
]
PARTICLES_CAP = [
    "Le", "La", "De", "Du", "Des", "Van", "Von", "Der", "Den",
    "Di", "Da", "Del", "Della", "Dos",
]  # fmt: skip
PARTICLES_ALLCAPS = sorted({p.upper() for p in PARTICLES_CAP})
LOWER_DE = {"de", "du", "des"}

# AC6 role words (generic job-title head words, case-sensitive capitalised)
ROLE_WORDS = [
    "Responsable", "Directeur", "Directrice", "Chef", "Président", "Présidente",
    "Gérant", "Gérante", "Associé", "Associée", "Consultant", "Consultante",
    "Ingénieur", "Ingénieure", "Manager", "Head", "Lead", "Architecte",
    "Développeur", "Analyste", "Avocat", "Avocate", "Juriste", "Chargé",
    "Chargée", "Délégué", "Déléguée", "Secrétaire", "Trésorier",
]  # fmt: skip

# AC1/AC2 LOCATION stoplist, compared case-folded, accent-sensitive, on the
# whole normalized text. Generic categories only (story "LOCATION Noise
# Rules"); never a place, never US/USA/UK/UE/EU, never Nord/Sud/Est/Ouest.
STOPLIST: dict[str, str] = {
    # document status and label words (headers, checklists, e-mail headers)
    "conforme": "status word in audit/compliance checklists",
    "validé": "status word",
    "validée": "status word (feminine)",
    "ok": "status word",
    "cc": "e-mail header label (copie carbone)",
    "cci": "e-mail header label (copie carbone invisible)",
    "objet": "e-mail / letter header label",
    "urgent": "priority label",
    "confidentiel": "classification label",
    "nouveau": "status tag in lists and announcements",
    "new": "status tag in English lists and announcements",
    "cordialement": "letter closing word",
    # French common nouns used as headings, labels or list heads
    "équipe": "common noun used as a heading/label",
    "constat": "common noun used as an audit heading",
    "synthèse": "common noun used as a heading",
    "contexte": "common noun used as a heading",
    "annexe": "common noun used as a heading",
    "objectif": "common noun used as a heading",
    "objectifs": "common noun used as a heading (plural)",
    "recommandation": "common noun used as a heading",
    "recommandations": "common noun used as a heading (plural)",
    "conclusion": "common noun used as a heading",
    "résumé": "common noun used as a heading",
    "budget": "common noun used as a heading/label",
    "planning": "common noun used as a heading/label",
    "calendrier": "common noun used as a heading/label",
    "action": "common noun used as a heading/label",
    "actions": "common noun used as a heading/label (plural)",
    "risque": "common noun used as a heading/label",
    "risques": "common noun used as a heading/label (plural)",
    "décision": "common noun used as a heading/label",
    "commentaire": "common noun used as a heading/label",
    "résultat": "common noun used as a heading/label",
    "résultats": "common noun used as a heading/label (plural)",
    "analyse": "common noun used as a heading/label",
    "évaluation": "common noun used as a heading/label",
    "audit": "common noun used as a heading/label",
    "rapport": "common noun used as a heading/label",
    "projet": "common noun used as a heading/label",
    "phase": "common noun used as a heading/label",
    "jalon": "project-management noun (milestone)",
    "livrables": "project-management noun (plural)",
    "périmètre": "common noun used as a heading/label",
    "participants": "common noun used as a heading/label",
    "invités": "common noun used as a heading/label (minutes)",
    "registre": "common noun used as a heading/label",
    "directeur général": "job title, never a place",
    # IT and security jargon, certification names
    "pentest": "security jargon (penetration test)",
    "pentester": "security jargon (penetration tester)",
    "secnumcloud": "certification name (GUIDELINES Q6 b), never a place",
    "cloud": "IT jargon",
    "soc": "security jargon (security operations centre)",
    "siem": "security jargon",
    "api": "IT jargon",
    "devops": "IT jargon",
    "firewalls": "IT jargon (plural)",
    "backup": "IT jargon",
    "backups": "IT jargon (plural)",
    "edr": "security jargon",
    "mfa": "security jargon",
    "roadmap": "project-management jargon",
    "forensics": "security jargon",
}
Q14_ALWAYS_LOCATION = {"us", "usa", "uk", "ue", "eu"}
NEVER_STOP = Q14_ALWAYS_LOCATION | {"nord", "sud", "est", "ouest"}
LEGAL_FORMS = ["SA", "SARL", "SAS", "SASU", "EURL", "SNC", "SCM", "SCI", "GIE", "EI", "SCOP", "SEL"]  # fmt: skip

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIRES: list[tuple[str, str, str, str, str]] = []  # rule, doc, source, old, new
CUR: dict[str, Any] = {"doc": "", "sdoc": None}


def _geo_folded() -> set[str]:
    data = json.loads(FRENCH_GEOGRAPHY_PATH.read_text(encoding="utf-8"))
    out: set[str] = set()
    for key in ("cities", "regions", "departments", "countries_and_international"):
        out |= {s.casefold() for s in data.get(key, [])}
    return out


GEO = _geo_folded()


def norm_loc(text: str) -> str:
    """Stoplist comparison text: prepositions first, then titles, collapsed."""
    return " ".join(strip_french_titles(strip_french_prepositions(text)).split())


def norm_org(text: str) -> str:
    return " ".join(strip_french_titles(text).split())


def _alts(words: list[str]) -> str:
    return "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True))


PART_ANY = _alts(PARTICLES_LOWER + PARTICLES_CAP + PARTICLES_ALLCAPS)
PART_SPACED_RE = re.compile(f"{HSPACE}+({PART_ANY})(?={HSPACE})")
TAIL_PARTS_RE = re.compile(f"(?:{HSPACE}+(?:{PART_ANY}))+$")
ELISION_RE = re.compile(f"{HSPACE}+([dD]['’])(?=[{_U}])")
HS_RE = re.compile(f"{HSPACE}+")
SURNAME_RE = re.compile(
    f"(?:M(?:a)?c[{_U}][{_L}]+|[{_U}][{_L}]+|[{_U}]{{2,}})"
    f"(?:-(?:[{_U}][{_L}]+|[{_U}]{{2,}}))*(?![\\w'’])"
)
NEXT_CAP_RE = re.compile(f"{HSPACE}+[{_U}]")
MC_TAIL_RE = re.compile(r"(?<![\w])Ma?c$")
MC_WORD_RE = re.compile(f"[{_U}][{_L}]+")


def _overlaps_any(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(s < end and start < e for s, e in spans)


def fix_person_boundaries(
    entities: list[DetectedEntity],
    text: str,
    blockers: list[tuple[int, int]],
    opts: dict[str, Any],
) -> list[DetectedEntity]:
    """Dry-run of `_fix_person_boundaries` (Name Boundary Rules)."""
    out = []
    for e in entities:
        if e.entity_type != "PERSON":
            out.append(e)
            continue
        new = e
        if opts.get("mc"):
            new = _mc_extend(new, text)
        if opts.get("part"):
            new = _particle_extend(new, text, blockers, opts)
        if opts.get("role"):
            new = _role_trim(new, text, opts)
        if new is not e:
            FIRES.append(
                (new.context_label or "?", CUR["doc"], e.source, e.text, new.text)
            )
            new = dataclasses.replace(new, context_label=None)
        out.append(new)
    return out


def _with_span(e: DetectedEntity, text: str, start: int, end: int, rule: str):
    return dataclasses.replace(
        e, text=text[start:end], start_pos=start, end_pos=end, context_label=rule
    )


def _mc_extend(e: DetectedEntity, text: str) -> DetectedEntity:
    raw = text[e.start_pos : e.end_pos]
    if MC_TAIL_RE.search(raw) and e.end_pos < len(text) and text[e.end_pos].isupper():
        m = MC_WORD_RE.match(text, e.end_pos)
        if m:
            return _with_span(e, text, e.start_pos, m.end(), "mc_mac")
    return e


def _particle_extend(
    e: DetectedEntity, text: str, blockers: list[tuple[int, int]], opts: dict[str, Any]
) -> DetectedEntity:
    # work on the last line of the span only
    raw = text[e.start_pos : e.end_pos]
    last_lb = max((m.end() for m in hd._LINE_BREAK_RE.finditer(raw)), default=0)
    line_start = e.start_pos + last_lb
    # QA PERF-001: bounded walk over the last tokens (product helper)
    anchor = HybridDetector._trailing_particles_start(text, line_start, e.end_pos)
    pos = anchor
    parts: list[str] = []
    while len(parts) < 3:
        m = PART_SPACED_RE.match(text, pos)
        if not m:
            break
        parts.append(m.group(1))
        pos = m.end()
    m = ELISION_RE.match(text, pos)
    if m:
        parts.append(m.group(1))
        pos = m.end()
    else:
        if not parts:
            return e
        m = HS_RE.match(text, pos)
        if not m:
            return e
        pos = m.end()
    sur = SURNAME_RE.match(text, pos)
    if not sur:
        return e
    end = sur.end()
    if end <= e.end_pos:
        return e
    # condition 2: no further capitalised token
    if NEXT_CAP_RE.match(text, end):
        return e
    # condition 3: all-caps surname only after a capitalised/all-caps particle
    token = sur.group(0)
    if sum(c.isalpha() for c in token) >= 2 and token.replace("-", "").isupper():
        last = parts[-1]
        allowed = last[0].isupper() and opts.get("allcaps", True)
        if not allowed:
            return e
    # condition 4: blockers and geography
    if parts[-1] in ("le", "la") and token in ROLE_WORDS:
        return e  # QA REQ-001
    if _overlaps_any(e.end_pos, end, blockers):
        return e
    if token.casefold() in GEO:
        return e
    if HybridDetector._chain_names_a_place(parts, token, frozenset(GEO)):
        return e  # QA REQ-002
    phrase = " ".join(text[anchor:end].split())
    if phrase.casefold() in GEO:
        return e
    lower_de = any(
        p in LOWER_DE or p.lower().startswith("d'") or p.lower().startswith("d’")
        for p in parts
        if p[0].islower()
    )
    rule = "particle_lower_de" if lower_de else "particle"
    return _with_span(e, text, e.start_pos, end, rule)


ROLE_RE = _alts(ROLE_WORDS)
COMMA_ROLE_RE = re.compile(f",{HSPACE}+(?:{ROLE_RE})(?![\\w])")
DASH_ROLE_RE = re.compile(f"{HSPACE}+-{HSPACE}+(?:{ROLE_RE})(?![\\w])")
GLUED_PUNCT_RE = re.compile(r"[):,;]+$")


def _role_trim(e: DetectedEntity, text: str, opts: dict[str, Any]) -> DetectedEntity:
    raw = text[e.start_pos : e.end_pos]
    # same-line spans only: a span that crosses a line break is left to the
    # dedup (C2) and to R-SPLIT late
    if hd._LINE_BREAK_RE.search(raw):
        return e
    # AC6: ", <role word>" → cut before the comma (not "Last, First")
    m = COMMA_ROLE_RE.search(raw)
    if m:
        word = raw[m.start() + 1 :].split()[0]
        nd = CUR.get("names")
        if not (nd is not None and nd.is_first_name(word.strip(",.;:"))):
            keep = raw[: m.start()].rstrip()
            if keep:
                guard = [
                    (e.start_pos + w.start(), e.start_pos + w.end())
                    for w in hd._WORD_RE.finditer(raw, m.end())
                    if w.group()[0].isupper() and w.group() not in ROLE_WORDS
                ]
                CUR.setdefault("guards", []).append(
                    (CUR["doc"], e.start_pos, e.start_pos + len(keep), e, guard, 0)
                )
                return _with_span(
                    e, text, e.start_pos, e.start_pos + len(keep), "trailing_role_comma"
                )
    # AC9: " - <role word(s)> …" → cut only the role words, guarded
    if opts.get("dash"):
        m = DASH_ROLE_RE.search(raw)
        if m:
            keep = raw[: m.start()].rstrip()
            rest_start = e.start_pos + m.end()
            # capitalised words beyond the role word(s): must be covered later
            guard = [
                (e.start_pos + w.start(), e.start_pos + w.end())
                for w in hd._WORD_RE.finditer(raw, m.end())
                if w.group()[0].isupper() and w.group() not in ROLE_WORDS
            ]
            if keep:
                new = _with_span(
                    e, text, e.start_pos, e.start_pos + len(keep), "trailing_role_dash"
                )
                CUR.setdefault("guards", []).append(
                    (CUR["doc"], new.start_pos, new.end_pos, e, guard, rest_start)
                )
                return new
    # AC9 extension: trailing role acronym with no comma ("<Name> DRH")
    if opts.get("acr"):
        acr = sorted(load_org_role_filter().acronyms)
        m = re.search(f"(?<=[^\\W\\d_]){HSPACE}+(?:{_alts(acr)})$", raw)
        if m and m.start() > 0:
            return _with_span(
                e, text, e.start_pos, e.start_pos + m.start(), "trailing_role_acronym"
            )
    # AC9 extension: glued trailing punctuation ("<Name>):")
    if opts.get("punct"):
        m = GLUED_PUNCT_RE.search(raw)
        if m and m.start() > 0 and raw[m.start() - 1].isalpha():
            return _with_span(
                e, text, e.start_pos, e.start_pos + m.start(), "glued_punct"
            )
    # refinement: cut at a glued ")" / ":" followed by more text on the line
    if opts.get("punct2"):
        m = re.search(r"(?<=[^\W\d_])[):]", raw)
        if m and m.start() > 0 and raw[m.start() :].strip(" ):,;"):
            guard = [
                (e.start_pos + w.start(), e.start_pos + w.end())
                for w in hd._WORD_RE.finditer(raw, m.end())
                if w.group()[0].isupper()
            ]
            new = _with_span(
                e, text, e.start_pos, e.start_pos + m.start(), "glued_punct_cut"
            )
            if opts["punct2"] == "guarded":
                CUR.setdefault("guards", []).append(
                    (CUR["doc"], new.start_pos, new.end_pos, e, guard, 0)
                )
            return new
    return e


# --- LOCATION noise (patched in front of _filter_org_roles, both passes) ----

_ORIG_ROLES = HybridDetector._filter_org_roles


def _is_allcaps(t: str) -> bool:
    letters = [c for c in t if c.isalpha()]
    return len(letters) >= 2 and all(c.isupper() for c in letters)


def filter_location_noise(
    entities: list[DetectedEntity], text: str | None, opts: dict[str, Any]
) -> list[DetectedEntity]:
    if text is None:
        return entities
    orgs = {
        norm_org(e.text)
        for e in entities
        if e.entity_type == "ORG" and match_org_role(e.text) is None
    }
    out = []
    for e in entities:
        if e.entity_type != "LOCATION":
            out.append(e)
            continue
        raw = text[e.start_pos : e.end_pos]
        n = norm_loc(raw)
        fold = n.casefold()
        reason = None
        action = "dropped"
        if opts.get("frag"):
            bare = raw.strip().casefold()
            if n == "" or bare in {
                "d'",
                "l'",
                "aux",
                "au",
                "des",
                "du",
                "de",
                "à",
                "en",
            }:
                reason = "fragment"
        if reason is None and opts.get("stop") and fold in STOPLIST:
            if fold not in GEO and fold not in NEVER_STOP:
                reason = "allcaps_common_word" if _is_allcaps(n) else "common_noun"
        if reason is None and opts.get("ac3") and fold not in GEO and n in orgs:
            reason = "org_name"
            if opts["ac3"] == "retype":
                action = "retyped"
        if reason is None and opts.get("ac3ii"):
            if re.search(f"{HSPACE}(?:{_alts(LEGAL_FORMS)})$", n):
                reason = "org_legal_form"
        if reason is None and opts.get("pos") and CUR["sdoc"] is not None:
            if (
                n
                and len(n.split()) == 1
                and fold not in GEO
                and fold not in NEVER_STOP
                and not _is_allcaps(n)
            ):
                core = raw.find(n)
                span = CUR["sdoc"].char_span(
                    e.start_pos + max(core, 0),
                    e.start_pos + max(core, 0) + len(n),
                    alignment_mode="expand",
                )
                if span is not None and all(t.pos_ not in ("PROPN", "X") for t in span):
                    reason = "pos_common_noun"
        if reason is None:
            out.append(e)
            continue
        if action == "retyped":
            new = dataclasses.replace(e, entity_type="ORG", is_ambiguous=False)
            out.append(new)
        FIRES.append((f"loc_{reason}_{action}", CUR["doc"], e.source, e.text, action))
    return out


# --- C2 off (QA REL-002): base without the "\n" branch ----------------------

_ORIG_BASE = HybridDetector._resolve_same_type_pair_base.__func__  # type: ignore[attr-defined]
C2_FIRES: set[tuple[str, int, int, int]] = set()


def _c2_counting_base(cls, a, b, text=None):  # type: ignore[no-untyped-def]
    result, reason = _ORIG_BASE(cls, a, b, text)
    if reason == "containment_outer_trimmed_linebreak" and result is not None:
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        outer = a if (ca[0] <= cb[0] and cb[1] <= ca[1]) else b
        C2_FIRES.add((CUR["doc"], outer.start_pos, outer.end_pos, result.end_pos))
    return result, reason


def _c2off_base(cls, a, b, text=None):  # type: ignore[no-untyped-def]
    result, reason = _ORIG_BASE(cls, a, b, text)
    if reason == "containment_outer_trimmed_linebreak":
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        outer = a if (ca[0] <= cb[0] and cb[1] <= ca[1]) else b
        return outer, "containment"
    return result, reason


# --- R-WJP: W-JOIN reads the frozen particle list ---------------------------

_ORIG_WRAP_RE = hd._wrap_re  # since 10.3b the product builds it from the list


def _wjp_wrap_re() -> re.Pattern[str]:
    parts = f"(?:{_alts(PARTICLES_LOWER + PARTICLES_CAP)})"
    # QA WJ-001: Le/La/De/Du/Des are not particles on the next-line side
    after = f"(?:{_alts([p for p in PARTICLES_LOWER + PARTICLES_CAP if p not in ('Le', 'La', 'De', 'Du', 'Des')])})"
    return re.compile(
        f"(?:{HSPACE}+{parts})*{HSPACE}*\r?\n{HSPACE}*"
        f"(?P<right>(?:{after}{HSPACE}+)*{hd._WRAP_TOKEN})"
        f"(?={HSPACE}*(?:[,.!?)]|\\Z)|{HSPACE}+[a-zß-öø-ÿ])"
    )


_ORIG_JOIN = HybridDetector._join_wrapped_names


def _counting_join(entities, text):  # type: ignore[no-untyped-def]
    before = {(e.start_pos, e.end_pos, e.entity_type) for e in entities}
    out = _ORIG_JOIN(entities, text)
    for e in out:
        if (e.start_pos, e.end_pos, e.entity_type) not in before:
            FIRES.append(("wjoin", CUR["doc"], e.source, "", e.text))
    late = CUR.get("late_role")
    if late:
        CUR["guards"] = []
        res = []
        for e in out:
            new = _role_trim(e, text, late) if e.entity_type == "PERSON" else e
            if new is not e:
                ok = True
                for g in CUR["guards"]:
                    if g[3] is e:
                        ok = all(
                            any(
                                k is not e and k.start_pos <= ws and we <= k.end_pos
                                for k in out
                            )
                            for ws, we in g[4]
                        )
                if ok:
                    FIRES.append(
                        (
                            "late_" + (new.context_label or "?"),
                            CUR["doc"],
                            e.source,
                            e.text,
                            new.text,
                        )
                    )
                    new = dataclasses.replace(new, context_label=None)
                else:
                    FIRES.append(
                        ("late_guard_refused", CUR["doc"], e.source, e.text, "")
                    )
                    new = e
            res.append(new)
        CUR["guards"] = []
        out = CUR["det"]._dedup_same_type_overlaps(res, text)
        out.sort(key=lambda x: x.start_pos)
    return out


# --- regex variants -----------------------------------------------------------

TITLE_TOKEN = f"[{_U}][{_L}]+"
MC_TOKEN = f"(?:M(?:a)?c[{_U}][{_L}]+|[{_U}][{_L}]+)"


def write_yaml(out_dir: Path, name: str, mc: bool, kwc: bool) -> Path:
    cfg = yaml.safe_load(DETECTION_PATTERNS_PATH.read_text(encoding="utf-8"))
    pats = cfg["patterns"]
    if mc:
        p = pats["titles"]["patterns"][0]
        assert TITLE_TOKEN in p["pattern"]
        p["pattern"] = p["pattern"].replace(TITLE_TOKEN, MC_TOKEN)
    if kwc:
        p2 = pats["organizations"]["patterns"][1]["pattern"]
        head = "[ \\t\\u00A0\\u202F]+("
        assert head in p2, p2[:200]
        conn = "(?:de|du|des|la|le|et|&)"
        p2 = p2.replace(
            head,
            f"[ \\t\\u00A0\\u202F]+((?:{conn}[ \\t\\u00A0\\u202F]){{0,2}}(?:[dl]['’])?",
            1,
        )
        pats["organizations"]["patterns"][1]["pattern"] = p2
    path = out_dir / f"patterns_{name}.yaml"
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: C901
    if len(sys.argv) != 3:
        sys.exit(
            "usage: accuracy_particles_noise_dryrun.py <baseline_dump.json> <out_dir>"
        )
    dump_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    if REPO_ROOT in out_dir.parents or out_dir == REPO_ROOT:
        sys.exit("refusing to write inside the repository")
    out_dir.mkdir(parents=True, exist_ok=True)
    dump = json.loads(dump_path.read_text(encoding="utf-8"))

    det = HybridDetector()
    det.load_model("fr_core_news_lg")
    sep = HSPACE + "+"
    matchers = {
        "base": ro.VariantMatcher(str(DETECTION_PATTERNS_PATH), sep=sep),
        "mc": ro.VariantMatcher(str(write_yaml(out_dir, "mc", True, False)), sep=sep),
        "kwc": ro.VariantMatcher(str(write_yaml(out_dir, "kwc", False, True)), sep=sep),
        "mc_kwc": ro.VariantMatcher(
            str(write_yaml(out_dir, "mc_kwc", True, True)), sep=sep
        ),
    }
    for m in matchers.values():
        m.load_patterns()
    CUR["names"] = matchers["base"].name_dictionary
    CUR["det"] = det

    docs = _load_corpus_documents()
    spacy_pre: dict[str, list[DetectedEntity]] = {}
    regex_pre: dict[str, dict[str, list[DetectedEntity]]] = collections.defaultdict(
        dict
    )
    sdocs: dict[str, Any] = {}
    for name, text, _gt in docs:
        ents = det.spacy_detector.detect_entities(text)
        for e in ents:
            e.source = "spacy"
        spacy_pre[name] = det._trim_entity_boundaries(ents)
        sdocs[name] = det.spacy_detector.last_doc
        for key, m in matchers.items():
            rx = m.match_entities(text, spacy_doc=sdocs[name])
            for e in rx:
                e.source = "regex"
            regex_pre[name][key] = rx

    def compose(
        rx: str = "base",
        b: dict[str, Any] | None = None,
        c: dict[str, Any] | None = None,
        c2off: bool = False,
        wjp: bool = False,
        count_c2: bool = False,
        late_role: dict[str, Any] | None = None,
    ) -> dict[str, list[DetectedEntity]]:
        b = b or {}
        c = c or {}
        if c:
            HybridDetector._filter_org_roles = lambda self, ents, text=None: _ORIG_ROLES(  # type: ignore[method-assign]
                self, filter_location_noise(ents, text, c), text
            )
        if c2off:
            HybridDetector._resolve_same_type_pair_base = classmethod(_c2off_base)  # type: ignore[method-assign,assignment]
        elif count_c2:
            HybridDetector._resolve_same_type_pair_base = classmethod(_c2_counting_base)  # type: ignore[method-assign,assignment]
        if wjp:
            hd._wrap_re = _wjp_wrap_re  # type: ignore[assignment]
        HybridDetector._join_wrapped_names = staticmethod(_counting_join)  # type: ignore[method-assign,assignment]
        try:
            out = {}
            CUR["late_role"] = None
            for name, text, _ in docs:
                CUR["doc"], CUR["sdoc"], CUR["guards"] = name, sdocs[name], []
                sp = copy.deepcopy(spacy_pre[name])
                rxl = copy.deepcopy(regex_pre[name][rx])
                if b:
                    blockers = [
                        (e.start_pos, e.end_pos)
                        for e in sp + rxl
                        if e.entity_type in ("ORG", "LOCATION")
                    ]
                    sp = fix_person_boundaries(sp, text, blockers, b)
                    rxl = fix_person_boundaries(rxl, text, blockers, b)
                CUR["late_role"] = None
                merged = det._merge_entities(
                    copy.deepcopy(sp), copy.deepcopy(rxl), text
                )
                # guarded trims (AC9 dash, punct2 guarded): every capitalised
                # word beyond the cut must be covered by a kept detection
                guards = list(CUR["guards"])
                failing = [
                    g
                    for g in guards
                    if not all(
                        any(k.start_pos <= ws and we <= k.end_pos for k in merged)
                        for ws, we in g[4]
                    )
                ]
                if failing:
                    revert = {(g[1], g[2], g[3].start_pos) for g in failing}

                    def undo(lst: list[DetectedEntity]) -> list[DetectedEntity]:
                        res = []
                        for e in lst:
                            hit = [
                                g
                                for g in failing
                                if (e.start_pos, e.end_pos, g[3].start_pos) in revert
                                and e.entity_type == "PERSON"
                                and e.start_pos == g[1]
                                and e.end_pos == g[2]
                            ]
                            res.append(hit[0][3] if hit else e)
                        return res

                    for g in failing:
                        FIRES.append(
                            ("guard_refused", name, g[3].source, g[3].text, "")
                        )
                    merged = det._merge_entities(undo(sp), undo(rxl), text)
                if late_role:
                    # re-merge with the late trims on (guards checked inside)
                    CUR["late_role"] = late_role
                    merged = (
                        det._merge_entities(copy.deepcopy(sp), copy.deepcopy(rxl), text)
                        if not failing
                        else det._merge_entities(undo(sp), undo(rxl), text)
                    )
                    CUR["late_role"] = None
                out[name] = merged
            return out
        finally:
            HybridDetector._filter_org_roles = _ORIG_ROLES  # type: ignore[method-assign]
            HybridDetector._resolve_same_type_pair_base = classmethod(_ORIG_BASE)  # type: ignore[method-assign,assignment]
            hd._wrap_re = _ORIG_WRAP_RE  # type: ignore[assignment]
            HybridDetector._join_wrapped_names = staticmethod(_ORIG_JOIN)  # type: ignore[method-assign,assignment]

    log: list[str] = []

    # --- 1.2 re-merge reproduces the dump ---------------------------------
    C2_FIRES.clear()
    base_dets = compose(count_c2=True)
    c2_list = sorted(C2_FIRES)
    mism = 0
    for name in base_dets:
        got = sorted(
            (e.text, e.entity_type, e.start_pos, e.end_pos, e.source, e.is_ambiguous)
            for e in base_dets[name]
        )
        want = sorted(
            (d["text"], d["type"], d["start"], d["end"], d["source"], d["is_ambiguous"])
            for d in dump[name]
        )
        if got != want:
            mism += 1
            log.append(f"  MISMATCH {name}: {set(got) ^ set(want)}")
    n_det = sum(len(v) for v in base_dets.values())
    log.insert(0, f"# 1.2 re-merge: {n_det} detections, {mism} documents differ")
    base = ro.Run("baseline (re-merged)", base_dets)
    btot, base_pairs = ro.tally(docs, base_dets)
    log.append(f"  baseline tally: {btot}")
    FIRES.clear()

    texts = {n: t for n, t, _ in docs}

    # --- 1.3 F6 -------------------------------------------------------------
    log.append("\n# 1.3 F6: LOCATION FP classes (baseline)")
    f6: collections.Counter[str] = collections.Counter()
    f6_rows: list[str] = []
    for name, text, gt in docs:
        _, fp, _ = match_entities(base_dets[name], gt)
        org_texts = {g.text for g in gt if g.entity_type == "ORG"}
        for d in fp:
            if d.entity_type != "LOCATION":
                continue
            n = norm_loc(d.text)
            ov = [g for g in gt if g.start_pos < d.end_pos and d.start_pos < g.end_pos]
            if n == "":
                cls = "(d) fragment"
            elif n.casefold() in Q14_ALWAYS_LOCATION:
                cls = "(f) US/UK-type"
            elif (
                any(
                    g.entity_type == "ORG"
                    and g.start_pos <= d.start_pos + 3
                    and d.end_pos <= g.end_pos + 1
                    for g in ov
                )
                or n in org_texts
            ):
                cls = "(c) organisation name"
            elif any(g.entity_type == "LOCATION" for g in ov):
                cls = "(e) boundary (overlaps a LOCATION annotation)"
            elif d.source == "regex" and re.match(
                r"(?:à|en|dans|près de|ville de)\s", d.text
            ):
                cls = "(g) other: location indicator before a non-place"
            elif _is_allcaps(n) and n.replace(" ", "").isalpha():
                cls = "(a) all-caps word"
            elif n.casefold() in GEO:
                cls = "(g) other: dictionary place not annotated"
            elif len(n.split()) == 1 and not re.search(r"\d", n):
                cls = "(b) common noun / jargon (single word)"
            else:
                cls = "(g) other"
            f6[cls] += 1
            ann = [(g.entity_type, g.text) for g in ov]
            f6_rows.append(
                f"    {cls} | [{name}] {d.text!r} @{d.start_pos} src={d.source} ann={ann}"
            )
    for k, v in sorted(f6.items()):
        log.append(f"  {v:4d}  {k}")
    log.extend(sorted(f6_rows))

    log.append("\n# 1.3b LOCATION TPs that are all-caps or absent from the dictionary")
    for name, text, gt in docs:
        tp, _, _ = match_entities(base_dets[name], gt)
        for d, g in tp:
            if d.entity_type != "LOCATION":
                continue
            n = norm_loc(d.text)
            flags = []
            if _is_allcaps(n):
                flags.append("all-caps")
            geo = matchers["base"].geography_dictionary
            if geo is not None and not geo.is_location(n):
                flags.append("absent (case-sensitive)")
            if n.casefold() not in GEO:
                flags.append("absent (case-folded)")
            if flags:
                log.append(f"    [{name}] {d.text!r} @{d.start_pos} {flags}")
    log.append("\n# 1.3c ORG annotations covered by a LOCATION span only")
    for name, text, gt in docs:
        for g in gt:
            if g.entity_type != "ORG":
                continue
            cov = [
                k
                for k in base_dets[name]
                if k.start_pos <= g.start_pos and g.end_pos <= k.end_pos
            ]
            if cov and all(k.entity_type == "LOCATION" for k in cov):
                log.append(
                    f"    [{name}] ORG {g.text!r} @{g.start_pos} <- {[ro.fmt(k) for k in cov]}"
                )

    # --- 1.4 F7 -------------------------------------------------------------
    log.append("\n# 1.4 F7: PERSON FN and overlapping FP by pattern (baseline)")
    f7: collections.Counter[str] = collections.Counter()
    f7_rows: list[str] = []
    part_words = set(PARTICLES_LOWER + PARTICLES_CAP + PARTICLES_ALLCAPS) | {"d"}

    def pattern_of(gtext: str, dtext: str | None) -> str:
        if dtext is not None and re.search(f",{HSPACE}+(?:{ROLE_RE})", dtext):
            return "trailing ', Role'"
        if dtext is not None and (
            re.search(f"{HSPACE}+-{HSPACE}+", dtext)
            or re.search(r"[):]", dtext)
            or re.search(
                f"{HSPACE}(?:{_alts(sorted(load_org_role_filter().acronyms))})$", dtext
            )
        ):
            return "trailing role/punct without comma"
        if dtext is not None and hd._LINE_BREAK_RE.search(dtext):
            return "line break"
        toks = re.split(f"{HSPACE}+|['’]", gtext)
        if any(t in part_words for t in toks[1:-1]) or re.search(r"\b[dD]['’]", gtext):
            return "particle (P4)"
        if re.search(f"\\bMa?c[{_U}]", gtext):
            return "Mc/Mac (P5)"
        if re.search(f"[{_L}][{_U}]|['’]", gtext):
            return "inner capital / apostrophe (Q11)"
        if any(len(t) > 1 and t.isalpha() and t.isupper() for t in gtext.split()):
            return "all-caps surname"
        if (
            dtext is not None
            and re.search(
                f"{HSPACE}(?:de|du|des|d['’])",
                dtext[len(dtext) - len(dtext.lstrip()) :],
            )
            and not re.search(f"{HSPACE}(?:de|du|des|d['’])", gtext)
        ):
            return "de/d' + ORG tail (span too long, P4 negative)"
        return "other"

    for name, text, gt in docs:
        tp, fp, fn = match_entities(base_dets[name], gt)
        for g in fn:
            if g.entity_type != "PERSON":
                continue
            ov = [
                k
                for k in base_dets[name]
                if k.start_pos < g.end_pos and g.start_pos < k.end_pos
            ]
            same = [k for k in ov if k.entity_type == "PERSON"]
            dtext = same[0].text if same else None
            p = pattern_of(g.text, dtext)
            if (
                p == "other"
                and same
                and any(
                    " ".join(strip_french_titles(k.text).split()).casefold()
                    == g.text.casefold()
                    for k in same
                )
            ):
                p = "scorer re-pairing (an exact span is at the position)"
            elif p == "other" and not ov:
                p = "no detection (bare first name / missed)"
            src = (
                same[0].source
                if same
                else ("other type: " + ov[0].entity_type if ov else "none")
            )
            f7[f"FN | {p} | {src}"] += 1
            f7_rows.append(
                f"    FN {p} | [{name}] {g.text!r} @{g.start_pos} det={[ro.fmt(k) for k in ov]}"
            )
        for d in fp:
            if d.entity_type != "PERSON":
                continue
            ov = [
                g
                for g in gt
                if g.entity_type == "PERSON"
                and g.start_pos < d.end_pos
                and d.start_pos < g.end_pos
            ]
            if not ov:
                continue
            p = pattern_of(ov[0].text, d.text)
            f7[f"FP | {p} | {d.source}"] += 1
            f7_rows.append(
                f"    FP {p} | [{name}] {ro.fmt(d)} src={d.source} ann={[g.text for g in ov]}"
            )
    for k, v in sorted(f7.items()):
        log.append(f"  {v:4d}  {k}")
    log.extend(f7_rows)
    log.append(
        "\n# 1.4b all-caps surname tokens in PERSON annotations (particle in front)"
    )
    for name, text, gt in docs:
        for g in gt:
            if g.entity_type != "PERSON":
                continue
            toks = g.text.split()
            for i, t in enumerate(toks):
                if (
                    len(t) > 1
                    and t.replace("-", "").isalpha()
                    and t.replace("-", "").isupper()
                ):
                    prev = toks[i - 1] if i else ""
                    kind = (
                        "after lower-case de/du/des/d'"
                        if prev in LOWER_DE or prev.startswith("d'")
                        else (
                            "after capitalised/all-caps particle"
                            if prev in PARTICLES_CAP + PARTICLES_ALLCAPS
                            else "no particle"
                        )
                    )
                    log.append(f"    [{name}] {g.text!r}: {t!r} {kind}")

    # --- 1.5 trailing-role inventory ---------------------------------------
    log.append("\n# 1.5 PERSON spans ending in a role / punctuation (baseline)")
    acr_alt = _alts(sorted(load_org_role_filter().acronyms))
    for name in base_dets:
        for d in base_dets[name]:
            if d.entity_type != "PERSON":
                continue
            t = d.text
            kinds = []
            if re.search(f",{HSPACE}+(?:{ROLE_RE})", t):
                kinds.append("', role'")
            if re.search(f"{HSPACE}-{HSPACE}", t):
                kinds.append("' - …'")
            if re.search(f"{HSPACE}(?:{acr_alt})$", t):
                kinds.append("role acronym")
            if re.search(r"[):,;]", t):
                kinds.append("punctuation")
            if kinds:
                log.append(f"    [{name}] {ro.fmt(d)} src={d.source} {kinds}")

    log.append(f"\n# 1.7a C2 fires on the baseline: {len(c2_list)}")
    for doc, s, e_, cut in c2_list:
        t = texts[doc]
        log.append(
            f"    [{doc}] outer {t[s:e_]!r} @{s} kept {t[s:cut]!r} dropped tail {t[cut:e_]!r}"
        )

    # --- 1.6 / 1.7 / 1.8 dry-runs -------------------------------------------
    b_part = {"part": True}
    b_part_nocaps = {"part": True, "allcaps": False}
    b_mc = {"mc": True}
    b_role = {"role": True}
    b_dash = {"role": True, "dash": True}
    b_acr = {"role": True, "acr": True}
    b_punct = {"role": True, "punct": True}
    b_all = {
        "part": True,
        "mc": True,
        "role": True,
        "dash": True,
        "acr": True,
        "punct": True,
    }
    c_stop = {"stop": True}
    c_frag = {"frag": True}
    c_ac3d = {"ac3": "drop"}
    c_ac3r = {"ac3": "retype"}
    c_ac3ii = {"ac3ii": True}
    c_pos = {"pos": True}
    c_def = {"stop": True, "frag": True, "ac3": "drop", "ac3ii": True}
    c_ret = {"stop": True, "frag": True, "ac3": "retype", "ac3ii": True}
    variants: list[tuple[str, dict[str, Any]]] = [
        ("R-PART (particles, all-caps after capitalised particle)", dict(b=b_part)),
        ("R-PART, no all-caps surnames", dict(b=b_part_nocaps)),
        ("R-MC (extension + titles token)", dict(b=b_mc, rx="mc")),
        ("R-ROLE comma (AC6)", dict(b=b_role)),
        ("R-ROLE + ' - Lead <Org>' guarded (AC9)", dict(b=b_dash)),
        ("R-ROLE + role acronym ('<Name> DRH')", dict(b=b_acr)),
        ("R-ROLE + glued punctuation ('<Name>):')", dict(b=b_punct)),
        (
            "Refinement R-PUNCT2 guarded (cut at glued ')' / ':')",
            dict(b={"role": True, "punct2": "guarded"}),
        ),
        (
            "Refinement R-PUNCT2 unguarded",
            dict(b={"role": True, "punct2": "unguarded"}),
        ),
        (
            "Slice B composed (PART + MC + ROLE + dash + acronym + punct)",
            dict(b=b_all, rx="mc"),
        ),
        (
            "Slice B composed, no all-caps surnames",
            dict(b={**b_all, "allcaps": False}, rx="mc"),
        ),
        (
            "Slice B composed + R-PUNCT2 guarded",
            dict(b={**b_all, "punct2": "guarded"}, rx="mc"),
        ),
        (
            "Refinement R-ROLE-LATE (role/punct trims also after W-JOIN) + Slice B",
            dict(
                b=b_all,
                rx="mc",
                late_role={"role": True, "dash": True, "acr": True, "punct": True},
            ),
        ),
        ("C2 off alone", dict(c2off=True)),
        ("C2 off + Slice B", dict(b=b_all, rx="mc", c2off=True)),
        ("R-LOC stoplist (AC1 + AC2)", dict(c=c_stop)),
        ("R-LOC fragment", dict(c=c_frag)),
        ("R-LOC AC3 drop-(i)", dict(c=c_ac3d)),
        ("R-LOC AC3 retype-(i)", dict(c=c_ac3r)),
        ("R-LOC AC3 (ii) legal-form tail", dict(c=c_ac3ii)),
        ("Refinement R-LOC POS lexical check", dict(c=c_pos)),
        ("Slice C composed, drop (stop + frag + drop-(i) + (ii))", dict(c=c_def)),
        ("Slice C composed, retype-(i)", dict(c=c_ret)),
        ("Slice C composed, drop + POS", dict(c={**c_def, "pos": True})),
        ("ALL: B + C drop", dict(b=b_all, rx="mc", c=c_def)),
        (
            "RECOMMENDED: B + C (stop + frag + (ii)), C2 kept",
            dict(b=b_all, rx="mc", c={"stop": True, "frag": True, "ac3ii": True}),
        ),
        (
            "RECOMMENDED + R-ROLE-LATE",
            dict(
                b=b_all,
                rx="mc",
                c={"stop": True, "frag": True, "ac3ii": True},
                late_role={"role": True, "dash": True, "acr": True, "punct": True},
            ),
        ),
        (
            "FINAL Slice B (decided): B + R-ROLE-LATE + R-WJP, C2 kept",
            dict(
                b=b_all,
                rx="mc",
                late_role={"role": True, "dash": True, "acr": True, "punct": True},
                wjp=True,
            ),
        ),
        (
            "FINAL (decided): Slice B + C (stoplist + fragment), C2 kept",
            dict(
                b=b_all,
                rx="mc",
                c={"stop": True, "frag": True},
                late_role={"role": True, "dash": True, "acr": True, "punct": True},
                wjp=True,
            ),
        ),
        ("ALL: B + C retype-(i)", dict(b=b_all, rx="mc", c=c_ret)),
        ("ALL: B + C retype-(i) + C2 off", dict(b=b_all, rx="mc", c=c_ret, c2off=True)),
        ("ALL: B + C drop + C2 off", dict(b=b_all, rx="mc", c=c_def, c2off=True)),
        ("R-KWC alone", dict(rx="kwc")),
        ("ALL (retype-(i)) + R-KWC", dict(b=b_all, rx="mc_kwc", c=c_ret)),
        ("R-WJP alone", dict(wjp=True)),
        ("ALL (retype-(i)) + R-WJP", dict(b=b_all, rx="mc", c=c_ret, wjp=True)),
    ]
    summary = []
    for label, kw in variants:
        FIRES.clear()
        run = ro.Run(label, compose(**kw))
        res = ro.report(docs, base, run, base_pairs, log)
        fires = collections.Counter(f[0] for f in FIRES)
        res["fires"] = dict(fires)
        log.append(f"  rule firings: {dict(sorted(fires.items()))}")
        for f in FIRES:
            log.append(f"    FIRE {f[0]} [{f[1]}] src={f[2]} {f[3]!r} -> {f[4]!r}")
        summary.append(res)

    # final detection sets, for the local dump check of each slice
    for tag, kw in (
        (
            "final_b",
            dict(
                b=b_all,
                rx="mc",
                late_role={"role": True, "dash": True, "acr": True, "punct": True},
                wjp=True,
            ),
        ),
        (
            "final_all",
            dict(
                b=b_all,
                rx="mc",
                c={"stop": True, "frag": True},
                late_role={"role": True, "dash": True, "acr": True, "punct": True},
                wjp=True,
            ),
        ),
    ):
        dets = compose(**kw)  # type: ignore[arg-type]
        (out_dir / f"{tag}_dets.json").write_text(
            json.dumps(
                {
                    n: [
                        {**ro.to_json(e), "is_ambiguous": e.is_ambiguous}
                        for e in sorted(v, key=lambda x: (x.start_pos, x.end_pos))
                    ]
                    for n, v in dets.items()
                },
                ensure_ascii=False,
                indent=0,
            ),
            encoding="utf-8",
        )

    # --- summary -------------------------------------------------------------
    print(log[0])
    print(f"baseline: {btot}")
    print(f"C2 fires on baseline: {len(c2_list)}")
    print(
        "\n| Rule / composition | PERSON dTP/dFP/dFN | LOCATION | ORG | Overall P/R/F1 | L2 | L2b | L1 chars (in GT) / spans | firings |"
    )
    for s in summary:
        d = s["delta"]
        p, r, f = ro.prf(*s["tot"]["Overall"])
        cells = " | ".join(f"{d[t][0]:+d}/{d[t][1]:+d}/{d[t][2]:+d}" for t in TYPES)
        print(
            f"| {s['label']} | {cells} | {p:.4f}/{r:.4f}/{f:.4f} | {s['l2']} | "
            f"{s['l2b']} | {s['l1_chars']} ({s['l1_in_gt']}) / {s['l1_spans']} | {s['fires']} |"
        )
    report_path = out_dir / "dryrun_report.txt"
    report_path.write_text("\n".join(log), encoding="utf-8")
    print(f"\nfull report -> {report_path}")


if __name__ == "__main__":
    main()
