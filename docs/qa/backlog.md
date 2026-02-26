# QA Backlog — Carry-Forward Items

Items identified during QA reviews that are not blocking but should be addressed in future work.

---

## Open Items

### GUI-001: Restore Pseudonym Highlighting in Results Screen

| Field | Value |
|-------|-------|
| **Source** | Story 6.7.1 QA Review (2026-02-26) |
| **Severity** | Medium |
| **Category** | GUI / UX |
| **Affects** | Results screen pseudonym highlighting (both one-shot and 3-phase flows) |

**Description:**
`entity_mappings` is always `[]` in both `ProcessingWorker` (L190) and `FinalizationWorker` (L129). The results screen (`results.py:_apply_highlighting`) uses this field to color-highlight pseudonyms in the output preview. With empty mappings, no highlighting is applied.

**Pre-existing:** The `FinalizationWorker` path (3-phase GUI flow) already had `entity_mappings = []` before Story 6.7.1. The `ProcessingWorker` path previously populated it via a DB query loop, but that loop was removed as part of the DATA-001 fix (it returned cumulative DB entities, not per-document ones — so the old highlighting was also incorrect).

**Fix approach:**
- Option A: Add `entity_mappings: list[tuple[str, str]] | None` to `ProcessingResult`, populated during `_resolve_pseudonyms` alongside `entity_type_counts`
- Option B: Build mappings in each worker from the validated entities list + the `ProcessingResult` pseudonym data

**Refs:**
- `gdpr_pseudonymizer/gui/workers/processing_worker.py:190`
- `gdpr_pseudonymizer/gui/workers/finalization_worker.py:129`
- `gdpr_pseudonymizer/gui/screens/results.py:212-239`

---

### SEC-002: Sanitize DEBUG-Level Log Statements for PII

| Field | Value |
|-------|-------|
| **Source** | Story 6.7.1 QA Review (2026-02-26) |
| **Severity** | Low |
| **Category** | Security / Defense-in-Depth |
| **Affects** | `document_processor.py` DEBUG-level logging |

**Description:**
Four `logger.debug()` calls reference entity text directly:
1. `_resolve_pseudonyms` (L477-479): logs `entity.text` and `entity.entity_type`
2. `_check_component_match` (L366-372): logs `parsed_first` and `prev_entity.full_name`
3. `_check_component_match` (L374-380): logs `parsed_first` and `prev_entity.full_name`

These are disabled in production (DEBUG level) and were out of scope for SEC-001 (which focused on `logger.error` paths). Risk is LOW but violates defense-in-depth principles.

**Fix approach:** Apply `_sanitize_error_message` pattern or use opaque identifiers (e.g., entity hash) instead of raw text in debug logs.

**Refs:**
- `gdpr_pseudonymizer/core/document_processor.py:366-380`
- `gdpr_pseudonymizer/core/document_processor.py:477-479`

---

## Resolved Items

| ID | Description | Resolved In | Date |
|----|-------------|-------------|------|
| DATA-001 | ProcessingWorker entity type count query uses cumulative DB totals | Story 6.7.1 | 2026-02-26 |
