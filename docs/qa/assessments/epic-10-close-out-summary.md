# Epic 10 Close-Out QA Summary

- **Date:** 2026-10-15
- **Reviewer:** Quinn (Test Architect)
- **Code:** `main` at `b2042c7` (PR #101, Story 10.11, the last Epic 10 merge)
- **Branch:** `epic-10/close-out` (docs only; the PM adds the epic close-out to the same branch)
- **Epic:** `docs/prd/epic-10-v2.3-detection-precision-quick-wins.md`, cited as "epic" and not repeated here
- **This folder:** one trace matrix per story merged after the detector close-out (`10.5-trace-20261015.md`, `10.7-`, `10.8-`, `10.9-`, `10.10-`, `10.11-`), the epic-level NFR assessment (`epic-10-nfr-20261015.md`) and this summary

## Verdict

Every Epic 10 story has a final gate of PASS. Every AC of the six stories traced here is covered at `b2042c7`: none is partial or uncovered. Eleven leak paths were found during the epic. All were fixed after a failing test was committed first, and probed on the written file (NFR section 1.1). Main CI on `b2042c7` is green on the first attempt: all five workflows that fired.

The NFR assessment gives three CONCERNS and one PASS (quality score 70):

- **Security/privacy:** two pre-existing residuals.
  - The erasure audit entry keeps the erased name.
  - Batch validation writes names still to review without a warning.
- **Reliability:** the batch worker's wait and resume edge cases.
- **Maintainability:** the epic left `CHANGELOG.md` `[Unreleased]` and the architecture schema docs contradicting the code. Coverage, 84.24% with branches, is just under its 85% target.
- **Performance:** PASS.

None of these is a regression, and none leaves a confirmed name in clear. B2 concerns names the user has not confirmed yet. Three items should be decided before a v2.3.0 release: B1, B2 and B14 in the backlog below.

## Gate History per Story

| Story | PR, merge commit | Gate file (`docs/qa/gates/`) | History | Final | Score |
|---|---|---|---|---|---|
| 10.1 | #79 | `10.1-benchmark-repair-held-out-set.yml` | PASS | **PASS** | 100 |
| 10.2 | #81 | `10.2-overlap-dedup-org-role-filter.yml` | PASS | **PASS** | 100 |
| 10.3a | #84 (gate after the merge, PR #85) | `10.3a-boundaries-run-on-spans.yml` | PASS (post-merge; DOC-003 records the merge before QA) | **PASS** | 90 |
| 10.3b | #87, `bab6717` | `10.3b-particles-roles-location-noise.yml` | PASS | **PASS** | 100 |
| 10.3c | #91, `5846419` | `10.3c-type-aware-exact-match.yml` | PASS | **PASS** | 100 |
| 10.4 | #93, `2d4a029` | `10.4-greetings-org-plus-country.yml` | PASS | **PASS** | 100 |
| 10.5 | #96, `67807c2` | `10.5-db-init-safety.yml` | PASS (pre-merge, `091103a`) | **PASS** | 100 |
| 10.6 PR A | #89, `6abf858` | `10.6-pr-a-confidence-ranges.yml` | PASS | **PASS** | 100 |
| 10.6 PR B | #92, `c63a7b6` (ledger #94, `91b500d`) | `10.6-pr-b-final-exam.yml` | PASS | **PASS** | 100 |
| 10.6 B15 | #95 | `10.6-b15-close-out.yml` (detector close-out) | PASS | **PASS** | 100 |
| 10.7 | #99, `acb7bdd` | `10.7-type-aware-mapping-lookup.yml` | PASS (pre-merge, `702a655`) | **PASS** | 100 |
| 10.8 | #97, `e16d15a` | `10.8-gui-type-aware-candidate-keys.yml` | PASS (pre-merge, `10ddd62`) | **PASS** | 100 |
| 10.9 | #98, `49d4daa` | `10.9-gui-edit-all-occurrences.yml` | **CONCERNS** at `a30557b` (UI-001, UX-001 medium) → PASS at `56b600e` after two amendments | **PASS** | 100 |
| 10.10 | #100, `eee4d41` | `10.10-batch-review-fixes.yml` | PASS (pre-merge, `fc95786`) | **PASS** | 100 |
| 10.11 | #101, `b2042c7` | `10.11-custom-pseudonym.yml` | **CONCERNS** at `5c02ba9` (80) → **FAIL** at `e8cb76a` (70; MW-001 made CI red, `38730457990`) → PASS at `af5b23b` after the amendment | **PASS** | 100 |

- **Merged heads.** `gh pr checks` is 9/9 at the merged head of PRs #96 to #101. Two PRs merged at a commit made after their gate: #99 at `b5e0f99` and #100 at `82eaead`. Both are merges of `main` into the branch. QA 10.10 had checked the #99/#100 merge clean in both orders (tree `0c30ee7`) and run the GUI suites on the merged tree.
- **Main pushes.** Every workflow of the `main` push runs of the five earlier merges (`67807c2`, `e16d15a`, `49d4daa`, `acb7bdd`, `eee4d41`) succeeded.

## Trace Coverage (six stories after the detector close-out)

| Story | ACs | Covered by tests | Covered by process evidence | Partial | Uncovered | N/A |
|---|---|---|---|---|---|---|
| 10.5 | 8 | 4 (AC1-AC4) | 4 (AC5-AC8) | 0 | 0 | 0 |
| 10.7 | 11 | 5 (AC1-AC5) | 5 (AC6-AC8, AC10, AC11) | 0 | 0 | 1 (AC9, moved to 10.8) |
| 10.8 | 11 | 5 (AC1-AC4, AC9) | 6 (AC5-AC8, AC10, AC11) | 0 | 0 | 0 |
| 10.9 | 11 | 5 (AC1, AC6, AC9-AC11) | 6 (AC2-AC5, AC7, AC8) | 0 | 0 | 0 |
| 10.10 | 14 | 7 (AC1-AC3, AC8, AC11, AC13, AC14) | 7 (AC4-AC7, AC9, AC10, AC12) | 0 | 0 | 0 |
| 10.11 | 21 | 12 (AC1-AC5, AC11, AC13, AC16, AC17, AC19-AC21) | 9 (AC6-AC10, AC12, AC14, AC15, AC18) | 0 | 0 | 0 |
| **Total** | **76** | **38** | **37** | **0** | **0** | **1** |

- **Process evidence** covers gates, tests-first CI proofs, CHANGELOG, consumer traces, isolation and user-copy ACs: requirements a unit test cannot hold. Each is cited to the gate field that records it.
- **Later stories changed earlier behaviour, on purpose:**
  - 10.10 refined 10.9's AC11 (Lionel's Q7).
  - 10.11 changed 10.10's AC14 (a) for custom pseudonyms (Q-B) and edited two 10.10 tests and one 10.7 test helper, as its AC6 allows.
  - 10.7 moved the 10.5 helper's `schema_version` to "1.1.0".

  Each matrix records these under "Changes Since the Gate".

