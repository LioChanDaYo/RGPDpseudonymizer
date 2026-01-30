# Epic 2: Core Pseudonymization Engine (Week 6-10)

**Epic Goal:** Implement production-quality compositional pseudonymization logic with encrypted mapping tables and audit trails, enabling consistent entity replacement across documents while validating architectural scalability for batch processing.

**Epic Duration:** 5 weeks (revised from original 4-5 weeks estimate)
**Timeline:** Week 6-10 (post Epic 1 completion)

---

## 📋 Epic 2 Story List (Updated)

| Story | Priority | Est. Duration | Backlog Source | Status |
|-------|----------|---------------|----------------|--------|
| **2.0.1: Integration Tests for Validation Workflow** | 🔴 **HIGH** | **2-3 days** | **TD-001 (Epic 1 debt)** | ✅ **DONE** |
| 2.1: Pseudonym Library System | HIGH | 3-4 days | Original Epic 2 | ✅ **DONE** |
| ~~**Task 2.1.1: Resolve Type Ignore Comments**~~ | ~~MEDIUM~~ | ~~**20 min**~~ | **✅ RESOLVED (TD-003)** | ✅ **DONE** |
| 2.2: Compositional Pseudonymization Logic | CRITICAL | 4-5 days | Original Epic 2 | ✅ **DONE** |
| 2.3: Compound Name Handling | HIGH | 2-3 days | Original Epic 2 | ✅ **DONE** |
| 2.4: Encrypted Mapping Table | CRITICAL | 4-5 days | Original Epic 2 | ✅ **DONE** |
| 2.5: Audit Logging | HIGH | 2-3 days | Original Epic 2 | ✅ **DONE** |
| 2.6: Single-Document Pseudonymization Workflow | CRITICAL | 3-4 days | Original Epic 2 | ✅ **DONE** (QA: PASS) |
| **2.6.1: Performance Benchmark Test** | 🟡 **LOW** | **1-2 days** | **TEST-001 (Story 2.6 QA deferred)** | 📋 **BACKLOG** |
| **2.6.2: Accuracy Validation Test Corpus** | 🟡 **LOW** | **2-3 days** | **TEST-002 (Story 2.6 QA deferred)** | 📋 **BACKLOG** |
| 2.7: Architectural Spike - Batch Processing | MEDIUM | 2-3 days | Original Epic 2 | ✅ **DONE** (QA: PASS with critical bug found) |
| **2.8: Pseudonym Component Collision Fix** | 🔴 **CRITICAL** | **2-3 days** | **BUG-001 (Story 2.7 discovery)** | 📋 **BACKLOG** - **BLOCKING for Epic 3** |
| 2.9: Alpha Release Preparation | MEDIUM | 2-3 days | Original Epic 2 | 📋 **BACKLOG** |

**Total Epic 2 Duration:** 26-36 days (5.2-7.2 weeks) vs 5 weeks allocated → Story 2.8 added post-Epic 2 completion

**⚠️ CRITICAL:** Story 2.8 (Pseudonym Component Collision Fix) is BLOCKING for Epic 3 implementation. Discovered during Story 2.7 spike - two different real entities can receive same pseudonym, violating GDPR 1:1 mapping requirement.

---

## 🆕 Story 2.0.1: Integration Tests for Validation Workflow (TD-001)

**Source:** Epic 1 Technical Debt (Story 1.7 QA Gate TEST-001)

**As a** developer,
**I want** end-to-end integration tests for the complete validation workflow,
**so that** I can confidently integrate validation into Epic 2's production workflow and catch regressions early.

**Priority:** 🔴 **HIGH** - Required before Story 2.6 (Single-Document Workflow)

**Rationale:**
- Story 1.7 QA gate identified lack of integration tests as MEDIUM priority issue
- Story 2.6 AC7 requires "Integration tests: End-to-end workflow"
- Validation workflow is critical path - must be tested before production integration
- Pays down Epic 1 technical debt before building on validation foundation

### Acceptance Criteria

1. **AC1:** Full validation workflow integration tests created in `tests/integration/test_validation_workflow_integration.py`:
   - Test complete flow: detect entities → display summary → review by type → final confirmation → validated entities
   - Simulate user actions (confirm, reject, modify, add entity, change pseudonym)
   - Test batch operations (Accept All Type, Reject All Type)

2. **AC2:** State transition verification tests:
   - Entity states: PENDING → CONFIRMED (via Space key)
   - Entity states: PENDING → REJECTED (via R key)
   - Entity states: PENDING → MODIFIED (via E key with text change)
   - Verify ValidationSession state correctly tracks all decisions

3. **AC3:** Edge case coverage tests:
   - Empty entity detection (no entities found in document)
   - Large document handling (100+ entities with deduplication)
   - Ctrl+C interruption handling (graceful exit without data loss)
   - Invalid input handling (unknown keys, malformed entity text)

