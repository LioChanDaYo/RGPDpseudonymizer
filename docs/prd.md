# GDPR Pseudonymizer Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Achieve ≥90% NER detection accuracy (precision and recall) on French text benchmark corpus
- Achieve ≥85% installation success rate for first-time users on target platforms
- Validate LLM utility preservation: pseudonymized documents maintain ≥80% usefulness for AI analysis
- Automate entity detection and pseudonymization with 50%+ time savings vs manual redaction for batch processing
- Provide GDPR-compliant pseudonymization with encrypted mapping tables, audit trails, and reversibility
- Enable consistent pseudonymization across document batches (10-100+ files) for corpus-level analysis
- Deliver transparent, cite-able methodology suitable for research ethics board evaluation

### Background Context

The explosion of LLM capabilities in 2024-2025 has created an urgent dilemma: organizations and researchers possess valuable documents that could benefit enormously from AI analysis, but cannot safely send them to cloud-based services due to embedded personal data and GDPR obligations. Every day, they choose between staying compliant but falling behind, or innovating but taking unacceptable privacy risks. Manual redaction doesn't scale and destroys document coherence, while cloud-based pseudonymization services require trusting third parties with confidential data.

GDPR Pseudonymizer solves this by providing a local Python CLI tool that automatically detects and replaces personal identifiers (names, locations, organizations) with consistent, readable pseudonyms—entirely on the user's infrastructure. The MVP targets **AI-forward organizations and technically-comfortable researchers** as primary users, focusing on French-language text files (.txt, .md) to validate core value propositions: trustworthy local processing, batch efficiency, and maintained document utility for LLM analysis and qualitative research. Phase 2 will expand to GUI for broader adoption. The tool prioritizes the LLM enablement use case for MVP validation while ensuring methodology meets academic rigor standards for research applications.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-11 | v1.0 | Initial PRD creation from Project Brief | John (PM) |

---

## Requirements

### Functional Requirements

**FR1:** The system shall detect personal names (persons) in French text using NER technology with ≥90% precision and recall for both entity detection and entity type classification, treating full names as composite entities (first name + last name).

**FR2:** The system shall detect location entities (cities, countries, regions) in French text using NER technology.

**FR3:** The system shall detect organization entities (companies, institutions) in French text using NER technology.

**FR4:** The system shall replace each detected entity with a consistent pseudonym throughout single documents and across document batches using compositional strict matching: when "Marie Dubois" is pseudonymized to "Leia Organa", all subsequent occurrences of "Marie Dubois" become "Leia Organa", isolated "Marie" becomes "Leia", and isolated "Dubois" becomes "Organa". Standalone name components without full name context shall be flagged for user validation when validation mode is enabled, or logged as ambiguous entities when validation is disabled.

**FR5:** The system shall handle multiple entities sharing name components by maintaining unique pseudonym assignments per complete entity: if both "Marie Dubois" and "Marie Dupont" are detected, they shall be pseudonymized to distinct full pseudonyms (e.g., "Leia Organa" and "Leia Skywalker" respectively), preserving shared first name consistency ("Marie" → "Leia") while distinguishing last names.

**FR6:** The system shall support batch processing of multiple documents (10-100+) with consistent pseudonym mapping across the entire corpus, with mapping table updates applied incrementally to ensure cross-document consistency within the batch.

**FR7:** The system shall provide an optional interactive validation mode (activated via `--validate` flag) that presents detected entities and classification results for review before pseudonymization is applied. Users may correct, add, or remove entities. Validation mode is recommended for highly sensitive documents but not required.

**FR8:** The system shall maintain a secure encrypted mapping table (SQLite with SQLCipher) storing original↔pseudonym correspondences with user-provided passphrase protection.

**FR9:** The system shall support pseudonymization reversibility by allowing authorized users to retrieve original entities from the encrypted mapping table.

**FR10:** The system shall provide themed pseudonym libraries (minimum 2-3 themes) with separate pools of ≥500 first names and ≥500 last names per theme to support compositional pseudonymization with sufficient combinations. Libraries shall include neutral/generic and optional thematic sets (e.g., Star Wars). Gender-preserving pseudonymization is recommended where NER provides gender classification.

**FR11:** The system shall gracefully handle pseudonym library exhaustion by providing clear warnings and systematic fallback naming (e.g., Person-001, Location-001).

**FR12:** The system shall log all pseudonymization operations including timestamp, files processed, entities detected, NLP model name and version, pseudonym theme selected, detection confidence scores (if available), entities modified by user (if validation mode used), and pseudonyms applied.

**FR13:** The system shall accept plain text (.txt) and Markdown (.md) file formats as input for MVP.

**FR14:** The system shall output pseudonymized documents in the same format as input files.

**FR15:** The system shall provide CLI commands: `init` (initialize mapping table), `process` (single document), `batch` (multiple documents), `list-mappings` (view correspondences), `validate-mappings` (review existing mappings without processing), `stats` (show statistics), `import-mappings` (load mappings from previous project), `export` (audit log), `destroy-table` (secure deletion).

**FR16:** The system shall perform all processing locally without network communication or external service dependencies.

**FR17:** The system shall securely delete mapping tables by overwriting data before file deletion when user executes `destroy-table` command, with mandatory user confirmation prompt (yes/no) before destruction to prevent accidental data loss.

**FR18:** The system shall disable validation mode by default (fast processing) and require explicit `--validate` flag to enable interactive review. In batch mode without validation, the system shall provide a summary report of detected entities after processing all documents.

**FR19:** The system shall implement idempotent processing: re-processing the same document shall reuse existing pseudonym mappings from the mapping table, ensuring consistency. If new entities are detected in subsequent runs, only those shall be added to the mapping table.

**FR20:** The system shall detect and handle French compound first names (e.g., "Jean-Pierre", "Marie-Claire") as single first name entities for compositional pseudonymization.

**FR21:** The system shall implement format-aware processing for Markdown files, excluding pseudonymization within URLs, code blocks (```), inline code (`), and image references.

### Non-Functional Requirements

**NFR1:** The system shall process typical documents (2000-5000 words) in <30 seconds on standard consumer hardware (8GB RAM, dual-core 2.0GHz+ CPU). Processing time excludes user interaction time when `--validate` flag is used.

**NFR2:** The system shall process batches of 50 documents in <30 minutes on standard consumer hardware. Processing time excludes user interaction time when `--validate` flag is used.

**NFR3:** The system shall achieve ≥85% installation success rate for first-time users across Windows 10/11, macOS 11+, and Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+).

**NFR4:** The system shall require maximum 8GB RAM and 2GB free disk space (including NLP models and dependencies).

**NFR5:** The system shall start up in <5 seconds after initial installation and model loading.

**NFR6:** The system shall maintain <10% crash/error rate during pseudonymization sessions.

**NFR7:** The system shall provide clear, actionable error messages that enable users to resolve issues without external support in ≥80% of error scenarios.

**NFR8:** The system shall maintain false negative rate <10% (missed sensitive entities) to ensure GDPR compliance safety.

**NFR9:** The system shall maintain false positive rate <15% (incorrectly flagged entities) to minimize user validation burden.

**NFR10:** The system shall preserve pseudonymized document utility such that LLM analysis maintains ≥80% quality compared to original documents (measured via user satisfaction surveys).

**NFR11:** The system shall operate entirely offline with zero network dependencies after initial installation and model download.

**NFR12:** The system shall implement encryption for mapping tables using industry-standard SQLCipher with user-provided passphrase (minimum 12 characters).

**NFR13:** The system shall provide comprehensive documentation including installation guide, usage tutorial, methodology description (for academic citation), FAQ, and troubleshooting guide.

**NFR14:** The system shall enable ≥80% of users to complete their first successful pseudonymization within 30 minutes including installation.

**NFR15:** The system shall support Python 3.9+ runtime environment across all target platforms.

---

## Technical Assumptions

### Repository Structure: Monorepo

The project shall use a **monorepo structure** with a single Python package for MVP. This provides:
- Simplified dependency management and versioning for early development
- Clear separation between CLI layer, core processing logic, NLP engine, and data layer
- Easy transition to component extraction if Phase 2+ requires microservices or separate GUI repository

**Rationale:** MVP scope is small enough that monorepo overhead is minimal, while providing clean module boundaries that support future refactoring.

### Service Architecture

**Single-process monolithic application** for MVP with modular internal architecture:

- **CLI Layer:** Command parsing and user interaction (Typer framework for modern type hints)
- **Core Processing Engine:** Orchestration of detection, pseudonymization, and validation workflows
- **NLP Engine:** Entity detection using spaCy with French models (selection validated in Week 0 benchmarking)
- **Data Layer:** SQLite with Python-native encryption (cryptography library) for mapping tables and audit logs
- **Pseudonym Manager:** Library loading and pseudonym assignment logic
- **Concurrency Model:** Process-based parallelism for batch processing (thread-unsafe NLP models require isolated processes)

