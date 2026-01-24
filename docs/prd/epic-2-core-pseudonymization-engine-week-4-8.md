# Epic 2: Core Pseudonymization Engine (Week 6-10)

**Epic Goal:** Implement production-quality compositional pseudonymization logic with encrypted mapping tables and audit trails, enabling consistent entity replacement across documents while validating architectural scalability for batch processing.

**Epic Duration:** 5 weeks (revised from original 4-5 weeks estimate)
**Timeline:** Week 6-10 (post Epic 1 completion)

---

## 📋 Epic 2 Story List (Updated)

| Story | Priority | Est. Duration | Backlog Source |
|-------|----------|---------------|----------------|
| **2.0.1: Integration Tests for Validation Workflow** | 🔴 **HIGH** | **2-3 days** | **TD-001 (Epic 1 debt)** |
| 2.1: Pseudonym Library System | HIGH | 3-4 days | Original Epic 2 |
| **Task 2.1.1: Resolve Type Ignore Comments** | MEDIUM | **20 min** | **TD-003 (Epic 1 debt)** |
| 2.2: Compositional Pseudonymization Logic | CRITICAL | 4-5 days | Original Epic 2 |
| 2.3: Compound Name Handling | HIGH | 2-3 days | Original Epic 2 |
| 2.4: Encrypted Mapping Table | CRITICAL | 4-5 days | Original Epic 2 |
| 2.5: Audit Logging | HIGH | 2-3 days | Original Epic 2 |
| 2.6: Single-Document Pseudonymization Workflow | CRITICAL | 3-4 days | Original Epic 2 |
| **Task 2.6.1 or 2.7.1: Performance Regression Tests** | LOW (Optional) | **1 hour** | **FE-003 (Optional)** |
| 2.7: Architectural Spike - Batch Processing | MEDIUM | 2-3 days | Original Epic 2 |
| 2.8: Alpha Release Preparation | MEDIUM | 2-3 days | Original Epic 2 |

**Total Epic 2 Duration:** 24-33 days (4.8-6.6 weeks) vs 5 weeks allocated → Within tolerance

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

#### Task 2.1.1: Resolve Type Ignore Comments in regex_matcher.py (TD-003)

**Source:** Epic 1 Technical Debt (Story 1.8 QA Gate)

**Description:** Fix 2 instances of `# type: ignore` comments by updating DetectedEntity signature to eliminate type safety warnings.

**Priority:** MEDIUM (Quick Win - 20 minutes)

**Rationale:** Clean code before Epic 2 adds more regex/NLP integration. Story 2.2 and 2.3 will interact with regex patterns - type safety helps prevent bugs.

**Acceptance Criteria:**
- [ ] Remove `# type: ignore` comments at lines 157 and 222 in `gdpr_pseudonymizer/nlp/regex_matcher.py`
- [ ] Update `DetectedEntity` dataclass signature if needed to resolve type conflicts
- [ ] Run `mypy` type checking - must pass with no errors
- [ ] Run full test suite - all existing tests must still pass
- [ ] Verify no new type warnings introduced elsewhere

**Estimated Effort:** 20 minutes
**Target:** Execute during Story 2.1 setup or as standalone quick task

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
2. **AC2:** Compound pseudonym assignment: Map compound names to compound pseudonyms (e.g., "Jean-Pierre" → "Luke-Han").
3. **AC3:** Component awareness: If "Jean" or "Pierre" appear separately, handle based on context (log as ambiguous if unclear).
4. **AC4:** Regex pattern support: Fallback regex for detecting common French compound patterns if NER doesn't identify them.
5. **AC5:** Unit tests: compound name detection, pseudonym assignment, edge cases (triple compounds, non-standard separators).
6. **AC6:** Test corpus validation: Verify compound names in test corpus processed correctly (from Story 1.1 edge cases).

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

2. ✅ **TD-003:** Resolve Type Ignore Comments → **Task 2.1.1**
   - Priority: MEDIUM (Quick Win)
   - Effort: 20 minutes
   - Rationale: Clean code before Epic 2 adds more regex/NLP integration

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
- **Task 2.1.1:** Type Ignore Comments (20 min) ← NEW from TD-003
- Story 2.2: Compositional Logic (4-5 days)
- Story 2.3: Compound Names (2-3 days)
- Story 2.4: Encrypted Mapping (4-5 days)
- Story 2.5: Audit Logging (2-3 days)
- Story 2.6: Single-Document Workflow (3-4 days)
- **Task 2.6.1:** Performance Tests (1 hour - optional) ← NEW from FE-003
- Story 2.7: Batch Processing Spike (2-3 days)
- **Task 2.7.1:** Performance Tests (1 hour - optional alternative) ← NEW from FE-003
- Story 2.8: Alpha Release Prep (2-3 days)

**Revised Total (with required backlog items):** 24-33 days (4.8-6.6 weeks)
**Revised Total (with all optional items):** 24.2-33.2 days (4.8-6.6 weeks)

### **Timeline Feasibility Check:**
- **Epic 2 Allocated Time:** 5 weeks (Week 6-10)
- **Revised Estimate:** 4.8-6.6 weeks
- **Buffer:** 0.2 weeks minimum, -1.6 weeks maximum (upper bound exceeds by 1.6 weeks)
- **Verdict:** Within tolerance if upper bound avoided; recommend aggressive prioritization

### **Risk Mitigation:**
1. **Story 2.0.1 is non-negotiable** - must complete before Story 2.6 (integration testing dependency)
2. **Task 2.1.1 is quick win** - 20 minutes won't impact timeline
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
   - **Task 2.1.1:** Resolve Type Ignore Comments (execute during setup - 20 min)

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
- ✅ **Task 2.1.1 Complete:** Type ignore comments resolved, mypy clean (TD-003 resolved)
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

**Document Status:** APPROVED v2.0 (Post-Epic 1 Completion, Backlog Integration)
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
