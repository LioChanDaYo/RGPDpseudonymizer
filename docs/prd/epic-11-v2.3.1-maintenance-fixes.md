# Epic 11: v2.3.1 — Maintenance Fixes - Brownfield Enhancement

**Epic Goal:** Ship a small v2.3.1 that raises the Python floor to 3.11 so a dependency refresh can close the open Dependabot alerts on `poetry.lock`, and fixes two bugs found by the v2.3.0 release review: custom pseudonyms refused at finalization, and the import "replace" answer ignored.

**Target Release:** v2.3.1. The release itself is a separate step after both stories merge (see Release); no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.0 (Epic 10, released 2026-11-03)
**Successor:** none set. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

---

## Scope Rule

Exactly the items below enter 2.3.1: Python 3.11 floor with the dependency refresh (Story 11.1), and the two bugs (Story 11.2). Nothing else. KL-001 to KL-005 and the two-Maries limitation (backlogged by Story 11.1) stay in `docs/BACKLOG.md` with their pull triggers.

Lionel's decisions, word for word:

- Story 11.2: "1yes" (2026-11-04). His full reply was "1yes and 2no"; "2no" concerned keeping some analysis folders and is unrelated to this epic.
- Story 11.1: "drop 3.10 in 2.3.1 (beware; 2.3.1 already has stuff planned in it)" (2026-11-05).

---

## Existing System Context

- **Current relevant functionality:** v2.3.0 on PyPI (`gdpr-pseudonymizer`) and as standalone desktop builds. Custom pseudonyms ("Changer le pseudonyme", CLI [C]) are checked during review and again at finalization (`gdpr_pseudonymizer/core/custom_pseudonym.py`). `import-mappings` copies mappings from another database (`gdpr_pseudonymizer/cli/commands/import_mappings.py`).
- **Technology stack:** Python 3.10-3.12 (`pyproject.toml` classifiers; `python = ">=3.10,<3.14"`), Poetry, spaCy 3.7 (`fr_core_news_lg`), PySide6-Essentials, pytest, GitHub Actions.
- **Integration points:** `pyproject.toml`, `poetry.lock`, `mypy.ini`, `.github/workflows/ci.yaml` (oldest-Python job), `tests/unit/test_project_config.py`, `gdpr_pseudonymizer/core/custom_pseudonym.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`.

---

## Stories

Story 11.1 lands first. Story 11.2 branches from main after 11.1 merges.

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

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

After both stories merge:

1. Release PR: version 2.3.1, dated CHANGELOG entry that says plainly that Python 3.10 is no longer supported and that pip on 3.10 keeps installing 2.3.0.
2. Read-only Codex review of the release PR.
3. Docs PR for version mentions.

No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] No CLI flag, GUI screen, mapping-table schema or file format changes.
- [ ] Python 3.11 and 3.12 users get 2.3.1; Python 3.10 users keep getting 2.3.0 from pip, and the CHANGELOG says so.
- [ ] Existing mapping databases open and work unchanged.

## Risk Mitigation

- **Primary risk:** the lock refresh changes the behaviour of a dependency used at runtime or in the desktop build.
- **Mitigation:** targeted refresh of the listed packages only; full CI and the three build jobs green before merge.
- **Rollback plan:** revert the story's merge commit; 2.3.0 stays on PyPI.

## Definition of Done

- [ ] Story 11.1 merged: Python floor 3.11, lock refreshed, Dependabot alerts closed on main, two BACKLOG entries added
- [ ] "Protect main" ruleset updated to the renamed check (orchestrator; Lionel said yes 2026-11-05)
- [ ] Story 11.2 merged: custom pseudonyms with a two-word surname no longer refused at finalization; import "replace" updates the existing row
- [ ] Each story: tests-first commit and draft PR, QA review, read-only Codex review of the final head
- [ ] No regression in existing features (full CI green)
- [ ] Release PR and docs PR prepared; tag and PyPI release only on Lionel's explicit go

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is a maintenance release of an existing Python/Poetry CLI and PySide6 desktop app.
- Integration points: `pyproject.toml`, `poetry.lock`, `mypy.ini`, `.github/workflows/ci.yaml`, `tests/unit/test_project_config.py`, `gdpr_pseudonymizer/core/custom_pseudonym.py`, `gdpr_pseudonymizer/cli/commands/import_mappings.py`.
- Story 11.1 lands first; Story 11.2 branches from main after it merges.
- Name the two bugs by their problem, never by a finding number alone.
- Each story must include verification that existing functionality remains intact.

The epic should keep the system intact while delivering a v2.3.1 with no open lock alerts and the two release-review bugs fixed."
