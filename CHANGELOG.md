# Changelog

All notable changes to the GDPR Pseudonymizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- 🪟 **Windows:** spaCy access violations possible (use Linux/macOS/WSL if encountered)
- 🐍 **Python 3.9-3.13 supported** - Python 3.14+ not supported due to dependency compatibility

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

- ✅ **553 tests passing** (86%+ coverage across all modules)
- ✅ **All quality gates pass** (Ruff linting, mypy type checking, pytest)
- ✅ **Validated on Python 3.9-3.11** (CI/CD matrix testing)

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

## [Unreleased]

Changes in development not yet released.

---

**Legend:**
- ✅ Added
- 🐛 Fixed
- 🔄 Changed
- ⚠️ Deprecated
- ❌ Removed
- 🔒 Security
