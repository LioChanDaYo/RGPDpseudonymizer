# Product Backlog - GDPR Pseudonymizer

**Last Updated:** 2026-02-20
**Epic 1 Status:** ✅ Complete (9/9 stories)
**Epic 2 Status:** ✅ Complete (9/9 stories)
**Epic 3 Status:** ✅ Complete (7/7 stories)
**Epic 4 Status:** ✅ Complete (7/7 stories)
**v1.0 MVP:** ✅ LAUNCHED (2026-02-09, PyPI published)
**Next Milestone:** v2.0 Desktop GUI (Epic 6 — Stories 6.1-6.5 complete)

---

## 🎯 Backlog Categories

- **Technical Debt:** Items deferred from Epic 1 that should be addressed
- **High Priority Enhancements:** Critical features for v1.0 MVP
- **Future Enhancements:** Nice-to-have improvements identified during development
- **Monitoring Items:** Things to watch in production/user testing
- **Epic 2+ Items:** Features planned for future epics

---

## 📋 Technical Debt from Epic 1

### HIGH Priority

#### TD-001: Integration Tests for Validation Workflow ✅ COMPLETE (Story 2.0.1)
**Source:** Story 1.7 QA Gate (TEST-001)
**Description:** Add end-to-end integration tests for complete validation workflow beyond unit tests
**Impact:** Reduced confidence in full workflow behavior, edge cases may not be covered
**Effort:** Medium (2-3 days)
**Target:** Epic 2 - Story 2.0.1 (before Story 2.6)
**Epic 2 Assignment:** Story 2.0.1: Integration Tests for Validation Workflow
**Rationale:** Required for Story 2.6 integration testing; pays down Epic 1 technical debt before production workflow
**References:**
- [docs/qa/gates/1.7-validation-ui-implementation.yml](qa/gates/1.7-validation-ui-implementation.yml)
- tests/integration/ directory

**Acceptance Criteria:**
- [x] Full validation workflow tests simulating user actions
- [x] State transition verification (pending → confirmed → rejected)
- [x] Edge case coverage (empty entities, 100+ entities, Ctrl+C interruption)
- [x] Tests run in CI/CD pipeline (Python 3.9-3.13)

---

### MEDIUM Priority

#### TD-002: External User Testing for Validation UI ✅ COMPLETE (Story 4.6 AC10)
**Source:** Story 1.7 QA Gate (AC10)
**Description:** Conduct external user testing (2-3 users) to validate UX with real users
**Impact:** Self-testing showed excellent results (4-5/5), but external validation deferred
**Effort:** Low (1-2 days including participant recruitment)
**Target:** Epic 4 - Story 4.6 AC10 (Beta Feedback Integration & Bug Fixes)
**Epic 2 Decision:** DEFER - Epic 2 focuses on core engine, not validation UI. Better timing after CLI polish (Epic 3).
**Epic 4 Assignment:** Story 4.6 AC10: External user testing with 2-3 users
**Rationale:** CLI is now polished (Epic 3 complete); Story 4.6 is the natural home for user testing before launch
**Completed:** 2026-02-09 (Story 4.6) — ≥4/5 satisfaction, <5 min validation time achieved
**References:**
- [docs/qa/gates/1.7-validation-ui-implementation.yml](qa/gates/1.7-validation-ui-implementation.yml)
- tests/test_corpus/validation_testing/USER_TESTING_GUIDE.md

**Acceptance Criteria:**
- [x] Recruit 2-3 external users (academic researchers, HR professionals, or compliance officers)
- [x] Provide test documents (20-50 entities each)
- [x] Measure: validation time, satisfaction (1-5 scale), completion rate
- [x] Target: ≥4/5 satisfaction, <5 min validation time for 50 entities
- [x] Document feedback and iterate on UX if needed

---

#### TD-003: Resolve Type Ignore Comments in regex_matcher.py ✅ COMPLETE (Commit 4e7533d)
**Source:** Story 1.8 QA Gate
**Description:** Fix 2 instances of `# type: ignore` comments by updating DetectedEntity signature
**Impact:** Minor - doesn't affect functionality but improves type safety
**Effort:** Very Low (20 minutes)
**Target:** Epic 2 - Task 2.1.1 (during Story 2.1 setup)
**Epic 2 Assignment:** Task 2.1.1: Resolve Type Ignore Comments (quick task)
**Rationale:** Quick win (20 min); clean code before Epic 2 adds more regex/NLP integration
**Completed:** 2026-01-22 (Commit 4e7533d) — Added `source` and `is_ambiguous` fields to DetectedEntity, mypy clean
**References:**
- [gdpr_pseudonymizer/nlp/regex_matcher.py:157,222](../gdpr_pseudonymizer/nlp/regex_matcher.py)
- [docs/qa/gates/1.8-hybrid-detection-strategy.yml](qa/gates/1.8-hybrid-detection-strategy.yml)

**Acceptance Criteria:**
- [x] Remove `# type: ignore` comments (lines 157, 222)
- [x] Update DetectedEntity dataclass if needed
- [x] mypy type checking passes with no errors
- [x] All existing tests still pass

---

#### TD-004: Python Version Support Inconsistency ✅ COMPLETE (Story 4.3 AC9 + Story 4.5)
**Source:** PM Review (2026-02-04)
**Description:** Misalignment between pyproject.toml, CI/CD matrix, and documentation regarding Python version support
**Impact:** Medium - Users may attempt installation on untested Python versions; CI doesn't verify claimed compatibility
**Effort:** Low (1-2 hours)
**Target:** Epic 4 - Story 4.3 AC9 (Complete Documentation Package)
**Owner:** DevOps / PM to verify spaCy compatibility before expansion
**Epic 4 Assignment:** Story 4.3 AC9: Python version alignment across all sources
**Rationale:** Story 4.2 confirmed Python 3.12 works on Ubuntu 24.04 and Fedora 39; Story 4.3 documentation package is the natural place to align all references
**Completed:** 2026-02-09 — CI matrix updated to 3.10-3.12; Python 3.13 blocked by thinc (see MON-005)

**Resolved State:**
| Source | Python Versions | Notes |
|--------|-----------------|-------|
| pyproject.toml | `>=3.10,<3.13` | Aligned with CI |
| CI/CD (ci.yaml) | `['3.10', '3.11', '3.12']` | All tested |
| Documentation | 3.10-3.12 | Consistent |

