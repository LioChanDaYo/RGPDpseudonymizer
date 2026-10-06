"""Re-measure and dry-run the Story 10.3a rules (boundaries + run-on spans).

Story 10.3a, Tasks 1.2-1.8. Main corpus only: calls ``_load_corpus_documents()``
and never the held-out loader. Imports ``tests.accuracy.conftest`` read-only
(G4 scope). No product code is changed: every candidate rule is patched in
this script only (modified copies of ``detection_patterns.yaml`` written
outside the repository, subclassed ``RegexMatcher``, monkeypatched module
functions).

What it does, per document:

1. runs spaCy once, then ``_trim_entity_boundaries`` (the spaCy pre-merge list);
2. runs the regex layer once per pattern variant (the regex pre-merge lists);
3. writes the baseline pre-merge lists to ``<out_dir>/premerge_baseline.json``
   and checks that ``_merge_entities`` over them reproduces the baseline dump
   (``scripts/accuracy_dump_detections.py``) detection for detection;
4. re-merges every composition of candidate rules and re-scores it with
   ``match_entities``: net per-type delta, lost/gained TP classification,
   coverage levels 1, 2 and 2b.

The counts printed here are local attribution numbers (Product Constraint 6):
they belong in the story only, never in the QA report, CHANGELOG or PR body.

Usage (Windows toolchain)::

    poetry run python scripts/accuracy_runon_dryrun.py <baseline_dump.json> <out_dir>
"""

from __future__ import annotations

import collections
import copy
import dataclasses
import io
import json
import logging
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import structlog  # noqa: E402

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))

from gdpr_pseudonymizer.nlp import hybrid_detector as hd  # noqa: E402
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity  # noqa: E402
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector  # noqa: E402
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher  # noqa: E402
from gdpr_pseudonymizer.resources import DETECTION_PATTERNS_PATH  # noqa: E402
from tests.accuracy.conftest import (  # noqa: E402
    GroundTruthEntity,
    _load_corpus_documents,
    _match_key,
    match_entities,
)

TYPES = ("PERSON", "LOCATION", "ORG")

# ---------------------------------------------------------------------------
# Candidate rule text (Task 2 freezes it; the product code implements it)
# ---------------------------------------------------------------------------

# R-LB: explicit horizontal whitespace (space, tab, NBSP, narrow NBSP)
HSPACE_CHARS = r" \t  "
HSPACE = f"[{HSPACE_CHARS}]"
# R-SPLIT: the line-break set HSPACE excludes
LINE_BREAK_RE = re.compile("[\n\r\v\f\x85  ]")

_U = "A-ZÀ-ÖØ-ÞĀ-ſ"  # upper-case letters (+ Latin Extended-A, as the YAML)
_L = "a-zß-öø-ÿĀ-ſ"  # lower-case letters
# R-ORG capitalised token: an upper-case letter, then letters/digits; & ' ’ .
# and - only inside the token (followed by a letter or digit)
ORG_TOKEN = f"[{_U}](?:[{_U}{_L}0-9]|[&'’.\\-](?=[{_U}{_L}0-9]))*"
ORG_CONNECTOR = "(?:de|du|des|la|le|et|&)"
ORG_ELISION = "[dl]['’]"
# between two capitalised tokens: one HSPACE, up to two spaced connectors,
# then an optional glued elision ("de l'", "d'")
ORG_SEP = f"{HSPACE}(?:{ORG_CONNECTOR}{HSPACE}){{0,2}}(?:{ORG_ELISION})?"
# at most ORG_MAX_TOKENS capitalised tokens: bounds the regex time on long
# runs of capitalised words (linear, not quadratic, in the line length)
ORG_MAX_TOKENS = 6
ORG_NAME_LAZY = f"{ORG_TOKEN}(?:{ORG_SEP}{ORG_TOKEN}){{0,{ORG_MAX_TOKENS - 1}}}?"
ORG_NAME_GREEDY = f"{ORG_TOKEN}(?:{ORG_SEP}{ORG_TOKEN}){{0,{ORG_MAX_TOKENS - 1}}}"
ORG_SUFFIXES = (
    "SA|SARL|SAS|SASU|EURL|SNC|SCM|SCI|GIE|EI|SCOP|SEL|Association|Fondation|"
    "Institut|Groupe|Consortium|Fédération|Syndicat|Chambre|Mutuelle|"
    "Coopérative|Ordre|Caisse|Union|Confédération|Agence|Comité|Commission|Ligue"
)
ORG_PREFIXES = (
    "Société|Entreprise|Cabinet|Groupe|Compagnie|Association|Fondation|"
    "Institut|Consortium|Fédération|Syndicat|Chambre|Mutuelle|Coopérative|"
    "Ordre|Caisse|Union|Confédération|Agence|Comité|Commission|Ligue"
)
R_ORG_P1 = f"\\b({ORG_NAME_LAZY}){HSPACE}+({ORG_SUFFIXES})\\b"
R_ORG_P2 = f"\\b({ORG_PREFIXES}){HSPACE}+({ORG_NAME_GREEDY})"
# refinement (dry-run only): the keyword may be followed by connectors /
# an elision before the name ("Chambre de Commerce", "Agence d'Zorbal")
R_ORG_P2_KWCONN = f"\\b({ORG_PREFIXES})({ORG_SEP})({ORG_NAME_GREEDY})"

