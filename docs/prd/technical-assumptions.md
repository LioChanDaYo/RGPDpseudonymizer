# Technical Assumptions

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
