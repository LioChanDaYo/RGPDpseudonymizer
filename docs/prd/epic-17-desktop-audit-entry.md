# Epic 17: The Desktop App Writes a Processing Entry in the Audit Log - Brownfield Enhancement

**Epic Goal:** Every document the desktop app writes after a review gets one PROCESS entry in the audit log, the same entry the command line writes for the same document. Today the two desktop paths that review (single document, and batch with review) write none, so an audit export after desktop use shows no processing at all. A desktop document that fails gets the same failure entry as on the command line, with its file.

**Target Release:** the next release (none is planned). No tag and no PyPI release without Lionel's explicit go.
**Predecessor:** Epics 14, 15 and 16 (Stories 14.1, 15.1 and 16.1), merged on main (`379eb2b`). Epics 12 and 13 are done and also target the next release.
**Successor:** none planned. Story 16.2 (English texts) is independent of this epic: either can land first (see Order). Epics 8 (v2.4) and 9 (v3.0) are unchanged.

**Why a new epic (PM, 2026-11-27):** this changes what the desktop app writes in the audit log, nothing else. It touches no detection, no review list, no written file and no text on screen. Epic 15's scope rule allowed Story 15.1 only; its SM recorded the missing desktop entry as "outside this story's scope", to raise with Lionel (`docs/stories/15.1.review-shows-what-is-written.story.md` l.103, l.657). Epic 16 is about English texts.

---

## Scope Rule

One story, Story 17.1: the desktop app writes the same audit entry as the command line, for each document, on success and on failure. Nothing else. Out of scope: any new or changed text on screen; any change to what the command line writes; TD-011 (detected names in debug log lines, `docs/BACKLOG.md`).

Lionel's decision, word for word:

- Lionel, 2026-11-27. He first asked "Why the processed suggestion?" and was told what the audit log is for and what is missing. The question asked: "Should the desktop app write a "processed" entry in the audit log for each document: its own small story, or a backlog line?" His answer: "Yes write a proceeded entry, own small story".

What it means: the desktop app writes a processing entry (operation type PROCESS) for each document, in its own small story, Story 17.1.

---

## Existing System Context

PM checked on origin/main `379eb2b`, 2026-11-27, by reading the code and with the probe `C:\Users\devea\Documents\GitHub\rgpd-analysis\r171\pm\pm171.py` (log `logs\pm171.log`). The probe runs a short made-up French text (4 lines, 10 detections, no corpus file) through each path on a fresh database, offscreen, with the real `DetectionWorker` and `FinalizationWorker`, every row accepted. It ran in the main checkout's Poetry environment, whose product code equals `379eb2b` (`git diff origin/main -- gdpr_pseudonymizer`: empty).

**What the audit log is.** The `operations` table of the encrypted database (`gdpr_pseudonymizer/data/models.py` l.76-116), written through `AuditRepository.log_operation` (`data/repositories/audit_repository.py` l.54) and exported by `gdpr-pseudo export audit.json` (or `.csv`: `export_to_json` l.226, `export_to_csv` l.319). Each row holds: operation type, time, the files, the model name and version, the theme, `entity_count`, the processing time, success, an error message, and `user_modifications`. A PROCESS row holds no detected name and no pseudonym: `user_modifications` is `None` and the error message goes through `_sanitize_error_message` (`core/document_processor.py` l.1854).

**Who writes what today:**

