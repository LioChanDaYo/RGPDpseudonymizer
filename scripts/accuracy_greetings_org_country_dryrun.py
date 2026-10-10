"""Re-measure and dry-run the Story 10.4 rules (greetings, org + place,
carried coverage losses, defined aliases, candidate items).

Story 10.4, Tasks 1.1-1.9. Main corpus only: calls ``_load_corpus_documents()``
and never the held-out loader. Imports ``tests.accuracy.conftest`` and
``tests.accuracy.bootstrap`` read-only (G4 scope). No product code is changed:
every candidate rule is patched in this script only, on one
``HybridDetector`` instance, and every document goes through script copies of
``detect_entities`` and ``_merge_entities`` whose hooks are off by default
(both ``_fix_person_boundaries`` calls, the guarded re-merge, the 10.3c exact
match, R-SPLIT late, W-JOIN and R-ROLE-LATE all run as in the product).

Rules (Dev Notes "Candidate Rules" and "Candidate Items"):

- Slice S: R-SAL-SPLIT, R-SAL-BARE (shape 1 / shape 2), and the information
  rows R-SAL-ADDR and R-SIG;
- Slice O: R-OPC (countries and regions, cities, the five abbreviations; with
  or without the nested LOCATION);
- Slice A: R-ACR (as specified, and refined: no role of ``match_org_role``),
  R-FN-DOC and the alternatives R-FN-SUBJ, R-FN-SUBJ-PROPN, R-FN-LINE, plus
  their fires on the AC3 sentences (real spaCy parse);
- Slice D: R-DEF as specified, plus two variants (clause alone; alias tied by
  name to an ORG detection of the document);
- Slice K: R-NEST; R-KWC and the four REQ-001 parts (R-ORG-SHAPE).

The ``base`` run must reproduce the baseline dump byte for byte
(``scripts/accuracy_dump_detections.py``); otherwise the script stops.

Reuses the 10.3a helpers of ``scripts/accuracy_runon_dryrun.py`` (net
per-type delta, lost/gained TP classification, coverage levels 1/2/2b), as
``scripts/accuracy_type_aware_match_dryrun.py`` (10.3c) does.

The counts printed here are local attribution numbers (Product Constraint 6):
they belong in the story only, never in the QA report, CHANGELOG or PR body.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_greetings_org_country_dryrun.py <baseline_dump.json> <out_dir>
"""

from __future__ import annotations

