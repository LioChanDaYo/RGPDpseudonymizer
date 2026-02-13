# Changelog

All notable changes to the GDPR Pseudonymizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **GDPR Right to Erasure** (Story 5.1) — `delete-mapping` command for GDPR Article 17 compliance. Delete specific entity mappings by name or UUID with passphrase verification, confirmation prompt, and ERASURE audit log entry. New `list-entities` command for erasure workflow (shows entity ID, type, pseudonym, first seen date). Optional `--reason` flag for documenting erasure rationale. `--force` flag to skip confirmation in scripted workflows.
- **Gender-aware pseudonym assignment** (Story 5.2) — Automatically detects French first name gender from a 945-name dictionary (470 male, 457 female, 18 ambiguous) and assigns gender-matched pseudonyms. Female names get female pseudonyms, male names get male pseudonyms, and ambiguous/unknown names fall back to the combined list. Supports compound names (e.g., "Marie-Claire" detected as female via first component).
- **GenderDetector module** (`gdpr_pseudonymizer.pseudonym.gender_detector`) — Standalone gender detection class with lazy-loaded INSEE-sourced French name dictionary.
- **Gender lookup data** (`french_gender_lookup.json`) — Built from neutral.json pseudonym library and french_names.json, licensed under Etalab Open License 2.0 (compatible with MIT).
- **NER accuracy improvements** (Story 5.3) — F1 score improved from 29.74% to 59.97% (+30.23pp) through annotation cleanup, regex pattern expansion, and French geography dictionary.
  - Ground-truth annotation cleanup: removed 118 garbage/duplicate annotations, fixed ORG/PERSON mislabeling, aligned title stripping with detection output (1,855 → 1,737 entities)
  - LastName, FirstName regex pattern for reversed name formats (e.g., "Dubois, Jean-Marc")
  - Expanded ORG detection: 18 suffixes (SA, SARL, SAS, SASU, EURL, SNC, SCM, SCI, GIE, EI, SCOP, SEL, Association, Fondation, Institut, Groupe, Consortium, Fédération) and 10 prefixes (Société, Entreprise, Cabinet, Groupe, Compagnie, Association, Fondation, Institut, Consortium, Fédération)
  - French geography dictionary: 100 cities, 18 regions, 101 departments for standalone location detection
  - PERSON recall: 34.23% → 82.93% (+48.70pp), ORG FN rate: 65.71% → 48.09% (PASS), LOCATION FN rate: 36.59% → 33.06% (improved)

---

## [1.0.6] - 2026-02-11

### Fixed

- Bundle data files (detection patterns, name dictionary, pseudonym libraries) inside the package so they are included in pip-installed wheels. Previously these files used CWD-relative paths and were missing from pip installs, causing `FileNotFoundError` on `gdpr-pseudo process`.

---

## [1.0.5] - 2026-02-11

### Added

- Auto-download spaCy model on first use — no more manual `python -m spacy download fr_core_news_lg` step required.

---

## [1.0.4] - 2026-02-11

### Fixed

- Tighten click pin to `<8.2.0` — click 8.2.x also incompatible with typer 0.9.x (`Parameter.make_metavar()` signature change). Previous pin `<8.3.0` was insufficient.

---

## [1.0.3] - 2026-02-11

### Fixed

- Pin `click` to `<8.3.0` — typer 0.9.x is incompatible with click 8.3.x, which caused `TypeError: Secondary flag is not valid for non-boolean flag` on fresh pip installs where pip resolved click to 8.3.1.

---

## [1.0.2] - 2026-02-11

### Fixed

- Remaining typer/click flag pair incompatibilities: `--continue-on-error/--stop-on-error` and `--skip-duplicates/--prompt-duplicates` custom secondary names replaced with standard `--flag/--no-flag` pattern that works across all typer versions.

---

## [1.0.1] - 2026-02-11

### Fixed

- CLI crash on newer typer/click versions: `TypeError: Secondary flag is not valid for non-boolean flag` caused by `--success-only/--failures-only` flag pair with `Optional[bool]` type. Split into two separate boolean flags.
- Release workflow missing spaCy model download, causing test failures in CI.

---

## [1.0.0] - 2026-02-11

**GDPR Pseudonymizer v1.0.0 — First Public Release**

