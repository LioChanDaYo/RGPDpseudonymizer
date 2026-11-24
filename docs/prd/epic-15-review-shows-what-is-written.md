# Epic 15: The Review List Matches the Written File - Brownfield Enhancement

**Epic Goal:** Every row the review list shows matches what is written in the output file. When two detections overlap or cover the same text, the list never shows two pseudonyms for that text when only one of them will be written. This keeps Story 11.5's promise, "the review list shows the pseudonym that will be written", in the desktop app (single document and batch) and in the command-line review, for every output format.

**Target Release:** the next release (none is planned). Story 15.1 lands on main first, before Story 14.1; no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.2 (Epic 11, released 2026-11-17). Epics 12 (Windows installer) and 13 (place pseudonyms) are done and also target the next release.
**Successor:** Epic 14 (first names on short text, Story 14.1), which is on a local branch that has not been pushed. Story 14.1 is rebased on Story 15.1 once 15.1 is merged. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

**Why a new epic (PM, 2026-11-22):** this is a fix to the review and writing steps, not to detection or to the pseudonym draw. Epic 14's scope rule allows Story 14.1 only ("Nothing else"). Epic 13's scope rule allows place pseudonyms only. Epic 11, which held Story 11.5, shipped and closed with v2.3.2.

---

## Scope Rule

One story, Story 15.1, on review rows whose pseudonym is never written. Nothing else. Out of scope: any detection change, which is Story 14.1's job.

Lionel's decisions: the old bug, where a review row is shown but never written, is fixed. It is fixed in its own story, Story 15.1, which lands on main before Story 14.1; it is not fixed inside Story 14.1. His words, word for word:

- Lionel, 2026-11-22. The question asked: "When a first name is already detected as a place, should CD leave it alone, so there's one row still replaced by a town (option 1)?" (Option 3 was to also fix, inside Story 14.1, the old bug where a review row is shown but never written.) His answer: "we need to fix the old bug".
- Lionel, 2026-11-22. The question asked: "Should the old bug get its own story, done before Story 14.1 (option a)?" His answer: "yes, its own story first".

CD is the candidate rule of Story 14.1 that the question refers to. These two answers also answer Story 14.1's question Q4.

---

## Existing System Context

PM checked on origin/main `1bb6f57`, 2026-11-22:

- **Detection keeps both detections of an overlap of different types.** `HybridDetector` (`gdpr_pseudonymizer/nlp/hybrid_detector.py` l.734-739): an exact match of different types keeps both and flags the regex entity; a partial overlap of different types flags the regex entity as ambiguous and keeps both. Each detection becomes its own review row, with its own pseudonym preview (`DocumentProcessor.build_pseudonym_previews`, `gdpr_pseudonymizer/core/document_processor.py` l.1886).
- **Writing keeps only one of them.** `DocumentProcessor._apply_replacements` (`core/document_processor.py` l.1475-1515) sorts the replacements by start, then longest span first, and drops any replacement that overlaps one already kept. Nothing records which replacement was dropped.
- **Every output format goes through that one function.** Text output: `finalize_document` (l.2001) and `process_document` (l.2082); PDF and DOCX inputs are read through `gdpr_pseudonymizer/utils/file_handler.py` and written as text. Excel and CSV: `_process_document_tabular` (l.2170) and `finalize_document_tabular` (l.2287) call `_apply_tabular_replacements` (l.2310), which calls `_apply_replacements` per cell (l.2345).
- **Story 11.5's notice does not see it.** `pseudonyms_changed` (`core/document_processor.py` l.119, l.166) lists a shown pseudonym that had to change at the end. A replacement dropped by `_apply_replacements` is not a change, so the list stays empty and no notice is shown: desktop single document (`gui/screens/validation.py` l.1199), desktop batch (`gui/screens/batch.py` l.1182), CLI `process` and `batch` (`cli/commands/process.py` l.247, `cli/commands/batch.py` l.628).
- **Where the rows are shown.** Desktop: `GUIValidationState` (`gui/models/validation_state.py` l.145, l.269), fed by `gui/workers/detection_worker.py` (l.237) and, for batch, `gui/screens/batch.py` (l.1053). Command line: the review shows "→ Pseudonym:" for each entity (`gdpr_pseudonymizer/validation/ui.py` l.299).
- **Not checked by the PM:** whether the dropped row's pseudonym is still saved in the mapping database and counted in the audit log. The SM checks it and writes what the fix does with it.
- **Technology stack:** Python 3.11-3.13, Poetry, spaCy 3.7 (`fr_core_news_lg`), PySide6-Essentials, pytest.

---

## Stories

### Story 15.1: Every Review Row Matches What Is Written

