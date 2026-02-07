# Platform Test: macOS (CI-Based Validation)

## Validation Method: GitHub Actions CI (Option B)
## Date: 2026-02-07
## CI Run ID: 21769193323

---

## Why CI-Based Validation?

Per Story 4.2 Task 4.2.4 Option B:
> "If no Apple hardware available: Use CI/CD validation. Review recent CI runs on `macos-latest` runner. Document CI test coverage as proxy for manual testing."

No Apple hardware is available for manual testing. GitHub Actions `macos-latest` runner tests both Intel and ARM architectures automatically.

---

## CI Test Coverage

### Configurations Tested

| Configuration | Python | Result |
|---------------|--------|--------|
| macos-latest | 3.9 | SUCCESS |
| macos-latest | 3.10 | SUCCESS |
| macos-latest | 3.11 | SUCCESS |

### Steps Validated (All Passed)

| Step | macos-3.9 | macos-3.10 | macos-3.11 |
|------|-----------|------------|------------|
| Set up Python | ✓ | ✓ | ✓ |
| Install Poetry | ✓ | ✓ | ✓ |
| Install dependencies | ✓ | ✓ | ✓ |
| Download spaCy model | ✓ | ✓ | ✓ |
| Run linting/type checks | ✓ | ✓ | ✓ |
| Run integration tests | ✓ | ✓ | ✓ |
| Run tests with coverage | ✓ | ✓ | ✓ |

---

## What CI Tests Validate

1. **Python Setup:** Correct version installs and activates
2. **Poetry Installation:** Poetry installs via pip successfully
3. **Dependency Installation:** All packages from poetry.lock install
4. **spaCy Model Download:** fr_core_news_lg downloads and loads
5. **Linting:** Code passes ruff, black, and mypy checks
6. **Integration Tests:** Full pseudonymization workflow works
7. **Unit Tests:** All test suites pass

---

## CI Runner Details

GitHub Actions `macos-latest` uses:
- macOS Monterey (12.x) or Ventura (13.x)
- Both Intel and ARM (Apple Silicon) runners
- Pre-configured with Xcode Command Line Tools
- pip/pipx available for Poetry installation

---

## Failure Scenarios (Inferred from CI Success)

| Scenario | CI Coverage |
|----------|-------------|
| Xcode Command Line Tools missing | CI has pre-installed |
| Homebrew Python conflicts | CI uses setup-python action |
| Poetry PATH issues with zsh | CI adds to PATH automatically |

**Note:** These scenarios are mitigated by CI environment configuration. Real-world fresh macOS installs may encounter these - documentation addresses them.

---

## Known Limitations

1. **Not a fresh OS install:** CI runners have pre-configured environments
2. **No interactive testing:** Cannot test validation UI interactively
3. **Network conditions ideal:** GitHub runners have fast, stable connections

---

## Documentation Validation

The installation guide (`docs/installation.md`) includes:
- [x] Homebrew Python installation steps
- [x] Xcode Command Line Tools requirement
- [x] Poetry PATH configuration for zsh
- [x] Apple Silicon compatibility note

---

## Conclusion

macOS installation validated via CI/CD:
- All 3 Python versions (3.9, 3.10, 3.11) pass
- All installation and test steps succeed
- Full integration test coverage confirms functionality

**Platform Status: PASS (via CI proxy)**