A CLI tool for GDPR-compliant pseudonymization of French text documents using NLP-based entity detection, human-in-the-loop validation, and reversible encrypted mappings. This release completes all four MVP epics: NLP Detection & Validation (Epic 1), Pseudonymization Engine (Epic 2), CLI Polish & Batch Processing (Epic 3), and Launch Readiness (Epic 4).

**Highlights:**
- Hybrid NLP + regex entity detection for French text (PERSON, LOCATION, ORG)
- Human-in-the-loop validation UI with keyboard shortcuts and entity variant grouping
- Themed pseudonym libraries (Neutral, Star Wars, LOTR) for all entity types
- AES-256-SIV encrypted mapping tables with passphrase protection
- Batch processing with multiprocessing support
- 1077+ tests, 86%+ coverage, full CI/CD pipeline

### Added
- **Beta Feedback Integration & Bug Fixes** (Story 4.6)
  - Entity variant grouping in validation UI (FB-001)
  - Selective entity type processing via `--entity-types` flag (FB-003)
  - Expanded organization pseudonym library: 196 entries (FE-006)
- **Performance & Stability Validation** (Story 4.5)
  - NFR validation suite with automated performance benchmarks
  - All NFR targets PASS: NFR1 ~6s (<30s), NFR2 ~5min (<30min), NFR4 ~1GB (<8GB), NFR5 0.56s (<5s), NFR6 <1% (<10%)
  - Stress testing: 100-document batch, 10K+ word documents
- **NER Accuracy Comprehensive Validation** (Story 4.4)
  - 22-test automated accuracy validation suite against 25-document annotated corpus
  - Dedicated CI workflow for accuracy regression detection
- **LOCATION and ORGANIZATION pseudonym libraries** (Story 3.0)
  - 80 locations and 35+ organizations per theme (neutral, Star Wars, LOTR)
  - Collision prevention and 1:1 mapping for all entity types
- **Documentation site** deployed to GitHub Pages (Story 4.3)
- **PyPI release workflow** for automated publishing on git tags
- **Community files**: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SUPPORT.md, SECURITY.md
- **GitHub Issue Templates** for bug reports and feature requests

### Changed
- Faster `--help` display via lazy imports — ~55% import time reduction (FB-007)
- License changed from GPL-3.0 to MIT
- Version bumped from 0.1.0-alpha to 1.0.0

### Fixed
- Entity variant grouping bridging bug — ambiguous single-word names now isolated (FB-001)
- `--entity-types` filter not applied in batch mode (FB-003)

### Refactored
- **Codebase Refactoring & Technical Debt Resolution** (Story 4.6.1)
  - R1: Decoupled core/CLI layer via `ProcessingNotifier` callback protocol
  - R2: Centralized French patterns into `utils/french_patterns.py`
  - R3: Decomposed `process_document()` god method into 9 focused sub-methods
  - R4: Fixed encapsulation violations in `PseudonymManager` ABC
  - R5: Factored Union-Find into reusable `UnionFind` class
  - R6: Extracted shared CLI logic into `cli/validators.py`
  - R7: Removed dead code `SimplePseudonymManager` stub
  - R8: Centralized exceptions under `PseudonymizerError` hierarchy
  - R9: Harmonized logging to `structlog` across all modules

---

## [0.1.0-alpha] - 2026-01-30

**Release Status:** Alpha release for early feedback (not production-ready)

**Alpha Testing:** Seeking 3-5 friendly users for feedback on installation, validation UI, and output quality. Testing period: 1 week. See [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) for installation instructions.

### What's New - Epic 2 Complete

#### Core Pseudonymization Features
- ✅ **Pseudonym library system** with 3 themed libraries (neutral, Star Wars, LOTR)
- ✅ **Compositional pseudonymization logic** with component-level matching
  - "Marie Dubois" → "Leia Organa", "Marie" alone → "Leia"
  - Smart handling of partial name matches
- ✅ **French name preprocessing**
  - Title stripping (Dr., M., Mme.)
  - Compound name handling (Jean-Pierre treated as atomic)
- ✅ **Encrypted mapping table** (AES-128-CBC with passphrase protection)
  - PBKDF2 key derivation with 210K iterations
  - Idempotent processing (same document = same mappings)
