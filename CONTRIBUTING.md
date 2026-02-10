# Contributing to GDPR Pseudonymizer

Thank you for your interest in contributing! This guide explains how to get involved.

## How to Contribute

### Reporting Bugs

1. Search [existing issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues) to avoid duplicates
2. Use the [Bug Report template](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues/new?template=bug_report.md)
3. Include: Python version, OS, steps to reproduce, expected vs actual behavior

### Requesting Features

1. Check the [project roadmap](https://liochandayo.github.io/RGPDpseudonymizer/) for planned features
2. Use the [Feature Request template](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues/new?template=feature_request.md)
3. Describe the use case and proposed solution

### Code Contributions

1. Fork the repository
2. Create a feature branch (`feature/short-description` or `bugfix/short-description`)
3. Make your changes following the standards below
4. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10-3.12
- Git 2.30+
- 8GB RAM minimum (spaCy model requires ~571MB)

### Installation

```bash
# Clone your fork
git clone https://github.com/<your-username>/RGPDpseudonymizer.git
cd RGPDpseudonymizer

# Install dependencies via Poetry
pip install poetry>=1.7.0
poetry install

# Download spaCy French model (~571MB)
poetry run python -m spacy download fr_core_news_lg

# Verify installation
poetry run gdpr-pseudo --help
poetry run pytest tests/unit/ -v
```

## Code Quality Requirements

All four checks **must pass** before submitting a PR:

```bash
# Formatting (Black)
poetry run black --check gdpr_pseudonymizer/ tests/

# Linting (Ruff)
poetry run ruff check gdpr_pseudonymizer/

# Type checking (mypy)
poetry run mypy gdpr_pseudonymizer/

# Tests (pytest)
poetry run pytest tests/ -v --timeout=120 -p no:benchmark
```

To auto-fix formatting:

```bash
poetry run black gdpr_pseudonymizer/ tests/
poetry run ruff check --fix gdpr_pseudonymizer/
```

### Coding Standards

- **Imports:** Always use absolute imports (`from gdpr_pseudonymizer.x import y`)
- **Type hints:** Required on all public functions
- **Naming:** snake_case for functions/modules, PascalCase for classes, UPPER_SNAKE_CASE for constants
- **Logging:** Use `structlog` via `get_logger()` — never log sensitive data (entity values, names, etc.)
- **Line length:** 88 characters (enforced by Black)

## Pull Request Process

### Branch Naming

```
feature/short-description      # New features
bugfix/short-description       # Bug fixes
hotfix/short-description       # Urgent fixes
```

### Commit Message Format

```
<type>: <short summary>

<detailed description>
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

### PR Checklist

- [ ] All four quality checks pass (black, ruff, mypy, pytest)
- [ ] New code has tests with adequate coverage
- [ ] No sensitive data logged or exposed
- [ ] Commit messages follow the format above
- [ ] PR description explains what and why

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## Questions?

- **General questions:** [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions)
- **Bug reports:** [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues)
- **Documentation:** [https://liochandayo.github.io/RGPDpseudonymizer/](https://liochandayo.github.io/RGPDpseudonymizer/)