**Acceptance Criteria:**
- [x] Verify spaCy 3.7+ wheel availability for Python 3.12 and 3.13
- [x] If verified: Add 3.12 and 3.13 to CI/CD matrix (ci.yaml)
- [x] If NOT verified: Tighten pyproject.toml to match actual tested versions
- [x] Update ALPHA-INSTALL.md to match pyproject.toml
- [x] Update coding-standards.md to match pyproject.toml
- [x] Update TD-001 acceptance criteria to match actual CI matrix
- [x] All documentation reflects actual tested/supported versions

**References:**
- [pyproject.toml](../pyproject.toml):14
- [.github/workflows/ci.yaml](../.github/workflows/ci.yaml):17
- [docs/ALPHA-INSTALL.md](ALPHA-INSTALL.md):13
- [docs/architecture/19-coding-standards.md](architecture/19-coding-standards.md):27

---

## 🌟 Future Enhancements

### LOW Priority

#### FE-001: Visual Indicator for Context Cycling ⏸️ DEFERRED TO EPIC 3
**Source:** Story 1.9 QA Gate (Future Recommendation)
**Description:** Add visual indicator (e.g., dot navigation ● ○ ○) to improve context cycling discoverability
**Impact:** Improves UX for users who may not discover X key for context cycling
**Effort:** Low (1-2 hours)
**Target:** Epic 3 (UI polish) or v1.1
**Epic 2 Decision:** DEFER - Epic 2 has no UI polish scope. Epic 3 Story 3.4 (CLI UX polish) is natural home.
**References:**
- [gdpr_pseudonymizer/validation/ui.py:255-259](../gdpr_pseudonymizer/validation/ui.py)
- [docs/qa/gates/1.9-entity-deduplication-validation-ui.yml](qa/gates/1.9-entity-deduplication-validation-ui.yml)

**Proposed Design:**
```
Context (2/5): ○ ● ○ ○ ○  [Press X to cycle]
"...during the interview with Marie Dubois about..."
```

---

#### FE-002: Batch Operations Visual Feedback ⏸️ DEFERRED TO EPIC 3
**Source:** Story 1.7 QA Gate (Future Recommendation)
**Description:** Add visual feedback for batch operations (Shift+A/R) to confirm action
**Impact:** Improves confidence that batch action was applied correctly
**Effort:** Low (2-3 hours)
**Target:** Epic 3 (UI polish) or v1.1
**Epic 2 Decision:** DEFER - Epic 2 has no UI polish scope. Epic 3 Story 3.4 (CLI UX polish) is natural home.
**References:**
- [gdpr_pseudonymizer/validation/ui.py](../gdpr_pseudonymizer/validation/ui.py)
- [docs/qa/gates/1.7-validation-ui-implementation.yml](qa/gates/1.7-validation-ui-implementation.yml)

**Proposed Design:**
```
✓ Accepted all 15 PERSON entities
  → Marie Dubois (10 occurrences) ✓
  → Jean Martin (5 occurrences) ✓
Press Enter to continue...
```

---

#### FE-003: Performance Regression Tests with pytest-benchmark 🤔 OPTIONAL FOR EPIC 2
**Source:** Story 1.8 QA Gate (Future Recommendation)
**Description:** Add automated performance regression tests using pytest-benchmark
**Impact:** Catch performance regressions in hybrid detection pipeline
**Effort:** Low (1 hour)
**Target:** Epic 2 (optional) - Task 2.6.1 or 2.7.1, or defer to Epic 3
**Epic 2 Assignment:** Task 2.6.1 or 2.7.1 (optional - during Story 2.6 or 2.7)
**Rationale:** Story 2.6 AC5 requires performance validation; automated benchmarks > manual testing. Optional if time permits.
**References:**
- [docs/qa/gates/1.8-hybrid-detection-strategy.yml](qa/gates/1.8-hybrid-detection-strategy.yml)
- AC8 (Story 1.8)
- Epic 2 Story 2.6 AC5, Story 2.7 AC4

**Acceptance Criteria:**
- [ ] Install pytest-benchmark
- [ ] Add benchmark tests for hybrid detection (target: <30s per document)
- [ ] Add benchmark tests for validation workflow (target: <5 min for 100 entities)
- [ ] Integrate into CI/CD pipeline with threshold alerts

---

#### FE-004: Alternative Key for Context Cycling
**Source:** Story 1.9 QA Gate (Future Recommendation)
**Description:** Monitor user feedback on X key for context cycling - consider alternative if conflicts arise
**Impact:** X key may conflict with user muscle memory or other tools
**Effort:** Low (30 minutes to change key binding)
**Target:** Post-MVP (v1.1) if user feedback indicates issue
**References:**
- [gdpr_pseudonymizer/validation/ui.py:42-43](../gdpr_pseudonymizer/validation/ui.py)
- [docs/qa/gates/1.9-entity-deduplication-validation-ui.yml](qa/gates/1.9-entity-deduplication-validation-ui.yml)

**Options to Consider:**
- Tab key (cycle through contexts)
- Arrow keys (Left/Right to cycle)
- V key (View all contexts)

---

---

## 🔥 HIGH Priority Enhancements

#### FE-005: LOCATION and ORGANIZATION Pseudonym Libraries ✅ COMPLETED (Story 3.0)
**Source:** Story 2.9 Alpha Testing Preparation (discovered during quick test)
**Description:** Add LOCATION and ORGANIZATION pseudonym libraries for all 3 themes (neutral, star_wars, lotr)
**Status:** ✅ **COMPLETED** - Implemented in Story 3.0 (2026-02-02)
**References:**
- [docs/stories/3.0.location-org-pseudonym-libraries.story.md](stories/3.0.location-org-pseudonym-libraries.story.md)

---

### MEDIUM Priority

#### FE-006: Expand Organization Pseudonym Library ✅ COMPLETED (Story 4.6)
**Source:** Story 3.0 - Batch processing testing (2026-02-02)
**Description:** Expand neutral theme organization library from 35 to 150-200 entries to support larger document corpora without exhausting the library and falling back to generic naming (Org-001, etc.)
**Status:** ✅ **COMPLETED** - Implemented in Story 4.6 Task 4.6.6 (2026-02-09)
**Outcome:** Expanded neutral.json from 35 to 196 ORG entries (101 companies, 50 agencies, 45 institutions). Location library (80 entries) evaluated as sufficient. Themed libraries (35 each) adequate for their design intent.
**References:**
- [data/pseudonyms/neutral.json](../data/pseudonyms/neutral.json)
- [docs/stories/4.6.beta-feedback-integration-bug-fixes.story.md](stories/4.6.beta-feedback-integration-bug-fixes.story.md)

