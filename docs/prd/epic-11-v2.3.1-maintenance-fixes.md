# Epic 11: v2.3.1 — Maintenance Fixes - Brownfield Enhancement

**Epic Goal:** Ship a small v2.3.1 that raises the Python floor to 3.11 so a dependency refresh can close the open Dependabot alerts on `poetry.lock`, tests Python 3.13 in CI, and fixes two bugs found by the v2.3.0 release review: custom pseudonyms refused at finalization, and the import "replace" answer ignored.

**Target Release:** v2.3.1. The release itself is a separate step after all three stories merge (see Release); no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.0 (Epic 10, released 2026-11-03)
**Successor:** none set. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

---

## Scope Rule

Exactly four items enter 2.3.1: Python 3.11 floor with the dependency refresh (Story 11.1), Python 3.13 in CI (Story 11.3), and the two bugs (Story 11.2). Nothing else. KL-001 to KL-005 and the two-Maries limitation (backlogged by Story 11.1) stay in `docs/BACKLOG.md` with their pull triggers.

Lionel's decisions, word for word:

- Story 11.2: "1yes" (2026-11-04). His full reply was "1yes and 2no"; "2no" concerned keeping some analysis folders and is unrelated to this epic.
- Story 11.1: "drop 3.10 in 2.3.1 (beware; 2.3.1 already has stuff planned in it)" (2026-11-05).
- Story 11.3: "we're getting 3.10 out of CI right? how about we add 3.13, then? so that it's not untested anymore?" (2026-11-05). Given three options, he answered "b". Option b, in our words, not his: a separate small story right after 11.1, inside 2.3.1.

---

## Existing System Context

- **Current relevant functionality:** v2.3.0 on PyPI (`gdpr-pseudonymizer`) and as standalone desktop builds. Custom pseudonyms ("Changer le pseudonyme", CLI [C]) are checked during review and again at finalization (`gdpr_pseudonymizer/core/custom_pseudonym.py`). `import-mappings` copies mappings from another database (`gdpr_pseudonymizer/cli/commands/import_mappings.py`).
- **Technology stack:** Python 3.10-3.12 (`pyproject.toml` classifiers; `python = ">=3.10,<3.14"`), Poetry, spaCy 3.7 (`fr_core_news_lg`), PySide6-Essentials, pytest, GitHub Actions.
- **Integration points:** `pyproject.toml`, `poetry.lock`, `mypy.ini`, `.github/workflows/ci.yaml` (oldest-Python job), `tests/unit/test_project_config.py`, `gdpr_pseudonymizer/core/custom_pseudonym.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`.

---

## Stories

Story 11.1 lands first (merged 2026-11-05). Story 11.3 lands next. Story 11.2 branches from main after 11.3 merges. The numbers stay: 11.2 keeps its approved number and text.

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
- Lionel, 2026-11-05: "Move the desktop app to PySide6 6.8.3 for everyone", chosen among three options: CLI-only on 3.13, PySide6 6.8.3 for everyone, drop 3.13 from 2.3.1. So: `PySide6-Essentials = {version = "~6.8.3", optional = true, python = ">=3.11,<3.14"}`; add the `Programming Language :: Python :: 3.13` classifier.
- Update `tests/unit/test_project_config.py`: the classifiers test, the PySide6 marker test and the CI-job test all pin today's values.
- Re-lock. pyside6-essentials and shiboken6 move 6.7.3 → 6.8.3 on every Python, plus the stanza bump below (with orjson). **Any other package movement stops the story** for a report.
- Bump stanza 1.14.0 → 1.15.0 (Dependabot alert #109, dev-only, excluded from the installers). stanza 1.15.0 adds one new dev-only requirement, orjson (3.13.0, measured on PyPI 2026-11-05). Apart from pyside6-essentials and shiboken6, only stanza and orjson may move; otherwise stop for a report. Lionel, 2026-11-05: "Stanza : a", then "clear, yes to orjson".
- **If a test fails on 3.13**, the story fixes it only if the fix is small and real. Otherwise the story stops and the orchestrator reports to Lionel.
- Every installer ships Qt 6.8. The orchestrator runs `build-executables.yaml` on the branch head before merge. The dev runs the GUI test suite locally on Windows with the new lock. Before the 2.3.1 tag, Lionel opens the desktop app once from a branch or release-candidate build (a release-step check, his).
- Current user docs say Python 3.11 to 3.13 for both the CLI and the desktop app, and that the desktop app needs macOS 12 or later wherever they state a macOS version for it (for example `docs/architecture/1-introduction.md:71` says macOS 11+): English, and French only with Lionel's word-for-word approval of the text. History docs (past CHANGELOG entries, stories, QA reports) untouched.
- CHANGELOG `[Unreleased]` entry: Python 3.13 is tested; the desktop app moves to Qt 6.8 (PySide6 6.8.3); macOS 12 is now the minimum for the desktop app.
- `docs/BACKLOG.md` MON-005: a dated 2026-11-05 paragraph with the measurement, including the correction that PySide6 6.7 did not support 3.13; closed for 3.13. 3.14 stays monitored.

**Orchestrator step, not a dev task:** the "Protect main" ruleset (12689559) requires the check `test (ubuntu-22.04, 3.11, false)` by name. Just before Lionel's merge, it is renamed to `test (ubuntu-22.04, 3.13, false)`. This needs Lionel's yes, not yet asked.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

After all three stories merge:

1. Release PR: version 2.3.1, dated CHANGELOG entry that says plainly that Python 3.10 is no longer supported and that pip on 3.10 keeps installing 2.3.0.
2. Read-only Codex review of the release PR.
3. Docs PR for version mentions.

No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] No CLI flag, GUI screen, mapping-table schema or file format changes.
- [ ] Python 3.11, 3.12 and 3.13 users get 2.3.1 (the desktop app needs macOS 12 or later on a Mac); Python 3.10 users keep getting 2.3.0 from pip, and the CHANGELOG says so.
- [ ] Existing mapping databases open and work unchanged.

