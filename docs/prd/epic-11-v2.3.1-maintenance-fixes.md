# Epic 11: v2.3.1 — Maintenance Fixes - Brownfield Enhancement

**Epic Goal:** Ship a small v2.3.1 that raises the Python floor to 3.11 so a dependency refresh can close the open Dependabot alerts on `poetry.lock`, tests Python 3.13 in CI, and fixes two bugs found by the v2.3.0 release review: custom pseudonyms refused at finalization, and the import "replace" answer ignored. It also fixes the passphrase traps and the hardcoded version label found by Lionel's hand check of a 2.3.1 Windows build, and a real leak: a generated pseudonym can reuse a word of the document, and rows stored by 2.3.0 or earlier can already hold such a pseudonym. It also stops two people getting one pseudonym through values shared by the first-name and last-name lists.

**Target Release:** v2.3.1. The release itself is a separate step after all six stories merge (see Release); no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.0 (Epic 10, released 2026-11-03)
**Successor:** none set. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

---

## Scope Rule

Exactly eleven items in six stories enter 2.3.1: Python 3.11 floor with the dependency refresh (Story 11.1), Python 3.13 in CI (Story 11.3), the two bugs (Story 11.2), generated pseudonyms that reuse a word of the document and two people given one pseudonym through values shared by the first-name and last-name lists (Story 11.6), four desktop problems (Story 11.4: the short-passphrase trap on a new database, the wrong-passphrase trap on a single document, the same trap in a batch, and the version label), and stored pseudonyms that leak a word of their own name (Story 11.7). Nothing else. Story 11.5 moves to v2.3.2. KL-001 to KL-005 and the two-Maries limitation (backlogged by Story 11.1) stay in `docs/BACKLOG.md` with their pull triggers.

Lionel's decisions, word for word:

- Story 11.2, Lionel, 2026-11-04: of the v2.3.0 release-review findings, custom pseudonyms refused at finalization and import "replace" ignored are fixed in 2.3.1; the other five are known limitations, reopened only on a real user report.
- Story 11.1: "drop 3.10 in 2.3.1 (beware; 2.3.1 already has stuff planned in it)" (2026-11-05).
- Story 11.3, Lionel, 2026-11-05: Python 3.13 is tested in CI so that it is not untested anymore, as a separate small story right after 11.1, inside 2.3.1. His words: "we're getting 3.10 out of CI right? how about we add 3.13, then? so that it's not untested anymore?"
- Story 11.4, Lionel, 2026-11-10: the passphrase trap and the version label are fixed in one small story before the tag; the second passphrase trap (a wrong passphrase on an existing database) is fixed in it too, with the existing message « Phrase secrète incorrecte. Veuillez réessayer. ».
- Story 11.5, Lionel, 2026-11-10: the review list must show the pseudonym that will be written. His words: "indeed, if i knew it was systematic, i wouldn't have accepted it. as usual, i don't care if it's old, i want it fixed."
- Story 11.6, Lionel, 2026-11-10: the leak fix ships first as its own small story, then 11.4, then the 2.3.1 release; the rest of 11.5 (the list shows the written pseudonym, the title gap, the batch preview theme) moves to 2.3.2.
- Stories 11.4, 11.6 and 11.7, Lionel, 2026-11-10: the batch screen's wrong-passphrase trap is fixed in 11.4; stored rows whose pseudonym leaks a word of their own name are dealt with in 2.3.1 (Story 11.7); 11.6 checks every word of a drawn organisation or place against the document, not only the whole value. His words: "batch in 11.4; stored rows in 2.3.1; widen".
- Stories 11.6 and 11.7, Lionel, 2026-11-10: after a replacement, the old pseudonym is freed (as `delete-mapping` does); a place or organisation is reported only when the shared part is its whole name, its whole pseudonym, or a place from the pseudonym library; the app gives a notice when a document is written; every value that is also a first name is removed from the last-name list (Story 11.6). His words: "1) forget 2) report only real leaks 3) when a document is written ; about the new bug: remove all shared from last name list".

---

## Existing System Context