# R-REL4 option (c): sentence-initial function words (a resource in product
# code, each entry with a ``why``). Case-sensitive, capitalised form.
REL4_FUNCTION_WORDS = {
    # articles
    "Le": "article",
    "La": "article",
    "Les": "article",
    "L": "elided article (L')",
    "Un": "article",
    "Une": "article",
    "Des": "article / contracted preposition",
    "Du": "contracted preposition",
    "Au": "contracted preposition",
    "Aux": "contracted preposition",
    # personal / demonstrative pronouns
    "Je": "pronoun",
    "J": "elided pronoun (J')",
    "Il": "pronoun",
    "Elle": "pronoun",
    "Ils": "pronoun",
    "Elles": "pronoun",
    "On": "pronoun",
    "Nous": "pronoun",
    "Vous": "pronoun",
    "Ce": "demonstrative",
    "C": "elided demonstrative (C')",
    "Cela": "demonstrative",
    "Ceci": "demonstrative",
    "Cette": "demonstrative",
    "Cet": "demonstrative",
    "Ces": "demonstrative",
    # possessives
    "Notre": "possessive",
    "Nos": "possessive",
    "Votre": "possessive",
    "Vos": "possessive",
    "Leur": "possessive",
    "Leurs": "possessive",
    "Mon": "possessive",
    "Ma": "possessive",
    "Mes": "possessive",
    "Son": "possessive",
    "Ses": "possessive",
    # conjunctions
    "Et": "conjunction",
    "Mais": "conjunction",
    "Ou": "conjunction",
    "Donc": "conjunction",
    "Car": "conjunction",
    "Si": "conjunction",
    "Quand": "conjunction",
    "Comme": "conjunction",
    "Lorsque": "conjunction",
    # prepositions
    "En": "preposition",
    "Dans": "preposition",
    "Pour": "preposition",
    "Par": "preposition",
    "Sur": "preposition",
    "Avec": "preposition",
    "Sans": "preposition",
    "Chez": "preposition",
    "Selon": "preposition",
    "Après": "preposition",
    "Avant": "preposition",
    "Depuis": "preposition",
    "Pendant": "preposition",
    # common sentence adverbs
    "Ensuite": "adverb",
    "Enfin": "adverb",
    "Puis": "adverb",
    "Alors": "adverb",
    "Ainsi": "adverb",
    "Aussi": "adverb",
    "Cependant": "adverb",
    "Toutefois": "adverb",
    "Oui": "adverb",
    "Non": "adverb",
    "Bien": "adverb",
    "Tout": "determiner / adverb",
    "Tous": "determiner",
    "Chaque": "determiner",
    # interrogatives
    "Qui": "interrogative",
    "Que": "interrogative",
    "Quel": "interrogative",
    "Quelle": "interrogative",
    "Comment": "interrogative",
    "Pourquoi": "interrogative",
}

# label words of ``_filter_label_words`` (R-SPLIT alternative)
LABEL_WORDS = {"lieu", "date", "heure", "objet", "sujet", "titre", "nom", "adresse"}

# ---------------------------------------------------------------------------
# Regex variants
# ---------------------------------------------------------------------------


def _hspace_pattern(p: str) -> str:
    """R-LB on one YAML pattern: ``\\s+``/``\\s*`` → HSPACE, ``\\s`` in a class → chars."""
    p = p.replace(r"\s+", HSPACE + "+").replace(r"\s*", HSPACE + "*")
    return p.replace(r"\s", HSPACE_CHARS)


def write_variant_yaml(out_dir: Path, name: str, lb: bool, org: str | None) -> Path:
    """Copy of the bundled YAML with R-LB and/or an R-ORG variant applied."""
    cfg = yaml.safe_load(DETECTION_PATTERNS_PATH.read_text(encoding="utf-8"))
    pats = cfg["patterns"]
    if lb:
        for cat in ("titles", "last_first_names", "location_indicators"):
            for pd in pats[cat]["patterns"]:
                pd["pattern"] = _hspace_pattern(pd["pattern"])
        if org is None:
            for pd in pats["organizations"]["patterns"]:
                pd["pattern"] = _hspace_pattern(pd["pattern"])
    if org == "default":
        pats["organizations"]["patterns"][0]["pattern"] = R_ORG_P1
        pats["organizations"]["patterns"][1]["pattern"] = R_ORG_P2
    elif org == "kwconn":
        pats["organizations"]["patterns"][0]["pattern"] = R_ORG_P1
        pats["organizations"]["patterns"][1]["pattern"] = R_ORG_P2
        pats["organizations"]["patterns"].append({"pattern": R_ORG_P2_KWCONN})
    path = out_dir / f"patterns_{name}.yaml"
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return path


class VariantMatcher(RegexMatcher):
    """RegexMatcher with an optional HSPACE separator in the code patterns
    (``full_names``, geography) and the category of each match recorded."""

    def __init__(self, config_path: str, sep: str = r"\s+") -> None:
        super().__init__(config_path)
        self.sep = sep
        self.category: dict[int, str] = {}

    def match_entities(
        self, text: str, spacy_doc: Any | None = None
    ) -> list[DetectedEntity]:
        self.category = {}
        entities: list[DetectedEntity] = []
        for category, pattern_list in self.patterns.items():
            for i, pattern_def in enumerate(pattern_list):
                for match in pattern_def["regex"].finditer(text):
                    if pattern_def[
                        "require_known_first_name"
                    ] and not self._has_known_first_name(match):
                        continue
                    e = DetectedEntity(
                        text=match.group(0),
                        entity_type=pattern_def["entity_type"],
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=pattern_def["confidence"],
                        source="regex",
                    )
                    self.category[id(e)] = f"{category}#{i + 1}"
                    entities.append(e)
        if self.name_dictionary and self._is_full_names_enabled():
            for e in self._match_full_names(text):
                self.category[id(e)] = "full_names"
                entities.append(e)
        if self.geography_dictionary and self._is_geography_enabled():
            for e in self._match_geography(text, spacy_doc=spacy_doc):
                self.category[id(e)] = "geography"
                entities.append(e)
        return self._deduplicate_entities(entities)

    def _match_full_names(self, text: str) -> list[DetectedEntity]:
        assert self.name_dictionary is not None
        name_pattern = re.compile(
            r"\b([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]+(?:-[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]+)?)"
            + self.sep
            + r"([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]+)",
            re.UNICODE,
        )
        conf = self._config["patterns"]["full_names"].get("confidence", 0.65)
        out = []
        for m in name_pattern.finditer(text):
            if self.name_dictionary.is_full_name(m.group(1), m.group(2)):
                out.append(
                    DetectedEntity(
                        text=f"{m.group(1)} {m.group(2)}",
                        entity_type="PERSON",
                        start_pos=m.start(),
                        end_pos=m.end(),
                        confidence=conf,
                        source="regex",
                    )
                )
        return out

    def _match_geography(
        self, text: str, spacy_doc: Any | None = None
    ) -> list[DetectedEntity]:
        assert self.geography_dictionary is not None
        conf = self._config["patterns"]["geography_dictionary"].get("confidence", 0.6)
        token_pattern = re.compile(
            r"\b([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][a-zàâäéèêëïîôöùûü]*"
            r"(?:[-'][A-Za-zàâäéèêëïîôöùûü]+)*"
            r"(?:"
            + self.sep
            + r"(?:de|du|des|d'|en|et|la|le|les|sur)"
            + self.sep
            + r"[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜa-zàâäéèêëïîôöùûü]"
            r"[a-zàâäéèêëïîôöùûü]*(?:[-'][A-Za-zàâäéèêëïîôöùûü]+)*)*)",
            re.UNICODE,
        )
        out = []
        for m in token_pattern.finditer(text):
            cand = m.group(0)
            if self.geography_dictionary.is_location(cand):
                if spacy_doc is not None and not self._passes_pos_disambiguation(
                    spacy_doc, m.start(), m.end()
                ):
                    continue
                out.append(
                    DetectedEntity(
                        text=cand,
                        entity_type="LOCATION",
                        start_pos=m.start(),
                        end_pos=m.end(),
                        confidence=conf,
                        source="regex",
                    )
                )
        return out


