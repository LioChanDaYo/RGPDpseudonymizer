# Epic 10: v2.3 — Detection Precision Quick Wins - Brownfield Enhancement

**Epic Goal:** Raise detection precision and make the accuracy benchmark trustworthy with local, deterministic changes to the hybrid detector and the ground-truth corpus, without lowering recall. The user-facing value is fewer false entities to reject during the (mandatory) validation step and a benchmark whose numbers can be believed.

**Target Release:** v2.3.0 candidate. **No release is part of this epic.** v2.3.0 ships only on Lionel's explicit go, through a separate release story.
**Duration:** Estimated 14.5-21.5 weeks (10.1 is annotation-labor-bound; 10.3 split into 10.3a and 10.3b, and 10.3c added, Lionel, 2026-10-06; 10.5 added, Lionel, 2026-10-07; 10.3b re-estimated after its STOP R, 2026-10-07; 10.7 added, Lionel, 2026-10-09; 10.8 and 10.9 added, Lionel, 2026-10-13; 10.10 and 10.11 added, Lionel, 2026-10-14; 10.11 re-estimated after its PO review, 2026-10-15; 10.12 and 10.13 added as release blockers, Lionel, 2026-10-16; 10.12 and 10.13 re-estimated after Lionel's answers, and 10.14, 10.15 and 10.16 added from the Codex release review, Lionel, 2026-10-16; 10.15 extended and 10.17 added for names added by hand, Lionel, 2026-10-16; 10.18 added for the CLI's skipped review, Lionel, 2026-10-16, and re-estimated after its PO review; 10.20 added for accents stored two ways, Lionel, 2026-10-20, option A); 10.6 runs in parallel (2-3 weeks elapsed) and close-out waits for its adjudication after 10.4 merges, then its commit and one scored run
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
- **How it integrates:** all detector changes are post-processing steps or patterns inside the existing `HybridDetector` pipeline and its YAML/JSON resources. No public API, CLI flag, GUI screen, mapping-table schema or file format changes. Exception: Story 10.7 (data layer) changes how mapping rows are keyed, and with rule (a), "Convert once" (Lionel, 2026-10-13, 10.7 STOP C) the mapping table's unique key becomes (text, type); see Compatibility Requirements. The release blockers 10.12 to 10.18 (2026-10-16) change no flag or screen; they add message windows and CLI lines and questions (10.13, 10.14, 10.18), a one-time cleaning of the erasure log on open (10.12) and fixes to review hand-offs and to names added by hand (10.14 to 10.17); see Compatibility Requirements.
- **Success criteria:**
  - Every story closes with a G1 run, G2 verification, no unapproved recall drop (G3) and held-out numbers (G5, from 10.2 on).
  - Overall precision on the repaired benchmark rises over the 10.1 close-out baseline by the end of 10.4, measured by G1 runs. No numeric precision target is set: the arithmetic estimate above is not a target.
  - The ground truth follows written, Lionel-approved guidelines, and the held-out set is scored separately.

---

