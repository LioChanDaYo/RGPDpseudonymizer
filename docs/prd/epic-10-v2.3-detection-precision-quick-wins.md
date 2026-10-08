# Epic 10: v2.3 — Detection Precision Quick Wins - Brownfield Enhancement

**Epic Goal:** Raise detection precision and make the accuracy benchmark trustworthy with local, deterministic changes to the hybrid detector and the ground-truth corpus, without lowering recall. The user-facing value is fewer false entities to reject during the (mandatory) validation step and a benchmark whose numbers can be believed.

**Target Release:** v2.3.0 candidate. **No release is part of this epic.** v2.3.0 ships only on Lionel's explicit go, through a separate release story.
**Duration:** Estimated 5-7.5 weeks (10.1 is annotation-labor-bound; 10.3 split into 10.3a and 10.3b, and 10.3c added, Lionel, 2026-10-06; 10.5 added, Lionel, 2026-10-07; 10.3b re-estimated after its STOP R, 2026-10-07); 10.6 runs in parallel (2-3 weeks elapsed) and close-out waits for its sealed set
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
| F6 | LOCATION noise: "Wavestone" 10, "CONFORME" 10, "CC" 4, "US", "Équipe", "Constat", "SecNumCloud", "Pentest", "à Dr" | subset of 255 LOCATION FP | 10.3b |
| F7 | Name boundary errors: particles ("Jean-Charles Le Goff", "Sylvie van der Werf", "Chasseloup de Laubat"), "Mme Sarah Mc…" truncation, trailing roles (", Responsable") | not yet counted in full | 10.3b |
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

## Cross-Story Rules

These notes sit outside the normative Gates block above and do not change its text. They bind every detector story from 10.3a on: 10.3a, 10.3b, 10.3c and 10.4 (10.3c added, orchestrator 2026-10-07; rule text unchanged).

- **Coverage level 2b (Lionel, 2026-10-06):** No rule may remove the last covering span of any type from an annotation of any type without Lionel's sign-off.

---

## Enhancement Details

- **What's being changed:** (1) the benchmark is repaired against written annotation guidelines and gains a held-out set; (2) `HybridDetector` gets a same-type overlap rule and an ORG role filter; (3a) spans stop at line breaks and run-on regex name shapes are fixed; (3b) LOCATION noise filters and PERSON boundary rules for particles, Mc/Mac and trailing roles; (3c) the merge's exact-match check becomes type-aware; (4) salutation-aware first-name detection and ORG + country merging, plus two carried coverage losses restored; (6) a second, blind final-exam set written by a different author, sealed and scored once at close-out, plus bootstrap confidence ranges in the accuracy output.
- **How it integrates:** all detector changes are post-processing steps or patterns inside the existing `HybridDetector` pipeline and its YAML/JSON resources. No public API, CLI flag, GUI screen, mapping-table schema or file format changes.
- **Success criteria:**
  - Every story closes with a G1 run, G2 verification, no unapproved recall drop (G3) and held-out numbers (G5, from 10.2 on).
  - Overall precision on the repaired benchmark rises over the 10.1 close-out baseline by the end of 10.4, measured by G1 runs. No numeric precision target is set: the arithmetic estimate above is not a target.
  - The ground truth follows written, Lionel-approved guidelines, and the held-out set is scored separately.

---