**Rationale:** Modular monolith provides clear boundaries without deployment overhead. Concurrency model determined by spaCy's thread-safety limitations (global state in NLP models requires process isolation).

### Testing Requirements

**Incremental testing approach** with pytest framework, prioritized by sprint:

**Sprint 1 (Foundation):**
- Test infrastructure setup: pytest, coverage tooling, CI/CD pipeline (GitHub Actions)
- Labeled test corpus creation (20-30 French documents with ground truth annotations)
- Smoke tests for core modules

**Sprint 2-4 (Core Features):**
- Unit tests: Compositional name matching (FR4-5), pseudonym assignment, mapping table operations
- Integration tests: End-to-end workflows (process, batch, validation mode)
- NER accuracy benchmarking against test corpus (≥90% target)

**Sprint 5-8 (Quality & Polish):**
- Performance tests: Validate NFR1-2 (processing time thresholds)
- Markdown edge case test suite (FR21): nested code blocks, URLs with names, inline code, tables
- Error scenario catalog validation (NFR7)
- LLM utility preservation test protocol (NFR10)

**Target coverage:** ≥80% code coverage by end of Sprint 8

**Rationale:** Incremental testing prevents over-engineering early while ensuring quality foundation. Test corpus creation in Sprint 1 enables continuous accuracy validation.

### Additional Technical Assumptions and Requests

**Programming Language & Runtime:**
- **Python 3.9+** for broad compatibility and mature NLP ecosystem
- Cross-platform support: Windows 10/11, macOS 11+ (Intel & Apple Silicon), Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)

**NLP/NER Library Selection (CRITICAL - Week 0 Decision):**

**This decision MUST be validated BEFORE Epic planning begins.**

- **Primary candidate: spaCy** with `fr_core_news_lg` French model
- **Alternative: Stanza** (Stanford NLP) as fallback
- **Week 0 Benchmark Protocol:**
  - Test both libraries on 20-30 sample French documents (interview transcripts and business documents)
  - Measure precision, recall, F1 score for PERSON, LOCATION, ORG entities
  - Test compound name detection (FR20): "Jean-Pierre", "Marie-Claire"
  - Measure processing speed and memory footprint
  - **Go/No-Go Threshold:** ≥85% F1 score minimum to proceed with MVP
- **Contingency Plans if <85%:**
  - **Option A:** Hybrid approach combining NER with rule-based name detection (French name dictionaries)
  - **Option B:** Lower accuracy threshold but make validation mode (`--validate`) mandatory by default
  - **Option C:** Pivot to English language market where NER models have higher accuracy (requires Brief revision)
- **Post-Selection:** Document chosen library, model version, and benchmark results in architecture documentation

**Concurrency Model Decision (Resolved):**

**Process-based parallelism** for batch processing using Python's `multiprocessing` module:
- spaCy models use global state and are NOT thread-safe
- Each document in batch processed by isolated worker process
- Main process manages task queue and aggregates results
- Worker pool size: min(cpu_count, 4) to balance parallelism with memory constraints (8GB RAM target)

**Data Storage:**