4. **AC4:** Context cycling integration tests (Story 1.9):
   - Test X key cycles through grouped entity contexts
   - Verify context index wraps around correctly (modulo operator)
   - Test single-occurrence entities don't show cycling option

5. **AC5:** Tests run in CI/CD pipeline:
   - Integrate into `.github/workflows/ci.yaml`
   - Run on Python 3.9-3.13 matrix
   - Tests isolated from unit tests (separate test file)
   - Execution time <2 minutes for integration test suite

6. **AC6:** Mock user input simulation:
   - Use `unittest.mock` to simulate keyboard input
   - Mock `readchar` library for single-key capture
   - Verify correct actions triggered for each key press

7. **AC7:** Test data fixtures:
   - Create reusable test documents with known entity counts
   - Include edge cases: duplicate entities, compound names, ambiguous components
   - Fixtures stored in `tests/fixtures/validation_workflow/`

8. **AC8:** Code coverage validation:
   - Integration tests cover validation workflow code paths not covered by unit tests
   - Target: 90% coverage for validation workflow orchestration logic
   - Use `pytest-cov` to measure and report coverage

### Technical Notes

**Dependencies:**
- Story 1.7 (Validation UI) - COMPLETE ✅
- Story 1.9 (Entity Deduplication) - COMPLETE ✅

**Test Strategy:**
```python
# Example integration test structure
def test_full_validation_workflow_with_confirm_reject():
    """Test complete workflow with mixed confirm/reject actions."""
    # Setup
    document_text = "Marie Dubois travaille à Paris pour Acme SA."
    entities = [
        DetectedEntity("Marie Dubois", "PERSON", 0, 12),
        DetectedEntity("Paris", "LOCATION", 28, 33),
        DetectedEntity("Acme SA", "ORG", 39, 46),
    ]

    # Create validation session
    session = ValidationSession(document_path="test.txt", document_text=document_text)
    session.entities = entities

    # Simulate user actions
    with patch('readchar.readkey') as mock_readkey:
        mock_readkey.side_effect = [
            ' ',  # Confirm "Marie Dubois"
            'r',  # Reject "Paris" (false positive)
            ' ',  # Confirm "Acme SA"
            'y',  # Final confirmation
        ]

        # Run workflow
        workflow = ValidationWorkflow(session)
        result = workflow.run()

    # Verify
    assert len(result.validated_entities) == 2  # Marie Dubois + Acme SA
    assert result.validated_entities[0].text == "Marie Dubois"
    assert result.validated_entities[1].text == "Acme SA"
```

**Files to Create:**
- `tests/integration/test_validation_workflow_integration.py` - Main integration test file
- `tests/fixtures/validation_workflow/sample_documents.py` - Test document fixtures
- Update `.github/workflows/ci.yaml` - Add integration test step

**Estimated Effort:** 2-3 days
**Target Completion:** Before Story 2.6 begins

---

### Story 2.1: Pseudonym Library System

**As a** user,
**I want** themed pseudonym libraries with sufficient name combinations,
**so that** pseudonymized documents maintain readability and avoid repetitive fallback naming.

#### Acceptance Criteria

1. **AC1:** JSON-based pseudonym library structure implemented per Technical Assumptions: separate `first_names` (by gender) and `last_names` arrays.
2. **AC2:** Three themed libraries created with ≥500 first names and ≥500 last names each:
   - Neutral/Generic (French common names from INSEE public data)
   - Star Wars (curated from fan wikis)
   - LOTR (curated from Tolkien Gateway)
3. **AC3:** Gender metadata included where applicable (male/female/neutral tags).
4. **AC4:** Library manager implemented: load themes, select pseudonyms with gender-matching logic (when NER provides gender data).
5. **AC5:** Pseudonym exhaustion detection: warn when library usage exceeds 80%, provide systematic fallback naming ("Person-001", "Location-001") when exhausted.
6. **AC6:** Unit tests: library loading, pseudonym selection (with/without gender), exhaustion handling.
7. **AC7:** Library sourcing documented for legal compliance (public domain, fair use considerations).

#### ~~Task 2.1.1: Resolve Type Ignore Comments in regex_matcher.py (TD-003)~~ ✅ RESOLVED

**Source:** Epic 1 Technical Debt (Story 1.8 QA Gate)

**Status:** ✅ **RESOLVED** - Completed January 22, 2026 (commit 4e7533d)

**Resolution Summary:**
- Added `source: str = "spacy"` parameter to DetectedEntity dataclass
- Added `is_ambiguous: bool = False` parameter to DetectedEntity dataclass
- Removed both `# type: ignore[call-arg]` comments from lines 157 and 222
- Added proper type hints (`dict[str, Any]`) to RegexMatcher class
- All mypy checks passing: `Success: no issues found in 7 source files`

