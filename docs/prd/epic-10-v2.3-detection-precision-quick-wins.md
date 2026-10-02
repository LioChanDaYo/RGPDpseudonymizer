# Epic 10: v2.3 — Detection Precision Quick Wins - Brownfield Enhancement

**Epic Goal:** Raise detection precision and make the accuracy benchmark trustworthy with local, deterministic changes to the hybrid detector and the ground-truth corpus, without lowering recall. The user-facing value is fewer false entities to reject during the (mandatory) validation step and a benchmark whose numbers can be believed.

**Target Release:** v2.3.0 candidate. **No release is part of this epic.** v2.3.0 ships only on Lionel's explicit go, through a separate release story.
**Duration:** Estimated 4-6 weeks (10.1 is annotation-labor-bound)
**Predecessor:** v2.2.0 + accuracy scorer fix (#77), commit `fceef65`
**Successor:** Epic 9 (v3.0) starts from this epic's merged close-out baseline.

---

## Existing System Context

- **Current relevant functionality:** `HybridDetector` (`gdpr_pseudonymizer/nlp/hybrid_detector.py`) merges spaCy `fr_core_news_lg` entities with regex detections (`regex_matcher.py`, `resources/detection_patterns.yaml`), trims span edges, filters title-only and label-word entities, and logs `ambiguous_entity_added reason=partial_overlap` when overlapping detections are both kept. Every detection is reviewed by the user in the mandatory validation step (CLI and GUI).
- **Technology stack:** Python 3.10-3.12, Poetry, spaCy 3.7 (`fr_core_news_lg`), YAML regex patterns, French name and geography dictionaries (`name_dictionary.py`, `geography_dictionary.py`, `resources/french_names.json`, `resources/french_geography.json`), pytest, GitHub Actions.
- **Integration points:**
  - `gdpr_pseudonymizer/nlp/hybrid_detector.py` — merge, overlap handling, post-filters
  - `gdpr_pseudonymizer/nlp/regex_matcher.py` and `gdpr_pseudonymizer/resources/detection_patterns.yaml` — regex layer, `last_first_names` pattern
  - `gdpr_pseudonymizer/nlp/name_dictionary.py`, `geography_dictionary.py` — lexicons used by the new rules
  - `tests/accuracy/conftest.py` (`match_entities`, `_match_key`) and `tests/accuracy/test_ner_accuracy_validation.py` — benchmark
  - `tests/test_corpus/annotations/*.json` — ground truth; `scripts/auto_annotate_corpus.py` — the auto-annotator that produced part of it
  - `.github/workflows/accuracy.yaml` — CI accuracy run, `accuracy-results` artifact (`accuracy-output.txt`)

---

## Product Constraints (non-negotiable)

These apply to every story in this epic. A story that cannot meet its goal inside them stops and goes back to Lionel; it does not relax them.

1. **Local NLP only.** No LLM, no generative model, no API call, no cloud service, no telemetry. Every change is a deterministic rule, lexicon or pattern that runs offline.
2. **No encoder NER models.** Introducing a transformer/encoder NER model (e.g. CamemBERT-NER) is a Lionel decision that belongs to Epic 9. It must not be introduced in this epic, including as an optional dependency or experiment committed to the repo.
3. **Mandatory human validation stays.** No auto-accept mode, no `--no-validate`, no confidence-based skipping. Precision gains reduce the reviewer's workload; they do not replace the reviewer.
4. **No user data** for training, tuning or evaluation. All corpus and held-out documents are synthetic.
5. **Recall over precision.** Missing a real person is worse than showing an extra candidate. Any drop in overall recall or in any per-type recall needs Lionel's sign-off (gate G3).
6. **No public accuracy claim without CI evidence.** Every number that reaches README, FAQ, docs, CHANGELOG or the QA report comes from a cited CI accuracy run (gate G1).

---

## Evidence Base

### Baseline

Measured at commit `fceef65`, CI run `37013929807`, with the app-normalized scorer (see `docs/qa/ner-accuracy-report.md`, "Scorer aligned with app normalization (2026-10-02)").

| | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Overall | 48.42% | 73.98% | **58.53%** | 1,285 | 1,369 | 452 |
| PERSON | 70.34% | 75.71% | 72.93% | 1,122 | 473 | 360 |
| LOCATION | 30.14% | 88.71% | 44.99% | 110 | 255 | 14 |
| ORG | 7.64% | 40.46% | 12.85% | 53 | 641 | 78 |

**Benchmark:** `pytest tests/accuracy -m accuracy -s` — 25 French documents, 1,737 annotated entities. Scorer: `match_entities` in `tests/accuracy/conftest.py` — exact text+type, one-to-one, after `_match_key()` (`strip_french_titles` on all types, `strip_french_prepositions` on LOCATION).

### Sized Findings (error analysis at `fceef65`)

| # | Finding | Size | Addressed by |
|---|---------|------|--------------|
| F1 | Duplicate spans overlapping a correctly matched same-type detection ("Jean-Luc" next to "Jean-Luc Moreau", "à Paris" next to "Paris"); `HybridDetector` logs `ambiguous_entity_added reason=partial_overlap` | 158 FP | 10.2 |
| F2 | Job titles and role acronyms detected as ORG: CTO 29, CFO 18, COMEX 16, DPO 15, RSSI 11, VP Engineering 10, DRH 8, … A role filter loses only 6 "TPs", all junk annotations ("VP Europe") | 138 ORG FP | 10.2 (filter), 10.1 (junk annotations) |
| F3 | Truncated PERSON annotations from the auto-annotator: "Luc Moreau" ×16 for "Jean-Luc Moreau", "Charles Le", "Marc Bideau", "Anne-", "Marie-", "Rousseau, Responsable", "Paribas, Crédit" | 96 PERSON annotations | 10.1 |
| F4 | Junk PERSON annotations: "Directeur Commercial" 6, "Lancement Projet" 5, "Validation Architecture" 5, "Palo Alto", "Société Générale", … | not yet counted in full | 10.1 |
| F5 | Real organisations missing from the annotations (CNIL, ANSSI, Deloitte, …), so part of the 641 ORG FP are correct detections. ORG precision is not measurable until this is fixed | not yet counted in full | 10.1 |
| F6 | LOCATION noise: "Wavestone" 10, "CONFORME" 10, "CC" 4, "US", "Équipe", "Constat", "SecNumCloud", "Pentest", "à Dr" | subset of 255 LOCATION FP | 10.3 |
| F7 | Name boundary errors: particles ("Jean-Charles Le Goff", "Sylvie van der Werf", "Chasseloup de Laubat"), "Mme Sarah Mc…" truncation, trailing roles (", Responsable") | not yet counted in full | 10.3 |
| F8 | Greetings in `email_chain.txt`: "Laurent, Marie," matched as one person; bare "Marie," line and "Bonne initiative Laurent." missed | small, high user visibility | 10.4 |
| F9 | ORG split: "Microsoft France" detected as two pieces | small | 10.4 |
| F10 | ORG recall: brands missed (OVHcloud, TechCorp, Microsoft Azure, Partech, Kima Ventures, EY) | part of 78 ORG FN | **Not in scope** (see Out of Scope) |

**Arithmetic estimate — NOT a measurement, NOT a target, NOT a claim:** removing the 158 duplicate FP (F1) and the 138 role FP (F2) from the baseline counts gives P ≈ 54.5% and F1 ≈ 63%. This only sizes the opportunity. It must not appear in any doc, release note or story as an expected result; only G1 runs count.

---

## Gates

The following block is normative and is referenced by every story's acceptance criteria.

- **G1 — Metric evidence.** Every reported metric comes from a CI accuracy run on the story branch: `gh workflow run accuracy.yaml --ref <branch> -f reason="<story id>"`. Cite the run ID. Paste the `[Overall]`, `[PERSON]`, `[LOCATION]`, `[ORG]` lines from the `accuracy-results` artifact (`accuracy-output.txt`). Numbers typed by the dev agent without a run ID do not count.
- **G2 — QA verifies independently.** The QA agent downloads the cited run's artifact itself (`gh run download <id> -n accuracy-results`) and checks the numbers match the story's claims. QA never accepts the dev's text as evidence.
- **G3 — Recall guard.** Overall recall and each per-type recall must not drop versus the previous merged baseline. Any drop: stop and ask Lionel.
- **G4 — Attribution.** Changes to annotations/scorer and changes to detection code are never in the same PR. Benchmark-driven deltas and detector-driven deltas are reported separately.
- **G5 — Held-out check.** Once the held-out set exists (story 10.1), every detector story also reports held-out P/R/F1. A gain on the main corpus with a loss on held-out is a red flag for overfitting: report it.
- **G6 — Normal quality.** black, ruff, mypy clean; unit tests for every new rule; full CI green (one re-run allowed for the known macOS flake).
- **G7 — Docs.** If a story changes the headline numbers, it updates README/README.fr, `docs/faq*.md`, `docs/index*.md`, `docs/tutorial*.md`, the QA report and CHANGELOG `[Unreleased]`, all from the G1 run.

### Epic 10 G7 interpretation (Lionel, 2026-10-02)

Decided by Lionel, 2026-10-02. This note interprets the gates for Epic 10; the gate text above is unchanged.

- **G7 — per story vs. close-out.** The QA report (`docs/qa/ner-accuracy-report.md`) records the before/after at every story (10.1 marked "benchmark repair, same detector"), and each story adds its CHANGELOG `[Unreleased]` entry. README/README.fr, `docs/faq*.md`, `docs/index*.md` and `docs/tutorial*.md` change once, at Epic 10 close-out, from the final G1 run — not per story.
- **G3 under a ground-truth change (10.1).** G3 does not block 10.1. 10.1's close-out run becomes the new baseline. Every per-type recall drop between the old and new ground truth is listed with its cause (e.g. "+N ORG annotations added") in the story and the PR. G3 applies strictly from 10.2 onwards.

---

## Enhancement Details

- **What's being changed:** (1) the benchmark is repaired against written annotation guidelines and gains a held-out set; (2) `HybridDetector` gets a same-type overlap rule and an ORG role filter; (3) LOCATION noise filters and PERSON boundary rules for particles, Mc/Mac and trailing roles; (4) salutation-aware first-name detection and ORG + country merging.
- **How it integrates:** all detector changes are post-processing steps or patterns inside the existing `HybridDetector` pipeline and its YAML/JSON resources. No public API, CLI flag, GUI screen, mapping-table schema or file format changes.
- **Success criteria:**
  - Every story closes with a G1 run, G2 verification, no unapproved recall drop (G3) and held-out numbers (G5, from 10.2 on).
  - Overall precision on the repaired benchmark rises over the 10.1 close-out baseline by the end of 10.4, measured by G1 runs. No numeric precision target is set: the arithmetic estimate above is not a target.
  - The ground truth follows written, Lionel-approved guidelines, and the held-out set is scored separately.

---

## Epic 10 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 10.1: Benchmark Repair + Held-Out Set | HIGH | 1.5-2.5 weeks | F3, F4, F5, F2 (junk) | Draft |
| 10.2: Same-Type Overlap Dedup + ORG Role Filter | HIGH | 1 week | F1, F2 | Draft |
| 10.3: LOCATION Noise + Name Boundaries | MED | 1 week | F6, F7 | Draft |
| 10.4: Greetings + Org-Plus-Country | MED | 0.5-1 week | F8, F9 | Draft |

**Total Estimated Duration:** 4-6 weeks

---

## Story 10.1: Benchmark Repair + Held-Out Set

**As a** maintainer deciding whether a detector change helped,
**I want** ground truth that follows written rules and a held-out set that was never used for tuning,
**so that** precision and recall numbers reflect the detector and not annotation bugs, and overfitting to the 25-document corpus is visible.

**Priority:** HIGH — Every later story is measured against this story's baseline.
**Change type:** Benchmark-only (G4). No file under `gdpr_pseudonymizer/` changes in this story.

### Context

Part of the ground truth was produced by `scripts/auto_annotate_corpus.py` and accepted without full review. The error analysis at `fceef65` found 96 truncated PERSON annotations (F3), junk PERSON annotations (F4), real organisations missing from the annotations (F5) and junk ORG annotations such as "VP Europe" (F2). Until this is fixed, ORG precision cannot be measured and a correct detector change can score as a regression.

### Sequence (mandatory order)

1. Draft `tests/test_corpus/annotations/GUIDELINES.md`.
2. **Guidelines approval stop — Lionel approves the guidelines.** The draft goes to Lionel. No annotation file (existing or held-out) is created or edited before his approval is recorded in the story's Dev Notes (date + any amendments). Annotator and held-out authoring were decided by Lionel on 2026-10-02 (AC11).
3. Diagnose the auto-annotator bug; fix or retire `scripts/auto_annotate_corpus.py`.
4. Apply the approved guidelines to the 25 existing annotation files.
5. Write and annotate the held-out documents by hand under the approved guidelines.
6. Extend the accuracy suite to score the held-out set separately.
7. G1 run and before/after report.

### Acceptance Criteria

1. **AC1 — Guidelines drafted:** `tests/test_corpus/annotations/GUIDELINES.md` exists and states, with examples drawn from the corpus:
   - Titles (M., Mme, Dr, Pr, Me, …) are excluded from PERSON spans.
   - Hyphenated first names and particle surnames are annotated whole ("Jean-Luc Moreau", "Jean-Charles Le Goff", "Sylvie van der Werf", "Chasseloup de Laubat").
   - Job titles are not PERSON ("Directeur Commercial") and are not ORG.
   - Roles and role acronyms (CTO, CFO, DPO, RSSI, DRH, COMEX, "VP Europe", "VP Engineering") are not ORG.
   - What counts as ORG (companies, public bodies such as CNIL and ANSSI, firms such as Deloitte, schools, banks) and how brand + country is annotated ("Microsoft France").
   - What counts as LOCATION (granularity, prepositions excluded, company names never LOCATION, US/USA and country abbreviations).
   - How "Last, First" and salutation lines ("Laurent, Marie,") are annotated.
2. **AC2 — Guidelines approval stop respected:** Lionel's approval of the guidelines is recorded in the story before AC4 or AC5 work starts. Every later annotation edit cites the guideline rule it applies. Rules not in the approved guidelines are not applied; if a new case comes up, it goes back to Lionel as a guideline amendment.
3. **AC3 — Auto-annotator:** the root cause of the truncations (F3) is identified and written in the story. `scripts/auto_annotate_corpus.py` is either fixed (with a unit test reproducing a truncation such as "Jean-Luc Moreau" → "Luc Moreau") or retired (deleted or clearly marked as not to be used, with the reason). Either way, it is never used to produce held-out annotations.
4. **AC4 — Existing corpus repaired, per the approved guidelines:**
   - The 96 truncated PERSON annotations are corrected to the full span (or removed where the guidelines say the span is not an entity).
   - Junk labels are removed (F4 examples, comma artefacts such as "Rousseau, Responsable" and "Paribas, Crédit", role ORGs such as "VP Europe").
   - Missing real ORG and LOCATION annotations are added (CNIL, ANSSI, Deloitte and every other instance found).
   - `tests/test_corpus/annotations/README.md` entity counts are updated to the new totals.
   - A change log (counts per document: corrected / removed / added, per type) is attached to the story.
5. **AC5 — Held-out set:** at least 5 new documents with annotations (authoring and annotation as decided under AC11):
   - Synthetic French business and interview style text (no user data, no copy of real people's records), seeded with known hard cases: particles, Mc/Mac names, greetings, role acronyms, foreign places. The text may be written by an LLM agent; Lionel reviews the text before annotation.
   - Annotated under the approved guidelines, not pre-annotated by the detector or the auto-annotator.
   - Stored apart from the main corpus (the story fixes the exact location, e.g. `tests/test_corpus/held_out/`), and documented as never used for tuning: detector stories may read held-out aggregate metrics, not held-out FP/FN lists, while designing rules.
6. **AC6 — Held-out scoring:** the accuracy suite scores the held-out set separately and prints labelled lines in `accuracy-output.txt` (e.g. `[HELD-OUT Overall]`, `[HELD-OUT PERSON]`, `[HELD-OUT LOCATION]`, `[HELD-OUT ORG]`). Held-out entities are not added to the main corpus totals.
7. **AC7 — Before/after report:** the QA report gets a new section with the same detector scored on the old and the new ground truth: overall and per-type P/R/F1/TP/FP/FN, both from G1 runs (the "before" can be run `37013929807`), labelled as a benchmark-only delta, plus the first held-out numbers.
8. **AC8 — G7 for a benchmark-only change.** Decided by Lionel, 2026-10-02: 10.1 records its before/after in the QA report, marked "benchmark repair, same detector", and adds a CHANGELOG `[Unreleased]` entry. README/README.fr, FAQ, docs index and tutorials are not updated in 10.1; they change once, at Epic 10 close-out, from the final G1 run (see "Epic 10 G7 interpretation").
9. **AC9 — G3 on a ground-truth change.** Decided by Lionel, 2026-10-02: G3 does not block 10.1. 10.1's close-out run becomes the new baseline. Every per-type recall drop between the old and new ground truth is listed with its cause (e.g. "+N ORG annotations added") in the story and the PR. G3 applies strictly from 10.2 onwards.
10. **AC10 — Gates:** G1, G2, G3 (as AC9: not blocking for 10.1), G4 (annotation/scorer changes only, no detector code; the scorer change for held-out scoring may share the PR with annotation changes since both are benchmark-side), G6, G7 (as AC8) apply. G5 starts applying from story 10.2.
11. **AC11 — Annotator and held-out authoring.** Decided by Lionel, 2026-10-02 (recorded in Dev Notes):
   - Annotator: the dev agent drafts the corrections to the 25 existing annotation files and the held-out annotations, applying the approved guidelines only. Lionel reviews the annotation diff before merge.
   - Held-out authoring: an LLM agent may write the text of the ≥5 held-out documents (synthetic French business/interview style, seeded with known hard cases: particles, Mc/Mac names, greetings, role acronyms, foreign places). Lionel reviews the text before annotation. Held-out annotations are never pre-annotated by the detector or the auto-annotator.
   - No AC4 or AC5 work starts before the guidelines are approved.

### Integration Points

- `tests/test_corpus/annotations/` — `GUIDELINES.md` (new), all 25 `*.json`, `README.md`
- held-out documents and annotations (new location defined by the story)
- `tests/accuracy/conftest.py`, `tests/accuracy/test_ner_accuracy_validation.py` — held-out scoring
- `scripts/auto_annotate_corpus.py` (fix or retire)
- `docs/qa/ner-accuracy-report.md`

### Estimated Effort: 1.5-2.5 weeks (annotation review is the long pole; the guidelines approval stop adds Lionel's review latency)

---

## Story 10.2: Same-Type Overlap Dedup + ORG Role Filter

**As a** user reviewing detected entities,
**I want** one candidate per name instead of overlapping fragments, and no job titles offered as organisations,
**so that** I reject fewer false candidates during validation.

**Priority:** HIGH — The two largest sized FP sources (F1: 158, F2: 138).
**Change type:** Detector-only (G4). Baseline: 10.1 merged close-out.

### Context

`HybridDetector._merge_entities` keeps both detections when spans partially overlap and logs `ambiguous_entity_added reason=partial_overlap`. When both have the same type, the user sees "Jean-Luc" and "Jean-Luc Moreau", or "à Paris" and "Paris", and the scorer counts one of them as FP. Separately, spaCy tags role acronyms and job titles as ORG.

### Acceptance Criteria

1. **AC1 — Overlap rule defined in the story before coding.** The Dev Notes state the rule precisely. Default rule, to be refined only with evidence from the main corpus:
   - Applies only to detections of the **same entity type** whose character spans overlap.
   - Spans are compared after app normalization, the same as the scorer's `_match_key` (`strip_french_titles` on all types, `strip_french_prepositions` on LOCATION), not after `_trim_entity_boundaries` (which only runs on spaCy entities).
   - If one span contains the other, keep the containing span.
   - If spans partially overlap and neither contains the other, keep the spaCy span; if both come from the same source, keep the longer span.
   - Ties are resolved deterministically (e.g. earliest start).
   - Overlaps between **different** types keep today's behaviour (both kept, logged); out of scope.
2. **AC2:** The rule is implemented in `HybridDetector`; the `partial_overlap` log is kept for the different-type case, and a distinct log event records same-type dedup decisions (kept span, dropped span, reason) without logging entity text beyond what the existing logs already do.
3. **AC3 — ORG role filter:** ORG detections whose whole normalized span is a job title or role acronym are dropped. The list lives in a resource file (not hard-coded), covers at least CEO, CTO, CFO, COO, CIO, CDO, DSI, DAF, DRH, DPO, RSSI, COMEX, CODIR, bare "VP", "VP/Vice-président + function" forms ("VP Engineering") and "VP/Vice-président + region/country" forms ("VP Europe", "VP France"), and is matched case-sensitively for acronyms. Real organisations that look like acronyms (CNIL, ANSSI, BNP, EY) are not in the list; a unit test proves they survive.
4. **AC4:** Unit tests for each rule branch (containment, partial overlap, same-source tie, different-type untouched, role drop, real-acronym kept).
5. **AC5 — Gates:** G1 (main and held-out lines), G2, G3 versus the 10.1 baseline, G4 (no annotation or scorer change in this PR), G5, G6 (plus NFR1 timing unchanged: existing perf test green), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, regardless of G7, including an upgrade note on pseudonym continuity (see Risk Mitigation). The story reports the measured FP reduction attributable to each of the two rules (one G1 run with both, plus the dedup-only or filter-only split if the dev runs it; every number cited with its run ID), and how many of the detections dropped by the overlap rule were TPs in the previous (10.1 close-out) run.

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py` — `_merge_entities`, new ORG role post-filter
- `gdpr_pseudonymizer/resources/` — role list (new or in `detection_patterns.yaml`)
- `tests/unit/` — new rule tests

### Estimated Effort: 1 week

---

## Story 10.3: LOCATION Noise + Name Boundaries

**As a** user reviewing detected entities,
**I want** common words and company names not offered as places, and names with particles or "Mc/Mac" detected whole,
**so that** I reject fewer false places and do not have to repair cut names by hand.

**Priority:** MEDIUM
**Change type:** Detector-only (G4). Baseline: 10.2 merged close-out.

### Acceptance Criteria

1. **AC1 — All-caps common words:** an all-caps LOCATION detection is dropped only on positive evidence that it is a common word (hit in a common-word stoplist / lexical check, e.g. "CONFORME", "CC"), never merely because it is absent from `french_geography.json`. All-caps real places survive: unit tests prove it for a dictionary place ("PARIS" in a header) and for foreign places not in the dictionary ("TOKYO", "BOSTON"). "US"/"USA" handling follows the approved guidelines from 10.1.
2. **AC2 — Common-noun false places:** LOCATION detections that are French common nouns or domain jargon and not in the geography dictionary ("Équipe", "Constat", "SecNumCloud", "Pentest") are dropped. The mechanism (stoplist resource, lexical check, or both) is chosen and documented in the story; it is deterministic and local.
3. **AC3 — Company names tagged as places:** a LOCATION detection that is not in the geography dictionary and matches a known organisation (e.g. "Wavestone") is retyped to ORG or dropped; the story states which and why. The known-organisation lexicon must come from a source independent of the test corpus, documented in the story (source, licence, date); held-out FP/FN lists are never used to build it. If no such independent source is available, AC3 is limited to dropping (no retype). Fragments such as "à Dr" are dropped.
4. **AC4 — Particles:** PERSON spans are extended to include surname particles (le, la, de, du, des, d', van, van der, von, and others listed in the story) when the particle is followed by a capitalised surname ("Jean-Charles Le Goff", "Sylvie van der Werf", "Chasseloup de Laubat").
5. **AC5 — Mc/Mac:** names starting with "Mc"/"Mac" followed by a capital are not truncated ("Mme Sarah McAllister" → PERSON "Sarah McAllister" after title stripping).
6. **AC6 — Trailing roles:** a trailing ", Role" (e.g. ", Responsable", ", Directeur …") is trimmed from PERSON spans.
7. **AC7:** Unit tests for every rule, including the negative cases (real all-caps places, a particle not followed by a surname, "Mac" as an ordinary word).
8. **AC8 — Gates:** G1 (main and held-out), G2, G3 versus the 10.2 baseline (LOCATION recall is the type most at risk: report it explicitly), G4, G5, G6 (plus NFR1 timing unchanged: existing perf test green), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, regardless of G7, including an upgrade note on pseudonym continuity (see Risk Mitigation).

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py` — `_trim_entity_boundaries`, LOCATION post-filter
- `gdpr_pseudonymizer/nlp/geography_dictionary.py`, `gdpr_pseudonymizer/resources/` — stoplists
- `gdpr_pseudonymizer/resources/detection_patterns.yaml` — particle and Mc/Mac name patterns

### Estimated Effort: 1 week

---

## Story 10.4: Greetings + Org-Plus-Country

**As a** user pseudonymizing email threads,
**I want** each person in a salutation detected separately, a first name alone on a greeting line detected, and "Microsoft France" treated as one organisation,
**so that** the people addressed in an email are not left in clear text and organisations get one consistent pseudonym.

**Priority:** MEDIUM — Small counts, high user visibility (email is a primary use case).
**Change type:** Detector-only (G4). Baseline: 10.3 merged close-out.

### Acceptance Criteria

1. **AC1 — Split salutations:** a PERSON span of the form "X, Y," (e.g. "Laurent, Marie,") on a salutation line is split into two PERSON entities when both X and Y are known first names (name dictionary). If either is not a known first name, today's behaviour is kept. The interaction with the `last_first_names` pattern (`require_known_first_name`) is documented and tested.
2. **AC2 — Bare first name on a salutation line:** a known first name is detected as PERSON when it stands alone on a line followed by a comma ("Marie,") or follows a greeting or thanks opener ("Bonjour Marie", "Merci Laurent", "Bonne initiative Laurent."). The story defines "salutation line" precisely (opener list, maximum line length) as a resource, not a hard-coded string. The opener resource must state explicitly whether non-greeting phrases such as "Bonne initiative Laurent." (a compliment, not a salutation) are in scope; the call is left to the story but must be written down.
3. **AC3:** The new bare-first-name rule of AC2 fires only in salutation contexts; existing detection of these names is unchanged. Unit tests cover first names that are also common words (e.g. "Rose", "Pierre", "Claire") in running text, proving the new rule does not fire there.
4. **AC4 — Org + country:** an ORG immediately followed by a country or region name ("France", "Europe", and others listed in the story) is merged into a single ORG span ("Microsoft France"), when the approved guidelines annotate it that way. The merge runs after the 10.2 role filter and never merges a role token (e.g. "VP" + "Europe" is never merged into an ORG); a unit test proves it.
5. **AC5:** Unit tests for each rule, including `email_chain.txt`-style fixtures written for the tests (not copied from the held-out set).
6. **AC6 — Gates:** G1 (main and held-out), G2, G3 versus the 10.3 baseline, G4, G5, G6 (plus NFR1 timing unchanged: existing perf test green), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, regardless of G7, including an upgrade note on pseudonym continuity (see Risk Mitigation).

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py`, `gdpr_pseudonymizer/nlp/regex_matcher.py`
- `gdpr_pseudonymizer/nlp/name_dictionary.py`
- `gdpr_pseudonymizer/resources/detection_patterns.yaml` — salutation openers, country/region list

### Estimated Effort: 0.5-1 week

---

## Execution Sequence

```
Story 10.1 (Benchmark repair + held-out)  --- Week 1-2.5 ---  guidelines approval stop inside; benchmark-only
Story 10.2 (Overlap dedup + ORG roles)    --- Week 3      ---  baseline = 10.1 merged
Story 10.3 (LOCATION noise + boundaries)  --- Week 4      ---  baseline = 10.2 merged
Story 10.4 (Greetings + org+country)      --- Week 5      ---  baseline = 10.3 merged
```

**Strictly sequential.** Each story's baseline is the previous story's merged close-out G1 run. No parallel detector stories: overlapping changes would make G3/G4 attribution impossible.

**Epic close-out baseline:** the 10.4 merged G1 run (main + held-out) is the baseline Epic 9 starts from.

---

## Compatibility Requirements

- [ ] Existing APIs remain unchanged (`EntityDetector`, `DetectedEntity`, CLI flags, GUI)
- [ ] Database schema changes: none (mapping table schema untouched; mapping keys may change, because span changes in 10.2-10.4 change the normalized entity text — see the pseudonym-continuity risk)
- [ ] UI changes: none; validation stays mandatory
- [ ] Performance impact is minimal (post-filters are linear in the number of detections; single-document NFR1 still met)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| A filter drops real entities (recall loss) | MEDIUM | HIGH | G3 recall guard per type; negative-case unit tests; recall over precision |
| Rules overfit to the 25-document corpus | MEDIUM | MEDIUM | G5 held-out check from 10.2; held-out FP/FN lists not used for rule design |
| Ground-truth repair encodes the detector's own output | MEDIUM | HIGH | Written guidelines approved by Lionel (guidelines approval stop) before any edit; held-out annotated by hand, never pre-annotated |
| Benchmark and detector deltas mixed | LOW | HIGH | G4: separate PRs and separate reporting |
| Unsupported accuracy claims in docs | LOW | HIGH | G1/G2/G7; the arithmetic estimate is never published |
| Pseudonym continuity across versions: span changes in 10.2-10.4 re-key mapping entries (normalized text), so a user keeping a v2.2 mapping DB can get a new pseudonym for the same entity | MEDIUM | MEDIUM | CHANGELOG [Unreleased] entry with an upgrade note in each of 10.2-10.4 explaining the effect; schema unchanged |

- **Primary Risk:** a precision rule silently removes real persons, places or organisations.
- **Mitigation:** G3 on every story, negative-case tests for every rule, held-out check (G5).
- **Rollback Plan:** every rule is an isolated post-filter or pattern in its own PR; revert the PR. Annotation changes (10.1) are in their own PRs and revert independently.

---

## Definition of Done

- [ ] All 4 stories completed with acceptance criteria met
- [ ] Every story closed with a cited G1 run and an independent G2 check
- [ ] No unapproved recall drop (G3) at any story
- [ ] Held-out set exists and is reported for 10.2-10.4 (G5)
- [ ] `GUIDELINES.md` approved by Lionel and applied to the whole corpus
- [ ] black, ruff, mypy clean; full CI green (G6)
- [ ] QA report updated with the before/after at every story, and CHANGELOG `[Unreleased]` entries per story (G7)
- [ ] At Epic 10 close-out, README/README.fr, `docs/faq*.md`, `docs/index*.md` and `docs/tutorial*.md` updated once from the final G1 run (G7 interpretation, Lionel, 2026-10-02)
- [ ] Close-out baseline recorded as Epic 9's starting point: run ID plus the pasted `[Overall]`/`[PERSON]`/`[LOCATION]`/`[ORG]`/`[HELD-OUT …]` lines in the QA report (CI artifacts expire after 90 days, so the run ID alone is not enough)
- [ ] No release cut (v2.3.0 only on Lionel's explicit go)

---

## Out of Scope

| Item | Reason | Where |
|------|--------|-------|
| ORG recall for missed brands (OVHcloud, TechCorp, Microsoft Azure, Partech, Kima Ventures, EY) — F10 | A gazetteer built from the brands in the corpus would be overfitting by construction; needs a general approach | Epic 9 or a later story |
| Different-type overlaps (PERSON vs ORG on the same span) | Needs its own rule and evidence | Later |
| Encoder NER models (CamemBERT-NER, …) | Lionel decision | Epic 9 |
| Auto-accept / no-validation modes | Product constraint 3 | Parked in Epic 9 |
| v2.3.0 release | Only on Lionel's explicit go | Separate release story |

---

## Note: Epic 8 Version Label

Relabelled to v2.4 (Lionel, 2026-10-02). Epic 8 was titled "v2.2 — Output Format Preservation & Auto-Update", but v2.2.0 shipped different scope (model selection, validation retype, span-bleed fixes; commit `375eed9`). The file is now `docs/prd/epic-8-v2.4-output-format-preservation.md`; Epic 8's scope is unchanged.

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing system running Python 3.10-3.12, spaCy 3.7 `fr_core_news_lg` + regex hybrid detection, Poetry, pytest, GitHub Actions.
- Integration points: `HybridDetector` merge and post-filters, regex patterns and resource lexicons, the accuracy suite (`tests/accuracy/`), the annotation corpus and `scripts/auto_annotate_corpus.py`.
- Existing patterns to follow: post-filters as `HybridDetector` methods; lists and patterns in `gdpr_pseudonymizer/resources/`; structured logging without entity text beyond current practice.
- Critical compatibility requirements: the product constraints and gates G1-G7 above, verbatim; the guidelines approval stop inside 10.1; strict 10.1 → 10.2 → 10.3 → 10.4 order, each baseline the previous merged one.
- Each story must include verification that existing functionality remains intact (full CI green, recall guard).

The epic should maintain system integrity while delivering higher detection precision and a trustworthy benchmark, without lowering recall."

---

**Document Status:** DRAFT
**Created:** 2026-10-02
**Author:** John (PM)