# ---------------------------------------------------------------------------
# spaCy split (R-SPLIT) and dedup patches (R-REL4, R-TS)
# ---------------------------------------------------------------------------


def _has_name_word(seg: str) -> bool:
    return any(
        w[0].isupper() and w.lower() not in LABEL_WORDS
        for w in hd._WORD_RE.findall(seg)
    )


def _has_propn(sdoc: Any, start: int, end: int) -> bool:
    span = sdoc.char_span(start, end, alignment_mode="expand")
    if span is None:
        return True
    return any(
        t.pos_ in ("PROPN", "X") or (t.text.isupper() and len(t.text) > 1) or t.like_num
        for t in span
    )


def split_spacy(
    ents: list[DetectedEntity],
    text: str,
    alt: bool | str = False,
    sdoc: Any | None = None,
    trim: Callable[[list[DetectedEntity]], list[DetectedEntity]] | None = None,
) -> tuple[list[DetectedEntity], list[tuple[DetectedEntity, list[str]]]]:
    """R-SPLIT: cut each spaCy entity at every LINE_BREAK character.

    ``alt``: False = default (upper-case letter or digit); True = a
    capitalised non-label word; "pos" = default, and a segment after the
    first is kept only if spaCy tags one of its tokens PROPN/X, all-caps or
    number. ``trim``: re-apply the edge-junk trim to the segments."""
    out: list[DetectedEntity] = []
    changed: list[tuple[DetectedEntity, list[str]]] = []
    for e in ents:
        raw = text[e.start_pos : e.end_pos]
        if not LINE_BREAK_RE.search(raw):
            out.append(e)
            continue
        kept_texts = []
        segments: list[DetectedEntity] = []
        pos = 0
        for piece in LINE_BREAK_RE.split(raw):
            seg_start = pos
            pos += len(piece) + 1
            stripped = piece.strip()
            if not stripped:
                continue
            keep = (
                _has_name_word(stripped)
                if alt is True
                else any(c.isupper() or c.isdigit() for c in stripped)
            )
            s = e.start_pos + seg_start + (len(piece) - len(piece.lstrip()))
            if keep and alt == "pos" and kept_texts and sdoc is not None:
                keep = _has_propn(sdoc, s, s + len(stripped))
            if not keep:
                continue
            segments.append(
                dataclasses.replace(
                    e, text=stripped, start_pos=s, end_pos=s + len(stripped)
                )
            )
            kept_texts.append(stripped)
        out.extend(trim(segments) if trim is not None else segments)
        changed.append((e, kept_texts))
    return out, changed


# W-JOIN (STOP R decision 11): a PERSON name hard-wrapped over one line break
WRAP_PARTICLES = "(?:de|du|des|la|le|van|der|den)"
WRAP_TOKEN = f"[{_U}][{_U}{_L}]*(?:[-'’][{_U}][{_U}{_L}]*)*"
WRAP_RE = re.compile(
    f"(?:{HSPACE}+{WRAP_PARTICLES})*{HSPACE}*\r?\n{HSPACE}*"
    f"(?P<right>(?:{WRAP_PARTICLES}{HSPACE}+)*{WRAP_TOKEN})"
    f"(?={HSPACE}*(?:[,.!?)]|\\Z)|{HSPACE}+[a-zß-öø-ÿ])"
)
WRAP_TOKEN_RE = re.compile(WRAP_TOKEN)
_PROSE_WORD_RE = re.compile("(?<![\\w'’])[a-zß-öø-ÿ]")


def wrap_join(
    entities: list[DetectedEntity], text: str, fired: list[str] | None = None
) -> list[DetectedEntity]:
    """W-JOIN: extend a one-word PERSON at the end of a prose line across a
    single line break to the surname that starts the next line."""
    from gdpr_pseudonymizer.utils.french_patterns import strip_french_titles

    out = list(entities)
    for e in list(out):
        if e not in out or e.entity_type != "PERSON":
            continue
        raw = text[e.start_pos : e.end_pos]
        if not raw or not raw[-1].isalpha():
            continue
        core = strip_french_titles(raw).split()
        if len(core) != 1 or not WRAP_TOKEN_RE.fullmatch(core[0]):
            continue
        line_start = (
            max(text.rfind(c, 0, e.start_pos) for c in "\n\r\v\f\x85\u2028\u2029") + 1
        )
        if not _PROSE_WORD_RE.search(text, line_start, e.start_pos):
            continue
        m = WRAP_RE.match(text, e.end_pos)
        if m is None:
            continue
        end = m.end("right")
        joined = dataclasses.replace(e, text=text[e.start_pos : end], end_pos=end)
        out = [
            k
            for k in out
            if k is not e
            and not (
                k.entity_type == "PERSON"
                and e.start_pos <= k.start_pos
                and k.end_pos <= end
            )
        ]
        out.append(joined)
        if fired is not None:
            fired.append(f"{raw!r} -> {joined.text!r} @{e.start_pos}")
    out.sort(key=lambda x: x.start_pos)
    return out


