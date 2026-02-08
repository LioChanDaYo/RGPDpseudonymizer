# Product Backlog - GDPR Pseudonymizer

**Last Updated:** 2026-02-07
**Epic 1 Status:** ✅ Complete (9/9 stories)
**Epic 2 Status:** ✅ Complete
**Epic 3 Status:** ✅ Complete
**Current Epic:** Epic 4 - Launch Readiness & LLM Validation

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

#### TD-001: Integration Tests for Validation Workflow ✅ ASSIGNED TO EPIC 2
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
- [ ] Full validation workflow tests simulating user actions
- [ ] State transition verification (pending → confirmed → rejected)
- [ ] Edge case coverage (empty entities, 100+ entities, Ctrl+C interruption)
- [ ] Tests run in CI/CD pipeline (Python 3.9-3.13)

---

### MEDIUM Priority

#### TD-002: External User Testing for Validation UI ✅ ASSIGNED TO EPIC 4
**Source:** Story 1.7 QA Gate (AC10)
**Description:** Conduct external user testing (2-3 users) to validate UX with real users
**Impact:** Self-testing showed excellent results (4-5/5), but external validation deferred
**Effort:** Low (1-2 days including participant recruitment)
**Target:** Epic 4 - Story 4.6 AC10 (Beta Feedback Integration & Bug Fixes)
**Epic 2 Decision:** DEFER - Epic 2 focuses on core engine, not validation UI. Better timing after CLI polish (Epic 3).
**Epic 4 Assignment:** Story 4.6 AC10: External user testing with 2-3 users
**Rationale:** CLI is now polished (Epic 3 complete); Story 4.6 is the natural home for user testing before launch
**References:**
- [docs/qa/gates/1.7-validation-ui-implementation.yml](qa/gates/1.7-validation-ui-implementation.yml)
- tests/test_corpus/validation_testing/USER_TESTING_GUIDE.md

**Acceptance Criteria:**
- [ ] Recruit 2-3 external users (academic researchers, HR professionals, or compliance officers)
- [ ] Provide test documents (20-50 entities each)
- [ ] Measure: validation time, satisfaction (1-5 scale), completion rate
- [ ] Target: ≥4/5 satisfaction, <5 min validation time for 50 entities
- [ ] Document feedback and iterate on UX if needed

---

#### TD-003: Resolve Type Ignore Comments in regex_matcher.py ✅ ASSIGNED TO EPIC 2
**Source:** Story 1.8 QA Gate
**Description:** Fix 2 instances of `# type: ignore` comments by updating DetectedEntity signature
**Impact:** Minor - doesn't affect functionality but improves type safety
**Effort:** Very Low (20 minutes)
**Target:** Epic 2 - Task 2.1.1 (during Story 2.1 setup)
**Epic 2 Assignment:** Task 2.1.1: Resolve Type Ignore Comments (quick task)
**Rationale:** Quick win (20 min); clean code before Epic 2 adds more regex/NLP integration
**References:**
- [gdpr_pseudonymizer/nlp/regex_matcher.py:157,222](../gdpr_pseudonymizer/nlp/regex_matcher.py)
- [docs/qa/gates/1.8-hybrid-detection-strategy.yml](qa/gates/1.8-hybrid-detection-strategy.yml)

**Acceptance Criteria:**
- [ ] Remove `# type: ignore` comments (lines 157, 222)
- [ ] Update DetectedEntity dataclass if needed
- [ ] mypy type checking passes with no errors
- [ ] All existing tests still pass

---

#### TD-004: Python Version Support Inconsistency ✅ ASSIGNED TO EPIC 4
**Source:** PM Review (2026-02-04)
**Description:** Misalignment between pyproject.toml, CI/CD matrix, and documentation regarding Python version support
**Impact:** Medium - Users may attempt installation on untested Python versions; CI doesn't verify claimed compatibility
**Effort:** Low (1-2 hours)
**Target:** Epic 4 - Story 4.3 AC9 (Complete Documentation Package)
**Owner:** DevOps / PM to verify spaCy compatibility before expansion
**Epic 4 Assignment:** Story 4.3 AC9: Python version alignment across all sources
**Rationale:** Story 4.2 confirmed Python 3.12 works on Ubuntu 24.04 and Fedora 39; Story 4.3 documentation package is the natural place to align all references