**SQLite with Python-native encryption** (cryptography library's Fernet symmetric encryption):

- **Schema design:**
  - `entities` table: `id`, `entity_type` (PERSON/LOCATION/ORG), `first_name`, `last_name`, `full_name`, `pseudonym_first`, `pseudonym_last`, `pseudonym_full`, `first_seen_timestamp`, `gender` (optional), `confidence_score`
  - `operations` table: `id`, `timestamp`, `operation_type`, `files_processed`, `model_name`, `model_version`, `theme_selected`, `user_modifications`, `entity_count`
  - `metadata` table: `key`, `value` (stores encryption metadata, schema version, creation date)

- **Encryption Approach:**
  - User passphrase → PBKDF2 key derivation → Fernet encryption key
  - Encrypt sensitive columns (`first_name`, `last_name`, `full_name`, `pseudonym_*`) individually
  - Store salt and KDF parameters in `metadata` table
  - Passphrase validation on database open

- **Rationale for Change from SQLCipher:**
  - Eliminates cross-platform installation risk (SQLCipher requires platform-specific compilation)
  - Python-native solution improves NFR3 (85% installation success rate)
  - Provides equivalent security with simpler installation
  - Column-level encryption offers granular control vs full-database encryption

**CLI Framework:**
- **Typer** (modern Python CLI framework with excellent type hints support)
- Command structure follows FR15: `init`, `process`, `batch`, `list-mappings`, `validate-mappings`, `stats`, `import-mappings`, `export`, `destroy-table`
- Configuration file support: Optional `.gdpr-pseudo.yaml` in home directory or project root for default settings (theme, validation mode, output directory)

**Pseudonym Data Management:**

**Sourcing Strategy:**
- **Neutral/Generic theme:** French National Statistics Institute (INSEE) most common first/last names (public domain)
- **Star Wars theme:** Curated list from public fan wikis + generated combinations (verify fair use)
- **LOTR theme:** Curated from Tolkien Gateway + generated combinations (verify copyright status)
- **Legal review:** Defer to Phase 2 for commercial use; MVP is open-source tool, not commercial product (fair use likely applies)

**Structure:**
- **JSON files** with themed name lists in `data/pseudonyms/{theme_name}.json`
- **Format per theme:**
  ```json
  {
    "theme": "star_wars",
    "first_names": {
      "male": ["Luke", "Han", "Obi-Wan", ...],
      "female": ["Leia", "Padmé", "Rey", ...],
      "neutral": ["Yoda", "Chewbacca", ...]
    },
    "last_names": ["Skywalker", "Organa", "Solo", "Kenobi", ...]
  }
  ```
- **Initial counts:** 500+ first names (mixed gender), 500+ last names per theme = 250K+ combinations
- **Gender-preserving:** When NER provides gender classification, match gender in pseudonym selection

**Security & Privacy Architecture:**
- **Zero telemetry:** No analytics, crash reporting, or external communication (NFR11)
- **In-memory processing:** No temporary file creation; all transformations in RAM
- **Secure deletion:** Mapping table destruction uses secure overwrite (3-pass DoD 5220.22-M standard) before file deletion (FR17)
- **Passphrase requirements:** Minimum 12 characters (NFR12), entropy validation with user feedback ("weak/medium/strong")
- **Data minimization:** Only store entity mappings, not original document content

**Packaging & Distribution:**
- **PyPI package:** `gdpr-pseudonymizer` (CLI entry point: `gdpr-pseudo`)
- **Dependencies management:** Poetry for reproducible builds and dependency resolution
- **Model distribution:** spaCy French model downloaded post-install via `python -m spacy download fr_core_news_lg` (automatic on first run with user prompt)
- **Installation package:** Include comprehensive installation script with platform-specific checks and troubleshooting
- **CI/CD:** GitHub Actions (Sprint 1 deliverable) testing installation on Windows 10/11, macOS Intel/ARM, Ubuntu 22.04/24.04, Debian 11/12

**LLM API Requirements:**
- **OpenAI API key** (GPT-4 access) and **Anthropic API key** (Claude 3.5 Sonnet) for Epic 4 LLM utility testing
- **Estimated cost:** $50-100 for NFR10 validation testing

**Documentation Requirements (NFR13):**

**Installation Guide:**
- Platform-specific instructions (Windows/Mac/Linux)
- Troubleshooting common issues (Python version, model download failures, permissions)
- Docker container option for isolated environments

**Usage Tutorial:**
- Step-by-step walkthrough with example documents
- Command reference with all flags and options
- Configuration file examples

**Methodology Description (Academic Citation):**
- Technical approach: NER library, detection algorithm, pseudonymization logic
- Validation procedures and quality controls
- Limitations and edge cases
- Suitable for ethics board review and research paper citations

**Error Message Style Guide (NFR7):**
- Format: `[ERROR] Clear description | Suggested action | Reference: <doc link>`
- Examples for common scenarios (file not found, invalid passphrase, model not installed, low accuracy warning)
- Catalog of expected errors with standardized messages

**LLM Utility Test Protocol (NFR10):**
- **Test Set:** 10 representative documents (5 interview transcripts, 5 business documents)
- **Standardized Prompts:**
  - "Summarize the main themes in this document"
  - "Identify key relationships between individuals mentioned"
  - "Extract action items and decisions made"
- **Evaluation Rubric:**
  - Thematic accuracy (themes preserved after pseudonymization)
  - Relationship coherence (connections maintained between pseudonyms)
  - Factual preservation (non-name facts unchanged)
  - Overall utility score (1-5 scale)
- **Target:** ≥80% utility score (average 4.0/5.0 across test set and prompts)
- **Test Timing:** Sprint 4-5 after pseudonymization logic is stable

**Markdown Edge Case Test Suite (FR21):**

Comprehensive test cases covering:
- Nested code blocks within lists and quotes
- URLs with name-like patterns in query parameters
- Inline code containing French names (should not pseudonymize)
- Markdown tables with name-like headers
- Image alt text with names
- Link references with names in link text vs URL
- Mixed HTML in Markdown (name in HTML tags)
- Escaped characters near names

**Performance Optimization Strategies:**
- **Lazy model loading:** Load spaCy model on first use, not at CLI startup (improves NFR5 <5s startup)
- **Process pool:** Reuse worker processes across batch operations (avoid repeated model loading overhead)
- **Caching:** Cache NER results for idempotent processing (FR19) - stored in mapping table with document hash
- **Progress indicators:** Use `rich` library for enhanced CLI progress bars and status displays

**GDPR Compliance & Audit Trail:**
- **Article 30 compliance:** Audit logs (FR12) provide processing activity records
- **Data minimization:** Only store entity mappings and operation metadata, not original document content
- **Right to erasure:** `destroy-table` command (FR17) implements secure data deletion with verification
- **Transparency:** Full methodology documentation enables data subjects to understand processing
- **Purpose limitation:** Mapping table only used for pseudonymization/reversibility, no secondary purposes

**Development Environment & Tooling:**
- **Version control:** Git (repository already initialized)
- **Code quality:** Black (formatting), ruff (fast linting), mypy (type checking)
- **CI/CD:** GitHub Actions (Sprint 1) - automated testing on 6 platform variants
- **Issue tracking:** GitHub Issues for bug reports and feature requests
- **Documentation:** MkDocs for technical documentation with auto-deployment

**Known Limitations & Constraints (MVP):**
- **French language only:** Other languages deferred to Phase 2+
- **Text formats only:** .txt and .md (FR13); PDF/DOCX deferred to Phase 2
- **No GPU required:** CPU-only NLP models for accessibility (8GB RAM target)
- **Single-user tool:** No multi-user or team collaboration features in MVP
- **Name variations:** Titles ("Dr.", "M.", "Mme."), name order variations ("Dubois, Marie"), and abbreviations handled on best-effort basis; comprehensive support deferred to Phase 2
- **Compound names:** FR20 relies on NER library capabilities; may require custom regex patterns if NER insufficient

**Idempotency + Validation Mode Interaction (FR19 Clarification):**

When re-processing a document with existing mappings:

**Without `--validate` flag:**
- Reuse ALL existing entity→pseudonym mappings exactly
- Detect and add NEW entities not in mapping table
- Output uses consistent pseudonyms from previous run

**With `--validate` flag:**
- Present ALL detected entities (existing + new) for review
- Show existing pseudonyms for known entities (user can change if desired)
- Allow user to modify any mapping (changes persist to mapping table)
- New pseudonyms assigned only to genuinely new entities

**Rationale:** Idempotency provides consistency by default; validation mode provides override capability when user wants to revise decisions.

---

## Epic List

### Epic 0: Pre-Sprint Preparation (Week -1 to 0)

**Goal:** Prepare test data and development environment foundation to enable Epic 1 to start without blockers, validating basic NLP library viability before full sprint work begins.

---

### Epic 1: Foundation & NLP Validation (Week 1-4)

**Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, and deliver a working "walking skeleton" CLI command that demonstrates basic end-to-end pseudonymization capability for early validation.

---

### Epic 2: Core Pseudonymization Engine (Week 4-8)

**Goal:** Implement production-quality compositional pseudonymization logic with encrypted mapping tables and audit trails, enabling consistent entity replacement across documents while validating architectural scalability for batch processing.

---

### Epic 3: CLI Interface & Batch Processing (Week 8-11)

**Goal:** Deliver complete command-line interface with all user-facing commands, process-based parallel batch processing, and optional interactive validation mode, achieving production-ready workflows for real-world use cases.

---

### Epic 4: Launch Readiness & LLM Validation (Week 11-13)

**Goal:** Validate LLM utility preservation with real AI services, complete comprehensive documentation package, achieve all NFR quality thresholds, and prepare for confident early adopter release with full user support.

---

**Timeline: 13 weeks total (includes 1-week buffer for NLP selection and compositional logic complexity risks)**

---

### Epic Definitions of Done

**Epic 0 DoD:**
- ✓ Initial test corpus created (10 French documents with ground truth annotations)
- ✓ Development environment configured (Python 3.9+, Poetry, pytest)
- ✓ Quick spaCy benchmark completed (initial accuracy estimate)
- ✓ Ready to begin Epic 1 Sprint 1 without blockers

**Epic 1 DoD:**
- ✓ NLP library selected (spaCy or Stanza) with ≥85% accuracy validated on 20-30 document test corpus
- ✓ CI/CD pipeline operational (GitHub Actions testing on 2+ platforms)
- ✓ Walking skeleton: Basic `process` command runs end-to-end (naive pseudonymization)
- ✓ Git workflow and code quality tooling established
- ✓ Can demonstrate basic pseudonymization concept to alpha testers

**Epic 2 DoD:**
- ✓ Compositional pseudonymization logic (FR4-5) passes comprehensive unit tests
- ✓ Compound name handling (FR20) implemented and tested
- ✓ Encrypted mapping table operational with Python-native encryption
- ✓ Audit logging (FR12) captures all required fields
- ✓ Single-document performance meets NFR1 (<30s for 2-5K words)
- ✓ Architectural validation: Basic batch processing proves design scales
- ✓ **Alpha Release:** 3-5 friendly users provide initial feedback (after week 6)

**Epic 3 DoD:**
- ✓ All CLI commands (FR15) functional and tested
- ✓ Batch processing achieves NFR2 (<30min for 50 docs) with process-based parallelism
- ✓ Optional validation mode (`--validate` flag) operational
- ✓ Markdown format-aware processing (FR21) handles all edge cases
- ✓ Idempotent processing (FR19) validated
- ✓ Installation succeeds on Windows, macOS, Linux (initial NFR3 validation on 3 platforms)
- ✓ **Beta Release:** 10-15 early adopters using tool in real workflows (after week 10)

**Epic 4 DoD:**
- ✓ LLM utility preservation validated: ≥80% utility score (NFR10) with real ChatGPT/Claude API testing
- ✓ Cross-platform installation achieves ≥85% success rate (NFR3) across all target platforms
- ✓ Comprehensive documentation complete (NFR13): installation guide, tutorial, methodology, FAQ
- ✓ Error message catalog finalized with style guide compliance (NFR7)
- ✓ NER accuracy thresholds validated (NFR8: <10% false negatives, NFR9: <15% false positives)
- ✓ All bug fixes from beta testing applied (10% scope allowance)
- ✓ Ready for public early adopter release with full support capability

---

### Release Strategy

- **Week 6 (Post-Epic 2):** Alpha release to 3-5 friendly users for core functionality feedback
- **Week 10 (Post-Epic 3):** Beta release to 10-15 early adopters for production workflow validation
- **Week 13 (Post-Epic 4):** Public MVP release to broader early adopter community (target: 50+ users)

---

### NFR Validation Distribution (Incremental Quality Gates)

| NFR | Epic 1 | Epic 2 | Epic 3 | Epic 4 |
|-----|--------|--------|--------|--------|
| NFR1 (Single-doc performance) | - | ✓ Validate | ✓ Maintain | ✓ Verify |
| NFR2 (Batch performance) | - | Architectural spike | ✓ Validate | ✓ Verify |
| NFR3 (Installation success) | Basic setup | - | Sample (2-3 platforms) | ✓ Comprehensive |
| NFR5 (Startup time) | - | ✓ Validate | ✓ Maintain | ✓ Verify |
| NFR6 (Crash rate) | - | Unit test coverage | ✓ Integration testing | ✓ Comprehensive |
| NFR7 (Error messages) | Basic errors | Core errors | CLI errors | ✓ Complete catalog |
| NFR8-9 (Accuracy) | ✓ Benchmark | ✓ Validate | ✓ Maintain | ✓ Comprehensive |
| NFR10 (LLM utility) | - | - | - | ✓ Validate |
| NFR13 (Documentation) | Basic README | API docs start | User guide draft | ✓ Complete |

---

## Epic 0: Pre-Sprint Preparation

**Epic Goal:** Prepare test data and development environment foundation to enable Epic 1 to start without blockers, validating basic NLP library viability before full sprint work begins.

**Duration:** Week -1 to 0 (pre-sprint preparation)

---

### Story 0.1: Create Initial Test Corpus

**As a** developer,
**I want** an initial test corpus of French documents with ground truth entity annotations,
**so that** I can benchmark NLP library accuracy and validate entity detection quality throughout development.

#### Acceptance Criteria

1. **AC1:** Test corpus contains 10 French documents representing target use cases (5 interview transcripts, 5 business documents).
2. **AC2:** Each document manually annotated with ground truth entity boundaries and types (PERSON, LOCATION, ORG).
3. **AC3:** Documents include edge cases: compound names ("Jean-Pierre"), shared name components ("Marie Dubois", "Marie Dupont"), standalone name components.
4. **AC4:** Annotations stored in structured format (JSON or CSV) with: `document_id`, `entity_text`, `entity_type`, `start_offset`, `end_offset`.
5. **AC5:** Test corpus documented with: source/creation methodology, entity type distribution statistics, known edge cases.
6. **AC6:** Total annotation effort <20 hours (2-3 days part-time work).

---

### Story 0.2: Setup Development Environment

**As a** developer,
**I want** a standardized development environment with all necessary tools configured,
**so that** I can begin coding immediately in Epic 1 without setup delays.

#### Acceptance Criteria

1. **AC1:** Python 3.9+ installed and verified on development machine.
2. **AC2:** Poetry dependency manager installed and project initialized with `pyproject.toml`.
3. **AC3:** Code quality tools configured: Black (formatter), Ruff (linter), mypy (type checker).
4. **AC4:** pytest testing framework installed with basic test directory structure (`tests/unit`, `tests/integration`).
5. **AC5:** Git repository confirmed with `.gitignore` configured for Python projects (exclude `__pycache__`, `.pytest_cache`, virtual environments).
6. **AC6:** Basic `README.md` created with: project description, setup instructions, development workflow.
7. **AC7:** Development environment setup documented (IDE recommendations, required extensions, troubleshooting common issues).

---

### Story 0.3: Quick NLP Library Viability Test

**As a** product manager,
**I want** a quick initial test of spaCy's French NER accuracy on sample documents,
**so that** I can assess viability before committing to full Epic 1 benchmark and identify early red flags.

#### Acceptance Criteria

1. **AC1:** spaCy installed with `fr_core_news_lg` French model.
2. **AC2:** Simple script created that processes 3-5 sample documents through spaCy NER pipeline.
3. **AC3:** Script outputs detected entities with types and confidence scores (if available).
4. **AC4:** Manual comparison of detected entities vs known entities in sample documents.
5. **AC5:** Rough accuracy estimate calculated: "Good" (>80%), "Marginal" (60-80%), "Poor" (<60%).
6. **AC6:** Decision documented: Proceed to Epic 1 full benchmark, or investigate Stanza/alternatives immediately.
7. **AC7:** Quick test results shared with stakeholders (estimated accuracy, notable strengths/weaknesses, recommendation).

---

## Epic 1: Foundation & NLP Validation (Week 1-4)

**Epic Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, and deliver a working "walking skeleton" CLI command that demonstrates basic end-to-end pseudonymization capability for early validation.

---

### Story 1.1: Expand Test Corpus to Full Benchmark Set

**As a** developer,
**I want** a comprehensive test corpus of 20-30 French documents with ground truth annotations,
**so that** I can rigorously benchmark NLP library accuracy and track quality metrics throughout development.

#### Acceptance Criteria

1. **AC1:** Test corpus expanded from 10 to 25 French documents (15 interview transcripts, 10 business documents).
2. **AC2:** All documents manually annotated with ground truth entity boundaries and types (PERSON, LOCATION, ORG).
3. **AC3:** Documents include comprehensive edge cases: titles ("Dr. Marie Dubois"), name order variations ("Dubois, Marie"), abbreviations ("M. Dubois"), nested entities.
4. **AC4:** Entity type distribution documented: minimum 100 PERSON entities, 50 LOCATION entities, 30 ORG entities across corpus.
5. **AC5:** Annotations validated by second reviewer for quality assurance (sample 20% of documents, resolve discrepancies).
6. **AC6:** Benchmark automation script created: loads corpus, runs NER, calculates precision/recall/F1 per entity type.

---

### Story 1.2: Comprehensive NLP Library Benchmark

**As a** product manager,
**I want** rigorous accuracy comparison between spaCy and Stanza on our French test corpus,
**so that** I can make an evidence-based decision on which library meets our ≥85% accuracy threshold.

#### Acceptance Criteria

1. **AC1:** spaCy pipeline implemented with `fr_core_news_lg` model processing full 25-document corpus.
2. **AC2:** Stanza pipeline implemented with French models processing same corpus.
3. **AC3:** Accuracy metrics calculated for both libraries: precision, recall, F1 score per entity type (PERSON, LOCATION, ORG) and overall.
4. **AC4:** Performance metrics measured: processing time per document, memory footprint, startup time.
5. **AC5:** Compound name detection tested: accuracy on "Jean-Pierre", "Marie-Claire" patterns (FR20 requirement).
6. **AC6:** Results documented in comparison table with recommendation.
7. **AC7:** **Go/No-Go Decision:** Selected library achieves ≥85% F1 score overall. If neither meets threshold, execute contingency plan (hybrid approach, lower threshold with mandatory validation, or pivot).
8. **AC8:** Selected library, model version, and benchmark results documented in architecture documentation.

---

### Story 1.3: CI/CD Pipeline Setup

**As a** developer,
**I want** automated testing pipeline running on every commit across multiple platforms,
**so that** I can catch regressions early and ensure cross-platform compatibility throughout development.

#### Acceptance Criteria

1. **AC1:** GitHub Actions workflow configured with test matrix: Windows 11, macOS (latest), Ubuntu 22.04.
2. **AC2:** Workflow runs on every push and pull request: install dependencies, run pytest, report coverage.
3. **AC3:** Code quality checks integrated: Black formatting verification, Ruff linting, mypy type checking.
4. **AC4:** Test execution time <5 minutes for unit tests, <15 minutes including integration tests.
5. **AC5:** Failed checks block PR merges (branch protection rules configured).
6. **AC6:** Coverage reporting integrated (codecov or similar), minimum 80% coverage threshold enforced.
7. **AC7:** CI/CD documentation created: workflow description, how to run locally, troubleshooting common failures.

---

### Story 1.4: Project Foundation & Module Structure

**As a** developer,
**I want** clean module boundaries and project structure established,
**so that** I can build features in Epic 2-3 without architectural refactoring.

#### Acceptance Criteria

1. **AC1:** Package structure created following Technical Assumptions architecture:
   - `gdpr_pseudonymizer/cli/` - Command-line interface layer
   - `gdpr_pseudonymizer/core/` - Core processing orchestration
   - `gdpr_pseudonymizer/nlp/` - NLP engine (entity detection)
   - `gdpr_pseudonymizer/data/` - Data layer (mapping tables, audit logs)
   - `gdpr_pseudonymizer/pseudonym/` - Pseudonym manager
   - `gdpr_pseudonymizer/utils/` - Utilities (encryption, file handling)
2. **AC2:** Selected NLP library integrated as modular component with interface abstraction (allows future library swapping).
3. **AC3:** Basic configuration management: support for `.gdpr-pseudo.yaml` config files (home directory and project root).
4. **AC4:** Logging framework established: structured logging with configurable verbosity levels.
5. **AC5:** Unit tests created for each module demonstrating testability.
6. **AC6:** Module dependency graph documented (no circular dependencies).

---

### Story 1.5: Walking Skeleton - Basic Process Command

**As a** developer,
**I want** a simple end-to-end `process` command that performs naive pseudonymization,
**so that** I can validate the CLI→processing→output pipeline before implementing complex algorithms.

#### Acceptance Criteria

1. **AC1:** CLI framework (Typer) integrated with basic command structure: `gdpr-pseudo process <file>`.
2. **AC2:** Command reads input file (.txt or .md), performs naive pseudonymization (simple find-replace from hardcoded list), writes output file.
3. **AC3:** Basic error handling: file not found, invalid file format, permission errors with clear error messages.
4. **AC4:** Logging output shows: file processed, entities detected (count), pseudonyms applied (count), output location.
5. **AC5:** No NLP integration yet - uses hardcoded entity list (e.g., 10 common French names) for proof of concept.
6. **AC6:** Unit tests validate: file I/O, basic replacement logic, error handling paths.
7. **AC7:** Integration test: process sample document end-to-end, verify output correctness.
8. **AC8:** Can demo to stakeholders: "This is the skeleton we're building on."

---

### Story 1.6: NLP Integration with Basic Entity Detection

**As a** user,
**I want** the system to automatically detect personal names in French documents using validated NLP library,
**so that** I don't have to manually identify entities for pseudonymization.

#### Acceptance Criteria

1. **AC1:** Selected NLP library (from Story 1.2) integrated into `nlp` module.
2. **AC2:** Entity detection function created: accepts document text, returns list of detected entities with types (PERSON, LOCATION, ORG), positions, and confidence scores.
3. **AC3:** `process` command (from Story 1.5) updated to use NLP detection instead of hardcoded list.
4. **AC4:** Detection accuracy on test corpus validates Epic 1 DoD: ≥85% F1 score overall.
5. **AC5:** Processing performance measured: meets or approaches NFR1 target (<30s for 2-5K word document) on standard hardware.
6. **AC6:** False negative tracking: Log entities in ground truth corpus missed by NLP (target <15% miss rate).
7. **AC7:** False positive handling: Detected entities that aren't sensitive data logged (informational only in Epic 1, validation mode in Epic 3 addresses this).
8. **AC8:** Unit tests: NLP integration, entity extraction, error handling (model not found, corrupt document).
9. **AC9:** Integration test: Process test corpus documents, compare detected entities to ground truth, validate accuracy thresholds.

---

## Epic 2: Core Pseudonymization Engine (Week 4-8)

**Epic Goal:** Implement production-quality compositional pseudonymization logic with encrypted mapping tables and audit trails, enabling consistent entity replacement across documents while validating architectural scalability for batch processing.

---

### Story 2.1: Pseudonym Library System

**As a** user,
**I want** themed pseudonym libraries with sufficient name combinations,
**so that** pseudonymized documents maintain readability and avoid repetitive fallback naming.

#### Acceptance Criteria

1. **AC1:** JSON-based pseudonym library structure implemented per Technical Assumptions: separate `first_names` (by gender) and `last_names` arrays.
2. **AC2:** Three themed libraries created with ≥500 first names and ≥500 last names each:
   - Neutral/Generic (French common names from INSEE public data)
   - Star Wars (curated from fan wikis)
   - LOTR (curated from Tolkien Gateway)
3. **AC3:** Gender metadata included where applicable (male/female/neutral tags).
4. **AC4:** Library manager implemented: load themes, select pseudonyms with gender-matching logic (when NER provides gender data).
5. **AC5:** Pseudonym exhaustion detection: warn when library usage exceeds 80%, provide systematic fallback naming ("Person-001", "Location-001") when exhausted.
6. **AC6:** Unit tests: library loading, pseudonym selection (with/without gender), exhaustion handling.
7. **AC7:** Library sourcing documented for legal compliance (public domain, fair use considerations).

---

### Story 2.2: Compositional Pseudonymization Logic (FR4-5)

**As a** user,
**I want** consistent pseudonym application using compositional strict matching,
**so that** "Marie Dubois" → "Leia Organa" everywhere, with "Marie" → "Leia" and "Dubois" → "Organa" when they appear alone.

#### Acceptance Criteria

1. **AC1:** Full name entity detection: identify complete person names (first + last) from NER results.
2. **AC2:** Composite pseudonym assignment: Map full name to full pseudonym (e.g., "Marie Dubois" → "Leia Organa").
3. **AC3:** Component mapping: Extract and store first name → pseudonym first name, last name → pseudonym last name mappings.
4. **AC4:** Standalone component replacement: When "Marie" appears alone, replace with "Leia" (using first name mapping).
5. **AC5:** Shared component handling (FR5): "Marie Dubois" → "Leia Organa", "Marie Dupont" → "Leia Skywalker" (preserves "Marie" → "Leia" consistency).
6. **AC6:** Ambiguous component flagging: Log standalone components without full name context as potentially ambiguous for validation mode review.
7. **AC7:** Unit tests: full name composition, component extraction, standalone replacement, shared component scenarios.
8. **AC8:** Integration test: Process documents with complex name patterns, verify compositional logic correctness.

---

### Story 2.3: Compound Name Handling (FR20)

**As a** user,
**I want** French compound first names like "Jean-Pierre" and "Marie-Claire" handled correctly,
**so that** pseudonymization maintains name structure integrity.

#### Acceptance Criteria

1. **AC1:** Compound first name detection: Identify hyphenated first names in NER results.
2. **AC2:** Compound pseudonym assignment: Map compound names to compound pseudonyms (e.g., "Jean-Pierre" → "Luke-Han").
3. **AC3:** Component awareness: If "Jean" or "Pierre" appear separately, handle based on context (log as ambiguous if unclear).
4. **AC4:** Regex pattern support: Fallback regex for detecting common French compound patterns if NER doesn't identify them.
5. **AC5:** Unit tests: compound name detection, pseudonym assignment, edge cases (triple compounds, non-standard separators).
6. **AC6:** Test corpus validation: Verify compound names in test corpus processed correctly (from Story 1.1 edge cases).

---

### Story 2.4: Encrypted Mapping Table with Python-Native Encryption

**As a** user,
**I want** a secure encrypted mapping table storing original↔pseudonym correspondences,
**so that** I can exercise GDPR rights (reversibility) while protecting sensitive data.

#### Acceptance Criteria

1. **AC1:** SQLite database schema implemented per Technical Assumptions:
   - `entities` table: id, entity_type, first_name, last_name, full_name, pseudonym_first, pseudonym_last, pseudonym_full, first_seen_timestamp, gender, confidence_score
   - `operations` table: id, timestamp, operation_type, files_processed, model_name, model_version, theme_selected, user_modifications, entity_count
   - `metadata` table: key, value (stores encryption params, schema version)
2. **AC2:** Python-native encryption implemented using `cryptography` library (Fernet symmetric encryption).
3. **AC3:** Passphrase-based key derivation: PBKDF2 with salt stored in `metadata` table.
4. **AC4:** Column-level encryption: Sensitive columns (names, pseudonyms) encrypted individually.
5. **AC5:** Passphrase validation on database open: verify passphrase before allowing access.
6. **AC6:** Passphrase strength validation: minimum 12 characters (NFR12), provide entropy feedback ("weak/medium/strong").
7. **AC7:** Database operations: create, open (with passphrase), query mappings, insert new entities, close.
8. **AC8:** Unit tests: encryption/decryption, passphrase validation, CRUD operations, error handling (wrong passphrase, corrupted database).
9. **AC9:** Security review: No plaintext sensitive data in logs, no temp file leakage.

---

### Story 2.5: Audit Logging (FR12)

**As a** compliance officer,
**I want** comprehensive audit logs of all pseudonymization operations,
**so that** I can demonstrate GDPR Article 30 compliance and troubleshoot issues.

#### Acceptance Criteria

1. **AC1:** Audit log implemented in `operations` table (from Story 2.4 schema).
2. **AC2:** Log entry created for each pseudonymization operation with required fields (FR12): timestamp, operation type, files processed, model version, theme selected, entity count.
3. **AC3:** User modifications logged when validation mode used (deferred to Epic 3, placeholder in schema).
4. **AC4:** Export functionality: Query audit log and export to JSON or CSV format.
5. **AC5:** Log rotation not required for MVP (SQLite database handles growth).
6. **AC6:** Unit tests: log entry creation, query operations, export functionality.
7. **AC7:** Documentation: audit log schema, query examples, GDPR Article 30 mapping.

---

### Story 2.6: Single-Document Pseudonymization Workflow

**As a** user,
**I want** to pseudonymize a single document with all compositional logic applied,
**so that** I can validate the core value proposition on real documents.

#### Acceptance Criteria

1. **AC1:** Integrate all Epic 2 components: NER detection (Epic 1) → compositional logic (2.2) → compound handling (2.3) → mapping table (2.4) → audit log (2.5).
2. **AC2:** `process` command updated from Epic 1 skeleton to production implementation.
3. **AC3:** Workflow: Load document → detect entities → assign pseudonyms (compositional) → store mappings → apply replacements → write output → log operation.
4. **AC4:** Idempotent behavior (FR19): Re-processing same document reuses existing mappings.
5. **AC5:** Performance validation (NFR1): Process 2-5K word document in <30 seconds on standard hardware.
6. **AC6:** Accuracy validation: False negative rate <10% (NFR8), false positive rate <15% (NFR9) on test corpus.
7. **AC7:** Integration tests: End-to-end workflow, idempotency, error scenarios (file not found, encryption errors).
8. **AC8:** Can demo to alpha testers: Fully functional single-document pseudonymization.

---

### Story 2.7: Architectural Spike - Batch Processing Scalability

**As a** developer,
**I want** to validate that our architecture can handle batch processing efficiently,
**so that** Epic 3 batch implementation doesn't require major refactoring.

#### Acceptance Criteria

1. **AC1:** Prototype batch processing with process-based parallelism (multiprocessing module).
2. **AC2:** Test with 10-document batch: process in parallel using worker pool (min(cpu_count, 4) workers).
3. **AC3:** Validate mapping table consistency: Cross-document entity mapping works correctly (same entity gets same pseudonym across batch).
4. **AC4:** Performance measurement: Estimate batch processing time vs sequential processing (should show speedup).
5. **AC5:** Identify architectural issues: memory leaks, mapping table contention, worker process overhead.
6. **AC6:** Document findings: Recommendations for Epic 3 implementation, known limitations, optimization opportunities.
7. **AC7:** If major issues found, adjust architecture before proceeding to Epic 3.

---

### Story 2.8: Alpha Release Preparation

**As a** product manager,
**I want** to release an alpha version to 3-5 friendly users after Epic 2,
**so that** I can validate core value proposition and gather early feedback before investing in CLI polish and batch features.

#### Acceptance Criteria

1. **AC1:** Basic installation package created: PyPI-style package installable via `pip install -e .`.
2. **AC2:** Minimal documentation: README with installation instructions, basic usage example, known limitations.
3. **AC3:** Alpha testers identified and onboarded (3-5 users: 2 researchers, 2-3 LLM users).
4. **AC4:** Alpha testing protocol created: specific tasks for testers, feedback survey questions.
5. **AC5:** Feedback collection mechanism: Google Form or GitHub issues for structured feedback.
6. **AC6:** Alpha release tagged in Git: `v0.1.0-alpha`.
7. **AC7:** Alpha feedback review session scheduled (end of week 6-7) to inform Epic 3 priorities.

---

## Epic 3: CLI Interface & Batch Processing (Week 8-11)

**Epic Goal:** Deliver complete command-line interface with all user-facing commands, process-based parallel batch processing, and optional interactive validation mode, achieving production-ready workflows for real-world use cases.

---

### Story 3.1: Complete CLI Command Set (FR15)

**As a** user,
**I want** all planned CLI commands implemented with consistent interface and help documentation,
**so that** I can perform all necessary operations through intuitive commands.

#### Acceptance Criteria

1. **AC1:** All commands from FR15 implemented:
   - `init` - Initialize new mapping table with passphrase
   - `process` - Process single document (already exists from Epic 2, enhanced)
   - `batch` - Process multiple documents
   - `list-mappings` - View entity↔pseudonym correspondences
   - `validate-mappings` - Review existing mappings without processing
   - `stats` - Show statistics (# entities, # documents, library exhaustion %)
   - `import-mappings` - Load mappings from previous project
   - `export` - Export audit log
   - `destroy-table` - Secure deletion with confirmation prompt
2. **AC2:** Consistent command structure: global options (--config, --verbose), command-specific options.
3. **AC3:** Help text for all commands: `gdpr-pseudo --help`, `gdpr-pseudo process --help`.
4. **AC4:** Configuration file support: `.gdpr-pseudo.yaml` in home directory or project root for default settings.
5. **AC5:** Unit tests for each command: argument parsing, execution, error handling.
6. **AC6:** CLI documentation: Command reference with examples, common workflows.

---

### Story 3.2: Interactive Validation Mode (FR7, FR18)

**As a** user,
**I want** optional interactive validation mode to review detected entities before pseudonymization,
**so that** I can ensure quality and catch NER errors on sensitive documents.

#### Acceptance Criteria

1. **AC1:** `--validate` flag implemented for `process` and `batch` commands.
2. **AC2:** Validation mode workflow:
   - Detect entities using NER
   - Present entities to user in readable format (grouped by type: PERSON, LOCATION, ORG)
   - Allow user actions: confirm, remove entity, add missed entity, modify entity text
   - Show ambiguous standalone components flagged by FR4 logic
   - Apply user modifications before final pseudonymization
3. **AC3:** Interactive UI using `rich` library: formatted tables, color-coded entity types, keyboard navigation.
4. **AC4:** Default behavior (FR18): Validation mode OFF by default (fast processing).
5. **AC5:** Batch mode with validation: User reviews entities from all documents, then batch proceeds.
6. **AC6:** User modifications logged in audit log (FR12).
7. **AC7:** Unit tests: Validation flow, user input handling, modification application.
8. **AC8:** Integration test: Run validation mode on test document, simulate user interactions, verify final output.

---

### Story 3.3: Process-Based Batch Processing

**As a** user,
**I want** to efficiently process 10-100+ documents in a single batch operation,
**so that** I can pseudonymize entire document corpora with consistent mappings.

#### Acceptance Criteria

1. **AC1:** `batch` command implemented: accepts directory path or file list, processes all documents.
2. **AC2:** Process-based parallelism using `multiprocessing` module (per Technical Assumptions): worker pool with size min(cpu_count, 4).
3. **AC3:** Cross-document consistency (FR6): Mapping table updates incrementally ensure same entity gets same pseudonym across batch.
4. **AC4:** Progress indicators using `rich` library: progress bar, current file, entities detected, estimated time remaining.
5. **AC5:** Error handling: Continue processing on individual file errors, report failures at end.
6. **AC6:** Performance validation (NFR2): Process 50 documents in <30 minutes on standard hardware.
7. **AC7:** Batch summary report (FR18): After processing, show detected entities across all documents, statistics, any errors.
8. **AC8:** Unit tests: Batch orchestration, worker management, error handling.
9. **AC9:** Integration test: Process 25-document test corpus in batch, verify consistency and performance.

---

### Story 3.4: Idempotent Processing with Validation Mode (FR19 Clarification)

**As a** user,
**I want** clear behavior when re-processing documents with existing mappings,
**so that** I can iterate on documents without creating inconsistent pseudonyms.

#### Acceptance Criteria

1. **AC1:** Without `--validate`: Reuse ALL existing mappings, detect and add only new entities, output uses consistent pseudonyms.
2. **AC2:** With `--validate`: Present ALL entities (existing + new), show existing pseudonyms, allow user to change any mapping.
3. **AC3:** Document hash stored in mapping table: Detect when document content changes (new entities likely).
4. **AC4:** User-friendly messaging: "Document previously processed on [date], reusing 15 existing mappings, found 2 new entities."
5. **AC5:** Unit tests: Idempotency scenarios (exact reprocess, modified document, new entities), validation mode interaction.
6. **AC6:** Integration test: Process document, modify document, reprocess with/without validation, verify correct behavior.

---

### Story 3.5: Markdown Format-Aware Processing (FR21)

**As a** user,
**I want** Markdown files processed intelligently without breaking syntax,
**so that** pseudonymized Markdown remains valid and usable.

#### Acceptance Criteria

1. **AC1:** Markdown parser integrated: Identify exclusion zones (URLs, code blocks, inline code, image references).
2. **AC2:** Pseudonymization skips exclusion zones: Names in URLs, code blocks, inline code not replaced.
3. **AC3:** Comprehensive edge case handling from Technical Assumptions test suite:
   - Nested code blocks within lists
   - URLs with name-like query parameters
   - Inline code with French names
   - Markdown tables with name headers
   - Image alt text with names
   - Link references (text vs URL)
   - Mixed HTML in Markdown
4. **AC4:** Unit tests: Each edge case validated, regression tests for Markdown parsing.
5. **AC5:** Integration test: Process complex Markdown document with all edge cases, verify syntax validity and correct exclusions.
6. **AC6:** Plain text (.txt) processing unchanged (no Markdown parsing).

---

### Story 3.6: Enhanced Error Handling & Messages (NFR7)

**As a** user,
**I want** clear, actionable error messages when things go wrong,
**so that** I can resolve issues without external support.

#### Acceptance Criteria

1. **AC1:** Error message style guide implemented: `[ERROR] Clear description | Suggested action | Reference: <doc link>`.
2. **AC2:** Error catalog created covering common scenarios:
   - File not found → "Check file path, use absolute or relative path"
   - Invalid passphrase → "Passphrase incorrect, use same passphrase from `init` command"
   - Model not installed → "Run `python -m spacy download fr_core_news_lg`"
   - Low disk space → "Free up disk space or change output directory"
   - Permission denied → "Check file permissions or run with appropriate privileges"
   - Corrupt database → "Mapping table corrupted, restore from backup or run `init` for new table"
3. **AC3:** Contextual help: Error messages link to relevant documentation sections.
4. **AC4:** User-friendly validation: Validate inputs before processing (file exists, passphrase strength, valid config).
5. **AC5:** Unit tests: Trigger each error scenario, verify message format and clarity.
6. **AC6:** Target validation (NFR7): ≥80% of users resolve issues without support (measured in Beta testing).

---

### Story 3.7: Cross-Platform Installation Testing (NFR3 Initial Validation)

**As a** user,
**I want** smooth installation on Windows, macOS, and Linux,
**so that** I can start using the tool quickly without setup frustration.

#### Acceptance Criteria

1. **AC1:** Installation tested on minimum 3 platforms: Windows 11, macOS (Intel or ARM), Ubuntu 22.04.
2. **AC2:** Installation script created: Checks Python version, installs dependencies, downloads NLP model, verifies installation.
3. **AC3:** Installation documentation updated: Platform-specific instructions, troubleshooting section.
4. **AC4:** Common installation issues documented with solutions:
   - Python version mismatch
   - pip vs Poetry installation
   - Model download failures (network issues, firewall)
   - Platform-specific dependency issues
5. **AC5:** Docker container option created as fallback for complex environments.
6. **AC6:** Initial NFR3 validation: ≥80% installation success rate on tested platforms (comprehensive validation in Epic 4).
7. **AC7:** Beta testers installation experience tracked: success rate, time to completion, support requests.

---

### Story 3.8: Beta Release Preparation

**As a** product manager,
**I want** to release a beta version to 10-15 early adopters after Epic 3,
**so that** I can validate production workflows and gather feedback for final polish in Epic 4.

#### Acceptance Criteria

1. **AC1:** Beta release package: PyPI-publishable package with proper versioning (`v0.2.0-beta`).
2. **AC2:** Comprehensive documentation: Installation guide, usage tutorial (all commands), configuration reference.
3. **AC3:** Beta testers recruited: 10-15 users (5 researchers, 5-7 LLM users, 1-2 compliance/legal professionals).
4. **AC4:** Beta testing protocol: Specific workflows to test (batch processing, validation mode, idempotency), feedback survey.
5. **AC5:** Beta feedback collection: Structured survey + open-ended feedback + usage analytics (if users opt-in).
6. **AC6:** Beta support channel: Dedicated communication channel (Slack/Discord) for beta testers.
7. **AC7:** Beta feedback review: Scheduled review session (end of week 10-11) to prioritize Epic 4 work and identify critical bugs.

---

## Epic 4: Launch Readiness & LLM Validation (Week 11-13)

**Epic Goal:** Validate LLM utility preservation with real AI services, complete comprehensive documentation package, achieve all NFR quality thresholds, and prepare for confident early adopter release with full user support.

---

### Story 4.1: LLM Utility Preservation Testing (NFR10)

**As a** product manager,
**I want** rigorous validation that pseudonymized documents maintain usefulness for LLM analysis,
**so that** I can confidently market the primary value proposition to LLM users.

#### Acceptance Criteria

1. **AC1:** LLM API access configured: OpenAI API (ChatGPT) and Anthropic API (Claude) keys obtained, testing budget allocated ($50-100).
2. **AC2:** Test set prepared: 10 representative documents (5 interview transcripts, 5 business documents) per Technical Assumptions protocol.
3. **AC3:** Standardized prompts executed for both original and pseudonymized versions:
   - "Summarize the main themes in this document"
   - "Identify key relationships between individuals mentioned"
   - "Extract action items and decisions made"
4. **AC4:** Evaluation rubric applied: Thematic accuracy, relationship coherence, factual preservation, overall utility (1-5 scale).
5. **AC5:** Results analyzed: Average utility score ≥4.0/5.0 (80% threshold from NFR10).
6. **AC6:** Edge cases documented: Scenarios where pseudonymization degraded utility, recommendations for users.
7. **AC7:** Results documented: Methodology, findings, example comparisons (original vs pseudonymized LLM outputs).
8. **AC8:** **Go/No-Go Decision:** If <80% utility, determine if acceptable with caveats or requires changes before launch.

---

### Story 4.2: Comprehensive Cross-Platform Installation Validation (NFR3)

**As a** user,
**I want** reliable installation across all target platforms,
**so that** I can adopt the tool regardless of my operating system.

#### Acceptance Criteria

1. **AC1:** Comprehensive platform testing:
   - Windows: 10, 11 (64-bit)
   - macOS: Intel (Big Sur+), Apple Silicon (M1/M2)
   - Linux: Ubuntu 20.04, 22.04, 24.04; Debian 11, 12; Fedora 35+
2. **AC2:** Installation testing protocol: Fresh OS installs (VMs or containers), follow documentation, track success/failure and time.
3. **AC3:** Common failure scenarios tested: Missing Python, pip not found, model download failures, permission issues.
4. **AC4:** Installation success rate validated (NFR3): ≥85% across all platforms.
5. **AC5:** Installation time tracked: ≥80% of users complete first successful pseudonymization within 30 minutes (NFR14).
6. **AC6:** Troubleshooting guide enhanced: Document all discovered issues with platform-specific solutions.
7. **AC7:** Docker container validated: Works on all platforms as fallback for complex environments.
8. **AC8:** Beta tester installation data analyzed: Incorporate real-world installation experiences.

---

### Story 4.3: Complete Documentation Package (NFR13)

**As a** user,
**I want** comprehensive, well-organized documentation,
**so that** I can install, use, and troubleshoot the tool without developer support.

#### Acceptance Criteria

1. **AC1:** Installation Guide complete:
   - Platform-specific instructions (Windows/Mac/Linux)
   - Python/Poetry setup
   - Model download process
   - Docker installation alternative
   - Troubleshooting common issues
   - Video walkthrough (optional, nice-to-have)
2. **AC2:** Usage Tutorial complete:
   - Quick start (first pseudonymization in 5 minutes)
   - All CLI commands with examples
   - Common workflows (single document, batch, validation mode)
   - Configuration file examples
   - Tips and best practices
3. **AC3:** Methodology Description complete (academic citation):
   - Technical approach (NER library, algorithm description)
   - Validation procedures and quality controls
   - Limitations and edge cases
   - GDPR compliance mapping
   - Suitable for ethics board review
   - Proper academic formatting with citations
4. **AC4:** FAQ complete:
   - Common questions (accuracy expectations, supported formats, GDPR compliance)
   - Comparison with alternatives
   - Roadmap and Phase 2 GUI plans
5. **AC5:** Troubleshooting Guide complete:
   - Error message reference
   - Common failure scenarios with solutions
   - Platform-specific issues
   - When to file bug reports
6. **AC6:** API Reference (for developers):
   - Module documentation
   - Core classes and functions
   - Extension points for customization
7. **AC7:** Documentation hosted: GitHub Pages or Read the Docs with search functionality.
8. **AC8:** Documentation effectiveness validated: <20% of users require support beyond documentation (NFR14 target).

---

### Story 4.4: NER Accuracy Comprehensive Validation (NFR8-9)

**As a** quality assurance lead,
**I want** final validation of NER accuracy thresholds on expanded test corpus,
**so that** I can confidently report quality metrics to users and stakeholders.

#### Acceptance Criteria

1. **AC1:** Full 25-document test corpus processed with current implementation.
2. **AC2:** False negative rate calculated (NFR8): <10% of sensitive entities missed.
3. **AC3:** False positive rate calculated (NFR9): <15% of flagged entities are false positives.
4. **AC4:** Accuracy by entity type reported: PERSON, LOCATION, ORG precision/recall.
5. **AC5:** Edge case accuracy documented: Compound names, titles, abbreviations, ambiguous components.
6. **AC6:** Confidence score analysis: Correlation between NER confidence and actual accuracy (informational for future features).
7. **AC7:** Results compared to Epic 1 benchmarking: Validate no regression from full implementation complexity.
8. **AC8:** Quality report created: Accuracy metrics, known limitations, recommended validation mode use cases.

---

### Story 4.5: Performance & Stability Validation (NFR1-2, NFR5-6)

**As a** quality assurance lead,
**I want** comprehensive performance and stability testing,
**so that** users experience reliable, fast processing.

#### Acceptance Criteria

1. **AC1:** Single-document performance (NFR1): 100 test runs with 2-5K word documents, validate <30s processing time on standard hardware.
2. **AC2:** Batch performance (NFR2): 10 test runs with 50-document batches, validate <30min processing time.
3. **AC3:** Startup time (NFR5): 50 test runs, validate <5 seconds CLI startup (cold start).
4. **AC4:** Crash/error rate (NFR6): 1000+ operations across all commands, validate <10% error rate.
5. **AC5:** Memory profiling: Verify no memory leaks during batch processing, stays within 8GB RAM constraint (NFR4).
6. **AC6:** Stress testing: Process 100-document batch, validate behavior (should complete or fail gracefully with clear errors).
7. **AC7:** Performance regression testing: Compare to Epic 2-3 baseline, ensure no degradation.
8. **AC8:** Performance report created: Metrics summary, hardware specifications used, optimization recommendations for Phase 2.

---

### Story 4.6: Beta Feedback Integration & Bug Fixes

**As a** product manager,
**I want** to address critical bugs and usability issues discovered during beta testing,
**so that** the launch version provides a polished user experience.

#### Acceptance Criteria

1. **AC1:** Beta feedback analyzed: Categorize issues by severity (critical, high, medium, low) and type (bug, usability, feature request).
2. **AC2:** Critical bugs fixed: Anything causing data loss, crashes, incorrect pseudonymization, or security issues.
3. **AC3:** High-priority usability issues addressed: Confusing errors, unintuitive workflows, documentation gaps.
4. **AC4:** Medium issues triaged: Fix if time allows, defer to post-launch updates if necessary.
5. **AC5:** Low priority and feature requests: Document for Phase 2 consideration, provide clear roadmap communication.
6. **AC6:** Bug fix testing: Regression tests for all fixes, validate no new issues introduced.
7. **AC7:** Beta testers notified: Release notes with fixes, request final verification.
8. **AC8:** Launch readiness review: PM/Dev/QA sign-off that product is ready for public release.

---

### Story 4.7: Final Launch Preparation

**As a** product manager,
**I want** all launch materials ready for public early adopter release,
**so that** users can discover, adopt, and successfully use the tool.

#### Acceptance Criteria

1. **AC1:** PyPI package published: `gdpr-pseudonymizer` v1.0.0 available via `pip install gdpr-pseudonymizer`.
2. **AC2:** GitHub repository public: README, documentation links, contributing guide, code of conduct, license (open-source, likely MIT or Apache 2.0).
3. **AC3:** Release announcement prepared: Blog post or article describing project, use cases, key features, getting started.
4. **AC4:** Community channels established: GitHub Discussions or forum for user questions, issue reporting.
5. **AC5:** Outreach plan executed: Post to relevant communities (Reddit r/datascience, r/privacy, academic mailing lists, LinkedIn).
6. **AC6:** Early adopter targets contacted: Direct outreach to identified potential users (researchers, enterprises).
7. **AC7:** Support process documented: How users get help, expected response times, escalation path.
8. **AC8:** Success metrics tracking setup: User count, downloads, GitHub stars, issue volume, community activity.

---

## Checklist Results Report

### Executive Summary

**Overall PRD Completeness:** 95%

**MVP Scope Appropriateness:** Just Right - The scope has been carefully refined through multiple elicitation cycles to focus on essential features while maintaining viability.

**Readiness for Architecture Phase:** Ready - The PRD provides clear technical guidance, comprehensive requirements, and well-structured epics with detailed acceptance criteria.

**Most Critical Success Factor:** NLP library accuracy validation in Epic 0-1 (Week 0-2) is THE critical path decision that determines MVP viability.

---

### Category Analysis Table

| Category                         | Status  | Critical Issues                                                           |
| -------------------------------- | ------- | ------------------------------------------------------------------------- |
| 1. Problem Definition & Context  | PASS    | None - Goals, background, and brief provide comprehensive context         |
| 2. MVP Scope Definition          | PASS    | None - Clear boundaries with what's in/out of scope                       |
| 3. User Experience Requirements  | PASS    | CLI-only MVP; UX section appropriately skipped, addressed in requirements |
| 4. Functional Requirements       | PASS    | 21 FRs comprehensive with compositional logic well-specified              |
| 5. Non-Functional Requirements   | PASS    | 15 NFRs with measurable thresholds tied to success criteria               |
| 6. Epic & Story Structure        | PASS    | 5 epics (0-4) with 32 stories total, appropriate sizing and sequencing   |
| 7. Technical Guidance            | PASS    | Comprehensive technical assumptions with resolved architecture decisions  |
| 8. Cross-Functional Requirements | PASS    | Data layer, encryption, audit logging well-defined                        |
| 9. Clarity & Communication       | PASS    | PRD refined through multiple elicitation cycles for clarity               |

**Overall Assessment:** PASS (95% complete)

---

### Top Issues by Priority

#### BLOCKERS: None

All potential blockers have been addressed through elicitation and refinement:
- ✅ NLP accuracy risk: Week 0 benchmark with go/no-go decision and contingency plans
- ✅ Compositional logic complexity: Epic 2 extended to 4 weeks, comprehensively specified through user feedback
- ✅ Installation risk: SQLCipher→Python-native encryption change
- ✅ Validation mode ambiguity: Resolved (optional via `--validate`, default OFF)

#### HIGH: None

Quality is comprehensive across all categories.

#### MEDIUM: 1 Item

**M1: LLM API Access Not Yet Secured (Epic 4 Story 4.1)**
- Story 4.1 AC1 requires OpenAI and Anthropic API keys for LLM utility testing
- Budget allocation ($50-100) mentioned but not confirmed
- **Recommendation:** Secure API access and budget approval before Epic 4 begins (week 11)
- **Impact if not addressed:** Cannot validate NFR10 (80% LLM utility preservation), blocks launch readiness

---

### Final Decision

**✅ READY FOR ARCHITECT**

**The PRD and epics are comprehensive, properly structured, and ready for architectural design.**

**Justification:**
- **95% completeness** across all 9 checklist categories (all PASS)
- **Zero blockers** - all critical risks addressed with mitigation plans
- **MVP scope is appropriate** - focused on essential features while maintaining viability
- **Technical guidance is clear** - architecture decisions resolved, constraints documented
- **Epic/story structure is solid** - 32 stories across 5 epics with clear dependencies
- **Requirements are testable** - comprehensive acceptance criteria and NFR thresholds
- **Timeline is realistic** - 13 weeks with built-in buffers for known risks

**Only 1 medium-priority item (LLM API access)** should be addressed before development begins, but does not block architecture phase.

**Next Steps:**
1. **Immediate:** Secure LLM API access and budget
2. **This Week:** Finalize PRD with minor additions (LLM API requirements note)
3. **Next Week:** Handoff to Architect for architecture design phase
4. **Week -1 to 0:** Execute Epic 0 (pre-sprint preparation) while architecture is designed

---

## Next Steps

### UX Expert Prompt

*Note: While the MVP is CLI-only, this prompt is included for Phase 2 GUI planning.*

The GDPR Pseudonymizer MVP (CLI tool) is now defined in the PRD. Phase 2 will introduce a GUI to expand accessibility beyond technical users.

Please review [docs/prd.md](docs/prd.md) and [docs/brief.md](docs/brief.md), then design the Phase 2 GUI architecture considering:

- **Target Users:** Non-technical researchers, HR professionals, compliance officers (low CLI comfort)
- **Core Workflows:** Drag-and-drop document processing, visual entity review/editing, batch progress visualization, configuration management
- **Key Constraints:** Maintain local-first architecture (no cloud dependencies), cross-platform desktop app (Windows/Mac/Linux), preserve security model (encrypted mapping tables)
- **Phase 1 Integration:** GUI should wrap existing CLI core logic, not duplicate it
- **Accessibility:** WCAG AA compliance for professional/academic contexts

Deliverables: UX architecture document with wireframes, interaction patterns, and implementation guidance.

---

### Architect Prompt

The GDPR Pseudonymizer PRD is complete and ready for architectural design.

Please review [docs/prd.md](docs/prd.md) and [docs/brief.md](docs/brief.md), then create the architecture document addressing:

**Critical Decisions (Week 0 Prerequisites):**
- NLP library selection validation (spaCy vs Stanza benchmark protocol - Story 0.3, 1.2)
- Test corpus annotation methodology and quality standards

**Core Architecture (Epic 1-2 Foundation):**
- Module structure and interfaces (cli, core, nlp, data, pseudonym, utils layers)
- Compositional pseudonymization algorithm design (FR4-5-20 implementation approach)
- Data layer design (SQLite schema, Python-native encryption implementation, query patterns)
- Error handling taxonomy and recovery strategies

**Scalability & Performance (Epic 2-3):**
- Process-based batch processing architecture (worker pool management, IPC, state sharing)
- Caching and idempotency implementation (FR19)
- Performance optimization strategies (lazy loading, memory management)

**Quality & Testing (All Epics):**
- Testing strategy details (unit/integration/performance test structure, mocking approaches)
- CI/CD pipeline specifics (GitHub Actions workflow, platform matrix)
- Quality gates per epic (when to block vs warn)

**Constraints:**
- Local-only processing (no network dependencies)
- Consumer hardware target (8GB RAM, dual-core CPU)
- Python 3.9+ cross-platform compatibility
- NFR thresholds (90% accuracy, <30s single-doc, <30min 50-doc batch)

Deliverables: Architecture document with system diagrams, module specifications, data models, and Epic 0-1 implementation guidance.

---

*This PRD was created using the BMAD-METHOD™ framework with interactive elicitation and multi-perspective validation.*