---

#### FE-007: Gender-Aware Pseudonym Assignment 📅 PLANNED FOR v1.1
**Source:** Alpha/beta user feedback (2026-02)
**Description:** Female names should receive female pseudonyms and male names should receive male pseudonyms, maintaining gender coherence in pseudonymized documents for LLM utility
**Impact:** Medium — improves LLM utility score and document readability; currently female names may receive male pseudonyms
**Effort:** Medium (2-3 days)
**Target:** v1.1 — Epic 5 Story 5.2
**Rationale:** Pseudonym libraries already have gender-tagged first names; only the detection/assignment logic is missing. French first-name gender lookup (from existing library data + INSEE public data) enables gender-matched assignment.

**Acceptance Criteria:**
- [ ] French name gender detection via heuristic lookup (≥90% coverage of common first names)
- [ ] Gender detection integrated into pseudonym assignment pipeline
- [ ] Female entity → female pseudonym, male → male, unknown → combined list (no regression)
- [ ] Compound names handled (first component determines gender)

**References:**
- [gdpr_pseudonymizer/pseudonym/library_manager.py](../gdpr_pseudonymizer/pseudonym/library_manager.py)
- [docs/prd/epic-5-v1.1-quick-wins-gdpr-compliance.md](prd/epic-5-v1.1-quick-wins-gdpr-compliance.md) — Story 5.2

---

#### FE-008: GDPR Right to Erasure — `delete-mapping` Command ✅ COMPLETED (Story 5.1)
**Source:** GDPR Article 17 compliance gap analysis (2026-02)
**Description:** Implement `delete-mapping` CLI command to delete specific entity mappings from the database, fulfilling Article 17 erasure requests. Deleting a mapping converts pseudonymization into anonymization (data exits GDPR scope).
**Status:** ✅ **COMPLETED** — Implemented in Story 5.1 (2026-02-11)
**Outcome:** `delete-mapping` command (by name or UUID, with confirmation + `--force`), `list-entities` command (search/filter/type), ERASURE audit logging, 38 new tests. Full GDPR Article 17 compliance achieved.
**References:**
- [docs/stories/5.1.gdpr-right-to-erasure.story.md](stories/5.1.gdpr-right-to-erasure.story.md)
- [docs/prd/epic-5-v1.1-quick-wins-gdpr-compliance.md](prd/epic-5-v1.1-quick-wins-gdpr-compliance.md) — Story 5.1

**Acceptance Criteria:**
- [x] `delete-mapping` command: delete by entity name or UUID, with passphrase verification
- [x] Confirmation prompt showing entity details (name, type, pseudonym) with permanent deletion warning
- [x] Audit log entry with `operation_type='ERASURE'`
- [x] `list-entities` command with search/filter capability

---

#### FB-004: PDF/DOCX Input Format Support 📅 PLANNED FOR v1.1
**Source:** Alpha/beta user feedback (2026-02)
**Description:** Support PDF and DOCX input formats in the `process` and `batch` commands, extracting text before running the existing NER/validation/pseudonymization pipeline
**Impact:** Medium — second most requested alpha feature; real-world users have documents in PDF (academic papers, legal documents) and DOCX (HR files, interview transcripts)
**Effort:** Medium-High (1-2 weeks)
**Target:** v1.1 — Epic 5 Story 5.5
**Rationale:** Manual conversion to .txt loses formatting and creates friction. Text extraction from PDF/DOCX is well-supported by Python libraries. Output as .txt only for v1.1 (format preservation deferred to v1.2).

**Acceptance Criteria:**
- [ ] PDF text extraction (pdfplumber or PyMuPDF) — multi-page, scanned PDF warning
- [ ] DOCX text extraction (python-docx) — paragraphs, headers, tables (best-effort)
- [ ] New dependencies as optional extras: `pip install gdpr-pseudonymizer[pdf,docx]`
- [ ] No regression in existing .txt/.md processing

**References:**
- [docs/prd/epic-5-v1.1-quick-wins-gdpr-compliance.md](prd/epic-5-v1.1-quick-wins-gdpr-compliance.md) — Story 5.5

---

#### FE-011: NLP Accuracy — Regex Pattern Expansion 📅 POST-MVP
**Source:** Story 4.4 NER Accuracy Report, MON-003 Baseline Review
**Description:** Expand regex patterns to address lowest-accuracy edge case categories identified in Story 4.4 accuracy validation
**Impact:** High — LOCATION FN=37%, ORG FN=66%, Last/First recall=0%. Regex improvements are the fastest path to reducing user-added entities in validation mode
**Effort:** Medium (1-2 days)
**Target:** v1.1 (post-MVP)
**Rationale:** Story 4.4 identified specific pattern gaps causing high false negative rates. These are independent of NLP model fine-tuning and can be implemented incrementally.

**Specific Improvements:**
1. **Last, First name format** (0% recall): Add regex for `LastName, FirstName` pattern (e.g., "Dubois, Jean-Marc")
2. **ORG suffix expansion**: Add patterns for Association, Fondation, Institut, Groupe, Consortium, Fédération
3. **LOCATION dictionary**: Add French city/department/region dictionary to supplement spaCy detection
4. **Title normalization**: Improve matching when titles (Dr., M., Mme.) are part of annotated entities

**Acceptance Criteria:**
- [ ] Last, First regex pattern added to `regex_matcher.py`
- [ ] ORG suffix patterns expanded (target: 15+ suffixes)
- [ ] French geography dictionary added (top 100 cities, 13 regions, 101 departments)
- [ ] Accuracy test re-run shows measurable improvement (target: LOCATION FN <25%, ORG FN <50%)
- [ ] No regression in PERSON detection

**References:**
- [docs/qa/ner-accuracy-report.md](qa/ner-accuracy-report.md) — Edge Case Analysis, Recommendations
- [docs/qa/monitoring-baselines-4.4.md](qa/monitoring-baselines-4.4.md) — MON-003 findings
- [gdpr_pseudonymizer/nlp/regex_matcher.py](../gdpr_pseudonymizer/nlp/regex_matcher.py)

