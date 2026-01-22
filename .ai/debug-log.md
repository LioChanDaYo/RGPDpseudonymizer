# Debug Log

## Story 1.8 - Manual Testing Findings (2026-01-22)

### UX Issue: Overlapping Entity Validation Order

**Reported By:** User (manual testing)
**Date:** 2026-01-22
**Severity:** Medium (UX improvement, not a blocker)
**Category:** Future Enhancement

**Issue Description:**

During manual testing of Story 1.8 hybrid detection, user identified a validation workflow UX issue:

When the system detects overlapping entities like:
- "Londres" (spaCy detection)
- "à Londres" (regex pattern detection)

OR

- "Marie Dubois" (spaCy detection)
- "Dr. Marie Dubois" (regex pattern detection)

The validation UI presents them sequentially without showing the user that there's an overlapping/contained entity coming next. This causes the user to validate "Londres" without knowing "à Londres" will appear later, leading to suboptimal decisions.

**Current Behavior:**
1. User sees "Londres" → Validates it
2. User sees "à Londres" next → Realizes they should have rejected "Londres" since it's contained in the longer entity
3. No way to know overlapping entities are coming

**User Impact:**
- Creates validation friction and potential for inconsistent entity selection
- User may validate shorter entity when longer, more complete entity should be preferred
- Requires backtracking or creates duplicate/overlapping pseudonyms

**Root Cause:**
- Deduplication logic correctly flags overlaps as ambiguous (AC4 requirement)
- BUT validation UI doesn't surface the overlap relationship to the user
- No "preview next entity" or "grouped overlapping entities" feature

**Potential Solutions (Future Enhancement):**

1. **Option A - Smart Deduplication:** When one entity fully contains another, automatically prefer the longer entity
   - Pro: Less user validation burden
   - Con: Loses user control, might prefer shorter in some cases

2. **Option B - Grouped Validation:** Show overlapping entities together in validation UI
   - Pro: User sees full context before deciding
   - Con: More complex UI, requires validation workflow changes

3. **Option C - Preview/Lookahead:** Show "Next entity: à Londres" when validating "Londres"
   - Pro: Simple UI addition, keeps sequential flow
   - Con: Only helps for immediate next entity

**Recommended Approach:**
Option B (Grouped Validation) provides best UX - show all overlapping entities in a single validation step, let user choose which version to keep.

**Story 1.8 Decision:**
- Mark as **Future Enhancement** - not blocking Story 1.8 completion
- Current behavior is documented and working as designed per AC4
- Story 1.8 can be marked Done with this noted for backlog

**Follow-up Action:**
- Create future story for validation workflow enhancement
- Consider in Epic 2 or post-MVP improvements

---