_ORIG_CAPWORDS = hd._capitalised_words


def capwords_option(option: str) -> Callable[..., list[tuple[int, int]]]:
    """``_capitalised_words`` for REL-004 option a (keep), b (drop), c (list)."""

    def fn(context: str, regions: list[tuple[int, int]]) -> list[tuple[int, int]]:
        found = []
        for start, end in regions:
            for match in hd._WORD_RE.finditer(context, start, end):
                word = match.group()
                if not word[0].isupper():
                    continue
                if hd._TITLE_WORD_RE.fullmatch(word) or hd._TITLE_WORD_RE.fullmatch(
                    word + "."
                ):
                    continue
                if option != "b":
                    before = context[: match.start()].rstrip()
                    if before.endswith(".") and hd._is_sentence_period(
                        context, len(before) - 1
                    ):
                        if option == "a":
                            continue
                        head = re.split(r"['’]", word)[0]
                        if head in REL4_FUNCTION_WORDS:
                            continue
                found.append((match.start(), match.end()))
        return found

    return fn


_ORIG_EXACT = HybridDetector._is_exact_match


def _exact_same_type(
    self: HybridDetector, e1: DetectedEntity, e2: DetectedEntity
) -> bool:
    """MX (dry-run refinement): the merge loop's exact match also needs the
    same type; otherwise the pair goes to the different-type branch."""
    return e1.entity_type == e2.entity_type and _ORIG_EXACT(self, e1, e2)


_ORIG_BASE = HybridDetector._resolve_same_type_pair_base.__func__  # type: ignore[attr-defined]


def _rts_base(
    cls: type[HybridDetector],
    a: DetectedEntity,
    b: DetectedEntity,
    text: str | None = None,
) -> tuple[DetectedEntity | None, str]:
    """R-TS (blunt dry-run form): no C2 trim when the cut-off tail holds a
    capitalised word (outside titles / sentence starts); keep the outer."""
    result, reason = _ORIG_BASE(cls, a, b, text)
    if reason == "containment_outer_trimmed_linebreak" and result is not None:
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        outer = a if (ca[0] <= cb[0] and cb[1] <= ca[1]) else b
        if text is not None:
            words = hd._capitalised_words(text, [(result.end_pos, outer.end_pos)])
            if words:
                return outer, "containment"
    return result, reason


# ---------------------------------------------------------------------------
# Scoring and coverage
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Run:
    label: str
    dets: dict[str, list[DetectedEntity]]


def tally(docs, dets: dict[str, list[DetectedEntity]]):
    tot = {t: [0, 0, 0] for t in TYPES}
    pairs: dict[str, dict[int, DetectedEntity]] = {}
    for name, _text, gt in docs:
        tp, fp, fn = match_entities(dets[name], gt)
        pairs[name] = {id(g): d for d, g in tp}
        for t in TYPES:
            tot[t][0] += sum(1 for d, _ in tp if d.entity_type == t)
            tot[t][1] += sum(1 for d in fp if d.entity_type == t)
            tot[t][2] += sum(1 for g in fn if g.entity_type == t)
    tot["Overall"] = [sum(tot[t][i] for t in TYPES) for i in range(3)]
    return tot, pairs


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def contains(d: DetectedEntity, g: GroundTruthEntity) -> bool:
    return d.start_pos <= g.start_pos and g.end_pos <= d.end_pos


def overlaps(d: DetectedEntity, g: Any) -> bool:
    return d.start_pos < g.end_pos and g.start_pos < d.end_pos


def name_chars(dets: list[DetectedEntity], text: str) -> set[tuple[str, int]]:
    """(type, offset) of every upper-case letter or digit inside a span."""
    out = set()
    for d in dets:
        for i in range(d.start_pos, d.end_pos):
            c = text[i]
            if c.isupper() or c.isdigit():
                out.add((d.entity_type, i))
    return out


def fmt(e: Any) -> str:
    t = e.text.replace("\n", "⏎")
    if len(t) > 90:
        t = t[:87] + "..."
    return f"{e.entity_type} {t!r} @{e.start_pos}"