---

#### FE-012: Ground-Truth Annotation Quality Cleanup 📅 POST-MVP
**Source:** Story 4.4 Task 4.4.1 corpus validation
**Description:** Clean up annotation quality issues discovered during Story 4.4 accuracy validation
**Impact:** Medium — annotation quality issues inflate FN counts and make accuracy metrics unreliable for trend analysis
**Effort:** Low (2-4 hours)
**Target:** v1.1 (before next accuracy benchmark)

**Issues Identified:**
1. **Entity count discrepancy:** `tests/test_corpus/annotations/README.md` claims 3,230 entities but actual count is 1,855
2. **board_minutes.json quality:** Entities spanning newlines, ORGs mislabeled as PERSON, truncated entities at hyphen boundaries, garbage annotations (e.g., "élicite Mme")
3. **Title inclusion inconsistency:** Some annotations include titles ("Mme Sophie Laurent") while others don't ("Sophie Laurent")

**Acceptance Criteria:**
- [ ] README entity count corrected to match actual count
- [ ] board_minutes.json annotations cleaned (fix or remove garbage entries)
- [ ] Consistent annotation policy for titles documented
- [ ] Accuracy test re-run to establish clean baseline

**References:**
- [tests/test_corpus/annotations/README.md](../tests/test_corpus/annotations/README.md)
- [tests/test_corpus/annotations/board_minutes.json](../tests/test_corpus/annotations/board_minutes.json)
- [docs/qa/ner-accuracy-report.md](qa/ner-accuracy-report.md) — Known Limitations

---

#### FE-013: Confidence Score Calibration Layer 📅 v1.1+
**Source:** Story 4.4 Confidence Score Analysis (AC6)
**Description:** Implement a confidence calibration layer to enable confidence-based auto-accept/auto-reject in validation mode
**Impact:** Medium — would allow skipping validation for high-confidence entities, reducing user effort
**Effort:** High (1-2 weeks — requires ML training)
**Target:** v1.1+ (dependent on FE-011 regex improvements first)
**Rationale:** Story 4.4 found 83.8% of entities have confidence=None (spaCy limitation). The 16.2% with regex confidence scores show counterintuitive precision (0.5-0.7 bucket better than 0.7-0.9). A dedicated calibration model is needed.

**Acceptance Criteria:**
- [ ] Calibration model trained on ground-truth corpus
- [ ] All detected entities assigned meaningful confidence (0.0-1.0)
- [ ] Higher confidence correlates with higher precision (monotonic)
- [ ] Optional `--auto-accept-threshold` flag in validation mode

**References:**
- [docs/qa/ner-accuracy-report.md](qa/ner-accuracy-report.md) — Confidence Score Analysis

---

#### FE-014: Extended Coreference Resolution 📅 POST-MVP
**Source:** Story 4.6 FB-001 (alpha feedback — entity variant grouping)
**Description:** Extend entity variant grouping beyond heuristic suffix/prefix matching to full NLP coreference resolution (pronoun resolution, contextual entity linking)
**Impact:** Medium — current heuristic grouping handles common cases (title variants, last-name-only references) but misses pronoun references ("il", "elle") and complex coreference chains
**Effort:** High (1-2 weeks — requires coreference model integration)
**Target:** v1.1+ (dependent on NLP model improvements)
**Rationale:** Story 4.6 implemented basic variant grouping (suffix matching, title stripping, preposition stripping). Full coreference resolution requires a dedicated NLP component (e.g., neuralcoref, crosslingual-coreference) which is out of scope for MVP.

**Acceptance Criteria:**
- [ ] Pronoun resolution for French (il/elle → nearest PERSON entity)
- [ ] Cross-sentence entity linking (contextual coreference)
- [ ] Integration with validation UI (grouped entities include pronoun references)
- [ ] No regression in current variant grouping behavior

**References:**
- [gdpr_pseudonymizer/nlp/entity_grouping.py](../gdpr_pseudonymizer/nlp/entity_grouping.py) — current heuristic implementation
- [docs/qa/alpha-feedback-summary.md](qa/alpha-feedback-summary.md) — FB-001 original feedback

---

#### FE-010: French Documentation Translation 📅 PLANNED FOR v1.1
**Source:** PM session (2026-02-08)
**Description:** Translate all user-facing documentation into French to serve the primary target audience (French-speaking researchers, HR professionals, compliance officers)
**Impact:** High — removes language barrier for the primary user base; lowers adoption friction before v2.0 GUI
**Effort:** Medium (1-2 weeks)
**Target:** v1.1 (Q2-Q3 2026)
**Rationale:** Primary audience is French-speaking (stated across PRD). Documentation translation is independent of the v2.0 GUI i18n effort and delivers immediate value to CLI users.

**Scope:**
- README.md (French version or bilingual)
- ALPHA-INSTALL.md / installation guide
- CLI `--help` text and error messages
- User guide / FAQ / troubleshooting
- CHANGELOG (summary sections)

**Out of Scope (deferred to v2.0 i18n):**
- GUI interface translation
- i18n architecture / framework
- Developer-facing docs (architecture, PRD, stories)

**Acceptance Criteria:**
- [ ] French README available (README.fr.md or bilingual README)
- [ ] French installation guide available
- [ ] CLI `--help` output available in French (via `--lang fr` flag or locale detection)
- [ ] User guide translated into French
- [ ] Language toggle or clear navigation between EN/FR versions
- [ ] Native French speaker review for quality

---

#### FE-015: Excel and Google Sheets Format Support 📅 POST-v2.0 (v2.1+)
**Source:** User inquiry (2026-02-19)
**Description:** Support Excel (.xlsx, .xls) and CSV formats for structured data pseudonymization. Google Sheets require export-to-Excel workflow (local-only architecture constraint).
**Impact:** Medium — HR/compliance professionals (GUI target audience) heavily use Excel for employee data, case management, research datasets
**Effort:** Medium (1-2 weeks)
**Target:** v2.1 or v2.2 (after v2.0 GUI ships)
**Rationale:** Natural extension after v2.0 GUI launch. Can leverage existing DOCX parser patterns. Structural preservation (formulas, formatting) adds complexity vs plain text extraction.

**Scope:**
- **Simple approach:** Process spreadsheet cells as plain text (flatten structure)
- **Advanced approach:** Preserve structure (columns, formulas, formatting) while pseudonymizing specific cells

