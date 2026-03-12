# Epic 7: v2.1 — GUI Polish, Excel Support & NER Accuracy

**Epic Goal:** Refine the v2.0 desktop GUI based on real user feedback, add Excel/CSV format support for the HR/compliance audience, introduce a neutral pseudonym theme, and improve NER accuracy through regex pattern expansion — delivering a tighter, more productive experience for existing users.

**Target Release:** v2.1.0
**Duration:** Estimated 4-6 weeks
**Predecessor:** Epic 6 (v2.0.0 released 2026-03-04)

---

## Existing System Context

- **v2.0:** Desktop GUI (PySide6), standalone executables (.exe, .app, AppImage), French/English i18n, WCAG AA accessibility, batch processing with optional validation, 1670+ tests, 86%+ coverage
- **Technology Stack:** Python 3.10-3.12, Poetry, PySide6, spaCy `fr_core_news_lg`, Rich, Typer 0.9.x, SQLite + cryptography (Fernet), structlog
- **Key Constraint:** All changes must preserve existing CLI and GUI functionality. No architectural changes — this is a polish and enhancement release.

---

## Strategic Context

### Why v2.1 Now?

v2.0 successfully launched the desktop GUI and standalone executables. Early user feedback has identified concrete friction points in the validation workflow — the feature users spend 80% of their time in. Addressing these quickly maximizes user retention and satisfaction before tackling deeper NLP improvements in v3.0.

### What This Release Delivers

1. **Validation productivity** — Validate-once-per-entity eliminates repetitive clicks (FE-020)
2. **GUI discoverability** — Hidden shortcuts and toggles made visible (FE-018, FE-019)
3. **Session continuity** — Database persistence across restarts (FE-017)
4. **New format** — Excel/CSV support for HR/compliance workflows (FE-015)
5. **New theme** — Neutral/generic pseudonyms for formal contexts (FE-016)
6. **Better accuracy** — Regex expansion reduces missed entities (FE-011, FE-012)

---

## Epic 7 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 7.1: Validation Workflow Productivity | HIGH | 1-2 days | FE-020, FE-019 | Done |
| 7.2: GUI Discoverability & Session UX | MED | 1 day | FE-017, FE-018 | Done |
| 7.3: Neutral Pseudonym Theme | MED | 1-2 days | FE-016 | Draft |
| 7.4: Excel & CSV Format Support | MED | 1-2 weeks | FE-015 | Draft |
| 7.5: NER Accuracy — Regex Expansion & Corpus Cleanup | HIGH | 3-5 days | FE-011, FE-012 | Draft |
| 7.6: Quality & Compatibility | LOW | 2-3 days | TD-007, MON-005 | Draft |
| 7.7: v2.1 Release Preparation | HIGH | 1-2 days | — | Draft |

**Total Estimated Duration:** 4-6 weeks

---

## Story 7.1: Validation Workflow Productivity

**As a** user validating entities in a document,
**I want** accepting or rejecting one occurrence of an entity to apply to all occurrences, and I want to hide already-confirmed entities,
**so that** I can complete validation faster, especially in documents with repeated names.

**Priority:** HIGH — Addresses the #1 user friction point

### Context

FE-020 (validate-once-per-entity) is the single highest-impact UX improvement identified in v2.0 user feedback. Documents with repeated names (e.g., interview transcripts where "Marie Dupont" appears 20+ times) currently require 20+ individual validations. Combined with FE-019 (hide confirmed entities), this story transforms validation from tedious to efficient.

### Acceptance Criteria

1. **AC1 (FE-020):** Accepting one occurrence of an entity (e.g., "Marie Dupont") confirms ALL occurrences of the same entity text in the document
2. **AC2 (FE-020):** Rejecting one occurrence rejects all occurrences of the same entity text
3. **AC3 (FE-020):** Undo reverses the group action — all occurrences revert to previous state
4. **AC4 (FE-020):** Grouping uses exact text match only — different entity texts are NOT grouped (e.g., "Marie" and "Marie Dupont" remain independent). No fuzzy matching in v2.1.
5. **AC5 (FE-020):** Works from keyboard navigation (Enter/Delete), context menu, and bulk selection
6. **AC6 (FE-020):** Sidebar and document highlights update immediately for all affected occurrences
7. **AC7 (FE-019):** "Masquer les validees" checkbox visible next to existing "Masquer les rejetees" toggle
8. **AC8 (FE-019):** When toggled on, confirmed and known entities are hidden from document highlights
9. **AC9 (FE-019):** Pending and rejected entities remain visible
10. **AC10:** No regression in existing bulk accept/reject by type or checkbox selection
11. **AC11:** Unit tests for grouping logic, undo/redo, and hide-confirmed toggle

