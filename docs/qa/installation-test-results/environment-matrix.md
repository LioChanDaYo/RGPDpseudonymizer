# Test Environment Matrix

## Host Machine Specifications

| Attribute | Value |
|-----------|-------|
| **OS** | Windows 11 (64-bit) |
| **Tester** | Dev Agent (James) |
| **Date** | 2026-02-07 |
| **Docker Available** | No |
| **WSL Available** | No |
| **Hyper-V/VirtualBox** | Not tested |

---

## Platform Coverage Strategy

| Platform | Test Method | Status |
|----------|-------------|--------|
| Windows 11 | Host machine | Planned |
| Windows 10 | Requires VM | Deferred - No VM |
| macOS Intel | CI results | Using CI |
| macOS Apple Silicon | CI results | Using CI |
| Ubuntu 22.04 | CI results | Using CI |
| Ubuntu 20.04 | Requires Docker | Deferred - No Docker |
| Ubuntu 24.04 | Requires Docker | Deferred - No Docker |
| Debian 11 | Requires Docker | Deferred - No Docker |
| Debian 12 | Requires Docker | Deferred - No Docker |
| Fedora 39 | Requires Docker | Deferred - No Docker |

---

## CI/CD Platform Coverage

**Source:** GitHub Actions CI run #21769193323 (2026-02-06)
**Workflow:** CI - Test Matrix
**Trigger:** feat(Story 4.1): LLM Utility Preservation Testing - NFR10 PASSED (#26)

| Platform | Python 3.9 | Python 3.10 | Python 3.11 |
|----------|------------|-------------|-------------|
| ubuntu-22.04 | SUCCESS | SUCCESS | SUCCESS |
| macos-latest | SUCCESS | SUCCESS | SUCCESS |
| windows-latest | SUCCESS | SUCCESS | SUCCESS |

**Notes:**
- Windows CI runs linting + non-spaCy tests only (spaCy access violation issue)
- macOS-latest tests both Intel and ARM architectures
- All 9 configurations pass consistently

---

## Environment Limitations

### Docker Not Available

Docker Desktop is not installed on the test machine. This prevents testing:
- Ubuntu 20.04, 24.04
- Debian 11, 12
- Fedora 39

**Recommendation:** Install Docker Desktop for comprehensive Linux testing.

### WSL Not Available

Windows Subsystem for Linux is not configured. This prevents quick Ubuntu testing.

**Recommendation:** Enable WSL2 for additional Linux validation.

### No Apple Hardware

macOS testing relies entirely on CI results (per Story 4.2 Option B).

---

## Validation Approach

Given limitations, this validation will:

1. **Use CI results** as primary evidence for:
   - Ubuntu 22.04 (fully tested with spaCy)
   - macOS Intel/ARM (fully tested with spaCy)
   - Windows latest (linting + partial tests)

2. **Perform manual testing** on:
   - Windows 11 (host machine) - full installation verification

3. **Document as deferred**:
   - Windows 10, Ubuntu 20.04/24.04, Debian 11/12, Fedora 39
   - These require VMs or Docker not available in current environment

4. **Calculate success rate** from available data points