**Resolved By:** Commit 4e7533d "fix: resolve mypy type errors in regex_matcher" (January 22, 2026)

**Verification:** Confirmed via mypy validation on January 24, 2026 during Story 2.1 PO validation

**Impact on Story 2.1:** Task 2.1.1 removed from Story 2.1 scope (no work required)

---

### Story 2.2: Compositional Pseudonymization Logic (FR4-5)

**As a** user,
**I want** consistent pseudonym application using compositional strict matching,
**so that** "Marie Dubois" → "Leia Organa" everywhere, with "Marie" → "Leia" and "Dubois" → "Organa" when they appear alone.

#### Acceptance Criteria

1. **AC1:** Full name entity detection: identify complete person names (first + last) from NER results.
2. **AC2:** Composite pseudonym assignment: Map full name to full pseudonym (e.g., "Marie Dubois" → "Leia Organa").
3. **AC3:** Component mapping: Extract and store first name → pseudonym first name, last name → pseudonym last name mappings.
4. **AC4:** Standalone component replacement: When "Marie" appears alone, replace with "Leia" (using first name mapping).
5. **AC5:** Shared component handling (FR5): "Marie Dubois" → "Leia Organa", "Marie Dupont" → "Leia Skywalker" (preserves "Marie" → "Leia" consistency).
6. **AC6:** Ambiguous component flagging: Log standalone components without full name context as potentially ambiguous for validation mode review.
7. **AC7:** Unit tests: full name composition, component extraction, standalone replacement, shared component scenarios.
8. **AC8:** Integration test: Process documents with complex name patterns, verify compositional logic correctness.

---

### Story 2.3: Compound Name Handling (FR20)

**As a** user,
**I want** French compound first names like "Jean-Pierre" and "Marie-Claire" handled correctly,
**so that** pseudonymization maintains name structure integrity.

#### Acceptance Criteria

1. **AC1:** Compound first name detection: Identify hyphenated first names in NER results.
2. **AC2:** Simple pseudonym assignment for compounds: Map compound names to SIMPLE pseudonyms as atomic units (e.g., "Jean-Pierre" → "Han", not "Luke-Han"). This simplifies implementation and avoids gender consistency checks across compound components.
3. **AC3:** Atomic compound handling: Treat compound names (e.g., "Jean-Pierre") as distinct from their component parts (e.g., "Jean"). Standalone "Jean" and compound "Jean-Pierre" are separate entities receiving different pseudonyms.
4. **AC4:** Regex pattern support: Fallback regex for detecting common French compound patterns if NER doesn't identify them.
5. **AC5:** Unit tests: compound name detection, pseudonym assignment, edge cases (triple compounds, non-standard separators).
6. **AC6:** Test corpus validation: Verify compound names in test corpus processed correctly (from Story 1.1 edge cases).

#### 📝 Scope Enhancement Note (Added 2026-01-25)

**Context:** During Story 2.2 testing, a defect was discovered where French honorific titles (Dr., M., Mme., etc.) are incorrectly treated as part of names, causing duplicate entity mappings:
- "Dr. Marie Dubois" → parsed as `first_name="Dr. Marie"`, creating a separate mapping from "Marie Dubois"
- This breaks Story 2.2's compositional logic consistency

**Decision:** Enhanced Story 2.3 scope to include **title preprocessing** in addition to compound name handling:
- **Rationale:** Both are name parsing edge cases touching the same code area (`parse_full_name()`)
- **Impact:** Minimal effort increase (1-2 hours for title regex patterns)
- **Benefit:** Fixes duplicate mapping issue without reopening completed Story 2.2 (QA-approved)
- **Priority:** HIGH - Must be fixed before Story 2.6 (Single-Document Workflow) to meet accuracy targets

**Updated Story Title:** "French Name Preprocessing (Titles + Compound Names)"

**Enhanced Acceptance Criteria Added:**
- AC1: Title stripping (Dr., M., Mme., Mlle., Pr., Prof.)
- AC5: Title edge cases (with/without periods, multiple titles, title+compound combos)
- AC6: Integration with Story 2.2 compositional logic (replaces original AC6)
- AC7: Unit tests for titles and compounds
- AC8: Integration tests verifying no duplicate mappings

**Design Decision Update (2026-01-26 - PO Approved):**
- **Original AC2:** Compound-to-compound mapping ("Jean-Pierre" → "Luke-Han")
- **Updated AC2:** Compound-to-simple mapping ("Jean-Pierre" → "Han")
- **Rationale:** Simplifies implementation, eliminates gender consistency complexity across compound components, uses existing LibraryBasedPseudonymManager without modification, produces cleaner/more readable pseudonyms
- **Impact:** User-facing change - compound names receive simple pseudonyms instead of compound pseudonyms
- **PO Approval:** Sarah (Product Owner) - 2026-01-26

