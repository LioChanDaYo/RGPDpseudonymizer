# 13. Development Workflow

### 13.1 Local Development Setup

**Prerequisites:**
- Python 3.9+
- Git 2.30+
- 8GB RAM minimum

**Initial Setup:**

```bash
# Clone repository
git clone https://github.com/org/gdpr-pseudonymizer.git
cd gdpr-pseudonymizer

# Install dependencies via Poetry
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Download NLP models
python -m spacy download fr_core_news_lg

# Verify installation
poetry run pytest tests/unit/ -v
poetry run gdpr-pseudo --help
```

---

### 13.2 Development Commands

```bash
# Code quality
poetry run black gdpr_pseudonymizer/ tests/
poetry run ruff gdpr_pseudonymizer/ tests/
poetry run mypy gdpr_pseudonymizer/

# Testing
poetry run pytest                      # All tests
poetry run pytest tests/unit/ -v      # Unit tests only
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=html

# Performance tests
poetry run pytest tests/performance/ --benchmark-only

# Scripts
poetry run python scripts/benchmark_nlp.py --corpus tests/test_corpus/
```

---

### 13.3 Git Workflow

**Branch Naming:**
```
feature/short-description      # New features
bugfix/short-description       # Bug fixes
hotfix/short-description       # Urgent fixes
```

**Commit Message Format:**
```
<type>: <short summary> (max 50 chars)

<detailed description> (wrap at 72 chars)

Relates to: Epic X, Story X.Y
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

---