### Integration Points

- `gdpr_pseudonymizer/gui/widgets/validation_state.py` — grouping logic in `accept_entity()` / `reject_entity()`
- `gdpr_pseudonymizer/gui/widgets/entity_editor.py` — `set_hide_confirmed()` (mirrors `set_hide_rejected`)
- `gdpr_pseudonymizer/gui/widgets/entity_panel.py` — new checkbox

### Estimated Effort: 1-2 days

---

## Story 7.2: GUI Discoverability & Session UX

**As a** GUI user,
**I want** all keyboard shortcuts documented in the Help menu, and my last-used database remembered across sessions,
**so that** I can discover power-user features and avoid repetitive setup.

**Priority:** MEDIUM — Reduces friction for returning users

### Acceptance Criteria

1. **AC1 (FE-018):** F1 help dialog lists ALL keyboard shortcuts grouped by context:
   - Global, Validation, Navigation Mode, Editor
   - Includes: Enter/Tab/Delete/Escape (navigation mode), Ctrl+Z/Ctrl+Shift+Z (undo/redo), Ctrl+F (filter), Ctrl++/Ctrl+- (zoom)
2. **AC2 (FE-018):** Settings screen shortcuts section updated to match
3. **AC3 (FE-018):** Navigation mode section explains activation (Enter) and deactivation (Escape)
4. **AC4 (FE-017):** After selecting a database, choice is persisted in `.gdpr-pseudo.yaml` as `default_db_path`
5. **AC5 (FE-017):** On next launch, previously used database is pre-selected in PassphraseDialog
6. **AC6 (FE-017):** Creating a new database also persists it as the new default
7. **AC7:** No regression in existing help, settings, or database detection
8. **AC8:** Unit tests for config persistence and help dialog content

### Integration Points

- `gdpr_pseudonymizer/gui/main_window.py` — `_show_shortcuts()` help dialog
- `gdpr_pseudonymizer/gui/screens/settings.py` — shortcuts section
- `gdpr_pseudonymizer/gui/config.py` — `save_gui_config()`
- `gdpr_pseudonymizer/gui/widgets/passphrase_dialog.py` — `_populate_db_paths()`

### Estimated Effort: 1 day

---

## Story 7.3: Neutral Pseudonym Theme

**As a** user processing formal or legal documents,
**I want** a neutral/generic pseudonym theme that replaces names with identifiers like PER-001, LOC-001, ORG-001,
**so that** pseudonymized output is appropriate for contexts where themed names (Star Wars, LOTR) feel unprofessional.

**Priority:** MEDIUM — Clear use case for legal/compliance/research contexts

### Acceptance Criteria

1. **AC1:** New theme option `--theme neutral` (CLI) and "Neutre / Generique" in GUI theme dropdown
2. **AC2:** Generates sequential identifiers per entity type: PER-001, PER-002, LOC-001, ORG-001, etc.
3. **AC3:** Compositional pseudonymization works — if "Marie Dupont" -> PER-001, then "Marie" -> PER-001-P (prenom) and "Dupont" -> PER-001-N (nom). If "Marie" also appears independently (not as a sub-entity of a compound name), it receives its own identifier (PER-002). Grouping follows existing variant grouping logic from Story 4.6.
4. **AC4:** Mapping table stores neutral pseudonyms like any other theme
5. **AC5:** Counter resets per database session (not globally)
6. **AC6:** Documentation updated (theme comparison table, CLI reference, GUI settings)
7. **AC7:** No regression in existing theme functionality (french, lotr, star_wars)
8. **AC8:** Unit tests for counter-based generation, compositional logic, and mapping persistence

### Implementation Notes

- No library files needed — purely algorithmic generation
- Counter-based: `NeutralPseudonymGenerator` class in `pseudonym/` module
- Must integrate with existing `LibraryManager` API so GUI/CLI theme selection works transparently

### Estimated Effort: 1-2 days

---

## Story 7.4: Excel & CSV Format Support