**Estimated Effort:** Remains 2-3 days (unchanged)

**Story File:** [docs/stories/2.3.french-name-preprocessing.story.md](../stories/2.3.french-name-preprocessing.story.md)

---

### Story 2.4: Encrypted Mapping Table with Python-Native Encryption

**As a** user,
**I want** a secure encrypted mapping table storing original↔pseudonym correspondences,
**so that** I can exercise GDPR rights (reversibility) while protecting sensitive data.

#### Acceptance Criteria

1. **AC1:** SQLite database schema implemented per Technical Assumptions:
   - `entities` table: id, entity_type, first_name, last_name, full_name, pseudonym_first, pseudonym_last, pseudonym_full, first_seen_timestamp, gender, confidence_score
   - `operations` table: id, timestamp, operation_type, files_processed, model_name, model_version, theme_selected, user_modifications, entity_count
   - `metadata` table: key, value (stores encryption params, schema version)
2. **AC2:** Python-native encryption implemented using `cryptography` library (Fernet symmetric encryption).
3. **AC3:** Passphrase-based key derivation: PBKDF2 with salt stored in `metadata` table.
4. **AC4:** Column-level encryption: Sensitive columns (names, pseudonyms) encrypted individually.
5. **AC5:** Passphrase validation on database open: verify passphrase before allowing access.
6. **AC6:** Passphrase strength validation: minimum 12 characters (NFR12), provide entropy feedback ("weak/medium/strong").
7. **AC7:** Database operations: create, open (with passphrase), query mappings, insert new entities, close.
8. **AC8:** Unit tests: encryption/decryption, passphrase validation, CRUD operations, error handling (wrong passphrase, corrupted database).
9. **AC9:** Security review: No plaintext sensitive data in logs, no temp file leakage.

---

### Story 2.5: Audit Logging (FR12)

**As a** compliance officer,
**I want** comprehensive audit logs of all pseudonymization operations,
**so that** I can demonstrate GDPR Article 30 compliance and troubleshoot issues.

#### Acceptance Criteria

1. **AC1:** Audit log implemented in `operations` table (from Story 2.4 schema).
2. **AC2:** Log entry created for each pseudonymization operation with required fields (FR12): timestamp, operation type, files processed, model version, theme selected, entity count.
3. **AC3:** User modifications logged when validation mode used (deferred to Epic 3, placeholder in schema).
4. **AC4:** Export functionality: Query audit log and export to JSON or CSV format.
5. **AC5:** Log rotation not required for MVP (SQLite database handles growth).
6. **AC6:** Unit tests: log entry creation, query operations, export functionality.
7. **AC7:** Documentation: audit log schema, query examples, GDPR Article 30 mapping.

---

### Story 2.6: Single-Document Pseudonymization Workflow

**As a** user,
**I want** to pseudonymize a single document with all compositional logic applied,
**so that** I can validate the core value proposition on real documents.

#### Acceptance Criteria

1. **AC1:** Integrate all Epic 2 components: NER detection (Epic 1) → compositional logic (2.2) → compound handling (2.3) → mapping table (2.4) → audit log (2.5).
2. **AC2:** `process` command updated from Epic 1 skeleton to production implementation.
3. **AC3:** Workflow: Load document → detect entities → assign pseudonyms (compositional) → store mappings → apply replacements → write output → log operation.
4. **AC4:** Idempotent behavior (FR19): Re-processing same document reuses existing mappings.
5. **AC5:** Performance validation (NFR1): Process 2-5K word document in <30 seconds on standard hardware.
6. **AC6:** Accuracy validation: False negative rate <10% (NFR8), false positive rate <15% (NFR9) on test corpus.
7. **AC7:** Integration tests: End-to-end workflow, idempotency, error scenarios (file not found, encryption errors).
8. **AC8:** Can demo to alpha testers: Fully functional single-document pseudonymization.

#### Task 2.6.1: Performance Regression Tests with pytest-benchmark (FE-003 - OPTIONAL)

**Source:** Epic 1 Future Enhancement (Story 1.8 QA Gate recommendation)

**Description:** Add automated performance regression tests using pytest-benchmark to validate NFR1 in CI/CD.

**Priority:** LOW (Optional - if time permits during Story 2.6)

**Rationale:** Story 2.6 AC5 requires manual performance validation (<30s per document). Automated benchmarks provide continuous regression detection and are more reliable than manual testing.

**Acceptance Criteria:**
- [ ] Install `pytest-benchmark` in development dependencies
- [ ] Add benchmark tests for hybrid detection pipeline (target: <30s per 2-5K word document)
- [ ] Add benchmark tests for validation workflow (target: <5 min for 100 entities)
- [ ] Integrate into CI/CD pipeline (`.github/workflows/ci.yaml`) with threshold alerts
- [ ] Configure benchmark to run on representative test documents
- [ ] Document performance baselines in benchmark report

