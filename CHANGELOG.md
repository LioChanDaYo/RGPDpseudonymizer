# Changelog

All notable changes to the GDPR Pseudonymizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- ✅ **Beta Feedback Integration & Bug Fixes** (Story 4.6)
  - **Entity variant grouping in validation UI** (FB-001): Groups related entity forms (e.g., "Marie Dubois", "Pr. Dubois", "Dubois") into a single validation item. Reduces redundant validation prompts. Shows "Also appears as:" for variant forms.
  - **Selective entity type processing** (FB-003): New `--entity-types` CLI flag for both `process` and `batch` commands. Filter entities by type (e.g., `--entity-types PERSON,LOCATION`). Valid types: PERSON, LOCATION, ORG.
  - **Expanded organization pseudonym library** (FE-006): Neutral theme expanded from 35 to 196 organization entries (101 companies, 50 agencies, 45 institutions). Supports batch processing of 50+ documents without library exhaustion.
  - New backlog item FE-014 for extended coreference resolution (v1.1+)

### Changed
- 🔄 **Faster `--help` display** (FB-007): Refactored CLI to use lazy imports — heavy dependencies (spaCy, torch, SQLAlchemy, cryptography) only loaded when commands are invoked, not during `--help`. Import time reduced ~55%.
- 🔄 **Python 3.13 CI evaluation** (FB-006): Evaluated and deferred — blocked by `thinc` (spaCy ML backend) lacking Python 3.13 wheels. CI matrix remains Python 3.10-3.12.

### Fixed
- 🐛 **Entity variant grouping bridging bug** (FB-001): Fixed Union-Find transitive bridging where a titled surname (e.g., "Mme Durand") could incorrectly merge two different people sharing the same family name (e.g., "M. Olivier Durand" and "Mme Alice Durand"). Ambiguous single-word names are now detected and isolated from Union-Find pairing.
- 🐛 **`--entity-types` filter not applied in batch mode** (FB-003): Fixed `entity_type_filter` not being forwarded to `process_document()` in batch command — affected sequential mode, parallel worker, and parallel orchestrator call sites.
- 🐛 **Deferred items documented**: FB-002 (French docs → FE-010 v1.1), FB-004 (DOCX/PDF → v1.1), FB-005 (GUI → v2.0), Python 3.14 (→ MON-005 monitoring)

---

- ✅ **Performance & Stability Validation** (Story 4.5)
  - NFR validation suite with automated performance benchmarks
  - All NFR targets PASS: NFR1 ~6s (<30s), NFR2 ~5min (<30min), NFR4 ~1GB (<8GB), NFR5 0.56s (<5s), NFR6 <1% (<10%)
  - Monitoring baselines documented: `docs/qa/monitoring-baselines-4.5.md`
  - Stress testing: 100-document batch, 10K+ word documents, concurrent processing

- ✅ **NER Accuracy Comprehensive Validation** (Story 4.4)
  - 22-test automated accuracy validation suite (`tests/accuracy/`)
  - Validates hybrid detection pipeline against 25-document annotated corpus (1,855 entities)
  - Overall metrics: F1=29.74%, Precision=25.25%, Recall=36.17%
  - Per-entity-type breakdown: PERSON F1=33.71%, LOCATION F1=37.05%, ORG F1=9.16%
  - Edge case analysis: 6 categories (compound names, titles, abbreviations, multi-word ORG, diacritics, Last/First order)
  - Confidence score analysis (83.8% entities lack confidence — spaCy limitation)
  - Regression comparison vs Epic 1 baselines (no regression, within 3% tolerance)
  - Quality report: `docs/qa/ner-accuracy-report.md`
  - Monitoring baselines review: `docs/qa/monitoring-baselines-4.4.md` (MON-001, MON-003, MON-004)
  - Dedicated CI workflow: `.github/workflows/accuracy.yaml`
  - NFR8/NFR9 targets documented as aspirational (validation mode is mitigation)
  - Backlog items FE-011/012/013 added for future NLP improvements
- ✅ **LOCATION and ORGANIZATION pseudonym libraries** (Story 3.0)
  - Added themed pseudonyms for LOCATION entities (cities, regions, planets/countries)
  - Added themed pseudonyms for ORGANIZATION entities (companies, agencies, institutions)
  - 80 locations per theme (50 cities, 20 countries/planets, 10 regions)
  - 35 organizations per theme (20 companies, 10 agencies, 5 institutions)
  - Available for all 3 themes: neutral (French), Star Wars, LOTR
  - Collision prevention and 1:1 mapping for LOC/ORG entities
  - Updated exhaustion calculation to include LOC/ORG pools

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
- Email feedback: [your-email@example.com]

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