**As a** HR professional or compliance officer,
**I want** to pseudonymize Excel (.xlsx) and CSV files directly,
**so that** I can process employee data, case files, and research datasets without manual conversion to text.

**Priority:** MEDIUM — Natural extension for GUI target audience

### Context

HR and compliance professionals — the primary GUI audience — heavily use Excel for employee data, case management, and research datasets. Currently they must manually copy/paste into .txt files. This story adds direct Excel/CSV support, following the same pattern established by PDF/DOCX support in Story 5.5.

### Acceptance Criteria

1. **AC1:** Excel file loading (.xlsx) via openpyxl
2. **AC2:** CSV file loading with auto-detection of delimiter and encoding
3. **AC3:** Cell-by-cell text extraction — each cell's text content is processed through the NER pipeline
4. **AC4:** Output options:
   - Pseudonymized Excel (.xlsx) — same structure, pseudonymized cell contents
   - Pseudonymized CSV — same structure, pseudonymized cell contents
   - Flattened text (.txt) — all cell contents concatenated (fallback)
5. **AC5:** Entity validation shows cell references (e.g., "Sheet1!B3") as context
6. **AC6:** GUI file dialog updated to include .xlsx, .csv filters
7. **AC7:** CLI `process` and `batch` commands accept .xlsx and .csv files
8. **AC8:** New dependencies as optional extras: `pip install gdpr-pseudonymizer[excel]`
9. **AC9:** Formulas are preserved where possible (best-effort — openpyxl reads formula strings but pseudonymization only targets display/cached values, not formula expressions). If a formula references a cell whose display value was pseudonymized, the formula result may become stale until recalculated in Excel. This limitation should be documented.
10. **AC10:** Error handling: password-protected Excel, corrupt files, binary .xls (unsupported with clear message)
11. **AC11:** No regression in existing format support (.txt, .md, .pdf, .docx)
12. **AC12:** Unit and integration tests for Excel/CSV reading, processing, and output

### Implementation Notes

**Phased approach recommended:** CSV support (no new dependency, simpler parsing) should land first as a quick win. Excel support (openpyxl, cell-aware processing, structured output) is the heavier lift and can follow within the same story. If the epic timeline is tight, Excel output preservation (xlsx->xlsx) can be deferred — input support alone (xlsx->txt) still delivers value.

**Scope note:** This is the largest story in a "polish" release. If it slips, it should not block the v2.1 release — ship the other stories and promote 7.4 to v2.2 if needed.

### Integration Points

- `gdpr_pseudonymizer/utils/file_reader.py` — new `read_excel()`, `read_csv()` functions
- `gdpr_pseudonymizer/utils/file_writer.py` — new Excel/CSV output writers (or new module)
- `gdpr_pseudonymizer/core/processor.py` — cell-aware processing mode
- `pyproject.toml` — `[excel]` optional dependency group

### Estimated Effort: 1-2 weeks

---

## Story 7.5: NER Accuracy — Regex Expansion & Corpus Cleanup

**As a** user who frequently adds missed entities during validation,
**I want** the NER engine to detect more entities automatically,
**so that** I spend less time manually adding entities and more time confirming/rejecting.

**Priority:** HIGH — Directly reduces validation effort for every user

### Context

Story 4.4 accuracy analysis identified specific pattern gaps: LOCATION FN=37%, ORG FN=66%, Last/First name format recall=0%. These are addressable through regex expansion without NLP model changes. Additionally, annotation quality issues inflate false negative counts, making accuracy metrics unreliable.

### Acceptance Criteria

1. **AC1 (FE-011):** "LastName, FirstName" regex pattern added (e.g., "Dubois, Jean-Marc")
2. **AC2 (FE-011):** ORG suffix patterns expanded to 15+ suffixes (Association, Fondation, Institut, Groupe, Consortium, Federation, Syndicat, Chambre, etc.)
3. **AC3 (FE-011):** French geography dictionary added — top 100 cities, 13 regions, 101 departments. Disambiguation strategy: dictionary matches are only accepted when (a) the token is capitalized, AND (b) spaCy POS tags the token as PROPN or the token has no other entity assignment. This prevents false positives on ambiguous names (e.g., "Lyon" as surname, "Paris" in non-geographic context).
4. **AC4 (FE-011):** Accuracy re-run shows measurable improvement: target LOCATION FN <25%, ORG FN <50%
5. **AC5 (FE-011):** No regression in PERSON detection precision (measure precision before and after regex expansion; revert any pattern that drops precision by >2%)
6. **AC6 (FE-012):** Annotation README entity count corrected to match actual count
7. **AC7 (FE-012):** board_minutes.json annotations cleaned (garbage entries removed, quality issues fixed)
8. **AC8 (FE-012):** Consistent annotation policy for titles documented
9. **AC9 (FE-012):** Accuracy test re-run against clean corpus to establish new baseline
10. **AC10:** Updated accuracy metrics documented in `docs/qa/ner-accuracy-report.md`