**Estimated Effort:** 1 hour
**Target:** Optional - execute during Story 2.6 performance validation if time permits, otherwise defer to Epic 3

**Benefits if Implemented:**
- Automated NFR1 validation in CI/CD
- Catch performance regressions early
- Historical performance trend tracking
- Reduced manual testing burden

---

### Story 2.7: Architectural Spike - Batch Processing Scalability

**As a** developer,
**I want** to validate that our architecture can handle batch processing efficiently,
**so that** Epic 3 batch implementation doesn't require major refactoring.

#### Acceptance Criteria

1. **AC1:** Prototype batch processing with process-based parallelism (multiprocessing module).
2. **AC2:** Test with 10-document batch: process in parallel using worker pool (min(cpu_count, 4) workers).
3. **AC3:** Validate mapping table consistency: Cross-document entity mapping works correctly (same entity gets same pseudonym across batch).
4. **AC4:** Performance measurement: Estimate batch processing time vs sequential processing (should show speedup).
5. **AC5:** Identify architectural issues: memory leaks, mapping table contention, worker process overhead.
6. **AC6:** Document findings: Recommendations for Epic 3 implementation, known limitations, optimization opportunities.
7. **AC7:** If major issues found, adjust architecture before proceeding to Epic 3.

#### Task 2.7.1: Performance Regression Tests (FE-003 - OPTIONAL ALTERNATIVE)

**Note:** If Task 2.6.1 (performance regression tests) not completed during Story 2.6, this task provides an alternative timing during Story 2.7.

**Description:** Add automated performance regression tests using pytest-benchmark as part of batch processing performance measurement.

**Priority:** LOW (Optional)

**Rationale:** Story 2.7 AC4 measures batch processing performance. Adding pytest-benchmark here provides automated regression detection for both single-document (Story 2.6) and batch processing performance.

**Acceptance Criteria:** Same as Task 2.6.1 (see above)

**Estimated Effort:** 1 hour
**Target:** Optional - execute during Story 2.7 performance measurement phase

---

### Story 2.8: Alpha Release Preparation

**As a** product manager,
**I want** to release an alpha version to 3-5 friendly users after Epic 2,
**so that** I can validate core value proposition and gather early feedback before investing in CLI polish and batch features.

#### Acceptance Criteria

1. **AC1:** Basic installation package created: PyPI-style package installable via `pip install -e .`.
2. **AC2:** Minimal documentation: README with installation instructions, basic usage example, known limitations.
3. **AC3:** Alpha testers identified and onboarded (3-5 users: 2 researchers, 2-3 LLM users).
4. **AC4:** Alpha testing protocol created: specific tasks for testers, feedback survey questions.
5. **AC5:** Feedback collection mechanism: Google Form or GitHub issues for structured feedback.
6. **AC6:** Alpha release tagged in Git: `v0.1.0-alpha`.
7. **AC7:** Alpha feedback review session scheduled (end of week 6-7) to inform Epic 3 priorities.

---

## 📊 Epic 2 Backlog Integration Summary

### **Backlog Items Added to Epic 2**

**From Epic 1 Technical Debt:**
1. ✅ **TD-001:** Integration Tests for Validation Workflow → **Story 2.0.1**
   - Priority: HIGH
   - Effort: 2-3 days
   - Rationale: Required for Story 2.6 integration testing; pays down Epic 1 technical debt

2. ✅ **TD-003:** Resolve Type Ignore Comments → **✅ RESOLVED (Commit 4e7533d, Jan 22 2026)**
   - Priority: MEDIUM (Quick Win)
   - Effort: 20 minutes → **Actual: Completed during Story 1.8**
   - Rationale: Clean code before Epic 2 adds more regex/NLP integration
   - Resolution: Added `source` and `is_ambiguous` fields to DetectedEntity, removed type: ignore comments
   - Verification: mypy clean (0 errors) as of January 24, 2026

**From Epic 1 Future Enhancements:**
3. 🤔 **FE-003:** Performance Regression Tests → **Task 2.6.1 or 2.7.1 (Optional)**
   - Priority: LOW (Optional if time permits)
   - Effort: 1 hour
   - Rationale: Automated NFR1 validation better than manual testing

### **Backlog Items Deferred from Epic 2**

**Technical Debt:**
- ⏸️ **TD-002:** External User Testing → Epic 4 (pre-MVP launch)
  - Reason: Epic 2 focuses on core engine, not validation UI; better timing after CLI polish (Epic 3)

**Future Enhancements:**
- ⏸️ **FE-001:** Visual Indicator for Context Cycling → Epic 3 (UI polish)
  - Reason: Epic 2 has no UI polish scope; Epic 3 Story 3.4 is natural home