## Epic 10 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 10.1: Benchmark Repair + Held-Out Set | HIGH | 1.5-2.5 weeks | F3, F4, F5, F2 (junk) | Done (PR #79) |
| 10.2: Same-Type Overlap Dedup + ORG Role Filter | HIGH | 1 week | F1, F2 | Done (PR #81) |
| 10.3a: Boundaries & Run-On Spans (split from 10.3, Lionel, 2026-10-06) | MED | 0.5-1 week | 10.2 handoff, REL-004 | Done (PR #84) |
| 10.3b: Particles, Roles & LOCATION Noise (split from 10.3, Lionel, 2026-10-06) | MED | 0.5-1 week (re-estimated after STOP R, 2026-10-07) | F6, F7 | Draft |
| 10.3c: Type-Aware Exact Match in Merge (added at 10.3a STOP R, Lionel, 2026-10-06) | MED | 0.5 week | 10.3a STOP R | Draft |
| 10.4: Greetings + Org-Plus-Country | MED | 0.5-1 week | F8, F9 | Draft |
| 10.5: DB Init Safety (data-layer hardening, added by Lionel, 2026-10-07) | LOW | 0.5 week | PR #83 finding | Draft |
| 10.6: Final-Exam Set and Confidence Ranges (added by Lionel, 2026-10-07) | HIGH | 2-3 weeks elapsed, in parallel | Overfitting check, close-out evidence | Draft |

**Total Estimated Duration:** 5-7.5 weeks; 10.6 runs in parallel (2-3 weeks elapsed) and close-out waits for its sealed set

---

## Course Correction: 10.3 Split (Lionel, 2026-10-06)

Story 10.3 is split into two sequential stories: **10.3a "Boundaries & run-on spans"** (the draft's Slice A) and **10.3b "Particles, roles & LOCATION noise"** (Slices B and C, the epic's original 10.3 ACs).

- **Reason (PO recommendation):** Slice A rewrites the regex patterns that Slices B and C depend on. 10.3b therefore needs the merged 10.3a close-out run as its baseline, and smaller PRs are easier to review. The combined 10.3 draft had 745 lines and 15 ACs against an epic estimate of 1 week.
- **Effect:** order is now 10.1 → 10.2 → 10.3a → 10.3b → 10.3c → 10.4. Each story's baseline is the previous story's merged close-out G1 run. Gates, product constraints and the Epic 10 G7 interpretation are unchanged.
- **Decisions at 10.3a STOP R (Lionel, 2026-10-06):**
  - New story **10.3c** makes the exact-match check in `_merge_entities` type-aware (0.5 week, after 10.3b, before 10.4).
  - The carried coverage losses PERSON "Pierre" and ORG "BRS" move to 10.4 (AC5). ORG "TechSolutions France SAS" stays in 10.3a.
  - The "keyword + connector(s)" ORG widening is deferred out of 10.3a (see Out of Scope).

---

## Close-Out Record

Numbers come only from CI runs; each line cites its run ID. Full verbatim lines are in `docs/qa/ner-accuracy-report.md`.

| Story | Close-out G1 run | Main corpus | Held-out | Merged |
|---|---|---|---|---|
| 10.1 (benchmark repair, same detector) | `37189862679` | P 66.69% / R 79.91% / F1 72.70% | F1 61.51% | PR #79 |
| 10.2 | `37385301566`, reproduced on `main` by `37424140809` | P 77.35% / R 78.33% / F1 77.84% | F1 72.36% | PR #81 |
| 10.3a | `37459114468` (head `39ab544`), reproduced on `main` by `37480506234` at `ac354cc` | P 77.64% / R 79.32% / F1 78.47% | F1 76.44% | PR #84 |

- **10.2 recall (G3):** Lionel accepted recall bounds of FN PERSON +21 / LOCATION +4 / ORG +16 versus 10.1 (`37189862679`). Run `37385301566` is inside them: FN PERSON +21 / LOCATION +4 / ORG +10.
- **10.2 held-out ORG recall:** Lionel accepted the drop (held-out ORG FN 28 → 34, `37189862679` → `37385301566`). It is tracked in 10.3a (AC7).
- **Side PRs:** #80 (test offsets in the document processor integration tests) and #82 (performance workflow fix; it makes the NFR1 gate real, since the workflow previously ran no tests).
- **10.3a recall (G3, strict):** main FN 458 (PERSON 50 / LOCATION 54 / ORG 354) versus 480 (53 / 54 / 373) in `37385301566`. No per-type FN increase.
- **10.3a held-out:** FN 59, ORG FN 28 (`37459114468`), versus 70 and 34 in `37385301566`. Held-out ORG FN is back to its 10.1 level (28 in `37189862679`).
- **10.3a QA:** PR #84 merged before QA. The post-merge QA gate is PASS (`docs/qa/gates/10.3a-boundaries-run-on-spans.yml`, PR #85). Its REQ-001 finding is routed to 10.4 (see "Candidate item" there).
- **10.6 final exam (close-out):** scored once in run `<run id>` at `<commit>` (ledger `tests/test_corpus/final_exam/RUNS.md`). Fill in at close-out with the pasted `[FINAL-EXAM …]` and CI95 lines.
- **Current baseline for 10.3b:** `37459114468` / `37480506234`.

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

## Story 10.3a: Boundaries & Run-On Spans

**Split from 10.3 (Lionel, 2026-10-06).** This is the 10.3 draft's Slice A. It must merge before 10.3b starts.

**As a** user reviewing detected entities,
**I want** detected spans to stop at line breaks and at the end of the name,
**so that** a heading, a signature line or the rest of a sentence is not offered as one organisation or person, and no part of a name is left in clear text.

**Priority:** MEDIUM — 10.3b depends on the regex patterns this story rewrites.
**Change type:** Detector-only (G4). Baseline: 10.2 merged close-out, run `37385301566` (reproduced on `main` by `37424140809`).

### Acceptance Criteria

1. **AC1 — Regex spans stop at line breaks:** no regex detection spans a line break. The "Laurent⏎⏎Laurent" junk span is gone (its cause is the `\s+` in the regex `full_names` pattern, `regex_matcher.py:257-262`, not spaCy).
2. **AC2 — spaCy spans split at line breaks:** a spaCy span that crosses a line break is split at the break; each part that holds an upper-case letter or a digit is kept as its own entity and then goes through the existing post-filters; other parts are dropped.
3. **AC3 — Run-on ORG/PERSON regex shapes:** the regex ORG and PERSON name shapes no longer swallow clauses, lists or leading words. Covered cases: signature lines, heading + org, sentence-long ORG, leading "La société", clause tails without punctuation.
4. **AC4 — TechSolutions partial leak:** the partial leak from 10.2 (union + trim against a junk inner span) is fixed.
5. **AC5 — REL-004:** the V3 guard's sentence-start exception, carried over from 10.2, is decided by Lionel from a dry-run of three options: keep it; drop it; or limit it to common sentence-initial function words held in a resource. The chosen option is implemented, with QA's 10.2 probe ("Nous avons conclu. Quentrix, Zorbalia Conseil") as a unit test.
6. **AC6 — Coverage invariant (from 10.2):** no rule uncovers a character that a span of the same type covered in the baseline, unless Lionel signs off the exception. Every close-out reports the coverage table.
7. **AC7 — Carried losses tracked:**
   - The three main-corpus annotations that lost coverage in 10.2 (ORG "TechSolutions France SAS", PERSON "Pierre", ORG "BRS") are each reported as restored, or as deferred with the reason. *(Lionel, 2026-10-06, STOP R: "Pierre" and "BRS" are deferred to 10.4 AC5.)*
   - Held-out ORG recall (FN 28 → 34, accepted by Lionel in 10.2) is reported against both the 10.1 and the 10.2 held-out lines, from the aggregate `[HELD-OUT …]` lines only.
8. **AC8:** Unit tests for every rule, including negative cases. Tests use synthetic strings with invented names, never held-out strings.
9. **AC9 — Gates:** G1 (main and held-out), G2, G3 versus the 10.2 baseline, G4, G5, G6 (plus NFR1 timing unchanged: a real `performance.yaml` run on the branch, green since PR #82), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, including an upgrade note on pseudonym continuity (see Risk Mitigation). The merged close-out run is 10.3b's baseline.

### Integration Points

- `gdpr_pseudonymizer/resources/detection_patterns.yaml`, `gdpr_pseudonymizer/nlp/regex_matcher.py` — line-break stops, ORG/PERSON name shapes
- `gdpr_pseudonymizer/nlp/hybrid_detector.py` — spaCy span split, V3 guard (REL-004), union + trim
- `tests/unit/` — new rule tests

### Estimated Effort: 0.5-1 week

---

## Story 10.3b: Particles, Roles & LOCATION Noise

**Split from 10.3 (Lionel, 2026-10-06).** This is the 10.3 draft's Slices B and C. AC1 to AC7 are the original 10.3 ACs, word for word. AC8 is the original text with its baseline amended at the split. AC9 is added by the split.

**As a** user reviewing detected entities,
**I want** common words and company names not offered as places, and names with particles or "Mc/Mac" detected whole,
**so that** I reject fewer false places and do not have to repair cut names by hand.

**Priority:** MEDIUM
**Change type:** Detector-only (G4). Baseline: 10.3a merged close-out, run `37459114468` (reproduced on `main` by `37480506234`).
**STOP R outcome (Lionel, 2026-10-07):** AC3 uses no organisation lexicon and no in-document evidence rule, so company names tagged LOCATION stay LOCATION; C2 is kept (QA REL-002); R-KWC is routed to 10.4 (candidate item).

### Acceptance Criteria

1. **AC1 — All-caps common words:** an all-caps LOCATION detection is dropped only on positive evidence that it is a common word (hit in a common-word stoplist / lexical check, e.g. "CONFORME", "CC"), never merely because it is absent from `french_geography.json`. All-caps real places survive: unit tests prove it for a dictionary place ("PARIS" in a header) and for foreign places not in the dictionary ("TOKYO", "BOSTON"). "US"/"USA" handling follows the approved guidelines from 10.1.
2. **AC2 — Common-noun false places:** LOCATION detections that are French common nouns or domain jargon and not in the geography dictionary ("Équipe", "Constat", "SecNumCloud", "Pentest") are dropped. The mechanism (stoplist resource, lexical check, or both) is chosen and documented in the story; it is deterministic and local.
3. **AC3 — Company names tagged as places:** a LOCATION detection that is not in the geography dictionary and matches a known organisation (e.g. "Wavestone") is retyped to ORG or dropped; the story states which and why. The known-organisation lexicon must come from a source independent of the test corpus, documented in the story (source, licence, date); held-out FP/FN lists are never used to build it. If no such independent source is available, AC3 is limited to dropping (no retype). Fragments such as "à Dr" are dropped.
4. **AC4 — Particles:** PERSON spans are extended to include surname particles (le, la, de, du, des, d', van, van der, von, and others listed in the story) when the particle is followed by a capitalised surname ("Jean-Charles Le Goff", "Sylvie van der Werf", "Chasseloup de Laubat").
5. **AC5 — Mc/Mac:** names starting with "Mc"/"Mac" followed by a capital are not truncated ("Mme Sarah McAllister" → PERSON "Sarah McAllister" after title stripping).
6. **AC6 — Trailing roles:** a trailing ", Role" (e.g. ", Responsable", ", Directeur …") is trimmed from PERSON spans.
7. **AC7:** Unit tests for every rule, including the negative cases (real all-caps places, a particle not followed by a surname, "Mac" as an ordinary word).
8. **AC8 — Gates (amended at split, Lionel 2026-10-06):** G1 (main and held-out), G2, G3 versus the previous merged baseline (10.3a close-out) (LOCATION recall is the type most at risk: report it explicitly), G4, G5, G6 (plus NFR1 timing unchanged: existing perf test green), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, regardless of G7, including an upgrade note on pseudonym continuity (see Risk Mitigation).
9. **AC9 — " - Lead <Org>" variant (added by the split, 2026-10-06):** the AC6 trailing-role trim also covers a name followed by " - " and a role word on the same line ("<Name> - Lead <Org>", from the 10.2 handoff). Only the role word(s) are cut. The span becomes "<Name>" only if every capitalised word after the role word(s) is covered by another kept span; otherwise the span is not trimmed. Unit tests cover both branches.

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py` — `_trim_entity_boundaries`, LOCATION post-filter. *Note (2026-10-07): `_trim_entity_boundaries` (`hybrid_detector.py:741` at `main` `23df76a`) receives no document text. The particle and boundary rules therefore plug in through a new `_fix_person_boundaries(entities, text, blockers)`, wired after `_trim_entity_boundaries`, as the 10.3b story specifies.*
- `gdpr_pseudonymizer/nlp/geography_dictionary.py`, `gdpr_pseudonymizer/resources/` — stoplists
- `gdpr_pseudonymizer/resources/detection_patterns.yaml` — particle and Mc/Mac name patterns

### Estimated Effort: 0.5-1 week

Re-estimated after STOP R on 2026-10-07 (it was 1-1.5 weeks while the C2 removal and the optional ORG widening were open). Lionel kept C2, so there is no C2 removal and no test rewrite. R-KWC moved to 10.4, so there is no run K. What remains is AC1-AC9 in two slices (B and C), each with its own G1 run.

---

## Story 10.3c: Type-Aware Exact Match in Merge

**Added at 10.3a STOP R (Lionel, 2026-10-06).** Runs after 10.3b and before 10.4.

**As a** user reviewing detected entities,
**I want** a name or place found by the regex layer to stay on the list when spaCy found the same text with another type,
**so that** I choose the right type during validation instead of the candidate being silently lost.

**Priority:** MEDIUM — small, isolated fix to the merge step.
**Change type:** Detector-only (G4). Baseline: 10.3b merged close-out.

### Context

`HybridDetector._merge_entities` (definition `:430`; its `_is_exact_match` call at `:471`) skips a regex detection when `_is_exact_match` (defined at `hybrid_detector.py:1409-1432`) finds a spaCy detection with the same span or the same normalized text. (Line numbers at `main` `23df76a`, after PR #86.) The check ignores entity type, so a regex detection is dropped even when spaCy gave the text another type. Example: regex LOCATION "Nice" is dropped because spaCy found ORG "Nice".

**10.3a dry-run measure (local dump on top of 10.3a's rules; NOT a CI result, NOT a target):** FN PERSON −2 / LOCATION −2; FP +3 PERSON on hyphenated place names ("Saint-Gobain", "Clermont-Ferrand"); the kept regex entity is flagged `is_ambiguous`.

### Acceptance Criteria

1. **AC1 — Type-aware exact match:** the exact-match skip applies only when both detections have the same entity type. When the span or normalized text matches but the types differ, both detections are kept, the regex detection is flagged `is_ambiguous = True`, and a distinct log event records the decision without logging entity text beyond current practice. Same-type exact matches keep today's behaviour (regex skipped). The 10.2 same-type overlap rule and the regex-ORG-over-spaCy-PERSON special case (`_should_prefer_regex_org`) are unchanged.
2. **AC2 — Re-measure first:** the dry-run figures above were taken on top of 10.3a. Before coding, the story re-measures them on the 10.3b close-out baseline and reports the per-type FN/FP delta. Only the cited G1 run counts as a result.
3. **AC3 — Hyphenated place names:** the new PERSON FP on hyphenated place names ("Saint-Gobain", "Clermont-Ferrand" in the dry-run) are reported. A rule that removes them is in scope only if it is generic (no lexicon built from corpus strings) and keeps to the Cross-Story Rules. Otherwise they are recorded as accepted FP with Lionel's sign-off: both candidates reach the mandatory validation step, flagged ambiguous.
4. **AC4:** Unit tests with invented names: same text and different types (both kept, regex flagged ambiguous); same span and different types; title-normalized match ("Dr X" vs "X") with different types; same text and same type (regex skipped, unchanged).
5. **AC5 — Gates:** G1 (main and held-out), G2, G3 versus the previous merged baseline (10.3b close-out), G4, G5, G6 (plus NFR1 timing unchanged: a real `performance.yaml` run on the branch), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, including an upgrade note on pseudonym continuity (see Risk Mitigation). The merged close-out run is 10.4's baseline.

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py` — `_merge_entities`, `_is_exact_match`
- `tests/unit/` — merge tests

### Estimated Effort: 0.5 week

---

## Story 10.4: Greetings + Org-Plus-Country

**As a** user pseudonymizing email threads,
**I want** each person in a salutation detected separately, a first name alone on a greeting line detected, and "Microsoft France" treated as one organisation,
**so that** the people addressed in an email are not left in clear text and organisations get one consistent pseudonym.

**Priority:** MEDIUM — Small counts, high user visibility (email is a primary use case).
**Change type:** Detector-only (G4). Baseline: 10.3c merged close-out.

### Acceptance Criteria

1. **AC1 — Split salutations:** a PERSON span of the form "X, Y," (e.g. "Laurent, Marie,") on a salutation line is split into two PERSON entities when both X and Y are known first names (name dictionary). If either is not a known first name, today's behaviour is kept. The interaction with the `last_first_names` pattern (`require_known_first_name`) is documented and tested.
2. **AC2 — Bare first name on a salutation line:** a known first name is detected as PERSON when it stands alone on a line followed by a comma ("Marie,") or follows a greeting or thanks opener ("Bonjour Marie", "Merci Laurent", "Bonne initiative Laurent."). The story defines "salutation line" precisely (opener list, maximum line length) as a resource, not a hard-coded string. The opener resource must state explicitly whether non-greeting phrases such as "Bonne initiative Laurent." (a compliment, not a salutation) are in scope; the call is left to the story but must be written down.
3. **AC3:** The new bare-first-name rule of AC2 fires only in salutation contexts; existing detection of these names is unchanged. Unit tests cover first names that are also common words (e.g. "Rose", "Pierre", "Claire") in running text, proving the new rule does not fire there.
4. **AC4 — Org + country:** an ORG immediately followed by a country or region name ("France", "Europe", and others listed in the story) is merged into a single ORG span ("Microsoft France"), when the approved guidelines annotate it that way. The merge runs after the 10.2 role filter and never merges a role token (e.g. "VP" + "Europe" is never merged into an ORG); a unit test proves it.
5. **AC5 — Restore carried coverage losses (from 10.2; moved from 10.3a at STOP R, Lionel, 2026-10-06):** two main-corpus annotations that have had no covering detection since 10.2 regain coverage, each by a generic rule (no lexicon entry built from the corpus string):
   - PERSON "Pierre" (`hr_announcement`): a bare known first name at the start of an indented sentence, covered today by no detection. The rule must keep AC3 true (no firing on first names in running text); if both cannot hold, the annotation is reported as still uncovered, with the reason and Lionel's sign-off.
   - ORG "BRS": an alias that the text defines for an organisation, covered in v2.2 only by a junk span. Coverage comes from the alias being tied to its defining ORG in the text, not from listing "BRS".
   - The coverage table at close-out reports both annotations as restored or still uncovered.
6. **AC6:** Unit tests for each rule, including `email_chain.txt`-style fixtures written for the tests (not copied from the held-out set) and invented-name fixtures for the two AC5 cases.
7. **AC7 — Gates:** G1 (main and held-out), G2, G3 versus the previous merged baseline (10.3c close-out), G4, G5, G6 (plus NFR1 timing unchanged: existing perf test green), G7 per the Epic 10 G7 interpretation (Lionel, 2026-10-02): before/after recorded in the QA report in this story; README/README.fr, FAQ, docs index and tutorials are updated at Epic 10 close-out, not per story. CHANGELOG [Unreleased] entry describing the behaviour change, regardless of G7, including an upgrade note on pseudonym continuity (see Risk Mitigation).

### Candidate Item: ORG Name-Shape Limits and R-KWC (QA REQ-001, routed by Lionel 2026-10-07; R-KWC, routed by Lionel at 10.3b STOP R, 2026-10-07)

Not an AC. The 10.4 story decides whether to take each part in or leave it to later ORG recall work, and records the call. If it takes either in, it re-estimates 10.4. Any change follows G3 and the Cross-Story Rules.

- **Finding:** the 10.3a ORG name shape (`detection_patterns.yaml:77` suffix form, `:88` prefix form) can leave part of a real organisation name uncovered when the name:
  - has 7 or more words (past the 6-token cap);
  - contains "& Co." with a period;
  - has 3 or more connectors in a row (the shape allows at most 2);
  - has an elision right after the prefix keyword ("Chambre d'…").
- **Size:** no main-corpus case (QA gate `docs/qa/gates/10.3a-boundaries-run-on-spans.yml`, REQ-001, severity low).
- **R-KWC, the "keyword + connector(s)" ORG widening (routed by Lionel at 10.3b STOP R, 2026-10-07):**
  - What it does: the prefix form accepts connectors or an elision right after the keyword, so names such as "Chambre d'Agriculture d'Eure-et-Loir" or "Cour d'Appel de Paris" are covered whole.
  - Why it sits here: it changes the same `organizations` prefix pattern (`detection_patterns.yaml:88`) and shares REQ-001's elision-after-keyword case, so the two are handled together. It covers only that case; REQ-001's other limits (7+ words, "& Co.", 3+ connectors) stay as listed above.
  - Size: 0 change on the main corpus in the 10.3b dry-run (local, not a CI result); +1 ORG TP in the earlier 10.3a dry-run.
- **Related:** F10 (ORG recall) and the R-KWC row, both in Out of Scope.

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py`, `gdpr_pseudonymizer/nlp/regex_matcher.py`
- `gdpr_pseudonymizer/nlp/name_dictionary.py`
- `gdpr_pseudonymizer/resources/detection_patterns.yaml` — salutation openers, country/region list

### Estimated Effort: 0.5-1 week

---

## Story 10.5: DB Init Safety

**Added by Lionel, 2026-10-07.** Data-layer hardening found during the TEST-002 race fix (PR #83). It is not a detection-precision change. It sits in Epic 10 because this repo puts hardening found along the way into the active epic as a small story (precedents: 4.6.1, 6.7.1), and `epic-list.md` has no backlog section.

**As a** user running several CLI processes against a new mapping database (e.g. from a script),
**I want** a failed initialization never to delete a database that another process just created,
**so that** I do not lose the winner's mappings and passphrase setup to a race.

**Priority:** LOW — rare: it needs two processes initializing the same new DB at the same moment. Single CLI or GUI runs initialize once.
**Change type:** Data-layer only. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. It changes no detection, so it has no accuracy baseline and may run before, between or after the detector stories. It does not move the epic close-out baseline.

### Context

`init_database` (`gdpr_pseudonymizer/data/database.py:60`) checks that `db_path` does not exist, creates it, and on **any** exception deletes `db_path` (`database.py:180-184`, "Clean up partial database file on failure"). If two processes create the same new database at once, the loser's cleanup can delete the winner's freshly created file. PR #83 (open at the time of writing) makes index creation idempotent (`CREATE INDEX IF NOT EXISTS`). That only moves the loser's failure to the metadata key collision; the delete stays.

### Acceptance Criteria

1. **AC1 — No deletion of a pre-existing DB:** on failure, `init_database` deletes `db_path` only if this call itself created the file. A database that existed before the call, or that another process created during it, is never deleted. The mechanism is chosen and documented in the story: create the file exclusively and track ownership, or take a lock on first-time creation, or both.
2. **AC2 — Clear failure for the loser:** the process that loses the race fails with the existing "Database already exists" `ValueError`, or a documented equivalent, not a generic initialization exception. The winner's database opens with `open_database` and its own passphrase, and its metadata (schema version, encryption parameters, passphrase canary) is intact.
3. **AC3 — Concurrency test:** a test runs two initializations of the same new `db_path` concurrently, in separate processes, repeated enough times to make the race likely (the story states the count). Each iteration passes only if exactly one initialization succeeds, the file exists, it opens with the winner's passphrase, and the loser failed as AC2 says. The test is deterministic in its pass criteria and uses a temporary directory per iteration.
4. **AC4 — Existing behaviour kept:** initializing an existing path still raises `ValueError` without touching the file. A failure inside a single, uncontended initialization still leaves no partial file behind. Existing database tests stay green.
5. **AC5 — Gates:**
   - **G1 and G3 are N/A:** there is no detection change, so no accuracy run is required and recall cannot move. The PR states this explicitly.
   - **G5 is N/A** for the same reason.
   - **G4** holds trivially: no annotation, scorer or detector change.
   - **G2:** QA verifies the fix independently by re-running the AC3 test and reading the diff. There is no accuracy artifact to download.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes, so no QA report or docs update. CHANGELOG `[Unreleased]` gets a "Fixed" entry.

### Integration Points

- `gdpr_pseudonymizer/data/database.py` — `init_database` cleanup path
- `tests/unit/` or `tests/integration/` — concurrent-initialization test

### Estimated Effort: 0.5 week

---

## Story 10.6: Final-Exam Set and Confidence Ranges

**Added by Lionel, 2026-10-07**, in answer to "how do we make sure we're not overfitting?". It is benchmark-side work. It runs in parallel, outside the detector chain.

**As a** maintainer about to publish Epic 10's accuracy,
**I want** one blind test that no rule was ever shaped by, scored once, and ranges around every number,
**so that** the public figure reflects how the detector does on documents it has never met, and small story-to-story deltas are not read as wins.

**Priority:** HIGH. It is the evidence for the Epic 10 close-out number.
**Change type:** Benchmark-only (G4). No file under `gdpr_pseudonymizer/` changes. Two PRs: PR A (confidence ranges, scorer-side reporting) and PR B (final-exam set, sealing, CI job, leakage guard).
**Ordering:** outside the detector chain, like 10.5. PR A should land early, so 10.3c and 10.4 report ranges. PR B's set must be sealed before 10.4 merges, and must not influence 10.3c or 10.4. The set is scored exactly once, at Epic 10 close-out, after 10.4 merges.

### Context

The current overfitting guards are real, but weaker than the numbers suggest:

- **The held-out set is small.** It has 6 documents and 231 entities, including 51 ORG, so 1 ORG miss moves held-out ORG recall by about 2 points. It catches big overfitting, not subtle overfitting.
- **The held-out numbers have already shaped decisions.** Examples are the 10.2 ORG investigation and the guard variants E, F and G. Only aggregates were read, but every look leaks a little.
- **Same author family.** A Claude agent wrote the held-out text, and Claude agents also write the rules, so they share blind spots. The held-out text is also cleaner than real documents.
- **Some fixes are corpus-shaped by design.** The 10.3b LOCATION stoplist is made of main-corpus false-positive words. Its held-out effect was LOCATION FP 17 → 15 (10.3b run C, held-out aggregates).

This story adds a second, larger, blind "final exam" set, written by a different author and scored once. It also adds bootstrap confidence ranges to the accuracy output.

### Acceptance Criteria

**PR A: confidence ranges (scorer-side reporting only)**

1. **AC1 — Bootstrap ranges in the accuracy output.**
   - The accuracy suite prints a 95% bootstrap confidence range for P, R and F1. It does so for Overall and for each type, on the main corpus and on the held-out set.
   - Resampling is by **document**, with replacement, because entities in one document are not independent. Each resample re-sums TP/FP/FN and recomputes P/R/F1. The range is the percentile interval.
   - The number of resamples and the seed are fixed and printed, so the output is deterministic.
   - New labelled lines are added (e.g. `[CI95 Overall] …`, `[HELD-OUT CI95 ORG] …`), each stating `unit=document` and the document count.
   - The held-out ranges are aggregates. No per-document held-out number is printed or stored.
2. **AC2 — Metric definitions unchanged.** `match_entities`, `_match_key` and the P/R/F1 formulas do not change. The existing `[Overall]`/`[PERSON]`/`[LOCATION]`/`[ORG]`/`[HELD-OUT …]` lines keep their exact format. PR A's G1 run shows these eight lines byte-identical to the previous merged run on the same detector code.
3. **AC3 — Paired delta for story-to-story comparisons (main corpus only).**
   - The accuracy artifact also stores the main-corpus per-document, per-type TP/FP/FN as a JSON file. The main corpus is not blind.
   - A script computes the paired bootstrap range of the delta between two runs (same documents, resampled together).
   - From PR A's merge on, a detector story that reports a precision or F1 gain states whether that gain is outside the paired range.
   - Held-out has no paired delta, because that would need per-document held-out output.
   - *(PO question Q8: keep or drop AC3.)*

**PR B: final-exam set**

4. **AC4 — Brief and author.**
   - The set has 20 to 30 synthetic French documents (count chosen by Lionel, Q2). The formats are messier than the main corpus: email threads with quoted replies, PDF-style hard line breaks, tables flattened to text, mixed case, headers and signatures.
   - The author is **not** a rule-writing agent: GPT via `codex exec`, Lionel, or a mix (Lionel's choice, Q1).
   - The author brief lists formats and hard-case categories. It contains no GUIDELINES text and no corpus or held-out text. Lionel approves the brief before generation.
   - No real public figures and no real people. No user data, no copy of real records (product constraint 4).
   - An annotator who meets a real person or public figure flags it, and the name is replaced consistently before freeze.
5. **AC5 — Double blind annotation, with agreement reported.**
   - Two independent annotations are made under `tests/test_corpus/annotations/GUIDELINES.md`. Neither is pre-annotated by the detector or by any auto-annotator. Who annotates is Lionel's choice (Q3).
   - Inter-annotator agreement is reported per type as pairwise span F1. It uses the scorer's own matching (exact text and type after `_match_key`, one-to-one). Disagreements are counted by class.
   - Disagreements are adjudicated under GUIDELINES, and the adjudication is logged. A case GUIDELINES does not cover goes to Lionel as an amendment, as in 10.1.
   - The report holds only agreement figures, counts and classes, never entity text.
6. **AC6 — Sealed and frozen.**
   - Authoring and annotation happen in a sealed workspace outside the repo. Orchestrating agents handle only paths, hashes and counts, and never print document or annotation content.
   - At freeze, the set (documents plus adjudicated annotations) is sealed: an encrypted archive is committed under its own folder (e.g. `tests/test_corpus/final_exam/`), and its sha256 is recorded in this story.
   - The decryption key lives only in a GitHub Actions environment `final-exam`, with Lionel as required reviewer. No agent holds it.
   - The folder is outside every path the regular accuracy job loads, and outside `accuracy.yaml`'s push `paths`.
   - The storage choice is Lionel's (Q5); plain text plus rules alone is the weaker fallback.
7. **AC7 — Leakage guard covers the final exam without decrypting it.**
   - At sealing, a hash list of the final-exam-only strings is committed. These are the strings, normalized as `_match_key` does, that do not occur in the main-corpus text. They are stored as sha256 with a fixed salt, never as text.
   - `tests/unit/test_held_out_leakage.py`, or a sibling test, checks `gdpr_pseudonymizer/resources/**` and `tests/unit/**` against that list on every CI run, and reports paths and hashes only.
   - The held-out-blind rule (10.3b AC12) applies unchanged: any real string in a new test or resource must occur in main-corpus text or be approved by Lionel.
8. **AC8 — Scored exactly once, and enforced.**
   - **Trigger:** the final exam runs only on a manual `accuracy.yaml` dispatch whose `final_exam` input equals `final exam`.
   - **Job:** the run uses a job bound to the `final-exam` environment, so Lionel must approve it. The job checks the archive sha256 against the recorded value, decrypts, runs the usual suite and appends `[FINAL-EXAM Overall]`/`[FINAL-EXAM PERSON]`/`[FINAL-EXAM LOCATION]`/`[FINAL-EXAM ORG]` lines plus their CI95 lines to `accuracy-output.txt` in the `accuracy-results` artifact. The regular job is skipped in that run, so there is one `accuracy-results`.
   - **Why this shape:** the close-out evidence must be a G1 run as the Gates block defines it (an `accuracy.yaml` run, cited by ID, lines pasted from `accuracy-results`). With this shape G1 and G2 apply word for word. This is why the job lives inside `accuracy.yaml` rather than in a separate workflow.
   - **Ledger:** a committed ledger (e.g. `tests/test_corpus/final_exam/RUNS.md`) records the one scored run: run ID, commit, date, and Lionel's approval. A re-run is allowed only for an infrastructure failure at the **same** commit, with the reason recorded. A run at a later commit is a second look, and it is forbidden within Epic 10.
   - **Numbers are never inputs:** final-exam numbers are never used for a decision or for tuning. No agent opens, lists, decrypts or greps the set. From PR B on, every later story's Dev Notes restate this, next to the held-out isolation rule.
   - **Before the real run:** QA proves the job on a **dummy** sealed fixture (invented text, separate key) and never on the real set.
9. **AC9 — Close-out reporting and the public number.**
   - At Epic 10 close-out (10.4 merged), the QA report and the epic Close-Out Record carry the main, held-out and final-exam figures, each with its range. The lines are pasted verbatim, because `accuracy-results` artifacts are kept 30 days (`accuracy.yaml:83`).
   - Lionel decides which figure is public: main, held-out, final exam, or a stated combination. This is recorded under G7 and the Epic 10 G7 interpretation. README/README.fr, FAQ, docs index and tutorials then change once, from that run.
10. **AC10 — Gates.**
    - **Building the set (PR B):** G1, G3 and G5 are N/A, because no detector change is made. The scored-once run (AC8) is the close-out evidence, and it is a G1 run.
    - **PR A:** G1 applies (its run shows the eight lines unchanged, AC2). G3 holds trivially, because the lines are identical.
    - **G2:** QA re-checks the ranges independently. For PR A, it recomputes them from the AC3 JSON with the printed seed. For PR B, it checks the workflow, ledger and guard on the dummy fixture. At close-out, it downloads the final-exam run's `accuracy-results` itself.
    - **G4:** benchmark-side only. PR A and PR B are each separate from any detector PR.
    - **G6** applies in full.
    - **G7:** no headline change until close-out, then AC9. CHANGELOG `[Unreleased]` gets an entry for PR A (new report lines) and for PR B (final-exam set and CI job).

### Integration Points

- `tests/accuracy/conftest.py`, `tests/accuracy/test_ner_accuracy_validation.py`: ranges, per-document JSON, final-exam scoring
- `.github/workflows/accuracy.yaml`: `final_exam` dispatch input, environment-bound job, artifact contents
- `tests/unit/test_held_out_leakage.py` (or a sibling): final-exam hash list
- `tests/test_corpus/final_exam/` (new): sealed archive, sha256, hash list, `RUNS.md` ledger, README
- `scripts/`: sealing script (uses the existing `cryptography` dependency) and the paired-delta script (AC3)
- `docs/qa/ner-accuracy-report.md`: ranges from PR A on; final-exam section at close-out

### Estimated Effort: 2-3 weeks elapsed (annotation is the long pole), in parallel with 10.3c and 10.4

- PR A: about 2-3 days (ranges, JSON, paired-delta script, G1 run, QA).
- PR B, tooling: about 2-3 days (sealing, workflow job, ledger, guard, dummy-fixture proof).
- PR B, set: authoring 1-2 days. At held-out density (231 entities in 6 documents, about 38 per document), 20 documents means about 770 entities per annotator and 30 documents about 1,150, annotated twice and then adjudicated. Calendar time depends on who annotates (Q3).
- Close-out: one scored run, then the reporting in AC9.

### Decisions for Lionel at this story's STOP (before any authoring)

- **Q1 — Author.** GPT via `codex exec`, Lionel, or a mix.
  - *PM recommendation:* GPT via `codex exec` writes the texts from a brief Lionel approves. It is a different model family from the rule writers and costs Lionel no writing time.
- **Q2 — Document count, 20 or 30.**
  - At held-out density, 20 documents give about 170 ORG annotations, so 1 ORG miss is about 0.6 recall point. 30 documents give about 255, or about 0.4 point. Today's held-out set is about 2 points per ORG miss.
  - These are projections from held-out averages, not counts.
  - *PM recommendation:* 30, if annotation time allows, since annotation is the cost.
- **Q3 — Annotators and adjudicator.**
  - (a) GPT via `codex exec` as annotator A and Lionel as annotator B, with Lionel adjudicating.
  - (b) Two GPT annotations with different prompts. Independence is weak, so the agreement figure is less meaningful.
  - (c) Lionel plus a second human.
  - Claude agents are excluded: they write the rules.
  - *PM recommendation:* (a).
- **Q4 — Lionel's exposure.**
  - If Lionel reads, annotates or adjudicates the texts, he will also sit at the 10.3c and 10.4 STOPs having seen them.
  - Proposed rule: Lionel's STOP decisions never cite or draw on a final-exam case, and this is recorded in the story.
  - Alternatively, Lionel's annotation work is scheduled after 10.4's STOP R.
- **Q5 — Storage.**
  - *PM recommendation:* encrypted archive in the repo, with the key in a Lionel-approved CI environment.
  - Fallback: a plain folder protected by rules only. That is the same protection the held-out set has today, which this story exists to improve on.
- **Q6 — Seeding.**
  - *PM recommendation:* half the documents are seeded with known hard-case categories (particles, Mc/Mac, greetings, role acronyms, foreign places, ORG plus country). The other half are unseeded "natural" documents.
  - The final-exam lines then report both halves, so known-problem progress and general behaviour are visible separately.
- **Q7 — After Epic 10.** Once scored, the set is spent for Epic 10. For Epic 9, either it becomes a second held-out set (aggregate-only access, no longer blind), or it is retired and a new final exam is written for Epic 9's close-out.
- **Q8 — AC3 (paired delta).** Keep it (recommended: it is what stops a +0.3 F1 being called a win) or drop it to shrink PR A.
- **Q9 — Public number.** Not decided now. It is Lionel's call at close-out (AC9).

---

## Execution Sequence

```
Story 10.1 (Benchmark repair + held-out)  --- Week 1-2.5 ---  guidelines approval stop inside; benchmark-only
Story 10.2 (Overlap dedup + ORG roles)    --- Week 3      ---  baseline = 10.1 merged
Story 10.3a (Boundaries + run-on spans)   --- Week 4      ---  baseline = 10.2 merged
Story 10.3b (Particles, roles, LOC noise) --- Week 4.5-5  ---  baseline = 10.3a merged
Story 10.3c (Type-aware exact match)      --- Week 5.5    ---  baseline = 10.3b merged
Story 10.4 (Greetings + org+country)      --- Week 6-6.5  ---  baseline = 10.3c merged
Story 10.5 (DB init safety)               --- 0.5 week, any slot --- no accuracy baseline (data layer)
Story 10.6 (Final-exam set + ranges)      --- parallel ---  PR A early; set sealed before 10.4 merges; scored once after 10.4
```

**Strictly sequential:** 10.1 → 10.2 → 10.3a → 10.3b → 10.3c → 10.4. Each story's baseline is the previous story's merged close-out G1 run. No parallel detector stories: overlapping changes would make G3/G4 attribution impossible.

**Story 10.5** is outside this chain: it changes no detection, so it has no accuracy baseline and can merge at any point without affecting G3/G4 attribution.

**Story 10.6** is outside the detector chain too. PR A (ranges) changes no metric line and should land before 10.3c, so 10.3c and 10.4 report ranges. PR B's set must be sealed before 10.4 merges, and nothing in 10.3c or 10.4 may draw on it. The final exam is scored exactly once, after 10.4 merges, and that run is part of the Epic 10 close-out evidence.

**Epic close-out baseline:** the 10.4 merged G1 run (main + held-out) is the baseline Epic 9 starts from, together with the one final-exam run (10.6) and its ranges.

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
| 10.3b rules built on regex shapes that 10.3a then rewrites | LOW (after the split) | MEDIUM | 10.3 split (Lionel, 2026-10-06): 10.3b starts only after 10.3a merges and uses the 10.3a close-out run as its baseline |
| 10.3c offers more candidates of a second type (e.g. PERSON on hyphenated place names) | MEDIUM | LOW | Both candidates reach mandatory validation, flagged ambiguous; FP reported per type (10.3c AC3) |
| Unsupported accuracy claims in docs | LOW | HIGH | G1/G2/G7; the arithmetic estimate is never published |
| Pseudonym continuity across versions: span changes in 10.2, 10.3a, 10.3b, 10.3c and 10.4 re-key mapping entries (normalized text), so a user keeping a v2.2 mapping DB can get a new pseudonym for the same entity | MEDIUM | MEDIUM | CHANGELOG [Unreleased] entry with an upgrade note in each of 10.2, 10.3a, 10.3b, 10.3c and 10.4 explaining the effect; schema unchanged |
| Final-exam set seen or used before close-out (leak) | LOW | HIGH | Sealed (encrypted) at freeze; key only in a Lionel-approved CI environment; hash-list leakage guard on every CI run; isolation rule restated in every later story (10.6 AC6-AC8) |
| Final-exam score well below main or held-out | MEDIUM | MEDIUM | It is information, not a failure: no tuning in response inside Epic 10. Lionel picks the public number (10.6 AC9). The gap goes to Epic 9 as evidence |
| Double annotation delays close-out | MEDIUM | MEDIUM | 10.6 starts now, in parallel; close-out waits only for the sealed set, not for any detector story |
| Ranges misread (held-out has 6 documents, so its ranges are wide) | MEDIUM | LOW | Every range states unit=document and the document count; story-to-story claims use the paired main-corpus delta (10.6 AC3) |
| Final-exam author shares conventions with the rule writers | LOW | MEDIUM | Different model family or a human author; the brief contains no GUIDELINES text or corpus text and is approved by Lionel (10.6 AC4) |

- **Primary Risk:** a precision rule silently removes real persons, places or organisations.
- **Mitigation:** G3 on every story, negative-case tests for every rule, held-out check (G5).
- **Rollback Plan:** every rule is an isolated post-filter or pattern in its own PR; revert the PR. Reverting 10.3a after 10.3b has merged also means re-measuring 10.3b, since its baseline includes 10.3a. Annotation changes (10.1) are in their own PRs and revert independently.

---

## Definition of Done

- [ ] All 8 stories (10.1, 10.2, 10.3a, 10.3b, 10.3c, 10.4, 10.5, 10.6) completed with acceptance criteria met (10.5: G1/G3/G5 N/A, no detection change; 10.6: G1/G3/G5 N/A for building the set, its scored-once run is a G1 run)
- [ ] Every story closed with a cited G1 run and an independent G2 check
- [ ] No unapproved recall drop (G3) at any story
- [ ] Held-out set exists and is reported for 10.2, 10.3a, 10.3b, 10.3c and 10.4 (G5)
- [ ] `GUIDELINES.md` approved by Lionel and applied to the whole corpus
- [ ] black, ruff, mypy clean; full CI green (G6)
- [ ] QA report updated with the before/after at every story, and CHANGELOG `[Unreleased]` entries per story (G7)
- [ ] At Epic 10 close-out, README/README.fr, `docs/faq*.md`, `docs/index*.md` and `docs/tutorial*.md` updated once from the final G1 run (G7 interpretation, Lionel, 2026-10-02)
- [ ] Close-out baseline recorded as Epic 9's starting point: run ID plus the pasted `[Overall]`/`[PERSON]`/`[LOCATION]`/`[ORG]`/`[HELD-OUT …]` lines in the QA report (`accuracy-results` artifacts are kept 30 days, `retention-days: 30` at `.github/workflows/accuracy.yaml:83`, so the run ID alone is not enough)
- [ ] Accuracy output reports 95% bootstrap ranges (unit=document) per type for main and held-out, with the eight existing lines unchanged (10.6 PR A)
- [ ] Final-exam set (10.6) sealed before 10.4 merged, with its sha256 recorded, double-annotated with inter-annotator agreement reported, and scored exactly once at close-out: run ID, ledger entry and pasted `[FINAL-EXAM …]` lines in the QA report
- [ ] Public headline figure chosen by Lionel among main, held-out and final exam, with its range (G7 interpretation)
- [ ] No release cut (v2.3.0 only on Lionel's explicit go)

---

## Out of Scope

| Item | Reason | Where |
|------|--------|-------|
| ORG recall for missed brands (OVHcloud, TechCorp, Microsoft Azure, Partech, Kima Ventures, EY) — F10 | A gazetteer built from the brands in the corpus would be overfitting by construction; needs a general approach | Epic 9 or a later story. Related: 10.4 candidate item (QA REQ-001) |
| Different-type overlaps (PERSON vs ORG on the same span), except the exact-match case handled by 10.3c | Needs its own rule and evidence | Later |
| "Keyword + connector(s)" ORG widening, R-KWC ("Chambre d'Agriculture d'Eure-et-Loir", "Cour d'Appel de Paris"). Dry-runs (local, not CI results): 10.3a +1 ORG TP; 10.3b 0 change | Deferred out of 10.3a at STOP R (Lionel, 2026-10-06): it adds new recall rather than fixing a boundary. Routed to 10.4 at 10.3b STOP R (Lionel, 2026-10-07), together with QA REQ-001 (same prefix pattern) | 10.4 candidate item (not an AC) |
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
- Critical compatibility requirements: the product constraints and gates G1-G7 above, verbatim; the guidelines approval stop inside 10.1; strict 10.1 → 10.2 → 10.3a → 10.3b → 10.3c → 10.4 order for detector stories (10.5, data-layer hardening, sits outside that chain), each baseline the previous merged close-out G1 run (10.3 was split into 10.3a and 10.3b, and 10.3c was added at 10.3a STOP R, Lionel, 2026-10-06; see "Course Correction" and "Close-Out Record").
- Story 10.6 (final exam and ranges) runs outside the detector chain. From its PR B on, every story's Dev Notes forbid opening, listing, decrypting or grepping `tests/test_corpus/final_exam/`, next to the held-out isolation rule. Final-exam numbers exist only after close-out and are never used for a decision or for tuning inside Epic 10.
- Each story must include verification that existing functionality remains intact (full CI green, recall guard).

The epic should maintain system integrity while delivering higher detection precision and a trustworthy benchmark, without lowering recall."

---

**Document Status:** DRAFT
**Created:** 2026-10-02
**Author:** John (PM)