### Integration Points

- `gdpr_pseudonymizer/nlp/regex_matcher.py` — new patterns
- `gdpr_pseudonymizer/resources/` — French geography dictionary data file
- `tests/test_corpus/annotations/` — cleaned annotations
- `docs/qa/ner-accuracy-report.md` — updated baselines

### Estimated Effort: 3-5 days

---

## Story 7.6: Quality & Compatibility

**As a** developer,
**I want** integration tests for performance features and Python 3.13 support (if available),
**so that** the codebase has comprehensive test coverage and supports the latest Python.

**Priority:** LOW — Quality investment, not user-facing

### Acceptance Criteria

1. **AC1 (TD-007):** Integration test for keyboard-only document processing workflow
2. **AC2 (TD-007):** Integration test for batch validation workflow (5 documents, validate each)
3. **AC3 (TD-007):** Integration test for database background threading (1000+ entities, verify responsive)
4. **AC4 (TD-007):** Full GUI regression suite passes with new tests
5. **AC5 (MON-005, conditional):** If spaCy/thinc publish Python 3.13 wheels before v2.1 release:
   - Add Python 3.13 to CI matrix
   - Update `pyproject.toml` constraint to `>=3.10,<3.14`
   - Update documentation
6. **AC6:** If Python 3.13 remains blocked, document current status in release notes

### Integration Points

- `tests/integration/gui/` — new integration test files
- `.github/workflows/ci.yaml` — CI matrix (if Python 3.13 added)
- `pyproject.toml` — Python version constraint (if updated)

### Estimated Effort: 2-3 days

---

## Story 7.7: v2.1 Release Preparation

**As a** product manager,
**I want** v2.1.0 published with updated documentation, release notes, and standalone executables,
**so that** users can upgrade and benefit from the improvements.

**Priority:** HIGH — Gates the release

### Acceptance Criteria

1. **AC1:** Version bumped to `2.1.0` in `pyproject.toml`
2. **AC2:** CHANGELOG.md updated with v2.1.0 section
3. **AC3:** README updated: new theme, Excel support, validation improvements
4. **AC4:** README.fr.md mirrored with French updates
5. **AC5:** Full regression suite passing: black, ruff, mypy, pytest (CLI + GUI tests)
6. **AC6:** `poetry build` succeeds, PyPI package builds cleanly
7. **AC7:** Standalone executables built and tested for Windows, macOS, Linux
8. **AC8:** Git tag `v2.1.0` triggers release workflow
9. **AC9:** Release notes highlight user-facing improvements
10. **AC10:** BACKLOG.md updated — completed items marked, new items added if any

### Estimated Effort: 1-2 days

---

## Execution Sequence

```
Story 7.1 (Validation Productivity)    --- Day 1-2 ---    Highest user impact
Story 7.2 (Discoverability & UX)       --- Day 3 ---      Quick wins
Story 7.3 (Neutral Theme)              --- Day 4-5 ---    Independent
Story 7.5 (NER Accuracy)               --- Day 6-10 ---   Independent (parallelizable with 7.3-7.4)
Story 7.4 (Excel/CSV Support)          --- Day 8-18 ---   Largest story
Story 7.6 (Quality & Compatibility)    --- Day 16-18 ---  Parallelizable with 7.4
Story 7.7 (Release Prep)               --- Day 19-20 ---  Release gate
```

**Parallelization:** Stories 7.1-7.3 are independent quick wins. Story 7.5 can run in parallel with 7.3-7.4. Story 7.6 can run in parallel with 7.4.

**Critical Path:** 7.1 -> 7.4 -> 7.7 (longest chain ~3-4 weeks)

---

## Compatibility Requirements