- ⏸️ **FE-002:** Batch Operations Visual Feedback → Epic 3 (UI polish)
  - Reason: Epic 2 has no UI polish scope; Epic 3 Story 3.4 is natural home

### **Monitoring Items During Epic 2**

- 📊 **MON-002:** Hybrid detection processing time (track during Story 2.6 performance validation)
- 📊 **MON-005:** spaCy Python 3.14 compatibility (passive monitoring - update if available)

---

## ⏱️ Epic 2 Revised Timeline Estimate

### **Original Epic 2 Estimate (8 stories):**
- Story 2.1: Pseudonym Library (3-4 days)
- Story 2.2: Compositional Logic (4-5 days)
- Story 2.3: Compound Names (2-3 days)
- Story 2.4: Encrypted Mapping (4-5 days)
- Story 2.5: Audit Logging (2-3 days)
- Story 2.6: Single-Document Workflow (3-4 days)
- Story 2.7: Batch Processing Spike (2-3 days)
- Story 2.8: Alpha Release Prep (2-3 days)

**Original Total:** 22-30 days (4.4-6 weeks)

### **Epic 2 with Backlog Additions (10 stories + 3 optional tasks):**
- **Story 2.0.1:** Integration Tests (2-3 days) ← NEW from TD-001
- Story 2.1: Pseudonym Library (3-4 days)
- ~~**Task 2.1.1:** Type Ignore Comments (20 min)~~ ← ✅ RESOLVED (TD-003)
- Story 2.2: Compositional Logic (4-5 days)
- Story 2.3: Compound Names (2-3 days)
- Story 2.4: Encrypted Mapping (4-5 days)
- Story 2.5: Audit Logging (2-3 days)
- Story 2.6: Single-Document Workflow (3-4 days)
- **Task 2.6.1:** Performance Tests (1 hour - optional) ← NEW from FE-003
- Story 2.7: Batch Processing Spike (2-3 days)
- **Task 2.7.1:** Performance Tests (1 hour - optional alternative) ← NEW from FE-003
- Story 2.8: Alpha Release Prep (2-3 days)

**Revised Total (with required backlog items):** 22-30 days (4.4-6 weeks) - TD-003 already resolved
**Revised Total (with all optional items):** 22.2-30.2 days (4.4-6 weeks)

### **Timeline Feasibility Check:**
- **Epic 2 Allocated Time:** 5 weeks (Week 6-10)
- **Revised Estimate:** 4.4-6 weeks (TD-003 resolved saves 20 min)
- **Buffer:** 0.6 weeks minimum, -1 week maximum (upper bound exceeds by 1 week)
- **Verdict:** Improved feasibility; within tolerance with moderate prioritization

### **Risk Mitigation:**
1. **Story 2.0.1 is non-negotiable** - must complete before Story 2.6 (integration testing dependency)
2. ~~**Task 2.1.1 is quick win**~~ - ✅ Already resolved (no timeline impact)
3. **Task 2.6.1/2.7.1 are optional** - defer if timeline pressure builds
4. **Monitor Story 2.1-2.5 velocity** - if stories run long, defer optional tasks and compress Story 2.7-2.8

---

## 📋 Epic 2 Execution Sequence

**Recommended Story Order:**

1. **Story 2.0.1:** Integration Tests for Validation Workflow (2-3 days)
   - Pays down Epic 1 technical debt
   - Unblocks confident Story 2.6 integration testing
   - Can run in parallel with early Story 2.1 work if team has capacity

2. **Story 2.1:** Pseudonym Library System (3-4 days)
   - ~~**Task 2.1.1:** Resolve Type Ignore Comments~~ ✅ Already resolved (TD-003)

3. **Story 2.2:** Compositional Pseudonymization Logic (4-5 days)

4. **Story 2.3:** Compound Name Handling (2-3 days)

5. **Story 2.4:** Encrypted Mapping Table (4-5 days)

6. **Story 2.5:** Audit Logging (2-3 days)

7. **Story 2.6:** Single-Document Pseudonymization Workflow (3-4 days)
   - **Dependencies:** Story 2.0.1 (integration tests must be complete)
   - **Task 2.6.1:** Performance Regression Tests (optional - 1 hour during performance validation)

8. **Story 2.7:** Architectural Spike - Batch Processing (2-3 days)
   - **Task 2.7.1:** Performance Regression Tests (optional alternative - 1 hour if not done in 2.6.1)

9. **Story 2.8:** Alpha Release Preparation (2-3 days)

---

## ✅ Epic 2 Definition of Done (Updated)