**Acceptance Criteria:**
- [ ] Excel file loading (.xlsx, .xls) via openpyxl or xlrd
- [ ] CSV file support for simple tabular data
- [ ] Cell-by-cell entity detection and pseudonymization
- [ ] Output format options: Excel (preserve structure) or text (flattened)
- [ ] Google Sheets workflow documented (export → Excel → process)
- [ ] No regression in existing format support

**References:**
- v2.0 GUI target audience (HR professionals, compliance officers)
- Epic 5 Story 5.5 (PDF/DOCX format support — similar pattern)

---

#### FE-016: Neutral/Generic Pseudonym Theme 📅 v2.0 or v2.1
**Source:** User request (2026-02-19)
**Description:** Add a "neutral" pseudonym theme option that uses generic identifiers (PER-001, PER-002, LOC-001, ORG-001, etc.) instead of named pseudonyms. Alternative to existing themes (french, lotr, star_wars).
**Impact:** Medium — useful for formal/legal contexts where themed names feel inappropriate, maximum anonymity (no cultural associations), simpler for automated data processing
**Effort:** Low (1-2 days)
**Target:** v2.0 (GUI) or v2.1
**Rationale:** Low implementation effort, clear use case. Can be added alongside GUI theme selector. No pseudonym library needed (counter-based generation).

**Use Cases:**
- Legal/compliance documentation requiring maximum formality
- Research datasets where cultural/thematic associations are undesirable
- Automated processing pipelines that prefer generic IDs
- Users who want pure anonymization without character-based pseudonyms

**Implementation Notes:**
- Counter-based generation per entity type (PERSON-001, LOCATION-001, ORGANIZATION-001)
- Or shorter format: PER-001, LOC-001, ORG-001
- Should support compositional logic (if "Marie Dubois" → PER-001, then "Marie" → PER-001-F, "Dubois" → PER-001-L)
- No library files needed — purely algorithmic

**Acceptance Criteria:**
- [ ] New theme option: `--theme neutral` (CLI) or "Neutral/Generic" (GUI dropdown)
- [ ] Generates identifiers: PER-{n}, LOC-{n}, ORG-{n} (or PERSON-{n} format, TBD)
- [ ] Compositional pseudonymization works (first/last name components)
- [ ] Mapping table stores neutral pseudonyms like any other theme
- [ ] Documentation updated (theme comparison table)
- [ ] No regression in existing theme functionality

**References:**
- Existing themes: data/pseudonyms/{french,lotr,star_wars}.json
- Theme selection: CLI `--theme` flag, GUI settings (Story 6.2)

---

#### FE-017: Persist Last-Used Database Across App Restarts 📅 v2.0
**Source:** User feedback (2026-02-20)
**Description:** After selecting a database in the PassphraseDialog, persist that choice so it becomes the default on next app launch. Currently the app auto-detects databases but never remembers which one was last used — users must re-select every session.
**Impact:** Low-Medium — reduces friction for users who always work with the same database; especially important for single-project workflows
**Effort:** Low (1-2 hours)
**Target:** v2.0 (next GUI story)
**Rationale:** Config infrastructure already exists (`default_db_path` in `.gdpr-pseudo.yaml`, `save_gui_config()`). Only needs a `save_gui_config()` call after successful passphrase validation in `PassphraseDialog` or `HomeScreen._start_processing()`.

**Implementation Notes:**
- After successful DB selection + passphrase entry, save `config["default_db_path"] = db_path` via `save_gui_config()`
- On next launch, `PassphraseDialog._populate_db_paths()` already checks `config["default_db_path"]` — just needs to pre-select it in the combo box
- Consider: should "Create a new base" reset the default? Probably yes (new DB becomes default)

**Acceptance Criteria:**
- [ ] After selecting a database, the choice is persisted in `.gdpr-pseudo.yaml` as `default_db_path`
- [ ] On next app launch, the previously used database is pre-selected in the PassphraseDialog combo box
- [ ] Creating a new database also persists it as the new default
- [ ] User can still override by selecting a different database (choice updates the default)
- [ ] No regression in existing database detection or passphrase flow

**References:**
- `gdpr_pseudonymizer/gui/config.py` — `load_gui_config()`, `save_gui_config()`
- `gdpr_pseudonymizer/gui/widgets/passphrase_dialog.py` — `_populate_db_paths()`
- `gdpr_pseudonymizer/gui/screens/home.py` — `_start_processing()`

---

#### FE-018: Show Validation Keyboard Shortcuts in Help Menu 📅 v2.0
**Source:** User feedback (2026-02-20)
**Description:** The F1 keyboard shortcuts dialog and the Settings screen shortcuts section only show 6 global shortcuts. The powerful keyboard navigation mode (Enter, Tab, Delete, Escape) and validation shortcuts (Ctrl+Z, Ctrl+F) are completely undocumented in the UI — users can only discover them by accident.
**Impact:** Medium — expert mode is a key productivity feature but zero discoverability makes it effectively invisible to most users
**Effort:** Low (1-2 hours)
**Target:** v2.0 (next GUI story)
**Rationale:** No code logic changes needed — just update the help dialog text and Settings shortcuts section to include all shortcuts.

**Missing Shortcuts (to add):**
- **Navigation mode:** Enter (activate), Tab/Shift+Tab (next/prev entity), Enter (accept), Delete (reject), Shift+F10 (context menu), Escape (exit mode)
- **Validation screen:** Ctrl+Z (undo), Ctrl+Shift+Z / Ctrl+Y (redo), Ctrl+F (filter entities)
- **Editor:** Ctrl++ (zoom in), Ctrl+- (zoom out)

**Acceptance Criteria:**
- [ ] F1 help dialog lists all keyboard shortcuts grouped by context (Global, Validation, Navigation Mode, Editor)
- [ ] Settings screen shortcuts section updated to match
- [ ] Navigation mode section clearly explains how to activate/deactivate (Enter to start, Escape to exit)
- [ ] Shortcuts displayed in French (consistent with existing UI language)
- [ ] No regression in existing help/settings functionality

**References:**
- `gdpr_pseudonymizer/gui/main_window.py:166-176` — `_show_shortcuts()` help dialog
- `gdpr_pseudonymizer/gui/screens/settings.py:181-202` — shortcuts section
- `gdpr_pseudonymizer/gui/widgets/entity_editor.py:369-527` — navigation mode implementation
- `gdpr_pseudonymizer/gui/screens/validation.py:133-148` — validation shortcuts