| Path | Code | Audit entry today | Probe |
|---|---|---|---|
| CLI `process` (with review) | `cli/commands/process.py:219` → `process_document` | one PROCESS row per document (`_log_success_operation`, `core/document_processor.py:1832-1851`, called at `:2141`; Excel/CSV at `:2234`) | 1 row, `entity_count` 10, `fr_core_news_lg-3.8.0` |
| CLI `batch`, sequential with review | `cli/commands/batch.py:620` → `process_document` | one PROCESS row per document | (same code as `process`) |
| CLI `batch`, parallel workers | `cli/commands/batch.py:126` → `process_document(skip_validation=True)` | one PROCESS row per document | (same code as below) |
| Desktop batch without review | `gui/workers/batch_worker.py:330` → `process_document(skip_validation=True)` | one PROCESS row per document | 1 row, `entity_count` 10 |
| **Desktop single document (review)** | `DetectionWorker` (`gui/workers/detection_worker.py:175`), then `FinalizationWorker` (`gui/workers/finalization_worker.py:121`) → `finalize_document` | **none** | **0 rows** (10 entities sent) |
| **Desktop batch with review** | `batch_worker.py:325-327` → `_process_with_validation`: read and detect `:420-421`, then `finalize_document` `:460` | **none** | **0 rows** (10 entities sent) |
| CLI `delete-mapping`, desktop deletion | `cli/commands/delete_mapping.py:189-207`, `gui/workers/database_worker.py:318-320` | ERASURE | not run |
| Replacing a stored pseudonym (Story 11.7) | `core/saved_own_words.py:513-528` | REPLACEMENT | not run |

