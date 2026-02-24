> 🇬🇧 **English** | 🇫🇷 [Français](README.fr.md)

# GDPR Pseudonymizer

[![PyPI version](https://img.shields.io/pypi/v/gdpr-pseudonymizer)](https://pypi.org/project/gdpr-pseudonymizer/)
[![Python versions](https://img.shields.io/pypi/pyversions/gdpr-pseudonymizer)](https://pypi.org/project/gdpr-pseudonymizer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/LioChanDaYo/RGPDpseudonymizer/actions/workflows/ci.yaml/badge.svg)](https://github.com/LioChanDaYo/RGPDpseudonymizer/actions/workflows/ci.yaml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://liochandayo.github.io/RGPDpseudonymizer/)

**AI-Assisted Pseudonymization for French Documents with Human Verification**

Transform sensitive French documents for safe AI analysis with local processing, mandatory human review, and GDPR compliance.

---

## What's New in v1.1

- **GDPR Article 17 Right to Erasure** — `delete-mapping` and `list-entities` commands for selective entity deletion with audit trail
- **Gender-aware pseudonym assignment** — 945-name French dictionary automatically matches pseudonym gender to detected name gender
- **NER accuracy doubled** — F1 score improved from 29.74% to 59.97% (+30.23pp) via annotation cleanup, regex expansion, and geography dictionary
- **PDF/DOCX input support** — Process PDF and DOCX files directly: `pip install gdpr-pseudonymizer[formats]`
- **French documentation** — Full French translation of README and user guides, MkDocs FR/EN toggle
- **Validation UI improvements** — Context cycling dot indicator, batch feedback with entity counts, CI benchmark regression gate

**Upgrade:** `pip install --upgrade gdpr-pseudonymizer`

---

## 🎯 Overview

GDPR Pseudonymizer is a **privacy-first tool** that combines AI efficiency with human accuracy to pseudonymize French text documents. Available as a **CLI tool** and a **desktop GUI** (v2.0 in development). Unlike fully automatic tools or cloud services, we prioritize **zero false negatives** and **legal defensibility** through mandatory validation workflows.

**Perfect for:**
- 🏛️ **Privacy-conscious organizations** needing GDPR-compliant AI analysis
- 🎓 **Academic researchers** with ethics board requirements
- ⚖️ **Legal/HR teams** requiring defensible pseudonymization
- 🤖 **LLM users** who want to analyze confidential documents safely

---

## ✨ Key Features

### 🔒 **Privacy-First Architecture**
- ✅ **100% local processing** - Your data never leaves your machine
- ✅ **No cloud dependencies** - Works completely offline after installation
- ✅ **Encrypted mapping tables** - AES-256-SIV encryption with PBKDF2 key derivation (210K iterations), passphrase-protected reversible pseudonymization
- ✅ **Zero telemetry** - No analytics, crash reporting, or external communication

### 🤝 **AI + Human Verification**
- ✅ **Hybrid detection** - AI pre-detects ~60% of entities (NLP + regex + geography dictionary)
- ✅ **Mandatory validation** - You review and confirm all entities (ensures 100% accuracy)
- ✅ **Fast validation UI** - Rich CLI interface with keyboard shortcuts, <2 min per document
- ✅ **Smart workflow** - Entity-by-type grouping (PERSON → ORG → LOCATION) with context display
- ✅ **Entity variant grouping** - Related forms ("Marie Dubois", "Pr. Dubois", "Dubois") merged into one validation item with "Also appears as:" display
- ✅ **Batch actions** - Confirm/reject multiple entities efficiently

### 📊 **Batch Processing**
- ✅ **Consistent pseudonyms** - Same entity = same pseudonym across 10-100+ documents
- ✅ **Compositional matching** - "Marie Dubois" → "Leia Organa", "Marie" alone → "Leia"
- ✅ **Smart name handling** - Title stripping ("Dr. Marie Dubois" = "Marie Dubois"), compound names ("Jean-Pierre" treated as atomic)
- ✅ **Selective entity processing** - `--entity-types` flag to filter by type (e.g., `--entity-types PERSON,LOCATION`)
- ✅ **50%+ time savings** vs manual redaction (AI pre-detection + validation)

### 🎭 **Themed Pseudonyms**
- ✅ **Readable output** - Star Wars, LOTR, or generic French names
- ✅ **Maintains context** - LLM analysis preserves 85% document utility (validated: 4.27/5.0)
- ✅ **Gender-aware** - Auto-detects French first name gender from 945-name dictionary and assigns gender-matched pseudonyms (female names → female pseudonyms, male names → male pseudonyms)
- ✅ **Full entity support** - PERSON, LOCATION, and ORGANIZATION pseudonyms for all themes

---

## 🚀 Quick Start

**Status:** 🎉 **v1.1.0** (February 2026)

### Realistic Expectations for v1.1

**What v1.1 delivers:**
- 🤖 **AI-assisted detection** — Hybrid NLP + regex detects ~60% of entities automatically (F1 59.97%)
- ✅ **Mandatory human verification** — You review and confirm all entities (2-3 min per document)
- 🔒 **100% accuracy guarantee** — Human validation ensures zero false negatives
- ⚡ **50%+ faster than manual** — Pre-detection saves time vs pure manual redaction
- 🗑️ **GDPR Article 17 erasure** — Selectively delete entity mappings with audit trail
- 📄 **PDF/DOCX support** — Process PDF and DOCX files directly (optional extras)
- 🇫🇷 **French documentation** — Full French translation of docs and user guides

**What v1.1 does NOT deliver:**
- ❌ Fully automatic "set and forget" processing
- ❌ 85%+ AI accuracy (current: ~60% F1 with hybrid approach)
- ❌ Optional validation mode (validation is mandatory)

### Roadmap

**v1.0 (MVP - Q1 2026):** AI-assisted CLI with mandatory validation
- Target: Privacy-conscious early adopters who value human oversight
- 100% local processing, encrypted mapping tables, audit trails

**v1.1 (Q1 2026) — CURRENT RELEASE:**
- ✅ GDPR Right to Erasure: selective entity deletion (`delete-mapping` command, Article 17)
- ✅ Gender-aware pseudonym assignment for French names (945-name dictionary)
- ✅ NER accuracy improvements: F1 29.74% → 59.97% (+30.23pp)
- ✅ French documentation translation (MkDocs i18n, 6 docs translated)
- ✅ PDF/DOCX input format support (optional extras, text extraction)
- ✅ CLI polish & minor enhancements (context cycling indicator, batch feedback, CI benchmarks)

**v2.0 (Q3-Q4 2026):** GUI & broader accessibility
- Desktop GUI wrapping CLI core (drag-and-drop, visual entity review)
- Standalone executables (.exe for Windows, .app for macOS) — no Python required
- ✅ French-first UI with i18n architecture (multi-language ready) — **implemented in Story 6.6**
- WCAG AA accessibility for professional/academic contexts
- Target: Non-technical users (HR, legal, compliance teams)

**v3.0 (2027+):** NLP accuracy & automation
- Fine-tuned French NER model (70-85% F1 target, up from ~60%)
- Optional `--no-validate` flag for high-confidence workflows
- Confidence-based auto-processing (85%+ F1 target)
- Multi-language support (English, Spanish, German)

---

## ⚙️ Installation

See [Installation Guide](https://liochandayo.github.io/RGPDpseudonymizer/installation/) for detailed platform-specific instructions.

### Prerequisites
- **Python 3.10, 3.11, or 3.12** (validated in CI/CD — 3.13+ not yet tested)

### Install from PyPI (Recommended)

```bash
pip install gdpr-pseudonymizer

# Verify installation
gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> python -m spacy download fr_core_news_lg
> ```

### Install from Source (Developer)

```bash
# Clone repository
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer

# Install dependencies via Poetry
pip install poetry>=1.7.0
poetry install

# Verify installation
poetry run gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> poetry run python -m spacy download fr_core_news_lg
> ```

### Quick Test

```bash
# Test on sample document
echo "Marie Dubois travaille à Paris pour Acme SA." > test.txt
gdpr-pseudo process test.txt

# Or specify custom output file
gdpr-pseudo process test.txt -o output.txt
```

Expected output: "Leia Organa travaille à Coruscant pour Rebel Alliance."

### Configuration File (Optional)

Generate a config template to customize default settings:

```bash
# Generate .gdpr-pseudo.yaml template in current directory
poetry run gdpr-pseudo config --init

# View current effective configuration
poetry run gdpr-pseudo config
```

Example `.gdpr-pseudo.yaml`:
```yaml
database:
  path: mappings.db

pseudonymization:
  theme: star_wars    # neutral, star_wars, lotr
  model: spacy

batch:
  workers: 4          # 1-8 (use 1 for interactive validation)
  output_dir: null

logging:
  level: INFO
```

**Note:** Passphrase is never stored in config files (security). Use `GDPR_PSEUDO_PASSPHRASE` env var or interactive prompt. Minimum 12 characters required (NFR12).

---

## 📖 Documentation

**Documentation Site:** [https://liochandayo.github.io/RGPDpseudonymizer/](https://liochandayo.github.io/RGPDpseudonymizer/)

**For Users:**
- 📘 [Installation Guide](docs/installation.md) - Platform-specific installation instructions
- 📗 [Usage Tutorial](docs/tutorial.md) - Step-by-step usage tutorials
- 📕 [CLI Reference](docs/CLI-REFERENCE.md) - Complete command documentation
- 📕 [Methodology & Academic Citation](docs/methodology.md) - Technical approach and GDPR compliance
- ❓ [FAQ](docs/faq.md) - Common questions and answers
- 🔧 [Troubleshooting](docs/troubleshooting.md) - Error reference and solutions

**For Developers:**
- 📚 [API Reference](docs/api-reference.md) - Module documentation and extension points
- 🏗️ [Architecture Documentation](docs/architecture/) - Technical design
- 📊 [NLP Benchmark Report](docs/nlp-benchmark-report.md) - NER accuracy analysis
- 📊 [Performance Report](docs/qa/performance-stability-report.md) - NFR performance validation results

**For Stakeholders:**
- 🎨 [Positioning & Messaging](docs/positioning-messaging-v2-assisted.md)
- 📋 [Deliverables Summary](docs/DELIVERABLES-SUMMARY-2026-01-16.md)

---

## 🌐 Language Support

The GUI and CLI are available in **French** (default) and **English**, with live language switching.

### GUI Language Switching

Select your language in **Settings > Appearance > Language**. The change takes effect immediately — no restart required.

### CLI Language

```bash
# French help (default on French systems)
gdpr-pseudo --lang fr --help

# English help (default on non-French systems)
gdpr-pseudo --lang en --help

# Via environment variable
GDPR_PSEUDO_LANG=fr gdpr-pseudo --help
```

**Language detection priority:**
1. `--lang` flag (explicit)
2. `GDPR_PSEUDO_LANG` environment variable
3. System locale auto-detection
4. English (CLI default) / French (GUI default)

---

## 🔬 Technical Details

### NLP Library Selection (Story 1.2 - Completed)

After comprehensive benchmarking on 25 French interview/business documents (1,737 annotated entities):

| Approach | F1 Score | Precision | Recall | Notes |
|----------|----------|-----------|--------|-------|
| **spaCy only** `fr_core_news_lg` | 29.5% | 27.0% | 32.7% | Story 1.2 baseline |
| **Hybrid** (spaCy + regex) | 59.97% | 48.17% | 79.45% | Story 5.3 (current) |

**Accuracy trajectory:** spaCy-only baseline → hybrid approach with annotation cleanup, expanded regex patterns, and French geography dictionary doubled F1 score. PERSON recall reached 82.93%.

**Approved Solution:**
- ✅ **Hybrid approach** (NLP + regex + geography dictionary) achieves ~60% F1
- ✅ **Mandatory validation** ensures 100% final accuracy
- 📅 **Fine-tuning** deferred to v3.0 (70-85% F1 target, requires training data from v1.x/v2.x user validations)

See full analysis: [docs/qa/ner-accuracy-report.md](docs/qa/ner-accuracy-report.md) | Historical baseline: [docs/nlp-benchmark-report.md](docs/nlp-benchmark-report.md)

### Validation Workflow (Story 1.7 - Complete)

The validation UI provides an intuitive keyboard-driven interface for reviewing detected entities:

**Features:**
- ✅ **Entity-by-type grouping** - Review PERSON → ORG → LOCATION in logical order
- ✅ **Context display** - See 10 words before/after each entity with highlighting
- ✅ **Confidence scores** - Color-coded confidence from spaCy NER (green >80%, yellow 60-80%, red <60%)
- ✅ **Keyboard shortcuts** - Single-key actions: [Space] Confirm, [R] Reject, [E] Modify, [A] Add, [C] Change pseudonym
- ✅ **Batch operations** - Accept/reject all entities of a type at once (Shift+A/R) with entity count feedback
- ✅ **Context cycling indicator** - Dot indicator (`● ○ ○ ○ ○`) shows current context position; `[Press X to cycle]` hint improves discoverability
- ✅ **Help overlay** - Press [H] for full command reference
- ✅ **Performance** - <2 minutes for typical 20-30 entity documents

**Workflow Steps:**
1. Summary screen (entity counts by type)
2. Review entities by type with context
3. Flag ambiguous entities for careful review
4. Final confirmation with summary of changes
5. Process document with validated entities

**Deduplication Feature (Story 1.9):** Duplicate entities grouped together - validate once, apply to all occurrences (66% time reduction for large docs)

**Entity Variant Grouping (Story 4.6):** Related entity forms automatically merged into single validation items. "Marie Dubois", "Pr. Dubois", and "Dubois" appear as one item with "Also appears as:" showing variant forms. Prevents Union-Find transitive bridging for ambiguous surnames shared by different people.

---

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.10-3.12 | Validated in CI/CD (3.13+ not yet tested) |
| **NLP Library** | spaCy | 3.8.0 | French entity detection (fr_core_news_lg) |
| **CLI Framework** | Typer | 0.9+ | Command-line interface |
| **Database** | SQLite | 3.35+ | Local mapping table storage with WAL mode |
| **Encryption** | cryptography (AESSIV) | 44.0+ | AES-256-SIV encryption for sensitive fields (PBKDF2 key derivation, passphrase-protected) |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction and session management |
| **Desktop GUI** | PySide6 | 6.7+ | Desktop application (optional: `pip install gdpr-pseudonymizer[gui]`) |
| **Validation UI** | rich | 13.7+ | Interactive CLI entity review |
| **Keyboard Input** | readchar | 4.2+ | Single-keypress capture for validation UI |
| **Testing** | pytest | 7.4+ | Unit & integration testing |
| **CI/CD** | GitHub Actions | N/A | Automated testing (Windows/Mac/Linux) |

---

## 🤔 Why AI-Assisted Instead of Automatic?

**Short answer:** Privacy and compliance require human oversight.

**Long answer:**
1. **GDPR defensibility** - Human verification provides legal audit trail
2. **Zero false negatives** - AI misses entities, humans catch them (100% coverage)
3. **Current NLP limitations** - French models on interview/business docs: 29.5% F1 out-of-box (hybrid approach reaches ~60%)
4. **Better than alternatives:**
   - ✅ **vs Manual redaction:** 50%+ faster (AI pre-detection)
   - ✅ **vs Cloud services:** 100% local processing (no data leakage)
   - ✅ **vs Fully automatic tools:** 100% accuracy (human verification)

**User Perspective:**
> "I WANT human review for compliance reasons. The AI saves me time by pre-flagging entities, but I control the final decision." - Compliance Officer

---

## 🎯 Use Cases

### 1. **Research Ethics Compliance**
**Scenario:** Academic researcher with 50 interview transcripts needing IRB approval

**Without GDPR Pseudonymizer:**
- ❌ Manual redaction: 16-25 hours
- ❌ Destroys document coherence for analysis
- ❌ Error-prone (human fatigue)

**With GDPR Pseudonymizer:**
- ✅ AI pre-detection: ~30 min processing
- ✅ Human validation: ~90 min review (50 docs × ~2 min each)
- ✅ Total: **2-3 hours** (85%+ time savings)
- ✅ Audit trail for ethics board

---

### 2. **HR Document Analysis**
**Scenario:** HR team analyzing employee feedback with ChatGPT

**Without GDPR Pseudonymizer:**
- ❌ Can't use ChatGPT (GDPR violation - employee names exposed)
- ❌ Manual analysis only (slow, limited insights)

**With GDPR Pseudonymizer:**
- ✅ Pseudonymize locally (employee names → pseudonyms)
- ✅ Send to ChatGPT safely (no personal data exposed)
- ✅ Get AI insights while staying GDPR-compliant

---

### 3. **Legal Document Preparation**
**Scenario:** Law firm preparing case materials for AI legal research

**Without GDPR Pseudonymizer:**
- ❌ Cloud pseudonymization service (third-party risk)
- ❌ Manual redaction (expensive billable hours)

**With GDPR Pseudonymizer:**
- ✅ 100% local processing (client confidentiality)
- ✅ Human-verified accuracy (legal defensibility)
- ✅ Reversible mappings (can de-pseudonymize if needed)

---

## ⚖️ GDPR Compliance

### How GDPR Pseudonymizer Supports Compliance

| GDPR Requirement | Implementation |
|------------------|----------------|
| **Art. 25 - Data Protection by Design** | Local processing, no cloud dependencies, encrypted storage |
| **Art. 30 - Processing Records** | Comprehensive audit logs (Story 2.5): operations table tracks timestamp, files processed, entity count, model version, theme, success/failure, processing time; JSON/CSV export for compliance reporting |
| **Art. 32 - Security Measures** | AES-256-SIV encryption with PBKDF2 key derivation (210,000 iterations), passphrase-protected storage, column-level encryption for sensitive fields |
| **Art. 35 - Privacy Impact Assessment** | Transparent methodology, cite-able approach for DPIA documentation |
| **Recital 26 - Pseudonymization** | Consistent pseudonym mapping, reversibility with passphrase |

### What Pseudonymization Means (Legally)

**According to GDPR Article 4(5):**
> "Pseudonymization means the processing of personal data in such a manner that the personal data can no longer be attributed to a specific data subject **without the use of additional information**, provided that such additional information is kept separately."

**GDPR Pseudonymizer approach:**
- ✅ **Personal data replaced:** Names, locations, organizations → pseudonyms
- ✅ **Separate storage:** Mapping table encrypted with passphrase (separate from documents)
- ✅ **Reversibility:** Authorized users can de-pseudonymize with passphrase
- ⚠️ **Note:** Pseudonymization reduces risk but **does NOT make data anonymous**

**Recommendation:** Consult your Data Protection Officer (DPO) for specific compliance guidance.

---

## 🛠️ Development Status

**Epics 1-5 Complete** — v1.1.0 (February 2026). **Epic 6 in progress** — v2.0 Desktop GUI.

- ✅ **Epic 1:** Foundation & NLP Validation (9 stories) — spaCy integration, validation UI, hybrid detection, entity deduplication
- ✅ **Epic 2:** Core Pseudonymization Engine (9 stories) — pseudonym libraries, encryption, audit logging, batch processing, GDPR 1:1 mapping
- ✅ **Epic 3:** CLI Interface & Batch Processing (7 stories) — 8 CLI commands, progress reporting, config files, parallel batch, UX polish
- ✅ **Epic 4:** Launch Readiness (8 stories) — LLM utility validation, cross-platform testing, documentation, NER accuracy suite, performance validation, beta feedback integration, codebase refactoring, launch preparation
- ✅ **Epic 5:** Quick Wins & GDPR Compliance (7 stories) — GDPR Article 17 erasure, gender-aware pseudonyms, NER accuracy improvements (F1 29.74% → 59.97%), French documentation translation, PDF/DOCX support, CLI polish & benchmarks, v1.1 release
- 🚧 **Epic 6:** v2.0 Desktop GUI & Broader Accessibility (9 stories) — PySide6 desktop application, visual entity validation, batch GUI, i18n, WCAG AA, standalone executables
  - ✅ Story 6.1: UX Architecture & GUI Framework Selection
  - ✅ Story 6.2: GUI Application Foundation (main window, theming, home screen, settings, 77 GUI tests)
  - ✅ Story 6.3: Document Processing Workflow (passphrase dialog, processing worker, results screen, 45 new GUI tests)
  - ✅ Story 6.4: Visual Entity Validation Interface (entity editor, entity panel, validation state with undo/redo, 72 new GUI tests)
  - ✅ Story 6.5: Batch Processing & Configuration Management (batch screen, database management, settings enhancements, 40 new tests)
  - ✅ Story 6.6: Internationalization & French UI (dual-track i18n: Qt Linguist + gettext, 267 GUI strings, ~50 CLI strings, live language switching, 53 new tests)
- **Total:** 46 stories, 1418+ tests, 86%+ coverage, all quality gates green

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- Bug reports and feature requests
- Development setup and code quality requirements
- PR process and commit message format

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

---

## 📧 Contact & Support

**Project Lead:** Lionel Deveaux - [@LioChanDaYo](https://github.com/LioChanDaYo)

**For questions and support:**
- 💬 [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions) — General questions, use cases
- 🐛 [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues) — Bug reports, feature requests
- 📖 [SUPPORT.md](SUPPORT.md) — Full support process and self-help checklist

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

**Built with:**
- [spaCy](https://spacy.io/) - Industrial-strength NLP library
- [Typer](https://typer.tiangolo.com/) - Modern CLI framework
- [rich](https://rich.readthedocs.io/) - Beautiful CLI formatting

**Inspired by:**
- GDPR privacy-by-design principles
- Academic research ethics requirements
- Real-world need for safe AI document analysis

**Methodology:**
- Developed using [BMAD-METHOD™](https://bmad.ai) framework
- Interactive elicitation and multi-perspective validation

---

## ⚠️ Disclaimer

**GDPR Pseudonymizer is a tool to assist with GDPR compliance. It does NOT provide legal advice.**

**Important notes:**
- ⚠️ Pseudonymization reduces risk but is NOT anonymization
- ⚠️ You remain the data controller under GDPR
- ⚠️ Consult your DPO or legal counsel for compliance guidance
- ⚠️ Human validation is MANDATORY - do not skip review steps
- ⚠️ Test thoroughly before production use

**Current limitations:**
- AI detection: ~60% F1 baseline (not 85%+)
- Validation required for ALL documents (not optional)
- French documents only (English, Spanish, etc. in future versions)
- Text-based formats: .txt, .md, .pdf, .docx (PDF/DOCX require optional extras: `pip install gdpr-pseudonymizer[formats]`)

---

## 🧪 Testing

### Running Tests

The project includes comprehensive unit and integration tests covering the validation workflow, NLP detection, and core functionality.

**Note for Windows users:** Due to known spaCy access violations on Windows ([spaCy issue #12659](https://github.com/explosion/spaCy/issues/12659)), Windows CI runs non-spaCy tests only. Full test suite runs on Linux/macOS.

**Run all tests:**
```bash
poetry run pytest -v
```

**Run only unit tests:**
```bash
poetry run pytest tests/unit/ -v
```

**Run only integration tests:**
```bash
poetry run pytest tests/integration/ -v
```

**Run accuracy validation tests (requires spaCy model):**
```bash
poetry run pytest tests/accuracy/ -v -m accuracy -s
```

**Run performance & stability tests (requires spaCy model):**
```bash
# All performance tests (stability, memory, startup, stress)
poetry run pytest tests/performance/ -v -s -p no:benchmark --timeout=600

# Benchmark tests only (pytest-benchmark)
poetry run pytest tests/performance/ --benchmark-only -v -s
```

**Run with coverage report:**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=term-missing --cov-report=html
```

**Run validation workflow integration tests specifically:**
```bash
poetry run pytest tests/integration/test_validation_workflow_integration.py -v
```

**Run quality checks:**
```bash
# Code formatting check
poetry run black --check gdpr_pseudonymizer tests

# Format code automatically
poetry run black gdpr_pseudonymizer tests

# Linting check
poetry run ruff check gdpr_pseudonymizer tests

# Type checking
poetry run mypy gdpr_pseudonymizer
```

**Run Windows-safe tests only (excludes spaCy-dependent tests):**
```bash
# Run non-spaCy unit tests (follows Windows CI pattern)
poetry run pytest tests/unit/test_benchmark_nlp.py tests/unit/test_config_manager.py tests/unit/test_data_models.py tests/unit/test_file_handler.py tests/unit/test_logger.py tests/unit/test_naive_processor.py tests/unit/test_name_dictionary.py tests/unit/test_process_command.py tests/unit/test_project_config.py tests/unit/test_regex_matcher.py tests/unit/test_validation_models.py tests/unit/test_validation_stub.py -v

# Run validation workflow integration tests (Windows-safe)
poetry run pytest tests/integration/test_validation_workflow_integration.py -v
```

### Test Coverage

- **Unit tests:** 1030+ tests covering validation models, UI components, encryption, database operations, audit logging, progress tracking, gender detection, context cycling indicator, i18n (GUI + CLI), and core logic
- **Integration tests:** 90 tests for end-to-end workflows including validation (Story 2.0.1), encrypted database operations (Story 2.4), compositional logic, and hybrid detection
- **Accuracy tests:** 22 tests validating NER accuracy against 25-document ground-truth corpus (Story 4.4)
- **Performance tests:** 19 tests validating all NFR targets — single-document benchmarks (NFR1), entity-detection benchmarks, batch performance (NFR2), memory profiling (NFR4), startup time (NFR5), stability/error rate (NFR6), stress testing (Story 4.5)
- **Current coverage:** 86%+ across all modules (100% for progress module, 91.41% for AuditRepository)
- **Total tests:** 1418+ tests
- **CI/CD:** Tests run on Python 3.10-3.12 across Windows, macOS, and Linux
- **Quality gates:** All pass (Black, Ruff, mypy, pytest)

### Key Integration Test Scenarios

The integration test suite covers:

**Validation Workflow (19 tests):**
- ✅ Full workflow: entity detection → summary → review → confirmation
- ✅ User actions: confirm (Space), reject (R), modify (E), add entity (A), change pseudonym (C), context cycling (X)
- ✅ State transitions: PENDING → CONFIRMED/REJECTED/MODIFIED
- ✅ Entity deduplication with grouped review
- ✅ Edge cases: empty documents, large documents (320+ entities), Ctrl+C interruption, invalid input
- ✅ Batch operations: Accept All Type (Shift+A), Reject All Type (Shift+R) with confirmation prompts
- ✅ Mock user input: Full simulation of keyboard interactions and prompts

**Encrypted Database (9 tests):**
- ✅ End-to-end workflow: init → open → save → query → close
- ✅ Cross-session consistency: Same passphrase retrieves same data
- ✅ Idempotency: Multiple queries return same results
- ✅ Encrypted data at rest: Sensitive fields stored encrypted in SQLite
- ✅ Compositional logic integration: Encrypted component queries
- ✅ Repository integration: All repositories (mapping, audit, metadata) work with encrypted session
- ✅ Concurrent reads: WAL mode enables multiple readers
- ✅ Database indexes: Query performance optimization verified
- ✅ Batch save rollback: Transaction integrity on errors

---

## 📊 Project Metrics (As of 2026-02-20)

| Metric | Value | Status |
|--------|-------|--------|
| **Development Progress** | v2.0-dev | 🚧 Epic 6 in progress (Stories 6.1-6.6 complete) |
| **Stories Complete** | 46 (Epic 1-5 + 6.1-6.6) | ✅ Epics 1-5, 🚧 Epic 6 |
| **LLM Utility (NFR10)** | 4.27/5.0 (85.4%) | ✅ PASSED (threshold: 80%) |
| **Installation Success (NFR3)** | 87.5% (7/8 platforms) | ✅ PASSED (threshold: 85%) |
| **First Pseudonymization (NFR14)** | 100% within 30 min | ✅ PASSED (threshold: 80%) |
| **Critical Bugs Found** | 1 (Story 2.8) | ✅ RESOLVED - Epic 3 Unblocked |
| **Test Corpus Size** | 25 docs, 1,737 entities | ✅ Complete (post-cleanup) |
| **NLP Accuracy (Baseline)** | 29.5% F1 (spaCy only) | ✅ Measured (Story 1.2) |
| **Hybrid Accuracy (NLP+Regex)** | 59.97% F1 (+30.23pp vs baseline) | ✅ Story 5.3 Complete |
| **Final Accuracy (AI+Human)** | 100% (validated) | 🎯 By Design |
| **Pseudonym Libraries** | 3 themes (2,426 names + 240 locations + 588 orgs) | ✅ Stories 2.1, 3.0, 4.6 Complete |
| **Compositional Matching** | Operational (component reuse + title stripping + compound names) | ✅ Stories 2.2, 2.3 Complete |
| **Batch Processing** | Architecture validated (multiprocessing.Pool, 1.17x-2.5x speedup) | ✅ Story 2.7 Complete |
| **Encrypted Storage** | AES-256-SIV with passphrase protection (PBKDF2 210K iterations) | ✅ Story 2.4 Complete |
| **Audit Logging** | GDPR Article 30 compliance (operations table + JSON/CSV export) | ✅ Story 2.5 Complete |
| **Validation UI** | Operational with deduplication | ✅ Stories 1.7, 1.9 Complete |
| **Validation Time** | <2 min (20-30 entities), <5 min (100 entities) | ✅ Targets Met |
| **Single-Doc Performance (NFR1)** | ~6s mean for 3.5K words | ✅ PASSED (<30s threshold, 80% headroom) |
| **Batch Performance (NFR2)** | ~5 min for 50 docs | ✅ PASSED (<30min threshold, 83% headroom) |
| **Memory Usage (NFR4)** | ~1 GB Python-tracked peak | ✅ PASSED (<8GB threshold) |
| **CLI Startup (NFR5)** | 0.56s (help), 6.0s (cold start w/ model) | ✅ PASSED (<5s for CLI startup) |
| **Error Rate (NFR6)** | ~0% unexpected errors | ✅ PASSED (<10% threshold) |
| **Test Coverage** | 1418+ tests (incl. 301 GUI), 86%+ coverage | ✅ All Quality Checks Pass |
| **Quality Gates** | Ruff, mypy, pytest | ✅ All Pass (0 issues) |
| **GUI/CLI Languages** | French (default), English | 🌐 Live switching (Story 6.6) |
| **Supported Document Languages** | French | 🇫🇷 v1.0 only |
| **Supported Formats** | .txt, .md, .pdf, .docx | 📝 PDF/DOCX via optional extras |

---

## 🔗 Quick Links

- 📘 [Full PRD](docs/.ignore/prd.md) - Complete product requirements
- 📊 [Benchmark Report](docs/nlp-benchmark-report.md) - NLP accuracy analysis
- 🎨 [Positioning Strategy](docs/positioning-messaging-v2-assisted.md) - Marketing & messaging
- 🏗️ [Architecture Docs](docs/architecture/) - Technical design
- 📋 [Approval Checklist](docs/PM-APPROVAL-CHECKLIST.md) - PM decision tracker

---

**Last Updated:** 2026-02-23 (v2.0-dev — Epic 6 Story 6.6 complete: internationalization & French UI, dual-track i18n with live language switching, 301 GUI tests, 1418+ total tests)
