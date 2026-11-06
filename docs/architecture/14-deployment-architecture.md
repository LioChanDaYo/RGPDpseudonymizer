# 14. Deployment Architecture

### 14.1 Deployment Strategy

**Deployment Model:** **User-installed package** (not SaaS, not containerized service)

**Distribution Method:** PyPI (Python Package Index)

**Installation Command:**
```bash
pip install gdpr-pseudonymizer
```

---

### 14.2 Package Distribution

**Build Process:**

```bash
# Build distribution packages
poetry build

# Output:
# dist/gdpr_pseudonymizer-1.0.0-py3-none-any.whl
# dist/gdpr_pseudonymizer-1.0.0.tar.gz
```

**Publishing to PyPI:**

```bash
# Production PyPI
poetry publish
```

---

### 14.3 CI/CD Pipeline

**GitHub Actions Workflow:**

```yaml
name: CI - Test Matrix

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-22.04
            python-version: '3.11'
            coverage: true
          - os: ubuntu-22.04
            python-version: '3.13'
            coverage: false
          - os: macos-latest
            python-version: '3.12'
            coverage: false
          - os: windows-latest
            python-version: '3.12'
            coverage: false

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: poetry install
      - name: Run tests
        run: poetry run pytest --cov=gdpr_pseudonymizer
```

**Test Matrix Coverage:**
- **Operating Systems:** Ubuntu 22.04, macOS (latest), Windows (latest)
- **Python Versions:** 3.11 (with coverage) and 3.13 on Ubuntu, 3.12 on macOS and Windows
- **Total Configurations:** 4 (the `include` list of `.github/workflows/ci.yaml`)

---