**Current State (Inconsistent):**
| Source | Python Versions | Notes |
|--------|-----------------|-------|
| pyproject.toml | `>=3.9,<3.14` | Claims 3.12, 3.13 support |
| CI/CD (ci.yaml) | `['3.9', '3.10', '3.11']` | Does NOT test 3.12, 3.13 |
| ALPHA-INSTALL.md | "3.9-3.12 (NOT 3.13+)" | Contradicts pyproject.toml |
| BACKLOG.md TD-001 | "Python 3.9-3.13" | Aspirational, not actual |
| coding-standards.md | "3.9-3.11, not 3.12+" | Outdated |

**Root Cause:** spaCy wheel availability and compatibility varies by Python version. No systematic verification before expanding version claims.

**Acceptance Criteria:**
- [ ] Verify spaCy 3.7+ wheel availability for Python 3.12 and 3.13
- [ ] If verified: Add 3.12 and 3.13 to CI/CD matrix (ci.yaml)
- [ ] If NOT verified: Tighten pyproject.toml to match actual tested versions
- [ ] Update ALPHA-INSTALL.md to match pyproject.toml
- [ ] Update coding-standards.md to match pyproject.toml
- [ ] Update TD-001 acceptance criteria to match actual CI matrix
- [ ] All documentation reflects actual tested/supported versions

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

#### FE-006: Expand Organization Pseudonym Library ✅ ASSIGNED TO EPIC 4
**Source:** Story 3.0 - Batch processing testing (2026-02-02)
**Description:** Expand neutral theme organization library from 35 to 150-200 entries to support larger document corpora without exhausting the library and falling back to generic naming (Org-001, etc.)
**Impact:** Batch processing of 15+ documents exhausts the 35-entry organization library quickly
**Effort:** Medium (2-4 hours - research + data entry)
**Target:** Epic 4 - Story 4.6 AC9 (Beta Feedback Integration & Bug Fixes)
**Epic 4 Assignment:** Story 4.6 AC9: Organization pseudonym library expansion
**Rationale:** Known quality gap impacting batch users; must resolve before launch
**References:**
- [data/pseudonyms/neutral.json](../data/pseudonyms/neutral.json)
- [docs/stories/3.0.location-org-pseudonym-libraries.story.md](stories/3.0.location-org-pseudonym-libraries.story.md#future-enhancements)

**Current State:**
- 35 organizations (20 companies + 10 agencies + 5 institutions)
- Fallback to Org-001, Org-002, etc. when exhausted (fixed 2026-02-02)

**Recommended Expansion:**
- 80-100 companies (diverse sectors: tech, manufacturing, finance, retail, healthcare)
- 40-50 agencies (government agencies, NGOs, research bodies)
- 30-50 institutions (universities, hospitals, professional associations)

**Note:** Location library (80 entries) may also need expansion for very large corpora.

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

**Current Status (2026-02-04):**
| Python | spaCy Status | CI Status | Action Needed |
|--------|--------------|-----------|---------------|
| 3.12 | ⚠️ Unverified | ❌ Not in matrix | Verify & add |
| 3.13 | ⚠️ Unverified | ❌ Not in matrix | Verify & add |
| 3.14 | ❌ Not released | N/A | Monitor |

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

### v1.1 (Post-MVP)

**Roadmap Items:**
- Fine-tuned spaCy model (target: 70-85% F1 accuracy)
- Optional `--no-validate` flag for high-confidence workflows
- Additional language support (English, Spanish, German)
- PDF/DOCX format support

**Planned Backlog Items:**
- FE-010: French documentation translation (README, install guide, CLI help, user guide)

**Potential Backlog Items:**
- FE-003: Performance regression tests (if not added in Epic 2-3)
- FE-004: Alternative context cycling key (if user feedback indicates need)

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
**Last Review:** 2026-02-07 (Epic 4 gap analysis — all backlog items assigned)
**Last Update:** 2026-02-07 (Assigned TD-002 → 4.6, TD-004 → 4.3, FE-006 → 4.6, MON-001/3/4 → 4.4, MON-002/5 → 4.5)
**Next Review:** After Story 4.7 completion (launch readiness)

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
