# Monitoring Baselines Review — Story 4.4

**Date:** 2026-02-08
**Reviewer:** Dev Agent (Story 4.4)

---

## MON-001: Validation UI Performance

**Target:** <10s per unique entity, >=90% completion rate

### Data Source

Review of `tests/test_corpus/validation_testing/TESTING_RESULTS.md` (Story 1.7 self-testing results, 2026-01-20).

### Findings

| Metric | Target | Observed | Status |
|--------|--------|----------|--------|
| Time per entity | <10s | ~few seconds | PASS |
| Completion rate (20-30 entity docs) | >=90% | 100% (doc2, doc3, doc4 completed) | PASS |
| Completion rate (100 entity docs) | >=90% | Incomplete (doc5 skipped due to duplicate fatigue) | PARTIAL |

**Detail:**
- **doc2 (20 entities):** Completed in <2 minutes (~few seconds per entity)
- **doc3 (30 entities):** Completed in <2 minutes
- **doc4 (50 entities):** Completed in <2 minutes
- **doc5 (100 entities):** Skipped — tester reported duplicate validation as too redundant

**User ratings** (self-testing):
- Speed: 4/5
- Clarity: 5/5
- Ease of Use: 5/5

### Baseline Methodology for Post-Launch

Real user data is not yet available (self-testing only). For production monitoring:
1. Instrument validation workflow to log: start time, end time, entity count, unique entity count
2. Calculate: time per unique entity = total_time / unique_entity_count
3. Track: completion rate = sessions_completed / sessions_started
4. **Note:** Deduplication was identified as critical for large-document completion rates

---

## MON-003: LOCATION/ORG Detection Accuracy

**Target:** <10% user-added entities (entities missed by detector that users must add manually)

### Data Source

Story 4.4 accuracy test results (Task 4.4.2).

### Findings

| Entity Type | Ground Truth | Detected (TP) | Missed (FN) | FN Rate | Target | Status |
|-------------|-------------|---------------|-------------|---------|--------|--------|
| **LOCATION** | 123 | 78 | 45 | 36.59% | <10% | FAIL |
| **ORG** | 105 | 36 | 69 | 65.71% | <10% | FAIL |
| **Combined** | 228 | 114 | 114 | 50.00% | <10% | FAIL |

**Interpretation:** The false negative rate for LOCATION (36.59%) and ORG (65.71%) exceeds the <10% target by a large margin. In practical terms:
- ~37% of locations would need to be manually added by users during validation
- ~66% of organizations would need to be manually added by users during validation

### Recommendations

1. **Expand LOCATION regex patterns:** Add French city/region dictionaries to supplement spaCy detection
2. **Expand ORG suffix patterns:** Add more organization indicators (Association, Fondation, Institut, Groupe, Consortium)
3. **Consider ORG dictionary approach:** Maintain a list of known French organizations for pattern matching
4. **Note:** These improvements are post-MVP; validation mode compensates for current accuracy

---

## MON-004: Context Cycling UX Discoverability

**Target:** >=50% of users use X key cycling

### Assessment

**Implementation status:** X key context cycling is fully implemented in the validation UI:
- File: `gdpr_pseudonymizer/validation/ui.py` — "Press X to cycle through N contexts" hint displayed for multi-occurrence entities
- File: `gdpr_pseudonymizer/validation/workflow.py` — `expand_context` action handler cycles through entity occurrences
- File: `gdpr_pseudonymizer/validation/ui.py` line 391 — Help overlay lists X key shortcut

**Discoverability features present:**
- Status bar text: "Press X to cycle through N contexts" shown when entity has multiple occurrences
- Help overlay (H key): Lists X as "Cycle contexts" shortcut
- Context indicator: Shows "(1/N)" format when multiple contexts available

**User testing data:** The TESTING_RESULTS.md does not specifically mention X key usage. The tester did not list X in the "shortcuts used" section, though they noted keyboard shortcuts were "intuitive" and the context display was "helpful."

### Assessment Result

Cannot definitively measure discoverability without user testing (per NFR11, no telemetry is collected). Current implementation includes:
- Inline hint text (good for discoverability)
- Help overlay mention (good for reference)
- Context count indicator (provides visual cue)

### Recommendations

1. **Collect data via Story 4.6 (external user testing):** Include specific question "Did you discover and use the X key for context cycling?"
2. **Consider enhancing discoverability:** Add a one-time tooltip or first-run prompt highlighting the X key feature
3. **No code changes needed:** Current implementation has adequate discoverability features; verification requires real user data

---

## Summary

| MON ID | Target | Status | Action Required |
|--------|--------|--------|-----------------|
| MON-001 | <10s/entity, >=90% completion | PASS (small docs), PARTIAL (large docs) | Instrument timing for production; deduplication critical for large docs |
| MON-003 | <10% user-added entities | FAIL (LOCATION 37%, ORG 66%) | Expand regex patterns post-MVP; validation mode is mitigation |
| MON-004 | >=50% use X key | CANNOT ASSESS (no telemetry) | Collect via Story 4.6 user testing |