- [x] Existing CLI commands remain unchanged
- [ ] New `--theme neutral` option added to CLI
- [ ] New `.xlsx` and `.csv` file support added to CLI and GUI
- [ ] Existing mapping databases remain compatible (no migration)
- [ ] PyPI installation path continues to work
- [ ] Standalone executables include new features
- [ ] Configuration file (`.gdpr-pseudo.yaml`) backward compatible

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Excel structure preservation complexity | MEDIUM | MEDIUM | Start with simple cell-text extraction; structured output as stretch goal |
| Regex expansion increases false positives | MEDIUM | MEDIUM | Measure precision alongside recall; revert patterns that hurt precision |
| Python 3.13 still blocked by thinc | HIGH | LOW | Document status, defer to v2.2; not a user-facing feature |
| Validate-once edge cases (partial names) | LOW | LOW | Strict text-match grouping; no fuzzy matching in v2.1 |

---

## Definition of Done

- [ ] All 7 stories completed with acceptance criteria met
- [ ] Existing CLI and GUI functionality verified (full test suite passing)
- [ ] All quality gates green: black, ruff, mypy, pytest
- [ ] Test count >= v2.0 baseline (1670+), coverage >= 86%
- [ ] No regression in existing processing workflows
- [ ] v2.1.0 published on PyPI and standalone downloads on GitHub Releases
- [ ] Documentation updated (EN + FR)

---

## Explicitly Deferred (v2.2+)

| Item | Reason | Target |
|------|--------|--------|
| Output format preservation (PDF->PDF, DOCX->DOCX) | Significant complexity; dedicated epic | v2.2 |
| Auto-update mechanism | Non-trivial infrastructure | v2.2 |
| Confidence score calibration (FE-013) | Requires ML training; v3.0 scope | v3.0 |
| Extended coreference resolution (FE-014) | Research-level NLP | v3.0 |
| Fine-tuned French NER model | Major effort; v3.0 scope | v3.0 |
| Multi-language NER (EN, ES, DE) | Architectural change; v3.1+ | v3.1+ |

---

## Architect Feasibility Review

**Reviewed by:** Winston (Architect) — 2026-03-06
**Verdict:** GO — All stories technically sound

### Story-Level Assessment

| Story | Feasibility | Notes |
|-------|------------|-------|
| 7.1 Validation Productivity | Green | `validation_state.py` already has accept/reject per-entity. Grouping by exact text match is a simple dict lookup. Low risk. |
| 7.2 GUI Discoverability | Green | Trivial — config persistence in YAML, help dialog content. |
| 7.3 Neutral Theme | Green | Counter-based generation, no external data. Must integrate with `LibraryManager` API but pattern is established by existing themes. |
| 7.4 Excel/CSV | Green/Yellow | CSV is trivial (stdlib `csv`). Excel needs `openpyxl` as new optional dep. The `[excel]` optional extra pattern already exists for `[pdf]`/`[docx]` in pyproject.toml. |
| 7.5 NER Regex Expansion | Green | `regex_matcher.py` already supports pattern configs with confidence. `geography_dictionary.py` already exists — just needs expansion. Disambiguation strategy (capitalized + PROPN) is sound. |
| 7.6 Quality & Compatibility | Green | Standard test work. Python 3.13 likely still blocked by spaCy/thinc — correctly scoped as conditional. |
| 7.7 Release | Green | Established workflow from v2.0. |

### Recommendation: Story 7.4 Cell-Location Metadata

**Design this upfront.** The current pipeline assumes flat text — `DetectedEntity` has `start_pos`/`end_pos` as character offsets. AC5 ("entity validation shows cell references like Sheet1!B3") requires the processor to carry cell-location metadata through the pipeline.

**Recommended approach:** Add an optional `context_label: str | None` field to `DetectedEntity` rather than overloading `start_pos`/`end_pos`. This keeps the flat-text processing path unchanged while allowing cell-aware formats to attach location info. The cell-by-cell processing adapter should process each cell as an independent text unit, then tag resulting entities with their cell reference.

---

**Document Status:** REVIEWED
**Created:** 2026-03-06
**Author:** Sarah (Product Owner)
**Reviewed by:** John (PM) — 2026-03-06
**Review Notes:** Approved with inline clarifications added (neutral theme grouping rules, geography FP disambiguation, Excel formula best-effort, Story 7.4 phased approach note). Story 7.4 is the largest item — if it slips, do not let it block the v2.1 release.
