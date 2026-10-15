# Epic 10: v2.3 — Detection Precision Quick Wins - Brownfield Enhancement

**Epic Goal:** Raise detection precision and make the accuracy benchmark trustworthy with local, deterministic changes to the hybrid detector and the ground-truth corpus, without lowering recall. The user-facing value is fewer false entities to reject during the (mandatory) validation step and a benchmark whose numbers can be believed.

**Target Release:** v2.3.0 candidate. **No release is part of this epic.** v2.3.0 ships only on Lionel's explicit go, through a separate release story.
**Duration:** Estimated 7.5-11.5 weeks (10.1 is annotation-labor-bound; 10.3 split into 10.3a and 10.3b, and 10.3c added, Lionel, 2026-10-06; 10.5 added, Lionel, 2026-10-07; 10.3b re-estimated after its STOP R, 2026-10-07; 10.7 added, Lionel, 2026-10-09; 10.8 and 10.9 added, Lionel, 2026-10-13; 10.10 and 10.11 added, Lionel, 2026-10-14); 10.6 runs in parallel (2-3 weeks elapsed) and close-out waits for its adjudication after 10.4 merges, then its commit and one scored run
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

- **What's being changed:** (1) the benchmark is repaired against written annotation guidelines and gains a held-out set; (2) `HybridDetector` gets a same-type overlap rule and an ORG role filter; (3a) spans stop at line breaks and run-on regex name shapes are fixed; (3b) LOCATION noise filters and PERSON boundary rules for particles, Mc/Mac and trailing roles; (3c) the merge's exact-match check becomes type-aware; (4) salutation-aware first-name detection and ORG + country merging, plus two carried coverage losses restored; (6) a second, blind final-exam set written by a different author, kept outside the repo until 10.4 merges, then committed and scored once at close-out, plus bootstrap confidence ranges in the accuracy output.
- **How it integrates:** all detector changes are post-processing steps or patterns inside the existing `HybridDetector` pipeline and its YAML/JSON resources. No public API, CLI flag, GUI screen, mapping-table schema or file format changes. Exception: Story 10.7 (data layer) changes how mapping rows are keyed, and with rule (a), "Convert once" (Lionel, 2026-10-13, 10.7 STOP C) the mapping table's unique key becomes (text, type); see Compatibility Requirements.
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
| 10.3b: Particles, Roles & LOCATION Noise (split from 10.3, Lionel, 2026-10-06) | MED | 0.5-1 week (re-estimated after STOP R, 2026-10-07) | F6, F7 | Done (PR #87, `bab6717`) |
| 10.3c: Type-Aware Exact Match in Merge (added at 10.3a STOP R, Lionel, 2026-10-06) | MED | 0.5 week | 10.3a STOP R | Done (PR #91, `5846419`) |
| 10.4: Greetings + Org-Plus-Country | MED | 0.5-1 week | F8, F9 | Done (PR #93, `2d4a029`) |
| 10.5: DB Init Safety (data-layer hardening, added by Lionel, 2026-10-07) | MED (raised from LOW by the PM, 2026-10-13) | 0.5 week | PR #83 finding | Done (PR #96, `67807c2`) |
| 10.6: Final-Exam Set and Confidence Ranges (added by Lionel, 2026-10-07) | HIGH | 2-3 weeks elapsed, in parallel | Overfitting check, close-out evidence | Done (PRs #89, #92, #94, #95) |
| 10.7: Type-Aware Mapping Lookup (data layer, added by Lionel at 10.3c STOP R, 2026-10-09) | MED | 0.5-1 week | 10.3c STOP R | Done (PR #99, `acb7bdd`) |
| 10.8: Desktop App Type-Aware Candidate Keys (10.3c regression, added by Lionel, 2026-10-13) | HIGH | 0.5 week | 10.7 SM finding | Done (PR #97, `e16d15a`) |
| 10.9: Desktop App Edit Applies to Every Occurrence (added by Lionel, 2026-10-13) | HIGH | 0.5 week | 10.8 SM finding | Done (PR #98, `49d4daa`) |
| 10.10: Desktop Batch Review Fixes (added by Lionel, 2026-10-14) | HIGH | 0.5-1 week | 10.8 QA pre-existing findings PRE-001 to PRE-003 | Done (PR #100, `eee4d41`) |
| 10.11: Custom Pseudonym Stored and Used (added by Lionel, 2026-10-14; not the recommendation) | HIGH (proposed) | 0.5-1 week | 10.8 QA PRE-004; Lionel 2026-10-14 | Draft (open questions for Lionel) |

**Total Estimated Duration:** 7.5-11.5 weeks; 10.6 runs in parallel (2-3 weeks elapsed) and close-out waits for its adjudication after 10.4 merges, then its commit and one scored run

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
| 10.3b | `37641796495` (run D), reproduced on `main` by `37678069251` | P 79.24% / R 79.59% / F1 79.41% | F1 76.79% | PR #87 (`bab6717`) |
| 10.3c | `37963522411` (run P, head `8d25dbe`), reproduced on `main` by `37975010715` | P 79.20% / R 79.77% / F1 79.49% | F1 76.79% | PR #91 (`5846419`) |
| 10.4 | `38173542707` (run K, head `7c1b5fb`, code `2695dee`), reproduced on `main` by `38212303870` | P 80.68% / R 84.65% / F1 82.62% | F1 78.07% | PR #93 (`2d4a029`) |
| 10.6 final exam | `38382553368` (the one scored run, on `main` `c63a7b6`) | Final exam: P 62.33% / R 60.57% / F1 61.44% (CI95 F1 59.26-63.56%); main-corpus lines same as `38212303870` | F1 78.07% (same as 10.4) | PR #92 (`c63a7b6`); ledger PR #94 (`91b500d`) |

- **10.2 recall (G3):** Lionel accepted recall bounds of FN PERSON +21 / LOCATION +4 / ORG +16 versus 10.1 (`37189862679`). Run `37385301566` is inside them: FN PERSON +21 / LOCATION +4 / ORG +10.
- **10.2 held-out ORG recall:** Lionel accepted the drop (held-out ORG FN 28 → 34, `37189862679` → `37385301566`). It is tracked in 10.3a (AC7).
- **Side PRs:** #80 (test offsets in the document processor integration tests) and #82 (performance workflow fix; it makes the NFR1 gate real, since the workflow previously ran no tests).
- **10.3a recall (G3, strict):** main FN 458 (PERSON 50 / LOCATION 54 / ORG 354) versus 480 (53 / 54 / 373) in `37385301566`. No per-type FN increase.
- **10.3a held-out:** FN 59, ORG FN 28 (`37459114468`), versus 70 and 34 in `37385301566`. Held-out ORG FN is back to its 10.1 level (28 in `37189862679`).
- **10.3a QA:** PR #84 merged before QA. The post-merge QA gate is PASS (`docs/qa/gates/10.3a-boundaries-run-on-spans.yml`, PR #85). Its REQ-001 finding is routed to 10.4 (see "Candidate item" there).
- **10.3b close-out:** PR #87 merged as `bab6717`. Close-out run D `37641796495`, reproduced by the `main` push run `37678069251`. Main P 0.7924 / R 0.7959 / F1 0.7941, TP 1763 / FP 462 / FN 452 (PERSON 44 / LOCATION 54 / ORG 354). Held-out F1 0.7679, FN 59 (PERSON 15 / LOCATION 16 / ORG 28), FP 45. NFR1: performance run `37641855606` (AMD EPYC 7763).
- **10.6 PR A (confidence ranges):** PR #89 merged as `6abf858`. G1 run `37856056081`, QA re-run `37860150044`. The eight existing lines are byte-identical to `37678069251` (AC2). Ranges added: `[CI95 …]` lines, unit=document, 10,000 resamples, seed 20261008. The `main` push run `37891970847` on `6abf858` is the JSON-bearing baseline for 10.3c's paired delta (AC3).
- **10.3c close-out:** PR #91 merged as `5846419`. Close-out run P `37963522411` (head `8d25dbe`), reproduced by the `main` push run `37975010715` (16 lines identical; carries `accuracy-per-document.json`). Main P 0.7920 / R 0.7977 / F1 0.7949, TP 1767 / FP 464 / FN 448 (PERSON 42 / LOCATION 52 / ORG 354). Held-out F1 0.7679, FN 59 (PERSON 15 / LOCATION 16 / ORG 28), FP 45. NFR1: performance run `37963988214` (AMD EPYC 7763). STOP R (Lionel, 2026-10-09): R-HYPH-FN adopted; the type-blind mapping lookup became Story 10.7.
- **10.4 close-out:** PR #93 merged as `2d4a029`. Close-out run K `38173542707` (head `7c1b5fb`, a docs-only commit on code `2695dee`), reproduced by the `main` push run `38212303870` (16 lines identical; carries `accuracy-per-document.json`). Main P 0.8068 / R 0.8465 / F1 0.8262, TP 1875 / FP 449 / FN 340 (PERSON 30 / LOCATION 51 / ORG 259). Held-out F1 0.7807, FN 53 (PERSON 15 / LOCATION 16 / ORG 22), FP 47. NFR1: performance run `38174221283` (AMD EPYC 7763). STOP R (Lionel, 2026-10-10): R-DEF-NAME, R-FN-DOC and refined R-ACR adopted. REQ-001 (greeting shapes) deferred to Epic 9 (Lionel, 2026-10-12).
- **10.6 PR B (final-exam set):** PR #92 merged as `c63a7b6`. Its squash message carried throw-away skip-CI titles, so no push workflow ran on `c63a7b6`. Its tree equals PR head `f4c4a7b`, which was 9/9 green, and a manual regular run on `main`, `38383159395`, equals `38212303870` (16 lines). Ledger PR #94 merged as `91b500d`.
- **10.6 final exam (close-out):** committed as plain files at `40692ff` (B11.4, on PR #92; on `main` as `c63a7b6`), with the documents' sha256 matching the freeze record (the scored run's first line: `fingerprints_sha256=faea9dc9…5005`). Scored once in run `38382553368` at `c63a7b6`, dispatched by Lionel on 2026-10-13 (ledger `tests/test_corpus/final_exam/RUNS.md`, PR #94). QA B14.3: PASS. Lines from that run's `accuracy-results`, verbatim:
  ```
  [FINAL-EXAM Overall] P=0.6233 R=0.6057 F1=0.6144 TP=1977 FP=1195 FN=1287 FN%=39.43 FP%=37.67
  [CI95 FINAL-EXAM Overall] P=[0.5956,0.6496] R=[0.5838,0.6281] F1=[0.5926,0.6356] unit=document docs=30 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  [FINAL-EXAM PERSON] P=0.6744 R=0.7098 F1=0.6917 TP=729 FP=352 FN=298
  [CI95 FINAL-EXAM PERSON] P=[0.6240,0.7190] R=[0.6473,0.7651] F1=[0.6393,0.7365] unit=document docs=30 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  [FINAL-EXAM LOCATION] P=0.6727 R=0.7019 F1=0.6870 TP=1003 FP=488 FN=426
  [CI95 FINAL-EXAM LOCATION] P=[0.6360,0.7077] R=[0.6708,0.7324] F1=[0.6562,0.7159] unit=document docs=30 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  [FINAL-EXAM ORG] P=0.4083 R=0.3032 F1=0.3480 TP=245 FP=355 FN=563
  [CI95 FINAL-EXAM ORG] P=[0.3486,0.4686] R=[0.2490,0.3613] F1=[0.2955,0.3997] unit=document docs=30 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  [FINAL-EXAM PLANTED Overall] P=0.6257 R=0.6065 F1=0.6160 TP=1085 FP=649 FN=704 FN%=39.35 FP%=37.43
  [CI95 FINAL-EXAM PLANTED Overall] P=[0.5852,0.6634] R=[0.5839,0.6315] F1=[0.5873,0.6437] unit=document docs=15 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  [FINAL-EXAM NATURAL Overall] P=0.6203 R=0.6047 F1=0.6124 TP=892 FP=546 FN=583 FN%=39.53 FP%=37.97
  [CI95 FINAL-EXAM NATURAL Overall] P=[0.5848,0.6582] R=[0.5668,0.6449] F1=[0.5806,0.6452] unit=document docs=15 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  ```
- **Public number (Lionel, 2026-10-13, 10.6 AC9):** "Final exam as headline (Recommended)".
- **Baseline used by 10.3c:** main push run `37891970847` on `6abf858` (same lines as 10.3b close-out run D; carries `accuracy-per-document.json`).
- **Baseline used by 10.4:** main push run `37975010715` on `5846419` (same 16 lines as 10.3c close-out run P `37963522411`; carries `accuracy-per-document.json`).
- **Epic 10 detector close-out / Epic 9 starting point:** main `38212303870` (main corpus + held-out) and the final exam `38382553368`. Overall lines of `38212303870`, verbatim:
  ```
  [Overall] P=0.8068 R=0.8465 F1=0.8262 TP=1875 FP=449 FN=340 FN%=15.35 FP%=19.32
  [CI95 Overall] P=[0.7782,0.8402] R=[0.8230,0.8659] F1=[0.8054,0.8461] unit=document docs=25 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  [HELD-OUT Overall] P=0.7911 R=0.7706 F1=0.7807 TP=178 FP=47 FN=53 FN%=22.94 FP%=20.89
  [CI95 HELD-OUT Overall] P=[0.7194,0.8564] R=[0.7130,0.8286] F1=[0.7216,0.8342] unit=document docs=6 resamples=10000 seed=20261008 undef_P=0 undef_R=0 undef_F1=0
  ```
- **Carried to Epic 9:**
  - **REQ-001 (10.4 QA gate, greeting shapes):** French spacing before "!" and "et" between two names on a greeting line are not covered. Deferred by Lionel, 2026-10-12 (10.4 story, Decisions Recorded).
  - **REQ-002 (10.4 QA gate, role + place):** a spelled-out French role that spaCy types ORG merges with a following place ("Directeur France" becomes one ORG; the LOCATION "France" is kept). No main-corpus case; noted with the QA lows.
  - **Corpus glob (10.6 PR B QA, B13):** confine `scripts/benchmark_hybrid.py`'s recursive `tests/test_corpus` glob (`:49`, `:237`) to the main-corpus folders before the exam becomes a held-out set.
  - **Q7:** the scored exam becomes a second held-out set (aggregate-only, never opened). The held-out isolation rules then apply to it and its plain-text guard stays active (10.6 B15.3). Epic 9 writes a new blind exam for its own close-out.
  - **Guard hash list (B16):** the guard's committed allowlist (`tests/unit/final_exam_leakage_allowlist.json`, 157 path and sha256 pairs, approved by Lionel 2026-10-13) stores plain sha256 of exam-only keys, with no salt. It reveals nothing beyond the plain files already in the repo. If Epic 9 reuses this guard for its own blind exam, it decides whether a committed hash list needs a salt.
  - **Headline finding:** the main-vs-exam gap. F1 is 0.8262 on the main corpus (`38212303870`) and 0.6144 on the final exam (`38382553368`), about 21 points.
- **Merged since the detector close-out:** 10.5 (PR #96, `67807c2`), 10.8 (PR #97, `e16d15a`), 10.9 (PR #98, `49d4daa`), 10.7 (PR #99, `acb7bdd`) and 10.10 (PR #100, `eee4d41`). None is a detector story.
- **Still open in Epic 10:** 10.11 (custom pseudonym stored and used; Lionel, 2026-10-14: "Make it work (new story)", not the recommendation; four open questions for Lionel before dev; before any release). It is not a detector story, so it does not move the close-out baseline. The epic is not closed.

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

`HybridDetector._merge_entities` (definition `:667`; its `_is_exact_match` call at `:708`) skips a regex detection when `_is_exact_match` (defined at `hybrid_detector.py:2030-2053`) finds a spaCy detection with the same span or the same normalized text. (Line numbers at `main` `4f3cf30`, after PR #90.) The check ignores entity type, so a regex detection is dropped even when spaCy gave the text another type. Example: regex LOCATION "Nice" is dropped because spaCy found ORG "Nice".

**10.3a dry-run measure (local dump on 10.3a's starting code; MX tried as a fall-through into the existing branches, so the Cabinet special case ran first; NOT a CI result, NOT a target):** PERSON TP +2 / FP +2 / FN −2; LOCATION +2 / 0 / −2; ORG 0 / +2 / 0 (10.3a story, Dry-Run Results, "MX alone"). The PERSON FP figure is net: +4 regex PERSON on hyphenated place or company names ("Sophia-Antipolis", "Saint-Gobain" twice, "Clermont-Ferrand") and −2 spaCy PERSON "Cabinet …" removed by the special case; the ORG FP +2 are those two regex "Cabinet …" ORGs. The kept regex entity is flagged `is_ambiguous`.

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
4. **AC4 — Org + country:** an ORG immediately followed by a country, region or city name ("France", "Europe", "UK", "Paris", and others listed in the story) is merged into a single ORG span ("Microsoft France"), and the place keeps its own nested LOCATION ("France"), as the approved guidelines annotate it (GUIDELINES Q3 and G7, decided by Lionel at STOP A, 2026-10-02; G7's meaning test added by amendment A2, 2026-10-03). The merge runs after the 10.2 role filter and never merges a role token (e.g. "VP" + "Europe" is never merged into an ORG); a unit test proves it.
5. **AC5 — Restore carried coverage losses (from 10.2; moved from 10.3a at STOP R, Lionel, 2026-10-06):** two main-corpus annotations that have had no covering detection since 10.2 regain coverage, each by a generic rule (no lexicon entry built from the corpus string):
   - PERSON "Pierre" (`hr_announcement`): a bare known first name at the start of an indented sentence, covered today by no detection. The rule must keep AC3 true (no firing on first names in running text); if both cannot hold, the annotation is reported as still uncovered, with the reason and Lionel's sign-off.
   - ORG "BRS": an abbreviation of an organisation named in the same text ("Banque Régionale du Sud"), covered in v2.2 only by a junk span. Coverage comes from tying the abbreviation to that ORG in the text, not from listing "BRS".
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
- **Normalized-text exact match without containment** (10.3c QA gate, routed to 10.4 by the orchestrator, 2026-10-09): the merge's normalized-text match does not require one span to contain the other ("Zorbalia Dr Zorbalia"), so one occurrence of a name can stay in clear. 0 main-corpus case (0 non-nested pairs among 1,662 exact matches).
- **Related:** F10 (ORG recall) and the R-KWC row, both in Out of Scope.

### Integration Points

- `gdpr_pseudonymizer/nlp/hybrid_detector.py`, `gdpr_pseudonymizer/nlp/regex_matcher.py`
- `gdpr_pseudonymizer/nlp/name_dictionary.py`
- `gdpr_pseudonymizer/resources/salutations.yaml` (new): openers and line-length limit; place names read from `french_geography.json` and `org_role_filter.yaml`; `detection_patterns.yaml` only for a candidate item taken in

### Estimated Effort: 0.5-1 week

---

## Story 10.5: DB Init Safety

**Added by Lionel, 2026-10-07.** Data-layer hardening found during the TEST-002 race fix (PR #83). It is not a detection-precision change. It sits in Epic 10 because this repo puts hardening found along the way into the active epic as a small story (precedents: 4.6.1, 6.7.1), and `epic-list.md` has no backlog section.

**As a** user running several CLI processes against a new mapping database (e.g. from a script),
**I want** a failed initialization never to delete a database that another process just created,
**so that** I do not lose the winner's mappings and passphrase setup to a race.

**Priority:** MEDIUM (raised from LOW by the PM, 2026-10-13, after the SM probe) — rare in interactive use: it needs two processes initializing the same new DB at the same moment, and single CLI or GUI runs initialize once. For this story's own case, a script that starts several first runs on the same new database, it is not rare: two processes started together lost the database in 40 of 40 SM probe pairs on Linux.
**Change type:** Data-layer only. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. It changes no detection, so it has no accuracy baseline and may run before, between or after the detector stories. It does not move the epic close-out baseline.

### Context

`init_database` (`gdpr_pseudonymizer/data/database.py:60`) checks that `db_path` does not exist, creates it, and on **any** exception deletes `db_path` (`database.py:192-196`, "Clean up partial database file on failure"; line numbers at `main` `51d8429`). If two processes create the same new database at once, the loser's cleanup can delete the winner's freshly created file. PR #83 (merged as `5790970`, 2026-10-06) made index creation idempotent (`CREATE INDEX IF NOT EXISTS`). In a real concurrent start, most losers fail earlier, at table creation (`create_all`, `database.py:100`), which #83 did not cover, and others at the metadata key collision (10.5 SM probe on Linux: 31 of 40 at `create_all`, 7 at the metadata insert, 2 with both processes failing). Either way, the delete stays.

- **Windows behaves differently:** the loser's delete fails (WinError 32) and the loser crashes with a raw `PermissionError`; the winner's file survives by accident. The paragraph above describes the POSIX outcome. AC2 covers both.
- **AC4's "still leaves no partial file" is the target state, not today's behaviour:** today a late failure in a single, uncontended initialization leaves `-wal`/`-shm` files (Linux) or the partial `mappings.db` plus a `PermissionError` (Windows). AC4 holds after the fix.

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

### Follow-ups Found by the 10.5 SM (not ACs, 2026-10-13)

- **GUI passphrase message on any "12" (backlog):** the GUI workers show "La phrase secrète doit contenir au moins 12 caractères." for any `ValueError` whose message contains "12" (`gui/workers/detection_worker.py:109`, `gui/workers/processing_worker.py:102`), including any database path that contains "12". Pre-existing, not part of the init race.
- **Stale architecture sketch:** the `init_database` sketch in `docs/architecture/9-database-schema.md` §9.4 lists an `encryption_algorithm` metadata key and JSON-encoded values. The code stores four keys as plain strings (`database.py:161-180`). Docs follow-up for the architect or PM.

### Estimated Effort: 0.5 week

---

## Story 10.6: Final-Exam Set and Confidence Ranges

**Added by Lionel, 2026-10-07**, in answer to "how do we make sure we're not overfitting?". It is benchmark-side work. It runs in parallel, outside the detector chain.

**As a** maintainer about to publish Epic 10's accuracy,
**I want** one blind test that no rule was ever shaped by, scored once, and ranges around every number,
**so that** the public figure reflects how the detector does on documents it has never met, and small story-to-story deltas are not read as wins.

**Priority:** HIGH. It is the evidence for the Epic 10 close-out number.
**Change type:** Benchmark-only (G4). No file under `gdpr_pseudonymizer/` changes. Two PRs: PR A (confidence ranges, scorer-side reporting) and PR B (final-exam set, freeze record, CI job, leakage guard).
**Ordering:** outside the detector chain, like 10.5. PR A should land early, so 10.3c and 10.4 report ranges. PR B's 30 documents are frozen, and both model annotations are done, before 10.4 merges. They must not influence 10.3c or 10.4. Lionel adjudicates after 10.4 merges. The documents and adjudicated annotations are then committed as plain files and scored exactly once, at Epic 10 close-out. Close-out waits for his adjudication.

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

**PR B: final-exam set**

4. **AC4 — Brief and author.**
   - The set has 30 synthetic French documents (Lionel, Q2). The formats are messier than the main corpus: email threads with quoted replies, PDF-style hard line breaks, tables flattened to text, mixed case, headers and signatures.
   - 15 documents are planted with the known hard-case categories and 15 are natural, with no planted case (Lionel, Q6). The half each document belongs to is recorded with the set, so AC8 can score each half.
   - The author is GPT via `codex exec` (Lionel, Q1). It is **not** a rule-writing agent.
   - The author brief lists formats and hard-case categories. It names categories only, never corpus examples. It contains no GUIDELINES text and no corpus or held-out text. Lionel approves the brief before any generation.
   - No real public figures and no real people. No user data, no copy of real records (product constraint 4).
   - An annotator who meets a real person or public figure flags it, and the name is replaced consistently before freeze.
5. **AC5 — Double blind annotation, with agreement reported.**
   - Two independent annotations are made under `tests/test_corpus/annotations/GUIDELINES.md` (Lionel, Q3):
     - Annotator A is GPT via `codex exec`.
     - Annotator B is Kimi (Moonshot), or Gemini if Kimi access fails.
     - Neither sees the other's output. Neither is pre-annotated by the detector or by any auto-annotator.
     - Lionel does no hand annotation. Claude agents do not annotate, because they write the rules.
   - Inter-annotator agreement is reported per type as pairwise span F1. It uses the scorer's own matching (exact text and type after `_match_key`, one-to-one). Disagreements are counted by class.
   - Lionel adjudicates the disagreements only, under GUIDELINES, after 10.4 merges (Q4). The adjudication is logged. A case GUIDELINES does not cover goes to Lionel as an amendment, as in 10.1.
   - **Spot-check:** Lionel also checks about 3 documents where the two annotations agree, to catch errors both models share. The finding (the number of shared errors, by class) is reported next to the agreement figures.
   - The report holds only agreement figures, spot-check counts and classes, never entity text.
6. **AC6 — Frozen, adjudicated, then committed.**
   - Authoring and annotation happen in an isolated workspace outside the repo. Orchestrating agents handle only paths, hashes and counts, and never print document or annotation content.
   - **Freeze, before 10.4 merges:** once both model annotations are done, the 30 documents and the two annotations are frozen in that workspace. Their sha256 fingerprints are recorded in this story (the freeze record), as proof that the texts are not edited later. Nothing is encrypted.
   - **Adjudication, after 10.4 merges:** Lionel adjudicates and spot-checks (AC5). Any adjudication view shown to him is produced by a deterministic local script. Agents run that script without printing or reading its output.
   - **Commit, after adjudication:** the documents, the adjudicated annotations and the adjudication log (both model annotations, Lionel's decisions, the spot-check) are committed as plain files under `tests/test_corpus/final_exam/`. At commit time, the documents' sha256 fingerprints are checked against the freeze record; a mismatch stops the commit and goes to Lionel. The sha256 of the adjudicated annotations is added to the record.
   - The folder is outside every path the regular accuracy job loads, and outside `accuracy.yaml`'s push `paths`.
   - Storage: plain files in the repo, committed only after 10.4 merges. No encryption, no key, no GitHub environment (Lionel, Q5 reversed, 2026-10-09).
7. **AC7 — Leakage guard covers the final exam.**
   - A plain-text check of the same kind as the held-out guard: `tests/unit/test_held_out_leakage.py`, or a sibling test, takes the final-exam-only strings from the committed final-exam annotations (normalized as `_match_key` does, and not occurring in the main-corpus text) and checks `gdpr_pseudonymizer/resources/**` and `tests/unit/**` for them. It reports paths and hashes only, never the string. There is no salted hash list.
   - It is active from the AC6 commit onward, on every CI run. Its first run checks every file that 10.3c and 10.4 added.
   - The held-out-blind rule (10.3b AC12) applies unchanged: any real string in a new test or resource must occur in main-corpus text or be approved by Lionel.
8. **AC8 — Scored exactly once, and enforced.**
   - **Trigger:** the final exam runs only on a manual `accuracy.yaml` dispatch whose `final_exam` input equals `final exam`. The job has no environment binding (Q5 reversed, 2026-10-09).
   - **Job:** before scoring, the job checks the folder's sha256 fingerprints against the freeze record (the adjudicated annotations against the value added at commit, AC6). It then runs the usual suite and appends `[FINAL-EXAM Overall]`/`[FINAL-EXAM PERSON]`/`[FINAL-EXAM LOCATION]`/`[FINAL-EXAM ORG]` lines plus their CI95 lines to `accuracy-output.txt` in the `accuracy-results` artifact. The regular job is skipped in that run, so there is one `accuracy-results`.
   - **No exam text in public CI logs:** errors print the error class and a document id only; the detector logs at CRITICAL in that job; pytest runs with `--tb=short` or an equivalent, so a failing test never prints its arguments (QA SEC-001, PR A).
   - **Per half (Q6):** the same Overall and per-type lines, each with its CI95 line, are also printed for each half: `[FINAL-EXAM PLANTED …]` for the 15 planted documents and `[FINAL-EXAM NATURAL …]` for the 15 natural ones.
   - **Why this shape:** the close-out evidence must be a G1 run as the Gates block defines it (an `accuracy.yaml` run, cited by ID, lines pasted from `accuracy-results`). With this shape G1 and G2 apply word for word. This is why the job lives inside `accuracy.yaml` rather than in a separate workflow.
   - **Ledger:** a committed ledger (e.g. `tests/test_corpus/final_exam/RUNS.md`) records the one scored run: run ID, commit, date, and Lionel's approval. A re-run is allowed only for an infrastructure failure at the **same** commit, with the reason recorded. A run at a later commit is a second look, and it is forbidden within Epic 10.
   - **Numbers are never inputs:** final-exam numbers are never used for a decision or for tuning. No agent opens, lists or greps the set, in its workspace outside the repo or in `tests/test_corpus/final_exam/`. From the start of 10.6 authoring, every later story's Dev Notes restate this, next to the held-out isolation rule.
   - **Before the real run:** QA proves the job on a **dummy** fixture (invented text, with its own fingerprint record) and never on the real set. This proves the job wiring (trigger, fingerprint check, skipped regular job, artifact lines, quiet logs) without spending the one real run.
9. **AC9 — Close-out reporting and the public number.**
   - At Epic 10 close-out (10.4 merged), the QA report and the epic Close-Out Record carry the main, held-out and final-exam figures, each with its range. The lines are pasted verbatim, because `accuracy-results` artifacts are kept 30 days (`accuracy.yaml:83`).
   - Lionel decides which figure is public: main, held-out, final exam, or a stated combination. This is recorded under G7 and the Epic 10 G7 interpretation. README/README.fr, FAQ, docs index and tutorials then change once, from that run.
10. **AC10 — Gates.**
    - **Building the set (PR B):** G1, G3 and G5 are N/A, because no detector change is made. The scored-once run (AC8) is the close-out evidence, and it is a G1 run.
    - **PR A:** G1 applies (its run shows the eight lines unchanged, AC2). G3 holds trivially, because the lines are identical.
    - **G2:** QA re-checks the ranges independently. For PR A, it recomputes them from the AC3 JSON with the printed seed. For PR B, it checks the workflow (trigger, fingerprint check, quiet logs), ledger and guard on the dummy fixture, and at the AC6 commit it checks the fingerprint match from the hashes alone. At close-out, it downloads the final-exam run's `accuracy-results` itself.
    - **G4:** benchmark-side only. PR A and PR B are each separate from any detector PR.
    - **G6** applies in full.
    - **G7:** no headline change until close-out, then AC9. CHANGELOG `[Unreleased]` gets an entry for PR A (new report lines) and for PR B (final-exam set and CI job).

### Integration Points

- `tests/accuracy/conftest.py`, `tests/accuracy/test_ner_accuracy_validation.py`: ranges, per-document JSON, final-exam scoring
- `.github/workflows/accuracy.yaml`: `final_exam` dispatch input, final-exam job (fingerprint check, quiet logs, no environment binding), artifact contents
- `tests/unit/test_held_out_leakage.py` (or a sibling): final-exam plain-text check
- `tests/test_corpus/final_exam/` (new): plain documents, adjudicated annotations, adjudication log, `RUNS.md` ledger, README
- `scripts/`: the paired-delta script (AC3), the deterministic adjudication-view script (AC6) and the sha256 fingerprint check against the freeze record (AC6, AC8). No sealing script; `cryptography` is not used.
- `docs/qa/ner-accuracy-report.md`: ranges from PR A on; final-exam section at close-out

### Estimated Effort: 2-3 weeks elapsed (adjudication waits for 10.4 to merge), in parallel with 10.3c and 10.4

- PR A: about 2-3 days (ranges, JSON, paired-delta script, G1 run, QA).
- PR B, tooling: about 1-2 days (freeze record and fingerprint check, workflow job, ledger, plain-text guard, adjudication-view script, dummy-fixture proof). No encryption or key handling since the Q5 reversal (2026-10-09).
- PR B, set: GPT writes the 30 documents from the approved brief. GPT and Kimi (or Gemini) then annotate them independently. This is machine time, not Lionel's.
- Lionel's time: after 10.4 merges, he adjudicates the disagreements and spot-checks about 3 agreed documents (AC5). Its size depends on the agreement rate, so it is not estimated here.
- Close-out: Lionel's adjudication, the commit of the plain files (fingerprints checked), one scored run, then the reporting in AC9.

### Decisions Recorded (Lionel, 2026-10-08)

- **Q1 — Author:** GPT via `codex exec`, from a brief Lionel approves before any generation.
- **Q2 — Document count:** 30.
  - The recommendation at the time was 20, made while Lionel was going to annotate by hand. Lionel kept 30 after Q3 was redone.
  - At held-out density, 30 documents give about 255 ORG annotations, so 1 ORG miss is about 0.4 recall point, against about 2 points on today's held-out set. This is a projection from held-out averages, not a count.
- **Q3 — Annotators and adjudicator:**
  - *Superseded (first answer):* ~~GPT via `codex exec` as annotator A and Lionel annotating by hand as annotator B, with Lionel adjudicating.~~
  - *Redone, and this supersedes the first answer:* Lionel had understood "GPT-assisted" as confirming edge cases only, not annotating by hand.
    - Annotator A is GPT via `codex exec`. Annotator B is Kimi (Moonshot), with Gemini as the fallback if Kimi access fails. The two annotate independently.
    - Lionel adjudicates the disagreements only. He also spot-checks about 3 documents where the two agreed, to catch shared errors. The spot-check finding (the number of shared errors, by class, no entity text) is reported next to the agreement figures.
    - Lionel does no hand annotation. Claude agents stay excluded, because they write the rules.
- **Q4 — Lionel's exposure:**
  - Lionel sees no final-exam content until 10.4 has merged.
  - The documents are frozen, and both model annotations are done, before 10.4 merges. Their sha256 values are recorded ~~and the material is kept encrypted~~ (encryption dropped, see "Q5 reversed" below).
  - Lionel's adjudication and spot-check happen after 10.4 merges. The final archive (documents plus adjudicated annotations) is then ~~sealed~~ committed as plain files (see "Q5 reversed" below) and scored once.
  - Close-out waits for his adjudication.
- **Q5 — Storage:**
  - *Superseded (reversed by Lionel, 2026-10-09, see the next bullet):* ~~An encrypted archive in the repo, with the key only in the GitHub environment `final-exam`, where Lionel is the required reviewer. Lionel runs the sealing command himself, so no agent ever holds the key.~~
  - Not affected by the reversal: any adjudication view shown to Lionel is produced by a deterministic local script. Agents run it without printing or reading its content.
- **Q5 reversed (Lionel, 2026-10-09): no encryption, no key, no environment gate.**
  - Lionel asked "why on earth we're encrypting the 'exam'", then, after the explanation: "yes, and also, we're protected from whom? that's what i'm wondering."
  - Reasoning: the only risk is contamination of the rule writers (agents, and Lionel at STOP R) during detector work, and Q4 already prevents it: the exam lives in a workspace outside the repo until 10.4 merges, and Lionel adjudicates only after. Encryption and the Lionel-approved GitHub environment guarded nothing beyond that.
  - New design: sha256 fingerprints recorded at freeze; after adjudication, plain files committed under `tests/test_corpus/final_exam/`, checked against the freeze record (AC6); a plain-text leakage guard (AC7); one manual `accuracy.yaml` dispatch with no environment binding (AC8).
  - The `final-exam` environment approval gate was dropped by the orchestrator on the same reasoning. Lionel may restore it.
- **Q6 — Seeding:**
  - 15 documents are planted with the known hard-case categories (particles, Mc/Mac, greetings, role acronyms, foreign places, ORG plus country). The brief names the categories only, never corpus examples. The other 15 are natural.
  - The final-exam output reports the overall figures and each half, with CI95 (AC8).
- **Q7 — After Epic 10:**
  - Once scored, the exam becomes a second held-out set (aggregate-only, never opened). That takes the held-out pool from 6 to 36 documents.
  - Epic 9 writes a new blind final exam for its own close-out.
  - This records intent for Epic 9. It changes nothing in Epic 10.
- **Q8 — AC3 (paired delta):** kept.
- **Q9 — Public number:** still open. Lionel decides at close-out (AC9).

---

## Story 10.7: Type-Aware Mapping Lookup

**Added by Lionel at the 10.3c STOP R, 2026-10-09.** Asked "the pseudonym database looks names up without their type. Plan a later story to make that lookup type-aware?", he answered "Add a follow-up story". The orchestrator had recommended keeping it out of Epic 10. It is not a detection-precision change: like 10.5, it is a data-layer story found along the way.

**As a** user who confirms the same text under two entity types (for example a person and a place),
**I want** each type to get its own pseudonym and its own mapping row, and a text already known under one type to reach validation when it shows up under another,
**so that** the type I choose during validation is the type that is stored and pseudonymized.

**Priority:** MEDIUM — no text is left in clear today in the CLI (the desktop app's same-span case is Story 10.8), but 10.3c keeps more different-type pairs, and for those the type choice can be lost.
**Change type:** `core/` and data layer, plus the callers that look up by name in `cli/` and `gui/` (AC4). No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain, like 10.5. It changes no detection, so it has no accuracy baseline and may run in any slot. It does not move the epic close-out baseline. Its effect shows most once 10.3c has merged. It merges after Story 10.8, which fixes the desktop app's text-only keys.

### Context

At `main` `4f3cf30`, mapping keys carry no entity type:

- `Entity.full_name` is unique on its own (`gdpr_pseudonymizer/data/models.py:38`). Each row stores an `entity_type` (`:31`), but no lookup uses it.
- `SQLiteMappingRepository.find_by_full_name` (`gdpr_pseudonymizer/data/repositories/mapping_repository.py:148`) queries by the encrypted text only.
- In `gdpr_pseudonymizer/core/document_processor.py`, `_normalize_entity_text` (`:211`) builds the key from the text alone (titles stripped, and prepositions for LOCATION). Three places then look it up without the type: the validation preview and its `preview_cache` (`:254`), the known/unknown split before validation (`:297-308`), and `_resolve_pseudonyms` with its per-run `entity_cache` (`:489`, lookup `:507`).
- Other callers look up by name alone too: `delete-mapping` (`gdpr_pseudonymizer/cli/commands/delete_mapping.py:118`, and its delete call at `:146`), `import-mappings` (`gdpr_pseudonymizer/cli/commands/import_mappings.py:164`), the GUI known-entity check (`gdpr_pseudonymizer/gui/models/validation_state.py:111`), the repository's race fallback (`mapping_repository.py:345`) and `delete_entity_by_full_name` (`:388`).
- `build_pseudonym_previews` (`core/document_processor.py:759-802`, key `:786`) fills the desktop app's preview map through the same validation preview (`:254`); its callers are `gui/workers/detection_worker.py:199` and `gui/screens/batch.py:896`. The desktop app also keys three per-run maps without the type: the preview map (read at `validation_state.py:86-88`), the variant map (`gui/workers/detection_worker.py:154-157`, read at `validation_state.py:313-331`) and the same-text group that accept and reject act on (`validation_state.py:89-93`, `:128`, `:144`). Story 10.8 keys these three on type (they were AC9 of the 10.7 SM draft).

Consequences once 10.3c keeps both detections of a different-type pair:

- If the user confirms both, they share one pseudonym and one database row.
- If the text is already in the database, both are auto-accepted as known and never shown, so the type choice never reaches the user.
- In the CLI, no text is left in clear: every confirmed occurrence is still replaced. In the desktop app, the text-only variant map can drop one type's occurrences from finalization, so one can stay in clear (10.7 SM probe; 0 positions on the main corpus). Story 10.8 fixes that before 10.7.

### Acceptance Criteria

1. **AC1 — Separate pseudonyms per type:** the same normalized text under a different entity type gets its own pseudonym and its own mapping row. The same text under the same type keeps today's behaviour: one row, one pseudonym, reused.
2. **AC2 — Type-aware lookups and caches:** the known-entity check, the validation preview, `_resolve_pseudonyms` and the per-run caches key on text and type. A text known only under another type is unknown for the new type, so it reaches the validation step (for databases created before 10.7, AC3 applies). The PERSON component match (`_check_component_match`) is unchanged.
3. **AC3 — Continuity for existing databases (decision for Lionel at this story's STOP):**
   - Databases created before 10.7 hold one row per text. The story defines what happens to them, so that existing pseudonyms stay stable for existing documents.
   - The story presents the options with their trade-offs, for example a migration (each existing row keeps its pseudonym under its stored `entity_type`) or read-compatibility (on a pre-10.7 database, a type-aware miss falls back to the text-only row, as today), or another rule it proposes. Lionel decides at the STOP. The story does not pick one before.
   - Whatever the rule: no existing row is deleted or given a new pseudonym, the database still opens with its passphrase, and a pre-10.7 database is detected reliably (e.g. through `schema_version`, `gdpr_pseudonymizer/data/database.py:161`).
   - If the rule changes the schema (today `full_name` is unique on its own), the story says so and updates the Compatibility Requirements of this epic.
4. **AC4 — Other name lookups:** every other caller listed in Context has its behaviour under AC1-AC3 written in the story and tested. `delete-mapping` (GDPR Article 17 erasure) never leaves a row of another type for the requested name behind without telling the user.
5. **AC5 — Tests, invented names only:** same text under two types (two rows, two pseudonyms); same text and type (reused, unchanged); a text known under one type and met under another (not auto-accepted, AC2); both types in one document (per-run cache); the AC3 rule on a database written by the pre-10.7 code (fixture built in the test); the AC4 callers. Existing database and document-processor tests stay green.
6. **AC6 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change, so no accuracy run is required and recall cannot move. The PR states this explicitly. No public number changes.
   - **G4:** `core/` and data-layer change (plus the AC4 callers), never in the same PR as a detector change.
   - **G2:** QA verifies the change independently by re-running the AC5 tests, including the AC3 rule on a pre-10.7 database, and reading the diff. There is no accuracy artifact to download.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes, so no QA report or docs update. CHANGELOG `[Unreleased]` gets an entry with an upgrade note: what happens to existing databases (AC3), and that the same text under two types now gets two pseudonyms.

### Integration Points

- `gdpr_pseudonymizer/core/document_processor.py` — `_normalize_entity_text`, the validation preview and its cache, the known-entity split, `_resolve_pseudonyms` and its cache
- `gdpr_pseudonymizer/data/repositories/mapping_repository.py` — lookups by name (`find_by_full_name`, the race fallback, `delete_entity_by_full_name`)
- `gdpr_pseudonymizer/data/models.py`, `gdpr_pseudonymizer/data/database.py` — row key and `schema_version`, if the AC3 rule needs them
- `gdpr_pseudonymizer/cli/commands/delete_mapping.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`, `gdpr_pseudonymizer/gui/models/validation_state.py` — other name lookups (AC4)
- `gdpr_pseudonymizer/gui/workers/detection_worker.py`, `gdpr_pseudonymizer/gui/screens/batch.py` — callers of `build_pseudonym_previews` (`:199`, `:896`); the desktop app's text-only keys themselves are Story 10.8
- `tests/unit/` or `tests/integration/` — AC5 tests
- `docs/CLI-REFERENCE.md` and `docs/CLI-REFERENCE.fr.md`, `### delete-mapping` — docs exception (PO item 3, 2026-10-13): one line each on the new visible behaviour (every row of the name is removed). These are not G7 headline docs; README, FAQ, docs index, tutorials and the QA report stay untouched

### Follow-ups Found by the 10.7 SM (not ACs, 2026-10-13)

- **Stale architecture docs:** `docs/architecture/6-components.md:158` says `schema_version` is "checked on open", but `open_database` never reads it. `docs/architecture/9-database-schema.md` §9.1 says Fernet (AES-128-CBC + HMAC), while the code uses AES-256-SIV (`data/encryption.py`, as §9.3 of the same document shows); its table definition (§9.2) has no `UNIQUE (full_name)` and has a `CHECK (entity_type IN …)` that the code does not create. Docs follow-up for the architect or PM. Under rule (a) (STOP C, 2026-10-13) the schema changes, so §9.2 changes with it.
- **`import-mappings` "Replace existing mapping?" never replaces** (`cli/commands/import_mappings.py:178-205`): answering yes saves a new row, the save hits the unique key, and the row is counted as skipped. Pre-existing, not a type-awareness change. Carried as an Epic 9 or backlog item, not fixed in 10.7.
- **Erasure audit entry keeps the erased name (optional backlog item, Lionel's call; not part of 10.7):** the ERASURE audit entry stores the erased name unencrypted (`cli/commands/delete_mapping.py:167`, `deleted_entity_name` in the `operations` table), so after `delete-mapping` the name is still in the file (10.7 PO N7).

### Estimated Effort: 0.5-1 week (the upper end if the AC3 rule is a migration)

---

## Story 10.8: Desktop App Type-Aware Candidate Keys (10.3c regression)

**Added by Lionel, 2026-10-13** ("Fix now, own story (Recommended)"), from the 10.7 SM's finding at `main` `51d8429`. The 10.7 SM draft (`55a87e4`) had this as its AC9. It moves here, so the fix does not wait for 10.7's continuity decision.

**As a** desktop-app user reviewing a name found at one place with two types,
**I want** each type to be its own candidate, with its own preview, its own occurrences and its own accept or reject,
**so that** rejecting one type keeps the other, and no occurrence of a name I confirmed is left in clear.

**Priority:** HIGH — it is a leak path in the desktop app: an occurrence of a confirmed name can stay in clear. It must be fixed before any release. It is on `main` only (since 10.3c), unreleased.
**Change type:** desktop app and core preview keys only. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes. If any file the accuracy suite loads is touched, one regular accuracy run on the branch shows the 16 lines identical to `38212303870`.
**Ordering:** outside the detector chain, like 10.5 and 10.7. It merges before 10.7 and does not depend on 10.7's continuity decision (10.7 AC3).

### Context

Since 10.3c (R-MX), one span can be kept with two types: the regex detection is flagged ambiguous and both reach validation. At `main` `51d8429`:

- The desktop app keys two per-run maps as `"{text}_{start}"`, without the type: the preview map built by `build_pseudonym_previews` (`gdpr_pseudonymizer/core/document_processor.py:786`, read at `gdpr_pseudonymizer/gui/models/validation_state.py:86`) and the variant map (`gdpr_pseudonymizer/gui/workers/detection_worker.py:156`, read at `validation_state.py:328` for finalization and `:344` for highlights).
- The same-text group that accept and reject act on is keyed by text alone (`validation_state.py:89-93`, used at `:128` and `:144`).
- So for a pair at one span, the second type's entry overwrites the first, and rejecting one type rejects both. This contradicts the 10.3c CHANGELOG `[Unreleased]` line "Rejecting one candidate gives the earlier result for the other".
- **Probe (10.7 and 10.8 SM probes, invented name; re-run by the PM on 2026-10-13 on code identical to `51d8429`):** ORG "Zorbaville" at 0 and at 21, plus LOCATION "Zorbaville" at 0, came out of finalization as [LOCATION 0, LOCATION 0]. The ORG at 21 would stay in clear.
  - **Reverse order** (LOCATION listed first): accepting both sent [ORG 0, ORG 21, ORG 0, ORG 21]. The LOCATION was retyped to ORG, and the ORG positions were sent twice.
  - **Batch screen** (one row per detection, no variant map): the same-text group held all three rows, so rejecting the LOCATION row also rejected both ORG rows, and nothing was sent for "Zorbaville".
- **Previews (PO S1):** after 10.8, each row gets its own preview entry, title included. The suggested pseudonym itself becomes type-aware only with Story 10.7; until then, a row of one type can show a pseudonym drawn for the other type (the assigner's per-run cache is type-blind).
- **Main corpus (10.4 close-out detections, local, not a CI result):** 11 spans with two types, 8 key collisions in 5 documents, 0 positions left in clear.
- **The CLI is not affected:** it already groups by (text, type) (`gdpr_pseudonymizer/validation/models.py:416`).

### Acceptance Criteria

1. **AC1 — Keys include the type:** the preview map and the variant map key on text, start and type, and the same-text group keys on text and type, as the CLI groups already do. This covers `build_pseudonym_previews`, `detection_worker.py`, `validation_state.py` and every caller and reader of these maps (including `gui/screens/batch.py:896`).
2. **AC2 — The probe case and its reverse:** ORG "Zorbaville" at 0 and at 21 with LOCATION "Zorbaville" at 0 finalizes to every occurrence with its own type, in both list orders. No occurrence is dropped or retyped.
3. **AC3 — Rejecting one type keeps the other:** accepting or rejecting one type of a same-span pair changes only that type's group; the other type keeps its state.
4. **AC4 — No variant-map collision:** two variant groups with the same canonical text and start but different types get separate entries, and the highlight ranges map each occurrence to its own review row.
5. **AC5 — Tests first, invented names only:** unit tests for AC1–AC4 use invented names only. Run on the unchanged code, every test of a changed behaviour fails; the dev records the list. The fix then makes them pass. Existing GUI and CLI validation tests stay green; tests that build the review list's key by hand change only how they build it.
6. **AC6 — CHANGELOG:** CHANGELOG `[Unreleased]` corrects the 10.3c line "Rejecting one candidate gives the earlier result for the other", so that it holds for the desktop app too, and records the desktop-app fix.
7. **AC7 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** desktop app and core preview keys only, never in the same PR as a detector change.
   - **G2:** QA re-runs the AC5 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes, so no QA report or docs update. CHANGELOG as AC6.

### Integration Points

- `gdpr_pseudonymizer/core/document_processor.py` — `build_pseudonym_previews` (`:759`, key at `:786`)
- `gdpr_pseudonymizer/gui/workers/detection_worker.py` — variant map (`:156`), previews call (`:199`)
- `gdpr_pseudonymizer/gui/models/validation_state.py` — preview read (`:86`), same-text group (`:89-93`, `:128`, `:144`), finalization (`:328`), highlight ranges (`:344`)
- `gdpr_pseudonymizer/gui/screens/batch.py` — previews call (`:896`)
- `gdpr_pseudonymizer/validation/models.py` — the key function `candidate_key()` (new; the CLI's grouping is unchanged)
- `gdpr_pseudonymizer/gui/screens/validation.py` — the `set_context` docstring line (`:332`) only
- Existing tests, key construction only (AC5): `tests/unit/test_document_processor.py::TestBuildPseudonymPreviews` `test_happy_path_new_entities` (`:628-629`), `test_existing_mapping` (`:690`) and `test_title_preservation` (`:753-755`); and `tests/unit/gui/test_validation_state.py::TestGUIValidationStateInit::test_pseudonym_previews_assigned`, through the shared fixture `sample_detection_result` (`tests/unit/gui/conftest.py:134-155`)
- `tests/unit/` — AC5 tests; `CHANGELOG.md` — AC6

### Estimated Effort: 0.5 week

---

## Story 10.9: Desktop App Edit Applies to Every Occurrence

**Added by Lionel, 2026-10-13** ("Own story, before release (Recommended)"). The option text he saw: "New small story 10.9. Desktop edit applies to all occurrences, like the CLI. Must land before the next release. 10.8 stays narrow (keys only). Tests first, invented names." From the 10.8 SM's finding at `main` `51d8429`.

**Decisions (Lionel, 2026-10-14), each the recommendation; the 10.9 story records the questions word for word:**

- **Q1, the desktop type change: "Fold into 10.9 (Recommended)".** A desktop type change applies to every occurrence of that name, as in the command line (10.9 story, AC9).
- **UX-001: "Fix in 10.9 (Rec.)".** QA found that the edit dialog reopened on the detected text ("Valmont") instead of the user's edit ("Quentrix Valmont"), so a second edit silently dropped the first. Preview he saw: reopening shows the latest edit ("Quentrix Valmont"); a second edit builds on it; the whole name is replaced at every place (10.9 story, AC10).
- **Rejected places: "Skip rejected places (Rec.)".** "Zorbal" is found three times; the third is part of "Saint-Zorbal", which the user rejects on its own; a correction on another row also reached the rejected row (output "Saint-[pseudonym]"). Preview he saw: rows 1 and 2 corrected and pseudonymized; Saint-Zorbal stays rejected, left as is. A correction or a type change never reaches a place the user rejected (10.9 story, AC11; 10.10 follows).

**As a** desktop-app user correcting a detected name in the review list,
**I want** my edit to apply to every occurrence of that name and type, as it does in the CLI,
**so that** no other occurrence of the name is left in clear.

**Priority:** HIGH — it is a leak path: after an edit, the other occurrences of the name are not pseudonymized. It must land before the next release. It is not a 10.3c regression: the behaviour is in every desktop release since v2.0.0 (Story 6.8, PR #57), and the code is unchanged since v2.2.0.
**Change type:** desktop app review only. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes. If any file the accuracy suite loads is touched, one regular accuracy run on the branch shows the 16 lines identical to `38212303870`.
**Ordering:** outside the detector chain. It goes after Story 10.8, because both change `gui/models/validation_state.py`, and never in the same PR as 10.8 (10.8 stays narrow: keys only).

### Context

At `main` `51d8429`:

- **Desktop app:** editing a name's text in the review list (`GUIValidationState.modify_entity_text`, `gdpr_pseudonymizer/gui/models/validation_state.py:155-164`) pushes one `_ModifyTextCommand` (`:404`, `redo` `:427-439`), which changes that one review row. The row stands for every occurrence of its name (the variant map, `gui/workers/detection_worker.py:154-157`), but at finalization `expand_validated_entities` keeps a MODIFIED entity "as-is (single position)" (`validation_state.py:313-333`, docstring `:320`): the edited text no longer matches the variant-map key, so only that one occurrence is sent. The other occurrences stay in clear.
- **CLI:** the same edit applies to every occurrence of the group (`gdpr_pseudonymizer/validation/workflow.py:242-259`, "Apply modification to all occurrences in group", each span located by `_locate_modified_span`, `:432`), and its groups are (text, type) (`validation/models.py:416`).
- **Probe (10.8 SM, invented name; re-run by the PM on 2026-10-13 on code identical to `51d8429`):** PERSON "Quentrel Zorbalia" at 0 and at 30; editing the row's text to "Quentrel Zorbalia parle" (0-23) finalizes to [PERSON 0-23] only. The occurrence at 30 is not pseudonymized.
- **Not a 10.3c regression:** `validation_state.py` and `detection_worker.py` are unchanged between `v2.2.0` and `51d8429`, and the single-position rule is in every tag from `v2.0.0`.

### Acceptance Criteria

1. **AC1 — An edit applies to every occurrence:** in the desktop app, editing the text of a name applies the edit to every occurrence of that name and type, as the CLI does (`validation/workflow.py:242-259`). Finalization sends every occurrence, each with its edited span. One undo reverts the whole edit.
2. **AC2 — Tests first, invented names only:** unit tests for AC1 use invented names only, starting from the probe case. Run on the unchanged code, every test of the changed behaviour fails; the dev records the list. The fix then makes them pass. Existing GUI and CLI validation tests stay green.
3. **AC3 — CHANGELOG:** CHANGELOG `[Unreleased]` gets a "Fixed" line: in the desktop app, editing a name now applies to every occurrence of it, as in the CLI.
4. **AC4 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** desktop app review only, never in the same PR as a detector change or as Story 10.8.
   - **G2:** QA re-runs the AC2 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes, so no QA report or docs update. CHANGELOG as AC3.

### Integration Points

- `gdpr_pseudonymizer/gui/models/validation_state.py` — `modify_entity_text` (`:155-164`), `_ModifyTextCommand` (`:404`), `expand_validated_entities` (`:313-333`)
- `gdpr_pseudonymizer/gui/workers/detection_worker.py` — the variant map (`:154-157`), read only
- `gdpr_pseudonymizer/validation/workflow.py` — the CLI behaviour to match (`:242-259`), read only
- `tests/unit/` — AC2 tests; `CHANGELOG.md` — AC3

### Estimated Effort: 0.5 week

---

## Story 10.10: Desktop Batch Review Fixes

**Added by Lionel, 2026-10-14.** PRE-001: "Own story, before release (Recommended)". PRE-002 and PRE-003: "Into 10.10 (Recommended)", so the story covers all three. They are QA's pre-existing findings on Story 10.8 (`docs/qa/gates/10.8-gui-type-aware-candidate-keys.yml`, `pre_existing_findings`), not caused by 10.8.

**Q3, GRP-001 (Lionel, 2026-10-14): "Every place (Rec.)"**, the recommendation. Question asked: "10.10, one more. The detector finds "Quentrel Zorbalia" at two places and misses a third, which you add by hand. Then you correct the name to "Quentrel Zorbalia Quentrix". Should that correction reach every place of the name, whether the detector found it or you added it? Accept and reject always stay on the row you click; that is the fix for the earlier reject bug." The preview he saw: correct any one of [found] [found] [added by you] → all three become "Quentrel Zorbalia Quentrix", one pseudonym; accept / reject → only the row you click.

**Further decisions on the same rule (Lionel, 2026-10-14), each the recommendation:**

- **Q3 correction, accept and reject on found places: "Keep group action (Rec.)".** The Q3 wording "Accept and reject always stay on the row you click" was wrong for detected rows. Preview he saw: accept or reject a found place → both found places; accept or reject the added place → that place only; correct the name anywhere → all three.
- **Group accept and a place rejected on its own: "Skip rejected (Rec.)".** Preview: accept row 1 again → rows 1 and 2 accepted, Saint-Zorbal stays rejected; clicking Saint-Zorbal itself accepts it.
- **Q5, group reject and a place accepted or corrected on its own: "Skip your own (Rec.)".** Preview: the person's place, accepted on its own, stays accepted when rejecting from row 2; rows 2 and 3 rejected; a group accept then a group reject → all rejected.
- **Q6, "Accepter les déjà connues" and rejected places: "Skip rejected (Rec.)".** Preview: Saint-Zorbal stays rejected, left as is; corrected places keep their correction and their "modifié" label.
- **Q7, accept after a mistaken group reject: "Whole group back (Rec.)".** Preview: reject the group by mistake → all 3 rejected; accept row 1 → all 3 accepted again; Saint-Zorbal, rejected on its own earlier, stays rejected.
- **Ctrl+Shift+R (PO P1): "Stay rejected (Rec.)".** Preview: Ctrl+Shift+R → rows 2 and 3 rejected; correcting the person's name → row 1 corrected, rows 2 and 3 stay rejected (Saint-Zorbal as is). Ctrl+Shift+A is unchanged.

**As a** desktop-app user reviewing a batch of documents,
**I want** "Précédent", "Suivant" and "Valider et continuer" to keep each document's own decisions and positions, and an action on a name I added by hand to act on that name,
**so that** no name is left in clear and no document is written with another document's positions.

**Priority:** HIGH — three leak paths in desktop batch review; PRE-001 also damages the output text. They must land before any release. None is a 10.3c regression: QA found the code involved unchanged since v2.2.0, and PRE-001 contradicts Story 6.7.3 (v2.0.0).
**Change type:** desktop batch review only. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes. If any file the accuracy suite loads is touched, one regular accuracy run on the branch shows the 16 lines identical to `38212303870`.
**Ordering:** outside the detector chain. 10.10's dev work starts after Story 10.9 merges, because 10.10 changes 10.9's `_action_rows` (the rows an edit or a type change reaches) and its docstring: under Lionel's Q3, accept and reject on a hand-added row stay on that row (`_group_ids`, `validation_state.py:164-176`), while an edit or a type change reaches every row of the same name and type, found or added by hand. 10.10's story and PO work can run in parallel with 10.9. Never in the same PR as 10.9.

### Context

At `main` `e16d15a`. QA's probes (`rgpd-analysis/r108/qa/probes/`; invented names, local, not CI results) were re-run by the PM against this commit on 2026-10-14, with the same results.

- **PRE-001 (HIGH), "Précédent" then "Valider et continuer":** on a previous document the button is shown and enabled (`gui/screens/validation.py:319`), and in batch mode it emits that document's validated list (`_on_finalize`, `:777-786`). `BatchScreen._on_validation_complete` stores the list under the index of the document the worker is waiting on (`gui/screens/batch.py:928-929`) and wakes the worker with it (`:950`). That document is then written with the earlier document's positions. Story 6.7.3 (v2.0.0) says re-submitting a previous document "replaces the stored result but does not re-trigger the worker" (`docs/stories/6.7.3.batch-validation-workflow.story.md:43`).
  - **Real-worker probe** (real `BatchWorker` thread, only detection replaced): doc 1 "Quentrel Zorbalia rejoint le projet. Le contrat est signé avec Quentrel Zorbalia." came out as "<org pseudonym>orbalia rej<org pseudonym>ojet. Le contrat est signé avec Quentrel Zorbalia.": the second occurrence in clear, the first partly, the text damaged. The result stored for doc 1 was doc 0's list. The batch summary still lists it as processed ("Traité"), with the earlier document's entity count (PO probe, 2026-10-14).
- **Same class as PRE-001, Ctrl+O during a waiting batch (found by the PO, 2026-10-14):** opening a single document with Ctrl+O (`gui/main_window.py:135-136`, `:381-389`; a file from the recent-files menu takes the same route, `:369-375`) while a batch waits for validation goes through `_notify_file_selected` (`:399-414`) to the home screen (`gui/screens/home.py:231-278`, no batch check) and on to `start_validation` (`gui/screens/processing.py:369`). The validation screen keeps `_batch_mode=True` and the waiting `_doc_index`, because only `set_context` writes them (`validation.py:56`, `:343-345`), so "Valider et continuer" sends the single document's list as the waiting batch document's result. A third route ends in the same `start_validation` call (found by the SM): the home screen's drop zone (`home.py:58`) and its recent list (`:202`) call the same `_on_file_selected`, and the home screen is reached while a batch waits through the "Retour" button of the settings screen (`gui/screens/settings.py:54`) or the database screen (`gui/screens/database.py:103`).
  - **PO probe, unfixed code:** doc 1 was written as "Drake Peixotoel Zorbalia rejoint le projet. …", `_validation_results[1] = [(PERSON, 0, 6)]`, and the summary showed "Traité".
  - AC1's words already forbid it ("A list built on one document is never stored for, or sent as the result of, another document"). It is inside 10.10's scope; the story covers it in its AC11.
  - **Related defect (found by the SM):** after a batch run ends, a single document validated in the same session stays in batch mode (the same flag): its button sends the list to the batch screen, which has no worker any more, so nothing is written (no output, so nothing in clear). The story's AC11 covers it too.
- **PRE-002 (MEDIUM), "Précédent" then "Suivant":** the navigation reloads the cached detection context (`validation.py:695-733`; the cache is filled at `batch.py:900-914`), so the current document is rebuilt and every accept and reject already made on it is lost (rows back to "to review", except names already in the mapping database). "Valider et continuer" sends only confirmed, modified or added rows, never pending ones (`validation_state.py:335-358`), and gives no warning about rows still to review. Probe: both confirmed rows of doc 1 were pending again after "Suivant"; validating wrote doc 1 unchanged, both names in clear.
- **PRE-003 (MEDIUM), an action on a hand-added row:** a row added by hand has no stored candidate key, so `_group_ids` (`validation_state.py:164-176`) uses its current text and type and returns the detected group of that (text, type), which does not contain the added row. When that group has more than one row, "Rejeter" on the added row (right-click menu, `gui/widgets/entity_editor.py:384-386`; Delete in navigation mode, `:474-475`, `:553-558`) rejects the detected rows instead; the added row stays "added" and is sent, and the detected occurrences stay in clear. "Accepter" confirms the detected rows instead (harmless).
  - **Batch probe:** ORG "Zorbaville" detected at 0 and 21 and accepted, ORG "Zorbaville" added at 33, "Rejeter" on the added row: rows 0 and 21 REJECTED, [ORG 33] sent, two "Zorbaville" left in clear.
  - 10.8 narrowed it: single-document validation has one row per (text, type) group, so it no longer happens there. In batch review (one row per occurrence) it happens for any name detected at least twice in the document. Present in v2.2.0.

### Acceptance Criteria

1. **AC1 — PRE-001:** "Valider et continuer" always applies to the document it belongs to, or is blocked with a clear message. A list built on one document is never stored for, or sent as the result of, another document, and a re-submit of a previous document never wakes the worker.
2. **AC2 — PRE-002:** navigating with "Précédent" and "Suivant", in any order and any number of times, never loses a decision already made on a document (accept, reject, edit, type change, added row).
3. **AC3 — PRE-003 (Lionel, 2026-10-14: Q3, its correction, group accept, Q5, Q6, Q7 and Ctrl+Shift+R):** accept and reject on a row added by hand act on that row only. The rule: for accept and reject, a row with no stored candidate key (a row added by hand) is its own group of one, so accept and reject on it reach no other row; detected rows keep 10.8's grouping by their stored (text, type) key, which never includes a hand-added row. A text correction or a type change on any row, found or added by hand, reaches every row of the same name and type, found or added by hand, except a row the user rejected on its own: they all take the corrected text or type and get one pseudonym. A group accept skips rows the user rejected on its own; a group reject skips rows the user accepted or corrected on its own; "Accepter les déjà connues" (`accept_all_known`) takes only rows still to review; Ctrl+Shift+R counts as the user's own reject. The story's AC14 carries the detail.
4. **AC4 — Tests first, invented names only:** the tests are committed before the fix. PRE-001 and PRE-002 are tested through the real batch path (real `BatchScreen`, `ValidationScreen` and `BatchWorker` thread, only detection replaced), as in QA's probe. Each expected failure is an `assert` on the captured outcome, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code, so a harness error shows as a plain FAILED (the 10.5 pattern). The fix removes the markers. Existing GUI and CLI validation tests stay green.
5. **AC5 — CHANGELOG:** CHANGELOG `[Unreleased]` gets a "Fixed" entry for the three defects in desktop batch review.
6. **AC6 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** desktop batch review only, never in the same PR as a detector change or as Story 10.9.
   - **G2:** QA re-runs the AC4 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes, so no QA report or docs update. CHANGELOG as AC5.

### Integration Points

- `gdpr_pseudonymizer/gui/screens/batch.py` — `_on_validation_complete` (`:919`, store `:928-929`, worker wake-up `:950`), the context cache (`:900-914`)
- `gdpr_pseudonymizer/gui/screens/validation.py` — `start_validation` (`:283-323`), the button on a previous document (`:319`), `_on_prev_doc` / `_on_next_doc` (`:695-733`), `_on_finalize` (`:777-786`)
- `gdpr_pseudonymizer/gui/main_window.py` — the Ctrl+O and recent-files routing (`:135-136`, `:381-389`, `:369-375`, `:399-414`), read only, no change expected
- `gdpr_pseudonymizer/gui/models/validation_state.py` — `_group_ids` (`:164-176`), `_validated_rows` (`:327-358`)
- `gdpr_pseudonymizer/gui/widgets/entity_editor.py` — the reject actions (`:384-386`, `:474-475`, `:553-558`), read only unless the fix needs them
- `tests/unit/gui/` or `tests/integration/gui/` — AC4 tests; `CHANGELOG.md` — AC5
- `tests/unit/gui/conftest.py`, `tests/integration/gui/conftest.py` — a test-only autouse fixture that points `gui.config._config_path` at `tmp_path`, because local GUI test runs have been overwriting the user's real settings file (`.gdpr-pseudo.yaml` in the home folder)

### Follow-ups Found by the 10.10 SM and PO (not ACs, 2026-10-14)

None is in 10.10's scope. Backlog unless Lionel routes one elsewhere. (a)–(j) are pre-existing; (k)–(m) were added on 2026-10-14 from the 10.9 QA gate, a local test run and the 10.10 PO review.

- **(a)** The batch-validation texts (for example "Valider et continuer") have no English translation (`gui/i18n/en.ts`).
- **(b)** At `gui/screens/batch.py:699-708`, disconnecting a signal that is not connected makes PySide6 warn instead of raising, so the `except RuntimeError` guards never fire.
- **(c)** The worker's validation wait has no predicate loop, so a spurious wake-up ends the batch as if it were cancelled; `validation_required` is emitted before the mutex is taken (`gui/workers/batch_worker.py:356-367`).
- **(d)** Batch "Valider et continuer" asks for no confirmation and gives no warning about rows still to review.
- **(e)** The live document table shows "Traité" for a document whose finalization failed (`gui/screens/batch.py:748-751`); the summary says "Erreur".
- **(f)** Ctrl+O during a batch leaves the waiting worker blocked with no way back. After 10.10 nothing leaks, but the batch cannot be resumed.
- **(g)** "◀ Précédent" past a document that failed to read does nothing.
- **(h)** The "validation per document" checkbox is never remembered: `batch_validate_per_document` is not in `_DEFAULT_CONFIG` (`gui/config.py:14-27`), and saving keeps only the keys listed there.
- **(i)** CHANGELOG `[Unreleased]` needs harmonising before the release: once 10.7 ships, 10.5's "The schema version stays 1.0.0" and the 10.3c and 10.4 continuity bullets ("The mapping schema is unchanged … without the entity type") are stale.
- **(j)** `docs/architecture/9-database-schema.md` needs the (text, type) key and schema version 1.1.0 after 10.7.
- **(k) TEST-FLAKE-001:** `tests/unit/test_final_exam_tooling.py::test_serve_refuses_foreign_host_and_origin` fails with a Windows-local `ConnectionAbortedError` under load; it is green on CI.
- **(l) 10.9 DOC-002** (`docs/qa/gates/10.9-gui-edit-all-occurrences.yml`, low): three texts still say "detected span" where 10.9's step 12 keeps the previous edit's span: the 10.9 story's Consumer Trace #6 and #7, and `CHANGELOG.md:152` ("keeps its detected span").
- **(m)** No visible cue when a group action skips places the user decided on their own (10.10 AC3). The PO's toast wordings are a backlog note only, not approved text.

### Estimated Effort: 0.5-1 week (the real-worker tests are the long pole)

---

## Story 10.11: Custom Pseudonym Stored and Used

**Added by Lionel, 2026-10-14:** "Make it work (new story)". This was not the recommendation: the orchestrator had recommended a PM backlog item, because the feature leaks nothing. Lionel's meaning, as recorded in the orchestrator's decision log (2026-10-14 morning decisions): "Changer le pseudonyme" is stored in the mapping database and used in every output, so later documents keep it; a data-layer change, after 10.7. Lionel treats a documented feature that silently does nothing as a product-integrity defect, not a minor issue.

**As a** user who sets a pseudonym of my own for a name during validation ("Changer le pseudonyme" in the desktop app, [C] in the CLI),
**I want** the written file to use it, and later documents and runs to reuse it for that name,
**so that** the feature the documentation advertises does what it says.

**Priority:** HIGH (proposed by the PM), before release. The feature is advertised and silently does nothing: every confirmed name is still replaced, so nothing is left in clear, but with a generated pseudonym instead of the user's.
**Change type:** desktop review, the CLI validation path and the mapping data layer. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes. If any file the accuracy suite loads is touched, one regular accuracy run on the branch shows the 16 lines identical to `38212303870`.
**Ordering:** outside the detector chain. After 10.7 (merged, `acb7bdd`), because the pseudonym is stored in the (text, type) row, and after 10.10 (merged, `eee4d41`), because it changes `gui/models/validation_state.py`. Lionel answers the open questions below before dev starts. Never in the same PR as a detector change.

### Context

At `main` `eee4d41`:

- **Desktop app:** the editor's right-click menu "Changer le pseudonyme" (`gui/widgets/entity_editor.py:396-398`) opens a dialog (`gui/screens/validation.py:564-565`, `_show_change_pseudonym_dialog` `:702-714`) that calls `GUIValidationState.change_pseudonym` (`gui/models/validation_state.py:438-441`). Its `_ChangePseudonymCommand` (`:936-973`) sets `EntityReview.custom_pseudonym` (`validation/models.py:166`), marks the row MODIFIED and, since 10.10, records it as the row's own decision (comment `:951-952`, `_set_own` `:963`), so group actions do not undo it. The list shows it (`get_pseudonym`, `:786-793`).
- **It never reaches the written file:** finalization sends plain detected entities, without the custom pseudonym (`_validated_rows` `:671-687`, `get_validated_entities` `:689-691`, `expand_validated_entities` `:693`; `validation.py:942` → `FinalizationWorker` → `finalize_document`, `core/document_processor.py:902`). `_resolve_pseudonyms` (`:562`) takes each name's pseudonym from the mapping database by (key, type) (`:595`) or generates one, one pseudonym per (key, type) per run (`entity_cache`, `:576`); it never sees the custom pseudonym.
- **CLI, the same defect:** [C] in validation (`validation/ui.py:86-87`) asks for a pseudonym and sets it on every occurrence of the group (`validation/workflow.py:266-271`; `ValidationSession.change_pseudonym`, `validation/models.py:328-345`, which records a CHANGE_PSEUDONYM decision and marks the row CONFIRMED). `get_validated_entities` (`:348`) returns plain detected entities, so the CLI drops it too (`core/document_processor.py:336` → `_resolve_pseudonyms`). `ChangePseudonymAction.execute` (`validation/actions.py:131-134`) is a no-op ("Action handled by pseudonym assignment engine"), exported but unused.
- **No version ever wrote it:** in every tag from `v1.0.0` to `v2.2.0`, and at `eee4d41`, nothing outside the two review models reads `custom_pseudonym`. The CLI field came with Story 1.7 (`d631a7d`), the desktop action with Story 6.4 (`2e541e0`). QA recorded it on 10.8 as PRE-004 (low, not a leak; `docs/qa/gates/10.8-gui-type-aware-candidate-keys.yml`).
- **Advertised:** `README.md:384` and `:701`; `README.fr.md:383` and `:700`; `docs/gui-guide.md:123` and `docs/gui-guide.fr.md:123`; `docs/methodology.md:136` and `docs/methodology.fr.md:136`; `docs/tutorial.md:344`, `:357`, `:394` and `docs/tutorial.fr.md:344`, `:357`, `:394`.
- **Data layer since 10.7:** one row per (text, type) (`data/models.py:30-33`), schema 1.1.0 (`data/database.py:36`). A row holds `pseudonym_full` and, for PERSON, `pseudonym_first` and `pseudonym_last` (`data/models.py:47-49`), which a later first or last name used alone reuses. The repository has no method that changes a stored pseudonym (`data/repositories/mapping_repository.py`: find, save and delete only).

### Acceptance Criteria

1. **AC1 — Used in the written file:** a custom pseudonym set in the desktop app or the CLI replaces that name, for that type, at every occurrence written (the file holds one pseudonym per name and type). A row rejected on its own is not written (10.10). Which rows of batch review show it is open question 3. The tests assert the written file, not the list.
2. **AC2 — Stored and reused:** the custom pseudonym is stored in the mapping row for that (text, type), so later documents and later runs, in the desktop app and the CLI, reuse it. A name with no stored row gets a new row holding it. What happens when the name already has a stored pseudonym is open question 1; for a person, the first-name and last-name parts follow open question 4. Nothing is built for either case before Lionel answers.
3. **AC3 — Collisions:** a custom pseudonym equal to another name's stored pseudonym, or to a real name in the document, is handled as Lionel decides (open question 2). Whatever the answer, two different names never end up with the same pseudonym without the user being told.
4. **AC4 — The CLI is in scope:** the CLI's [C] (`validation/ui.py:86-87`) is advertised (`README.md:384`) and fails the same way, and Lionel asked for "every output". It gets AC1–AC3 too. The CLI keeps its flags and keys.
5. **AC5 — Undo, redo and navigation:** in the desktop app, undo and redo of "Changer le pseudonyme" restore the previous pseudonym and the row's own-decision flag (10.10). In batch review, "Précédent" and "Suivant" keep it (10.10 AC2). Nothing is stored in the mapping database before the document is finalized, so an undone change is never stored.
6. **AC6 — Tests first, invented names only:** the tests are committed before the fix, for the desktop app and the CLI. Each expected failure is an `assert` on the written output (and on the stored row), made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Existing tests stay green.
7. **AC7 — CHANGELOG:** CHANGELOG `[Unreleased]` gets a "Fixed" entry: a custom pseudonym is now used in the written file and kept for later documents, with an upgrade note if a stored pseudonym can now change (open question 1).
8. **AC8 — Docs:** the docs listed in Context keep advertising the feature, now accurately. A doc line changes only where it says something the fix does not do. G7 applies: no headline number changes.
9. **AC9 — User copy:** any new visible text (a dialog line, a warning, a CLI message) is user copy that Lionel approves, word for word, before the story is done.
10. **AC10 — Gates:**
    - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
    - **G4:** never in the same PR as a detector change.
    - **G2:** QA re-runs the AC6 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
    - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
    - **G7:** no headline number changes. CHANGELOG as AC7, docs as AC8.

### Open Questions for Lionel (asked one at a time; nothing is built for them before the answer)

1. **A name that already has a stored pseudonym.** When you set your own pseudonym for a name that already has one in your mapping database (from an earlier document), what should happen? Recommendation: refuse, with a message that says why and how to do it anyway (remove the name with `delete-mapping`, then set your pseudonym). Replacing it would give the same person one pseudonym in the documents already written and another in new ones.
2. **A pseudonym that clashes.** Your pseudonym could be the same as the pseudonym already given to another name, or the same as a real name in the document. Recommendation: refuse in both cases, with a message that names the clash. Two names sharing one pseudonym can no longer be told apart in the output, and a pseudonym equal to a real name makes the file read as if that person were mentioned.
3. **Batch review: the other places of the same name.** In batch review each place of a name is its own row, but the written file can hold only one pseudonym per name and type. If you set your own pseudonym on one place, should the other places of that name and type show it too? Recommendation: yes, every place of that name and type, except a place you rejected on its own, as corrections already do (10.9, 10.10).
4. **A person's first and last name.** For a person, the database also keeps a first-name part and a last-name part, so that a later mention of only the first or only the last name gets the matching part. If you set "Quentrix Zorbal" for "Marie Dubois", should a later "Dubois" alone become "Zorbal"? Recommendation: yes. Split your pseudonym at its last space: the part before for the first name, the part after for the last name. If your pseudonym is one word, keep it for the full name only; a later "Dubois" alone then gets its own generated pseudonym.

### Integration Points

- `gdpr_pseudonymizer/gui/models/validation_state.py` — `change_pseudonym` (`:438-441`), `_ChangePseudonymCommand` (`:936-973`), `_validated_rows` (`:671-687`), `expand_validated_entities` (`:693`)
- `gdpr_pseudonymizer/gui/screens/validation.py` — the dialog (`:702-714`), finalization (`:942`)
- `gdpr_pseudonymizer/validation/models.py` — `EntityReview.custom_pseudonym` (`:166`), `change_pseudonym` (`:328-345`), `get_validated_entities` (`:348`)
- `gdpr_pseudonymizer/validation/workflow.py` (`:266-271`) and `validation/ui.py` (`:86-87`) — the CLI's [C]
- `gdpr_pseudonymizer/validation/actions.py` — `ChangePseudonymAction` (`:118-134`, a no-op), kept or removed by the story with no behaviour change
- `gdpr_pseudonymizer/core/document_processor.py` — `_run_validation` (`:286`), `_resolve_pseudonyms` (`:562`, cache `:576`, lookup `:595`), `finalize_document` (`:902`)
- `gdpr_pseudonymizer/data/repositories/mapping_repository.py` — a method that changes a stored pseudonym, only if open question 1 allows replacing; `data/models.py` read only (no schema change expected)
- `tests/unit/` and `tests/integration/` — AC6 tests; `CHANGELOG.md` — AC7; the docs in Context — AC8

### Estimated Effort: 0.5-1 week (the upper end if Lionel allows replacing a stored pseudonym)

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
Story 10.6 (Final-exam set + ranges)      --- parallel ---  PR A early; frozen + model-annotated before 10.4 merges; adjudicated after 10.4, then committed and scored once
Story 10.7 (Type-aware mapping lookup)    --- 0.5-1 week, any slot --- no accuracy baseline (data layer)
Story 10.8 (Desktop app type-aware keys)  --- 0.5 week, before 10.7 --- no accuracy baseline (desktop app)
Story 10.9 (Edit at every occurrence)     --- 0.5 week, after 10.8 --- no accuracy baseline (desktop app)
Story 10.10 (Batch review fixes)          --- 0.5-1 week, dev after 10.9 merges --- no accuracy baseline (desktop app)
Story 10.11 (Custom pseudonym used)       --- 0.5-1 week, after 10.7 and 10.10 --- no accuracy baseline (desktop app + data layer)
```

**Strictly sequential:** 10.1 → 10.2 → 10.3a → 10.3b → 10.3c → 10.4. Each story's baseline is the previous story's merged close-out G1 run. No parallel detector stories: overlapping changes would make G3/G4 attribution impossible.

**Story 10.5** is outside this chain: it changes no detection, so it has no accuracy baseline and can merge at any point without affecting G3/G4 attribution.

**Story 10.6** is outside the detector chain too. PR A (ranges) changes no metric line and should land before 10.3c, so 10.3c and 10.4 report ranges. PR B's documents are frozen, and both model annotations are done, before 10.4 merges. Nothing in 10.3c or 10.4 may draw on them. Lionel adjudicates after 10.4 merges, and close-out waits for his adjudication. The documents and adjudicated annotations are then committed as plain files (fingerprints checked against the freeze record) and scored exactly once, and that run is part of the Epic 10 close-out evidence.

**Story 10.7** is outside the chain, like 10.5: it changes no detection (data layer only), so it has no accuracy baseline and can merge at any point without affecting G3/G4 attribution. Its effect shows most once 10.3c has merged.

**Story 10.8** is outside the chain too: it changes no detection (desktop app and core preview keys), so it has no accuracy baseline. It merges before 10.7 and does not wait for 10.7's continuity decision.

**Story 10.9** is outside the chain too: it changes no detection (desktop app review only), so it has no accuracy baseline. It goes after Story 10.8, because both change `gui/models/validation_state.py`, and never in the same PR as 10.8.

**Story 10.10** is outside the chain too: it changes no detection (desktop batch review only), so it has no accuracy baseline. Its dev work starts after 10.9 merges, because it changes 10.9's `_action_rows` and that function's docstring (Lionel's Q3, 2026-10-14); its story and PO work can run in parallel with 10.9. Never in the same PR as 10.9.

**Story 10.11** is outside the chain too: it changes no detection (desktop review, the CLI validation path and the mapping data layer), so it has no accuracy baseline. It comes after 10.7 and 10.10 (both merged); Lionel answers its open questions before dev starts.

**Epic close-out baseline:** the 10.4 merged G1 run (main + held-out) is the baseline Epic 9 starts from, together with the one final-exam run (10.6) and its ranges.

---

## Compatibility Requirements

- [ ] Existing APIs remain unchanged (`EntityDetector`, `DetectedEntity`, CLI flags, GUI). Exceptions allowed by 10.7 (inside its G4 scope), none of them a flag or screen change: a new error class for a failed conversion, a subclass of `DatabaseError` (an addition); `batch` opens the database once before its worker pool; `delete-mapping` keeps its flags but removes every row of the name; the internal repository interface (`MappingRepository`) gets lookups and deletion by (text, type) and keeps no text-only lookup
- [ ] Database schema changes: none (mapping table schema untouched; mapping keys may change, because span changes in 10.2-10.4 change the normalized entity text — see the pseudonym-continuity risk). Exception: Story 10.7 changes the `entities` unique key from `full_name` alone to (text, type), rule (a), "Convert once" (Lionel, 2026-10-13, 10.7 STOP C); see the next line
- [ ] Database schema after 10.7 (rule (a), "Convert once" (Lionel, 2026-10-13, 10.7 STOP C); details in the 10.7 story, Dev Notes "Decided Continuity Rule (a)"):
  - **When:** on the first open by the new version, after the passphrase check, a pre-10.7 file is converted to the (text, type) key. It is recognised by both its unique index on `full_name` alone and its `schema_version`; if only one holds, the open stops and changes nothing.
  - **How:** one explicit `BEGIN IMMEDIATE` transaction on an autocommit connection, all or nothing. Every row, pseudonym and id is kept, values copied as stored.
  - **Which opens:** every open converts, including the read-only commands, the source of `import-mappings`, the desktop app and backup copies the user opens. A converted file is not converted again.
  - **Several processes:** concurrent opens are serialised by the write lock (with a busy timeout); a process that waited sees the converted file and changes nothing.
  - **Failure:** if the conversion fails, the open stops with the new error class and the file is untouched.
  - **Going back:** opening a converted file with 2.2 or older is unsafe. The CHANGELOG tells users to copy their database file before upgrading if they may need to go back. No automatic copy is kept (a kept copy would still hold names erased later).
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
| 10.3c offers more candidates of a second type (e.g. PERSON on hyphenated place names) | MEDIUM | LOW | Both candidates reach mandatory validation, flagged ambiguous (the ambiguity marker shows in the CLI; the GUI lists both entries without a marker); FP reported per type (10.3c AC3) |
| Unsupported accuracy claims in docs | LOW | HIGH | G1/G2/G7; the arithmetic estimate is never published |
| Pseudonym continuity across versions: span changes in 10.2, 10.3a, 10.3b, 10.3c and 10.4 re-key mapping entries (normalized text), so a user keeping a v2.2 mapping DB can get a new pseudonym for the same entity. Mapping lookups are type-blind: for a key already in the database, both 10.3c candidates are auto-accepted with the stored pseudonym, the same as today (Story 10.7 makes the lookup type-aware) | MEDIUM | MEDIUM | CHANGELOG [Unreleased] entry with an upgrade note in each of 10.2, 10.3a, 10.3b, 10.3c and 10.4 explaining the effect; schema unchanged |
| Pseudonym continuity for existing databases under 10.7: databases created before 10.7 hold one row per text, so a type-aware lookup could give an existing entity a new pseudonym in a document processed before | MEDIUM | MEDIUM | 10.7 AC3: rule (a), "Convert once" (Lionel, 2026-10-13, 10.7 STOP C): a pre-10.7 file is converted once, all or nothing, on its first open, keeping every row and pseudonym (Compatibility Requirements); no existing row is deleted or given a new pseudonym; tested on a database written by the pre-10.7 code (AC5); CHANGELOG upgrade note |
| Desktop app merges a same-span pair of two types (10.3c regression): text-only keys let the second type overwrite the first and one reject act on both, so an occurrence of a confirmed name can stay in clear | MEDIUM | HIGH | Story 10.8 (HIGH, before any release; on `main` only, unreleased): preview map, variant map and same-text group keyed on type; tests first with invented names; QA before merge. The CLI is not affected (`validation/models.py:416`) |
| Desktop app edit leaves other occurrences in clear: editing a name in the review list changes one occurrence, and the others are not pseudonymized (since v2.0.0; not a 10.3c regression) | MEDIUM | HIGH | Story 10.9 (HIGH, before the next release): an edit applies to every occurrence of that name and type, as in the CLI (`validation/workflow.py:242-259`); tests first with invented names; QA before merge |
| Desktop batch review leaks (pre-existing, found by QA on 10.8): "Précédent" then "Valider et continuer" writes the waiting document with an earlier document's positions (names in clear, text damaged); "Précédent" then "Suivant" drops decisions already made; a reject on a hand-added row rejects the detected rows | MEDIUM | HIGH | Story 10.10 (HIGH, before any release): each document's result and decisions stay its own; a hand-added row acts on itself only; tests first through the real batch worker, with invented names; QA before merge |
| Custom pseudonym advertised but never used (every version since v1.0.0; QA PRE-004 on 10.8): the user believes the chosen pseudonym is in the file, but a generated one is written. A careless fix could give two names one pseudonym | HIGH (every use) | MEDIUM (no leak; wrong output, lost trust) | Story 10.11 (HIGH, before release): the pseudonym is used in the file and stored for that (text, type); tests assert the written output; clashes and an already-stored pseudonym follow Lionel's answers (10.11 open questions 1 and 2) |
| Final-exam set seen or used before close-out (leak) | LOW | HIGH | Kept in a workspace outside the repo until 10.4 merges, so no rule writer (agent, or Lionel at STOP R) can draw on it during detector work; Lionel sees no content before 10.4 merges; sha256 fingerprints recorded at freeze and checked at commit and before the scored run; adjudication view from a deterministic script that agents never read; plain files committed only after adjudication, outside every regular accuracy path; plain-text leakage guard on every CI run from that commit (its first run checks every file 10.3c and 10.4 added); no exam text in public CI logs; isolation rule restated in every later story (10.6 AC5-AC8). No encryption: it guarded nothing beyond this (Q5 reversed, Lionel, 2026-10-09) |
| Final-exam score well below main or held-out | MEDIUM | MEDIUM | It is information, not a failure: no tuning in response inside Epic 10. Lionel picks the public number (10.6 AC9). The gap goes to Epic 9 as evidence |
| Double annotation and adjudication delay close-out | MEDIUM | MEDIUM | 10.6 starts now, in parallel; both annotations are model runs, done before 10.4 merges; Lionel adjudicates only the disagreements plus a spot-check of about 3 agreed documents (10.6 AC5); close-out waits for that adjudication, the commit and one scored run, not for any further detector story |
| Ranges misread (held-out has 6 documents, so its ranges are wide) | MEDIUM | LOW | Every range states unit=document and the document count; story-to-story claims use the paired main-corpus delta (10.6 AC3) |
| Final-exam author shares conventions with the rule writers | LOW | MEDIUM | Different model family: GPT via `codex exec` writes, GPT and Kimi (or Gemini) annotate, no Claude agent takes part; the brief contains no GUIDELINES text or corpus text and is approved by Lionel (10.6 AC4, AC5) |

- **Primary Risk:** a precision rule silently removes real persons, places or organisations.
- **Mitigation:** G3 on every story, negative-case tests for every rule, held-out check (G5).
- **Rollback Plan:** every rule is an isolated post-filter or pattern in its own PR; revert the PR. Reverting 10.3a after 10.3b has merged also means re-measuring 10.3b, since its baseline includes 10.3a. Annotation changes (10.1) are in their own PRs and revert independently.

---

## Definition of Done

- [ ] All 13 stories (10.1, 10.2, 10.3a, 10.3b, 10.3c, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11) completed with acceptance criteria met (10.5, 10.7, 10.8, 10.9, 10.10 and 10.11: G1/G3/G5 N/A, no detection change; 10.6: G1/G3/G5 N/A for building the set, its scored-once run is a G1 run)
- [ ] Every story closed with a cited G1 run and an independent G2 check
- [ ] No unapproved recall drop (G3) at any story
- [ ] Held-out set exists and is reported for 10.2, 10.3a, 10.3b, 10.3c and 10.4 (G5)
- [ ] `GUIDELINES.md` approved by Lionel and applied to the whole corpus
- [ ] black, ruff, mypy clean; full CI green (G6)
- [ ] QA report updated with the before/after at every story, and CHANGELOG `[Unreleased]` entries per story (G7)
- [ ] At Epic 10 close-out, README/README.fr, `docs/faq*.md`, `docs/index*.md` and `docs/tutorial*.md` updated once from the final G1 run (G7 interpretation, Lionel, 2026-10-02)
- [ ] Close-out baseline recorded as Epic 9's starting point: run ID plus the pasted `[Overall]`/`[PERSON]`/`[LOCATION]`/`[ORG]`/`[HELD-OUT …]` lines in the QA report (`accuracy-results` artifacts are kept 30 days, `retention-days: 30` in `.github/workflows/accuracy.yaml`, so the run ID alone is not enough)
- [ ] Accuracy output reports 95% bootstrap ranges (unit=document) per type for main and held-out, with the eight existing lines unchanged (10.6 PR A)
- [ ] Final-exam set (10.6): 30 documents frozen and annotated independently by two models before 10.4 merged, with sha256 recorded; inter-annotator agreement and the spot-check finding reported; adjudicated by Lionel after 10.4 merged; then committed as plain files under `tests/test_corpus/final_exam/`, with the documents' sha256 matching the freeze record, and scored exactly once at close-out: run ID, ledger entry and pasted `[FINAL-EXAM …]` lines (overall, planted half, natural half) in the QA report
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
- Critical compatibility requirements: the product constraints and gates G1-G7 above, verbatim; the guidelines approval stop inside 10.1; strict 10.1 → 10.2 → 10.3a → 10.3b → 10.3c → 10.4 order for detector stories (10.5 and 10.7, data-layer stories, and 10.8, desktop app keys, sit outside that chain; 10.8 merges before 10.7; 10.7's continuity rule is rule (a), "Convert once" (Lionel, 2026-10-13, 10.7 STOP C)), each baseline the previous merged close-out G1 run (10.3 was split into 10.3a and 10.3b, and 10.3c was added at 10.3a STOP R, Lionel, 2026-10-06; see "Course Correction" and "Close-Out Record").
- Story 10.6 (final exam and ranges) runs outside the detector chain. Its documents are frozen and model-annotated before 10.4 merges, adjudicated by Lionel after 10.4 merges, then committed as plain files and scored once. From the start of 10.6 authoring, every story's Dev Notes forbid opening, listing or grepping the final-exam material (its workspace outside the repo and `tests/test_corpus/final_exam/`), next to the held-out isolation rule. Final-exam numbers exist only after close-out and are never used for a decision or for tuning inside Epic 10.
- Each story must include verification that existing functionality remains intact (full CI green, recall guard).

The epic should maintain system integrity while delivering higher detection precision and a trustworthy benchmark, without lowering recall."

---

**Document Status:** DRAFT
**Created:** 2026-10-02
**Author:** John (PM)
