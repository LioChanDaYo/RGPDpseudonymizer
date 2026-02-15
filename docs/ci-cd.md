# CI/CD Documentation

## Overview

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the GDPR Pseudonymizer project. The CI/CD system automates testing, code quality checks, and coverage reporting across multiple platforms.

---

## CI/CD Architecture

### Workflow Files

All GitHub Actions workflows are located in `.github/workflows/`:

- **[ci.yaml](.github/workflows/ci.yaml)**: Main testing workflow with OS/Python matrix
- **[code-quality.yaml](.github/workflows/code-quality.yaml)**: Code formatting, linting, and type checking

### Test Matrix Strategy

The CI pipeline runs tests across **9 configurations** to ensure cross-platform compatibility:

| Operating System | Python Versions | Total Configs |
|-----------------|----------------|---------------|
| Ubuntu 22.04 | 3.9, 3.10, 3.11 | 3 |
| macOS (latest) | 3.9, 3.10, 3.11 | 3 |
| Windows (latest) | 3.9, 3.10, 3.11 | 3 |

**Rationale:**
- Python 3.9+ required (EOL Oct 2025)
- Ubuntu 22.04: Primary development platform
- macOS/Windows: Ensure cross-platform compatibility
- Matrix runs in parallel for fast feedback

---

## Quality Checks

### 1. Code Formatting (Black)

**Tool:** Black 23.12+
**Configuration:** [pyproject.toml](pyproject.toml) `[tool.black]`
**Command:** `poetry run black --check gdpr_pseudonymizer/ tests/ scripts/`

**Settings:**
- Line length: 88 characters
- Target: Python 3.9+
- Opinionated formatting (no configuration debates)

**CI Behavior:** Fails if code is not formatted. Run `poetry run black .` to auto-format.

### 2. Linting (Ruff)

**Tool:** Ruff 0.1+ (10-100x faster than Flake8)
**Configuration:** [pyproject.toml](pyproject.toml) `[tool.ruff]`
**Command:** `poetry run ruff check gdpr_pseudonymizer/ tests/ scripts/`

**Rules Enabled:**
- `F` - Pyflakes (import errors, undefined names)
- `E` - pycodestyle errors (style violations)
- `W` - pycodestyle warnings
- `I` - isort (import sorting)
- `N` - pep8-naming (naming conventions)
- `UP` - pyupgrade (modern Python syntax)

**CI Behavior:** Fails on any linting errors. Run `poetry run ruff check --fix .` to auto-fix.

### 3. Type Checking (mypy)

**Tool:** mypy 1.7+
**Configuration:** [mypy.ini](mypy.ini) and [pyproject.toml](pyproject.toml) `[tool.mypy]`
**Command:** `poetry run mypy gdpr_pseudonymizer/`

**Settings:**
- Strict mode enabled
- Python 3.9 compatibility
- Ignores missing type stubs for spaCy, Stanza, pytest

**CI Behavior:** Fails on type errors. Add type hints or `# type: ignore` comments where necessary.

---

## Coverage Requirements

### Target Thresholds

| Epic | Coverage Target | Status |
|------|----------------|--------|
| Epic 1 | 70% | Active |
| Epic 2 | 80% | Future |
| Epic 3-4 | 85% | Future |

### Coverage Configuration

**Tool:** pytest-cov 4.1+ (Coverage.py wrapper)
**Configuration:** [pyproject.toml](pyproject.toml) `[tool.coverage]`
**Codecov Config:** [.codecov.yml](.codecov.yml)

**Coverage Options:**
- Branch coverage enabled (`--cov-branch`)
- Source: `gdpr_pseudonymizer/` package
- Excludes: `tests/`, `scripts/`, `__pycache__/`

### Coverage Reporting

**In CI:**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=xml --cov-report=term --cov-branch -v
```

**Locally (HTML report):**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=html
# Open htmlcov/index.html in browser
```

**Codecov Integration:**
- Coverage reports uploaded from Ubuntu 22.04, Python 3.11 configuration
- Codecov comments on PRs with coverage changes
- Requires repository admin to add Codecov GitHub App

---

## Running Checks Locally

### Prerequisites

1. **Install Poetry:**
   ```bash
   pip install poetry>=1.7.0
   ```

2. **Install Dependencies:**
   ```bash
   poetry install
   ```

3. **Download spaCy Model:**
   ```bash
   poetry run python -m spacy download fr_core_news_lg
   ```

### Code Quality Commands

