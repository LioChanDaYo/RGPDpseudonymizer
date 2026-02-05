# GDPR Pseudonymizer

**AI-Assisted Pseudonymization for French Documents with Human Verification**

Transform sensitive French documents for safe AI analysis with local processing, mandatory human review, and GDPR compliance.

---

## 🎯 Overview

GDPR Pseudonymizer is a **privacy-first CLI tool** that combines AI efficiency with human accuracy to pseudonymize French text documents. Unlike fully automatic tools or cloud services, we prioritize **zero false negatives** and **legal defensibility** through mandatory validation workflows.

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
- ✅ **Encrypted mapping tables** - AES-128-CBC encryption with PBKDF2 key derivation (210K iterations), passphrase-protected reversible pseudonymization
- ✅ **Zero telemetry** - No analytics, crash reporting, or external communication

### 🤝 **AI + Human Verification**
- ✅ **Hybrid detection** - AI pre-detects 40-50% of entities (NLP + regex patterns)
- ✅ **Mandatory validation** - You review and confirm all entities (ensures 100% accuracy)
- ✅ **Fast validation UI** - Rich CLI interface with keyboard shortcuts, <2 min per document
- ✅ **Smart workflow** - Entity-by-type grouping (PERSON → ORG → LOCATION) with context display
- ✅ **Batch actions** - Confirm/reject multiple entities efficiently

### 📊 **Batch Processing**
- ✅ **Consistent pseudonyms** - Same entity = same pseudonym across 10-100+ documents
- ✅ **Compositional matching** - "Marie Dubois" → "Leia Organa", "Marie" alone → "Leia"
- ✅ **Smart name handling** - Title stripping ("Dr. Marie Dubois" = "Marie Dubois"), compound names ("Jean-Pierre" treated as atomic)
- ✅ **50%+ time savings** vs manual redaction (AI pre-detection + validation)

### 🎭 **Themed Pseudonyms**
- ✅ **Readable output** - Star Wars, LOTR, or generic French names
- ✅ **Maintains context** - LLM analysis preserves ≥80% document utility
- ✅ **Gender-preserving** - When NER provides gender classification (PERSON entities)
- ✅ **Full entity support** - PERSON, LOCATION, and ORGANIZATION pseudonyms for all themes

---

## 🚀 Quick Start

**Status:** 🎉 **Alpha Release v0.1.0** - Seeking 3-5 alpha testers for feedback (see [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md))

### Current Development Stage

We're actively developing v1.0 MVP with an **AI-assisted approach**:
- ✅ **Epic 1 Complete (9/9 stories):** Foundation & NLP validation operational
  - Story 1.7: Validation UI with rich CLI interface
  - Story 1.8: Hybrid detection (35.3% improvement, +52.2% PERSON detection)
  - Story 1.9: Entity deduplication (66% time reduction for large docs)
- ✅ **Epic 2 Complete:** Core pseudonymization engine
  - Story 2.1-2.5: Pseudonym libraries, compositional logic, encryption, audit logging
  - Story 2.6-2.8: End-to-end workflow, batch processing spike, GDPR 1:1 mapping fix
  - Story 2.9: Alpha release v0.1.0 preparation
- 🔄 **Week 8-11 (Current):** Epic 3 - CLI Interface & Batch Processing
  - Story 3.0: LOCATION/ORG pseudonym libraries ✅ (themed locations + organizations for all 3 themes)
  - Story 3.1: Complete CLI command set ✅ (8 new commands, 155+ tests, 80.56% coverage)
    - Commands: init, batch, list-mappings, validate-mappings, stats, import-mappings, export, destroy-table
    - Bug fixes: LOC/ORG fallback naming, batch excludes `*_pseudonymized.*` files
  - Story 3.2: Progress reporting for large batches ✅ (live entity counts, ETA calculation, 29 tests, 100% module coverage)
  - Story 3.3: Configuration file support & parallel batch ✅ (`.gdpr-pseudo.yaml` config files, `config --init` template generation, parallel `--workers` flag, 215 tests)
- 📅 **Week 11-14:** Beta release, launch prep
- 🎯 **MVP Launch:** Week 14 (estimated Q2 2026)

### Realistic Expectations for v1.0

