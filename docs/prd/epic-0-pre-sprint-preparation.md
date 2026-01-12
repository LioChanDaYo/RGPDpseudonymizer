# Epic 0: Pre-Sprint Preparation

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