**Format Code:**
```bash
poetry run black gdpr_pseudonymizer/ tests/ scripts/
```

**Check Formatting (no changes):**
```bash
poetry run black --check gdpr_pseudonymizer/ tests/ scripts/
```

**Lint Code:**
```bash
poetry run ruff check gdpr_pseudonymizer/ tests/ scripts/
```

**Auto-Fix Linting Issues:**
```bash
poetry run ruff check --fix gdpr_pseudonymizer/ tests/ scripts/
```

**Type Check:**
```bash
poetry run mypy gdpr_pseudonymizer/
```

### Testing Commands

**Run All Tests:**
```bash
poetry run pytest
```

**Run Unit Tests Only:**
```bash
poetry run pytest tests/unit/ -v
```

**Run Tests with Coverage:**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=term
```

**Run Tests with HTML Coverage Report:**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=html
# Open htmlcov/index.html
```

**Run Specific Test File:**
```bash
poetry run pytest tests/unit/test_spacy_detector.py -v
```

**Run Tests Matching Pattern:**
```bash
poetry run pytest -k "test_entity_detection" -v
```

### Performance Testing

**Run Benchmark Tests:**
```bash
poetry run pytest tests/performance/ --benchmark-only
```

### Performance Benchmarks in CI

The primary CI job (Ubuntu 3.11) runs performance benchmarks alongside the test suite:

- **Benchmark JSON output:** `--benchmark-json=benchmark-results.json` captures benchmark results
- **Time guard:** `--benchmark-max-time=60` limits benchmark duration to prevent CI timeouts
- **Artifact upload:** Benchmark JSON is uploaded as a build artifact with 30-day retention for tracking

**Benchmark groups:**

| Group | File | Measures |
|-------|------|----------|
| `single-document` | `test_single_document_benchmark.py` | Full pipeline (NLP + DB + file I/O) for 2K/3.5K/5K word docs |
| `entity-detection` | `test_single_document_benchmark.py` | Hybrid NLP+regex detection only (isolates NLP regressions) |
| `batch` | `test_batch_performance.py` | 50-document batch processing throughput |

**Thresholds:**
- NFR1: Single document processing <30 seconds
- NFR2: 50-document batch <30 minutes (1800s)

Benchmarks are **not** run on Windows (spaCy segfault) or macOS — only on the primary Ubuntu 3.11 job.

See [tests/performance/README.md](../tests/performance/README.md) for local usage.

---

## Common CI Failures and Troubleshooting

### 1. Poetry Dependency Resolution Failures

**Symptoms:**
- `poetry install` hangs or fails
- Dependency conflicts reported

**Solutions:**
- Update `poetry.lock`: `poetry lock --no-update`
- Clear Poetry cache: `poetry cache clear pypi --all`
- Check Python version matches `pyproject.toml` requirements

### 2. spaCy Model Download Issues

**Symptoms:**
- 571MB download timeout
- Model not found errors
- Network errors during download

**Solutions:**
- CI caches models at `~/.spacy` (check cache key in [ci.yaml](.github/workflows/ci.yaml))
- Manually download model: `poetry run python -m spacy download fr_core_news_lg`
- Check model installed: `poetry run python -c "import spacy; nlp = spacy.load('fr_core_news_lg'); print('OK')"`

### 3. Platform-Specific Test Failures