---

#### FE-019: "Masquer les validées" Toggle — Hide Confirmed Entities 📅 v2.0
**Source:** User feedback (2026-02-20)
**Description:** Add a "Masquer les validées" checkbox next to the existing "Masquer les rejetées" toggle. When enabled, confirmed/accepted entities are hidden from the document view, letting users focus on remaining pending entities. Mirrors the existing hide-rejected pattern exactly.
**Impact:** Medium — significantly improves focus during validation of large documents where many entities are already confirmed; complementary to existing "masquer les rejetées"
**Effort:** Low (1-2 hours)
**Target:** v2.0 (next GUI story)
**Rationale:** Exact mirror of existing hide-rejected implementation. Same architecture: checkbox → signal → `set_hide_confirmed()` → skip in `_apply_highlights()`.

**Implementation Notes:**
- Add `_hide_confirmed_cb = QCheckBox("Masquer les validées")` in `EntityPanel._build_ui()` next to existing `_hide_rejected_cb`
- Add `set_hide_confirmed(hide: bool)` method to `EntityEditor` (mirrors `set_hide_rejected`)
- Add skip logic in `_apply_highlights()`: `if is_confirmed and self._hide_confirmed: continue`
- Connect signal in `ValidationScreen._connect_signals()`
- Consider: should this also hide known/auto-accepted entities? Probably yes (same visual state)

**Acceptance Criteria:**
- [ ] "Masquer les validées" checkbox visible next to "Masquer les rejetées" in the entity panel
- [ ] When toggled on, confirmed and known entities are hidden from document highlights
- [ ] Pending and rejected entities remain visible
- [ ] Toggle state does not persist across sessions (same behavior as hide-rejected)
- [ ] No regression in existing hide-rejected functionality
- [ ] Works correctly in both light and dark themes

**References:**
- `gdpr_pseudonymizer/gui/widgets/entity_panel.py:101-103` — existing `_hide_rejected_cb` pattern
- `gdpr_pseudonymizer/gui/widgets/entity_editor.py:98-101, 166-168` — existing `set_hide_rejected` + skip logic
- `gdpr_pseudonymizer/gui/screens/validation.py:128-131` — existing signal connection

---

#### FE-020: Validate-Once-Per-Entity — Group Occurrences on Accept/Reject 📅 v2.0
**Source:** User feedback (2026-02-20)
**Description:** When a user accepts or rejects an entity (e.g., "Marie Dupont"), ALL occurrences of that same entity in the document should be accepted/rejected at once. Currently each occurrence has its own `entity_id` and must be validated individually — "Marie Dupont" appearing 8 times requires 8 separate validations.
**Impact:** High — this is the single biggest friction point in the validation workflow for documents with repeated entities; directly reduces validation time proportionally to entity repetition count
**Effort:** Medium (3-4 hours)
**Target:** v2.0 (next GUI story)
**Rationale:** The `bulk_accept(entity_ids)` infrastructure already exists in `GUIValidationState`. The missing piece is grouping reviews by canonical entity text and dispatching a bulk action when any single occurrence is accepted/rejected.

**Implementation Notes:**
- `GUIValidationState` already stores all `EntityReview` objects; need a reverse index from entity text → list of entity_ids
- When `accept_entity(entity_id)` is called, look up all other reviews with the same `entity.text` (or canonical form) and call `bulk_accept()` on all of them
- Use existing `_BulkActionCommand` for undo/redo support (undoing groups all occurrences back)
- Edge case: should this apply to keyboard navigation (Enter) and context menu accept equally? Yes — all accept/reject actions should propagate
- Edge case: partial names — "Marie" vs "Marie Dupont" should NOT group together (different entity text)
- Consider: make this opt-out via a setting? Probably not — validate-once is the expected default behavior

**Acceptance Criteria:**
- [ ] Accepting one occurrence of "Marie Dupont" confirms all occurrences in the document
- [ ] Rejecting one occurrence rejects all occurrences
- [ ] Undo reverses the group action (all occurrences revert to previous state)
- [ ] Sidebar list updates immediately for all affected occurrences
- [ ] Document highlights update immediately for all affected occurrences
- [ ] Different entity texts are NOT grouped (e.g., "Marie" and "Marie Dupont" remain independent)
- [ ] Works from keyboard navigation (Enter/Delete), context menu, and bulk selection
- [ ] No regression in existing bulk accept/reject by type or checkbox selection

**References:**
- `gdpr_pseudonymizer/gui/widgets/validation_state.py:112-115` — `accept_entity()` current single-id logic
- `gdpr_pseudonymizer/gui/widgets/validation_state.py:156-164` — `bulk_accept()` existing infrastructure
- `gdpr_pseudonymizer/gui/widgets/validation_state.py:144` — `EntityReview` with unique `entity_id` per occurrence
- `gdpr_pseudonymizer/gui/screens/validation.py:291-295` — `_on_entity_state_changed()` refresh logic

---

#### FE-021: Database Operations on Background Thread 📅 v2.0 → Story 6.7
**Source:** Story 6.5 QA Gate (PERF-001)
**Description:** `DatabaseScreen` performs all database operations (entity listing, search/filter, Article 17 deletion, CSV export) on the main GUI thread. Large databases will freeze the UI during these operations, blocking assistive technologies and violating WCAG 2.1 Principle 2 (Operable).
**Impact:** Medium — UI responsiveness degrades with large mapping databases; blocks screen reader interaction during operations
**Effort:** Medium (2-3 days)
**Target:** v2.0 — Story 6.7 (Accessibility / WCAG AA)
**Rationale:** The `QRunnable + WorkerSignals` pattern is already established in `ProcessingWorker` and `BatchWorker`. Applying it to `DatabaseScreen` operations is architectural consistency and directly addresses WCAG AA responsive UI requirements.

**Acceptance Criteria:**
- [ ] Entity listing, search, and filter operations run on a background thread via `QRunnable + WorkerSignals`
- [ ] Article 17 deletion runs on a background thread with progress indication
- [ ] CSV export runs on a background thread with progress indication
- [ ] Main thread remains responsive during all database operations
- [ ] Error handling displays user-friendly messages on failure
- [ ] No regression in existing `DatabaseScreen` functionality