## Risk Mitigation

- **Primary risk:** the lock refresh changes the behaviour of a dependency used at runtime or in the desktop build; the Qt 6.7 → 6.8 upgrade (PySide6 6.8.3, Story 11.3) changes how the desktop app behaves.
- **Mitigation:** targeted refresh of the listed packages only; full CI and the three build jobs green before merge. For the Qt upgrade: the full GUI test suite on all four CI legs, the three installer builds, and Lionel's hands-on check of the desktop app before the tag.
- **Rollback plan:** revert the story's merge commit; 2.3.0 stays on PyPI.

## Definition of Done

- [ ] Story 11.1 merged: Python floor 3.11, lock refreshed, Dependabot alerts closed on main, two BACKLOG entries added
- [ ] "Protect main" ruleset updated to the renamed check (orchestrator; Lionel said yes 2026-11-05)
- [ ] Story 11.3 merged: CI tests Python 3.13 with the full suite, GUI tests included (still 4 test jobs), PySide6-Essentials `~6.8.3` with marker `<3.14`, 3.13 classifier, lock changes limited to pyside6-essentials and shiboken6 6.8.3, stanza 1.15.0 and the new orjson, alert #109 closed, three installer builds green on the branch head, docs say macOS 12 or later for the desktop app, MON-005 closed for 3.13
- [ ] "Protect main" required check renamed from `test (ubuntu-22.04, 3.11, false)` to `test (ubuntu-22.04, 3.13, false)` just before the 11.3 merge (orchestrator; needs Lionel's yes, not yet asked)
- [ ] Story 11.2 merged: custom pseudonyms with a two-word surname no longer refused at finalization; import "replace" updates the existing row
- [ ] Each story: tests-first commit and draft PR, QA review, read-only Codex review of the final head
- [ ] No regression in existing features (full CI green)
- [ ] Before the 2.3.1 tag: Lionel opens the desktop app once from a branch or release-candidate build (his release-step check)
- [ ] Release PR and docs PR prepared; tag and PyPI release only on Lionel's explicit go

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is a maintenance release of an existing Python/Poetry CLI and PySide6 desktop app.
- Integration points: `pyproject.toml`, `poetry.lock`, `mypy.ini`, `.github/workflows/ci.yaml`, `tests/unit/test_project_config.py`, `gdpr_pseudonymizer/core/custom_pseudonym.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`.
- Story 11.3 integration points: the PySide6-Essentials version, marker and classifiers in `pyproject.toml`, the `poetry.lock` re-lock, the 3.13 job in `.github/workflows/ci.yaml`, `.github/workflows/build-executables.yaml`, `tests/unit/test_project_config.py`, current user docs (Python versions and the macOS minimum), CHANGELOG, `docs/BACKLOG.md` MON-005.
- Story 11.1 lands first (merged); Story 11.3 lands next; Story 11.2 branches from main after 11.3 merges.
- Story 11.3 stops for a report if the lock moves any package other than pyside6-essentials and shiboken6 (6.7.3 → 6.8.3), stanza (1.14.0 → 1.15.0) and the new orjson, or if a 3.13 test failure has no small, real fix.
- Name the two bugs by their problem, never by a finding number alone.
- Each story must include verification that existing functionality remains intact.

The epic should keep the system intact while delivering a v2.3.1 with no open lock alerts, Python 3.13 tested in CI, and the two release-review bugs fixed."