**Symptoms:**
- Tests pass on Linux, fail on Windows/macOS
- Path separator issues (`/` vs `\`)
- Line ending issues (LF vs CRLF)

**Solutions:**
- Use `pathlib.Path` for all file paths (not `os.path`)
- Configure Git line endings: `.gitattributes` file
- Test locally on target OS before pushing

### 4. Type Checking Errors (mypy)

**Symptoms:**
- mypy reports type errors not caught by IDE
- Strict mode too restrictive

**Solutions:**
- Add type hints to function signatures
- Use `# type: ignore` comments sparingly for unavoidable errors
- Add missing imports to `mypy.ini` `[mypy-<module>]` sections
- Relax strictness temporarily if blocking (edit `mypy.ini`)

### 5. Coverage Threshold Failures

**Symptoms:**
- Coverage drops below 80% threshold
- New code not tested

**Solutions:**
- Write unit tests for new functions/classes
- Check coverage report: `poetry run pytest --cov=gdpr_pseudonymizer --cov-report=html`
- Open `htmlcov/index.html` to see uncovered lines
- Add tests for edge cases and error handling

### 6. Black Formatting Failures

**Symptoms:**
- CI reports "files would be reformatted"
- Code not formatted to Black style

**Solutions:**
- Run `poetry run black .` to auto-format
- Commit formatted changes
- Configure IDE to format on save (VS Code: `python.formatting.provider = "black"`)

### 7. Ruff Linting Failures

**Symptoms:**
- Import sorting errors
- Naming convention violations
- Unused imports

**Solutions:**
- Run `poetry run ruff check --fix .` to auto-fix
- Remove unused imports
- Follow naming conventions (see [19-coding-standards.md](architecture/19-coding-standards.md))

---

## Branch Protection Rules

### Required Status Checks

To merge a PR, the following checks **must pass**:

1. **CI Checks (3 required):**
   - `ci (ubuntu-22.04, 3.11)` - Primary platform
   - `ci (macos-latest, 3.11)` - macOS compatibility
   - `ci (windows-latest, 3.11)` - Windows compatibility

2. **Code Quality:**
   - `code-quality` - Black, Ruff, mypy checks

**Note:** Not all 9 matrix configurations are required (to allow faster merges), but all must pass before merging.

### Configuring Branch Protection (Admin Guide)

**Prerequisites:** Repository admin access

**Steps:**

1. Navigate to **Settings** → **Branches** → **Branch protection rules**
2. Click **Add rule**
3. Configure:
   - **Branch name pattern:** `main`
   - ✅ **Require status checks to pass before merging**
   - ✅ **Require branches to be up to date before merging**
   - **Status checks that are required:**
     - `ci (ubuntu-22.04, 3.11)`
     - `ci (macos-latest, 3.11)`
     - `ci (windows-latest, 3.11)`
     - `code-quality`
   - ✅ **Require linear history** (optional, prevents merge commits)
   - ✅ **Do not allow bypassing the above settings** (enforce for admins)
4. Click **Create** or **Save changes**

**Screenshot Placeholder:** (Add screenshot of GitHub branch protection UI)

---

## Workflow Badges

Add these badges to [README.md](README.md) to show CI status:

### CI Status Badge

```markdown
[![CI](https://github.com/your-org/gdpr-pseudonymizer/actions/workflows/ci.yaml/badge.svg)](https://github.com/your-org/gdpr-pseudonymizer/actions/workflows/ci.yaml)
```

### Code Quality Badge

```markdown
[![Code Quality](https://github.com/your-org/gdpr-pseudonymizer/actions/workflows/code-quality.yaml/badge.svg)](https://github.com/your-org/gdpr-pseudonymizer/actions/workflows/code-quality.yaml)
```

### Coverage Badge (Codecov)

```markdown
[![codecov](https://codecov.io/gh/your-org/gdpr-pseudonymizer/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/gdpr-pseudonymizer)
```

**Note:** Replace `your-org` with actual GitHub organization/username.

---

## Workflow Execution Times

### Performance Targets

| Workflow | Target Time | Typical Time |
|----------|-------------|--------------|
| Unit Tests | <5 minutes | ~3-4 minutes |
| Code Quality | <2 minutes | ~1-2 minutes |
| Full CI (9 configs) | <15 minutes | ~8-12 minutes |

### Optimization Strategies

**Implemented:**
- ✅ Poetry dependency caching (`actions/cache@v3`)
- ✅ spaCy model caching (avoid 571MB re-download)
- ✅ Parallel matrix execution (9 jobs run simultaneously)
- ✅ Separate quality checks (single OS, faster than full matrix)

**Future Optimizations:**
- Conditional workflows (skip if only docs changed)
- Test splitting (parallel test execution within job)
- Docker layer caching

---

## Codecov Integration

### Setup (Admin Required)

1. Go to [codecov.io](https://codecov.io)
2. Sign in with GitHub
3. Add repository: `your-org/gdpr-pseudonymizer`
4. Install Codecov GitHub App (grants PR comment access)
5. Copy upload token (not required for public repos)

### Configuration

**File:** [.codecov.yml](.codecov.yml)

**Key Settings:**
- Project coverage target: 80%
- Patch coverage target: 80%
- Threshold: 2% drop allowed (prevents flaky failures)
- Comments on PRs: Enabled

### Viewing Coverage Reports

**On Codecov.io:**
- Project dashboard: https://codecov.io/gh/your-org/gdpr-pseudonymizer
- File browser: Click files to see line-by-line coverage
- Commit history: Track coverage over time

**Locally:**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=html
# Open htmlcov/index.html
```

---

## Development Workflow

### Standard Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test locally:**
   ```bash
   poetry run black .
   poetry run ruff check --fix .
   poetry run mypy gdpr_pseudonymizer/
   poetry run pytest
   ```

3. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push to GitHub:**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request:**
   - Navigate to GitHub repository
   - Click **New Pull Request**
   - Select your branch
   - Fill in PR description
   - Wait for CI checks to pass

6. **Address CI Failures:**
   - Check workflow logs on GitHub Actions tab
   - Fix issues locally
   - Push new commits (CI re-runs automatically)

7. **Merge PR:**
   - All status checks pass
   - Code review approved (if required)
   - Click **Merge pull request**

### Pre-Commit Checks

**Recommended:** Run all checks before committing:

```bash
# Format and fix linting
poetry run black .
poetry run ruff check --fix .

# Type check
poetry run mypy gdpr_pseudonymizer/

# Run tests
poetry run pytest --cov=gdpr_pseudonymizer
```

**Optional:** Set up pre-commit hooks to automate this.

---

## CI/CD Performance Monitoring

### GitHub Actions Insights

**View Workflow Runs:**
1. Go to **Actions** tab in GitHub repository
2. Select workflow (CI or Code Quality)
3. View run history, duration, success rate

**Workflow Run Details:**
- Click on specific run to see job details
- Expand job to see step-by-step logs
- Check duration of each step (identify bottlenecks)

### Monitoring Coverage Trends

**Codecov Dashboard:**
- View coverage over time (line chart)
- Identify files with low coverage
- Track coverage impact of PRs

---

## Troubleshooting Resources

### Logs and Debugging

**GitHub Actions Logs:**
- Navigate to **Actions** tab → Select workflow run → Expand failed job
- Download logs: Click **...** → **Download log archive**

**Local Debugging:**
```bash
# Verbose pytest output
poetry run pytest -v --tb=long

# Run single test for debugging
poetry run pytest tests/unit/test_file.py::test_function -v

# Enable debug logging
poetry run pytest --log-cli-level=DEBUG
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'gdpr_pseudonymizer'` | Package not installed | Run `poetry install` |
| `Model 'fr_core_news_lg' not found` | spaCy model not downloaded | Run `poetry run python -m spacy download fr_core_news_lg` |
| `files would be reformatted by black` | Code not formatted | Run `poetry run black .` |
| `Ruff found X errors` | Linting violations | Run `poetry run ruff check --fix .` |
| `mypy: error: Argument X has incompatible type` | Type hint mismatch | Add/fix type hints |
| `Coverage below threshold` | Insufficient tests | Write tests for uncovered code |

### Getting Help

- **GitHub Issues:** [Report CI/CD issues](https://github.com/your-org/gdpr-pseudonymizer/issues)
- **Workflow Logs:** Check GitHub Actions logs for detailed error messages
- **Poetry Docs:** [python-poetry.org](https://python-poetry.org)
- **pytest Docs:** [pytest.org](https://pytest.org)

---

## Future Enhancements

### Implemented (Epics 2-5)

- **Integration Tests:** 90+ integration tests covering validation, encryption, and hybrid detection
- **Performance Benchmarks:** pytest-benchmark tests for NFR1/NFR2 validation with JSON artifact upload (Story 5.6)
- **Entity Detection Benchmark:** Isolated NLP+regex benchmark to detect regressions in detection pipeline
- **Release Workflow:** Automated PyPI publishing via `release.yaml` on git tags
- **Accuracy Tests:** 22-test NER accuracy suite against 25-document annotated corpus

### Planned

- **Docker CI:** Add Docker image build and test
- **Security Scanning:** Add Snyk or Dependabot for vulnerability scanning
- **Pre-commit Hooks:** Automate local quality checks

### Optional Improvements

- **Test Parallelization:** Use pytest-xdist for faster test execution
- **Matrix Expansion:** Add Python 3.12 when available
- **Conditional Workflows:** Skip CI for docs-only changes
- **Codecov Graph:** Add coverage badge to README
- **Workflow Optimization:** Further reduce CI execution time

---

## References

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Poetry Docs:** https://python-poetry.org/docs/
- **pytest Docs:** https://docs.pytest.org/
- **Black Docs:** https://black.readthedocs.io/
- **Ruff Docs:** https://docs.astral.sh/ruff/
- **mypy Docs:** https://mypy.readthedocs.io/
- **Codecov Docs:** https://docs.codecov.com/

---

**Last Updated:** 2026-02-15
**Version:** 1.1
**Epic:** 1-5
**Story:** 1.3, 4.5, 5.6