- **Why the review paths write none.** `finalize_document` (`core/document_processor.py:2015-2073`) writes the file (`:2058`) and returns; it never calls `_log_success_operation`. It is not given the input file either: its signature has no input path, and its result has `input_file=""`.
- **No path writes a BATCH row.** "BATCH" appears only in `audit_repository.py` docstrings and in the export filter's help text. CLI `batch` writes one PROCESS row per document. So every desktop path writes PROCESS, like its command-line counterpart.
- **The count.** `entity_count` is `len(validated_entities)`, every entity sent to be written, written or not (Lionel's Q5 in Story 15.1, 2026-11-23, "yes, a"). The desktop sends the same count as the CLI: the probe sends 10 on both desktop review paths and the CLI row says 10; Story 15.1's PO probe, on the 25 dev documents, sends 2,324 entities on desktop single and on desktop batch and logs 2,324 on the CLI (`rgpd-analysis\r151\po\logs\po151.log` l.4, l.71, l.113; 0 audit rows after the 25 desktop single finalizes, l.21).
- **The model version.** `_get_model_version` (`core/document_processor.py:2417`) asks the processor's own detector. `FinalizationWorker` builds a fresh processor (`finalization_worker.py:108`) that never detected, so its version reads `fr_not_loaded-unknown` (probe, 0.00 s) where the CLI row says `fr_core_news_lg-3.8.0`. Desktop batch with review detects and finalizes on the same processor (`batch_worker.py:278`, `:421`, `:460`), so its version is loaded.
- **The processing time.** The CLI's clock starts before the file is read and stops after it is written, so it includes detection and the human review (probe: 11.1 s; 3.1 s without review). `finalize_document`'s clock covers only the write (probe: 0.14 s for the whole `FinalizationWorker`).

**Failures today** (probe):

| Failure | Code | Audit entry today |
|---|---|---|
| CLI: the write fails | `process_document` → `_handle_processing_error` (`:1888-1910`) → `_log_failed_operation` (`:2439-2471`) | one PROCESS row, `success` false, the input file, `entity_count` 0, model version loaded, sanitized error |
| CLI: the input cannot be read | the same, the read is inside `process_document`'s `try` | one PROCESS row, `success` false, the input file, `entity_count` 0, `fr_not_loaded-unknown` (detection never ran) |
| **Desktop single or batch with review: the write fails** | `finalize_document`'s `except` calls `_handle_processing_error(e, "", …)` (`:2073`) | one PROCESS row, `success` false, but **files `[""]`** and **`fr_not_loaded-unknown`** on desktop single |
| **Desktop single: the input cannot be read or detection fails** | `DetectionWorker` catches it (`detection_worker.py:197`, `:211`) and shows a message | **none** |
| **Desktop batch with review: the input cannot be read or detection fails** | `batch_worker.py:420-421`, caught at `:368` / `:376` | **none** |
| Desktop batch without review, any failure | inside `process_document` | as the CLI |
| A review stopped before writing (CLI `q` or Ctrl+C; desktop cancel) | `_run_validation` re-raises `KeyboardInterrupt` (`:637-639`), which `process_document`'s `except Exception` does not catch; the desktop never calls finalize | none on either side |

So a desktop failure at the write already leaves a row, without its file, and a desktop failure before the review leaves none, where the CLI leaves one.

**Not on any app path:** `ProcessingWorker` (`gui/workers/processing_worker.py:49`; only tests build it; it calls `process_document`, so it logs) and `finalize_document_tabular` (`core/document_processor.py:2304`; only tests call it). Both desktop review paths read Excel and CSV files as flat text (`detect_entities` → `read_file`; `batch_worker.py:420`) and write them through `finalize_document`, where the CLI detects cell by cell (`_process_document_tabular`, `:2159`). So for `.xlsx` and `.csv` the desktop and the CLI can detect different counts for reasons outside this epic.

**Where the entries show.** The export (`gdpr-pseudo export`), `gdpr-pseudo stats` (operation counts, `cli/commands/stats.py:103-109`) and the desktop database screen's « Dernière opération : %3 » (`gui/workers/database_worker.py:155-168`, `gui/screens/database.py:554`). After desktop-only use, that screen says « aucune » today.

**Technology stack:** Python 3.11-3.13, Poetry, SQLAlchemy 2.0 (SQLite, encrypted fields), PySide6-Essentials, pytest.

---

## Stories

### Story 17.1: The Desktop App Writes a Processing Entry in the Audit Log

**Problem** (PM, 2026-11-27, origin/main `379eb2b`, `pm171.log`; first seen by Story 15.1's PO, `po151.log` l.21):

- The desktop single-document path and the desktop batch with review write the file and log nothing: 0 audit rows after a desktop finalize, where the CLI logs one PROCESS row for the same document.
- A desktop finalize that fails logs a failure row with no file (`[""]`) and, on single document, no model version.
- A desktop document that cannot be read, or whose detection fails, logs nothing; the CLI logs a failure row.
- Why it matters: the audit log is the record a user shows of what was processed, when and with which model (Story 2.5). After desktop use it shows nothing, and the database screen's « Dernière opération » stays « aucune ».

**Scope (the SM writes the detailed story):**

- **One PROCESS entry per document written, on both desktop review paths**, desktop single (`FinalizationWorker`) and desktop batch with review (`_process_with_validation`), each equal to the CLI's entry for the same document:
  - operation type PROCESS, as CLI `process` and CLI `batch` write;
  - files: the input document's path (what the CLI writes), never the temporary output file;
  - `entity_count`: `len(validated_entities)`, every entity sent, written or not (Lionel's Q5, Story 15.1);
  - model name and model version: the model that detected the document, as the CLI writes it (`fr_core_news_lg-3.8.0` today), never `fr_not_loaded-unknown` when detection ran. The SM chooses how the version reaches the finalize (for example carried from the detection), without loading the spaCy model a second time just for the version;
  - theme, `success` true, no error message, `user_modifications` `None`;
  - the time is the row's own; `processing_time_seconds` cannot match the CLI's (it includes the human review there). The SM writes what the desktop measures and says so in the story.
- **One failure entry per document that fails, where the CLI writes one:**
  - the write fails (desktop single, desktop batch with review): one PROCESS row, `success` false, with the input file and the model version as the CLI's, `entity_count` 0 as the CLI's, the sanitized error. Today's row with files `[""]` is replaced by it, never added to it;
  - the input cannot be read, or detection fails (`DetectionWorker`, `batch_worker.py:420-421`): one PROCESS failure row with the input file, as the CLI's;
  - a failure the CLI cannot log either logs nothing, as today: for example a wrong passphrase, where `_log_failed_operation` cannot open the database either and only logs to the application log (`:2454-2471`);
  - a review stopped or cancelled before the write logs nothing, as on the CLI.
- **No double entries.** Desktop batch without review (`batch_worker.py:330`), CLI `process` and CLI `batch` keep exactly one row per document. A desktop document that fails at the write gets one row, not one from the finalize and one from the worker.
- Ships with the next release (none planned), with a CHANGELOG `[Unreleased]` entry in the project's usual style.
- Out of scope: any new or changed text on screen; what the CLI writes; the audit schema and the export format; Excel and CSV detection on the desktop (cell by cell or flat text); `ProcessingWorker` and `finalize_document_tabular`, which no app path uses (left as they are, unless a shared change reaches them, which the SM records); TD-011.

**Open questions:** none for Lionel. The story adds no French text. The model-version carrier and the time measured are the SM's technical choices, recorded in the story.

**Acceptance (epic level):**

1. Tests first on CI: they fail on `379eb2b` for each missing entry and pass after the fix.
2. The real desktop single path (`DetectionWorker` then `FinalizationWorker`) and the real desktop batch with review (`BatchWorker` with review on) each leave exactly one PROCESS row per document written.
3. For the same text input (`.txt`, `.md`, `.pdf`, `.docx`) and the same decisions (every row accepted on both sides; the CLI accepts known names without showing them, the desktop lets the user reject them), each desktop row equals the CLI `process` row field by field, apart from the timestamp, `processing_time_seconds` and the path: operation type, `entity_count`, model name, model version, theme, success, error message, `user_modifications`.
4. Each failure case above leaves the row the CLI leaves, with the input file; the `[""]` row is gone; a review stopped before the write leaves none.
5. Desktop batch without review, CLI `process` and CLI `batch` (sequential and parallel) still leave exactly one row per document; a test pins it.
6. No detected name and no pseudonym in any audit field of the new rows (a test reads every field of the rows written for a text with known names).
7. A database made before the fix opens and works unchanged, and its export reads the same; the export's fields and format are unchanged.
8. Accuracy identical to the baseline, since detection is untouched: the dev triggers `accuracy.yaml` on the story branch, cites the run ID and pastes the `[Overall]`, `[PERSON]`, `[LOCATION]`, `[ORG]` and held-out lines from its `accuracy-results` artifact; QA re-runs it independently. Baseline: Story 14.1's G1 run `45776619159` on `4367cfe` (saved copy `C:\Users\devea\Documents\GitHub\rgpd-analysis\r143\acc\r45776619159\accuracy-output.txt`, sha256 `79478a04ddb126427bba2c09cbebd613f1b929eb5b3bd7d22da50f8a6d245cb1`), for example `[Overall] P=0.8001 R=0.8474 F1=0.8231 TP=1877 FP=469 FN=338`. Any bracketed line that differs stops the story and goes to Lionel with the numbers. No agent opens, edits or runs `tests/accuracy/`, `tests/test_corpus/held_out/` or `tests/test_corpus/final_exam/` locally.
9. Full CI green; QA review; Codex reviews the final head read-only, under the stopping rule.
10. CHANGELOG `[Unreleased]` entry.
11. Before the next release, Lionel hand-checks an audit export after using the desktop app (one document, and a batch with review).

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- Codex reviews the final head read-only, under the stopping rule. Codex only reviews. Claude BMAD agents write the code.

---

## Order

- Independent of Story 16.2. Story 17.1 adds no `tr()` text and touches no `.ts` or `.qm` file. The files it is expected to change (`core/document_processor.py`, `gui/workers/finalization_worker.py`, `gui/workers/batch_worker.py`, `gui/workers/detection_worker.py`) hold no `tr()` call: their messages are plain French strings (`grep -nE "(^|[^s_a-zA-Z])tr\("` on the four files: no match). Story 16.2 changes `tr()` texts and the `.ts` files.
- If the SM has to touch a screen (for example `gui/screens/validation.py:1183-1191`, where `FinalizationWorker` is built), the change stays away from its `tr()` lines, so a later Story 16.2 merges cleanly. The SM checks it against main when the story is written, and again before merge if Story 16.2 has landed.

---

## Release

Story 17.1 lands on main with its CHANGELOG `[Unreleased]` entry and ships with the next release, none planned. Before that release, Lionel hand-checks an audit export after desktop use. No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] No detected name and no pseudonym in any audit field: `user_modifications` stays `None`, error messages stay sanitized. The file path is recorded as the CLI records it.
- [ ] No schema change and no migration: databases made before the fix open and work unchanged; their existing rows are untouched.
- [ ] The export format (JSON and CSV fields) is unchanged.
- [ ] What the CLI writes is unchanged.
- [ ] No new or changed text on screen. The values shown change as intended: after desktop use, « Dernière opération » shows the day of the last desktop document instead of « aucune », and `gdpr-pseudo stats` counts the desktop documents.
- [ ] Detection is unchanged (accuracy gate above).

## Risk Mitigation

- **Primary risks:**
  - A double row: the finalize and a worker both log the same document, or a path that logs today logs twice.
  - A wrong model version on desktop single (`fr_not_loaded-unknown`), or a second spaCy load (seconds, several hundred MB) just to read the version.
  - A name reaching an audit field through an error message.
  - A failure row lost, or written twice, when the finalize and the worker both handle the failure.
- **Mitigation:**
  - A test per path pins exactly one row per document, success and failure.
  - A test pins the desktop single row's model version equal to the CLI's.
  - A test reads every field of the new rows for names and pseudonyms.
  - Lionel's hand check of an export before the release.
- **Rollback plan:** revert the story's merge commit; no row already written needs undoing, and nothing is released until Lionel's go.

## Definition of Done

- [ ] Story 17.1 merged: desktop single and desktop batch with review write one PROCESS row per document, equal to the CLI's apart from the timestamp, the processing time and the path; failures logged as the CLI logs them, with the input file; no double rows; CHANGELOG `[Unreleased]` entry
- [ ] CI accuracy run and QA re-run cited, every bracketed line identical to the baseline `45776619159`
- [ ] Tests-first commit and draft PR, QA review, read-only Codex review of the final head under the stopping rule
- [ ] No regression in existing features (full CI green)
- [ ] Before the next release: Lionel's hand check of an audit export after desktop use passes

---

## Story Manager Handoff

"Please write Story 17.1 for this epic (Lionel, 2026-11-27: "Yes write a proceeded entry, own small story"). Key considerations:

- This changes what the desktop app writes in the audit log of an existing Python/Poetry CLI and PySide6 desktop app. Nothing else: no text on screen, no detection, no review, no written file, no CLI change.
- Integration points: `finalize_document` (`core/document_processor.py:2015-2073`) logs nothing on success and a `[""]` row on failure (`:2073`); `_log_success_operation` (`:1832-1851`), `_handle_processing_error` (`:1888-1910`) and `_log_failed_operation` (`:2439-2471`) are what the CLI uses; `_get_model_version` (`:2417`) reads the processor's own detector; `FinalizationWorker` (`gui/workers/finalization_worker.py:108`, `:121`, input path at `:59`); `BatchWorker._process_with_validation` (`gui/workers/batch_worker.py:402-466`, its `except` at `:368`, `:376`); `DetectionWorker` (`gui/workers/detection_worker.py:164-211`).
- Re-measure every path with your own probe on main (success and each failure case), on synthetic text or through the real workers offscreen; no corpus file is needed.
- One row per document on every path; the desktop row equal to the CLI row apart from the timestamp, the processing time and the path; the model version that detected; `entity_count` = entities sent (Lionel's Q5, Story 15.1). Write in the story what the desktop processing time measures.
- Accuracy: CI run on the story branch with its run ID and pasted lines, QA re-run, baseline `45776619159`, any change stops for Lionel. No agent opens `tests/accuracy/`, `tests/test_corpus/held_out/` or `tests/test_corpus/final_exam/`.
- Independent of Story 16.2: no `tr()` text and no `.ts` or `.qm` file.
- Next release; tests first; QA; read-only Codex review under the stopping rule; Lionel's hand check of an export after desktop use before the release.
- Each story must include verification that existing functionality remains intact.

The epic should leave the audit log recording every document the app writes, whichever way the user writes it."
