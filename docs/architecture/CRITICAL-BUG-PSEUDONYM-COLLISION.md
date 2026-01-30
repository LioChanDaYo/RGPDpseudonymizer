# CRITICAL BUG: Pseudonym Component Collision

**Discovered:** 2026-01-29 during Story 2.7 (Batch Processing Spike)
**Severity:** CRITICAL - BLOCKING for Epic 3
**Status:** IDENTIFIED - Awaiting fix

---

## Summary

During batch processing verification, a critical GDPR compliance bug was discovered: **two different real entities can be assigned the same pseudonym**, violating the 1:1 mapping requirement.

**Example:**
- "Dubois" → pseudonym "Neto"
- "Lefebvre" → pseudonym "Neto"

This is unacceptable for GDPR-compliant pseudonymization.

---

## How It Happened

1. **"Marie Dubois"** processed first → randomly assigned last name "Neto" → pseudonym "Alexia **Neto**"
2. **"Pierre Lefebvre"** processed second → randomly assigned last name "Neto" → pseudonym "Maurice **Neto**"
3. By random chance, both got "Neto" as their last-name component
4. Later, standalone **"Dubois"** found existing mapping → correctly reused "Neto"
5. Later, standalone **"Lefebvre"** found existing mapping → correctly reused "Neto"
6. **Result:** Two different real last names now map to same pseudonym

---

## Root Cause

**File:** [gdpr_pseudonymizer/pseudonym/library_manager.py](gdpr_pseudonymizer/pseudonym/library_manager.py)

**Problem:** `LibraryBasedPseudonymManager._used_pseudonyms` only tracks FULL pseudonyms (e.g., "Alexia Neto"), not individual components (e.g., "Neto").

- Two people can have different full pseudonyms: "Alexia Neto" ≠ "Maurice Neto" ✓
- But they share the same last-name component: "Neto" = "Neto" ✗
- Component tracking missing

---

## Impact

- **GDPR Compliance:** Violates Article 4(5) pseudonymization requirement (1:1 mapping)
- **Data Integrity:** Different individuals conflated in processed documents
- **Reversibility:** Cannot uniquely reverse pseudonyms to original entities
- **Probability:** Low (~0.1% with 500-name library) but **non-zero** in production

---

## Proposed Fix (Recommended: Option 1)

### Option 1: Component-Level Collision Prevention

Add component mapping tracking to `LibraryBasedPseudonymManager`:

```python
class LibraryBasedPseudonymManager(PseudonymManager):
    def __init__(self):
        # ... existing code ...
        self._component_mappings: dict[tuple[str, str], str] = {}
        # Key: (real_component, component_type)
        # Value: pseudonym_component

    def _select_last_name(self, real_last_name: str | None = None) -> str:
        """Select last name with collision prevention."""

        # Check if real_last_name already has mapping
        if real_last_name:
            mapping_key = (real_last_name, "last_name")
            if mapping_key in self._component_mappings:
                return self._component_mappings[mapping_key]

        # Select new pseudonym, ensure no collision
        max_attempts = 100
        for _ in range(max_attempts):
            candidate = secrets.choice(self.last_names)

            # Check if this pseudonym component already used for different real name
            if candidate not in self._component_mappings.values():
                if real_last_name:
                    self._component_mappings[(real_last_name, "last_name")] = candidate
                return candidate

        raise RuntimeError("Unable to find unique last name component after 100 attempts")
```

**Changes needed:**
1. Add `_component_mappings` dict to `__init__()`
2. Update `_select_last_name()` to check mappings
3. Update `_select_first_name()` similarly
4. Pass `real_first_name` and `real_last_name` to selection methods

**Pros:**
- Minimal code change
- No database queries
- Fast in-memory check

**Cons:**
- In-memory only (lost on restart)
- Need to reconstruct mappings from database on startup

---

## Alternative Fixes

### Option 2: Database-Backed Component Lookup

Query MappingRepository before assigning components to check for existing mappings.

**Pros:** Most robust, leverages database constraints
**Cons:** Performance impact (DB query per component)

### Option 3: Deterministic Component Assignment

Use HMAC-based deterministic selection instead of random.

**Pros:** Eliminates collision risk entirely
**Cons:** Reduces randomness, requires key management

---

## Testing Requirements

Before merging fix:

1. **Unit test:** Verify no component collisions after 1000 assignments
2. **Integration test:** Process documents with overlapping components, verify 1:1 mapping
3. **Update verification script:** Add component-level collision detection to `verify_mapping_consistency.py`

---

## Next Steps

1. **Create bug fix story** (estimated: 2-3 days)
2. **Implement Option 1** (component-level collision prevention)
3. **Add unit + integration tests**
4. **Verify fix with batch processing spike**
5. **Then proceed with Epic 3**

---

## References

- **Story:** [2.7 Batch Processing Scalability Spike](docs/stories/2.7.batch-processing-scalability-spike.story.md)
- **Findings:** [Batch Processing Spike Findings - Issue 5](docs/architecture/batch-processing-spike-findings.md#issue-5-pseudonym-component-collision-critical---blocking)
- **Analysis Scripts:** `scripts/check_duplicates.py`, `scripts/check_names.py`
- **Affected Code:** [gdpr_pseudonymizer/pseudonym/library_manager.py](gdpr_pseudonymizer/pseudonym/library_manager.py) lines 184-286

---

**Status:** This is exactly the kind of critical issue that architectural spikes are designed to discover. The batch processing architecture itself is sound - this bug exists in the pseudonym assignment logic and would have occurred in single-document processing as well (just with lower probability).