**References:**
- `gdpr_pseudonymizer/gui/screens/database.py` — current main-thread implementation
- `gdpr_pseudonymizer/gui/workers/processing_worker.py` — established `QRunnable + WorkerSignals` pattern
- `gdpr_pseudonymizer/gui/workers/batch_worker.py` — established `QRunnable + WorkerSignals` pattern
- `docs/qa/gates/6.5-batch-processing-and-configuration-management.yml` — PERF-001

---

#### FE-022: Batch Validation Workflow 📅 v2.0 → Story 6.7
**Source:** Story 6.5 AC3 (DEFERRED-001)
**Description:** Batch processing currently forces `skip_validation=True`, removing user control over entity decisions for multi-document workflows. An optional validation step between documents would allow users to review and confirm/reject detected entities before pseudonymization proceeds, maintaining the same level of control available in single-document mode.
**Impact:** Medium — users who need entity review in batch mode currently have no option; reduces trust in batch output quality
**Effort:** Medium (3-4 days)
**Target:** v2.0 — Story 6.7 (Accessibility / WCAG AA)
**Rationale:** WCAG Principle 2 (Operable) requires that users maintain control over functionality. Batch mode removing validation choice is an operability gap. Groups naturally with FE-020 (Validate-Once-Per-Entity) — both are about user control during validation workflows.

**Acceptance Criteria:**
- [ ] Batch processing offers an optional "Validate entities" mode (checkbox or toggle in batch config)
- [ ] When enabled, after entity detection for each document, the validation screen is presented
- [ ] User can accept/reject entities before pseudonymization of that document proceeds
- [ ] "Skip validation" remains the default for fully automated batch runs
- [ ] Validation decisions persist across documents in the same batch (via shared mapping database)
- [ ] Progress tracking accounts for validation time (not just processing time)
- [ ] No regression in existing skip-validation batch mode

**References:**
- `gdpr_pseudonymizer/gui/screens/batch.py` — current batch workflow (skip_validation=True)
- `gdpr_pseudonymizer/gui/screens/validation.py` — existing validation screen
- `gdpr_pseudonymizer/gui/workers/batch_worker.py` — `BatchWorker` document loop
- `docs/qa/gates/6.5-batch-processing-and-configuration-management.yml` — DEFERRED-001

---

## 📊 Monitoring Items

### MON-001: Validation UI Performance with Real Users
**Source:** Story 1.9 QA Gate
**Description:** Monitor user validation time with real-world large documents (100+ entities)
**Metric:** Validation time per unique entity, user completion rate
**Target:** <10 seconds per unique entity, ≥90% completion rate
**Action if Missed:** Investigate UX bottlenecks, consider additional optimizations

---

### MON-002: Hybrid Detection Processing Time in Production
**Source:** Story 1.8 QA Gate
**Description:** Monitor hybrid detection processing time to ensure 0.07s average holds at scale
**Metric:** Processing time per document (avg, p95, p99)
**Target:** <30s per document (current: 0.07s)
**Action if Missed:** Profile performance, optimize regex patterns or spaCy loading

---

### MON-003: LOCATION and ORG Detection Accuracy
**Source:** Story 1.8 QA Gate
**Description:** Monitor LOCATION (+24.2%) and ORG (+3.1%) detection improvements in production
**Metric:** User-reported false negatives (missed entities) by type
**Target:** <10% user-added entities for LOCATION/ORG
**Action if Missed:** Add additional regex patterns for LOCATION/ORG

---

### MON-004: Context Cycling UX Discoverability
**Source:** Story 1.9 QA Gate
**Description:** Track whether users discover and use X key for context cycling
**Metric:** Usage logs (if added), user survey feedback
**Target:** ≥50% of users use context cycling for multi-occurrence entities
**Action if Missed:** Improve discoverability (e.g., FE-001 visual indicator)

---

### MON-005: spaCy Python 3.12/3.13/3.14 Compatibility
**Source:** Story 1.8 QA Gate, PM Review (2026-02-04)
**Owner:** PM (quarterly check) + DevOps (implementation)
**Description:** Monitor spaCy releases for Python version compatibility; verify wheel availability before expanding support
**Metric:** spaCy release notes, PyPI wheel availability, GitHub issues
**Frequency:** Quarterly review (or upon major spaCy/Python release)
**Target:** Add Python version to CI within 1 month of confirmed spaCy wheel availability
**Action if Available:**
1. Verify spaCy wheels available on PyPI for target Python version
2. Test locally: `pip install spacy` on target Python version
3. Run full test suite on target version
4. If passing: Update CI matrix, pyproject.toml, and documentation (see TD-004)

**Current Status (2026-02-09):**
| Python | spaCy Status | CI Status | Action Needed |
|--------|--------------|-----------|---------------|
| 3.12 | ✅ Verified | ✅ In matrix | None |
| 3.13 | ❌ Blocked (thinc lacks cp313 wheels) | ❌ Not in matrix | Monitor thinc releases |
| 3.14 | ❌ Pre-release | N/A | Monitor |

