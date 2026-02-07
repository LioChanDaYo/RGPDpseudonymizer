# Installation Test Protocol

## Purpose

Standardized procedure for validating NFR3 (≥85% installation success rate) and NFR14 (≥80% complete first pseudonymization within 30 minutes).

---

## Test Procedure

### Step-by-Step Process

1. **Record start time** (wall clock)
2. **Follow `docs/installation.md` exactly** as written
3. **Record each step** with timestamp and result (✓/✗)
4. **Note any deviations** or issues encountered
5. **Complete first pseudonymization** - verify `gdpr-pseudo process` works
6. **Record end time** (wall clock)

### Verification Commands

```bash
# Standard installation verification
poetry run gdpr-pseudo --help
poetry run gdpr-pseudo --version

# First pseudonymization test
echo "Marie Dubois travaille a Paris." > test_install.txt
poetry run gdpr-pseudo process test_install.txt
cat test_install_pseudonymized.txt

# Clean up
rm test_install.txt test_install_pseudonymized.txt mappings.db
```

---

## Test Result Template

Copy this template for each platform test:

```markdown
## Platform: [OS Name Version Architecture]
### Tester: [Name/ID]
### Date: [YYYY-MM-DD]
### Environment: [VM/Container/Physical] - [RAM] / [Disk] / [Virtualization Platform]

| Step | Time (mm:ss) | Result | Notes |
|------|--------------|--------|-------|
| 1. Install Python | 00:00 | ✓/✗ | |
| 2. Install Poetry | 05:00 | ✓/✗ | |
| 3. Clone repository | 08:00 | ✓/✗ | |
| 4. poetry install | 10:00 | ✓/✗ | |
| 5. Install spaCy model | 15:00 | ✓/✗ | |
| 6. Verify CLI (--help) | 20:00 | ✓/✗ | |
| 7. First pseudonymization | 22:00 | ✓/✗ | |

### Total Time: XX minutes
### Final Status: SUCCESS / FAILED
### Issues Encountered:
- Issue 1: [description]

### Recommendations:
- [Any documentation improvements needed]
```

---

## Platforms to Test

| Platform | Method | Priority |
|----------|--------|----------|
| Windows 11 (64-bit) | Host/VM | High |
| Windows 10 (64-bit) | VM | High |
| Ubuntu 22.04 | Docker/CI | High |
| Ubuntu 20.04 | Docker | Medium |
| Ubuntu 24.04 | Docker | Medium |
| Debian 12 | Docker | Medium |
| Debian 11 | Docker | Medium |
| Fedora 39 | Docker | Low |
| macOS Intel | CI results | Medium |
| macOS Apple Silicon | CI results | Medium |

---

## Docker Commands for Linux Testing

```bash
# Ubuntu 20.04 - fresh install test
docker run -it --rm ubuntu:20.04 bash

# Ubuntu 22.04 - fresh install test
docker run -it --rm ubuntu:22.04 bash

# Ubuntu 24.04 - fresh install test
docker run -it --rm ubuntu:24.04 bash

# Debian 11 - fresh install test
docker run -it --rm debian:11 bash

# Debian 12 - fresh install test
docker run -it --rm debian:12 bash

# Fedora 39 - fresh install test
docker run -it --rm fedora:39 bash
```

---

## Failure Scenarios to Test

| Scenario | Expected Error | Recovery Steps |
|----------|----------------|----------------|
| Python not installed | "python: command not found" | Install Python 3.9-3.11 |
| Python 3.12+ installed | "not supported" message | Use `poetry env use python3.11` |
| Poetry not in PATH | "poetry: command not found" | Add to PATH per docs |
| Model download fails | Network/disk error | Check space, retry with --verbose |
| Permission denied | Access error | Check file permissions |
| PowerShell blocks scripts | Execution policy error | Set-ExecutionPolicy |

---

## Success Criteria

- **NFR3:** ≥85% of platforms install successfully
- **NFR14:** ≥80% complete first pseudonymization within 30 minutes