- ✅ **Story 2.0.1 Complete:** Integration tests for validation workflow passing in CI/CD (TD-001 resolved)
- ✅ **TD-003 Pre-Resolved:** Type ignore comments resolved, mypy clean (completed Jan 22, 2026)
- ✅ Pseudonym libraries created with ≥500 names each (3 themes)
- ✅ Compositional pseudonymization logic functional (FR4-5)
- ✅ Compound name handling operational (FR20)
- ✅ Encrypted mapping table with passphrase protection
- ✅ Audit logging implemented (GDPR Article 30 compliance)
- ✅ Single-document pseudonymization workflow operational (<30s processing time)
- ✅ Batch processing architecture validated (spike complete)
- ✅ Alpha release tagged and deployed to 3-5 testers
- 🤔 Optional: Performance regression tests automated (FE-003)

**Handoff to Epic 3:**
- ✅ Validation workflow integration tests provide confident foundation
- ✅ Clean codebase (no type safety debt)
- ✅ Core pseudonymization engine production-ready
- ✅ Alpha feedback collected to inform Epic 3 CLI polish priorities

---

## 🆕 Story 2.6.1: Performance Benchmark Test (TEST-001)

**Source:** Story 2.6 QA Gate Review - Deferred Item (Low priority)

**As a** developer,
**I want** automated performance benchmarks for document processing,
**so that** I can validate NFR1 compliance and prevent performance regressions.

**Priority:** 🟡 **LOW** - Post-MVP enhancement
**QA Gate Reference:** TEST-001 (Story 2.6 QA review)
**Story File:** [docs/stories/2.6.1.performance-benchmark-test.story.md](../stories/2.6.1.performance-benchmark-test.story.md)

**Rationale:**
- Story 2.6 QA review identified missing automated performance tests (AC5)
- Manual validation shows <30s for 3000-word docs; needs automated regression testing
- pytest-benchmark tests will prevent performance degradation in future changes
- Low priority: Manual validation sufficient for MVP/alpha release

### Acceptance Criteria

1. **AC1:** Automated pytest-benchmark test validates NFR1: <30s for 2-5K word documents
2. **AC2:** Test realistic documents with varied entity densities (low/medium/high)
3. **AC3:** Performance baseline documented (mean, std dev, min/max)
4. **AC4:** CI/CD integration with regression detection (>20% slowdown fails build)
5. **AC5:** Performance metrics logged (NLP, DB ops, file I/O breakdown)

**Estimated Duration:** 1-2 days

---

## 🆕 Story 2.6.2: Accuracy Validation Test Corpus (TEST-002)

**Source:** Story 2.6 QA Gate Review - Deferred Item (Low priority)

**As a** quality engineer,
**I want** automated accuracy validation against a ground-truth test corpus,
**so that** I can verify NER accuracy meets NFR8/NFR9 thresholds.

**Priority:** 🟡 **LOW** - Post-MVP enhancement
**QA Gate Reference:** TEST-002 (Story 2.6 QA review)
**Story File:** [docs/stories/2.6.2.accuracy-validation-test-corpus.story.md](../stories/2.6.2.accuracy-validation-test-corpus.story.md)

**Rationale:**
- Story 2.6 QA review identified missing accuracy validation (AC6)
- NFR8 (<10% false negatives) and NFR9 (<15% false positives) not validated against test corpus
- NLP accuracy known from Story 1.2, but systematic validation missing
- Low priority: Validation mode (Epic 3) will provide user correction mechanism

### Acceptance Criteria

1. **AC1:** Test corpus with ground-truth annotations (25+ documents)
2. **AC2:** Automated test calculates false negative rate: <10% (NFR8)
3. **AC3:** Automated test calculates false positive rate: <15% (NFR9)
4. **AC4:** Per-entity-type accuracy metrics (PERSON, LOCATION, ORG)
5. **AC5:** Accuracy report generated with failure case analysis
6. **AC6:** CI/CD integration for NLP model change regression detection

**Estimated Duration:** 2-3 days
**Dependency:** May require test corpus creation (Story 1.1 artifact check)

---

## 🆕 Story 2.8: Pseudonym Component Collision Fix (BUG-001) - **CRITICAL**

**Source:** Story 2.7 Architectural Spike - Critical Bug Discovery

**As a** GDPR compliance officer,
**I want** pseudonym component assignments to be collision-free at the component level,
**so that** two different real entities never receive the same pseudonym, ensuring 1:1 reversible mapping (GDPR Article 4(5)).

**Priority:** 🔴 **CRITICAL** - BLOCKING for Epic 3

**Bug Discovery:** During Story 2.7 batch processing verification, two different real last names ("Dubois" and "Lefebvre") were assigned the same pseudonym ("Neto"). This violates the fundamental 1:1 mapping requirement for GDPR-compliant pseudonymization.