def report(docs, base: Run, new: Run, base_pairs, log: list[str]) -> dict[str, Any]:
    btot, _ = tally(docs, base.dets)
    ntot, npairs = tally(docs, new.dets)
    lost: collections.Counter[str] = collections.Counter()
    gained: collections.Counter[str] = collections.Counter()
    cover: collections.Counter[str] = collections.Counter()
    l2: list[str] = []
    l2b: list[str] = []
    l1_chars = 0
    l1_in_gt = 0
    l1_spans: list[str] = []
    rows: list[str] = []
    fp_rows: list[str] = []
    for name, text, gt in docs:
        bd, nd = base.dets[name], new.dets[name]
        bp, np_ = base_pairs[name], npairs[name]
        # FP detections that appear / disappear (by span and type)
        _, bfp, _ = match_entities(bd, gt)
        _, nfp, _ = match_entities(nd, gt)
        bset = {(e.entity_type, e.start_pos, e.end_pos) for e in bfp}
        nset = {(e.entity_type, e.start_pos, e.end_pos) for e in nfp}
        for e in nfp:
            if (e.entity_type, e.start_pos, e.end_pos) not in bset:
                fp_rows.append(f"    +FP [{name}] {fmt(e)} src={e.source}")
        for e in bfp:
            if (e.entity_type, e.start_pos, e.end_pos) not in nset:
                fp_rows.append(f"    -FP [{name}] {fmt(e)} src={e.source}")
        for g in gt:
            if id(g) in bp and id(g) not in np_:
                d = bp[id(g)]
                if not overlaps(d, g):
                    kind = "cross-position artefact (was matched elsewhere)"
                elif any(
                    k.entity_type == g.entity_type
                    and overlaps(k, g)
                    and _match_key(k.text, k.entity_type)
                    == _match_key(g.text, g.entity_type)
                    for k in nd
                ):
                    kind = "re-paired artefact (exact span still at position)"
                else:
                    kind = "position loss"
                lost[f"{g.entity_type}: {kind}"] += 1
                same = any(
                    k.entity_type == g.entity_type and contains(k, g) for k in nd
                )
                anyt = any(contains(k, g) for k in nd)
                cv = (
                    "same-type"
                    if same
                    else ("other type only" if anyt else "UNCOVERED")
                )
                cover[f"{g.entity_type} {cv}"] += 1
                part = [fmt(k) for k in nd if overlaps(k, g)]
                rows.append(
                    f"    LOST {g.entity_type} {g.text!r} @{g.start_pos} [{name}] "
                    f"{kind}; cover={cv}; now={part}"
                )
            elif id(g) not in bp and id(g) in np_:
                d = np_[id(g)]
                kind = "real fix" if overlaps(d, g) else "cross-position artefact"
                gained[f"{g.entity_type}: {kind}"] += 1
                was = [fmt(k) for k in bd if overlaps(k, g)]
                rows.append(
                    f"    GAINED {g.entity_type} {g.text!r} @{g.start_pos} [{name}] "
                    f"{kind}; was={was}"
                )
            # level 2 / 2b
            b_same = any(k.entity_type == g.entity_type and contains(k, g) for k in bd)
            n_same = any(k.entity_type == g.entity_type and contains(k, g) for k in nd)
            if b_same and not n_same:
                l2.append(
                    f"    L2 {g.entity_type} {g.text!r} @{g.start_pos} [{name}] "
                    f"now={[fmt(k) for k in nd if overlaps(k, g)]}"
                )
            b_any = any(contains(k, g) for k in bd)
            n_any = any(contains(k, g) for k in nd)
            if b_any and not n_any:
                l2b.append(
                    f"    L2b {g.entity_type} {g.text!r} @{g.start_pos} [{name}] "
                    f"was={[fmt(k) for k in bd if contains(k, g)]} "
                    f"now={[fmt(k) for k in nd if overlaps(k, g)]}"
                )
        # level 1: name characters a same-type span covered before, not after
        lost_chars = name_chars(bd, text) - name_chars(nd, text)
        if lost_chars:
            l1_chars += len(lost_chars)
            gt_chars = {i for g in gt for i in range(g.start_pos, g.end_pos)}
            l1_in_gt += sum(1 for _, i in lost_chars if i in gt_chars)
            for d in bd:
                hit = [
                    i
                    for t, i in lost_chars
                    if t == d.entity_type and d.start_pos <= i < d.end_pos
                ]
                if hit:
                    words = sorted(
                        {
                            m.group()
                            for m in hd._WORD_RE.finditer(text, d.start_pos, d.end_pos)
                            if any(m.start() <= i < m.end() for i in hit)
                        }
                    )
                    in_gt = any(i in gt_chars for i in hit)
                    l1_spans.append(
                        f"    L1 [{name}] baseline {fmt(d)} src={d.source}: lost "
                        f"{len(hit)} chars, words={words}{' (in an annotation)' if in_gt else ''}"
                    )
    log.append(f"\n## {new.label}")
    for t in ("Overall",) + TYPES:
        b, n = btot[t], ntot[t]
        p, r, f = prf(*n)
        log.append(
            f"  [{t}] TP={n[0]} ({n[0]-b[0]:+d}) FP={n[1]} ({n[1]-b[1]:+d}) "
            f"FN={n[2]} ({n[2]-b[2]:+d})  projected P={p:.4f} R={r:.4f} F1={f:.4f}"
        )
    log.append(f"  lost TPs: {dict(sorted(lost.items()))}")
    log.append(f"  gained TPs: {dict(sorted(gained.items()))}")
    log.append(f"  coverage of lost TPs: {dict(sorted(cover.items()))}")
    log.append(f"  level 2 (lost same-type full cover): {len(l2)}")
    log.extend(l2)
    log.append(f"  level 2b (lost last cover of any type): {len(l2b)}")
    log.extend(l2b)
    log.append(
        f"  level 1 (same-type name chars uncovered): {l1_chars} chars, "
        f"{l1_in_gt} inside an annotation, {len(l1_spans)} baseline spans"
    )
    log.extend(l1_spans)
    log.extend(rows)
    log.append(
        f"  FP changes (+{sum(r.startswith('    +') for r in fp_rows)} / -{sum(r.startswith('    -') for r in fp_rows)}):"
    )
    log.extend(fp_rows)
    return {
        "label": new.label,
        "tot": ntot,
        "delta": {t: [ntot[t][i] - btot[t][i] for i in range(3)] for t in ntot},
        "l2": len(l2),
        "l2b": len(l2b),
        "l1_chars": l1_chars,
        "l1_in_gt": l1_in_gt,
        "l1_spans": len(l1_spans),
    }


# ---------------------------------------------------------------------------
# Inventories (1.3, 1.4, 1.8)
# ---------------------------------------------------------------------------

_LOWER_WORD = re.compile(r"(?<![\w'’])([a-zß-öø-ÿ][\w'’-]*)")
_ORG_CONNECTORS = {"de", "du", "des", "d'", "d’", "la", "le", "l'", "l’", "et", "&"}
_SENT_PERIOD = re.compile(r"\.(?=\s+\S)")


