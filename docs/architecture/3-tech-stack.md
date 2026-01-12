# 3. Tech Stack

This is the **DEFINITIVE** technology selection table. All development must use these exact versions.

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Runtime** | Python | 3.9+ | Application runtime environment | Balance of modern features (type hints, asyncio) with broad platform support. 3.9 EOL Oct 2025 provides safe window for MVP. |
| **CLI Framework** | Typer | 0.9+ | Command-line interface | Excellent type hints support, automatic help generation, based on Click (mature foundation). Simpler than argparse for complex CLIs. |
| **NLP Library** | spaCy OR Stanza | spaCy 3.7+ OR Stanza 1.7+ | French NER (entity detection) | **DECISION PENDING Epic 0-1 benchmark**. spaCy preferred for speed/docs, Stanza for Stanford quality. Must achieve ≥85% F1 score. |
| **NLP Model** | fr_core_news_lg OR fr_default | spaCy 3.7 model OR Stanza 1.7 | French language model | Large model size for accuracy. Downloaded post-install (~500MB). |
| **Database** | SQLite | 3.35+ | Local data persistence | Embedded database, zero configuration, cross-platform. Python stdlib support eliminates dependency. |
| **Encryption** | cryptography (Fernet) | 41.0+ | Symmetric encryption for mappings | Python-native (no compilation), NIST-approved AES-128-CBC with HMAC. Simpler than SQLCipher, higher install success rate. |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction | Repository pattern support, migration tooling (Alembic), type-safe queries. Modern 2.0 API with async support (future-proof). |
| **Dependency Mgmt** | Poetry | 1.7+ | Development dependency management | Modern lockfile (reproducible builds), PEP 621 compliant, better resolver than pip. |
| **Code Formatter** | Black | 23.12+ | Consistent code formatting | Uncompromising formatter eliminates style debates. Industry standard for Python projects. |
| **Linter** | Ruff | 0.1+ | Fast Python linting | 10-100x faster than Pylint/Flake8, replaces multiple tools. Compatible with Black. |
| **Type Checker** | mypy | 1.7+ | Static type checking | Catch type errors before runtime, enforce type hints across codebase. Integrates with Typer/SQLAlchemy types. |
| **Testing Framework** | pytest | 7.4+ | Unit & integration testing | Fixture system, parametrization, excellent plugin ecosystem. Industry standard. |
| **Test Coverage** | pytest-cov | 4.1+ | Code coverage measurement | Coverage.py integration, ≥80% coverage target. Branch coverage tracking. |
| **Mocking** | pytest-mock | 3.12+ | Test doubles for unit tests | Wrapper around unittest.mock with pytest integration. Mock NLP models, file I/O, encryption. |
| **Performance Testing** | pytest-benchmark | 4.0+ | NFR1-2 performance validation | Measure processing time, track regressions. Validate <30s single-doc, <30min batch. |
| **CLI Testing** | click-testing (via Typer) | Included with Typer | CLI command testing | Simulate CLI invocations, capture output, test error paths. |
| **Progress Bars** | rich | 13.7+ | CLI UX enhancements | Progress bars for batch processing, formatted tables for entity review, colored error messages. |
| **Configuration** | PyYAML | 6.0+ | Config file parsing | Parse `.gdpr-pseudo.yaml` config files. Secure loader to prevent code execution. |
| **CI/CD** | GitHub Actions | N/A | Automated testing & release | Free for public repos, excellent OS matrix support (Windows/Mac/Linux), PyPI publishing integration. |
| **Documentation** | MkDocs | 1.5+ | Technical documentation | Markdown-based docs, material theme, GitHub Pages deployment. Academic methodology section. |
| **Logging** | structlog | 23.2+ | Structured logging | JSON-formatted logs, context preservation, easier audit trail analysis than stdlib logging. |
| **File Handling** | pathlib | stdlib | Cross-platform paths | Python 3.4+ stdlib, object-oriented paths, safer than os.path. |
| **Markdown Parsing** | markdown-it-py | 3.0+ | Format-aware processing (FR21) | CommonMark compliant, AST access for exclusion zones (code blocks, URLs). Pure Python (no C deps). |

**Version Strategy:**
- Specify minimum versions (e.g., `3.9+`, `1.7+`) to allow security patches
- Lock exact versions in `poetry.lock` for reproducible builds
- Update dependencies quarterly, test on CI matrix before release
- Pin major versions for stability (e.g., SQLAlchemy `2.x`, not `^2.0`)

**Critical Dependencies:**
1. **NLP Library:** Entire MVP depends on ≥85% accuracy validation
2. **cryptography:** Installation failure would block core security requirement
3. **SQLite:** Bundled with Python, but version ≥3.35 needed for modern features

**Rationale Summary:**

The stack prioritizes:
- **Python ecosystem maturity** (spaCy, pytest, Black = industry standards)
- **Installation reliability** (pure Python where possible, avoid C compilation)
- **Cross-platform compatibility** (stdlib components favored, tested on 6 OS variants)
- **Developer productivity** (Typer automates CLI boilerplate, Black eliminates formatting debates, mypy catches type errors)
- **Future-proofing** (SQLAlchemy 2.0 async support, Poetry modern packaging, Ruff next-gen linter)

**Trade-offs:**
- SQLite limits multi-user scalability (acceptable for MVP single-user focus)
- Process-based parallelism increases memory (necessary for spaCy thread-safety)
- Poetry adds learning curve vs pip (justified by lockfile reliability)

**Alternatives Rejected:**
- **Click** (CLI) → Chose Typer for better type hints
- **SQLCipher** (encryption) → Chose cryptography for easier installation
- **Pylint/Flake8** (linting) → Chose Ruff for 10-100x speed
- **Stanza** (NLP) → May choose after benchmark, but spaCy preferred for docs/speed

---