import collections
import dataclasses
import json
import re
import sys
import time
import types
import unicodedata
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
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector  # noqa: E402
from gdpr_pseudonymizer.nlp.regex_matcher import HSPACE, RegexMatcher  # noqa: E402
from gdpr_pseudonymizer.resources import (  # noqa: E402
    FRENCH_GEOGRAPHY_PATH,
    ORG_ROLE_FILTER_PATH,
)
from gdpr_pseudonymizer.utils.french_patterns import (  # noqa: E402
    strip_french_titles,
)
from tests.accuracy import bootstrap  # noqa: E402
from tests.accuracy.conftest import (  # noqa: E402
    _load_corpus_documents,
    _match_key,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")
_U = "A-ZÀ-ÖØ-ÞĀ-ſ"
_L = "a-zß-öø-ÿĀ-ſ"
HS_CHARS = frozenset(" \t  ")
LINE_BREAK_RE = re.compile("[\n\r\v\f\x85  ]")
# A name token: capitalised, hyphen allowed ("known first name", AC precisions)
NAME_TOK = f"[{_U}][{_U}{_L}]*(?:-[{_U}][{_U}{_L}]*)*"
WORD_RE = re.compile(f"(?<![\\w-]){NAME_TOK}(?![\\w-])")

# ---------------------------------------------------------------------------
# Candidate resources (drafted here; frozen at Task 2 into the product files)
# ---------------------------------------------------------------------------

# salutations.yaml (DRAFT): every term occurs in the main-corpus text
OPENERS: tuple[tuple[str, str], ...] = (
    ("Bonjour", "greeting"),
    ("Merci", "thanks"),
    ("Bonne initiative", "compliment"),
    ("Félicitations", "compliment"),
)
CLOSINGS: tuple[str, ...] = ("Cordialement",)  # R-SIG only (information row)
MAX_LINE_LENGTH = 40  # shape 1 only; reach also measured at 60 and 80

# place_abbreviations.yaml (DRAFT): GUIDELINES Q14 / A5
PLACE_ABBREVIATIONS: tuple[str, ...] = ("UK", "US", "USA", "UE", "EU")
# vp_regions entries that are not places on their own (AC precisions, AC4)
VP_NOT_PLACES = frozenset(
    {
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
    }
)
ORG_CONNECTORS = frozenset({"de", "du", "des", "la", "le", "et", "&"})
ARTICLES = frozenset({"le", "la", "les", "l'", "l’", "un", "une"})

DEFAULT_CFG: dict[str, Any] = {
    "split": False,  # R-SAL-SPLIT
    "bare": None,  # R-SAL-BARE: None | "shape1" | "shape2" | "both"
    "maxlen": MAX_LINE_LENGTH,
    "addr": False,  # R-SAL-ADDR (information)
    "sig": False,  # R-SIG (information)
    "opc": None,  # R-OPC: None | frozenset of {"cr", "city", "abbr"}
    "opc_nested": True,
    "acr": False,  # R-ACR
    "acr_roles": "match_org_role",  # "acronyms" (as specified) | "match_org_role"
    "acr_min": 2,  # shortest acronym (letters)
    "def": None,  # R-DEF: None | "spec" | "any" | "name"
    "fn": None,  # None | "doc" | "subj" | "subj_propn" | "line"
    "late_dedup": True,
    "nest": False,  # R-NEST
    "org_variant": None,  # R-KWC / REQ-001 parts
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


def fire(rule: str, start: int, end: int, etype: str, **extra: Any) -> None:
    CUR["fires"].append(
        {
            "rule": rule,
            "merge": CUR["merge_no"],
            "start": start,
            "end": end,
            "type": etype,
            "text": CUR["text"][start:end],
            **extra,
        }
    )


def fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
    ).casefold()


# ---------------------------------------------------------------------------
# Salutation lines (AC precisions, "Salutation line")
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SalLine:
    start: int
    end: int
    shape: int  # 1 or 2
    kind: str  # "names" (shape 1) or the opener kind
    names: tuple[tuple[int, int], ...]
    comma_after: bool  # the names end with a comma
    length: int  # stripped line length


def known(det: HybridDetector, word: str) -> bool:
    return bool(word) and word[0].isupper() and det._known_first_name(word)


_SHAPE1 = re.compile(
    f"({NAME_TOK})(?:{HSPACE}*,{HSPACE}*({NAME_TOK}))?{HSPACE}*,{HSPACE}*$"
)


def _opener_re() -> re.Pattern[str]:
    alts = "|".join(
        f"(?P<o{i}>{re.escape(t).replace(chr(92) + ' ', HSPACE + '+')})"
        for i, (t, _k) in enumerate(OPENERS)
    )
    return re.compile(f"(?:{alts}){HSPACE}+")


_OPENER = _opener_re()
_TWO = re.compile(
    f"({NAME_TOK}){HSPACE}*,{HSPACE}*({NAME_TOK})(?=[,.!]|{HSPACE}*$)", re.M
)
_ONE = re.compile(f"({NAME_TOK})(?=[,.!]|{HSPACE}*$)", re.M)


def lines_of(text: str) -> list[tuple[int, int]]:
    out, pos = [], 0
    for m in LINE_BREAK_RE.finditer(text):
        out.append((pos, m.start()))
        pos = m.end()
    out.append((pos, len(text)))
    return out


def salutation_lines(
    det: HybridDetector, text: str, maxlen: int | None
) -> list[SalLine]:
    found: list[SalLine] = []
    for ls, le in lines_of(text):
        line = text[ls:le]
        lead = len(line) - len(line.lstrip(" \t  "))
        body_start = ls + lead
        stripped = line.strip(" \t  ")
        m = _SHAPE1.fullmatch(text, body_start, le)
        if m:
            parts = [(m.start(g), m.end(g)) for g in (1, 2) if m.group(g)]
            if all(known(det, text[s:e]) for s, e in parts):
                if maxlen is None or len(stripped) <= maxlen:
                    found.append(
                        SalLine(ls, le, 1, "names", tuple(parts), True, len(stripped))
                    )
                continue
        o = _OPENER.match(text, body_start, le)
        if not o:
            continue
        kind = OPENERS[int(next(k for k, v in o.groupdict().items() if v)[1:])][1]
        pos = o.end()
        two = _TWO.match(text, pos, le)
        if two and known(det, two.group(1)) and known(det, two.group(2)):
            nxt = text[two.end() : two.end() + 1]
            found.append(
                SalLine(
                    ls,
                    le,
                    2,
                    kind,
                    ((two.start(1), two.end(1)), (two.start(2), two.end(2))),
                    nxt == ",",
                    len(stripped),
                )
            )
            continue
        one = _ONE.match(text, pos, le)
        if one and known(det, one.group(1)):
            nxt = text[one.end() : one.end() + 1]
            found.append(
                SalLine(
                    ls,
                    le,
                    2,
                    kind,
                    ((one.start(1), one.end(1)),),
                    nxt == ",",
                    len(stripped),
                )
            )
    return found


def on_salutation_line(lines: list[SalLine], start: int, end: int) -> bool:
    return any(s.start <= start and end <= s.end for s in lines)


# ---------------------------------------------------------------------------
# Slice S rules (pre-merge)
# ---------------------------------------------------------------------------


def _covered(ents: list[DetectedEntity], s: int, e: int, etype: str | None) -> bool:
    return any(
        x.start_pos <= s
        and e <= x.end_pos
        and (etype is None or x.entity_type == etype)
        for x in ents
    )


def sal_bare(
    det: HybridDetector,
    text: str,
    spacy_e: list[DetectedEntity],
    regex_e: list[DetectedEntity],
) -> list[DetectedEntity]:
    shapes = {"shape1": {1}, "shape2": {2}, "both": {1, 2}}[CFG["bare"]]
    added: list[DetectedEntity] = []
    for line in CUR["sal"]:
        if line.shape not in shapes:
            continue
        for s, e in line.names:
            if _covered(spacy_e + regex_e + added, s, e, "PERSON"):
                continue
            added.append(
                DetectedEntity(
                    text=text[s:e],
                    entity_type="PERSON",
                    start_pos=s,
                    end_pos=e,
                    confidence=0.80,
                    source="regex",
                )
            )
            fire(
                "R-SAL-BARE",
                s,
                e,
                "PERSON",
                shape=line.shape,
                kind=line.kind,
            )
    return added


_ADDR = re.compile(f"({NAME_TOK}),{HSPACE}+[{_L}]")


def sal_addr_sig(
    det: HybridDetector,
    text: str,
    spacy_e: list[DetectedEntity],
    regex_e: list[DetectedEntity],
) -> list[DetectedEntity]:
    added: list[DetectedEntity] = []
    lines = lines_of(text)
    for i, (ls, le) in enumerate(lines):
        line = text[ls:le]
        lead = len(line) - len(line.lstrip(" \t  "))
        body = ls + lead
        cands: list[tuple[str, int, int]] = []
        if CFG["addr"]:
            m = _ADDR.match(text, body, le)
            if m and known(det, m.group(1)):
                cands.append(("R-SAL-ADDR", m.start(1), m.end(1)))
        if CFG["sig"]:
            stripped = line.strip(" \t  ")
            if re.fullmatch(NAME_TOK, stripped) and known(det, stripped):
                prev = [text[a:b].strip(" \t  ") for a, b in lines[max(0, i - 2) : i]]
                # directly after a closing line, at most one blank line between
                ok = bool(prev) and (
                    any(prev[-1].startswith(c) for c in CLOSINGS)
                    or (
                        len(prev) == 2
                        and prev[-1] == ""
                        and any(prev[-2].startswith(c) for c in CLOSINGS)
                    )
                )
                if ok:
                    cands.append(("R-SIG", body, body + len(stripped)))
        for rule, s, e in cands:
            if _covered(spacy_e + regex_e + added, s, e, "PERSON"):
                continue
            added.append(
                DetectedEntity(
                    text=text[s:e],
                    entity_type="PERSON",
                    start_pos=s,
                    end_pos=e,
                    confidence=0.80,
                    source="regex",
                )
            )
            fire(rule, s, e, "PERSON")
    return added


_XY = re.compile(f"({NAME_TOK}){HSPACE}*,{HSPACE}*({NAME_TOK})")


def sal_split(
    det: HybridDetector,
    text: str,
    ents: list[DetectedEntity],
    guards: list[Any],
) -> tuple[list[DetectedEntity], list[Any]]:
    out: list[DetectedEntity] = []
    shift: dict[int, int] = {}
    for i, ent in enumerate(ents):
        shift[i] = len(out)
        if ent.entity_type != "PERSON":
            out.append(ent)
            continue
        m = _XY.fullmatch(text, ent.start_pos, ent.end_pos)
        line = next(
            (
                ln
                for ln in CUR["sal"]
                if len(ln.names) == 2
                and ln.comma_after
                and ln.names[0][0] == ent.start_pos
                and ln.names[1][1] == ent.end_pos
            ),
            None,
        )
        if (
            m is None
            or line is None
            or not known(det, m.group(1))
            or not known(det, m.group(2))
        ):
            out.append(ent)
            continue
        for g in (1, 2):
            out.append(
                dataclasses.replace(
                    ent,
                    text=m.group(g),
                    start_pos=m.start(g),
                    end_pos=m.end(g),
                    is_ambiguous=False,
                )
            )
        fire(
            "R-SAL-SPLIT",
            ent.start_pos,
            ent.end_pos,
            "PERSON",
            source=ent.source,
            pieces=[(m.start(1), m.end(1)), (m.start(2), m.end(2))],
        )
    new_guards = [dataclasses.replace(g, index=shift[g.index]) for g in guards]
    return out, new_guards


# ---------------------------------------------------------------------------
# Slice O rule (in the merge, after _filter_org_roles)
# ---------------------------------------------------------------------------


def place_phrases(sources: frozenset[str]) -> list[tuple[str, str]]:
    with open(FRENCH_GEOGRAPHY_PATH, encoding="utf-8") as f:
        geo = json.load(f)
    with open(ORG_ROLE_FILTER_PATH, encoding="utf-8") as f:
        role = yaml.safe_load(f)
    out: dict[str, str] = {}
    if "cr" in sources:
        for p in list(geo["countries_and_international"]) + list(geo["regions"]):
            out.setdefault(p, "country/region")
        for e in role["vp_regions"]:
            if e["term"] not in VP_NOT_PLACES:
                out.setdefault(e["term"], "country/region")
    if "city" in sources:
        for p in geo["cities"]:
            out.setdefault(p, "city")
    if "abbr" in sources:
        for p in PLACE_ABBREVIATIONS:
            out.setdefault(p, "abbr")
    return sorted(out.items(), key=lambda kv: len(kv[0]), reverse=True)


def _place_at(text: str, pos: int, phrases: list[tuple[str, str]]) -> Any:
    if pos >= len(text) or not text[pos].isupper():
        return None
    for phrase, src in phrases:
        end = pos + len(phrase)
        cand = text[pos:end]
        same = cand == phrase if src == "abbr" else cand.casefold() == phrase.casefold()
        if not same:
            continue
        if end < len(text) and text[end].isalpha():
            continue
        return phrase, src, end
    return None


def org_place_merge(
    det: HybridDetector, merged: list[DetectedEntity], text: str | None
) -> list[DetectedEntity]:
    if not CFG["opc"] or text is None:
        return merged
    phrases = CUR["phrases"]
    locs = {(e.start_pos, e.end_pos) for e in merged if e.entity_type == "LOCATION"}
    out: list[DetectedEntity] = []
    emitted: list[DetectedEntity] = []
    for e in merged:
        if e.entity_type != "ORG" or e.end_pos + 1 >= len(text):
            out.append(e)
            continue
        if text[e.end_pos] not in HS_CHARS:
            out.append(e)
            continue
        hit = _place_at(text, e.end_pos + 1, phrases)
        if hit is None:
            out.append(e)
            continue
        _phrase, src, p_end = hit
        p_start = e.end_pos + 1
        new_text = text[e.start_pos : p_end]
        if hd.match_org_role(new_text) is not None:
            fire("R-OPC-role-refused", e.start_pos, p_end, "ORG", src=src)
            out.append(e)
            continue
        out.append(
            dataclasses.replace(e, text=new_text, end_pos=p_end, is_ambiguous=False)
        )
        loc_emitted = False
        if CFG["opc_nested"] and (p_start, p_end) not in locs:
            emitted.append(
                DetectedEntity(
                    text=text[p_start:p_end],
                    entity_type="LOCATION",
                    start_pos=p_start,
                    end_pos=p_end,
                    confidence=e.confidence,
                    source=e.source,
                )
            )
            locs.add((p_start, p_end))
            loc_emitted = True
        fire(
            "R-OPC",
            e.start_pos,
            p_end,
            "ORG",
            src=src,
            org=(e.start_pos, e.end_pos, e.source),
            place=(p_start, p_end),
            loc_emitted=loc_emitted,
        )
    return out + emitted


# ---------------------------------------------------------------------------
# Late rules (after the final merge): R-ACR, R-DEF, R-FN-DOC and alternatives
# ---------------------------------------------------------------------------

_ACRO = re.compile(f"(?<![\\w-])([{_U}]{{2,6}})(?![\\w-])")
_ELISION_PREFIX = re.compile(r"^[dlDL]['’]")


def org_initials(text: str) -> str | None:
    words = []
    for tok in strip_french_titles(text).split():
        if tok in ORG_CONNECTORS:
            continue
        tok = _ELISION_PREFIX.sub("", tok)
        if tok[:1].isupper():
            words.append(tok)
    if len(words) < 2:
        return None
    return "".join(w[0] for w in words)


def late_acr(
    det: HybridDetector, text: str, ents: list[DetectedEntity]
) -> list[DetectedEntity]:
    roles = hd.load_org_role_filter().acronyms
    initials: dict[str, DetectedEntity] = {}
    # as specified: not a role acronym of org_role_filter.yaml; refined: not a
    # role at all for the 10.2 role test (role acronyms and VP prefixes)
    for e in ents:
        if e.entity_type == "ORG":
            ini = org_initials(e.text)
            if ini:
                initials.setdefault(fold(ini).upper(), e)
    added: list[DetectedEntity] = []
    for m in _ACRO.finditer(text):
        t = m.group(1)
        if len(t) < CFG["acr_min"] or fold(t).upper() not in initials:
            continue
        if CFG["acr_roles"] == "acronyms" and t in roles:
            continue
        if CFG["acr_roles"] == "match_org_role" and hd.match_org_role(t) is not None:
            continue
        # covered by no detection: no detection overlaps the token
        if any(x.start_pos < m.end() and m.start() < x.end_pos for x in ents + added):
            continue
        src = initials[fold(t).upper()]
        added.append(
            DetectedEntity(
                text=t,
                entity_type="ORG",
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.70,
                source="regex",
            )
        )
        fire(
            "R-ACR",
            m.start(),
            m.end(),
            "ORG",
            tied_to=(src.text, src.start_pos),
        )
    return added


_ALIAS = f"(?:[{_U}][\\w&'’.-]*(?:{HSPACE}+[{_U}][\\w&'’.-]*)*)"
_CLAUSE = re.compile(
    f"[Cc]i-après{HSPACE}+(?:(?:dénommée?|désignée?|dénommés|dénommées){HSPACE}+)?"
    f'(?:["“«]{HSPACE}*)({_ALIAS})(?:{HSPACE}*["”»])'
)
_PAREN = re.compile(f"{HSPACE}*\\({HSPACE}*({_ALIAS}){HSPACE}*\\)")
_SENT_END = re.compile(r"[.!?](?=\s)|\n[ \t]*\n")


def _alias_ok(alias: str) -> bool:
    first = alias.split()[0]
    if first.casefold() in ARTICLES or first.casefold().startswith(("l'", "l’")):
        return False
    return True


def late_def(
    det: HybridDetector, text: str, ents: list[DetectedEntity]
) -> list[DetectedEntity]:
    mode = CFG["def"]
    aliases: dict[str, tuple[int, str]] = {}
    orgs = sorted((e for e in ents if e.entity_type == "ORG"), key=lambda e: e.end_pos)
    persons = [e for e in ents if e.entity_type == "PERSON"]
    org_names = {}
    for e in orgs:
        core = strip_french_titles(e.text)
        if core:
            org_names.setdefault(fold(core), e)
            org_names.setdefault(fold(core.split()[0]), e)
    for m in _CLAUSE.finditer(text):
        alias = m.group(1)
        if not _alias_ok(alias):
            CUR["def_seen"].append(("clause-refused-article", m.start(1), alias))
            continue
        tie = None
        if mode == "spec":
            for e in reversed(orgs):
                if e.end_pos > m.start():
                    continue
                gap = text[e.end_pos : m.start()]
                if _SENT_END.search(gap):
                    break
                if any(
                    e.end_pos <= p.start_pos and p.end_pos <= m.start() for p in persons
                ):
                    break
                tie = ("ORG before, same sentence", e.text, e.start_pos)
                break
        elif mode == "any":
            tie = ("clause only", "", -1)
        elif mode == "name":
            e2 = org_names.get(fold(alias))
            if e2 is not None:
                tie = ("same name as an ORG", e2.text, e2.start_pos)
        CUR["def_seen"].append(("clause", m.start(1), alias, tie))
        if tie is not None:
            aliases.setdefault(alias, (m.start(1), str(tie)))
    if mode in ("spec", "any"):
        for e in orgs:
            p = _PAREN.match(text, e.end_pos)
            if p and _alias_ok(p.group(1)):
                CUR["def_seen"].append(("paren", p.start(1), p.group(1), e.text))
                aliases.setdefault(p.group(1), (p.start(1), f"paren after {e.text!r}"))
    added: list[DetectedEntity] = []
    for alias, (def_at, why) in aliases.items():
        for m in re.finditer(f"(?<![\\w-]){re.escape(alias)}(?![\\w-])", text):
            if any(
                x.start_pos < m.end() and m.start() < x.end_pos for x in ents + added
            ):
                continue
            added.append(
                DetectedEntity(
                    text=alias,
                    entity_type="ORG",
                    start_pos=m.start(),
                    end_pos=m.end(),
                    confidence=0.70,
                    source="regex",
                )
            )
            fire("R-DEF", m.start(), m.end(), "ORG", defined_at=def_at, tie=why)
    return added


def _sentence_start(text: str, pos: int) -> bool:
    i = pos
    while i > 0 and text[i - 1] in HS_CHARS:
        i -= 1
    if i == 0 or LINE_BREAK_RE.match(text[i - 1]):
        return True
    return i < pos and text[i - 1] in ".!?"


def late_fn(
    det: HybridDetector, text: str, ents: list[DetectedEntity]
) -> list[DetectedEntity]:
    mode = CFG["fn"]
    firsts: set[str] = set()
    for e in ents:
        if e.entity_type != "PERSON":
            continue
        toks = strip_french_titles(e.text).split()
        if len(toks) >= 2:
            firsts.add(toks[0].strip(",;:"))
    doc = CUR.get("doc")
    tok_at = {t.idx: t for t in doc} if doc is not None else {}
    added: list[DetectedEntity] = []
    for m in WORD_RE.finditer(text):
        n = m.group()
        if not known(det, n):
            continue
        s, e = m.start(), m.end()
        if any(x.start_pos < e and s < x.end_pos for x in ents + added):
            continue
        rule = None
        if mode == "doc":
            if n in firsts:
                rule = "R-FN-DOC"
        elif mode in ("subj", "subj_propn"):
            if not _sentence_start(text, s):
                continue
            tok = tok_at.get(s)
            if (
                tok is not None
                and tok.dep_ in ("nsubj", "nsubj:pass")
                and tok.head.pos_ in ("VERB", "AUX")
                and (mode == "subj" or tok.pos_ == "PROPN")
            ):
                rule = "R-FN-SUBJ" if mode == "subj" else "R-FN-SUBJ-PROPN"
        elif mode == "line":
            ls = s
            while ls > 0 and text[ls - 1] in HS_CHARS:
                ls -= 1
            indented = ls < s and (ls == 0 or LINE_BREAK_RE.match(text[ls - 1]))
            if indented and re.match(f"{HSPACE}[{_L}]", text[e : e + 2]):
                rule = "R-FN-LINE"
        if rule is None:
            continue
        added.append(
            DetectedEntity(
                text=n,
                entity_type="PERSON",
                start_pos=s,
                end_pos=e,
                confidence=0.80,
                source="regex",
            )
        )
        tok = tok_at.get(s)
        fire(
            rule,
            s,
            e,
            "PERSON",
            pos=getattr(tok, "pos_", None),
            dep=getattr(tok, "dep_", None),
            head_pos=getattr(getattr(tok, "head", None), "pos_", None),
        )
    return added


# ---------------------------------------------------------------------------
# Slice K: R-NEST and the ORG pattern widenings
# ---------------------------------------------------------------------------

_ORIG_EXACT = HybridDetector._is_exact_match


def _exact(self: HybridDetector, e1: DetectedEntity, e2: DetectedEntity) -> bool:
    base = _ORIG_EXACT(self, e1, e2)
    if not base:
        return False
    same_span = e1.start_pos == e2.start_pos and e1.end_pos == e2.end_pos
    nested = (e1.start_pos <= e2.start_pos and e2.end_pos <= e1.end_pos) or (
        e2.start_pos <= e1.start_pos and e1.end_pos <= e2.end_pos
    )
    if CUR.get("in_loop"):
        CUR["exact_calls"].append((same_span, nested))
    if CFG["nest"] and not same_span and not nested:
        fire(
            "R-NEST",
            min(e1.start_pos, e2.start_pos),
            max(e1.end_pos, e2.end_pos),
            e2.entity_type,
        )
        return False
    return True


_ORG_TOKEN = f"[{_U}](?:[{_U}{_L}0-9]|[&'’.\\-](?=[{_U}{_L}0-9]))*"
_HS = "[ \\t\\u00A0\\u202F]"
_CONN = "(?:de|du|des|la|le|et|&)"
_ELI = "(?:[dl]['’])"
_PREFIXES = (
    "Société|Entreprise|Cabinet|Groupe|Compagnie|Association|Fondation|Institut|"
    "Consortium|Fédération|Syndicat|Chambre|Mutuelle|Coopérative|Ordre|Caisse|"
    "Union|Confédération|Agence|Comité|Commission|Ligue"
)
_SUFFIXES = (
    "SA|SARL|SAS|SASU|EURL|SNC|SCM|SCI|GIE|EI|SCOP|SEL|Association|Fondation|"
    "Institut|Groupe|Consortium|Fédération|Syndicat|Chambre|Mutuelle|Coopérative|"
    "Ordre|Caisse|Union|Confédération|Agence|Comité|Commission|Ligue"
)


def org_patterns(variant: str | None) -> tuple[str, str]:
    """(suffix form, prefix form) of the ``organizations`` category."""
    max_conn = 3 if variant in ("req_conn",) else 2
    cap = 9 if variant == "req_words" else 5
    sep = f"{_HS}(?:{_CONN}{_HS}){{0,{max_conn}}}{_ELI}?"
    co = f"(?:{_HS}&{_HS}Co\\.)?" if variant == "req_co" else ""
    name = f"{_ORG_TOKEN}(?:{sep}{_ORG_TOKEN}){{0,{cap}}}"
    # the product's suffix form is lazy, its prefix form greedy
    suffix = f"\\b({name}?{co}){_HS}+({_SUFFIXES})\\b"
    after_kw = f"{_HS}+"
    if variant in ("kwc", "kwc+req_elision"):
        after_kw = f"{_HS}+(?:{_CONN}{_HS}){{0,2}}{_ELI}?"
    elif variant == "req_elision":
        after_kw = f"(?:{_HS}+|{_HS}+{_ELI})"
    prefix = f"\\b({_PREFIXES}){after_kw}({name}{co})"
    return suffix, prefix


_ORIG_ORG_PATTERNS: list[Any] = []


def set_org_variant(det: HybridDetector, variant: str | None) -> None:
    pats = det.regex_matcher.patterns["organizations"]
    if not _ORIG_ORG_PATTERNS:
        _ORIG_ORG_PATTERNS.extend(p["regex"] for p in pats)
    if variant is None:
        for p, orig in zip(pats, _ORIG_ORG_PATTERNS):
            p["regex"] = orig
        return
    suffix, prefix = org_patterns(variant)
    pats[0]["regex"] = re.compile(suffix, re.UNICODE)
    pats[1]["regex"] = re.compile(prefix, re.UNICODE)


# ---------------------------------------------------------------------------
# Recording regex matcher (category of each regex entity)
# ---------------------------------------------------------------------------


def _rec_match(
    self: RegexMatcher, text: str, spacy_doc: Any | None = None
) -> list[DetectedEntity]:
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
    CUR["cat"] = {key(e): cat[id(e)] for e in out}
    return out


# ---------------------------------------------------------------------------
# Script copies of detect_entities and _merge_entities (hooks off by default)
# ---------------------------------------------------------------------------


def _detect(self: HybridDetector, text: str) -> list[DetectedEntity]:
    """``HybridDetector.detect_entities`` (hybrid_detector.py:580-668) with
    the 10.4 hooks."""
    CUR["text"] = text
    CUR["sal"] = salutation_lines(self, text, CFG["maxlen"])
    spacy_entities = self.spacy_detector.detect_entities(text)
    for entity in spacy_entities:
        entity.source = "spacy"
    spacy_entities = self._trim_entity_boundaries(spacy_entities)
    CUR["doc"] = self.spacy_detector.last_doc
    regex_entities = self.regex_matcher.match_entities(
        text, spacy_doc=self.spacy_detector.last_doc
    )
    for entity in regex_entities:
        entity.source = "regex"
    CUR["pre_spacy"] = list(spacy_entities)
    CUR["pre_regex"] = list(regex_entities)

    # 10.4 R-SAL-BARE (and the information rows): added to the regex list
    if CFG["bare"]:
        regex_entities = regex_entities + sal_bare(
            self, text, spacy_entities, regex_entities
        )
    if CFG["addr"] or CFG["sig"]:
        regex_entities = regex_entities + sal_addr_sig(
            self, text, spacy_entities, regex_entities
        )

    blockers = [
        (e.start_pos, e.end_pos)
        for e in spacy_entities + regex_entities
        if e.entity_type in ("ORG", "LOCATION")
    ]
    spacy_entities, spacy_guards = self._fix_person_boundaries(
        spacy_entities, text, blockers
    )
    regex_entities, regex_guards = self._fix_person_boundaries(
        regex_entities, text, blockers
    )
    # 10.4 R-SAL-SPLIT: on both lists, next to the boundary fix
    if CFG["split"]:
        spacy_entities, spacy_guards = sal_split(
            self, text, spacy_entities, spacy_guards
        )
        regex_entities, regex_guards = sal_split(
            self, text, regex_entities, regex_guards
        )
    CUR["fixed_spacy"] = list(spacy_entities)
    CUR["fixed_regex"] = list(regex_entities)
    pristine_regex = (
        [dataclasses.replace(e) for e in regex_entities]
        if spacy_guards or regex_guards
        else []
    )
    merged_entities = self._merge_entities(spacy_entities, regex_entities, text)
    if spacy_guards or regex_guards:
        kept = hd._SpanIndex.of(merged_entities)
        refused_spacy = self._refused_guards(spacy_guards, kept)
        refused_regex = self._refused_guards(regex_guards, kept)
        if refused_spacy or refused_regex:
            for index, original in refused_spacy.items():
                spacy_entities[index] = original
            for index, original in refused_regex.items():
                pristine_regex[index] = original
            merged_entities = self._merge_entities(spacy_entities, pristine_regex, text)

    # 10.4 late rules: after the final merge
    added: list[DetectedEntity] = []
    if CFG["acr"]:
        added += late_acr(self, text, merged_entities + added)
    if CFG["def"]:
        added += late_def(self, text, merged_entities + added)
    if CFG["fn"]:
        added += late_fn(self, text, merged_entities + added)
    if added:
        CUR["late_added"] = [key(e) for e in added]
        if CFG["late_dedup"]:
            before = {key(e) for e in merged_entities}
            merged_entities = self._dedup_same_type_overlaps(
                merged_entities + added, text
            )
            after = {key(e) for e in merged_entities}
            CUR["late_side_effects"] = sorted(
                (before - after) | (after - before - {key(e) for e in added})
            )
        else:
            merged_entities = merged_entities + added
        merged_entities.sort(key=lambda e: e.start_pos)
    return merged_entities


def _merge(
    self: HybridDetector,
    spacy_entities: list[DetectedEntity],
    regex_entities: list[DetectedEntity],
    text: str | None = None,
) -> list[DetectedEntity]:
    """``HybridDetector._merge_entities`` (hybrid_detector.py:670-822) with
    the R-OPC hook after ``_filter_org_roles`` (both passes)."""
    CUR["merge_no"] += 1
    merged: list[DetectedEntity] = list(spacy_entities)
    entities_to_remove: list[DetectedEntity] = []
    for regex_entity in regex_entities:
        overlap_found = False
        for spacy_entity in spacy_entities:
            if self._has_overlap(spacy_entity, regex_entity):
                overlap_found = True
                CUR["in_loop"] = True
                exact = self._is_exact_match(spacy_entity, regex_entity)
                CUR["in_loop"] = False
                if exact:
                    if regex_entity.entity_type == spacy_entity.entity_type:
                        pass
                    elif self._is_hyphen_name_without_first_name(regex_entity):
                        pass
                    else:
                        regex_entity.is_ambiguous = True
                        merged.append(regex_entity)
                    break
                elif self._should_prefer_regex_org(regex_entity, spacy_entity):
                    entities_to_remove.append(spacy_entity)
                    merged.append(regex_entity)
                    break
                elif regex_entity.entity_type != spacy_entity.entity_type:
                    regex_entity.is_ambiguous = True
                    merged.append(regex_entity)
                    break
                else:
                    merged.append(regex_entity)
                    break
        if not overlap_found:
            merged.append(regex_entity)
    for entity in entities_to_remove:
        if entity in merged:
            merged.remove(entity)
    merged = self._filter_title_only_entities(merged)
    merged = self._filter_label_words(merged)
    merged = self._filter_location_noise(merged, text)
    merged = self._filter_org_roles(merged, text)
    merged = org_place_merge(self, merged, text)  # 10.4 R-OPC
    merged = self._dedup_same_type_overlaps(merged, text)
    merged, split_count = self._split_at_line_breaks(merged, text)
    if split_count:
        merged = self._filter_title_only_entities(merged)
        merged = self._filter_label_words(merged)
        merged = self._filter_location_noise(merged, text)
        merged = self._filter_org_roles(merged, text)
        merged = org_place_merge(self, merged, text)  # 10.4 R-OPC
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
    def __init__(self, label: str) -> None:
        self.label = label
        self.dets: dict[str, list[DetectedEntity]] = {}
        self.fires: dict[str, list[dict[str, Any]]] = {}
        self.sal: dict[str, list[SalLine]] = {}
        self.side: dict[str, list[Any]] = {}
        self.exact_calls: dict[str, list[tuple[bool, bool]]] = {}
        self.def_seen: dict[str, list[Any]] = {}
        self.pre: dict[str, dict[str, list[DetectedEntity]]] = {}
        self.cat: dict[str, dict[Key, str]] = {}
        self.docs_parsed: dict[str, Any] = {}


def run(
    det: HybridDetector, docs: list[Any], label: str, keep_doc: bool = False, **cfg: Any
) -> Result:
    CFG.clear()
    CFG.update(DEFAULT_CFG)
    CFG.update(cfg)
    set_org_variant(det, CFG["org_variant"])
    if CFG["opc"]:
        CUR["phrases"] = place_phrases(CFG["opc"])
    res = Result(label)
    for name, text, _gt in docs:
        CUR.update(
            doc_name=name,
            merge_no=0,
            fires=[],
            late_side_effects=[],
            late_added=[],
            exact_calls=[],
            def_seen=[],
            cat={},
            in_loop=False,
        )
        res.dets[name] = det.detect_entities(text)
        last = CUR["merge_no"]
        res.fires[name] = [
            # pre-merge (0) and late fires, and the fires of the last merge
            f
            for f in CUR["fires"]
            if f["merge"] in (0, last)
        ]
        res.sal[name] = list(CUR["sal"])
        res.side[name] = list(CUR["late_side_effects"])
        res.exact_calls[name] = list(CUR["exact_calls"])
        res.def_seen[name] = list(CUR["def_seen"])
        res.pre[name] = {
            "spacy": CUR["pre_spacy"],
            "regex": CUR["pre_regex"],
            "fixed_spacy": CUR["fixed_spacy"],
            "fixed_regex": CUR["fixed_regex"],
        }
        res.cat[name] = dict(CUR["cat"])
        if keep_doc:
            res.docs_parsed[name] = CUR["doc"]
    set_org_variant(det, None)
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


def gt_at(gt: list[Any], start: int, end: int) -> list[Any]:
    return [g for g in gt if g.start_pos < end and start < g.end_pos]


def gt_str(gs: list[Any]) -> str:
    return ", ".join(f"{g.entity_type} {g.text!r}@{g.start_pos}" for g in gs) or "none"


def exact_ann(gt: list[Any], s: int, e: int, etype: str, text: str) -> bool:
    k = _match_key(text[s:e], etype)
    return any(
        g.entity_type == etype
        and g.start_pos < e
        and s < g.end_pos
        and _match_key(g.text, etype) == k
        for g in gt
    )


def classify_fire(f: dict[str, Any], gt: list[Any], text: str) -> str:
    """'target' when every span the fire produces is an annotation of its
    type at that position, else 'NON-TARGET'."""
    rule = f["rule"]
    if rule == "R-SAL-SPLIT":
        ok = all(exact_ann(gt, s, e, "PERSON", text) for s, e in f["pieces"])
    elif rule == "R-OPC":
        ok = exact_ann(gt, f["start"], f["end"], "ORG", text)
        ps, pe = f["place"]
        ok = ok and exact_ann(gt, ps, pe, "LOCATION", text)
    elif rule in ("R-NEST", "R-OPC-role-refused"):
        return "info"
    else:
        ok = exact_ann(gt, f["start"], f["end"], f["type"], text)
    return "target" if ok else "NON-TARGET"


PIERRE = ("hr_announcement.txt", "PERSON", "Pierre", 2778)
BRS = ("sales_proposal.txt", "ORG", "BRS", 5726)


def debt_status(res: Result) -> str:
    out = []
    for doc, etype, text, start in (PIERRE, BRS):
        end = start + len(text)
        dets = res.dets[doc]
        same = any(
            d.entity_type == etype and d.start_pos <= start and end <= d.end_pos
            for d in dets
        )
        anyt = any(d.start_pos <= start and end <= d.end_pos for d in dets)
        st = (
            "restored (same type)"
            if same
            else ("covered by another type" if anyt else "still uncovered")
        )
        out.append(f"{text}: {st}")
    return "; ".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: C901
    if len(sys.argv) != 3:
        sys.exit(
            "usage: accuracy_greetings_org_country_dryrun.py <baseline_dump.json> "
            "<out_dir>"
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
    det.detect_entities = types.MethodType(_detect, det)  # type: ignore[method-assign]
    det._merge_entities = types.MethodType(_merge, det)  # type: ignore[method-assign]
    det._is_exact_match = types.MethodType(_exact, det)  # type: ignore[method-assign]

    docs = _load_corpus_documents()
    by = {n: (t, g) for n, t, g in docs}
    log: list[str] = []
    table: list[str] = []
    product = [p["regex"].pattern for p in det.regex_matcher.patterns["organizations"]]
    if list(org_patterns(None)) != product:
        sys.exit("org_patterns(None) does not rebuild the product patterns: stop")

    # --- 1.1 base run reproduces the baseline dump -------------------------
    base = run(det, docs, "base", keep_doc=True)
    base_text = dump_json(base)
    (out_dir / "dump_base.json").write_text(base_text, encoding="utf-8")
    identical = base_text == dump_path.read_text(encoding="utf-8")
    btot, base_pairs = ro.tally(docs, base.dets)
    n_det = sum(len(v) for v in base.dets.values())
    log.append(
        f"# 1.1 base run: {n_det} detections; byte-identical to {dump_path.name}: "
        f"{identical}; flagged {n_flagged(base)}"
    )
    log.append(f"  tally: {btot}")
    if not identical:
        print("\n".join(log))
        sys.exit("base run does not reproduce the baseline dump: stop")
    write_per_doc(out_dir / "perdoc_base.json", docs, base)
    log.append("# 1.2 local per-document JSON: perdoc_base.json (run `delta`)")
    base_run = ro.Run("base", base.dets)
    bp, br, bf = ro.prf(*btot["Overall"])
    table.append(
        f"| Baseline (run P), absolute | {'/'.join(map(str, btot['PERSON']))} | "
        f"{'/'.join(map(str, btot['LOCATION']))} | {'/'.join(map(str, btot['ORG']))} | "
        f"{bp:.4f} / {br:.4f} / {bf:.4f} | - | - | - | {n_flagged(base)} | - | "
        f"{btot['Overall'][2]} / {btot['PERSON'][2]} / {btot['LOCATION'][2]} / "
        f"{btot['ORG'][2]} | {debt_status(base)} |"
    )

    inventory(det, docs, base, log)

    results: dict[str, Result] = {"base": base}

    def evaluate(label: str, res: Result, show_fires: bool = True) -> dict[str, Any]:
        results[label] = res
        fname = re.sub(r"[^\w.+-]+", "_", label).strip("_")
        (out_dir / f"dump_{fname}.json").write_text(dump_json(res), encoding="utf-8")
        write_per_doc(out_dir / f"perdoc_{fname}.json", docs, res)
        rep = ro.report(docs, base_run, ro.Run(label, res.dets), base_pairs, log)
        log.append(
            f"  flagged (is_ambiguous): base {n_flagged(base)} -> {n_flagged(res)}"
        )
        log.append(f"  AC5 debt: {debt_status(res)}")
        counts: collections.Counter[str] = collections.Counter()
        nt = 0
        for name, _t, gt in docs:
            text = by[name][0]
            for f in res.fires[name]:
                c = classify_fire(f, gt, text)
                counts[f"{f['rule']}:{c}"] += 1
                if c == "NON-TARGET":
                    nt += 1
                if show_fires:
                    extra = {
                        k: v
                        for k, v in f.items()
                        if k not in ("rule", "merge", "start", "end", "type", "text")
                    }
                    log.append(
                        f"    FIRE {f['rule']} [{name}] {f['type']} "
                        f"{f['text']!r}@{f['start']}-{f['end']} {c}; "
                        f"GT at position: {gt_str(gt_at(gt, f['start'], f['end']))}"
                        f"{'; ' + str(extra) if extra else ''}"
                    )
            if res.side[name]:
                log.append(f"    LATE-DEDUP SIDE EFFECTS [{name}]: {res.side[name]}")
        log.append(f"  fires: {dict(sorted(counts.items()))}")
        rep["fires"] = counts
        rep["nt"] = nt
        d = rep["delta"]
        p, r, f1 = ro.prf(*rep["tot"]["Overall"])
        cells = " | ".join(f"{d[t][0]:+d}/{d[t][1]:+d}/{d[t][2]:+d}" for t in TYPES)
        fn = " / ".join(str(rep["tot"][t][2]) for t in ("Overall",) + TYPES)
        nfires = sum(v for k, v in counts.items() if not k.endswith(":info"))
        table.append(
            f"| {label} | {cells} | {p:.4f} / {r:.4f} / {f1:.4f} | {rep['l2']} | "
            f"{rep['l2b']} | {rep['l1_chars']} ({rep['l1_in_gt']}) / "
            f"{rep['l1_spans']} | {n_flagged(res)} | {nfires} ({nt}) | {fn} | "
            f"{debt_status(res)} |"
        )
        return rep

    # --- 1.4 Slice S ---------------------------------------------------------
    log.append("\n# 1.4 Slice S")
    for ml in (40, 60, 80, None):
        reach = []
        for name, text, _g in docs:
            for ln in salutation_lines(det, text, ml):
                if ln.shape == 1:
                    reach.append(f"{name}@{ln.start}({ln.length})")
        log.append(f"  shape-1 reach at max_line_length={ml}: {len(reach)} {reach}")
    s_split = run(det, docs, "R-SAL-SPLIT", split=True)
    evaluate("R-SAL-SPLIT", s_split)
    for shape in ("shape1", "shape2", "both"):
        evaluate(f"R-SAL-BARE {shape}", run(det, docs, "b", bare=shape))
    s_all = run(det, docs, "S", split=True, bare="both")
    evaluate("FINAL Slice S (R-SAL-SPLIT + R-SAL-BARE both)", s_all)
    evaluate("info: R-SAL-ADDR", run(det, docs, "a", addr=True))
    evaluate("info: R-SIG", run(det, docs, "g", sig=True))
    ac3_check(det, docs, base, s_all, log)

    # --- 1.5 Slice O ---------------------------------------------------------
    log.append("\n# 1.5 Slice O")
    allsrc = frozenset({"cr", "city", "abbr"})
    for label, src in (
        ("R-OPC countries+regions only", frozenset({"cr"})),
        ("R-OPC cities only", frozenset({"city"})),
        ("R-OPC abbreviations only", frozenset({"abbr"})),
    ):
        evaluate(label, run(det, docs, label, opc=src))
    evaluate("R-OPC (all sources, nested LOCATION)", run(det, docs, "o", opc=allsrc))
    evaluate(
        "info: R-OPC without nested LOCATION",
        run(det, docs, "o2", opc=allsrc, opc_nested=False),
    )

    # --- 1.6 Slice A / D -----------------------------------------------------
    log.append("\n# 1.6 Slice A and D")
    evaluate(
        "R-ACR (as specified: role acronyms excluded)",
        run(det, docs, "acr", acr=True, acr_roles="acronyms"),
    )
    evaluate(
        "R-ACR (refined: every role of match_org_role excluded)",
        run(det, docs, "acr1", acr=True),
    )
    evaluate(
        "info: R-ACR as specified, 3-6 letters",
        run(det, docs, "acr3", acr=True, acr_roles="acronyms", acr_min=3),
    )
    evaluate(
        "R-ACR refined (no late dedup)",
        run(det, docs, "acr2", acr=True, late_dedup=False),
    )
    for mode, label in (
        ("doc", "R-FN-DOC"),
        ("subj", "R-FN-SUBJ"),
        ("subj_propn", "R-FN-SUBJ-PROPN"),
        ("line", "R-FN-LINE"),
    ):
        evaluate(label, run(det, docs, label, fn=mode))
    pierre_parse(base, log)
    fn_ac3(det, log)
    for mode, label in (
        ("spec", "R-DEF (as specified)"),
        ("any", "R-DEF-ANY (variant: clause alone, no tie)"),
        ("name", "R-DEF-NAME (variant: alias = name of an ORG of the document)"),
    ):
        res = run(det, docs, label, **{"def": mode})
        for name in res.def_seen:
            for s in res.def_seen[name]:
                log.append(f"    DEF-SEEN [{name}] {s}")
        evaluate(label, res)
    evaluate("R-ACR + R-DEF-NAME", run(det, docs, "ad", acr=True, **{"def": "name"}))

    # --- 1.7 Candidate items -------------------------------------------------
    log.append("\n# 1.7 candidate items")
    calls = [c for n in base.exact_calls for c in base.exact_calls[n]]
    log.append(
        f"  R-NEST: exact matches in the merge loop (all merges): {len(calls)}; "
        f"span-equal {sum(1 for c in calls if c[0])}; normalized-text only, "
        f"nested {sum(1 for c in calls if not c[0] and c[1])}; normalized-text "
        f"only, NOT nested {sum(1 for c in calls if not c[0] and not c[1])}"
    )
    evaluate("R-NEST", run(det, docs, "nest", nest=True))
    for variant, label in (
        ("req_words", "R-ORG-SHAPE 7+ words (cap 10 tokens)"),
        ("req_co", "R-ORG-SHAPE '& Co.'"),
        ("req_conn", "R-ORG-SHAPE 3 connectors"),
        ("req_elision", "R-ORG-SHAPE elision after the keyword"),
        ("kwc", "R-KWC"),
        ("kwc+req_elision", "R-KWC + elision part"),
    ):
        evaluate(label, run(det, docs, label, org_variant=variant))
        log.append(f"  regex time ratio {label}: {regex_ratio(variant)}")
    log.append(f"  regex time ratio product patterns: {regex_ratio(None)}")

    # --- 1.8 compositions ----------------------------------------------------
    log.append("\n# 1.8 compositions")
    s_cfg = {"split": True, "bare": "both"}
    o_cfg = {"opc": allsrc}
    a_cfg = {"acr": True, "fn": "doc"}
    d_cfg = {"def": "name"}
    k_cfg = {"nest": True, "org_variant": "kwc"}
    rec_cfg = {**s_cfg, **o_cfg, **a_cfg, **d_cfg, **k_cfg}
    comps = [
        ("Slice K alone (R-NEST + R-KWC)", k_cfg),
        ("FINAL Slice S+O", {**s_cfg, **o_cfg}),
        ("FINAL Slice S+O+A", {**s_cfg, **o_cfg, **a_cfg}),
        ("FINAL Slice S+O+A+D", {**s_cfg, **o_cfg, **a_cfg, **d_cfg}),
        ("Recommended = FINAL Slice S+O+A+D+K", rec_cfg),
        ("Recommended without D (S+O+A+K)", {**s_cfg, **o_cfg, **a_cfg, **k_cfg}),
        (
            "Recommended without R-KWC (S+O+A+D+R-NEST)",
            {**s_cfg, **o_cfg, **a_cfg, **d_cfg, "nest": True},
        ),
    ]
    for label, cfg in comps:
        evaluate(label, run(det, docs, label, **cfg))
    # input-order check of the recommended composition (lists reversed)
    rec = results["Recommended = FINAL Slice S+O+A+D+K"]
    log.append(order_check(det, docs, rec, rec_cfg))

    (out_dir / "dryrun_report.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    hdr = (
        "| Rule / composition | PERSON ΔTP/ΔFP/ΔFN | LOCATION | ORG | "
        "Projected overall P / R / F1 (local) | L2 | L2b | L1 chars (in GT) / "
        "spans | Flagged | Fires (non-target) | Projected FN O / P / L / Org "
        "(local) | AC5 debt |"
    )
    (out_dir / "dryrun_table.md").write_text(
        hdr + "\n" + "\n".join(table) + "\n", encoding="utf-8"
    )
    print("\n".join(log[:3]))
    print(hdr)
    print("\n".join(table))
    print(f"-> {out_dir / 'dryrun_report.txt'}")


def order_check(
    det: HybridDetector, docs: list[Any], ref: Result, cfg: dict[str, Any]
) -> str:
    orig = det._merge_entities

    def rev(
        self: HybridDetector,
        s: list[DetectedEntity],
        r: list[DetectedEntity],
        text: str | None = None,
    ) -> list[DetectedEntity]:
        return _merge(self, list(reversed(s)), list(reversed(r)), text)

    det._merge_entities = types.MethodType(rev, det)  # type: ignore[method-assign]
    res_rev = run(det, docs, "rev", **cfg)
    base_rev = run(det, docs, "base_rev")
    det._merge_entities = orig  # type: ignore[method-assign]
    base_ref = run(det, docs, "base_ref")
    dep_rec = {n for n in ref.dets if canon(ref.dets[n]) != canon(res_rev.dets[n])}
    dep_base = {
        n for n in base_ref.dets if canon(base_ref.dets[n]) != canon(base_rev.dets[n])
    }
    return (
        f"  order check (both pre-merge lists reversed): order-dependent documents "
        f"base {len(dep_base)} {sorted(dep_base)}; recommended {len(dep_rec)} "
        f"{sorted(dep_rec)}; new {sorted(dep_rec - dep_base)}"
    )


def regex_ratio(variant: str | None) -> str:
    suffix, prefix = org_patterns(variant)  # None: the product shape, rebuilt
    regexes = [re.compile(suffix), re.compile(prefix)]
    lines = [
        "Zorbal Quentrix " * 3200,
        "Zorbal, Quentrix de Vardel " * 2000,
        "Zorbal de la Quentrix d'Vardel " * 2000,
        "Institut de la d'Zorbal Quentrix & Co. de la de Vardel " * 1000,
    ]

    def best(length: int) -> float:
        cut = [ln[:length] for ln in lines]
        b = float("inf")
        for _ in range(5):
            t0 = time.perf_counter()
            for ln in cut:
                for rx in regexes:
                    for _m in rx.finditer(ln):
                        pass
            b = min(b, time.perf_counter() - t0)
        return b

    t_big = best(50_000)
    return f"{t_big / best(6_250):.1f}x (50 KB best of 5: {t_big * 1000:.1f} ms)"


# ---------------------------------------------------------------------------
# Inventory (1.3)
# ---------------------------------------------------------------------------


def inventory(  # noqa: C901
    det: HybridDetector, docs: list[Any], base: Result, log: list[str]
) -> None:
    log.append("\n# 1.3 inventory")

    def cover(name: str, s: int, e: int) -> str:
        c = [
            f"{d.entity_type} {d.text!r}@{d.start_pos}-{d.end_pos} {d.source}"
            for d in base.dets[name]
            if d.start_pos < e and s < d.end_pos
        ]
        return ", ".join(c) or "nothing"

    # salutation lines and the PERSON annotations on them
    log.append("## salutation lines (shape 1 without a length limit; shape 2)")
    for name, text, gt in docs:
        for ln in salutation_lines(det, text, None):
            log.append(
                f"  [{name}@{ln.start}] shape {ln.shape} ({ln.kind}, len "
                f"{ln.length}) {text[ln.start:ln.end].strip()!r}"
            )
            for g in gt:
                if ln.start <= g.start_pos and g.end_pos <= ln.end:
                    log.append(
                        f"     GT {g.entity_type} {g.text!r}@{g.start_pos}: "
                        f"{cover(name, g.start_pos, g.end_pos)}"
                    )
    # short lines ending with "," or "!", and lines whose first word is
    # followed by a known first name: opener / closing candidates
    log.append("## short lines (<= 60) ending with ',' or '!' (opener/closing words)")
    words: collections.Counter[str] = collections.Counter()
    for name, text, _g in docs:
        for ls, le in lines_of(text):
            st = text[ls:le].strip(" \t  ")
            if st and len(st) <= 60 and st[-1] in ",!":
                log.append(f"  [{name}@{ls}] {st!r}")
                words[st.split()[0].rstrip(",!")] += 1
    log.append(f"  first words: {dict(words)}")
    log.append("## lines whose first word(s) are followed by a known first name")
    for name, text, gt in docs:
        for ls, le in lines_of(text):
            line = text[ls:le]
            m = re.match(
                f"{HSPACE}*([{_U}][{_L}]+(?:{HSPACE}+[{_L}]+)?){HSPACE}+({NAME_TOK})"
                f"(?=[,.!]|{HSPACE}*$)",
                line,
            )
            if m and known(det, m.group(2)):
                log.append(f"  [{name}@{ls}] {line.strip()[:90]!r}")
    # address and signature lines
    log.append("## address lines (<first name>, <lower-case word>) and signatures")
    for name, text, gt in docs:
        lines = lines_of(text)
        for i, (ls, le) in enumerate(lines):
            line = text[ls:le]
            st = line.strip(" \t  ")
            body = ls + len(line) - len(line.lstrip(" \t  "))
            m = _ADDR.match(text, body, le)
            if m and known(det, m.group(1)):
                log.append(
                    f"  ADDR [{name}@{m.start(1)}] {st[:60]!r}; GT "
                    f"{gt_str(gt_at(gt, m.start(1), m.end(1)))}; "
                    f"cover {cover(name, m.start(1), m.end(1))}"
                )
            if re.fullmatch(NAME_TOK, st) and known(det, st):
                prev = [text[a:b].strip() for a, b in lines[max(0, i - 3) : i]]
                log.append(
                    f"  BARE-NAME LINE [{name}@{body}] {st!r} after {prev}; GT "
                    f"{gt_str(gt_at(gt, body, body + len(st)))}; "
                    f"cover {cover(name, body, body + len(st))}"
                )
    # "X, Y" PERSON spans
    log.append("## 'X, Y' PERSON spans (final and pre-merge) and last_first_names hits")
    for name, text, _g in docs:
        sal = salutation_lines(det, text, None)
        seen = set()
        for where, ents in (
            ("final", base.dets[name]),
            ("pre-spacy", base.pre[name]["spacy"]),
            ("pre-regex", base.pre[name]["regex"]),
        ):
            for e in ents:
                if e.entity_type != "PERSON":
                    continue
                m = _XY.fullmatch(text, e.start_pos, e.end_pos)
                if not m:
                    continue
                kx, ky = known(det, m.group(1)), known(det, m.group(2))
                cat = base.cat[name].get(key(e), "") if where == "pre-regex" else ""
                tag = (where, e.start_pos, e.end_pos)
                if tag in seen:
                    continue
                seen.add(tag)
                log.append(
                    f"  [{name}@{e.start_pos}] {where} {e.source} {cat} {e.text!r} "
                    f"X known={kx} Y known={ky} salutation line="
                    f"{on_salutation_line(sal, e.start_pos, e.end_pos)}"
                )
    # ORG + place adjacencies
    log.append("## ORG + listed place (one space) in the baseline detections")
    phrases = place_phrases(frozenset({"cr", "city", "abbr"}))
    for name, text, gt in docs:
        for e in base.dets[name]:
            if e.entity_type != "ORG" or e.end_pos + 1 >= len(text):
                continue
            if text[e.end_pos] not in HS_CHARS:
                continue
            hit = _place_at(text, e.end_pos + 1, phrases)
            if hit is None:
                continue
            ps, pe = e.end_pos + 1, hit[2]
            whole = exact_ann(gt, e.start_pos, pe, "ORG", text)
            log.append(
                f"  [{name}@{e.start_pos}] ORG {e.text!r} + {text[ps:pe]!r} "
                f"({hit[1]}); ORG annotation on the whole: {whole}; place cover: "
                f"{cover(name, ps, pe)}; role: {hd.match_org_role(text[e.start_pos:pe])}"
            )
    log.append("## ORG annotations ending with a listed place")
    for name, text, gt in docs:
        for g in gt:
            if g.entity_type != "ORG":
                continue
            for phrase, src in phrases:
                if g.text.endswith(" " + phrase):
                    ps = g.end_pos - len(phrase)
                    nested = [
                        x
                        for x in gt
                        if x.entity_type == "LOCATION"
                        and x.start_pos == ps
                        and x.end_pos == g.end_pos
                    ]
                    nloc = any(
                        d.entity_type == "LOCATION"
                        and d.start_pos == ps
                        and d.end_pos == g.end_pos
                        for d in base.dets[name]
                    )
                    log.append(
                        f"  [{name}@{g.start_pos}] {g.text!r} place {phrase!r} "
                        f"({src}); nested LOCATION annotated {bool(nested)}, "
                        f"detected {nloc}; detections: {cover(name, g.start_pos, g.end_pos)}"
                    )
                    break
    log.append("## role forms followed by a listed place (text scan)")
    rf = hd.load_org_role_filter()
    role_re = re.compile(
        f"(?<![\\w-])(?:{'|'.join(map(re.escape, rf.vp_prefixes))}|"
        f"{'|'.join(map(re.escape, sorted(rf.acronyms)))})(?:{HSPACE}+[{_U}][\\w&-]*)*"
    )
    for name, text, gt in docs:
        for m in role_re.finditer(text):
            # every listed place inside or right after the role form
            for pm in re.finditer(f"{HSPACE}", text[m.start() : m.end() + 1]):
                pos = m.start() + pm.end()
                hit = _place_at(text, pos, phrases)
                if hit:
                    log.append(
                        f"  [{name}@{m.start()}] {text[m.start():hit[2]]!r} place "
                        f"{text[pos:hit[2]]!r}: {cover(name, m.start(), hit[2])}"
                    )
                    break
    # defined aliases
    log.append("## definition clauses")
    for name, text, gt in docs:
        for m in _CLAUSE.finditer(text):
            alias = m.group(1)
            occ = [
                x.start()
                for x in re.finditer(f"(?<![\\w-]){re.escape(alias)}(?![\\w-])", text)
            ]
            ann = sum(1 for o in occ if exact_ann(gt, o, o + len(alias), "ORG", text))
            cov = sum(
                1
                for o in occ
                if any(
                    d.start_pos < o + len(alias) and o < d.end_pos
                    for d in base.dets[name]
                )
            )
            same = sum(
                1
                for o in occ
                if any(
                    d.entity_type == "ORG"
                    and d.start_pos <= o
                    and o + len(alias) <= d.end_pos
                    for d in base.dets[name]
                )
            )
            before = [
                f"{d.entity_type} {d.text!r}@{d.start_pos}"
                for d in base.dets[name]
                if d.end_pos <= m.start() and d.end_pos > m.start() - 250
            ]
            log.append(
                f"  [{name}@{m.start(1)}] alias {alias!r}: {len(occ)} standalone "
                f"occurrences, {ann} annotated ORG at position, {cov} overlapped by a "
                f"detection, {same} inside an ORG detection; detections in the 250 "
                f"chars before: {before}"
            )
    # R-FN-DOC targets
    log.append(
        "## R-FN-DOC targets (uncovered capitalised known first names equal to "
        "the first token of a 2+-token PERSON of the document)"
    )
    for name, text, gt in docs:
        firsts: dict[str, list[str]] = collections.defaultdict(list)
        for e in base.dets[name]:
            if e.entity_type == "PERSON":
                toks = strip_french_titles(e.text).split()
                if len(toks) >= 2:
                    firsts[toks[0].strip(",;:")].append(f"{e.text!r}@{e.start_pos}")
        for m in WORD_RE.finditer(text):
            n = m.group()
            if not known(det, n) or n not in firsts:
                continue
            if any(
                d.start_pos < m.end() and m.start() < d.end_pos for d in base.dets[name]
            ):
                continue
            log.append(
                f"  [{name}@{m.start()}] {n!r}: GT {gt_str(gt_at(gt, m.start(), m.end()))}"
                f"; PERSON detections: {firsts[n][:3]}"
            )
    # BRS / acronyms
    log.append("## R-ACR: ORG initials and standalone all-caps tokens")
    for name, text, gt in docs:
        ini: dict[str, list[str]] = collections.defaultdict(list)
        for e in base.dets[name]:
            if e.entity_type == "ORG":
                i = org_initials(e.text)
                if i:
                    ini[fold(i).upper()].append(f"{e.text!r}@{e.start_pos}")
        for m in _ACRO.finditer(text):
            if fold(m.group(1)).upper() in ini:
                log.append(
                    f"  [{name}@{m.start()}] {m.group(1)!r} = initials of "
                    f"{ini[fold(m.group(1)).upper()][:3]}; GT "
                    f"{gt_str(gt_at(gt, m.start(), m.end()))}; cover "
                    f"{cover(name, m.start(), m.end())}"
                )


def pierre_parse(base: Result, log: list[str]) -> None:
    doc = base.docs_parsed.get(PIERRE[0])
    if doc is None:
        return
    log.append("## 'Pierre' @2778 in the real pipeline parse (last_doc)")
    for tok in doc:
        if tok.idx in (2778,) or (tok.text == "Pierre" and tok.idx > 2700):
            log.append(
                f"  token {tok.text!r}@{tok.idx}: pos_={tok.pos_} dep_={tok.dep_} "
                f"head={tok.head.text!r} head.pos_={tok.head.pos_} ent_type_="
                f"{tok.ent_type_!r}"
            )


# AC3 sentences (common-word uses of "Pierre" and "Blanche", and a running-text
# first name); all words occur in the main-corpus text (Task 1.10)
AC3_DOCS = {
    "sentence-start noun": "Pierre après pierre, le projet reste solide.",
    "running-text name": "Le rapport de Pierre et du comité est prêt.",
    "lower-case noun": "Une pierre sur le bureau du comité.",
    "lower-case adjective": "Une page blanche pour le rapport.",
    "sentence-start adjective": "Blanche, la page du rapport reste sur le bureau.",
    "copula": "Pierre est une base solide.",
    "indented sentence-start noun": "   Pierre après pierre, le projet reste solide.",
}
AC3_RESIDUAL = (
    "M. Pierre Fontaine a signé le rapport.\n" + AC3_DOCS["sentence-start noun"]
)


def fn_ac3(det: HybridDetector, log: list[str]) -> None:
    log.append("## AC3 sentences: fires of R-FN-DOC and the alternatives")
    docs = [(k, v, []) for k, v in AC3_DOCS.items()]
    docs.append(("residual (document names Pierre Fontaine)", AC3_RESIDUAL, []))
    for mode, label in (
        ("doc", "R-FN-DOC"),
        ("subj", "R-FN-SUBJ"),
        ("subj_propn", "R-FN-SUBJ-PROPN"),
        ("line", "R-FN-LINE"),
    ):
        res = run(det, docs, label, keep_doc=True, fn=mode)
        for name, text, _g in docs:
            fires = [f for f in res.fires[name] if f["rule"].startswith("R-FN")]
            parse = ""
            doc = res.docs_parsed[name]
            for tok in doc:
                if tok.text in ("Pierre", "Blanche"):
                    parse += (
                        f" [{tok.text}@{tok.idx} pos={tok.pos_} dep={tok.dep_} "
                        f"head={tok.head.text}/{tok.head.pos_}]"
                    )
            log.append(
                f"  {label} | {name}: fires "
                f"{[(f['text'], f['start']) for f in fires]}{parse}"
            )


def ac3_check(
    det: HybridDetector, docs: list[Any], base: Result, s_all: Result, log: list[str]
) -> None:
    log.append("## AC3: Slice S never fires outside a salutation line")
    outside = 0
    diff_outside = 0
    n_names = 0
    for name, text, _g in docs:
        sal = s_all.sal[name]
        for f in s_all.fires[name]:
            if not on_salutation_line(sal, f["start"], f["end"]):
                outside += 1
                log.append(f"    fire outside a salutation line: {name} {f}")
        a, b = set(canon(base.dets[name])), set(canon(s_all.dets[name]))
        for t in a ^ b:
            if not on_salutation_line(sal, t[2], t[3]):
                diff_outside += 1
                log.append(
                    f"    detection change outside a salutation line: {name} {t}"
                )
        for m in WORD_RE.finditer(text):
            if known(det, m.group()) and not on_salutation_line(
                sal, m.start(), m.end()
            ):
                n_names += 1
    log.append(
        f"  fires outside a salutation line: {outside}; detection changes outside a "
        f"salutation line: {diff_outside}; capitalised known first names not on a "
        f"salutation line: {n_names} (no new detection at any of them)"
    )


if __name__ == "__main__":
    main()