**Problem** (found by the PO of Story 14.1 on 2026-11-22, on origin/main `1bb6f57`; probes in `C:\Users\devea\Documents\GitHub\rgpd-analysis\r143\po\`, account in Story 14.1 v1.2, commits `62a043b` and `29afd94`):

- **Today, with no new rule** (`po143c.py`, `logs\po143c.log`: the real desktop path, base code, every row accepted, a fresh database per document):
  - the 25 dev-corpus documents give 1,488 review rows; 110 of them belong to an overlapping pair of different types (the 25 documents hold 75 such pairs of detections);
  - **32 of those rows, in 17 of the 25 documents, show a pseudonym that is written nowhere in the file**, and `pseudonyms_changed` is empty in all 25 documents, so the user is never told;
  - examples: in `hr_announcement.txt`, the organisation row « Product Management » shows « Fondation Recherche Médicale », which is never written, because the place « à Product Management » wins; in `interview_04.txt`, the place row « Hauts-de-France »; in `partnership_agreement.txt`, the person row « Cabinet Bredin Prat »;
  - how the 32 were counted: a text search for each shown pseudonym in the written file, limited to rows of such pairs. A title or a place word written differently could make a row look dropped when it is not, so the 32 may be too high. QA confirms them by hand. Rows outside a cross-type pair were not searched.
- **The end-to-end case** (`po143_e2e.py`, `logs\po143_e2e.log`: detection, grouping, previews, `GUIValidationState`, every row accepted, `finalize_document`, a fresh database outside the repo, Story 14.1's candidate rule CD patched in memory):
  - « Réponse de Diego : d'accord. » shows two review rows: the place « Diego » → « Boulogne-Billancourt » and the person « Diego » → « Lilian Breton »;
  - the file written reads « Réponse de Boulogne-Billancourt : d'accord. »;
  - the person's pseudonym is written nowhere, and `pseudonyms_changed` is empty, so the user gets no notice. « Kylian » behaves the same way;
  - on main as it is, that sentence shows one row and the file matches it. The case appears only with Story 14.1's rule. With that rule, it happens for 255 of the 7,390 grid answers (3.5%).
- **Why it matters.** Story 11.5's promise is "the review list shows the pseudonym that will be written" (`docs/stories/11.5.review-list-shows-written-pseudonym.story.md`). Overlapping or duplicate detections of the same text break it, with no notice. No real name is left in clear text, because one of the overlapping pseudonyms is written. But the review shows replacements that never happen.

**Scope (the SM writes the detailed story):**

- **Every row matches the file.** After the fix, every row the review list shows corresponds to what is written, in the desktop app (single document and batch) and in the command-line review, in every output format (text, including PDF and DOCX inputs, Excel and CSV). Two detections that overlap or cover the same text never both show a pseudonym when only one will be written.
- **The SM and the dev choose the mechanism.** For example: resolve overlaps before the review, merge the rows, show the losing row as "not written", or write what is shown. Each candidate is shown to Lionel before the mechanism is fixed in the story, with what the user sees and an example.
- **Lionel approves the French first.** Any new French text (a label, a notice, a message) is shown to Lionel word for word, with where it appears, an example and the English, and approved before it is committed.
- **Measured before and after:**
  - on the 25 dev documents: the 32 rows, confirmed by hand by QA, before and after the fix;
  - on Story 14.1's grid case « Réponse de X : ». On main this case needs both detections, a place and a person « Diego », put through the real review and write path by a test, since main's detector gives only the place. After Story 14.1 is rebased on Story 15.1, the case is checked again with Story 14.1's rule.
- **No name left in clear.** Text that is replaced today is still replaced after the fix.
- **No regression in detection.** Detection is out of scope; a mechanism that removes a detection before the review is still held to this gate:
  - the dev triggers the CI accuracy workflow on the story branch (`gh workflow run accuracy.yaml --ref <branch> -f reason="15.1"`), cites the run ID and pastes the `[Overall]`, `[PERSON]`, `[LOCATION]`, `[ORG]` and held-out lines from the `accuracy-results` artifact; QA re-runs it independently;
  - the baseline is the latest cited accuracy run on main; the SM finds it and records it in the story;
  - no agent opens, edits or runs `tests/accuracy/` locally, and no agent opens `tests/test_corpus/held_out/` or `tests/test_corpus/final_exam/`; held-out numbers are read only from the CI artifact;
  - any drop in an overall or per-type recall or precision stops the story and goes to Lionel with the numbers before merge.
- **The other rules still apply.** Story 11.5's check and notice, and Story 11.6's rule (no word of the document as a pseudonym), still hold.
- Ships with the next release (none is planned); it lands on main first, before Story 14.1, with a CHANGELOG `[Unreleased]` entry.
- Proof: tests first on CI. Before the release, Lionel hand-checks a document with two overlapping detections, in the desktop app and in the command line.
- Out of scope: any detection change (Story 14.1's job).

**Open questions (for Lionel; the story does not decide them):**

- **The mechanism.** Which candidate ships, given what the user sees in each case and an example.
- **Any new French text.** The exact French (and its English). Lionel approves it word for word.

**Acceptance (epic level):**

1. After the fix, every row the review list shows matches what is written, in the desktop app (single document and batch) and in the command-line review, in every output format. Two overlapping detections never both show a pseudonym when only one is written. Tests cover each of these paths.
2. The candidate mechanisms were shown to Lionel, each with what the user sees and an example, and he chose one before it was fixed in the story.
3. Every new French text was shown to Lionel (the French, where it appears, an example, the English) and approved word for word before it was committed.
4. On the 25 dev documents, the 32 rows (confirmed by hand by QA) are measured before and after; after the fix, no row shows a pseudonym that is not written.
5. Story 14.1's grid case « Réponse de X : » is tested on main with both detections put through the real review and write path, and checked again after Story 14.1 is rebased.
6. No text that is replaced today is left in clear after the fix.
7. CI accuracy run on the story branch cited with its run ID and pasted lines, QA re-run cited; no overall or per-type recall or precision drop against main's latest cited run, unless Lionel accepted it with the numbers in front of him.
8. Story 11.5's check and notice and Story 11.6's rule still hold.
9. Tests first on CI; full CI green; QA review; one read-only Codex review of the final head.
10. CHANGELOG `[Unreleased]` entry.
11. Before the release, Lionel's hand check of a document with two overlapping detections, in the desktop app and in the command line, passes.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

Story 15.1 lands on main with its CHANGELOG `[Unreleased]` entry, before Story 14.1, and ships with the next release, none planned. Before that release, Lionel hand-checks a document with two overlapping detections, in the desktop app and in the command line. No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] Existing mapping databases open and work unchanged.
- [ ] No CLI flag, mapping-table schema or file format changes, unless the mechanism Lionel chooses needs one and the story says so.
- [ ] Detection is unchanged, apart from what the accuracy run reports and Lionel accepted.

## Risk Mitigation

- **Primary risks:**
  - A mechanism that resolves overlaps before the review can remove a detection the user wanted, or lower accuracy.
  - A mechanism that writes what is shown can change which text is replaced, and leave part of a name in clear.
  - Desktop single, desktop batch and the command line build their rows in different places, so a fix in one can miss another.
  - Excel and CSV resolve overlaps per cell, text output per document.
- **Mitigation:**
  - The accuracy gate above, with any drop going to Lionel.
  - A test that text replaced today stays replaced.
  - Tests for each path and each output format.
  - Lionel's hand check before the release.
- **Rollback plan:** revert the story's merge commit; nothing is released until Lionel's go.

## Definition of Done

- [ ] Story 15.1 merged: every review row matches the written file, in the desktop app (single and batch) and the command line, in every output format; CHANGELOG `[Unreleased]` entry
- [ ] The mechanism chosen by Lionel from the candidates shown to him; every new French text approved word for word before it is committed
- [ ] The 32 rows confirmed by hand and measured before and after; the « Réponse de X : » case tested
- [ ] CI accuracy run and QA re-run cited; no recall or precision drop unless Lionel accepted it
- [ ] Tests-first commit and draft PR, QA review, read-only Codex review of the final head
- [ ] No regression in existing features (full CI green)
- [ ] Story 14.1 rebased on Story 15.1, its Q4 recorded as answered by Lionel's two decisions above
- [ ] Before the next release: Lionel's hand check of a document with two overlapping detections passes

---

## Story Manager Handoff

"Please write Story 15.1 for this epic (Lionel: "we need to fix the old bug", then "yes, its own story first"). Key considerations:

- This changes the review and the writing step of an existing Python/Poetry CLI and PySide6 desktop app, so that every review row matches what is written. Nothing else.
- Integration points: `HybridDetector` keeps both detections of a cross-type overlap (`nlp/hybrid_detector.py` l.734-739); `DocumentProcessor._apply_replacements` keeps one and drops the others silently (`core/document_processor.py` l.1475-1515); every output format goes through it (l.2001, l.2082, l.2170, l.2287, l.2345); `pseudonyms_changed` never sees a dropped replacement; the desktop rows (`gui/models/validation_state.py`, `gui/workers/detection_worker.py`, `gui/screens/batch.py`) and the CLI review (`validation/ui.py` l.299).
- Re-measure the 32 rows in 17 documents with your own probe; QA confirms them by hand. Check whether a dropped row's pseudonym is saved in the mapping database and counted in the audit log.
- Show Lionel each candidate mechanism with what the user sees and an example; he chooses. Any new French text: the French, where it appears, an example and the English; he approves word for word before it is committed.
- Test Story 14.1's grid case « Réponse de X : » on main by putting both detections through the real review and write path.
- Accuracy: the CI accuracy workflow on the story branch, cited run ID and pasted lines, QA re-run, held-out lines from the artifact; any drop stops for Lionel. No agent opens `tests/accuracy/`, `tests/test_corpus/held_out/` or `tests/test_corpus/final_exam/`. Record main's latest cited run as the baseline.
- Next release, on main first, before Story 14.1; tests first; QA; one read-only Codex review; Lionel's hand check before the release.
- Out of scope: detection changes (Story 14.1).
- Each story must include verification that existing functionality remains intact.

The epic should leave the review list showing exactly what will be written, so what the user approves is what they get."