**Story 4.6 Finding (2026-02-09):** Python 3.13 blocked by `thinc` (spaCy's ML backend). Neither thinc 8.3.2 (locked) nor thinc 9.1.1 (latest) publishes cp313 wheels. Also blocked: `srsly` <2.5.0 and `numpy` <2.1.0 lack 3.13 wheels. Re-evaluate when thinc publishes 3.13 support.

**References:**
- spaCy releases: https://github.com/explosion/spaCy/releases
- spaCy PyPI: https://pypi.org/project/spacy/#files
- TD-004: Python Version Support Inconsistency

---

## 🚀 Epic 2+ Planned Features

### Epic 2: Core Pseudonymization Engine (Week 6-10)

**Planned Stories:**
- Story 2.1: Pseudonym generator with themed libraries (Star Wars, LOTR, French names)
- Story 2.2: Compositional pseudonymization (FR4-5) - "Marie Dubois" → "Leia Organa", "Marie" → "Leia"
- Story 2.3: Encrypted mapping tables with passphrase protection
- Story 2.4: Mapping table persistence (SQLite) for batch processing
- Story 2.5: Audit logging for GDPR compliance

**Dependencies from Epic 1:**
- Story 2.2 depends on Story 1.7 validation UI for flagging ambiguous components
- Story 2.4 stores validation user modifications (FR12)

---

### Epic 3: CLI Polish & Batch Processing (Week 11-13)

**Planned Stories:**
- Story 3.1: Batch processing for multiple documents
- Story 3.2: Progress reporting for large batches
- Story 3.3: Configuration file support (.gdpr-pseudo.yaml)
- Story 3.4: CLI UX polish (better error messages, help text)
- Story 3.5: Installation guide and user documentation

**Confirmed Additions from Backlog:**
- ✅ **FE-005:** LOCATION and ORGANIZATION pseudonym libraries (HIGH priority - new Story 3.X or integrate into Story 3.1)

**Potential Additions from Backlog:**
- FE-001: Visual indicator for context cycling (if high user demand)
- FE-002: Batch operations visual feedback

---

### Epic 4: Launch Readiness & LLM Validation (Week 14)

**Planned Stories:**
- Story 4.1: LLM validation (verify pseudonymized docs maintain utility)
- Story 4.2: Methodology documentation for academic citation
- Story 4.3: FAQ and troubleshooting guide
- Story 4.4: Launch checklist (README polish, license selection, etc.)

**Must Complete from Backlog:**
- TD-002: External user testing (→ Story 4.6 AC10)
- TD-004: Python version support alignment (→ Story 4.3 AC9)
- FE-006: Organization pseudonym library expansion (→ Story 4.6 AC9)
- MON-001, MON-003, MON-004 review (→ Story 4.4 AC9)
- MON-002, MON-005 review (→ Story 4.5 AC9)

---

### v1.1 — Epic 5: Quick Wins & GDPR Compliance (Q2 2026)

**Epic File:** [docs/prd/epic-5-v1.1-quick-wins-gdpr-compliance.md](prd/epic-5-v1.1-quick-wins-gdpr-compliance.md)
**Status:** ✅ PM APPROVED (2026-02-11)
**Estimated Duration:** 6-7 weeks (ceiling: 8.5 weeks)

**Assigned to Epic 5 (7 stories):**
- ✅ **FE-008:** GDPR Right to Erasure → Story 5.1 (HIGH) — **DONE** (2026-02-11)
- ✅ **FE-007:** Gender-Aware Pseudonym Assignment → Story 5.2 (MEDIUM)
- ✅ **FE-011 + FE-012:** NER Accuracy & Annotation Quality → Story 5.3 (MEDIUM)
- ✅ **FE-010:** French Documentation Translation → Story 5.4 (MEDIUM)
- ✅ **FB-004:** PDF/DOCX Input Format Support → Story 5.5 (MEDIUM)
- ✅ **FE-001 + FE-002 + FE-003:** CLI Polish & Minor Enhancements → Story 5.6 (LOW)
- ✅ v1.1 Release Preparation → Story 5.7 (HIGH)

**Deferred to v1.2+:**
- FE-013: Confidence score calibration layer (depends on FE-011, HIGH effort)
- FE-014: Extended coreference resolution (research-level complexity)
- FE-004: Alternative context cycling key (monitor user feedback)

**Deferred to v2.0+:**
- FE-009: Standalone executables (coupled with GUI)
- FE-010b: CLI `--help` i18n (requires i18n framework; Typer/click compat risk)
- FB-005: Desktop GUI
- Fine-tuned French NER model (requires curated training data)
- Multi-language support (English, Spanish, German)
- Optional `--no-validate` flag (requires confidence calibration first)

---

## 📝 Notes

### How to Use This Backlog

1. **Technical Debt Items (TD-xxx):** Should be addressed before MVP launch (Week 14) or immediately after
2. **Future Enhancements (FE-xxx):** Nice-to-have items for v1.1 or later
3. **Monitoring Items (MON-xxx):** Track metrics in production, act if targets missed
4. **Epic 2+ Items:** Already planned in roadmap, listed here for visibility

### Prioritization Criteria

- **HIGH:** Blocks production deployment or significantly impacts quality
- **MEDIUM:** Important but not blocking, should address before MVP launch
- **LOW:** Nice-to-have, can defer to v1.1 or later

### Adding New Backlog Items

When adding items from future stories:
1. Assign ID (TD-xxx, FE-xxx, MON-xxx)
2. Specify source (story, QA gate, user feedback)
3. Estimate effort (Very Low, Low, Medium, High)
4. Set target (Epic 2, Epic 3, Epic 4, v1.1, etc.)
5. Define acceptance criteria or monitoring metrics

---

## ✅ Completed Backlog Items

### CB-001: Entity Deduplication (Story 1.9)
**Original Source:** Story 1.7 QA Gate (UX-001)
**Completed:** 2026-01-23
**Outcome:** 66% validation time reduction for large documents, 100% Epic 1 complete

---

**Backlog Maintained By:** Sarah (Product Owner)
**Review Cadence:** End of each epic
**Last Review:** 2026-02-11 (Post-launch cleanup — all epics complete, v1.0 launched)
**Last Update:** 2026-02-11 (Epic 5 created — all v1.1 backlog items assigned to stories)
**Next Review:** After Epic 5 completion (v1.1 release)

---

## 📊 Epic 2 Backlog Summary

### **Completed in Epic 2:**
- ✅ **TD-001:** Integration Tests for Validation Workflow → Story 2.0.1
- ✅ **TD-003:** Resolve Type Ignore Comments → Task 2.1.1

### **Added During Epic 2 (Assigned to Epic 3):**
- ✅ **FE-005:** LOCATION and ORGANIZATION Pseudonym Libraries → Epic 3 (HIGH priority)

### **Optional for Epic 2:**
- 🤔 **FE-003:** Performance Regression Tests → Task 2.6.1 or 2.7.1 (if time permits)

### **Deferred from Epic 2:**
- ⏸️ **TD-002:** External User Testing → Epic 4
- ⏸️ **FE-001:** Visual Indicator for Context Cycling → Epic 3
- ⏸️ **FE-002:** Batch Operations Visual Feedback → Epic 3

### **Monitoring During Epic 2:**
- 📊 **MON-002:** Hybrid detection processing time (Story 2.6 performance validation)
- 📊 **MON-005:** spaCy Python 3.14 compatibility (passive monitoring)

**Epic 2 Status:** ✅ Complete (9/9 stories)
**Epic 2 Actual Duration:** 6 weeks (within allocated 5-week estimate + 1 week tolerance)
**Alpha Release:** v0.1.0-alpha - 2026-01-30
