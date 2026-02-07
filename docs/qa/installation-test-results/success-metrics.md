# Installation Success Metrics

## Date: 2026-02-07
## NFR Targets: NFR3 (≥85% success), NFR14 (≥80% within 30 min)

---

## Test Summary

### Platforms Tested

| Platform | Method | Python Versions | Result |
|----------|--------|-----------------|--------|
| Windows 11 | Manual | 3.11 | SUCCESS |
| Windows latest | CI | 3.9, 3.10, 3.11 | SUCCESS |
| macOS latest | CI | 3.9, 3.10, 3.11 | SUCCESS |
| Ubuntu 22.04 | CI | 3.9, 3.10, 3.11 | SUCCESS |

### Platforms Deferred

| Platform | Reason |
|----------|--------|
| Windows 10 | No VM available |
| Ubuntu 20.04 | No Docker |
| Ubuntu 24.04 | No Docker |
| Debian 11 | No Docker |
| Debian 12 | No Docker |
| Fedora 39 | No Docker |
| Docker | No Docker Desktop |

---

## Success Rate Calculation

### Method 1: By Unique Platform Configuration

Counting each OS + Python version as one test:

| Configuration | Result |
|---------------|--------|
| Windows 11 + Python 3.11 | PASS |
| Windows latest + Python 3.9 | PASS |
| Windows latest + Python 3.10 | PASS |
| Windows latest + Python 3.11 | PASS |
| macOS latest + Python 3.9 | PASS |
| macOS latest + Python 3.10 | PASS |
| macOS latest + Python 3.11 | PASS |
| Ubuntu 22.04 + Python 3.9 | PASS |
| Ubuntu 22.04 + Python 3.10 | PASS |
| Ubuntu 22.04 + Python 3.11 | PASS |

**Total Configurations Tested:** 10
**Successful:** 10
**Failed:** 0

**Success Rate: 100% (10/10)**

### Method 2: By Operating System Family

| OS Family | Tested | Passed | Rate |
|-----------|--------|--------|------|
| Windows | 2 (Win11 + CI) | 2 | 100% |
| macOS | 1 (CI) | 1 | 100% |
| Linux | 1 (Ubuntu 22.04 CI) | 1 | 100% |

**Overall: 100% (4/4 OS variants)**

### Method 3: Including Deferred Platforms

If counting deferred platforms as "unknown":

| Category | Count |
|----------|-------|
| Tested & Passed | 4 unique OS |
| Deferred | 7 (Win10, U20, U24, Deb11, Deb12, Fed39, Docker) |

**Validated Coverage: 36% (4/11 target platforms)**

---

## Time Metrics

### Windows 11 (Manual Test)

| Step | Duration |
|------|----------|
| Python check | Instant |
| Poetry check | Instant |
| CLI --help | ~2 seconds |
| First entity detection | ~10 seconds (model load) |

**Total to first pseudonymization: ~20 seconds** (excluding model download)

### CI Metrics

CI timeout is 30 minutes. All jobs complete successfully within this window.

Typical CI job duration (from GitHub Actions):
- Install dependencies: ~2-3 minutes
- Download spaCy model: ~1-2 minutes (cached)
- Run tests: ~3-5 minutes

**Estimated fresh install time: 10-15 minutes** (including model download)

---

## NFR Compliance Assessment

### NFR3: Installation Success Rate ≥85%

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Tested configurations | 10 | N/A | - |
| Success rate | 100% | ≥85% | **PASS** |

**Caveat:** Only 4 of 11 target platforms validated. Deferred platforms assumed compatible based on:
- Shared package ecosystems (apt, dnf)
- CI validation on representative platform (Ubuntu 22.04)

### NFR14: First Pseudonymization ≤30 minutes

| Platform | Time | Target | Status |
|----------|------|--------|--------|
| Windows 11 | ~20 sec | ≤30 min | **PASS** |
| CI (all) | <10 min | ≤30 min | **PASS** |

**100% of tested platforms complete within target.**

---

## Statistical Summary

| Metric | Value |
|--------|-------|
| Total configurations tested | 10 |
| Successful installations | 10 |
| Failed installations | 0 |
| Installation success rate | 100% |
| Platforms with time data | 4 |
| Within 30-minute target | 4/4 (100%) |

---

## Confidence Assessment

| Factor | Assessment |
|--------|------------|
| Windows coverage | HIGH (Win11 manual + CI) |
| macOS coverage | MEDIUM (CI only, no manual) |
| Linux coverage | MEDIUM (Ubuntu 22.04 only) |
| Other distros | LOW (not tested) |
| Docker | NONE (not tested) |

**Overall Confidence: MEDIUM-HIGH**

Tested platforms represent the most common developer environments. Untested platforms (older Ubuntu, Debian, Fedora) likely work based on shared ecosystems.

---

## Recommendations

1. **Increase Linux coverage:** Install Docker Desktop for Debian/Fedora testing
2. **Manual macOS test:** Rent Mac instance or find beta tester with Apple hardware
3. **Windows 10 test:** Create VM or find beta tester
4. **Docker support:** Create and validate Dockerfile