**Root Cause:** `LibraryBasedPseudonymManager._used_pseudonyms` only tracks FULL pseudonyms (e.g., "Alexia Neto"), not individual components (e.g., "Neto"). Random selection can assign the same component to different real entities.

**Impact:**
- **GDPR Compliance:** Violates Article 4(5) (1:1 reversible mapping)
- **Data Integrity:** Different individuals conflated in processed documents
- **Probability:** Low (~0.1% with 500-name library) but non-zero in production

**References:**
- Bug Report: `docs/architecture/CRITICAL-BUG-PSEUDONYM-COLLISION.md`
- Story File: `docs/stories/2.8.pseudonym-component-collision-fix.story.md`
- Spike Findings: `docs/architecture/batch-processing-spike-findings.md` (Issue 5)

### Key Acceptance Criteria

1. **AC1:** Implement component-level collision prevention in `LibraryBasedPseudonymManager`
2. **AC2-3:** Update `_select_first_name()` and `_select_last_name()` with collision tracking
3. **AC6:** Unit tests verify no component collisions after 100+ assignments
4. **AC7:** Integration test with Story 2.7 test corpus - all 5 consistency tests PASS
5. **AC9:** Backwards compatibility - reconstruct mappings from existing database
6. **AC10:** Performance validation - <5ms overhead per assignment

### Implementation Strategy

Add `_component_mappings` dict to track real component → pseudonym component mappings:
```python
self._component_mappings: dict[tuple[str, str], str] = {}
# Key: (real_component, component_type)
# Value: pseudonym_component
```

Before assigning pseudonym component:
1. Check if real component already has mapping (idempotency)
2. Select random pseudonym component
3. Verify no other real component uses this pseudonym (collision prevention)
4. Store mapping for future consistency

**Estimated Duration:** 2-3 days
**Dependency:** Story 2.7 (Architectural Spike) - COMPLETE ✅
**Blocking:** Epic 3 (Batch Processing CLI) - cannot proceed until fixed

---

**Document Status:** APPROVED v2.1 (Post-Story 2.7 - Critical Bug Added)
**Updated:** 2026-01-29 (Story 2.8 added as CRITICAL/BLOCKING, Story 2.7 marked DONE)
**Date:** 2026-01-23
**Last Updated:** 2026-01-24 (PM Approval)

**Approvals Required:**
- [x] PM approval of Story 2.0.1 addition (HIGH priority - required before Story 2.6) - **APPROVED 2026-01-24 by John (PM)**
- [x] PM confirmation that 4.8-6.6 week estimate acceptable for 5-week Epic 2 allocation - **APPROVED 2026-01-24 by John (PM)**
- [x] Dev lead feasibility review of Story 2.0.1 (2-3 days estimate) - **APPROVED 2026-01-24 by James (Dev Lead)**

**Key Decisions:**
- ✅ TD-001 (Integration Tests) elevated to Story 2.0.1 - non-negotiable for Epic 2
- ✅ TD-003 (Type Ignore) added as Task 2.1.1 - quick win during Story 2.1 setup
- 🤔 FE-003 (Performance Tests) optional - defer if timeline pressure
- ⏸️ TD-002, FE-001, FE-002 deferred to Epic 3/4 - not in Epic 2 scope
- 📋 **NEW:** TEST-001 (Performance Benchmark) → Story 2.6.1 (LOW priority, post-MVP)
- 📋 **NEW:** TEST-002 (Accuracy Validation) → Story 2.6.2 (LOW priority, post-MVP)

**PM Approval Rationale:**
- Story 2.0.1 is a non-negotiable dependency for Story 2.6 AC7 integration testing
- 2-3 day investment prevents costly rework and technical debt accumulation
- Timeline feasible with risk mitigation: optional tasks (2.6.1/2.7.1) provide schedule flexibility
- Upper bound (6.6 weeks) manageable through aggressive prioritization and velocity monitoring

**Next Actions:**
1. ✅ PM approval complete - Epic 2 scope approved (Story 2.0.1 + Task 2.1.1)
2. ✅ Dev lead feasibility review complete - Story 2.0.1 APPROVED (2-3 days realistic, target 2.5 days)
3. 🚀 Begin Story 2.0.1 (Integration Tests) when Epic 2 kicks off (Week 6)
4. 📊 Monitor Story 2.1-2.5 velocity to assess optional task feasibility

**Dev Lead Feasibility Notes (James - 2026-01-24):**
- Effort estimate: 2-3 days confirmed realistic (recommend 2.5 days planning)
- Risk level: LOW - clear scope, proven frameworks, no blocking dependencies
- Execution strategy: Prioritize AC1-AC2-AC4 (core workflow), AC3+AC8 flexible
- Coverage target: 85% success threshold, 90% stretch goal (AC8 is aggressive)
- Parallel execution possible: Can overlap with Story 2.1 setup if team capacity allows

---