## Epic 10 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 10.1: Benchmark Repair + Held-Out Set | HIGH | 1.5-2.5 weeks | F3, F4, F5, F2 (junk) | Done (PR #79, `d4b7105`) |
| 10.2: Same-Type Overlap Dedup + ORG Role Filter | HIGH | 1 week | F1, F2 | Done (PR #81, `f75ad9a`) |
| 10.3a: Boundaries & Run-On Spans (split from 10.3, Lionel, 2026-10-06) | MED | 0.5-1 week | 10.2 handoff, REL-004 | Done (PR #84, `ac354cc`) |
| 10.3b: Particles, Roles & LOCATION Noise (split from 10.3, Lionel, 2026-10-06) | MED | 0.5-1 week (re-estimated after STOP R, 2026-10-07) | F6, F7 | Done (PR #87, `bab6717`) |
| 10.3c: Type-Aware Exact Match in Merge (added at 10.3a STOP R, Lionel, 2026-10-06) | MED | 0.5 week | 10.3a STOP R | Done (PR #91, `5846419`) |
| 10.4: Greetings + Org-Plus-Country | MED | 0.5-1 week | F8, F9 | Done (PR #93, `2d4a029`) |
| 10.5: DB Init Safety (data-layer hardening, added by Lionel, 2026-10-07) | MED (raised from LOW by the PM, 2026-10-13) | 0.5 week | PR #83 finding | Done (PR #96, `67807c2`) |
| 10.6: Final-Exam Set and Confidence Ranges (added by Lionel, 2026-10-07) | HIGH | 2-3 weeks elapsed, in parallel | Overfitting check, close-out evidence | Done (PRs #89 `6abf858`, #92 `c63a7b6`, #94 `91b500d`, #95 `51d8429`) |
| 10.7: Type-Aware Mapping Lookup (data layer, added by Lionel at 10.3c STOP R, 2026-10-09) | MED | 0.5-1 week | 10.3c STOP R | Done (PR #99, `acb7bdd`) |
| 10.8: Desktop App Type-Aware Candidate Keys (10.3c regression, added by Lionel, 2026-10-13) | HIGH | 0.5 week | 10.7 SM finding | Done (PR #97, `e16d15a`) |
| 10.9: Desktop App Edit Applies to Every Occurrence (added by Lionel, 2026-10-13) | HIGH | 0.5 week | 10.8 SM finding | Done (PR #98, `49d4daa`) |
| 10.10: Desktop Batch Review Fixes (added by Lionel, 2026-10-14) | HIGH | 0.5-1 week | 10.8 QA pre-existing findings PRE-001 to PRE-003 | Done (PR #100, `eee4d41`) |
| 10.11: Custom Pseudonym Stored and Used (added by Lionel, 2026-10-14; not the recommendation) | HIGH (proposed) | 1.5 weeks (re-estimated after the PO review, 2026-10-15) | 10.8 QA PRE-004; Lionel 2026-10-14 | Done (PR #101, `b2042c7`) |
| 10.12: Erasure Log Without the Erased Name (release blocker B1, added by Lionel, 2026-10-16) | HIGH (release blocker) | 1 week | QA backlog B1; Codex release review #3 | Draft (Lionel's three answers recorded, 2026-10-16) |
| 10.13: Warning Before Writing Names Still to Review (release blocker B2, added by Lionel, 2026-10-16; single document and CLI added by his Q1) | HIGH (release blocker) | 0.5-1 week | QA backlog B2 | Draft (Lionel's answers and approved texts recorded, 2026-10-16) |
| 10.14: Desktop Batch and Finalization Hand-Offs (release blocker, added by Lionel, 2026-10-16) | HIGH (release blocker) | 1-1.5 weeks | Codex release review #1, #4 | Draft (Lionel's answers and approved texts recorded, 2026-10-16) |
| 10.15: CLI Corrections and Hand-Added Names (release blocker, added by Lionel, 2026-10-16; [A] at every place added the same day) | HIGH (release blocker) | 1-1.5 weeks | Codex release review #2; PO finding (names added by hand) | Draft |
| 10.16: Custom Pseudonym Fixes (release blocker, added by Lionel, 2026-10-16) | HIGH (release blocker) | 0.5-1 week | Codex release review #6, #7, #8 | Draft |
| 10.17: Desktop Hand-Added Names at Every Place (release blocker, added by Lionel, 2026-10-16) | HIGH (release blocker) | 0.5-1 week | PO finding (names added by hand) | Draft |
| 10.18: CLI Question When Nothing Is Left to Review (release blocker, added by Lionel, 2026-10-16) | HIGH (release blocker) | 0.5-1 week (re-estimated after the PO review) | 10.15 PO finding (no review since v1.0.0) | Draft (Lionel's four answers and approved texts recorded, 2026-10-16) |
| 10.19: Capitals in Hand-Added Names and Corrections (release blocker, added by Lionel, 2026-10-19) | HIGH (release blocker) | 0.5-1 week | PO measurement of QA's 10.15 finding (capitals) | Draft (Lionel's Q1-Q4 answers recorded, 2026-10-19) |
| 10.20: Accents Stored Two Ways: One Form Everywhere (release blocker, added by Lionel, 2026-10-20, option A) | HIGH (release blocker) | 1-1.5 weeks | PO sweep of decomposed accents (`r1019/po/nfd`); 10.16 Codex P0 and the 10.16 SM's follow-up (f) | Draft (Lionel's answer recorded, 2026-10-20) |

**Total Estimated Duration:** 14.5-21.5 weeks; 10.6 runs in parallel (2-3 weeks elapsed) and close-out waits for its adjudication after 10.4 merges, then its commit and one scored run

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
- **Stories after the detector close-out (none changes detection, so G1, G3 and G5 are N/A and the close-out baseline above stands):**

  | Story | PR, merge commit | Final gate (`docs/qa/gates/`) | Gate history | QA trace (`docs/qa/assessments/`) |
  |---|---|---|---|---|
  | 10.5 DB init safety | #96, `67807c2` | `10.5-db-init-safety.yml`: **PASS** | PASS (pre-merge, `091103a`) | `10.5-trace-20261015.md` |
  | 10.7 Type-aware mapping lookup | #99, `acb7bdd` | `10.7-type-aware-mapping-lookup.yml`: **PASS** | PASS (pre-merge, `702a655`) | `10.7-trace-20261015.md` |
  | 10.8 Desktop type-aware candidate keys | #97, `e16d15a` | `10.8-gui-type-aware-candidate-keys.yml`: **PASS** | PASS (pre-merge, `10ddd62`) | `10.8-trace-20261015.md` |
  | 10.9 Desktop edit at every occurrence | #98, `49d4daa` | `10.9-gui-edit-all-occurrences.yml`: **PASS** | CONCERNS at `a30557b` → PASS at `56b600e` after two amendments | `10.9-trace-20261015.md` |
  | 10.10 Desktop batch review fixes | #100, `eee4d41` | `10.10-batch-review-fixes.yml`: **PASS** | PASS (pre-merge, `fc95786`) | `10.10-trace-20261015.md` |
  | 10.11 Custom pseudonym stored and used | #101, `b2042c7` | `10.11-custom-pseudonym.yml`: **PASS** | CONCERNS at `5c02ba9` → FAIL at `e8cb76a` (MW-001) → PASS at `af5b23b` after the amendment | `10.11-trace-20261015.md` |

- **QA close-out (Quinn, 2026-10-15, at `main` `b2042c7`):** `docs/qa/assessments/epic-10-close-out-summary.md`. Every Epic 10 story has a final gate of PASS; 75 of the 76 ACs of the six stories above are covered (38 by tests, 37 by process evidence) and one is N/A (10.7 AC9, moved to 10.8). Main CI on `b2042c7` is green on attempt 1 (five workflows). Eleven leak paths found during the epic were each fixed after a failing test was committed first.
- **Epic NFR verdicts (QA, `docs/qa/assessments/epic-10-nfr-20261015.md`; quality score 70):** security/privacy **CONCERNS**, reliability **CONCERNS**, maintainability **CONCERNS**, performance **PASS** (NFR1 on `b2042c7`: 5,000 words in 0.87 s mean, target 30 s). QA: none of the CONCERNS is a regression, and none leaves a confirmed name in clear.
- **Follow-ups, consolidated:** every story's follow-ups and open gate items are consolidated in QA's backlog B1–B42 (`docs/qa/assessments/epic-10-close-out-summary.md`, "Consolidated Backlog"), also pointed to from `docs/qa/backlog.md`. Nothing there is scheduled by this close-out.
- **Release decisions for Lionel (QA):** B1 (the erasure audit entry keeps the erased name), B2 (batch "Valider et continuer" gives no warning about rows still to review) and B14 (`CHANGELOG.md` `[Unreleased]` harmonisation; the harmonised text is on `main` since #102, `fb7917c`), before a v2.3.0 release.
- **Re-opened for two release blockers (Lionel, 2026-10-16):** B1 "Fix before release (Rec.)" → Story 10.12; B2 "Fix before release (Rec.)" → Story 10.13. Both are written through Codex.
- **Codex release review (2026-10-16):** a `codex exec` review of `main` at `fb7917c` found ten problems, verdict NO-SHIP. QA reproduced each one on the real code with invented names (probes and logs kept outside the repository, in the orchestrator's analysis folder `r23codex/qa`). It found leaks that the QA close-out above had not: #1, #2 and #4. Lionel's answer: "Leaks + new 10.11 bugs (Rec.)".
  - **Fixed before release:** #1 (a second batch mixes with the first) and #4 (finalization shares live entities with the review) → Story 10.14; #2 (CLI [E] and [T] on spreadsheets leave the name in clear) → Story 10.15; #3 (the erased name in the erasure log) is Story 10.12; #8 (the real-name check ignores lowercase reviewed names), #6 (the generation guard ignores roles and spellings) and #7 (a custom pseudonym spreads by detected names) → Story 10.16.
  - **Later, backlog (Lionel: later):** #5, the final custom-pseudonym check is not atomic with saving, so two programs on one mapping database can store or write a pseudonym the other has (`core/document_processor.py:443`, `:801`; QA: its three probes with forced timing failed at `fb7917c`, and the one for generated pseudonyms also failed at v2.2.0, so that part is pre-existing; a natural stress run passed). The release notes can tell users to use one program at a time on a mapping database (user copy, Lionel approves it). #9, two programs opening a pre-10.7 file at the same moment: one can refuse a healthy file with the conversion error, because its first checks do not share one read (`data/database.py:454`, `:575`; QA: the probe with forced timing failed at `fb7917c`, a natural stress run passed; new with 10.7, unreleased). #10, the batch worker emits its request before it sets its wait state, so a submission or a cancel can be lost and the batch hangs (`gui/workers/batch_worker.py:365`; QA: a lost submission and a lost cancel, each failed at `fb7917c` and at v2.2.0, so pre-existing; the same as 10.10 follow-up (c)).
- **Names added by hand (a new finding of the PO, 2026-10-16):** a name added by hand is replaced at one place only (the desktop app, single document and batch: the selected place; CLI [A]: the first place found) and, in Excel and CSV files with CLI [A], at no place; its other places stay in clear while the name is stored. Measured at `fb7917c` and the same at v2.2.0. Lionel: "Fix before release (Rec.)": every place of that name and type, in the CLI and the desktop app. The CLI part is in Story 10.15, which already changes [A]; the desktop part is Story 10.17.
- **The CLI's skipped review (a finding of the 10.15 PO, 2026-10-16):** since v1.0.0 (Story 2.9 wired the review into `process`, Story 3.4 added the skip, both first in v1.0.0), `process` and `batch --workers 1` write a document without any review when the detector finds no name, or only names already stored, so a missed name cannot be added with [A]; the screen then says "All entities have existing mappings. Skipping validation.", even when nothing was found. Against Product Constraint 3; re-measured by the PM at `1f35dae`. Lionel: "Fix before 2.3.0 (Rec.)" → Story 10.18, whose four questions he answered the same day. The parallel batch, which never reviews, stays parked in Epic 9. Backlog from the 10.18 PO review (not release blockers): "n" at « Ready to process document with validated entities? » restarts the review and drops every decision (also 10.13 follow-up (a)); without a terminal, the CLI review waits forever on Windows and fails on Linux.
- **Docs debt for the close-out (10.12 PO):** `docs/architecture/6-components.md:135` says the data layer persists audit logs "with encryption"; the operations table is not encrypted (10.12 Context). The architecture docs are corrected with the 10.12 docs or at the close-out.
- **Still open in Epic 10:** the release blockers 10.16, 10.17 and 10.20 (the Codex release review, names added by hand, accents stored two ways), and 10.19, also a release blocker (capitals, added 2026-10-19; its epic section is on its branch, `story/10.19-capitals-forms`). 10.12, 10.13, 10.15, 10.18 and 10.14 are merged (PRs #104 to #108, 10.14 last, `43041e9`), after stories 10.1 to 10.11 (10.11, PR #101, `b2042c7`). The v2.3.0 release is not part of the epic; it waits for every release blocker and for Lionel's explicit go (separate release story).

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
- **(f)** Ctrl+O during a batch leaves the waiting worker blocked with no way back. After 10.10 nothing leaks, but the batch cannot be resumed. **Corrected 2026-10-16:** "nothing leaks" is wrong for a second batch started during a batch (File → "Ouvrir un dossier...", then "Démarrer"): its document can be written with the first batch's review, a name left in clear (Codex release review #1, reproduced by QA). Story 10.14 fixes it; Lionel's answer to its Q1 ("Refuse while running", 2026-10-16) also covers Ctrl+O during a batch, and its message leads back to the waiting batch.
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
**Ordering:** outside the detector chain. After 10.7 (merged, `acb7bdd`), because the pseudonym is stored in the (text, type) row, and after 10.10 (merged, `eee4d41`), because it changes `gui/models/validation_state.py`. Lionel answered its four questions on 2026-10-15 (Decisions Recorded). Never in the same PR as a detector change.

### Context

At `main` `eee4d41`:

- **Desktop app:** the editor's right-click menu "Changer le pseudonyme" (`gui/widgets/entity_editor.py:396-398`) opens a dialog (`gui/screens/validation.py:564-565`, `_show_change_pseudonym_dialog` `:702-714`) that calls `GUIValidationState.change_pseudonym` (`gui/models/validation_state.py:438-441`). Its `_ChangePseudonymCommand` (`:936-973`) sets `EntityReview.custom_pseudonym` (`validation/models.py:166`), marks the row MODIFIED and, since 10.10, records it as the row's own decision (comment `:951-952`, `_set_own` `:963`), so group actions do not undo it. The list shows it (`get_pseudonym`, `:786-793`).
- **It never reaches the written file:** finalization sends plain detected entities, without the custom pseudonym (`_validated_rows` `:671-687`, `get_validated_entities` `:689-691`, `expand_validated_entities` `:693`; `validation.py:942` → `FinalizationWorker` → `finalize_document`, `core/document_processor.py:902`). `_resolve_pseudonyms` (`:562`) takes each name's pseudonym from the mapping database by (key, type) (`:595`) or generates one, one pseudonym per (key, type) per run (`entity_cache`, `:576`); it never sees the custom pseudonym.
- **CLI, the same defect:** [C] in validation (`validation/ui.py:86-87`) asks for a pseudonym and sets it on every occurrence of the group (`validation/workflow.py:266-271`; `ValidationSession.change_pseudonym`, `validation/models.py:328-345`, which records a CHANGE_PSEUDONYM decision and marks the row CONFIRMED). `get_validated_entities` (`:348`) returns plain detected entities, so the CLI drops it too (`core/document_processor.py:336` → `_resolve_pseudonyms`). `ChangePseudonymAction.execute` (`validation/actions.py:131-134`) is a no-op ("Action handled by pseudonym assignment engine"), exported but unused.
- **Two older CLI review leaks, in every version (found by the 10.11 PO, routed in by Lionel's Q-F):** going back to a name with [P] or the left arrow (`validation/ui.py:94-95`, `validation/workflow.py:307-312`) and pressing Space confirms it again (`mark_confirmed`, `validation/models.py:233`). After [E], that turns the correction back into the detected text, so the corrected part stays in clear; after [R], the name stays in clear although it was accepted last, because `get_validated_entities` excludes any name with a REJECT anywhere in its history (`:362-364`). [C] after [E] drops the correction and the custom pseudonym the same way (`change_pseudonym` sets the row CONFIRMED, `:338`; PO R2).
- **No version ever wrote it:** in every tag from `v1.0.0` to `v2.2.0`, and at `eee4d41`, nothing outside the two review models reads `custom_pseudonym`. The CLI field came with Story 1.7 (`d631a7d`), the desktop action with Story 6.4 (`2e541e0`). QA recorded it on 10.8 as PRE-004 (low, not a leak; `docs/qa/gates/10.8-gui-type-aware-candidate-keys.yml`).
- **Advertised:** `README.md:384` and `:701`; `README.fr.md:383` and `:700`; `docs/gui-guide.md:123` and `docs/gui-guide.fr.md:123`; `docs/methodology.md:136` and `docs/methodology.fr.md:136`; `docs/tutorial.md:344`, `:357`, `:394` and `docs/tutorial.fr.md:344`, `:357`, `:394`.
- **Data layer since 10.7:** one row per (text, type) (`data/models.py:30-33`), schema 1.1.0 (`data/database.py:36`). A row holds `pseudonym_full` and, for PERSON, `pseudonym_first` and `pseudonym_last` (`data/models.py:47-49`), which a later first or last name used alone reuses. The repository has no method that changes a stored pseudonym (`data/repositories/mapping_repository.py`: find, save and delete only).

### Acceptance Criteria

1. **AC1 — Used in the written file, at every place (Q3):** a custom pseudonym set in the desktop app or the CLI replaces that name, for that type, at every occurrence written (the file holds one pseudonym per name and type). In batch review, setting it on one place applies it to every place of that name and type, found or added by hand, except a place the user rejected on its own, as corrections do (10.9, 10.10); the list shows it on each of those rows, and one undo reverts it everywhere. A custom pseudonym that reached several places follows the group like a correction (Q-B): rejecting the name from another found place rejects those places too, and a place the user rejected on its own before is never reached. The tests assert the written file, not the list.
2. **AC2 — Stored and reused (Q1, Q4):** the custom pseudonym is stored in a new mapping row for that (text, type), so later documents and later runs, in the desktop app and the CLI, reuse it. A name that already has a stored pseudonym keeps it: the custom pseudonym is refused, with a message that says why and how to proceed (remove the name with `delete-mapping` first). For a person, the custom pseudonym is split into a first-name part and a last-name part, in this order (Q4, Q-D, Q-G): when the real last name already has a stored part and the pseudonym ends with it as whole words, that is the last part; else, when the real first name already has a stored part and the pseudonym starts with it, that is the first part; else, when the pseudonym ends with one of the library's two-word last names ("Da Silva", "Le Gall", "Da Costa", "Espírito Santo", in the neutral theme), that name stays whole as the last part; otherwise it is split at its last space. A later first or last name used alone gets the matching part. A one-word custom pseudonym is stored for the full name only, so a later first or last name alone gets its own generated pseudonym. A real first name that already has a stored first-name part keeps it (Q-D, not the recommendation): if "Quentrel" alone is already written "Aubin", a custom pseudonym whose first part is not "Aubin" is refused, with a message saying it must start with "Aubin" (for example "Aubin Vellion"). The same holds for a real last name that already has a stored last-name part, which must then be the custom pseudonym's last part (10.11 story, AC17 (b)).
3. **AC3 — Clashes are refused, whatever the split (Q2, Q-C, Q-C2, Q-I; PO B1):** a custom pseudonym is refused, with a message that names the clash, in these cases. For a person, the full pseudonym, every beginning and every ending of it (one or more whole words) are compared with other people's stored pseudonyms and parts, and with every beginning and ending of other people's custom pseudonyms, stored or in this review (both directions, PO B1); an organisation's or a place's custom pseudonym is compared whole. Every run of consecutive whole words of a person's pseudonym (an organisation's or a place's: the whole of it) is compared with the document's words that start with a capital letter, found by the detector or not, a sentence-initial word included (Q-C), and with the full names already stored (Q-C2: a stored first or last name alone does not count). Words in small letters do not count, and a linking word (da, das, de, del, della, des, di, do, dos, du, la, le, les, van, von, der) followed by another word of the pseudonym is not checked on its own, while the words around it and a linking word at the end still are (Q-I). Capitals and accents are ignored. Later generated pseudonyms: a generated full pseudonym never equals a stored one (the library's used set), and a generated pseudonym never takes, for another real name, a beginning or an ending of a person's stored custom pseudonym (a check in `core/`; the library alone tracks only parts stored beside a real part, `pseudonym/library_manager.py:788-797`, `:637-643`). The same gap for generated pseudonyms of one-word names predates 10.11 and is a follow-up. The 10.11 story's AC17 and AC19 carry the detail.
4. **AC4 — The CLI is in scope (see also AC11):** the CLI's [C] (`validation/ui.py:86-87`) is advertised (`README.md:384`) and fails the same way, and Lionel asked for "every output". It gets AC1–AC3 too. The CLI keeps its flags and keys.
5. **AC5 — Undo, redo, navigation and a later correction:** in the desktop app, one undo of "Changer le pseudonyme" restores the previous pseudonym at every place it reached (Q3), and the own-decision flags as they were (10.10); redo applies it again. A text correction or a type change on a row that carries a custom pseudonym removes it (Q-E): the row shows a suggested pseudonym again, and setting it again runs the checks again against the corrected name; in the desktop app, one undo restores both the old name and its pseudonym. In the desktop dialog, OK on the pre-filled pseudonym without a change works like Cancel (Q-H): no custom pseudonym, no "modifié", nothing stored, no message. In batch review, "Précédent" and "Suivant" keep it (10.10 AC2). Nothing is stored in the mapping database before the document is finalized, so an undone change is never stored.
6. **AC6 — Tests first, invented names only:** the tests are committed before the fix, for the desktop app and the CLI. Each expected failure is an `assert` on the written output (and on the stored row), made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). A refusal test fails first on the message shown (the old code shows none), then asserts that the written file and the mapping row are unchanged. The fix removes the markers. Existing tests stay green, except three that change, each for a stated reason (10.11 story, Dev Notes "Existing Tests"): two because Lionel's Q3 changes the reach they encode (one of them through Q-B), and one test fake whose fixed signature rejects new keyword arguments. No other existing test changes.
7. **AC7 — CHANGELOG:** CHANGELOG `[Unreleased]` gets a "Fixed" entry: a custom pseudonym is now used in the written file and kept for later documents; a name that already has a stored pseudonym keeps it (Q1); and in the CLI review, going back to a name with [P] no longer loses a correction or a later accept (Q-F).
8. **AC8 — Docs:** the docs listed in Context keep advertising the feature, now accurately. A doc line changes only where it says something the fix does not do. G7 applies: no headline number changes.
9. **AC9 — User copy:** any new visible text (a dialog line, a warning, a CLI message) is user copy that Lionel approves, word for word, before the story is done. This includes the refusal messages of AC2 (Q1, Q-D) and AC3 (Q2), in the desktop app and the CLI.
10. **AC10 — Gates:**
    - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
    - **G4:** never in the same PR as a detector change.
    - **G2:** QA re-runs the AC6 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
    - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
    - **G7:** no headline number changes. CHANGELOG as AC7, docs as AC8.
11. **AC11 — The CLI review keeps the last decision (Q-F, PO R2 and F2):** in the CLI review, the last decision on a name counts, and a correction stays unless the user corrects the name again. Going back with [P] or the left arrow and pressing Space keeps an earlier [E] correction and writes it; a name rejected with [R] and then accepted with Space is written; [C] after [E] keeps both the correction and the custom pseudonym; a [T] type change after [E] keeps the correction (`ValidationSession.change_entity_type`, `validation/models.py:305-326`, builds the retyped entity from `modified_entity or entity`). Each case is tested first, with invented names, on the written file (AC6).

### Decisions Recorded (Lionel, 2026-10-15)

The questions were asked one at a time, word for word, in the orchestrator's decision log. Each answer is the recommendation except Q-D, Q-G and Q-H.

1. **Q1, a name that already has a stored pseudonym: "Refuse, explain (Rec.)".** Preview he saw: Marie Dubois is already stored as "Quentrel Zorbalia"; typing "Xantor Vellion" is refused, with a message saying the name already has a pseudonym from an earlier document and that, to change it, the name is first removed with `delete-mapping`. The message wording is user copy, approved separately (AC9).
2. **Q2, a pseudonym that clashes: "Refuse both (Rec.)".** Preview: "Xantor Vellion", already the pseudonym of Paul Martin, is refused (two people would merge in the output); "Paul Martin" typed as a pseudonym while Paul Martin appears in this document is refused (it reads as the real person).
3. **Q3, batch review, the other places of the same name: "Every place (Rec.)".** Preview: [Zorbal] [Zorbal] [rejected: Saint-Zorbal]; setting "Xantor" on row 1 gives rows 1 and 2 "Xantor", shown and written; Saint-Zorbal stays rejected. The same rule as corrections (10.9, 10.10); one undo reverts it everywhere.
   - **Note for the SM:** 10.10's `_ChangePseudonymCommand` acts on one row and marks it the row's own decision (`gui/models/validation_state.py:951-952`, `:963`). Its reach now changes, so its "own" rule has to be restated to match how corrections set that flag. The SM proposes the exact rule; any real product choice in it goes back to Lionel.
4. **Q4, a person's first and last name: "Yes, split it (Rec.)".** Preview: Marie Dubois → "Quentrix Zorbal" (the user's); a later "Dubois" alone → "Zorbal", "Marie" alone → "Quentrix"; with the one-word pseudonym "Xantor", a later "Dubois" alone gets its own generated pseudonym. The split is at the last space.
5. **Q-B, a custom pseudonym's "own" status under the Q3 reach: "Like a correction (Rec.)".** Preview: [Zorbal] [Zorbal] [Saint-Zorbal], all to review; "Xantor" set on row 1 → all three show it; rejecting row 2 then rejects all three and nothing is replaced, as after "Accepter" then reject; either way, a place rejected on its own before stays rejected.
6. **Q-C, which words count as a real name: "Capitalised words (Rec.)".** Preview, on « Zorbaville a signé avec Quentrel Zorbalia en avril, grâce à sa petite équipe. » (the detector found "Quentrel Zorbalia" and missed "Zorbaville"): "Xantor Zorbalia" refused; "Xantor Zorbaville" refused; "Grace Vellion" accepted; "Xantor Avril" accepted. A capitalised word at the start of a sentence counts as capitalised.
7. **Q-D, a first or last name that already has a stored part: "Refuse" (NOT the recommendation, which was "Keeps its part").** Preview: "Quentrel Zorbalia" is stored as "Aubin Ferrand", so "Quentrel" alone is written "Aubin"; for "Quentrel Zorbal", "Xantor Vellion" is refused with a new message (to approve): the pseudonym must start with "Aubin", for example "Aubin Vellion". The symmetric case for a last name that already has a stored last-name part is stated by the SM and checked by the PO.
8. **Q-E, a correction after a custom pseudonym: "Removed, set it again (Rec.)".** Preview: "Quentrel" found (the detector missed "Zorbalia"); "Xantor Vellion" set, then the name corrected to "Quentrel Zorbalia" → the pseudonym is removed; set again, it is checked against the new name. In the desktop app, one undo brings back the old name and its pseudonym.
9. **Q-F, two older CLI leaks with [P] then Space: "Fix in 10.11 (Rec.)".** Preview, on « Quentrel Zorbalia a signé avec Zorbal. » (only "Quentrel" found): [E] "Quentrel Zorbalia", [P] back, Space → today the correction is lost and "Zorbalia" stays in clear; [R] "Quentrel", [P] back, Space → today left in clear although accepted last. After the fix, the last decision counts and a correction stays unless redone (AC11).
10. **Q-C2, stored names for the real-name check: "Whole names only (Rec.)".** For the database part of the Q-C check, only full names already stored count; a stored first or last name alone does not (Lionel's Q-C had said "the names already in your mapping database"). Preview: "Quentrel Zorbalia" stored, not in this document → "Quentrel Zorbalia" refused; "Xantor Zorbalia" accepted; "Quentrel Vellion" accepted. In the document's own text the Q-C rule stays: any capitalised word counts.
11. **Q-A, the exact texts: "Approve all (Rec.)".** Lionel approved the new texts word for word: the refusal messages in the desktop app (French and English) and the CLI, the rare finalization error, and the theme value "custom" in the CLI listings. The source is the 10.11 story, Dev Notes "Approved Texts"; the epic does not copy them (AC9).
12. **After QA's FAIL (MW-001, GUARD-001): "Fix before merge (Rec.)".** QA found that the library's two-word last names ("Da Silva", "Le Gall", "Da Costa", "Espírito Santo") broke Q2 and Q-D, since splitting at the last space let "Xantor Da Velmar" through while another person had "Da Velmar", and made four of the new tests flaky (MW-001, CI run `38730457990`); and that confirming a suggested pseudonym on a first name alone made a later full name lose its matching part (GUARD-001). Both are fixed before merge. Neither leaves a name in clear.
13. **Q-G, where a pseudonym of three or more words is split: "Keep the app's four whole" (NOT the recommendation, which was "First word").** Split at the last space (Q4), except that a pseudonym ending with one of the library's two-word last names ("Da Silva", "Le Gall", "Da Costa", "Espírito Santo") keeps it whole as the last name. A part that the real name already has is matched whole first (MW-001 (b)). The checks against other people's names do not depend on the split (AC3).
14. **Q-H, OK on the pre-filled pseudonym without a change: "No, nothing changes" (NOT the recommendation, which was "Yes, keep as shown").** OK without a change works like Cancel: no custom pseudonym, no "modifié", nothing stored, no message, also on a name already in the database. Preview: nothing changes; the file may still get another pseudonym than the list shows.
15. **Q-I, small linking words in the real-name check: "Not alone (Rec.)".** Preview, on « Le contrat est signé avec Zorbaville. »: "Xantor Le Gall" accepted; "Le Velmar" accepted; "Xantor Zorbaville Le Gall" refused; "Xantor Le" ("Le" at the end) refused. Linking words: da das de del della des di do dos du la le les van von der.

### Integration Points

- `gdpr_pseudonymizer/gui/models/validation_state.py` — `change_pseudonym` (`:438-441`), `_ChangePseudonymCommand` (`:936-973`), `_validated_rows` (`:671-687`), `expand_validated_entities` (`:693`); `_ModifyTextCommand` and `_ChangeTypeCommand` (Q-E)
- `gdpr_pseudonymizer/gui/screens/validation.py` — the dialog (`:702-714`), finalization (`:942`)
- `gdpr_pseudonymizer/validation/models.py` — `EntityReview.custom_pseudonym` (`:166`), `mark_confirmed` (`:233`), `change_pseudonym` (`:328-345`), `get_validated_entities` (`:348`, the REJECT exclusion `:362-364`; Q-F)
- `gdpr_pseudonymizer/validation/workflow.py` (`:266-271`, [P] `:307-312`) and `validation/ui.py` (`:86-87`, `:94-95`) — the CLI's [C] and [P] (AC4, AC11)
- `gdpr_pseudonymizer/validation/actions.py` — `ChangePseudonymAction` (`:118-134`, a no-op), kept or removed by the story with no behaviour change
- `gdpr_pseudonymizer/core/document_processor.py` — `_run_validation` (`:286`), `_resolve_pseudonyms` (`:562`, cache `:576`, lookup `:595`), `finalize_document` (`:902`)
- `gdpr_pseudonymizer/core/custom_pseudonym.py` (new) — the checks shared by the desktop app, the CLI and finalization (Q1, Q2, Q-C, Q-D), the split (Q4) and the CLI's texts
- `gdpr_pseudonymizer/gui/screens/batch.py`, `gui/workers/batch_worker.py`, `gui/workers/finalization_worker.py` — the hand-offs of the custom pseudonym to finalization
- `gdpr_pseudonymizer/exceptions.py` — the refusal error class
- `gdpr_pseudonymizer/gui/i18n/en.ts`, `fr.ts` and their `.qm` files — the new desktop texts, once Lionel approves them (AC9)
- `data/` read only: no repository method and no schema change (the Q2 and Q-C checks read the stored rows with the existing `find_all`; Q1 refuses rather than replaces)
- `tests/unit/` and `tests/integration/` — AC6 tests; `CHANGELOG.md` — AC7; the docs in Context — AC8

### Follow-ups Found by the 10.11 SM and PO (not ACs, 2026-10-15)

None is in 10.11's scope. Backlog unless Lionel routes one elsewhere.

- **(a)** The CLI cannot remove a custom pseudonym once set: [C] with an empty answer confirms the group and keeps it (`validation/workflow.py:266-276`). The user can replace it, or quit the review; a correction removes it (Q-E).
- **(b)** `import-mappings` copies rows without checking that their pseudonyms differ from the destination's (`cli/commands/import_mappings.py:163-197`), so two names can share a pseudonym after an import. Pre-existing, for generated pseudonyms too.
- **(c)** In the document where a custom pseudonym is set, a separate row for a lone first or last name keeps its earlier preview in the list, although the file writes the matching part.
- **(d)** `finalize_document_tabular` has no caller in the package (`core/document_processor.py:1107-1154`).
- **(e)** A place rejected on its own keeps an older custom pseudonym in its list entry when the name gets a new one; accepted on its own later, its entry shows the older value while the file uses the name's current one.
- **(f)** Rows created for a custom pseudonym set `is_ambiguous=False`, while generated rows of one-word and three-or-more-word names are ambiguous (PO R9). Match the engine, or note why not.
- **(g)** A generated pseudonym for a one-word name leaves its last part untracked by the library, so a later generated pseudonym can reuse it (PO R8; pre-existing). 10.11 guards custom pseudonyms only (AC3).
- **(h)** The list's preview can differ from the written file for a name that is not stored (previews are not binding; Q-H's preview says so).
- **(i)** A middle word of another person's custom pseudonym of three words is not refused (for example "Zed Quovan" while "Xantor Quovan Velmar" is stored): AC3 compares beginnings and endings, not middles.
- **(j)** A linking word that is itself a whole surname ("Le", "Do", "Du") is not checked on its own, by Q-I.
- **(k)** The CLI and the desktop app differ under Q-H: in the CLI, typing the shown suggestion makes it the user's own pseudonym; in the desktop app, OK on it does nothing.
- **(l)** A desktop batch left waiting while the user follows Q1's route out (`delete-mapping`) cannot be resumed (the mechanism of 10.10 follow-up (f)).
- **(m) For Lionel:** `gui/i18n/en.qm` is stale: three file-filter strings show in French in English mode.

### Estimated Effort: 1.5 weeks (re-estimated after the PO review, 2026-10-15: the refusal checks of Q1, Q2, Q-C and Q-D, the batch reach of Q3 and the CLI fixes of Q-F are the larger part)

---

## Story 10.12: Erasure Log Without the Erased Name (release blocker B1)

**Added by Lionel, 2026-10-16 (release blocker B1 for v2.3.0):** "Fix before release (Rec.)". The question he answered: "B1. When you delete a name from the mapping database with delete-mapping, the database's operation log still records that name. So a deletion request for a person leaves their name in the file. This has been the case in earlier versions too. Fix it before releasing 2.3.0?" The option he chose: "The log keeps a record that a deletion happened (date, row id, type), but not the name. A small story, written through Codex, with failing tests first." Found by QA at the Epic 10 close-out (backlog B1). The same defect is #3 of the Codex release review (2026-10-16). Lionel answered the story's three questions on 2026-10-16, after the PO's review (Decisions Recorded).

**As a** user who erases a person's name with `delete-mapping` (GDPR Article 17),
**I want** the database to keep a record that the deletion happened, without the name,
**so that** the erased person's name is no longer in the file.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-16).
**Change type:** the CLI erasure command and its audit entry; on open, a one-time removal of the names already in the log and one compaction of the file (data layer); deleted data overwritten at every deletion, in the CLI and the desktop app; the `--reason` help and the docs. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. It shares no code file with Stories 10.13 to 10.17 (only `CHANGELOG.md`, which every story edits); never in the same PR as another story. All six land before the v2.3.0 release.

### Context

At `main` `fb7917c`. The PO checked every fact below on 2026-10-16 and measured the marked ones with probes on invented names (PO review notes for 10.12 and 10.13).

- **What is written:** `delete-mapping` writes one ERASURE entry per deleted row into the `operations` table (`gdpr_pseudonymizer/cli/commands/delete_mapping.py:169-192`). Its `user_modifications` holds `deleted_entity_id`, `deleted_entity_name` (the erased text, `:180`), `deleted_entity_type` and `reason`; the entry also has the date, `theme_selected` and `entity_count`. The deleted rows come back decrypted (`data/repositories/mapping_repository.py`, `delete_entities_by_full_name`), so the name is stored as plain text.
- **Not encrypted (measured):** `user_modifications` is a JSON column (`data/models.py`, `Operation`), written as is by `AuditRepository.log_operation` (`data/repositories/audit_repository.py:52-77`). The module says the operations table holds no sensitive data and needs no encryption (`:6`, `:26-27`). Only the entity name and pseudonym columns are encrypted (`mapping_repository.py:551-556`); the operations, the metadata, the types and the themes are plain. After `delete-mapping` by name and by `--id`, both erased names could be read with plain `sqlite3`, without the passphrase. A name with an accent is stored escaped (`"Quentrelle Z\u00e9brandine"`), as `json.dumps` writes by default.
- **Copied out by `export` (measured):** `export` writes the audit log to JSON or CSV (`cli/commands/export.py:174-190`), `user_modifications` included (`audit_repository.py:286`, `:393-395`). The JSON file holds the name in UTF-8 (`ensure_ascii=False`, `:310`); the CSV file holds it escaped (`json.dumps`, `:394`). Only exports that include the ERASURE entries hold names: `--type` and the date filters can leave them out. `stats` shows only counts and the type of the last operation (`cli/commands/stats.py:104-173`); it shows no name.
- **Encrypted copies left by every deletion (measured):** after a deletion whose log entry holds no name, 7 encrypted copies of the person's name stay in the file: the full name 3 times (the table, `idx_entities_full_name`, the unique index), the first name twice, the last name twice. They sit in freed space inside pages still in use (`freelist_count` 0). The encryption is deterministic (AES-256-SIV, `data/encryption.py:1-10`): the same name always gives the same encrypted text, so anyone with the passphrase and a raw-byte reader can find them; the app never shows them. With `PRAGMA secure_delete=ON` on the deleting connection, 0 copies stay.
- **The desktop app:** its database screen erases rows with the same function as `--id` (`gui/workers/database_worker.py:281`; `delete_mapping.py:158`), so its deletions leave the same encrypted copies. It writes one ERASURE entry with a count, and no name, row id or type (`:296-307`).
- **Cleaning old entries (measured):** removing the names in one `BEGIN IMMEDIATE` transaction, then `VACUUM`, then `PRAGMA wal_checkpoint(TRUNCATE)`, leaves 0 copies of any form and a 0-byte `-wal`. `VACUUM` fails inside a transaction ("cannot VACUUM from within a transaction"), so it runs after the COMMIT. After `VACUUM` alone, the main file still holds the names until the checkpoint. A reader in another process makes the checkpoint report busy (`(1, 16, 0)`), and the names stay in the main file until that reader closes. The removal without `VACUUM` leaves the 7 encrypted copies of each erased person. On a 14.9 MB file (20,000 entity rows, 2,000 old entries): removal 0.009 s, `VACUUM` 0.101 s, checkpoint 0.002 s; the `-wal` grew to 14.8 MB during `VACUUM`.
- **The 10.7 pattern:** `_ensure_current_schema` (`data/database.py:551-610`) runs on its own `sqlite3` connection in autocommit mode, takes `BEGIN IMMEDIATE`, checks the file again inside the transaction, and is all or nothing. A failure stops the open with `DatabaseConversionError` and leaves the file as it was (`open_database`, `:398-399`, `:404-408`). Its error text names the conversion (`_conversion_failed_message`, `:530`: the file "could not be converted to the new format (one row per name and type)"). Every file of a released version (v2.2.0 and older) is converted by 10.7 on its first 2.3.0 open, so a file of a released version that 2.3.0 cannot write to already does not open.
- **Out of reach of any fix in the app:** files already written by `export`; mapping exports, which hold `full_name` by design (`list-mappings --export`, `cli/commands/list_mappings.py:279-296`; the desktop CSV export, `database_worker.py:371-381`); copies of a database never opened by 2.3.0; names a user typed into `--reason`. Logs hold no name: structlog writes to stdout only (`utils/logger.py:28`), and its `entity_deleted` event holds the id, type and reason (`delete_mapping.py:216-221`); the success lines print the name to the terminal only (`:204-210`).
- **Since v1.1.0:** the name field came with Story 5.1 (`29df6dd`, 2026-02-12), so every database whose user ran `delete-mapping` since v1.1.0 holds the erased names in its log.
- **This story reverses a deliberate design (Lionel, 2026-10-16):** Story 5.1 kept the name on purpose, as proof of the erasure. `docs/CLI-REFERENCE.md` says so in three passages: "Audit Trail" (`:511-515`, "Entity name, type, and ID"), the compliance list (`:626`, "recording who was deleted, when, and why") and "PII Retention in Audit Logs" (`:651-661`). That last passage justifies keeping the name under GDPR Article 17(3)(e) and Article 5(2) (`:653-655`), and says it is "Protected by the same AES-256-SIV encryption as all other database content" (`:658`) and "Accessible only with the database passphrase" (`:659`). Both claims are false (see "Not encrypted"). `docs/CLI-REFERENCE.fr.md` has the same passages at the same lines (`:626`: "quelle personne a été supprimée"). From 2.3.0 the log proves that a deletion happened, not whom it concerned.
- **The `--reason` text:** kept as typed. Its help reads « Reason for deletion (GDPR request reference) » (`delete_mapping.py:52`); the docs' option table (`CLI-REFERENCE.md:490`, `CLI-REFERENCE.fr.md:490`) and examples use `GDPR-REQ-2026-042`.
- **Three existing tests assert the name:** `tests/integration/test_erasure_workflow.py:159`, `tests/unit/cli/commands/test_delete_mapping.py:243`, `tests/unit/cli/commands/test_delete_mapping_type_aware.py:135`.

### Acceptance Criteria

1. **AC1 — No name in a new erasure entry:** `delete-mapping`, by name and by `--id`, still writes one ERASURE entry per deleted row, with the date, the row id, the type and the reason, and with the erased name in no field of the entry. The same holds for the entry as `export` writes it (JSON and CSV). The deletion itself, the confirmation and the success lines on screen are unchanged.
2. **AC2 — Deleted data overwritten (Q2):** from 2.3.0, every connection the app opens to the mapping database has `PRAGMA secure_delete=ON`, so a deletion writes zeros over the deleted row and its index entries. This holds for `delete-mapping` (by name and by `--id`), for the desktop database screen and for the AC3 removal. Nothing changes on screen.
3. **AC3 — Names already in the log (Q1):** on the first open by 2.3.0 of a file that has not been cleaned (whatever its schema version), after the passphrase check and the 10.7 conversion, the name is removed from every ERASURE entry; the date, row id, type, reason and every other field of the entry stay as they were. Then the file is compacted once.
   - **Removal:** the 10.7 pattern: its own connection, autocommit, `BEGIN IMMEDIATE`, a check again inside the transaction, all or nothing. A second process that waited finds the work done and changes nothing. Only entries whose JSON is valid are edited (a `json_valid` guard): `json_remove` raises on malformed JSON, which would block that file's opens for good; an entry skipped this way is counted in the log, without its content. SQLAlchemy always writes valid JSON, so the guard should never fire.
   - **A failed removal stops the open** and leaves the log unchanged (the 10.7 conversion of the same open has already committed), as a failed 10.7 conversion stops it; otherwise `export` could copy the old names out right after the failed open. It raises the 10.7 error class with its own text, not the conversion text, which would be false here. That text is new user copy, approved with the AC4 texts. This is the PM's reading of the 10.7 precedent, checked by the PO: for files of released versions it adds no file that cannot be opened, since the same open converts them and a file 2.3.0 cannot write to is already stopped by the conversion. It does not hold for files converted by unreleased `main` builds since 10.7 (schema 1.1.0, not yet cleaned), such as developers' databases; that case is negligible.
   - **Compaction:** after the COMMIT, `VACUUM`, then `PRAGMA wal_checkpoint(TRUNCATE)`. It runs once per file, even when no name was found, because that also clears the encrypted copies left by earlier deletions (desktop deletions included).
   - **Retry:** a metadata row, written in the removal transaction, records that the compaction is due. It is cleared only after a checkpoint that reports no busy page. A compaction that fails, or a checkpoint held up by another reader, is retried at the next open; it never stops the open.
   - A file created by 2.3.0 needs neither step (the SM chooses how it is marked). The schema does not change and `schema_version` stays 1.1.0.
4. **AC4 — Docs and help (Q3):** in `docs/CLI-REFERENCE.md` and `docs/CLI-REFERENCE.fr.md`:
   - "Audit Trail" (`:511-515`) and the compliance list (`:626`) say what the entry keeps (date, row id, type, reason) and that it no longer keeps the name.
   - "PII Retention in Audit Logs" (`:651-661`) is removed or rewritten. Both encryption bullets (`:658`, `:659`) go whatever happens, and the Article 17(3)(e) and 5(2) paragraph (`:653-655`) goes or is rewritten. Suggested line: proof that a request was handled is the date, the row id, the type and the user's own request reference in `--reason`; a user who must keep the person's identity keeps it in their own request register, outside this tool.
   - The `--reason` help (`delete_mapping.py:52`) and the option rows (`:490`) ask for a request reference, never the person's name. Nothing is checked (Q3).
   - The docs say what stays out of reach (Context).
   - The error text for a failed removal (AC3) goes with these texts.
   - Every text here is user copy that Lionel approves, word for word, before the story is done.
5. **AC5 — Tests first, invented names only:** the tests are committed before the fix. Each expected failure is an `assert` on the stored rows, the `export` output or the file's raw bytes, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. The tests cover:
   - the stored `operations` rows and the `export` output (JSON and CSV) after a deletion by name and by `--id` (AC1);
   - a raw-byte check of the file after a deletion by `delete-mapping` and by the desktop deletion worker (Q2): no copy of the name in UTF-8, in its `\u`-escaped form, or in the encrypted form the repository stores (full name, first name, last name);
   - a raw-byte check of a file written in the old format, with ERASURE entries holding names (one with an accent), after its first 2.3.0 open (Q1): no copy in any of those forms; every other field of each entry unchanged; a second open changes nothing; a reader held open in another connection during the open leaves the compaction due, and the next open completes it;
   - raw bytes are read only after every connection is closed, or after a TRUNCATE checkpoint, `-wal` file included.

   The three existing tests listed in Context change, each for that stated reason; no other existing test changes.
6. **AC6 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: the erasure log no longer keeps the erased name; names already in the log are removed on the first open by 2.3.0 and the file is compacted once (the `-wal` file grows to about the size of the database while it does); every deletion now overwrites the deleted data; files already written by `export` or by a mapping export, and database copies never opened by 2.3.0, are not changed. The 10.7 entry's sentence "The erasure audit entry records the deleted name, as before." (`CHANGELOG.md:40`) is corrected.
7. **AC7 — Codex:** the code is written through Codex (Forge, `ForgeProgress.ts`), as Lionel requires for customer-facing repositories. The tests-first commit is code too: it is written through Forge, or the final review below covers it explicitly. The PR gets a `codex exec` review of its final diff before the merge command. If Codex cannot run, the work stops and Lionel is told; no Claude-written code is presented as Codex's.
8. **AC8 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
   - **G2:** QA re-runs the AC5 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes. CHANGELOG and docs as above.

### Decisions Recorded (Lionel, 2026-10-16)

The PO reviewed the story and the questions first. The questions were asked one at a time, word for word, in the orchestrator's decision log. Each answer is the recommendation.

1. **Q1, the names already in the log: "Remove and compact (Rec.)".** On the first open by 2.3.0, the name is removed from the old ERASURE entries; the date, row id, type and reason are kept; then the file is compacted once (`VACUUM`, then `wal_checkpoint(TRUNCATE)`). The message he saw: the old names can be read without the passphrase since 1.1.0; out of reach are exports, copies never opened by 2.3.0 and names typed in reasons. The other option was "Leave them". The PM's first draft also offered "leave them and explain how to remove them"; the PO showed it is not a real option (no supported command edits the log), and it was not asked.
2. **Q2, overwriting deleted data: "Overwrite (Rec.)".** From 2.3.0, every deletion writes zeros over the deleted data (`PRAGMA secure_delete`), in the CLI and the desktop app. Nothing changes on screen. Measured: 7 encrypted copies left per deleted person today, 0 with it.
3. **Q3, names in `--reason`: "Ask, don't check (Rec.)".** The `--reason` help (today « Reason for deletion (GDPR request reference) », `delete_mapping.py:52`) and the docs ask for a request reference, never the person's name. Nothing is checked. The wording is user copy for his approval with the other doc texts (AC4). The other option was "Also refuse the name".

### Integration Points

- `gdpr_pseudonymizer/cli/commands/delete_mapping.py` — the ERASURE entry (`:169-192`, the name at `:180`), the `--reason` help (`:52`)
- `gdpr_pseudonymizer/data/repositories/audit_repository.py` — `log_operation` (`:52-77`), the export functions (`:224`, `:317`); the module note (`:6`, `:26-27`)
- `gdpr_pseudonymizer/data/database.py` — `open_database` (`:301`): `secure_delete` on every connection (AC2); the removal and compaction beside `_ensure_current_schema` (`:551`), and its metadata row (AC3)
- `gdpr_pseudonymizer/gui/workers/database_worker.py` — its deletion (`:281`) gets `secure_delete` through the shared open; its ERASURE entry stays as it is
- `docs/CLI-REFERENCE.md`, `docs/CLI-REFERENCE.fr.md` — AC4
- `tests/` — AC5; `CHANGELOG.md` — AC6

### Follow-ups Found by the PM and PO (not ACs, 2026-10-16)

- **(a)** The desktop app's ERASURE entry holds a count only, no row id or type (`database_worker.py:296-307`), unlike the CLI's. Not a leak.
- **(b)** Mapping exports (`list-mappings --export`, the desktop CSV export) hold names by design. The docs could remind users to delete them after use.
- **(c)** Input file names in `files_processed` are the user's own naming (low).
- **(d) Docs debt (10.12 PO, 2026-10-16):** `docs/architecture/6-components.md:135` says the data layer persists "entity mappings and audit logs with encryption". The operations table is not encrypted (Context, "Not encrypted"). Corrected with this story's docs or at the epic close-out.

### Estimated Effort: 1 week (the one-time cleaning on open and its raw-byte tests are the larger part)

---

## Story 10.13: Warning Before Writing Names Still to Review (release blocker B2)

**Added by Lionel, 2026-10-16 (release blocker B2 for v2.3.0):** "Fix before release (Rec.)". The question he answered: "B2. In desktop batch review, "Valider et continuer" writes the document even when some names are still "to review" (neither accepted nor rejected). Those names stay in clear, and nothing warns you. Fix it before releasing 2.3.0?" The option he chose: "If names are still to review, a warning asks you to confirm before the document is written. The warning text comes to you for approval first. A small story, written through Codex, with failing tests first." Found by QA at the Epic 10 close-out (backlog B2; 10.10 follow-up (d)). Lionel's Q1 (2026-10-16) extends it to single-document validation and the CLI, and he approved the texts word for word (Decisions Recorded).

**As a** user validating documents in the desktop app or the CLI,
**I want** to be told, before a document is written, that some names are still to review,
**so that** I do not leave names in clear without knowing it.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-16).
**Change type:** desktop batch review and single-document validation, the CLI's final summary, the desktop translations. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. Its own PR, never shared with another story; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. It shares `validation/workflow.py`, `validation/models.py` and `validation/ui.py` with 10.15; `gui/models/validation_state.py` with 10.16 and 10.17 (and 10.14 if it changes it); `gui/screens/validation.py` and the `gui/i18n/` files with 10.14, which comes after it (both change `_on_finalize`'s batch branch). The `.qm` files are binary: they are regenerated after a rebase, never merged. Every story edits `CHANGELOG.md`. All six land before the v2.3.0 release.

### Context

At `main` `fb7917c`. The PO checked every fact below on 2026-10-16 and measured the marked ones with probes on invented names, through the real batch path (`BatchScreen`, `ValidationScreen`, `BatchWorker`), the real single-document path (`DetectionWorker`, `ValidationScreen`, `FinalizationWorker`) and the real CLI review.

- **Batch review (measured, case B2a):** "Valider et continuer" and, on the last document, "Valider et terminer" (`gdpr_pseudonymizer/gui/screens/validation.py:236`, `:238`) both go through the batch branch of `_on_finalize` (`:986-1000`), which sends the validated list at once, with no window. The list holds confirmed, modified and added rows only (`gui/models/validation_state.py`, `_validated_rows`). In batch each place of a name is its own row (`CHANGELOG.md:180`). "Quentrelle" at 2 places, both rows still to review: no window; `get_pending_count()` gives 2 rows (`validation_state.py:698-704`) for 1 name; the output holds "Quentrelle" twice in clear.
- **The same place under another type (measured, case B2b):** ORG "Zorbaville" accepted at 2 places, LOCATION "Zorbaville" at the same place left to review: pending count 1, no window, and no "Zorbaville" in the output, because the ORG pseudonym covers the place. A count of rows still to review would be wrong here.
- **Single document (measured):** "Finaliser" (`validation.py:240`) shows the "Résumé de validation" window (`:1002-1028`): "Vous avez accepté %1 entités, rejeté %2, ajouté %3 manuellement et modifié %4 pseudonymes. / Continuer avec la pseudonymisation ?", buttons "Confirmer" and "Annuler" (`gui/widgets/confirm_dialog.py`). Its counts (`get_summary`, `validation_state.py:706-724`) have no "to review" count. One name still to review at 2 places: the window says 2 accepted, 0 rejected, 0 added, 0 modified, and the output holds the name twice in clear. In this mode rows are names already (variant grouping, `gui/workers/detection_worker.py:148-164`).
- **English mode (measured):** the same window shows "Validation summary", "Confirm" and "Annuler": the cancel label is the dialog's untranslated default (`confirm_dialog.py:22`), and the factories never pass one. The batch buttons stay in French (QA backlog B21; 10.10 follow-up (a)). A `tr()` source written with a `\u` escape is extracted mangled and never translated (`gui/i18n/en.ts:1312` "Finaliser u25b6", `:661` "Toutes vu00e9rifiu00e9es"). The app has no Qt plural forms: it writes "(s)" on nouns and adjectives (`gui/i18n/translator.py:94`, `gui/screens/batch.py:584`) or plain plurals.
- **CLI (measured):** [N] or the right or down arrow moves to the next name without a decision (`gdpr_pseudonymizer/validation/ui.py:92-93`, `validation/workflow.py:377-382`); on the last name of a type it does not move ("Already at last entity of this type", `:381`). A name skipped that way is not sent unless the user comes back to it with [P] and decides. The final screen (`FinalConfirmationScreen`, `validation/ui.py:343`) and the question "Ready to process document with validated entities?" (`validation/workflow.py:141`) count no names still to review. [N] on the first person, decisions on the rest: "Zorbalia Quentrix" stays in clear, and the final counts show 3 confirmed and no "to review".
- **"No" at "Ready to process" (measured):** it restarts the review from the first name (`workflow.py:144` calls `self.run`, which builds a new `ValidationSession`, `:96`), so every decision is lost. Lionel was told on 2026-10-16; it stays as is.
- **10.10 stays:** only the document the batch waits on can be validated (10.10 AC1); "Précédent" and "Suivant" keep each document's decisions (10.10 AC2).

### Acceptance Criteria

1. **AC1 — What is counted:** the number of different names (text and type) still to review that would be written in clear. One name counts once however many places it has (2 places of one name = 1). A name whose every place is entirely covered by a place that is written (accepted, corrected or added, under any type) does not count, since nothing of it stays in clear (case B2b). In batch review each place is a row; in single-document validation rows are names already; in the CLI a name skipped with [N] and never decided counts.
2. **AC2 — Batch review:** "Valider et continuer" and "Valider et terminer", on a document whose count is 1 or more, show the warning window (AC5) before anything is sent. "Continuer quand même" sends the list and the document is written as today. "Annuler" returns to the review: nothing is sent to the batch, nothing is written, and the batch still waits on that document. With a count of 0, no window, as today.
3. **AC3 — Single document:** "Finaliser", with a count of 1 or more, shows the same window before the "Résumé de validation" window. "Continuer quand même" goes on to the summary window, as today; "Annuler" returns to the review and nothing is written. With a count of 0, only the summary window, as today.
4. **AC4 — CLI:** with a count of 1 or more, the final summary shows one line, above the question "Ready to process document with validated entities?": "⚠ Still to review: %1 (left in plain text)". With a count of 0, no line. The question and its "No" are unchanged.
5. **AC5 — The approved texts (Lionel, 2026-10-16, word for word; " / " marks a new line; %1 is the AC1 count):**
   - **French:** title « Noms encore à vérifier »; text « Noms encore à vérifier dans ce document : %1. » / « Un nom ni accepté ni rejeté n'est pas pseudonymisé : il reste en clair dans le fichier de sortie. » / « Continuer quand même ? »; buttons « Annuler » and « Continuer quand même ».
   - **English:** title "Names still to review"; text "Names still to review in this document: %1." / "A name neither accepted nor rejected is not pseudonymized: it stays in plain text in the output file." / "Continue anyway?"; buttons "Cancel" and "Continue anyway".
   - **CLI:** "⚠ Still to review: %1 (left in plain text)".
   - The window passes its own translated cancel label, since the dialog's default "Annuler" is never translated. Its `tr()` sources are written without `\u` escapes, and `en.qm` is regenerated. Changing the default label of other windows is not in scope (follow-up (b)).
6. **AC6 — Tests first, invented names only:** the tests are committed before the fix and run through the real paths: the real `BatchScreen`, `ValidationScreen` and `BatchWorker` thread, only detection replaced, as in 10.10; the real single-document path (`DetectionWorker`, `ValidationScreen`, `FinalizationWorker`); the real CLI review, driven by keys. Each expected failure is an `assert` on the window shown (its texts and its count) or on the CLI line, and on the written file, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - "Annuler" leaves no output, and in batch the batch still waits on the document;
   - "Continuer quand même" writes the file as today;
   - one name at 2 places counts 1 (B2a);
   - the same place accepted under another type counts 0 and shows no window (B2b);
   - in English mode the window shows the English texts, "Cancel" included;
   - in the CLI, a name skipped with [N] gives the line with 1, and a review with every name decided gives no line.

   Existing tests stay green.
7. **AC7 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: before a document is written with names still to review, batch review and single-document validation show a warning, and the CLI's final summary shows how many there are.
8. **AC8 — Codex:** the code is written through Codex (Forge, `ForgeProgress.ts`), as Lionel requires for customer-facing repositories. The tests-first commit is code too: it is written through Forge, or the final review below covers it explicitly. The PR gets a `codex exec` review of its final diff before the merge command. If Codex cannot run, the work stops and Lionel is told; no Claude-written code is presented as Codex's.
9. **AC9 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
   - **G2:** QA re-runs the AC6 tests, checks out the tests-first commit to see them fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes. CHANGELOG as above.

### Decisions Recorded (Lionel, 2026-10-16)

The PO reviewed the story and the questions first. The questions were asked one at a time, word for word, in the orchestrator's decision log. Each answer is the recommendation.

1. **Q1, where the warning comes: "Both (Rec.)".** Whenever a name still to review would be written in clear, the user is told first, with one rule everywhere. Preview: batch, the warning window before writing; single document, the same window before the summary window, only when names are left; CLI, one line in the final summary, "⚠ Still to review: 1 (left in plain text)". He was told that "No" at the CLI's "Ready to process" restarts the review and loses every decision; that stays as is. The other options were "Single document only" and "Batch only".
2. **Q2a, the French text: "Approve (Rec.)".** Approved exactly as in AC5. %1 is the number of different names still to review that would be written in clear (2 places of one name = 1).
3. **Q2b, the English text and the CLI line: "Approve (Rec.)".** Approved exactly as in AC5.

These texts replace the PM's first proposal, which the PO found wrong in three ways: "Ils resteront en clair dans le fichier écrit" is false when the same place is accepted under another type (B2b); "%1 nom(s) … n'ont été … Ils" cannot agree with a count of 1; and the app says "fichier de sortie" (`batch.py:856`, `validation.py:947`), not "fichier écrit". At the first asking Lionel could not see the texts ("i can't see the texts, show them"); they were asked again with each text in the option preview.

### Integration Points

- `gdpr_pseudonymizer/gui/screens/validation.py` — `_on_finalize` (`:981-1028`): the batch branch (`:986-1000`) and the summary window (`:1002-1028`)
- `gdpr_pseudonymizer/gui/models/validation_state.py` — the AC1 count, beside `get_pending_count` (`:698-704`) and `get_summary` (`:706-724`)
- `gdpr_pseudonymizer/gui/widgets/confirm_dialog.py` — read only; the new window passes its `cancel_label`
- `gdpr_pseudonymizer/gui/i18n/fr.ts`, `en.ts` and their `.qm` files — the approved texts
- `gdpr_pseudonymizer/validation/workflow.py` (`:138-141`), `validation/ui.py` (`FinalConfirmationScreen`, `:343`) and `validation/models.py` (`ValidationSession`) — the CLI count and line
- `tests/unit/`, `tests/integration/` — AC6; `CHANGELOG.md` — AC7

### Follow-ups Found by the PO (not ACs, 2026-10-16)

- **(a)** "No" at the CLI's "Ready to process" restarts the review and loses every decision (`workflow.py:144`, `:96`). Lionel was told; it stays as is.
- **(b)** In English mode every confirm window shows "Annuler" (`confirm_dialog.py:22`), the "Résumé de validation" window included. With QA backlog B21 (batch buttons in French).
- **(c)** [N] on the last name of a type does not move on (`workflow.py:381`).

### Estimated Effort: 0.5-1 week (single-document validation and the CLI were added by Q1)

---

## Story 10.14: Desktop Batch and Finalization Hand-Offs (Codex release review #1 and #4)

**Added by Lionel, 2026-10-16 (Codex release review):** "Leaks + new 10.11 bugs (Rec.)". The question he answered: "Codex review: which of the confirmed problems must be fixed before releasing 2.3.0? (Details in the previews; numbers are Codex's.)" In his preview, to fix before release: "1 second batch mixes with the first (leak)" and "4 edit during writing leaves part in clear"; later: 5, 9 and 10. The review (`codex exec`, verdict NO-SHIP) read `main` at `fb7917c` and found ten problems; QA reproduced each one on the real code with invented names (probes and logs kept outside the repository, in the orchestrator's analysis folder `r23codex/qa`). This story takes #1 and #4. #3 is Story 10.12, #2 is Story 10.15, #6, #7 and #8 are Story 10.16; #5, #9 and #10 are in the backlog (Close-Out Record). Lionel answered the story's two questions on 2026-10-16, after the PO's review (Decisions Recorded).

**As a** desktop-app user,
**I want** each batch and each finalization to write exactly the review I validated, and a running batch never to be replaced or lost by opening something else,
**so that** no name is left in clear because another run or a late change got mixed in.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-16). Both are leaks (Codex P0).
**Change type:** desktop app: every route that opens a document or a folder while a batch runs, and its message; the batch run's hand-offs between screen and worker; the finalization hand-off; the review's controls while a document is written. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. It comes after 10.13: both change `gui/screens/validation.py` (`_on_finalize`'s batch branch) and the `gui/i18n/` files; the `.qm` files are binary, regenerated after the rebase, never merged. If it changes `gui/models/validation_state.py`, it shares that file with 10.13, 10.16 and 10.17. Every story edits `CHANGELOG.md`. Before the v2.3.0 release.

### Context

At `main` `fb7917c`:

- **#1, a second batch mixes with the first (Codex P0).**
  - **Code:** a new batch replaces the worker without stopping or disconnecting the old one (`gui/screens/batch.py:624`, `_launch_worker`: the kept reviews are emptied at `:656`, the new worker is set at `:676`), and the old worker's `validation_required` stays connected to the screen. The kept review and the submission guard identify a document by its index only, not by its run (`gui/screens/validation.py:427`, `batch.review_state(self._doc_index)`; `batch.py:951`, `doc_index != self._awaiting_doc_index`).
  - **QA's reproduction:** batch A running; batch B started from File → "Ouvrir un dossier..." and "Démarrer" while A is detecting; the test chooses which worker's signal arrives first.
    - **A's signal first:** at `eee4d41` (10.10) and at `fb7917c`, B shows A's review ("Zorbal Quentrix signe le contrat A.", the same review object after B's own signal). "Valider et continuer" sends A's positions to B's worker. B's output at `eee4d41`: "Yasmine Seixast signé par Vorlan Mestrix.": B's name in clear and B's text damaged (at `fb7917c`: "Douglas Brancot signé par Vorlan Mestrix."). A's worker waits forever. At `49d4daa` (10.9) and v2.2.0 this order passes.
    - **B's signal first:** at v2.2.0 the screen then shows A's document, and validating it writes B's output with A's positions: "Éliza Carret signé par Vorlan Mestrix.". At `fb7917c` this order passes.
  - **So:** two runs at once have leaked in every version tested; 10.10's kept reviews changed which order leaks. 10.10 follow-up (f), "After 10.10 nothing leaks", is wrong for this path (corrected there).
- **Every route that opens something during a batch (measured by the PO, with the batch worker waiting on document 0):**
  - **File › "Ouvrir un dossier..." (Ctrl+Shift+O;** `gui/main_window.py:140`, `_on_open_folder` `:391-397`): the batch screen goes back to its first phase with "Démarrer" enabled; clicking it starts a second worker while the first still waits (the #1 path above).
  - **File › "Ouvrir un document..." (Ctrl+O;** `:134-136`, `_on_open_file` `:381`) **and File › "Fichiers récents"** (`_open_recent`, `:369`): the processing screen, then the single-document review of the opened file. The batch worker still waits on document 0, and nothing leads back to it (10.10 follow-up (f)).
  - **The home screen,** reached through Outils › "Paramètres..." (Ctrl+,, `:178-180`) then "Retour": its "Traitement par lot" button (labelled "Ouvrir un dossier", `gui/screens/home.py:79-81`, `:130-132`) opens the batch screen with `reset=True` (`batch.py:83-84`). The screen goes back to its first phase and drops its worker reference while the old worker still waits, so « Annuler le lot » can no longer stop it (`_do_cancel`, `batch.py:863-866`); a second batch then starts. The home drop zone sends a folder the same way (`home.py:280-286`, by reading) and a file to the processing screen (`:231-269`); its recent list opens a file (`:145`).
- **« Annuler le lot » (measured by the PO):** from the review of document 1, after document 0 was written, the window says « Tous les documents traités seront annulés. Aucun fichier de sortie ne sera conservé. ». Document 0's output is deleted and document 1 is not written (`gui/workers/batch_worker.py:331-333`, `:403-414`); the mapping row stored for document 0 stays.
- **English labels (measured by the PO):** the batch screen's cancel button shows "Cancel batch" (`gui/i18n/en.ts:103-104`, BatchScreen context). The review screen's batch cancel button (`validation.py:223`) shows « Annuler le lot », because its ValidationScreen context has no `en.ts` entry. Information windows have one button, « Fermer » / "Close" by default (`gui/widgets/confirm_dialog.py:117-126`); no window uses "OK".
- **#4, finalization shares live entities with the review (Codex P0).**
  - **Code:** single-document finalization gives the worker the review's own entity objects (`validation.py:1043`, `expand_validated_entities`; `gui/workers/finalization_worker.py:47` keeps the list as given) and the review's custom pseudonyms. While the document is written only "Finaliser" and "Retour" are disabled (`validation.py:1045-1046`); the editor, the list, undo and the keyboard shortcuts stay enabled (measured by QA: `editor_enabled`, `panel_enabled` and `undo_shortcut_enabled` all True).
  - **QA's reproduction** (failed at `fb7917c` and at v2.2.0, so pre-existing; since 10.11 it also reaches custom pseudonyms): « Zorbal Quentrix signe le contrat. », the name corrected to « Zorbal » while the worker runs. Output "Louane Sousa Quentrix signe le contrat." with a generated pseudonym, and "Xantor Vellion Quentrix signe le contrat." with the custom pseudonym "Xantor Vellion": the surname stays in clear while the database holds the full name. At v2.2.0, an undo of a type change during writing also wrote a name the user sent as PERSON as an ORG; at `fb7917c` that case passes.
  - **Batch:** the list the batch screen sends to its worker is built from the same review objects (`validation.py:986-1000` → `batch.py:978`, `submit_validation_result`). Not reproduced as a leak, since the screen leaves the review while the worker writes; the same rule applies.
- **Not in this story:** #10, the batch worker's lost wake-up (`gui/workers/batch_worker.py:365`; 10.10 follow-up (c)), is in the backlog (Lionel: later). The run identifier must not make it worse.

### Acceptance Criteria

1. **AC1 — Refused while a batch runs (#1, Q1):** while a batch runs (from "Démarrer" until its summary), every route that opens a document or a folder shows the AC6 message, and nothing else happens: File › "Ouvrir un document..." and Ctrl+O; File › "Ouvrir un dossier..." and Ctrl+Shift+O; File › "Fichiers récents"; and on the home screen, the "Traitement par lot" button, the drop zone (a file, a folder or several files) and the recent list. A second worker never runs beside the first.
2. **AC2 — The way back (Q1):** the message's button, « Revenir au lot », opens the running batch where it waits: the review of the document it waits on, or its progress screen. No route resets the batch screen or drops its worker while a batch runs; the batch comes back as it was. « Annuler le lot » stays the way to stop a batch, with its confirmation window, as today.
3. **AC3 — Every hand-off tied to its run (#1):** each batch run has its own identifier, carried by every signal of its worker, every kept review and every submission. A signal from a worker that is not the current run's is ignored (logged without any name); a kept review is attached only within its own run; a list goes only to the worker of the run its review belongs to. This holds even if a second run starts by a route AC1 missed.
4. **AC4 — Finalization gets copies (#4):** the entities and the custom pseudonyms a finalization receives, in single-document validation and in batch, are copies made when the user confirms; nothing done in the review afterwards changes them.
5. **AC5 — The review cannot change while a document is written (#4):** during single-document finalization, the editor, the list, undo and redo, and the review's keyboard shortcuts (undo and redo, accept and reject, and the others) are disabled, as "Finaliser" and "Retour" already are. They are enabled again if the finalization fails.
6. **AC6 — The approved texts (Lionel, 2026-10-16, word for word):**
   - **French:** title « Lot en cours »; text « Un lot de documents est en cours de traitement. Pour ouvrir un autre document ou dossier, terminez d'abord ce lot ou arrêtez-le avec « Annuler le lot ». »; button « Revenir au lot ».
   - **English:** title "Batch in progress"; text "A batch of documents is being processed. To open another document or folder, finish this batch first or stop it with "Cancel batch"."; button "Back to the batch".
   - The review screen's batch cancel button gets its English translation, "Cancel batch", the text the batch screen already shows (`en.ts:104`), so the English message names a button that both screens show.
   - The `tr()` sources are written without `\u` escapes, and `en.qm` is regenerated.
7. **AC7 — Tests first, invented names only:** the tests are committed before the fix and run through the real paths: the real `BatchScreen`, `ValidationScreen` and `BatchWorker` threads for #1 and the routes, as in 10.10; the real `ValidationScreen` and `FinalizationWorker` for #4; only detection replaced. Each expected failure is an `assert` on the window shown, the written file or the stored rows, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - each AC1 route during a running batch shows the message (French and English texts), starts nothing, and leaves the batch waiting; « Revenir au lot » brings back the waiting batch; after the home route, « Annuler le lot » still stops the worker;
   - #1 in both signal orders: B's output holds none of B's names in clear and none of A's text, and A's worker ends;
   - #4: an edit and an undo made while the worker is held before it reads its input, with a generated and with a custom pseudonym: the written file holds the full pseudonym and no part of the real name, and the stored row matches; the shortcuts are disabled while it writes;
   - the batch hand-off: the list and the custom pseudonyms the worker gets share no object with the kept review;
   - in English mode, the review screen's batch cancel button shows "Cancel batch".

   Existing tests stay green.
8. **AC8 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: while a batch runs, opening another document or folder shows a message and leads back to the batch (before, a second batch could mix with the first and write a name in clear, and opening a document left the batch waiting with no way back); a change made in the review while a document is written no longer changes what is written; the review screen's « Annuler le lot » button is translated in English.
9. **AC9 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
10. **AC10 — Gates:**
    - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
    - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
    - **G2:** QA re-runs the AC7 tests, its own #1 and #4 probes and the PO's route probe, checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
    - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
    - **G7:** no headline number changes. CHANGELOG as above.

### Decisions Recorded (Lionel, 2026-10-16)

The PO reviewed the story and replaced the PM's two questions: the PM's draft covered only the File menu's folder route, said the batch "can always be stopped" (false after the home route), left out what « Annuler le lot » deletes, used an "OK" button that no window in the app uses, said « attendez la fin du lot » although the batch waits on the user's own review, and named in English a button that the review screen shows in French. The PO's versions were asked one at a time, word for word, in the orchestrator's decision log. Each answer is the recommendation.

1. **Q1, opening something during a batch: "Refuse while running (Rec.)".** The question: "10.14 Q1: during a batch, what should opening another document or folder do?" The option: "A message says a batch is running, and nothing else happens. Nothing is deleted unless you choose « Annuler le lot », which asks first." Preview: every open route shows a message; its button takes you back to the batch, where it waits; to stop it, « Annuler le lot » (it deletes the files the batch already wrote, and asks first). The other option was "Stop the batch first".
2. **Q2a, the French message: "Approve (Rec.)".** Approved exactly as in AC6. At the first asking, with the text in the option preview, Lionel answered "Show the messages I can't see it"; it was asked again with the full text in the question itself.
3. **Q2b, the English message: "Approve (Rec.)".** Approved exactly as in AC6.

### Integration Points

- `gdpr_pseudonymizer/gui/main_window.py` — the open routes: `_on_open_file` (`:381`, Ctrl+O `:134-136`), `_on_open_folder` (`:391`, Ctrl+Shift+O `:140`), `_open_recent` (`:369`)
- `gdpr_pseudonymizer/gui/screens/home.py` — the batch button (`:79-81`), the drop zone's routes (`:231-286`), the recent list (`:145`)
- `gdpr_pseudonymizer/gui/screens/batch.py` — the reset (`:83-84`, `_reset_selection` `:93`), `_launch_worker` (`:624`), `_on_validation_required` (`:875`), `_do_cancel` (`:863`), the submission guard (`:951`) and submission (`:978`), `review_state` and `store_review_state` (`:987-993`)
- `gdpr_pseudonymizer/gui/workers/batch_worker.py` — its signals (`:365`) carry the run identifier
- `gdpr_pseudonymizer/gui/screens/validation.py` — the kept review (`:427`), the batch cancel button (`:223`), the batch branch (`:986-1000`), `_start_finalization` (`:1032-1065`)
- `gdpr_pseudonymizer/gui/workers/finalization_worker.py` (`:47`)
- `gdpr_pseudonymizer/gui/widgets/confirm_dialog.py` — read only; the message passes its own button label
- `gdpr_pseudonymizer/gui/i18n/fr.ts`, `en.ts` and their `.qm` files — AC6
- `tests/unit/gui/`, `tests/integration/gui/` — AC7; `CHANGELOG.md` — AC8

### Follow-ups Found by the PO (not ACs, 2026-10-16)

- **(a)** « Annuler le lot » deletes the files the batch already wrote, but the mapping rows stored for those documents stay in the database. No name is left in a file.
- **(b)** In English mode, the batch screen's cancel window has an English title and French text, and the review screen's cancel window is all in French. With QA backlog B21.
- **(c)** Not checked by the PO: a batch signal arriving while a single-document review is shown. AC1 stops that route, and AC3 covers it anyway.

### Estimated Effort: 1-1.5 weeks (the real-thread tests of both signal orders and of the routes are the long pole)

---

## Story 10.15: CLI Corrections and Hand-Added Names (Codex release review #2; PO finding)

**Added by Lionel, 2026-10-16 (Codex release review):** "Leaks + new 10.11 bugs (Rec.)" (the question is quoted in Story 10.14). In his preview, to fix before release: "2 CLI: corrected Excel/CSV names stay in clear".

**Extended by Lionel, 2026-10-16 (a new finding of the PO):** "Fix before release (Rec.)". The question he answered: "New leak the PO found, also in v2.2.0: a name you add by hand is replaced at one place only, and its other places stay in clear while the name is stored. Desktop app: only the place you selected. Command line [A]: only the first place found, and in Excel/CSV no place at all. Fix before 2.3.0?" The option he chose: "A name you add by hand is replaced at every place of that name and type. Command line and desktop app." The other option was "Later (backlog)". This story takes the CLI part, because it already changes [A] for spreadsheets; Story 10.17 takes the desktop part.

**As a** CLI user,
**I want** a name I correct ([E]), retype ([T]) or add ([A]) to be replaced at every place it belongs, in text documents and in Excel and CSV cells,
**so that** it is not left in clear while its pseudonym is stored.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-16). Leaks (Codex P0 for #2), in every version tested.
**Change type:** the CLI validation path ([E], [T], [A]) and the spreadsheet writer's matching of names to cells. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. It shares `validation/models.py`, `validation/workflow.py` and `validation/ui.py` with 10.13, and `core/document_processor.py` (and possibly `validation/workflow.py`) with 10.16. Every story edits `CHANGELOG.md`. Before the v2.3.0 release.

### Context

At `main` `fb7917c`:

- **How a spreadsheet goes through the CLI:** each cell is detected on its own; each name carries its cell in `context_label`, with positions inside the cell's text (`core/document_processor.py:1244-1294`, the label at `:1279`). The review shows the cells joined by line breaks (`:1197`). After the review, replacements are grouped by `context_label` and applied cell by cell (`_apply_tabular_replacements`, `:1345-1391`; `ref = entity.context_label or ""`, `:1372`). A replacement with no `context_label` matches no cell and is dropped without a word.
- **The rows are saved before the cells are written:** `_resolve_pseudonyms` (`:710`) saves the run's new rows (`:801`) before `_apply_tabular_replacements` runs (`:1220`). So a dropped replacement leaves a stored row for a name written in clear.
- **[T] loses the cell:** `ValidationSession.change_entity_type` builds the retyped name without `context_label` (`validation/models.py:309-337`, the rebuild at `:327-337`).
- **[E] loses the cell and puts the span in the wrong text:** the correction builds the corrected name without `context_label` (`validation/workflow.py:287-303`) and locates it in the joined review text (`_locate_modified_span`, `:541`, on `session.document_text`), so its positions are not positions inside the cell.
- **`_sent_entity`,** by reading, not probed: it builds a corrected name without `context_label` when it has no `modified_entity` (`validation/models.py:389-404`).
- **QA's reproduction of #2** (the real CLI driven by keys, ".xlsx" and ".csv"; failed at `fb7917c` and at v2.2.0, so pre-existing):
  - **[T]:** "Zorbal Quentrix", detected as ORG and retyped PERSON. Output cells `[['Nom', 'Note'], ['Brune Perrier', 'valide'], ['Zorbal Quentrix', 'signe']]`: the name in clear, while the database holds a row ('Zorbal Quentrix', PERSON) with the pseudonym 'Inaya Paul'.
  - **[E]:** "Zorbal Quentrix signe" detected, corrected to "Zorbal Quentrix". The output cell "Zorbal Quentrix signe le contrat" is in clear; a row is stored for the name.
  - The run reports success both times.
- **[A] adds one place only, and on a spreadsheet none (measured by the PO; v2.2.0 the same):** `_handle_add_entity` (`validation/workflow.py:569-606`) takes the first place found in the review text (`session.document_text.find`, `:588`) and gives it no cell.
  - On ".xlsx" and ".csv", the added name stays in clear in its cell while its row is stored, and the run ends with exit 0 after "Added PERSON entity": output `[['Nom', 'Note'], ['Alexandra Delgado', 'valide'], ['ok', 'contrat avec Zorbal Quentrix']]`, stored row ('Zorbal Quentrix', PERSON, 'Thibault Rego'). On ".txt" the place is replaced (control).
  - A name at 2 places: on ".txt" only the first is replaced (« Signé : Zorbal Quentrix. » stays in clear); on ".xlsx" both stay in clear.
- **The desktop app:** its review keeps `context_label` on corrections (`gui/models/validation_state.py:741`, `:791`); not probed for this story. Its hand-added names are Story 10.17.

### Acceptance Criteria

1. **AC1 — The cell is kept ([E], [T]):** in the CLI, on a spreadsheet, a name corrected with [E], retyped with [T], corrected then retyped, or given a custom pseudonym after a correction keeps its cell. It is replaced in that cell, at every place of its group, and its stored row matches what is written. The same applies to text documents: a correction that partly overlaps another written name has left part of a name in clear since v2.2.0 (Codex review of PR #106, 2026-10-19; Lionel's 10.15 Q4 applied to corrections, see the story).
2. **AC2 — A correction is found inside its cell:** a correction is located in the text of the cell the name came from, not in the joined review text. Where it is not found there, that place keeps its span, as on the text path (`_locate_modified_span`).
3. **AC3 — A name added with [A] is replaced at every place (Lionel, 2026-10-16):** every place of that name and type, that is every whole-word occurrence of the exact text added: in a text document, everywhere in the text; in a spreadsheet, in every cell where it occurs, each place with its cell and its position in the cell. An occurrence inside a longer word is not a place. A place where the detector found the same name with the same type stays with that name's group and its decision, as a decision on a row added by hand acts on that row only in the desktop app (10.10). One row is stored for the name, as today. The SM states how a place that overlaps another name already written is handled; no part of the added name stays in clear there.
4. **AC4 — No silent drop, checked before anything is saved:** before any row is saved (`_resolve_pseudonyms`, `:710`), every replacement of a spreadsheet is checked against the cells. If one matches no cell, the run stops with an error: no output file, no new mapping row and no success message. The error text is user copy (AC6).
5. **AC5 — Tests first, invented names only:** the tests are committed before the fix and drive the real CLI review with keys. Each expected failure is an `assert` on the written file (output text or cells) and the stored rows, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - on ".xlsx" and ".csv": [T]; [E]; [E] then [T]; [C] after [E]; [A] (measured failing);
   - [A] of a name at 2 places, on ".txt" and on ".xlsx" (measured failing);
   - [A] of a name the detector also found at another place with the same type: that place keeps its group's decision;
   - AC4: a replacement that matches no cell stops the run before any row is saved.

   Existing tests stay green.
6. **AC6 — User copy:** the AC4 error text, and any other new visible text, is user copy that Lionel approves, word for word, before the story is done.
7. **AC7 — CHANGELOG:** `[Unreleased]` gets two "Fixed" entries: in the CLI, on Excel and CSV files, a name corrected with [E] or retyped with [T] was left in clear in its cell while its pseudonym was stored (every earlier version), and is now replaced; a name added with [A] was replaced only at the first place found, and in Excel and CSV files at no place (every earlier version), and is now replaced at every place of that name and type.
8. **AC8 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
9. **AC9 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
   - **G2:** QA re-runs the AC5 tests, its own #2 probe and the PO's [A] probe, checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes. CHANGELOG as above.

### Integration Points

- `gdpr_pseudonymizer/validation/models.py` — `change_entity_type` (`:309-337`), `_sent_entity` (`:389-404`)
- `gdpr_pseudonymizer/validation/workflow.py` — [E] (`:287-303`), `_locate_modified_span` (`:541`), [A] (`_handle_add_entity`, `:569-606`)
- `gdpr_pseudonymizer/core/document_processor.py` — `_process_document_tabular` (`:1182-1242`), `_resolve_pseudonyms` (`:710`, the save at `:801`), `_apply_tabular_replacements` (`:1345-1391`)
- `tests/unit/`, `tests/integration/` — AC5; `CHANGELOG.md` — AC7

### Follow-ups Found by the PO (not ACs, 2026-10-16)

- **(a)** By reading, not probed: in the CLI review of a spreadsheet, the context shown around a name is taken from the joined text with positions inside cells (`validation/context_precomputer.py:12`, used at `validation/workflow.py:48`), so it may show the wrong text. A QA look; not a leak.
- **(b)** The CLI shows no review, so [A] cannot be used, when the detector finds no name or only names already stored (since v1.0.0; found by the 10.15 PO). Lionel: "Fix before 2.3.0 (Rec.)" → Story 10.18.

### Estimated Effort: 1-1.5 weeks ([A] at every place, in text and in cells, adds to the cell fixes)

---

## Story 10.16: Custom Pseudonym Fixes (Codex release review #8, #6 and #7)

**Added by Lionel, 2026-10-16 (Codex release review):** "Leaks + new 10.11 bugs (Rec.)" (the question is quoted in Story 10.14). In his preview, to fix before release: "8 lowercase real name accepted as own pseudonym", "6 own first name reused as someone's surname" and "7 false error after a correction". All three are gaps in Story 10.11, whose feature is new in 2.3.0: #8 can leave a real name in clear, #6 lets two people share part of a pseudonym, and #7 refuses a valid document.

**As a** user who sets my own pseudonym for a name,
**I want** it refused when it repeats the real name, whatever its capitals; never shared with another person's generated pseudonym; and applied to the name I set it for,
**so that** my own pseudonym never brings back the real name or merges two people, and a valid document is written.

**Priority:** HIGH — before the v2.3.0 release (Lionel, 2026-10-16). Codex P1.
**Change type:** the shared checks and the generation guard (`core/custom_pseudonym.py`), the desktop review's reach of a custom pseudonym, and the callers of the check in the desktop app, the CLI and finalization. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain, after 10.11 (merged, `b2042c7`). Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. It shares `gui/models/validation_state.py` with 10.13 and 10.17 (and 10.14 if it changes it), `core/document_processor.py` with 10.15, and may share `validation/workflow.py` with 10.13 and 10.15. Every story edits `CHANGELOG.md`. It has no open question, so it can go before 10.14 if needed. Before the v2.3.0 release.

### Context

At `main` `fb7917c`:

- **#8, the real-name check ignores a lowercase name the user reviewed (Codex P1).**
  - **Code:** the document part of the check counts only words with a capital (`core/custom_pseudonym.py:538-540`, Lionel's Q-C); the database part counts only full names already stored (`:541-544`, Q-C2). Nothing compares the custom pseudonym with the name it replaces, or with the other names of the review, when they are written in small letters.
  - **QA's reproduction** (fresh database, « zorbal quentrix signe le contrat. », the name reviewed as PERSON; the CLI and the desktop app): "Xantor Quentrix" is accepted and the output is "Xantor Quentrix signe le contrat.", the real surname kept; "zorbal quentrix" is accepted and the output is "zorbal quentrix signe le contrat.", the real name in clear and stored as its own pseudonym. The desktop app shows no refusal either. Control: with « Zorbal Quentrix » capitalised, "Xantor Quentrix" is refused.
  - **The PM's reading (no new question; the PO found it faithful):** Lionel's Q-C ("Capitalised words", 2026-10-15) is about the document's other words, which the detector may not have found: a common word in small letters must not block a pseudonym ("Grace Vellion" accepted beside « grâce »). Lionel put #8 among the fixes before release (2026-10-16), and that fix needs a lowercase name of the review to count. So: every name in the review list that is not rejected counts whatever its capitals, whether accepted, corrected, added by hand or still to review; the document's other words in small letters still do not. Names still to review are included so that a pseudonym accepted when it is set is never refused at finalization, if the user accepts them later. The cost: a lowercase false detection left to review blocks a pseudonym until the user rejects it.
- **#6, the generation guard lets a generated pseudonym take a custom part in the other role, or with another spelling (Codex P1; new in 10.11, its AC19).**
  - **Code:** `untracked_custom_values` (`core/custom_pseudonym.py:608-647`) leaves out a custom part that the library already tracks for its real word (`:646`), assuming the library protects it. The library keeps first names and last names apart, and compares exact spellings (`pseudonym/library_manager.py:788-797`, `:637-643`).
  - **QA's reproduction** (the library's draw forced, so rare in practice but reachable): custom "Martin Vellion" stored for "Zorbal Quentrix"; a later "Brimel Testar" gets "Dylan Martin", with "Martin" as a last name. Custom "Clement Vellion"; "Brimel Testar" gets "Clément Pereira". Control: "Martin" drawn as a first name is drawn again; and "Alice Martin" or "Clément Xorvan" typed as a custom pseudonym is refused (Q2).
- **#7, a custom pseudonym spreads by detected names, while the check and finalization use current names (Codex P1; new in 10.11, its Q3).**
  - **Code:** `_pseudonym_rows` (`gui/models/validation_state.py:478-497`) compares each row's fixed detected name (`_mapping_name`, `:470-476`; the comparison at `:492`), while `get_custom_pseudonyms` keys by the current name, after corrections and type changes (`_sent_name`, `:499-505`; `:507-517`).
  - **QA's reproduction** (batch review, rows « Zorbal Quentrix » and « M. Zorbal Quentrix »): the first row corrected to « Zorbal » (or retyped ORG), then "Xantor Vellion" set on the second: both rows carry it, so two names share it, ('Zorbal', PERSON) and ('Zorbal Quentrix', PERSON). Finalization refuses the document with "A pseudonym you chose can no longer be used: it, or a part of it, is now used for another name. Nothing was written."; no output file, no row. Not a leak: the document is not written.

### Acceptance Criteria

1. **AC1 — The review's names count whatever their capitals (#8):** a person's custom pseudonym is refused, with the real-name message Lionel approved for 10.11 (Q-A), when one of its runs of whole words (read as Q-C reads them, with Q-I's linking-word rule) equals, capitals and accents ignored, a word or a run of words of the name it replaces, or of another name of the review. When the pseudonym is set, the other names are every name of the review that is not rejected, names still to review included; at finalization, the names sent to the file. An organisation's or a place's pseudonym is compared whole, the same way. The Q-C rule for the document's other words is unchanged: words in small letters still do not count. This holds in the desktop app, the CLI and the finalization check.
2. **AC2 — The generation guard keeps roles and spellings (#6):** a generated pseudonym never takes, for another real name, a beginning or an ending of a person's stored custom pseudonym, whatever role (first or last name) the library gives it, and capitals and accents ignored. The only reuse allowed is the one 10.11 already requires: a part bound to the same real first or last name, in the same role (10.11 AC2, Q-D).
3. **AC3 — A custom pseudonym follows the current name (#7):** in review, a custom pseudonym reaches the rows whose current name (text after corrections, and current type, as `_sent_name` reads them) is the row's own, not the rows with the same detected name. The whole reach is checked before it is applied, so a pseudonym that is accepted is never refused at finalization for a clash inside the same review. 10.11's Q3 and Q-B (every place, like a correction) and Q-E (a later correction removes it) are unchanged.
4. **AC4 — Tests first, invented names only:** the tests are committed before the fix. Each expected failure is an `assert` on the refusal shown, or on the written file and the stored rows, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - #8, in the CLI, the desktop app and finalization: a custom pseudonym equal to the lowercase name; one that repeats its lowercase surname; one that repeats another lowercase name of the review, accepted or still to review; control: a lowercase common word of the document still does not block (Q-C's "Grace Vellion" case);
   - #6, with the library's draw forced: the other role, an accent variant, and the same-role control;
   - #7, through the real batch path: after a correction and after a type change, the written file and the stored rows.

   Existing tests stay green; a 10.11 test changes only if it encodes the old reach, each for a stated reason.
5. **AC5 — No new text:** the refusals use the messages Lionel approved for 10.11 (Q-A). If a new text seems needed, it is user copy for his approval, word for word, before the story is done.
6. **AC6 — CHANGELOG:** the 10.11 entry in `[Unreleased]` (the feature is unreleased) says what changes for the user: a custom pseudonym that repeats a name of the review, whatever its capitals, is refused.
7. **AC7 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
8. **AC8 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
   - **G2:** QA re-runs the AC4 tests and its own #6, #7 and #8 probes, checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes. CHANGELOG as above.

### Integration Points

- `gdpr_pseudonymizer/core/custom_pseudonym.py` — `check_custom_pseudonym` (`:486-546`, the real-name part `:538-544`), `untracked_custom_values` (`:608-647`)
- `gdpr_pseudonymizer/core/document_processor.py` — the CLI check (`:393-413`), the finalization check (`_register_custom_pseudonyms`, `:416`; the check at `:443-459`), the guard's inputs (`:480`, `:874`)
- `gdpr_pseudonymizer/gui/models/validation_state.py` — `_pseudonym_rows` (`:478-497`), `_sent_name` (`:499-505`), the desktop check (`:561`)
- `gdpr_pseudonymizer/validation/workflow.py` — only if the CLI check needs the review's other names
- `tests/unit/`, `tests/integration/` — AC4; `CHANGELOG.md` — AC6

### Estimated Effort: 0.5-1 week

---

## Story 10.17: Desktop Hand-Added Names at Every Place (PO finding)

**Added by Lionel, 2026-10-16 (release blocker):** "Fix before release (Rec.)". The question he answered is quoted in Story 10.15; the option he chose: "A name you add by hand is replaced at every place of that name and type. Command line and desktop app." Found by the PO while reviewing Stories 10.14 to 10.16 (2026-10-16), measured, and the same in v2.2.0. This story takes the desktop part; Story 10.15 takes the CLI part.

**Changed by Lionel, 2026-10-19 (capitals), before development starts:** "A: Fix, capitals only (Rec.)". His option: « Zorbal » also reaches « ZORBAL », never a word in small letters. AC1 now reaches the forms of the name written with capitals (Decisions Recorded). The command line and the corrections are Story 10.19.

**As a** desktop-app user who adds a name the detector missed, by selecting it in the document,
**I want** it replaced at every place of that name and type,
**so that** its other places are not left in clear while the name is stored.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-16). A leak, in every version tested.
**Change type:** desktop review: a row added by hand and its places (`gui/models/validation_state.py`), in single-document validation and in batch review. No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. It shares `gui/models/validation_state.py` with 10.13 and 10.16 (and 10.14 if it changes it), so it comes after them. Story 10.19 also changes that file (`_action_rows`, Lionel's 10.19 Q4: in batch review a correction reaches the same name written with other capitals), so 10.19 merges after 10.17 and is rebased on it. Every story edits `CHANGELOG.md`. Before the v2.3.0 release.

### Context

At `main` `fb7917c`:

- **Code:** adding a name by selection (`gui/screens/validation.py:584` → `GUIValidationState.add_entity`, `gui/models/validation_state.py:593-604`, `_AddEntityCommand`) creates one row at the selected place. `expand_validated_entities` (`:819`) expands a detected row to every occurrence of its variant group, but a row added by hand "normally stays single" (its docstring, `:833-835`). In batch review each place is its own row, and the add creates one.
- **Measured by the PO** (the real single-document and batch paths, detection replaced; the same at v2.2.0): « Vorlan Mestrix valide. Le contrat avec Zorbal Quentrix. Signé : Zorbal Quentrix. », "Zorbal Quentrix" added as PERSON at its first place. Single document: "Denny Berger valide. Le contrat avec Caroline Gonçalo. Signé : Zorbal Quentrix."; batch: "Ashley Andrade valide. Le contrat avec Aziz Richard. Signé : Zorbal Quentrix.". One place stays in clear each time, while the name is stored.
- **Rules that stay:** accepting or rejecting a row added by hand acts on that row only (10.10, Lionel's Q3, 2026-10-14; `CHANGELOG.md:180`). An edit (10.9) and a custom pseudonym (10.11) reach every place of the name and type, except a place rejected on its own, and the highlights show exactly the places that will be pseudonymized (`CHANGELOG.md:169`).
- **Why a story of its own:** Story 10.16 fixes gaps in the custom-pseudonym feature of 10.11, new in 2.3.0, mostly in `core/custom_pseudonym.py`. This defect is older and lies in another code path (the add command, `expand_validated_entities` and the batch rows). Keeping it apart gives each fix its own failing tests, QA gate and Codex review, and 10.16 is not held up by it.

### Acceptance Criteria

1. **AC1 — Every place (Lionel, 2026-10-16), in its forms with capitals (Lionel, 2026-10-19):** a name added by hand is replaced at every place of that name and type, that is every whole-word occurrence, in the document, of the same letters as the text selected, whatever their capitals, except a place written entirely in small letters (unless it is exactly the text selected). Lionel's rule: « Zorbal » also reaches « ZORBAL », never a word in small letters. This wording (the PO's, accepted by the orchestrator on 2026-10-19 without a question, Decisions Recorded) reaches the mixed forms of a name of several words: « Vorlan ZORBAL » for « Vorlan Zorbal », « Marie de Zorbal » for « MARIE DE ZORBAL », « O'Zorbal », « Jean-Zorbal », « LeZorbal »; on the real text measured (the app's 728 names, Lionel's ebook, the 25 main-corpus documents) it adds no place beyond the exact name. **Accents in capitals (Lionel's 10.19 Q3, the same rule as the command line):** a place written entirely in capitals is also a form when its letters are the name's letters once accents are set aside (« HELENE », « HELÈNE » for « Hélène »); still never a word in small letters, and « Helene » (no accent, not in capitals) stays a different name. An occurrence inside a longer word is not a place. A place where the detector found the same name with the same type, whatever the capitals of the text it found, keeps its own row and decision (10.10: a decision on a row added by hand acts on that row only). Every form takes the pseudonym of the name as added; the written file and the stored row match.
2. **AC2 — Shown as it is written:** in single-document validation, the added name's highlights show every place it will be written. In batch review, where each place is its own row, each place gets its own row added by hand. One undo removes the add at every place, and redo restores it. This follows the 10.9 and 10.11 conventions; the SM states the detail, and any real product choice in it goes back to Lionel.
3. **AC3 — Tests first, invented names only:** the tests are committed before the fix and run through the real single-document path and the real batch path (as in 10.10), only detection replaced. Each expected failure is an `assert` on the written file and the stored rows, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - a name added at one of its 2 places (measured failing), single document and batch;
   - a place where the detector found the same name with the same type and the user left it to review: the add does not decide it, and Story 10.13's warning still counts it;
   - the same text inside a longer word: not written;
   - the name in capitals at another place (« ZORBAL » for « Zorbal » added): written with the added name's pseudonym; a word in small letters (« petit » for « Petit » added): never written;
   - a mixed form: « Vorlan ZORBAL » written when « Vorlan Zorbal » is added;
   - a small particle: « Marie de Zorbal » written when « MARIE DE ZORBAL » is added;
   - accents in capitals: « HÉLÈNE » and « HELENE » written when « Hélène » is added; « Helene » not written;
   - one undo of the add: nothing of it is written;
   - **a correction that partly overlaps an accepted name (AC8; the PO's desktop probe):** « Vorlan Zorbal Quentrix a signé. », "Vorlan Zorbal" and "Quentrix" found as PERSON; "Vorlan Zorbal" accepted; "Quentrix" corrected in the editor to « Zorbal Quentrix »; in single-document review and in batch. Today, at `1f35dae` and on the 10.17 prototype, the file reads « <pseudonym> Quentrix a signé. » in both modes, with rows ('Vorlan Zorbal', PERSON) and ('Zorbal Quentrix', PERSON) stored. After the fix: none of "Vorlan", "Zorbal" or "Quentrix" in the written text, which reads « <the pseudonym stored for 'Zorbal Quentrix'> a signé. », and still one row each.

   Existing tests stay green; a 10.9 or 10.10 test changes only if it encodes the old reach, each for a stated reason.
4. **AC4 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: in the desktop app, a name added by hand was replaced only at the place selected (every earlier version), and is now replaced at every place of that name and type, including where it is written in capitals.
5. **AC5 — User copy:** no new text is expected. If one appears, it is user copy that Lionel approves, word for word, before the story is done.
6. **AC6 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
7. **AC7 — Gates:**
   - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
   - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
   - **G2:** QA re-runs the AC3 tests and the PO's desktop probe, checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
   - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
   - **G7:** no headline number changes. CHANGELOG as above.
8. **AC8 — A typed place that partly overlaps another name is widened (Lionel's 10.15 Q4, "A: Name you added", applied to the desktop; the 10.15 Codex P0 ruling, 2026-10-19):** in single-document validation and in batch review, a place the user typed (a name added by hand, AC1, or a name corrected in the editor) that partly overlaps another place being written (a name accepted in the review, a known name included, or another typed place) is widened to cover both, again until it partly overlaps none. "Partly" means neither span holds the other. The whole span takes the typed name's pseudonym, so nothing of either name stays in clear there; the other name keeps its row and its pseudonym at its other places. When two typed places partly overlap each other, the first in the list sent gives the span its pseudonym. A place inside a longer written place stays covered by it, as today, and a rejected or pending name is not written, so it widens nothing. This is the rule 10.15 applies to the command line (its AC14 (d), extended to corrections), so both apps keep one rule. The AC4 entry also says that a correction overlapping another name no longer leaves part of a name in clear (every earlier version), and QA re-runs the PO's overlap probe (G2).

### Decisions Recorded (Lionel and the orchestrator, 2026-10-19)

1. **Capitals in "every place": "A: Fix, capitals only (Rec.)".** The question, word for word, after the PO's measurements (2026-10-19): "Capitals in 'every place' (10.15 command line, 10.17 desktop): a name you add by hand is replaced only where it is written with exactly the capitals you typed. Measured with the real detector: in « Monsieur Zorbal a présenté le budget. Brimel Testar a validé la proposition de ZORBAL. », adding « Zorbal » leaves « ZORBAL » in clear, in a text file and in Excel. In four invented test texts the detector found « Zorbal » at all 5 of its places but « ZORBAL » at only 2 of 8. When every « Zorbal » was already found, the command line even says « 'Zorbal' is already in the review as PERSON at every place: nothing added » while two « ZORBAL » stay in clear. Corrections have an older gap of the same kind: if the review groups « Zorbal » and « ZORBAL » as one name and you correct it to « Zorbal Quentrix », the place « ZORBAL QUENTRIX » is written « [pseudonym] QUENTRIX » (command line, already in v2.2.0; desktop single-document review). (A) Fix before 2.3.0, forms with capitals only (Rec.): « Zorbal » also reaches « ZORBAL », never a word in small letters; none of the app's 728 known names appears in capitals in your ebook (20,000 words) or in the 25 test documents, so this adds no wrong replacement there. (B) Fix before 2.3.0, capitals ignored entirely: it also reaches small-letter words, so adding the surname « Petit » would also replace « petit », 8 times in your ebook. (C) Later (backlog). For A or B: 10.17's rule changes before its development starts, and the command line and the corrections get one small new story after 10.15 merges. Which one?" The options: "A: Fix, capitals only (Rec.)" / "B: Fix, ignore capitals" / "C: Later (backlog)". → AC1, AC3, AC4. The command line ([A]) and the corrections across capitals are Story 10.19.
2. **The wording of the rule (the PO's M1, accepted by the orchestrator on 2026-10-19 without a question):** "the same letters as the text selected, whatever their capitals, except a place written entirely in small letters (unless it is exactly the text selected)". It replaces the PM's three forms (as selected, each word's first letter in capitals, all capitals), which the PO measured to miss « Vorlan ZORBAL » for « Vorlan Zorbal », « Marie de Zorbal » for « MARIE DE ZORBAL », « O'Zorbal », « Jean-Zorbal » and « LeZorbal »; the new wording adds 0 places beyond the exact name on the real text measured. It is the faithful reading of Lionel's choice, so no question was asked.
3. **Overlaps on the desktop, corrections included (the 10.15 Codex P0 ruling, 2026-10-19, no question to Lionel):** a read-only Codex review of 10.15 found that a correction partly overlapping another name being written is dropped by the writer's overlap rule, leaving part of a name in clear with success; the PO reproduced it on the command line and on the desktop (single document and batch, at `1f35dae` and on the 10.17 prototype). The PO ruled, and the orchestrator accepted, that Lionel's 10.15 Q4 ("A: Name you added (Rec.)") covers it, since a correction is a name the user typed at that place (decision log, section "10.15 Codex P0"). The rule, word for word: a place the user typed (added with [A] or corrected with [E]) that partly overlaps another place being written is widened to cover both, repeatedly; the whole span takes the typed name's pseudonym; the other name keeps its row and pseudonym elsewhere; ties: first in the list sent. Lionel is told in the summary so he can object. → AC8, AC3.
4. **Accents dropped in capitals (Lionel's 10.19 Q3, "A: Reach it too (Rec.)", 2026-10-19):** the question, word for word: "10.19 Q3: a name written in capitals can lose its accents (« HELENE » for « Hélène »). Your capitals rule reaches « HÉLÈNE » but not « HELENE », whose letters differ. Measured on the real command line with the fix: adding « Hélène » writes « HÉLÈNE » with its pseudonym and leaves « HELENE » in clear; v2.2.0 and today's code leave both in clear. Reaching it adds no wrong replacement on the text measured: none of the app's 728 names appears in capitals, with or without accents, in your ebook (20,000 words) or in the 25 test documents. How often real documents drop accents in capitals is not measured. (A) Reach it too (Rec.): a place written entirely in capitals is also a form when its letters are the name's once accents are set aside (« HELENE », « HELÈNE »), and « delete-mapping Hélène » also deletes a saved pseudonym of « HELENE »; still never a word in small letters, and « Helene » (no accent, not in capitals) stays a different name. The desktop app (10.17) takes the same rule. (B) Keep the rule as it is: « HELENE » stays in clear, and « delete-mapping Hélène » leaves the saved pseudonym of « HELENE » (measured). Which one?" The options: "A: Reach it too (Rec.)" / "B: Keep the rule". As the question says, the desktop takes the same rule. → AC1, AC3.

### Integration Points

- `gdpr_pseudonymizer/gui/models/validation_state.py` — `add_entity` (`:593-604`), `_AddEntityCommand`, the keys of rows added by hand (`_hand_key_by_id`, `:83-87`), `expand_validated_entities` (`:819`)
- `gdpr_pseudonymizer/gui/screens/validation.py` — the add by selection (`:584`); the highlights, if they need a change
- `tests/unit/gui/`, `tests/integration/gui/` — AC3; `CHANGELOG.md` — AC4

### Estimated Effort: 0.5-1 week

---

## Story 10.18: CLI Question When Nothing Is Left to Review (PO finding)

**Added by Lionel, 2026-10-16 (release blocker):** "Fix before 2.3.0 (Rec.)". The question he answered, word for word as he saw it (asked 2026-10-16T12:07:18Z, header "No-review gap"): "10.15 follow-up, a gap since v1.0. On the command line ('process', and 'batch' one file at a time), a document is written without any review when the detector finds no name in it, or only names already in your database. You never see a review, so you can't add a missed name with [A], and the screen even says 'All entities have existing mappings. Skipping validation.' when nothing was found. A name the detector missed stays in plain text with no chance to catch it. The desktop app does open its review in that case. (The parallel batch never shows a review; that's documented and not part of this.) Proposed fix, as its own small story after 10.15: when nothing is left to review, the command line still asks whether you want to add a name by hand before writing the file. Fix before 2.3.0?" The options: "Fix before 2.3.0 (Rec.)" — "A new small story, built through Codex like the others." / "Later (backlog)" — "2.3.0 ships with this gap.". Found by the 10.15 PO (follow-up (b), 2026-10-16) and re-measured by the PM at `1f35dae`. The PO reviewed the story on 2026-10-16, and Lionel answered its four questions the same day (Decisions Recorded).

**As a** CLI user processing a document in which the detector found no new name,
**I want** to be asked, before the file is written, whether I want to add a name it missed,
**so that** a missed name is not left in plain text without any chance to catch it.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-16). Not a leak of a validated name (nothing is stored for the missed name), but the one CLI path with no human step at all, against Product Constraint 3 ("Mandatory human validation stays").
**Change type:** the CLI validation path of `process` and `batch --workers 1` when nothing is left to review: the question, its lines, the stop when no answer can be read; one docs correction (the `--workers` default). No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. After 10.15, whose code it needs: both change `_run_validation` (`core/document_processor.py`) and `validation/workflow.py`, and 10.18 uses 10.15's [A] (`_handle_add_entity`), the cells 10.15 gives the manual flow, and 10.15's F1 fix (the overlap widening over stored names accepted without review, 10.15 AC14 (d)). After 10.13, which also changes `validation/workflow.py`, `validation/ui.py` and the `run_validation_workflow(…)` call. 10.16 shares the file `core/document_processor.py` and that call's keyword arguments (`:368-370`), but not the skip. Every keyword argument of that call is kept at each rebase. Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. Every story edits `CHANGELOG.md`. Before the v2.3.0 release.

### Context

At `main` `1f35dae` (the code is the `fb7917c` code; #103 changed docs only). Line numbers checked by the PO (2026-10-16).

- **Where the review is skipped:** `_run_validation` (`gdpr_pseudonymizer/core/document_processor.py:307-390`) accepts the names already stored under the same type without review (`:331-359`), with the line "Auto-accepted N known entities (U unique) with existing mappings" (`:351-354`). Only when other names are left does it open the review (`if unknown_entities:` `:362`; `run_validation_workflow`, `:363-372`). Otherwise it prints "All entities have existing mappings. Skipping validation." (`:373-377`, the line at `:376`), and the file is written. The line is also printed when nothing was detected, so it is false then.
- **Both commands, both kinds of file:** `process` (`cli/commands/process.py:211`) and `batch` one file at a time (`--workers 1`, "Sequential mode: Interactive validation enabled", `cli/commands/batch.py:491-493`; the loop `:565-683`, the call at `:602`) go through it, for text documents and for spreadsheets (`_process_document_tabular`, `document_processor.py:1182`, calls `_run_validation` too). In `batch --workers 1`, the progress line stops on « Current: <file name> » before each file is processed (`batch.py:569-576`, `live.stop()` `:599`); a name over 40 characters shows as "..." and its last 37.
- **The desktop app never reaches this skip:** both of its callers pass `skip_validation=True` (`gui/workers/processing_worker.py:145`, `gui/workers/batch_worker.py:274`) and open the desktop review instead, which opens even when nothing is detected (a warning panel, `gui/screens/processing.py:309-311`) and lists stored names still to accept ("Accepter les déjà connues").
- **A prompt that is never reached:** the review handles an empty list with "No entities detected in document." and "Would you like to manually add entities?", then the manual flow (`validation/workflow.py:78-84`). `_manual_entity_addition_flow` (`:609-634`) prints "ℹ️  Manual entity addition mode" once (`:626`), repeats [A] (`_handle_add_entity`) and asks "Add another entity?" (`:631`). `_run_validation` never calls the review with an empty list, so `process` never reaches it.
- **History:** `process` never reached that prompt in any release. In v0.1.0-alpha, `process` had no review at all; Story 2.9 (`cee7349`) wired the review into `process`, and Story 3.4 (`02af996`) added the skip; both first shipped in v1.0.0. So the gap dates from v1.0.0.
- **Re-measured by the PM at `1f35dae`** with the 10.15 PO's probe (P3 and P4, invented names, the real CLI; probe in the orchestrator's analysis folder `r1015/po/probe/`):
  - **Nothing detected:** ".txt" « Le contrat avec Zorbal Quentrix est signé. »: exit 0, success; the screen shows "All entities have existing mappings" and "Skipping validation", no review and no prompt; the file is written with « Zorbal Quentrix » in plain text; no row. The same on ".xlsx" (written `[['Nom'], ['Zorbal Quentrix']]`).
  - **Every detected name already stored:** run 1 stores « Vorlan Mestrix »; run 2 on « Vorlan Mestrix valide. Le contrat avec Zorbal Quentrix. », where the detector finds only « Vorlan Mestrix », prints "Auto-accepted …" and the same line, with no review. Output: "Evann Joly valide. Le contrat avec Zorbal Quentrix.": the missed name in plain text.
- **The stored-name overlap (measured by the PO with the 10.15 prototype and a stand-in for the question):** "Vorlan Zorbal" stored; run 2 on « Vorlan Zorbal Quentrix a signé. », "y", "Zorbal Quentrix" added: « Liam Roy Quentrix a signé. », so "Quentrix" stays in plain text. The manual flow's session holds no stored names, so 10.15's overlap widening (its Q4) cannot see them. This is 10.15's F1 (its AC14 (d) extended to stored names accepted without review), here in 10.18's main case.
- **Without anyone to answer (measured by the PO on Windows; Linux by reading plus one measured call):**
  - Today, a document with nothing new is written with no question (exit 0). A document with names to review waits forever at the review on Windows with no terminal, and fails on Linux (`readchar` calls `termios.tcgetattr`, which raises without a terminal).
  - With a y/n question (Rich `Confirm.ask`, which reads with `input()`): closed or NUL stdin gives "✗ Processing Failed" and "Error: EOFError: EOF when reading a line", exit 1, no file; an empty line gives "Please enter Y or N", then the same error. A piped `n` writes the file as today; a piped `y`, name, type, `n` adds the name, replaces it and stores its row. In a batch, each such file fails the same way and the batch exits 1.
  - On Windows, `sys.stdin.isatty()` is True when stdin is NUL, so a rule based on `isatty` would not see `< NUL` runs.
- **Ctrl+C (measured by the PO):** at the empty-list prompt, "Processing cancelled by user" (`cli/commands/process.py:265`), exit 0, nothing written, with no confirmation. In a batch, "Batch processing cancelled by user" (`batch.py:709`), exit 0; the files already written stay. The review itself first asks "Quit validation? Progress will be lost." (`validation/workflow.py:118-133`).
- **Not in this story:** the parallel `batch` (`--workers 2` to `8`) never shows a review (`skip_validation`, `document_processor.py:323-329`; `batch.py:113-117`); that is parked in Epic 9 with the other no-validation modes (Out of Scope). Names already stored under the same type are still accepted without review.
- **The `--workers` default in the docs is wrong:** `docs/CLI-REFERENCE.md:177` and `docs/CLI-REFERENCE.fr.md:177` give `--workers` a default of 1 ("Use 1 for interactive validation"), but the default is 4 (`cli/config.py:55`; `batch --help`, "Parallel processing with 4 workers (default)", `batch.py:400`). So a plain `batch` runs in parallel with no review, while the docs suggest it reviews.
- **10.15's [A] rules** (its story, AC14; Lionel's 10.15 Q3 "Hyphen joins" and Q4 "Name you added", 2026-10-16): a name added with [A] is replaced at every place of that name and type, where a place is a whole-word occurrence of the exact text and a hyphen joins words ("Saint-Zorbal" holds no place of "Zorbal"); a place the detector already found keeps its own decision; where the added name overlaps a name already written, the whole span gets the added name's pseudonym. With 10.15's F1 fix, "a name already written" includes a stored name accepted without review.

### Acceptance Criteria

1. **AC1 — The question, only when nothing is left to review (Q1, Q2):** in `process` and `batch --workers 1`, on a text document or a spreadsheet where the detector found no name, or found only names already stored under the same type, the CLI shows the matching line and then asks the question (AC6), before the file is written. It never asks after a review that opened (Q2). With "y": « ℹ️  Manual entity addition mode », then [A] with 10.15's rules (every place of that name and type, a hyphen joins words, places already found not added, and the Q4 overlap rule, which here covers the stored names accepted without review, as 10.15's F1 fix makes it), and « Add another entity? [y/n] » after each name until the answer is n; the file is then written with every name added, and their rows are stored. With "n", the file is written as today. A `y` or an `n` must be typed; there is no default.
2. **AC2 — The false line is replaced:** "All entities have existing mappings. Skipping validation." is no longer shown. Nothing detected and every name already stored each get their own line (AC6).
3. **AC3 — `batch` one file at a time (Q3):** the question is asked for each file with nothing left to review; the « Current: <file name> » line above it shows which file it is.
4. **AC4 — When no answer can be read (Q4):** when the question, or a prompt of the manual flow, reads the end of input (closed stdin, `< NUL`, or a pipe that runs out), nothing is written for that document and no row is stored for it; the screen shows « ✗ Processing Failed » followed by the approved line (AC6), and the run ends with an error. The rule keys on reading no answer, never on `isatty()`, which is True on Windows when stdin is NUL. In `batch --workers 1`, each such file fails the same way, is listed as failed, and the batch goes on to the next file, as for any failed file. Answers piped in still work. There is no switch to skip the question (Product Constraint 3: "no `--no-validate`").
5. **AC5 — Ctrl+C at the question or while adding names:** it cancels at once, with no confirmation, as the existing empty-list path does: « Processing cancelled by user » for `process`, « Batch processing cancelled by user » for `batch`. Nothing is written for that document and no row is stored for the names being added; in a batch, the files already written stay. This is the PM's choice: at that point no review decision can be lost, and it needs no new text.
6. **AC6 — The approved texts (Lionel, 2026-10-16, Q1 and Q4, word for word; the command line is in English):**
   - **New:** « ℹ️  No names were found in this document. » / « ℹ️  No new names to review: every name found is already in your mapping database. » / « Add a name the detector missed before the file is written? [y/n] » (no default)
   - **Reused unchanged:** « ℹ️  Manual entity addition mode », 'Entity text', 'Entity type (PERSON/LOCATION/ORG)', « Add another entity? [y/n] ».
   - **When no answer can be read,** after « ✗ Processing Failed »: 'Error: NoAnswerError: No answer could be read, so this document was not processed: the command line must ask whether to add a name the detector missed. Run it in a terminal to answer. No output was written for this file.'
   - They replace « All entities have existing mappings. Skipping validation. ».
7. **AC7 — What stays as it is:** names already stored under the same type are still accepted without review, and the "Auto-accepted …" line stays; the review, when names are left, is unchanged (its Ctrl+C confirmation included); the parallel batch and the desktop app's calls (`skip_validation=True`) are unchanged and never ask.
8. **AC8 — Docs, a false fact corrected:** in `docs/CLI-REFERENCE.md:177` and `docs/CLI-REFERENCE.fr.md:177`, the `--workers` row gives the real default, 4 (`cli/config.py:55`), and says that only `--workers 1` shows the review. This corrects a fact and makes no product choice; the new rows are shown in the PR.
9. **AC9 — Tests first, invented names only:** The BMAD dev agent (Claude) writes the tests and commits them before the fix; they drive the real CLI (`process`, and `batch --workers 1` on a folder) with keys or piped input, on ".txt" and ".xlsx". Each expected failure is an `assert` on the written file, the stored rows or the lines shown, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - nothing detected, "y", a name added that stands at 2 places: the written file holds its pseudonym at both places and no part of the name, and its row is stored;
   - every name already stored, "y", the missed name added: the same;
   - **the stored-name overlap:** "Vorlan Zorbal" stored, « Vorlan Zorbal Quentrix a signé. », "y", "Zorbal Quentrix" added: the written file holds no part of either name (never « Liam Roy Quentrix a signé. »), on ".txt" and ".xlsx";
   - "n": the file is written as today, no row is stored for the missed name, the new line is shown and the false line is not;
   - a name inside a hyphenated compound ("Saint-Zorbal") is not a place;
   - a review that opened, with every name decided: no question (Q2);
   - `batch --workers 1` with two such files: the question for each (Q3);
   - **no answer (Q4):** closed stdin and an input that runs out: « ✗ Processing Failed » and the approved line, no output file, no row; in a batch, each such file fails and the batch goes on; a piped "n" still writes the file;
   - **Ctrl+C** at the question, and while adding a name: cancelled, nothing written for that document; in a batch, the file written before stays;
   - **a guard:** the `skip_validation` paths (the desktop's `processing_worker.py:145` and `batch_worker.py:274`, and the parallel batch) never ask and never read input.

   Existing tests stay green; a test that encodes the skipped review changes, each for a stated reason.
10. **AC10 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: on the command line (`process`, and `batch` one file at a time), a document in which no new name was found was written without any review since v1.0.0, so a name the detector missed could not be added, and the screen said "All entities have existing mappings" even when nothing was found; the command line now asks whether to add a name before writing the file. It also says what changes for scripts: a run with no input now stops for such a document, writes nothing for it and shows the NoAnswerError line; piping the answer still works (`n` writes the file as before; `y` followed by the names adds them). And the `--workers` default in `CLI-REFERENCE` is corrected.
11. **AC11 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
12. **AC12 — Gates:**
    - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
    - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
    - **G2:** QA re-runs the AC9 tests, the 10.15 PO's P3 and P4 probes and the 10.18 PO's no-answer and overlap measurements, checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
    - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
    - **G7:** no headline number changes. CHANGELOG and docs as above.

### Decisions Recorded (Lionel, 2026-10-16)

The PO reviewed the story first and rewrote the PM's questions: the PM's Q2 said "In the review you can already add a name with [A] at any time", which is false ([A] works only while a name is on screen); the PM's Q3 offered "Never in batch", which would reverse Lionel's answer, and an unclear "once per batch"; and the PO added Q4 (nobody can answer). The PO's versions were asked one at a time, in this order, word for word in the orchestrator's decision log. Each answer is the recommendation.

1. **Q2, after a review where every name was decided: "A: No (Rec.)".** The question, word for word: "10.18 Q2: when the review opens and you decide every name in it, should the command line also ask « Add a name the detector missed before the file is written? » before writing? In the review, [A] works while a name is on screen; once you decide the last name, the review ends, and answering 'n' at « Ready to process document with validated entities? » starts the review again from the beginning and drops your decisions. (A) No (Rec.): the review already lets you add a name on any name it shows; a second question would cost one more answer on every document. (B) Yes, every time." → AC1.
2. **Q3, `batch` one file at a time: "A: Each file (Rec.)".** The question, word for word: "10.18 Q3: in 'batch' one file at a time, a folder may hold many documents with nothing left to review. (A) Ask for each such file (Rec.): each document can hide its own missed name; the line « Current: <file name> » above the question shows which file it is. (B) Ask once: at the first such file; if you answer n, the other such files are written without asking. Which one?" → AC3.
3. **Q4, nobody can answer: "A: Stop, clear line (Rec.)".** The question, word for word: "10.18 Q4: what if the command runs where nobody can answer, for example a script with no input? Today a document with names to review already needs someone at the keyboard (without one, it waits forever on Windows and fails on Linux); only documents with nothing new go through, unreviewed. With the new question, such a run now stops at once with '✗ Processing Failed' and 'Error: EOFError: EOF when reading a line', and writes nothing for that document; answers piped in (y or n) still work. (A) Stop, with a clear line instead (Rec.): 'Error: NoAnswerError: No answer could be read, so this document was not processed: the command line must ask whether to add a name the detector missed. Run it in a terminal to answer. No output was written for this file.' (B) When no answer can be read, write the file as today without asking; that keeps a path with no review. A switch to skip the question is left out: the epic's rule 3 forbids one. Which one?" The approved line, exactly: 'Error: NoAnswerError: No answer could be read, so this document was not processed: the command line must ask whether to add a name the detector missed. Run it in a terminal to answer. No output was written for this file.' → AC4, AC6.
4. **Q1, the texts: "Approve (Rec.)".** The question, word for word: "10.18 Q1, the command-line texts. When the detector found no name: « ℹ️  No names were found in this document. » When every name it found is already stored, after the existing « Auto-accepted … » line: « ℹ️  No new names to review: every name found is already in your mapping database. » Then, in both cases: « Add a name the detector missed before the file is written? [y/n] » (y or n must be typed). With y: « ℹ️  Manual entity addition mode », then the [A] prompts as today ('Entity text', 'Entity type (PERSON/LOCATION/ORG)'), then « Add another entity? [y/n] » after each name; the last three are texts the command line already uses. These replace « All entities have existing mappings. Skipping validation. », which was false when nothing was found. Approve these texts?" The approved texts, exactly: « ℹ️  No names were found in this document. » / « ℹ️  No new names to review: every name found is already in your mapping database. » / « Add a name the detector missed before the file is written? [y/n] » (no default); reused unchanged: « ℹ️  Manual entity addition mode », 'Entity text', 'Entity type (PERSON/LOCATION/ORG)', « Add another entity? [y/n] ». → AC6.

### Integration Points

- `gdpr_pseudonymizer/core/document_processor.py` — `_run_validation` (`:307-390`; the skip `:373-377`), called for text documents and spreadsheets (`_process_document_tabular`, `:1182`)
- `gdpr_pseudonymizer/validation/workflow.py` — the empty-list prompt (`:78-84`), `_manual_entity_addition_flow` (`:609-634`), [A] (`_handle_add_entity`, as 10.15 leaves it), the review's Ctrl+C (`:118-133`, unchanged)
- `gdpr_pseudonymizer/validation/ui.py` — `display_info_message` (`:478`), `get_confirmation` (`:114`)
- `gdpr_pseudonymizer/exceptions.py` — the error class the approved line names (`NoAnswerError`)
- `gdpr_pseudonymizer/cli/commands/process.py` (`:211`, cancel `:265`), `cli/commands/batch.py` (sequential loop `:565-683`, cancel `:709`) — the failed and cancelled paths, read only unless AC4 or AC5 needs a change there
- `docs/CLI-REFERENCE.md`, `docs/CLI-REFERENCE.fr.md` (`:177`) — AC8
- `tests/unit/`, `tests/integration/` — AC9; `CHANGELOG.md` — AC10

### Follow-ups Found by the PO (not ACs, 2026-10-16)

- **(a)** With `--entity-types`, « ℹ️  No names were found in this document. » also shows when names of other types were found and filtered out. The SM may propose a variant ("No names of the selected types …") as new user copy for Lionel, or leave the approved text.
- **(b)** 10.15's approved line « 'Zorbal Quentrix' is already in the review as PERSON at every place: nothing added » can appear in this flow (the same name added twice) although no review was shown. The SM says whether it reads acceptably here or asks Lionel for a variant.
- **(c) Backlog (not changed by 10.18):** "n" at « Ready to process document with validated entities? » restarts the review and drops every decision (10.13 follow-up (a)); and without a terminal, today's review waits forever on Windows and fails on Linux.

### Estimated Effort: 0.5-1 week (the no-answer stop, Ctrl+C and the overlap case add tests to the question itself)

---

## Story 10.19: Capitals in Hand-Added Names and Corrections (PO finding)

**Added by Lionel, 2026-10-19 (release blocker):** "A: Fix, capitals only (Rec.)". His option: « Zorbal » also reaches « ZORBAL », never a word in small letters. The question he answered, word for word, after the PO's measurements (QA's finding on 10.15, PR #106, measured by the PO on 2026-10-19): "Capitals in 'every place' (10.15 command line, 10.17 desktop): a name you add by hand is replaced only where it is written with exactly the capitals you typed. Measured with the real detector: in « Monsieur Zorbal a présenté le budget. Brimel Testar a validé la proposition de ZORBAL. », adding « Zorbal » leaves « ZORBAL » in clear, in a text file and in Excel. In four invented test texts the detector found « Zorbal » at all 5 of its places but « ZORBAL » at only 2 of 8. When every « Zorbal » was already found, the command line even says « 'Zorbal' is already in the review as PERSON at every place: nothing added » while two « ZORBAL » stay in clear. Corrections have an older gap of the same kind: if the review groups « Zorbal » and « ZORBAL » as one name and you correct it to « Zorbal Quentrix », the place « ZORBAL QUENTRIX » is written « [pseudonym] QUENTRIX » (command line, already in v2.2.0; desktop single-document review). (A) Fix before 2.3.0, forms with capitals only (Rec.): « Zorbal » also reaches « ZORBAL », never a word in small letters; none of the app's 728 known names appears in capitals in your ebook (20,000 words) or in the 25 test documents, so this adds no wrong replacement there. (B) Fix before 2.3.0, capitals ignored entirely: it also reaches small-letter words, so adding the surname « Petit » would also replace « petit », 8 times in your ebook. (C) Later (backlog). For A or B: 10.17's rule changes before its development starts, and the command line and the corrections get one small new story after 10.15 merges. Which one?" The options: "A: Fix, capitals only (Rec.)" / "B: Fix, ignore capitals" / "C: Later (backlog)". As the question says, 10.17's rule changed before its development started (Story 10.17, AC1); this story is the "one small new story after 10.15 merges" for the command line and the corrections. Lionel's answer to its Q1 (2026-10-19, "B: Erasure only, in 10.19 (Rec.)") adds the erasure across capitals (AC4), and the rule takes the PO's wording, accepted by the orchestrator without a question (Decisions Recorded). On 2026-10-19 Lionel also approved the `delete-mapping` texts (Q2, AC8), extended the rule to capitals without accents (Q3, "A: Reach it too (Rec.)", AC1, AC4, AC5; the desktop, 10.17, takes the same rule), and extended corrections in desktop batch review to the rows written with other capitals (Q4, "A: Reach it too (Rec.)", AC3), which the PM placed in this story (Ordering).

**As a** user who adds a name by hand or corrects a name in the review,
**I want** the name also replaced where it is written in capitals, and an erasure by name to remove every row whose name differs from it only in capitals,
**so that** « ZORBAL » does not stay in clear when I added or corrected « Zorbal », and erasing « Zorbal » leaves no « ZORBAL » row.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-19). A leak: a name the user added or corrected stays in clear where it is written in capitals.
**Change type:** the places of a name added with [A] in the CLI (10.15's `places_of` and `is_listed_place`), and the shared function that locates a correction (`ValidationWorkflow._locate_modified_span`), used by the CLI's [E] and by the desktop's single-document review; the reach of a correction in desktop batch review (`gui/models/validation_state.py`, `_action_rows`, Q4); `delete-mapping` by name (Q1, Q3) and its screen line and reference paragraph (Q2). No detection change, so G1, G3 and G5 are N/A. No file under `gdpr_pseudonymizer/nlp/`, `gdpr_pseudonymizer/resources/`, `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. It starts after 10.15, merged as `90a1646` (PR #106), because it changes 10.15's `places_of` and `is_listed_place`. It merges after 10.17 and is rebased on it, because Q4 changes `_action_rows` in `gui/models/validation_state.py`, which 10.17 also changes (10.16 changes that file too, in other functions). Q4 is part of this story rather than a story of its own (the PM's choice, 2026-10-19): it is the batch-review half of this story's correction fix (b), it uses the same `is_form` rule, and one QA gate and one Codex review then cover the whole correction rule; the cost is this later merge. It shares the correction locating with 10.17: `_locate_modified_span` is called from `gui/models/validation_state.py` (`:378`, `:443`, `:800`) and `gui/screens/validation.py` (`:702`), and 10.17 changes `validation_state.py`. 10.16 also changes `validation_state.py`, but not the functions that call `_locate_modified_span`. 10.17 applies the same capitals rule to the desktop's places: whichever of 10.17 and 10.19 merges second reuses the first one's code for it, so the two apps keep one rule. It shares `validation/models.py` with 10.13 and 10.15, `validation/workflow.py` with 10.13, 10.15 and 10.18, and the `delete-mapping` code (`cli/commands/delete_mapping.py`, `data/repositories/mapping_repository.py`) with 10.12, now merged. Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. Every story edits `CHANGELOG.md`. Before the v2.3.0 release.

### Context

At `main` `e35ccc5`, and on 10.15's PR #106 (head `2143813`, QA gate at `cc3c79c`). Measured by the PO on 2026-10-19 (notes `rgpd-analysis/r1015/po/po_caps_1015_1017_notes.md`; probes in `r1015/po/caps/` and `r1017/po/probe/test_po_caps_desktop.py`; invented names only).

- **The real detector misses most capital forms.** On four invented French texts it found the title form « Zorbal » at all 5 of its places, and the capital form « ZORBAL » at only 2 of 8 (for example « Présents : Vorlan ZORBAL, … la proposition de ZORBAL. »: both missed).
- **(a) [A] reaches only the exact text typed.** 10.15's `places_of` (`validation/models.py:274`, PR #106) matches the exact text, so adding « Zorbal » with [A] leaves « ZORBAL » in clear, on ".txt" and ".xlsx":
  - « Présents : Vorlan ZORBAL, … Monsieur <pseudonym> a présenté le budget. … la proposition de ZORBAL. »: "ZORBAL" twice in clear;
  - when every « Zorbal » was already found, the CLI shows the approved 10.15 line « ℹ️ 'Zorbal' is already in the review as PERSON at every place: nothing added » (`validation/workflow.py:42`, PR #106) while two « ZORBAL » stay in clear. `is_listed_place` (`validation/models.py:306`, PR #106) compares the exact text, so a capital place found by the detector is not recognised as found either.
  - v2.2.0 is the same or worse: it replaced one place only, with the exact capitals (`str.find`).
- **(b) An older correction leak across capitals.** The review groups « Zorbal » and « ZORBAL » as one name, because `_is_person_variant` compares person names in small letters (`nlp/entity_grouping.py:133`, `:139-140`). A correction then looks for the new text with its exact capitals (`ValidationWorkflow._locate_modified_span`, `validation/workflow.py:550-578`, `str.find` at `:571`, `:575`); at a capital place it does not find it and keeps the old span. Measured, detection replaced, « Zorbal Quentrix a signé. Copie : ZORBAL QUENTRIX. », one group corrected to « Zorbal Quentrix »:
  - CLI on PR #106: « Maria Gonçalves a signé. Copie : Maria Gonçalves QUENTRIX. »; v2.2.0: the same kind of output;
  - desktop single-document review, at `1f35dae` and on the 10.17 prototype: « Julien Silva a signé. Copie : Julien Silva QUENTRIX. »: the desktop calls the same function (`gui/models/validation_state.py:378`, `:443`, `:800`; `gui/screens/validation.py:702`);
  - desktop batch: each place is its own row, and a correction reaches the rows with the same name key (10.10, `_action_rows`, `gui/models/validation_state.py:315`; `_name_key` `:302`), which keeps capitals. Measured by the PO (Q4): « Zorbal » found in « Zorbal Quentrix a signé. » and « ZORBAL » in « Signé : ZORBAL QUENTRIX. »; the « Zorbal » row corrected to « Zorbal Quentrix »: the « ZORBAL » row does not take it and stays to review; accepted as it is, the file reads « … Signé : [pseudonym] QUENTRIX. », today and with this story's fix before Q4.

  "QUENTRIX" stays in clear. So 10.9's and 10.10's "every place" corrections reach a grouped capital place but write over its old span.
- **(c) Two pseudonyms for one person, and a partial erasure (measured by the PO with the real CLI, PR #106 and v2.2.0 the same).** A stored name is keyed by its exact text (`core/mapping_key.py:17-35` keeps capitals; `_resolve_pseudonyms` gives one pseudonym per key and type, `core/document_processor.py:255`, `:712`).
  - With the real detector, « Entretien avec Quentrel Zorbal. Quentrel ZORBAL explique son parcours. … »: the review shows one name, accepted once, but two rows are stored, ('Quentrel ZORBAL' → 'Évangéline Caron') and ('Quentrel Zorbal' → 'Évangéline Hamel'), and the output reads « Entretien avec Évangéline Hamel. Évangéline Caron explique son parcours. … ». The same happens when the detector found « Zorbal » and « ZORBAL » is added by hand.
  - Erasure: `delete-mapping Zorbal --force` deletes only the ('Zorbal') row and prints « The pseudonym 'Christian Henriques' is now permanently anonymous. », while ('ZORBAL' → 'Astrid Daniel') stays. `delete-mapping` finds and deletes rows by the exact name (`cli/commands/delete_mapping.py:129`, `:159`; `find_all_by_full_name`, `data/repositories/mapping_repository.py:205`, `_query_by_full_name` `:216`, `delete_entities_by_full_name` `:443`), an equality on the encrypted name. The search step of the documented erasure workflow (`docs/CLI-REFERENCE.md:633-638`), `list-entities --search Zorbal`, lists both rows, since its search ignores capitals.
  - Nothing stays in clear in the written files.
- **Lionel's rule and the text it was weighed on:** the app's name list (`resources/french_names.json`, 728 names) holds ordinary French words. In Lionel's ebook (20,157 words), 10 of those names appear as small-letter words 22 times (« petit » ×8), but none appears in all capitals; the 25 main-corpus documents write no name in capitals. So forms with capitals add no wrong replacement on the text measured, while ignoring capitals entirely would (adding « Petit » would replace « petit »).
- **Why the rule reads "the same letters, whatever their capitals" (the PO's M1):** the PM's first wording listed three forms (as typed, each word's first letter in capitals, all capitals). The PO measured that it misses « Vorlan ZORBAL » for « Vorlan Zorbal », « Marie de Zorbal » for « MARIE DE ZORBAL », « O'Zorbal », « Jean-Zorbal » and « LeZorbal », and that the new wording adds 0 places beyond the exact name on the real text (the app's 728 names, Lionel's ebook, the 25 main-corpus documents).
- **Accents dropped in capitals (measured by the PO, Q3):** with this story's fix and Lionel's first rule, adding « Hélène » writes « HÉLÈNE » with its pseudonym and leaves « HELENE » in clear; v2.2.0 and today's code leave both in clear; `delete-mapping Hélène` leaves the saved pseudonym of « HELENE ». Reaching it adds no wrong replacement on the text measured: none of the app's 728 names appears in capitals, with or without accents, in Lionel's ebook or in the 25 main-corpus documents.
- **`delete-mapping --force` (the PO's S1):** with `--force` no confirmation screen is shown (`cli/commands/delete_mapping.py:143-145`); the deleted names are named only in the success lines (`:200-216`). The screen today says « You are about to delete the following N entity mappings (one per type of this name): » (`_display_confirmation`, `:293-312`), and the reference says "one row each" (`docs/CLI-REFERENCE.md:470`, `docs/CLI-REFERENCE.fr.md:470`).
- **Not measured:** how often real documents write names in capitals, or drop accents in capitals.

### Acceptance Criteria

1. **AC1 — The capitals rule (Lionel, 2026-10-19):** a form of a text is any whole-word occurrence of the same letters as the text selected, whatever their capitals, except a place written entirely in small letters (unless it is exactly the text selected). In the CLI, "the text selected" is the text typed with [A] or [E]. Lionel's rule: « Zorbal » also reaches « ZORBAL », never a word in small letters. **Accents in capitals (Lionel's Q3):** a place written entirely in capitals is also a form when its letters are the name's letters once accents are set aside (« HELENE », « HELÈNE » for « Hélène »); still never a word in small letters, and « Helene » (no accent, not in capitals) stays a different name. So « ZORBAL », « Vorlan ZORBAL » for « Vorlan Zorbal », « Marie de Zorbal » for « MARIE DE ZORBAL », « ZorBAL », « HÉLÈNE » and « HELENE » for « Hélène » are forms, and « petit » is never a form of « Petit ». Words are whole words as in 10.15 (a hyphen joins words). One rule serves the CLI here and the desktop in 10.17.
2. **AC2 — [A] reaches every form (a):** in the CLI, a name added with [A] is replaced at every form of it (AC1), in a text document and in every cell of a spreadsheet. Each place carries the text as added, so every form takes the added name's pseudonym and one row is stored. A place the detector found with the same span, type and cell, whatever the capitals of the text it found, is "already in the review" (`is_listed_place`) and keeps its own decision. So the approved line « … at every place: nothing added » appears only when no form is left unfound, which makes it true again.
3. **AC3 — A correction is found in its forms (b):** `_locate_modified_span` looks for the corrected text in any of its forms (AC1) around each place, so a grouped capital place (« ZORBAL QUENTRIX ») is covered whole by the correction (« Zorbal Quentrix »), and no part of it stays in clear. This holds for the CLI's [E] and for the desktop's single-document review, which call the same function. The corrected name keeps one pseudonym and one row. Where no form is found, the place keeps its span, as today. **In desktop batch review (Lionel's Q4),** where each place is its own row, a correction also reaches the rows of the same name and type written with other capitals, and without accents in capitals (AC1), except a row the user rejected on its own, and never a row written entirely in small letters: `_action_rows` matches `_name_key` by `is_form`, same type. This lifts the story's rule that desktop batch rows do not change.
4. **AC4 — Erasure across capitals (c), Lionel's Q1 and Q3:** `delete-mapping` with a name also removes the rows whose name differs from it only in capitals, and the rows written entirely in capitals whose letters are the name's once accents are set aside (`delete-mapping Hélène` also deletes the saved pseudonym of « HELENE »), listed with the others before the user confirms. With `--force`, no screen is shown and the rows are named only in the success lines, as today (the PO's S1). Each removed row gets its own erasure entry, as 10.12 writes them (no name). One pseudonym per spelling stays for a later story (Follow-ups).
5. **AC5 — Accents in capitals (Lionel's Q3):** « HELENE » and « HELÈNE » are forms of « Hélène » (AC1) for [A], for corrections and for `delete-mapping`; « Helene » is not. The desktop (10.17) takes the same rule.
6. **AC6 — Tests first, invented names only:** the BMAD dev agent writes the tests and commits them before the fix; they drive the real CLI with keys on ".txt" and ".xlsx", and the real desktop single-document and batch paths for AC3, detection replaced. Each expected failure is an `assert` on the written file, the stored rows or the line shown, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - [A] « Zorbal » on a text with « ZORBAL » at 2 places: both written with the added name's pseudonym, one row ('Zorbal', PERSON);
   - every « Zorbal » found, « ZORBAL » not: the approved "nothing added" line is not shown, and the capital places are added;
   - a capital place the detector found: it keeps its own decision;
   - [A] « Petit » on a text with « petit » and « PETIT »: « petit » never written, « PETIT » written;
   - a mixed form: [A] « Vorlan Zorbal » on a text with « Vorlan ZORBAL »: written with the added name's pseudonym;
   - a small particle: [A] « MARIE DE ZORBAL » on a text with « Marie de Zorbal »: written;
   - « SAINT-ZORBAL » for « Zorbal »: not a place (the hyphen joins);
   - the correction case of Context (b), CLI and desktop single document: no part of « ZORBAL QUENTRIX » in clear, one row;
   - **erasure (AC4):** rows ('Zorbal', PERSON) and ('ZORBAL', PERSON) stored; `delete-mapping Zorbal`: both are listed before the confirmation, both are deleted, each with its erasure entry; a row whose letters differ (« Zorbalix ») stays;
   - **accents (Q3):** [A] « Hélène » on a text with « HÉLÈNE », « HELENE » and « Helene »: the first two written with the added name's pseudonym, « Helene » not; `delete-mapping Hélène` with saved pseudonyms of « Hélène » and « HELENE »: both listed and deleted;
   - **desktop batch (Q4):** the Context (b) case: correcting the « Zorbal » row to « Zorbal Quentrix » also corrects the « ZORBAL » row, and no part of « ZORBAL QUENTRIX » is in clear; a « ZORBAL » row rejected on its own stays rejected; a row written « zorbal » is not reached;
   - **the screen (Q2):** with two saved pseudonyms of the name, the confirmation screen shows the approved line with the count; with `--force`, the success lines name every deleted saved pseudonym.

   Existing tests stay green; a 10.15 test changes only if it encodes the exact-capitals rule, each for a stated reason.
7. **AC7 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: a name added with [A] or corrected in the review is now also replaced where it is written in capitals (« ZORBAL » for « Zorbal »), never in a word in small letters, and in capitals without accents (« HELENE » for « Hélène »); in desktop batch review a correction also reaches the same name written with other capitals; the correction case was already in v2.2.0. And `delete-mapping` with a name now also deletes the saved pseudonyms of the same name written with other capitals or without accents in capitals, which earlier versions kept. The entry says "saved pseudonyms", never "rows" (Lionel's Q2 remark). The 10.15 entry's wording is aligned if it says "the exact text".
8. **AC8 — User copy (Lionel's Q2, approved word for word; the outer « » are quote marks):**
   - **The `delete-mapping` screen, for several saved pseudonyms** (the number is the count), replacing « You are about to delete the following N entity mappings (one per type of this name): »: « You are about to delete the following 2 saved pseudonyms (all of this name, whatever its type or its capitals): ». The one-row line is unchanged.
   - **`docs/CLI-REFERENCE.md`, replacing the paragraph at `:470`:** « The same name can have several saved pseudonyms: one for each type it was saved under, and one for each way it was written with capitals ("Marie Dupont", "MARIE DUPONT"). Deleting by name lists all of them, then deletes them all (each deletion is logged as an ERASURE entry); `--id` deletes only one and tells you which others remain for the same name written exactly the same way. »
   - **`docs/CLI-REFERENCE.fr.md`, replacing the paragraph at `:470`:** « Un même nom peut avoir plusieurs pseudonymes enregistrés : un pour chaque type sous lequel il a été enregistré, et un pour chaque façon dont il a été écrit avec des majuscules (« Marie Dupont », « MARIE DUPONT »). La suppression par nom les affiche tous, puis les supprime tous (chaque suppression est consignée par une entrée ERASURE) ; `--id` n'en supprime qu'un et indique ceux qui restent pour le même nom écrit exactement de la même façon. »
   - Any other new visible text is user copy that Lionel approves, word for word, before the story is done. User texts say "saved pseudonym", never "row", "ligne" or "mapping" (Lionel's Q2 remark).
9. **AC9 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
10. **AC10 — Gates:**
    - **G1, G3 and G5 are N/A:** there is no detection change. The PR states this explicitly. If any file the accuracy suite loads is touched, one regular `accuracy.yaml` run on the branch shows the 16 lines identical to `38212303870`, cited by ID.
    - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
    - **G2:** QA re-runs the AC6 tests and the PO's capitals probes, checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
    - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
    - **G7:** no headline number changes. CHANGELOG as above.

### Decisions Recorded (Lionel and the orchestrator, 2026-10-19)

1. **Q1, one person, two pseudonyms, and the erasure: "B: Erasure only, in 10.19 (Rec.)".** The question, word for word, as the PO measured and rewrote it: "10.19 Q1: the app keeps one pseudonym per exact spelling of a name, capitals included, so « Zorbal » and « ZORBAL » are two different names to it. Measured with the real detector: in « Entretien avec Quentrel Zorbal. Quentrel ZORBAL explique son parcours. », the review shows one name and you accept it once, but two rows are stored and the output reads « Entretien avec Évangéline Hamel. Évangéline Caron explique son parcours. »: one person, two pseudonyms. The same happens when the detector found « Zorbal » and you add « ZORBAL » by hand. Erasure: « delete-mapping Zorbal » removes only the « Zorbal » row and says its pseudonym is now permanently anonymous, while the « ZORBAL » row and its pseudonym stay; the search step of the documented erasure workflow (« list-entities --search Zorbal ») does list both rows. The two pseudonyms and the partial erasure are already so in v2.2.0; neither leaves anything in clear in the written files. (A) Later, all of it, as its own story after 2.3.0. (B) Before 2.3.0, in 10.19, the erasure only (Rec.): « delete-mapping » with a name also removes the rows whose name differs from it only in capitals, listed with the others before you confirm; one pseudonym per spelling stays for a later story, because changing it changes how every stored name is looked up and existing databases may already hold both spellings. (C) Before 2.3.0, in 10.19, all of it: names that differ only in capitals share one pseudonym and one row. Which one?" The options: "A: Later, all of it" / "B: Erasure only, in 10.19 (Rec.)" / "C: All of it, in 10.19". → AC4, AC6, AC7; one pseudonym per spelling → Follow-ups.
2. **The rule's wording, the PO's M1, accepted by the orchestrator without a question:** "the same letters as the text selected, whatever their capitals, except a place written entirely in small letters (unless it is exactly the text selected)", the faithful reading of Lionel's "forms with capitals only … never a word in small letters"; 0 extra places on real text. → AC1.
3. **Q2, the `delete-mapping` texts: "Approve (Rec.)".** On the first version, which said "row"/"ligne", Lionel answered: ""ligne" is confusing. Why refer to this in terms of database?" The reworded question, word for word: ""Fair point: "row"/"ligne" is how the database stores it, not how you think about it. I copied it from the current reference (line 470 says "one row each"). Same texts, reworded without database words. Screen (the number is the count): « You are about to delete the following 2 saved pseudonyms (all of this name, whatever its type or its capitals): ». CLI-REFERENCE.md: « The same name can have several saved pseudonyms: one for each type it was saved under, and one for each way it was written with capitals ("Marie Dupont", "MARIE DUPONT"). Deleting by name lists all of them, then deletes them all (each deletion is logged as an ERASURE entry); `--id` deletes only one and tells you which others remain for the same name written exactly the same way. ». CLI-REFERENCE.fr.md: « Un même nom peut avoir plusieurs pseudonymes enregistrés : un pour chaque type sous lequel il a été enregistré, et un pour chaque façon dont il a été écrit avec des majuscules (« Marie Dupont », « MARIE DUPONT »). La suppression par nom les affiche tous, puis les supprime tous (chaque suppression est consignée par une entrée ERASURE) ; `--id` n'en supprime qu'un et indique ceux qui restent pour le même nom écrit exactement de la même façon. ». Approve these?"" → AC8.
4. **Q3, accents dropped in capitals: "A: Reach it too (Rec.)".** The question, word for word: "10.19 Q3: a name written in capitals can lose its accents (« HELENE » for « Hélène »). Your capitals rule reaches « HÉLÈNE » but not « HELENE », whose letters differ. Measured on the real command line with the fix: adding « Hélène » writes « HÉLÈNE » with its pseudonym and leaves « HELENE » in clear; v2.2.0 and today's code leave both in clear. Reaching it adds no wrong replacement on the text measured: none of the app's 728 names appears in capitals, with or without accents, in your ebook (20,000 words) or in the 25 test documents. How often real documents drop accents in capitals is not measured. (A) Reach it too (Rec.): a place written entirely in capitals is also a form when its letters are the name's once accents are set aside (« HELENE », « HELÈNE »), and « delete-mapping Hélène » also deletes a saved pseudonym of « HELENE »; still never a word in small letters, and « Helene » (no accent, not in capitals) stays a different name. The desktop app (10.17) takes the same rule. (B) Keep the rule as it is: « HELENE » stays in clear, and « delete-mapping Hélène » leaves the saved pseudonym of « HELENE » (measured). Which one?" The options: "A: Reach it too (Rec.)" / "B: Keep the rule". → AC1, AC4, AC5, AC6; the desktop rule is in 10.17.
5. **Q4, corrections in desktop batch review: "A: Reach it too (Rec.)".** The question, word for word: "10.19 Q4 (desktop batch review, where each place of a name is its own row): the detector finds « Zorbal » in « Zorbal Quentrix a signé. » and « ZORBAL » in « Signé : ZORBAL QUENTRIX. ». You correct the « Zorbal » row to « Zorbal Quentrix ». Every other row written « Zorbal » takes the correction (your 10.10 rule), but the « ZORBAL » row does not: it stays to review, and if you accept it as it is, the file reads « … Signé : [pseudonym] QUENTRIX. » (measured, today and with this story's fix). If you correct that row too, nothing stays in clear. The command line and the one-document review reach « ZORBAL QUENTRIX » with this story. (A) Reach it too (Rec.): in batch review, a correction also reaches the rows of the same name and type written with other capitals (and without accents in capitals, as you just chose), except a row you rejected on its own, and never a row written entirely in small letters. (B) Keep it: each spelling is its own row, and you correct « ZORBAL » yourself. Which one?" The options: "A: Reach it too (Rec.)" / "B: Keep it". The orchestrator added "(and without accents in capitals, as you just chose)" to keep it consistent with Q3. Placement in this story: the PM (Ordering). → AC3, AC6.

### Follow-ups (not ACs, 2026-10-19)

- **(a) One pseudonym per spelling (Lionel's Q1, for a later story):** names that differ only in capitals keep two rows and two pseudonyms (Context (c)). Sharing one changes how every stored name is looked up, and existing databases may already hold both spellings.

### Integration Points

- `gdpr_pseudonymizer/validation/models.py` — `places_of` (`:274`) and `is_listed_place` (`:306`), as 10.15 leaves them (PR #106)
- `gdpr_pseudonymizer/validation/workflow.py` — `_locate_modified_span` (`:550-578` at `e35ccc5`), [E] (its caller at `:301`), the approved 10.15 line (`:42`, PR #106)
- `gdpr_pseudonymizer/gui/models/validation_state.py` (`:378`, `:443`, `:800`) and `gui/screens/validation.py` (`:702`) — the desktop callers of `_locate_modified_span`, read only unless the fix needs them
- `gdpr_pseudonymizer/gui/models/validation_state.py` — `_action_rows` (`:315`), `_name_key` (`:302`): the batch reach of a correction (Q4)
- `docs/CLI-REFERENCE.md`, `docs/CLI-REFERENCE.fr.md` (`:470`) — AC8
- `gdpr_pseudonymizer/cli/commands/delete_mapping.py` (`:129`, `:159`; the screen, `_display_confirmation` `:293-312`) and `data/repositories/mapping_repository.py` (`find_all_by_full_name` `:205`, `_query_by_full_name` `:216`, `delete_entities_by_full_name` `:443`) — AC4
- `tests/unit/`, `tests/integration/` — AC6; `CHANGELOG.md` — AC7

### Estimated Effort: 0.5-1 week (Q3 and Q4 added the accents rule and the batch reach)

---

## Story 10.20: Accents Stored Two Ways: One Form Everywhere (PO sweep, after the Codex review of 10.16)

**Added by Lionel, 2026-10-20 (release blocker):** "A: Before 2.3.0 (Rec.)". The question he answered, word for word, after the PO's sweep (orchestrator's decision log, "Release scope: accents stored two ways (NFD)"): "Fix the two-ways-of-storing-accents problem before releasing 2.3.0, or after?" The options, word for word: "A: Before 2.3.0 (Rec.)" — "One new story converts every file read, every typed name and every saved name to the usual form. All the cases above then behave like typed text. About one more pipeline round and one more Codex review." / "B: After 2.3.0" — "For 2.3.0, only what got worse is fixed: the « Mme Zo » detection case and the new checks in 10.16, 10.17, 10.19. The old cases wait for their own story after the release." Option A's preview, as the decision log records it, listed: every file read (.txt .docx .pdf .xlsx .csv) converted to the usual accent form; every typed and saved name compared in that form; fixes missed names, « Mme Zo », corrections, [A] not found, second pseudonym, deletion; written files then use the usual form (same look, different bytes); one accuracy run must show the scores unchanged; 10.17 and 10.19 build on it; cost one more story, one more Codex review. Found by the read-only Codex review of 10.16 (2026-10-20) for one check, then measured by the PO across the release paths (Context).

**As a** user whose documents may store an accented letter as the plain letter followed by a separate accent mark (some PDFs and some programs write it so),
**I want** every file read, every name I type and every comparison with my saved names to use one form,
**so that** such a name is found, replaced, reused and erased exactly like the same name written the usual way, and no part of it is left in clear.

**Priority:** HIGH — release blocker for v2.3.0 (Lionel, 2026-10-20). Paths 1, 2, 3, 5 and 6 leave a name or part of it in clear; paths 4 and 7 give one person two pseudonyms; path 8 keeps a saved pseudonym after an erasure that says it is gone (Context).
**Change type:** one composed form (Unicode NFC) at every entry: the readers (`utils/file_handler.py`, `utils/tabular_reader.py`), the typed texts (CLI prompts and arguments, desktop dialogs) and the comparisons with saved names (`data/repositories/mapping_repository.py` and its callers); the product's own word cuts keep combining marks inside their words (AC4); written files come out composed (AC5). The detector's code and patterns (`nlp/`, `resources/`) do not change: they receive composed text. G1 applies as a check (AC7): one accuracy run, its 16 lines unchanged. No file under `tests/accuracy/` or `tests/test_corpus/` changes.
**Ordering:** outside the detector chain. After 10.16 merges, rebased on it: 10.16 composes the texts its checks cut before cutting them (`document_words` and the pseudonym's runs; Decisions Recorded, item 2) and keeps `_WORD = \w+` (`core/custom_pseudonym.py:267` at `43041e9`); 10.20 changes the word cutting itself (AC4), next to 10.16's lines in the same file. Before 10.17 and 10.19, which build their places and forms on its composed text: each rebases on 10.20 and adds a decomposed-accent guard case to its own tests (a decomposed document and a composed typed name: every place reached, never an "Added" while a place stays in clear; path 9). It shares `validation/models.py` (`places_of`, `is_listed_place`) and `validation/workflow.py` (`_locate_modified_span`, the typed prompts) with 10.19; `cli/commands/delete_mapping.py` and `data/repositories/mapping_repository.py` with 10.19; `core/document_processor.py` with 10.16; and it may share `gui/screens/validation.py` and `gui/models/validation_state.py` with 10.16, 10.17 and 10.19. 10.12, 10.13, 10.14, 10.15 and 10.18 are merged (`main` `43041e9`). Its own PR; stories that change the same file are sequenced and the later one is rebased on the earlier, never merged together. Every story edits `CHANGELOG.md`. Before the v2.3.0 release.

### Context

At `main` `43041e9`. Measured by the PO on 2026-10-20, read-only, on `main` and on v2.2.0 (probes `rgpd-analysis/r1019/po/nfd/probe/test_nfd_*.py`, results in `r1019/po/nfd/logs/`; invented names only; detection replaced except in path 1). "Decomposed" means an accented letter stored as its plain letter followed by a separate accent mark (« o » + U+0301, Unicode NFD); "composed" means the usual single accented letter (« ó », Unicode NFC). Both look the same on screen; the product compares them as different texts. Every path was run with the same invented text written both ways.

- **Where it starts:** no product code converts text to one form when a document is read or a name is typed; `unicodedata` only folds accents inside two comparisons (`core/custom_pseudonym.py:196-197`, `nlp/hybrid_detector.py:298`). A combining mark is not a word character (`\w`), so the word patterns cut a decomposed word at its mark: the 10.16 check (`core/custom_pseudonym.py:267`), 10.15's places of [A] (`validation/models.py:32-33`), and the detector's title pattern (`resources/detection_patterns.yaml:15`).
- **The nine paths (the PO's table, in short; decomposed text, name typed composed where a name is typed):**

  | # | Path | `main` `43041e9` | v2.2.0 |
  |---|---|---|---|
  | 1 | Detection, the real detector on 10 invented sentences | 8 of the 10 sentences are detected differently: names missed (« Monsieur Zórbalia Quentrel », « Maître Éloria Quentrel », « Madame Éloria Vórlan »), shortened (« Vorlan Zórbalia » to « Zórbalia ») or given another type (« Éloria Vórlan » as ORG). **New:** in 2 of them « Mme Zórbalia » is cut to « Mme Zo », because the title pattern stops at the mark; the written file reads « Mme Mina Meyer », the mark, then « rbalia »: the end of the name in clear | The same misses; « Mme Zo » was found too, but spaCy also found the whole « Mme Zórbalia », and nothing of it stayed in clear |
  | 2 | CLI [A] (10.15) | « ⚠️ 'Zórbalia' not found in document », both places in clear, nothing added. In a document holding both forms, only the places written like the typed name are replaced | The same « not found » (and one place only) |
  | 3 | CLI [E] (10.15) | « Gilles Robin Quentrel a signé. Signé : Gilles Robin Quentrel. »: « Quentrel » in clear at both places; the row is stored composed | The same |
  | 4 | CLI review grouping, 10.13's count | The same name written composed at one place and decomposed at another is shown as separate names (3 unique instead of 1); accepted, the file reads « Fionn Salgado a signé. Signé : Jade Salgado. »: two pseudonyms for one person in one document, two rows | The same |
  | 5 | Desktop, single-document review | A correction typed composed on a decomposed name leaves « Quentrel » in clear at both places. In a document holding both forms, the decomposed row is not reached and stays to review; accepted as it is, the file keeps « Quentrel », and two rows are stored. A correction that extends the dialog's own text leaves nothing in clear. A name added by hand: no difference between the forms (one place only, the leak 10.17 fixes) | Not measured |
  | 6 | Desktop, batch review | The same as path 5 for corrections | Not measured |
  | 7 | A saved name reused in a later document (`process` twice; `batch --workers 1`) | Saved from a composed document and met decomposed, or the reverse: a second pseudonym (« Mona Andrade », then « André Andrade ») and a second row | The same |
  | 8 | `delete-mapping` by name | Saved decomposed: « Entity Not Found », exit 1, the saved pseudonym stays. Saved both ways: only the composed one is deleted, while the screen says « The pseudonym '…' is now permanently anonymous. ». `list-entities --search` with the composed name does not list the decomposed one (the probe's line count) | The same |
  | 9 | The 10.17 and 10.19 prototypes (not merged) | The forms rule finds only « ZORBALIA » (written without accent), so [A] shows « ℹ️ Added PERSON entity: Zórbalia » and « Added: 1 » while « Zórbalia » and « ZÓRBALIA », written decomposed, stay in clear: `main`'s visible « not found » becomes a silent "Added". 10.19's erasure across capitals, typed composed, leaves both decomposed saved pseudonyms | Not in v2.2.0 |

- **The 10.16 check (Codex, 2026-10-20):** on 10.16's head `463481a`, the custom pseudonym « Xantor Zórbalia » is accepted for a reviewed name « quentrel zórbalia » written decomposed, at set time and at finalization, and the real surname is written: the check cuts « zo » and « rbalia » apart at the mark before it folds accents (Codex P0, `rgpd-analysis/r1016/codex/review_final.txt`). 10.16 fixes it inside its checks (Decisions Recorded, item 2).
- **Two letters of a name in clear, and names saved wrongly (found by the SM, reproduced by the PO on a fresh database):** the title pattern (`utils/french_patterns.py:18`) ends a title where the next character is not a word character, and an accent mark is not one. So « Mélora » written decomposed begins with the title « Me »: the written file keeps « Me » before the pseudonym (« Le contrat avec MeEytan Roger a signé. » for « Le contrat avec Mélora Quentrel a signé. »), and the name is saved as « lora Quentrel » after a lone accent mark; a name ending « …ôme » loses « me » the same way (5 of the 106 accented names of the app's name lists). A decomposed « Maître » is not recognised as a title, so the name after it is saved with « Maître » in its key; a LOCATION after a decomposed « à » keeps « à » in its key the same way. The same in v2.2.0 and at `43041e9`. Fixed here by AC1, since the pattern then reads composed text; the rows saved so are covered by AC3.
- **New or pre-existing:** paths 1 (the misses), 2, 3, 4, 7 and 8 behave the same in v2.2.0; paths 5 and 6 were measured on `main` only. New since v2.2.0, never released: the « Mme Zo » cut (path 1), the 10.16 check (fixed in 10.16) and the prototypes' silent "Added" (path 9), which must not merge so (Ordering).
- **Where decomposed text comes from (the PO's inputs probe):** `.txt`, `.csv`, `.xlsx` and `.docx` return what the file stores, composed or decomposed. Typing in Word gives composed text; a decomposed paragraph that a script types into Word stays decomposed in the `.docx`; Word's « Save as PDF » gives composed text, even for that paragraph. A PDF that draws the accent apart from its letter (the PO made one with fpdf2) is returned decomposed: pdfplumber gives the accent as its own character (`utils/file_handler.py:114-116`), and its `unicode_norm="NFC"` option does not join it to its letter, because it normalizes each character alone (measured by the SM and the PO: 4 marks left). So `read_pdf` composes the text it extracts (AC1). Typed names are what the keyboard or the paste gives. How often real documents hold decomposed accents is not measured.
- **The PO's recommendation, which option A follows:** one point for the composed form, rather than a check in each story: the readers (for PDFs, the extracted text, since pdfplumber's `unicode_norm` does not compose it), the typed texts, and both sides of every comparison with saved names. The cost: a file written decomposed comes out composed (same look, different bytes), and one accuracy run.
- **The accuracy suite** loads 13 product files (the 10.11 count: `gdpr_pseudonymizer/__init__.py`, eight files of `nlp/`, `resources/__init__.py`, `utils/__init__.py`, `utils/french_patterns.py`, `utils/logger.py`), none of the readers. The run of AC7 is the check Lionel's option A asks for: the scores unchanged.
- **Not in this story:** compatibility forms (Unicode NFKC: ligatures such as « fi » stored as one character, full-width letters, …), which change more than accents, unless the SM measures a need; the detector's own patterns (Open Points (c)).

### Acceptance Criteria

1. **AC1 — Every reader returns composed text (Lionel, 2026-10-20, option A):** `read_file` for `.txt` and `.md`, `read_docx`, `read_pdf` (pdfplumber), `read_excel` and `read_csv`, and the structured readers `read_excel_structured` and `read_csv_structured` (every cell) return their text in composed form (Unicode NFC). Every path that reads a document goes through them, the CLI (`process`, `batch` one file at a time and parallel) and the desktop app (single document and batch); the SM lists any reader or path that does not, and covers it. So the detector, the review (its text, its highlights, a name selected for an add by hand) and every later step see one form. Compatibility forms (NFKC) are not changed (Context, "Not in this story").
2. **AC2 — Every typed name is read in composed form:** in the CLI, the texts typed at [A] ('Entity text'), [E] ('Enter corrected entity text') and [C] ('Enter custom pseudonym'), the name given to `delete-mapping`, and the `--search` text of `list-entities` and `list-mappings`; in the desktop app, the texts typed in « Modifier le texte de l'entité » and « Changer le pseudonyme », in the review's « Filtrer les entités... » field and in the database screen's search field. The SM lists any other place where the user types a name, and covers it.
3. **AC3 — Saved names are compared in composed form on both sides:** every comparison of a text with saved names compares composed forms: the reuse of a saved name and its pseudonym (`find_by_full_name_and_type`, `find_all_by_full_name`, the library's `find_by_component`, `import-mappings`' duplicate check), the erasure (`delete-mapping` by name removes every saved pseudonym whose name has the same composed form, listed before the confirmation, each with its 10.12 erasure entry) and the search (`list-entities`, `list-mappings`, the desktop database search). So a database written by v2.2.0 or by today's code still matches, with both kinds of old row: rows whose name kept its decomposed letters, and rows an earlier version saved wrongly because a title or preposition pattern met a decomposed name (Context): « Mélora Quentrel » saved as « lora Quentrel » after a lone accent mark, a name written after a decomposed « Maître » saved with « Maître » in its key, and a LOCATION saved with « à » before the place by the same mechanism. Rows the app saves are composed; rows `import-mappings` brings in are copied exactly as they were saved, because composing can erase the mark that shows an earlier version cut the name (QA, 2026-10-22, IMPORT-002). No saved row is rewritten: every lookup by name also tries the ways an earlier version saved the name (Lionel, 2026-10-21, Qa "A: Find as they are (Rec.)"). Rows an earlier version saved wrongly are reached when the loss of letters left a sign (a word starting with a lone accent mark, as « lora Quentrel »; two words glued where a space was, as « JérôQuentrel » for « Jérôme Quentrel »), and so are the rows with « Maître » or « à » kept in the key. A name that lost its last letters (« Jérôme » written alone, saved as « Jérô ») is not reached by its full name: that person gets a second pseudonym in later documents, as in v2.2.0, and `delete-mapping` with the full name finds nothing, while typing what was saved (« Jérô ») still erases it (Lionel, 2026-10-22, P0-1 "A: Only with a sign (Rec.)"). The P0-1 question as asked, word for word (the full text he was shown is in the story): "10.20 P0-1: names an earlier version saved with their last letters missing. Find them only when the loss left a sign, or all of them?" The options: "A: Only with a sign (Rec.)" — "Removes one of the two wrong-person cases. A name cut at its very end (« Jérô ») gets a second pseudonym, as in 2.2.0. The other case can't be closed without losing far more common names like « André »." / "B: All of them" — "Every cut name is still found by its full name, the last-letter ones too, and both wrong-person cases stay." The check that refuses a custom pseudonym equal to a real name already saved (10.11's Q-C2, at set time and at finalization) compares with the repaired forms of old rows, including what a name cut at its end could have been: « Jérôme » is refused as a pseudonym when « Jérô » was saved by an earlier version. It only ever refuses, so a few made-up pseudonyms are refused too (« Vorlan Zorbôme » when « Vorlan Zorbô » is saved); finding, reusing and erasing stay as P0-1 decided (Lionel, 2026-10-22, end cut "A: Refuse them too (Rec.)"). The end-cut question as asked, word for word (the full text he was shown is in the orchestrator's questions file, section "End cut"): "10.20 end cut: should the pseudonym check also refuse what a cut name could have been?" The options: "A: Refuse them too (Rec.)" — "« Jérôme » is refused as a pseudonym when « Jérô » was saved. Wrong outcome: a few made-up pseudonyms are refused too, and you choose another. Finding, reusing, erasing stay as in P0-1." / "B: Keep it as it is" — "The check ignores cut names. Wrong outcome: « Jérôme » can be chosen as a pseudonym when « Jérô » was saved, and that real name is written in the document." How old rows are reached: the exact lookups (reuse, erasure, `import-mappings`' duplicate check) try the keys an earlier version could have saved; the comparisons that scan the saved rows (the saved-real-name check and the four searches: `list-entities`, `list-mappings`, the desktop database screen and its worker) rebuild from each saved row the texts it may stand for, and only add them to what is compared. When a name and type are saved both ways, later documents use the pseudonym of the row saved the usual way, and both rows stay saved (Lionel, 2026-10-21, Qb "A: Usual way's one (Rec.)"). Open Points (a) and (b) record both decisions.
4. **AC4 — A word keeps its combining marks (the 10.16 SM's follow-up (f)):** wherever the product cuts text into words or checks that a place is a whole word, outside the detector, a combining mark (every character for which `unicodedata.combining` is not 0) stays inside its word, also where Unicode has no composed letter for it (« x » + U+0301). This covers at least the 10.16 checks (`core/custom_pseudonym.py`, `_WORD`, as 10.16 leaves it), 10.15's places of [A] (`validation/models.py`, `_NOT_AFTER_WORD` and `_NOT_BEFORE_WORD`, `places_of`, `is_listed_place`), the correction locator (`validation/workflow.py`, `_locate_modified_span`) and the redaction of names in logged and audited error messages (`core/document_processor.py`, `_sanitize_error_message`, its name pattern `:1079`); the SM lists every other cut it finds. So a decomposed « zórbalia » is one word, and « Zo » is never a whole-word place inside it. The detector's patterns are not changed here (Open Points (c)).
5. **AC5 — Written files use the composed form (Lionel's option A: "same look, different bytes"):** the written text file and every cell written back to an `.xlsx` or `.csv` file hold composed text, also where no name was replaced, since they are written from what the readers return; the rows saved from them hold composed text. The CHANGELOG says so (AC8).
6. **AC6 — Tests first, invented names only:** the BMAD dev agent writes the tests and commits them before the fix. Each of the PO's nine paths gets a test with the same invented text written composed and decomposed (and with both forms in one document where the PO measured it), through the real readers and the real CLI or desktop paths, detection replaced except for the « Mme Zo » case. Each expected failure is an `assert` on the written file, the stored rows or the line shown, made after the test's preconditions hold, and each failing test is marked `xfail(strict=True, raises=AssertionError)` on the old code (the 10.5 pattern). The fix removes the markers. Cases:
   - **path 1, « Mme Zo »:** a ".txt" holding « Mme Zórbalia » written decomposed, with the real detector (or the regex layer that cuts it; the SM chooses and says why): the detector receives composed text and the written file holds no part of the name, as for the composed text;
   - **path 2, [A]:** a name typed composed in a decomposed document, and typed decomposed in a composed one: no « not found », every place written with the added name's pseudonym, one row; in a document holding both forms, both forms are replaced;
   - **path 3, [E]:** a correction typed composed on a decomposed name: no part of it in clear, one row;
   - **path 4, grouping:** the name written composed at one place and decomposed at another: one name in the review, one pseudonym in the file, one row; 10.13's count of names still to review counts it once;
   - **paths 5 and 6, desktop corrections, single document and batch:** a correction typed composed on a decomposed name, and in a document holding both forms: every place reached, no « Quentrel » in clear, one row; a name added by hand: the same result in both forms (a guard);
   - **path 7, reuse (`process` twice, `batch --workers 1`):** a name saved from a composed document and met decomposed in the next one, and the reverse: the same pseudonym, no second row; and with a database that already holds the decomposed row, written by today's code: the same pseudonym;
   - **path 8, `delete-mapping`:** a name saved decomposed, the name typed composed: listed, deleted, with its erasure entry; saved both ways: both listed and deleted; `list-entities --search` lists both;
   - **path 9:** tested by 10.17 and 10.19 when they rebase (Ordering); here, path 2's cases assert the same outcome on `main`'s [A];
   - **every reader:** `.txt`, `.md`, `.docx`, `.pdf` (a PDF whose text pdfplumber returns decomposed today), `.xlsx`, `.csv` and the structured `.xlsx` and `.csv` readers return composed text; a file written decomposed comes out composed (AC5);
   - **the end cut (Lionel, 2026-10-22, end cut "A: Refuse them too (Rec.)"):** with a row an earlier version saved cut at its end (an invented name, such as « Vorlan Zorbôme » saved as « Vorlan Zorbô »), a custom pseudonym equal to what the cut name could have been is refused, in the CLI and the desktop app, at set time and at finalization: nothing written, no row stored; finding, reusing and erasing stay as P0-1 decided (a document naming the full name gets a second pseudonym, and `delete-mapping` with the full name finds nothing);
   - **a mark with no composed letter (AC4):** « x » + U+0301 inside an invented name: one word for the 10.16 check and for 10.15's places of [A]; [A] reaches the whole word.

   Decomposed forms are made at run time with `unicodedata.normalize("NFD", …)`: no combining mark is written in a test file (10.16's rule). The strings go through `scripts/accuracy_heldout_blind_check.py`, as in 10.16. Existing tests stay green. An existing test changes only for a reason this story gives, stated in the story and, for each edited assertion, in the body of the commit that edits it: in 10.16's round-2 test files and the round-1 helpers they call, for AC1 (their stand-in detector now meets composed text; the desktop batch helper's wait), AC2 (a custom pseudonym typed decomposed is saved composed) or AC5 (decomposed bytes in a written file or a stored row); in any other test, for AC5 only.
7. **AC7 — G1, one accuracy run (Lionel's option A: "one accuracy run must show the scores unchanged"):** one regular `accuracy.yaml` run on the branch, at the PR's final code, shows the 16 lines identical to `38212303870`, cited by ID, the lines pasted in the PR. The run is required whatever files the diff touches. Any difference is explained in the story and the PR and approved by Lionel before the merge; a recall drop is G3 (stop and ask Lionel).
8. **AC8 — CHANGELOG:** `[Unreleased]` gets a "Fixed" entry: an accented name stored with its accent as a separate mark (as some PDFs and programs write it) was treated as a different name from the same name written the usual way: cut by the detector (« Mme Zo »), with the letters « Me » of a name such as « Mélora » left in clear before its pseudonym, « not found » with [A], left partly in clear by a correction, shown as two names in the review, given a second pseudonym in a later file, and not found or only partly erased by `delete-mapping`. Every file read, every typed name and every comparison with saved names now use the usual (composed) form, so a document storing its accents apart is now detected exactly as the same document written the usual way. The entry does not say that missed names are now found: on the PO's texts the places found go from 11 to 17 of 19, and one text loses two places found today, which its usual form misses too. It also says what changes: written files come out in that form, with the same look and different bytes, even where no name was replaced. It says that names an earlier version saved with a separate mark, or saved wrongly because of it, are still found and erased, except a name that lost its last letters, and that nothing in the database is rewritten. It also says that a custom pseudonym equal to a name an earlier version saved wrongly, a name cut at its end included, is refused. It says "already in v2.2.0" only for what was measured there (paths 1 to 4, 7 and 8; the SM measures the desktop paths 5 and 6 on v2.2.0 before the entry names them), and that the « Mme Zo » cut was never released.
9. **AC9 — User copy (Lionel, 2026-10-21, Qc "A: Use it (Rec.)"):** the `delete-mapping` screen's line for several saved pseudonyms, « You are about to delete the following N entity mappings (one per type of this name): » (`cli/commands/delete_mapping.py:304-305`), is untrue when it lists a name's composed and decomposed saved pseudonyms of one type (AC3; measured by the SM). It becomes, byte for byte, N the count: « You are about to delete the following N saved pseudonyms (all of this name, whatever its type): ». It is Lionel's 10.19 line (10.19 Q2) without « or its capitals », which 10.19 puts back when it lands. The one-row line stays as it is. The question as asked, word for word (the full text he was shown is in the story, Dev Notes "Decisions Recorded"): "10.20 Qc: the delete screen's line when one name is saved both ways. Use the proposed line now, or keep today's until 10.19?" The options: "A: Use it (Rec.)" — "« You are about to delete the following 2 saved pseudonyms (all of this name, whatever its type): ». Your 10.19 wording minus « or its capitals », which 10.19 adds back." / "B: Keep it until 10.19" — "Today's line stays until 10.19 replaces it. Nothing is released in between, but the line is false on the main branch until then." Any other new text is user copy that Lionel approves, word for word, before the story is done (Lionel, 10.19 Q2 and Q5b: never "row" or "ligne").
10. **AC10 — Codex:** Lionel, 2026-10-18: "codex is NOT writing code, ever. Codex is a reviewer."; "codex is the reviewer for bmad projects, period, and don't substitute with forge without telling me first"; "forge cato and co are part of this. which is good, pai should keep and using it BUT NOT WITH BMAD". The BMAD dev agent (Claude) writes the code and the tests, tests first; no Forge, Anvil or Cato on this story. Before the merge command, the PR's final head gets one read-only Codex review (`codex exec --sandbox read-only`, run by the orchestrator, one session); if the code changes after that review, the new head is reviewed again. If Codex cannot run, the work stops and Lionel is told; no review is reported that did not run.
11. **AC11 — Gates:**
    - **G1:** AC7. The PR states that the detector's code and patterns do not change, and pastes the run's lines.
    - **G3 and G5** are read from the AC7 run: its 16 lines hold the main-corpus and held-out lines, so identical lines mean no recall change and no held-out change. Any recall drop: stop and ask Lionel.
    - **G4:** never in the same PR as a detector change, or as another Epic 10 story.
    - **G2:** QA downloads the AC7 run's artifact itself and checks its lines, re-runs the AC6 tests and the PO's nine probes (`rgpd-analysis/r1019/po/nfd/probe/`), checks out the tests-first commit to see the tests fail on the old code, and reads the diff. QA's gate comes before the merge.
    - **G6** applies in full (black, ruff, mypy, unit tests, full CI green).
    - **G7:** no headline number changes. CHANGELOG as above.

### Decisions Recorded (Lionel and the orchestrator, 2026-10-20)

1. **Release scope, accents stored two ways: "A: Before 2.3.0 (Rec.)".** The question, its options and option A's preview are quoted word for word at the top of this section. → AC1 to AC8; the order after 10.16 and before 10.17 and 10.19 (Ordering).
2. **10.16 keeps its own fix (the orchestrator's ruling on the Codex review of 10.16, `rgpd-analysis/r1016/codex/ruling.md`):** "fix it in 10.16, inside the checks, without changing what is written": every comparison of 10.16's rules reads its texts in composed form before cutting them into words; the written file and the stored rows keep the document's own characters in 10.16. This story does not undo that fix; after AC1 those checks receive composed text from the readers anyway. The 10.16 SM's follow-up (f) (NFC cannot join a combining mark to a letter that has no composed form, so cutting text into words must keep combining marks inside their word) belongs here. → AC4.

### Open Points for the SM and the PO (not ACs, 2026-10-20)

- **(a) Saved names written decomposed (AC3): decided (Lionel, 2026-10-21, Qa "A: Find as they are (Rec.)").** The question as asked, word for word (the full text he was shown, with the SM's and the PO's measurements, is in the story, Dev Notes "Decisions Recorded"): "10.20 Qa: names already saved the other way. Find them as they are, or rewrite them once?" The options: "A: Find as they are (Rec.)" — "Nothing in your database changes. Every lookup also tries the ways an older version saved the name, wrongly saved ones included. About a hundredth of a second more per 50-name document." / "B: Rewrite them once" — "The first time 2.3.0 opens your database, names saved the other way are rewritten (0.3 s for 10,000). Wrongly saved names and people saved twice still need A's lookups, so B adds a database change on top of A." The full text he was shown said « 5 of the 111 accented names »; the right count is 5 of 106 (five names are in both of the app's name lists and were counted twice), and Lionel was told so before P0-1 (2026-10-22). So every lookup by name also tries the ways an earlier version saved the name, the wrongly saved ones included where the loss of letters left a sign (Lionel's P0-1, AC3), and the rows with « Maître » or « à » kept in the key; no saved row is rewritten (AC3).
- **(b) One name saved both ways: decided (Lionel, 2026-10-21, Qb "A: Usual way's one (Rec.)").** The question as asked, word for word (the full text is in the story, Dev Notes "Decisions Recorded"): "10.20 Qb: one person saved twice, once each way. Which pseudonym do later documents use?" The options: "A: Usual way's one (Rec.)" — "Documents written the usual way, nearly all of them, keep exactly the pseudonym they get today. Only documents storing the accent apart change (« Anya Branco » for both)." / "B: The oldest one" — "The person keeps the first pseudonym they got. When the other way came first, usual documents change pseudonym (today's « Nassim Fonseca » would become « Noé Fonseca »)." So when a name and type are saved both ways, later documents use the pseudonym of the row saved the usual way; both rows stay saved, and an erasure by name removes both, each with its erasure entry (AC3).
- **(c) The detector and marks with no composed letter.** After AC1 the detector reads composed text, so a document storing its accents apart is detected exactly as the same document written the usual way, for every accented letter that has a composed form, which covers French: the « Mme Zo » cut goes away, and a name the usual form misses stays missed (on the PO's texts, 11 to 17 of 19 places found; one text loses two places found today). A mark with no composed letter (« x » + U+0301) would still stop the detector's patterns (`resources/detection_patterns.yaml:15`). Changing them is a detection change, not part of this story (G4); if the SM measures such a case, it is recorded as a follow-up for Lionel.

### Integration Points

- `gdpr_pseudonymizer/utils/file_handler.py` — `read_file` (`:44`; `.txt` and `.md` `:83`), `read_pdf` (`:91`; `pdfplumber.open` `:114`, `extract_text` `:116`; the extracted text is composed after it, since `unicode_norm` does not compose), `read_docx` (`:152`), `read_excel` (`:214`), `read_csv` (`:293`), `write_file` (`:343`) — AC1, AC5
- `gdpr_pseudonymizer/utils/tabular_reader.py` — `read_excel_structured` (`:69`, the cell values `:126`), `read_csv_structured` (`:157`); `utils/tabular_writer.py` — `write_excel` (`:17`), `write_csv` (`:76`) — AC1, AC5
- `gdpr_pseudonymizer/core/document_processor.py` — the reads (`:1132`, `:1252`, `:1388`, `:1390`) and the saved-name lookups (`:292`, `:364`, `:740`, `:875`), `_sanitize_error_message` (`:1056`, its name pattern `:1079`); `gui/workers/batch_worker.py` (`read_file`, `:366`) — AC1, AC3, AC4
- `gdpr_pseudonymizer/validation/ui.py` — `get_text_input` (`:102`); `validation/workflow.py` — [E] (`:334`), [C] (`:363`), [A] (`:628`), `_locate_modified_span` (`:592`; `str.find` `:613`, `:617`) — AC2, AC4
- `gdpr_pseudonymizer/validation/models.py` — `_NOT_AFTER_WORD` and `_NOT_BEFORE_WORD` (`:32-33`), `places_of` (`:282`), `is_listed_place` (`:314`) — AC4
- `gdpr_pseudonymizer/core/custom_pseudonym.py` — `_WORD` (`:267` at `43041e9`), as 10.16 leaves it — AC4
- `gdpr_pseudonymizer/data/repositories/mapping_repository.py` — `find_by_full_name_and_type` (`:170`; the equality on the encrypted name `:193`), `find_all_by_full_name` (`:205`), `_query_by_full_name` (`:216`, `:221`), `find_by_component` (`:227`), `delete_entities_by_full_name` (`:443`), `search_entities` (`:505`); `pseudonym/assignment_engine.py` (`find_by_component`, `:366`) — AC3
- `gdpr_pseudonymizer/cli/commands/delete_mapping.py` (the name `:42`; `:129`, `:159`, `:228`; the screen `_display_confirmation` `:293`, its line `:304-305`), `list_entities.py` (`--search` `:47`, `:111`), `list_mappings.py` (`--search` `:57`), `import_mappings.py` (`:166`) — AC2, AC3, AC9
- `gdpr_pseudonymizer/gui/screens/validation.py` — the dialogs « Modifier le texte de l'entité » (`:714`) and « Changer le pseudonyme » (`:743`); `gui/models/validation_state.py` (`:175`); `gui/widgets/entity_panel.py` (the review's « Filtrer les entités... » field, `:116`, its placeholder `:181`); `gui/workers/database_worker.py` (`_search_entities`, `:211`) and `gui/screens/database.py` (the search field, `:167`) — AC2, AC3
- `tests/unit/`, `tests/integration/` — AC6; `CHANGELOG.md` — AC8

### Estimated Effort: 1-1.5 weeks (nine paths tested in both forms, every reader, and the saved-name comparisons of Open Points (a))

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
Story 10.11 (Custom pseudonym used)       --- 1.5 weeks, after 10.7 and 10.10 --- no accuracy baseline (desktop app + data layer)
Story 10.12 (Erasure log, no name)        --- 1 week, release blocker --- no accuracy baseline (CLI + data layer + docs)
Story 10.13 (Warning, names to review)    --- 0.5-1 week, release blocker --- no accuracy baseline (desktop app + CLI)
Story 10.14 (Batch, finalization hand-offs) --- 1-1.5 weeks, release blocker --- no accuracy baseline (desktop app)
Story 10.15 (CLI corrections, [A])        --- 1-1.5 weeks, release blocker --- no accuracy baseline (CLI)
Story 10.16 (Custom pseudonym fixes)      --- 0.5-1 week, release blocker --- no accuracy baseline (desktop app + CLI + core)
Story 10.17 (Desktop hand-added names)    --- 0.5-1 week, release blocker --- no accuracy baseline (desktop app)
Story 10.18 (CLI question, nothing left)  --- 0.5-1 week, release blocker, after 10.13 and 10.15 --- no accuracy baseline (CLI)
Story 10.20 (Accents stored, one form)    --- 1-1.5 weeks, release blocker, after 10.16, before 10.17 and 10.19 --- G1 check: 16 lines identical to 38212303870 (readers, CLI, desktop, data layer)
```

**Strictly sequential:** 10.1 → 10.2 → 10.3a → 10.3b → 10.3c → 10.4. Each story's baseline is the previous story's merged close-out G1 run. No parallel detector stories: overlapping changes would make G3/G4 attribution impossible.

**Story 10.5** is outside this chain: it changes no detection, so it has no accuracy baseline and can merge at any point without affecting G3/G4 attribution.

**Story 10.6** is outside the detector chain too. PR A (ranges) changes no metric line and should land before 10.3c, so 10.3c and 10.4 report ranges. PR B's documents are frozen, and both model annotations are done, before 10.4 merges. Nothing in 10.3c or 10.4 may draw on them. Lionel adjudicates after 10.4 merges, and close-out waits for his adjudication. The documents and adjudicated annotations are then committed as plain files (fingerprints checked against the freeze record) and scored exactly once, and that run is part of the Epic 10 close-out evidence.

**Story 10.7** is outside the chain, like 10.5: it changes no detection (data layer only), so it has no accuracy baseline and can merge at any point without affecting G3/G4 attribution. Its effect shows most once 10.3c has merged.

**Story 10.8** is outside the chain too: it changes no detection (desktop app and core preview keys), so it has no accuracy baseline. It merges before 10.7 and does not wait for 10.7's continuity decision.

**Story 10.9** is outside the chain too: it changes no detection (desktop app review only), so it has no accuracy baseline. It goes after Story 10.8, because both change `gui/models/validation_state.py`, and never in the same PR as 10.8.

**Story 10.10** is outside the chain too: it changes no detection (desktop batch review only), so it has no accuracy baseline. Its dev work starts after 10.9 merges, because it changes 10.9's `_action_rows` and that function's docstring (Lionel's Q3, 2026-10-14); its story and PO work can run in parallel with 10.9. Never in the same PR as 10.9.

**Story 10.11** is outside the chain too: it changes no detection (desktop review, the CLI validation path and the mapping data layer), so it has no accuracy baseline. It comes after 10.7 and 10.10 (both merged); Lionel's decisions are recorded (2026-10-15).

**Stories 10.12 to 10.18, and 10.20,** are release blockers outside the chain: none changes detection code, so none has an accuracy baseline (10.20 makes one accuracy run as a check, its AC7). Each is its own PR, never shared with another story, and all eight land before the v2.3.0 release. Stories that change the same file are sequenced, and the later one is rebased on the earlier; they are never merged together. Most shared files are different functions, with two exceptions: 10.18 needs 10.15's code (its [A], the cells it gives the manual flow, and its F1 fix) and both change `_run_validation`; and 10.13, 10.15, 10.16 and 10.18 all edit the same `run_validation_workflow(…)` call (`core/document_processor.py:363-372`, its keyword arguments at `:368-370`), so every keyword argument is kept at each rebase. 10.20 goes after 10.16 and before 10.17 and 10.19; its shared files are in its Ordering. The shared files:
- 10.13, 10.15 and 10.18: `validation/workflow.py` and `validation/ui.py` (10.13 and 10.15 also `validation/models.py`); 10.18 reuses [A] as 10.15 leaves it.
- 10.13, 10.16 and 10.17 (and 10.14 if it changes it): `gui/models/validation_state.py`.
- 10.13 and 10.14: `gui/screens/validation.py` (`_on_finalize`'s batch branch) and the `gui/i18n/` files. The `.qm` files are binary: they are regenerated after a rebase, never merged.
- 10.15 and 10.18: `_run_validation` in `core/document_processor.py` (the same function). 10.16 shares the file and the `run_validation_workflow(…)` call's keyword arguments (`:368-370`), not the skip; its own points, as its SM measured them, are `:172-178`, `:368-370`, `:392-414`, `:416-482`, `:635-652` and `:737-739`. It does not change `:801` (Codex #5's save, in the backlog). 10.15 and 10.16 may also both change `validation/workflow.py`.
- 10.19 (added 2026-10-19): `validation/models.py` with 10.13 and 10.15; `validation/workflow.py` with 10.13, 10.15 and 10.18; the `delete-mapping` code (`cli/commands/delete_mapping.py`, `data/repositories/mapping_repository.py`) with 10.12, now merged; the callers of `_locate_modified_span` in `gui/models/validation_state.py` with 10.17. It starts after 10.15 merges.
- Every story edits `CHANGELOG.md`; 10.12 shares no other file.

Suggested order: 10.12 at any time; 10.13, then 10.14, then 10.16, then 10.17 on the desktop side; 10.15 after 10.13, then 10.18 on the CLI side (every question is answered). 10.16 has no question and can go before 10.14 if needed.

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
- [ ] Database after 10.12 (Lionel, 2026-10-16, Q1 and Q2): no schema change and no version bump. On the first open by 2.3.0, after the 10.7 conversion, the names are removed from the ERASURE entries written by earlier versions and the file is compacted once (`VACUUM`, then a TRUNCATE checkpoint); a metadata row records a compaction still due, retried at the next open. Every connection deletes with `secure_delete`. New ERASURE entries hold no name
- [ ] Text after 10.20 (Lionel, 2026-10-20, option A): every file read, every typed name and every comparison with saved names use the composed form of accented letters (Unicode NFC). A document whose accents are stored as separate marks is written composed, the same look with different bytes, also where no name was replaced, and the CHANGELOG says so. No schema change, and no saved row is rewritten: every lookup by name also tries the ways an earlier version saved the name (Lionel, 2026-10-21, Qa); wrongly saved rows are reached only where the loss of letters left a sign, and a name that lost its last letters is not reached by its full name (Lionel, 2026-10-22, P0-1 "A: Only with a sign (Rec.)"), while the check that refuses a custom pseudonym equal to a saved real name also refuses what a name cut at its end could have been (Lionel, 2026-10-22, end cut "A: Refuse them too (Rec.)"); when a name and type are saved both ways, later documents use the pseudonym of the row saved the usual way, both rows staying saved (Qb) (Story 10.20, Open Points (a) and (b)). The `delete-mapping` screen's line for several saved pseudonyms becomes « You are about to delete the following N saved pseudonyms (all of this name, whatever its type): » (Qc, approved word for word; Story 10.20, AC9)
- [ ] UI changes: none; validation stays mandatory. Exception, Story 10.11: the refusal messages Lionel approved word for word (desktop French and English, the CLI, the rare finalization error; Q-A, 2026-10-15); the theme value "custom" shown in `list-mappings` (and its exports), `validate-mappings`, `delete-mapping` and `stats`; internally, `validation_complete` gains an argument and `finalize_document` an optional one. The schema is unchanged and its version is not bumped. Exceptions, release blockers (2026-10-16): Story 10.13's warning window (batch and single document) and CLI line, approved by Lionel word for word; Story 10.14: every route that opens a document or a folder during a batch shows a message whose button leads back to the batch (Lionel, 2026-10-16, texts approved word for word), and the review screen's « Annuler le lot » button is translated in English; Story 10.15's error text; Story 10.12's `--reason` help and its error text for a failed cleaning; Story 10.18's two lines and question when nothing is left to review, and its NoAnswerError line when no answer can be read (Lionel, 2026-10-16, Q1 and Q4, approved word for word). Each new text is approved by Lionel word for word
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
| Custom pseudonym advertised but never used (every version since v1.0.0; QA PRE-004 on 10.8): the user believes the chosen pseudonym is in the file, but a generated one is written. A careless fix could give two names one pseudonym | HIGH (every use) | MEDIUM (no leak; wrong output, lost trust) | Story 10.11 (HIGH, before release): the pseudonym is used in the file and stored for that (text, type); tests assert the written output; a clash or an already-stored pseudonym is refused (Lionel's Q1, Q2, Q-C and Q-D, 2026-10-15); the two older CLI review leaks with [P] are fixed in the same story (Q-F, AC11) |
| An erased person's name stays in the database file (every version since v1.1.0; QA B1; Codex #3): `delete-mapping` writes it, unencrypted, into the operations log, `export` copies it out, and every deletion leaves 7 encrypted copies in freed space | HIGH (every erasure) | HIGH (privacy; defeats the erasure) | Story 10.12 (release blocker): the log keeps date, row id, type and reason, not the name; names already in the log removed and the file compacted once on the first 2.3.0 open (Q1); every deletion overwrites the deleted data (Q2); docs corrected and `--reason` asks for a request reference (Q3). Out of reach, said in the docs: earlier exports, mapping exports, copies never opened by 2.3.0 |
| Names still to review written in clear with no warning, in batch review, single-document validation and the CLI (QA B2; 10.10 follow-up (d)) | MEDIUM | HIGH (privacy) | Story 10.13 (release blocker): a warning with the count of names that would stay in clear, before writing; the texts approved by Lionel word for word (2026-10-16) |
| Two runs mix in the desktop app (Codex #1, in every version tested) or a late change in the review alters what is written (Codex #4, pre-existing): names in clear | MEDIUM | HIGH (privacy) | Story 10.14 (release blocker): every route that opens something during a batch is refused with a message that leads back to the batch (Lionel's Q1); every hand-off tied to its run; finalization gets copies and the review cannot change while a document is written; tests first through real worker threads |
| CLI [E] and [T] on Excel and CSV files leave the name in clear while its pseudonym is stored (Codex #2, every version tested) | MEDIUM (spreadsheets, corrections) | HIGH (privacy) | Story 10.15 (release blocker): the cell is kept and the correction found inside it; a replacement that matches no cell stops the run before any row is saved |
| A name added by hand is replaced at one place only (desktop app; CLI [A] on text) or at no place (CLI [A] on Excel and CSV), while it is stored (PO finding, every version tested) | MEDIUM (every hand-added name found at several places) | HIGH (privacy) | Stories 10.15 (CLI) and 10.17 (desktop app), release blockers: every place of that name and type, places found by the detector keeping their own decisions; tests first on the written file |
| The CLI writes a document without any review when the detector finds no name or only stored ones (since v1.0.0): a missed name stays in plain text with no chance to add it, and the screen says all names had existing mappings even when none was found | MEDIUM (documents where the detector finds nothing new) | HIGH (privacy; Product Constraint 3) | Story 10.18 (release blocker): the CLI asks whether to add a missed name before writing, for each such file, with 10.15's [A] rules (stored names included in the overlap rule); the false line replaced; with no answer, that document stops with a clear line and nothing is written; texts approved by Lionel |
| A name added by hand or corrected stays in clear where it is written in capitals (« ZORBAL » for « Zorbal »); the detector misses most capital forms (2 of 8 in the PO's texts); the correction case is in v2.2.0 | MEDIUM (names written in capitals) | HIGH (privacy) | Story 10.17 (desktop places, AC1) and Story 10.19 (CLI [A] and the shared correction locating), release blockers: the same letters whatever their capitals, never a word in small letters (Lionel, 2026-10-19); capitals without accents reached too (Q3); desktop batch corrections reach the other spellings (Q4); `delete-mapping` by name also deletes the other spellings (10.19, Lionel's Q1, Q3) |
| A custom pseudonym repeats a lowercase real name, shares a part with a generated pseudonym, or makes finalization refuse a valid document (Codex #8, #6, #7; new in 10.11) | LOW (custom pseudonyms only) | HIGH for #8 (a name in clear), MEDIUM for #6 and #7 | Story 10.16 (release blocker): the review's names count whatever their capitals; the guard keeps roles and spellings; the reach follows the current name |
| An accented name stored with its accent as a separate mark (some PDFs and programs) is missed or cut by the detector (« Mme Zo », new since v2.2.0), not found by [A], left partly in clear by a correction, shown as two names, or given a second pseudonym; the letters « Me » of a name such as « Mélora » are left in clear before its pseudonym (in v2.2.0 too); `delete-mapping` misses it or erases only part (PO sweep, 2026-10-20) | NOT MEASURED (how often real documents store accents that way) | HIGH (privacy: parts of names in clear) | Story 10.20 (release blocker): one composed form at every reader, every typed name and every comparison with saved names; a word keeps its accent marks; the nine measured paths tested in both forms; one accuracy run with its 16 lines unchanged |
| Saved names written decomposed by v2.2.0 or by today's code, some of them saved wrongly (a name cut by the title pattern, « Maître » or « à » kept in the key): the repository finds a name by equality on its encrypted value, so a composed name does not find them; the same name and type can already be saved twice, with two pseudonyms | NOT MEASURED (databases that already processed such documents) | MEDIUM (a second pseudonym for one person; an erasure that leaves one) | Story 10.20 AC3, Lionel's decisions (2026-10-21): every lookup by name also tries the ways an earlier version saved the name, wrongly saved ones included, and no saved row is rewritten (Qa); a name saved both ways gets the pseudonym of the row saved the usual way, both rows stay saved, and an erasure by name removes both (Qb). With P0-1 (2026-10-22, "A: Only with a sign (Rec.)"), a wrongly saved row is reached only when the loss of letters left a sign, so a name that lost its last letters gets a second pseudonym, as in v2.2.0, and a full name never gets the pseudonym of a person whose real name is what was left (« Vorlan Zorbôme » never gets « Vorlan Zorbô »'s). One wrong-person case remains, accepted: an old row cut at the end of a name is reached by a real shorter name (« Vorlan Zorbôme » saved by an earlier version as « Vorlan Zorbô »: a later « Vorlan Zorbô » gets its pseudonym, and erasing « Vorlan Zorbô » erases it); no such pair among the 500,962 combinations of the app's two name lists, and real names are not limited to them. Closing it would stop finding the far more common whole names an earlier version saved decomposed (« André », « Chloé »). With the end-cut answer (2026-10-22, "A: Refuse them too (Rec.)"), the custom-pseudonym check also refuses what a cut name could have been (« Jérôme » when « Jérô » was saved), so a real name cut at its end cannot be written as someone's chosen pseudonym; the price is that a few made-up pseudonyms are refused (« Vorlan Zorbôme » when « Vorlan Zorbô » is saved) |
| Rare races left for later (Codex #5, #9, #10; Lionel: later): two programs on one mapping database, two programs opening a pre-10.7 file at once, a lost wake-up in the batch worker | LOW | MEDIUM (a mapping out of step, a false open error, a hung batch) | Backlog (Close-Out Record); the release notes can tell users to use one program at a time on a mapping database (user copy) |
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

- [ ] All 21 stories (10.1, 10.2, 10.3a, 10.3b, 10.3c, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11, 10.12, 10.13, 10.14, 10.15, 10.16, 10.17, 10.18, 10.20) completed with acceptance criteria met (10.5 and 10.7 to 10.18: G1/G3/G5 N/A, no detection change; 10.6: G1/G3/G5 N/A for building the set, its scored-once run is a G1 run; 10.20: no detection code change, one G1 run with its 16 lines identical to `38212303870`, G3 and G5 read from it)
- [x] Every story closed with a cited G1 run and an independent G2 check
- [x] No unapproved recall drop (G3) at any story
- [x] Held-out set exists and is reported for 10.2, 10.3a, 10.3b, 10.3c and 10.4 (G5)
- [x] `GUIDELINES.md` approved by Lionel and applied to the whole corpus
- [x] black, ruff, mypy clean; full CI green (G6)
- [x] QA report updated with the before/after at every story, and CHANGELOG `[Unreleased]` entries per story (G7)
- [x] At Epic 10 close-out, README/README.fr, `docs/faq*.md`, `docs/index*.md` and `docs/tutorial*.md` updated once from the final G1 run (G7 interpretation, Lionel, 2026-10-02)
- [x] Close-out baseline recorded as Epic 9's starting point: run ID plus the pasted `[Overall]`/`[PERSON]`/`[LOCATION]`/`[ORG]`/`[HELD-OUT …]` lines in the QA report (`accuracy-results` artifacts are kept 30 days, `retention-days: 30` in `.github/workflows/accuracy.yaml`, so the run ID alone is not enough)
- [x] Accuracy output reports 95% bootstrap ranges (unit=document) per type for main and held-out, with the eight existing lines unchanged (10.6 PR A)
- [x] Final-exam set (10.6): 30 documents frozen and annotated independently by two models before 10.4 merged, with sha256 recorded; inter-annotator agreement and the spot-check finding reported; adjudicated by Lionel after 10.4 merged; then committed as plain files under `tests/test_corpus/final_exam/`, with the documents' sha256 matching the freeze record, and scored exactly once at close-out: run ID, ledger entry and pasted `[FINAL-EXAM …]` lines (overall, planted half, natural half) in the QA report
- [x] Public headline figure chosen by Lionel among main, held-out and final exam, with its range (G7 interpretation)
- [x] No release cut (v2.3.0 only on Lionel's explicit go)

---

## Out of Scope

| Item | Reason | Where |
|------|--------|-------|
| ORG recall for missed brands (OVHcloud, TechCorp, Microsoft Azure, Partech, Kima Ventures, EY) — F10 | A gazetteer built from the brands in the corpus would be overfitting by construction; needs a general approach | Epic 9 or a later story. Related: 10.4 candidate item (QA REQ-001) |
| Different-type overlaps (PERSON vs ORG on the same span), except the exact-match case handled by 10.3c | Needs its own rule and evidence | Later |
| "Keyword + connector(s)" ORG widening, R-KWC ("Chambre d'Agriculture d'Eure-et-Loir", "Cour d'Appel de Paris"). Dry-runs (local, not CI results): 10.3a +1 ORG TP; 10.3b 0 change | Deferred out of 10.3a at STOP R (Lionel, 2026-10-06): it adds new recall rather than fixing a boundary. Routed to 10.4 at 10.3b STOP R (Lionel, 2026-10-07), together with QA REQ-001 (same prefix pattern) | 10.4 candidate item (not an AC) |
| Encoder NER models (CamemBERT-NER, …) | Lionel decision | Epic 9 |
| Auto-accept / no-validation modes | Product constraint 3 | Parked in Epic 9 |
| Codex release review #5, #9 and #10 (two programs on one mapping database, a conversion race between two programs, a lost wake-up in the batch worker) | Lionel, 2026-10-16: later; rare races, #9 new with 10.7, the others pre-existing | Backlog (Close-Out Record) |
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

**Document Status:** Re-opened for release blockers (Lionel 2026-10-16): Stories 10.12 and 10.13 (QA B1, B2), 10.14 to 10.16 (Codex release review) 10.17 with part of 10.15 (names added by hand) and 10.18 (the CLI's skipped review); every question for Lionel on them is answered. Story 10.20 (accents stored two ways) added by Lionel on 2026-10-20 (option A); his answers to its three questions (Qa, Qb, Qc) recorded on 2026-10-21, and to P0-1 after its Codex review ("A: Only with a sign (Rec.)") on 2026-10-22, when he was also shown that Qa's « 5 of the 111 accented names » is 5 of 106, and to the end-cut question after its second Codex review ("A: Refuse them too (Rec.)") the same day. Stories 10.1 to 10.11 were done on 2026-10-15; 10.12 to 10.15 and 10.18 are merged (`43041e9`)
**Created:** 2026-10-02
**Author:** John (PM)
