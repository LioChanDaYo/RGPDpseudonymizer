# Bug Fix: Test Expectations for Hyphenated Pseudonyms

**Date:** 2026-01-29
**Type:** Test Bug (Not Code Bug)
**Severity:** Low - Test assertions were incorrect, code is correct

---

## Summary

Integration tests in `test_compositional_logic_integration.py` had incorrect assertions expecting that pseudonyms should NOT contain hyphens. However, the Star Wars pseudonym library legitimately contains hyphenated character names like "Qel-Droma", "Bo-Katan", and "Triple-Zero", which are valid Star Wars character names.

---

## The Issue

**Failed Test:**
```
FAILED tests/integration/test_compositional_logic_integration.py::TestTitleAndCompoundNameIntegration::test_compound_last_name_sharing
AssertionError: assert '-' not in 'Qel-Droma'
```

**Failing Assertions (Lines 812-813, 869-870):**
```python
# Compound names get SIMPLE pseudonyms (no hyphens)
assert "-" not in assignment_1.pseudonym_first
assert "-" not in assignment_2.pseudonym_first
assert "-" not in assignment_1.pseudonym_last
assert "-" not in assignment_2.pseudonym_last
```

**Contradiction:** The same test file acknowledges (lines 1043-1044):
```python
# Note: Pseudonyms may contain hyphens (e.g., "Triple-Zero", "Soo-Tath",
# "Bo-Katan" in Star Wars library) which is valid for character names.
```

---

## Root Cause

The test had a misunderstanding about pseudonym library design:
- **Incorrect assumption:** Compound REAL names (like "Paluel-Marmont") should receive SIMPLE pseudonyms without hyphens
- **Reality:** Pseudonym libraries contain character names that may naturally include hyphens (Star Wars characters like "Qel-Droma")
- **Design decision:** The system assigns atomic pseudonyms from the library - whether they contain hyphens is determined by the library content, not the system logic

---

## Evidence from Star Wars Library

`data/pseudonyms/star_wars.json` contains legitimate hyphenated character names:
- Line 135: "Bo-Katan"
- Line 213, 772: "Triple-Zero"
- Line 1046: "Qel-Droma"

These are canonical Star Wars character names.

---

## The Fix

**Changed:**
```python
# OLD (incorrect):
# Compound names get SIMPLE pseudonyms (no hyphens)
assert "-" not in assignment_1.pseudonym_last
assert "-" not in assignment_2.pseudonym_last

# NEW (correct):
# Note: Pseudonyms may contain hyphens (e.g., "Qel-Droma" in Star Wars)
# which is valid for character names in themed libraries
```

**Files Modified:**
- [tests/integration/test_compositional_logic_integration.py](tests/integration/test_compositional_logic_integration.py)
  - Lines 809-814: `test_compound_first_name_sharing`
  - Lines 865-870: `test_compound_last_name_sharing`

---

## Test Results After Fix

```bash
$ poetry run pytest tests/integration/test_compositional_logic_integration.py -v

18 passed in 0.19s
```

All tests pass ✓

---

## Why This is Not a Code Bug

1. **Library Design is Correct:** Themed pseudonym libraries should contain authentic character names from their source material
2. **Assignment Logic is Correct:** The system treats all pseudonyms as atomic units, whether they contain hyphens or not
3. **Compositional Logic is Correct:** A compound real name like "Paluel-Marmont" gets assigned a single atomic pseudonym (could be "Solo" or "Qel-Droma")
4. **GDPR Compliance:** The 1:1 mapping is maintained - "Paluel-Marmont" consistently maps to the same pseudonym (e.g., "Qel-Droma")

The fact that "Qel-Droma" contains a hyphen is irrelevant to the pseudonymization logic.

---

## Lessons Learned

1. **Test expectations should match reality:** Don't impose artificial constraints based on assumptions
2. **Library content drives behavior:** If Star Wars characters have hyphens, pseudonyms will have hyphens
3. **Atomic treatment:** The system correctly treats all pseudonyms as atomic units, regardless of internal structure

---

## Related Documentation

- Pseudonym Libraries: `data/pseudonyms/*.json`
- Story 2.1: Pseudonym Library System
- Story 2.3: Compound Name Handling

---

**Status:** FIXED ✓ - Tests updated to reflect correct behavior