## NFR Verdicts (epic level)

| NFR | Verdict | Why |
|---|---|---|
| Security / privacy | CONCERNS | Every epic leak path is fixed and proven. Still open, both older than the epic: the ERASURE audit name (B1) and batch validation without a pending-rows warning (B2) |
| Reliability | CONCERNS | The 10.5, 10.7 and 10.10 guarantees hold, and MW-001's flaky tests are fixed at the cause. Still open: batch worker wait and resume edge cases (B5, B6), a local Windows flake (B7) |
| Maintainability | CONCERNS | The code and tests are clean. The CHANGELOG `[Unreleased]` contradictions (B14) and the stale architecture schema docs (B15) were created by the epic. Coverage is 84.24% with branches against 85% (B24) |
| Performance | PASS | NFR1 on `b2042c7`: 5,000 words in 0.87 s mean (target 30 s); every new check is bounded and measured |

Details, the flaky-test lesson and the settings-file isolation are in `epic-10-nfr-20261015.md`.

## Open Low Items per Story

Status re-read at `b2042c7`. "Resolved" means the cited fix is in the code at `b2042c7`.

| Story | Open items (gate id, or epic follow-up letter) | Resolved or closed since the gate |
|---|---|---|
| 10.1 | DOC-001, DOC-002, DOC-003 (story and record nits; not re-audited) | TEST-001 and TEST-002: the guards are keyed per file and have negative tests (`tests/unit/test_held_out_leakage.py`, `test_allowlist_is_per_file`, `test_guard_fires_on_planted_string_in_new_resource_file`) |
| 10.2 | none | TEST-002 (PR #83); REL-004 (10.3a AC5) |
| 10.3a | DOC-001, DOC-003 (story text; not re-audited); REQ-001 carried to Epic 9 through 10.4 | PERF-001 and REL-001 (PR #86, `1703616`); REL-002 (Lionel at 10.3b STOP R: C2 kept); DOC-002 (`CHANGELOG.md:136` reworded) |
| 10.3b | none | MX-001 (Story 10.3c) |
| 10.3c | none | - |
| 10.4 | REQ-001, REQ-002 (carried to Epic 9); DOC-001 (folded into B14: `CHANGELOG.md:67` still has no pointer to 10.7) | TEST-001 (`tests/unit/test_hybrid_greetings_org_country.py:331`, `:942`) |
| 10.5 | SM follow-ups: GUI passphrase message on any "12" (B25); stale `init_database` sketch §9.4 (B15) | - |
| 10.6 | PR A REL-001 (B23) | PR A SEC-001 (`--tb=short`, `.github/workflows/accuracy.yaml:197-202`) |
| 10.7 | UX-001 (B28), UX-002 (B29), DOC-001 (B14), MNT-001 (B30), TEST-001 (no action needed); SM follow-ups: stale architecture docs (B15), `import-mappings` replace (B4), erasure audit name (B1) | - |
| 10.8 | TEST-001 (B18); MNT-001 (information only) | PRE-001 to PRE-003 (Story 10.10); PRE-004 (Story 10.11) |
| 10.9 | DOC-002 (B16); TEST-FLAKE-001 (B7); documented cosmetic residuals (panel and tooltip text, "Dr" carried, batch count) | UI-001, UX-001, DOC-001 (in-story amendments); GRP-001, GROUP-ACCEPT-REJECTED, PRE-001 (Story 10.10) |
| 10.10 | OBS-001 (B13), OBS-002 (B9), TEST-001 (optional, T12 answers "no"), TEST-ENV-001 (B11); epic follow-ups (a)-(m) (B2, B5-B9, B14-B16, B21, B22, B26, B27) | - |
| 10.11 | OBS-002 (B10), DOC-001 (B17), OBS-001 (B40), accepted residuals (B36-B38), TEST-ENV-001 (B11), BACKLOG-EN-QM (B20), PO note Q1 route out (B6); epic follow-ups (a)-(m) (B3, B6, B19, B20, B31-B39) | MW-001, GUARD-001, PERF-001 (in-story amendment) |

## Consolidated Backlog

- **Severity** is QA's. The epic gives the follow-ups no severity.
- **Owner** is a suggestion; Lionel routes.
- **Text** is short. Each item's full text is at its origin.

| # | Item | Origin | Severity | Owner suggestion |
|---|---|---|---|---|
| B1 | ERASURE audit entry keeps the erased name in clear after `delete-mapping` (`cli/commands/delete_mapping.py:180`) | Epic, 10.7 SM follow-ups | Medium (privacy) | Lionel decides; dev |
| B2 | Batch "Valider et continuer" gives no confirmation or warning about rows still to review; those names are written in clear | Epic, 10.10 follow-up (d) | Medium (privacy) | Lionel (copy); dev |
| B3 | `import-mappings` copies rows without checking that their pseudonyms differ from the destination's, so two names can share one | Epic, 10.11 follow-up (b) | Medium (integrity) | PO scopes; dev |
| B4 | `import-mappings` "Replace existing mapping?" never replaces (counted as skipped) | Epic, 10.7 SM follow-ups | Low | Dev |
| B5 | Batch worker validation wait has no predicate loop; `validation_required` emitted before the mutex is taken (`gui/workers/batch_worker.py:362-375`) | Epic, 10.10 follow-up (c) | Low (latent) | Dev |
| B6 | A waiting desktop batch cannot be resumed after Ctrl+O, or after following Q1's route out to `delete-mapping` | Epic, 10.10 (f), 10.11 (l); 10.10 and 10.11 gates (handed off) | Low | PO |
| B7 | TEST-FLAKE-001: `test_serve_refuses_foreign_host_and_origin` flaky on local Windows (`ConnectionAbortedError`) | 10.9 gate; epic, 10.10 (k) | Low | Dev |
| B8 | Live batch table shows "Traité" for a document whose finalization failed | Epic, 10.10 (e) | Low | Dev |
| B9 | "◀ Précédent" past a document that failed to read does nothing | Epic, 10.10 (g); 10.10 gate OBS-002 | Low | PO |
| B10 | A random redraw (`_assign_untaken_pseudonym`) keeps no component link, so a later full name can lose its bound part | 10.11 gate OBS-002 | Low | Dev |
| B11 | TEST-ENV-001: `test_ner_title_improvements.py` needs the repository root as working folder; `test_config_show` wraps under a long TEMP | 10.10 and 10.11 gates | Low | Dev |
| B12 | GUI settings isolation lives only in the two GUI conftests; a GUI test placed elsewhere would write the real `.gdpr-pseudo.yaml` | QA close-out (`epic-10-nfr-20261015.md` §2.3) | Low | Dev |
| B13 | `BatchScreen._validation_results` holds the review's live entity objects; store a copy if a reader is ever added | 10.10 gate OBS-001 | Low | Dev |
| B14 | Harmonise `CHANGELOG.md` `[Unreleased]`: "The mapping schema is unchanged" (`:67`, `:87`, `:109`, `:125`, `:150`, `:203`), "without the entity type" (`:67`, `:87`), "The schema version stays 1.0.0" (`:197`) | Epic, 10.10 (i); 10.7 gate DOC-001; 10.4 gate DOC-001 | Medium (before release) | PM |
| B15 | Architecture docs stale: `9-database-schema.md` §9.1 (Fernet vs AES-256-SIV), §9.2 (no (text, type) key, extra CHECK), §9.4 (metadata sketch), schema 1.1.0; `6-components.md:158` ("checked on open") | Epic, 10.10 (j); 10.5 and 10.7 SM follow-ups | Medium | Architect |
| B16 | DOC-002: "detected span" wording in `CHANGELOG.md:169` and the 10.9 story's Consumer Trace #6, #7 | 10.9 gate; epic, 10.10 (l) | Low | SM, PM |
| B17 | DOC-001: copy Task 8.2's phrase into the 10.11 story's Dev Notes "CHANGELOG Entry" | 10.11 gate | Low | SM |
| B18 | Four test fixtures build preview maps with the dead `"{text}_{start}"` key | 10.8 gate TEST-001 | Low | Dev |
| B19 | `finalize_document_tabular` has no caller (`core/document_processor.py:1296`) | Epic, 10.11 (d) | Low | Architect decides; dev |
| B20 | `gui/i18n/en.qm` predates Story 7.4: three file filters in French in English mode | Epic, 10.11 (m); 10.11 gate BACKLOG-EN-QM | Low | Lionel; dev |
| B21 | Batch-validation texts have no English translation (`gui/i18n/en.ts`) | Epic, 10.10 (a) | Low | Dev (Lionel approves copy) |
| B22 | `except RuntimeError` around signal disconnects never fires (PySide6 warns), `gui/screens/batch.py` | Epic, 10.10 (b) | Low | Dev |
| B23 | `scripts/accuracy_paired_delta.py:108` catches `OSError` only; non-UTF-8 input gives a traceback | 10.6 PR A gate REL-001 | Low | Dev |
| B24 | Coverage 84.24% (with branches) vs the 85% "maintain" target; the target's definition (branches or not) is unstated | QA close-out (`epic-10-nfr-20261015.md` §3.1) | Low | Architect (target); dev |
| B25 | GUI shows the 12-character passphrase message for any error containing "12" (`gui/workers/detection_worker.py:112`, `processing_worker.py:102`) | Epic, 10.5 SM follow-ups | Low | Dev |
| B26 | "Validation per document" checkbox not remembered (`batch_validate_per_document` missing from `_DEFAULT_CONFIG`) | Epic, 10.10 (h) | Low | Dev |
| B27 | No visible cue when a group action skips places decided on their own | Epic, 10.10 (m) | Low | PO (Lionel approves copy) |
| B28 | `destroy-table` shows a failed conversion under "Deletion Error" with a generic hint; an unrecognised file needs `--skip-passphrase-check` | 10.7 gate UX-001 | Low | PO; dev |
| B29 | Desktop database screen shows a generic error for a failed conversion | 10.7 gate UX-002 | Low | PO; dev |
| B30 | Clash path gives a one-word standalone PERSON a two-word replacement | 10.7 gate MNT-001 | Low | Dev |
| B31 | The CLI cannot remove a custom pseudonym once set | Epic, 10.11 (a) | Low | PO |
| B32 | A lone first or last name row keeps its earlier preview in the list after a custom pseudonym is set | Epic, 10.11 (c) | Low | Dev |
| B33 | A place rejected on its own keeps an older custom pseudonym in its list entry | Epic, 10.11 (e) | Low | Dev |
| B34 | Custom pseudonym rows set `is_ambiguous=False`, unlike generated rows | Epic, 10.11 (f) | Low | Dev |
| B35 | A generated pseudonym for a one-word name leaves its last part untracked by the library | Epic, 10.11 (g) | Low | Dev |
| B36 | The list's preview can differ from the written file for a name that is not stored | Epic, 10.11 (h) | Low (accepted by Q-H) | PO (docs only) |
| B37 | A middle word of another person's three-word custom pseudonym is not refused | Epic, 10.11 (i) | Low (accepted residual) | PO |
| B38 | A linking word that is itself a surname ("Le", "Do", "Du") is not checked alone | Epic, 10.11 (j) | Low (accepted by Q-I) | PO |
| B39 | CLI and desktop differ under Q-H (typing the suggestion makes it custom in the CLI only) | Epic, 10.11 (k) | Low | PO |
| B40 | An ORG or LOCATION "Saint Zorbal" is accepted when the document says "Saint-Zorbal" | 10.11 gate OBS-001 (PO O1) | Low | PO |
| B41 | Detector-story record nits not re-audited at close-out: 10.1 DOC-001 to DOC-003, 10.3a DOC-001 and DOC-003 | 10.1 and 10.3a gates | Low | SM |
| B42 | Epic 9 carry-overs: REQ-001, REQ-002, corpus glob, Q7, guard hash list, main-vs-exam gap | Epic, Close-Out Record "Carried to Epic 9" | As recorded there | Epic 9 (already carried) |

Not repeated here: `docs/qa/backlog.md` (GUI-001, SEC-002, NER-001), which predates Epic 10 and stays as it is.

## Main CI on `b2042c7`

Checked by QA on 2026-10-15 between 20:35 and 20:51 UTC, through the GitHub API (`run_attempt`, `conclusion`, `head_sha`) and the job logs. **Every workflow is green on attempt 1, so nothing was recorded as red and no stop was needed.**

| Workflow | Run | Event | Attempt | Conclusion | Detail |
|---|---|---|---|---|---|
| CI - Test Matrix | `38802701586` | push | 1 | success | lint ok; ubuntu 3.11 (coverage) "2645 passed in 550.32s"; ubuntu 3.10 "2645 passed in 374.81s"; macOS 3.12 "2645 passed in 843.50s"; windows 3.12 "2496 passed, 3 skipped in 417.12s"; no xfail, no XPASS, no failure |
| Code Quality | `38802701912` | push | 1 | success | quality |
| CodeQL ("Push on main") | `38802701975` | dynamic | 1 | success | - |
| Documentation | `38802701402` | push | 1 | success | docs changed in #101 |
| Performance & Stability Tests | `38802702053` | push | 1 | success | `core/` changed; NFR1 means 0.35 s / 0.59 s / 0.87 s for 2k / 3.5k / 5k words |

- **Accuracy did not fire, as expected.** `accuracy.yaml` fires on a `main` push only for `gdpr_pseudonymizer/nlp/**`, `tests/accuracy/**` or the annotation and held-out folders, and #101 touches none of them.
- **Build Executables and Release did not fire, as expected.** They run on tags only.
- **Five runs is the full set.** `gh run list --commit b2042c7…` lists exactly these five.

## Files Written

- `docs/qa/assessments/10.5-trace-20261015.md`
- `docs/qa/assessments/10.7-trace-20261015.md`
- `docs/qa/assessments/10.8-trace-20261015.md`
- `docs/qa/assessments/10.9-trace-20261015.md`
- `docs/qa/assessments/10.10-trace-20261015.md`
- `docs/qa/assessments/10.11-trace-20261015.md`
- `docs/qa/assessments/epic-10-nfr-20261015.md`
- `docs/qa/assessments/epic-10-close-out-summary.md`

No code, test, gate file, story or epic was changed. No held-out or final-exam file was opened, listed, read or searched. No GUI was built, so the settings-file isolation was not needed.