- **Current relevant functionality:** v2.3.0 on PyPI (`gdpr-pseudonymizer`) and as standalone desktop builds. Custom pseudonyms ("Changer le pseudonyme", CLI [C]) are checked during review and again at finalization (`gdpr_pseudonymizer/core/custom_pseudonym.py`). `import-mappings` copies mappings from another database (`gdpr_pseudonymizer/cli/commands/import_mappings.py`).
- **Technology stack:** Python 3.10-3.12 (`pyproject.toml` classifiers; `python = ">=3.10,<3.14"`), Poetry, spaCy 3.7 (`fr_core_news_lg`), PySide6-Essentials, pytest, GitHub Actions.
- **Integration points:** `pyproject.toml`, `poetry.lock`, `mypy.ini`, `.github/workflows/ci.yaml` (oldest-Python job), `tests/unit/test_project_config.py`, `gdpr_pseudonymizer/core/custom_pseudonym.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`.

---

## Stories

Story 11.1 lands first (merged 2026-11-05). Story 11.3 lands next. Story 11.2 branches from main after 11.3 merges. The numbers stay: 11.2 keeps its approved number and text. 11.1, 11.3 and 11.2 are merged, and the first release commit (`chore(release): v2.3.1`, #121) is on main; the tag is not pushed. Story 11.6 lands next, then Story 11.4, then Story 11.7, then the release (a second release commit). Story 11.5 moves to v2.3.2.

### Story 11.1: Python 3.11 Floor and Dependency Security Refresh

**Problem:** 61 open Dependabot alerts on `poetry.lock`, 6 of them critical (5 Pillow, 1 certifi). None reaches users: `gdpr-pseudo-gui.spec` excludes PIL and all three build jobs use that spec; the frozen app makes no network calls and bundles the spaCy model; PyPI installs do not use the lock. But the fixed Pillow 13.0.0 and filelock 4.2.1 require Python 3.11+, so with the 3.10 floor a lock refresh closes only 8 of the 61. Python 3.10 is end of life. PyPI downloads over the last 90 days: 3.10 = 4, 3.11 = 17, 3.12 = 20. pip on 3.10 keeps resolving 2.3.0 (requires-python), so 3.10 users are not broken; they just do not get the 2.3.1 fixes.

**Scope (the SM writes the detailed story):**

- Raise the Python floor to 3.11 in `pyproject.toml`, `mypy.ini` and the CI oldest-Python job; update `tests/unit/test_project_config.py`.
- Targeted lock refresh with Poetry 2.2.1: pillow, certifi, urllib3, setuptools, filelock, fpdf2, black.
- Ruff target: py311 with the `ruff --fix` UP017 rewrites, or stay on py310. The story decides.
- Current English user docs. French user docs only with Lionel's word-for-word approval of the text. History docs (past CHANGELOG entries, stories, QA reports) untouched.
- CHANGELOG `[Unreleased]` entry.
- Two `docs/BACKLOG.md` entries: this item itself, and the known limitation below.
- The alerts close when this story merges to main.

**Known limitation to backlog in this story, not fixed in 2.3.1** (Lionel 2026-11-05, "backlog it"): with the PER-001 style only (`--theme neutral_id`), after « Marie Dubois » and « Marie Dupont », a bare « Marie » gets PER-001-P in one run and PER-002-P in later runs. The default style is consistent. Pull trigger: a `neutral_id` user reports it.

**Orchestrator step, not a dev task:** the GitHub ruleset "Protect main" requires the check `test (ubuntu-22.04, 3.10, false)` by name. Once the CI job is renamed, the ruleset must be updated to the new check name. Lionel said yes on 2026-11-05.

### Story 11.2: 2.3.1 Fixes

Two items, unchanged from the release review. Each is named by its problem everywhere, never by a number alone: the QA report and the Codex review number them differently.

- **Custom pseudonyms refused at finalization** (`docs/BACKLOG.md` BUG-001; QA's VERIFY.md "Finding 5"; final Codex release review "finding 2"). Two custom pseudonyms are each accepted during review, then both refused at finalization, and the message wrongly blames the mapping database. Example: two people share a first name; « Aurore Bruneau » is chosen for « Élodie Martin » and « Aurore Le Goff » for « Élodie Dupont ». A two-word surname in a custom pseudonym (« Le Goff ») is split as first name « Aurore Le » plus surname « Goff ». Side effect: after « Inès Le Goff » is stored for « Ségolène Dupont », a later « Ségolène » gets « Inès Le Roque ». Code: `gdpr_pseudonymizer/core/custom_pseudonym.py:468`.
- **Import "replace" ignored** (`docs/BACKLOG.md` BUG-002; QA's VERIFY.md "Finding 8"; final Codex release review "finding 5"). With `import-mappings --no-skip-duplicates`, answering yes to « Replace existing mapping? » replaces nothing: it inserts a new row, the unique key refuses it, and the command counts the row as skipped. Code: `gdpr_pseudonymizer/cli/commands/import_mappings.py:182` and `:217-218`.

### Story 11.3: Python 3.13 in CI

**Problem:** Python 3.13 can be installed today but nothing tests it. Facts measured by the orchestrator on 2026-11-05:

- The old blocker is gone. `docs/BACKLOG.md` MON-005 waited because thinc had no Python 3.13 wheels. The locked thinc 8.3.13, spaCy 3.8.14, numpy 2.2.6, srsly 2.5.3, blis 1.3.3, cymem, preshed and murmurhash all publish cp313 wheels on PyPI.
- `pyproject.toml` already allows `python = ">=3.11,<3.14"`, so `pip install gdpr-pseudonymizer` on 3.13 installs the CLI today, untested. The docs say "3.13+ not yet tested".
- The GUI extra's PySide6 marker is `python = ">=3.11,<3.13"`, so on 3.13 `pip install gdpr-pseudonymizer[gui]` installs without PySide6 and `gdpr-pseudo-gui` cannot start.
- Moving the marker alone is not enough. PySide6-Essentials 6.7.0 through 6.8.0.1 declare `requires_python "<3.13,>=3.9"`, and pip honours it; the abi3 wheel tag does not help. `poetry.lock` line 3121 says the same for the locked 6.7.3. The first release that accepts 3.13 is 6.8.0.2. The latest 6.8 is 6.8.3 (`requires_python "<3.14,>=3.9"`, depends on `shiboken6==6.8.3`).
- pytest-qt 4.5.0 aborts the whole test session when no Qt binding is installed, so a 3.13 job without PySide6 cannot run at all.
- The PySide6-Essentials 6.8.3 macOS wheel is `macosx_12_0_universal2`; 6.7.3's was `macosx_11_0_universal2`. So the desktop app, and the macOS installer, now needs macOS 12 or later instead of 11. Linux x86_64 stays `manylinux_2_28`; Windows `win_amd64` is unchanged.
- The lock has pyinstaller 6.21.0, pyinstaller-hooks-contrib 2026.6 and pytest-qt 4.5.0.
- After Story 11.1, `.github/workflows/ci.yaml` has two ubuntu-22.04 Python 3.11 test jobs, one with coverage and one without. The one without coverage adds nothing.
- PyPI downloads over pypistats' ~180 days (a longer window than the 90 days quoted in Story 11.1): 3.11 = 47, 3.12 = 28, 3.13 = 2, 3.14 = 1.

**Scope (the SM writes the detailed story):**

- The ubuntu-22.04 Python 3.11 test job without coverage becomes ubuntu-22.04 Python 3.13 and runs the full suite, GUI tests included. CI keeps 4 test jobs; 3.11 stays tested by the coverage job.
- Lionel, 2026-11-05: "Move the desktop app to PySide6 6.8.3 for everyone". So: `PySide6-Essentials = {version = "~6.8.3", optional = true, python = ">=3.11,<3.14"}`; add the `Programming Language :: Python :: 3.13` classifier.
- Update `tests/unit/test_project_config.py`: the classifiers test, the PySide6 marker test and the CI-job test all pin today's values.
- Re-lock. pyside6-essentials and shiboken6 move 6.7.3 → 6.8.3 on every Python, plus the stanza bump below (with orjson). **Any other package movement stops the story** for a report.
- Bump stanza 1.14.0 → 1.15.0 (Dependabot alert #109, dev-only, excluded from the installers). stanza 1.15.0 adds one new dev-only requirement, orjson (3.13.0, measured on PyPI 2026-11-05). Apart from pyside6-essentials and shiboken6, only stanza and orjson may move; otherwise stop for a report. Lionel, 2026-11-05: "Stanza : a", then "clear, yes to orjson".
- **If a test fails on 3.13**, the story fixes it only if the fix is small and real. Otherwise the story stops and the orchestrator reports to Lionel.
- Every installer ships Qt 6.8. The orchestrator runs `build-executables.yaml` on the branch head before merge. The dev runs the GUI test suite locally on Windows with the new lock. Before the 2.3.1 tag, Lionel opens the desktop app once from a branch or release-candidate build (a release-step check, his).
- Current user docs say Python 3.11 to 3.13 for both the CLI and the desktop app, and that the desktop app needs macOS 12 or later wherever they state a macOS version for it (for example `docs/architecture/1-introduction.md:71` says macOS 11+): English, and French only with Lionel's word-for-word approval of the text. History docs (past CHANGELOG entries, stories, QA reports) untouched.
- CHANGELOG `[Unreleased]` entry: Python 3.13 is tested; the desktop app moves to Qt 6.8 (PySide6 6.8.3); macOS 12 is now the minimum for the desktop app.
- `docs/BACKLOG.md` MON-005: a dated 2026-11-05 paragraph with the measurement, including the correction that PySide6 6.7 did not support 3.13; closed for 3.13. 3.14 stays monitored.

**Orchestrator step, not a dev task:** the "Protect main" ruleset (12689559) requires the check `test (ubuntu-22.04, 3.11, false)` by name. Just before Lionel's merge, it is renamed to `test (ubuntu-22.04, 3.13, false)`. This needs Lionel's yes, not yet asked.

### Story 11.6: Generated Pseudonyms Never Reuse a Word of the Document

**Problem** (found by Story 11.5's SM, 2026-11-10; logs `C:\Users\devea\Documents\GitHub\rgpd-analysis\r115\sm\logs\collide_own_2000.log` and `leak_probe.log`): a real leak. The pseudonym library draws first names, last names, places and organisations without looking at the document, so a name can get one of its own words back: « Élodie Martin » → « Élodie Lucas » (the real first name kept), « Marseille » → « Marseille », « Lyon » → « Lyon ».

- Over 2,000 runs per document on five realistic French texts, 0.75% to 4.85% of runs left a word of a name in clear (about 1 run in 133 to 1 in 21, depending on the document; measured per run by Story 11.6's SM, correcting an earlier per-name count of 1 in 70 to 1 in 15).
- Same in 2.3.0 and 2.2.0. A forced end-to-end probe wrote « Élodie Martin a présenté le budget à Marseille. » unchanged on main, 2.3.0 and 2.2.0.
- The milder cousin: a pseudonym part equals another real name of the same document (0.50% to 16.35% of runs, measured per run by Story 11.6's SM). Seen once in 11.5's investigation: Martin → "Dupont" while the real Duponts → "Wagner". Lionel had decided, 2026-11-10: "include the real surname case in 11.5"; that case is now in this story.
- Organisations and places can carry a place word: 26 of the 196 organisations of the neutral library contain one (« Groupe Commercial Lyon », « Innovation Marseille SAS », 6 with « France », 3 with « Nord »). So « Datavora, installée à Lyon » could become « Groupe Commercial Lyon, installée à Metz », about 1% of organisation draws in a document that names one of those places. Comparing only the whole value misses it.
- Two people can get one pseudonym (found by Story 11.7's SM): the library's first-name and last-name lists share values, so a lone first name of one person and a lone last name of another can be written the same, for example « Tanguy ». 22 such pairs in 20,635 rows, in 13 of 22 generated databases. Same draw code as the leak, so it ships in this story.

**Scope (the SM writes the detailed story):**

- Every path that draws pseudonyms: CLI process and batch (parallel workers included), tabular, desktop single document and batch, and the no-review `ProcessingWorker`.
- A first name, last name, place or organisation that the library draws is drawn again when it matches a word of the document. For a place or an organisation, every word of it is checked, not only the whole value; for any drawn value, each part of a hyphenated word is checked too (« Saint-Denis » in a document naming a « Denis »; the orchestrator's reading of Lionel's "widen"). The custom-pseudonym check itself is unchanged. The rule is the custom-pseudonym real-name check's (Story 10.11 Q-C and Q-I, Story 10.16): capitals and accents ignored; a linking word followed by another word is not compared alone, and linking words are still not compared alone inside a place or organisation (Q-I).
- Bounded attempts; when they run out, today's fallback behaviour applies.
- Every value that is also a first name is removed from the last-name list (`gdpr_pseudonymizer/resources/pseudonyms/*.json`). Neutral theme: 44 values, 500 → 456 last names. The star_wars theme (213 shared, 287 left) and the lotr theme (231 shared, 269 left) would lose about 45% of their last names; they wait on a question to Lionel.
- Stored rows and their reuse are unchanged: a name already stored keeps its pseudonym (stored rows that leak are Story 11.7).
- It does not change what the review list shows (that is Story 11.5, now v2.3.2).
- CHANGELOG `[Unreleased]` entry under `### Security`; the exact text is shown to Lionel.
- Tests with realistic-shaped invented names, plus a forced-draw probe. An overfitting check, and a Codex stopping rule (as in Story 10.21). Same process as every story.

### Story 11.4: 2.3.1 Desktop Fixes

Found by Lionel's hand check of a 2.3.1 Windows build (2026-11-10). The two problems below are old (since February 2026) and real; the two wrong-passphrase traps in the scope were found while preparing the story (by the 11.4 SM and the PO).

- **Passphrase trap** (since Story 6.3, 2026-02-18). The passphrase dialog (`gdpr_pseudonymizer/gui/widgets/passphrase_dialog.py`, `_update_confirm_state` l.~266-271, `_on_confirm`) accepts any non-empty passphrase, and « Mémoriser pour cette session » is ticked by default. The single-document path (`gui/screens/home.py` l.~270-277) reuses the cached passphrase without asking. Database creation then refuses it on every document (`gui/workers/detection_worker.py` l.~107-116, « La phrase secrète doit contenir au moins 12 caractères. »). The database screen (`database.py:503-509`) clears a refused cached passphrase, and the batch screen (`batch.py:938-939`) clears it only for the creation refusal (its text match misses the French wrong-passphrase message); the single-document path never does, so the user loops until the app is closed.
- **Version label** (since Story 6.2, 2026-02-18). `gui/app.py:44` (`setApplicationVersion("2.0.0")`), the splash at `gui/app.py:133` (`"v2.0.0"`) and `gui/main_window.py:466` (« Version 2.0.0 ») are hardcoded.

**Scope (the SM writes the detailed story):**

- Passphrase: the dialog refuses fewer than 12 characters when creating a new database, with the message in the dialog (Lionel approved the existing wording, 2026-11-10: « La phrase secrète doit contenir au moins 12 caractères. », English "The passphrase must contain at least 12 characters."). The single-document path forgets a refused passphrase, as the database screen does.
- Second passphrase trap (found by the 11.4 SM, measured): an existing database opened with a wrong passphrase and « Mémoriser » ticked shows no pseudonyms, then fails at the end in English, and the wrong passphrase stays remembered. It is caught at the start of the document with the existing message « Phrase secrète incorrecte. Veuillez réessayer. » and forgotten, so the next document asks again.
- The same trap in a batch (traced in code by the PO; Lionel, 2026-11-10, "batch in 11.4"): in a desktop batch on an existing database with a wrong passphrase, `DocumentProcessor.__init__` opens no database (`core/document_processor.py:157-187`), so the batch worker's « Phrase secrète incorrecte » branch (`gui/workers/batch_worker.py:233-237`) never fires. Previews fail silently (`gui/screens/batch.py:1019-1028`); each file fails at finalization with the English message (`batch_worker.py:307-328`); the run ends `finished`, so `batch.py:_on_error` never clears the remembered passphrase (and its text match at `batch.py:938` misses the French message). Fix: the same start check in `BatchWorker._run_batch`, a flag, and the screen forgets the refused passphrase; existing message « Phrase secrète incorrecte. Veuillez réessayer. ».
- Version: read the package version with `importlib.metadata`, as `cli/main.py:36-41` does. The frozen app carries the package metadata (`gdpr-pseudo-gui.spec` copies metadata for readchar only, l.171). A fallback applies if the metadata is missing.
- The orchestrator runs `build-executables.yaml` on the branch head before merge.
- CHANGELOG `[Unreleased]` Fixed entries.

### Story 11.7: Stored Pseudonyms That Leak a Word of Their Own Name

**Problem:**

- A mapping database filled by 2.3.0 or earlier can hold rows whose pseudonym contains a word of the row's own real name, for example « Élodie Martin » stored as « Élodie Lucas ». Story 11.6 does not touch stored rows, so they keep being written.
- They spread: a later lone « Élodie » is written « Élodie », and a new « Élodie Vaz » keeps « Élodie ». Probe in `C:\Users\devea\Documents\GitHub\rgpd-analysis\r116\sm\logs\`: « Élodie Lucas a appelé. Élodie est partie. Élodie Vaz est venue. »
- Per-name rate in stored rows: about 1 in 280 to 1 in 175 (Story 11.6's PO, from the base log).

**Scope (the SM writes the detailed story):**

- A check compares each stored pseudonym with its own real name, with no documents needed (the own-name half of Story 11.6's rule), and reports the leaking rows.
- Only real leaks are reported: a place or organisation is reported only when the shared part is its whole name, its whole pseudonym, or a place from the pseudonym library.
- The user can replace each one: a new pseudonym drawn under Story 11.6's rule, with stored parts kept consistent for names that share a first or last name. After a replacement the old pseudonym is freed, as `delete-mapping` does.
- The app gives a notice when a document is written.
- A clear warning: documents already written keep the old pseudonym.
- CLI and desktop. The SM proposes where, for example a CLI command and the desktop database screen.
- Every new user text, French and English, approved by Lionel word for word.
- CHANGELOG `[Unreleased]` entry under `### Security`.

**Risks:** changing a stored pseudonym breaks consistency with documents already written (the user is warned); shared parts must move together or not at all; never two people with one pseudonym (replacement under the lock). A freed pseudonym can later be given to someone else while documents already written still use it for the first person; the warning must cover this.

### Story 11.5: The Review List Shows the Pseudonym That Will Be Written

Moved to v2.3.2 (Lionel, 2026-11-10: the leak fix ships first, the list fix in the next release); the real-surname/own-word part is now Story 11.6.

**Problem** (read-only investigation, 2026-11-10):

- For every name not yet stored, the review list, desktop and CLI, shows a pseudonym from a throw-away random draw (`core/document_processor.py:1176-1220` `build_pseudonym_previews`; `pseudonym/library_manager.py` `secrets.choice`). Finalization draws again under the lock (`_reset_pseudonym_state` :1009-1027, `_resolve_pseudonyms` :847-966, `_assign_new_pseudonym` :710-751).
- 0 of 62 shown/written pairs matched, over desktop and CLI runs on main, 2.3.0 and 2.2.0. The mismatch itself leaked nothing and merged no two people (the own-word leak found later is Story 11.6); the user approves a pseudonym that is never written.
- This reopens B36 (Story 10.11 follow-up (h), "can differ"; listed in `docs/qa/assessments/epic-10-close-out-summary.md:142`), accepted by Q-H on a "may differ" preview.
- The desktop batch screen builds its previews with the default theme (`gui/screens/batch.py:1020-1025`).
- Stored-title gap: for a stored titled name, the list drops the title (`gui/models/validation_state.py:270` vs `core/document_processor.py:1207-1216`).

**Scope (the SM writes the detailed story):**

- Each shown pseudonym, with its first-name and last-name parts, is passed to finalization as a proposal.
- Under `pseudonym_lock`, the proposal is kept only if it is still free: not used by a stored name, not another type's pseudonym for the same text, not a custom value, and consistent with stored first-name and last-name parts that appeared since the review. A kept proposal is stored with its parts and the real theme, not as a custom pseudonym.
- Otherwise it is redrawn and the user is told. New French text needs Lionel's word-for-word approval.
- Every path: CLI process and batch, desktop single document, desktop batch (its previews use the real theme), tabular.
- The list shows the title for a stored titled name.
- With this, Q-H's "OK unchanged does nothing" becomes exactly right.
- CHANGELOG `[Unreleased]` Fixed entry.

**Risk:** the "still free" check. A miss could give two people one pseudonym, the class of bug Story 10.22 fixed. The story requires tests with two documents finalized concurrently against one database.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

The first release commit (`chore(release): v2.3.1`, #121) is on main: version 2.3.1, CHANGELOG `[2.3.1]` dated 2026-11-07, which says plainly that Python 3.10 is no longer supported and that pip on 3.10 keeps installing 2.3.0. The tag is not pushed.

After Stories 11.6, 11.4 and 11.7 merge:

1. Second release PR: 11.6 and 11.7 (under Security) and 11.4 (under Fixed) put their entries under `[Unreleased]`; this PR folds them into `[2.3.1]` and dates that section with the tag date.
2. Read-only Codex review of the release PR.
3. Docs PR for version mentions.

No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] No CLI flag, GUI screen, mapping-table schema or file format changes, except the entry points Story 11.7 adds for its check (the SM proposes where).
- [ ] Python 3.11, 3.12 and 3.13 users get 2.3.1 (the desktop app needs macOS 12 or later on a Mac); Python 3.10 users keep getting 2.3.0 from pip, and the CHANGELOG says so.
- [ ] Existing mapping databases open and work unchanged.

## Risk Mitigation

- **Primary risk:** the lock refresh changes the behaviour of a dependency used at runtime or in the desktop build; the Qt 6.7 → 6.8 upgrade (PySide6 6.8.3, Story 11.3) changes how the desktop app behaves; Story 11.6's redraw loops, or changes the pseudonym of a name already stored (stored rows must not move); Story 11.7's replacement breaks consistency with documents already written, moves one shared part without the other, or gives two people one pseudonym; Story 11.6's smaller last-name list lowers the number of distinct real last names a database can hold before "library exhausted" (today about 413 for the neutral theme).
- **Mitigation:** targeted refresh of the listed packages only; full CI and the three build jobs green before merge. For the Qt upgrade: the full GUI test suite on all four CI legs, the three installer builds, and Lionel's hands-on check of the desktop app before the tag. For Story 11.6: bounded attempts with today's fallback, tests that stored rows and their reuse are unchanged, and a forced-draw probe; the new "library exhausted" limit is measured per theme and reported before merge. For Story 11.7: a clear warning before any replacement, shared parts moved together or not at all, and replacement under the lock with tests that no two people end up with one pseudonym.
- **Rollback plan:** revert the story's merge commit; 2.3.0 stays on PyPI.

## Definition of Done

- [ ] Story 11.1 merged: Python floor 3.11, lock refreshed, Dependabot alerts closed on main, two BACKLOG entries added
- [ ] "Protect main" ruleset updated to the renamed check (orchestrator; Lionel said yes 2026-11-05)
- [ ] Story 11.3 merged: CI tests Python 3.13 with the full suite, GUI tests included (still 4 test jobs), PySide6-Essentials `~6.8.3` with marker `<3.14`, 3.13 classifier, lock changes limited to pyside6-essentials and shiboken6 6.8.3, stanza 1.15.0 and the new orjson, alert #109 closed, three installer builds green on the branch head, docs say macOS 12 or later for the desktop app, MON-005 closed for 3.13
- [ ] "Protect main" required check renamed from `test (ubuntu-22.04, 3.11, false)` to `test (ubuntu-22.04, 3.13, false)` just before the 11.3 merge (orchestrator; needs Lionel's yes, not yet asked)
- [ ] Story 11.2 merged: custom pseudonyms with a two-word surname no longer refused at finalization; import "replace" updates the existing row
- [ ] Story 11.6 merged: on every path, no generated first name, last name, place or organisation matches a word of the document (same rule as the custom-pseudonym real-name check; every word of a place or organisation checked); bounded attempts; stored rows and their reuse unchanged; forced-draw probe green; no value in both the first-name and last-name lists of the neutral theme (star_wars and lotr per Lionel's answer); CHANGELOG Security text shown to Lionel
- [ ] Story 11.4 merged: the passphrase dialog refuses fewer than 12 characters for a new database, with the message in the dialog; the single-document path forgets a refused passphrase; a wrong passphrase on an existing database is caught at the start with the existing French message and forgotten, for a single document and in a batch; the desktop app shows the package version, installers included; new French text approved word for word by Lionel
- [ ] Story 11.7 merged: a check, CLI and desktop, reports stored rows whose pseudonym contains a word of their own real name and lets the user replace each one under Story 11.6's rule, with shared parts kept consistent, the old pseudonym freed and a clear warning that documents already written keep the old pseudonym; places and organisations reported only for real leaks; a notice when a document is written; no two people with one pseudonym; every new text, French and English, approved word for word by Lionel; CHANGELOG Security entry
- [ ] Each story: tests-first commit and draft PR, QA review, read-only Codex review of the final head
- [ ] No regression in existing features (full CI green)
- [ ] Before the 2.3.1 tag: Lionel opens the desktop app once from a branch or release-candidate build that includes Stories 11.6, 11.4 and 11.7 (his release-step check; his 2026-11-10 check found the problems 11.4 fixes)
- [ ] Second release PR (11.6, 11.4 and 11.7 entries folded into `[2.3.1]`, dated with the tag date) and docs PR prepared; tag and PyPI release only on Lionel's explicit go

### Next release (v2.3.2)

- [ ] Story 11.5 merged: on every path the review list shows the pseudonym that is written, or the user is told it was redrawn; batch previews use the real theme; stored titled names keep their title in the list; concurrent two-document tests green

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is a maintenance release of an existing Python/Poetry CLI and PySide6 desktop app.
- Integration points: `pyproject.toml`, `poetry.lock`, `mypy.ini`, `.github/workflows/ci.yaml`, `tests/unit/test_project_config.py`, `gdpr_pseudonymizer/core/custom_pseudonym.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`.
- Story 11.3 integration points: the PySide6-Essentials version, marker and classifiers in `pyproject.toml`, the `poetry.lock` re-lock, the 3.13 job in `.github/workflows/ci.yaml`, `.github/workflows/build-executables.yaml`, `tests/unit/test_project_config.py`, current user docs (Python versions and the macOS minimum), CHANGELOG, `docs/BACKLOG.md` MON-005.
- Story 11.4 integration points: `gdpr_pseudonymizer/gui/widgets/passphrase_dialog.py`, `gui/screens/home.py`, `gui/workers/detection_worker.py`, `gui/app.py`, `gui/main_window.py`, `gui/workers/batch_worker.py`, `gui/screens/batch.py`, `gdpr-pseudo-gui.spec`, `.github/workflows/build-executables.yaml`.
- Story 11.6 integration points: `gdpr_pseudonymizer/pseudonym/library_manager.py`, the last-name lists in `gdpr_pseudonymizer/resources/pseudonyms/*.json` (a copy also sits in `data/pseudonyms/`), `core/document_processor.py`, the real-name rule in `core/custom_pseudonym.py`, the CLI process and batch commands (parallel workers included), the tabular path, the desktop single-document and batch paths, the no-review `ProcessingWorker`.
- Story 11.7 integration points: the real-name rule in `gdpr_pseudonymizer/core/custom_pseudonym.py` and Story 11.6's draw, the mapping data layer (`data/`), a CLI entry point (`cli/commands/`, next to `delete_mapping.py`), the desktop database screen (`gui/screens/database.py`), the place where a document is written (for the notice); the SM proposes where.
- Story 11.5 (v2.3.2) integration points: `gdpr_pseudonymizer/core/document_processor.py`, `pseudonym/library_manager.py`, `gui/screens/batch.py`, `gui/models/validation_state.py`, the CLI process and batch commands, the tabular path.
- Story 11.1 lands first (merged); Story 11.3 lands next; Story 11.2 branches from main after 11.3 merges. All three are merged. Story 11.6 lands next, then Story 11.4, then Story 11.7, then the second release commit. Story 11.5 moves to v2.3.2.
- Story 11.3 stops for a report if the lock moves any package other than pyside6-essentials and shiboken6 (6.7.3 → 6.8.3), stanza (1.14.0 → 1.15.0) and the new orjson, or if a 3.13 test failure has no small, real fix.
- Name the two bugs by their problem, never by a finding number alone.
- New French user-facing text in 11.4 and 11.5 needs Lionel's word-for-word approval.
- Story 11.6 must leave stored rows and their reuse unchanged, bound its redraws, and show its CHANGELOG Security text to Lionel. The star_wars and lotr last-name cut waits on Lionel's answer.
- Story 11.7: every new text, French and English, approved by Lionel word for word; a clear warning before any replacement; shared parts move together or not at all; replacement under the lock; the old pseudonym freed; only real leaks reported; a notice when a document is written.
- Story 11.5 must test two documents finalized concurrently against one database.
- Each story must include verification that existing functionality remains intact.

The epic should keep the system intact while delivering a v2.3.1 with no open lock alerts, Python 3.13 tested in CI, the two release-review bugs fixed, the desktop passphrase traps and version label fixed, no generated pseudonym that reuses a word of the document or gives two people one pseudonym, and a way to find and replace stored pseudonyms that leak a word of their own name."