- ✅ **Audit logging** (GDPR Article 30 compliance)
  - Structured JSON logs with entity types, actions, timestamps
  - Excludes sensitive data (entity values never logged)
- ✅ **Single-document pseudonymization workflow**
  - End-to-end CLI with validation UI
  - Rich terminal interface with keyboard shortcuts
- ✅ **Batch processing architecture** validated
  - Multiprocessing support for parallel document processing
  - Consistent pseudonyms across document sets

#### Critical Bug Fixes
- 🐛 **Story 2.8:** Fixed pseudonym component collision bug
  - Prevented GDPR violation where "Marie" and "Marie Dubois" could map to same pseudonym
  - Ensures strict 1:1 entity-to-pseudonym mapping (GDPR requirement)
  - 18 tests added to prevent regression

#### Validation Workflow (Epic 1)
- ✅ **Rich CLI validation UI** with keyboard shortcuts (`a`/`r`/`?`)
- ✅ **Entity deduplication** (66% time reduction for large documents)
- ✅ **Hybrid detection** (NLP + regex, 35.3% F1 accuracy, +52.2% PERSON detection)
- ✅ **Context display** with entity highlighting
- ✅ **Batch operations** (Accept/Reject All Type)

### Known Limitations

- 🇫🇷 **French language only** - No other languages supported in alpha
- 📝 **Text files only** (.txt, .md) - No PDF, DOCX, or other formats
- ✅ **Validation mandatory** - No automatic mode available (human review required for 100% accuracy)
- 🤖 **AI detection: 40-50% accuracy** - Human validation ensures 100% coverage
- 👤 **PERSON entities only have themed pseudonyms** - LOCATION and ORGANIZATION entities are detected and validated but not pseudonymized with themed names (Epic 3 planned feature - HIGH priority)
- 🪟 **Windows:** spaCy access violations possible (use Linux/macOS/WSL if encountered)
- 🐍 **Python 3.10-3.12 supported** - Python 3.13+ blocked by thinc (spaCy dependency) lacking wheels

### Installation

See [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) for detailed instructions.

**Quick start:**
```bash
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Clone and install
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install

# Install spaCy French model (~571MB)
poetry run python scripts/install_spacy_model.py

# Verify installation
poetry run gdpr-pseudo --help
```

### Testing

- ✅ **802+ tests passing** (86%+ coverage across all modules)
- ✅ **All quality gates pass** (black, ruff, mypy, pytest)
- ✅ **Validated on Python 3.10-3.12** (CI/CD matrix testing)

### Documentation

**Alpha Testing Documentation:**
- [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) - Installation guide for alpha testers
- [ALPHA-QUICKSTART.md](docs/ALPHA-QUICKSTART.md) - Quick start tutorial and validation UI walkthrough
- [ALPHA-TESTING-PROTOCOL.md](docs/ALPHA-TESTING-PROTOCOL.md) - Test scenarios and feedback survey

**Project Documentation:**
- [README.md](README.md) - Project overview and quick start
- [docs/prd/](docs/prd/) - Product requirements (Epic 1-2)
- [docs/architecture/](docs/architecture/) - Technical architecture
- [docs/stories/](docs/stories/) - Implementation stories (1.0-2.9)

### Feedback

**How to provide feedback:**
- Complete alpha feedback survey (link in onboarding email)
- Report bugs via [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues)
- Feedback via [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions)

**Feedback deadline:** 1 week after onboarding

### Next Steps

- **Epic 3:** CLI polish & batch processing (Week 11-13)
  - LOCATION and ORGANIZATION pseudonym libraries (HIGH priority)
  - Auto-accept high-confidence entities (reduce validation time)
  - Batch folder processing CLI
  - Performance optimizations
- **Epic 4:** Launch readiness & LLM validation (Week 14)
  - Documentation finalization
  - MVP launch preparation
  - Public beta release

### Contributors

Epic 2 implementation team (Stories 2.0.1 - 2.9):
- Development: James (dev agent) + Claude Sonnet 4.5
- Product Management: John (PM agent) + Claude Sonnet 4.5
- Quality Assurance: QA team
- Product Owner: Sarah

### License

MIT License - See [LICENSE](LICENSE) file for details

---

**Legend:**
- ✅ Added
- 🐛 Fixed
- 🔄 Changed
- ⚠️ Deprecated
- ❌ Removed
- 🔒 Security
