# Epic 1: Foundation & NLP Validation (Week 1-4)

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