**What v1.0 delivers:**
- 🤖 **AI-assisted detection** - Hybrid NLP + regex detects ~40-50% of entities automatically
- ✅ **Mandatory human verification** - You review and confirm all entities (2-3 min per document)
- 🔒 **100% accuracy guarantee** - Human validation ensures zero false negatives
- ⚡ **50%+ faster than manual** - Pre-detection saves time vs pure manual redaction

**What v1.0 does NOT deliver:**
- ❌ Fully automatic "set and forget" processing
- ❌ 85%+ AI accuracy (current: 40-50% with hybrid approach)
- ❌ Optional validation mode (validation is mandatory)

### Roadmap

**v1.0 (MVP - Week 14):** AI-assisted with mandatory validation
- Target: Privacy-conscious early adopters who value human oversight

**v1.1 (Q2 2026):** Semi-automatic with optional validation
- Fine-tuned model: 70-85% F1 accuracy
- Optional `--no-validate` flag for high-confidence workflows

**v2.0 (Future):** Fully automatic with confidence thresholds
- 85%+ F1 accuracy
- Confidence-based auto-processing

---

## ⚙️ Installation

**Current status:** v0.1.0-alpha released! See [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) for detailed installation instructions.

### Prerequisites
- Python 3.9-3.11 (validated in CI/CD, Python 3.12-3.13 support planned, Python 3.14+ not supported due to spaCy compatibility)
- Poetry 1.7+

### Quick Install

```bash
# Clone repository
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer

# Install dependencies
poetry install

# Install spaCy French model (required - 571MB download)
poetry run python scripts/install_spacy_model.py
```

### Verify Installation

