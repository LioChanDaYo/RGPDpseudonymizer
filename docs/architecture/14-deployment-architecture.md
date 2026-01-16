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
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11']

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
- **Operating Systems:** Ubuntu, macOS, Windows
- **Python Versions:** 3.9, 3.10, 3.11
- **Total Configurations:** 9 (3 OS × 3 Python versions)

---