def shape_of(d: DetectedEntity, text: str) -> list[str]:
    raw = text[d.start_pos : d.end_pos]
    shapes = []
    lines = [ln.strip() for ln in LINE_BREAK_RE.split(raw) if ln.strip()]
    if LINE_BREAK_RE.search(raw):
        first = lines[0] if lines else ""
        if first.endswith(",") or first.rstrip(",").lower() in {
            "cordialement",
            "bien cordialement",
            "salutations",
            "merci",
        }:
            shapes.append("signature line")
        elif first.isupper() or first.endswith(":") or len(lines) > 2:
            shapes.append("heading + org/name")
        else:
            shapes.append("name + next line")
    if d.entity_type == "ORG":
        if re.search(r"[,;:](?=\s)", raw) or any(
            hd._is_sentence_period(raw, m.start()) for m in _SENT_PERIOD.finditer(raw)
        ):
            shapes.append("sentence-long / list ORG")
        words = _LOWER_WORD.findall(raw)
        content = [w for w in words if w.lower() not in _ORG_CONNECTORS]
        if content:
            first_upper = re.match(r"\s*([A-ZÀ-Þ][\w'’-]*)\s+([a-zß-ÿ])", raw)
            if first_upper:
                shapes.append("leading word(s) before the name")
            else:
                shapes.append("clause tail / lower-case content word")
    return shapes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def to_json(e: DetectedEntity, cat: str | None = None) -> dict[str, Any]:
    d = {
        "text": e.text,
        "type": e.entity_type,
        "start": e.start_pos,
        "end": e.end_pos,
        "source": e.source,
    }
    if cat:
        d["category"] = cat
    return d


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: accuracy_runon_dryrun.py <baseline_dump.json> <out_dir>")
    dump_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    if REPO_ROOT in out_dir.parents or out_dir == REPO_ROOT:
        sys.exit("refusing to write inside the repository")
    out_dir.mkdir(parents=True, exist_ok=True)
    dump = json.loads(dump_path.read_text(encoding="utf-8"))

    det = HybridDetector()
    det.load_model("fr_core_news_lg")

    matchers = {
        "base": VariantMatcher(str(DETECTION_PATTERNS_PATH)),
        "LB": VariantMatcher(
            str(write_variant_yaml(out_dir, "LB", True, None)), sep=HSPACE + "+"
        ),
        "ORG": VariantMatcher(
            str(write_variant_yaml(out_dir, "ORG", False, "default"))
        ),
        "LB+ORG": VariantMatcher(
            str(write_variant_yaml(out_dir, "LB_ORG", True, "default")),
            sep=HSPACE + "+",
        ),
        "LB+ORGkw": VariantMatcher(
            str(write_variant_yaml(out_dir, "LB_ORGkw", True, "kwconn")),
            sep=HSPACE + "+",
        ),
    }
    for m in matchers.values():
        m.load_patterns()

    docs = _load_corpus_documents()
    spacy_pre: dict[str, list[DetectedEntity]] = {}
    regex_pre: dict[str, dict[str, list[DetectedEntity]]] = collections.defaultdict(
        dict
    )
    cats: dict[str, dict[str, dict[int, str]]] = collections.defaultdict(dict)
    premerge_json: dict[str, Any] = {}
    sdocs: dict[str, Any] = {}
    for name, text, _gt in docs:
        ents = det.spacy_detector.detect_entities(text)
        for e in ents:
            e.source = "spacy"
        spacy_pre[name] = det._trim_entity_boundaries(ents)
        sdoc = det.spacy_detector.last_doc
        sdocs[name] = sdoc
        for key, m in matchers.items():
            rx = m.match_entities(text, spacy_doc=sdoc)
            for e in rx:
                e.source = "regex"
            regex_pre[name][key] = rx
            cats[name][key] = {id(e): m.category[id(e)] for e in rx}
        premerge_json[name] = {
            "spacy": [to_json(e) for e in spacy_pre[name]],
            "regex": [
                to_json(e, cats[name]["base"][id(e)]) for e in regex_pre[name]["base"]
            ],
        }
    (out_dir / "premerge_baseline.json").write_text(
        json.dumps(premerge_json, ensure_ascii=False, indent=0), encoding="utf-8"
    )

    def compose(
        rx_key: str = "base",
        split: str | None = None,
        rel4: str = "a",
        rts: bool = False,
        mx: bool = False,
        segtrim: bool = False,
        late: bool = False,
        wjoin: bool = False,
    ) -> dict[str, list[DetectedEntity]]:
        hd._capitalised_words = capwords_option(rel4)  # type: ignore[assignment]
        if mx:
            HybridDetector._is_exact_match = _exact_same_type  # type: ignore[method-assign]
        if rts:
            HybridDetector._resolve_same_type_pair_base = classmethod(_rts_base)  # type: ignore[method-assign,assignment]
        try:
            out = {}
            for name, text, _ in docs:
                sp = copy.deepcopy(spacy_pre[name])
                if split:
                    sp, _ = split_spacy(
                        sp,
                        text,
                        alt={"alt": True, "pos": "pos"}.get(split, False),
                        sdoc=sdocs[name],
                        trim=det._trim_entity_boundaries if segtrim else None,
                    )
                rx = copy.deepcopy(regex_pre[name][rx_key])
                merged = det._merge_entities(sp, rx, text)
                if late:
                    # R-SPLIT-late (dry-run refinement): split every merged
                    # span that still crosses a line break, after the dedup,
                    # then all four post-filters again
                    merged, changed = split_spacy(
                        merged,
                        text,
                        trim=det._trim_entity_boundaries if segtrim else None,
                    )
                    if changed:
                        merged = det._filter_label_words(
                            det._filter_title_only_entities(merged)
                        )
                        merged = det._filter_org_roles(merged, text)
                        merged = det._dedup_same_type_overlaps(merged, text)
                    merged.sort(key=lambda e: e.start_pos)
                if wjoin:
                    merged = wrap_join(merged, text, wj_fired)
                out[name] = merged
            return out
        finally:
            hd._capitalised_words = _ORIG_CAPWORDS  # type: ignore[assignment]
            HybridDetector._resolve_same_type_pair_base = classmethod(_ORIG_BASE)  # type: ignore[method-assign,assignment]
            HybridDetector._is_exact_match = _ORIG_EXACT  # type: ignore[method-assign]

    log: list[str] = []
    wj_fired: list[str] = []

    # --- 1.2: re-merge reproduces the dump -------------------------------
    base_dets = compose()
    mismatches = 0
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
            mismatches += 1
            log.append(f"  MISMATCH {name}: {set(got) ^ set(want)}")
    n_det = sum(len(v) for v in base_dets.values())
    log.insert(
        0,
        f"# 1.2 re-merge of pre-merge lists vs dump: {n_det} detections, "
        f"{mismatches} documents differ",
    )
    base = Run("baseline (re-merged)", base_dets)
    btot, base_pairs = tally(docs, base_dets)
    log.append(f"  baseline tally: {btot}")

    # --- 1.3 / 1.4 / 1.8 inventories -------------------------------------
    log.append("\n# 1.4 run-on inventory (baseline dump)")
    inv: collections.Counter[str] = collections.Counter()
    inv_rows: list[str] = []
    for name, text, gt in docs:
        rx_cat = {
            (e.start_pos, e.end_pos, e.entity_type): cats[name]["base"][id(e)]
            for e in regex_pre[name]["base"]
        }
        for d in base_dets[name]:
            raw = text[d.start_pos : d.end_pos]
            crosses = bool(LINE_BREAK_RE.search(raw))
            src = d.source
            if src == "regex":
                cat = rx_cat.get((d.start_pos, d.end_pos, d.entity_type))
                if cat is None:  # shortened by the dedup (V3 / C2)
                    cat = next(
                        (
                            f"{c} (trimmed by dedup)"
                            for (s0, _e0, t0), c in rx_cat.items()
                            if s0 == d.start_pos and t0 == d.entity_type
                        ),
                        "?",
                    )
                src = f"regex:{cat}"
            shapes = shape_of(d, text)
            is_regex_org = src.startswith("regex:organizations")
            if crosses or (is_regex_org and len(shapes) > 0):
                for s in shapes or ["(none)"]:
                    inv[
                        f"{d.entity_type} | {src} | {'LB' if crosses else 'same line'} | {s}"
                    ] += 1
                inv_rows.append(f"    [{name}] {fmt(d)} src={src} shapes={shapes}")
    for k, v in sorted(inv.items()):
        log.append(f"  {v:4d}  {k}")
    log.extend(inv_rows)

    log.append("\n# 1.4b pre-merge regex organizations spans with a run-on shape")
    pre_inv: collections.Counter[str] = collections.Counter()
    for name, text, _gt in docs:
        for e in regex_pre[name]["base"]:
            cat = cats[name]["base"][id(e)]
            if not cat.startswith("organizations"):
                continue
            shapes = shape_of(e, text)
            if shapes:
                for sh in shapes:
                    pre_inv[f"{cat} | {sh}"] += 1
                log.append(f"    [{name}] {fmt(e)} {cat} shapes={shapes}")
    n_org = sum(
        1
        for name, _t, _g in docs
        for e in regex_pre[name]["base"]
        if cats[name]["base"][id(e)].startswith("organizations")
    )
    log.append(f"  pre-merge regex organizations spans: {n_org}")
    for k, v in sorted(pre_inv.items()):
        log.append(f"  {v:4d}  {k}")

    log.append("\n# 1.3 line-break misses (baseline)")
    lbm: collections.Counter[str] = collections.Counter()
    lbm_rows: list[str] = []
    for name, text, gt in docs:
        tp, fp, fn = match_entities(base_dets[name], gt)
        for g in fn:
            for d in base_dets[name]:
                if overlaps(d, g) and LINE_BREAK_RE.search(
                    text[d.start_pos : d.end_pos]
                ):
                    same = (
                        "same type" if d.entity_type == g.entity_type else "other type"
                    )
                    lbm[f"FN {g.entity_type} <- {d.source} ({same})"] += 1
                    lbm_rows.append(
                        f"    FN [{name}] {g.entity_type} {g.text!r} @{g.start_pos} <- {fmt(d)} src={d.source}"
                    )
                    break
        for d in fp:
            if LINE_BREAK_RE.search(text[d.start_pos : d.end_pos]) and any(
                g.entity_type == d.entity_type and overlaps(d, g) for g in gt
            ):
                lbm[
                    f"FP {d.entity_type} {d.source} (overlaps same-type annotation)"
                ] += 1
                lbm_rows.append(f"    FP [{name}] {fmt(d)} src={d.source}")
    for k, v in sorted(lbm.items()):
        log.append(f"  {v:4d}  {k}")
    log.extend(lbm_rows)

    log.append("\n# 1.8 annotations containing a line break (wrapped names)")
    wrapped = [
        f"    [{n}] {g.entity_type} {g.text!r}"
        for n, _t, gt in docs
        for g in gt
        if LINE_BREAK_RE.search(g.text)
    ]
    log.append(f"  count={len(wrapped)}")
    log.extend(wrapped)

    # --- 1.5 / 1.6 dry-runs ----------------------------------------------
    variants = [
        ("R-LB", dict(rx_key="LB")),
        ("R-ORG", dict(rx_key="ORG")),
        ("R-LB + R-ORG", dict(rx_key="LB+ORG")),
        ("R-SPLIT default", dict(split="default")),
        ("R-SPLIT alternative", dict(split="alt")),
        (
            "Composed default (R-LB + R-ORG + R-SPLIT default)",
            dict(rx_key="LB+ORG", split="default"),
        ),
        (
            "Composed alt (R-LB + R-ORG + R-SPLIT alternative)",
            dict(rx_key="LB+ORG", split="alt"),
        ),
        ("Composed default + R-TS", dict(rx_key="LB+ORG", split="default", rts=True)),
        ("Baseline + R-TS", dict(rts=True)),
        ("REL-004 (b) drop exception, alone", dict(rel4="b")),
        ("REL-004 (c) function words, alone", dict(rel4="c")),
        (
            "Composed default + REL-004 (b)",
            dict(rx_key="LB+ORG", split="default", rel4="b"),
        ),
        (
            "Composed default + REL-004 (c)",
            dict(rx_key="LB+ORG", split="default", rel4="c"),
        ),
        (
            "Refinement: composed default with ORG keyword+connector",
            dict(rx_key="LB+ORGkw", split="default"),
        ),
        ("MX alone (type-aware exact match in the merge loop)", dict(mx=True)),
        ("R-LB + R-ORG + MX", dict(rx_key="LB+ORG", mx=True)),
        ("Composed default + MX", dict(rx_key="LB+ORG", split="default", mx=True)),
        (
            "Composed default + MX + segment trim",
            dict(rx_key="LB+ORG", split="default", mx=True, segtrim=True),
        ),
        ("R-SPLIT late alone (post-dedup)", dict(late=True)),
        ("R-LB + R-ORG + R-SPLIT late", dict(rx_key="LB+ORG", late=True)),
        ("R-LB + R-ORG + R-SPLIT late + MX", dict(rx_key="LB+ORG", late=True, mx=True)),
        (
            "R-LB + R-ORG + R-SPLIT late + segment trim",
            dict(rx_key="LB+ORG", late=True, segtrim=True),
        ),
        (
            "FINAL: R-LB + R-ORG + R-SPLIT late + segment trim + REL-004 (b) + W-JOIN",
            dict(rx_key="LB+ORG", late=True, segtrim=True, rel4="b", wjoin=True),
        ),
        (
            "R-LB + R-ORG + R-SPLIT late + segment trim + MX",
            dict(rx_key="LB+ORG", late=True, segtrim=True, mx=True),
        ),
        (
            "R-LB + R-ORG + R-SPLIT late + REL-004 (b)",
            dict(rx_key="LB+ORG", late=True, rel4="b"),
        ),
        (
            "R-LB + R-ORG + R-SPLIT late + REL-004 (c)",
            dict(rx_key="LB+ORG", late=True, rel4="c"),
        ),
        ("R-SPLIT POS alone", dict(split="pos")),
        (
            "Composed POS (R-LB + R-ORG + R-SPLIT POS)",
            dict(rx_key="LB+ORG", split="pos"),
        ),
        ("Composed POS + MX", dict(rx_key="LB+ORG", split="pos", mx=True)),
        (
            "Composed POS + MX + segment trim",
            dict(rx_key="LB+ORG", split="pos", mx=True, segtrim=True),
        ),
    ]
    summary = []
    for label, kw in variants:
        run = Run(label, compose(**kw))  # type: ignore[arg-type]
        summary.append(report(docs, base, run, base_pairs, log))

    # --- carried losses (1.7) -------------------------------------------
    log.append(
        "\n# 1.7 carried losses: annotations uncovered (any type) in the baseline"
    )
    carried_variants = {
        "composed default": compose(rx_key="LB+ORG", split="default"),
        "R-LB + R-ORG + R-SPLIT late": compose(rx_key="LB+ORG", late=True),
    }
    for name, text, gt in docs:
        for g in gt:
            if g.text in ("TechSolutions France SAS", "Pierre", "BRS"):
                b_any = [fmt(k) for k in base_dets[name] if contains(k, g)]
                if b_any:
                    continue
                c_any = {
                    lbl: [fmt(k) for k in cv[name] if contains(k, g)]
                    for lbl, cv in carried_variants.items()
                }
                ov = [fmt(k) for k in base_dets[name] if overlaps(k, g)]
                ctx = text[max(0, g.start_pos - 60) : g.end_pos + 40].replace("\n", "⏎")
                log.append(
                    f"  [{name}] {g.entity_type} {g.text!r} @{g.start_pos}: baseline "
                    f"overlapping={ov}; cover after={c_any}\n      ctx={ctx!r}"
                )

    # --- REL-004 probe ----------------------------------------------------
    log.append(
        "\n# REL-004 probe (QA 10.2): 'Nous avons conclu. Quentrix, Zorbalia Conseil'"
    )
    ptext = "Nous avons conclu. Quentrix, Zorbalia Conseil"
    o0 = ptext.index("conclu")
    i0 = ptext.index("Zorbalia")
    for opt in ("a", "b", "c"):
        hd._capitalised_words = capwords_option(opt)  # type: ignore[assignment]
        try:
            inner = DetectedEntity(ptext[i0:], "ORG", i0, len(ptext), source="spacy")
            outer = DetectedEntity(ptext[o0:], "ORG", o0, len(ptext), source="regex")
            res = det._merge_entities([inner], [outer], ptext)
        finally:
            hd._capitalised_words = _ORIG_CAPWORDS  # type: ignore[assignment]
        covered = any(e.start_pos <= ptext.index("Quentrix") < e.end_pos for e in res)
        log.append(
            f"  option ({opt}): {[e.text for e in res]}; 'Quentrix' covered={covered}"
        )

    # --- summary table ----------------------------------------------------
    print(log[0])
    print(f"baseline: {btot}")
    print(
        "\n| Rule / composition | PERSON dTP/dFP/dFN | LOCATION | ORG | Overall P/R/F1 | L2 | L2b | L1 chars (in GT) / spans |"
    )
    for s in summary:
        d = s["delta"]
        p, r, f = prf(*s["tot"]["Overall"])
        cells = " | ".join(f"{d[t][0]:+d}/{d[t][1]:+d}/{d[t][2]:+d}" for t in TYPES)
        print(
            f"| {s['label']} | {cells} | {p:.4f}/{r:.4f}/{f:.4f} | {s['l2']} | "
            f"{s['l2b']} | {s['l1_chars']} ({s['l1_in_gt']}) / {s['l1_spans']} |"
        )
    print(f"W-JOIN fired {len(wj_fired)} times on the main corpus: {wj_fired}")
    report_path = out_dir / "dryrun_report.txt"
    report_path.write_text("\n".join(log), encoding="utf-8")
    print(f"\nfull report -> {report_path}")


if __name__ == "__main__":
    main()