```bash
# Run CLI
poetry run gdpr-pseudo --help

# Test on sample document (output defaults to test_pseudonymized.txt)
echo "Marie Dubois travaille à Paris pour Acme SA." > test.txt
poetry run gdpr-pseudo process test.txt

# Or specify custom output file
poetry run gdpr-pseudo process test.txt -o output.txt
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

**For Alpha Testers:**
- 📘 [Alpha Installation Guide](docs/ALPHA-INSTALL.md) - Step-by-step installation for alpha testing
- 📗 [Alpha Quick Start](docs/ALPHA-QUICKSTART.md) - First pseudonymization tutorial and validation UI walkthrough
- 📋 [Alpha Testing Protocol](docs/ALPHA-TESTING-PROTOCOL.md) - Test scenarios and feedback survey

**For Users:**
- 📘 [Installation Guide](docs/installation.md) *(Coming in Epic 3)*
- 📗 [Usage Tutorial](docs/tutorial.md) *(Coming in Epic 3)*
- 📕 [Methodology & Academic Citation](docs/methodology.md) *(Coming in Epic 4)*
- ❓ [FAQ](docs/faq.md) *(Coming in Epic 4)*

**For Developers:**
- 🏗️ [Architecture Documentation](docs/architecture/) *(In progress)*
- 📊 [NLP Benchmark Report](docs/nlp-benchmark-report.md) *(Complete)*
- 🎯 [Product Requirements (PRD)](docs/.ignore/prd.md) *(v2.0 - Updated 2026-01-16)*

**For Stakeholders:**
- 🎨 [Positioning & Messaging](docs/positioning-messaging-v2-assisted.md)
- 📋 [Deliverables Summary](docs/DELIVERABLES-SUMMARY-2026-01-16.md)

---

## 🔬 Technical Details

### NLP Library Selection (Story 1.2 - Completed)

After comprehensive benchmarking on 25 French interview/business documents (1,855 entities):

| Library | F1 Score | Precision | Recall | Decision |
|---------|----------|-----------|--------|----------|
| **spaCy** `fr_core_news_lg` | **29.5%** | 27.0% | 32.7% | ✅ **Selected** |
| **Stanza** `fr_default` | 11.9% | 10.3% | 14.1% | ❌ Rejected |

**Why both failed 85% target:**
- Pre-trained models optimized for news text (not interview/business docs)
- Domain-specific language patterns (conversational, mixed registers)
- ORG detection catastrophic (3.8% precision = 96% false positives)

**Approved Solution:**
- ✅ **Hybrid approach** (NLP + regex) targets 40-50% F1
- ✅ **Mandatory validation** ensures 100% final accuracy
- 📅 **Fine-tuning** deferred to v1.1 (70-85% F1 target)

See full analysis: [docs/nlp-benchmark-report.md](docs/nlp-benchmark-report.md)

### Validation Workflow (Story 1.7 - Complete)

The validation UI provides an intuitive keyboard-driven interface for reviewing detected entities:

**Features:**
- ✅ **Entity-by-type grouping** - Review PERSON → ORG → LOCATION in logical order
- ✅ **Context display** - See 10 words before/after each entity with highlighting
- ✅ **Confidence scores** - Color-coded confidence from spaCy NER (green >80%, yellow 60-80%, red <60%)
- ✅ **Keyboard shortcuts** - Single-key actions: [Space] Confirm, [R] Reject, [E] Modify, [A] Add, [C] Change pseudonym
- ✅ **Batch operations** - Accept/reject all entities of a type at once (Shift+A/R)
- ✅ **Help overlay** - Press [H] for full command reference
- ✅ **Performance** - <2 minutes for typical 20-30 entity documents

**Workflow Steps:**
1. Summary screen (entity counts by type)
2. Review entities by type with context
3. Flag ambiguous entities for careful review
4. Final confirmation with summary of changes
5. Process document with validated entities

**Deduplication Feature (Story 1.9):** Duplicate entities grouped together - validate once, apply to all occurrences (66% time reduction for large docs)

---

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.9-3.11 | Validated baseline (3.12-3.13 planned, 3.14+ not supported) |
| **NLP Library** | spaCy | 3.8.0 | French entity detection (fr_core_news_lg) |
| **CLI Framework** | Typer | 0.9+ | Command-line interface |
| **Database** | SQLite | 3.35+ | Local mapping table storage with WAL mode |
| **Encryption** | cryptography (Fernet) | 41.0+ | AES-128-CBC encryption for sensitive fields (PBKDF2 key derivation, passphrase-protected) |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction and session management |
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
3. **Current NLP limitations** - French models on interview/business docs: 29.5% F1 out-of-box
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
| **Art. 32 - Security Measures** | AES-128-CBC encryption (Fernet) with PBKDF2 key derivation (210,000 iterations), passphrase-protected storage, column-level encryption for sensitive fields |
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

**Current Epic:** Epic 1 - Foundation & NLP Validation (Week 1-5/14)

### Completed ✅
- ✅ **Story 0.1-0.2:** Test corpus (25 docs, 1,855 entities) + dev environment
- ✅ **Story 1.1:** Expanded test corpus with ground truth annotations
- ✅ **Story 1.2:** NLP benchmark (spaCy selected, contingency plan approved)
- ✅ **Story 1.3:** CI/CD pipeline setup (GitHub Actions)
- ✅ **Story 1.4:** Project foundation & module structure
- ✅ **Story 1.5:** Walking skeleton - basic process command (48 tests passing)
- ✅ **Story 1.6:** NLP integration with spaCy `fr_core_news_lg` (QA gate: PASS)
- ✅ **Story 1.7:** Validation UI implementation with rich library (QA gate: PASS)
- ✅ **Story 1.8:** Hybrid detection strategy (NLP + regex) - 35.3% improvement, 52.2% PERSON detection (QA gate: PASS)
- ✅ **Story 1.9:** Entity deduplication for validation UI - 66% time reduction for large docs (QA gate: PASS)
- ✅ **Story 2.0.1:** Integration tests for validation workflow - 19 tests, 80.49% coverage, all quality gates pass (QA gate: PASS)
- ✅ **Story 2.1:** Pseudonym library system - 3 themed libraries (neutral, Star Wars, LOTR), gender-matching, exhaustion detection, 36 tests, 90.76% coverage (QA gate: PASS, Score: 98/100)
- ✅ **Story 2.2:** Compositional pseudonymization logic - Component-based matching ("Marie Dubois" → "Leia Organa", "Marie" → "Leia"), 37 tests, 94% coverage (QA gate: PASS, Score: 95/100)
- ✅ **Story 2.3:** French name preprocessing (titles + compounds) - Title stripping ("Dr. Marie Dubois" → "Marie Dubois"), compound names ("Jean-Pierre" treated as atomic), simple pseudonyms for compounds, 53 tests (31 unit + 15 unit + 7 integration), 94.64% coverage (QA gate: PASS, Score: 100/100)
- ✅ **Story 2.4:** Encrypted mapping table - Database encryption with AES-128-CBC (Fernet), passphrase protection, PBKDF2 key derivation (210,000 iterations), column-level encryption, WAL mode for concurrency, 9 integration tests (QA gate: PASS)
- ✅ **Story 2.5:** Audit logging - Comprehensive audit logs for GDPR Article 30 compliance, operations table tracks all pseudonymization operations, JSON/CSV export functionality, 32 unit tests, 91.41% coverage (QA gate: PASS, Score: 100/100)
- ✅ **Story 2.6:** Single-document pseudonymization workflow - End-to-end integration of all Epic 2 components, idempotent processing, optional `--output` parameter, 10 tests passing (3 unit + 7 integration), 6 critical bug fixes for consistent pseudonym generation across documents (QA gate: PASS, Ready for Done)
- ✅ **Story 2.7:** Batch processing scalability spike - Multiprocessing.Pool validated (1.17x speedup on small docs, 2-3x projected for 3000-word docs), mapping consistency verified, architectural validation complete, 1 critical bug discovered (pseudonym component collision - Story 2.8 created), 5 test scripts + findings document (QA gate: PASS with critical bug found)
- ✅ **Story 2.8:** Pseudonym component collision fix - Component-level collision prevention implemented in LibraryBasedPseudonymManager, `_component_mappings` dict tracks real→pseudonym component assignments, database reconstruction for backwards compatibility, 18 tests passing (13 unit + 5 integration), GDPR Article 4(5) compliance restored, Epic 3 unblocked (QA gate: PASS, Score: 92/100)
- ✅ **Story 2.9:** Alpha release preparation - Installation verification complete (Windows tested), alpha documentation created (ALPHA-INSTALL.md, ALPHA-QUICKSTART.md, ALPHA-TESTING-PROTOCOL.md), CHANGELOG.md with v0.1.0-alpha release notes, README updated to alpha status, git tag v0.1.0-alpha ready (Alpha Release: 2026-01-30)
- ✅ **Story 3.0:** LOCATION and ORGANIZATION pseudonym libraries - Extended all 3 themes with 80 locations + 35 organizations each (neutral: French cities/companies, Star Wars: planets/alliances, LOTR: Middle-earth locations/kingdoms), updated LibraryBasedPseudonymManager for atomic LOC/ORG pseudonymization, 8 new unit tests + integration tests, all ACs met (QA gate: PASS, Score: 95/100)

### Completed ✅
- ✅ **Epic 2 (Week 6-10):** Core pseudonymization engine - 9/9 stories complete, Epic 2 complete, v0.1.0-alpha released
- ✅ **Story 3.0 (Week 10):** LOCATION/ORG pseudonym libraries - Epic 3 first story, extends pseudonymization to all entity types
- ✅ **Story 3.1 (Week 10-11):** Complete CLI command set - 8 new commands (init, batch, list-mappings, validate-mappings, stats, import-mappings, export, destroy-table), 155+ tests
- ✅ **Story 3.2 (Week 11):** Progress reporting for large batches - Live entity counts, ETA calculation, rolling average, 29 tests with 100% module coverage
- ✅ **Story 3.3 (Week 11):** Configuration file support & parallel batch - `.gdpr-pseudo.yaml` config files, `config --init` template generation, parallel `--workers` flag for batch command, 215 tests

### Upcoming 📅
- **Epic 3 (Week 11-13):** CLI polish & batch processing
- **Epic 4 (Week 14):** Launch readiness & LLM validation

---

## 🤝 Contributing

**Status:** 🚧 Pre-release development - Not yet accepting contributions

Once we reach v1.0 MVP (Week 14), we'll welcome:
- 🐛 Bug reports
- 📝 Documentation improvements
- 🌍 Translations (English, Spanish, German)
- 💡 Feature suggestions

**For now:** Follow development progress via [GitHub Issues](https://github.com/yourusername/RGPDpseudonymizer/issues) and [Discussions](https://github.com/yourusername/RGPDpseudonymizer/discussions).

---

## 📧 Contact & Support

**Project Lead:** Lionel Deveaux - [@LioChanDaYo](https://github.com/LioChanDaYo)

**For questions:**
- 💬 [GitHub Discussions](https://github.com/yourusername/RGPDpseudonymizer/discussions) - General questions, use cases
- 🐛 [GitHub Issues](https://github.com/yourusername/RGPDpseudonymizer/issues) - Bug reports (post-launch)
- 📧 Email: [project-email@example.com](mailto:project-email@example.com) - Private inquiries

---

## 📜 License

**TBD** - Will be announced before v1.0 MVP launch (Week 14)

Likely: MIT or Apache 2.0 (open-source, permissive)

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

**v1.0 MVP limitations:**
- AI detection: 40-50% baseline (not 85%+)
- Validation required for ALL documents (not optional)
- French language only (English, Spanish, etc. in future versions)
- Text formats only (.txt, .md - no PDF/DOCX in v1.0)

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

- **Unit tests:** 492 tests covering validation models, UI components, encryption, database operations, audit logging, progress tracking, and core logic
- **Integration tests:** 90 tests for end-to-end workflows including validation (Story 2.0.1), encrypted database operations (Story 2.4), compositional logic, and hybrid detection
- **Current coverage:** 86%+ across all modules (100% for progress module, 91.41% for AuditRepository)
- **Total tests:** 616 tests collected (600+ passed, 12 skipped)
- **CI/CD:** Tests run on Python 3.9-3.11 across Windows, macOS, and Linux
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

## 📊 Project Metrics (As of 2026-02-03)

| Metric | Value | Status |
|--------|-------|--------|
| **Development Progress** | Week 11/14 | ✅ Epic 2 Complete + Stories 3.0-3.3 - v0.1.0-alpha Released |
| **Stories Complete** | 22 (Epic 1 + Epic 2 + Stories 3.0-3.3) | ✅ Epic 1 (9) + Epic 2 (9) + Stories 3.0, 3.1, 3.2, 3.3 |
| **Critical Bugs Found** | 1 (Story 2.8) | ✅ RESOLVED - Epic 3 Unblocked |
| **Test Corpus Size** | 25 docs, 1,855 entities | ✅ Complete |
| **NLP Accuracy (Baseline)** | 29.5% F1 (spaCy) | ✅ Measured |
| **Hybrid Accuracy (NLP+Regex)** | 35.3% F1 (+52.2% PERSON) | ✅ Story 1.8 Complete |
| **Final Accuracy (AI+Human)** | 100% (validated) | 🎯 By Design |
| **Pseudonym Libraries** | 3 themes (2,426 names + 240 locations + 105 orgs) | ✅ Stories 2.1, 3.0 Complete |
| **Compositional Matching** | Operational (component reuse + title stripping + compound names) | ✅ Stories 2.2, 2.3 Complete |
| **Batch Processing** | Architecture validated (multiprocessing.Pool, 1.17x-2.5x speedup) | ✅ Story 2.7 Complete |
| **Encrypted Storage** | AES-128-CBC with passphrase protection (PBKDF2 210K iterations) | ✅ Story 2.4 Complete |
| **Audit Logging** | GDPR Article 30 compliance (operations table + JSON/CSV export) | ✅ Story 2.5 Complete |
| **Validation UI** | Operational with deduplication | ✅ Stories 1.7, 1.9 Complete |
| **Validation Time** | <2 min (20-30 entities), <5 min (100 entities) | ✅ Targets Met |
| **Test Coverage** | 616 tests (502 unit + 114 integration), 86%+ coverage | ✅ All Quality Checks Pass |
| **Quality Gates** | Ruff, mypy, pytest | ✅ All Pass (0 issues) |
| **Supported Languages** | French | 🇫🇷 v1.0 only |
| **Supported Formats** | .txt, .md | 📝 v1.0 scope |

---

## 🔗 Quick Links

- 📘 [Full PRD](docs/.ignore/prd.md) - Complete product requirements
- 📊 [Benchmark Report](docs/nlp-benchmark-report.md) - NLP accuracy analysis
- 🎨 [Positioning Strategy](docs/positioning-messaging-v2-assisted.md) - Marketing & messaging
- 🏗️ [Architecture Docs](docs/architecture/) - Technical design
- 📋 [Approval Checklist](docs/PM-APPROVAL-CHECKLIST.md) - PM decision tracker

---

**Last Updated:** 2026-02-04 (v0.1.0-alpha released: Epic 2 complete; Stories 3.0-3.3 complete - LOCATION/ORG pseudonym libraries, complete CLI command set, progress reporting, config file support with `config --init`; Alpha documentation created; Seeking 3-5 alpha testers for feedback; 215 CLI tests, all quality gates pass)

**Current Focus:** Epic 3 development - Stories 3.0-3.3 complete (LOC/ORG pseudonym libraries, 8 CLI commands, batch progress reporting, config file support with `config --init`), Story 3.4 (CLI UX polish) next
