# Docker Container Installation Tests

## Date: 2026-02-07
## Environment: Docker Desktop 29.2.0 on Windows 11

---

## Test Results Summary

| Distribution | Python Version | Result | Time |
|--------------|---------------|--------|------|
| Ubuntu 20.04 | 3.8.10 | **FAIL** | N/A |
| Ubuntu 24.04 | 3.12.3 | **PASS** | 24 min |
| Debian 12 | 3.11.2 | **PASS** | 41 min |
| Fedora 39 | 3.12.7 | **PASS** | 42 min |

---

## Detailed Results

### Ubuntu 20.04 - FAIL

**Python Version:** 3.8.10
**Status:** FAILED - Python version below minimum requirement (3.9+)

```
Step 1: Update and install prerequisites... OK
Step 2: Check Python version... Python 3.8.10
Step 3: Install Poetry... FAILED (PATH issues)
```

**Root Cause:** Ubuntu 20.04 ships with Python 3.8.10, which is below the project's minimum requirement of Python 3.9.

**Recommendation:** Document that Ubuntu 20.04 users must install Python 3.9+ manually via deadsnakes PPA or pyenv.

---

### Ubuntu 24.04 - PASS

**Python Version:** 3.12.3
**Status:** SUCCESS
**Total Time:** 1447 seconds (~24 minutes)

```
Step 1: Update and install prerequisites... OK
Step 2: Check Python version... Python 3.12.3
Step 3: Install Poetry... Poetry (version 2.3.2)
Step 4: Clone repository... OK
Step 5: Poetry install... OK
Step 6: Verify CLI... gdpr-pseudo version 0.1.0
```

**Note:** Python 3.12 is outside the officially supported range (3.9-3.11), but installation and CLI verification succeeded. Consider expanding supported Python versions.

---

### Debian 12 - PASS

**Python Version:** 3.11.2
**Status:** SUCCESS
**Total Time:** 2467 seconds (~41 minutes)

```
Step 1: Update and install prerequisites... OK
Step 2: Check Python version... Python 3.11.2
Step 3: Install Poetry... Poetry (version 2.3.2)
Step 4: Clone repository... OK
Step 5: Poetry install... OK
Step 6: Verify CLI... gdpr-pseudo version 0.1.0
```

**Note:** Python 3.11.2 is within the supported range. Installation successful.

---

### Fedora 39 - PASS

**Python Version:** 3.12.7
**Status:** SUCCESS
**Total Time:** 2519 seconds (~42 minutes)

```
Step 1: Install prerequisites... OK
Step 2: Check Python version... Python 3.12.7
Step 3: Install Poetry... Poetry (version 2.3.2)
Step 4: Clone repository... OK
Step 5: Poetry install... OK
Step 6: Verify CLI... gdpr-pseudo version 0.1.0
```

**Note:** Fedora 39 uses dnf package manager. Fedora-specific instructions were added to installation.md.

---

## Updated Success Metrics

### All Platforms Combined

| Platform | Result |
|----------|--------|
| Windows 11 (manual) | PASS |
| Windows latest (CI) | PASS |
| macOS latest (CI) | PASS |
| Ubuntu 22.04 (CI) | PASS |
| Ubuntu 20.04 (Docker) | **FAIL** |
| Ubuntu 24.04 (Docker) | PASS |
| Debian 12 (Docker) | PASS |
| Fedora 39 (Docker) | PASS |

**Total:** 7 PASS / 1 FAIL = **87.5% success rate**

**NFR3 Target:** ≥85% → **PASS**

---

## Recommendations

1. **Ubuntu 20.04:** Add note to installation.md requiring Python 3.9+ installation via PPA
2. **Python 3.12 support:** Consider officially supporting Python 3.12 (tested working on Ubuntu 24.04 and Fedora 39)
3. **Installation time:** Note that first installation takes 20-45 minutes due to dependency downloads

---

## Test Commands Used

```bash
# Ubuntu 20.04
docker run --rm ubuntu:20.04 bash -c '...'

# Ubuntu 24.04
docker run --rm ubuntu:24.04 bash -c '...'

# Debian 12
docker run --rm debian:12 bash -c '...'

# Fedora 39
docker run --rm fedora:39 bash -c '...'
```
