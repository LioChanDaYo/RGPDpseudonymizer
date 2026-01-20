# Epic 1: Foundation & NLP Validation (v2 - RESCOPED)

**Epic Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, implement mandatory validation UI, and deliver a working "walking skeleton" CLI command with human-in-the-loop verification.

**Duration:** Week 1-5 (EXTENDED from 4 weeks to 5 weeks)

**CRITICAL CHANGES (Post-Story 1.2):**
1. ✅ **spaCy selected** (29.5% F1 vs Stanza 11.9% F1) - Decision made
2. 🔴 **NEW Story 1.7:** Validation UI Implementation (moved from Epic 3) - **CRITICAL PATH**
3. 🔴 **NEW Story 1.8:** Hybrid Detection Strategy (NLP + Regex patterns)
4. ⚠️ **Timeline extended:** 4 weeks → 5 weeks to accommodate validation UI priority

---

## Key Changes from Original Epic 1

| Change | Rationale | Impact |
|--------|-----------|--------|
| **Story 1.2:** Benchmark complete, spaCy selected | Both libraries failed 85% threshold; spaCy best available (29.5% vs 11.9%) | Go/No-Go decision: GO with contingency |
| **NEW Story 1.7:** Validation UI Implementation | Mandatory validation required due to accuracy limitations | +1 week to Epic 1 timeline |
| **NEW Story 1.8:** Hybrid Detection (NLP + Regex) | Improve from 29.5% → 40-50% F1 to reduce validation burden | +3-4 days to Epic 1 timeline |
| **Updated DoD:** Validation UI functional (not deferred to Epic 3) | Validation is core MVP, not optional feature | High priority shift |

---

## Epic 1 Story List (Updated)

| Story | Status | Priority | Est. Duration | Changes |
|-------|--------|----------|---------------|---------|
| 1.1: Expand Test Corpus | ✅ DONE | HIGH | 3-4 days | No change |
| 1.2: NLP Benchmark | ✅ DONE | CRITICAL | 2-3 days | **COMPLETE - spaCy selected** |
| 1.3: CI/CD Pipeline | 🔄 IN PROGRESS | HIGH | 2-3 days | No change |
| 1.4: Project Foundation | ⏳ PENDING | HIGH | 3-4 days | Updated: Add validation module |
| 1.5: Walking Skeleton | ⏳ PENDING | HIGH | 2-3 days | Updated: Include validation stub |
| 1.6: NLP Integration | ⏳ PENDING | CRITICAL | 3-4 days | Updated: spaCy implementation |
| **1.7: Validation UI (NEW)** | ✅ DONE | 🔴 **CRITICAL** | **4-5 days** | **Moved from Epic 3 - COMPLETE** |
| **1.8: Hybrid Detection (NEW)** | ⏳ PENDING | HIGH | **3-4 days** | **New contingency story** |
| **1.9: Entity Deduplication (NEW)** | ⏳ PENDING | 🔴 **CRITICAL** | **2-3 days** | **Follow-up to Story 1.7 QA** |

**Total Epic 1 Duration:** 24-33 days (5-6.5 weeks) → **Recommend 6 weeks with buffer**

---

## Story 1.1: Expand Test Corpus *(✅ COMPLETE - NO CHANGES)*

**Status:** ✅ DONE (25 documents, 1,855 entities annotated)

**As a** developer,
**I want** a comprehensive test corpus of 20-30 French documents with ground truth annotations,
**so that** I can rigorously benchmark NLP library accuracy and track quality metrics throughout development.

### Completion Summary

- ✅ 25 French documents (15 interview transcripts, 10 business documents)
- ✅ 1,855 total entities: 1,627 PERSON, 123 LOCATION, 105 ORG
- ✅ Ground truth annotations validated
- ✅ Comprehensive edge cases included (compound names, titles, abbreviations)

---

## Story 1.2: NLP Benchmark *(✅ COMPLETE - DECISION MADE)*

**Status:** ✅ DONE - **spaCy selected** (see [docs/nlp-benchmark-report.md](../nlp-benchmark-report.md))

**As a** product manager,
**I want** rigorous accuracy comparison between spaCy and Stanza on our French test corpus,
**so that** I can make an evidence-based decision on which library meets our ≥85% accuracy threshold.

### Completion Summary

**Results:**
- spaCy F1: 29.54% (FAIL - below 85% threshold)
- Stanza F1: 11.89% (FAIL - below 85% threshold)

**Decision:** spaCy selected (2.5x better than Stanza)

**Contingency Plan Activated:**
- ✅ Option 1: Lower threshold + mandatory validation mode
- ✅ Option 3: Hybrid approach (NLP + regex patterns)
- 🔄 Option 2: Fine-tuning deferred to v1.1 (post-MVP)

**Architecture Updated:**
- [docs/architecture/3-tech-stack.md](../architecture/3-tech-stack.md) line 9-10 updated
- Benchmark report: [docs/nlp-benchmark-report.md](../nlp-benchmark-report.md)

---

## Story 1.3: CI/CD Pipeline Setup *(UNCHANGED)*

**As a** developer,
**I want** automated testing pipeline running on every commit across multiple platforms,
**so that** I can catch regressions early and ensure cross-platform compatibility throughout development.

### Acceptance Criteria

1. **AC1:** GitHub Actions workflow configured with test matrix: Windows 11, macOS (latest), Ubuntu 22.04.
2. **AC2:** Workflow runs on every push and pull request: install dependencies, run pytest, report coverage.
3. **AC3:** Code quality checks integrated: Black formatting verification, Ruff linting, mypy type checking.
4. **AC4:** Test execution time <5 minutes for unit tests, <15 minutes including integration tests.
5. **AC5:** Failed checks block PR merges (branch protection rules configured).
6. **AC6:** Coverage reporting integrated (codecov or similar), minimum 80% coverage threshold enforced.
7. **AC7:** CI/CD documentation created: workflow description, how to run locally, troubleshooting common failures.

---

## Story 1.4: Project Foundation & Module Structure *(UPDATED)*

**As a** developer,
**I want** clean module boundaries and project structure established,
**so that** I can build features in Epic 2-3 without architectural refactoring.

### Acceptance Criteria

1. **AC1 (UPDATED):** Package structure created following Technical Assumptions architecture:
   - `gdpr_pseudonymizer/cli/` - Command-line interface layer
   - `gdpr_pseudonymizer/core/` - Core processing orchestration
   - `gdpr_pseudonymizer/nlp/` - NLP engine (entity detection)
   - `gdpr_pseudonymizer/data/` - Data layer (mapping tables, audit logs)
   - `gdpr_pseudonymizer/pseudonym/` - Pseudonym manager
   - `gdpr_pseudonymizer/utils/` - Utilities (encryption, file handling)
   - **`gdpr_pseudonymizer/validation/` - Validation UI module (human-in-the-loop)** ⭐ NEW

2. **AC2:** spaCy integrated as modular component with interface abstraction (allows future library swapping).

3. **AC3:** Basic configuration management: support for `.gdpr-pseudo.yaml` config files (home directory and project root).

4. **AC4:** Logging framework established: structured logging with configurable verbosity levels.

5. **AC5:** Unit tests created for each module demonstrating testability.

6. **AC6:** Module dependency graph documented (no circular dependencies).

7. **AC7 (NEW):** Validation module structure defined:
   - `validation/ui.py` - CLI UI components (entity display, user input)
   - `validation/models.py` - Validation data models (entity review state)
   - `validation/workflow.py` - Validation workflow orchestration

---

## Story 1.5: Walking Skeleton - Basic Process Command *(UPDATED)*

**As a** developer,
**I want** a simple end-to-end `process` command that performs naive pseudonymization with validation stub,
**so that** I can validate the CLI→validation→processing→output pipeline before implementing complex algorithms.

### Acceptance Criteria

1. **AC1:** CLI framework (Typer) integrated with basic command structure: `gdpr-pseudo process <file> --validate`.

2. **AC2:** Command reads input file (.txt or .md), performs naive pseudonymization (simple find-replace from hardcoded list), writes output file.

3. **AC3:** Basic error handling: file not found, invalid file format, permission errors with clear error messages.

4. **AC4:** Logging output shows: file processed, entities detected (count), pseudonyms applied (count), output location.

5. **AC5 (UPDATED):** Validation stub implemented:
   - Detects entities (hardcoded list)
   - Displays entities in simple CLI format
   - Prompts user: "Confirm pseudonymization? (y/n)"
   - Applies pseudonyms on confirmation

6. **AC6:** Unit tests validate: file I/O, basic replacement logic, error handling paths, validation stub flow.

7. **AC7:** Integration test: process sample document end-to-end with validation stub, verify output correctness.

8. **AC8:** Can demo to stakeholders: "This is the skeleton we're building on, including human-in-the-loop validation."

---

## Story 1.6: NLP Integration with Basic Entity Detection *(UPDATED)*

**As a** user,
**I want** the system to automatically detect personal names in French documents using spaCy,
**so that** I don't have to manually identify entities for pseudonymization.

### Acceptance Criteria

1. **AC1 (UPDATED):** spaCy integrated into `nlp` module with `fr_core_news_lg` model.

2. **AC2:** Entity detection function created: accepts document text, returns list of detected entities with types (PERSON, LOCATION, ORG), positions, and confidence scores.

3. **AC3:** `process` command (from Story 1.5) updated to use spaCy detection instead of hardcoded list.

4. **AC4 (UPDATED):** Detection accuracy baseline established:
   - **Realistic expectation:** 29.5% F1 score (from Story 1.2 benchmark)
   - **Target with hybrid approach (Story 1.8):** 40-50% F1 estimated
   - No longer expecting ≥85% F1 (contingency plan accepted)

5. **AC5:** Processing performance measured: meets or approaches NFR1 target (<30s for 2-5K word document) on standard hardware.

6. **AC6 (UPDATED):** False negative tracking: Log entities in ground truth corpus missed by NLP.
   - **Current rate:** ~70% miss rate (29.5% recall)
   - **Acceptable with mandatory validation:** Users will catch false negatives

7. **AC7:** False positive handling: Detected entities that aren't sensitive data logged.
   - **Current rate:** ~73% false positive rate (26.96% precision)
   - **Mitigation:** Validation UI allows users to reject false positives

8. **AC8:** Unit tests: NLP integration, entity extraction, error handling (model not found, corrupt document).

9. **AC9:** Integration test: Process test corpus documents, compare detected entities to ground truth, validate detection works (even if accuracy low).

10. **AC10 (NEW):** Documentation updated with realistic accuracy expectations:
    - README.md: "AI-assisted detection (40-50% automatic) + mandatory human verification"
    - Architecture docs: Accuracy limitations documented

---

## Story 1.7: Validation UI Implementation *(NEW - CRITICAL PATH)*

**As a** user,
**I want** an intuitive CLI interface to review and confirm detected entities,
**so that** I can ensure 100% accuracy despite AI limitations while minimizing review time.

**PRIORITY:** 🔴 **CRITICAL** - This is now core MVP functionality (not Epic 3 optional feature)

### Context

Following Story 1.2 benchmark (29.5% F1), validation mode is **MANDATORY** for MVP. Users will spend 80% of interaction time in validation workflow. This must be polished, fast, and intuitive.

### Acceptance Criteria

1. **AC1:** Validation UI implemented using `rich` library (as specified in Epic 0 Story 0.4):
   - `rich.table.Table` for entity display
   - `rich.prompt.Confirm` for yes/no decisions
   - `rich.console.Console` for color-coded output
   - `rich.panel.Panel` for grouped sections

2. **AC2:** Entity presentation layout:
   - Group by entity type (PERSON, LOCATION, ORG)
   - Show context (10 words before/after entity)
   - Display confidence score (from spaCy if available)
   - Highlight entity in context snippet
   - Show suggested pseudonym

3. **AC3:** User actions implemented:
   - ✅ **Confirm:** Accept entity and pseudonym (Space key)
   - ❌ **Reject:** Remove false positive (R key)
   - ✏️ **Modify:** Edit entity text (E key)
   - ➕ **Add:** Manually add missed entity (A key)
   - 🔄 **Change Pseudonym:** Override suggestion (C key)
   - ⏭️ **Next/Previous:** Navigate entities (N/P keys or arrow keys)
   - 📦 **Batch actions:** Accept all PERSON entities, reject all low-confidence ORG (custom)

4. **AC4:** Validation workflow steps:
   - **Step 1:** Show summary screen (X entities detected, Y PERSON, Z LOCATION, etc.)
   - **Step 2:** Review entities by type (PERSON → ORG → LOCATION priority)
   - **Step 3:** Flag ambiguous standalone components (FR4 logic integration)
   - **Step 4:** Final confirmation with summary of changes
   - **Step 5:** Process document with validated entities

5. **AC5:** Performance optimization:
   - Lazy loading: Display 10 entities per page (pagination)
   - Precompute context snippets during entity detection
   - Cache document text for fast lookups
   - Target: <2 minutes validation time for 2-5K word document

6. **AC6:** Accessibility:
   - Keyboard-only navigation (no mouse required)
   - Color-blind safe palette (use symbols + colors)
   - Clear help text (H key for help overlay)
   - Responsive layout (works in 80x24 terminal)

7. **AC7:** Error handling:
   - Invalid key press: Show inline hint
   - Empty entity detection: Show "No entities found" message with option to add manually
   - 100+ entities: Show warning "Large document detected, review may take 5-10 minutes"

8. **AC8:** Unit tests:
   - Entity display rendering (mock rich console)
   - User input handling (keyboard events)
   - Batch action logic
   - Workflow state management

9. **AC9:** Integration test:
   - Process sample document through full validation workflow
   - Simulate user actions (confirm, reject, modify)
   - Verify final output reflects user decisions

10. **AC10:** User testing:
    - 2-3 target users test validation UI with real documents
    - Measure time to complete validation (target: <2 min per doc)
    - Collect feedback: "Helpful or burdensome?" (target: ≥4/5 rating)
    - Iterate on UX based on feedback

11. **AC11 (CRITICAL):** Validation mode is ALWAYS ON by default:
    - `--validate` flag is not required (validation is mandatory)
    - Future: `--no-validate` flag can be added in v1.1 (not MVP)
    - CLI help text clarifies: "Validation is required for accuracy assurance"

### Example Validation Workflow (User Journey)

```
Step 1: Summary
────────────────────────────────────────────────────────
📄 Processing: interview_transcript_01.txt (2,340 words)

🔍 Detected: 23 entities
   • 15 PERSON entities
   • 5 LOCATION entities
   • 3 ORG entities

Estimated review time: 2-3 minutes

Press Enter to begin review...
────────────────────────────────────────────────────────

Step 2: Entity Review (PERSON)
────────────────────────────────────────────────────────
👤 PERSON Entities (15 found)                    [1/15]

Entity: Marie Dubois
Context: "...during the interview with Marie Dubois about..."
Pseudonym: → Leia Organa
Confidence: 95% ████████████████████░

[✓] Confirm  [R] Reject  [E] Edit  [C] Change pseudonym  [N] Next

> User presses Space (Confirm) ✅

────────────────────────────────────────────────────────

[Continues for all 15 PERSON entities...]

Step 3: Final Confirmation
────────────────────────────────────────────────────────
✅ Validation Complete

Summary of changes:
• Confirmed: 20 entities
• Rejected: 2 false positives
• Modified: 1 entity (expanded "Marie" → "Marie Dubois")
• Added: 3 missed entities

Ready to process document? [Y/n]

> User presses Y ✅

🔄 Processing... ████████████████████ 100%

✅ Success! Pseudonymized document saved:
   Output: interview_transcript_01_pseudonymized.txt
   Entities replaced: 23
   Time: 2m 15s (2m 10s review + 5s processing)
────────────────────────────────────────────────────────
```

### Technical Implementation Notes

**Architecture:**
```
gdpr_pseudonymizer/validation/
├── ui.py              # Rich UI components (EntityTable, ReviewScreen)
├── models.py          # ValidationSession, EntityReviewState
├── workflow.py        # ValidationWorkflow orchestrator
├── actions.py         # User action handlers (confirm, reject, modify)
└── tests/
    ├── test_ui.py     # UI component tests
    ├── test_workflow.py  # Workflow integration tests
    └── fixtures.py    # Test data (mock entities)
```

**Key Classes:**
- `ValidationSession`: Manages validation state (entities, user decisions)
- `EntityReviewState`: Tracks per-entity status (pending, confirmed, rejected, modified)
- `ReviewScreen`: Rich-based UI screen manager
- `ValidationWorkflow`: Orchestrates multi-step validation flow

**Dependencies:**
- `rich>=13.7` (already in tech stack)
- `typing_extensions` for TypedDict (Python 3.9 compatibility)

---

## Story 1.8: Hybrid Detection Strategy *(NEW - CONTINGENCY PLAN)*

**As a** user,
**I want** improved entity detection using hybrid NLP + regex patterns,
**so that** I spend less time reviewing entities (40-50% detection vs 29.5% baseline).

**PRIORITY:** HIGH - Reduces validation burden, improves user experience

### Context

Story 1.2 showed spaCy achieves only 29.5% F1 (recall ~33%, precision ~27%). Contingency plan Option 3 adds regex-based fallback patterns to improve detection to estimated 40-50% F1.

**Goal:** Detect additional entities that spaCy misses using French-specific patterns.

### Acceptance Criteria

1. **AC1:** Regex pattern library created for French entities:
   - **Titles:** "M. [Name]", "Mme [Name]", "Dr. [Name]", "Pr. [Name]"
   - **Full names:** "[Firstname] [Lastname]" patterns with French name lists
   - **Compound names:** "Jean-Pierre", "Marie-Claire" (hyphenated first names)
   - **Location indicators:** "à [City]", "en [Country]", "ville de [City]"
   - **Organization patterns:** "Société [Name]", "[Name] SA", "[Name] SARL"

2. **AC2:** French name dictionaries integrated:
   - **Source:** INSEE most common French first/last names (public domain)
   - **Size:** Top 500 first names, top 500 last names
   - **Format:** JSON file in `data/french_names.json`
   - **Usage:** Improve "Firstname Lastname" pattern matching

3. **AC3:** Hybrid detection pipeline implemented:
   - **Step 1:** Run spaCy NER (baseline detection)
   - **Step 2:** Run regex pattern matching on same text
   - **Step 3:** Merge results (deduplicate, prefer spaCy entities for overlaps)
   - **Step 4:** Return combined entity list to validation workflow

4. **AC4:** Deduplication logic:
   - If spaCy detects "Marie Dubois" at position 50-62 and regex detects same span: keep spaCy entity (has confidence score)
   - If regex detects "M. Dubois" at position 100-109 and spaCy missed it: add as new entity (confidence: regex)
   - Flag overlapping but non-identical entities for user review (e.g., spaCy: "Dubois", regex: "M. Dubois")

5. **AC5:** Performance measurement:
   - Benchmark hybrid approach on 25-document test corpus
   - Target: 40-50% F1 score (vs 29.5% spaCy baseline)
   - Measure processing time impact (should remain <30s per document)

6. **AC6:** Confidence score handling:
   - spaCy entities: Use spaCy confidence if available (not always provided)
   - Regex entities: Assign confidence based on pattern type (high: title patterns, medium: name dictionary matches, low: generic patterns)
   - Display confidence in validation UI to help user prioritize review

7. **AC7:** Configuration:
   - Regex patterns stored in `config/detection_patterns.yaml`
   - User can enable/disable specific pattern categories
   - Default: All patterns enabled for MVP

8. **AC8:** Unit tests:
   - Each regex pattern tested individually
   - Deduplication logic validated
   - Hybrid pipeline integration tested
   - Performance regression tests (processing time)

9. **AC9:** Integration test:
   - Process test corpus with hybrid detection
   - Compare results to baseline (spaCy only)
   - Validate improved recall (should detect more entities)
   - Acceptable precision trade-off (some regex false positives are okay - validation catches them)

10. **AC10:** Documentation:
    - Hybrid detection approach documented in architecture
    - Regex patterns documented with examples
    - Performance comparison table (spaCy only vs hybrid)

### Example Regex Patterns

```python
FRENCH_PATTERNS = {
    "titles": [
        r"\b(M\.|Mme|Mlle|Dr\.|Pr\.)\s+([A-Z][a-zéèêëàâäôöùûü]+(?:\s+[A-Z][a-zéèêëàâäôöùûü]+)?)",
        # Matches: "M. Dupont", "Dr. Marie Dubois", "Mme Laurent"
    ],
    "compound_names": [
        r"\b([A-Z][a-zéèêëàâäôöùûü]+-[A-Z][a-zéèêëàâäôöùûü]+)\b",
        # Matches: "Jean-Pierre", "Marie-Claire"
    ],
    "location_indicators": [
        r"\b(à|en|dans|près de)\s+([A-Z][a-zéèêëàâäôöùûü]+(?:\s+[A-Z][a-zéèêëàâäôöùûü]+)?)",
        # Matches: "à Paris", "en France", "près de Lyon"
    ],
    "organizations": [
        r"\b([A-Z][A-Za-zéèêëàâäôöùûü\s]+)\s+(SA|SARL|SAS|EURL)\b",
        # Matches: "Acme Corporation SA", "Tech Solutions SARL"
    ],
}
```

### Expected Impact

| Metric | spaCy Baseline | Hybrid Target | Improvement |
|--------|----------------|---------------|-------------|
| **Recall (PERSON)** | 31.28% | 45-55% | +14-24% |
| **Recall (LOCATION)** | 58.54% | 65-75% | +7-17% |
| **Recall (ORG)** | 23.81% | 30-40% | +6-16% |
| **Overall F1** | 29.54% | 40-50% | +10-20% |
| **User validation time** | ~4-5 min/doc | ~2-3 min/doc | -40-50% |

**Validation:** User spends less time adding missed entities, more time confirming detections.

---

## Story 1.9: Entity Deduplication *(NEW - CRITICAL FOLLOW-UP)*

**As a** user,
**I want** entities with identical text grouped during validation,
**so that** I can validate once and apply my decision to all occurrences automatically.

**PRIORITY:** 🔴 **CRITICAL** - Addresses scalability blocker identified in Story 1.7 QA review

### Context

Story 1.7 QA review (Quality Score: 75/100, Gate: CONCERNS) identified critical deduplication issue:
- **Problem:** Same entity text validated multiple times (e.g., "Marie Dubois" × 10 = 10 separate validations)
- **Impact:** Makes 100+ entity documents impractical - user testing showed validation fatigue
- **User skipped doc5 (100 entities)** during testing due to redundant validation
- **See:** [docs/qa/gates/1.7-validation-ui-implementation.yml](../qa/gates/1.7-validation-ui-implementation.yml)

### Acceptance Criteria

1. **AC1:** Entity grouping by unique (text, entity_type) combination:
   - Group all DetectedEntity instances with identical text and entity_type
   - Maintain list of all occurrences (positions) for each unique entity
   - Example: "Marie Dubois" (PERSON) at positions [10-22, 145-157, 890-902] = 1 group, 3 occurrences

2. **AC2:** UI displays occurrence count:
   - Summary screen shows: "15 unique entities (45 total occurrences)"
   - Review screen shows: "Marie Dubois (3 occurrences)" with first occurrence context
   - Option to view all occurrence contexts (V key during review)

3. **AC3:** User decision applies to all occurrences:
   - Confirm entity → All occurrences confirmed
   - Reject entity → All occurrences rejected
   - Modify entity text → All occurrences updated with new text
   - Change pseudonym → All occurrences use same pseudonym

4. **AC4:** Position tracking maintained for pseudonymization:
   - Store all (start_pos, end_pos) tuples for each unique entity
   - Apply pseudonymization to all occurrence positions
   - Replace from end to start to preserve character positions

5. **AC5:** ValidationSession model updated:
   - Add EntityGroup dataclass with fields: unique_key (text, entity_type), occurrences (List[DetectedEntity]), user_decision
   - Update workflow to iterate through EntityGroups instead of individual entities
   - Return expanded List[DetectedEntity] after validation (all occurrences with decisions applied)

6. **AC6:** Performance validation:
   - Test with doc5 (100 entities, ~30 unique entities expected)
   - Target validation time: <5 minutes for 100 entity document (vs impractical without deduplication)
   - Measure unique entity count vs total entity count ratio

7. **AC7:** Edge case handling:
   - Same text, different entity types: Treat as separate groups (e.g., "Paris" LOCATION vs "Paris" PERSON)
   - Modified entity text creates new unique key: Original occurrences keep old key, modified entity gets new key
   - Added entities: Treated as unique with 1 occurrence

8. **AC8:** Unit tests:
   - Entity grouping logic (multiple occurrences, different types, modified entities)
   - User decision propagation to all occurrences
   - Position tracking and pseudonymization application
   - EntityGroup data model tests

9. **AC9:** Integration test:
   - Full validation workflow with duplicate entities
   - Verify all occurrences receive same decision
   - Verify pseudonymization replaces all occurrences correctly

10. **AC10:** User testing (follow-up):
    - Test with doc5 (100 entities) after deduplication implemented
    - Target completion rate: ≥90% (vs 0% before deduplication)
    - Target validation time: <5 minutes
    - Collect feedback on occurrence display clarity

### Example Behavior

**Before Deduplication (Story 1.7):**
```
Validating entity 1/50: "Marie Dubois" (PERSON) → Confirm
Validating entity 2/50: "TechCorp" (ORG) → Reject
...
Validating entity 15/50: "Marie Dubois" (PERSON) → Confirm  [REDUNDANT!]
...
Validating entity 32/50: "Marie Dubois" (PERSON) → Confirm  [REDUNDANT!]
```
**User validates "Marie Dubois" 10 times = extreme fatigue**

**After Deduplication (Story 1.9):**
```
Validating 15 unique entities (50 total occurrences)

Entity 1/15: "Marie Dubois" (PERSON) - 10 occurrences
  Context: "...during the interview with Marie Dubois about..."
  [V] View all occurrence contexts
  Action: Confirm → All 10 occurrences confirmed ✓

Entity 2/15: "TechCorp" (ORG) - 5 occurrences
  Context: "...position at TechCorp as..."
  Action: Reject → All 5 occurrences rejected ✗
```
**User validates "Marie Dubois" ONCE, decision applies to all 10 occurrences**

### Data Model Changes

**New EntityGroup Model:**

```python
@dataclass
class EntityGroup:
    """Groups entities with identical text and type."""
    unique_key: tuple[str, str]  # (text, entity_type)
    occurrences: list[DetectedEntity]  # All occurrences of this entity
    user_decision: UserDecision | None = None

    @property
    def text(self) -> str:
        return self.unique_key[0]

    @property
    def entity_type(self) -> str:
        return self.unique_key[1]

    @property
    def occurrence_count(self) -> int:
        return len(self.occurrences)

    def get_first_occurrence(self) -> DetectedEntity:
        """Returns first occurrence for display context."""
        return self.occurrences[0]
```

**Updated ValidationSession:**

```python
@dataclass
class ValidationSession:
    entity_groups: list[EntityGroup]  # Changed from entities: list[DetectedEntity]
    document_text: str
    # ... rest unchanged

    def get_validated_entities(self) -> list[DetectedEntity]:
        """Expands entity groups back to individual occurrences with decisions applied."""
        validated = []
        for group in self.entity_groups:
            if group.user_decision and group.user_decision.action != "REJECT":
                # Apply decision to all occurrences
                for entity in group.occurrences:
                    validated.append(entity)
        return validated
```

### Expected Impact

| Metric | Before (Story 1.7) | After (Story 1.9) | Improvement |
|--------|-------------------|-------------------|-------------|
| **Validation time (100 entity doc)** | Impractical (skipped) | <5 minutes | Enables large docs |
| **Unique entities (typical doc)** | N/A | ~30% of total | 70% reduction in reviews |
| **User completion rate** | 0% (doc5 skipped) | ≥90% | Unblocks scalability |
| **User satisfaction** | 4/5 (would be 5/5) | 5/5 (estimated) | Peak UX |

### Dependencies

- Story 1.7 MUST be complete (validation UI foundation)
- See QA review findings: [docs/qa/gates/1.7-validation-ui-implementation.yml](../qa/gates/1.7-validation-ui-implementation.yml)

---

## Epic 1 Definition of Done (UPDATED)

- ✅ **spaCy selected** (29.5% F1, best available option) - **Story 1.2** ⭐ COMPLETE
- ✅ CI/CD pipeline operational (GitHub Actions testing on 2+ platforms) - **Story 1.3**
- ✅ Project foundation with validation module structure - **Story 1.4**
- ✅ Walking skeleton: Basic `process` command with validation stub - **Story 1.5**
- ✅ spaCy NLP integration functional - **Story 1.6**
- ✅ **Validation UI fully implemented and user-tested** - **Story 1.7** ⭐ CRITICAL COMPLETE
- ✅ **Entity deduplication enables 100+ entity documents** - **Story 1.9** ⭐ CRITICAL NEW
- ✅ **Hybrid detection (NLP + regex) achieves 40-50% F1 estimated** - **Story 1.8** ⭐ NEW
- ✅ Can demonstrate AI-assisted pseudonymization with human-in-the-loop validation - **Updated demo**
- ✅ **PM sign-off on "assisted mode" positioning** - **Contingency plan approved**

---

## Dependencies & Risks

### Critical Path

```
Story 1.2 (Benchmark) ✅ DONE
    ↓
Story 0.4 (Validation UI Design) → Epic 0
    ↓
Story 1.4 (Project Foundation with validation module)
    ↓
Story 1.5 (Walking Skeleton with validation stub)
    ↓
Story 1.7 (Validation UI Implementation) ← CRITICAL BOTTLENECK
    ↓
Story 1.6 (NLP Integration) + Story 1.8 (Hybrid Detection) ← Can parallelize
```

**Bottleneck:** Story 1.7 (Validation UI) is on critical path and high complexity (4-5 days).

**Mitigation:**
- Allocate senior dev to Story 1.7
- Conduct mid-story check-in (day 2-3) to catch UX issues early
- Parallel work: Junior dev implements Story 1.8 (hybrid detection) while senior dev does Story 1.7

---

### Risk 1: Validation UI Takes Longer Than Estimated

**Likelihood:** MEDIUM
**Impact:** HIGH (blocks Epic 1 completion, delays Epic 2)

**Mitigation:**
- Buffer built in: 4-5 days estimate for Story 1.7
- Epic 1 extended to 5 weeks (accommodates overrun)
- MVP validation UI can be basic; polish in Epic 2-3

**Kill Criteria:** If Story 1.7 exceeds 7 days, escalate to PM for de-scoping decision

---

### Risk 2: Hybrid Detection Doesn't Improve Accuracy Meaningfully

**Likelihood:** MEDIUM
**Impact:** MEDIUM (users spend more time validating)

**Scenario:** Hybrid approach only reaches 35% F1 (vs 40-50% target), minimal improvement over baseline.

**Mitigation:**
- Story 1.8 is "nice to have" not "must have" (validation works even with 29.5% baseline)
- If < 40% F1 achieved, document as "v1.0 limitation" and prioritize v1.1 fine-tuning
- User testing will reveal if validation burden is tolerable

**Kill Criteria:** If hybrid detection takes >5 days without reaching 35% F1, abandon and proceed with spaCy baseline only

---

### Risk 3: User Testing Reveals Validation Workflow Too Burdensome

**Likelihood:** LOW-MEDIUM
**Impact:** CRITICAL (product viability question)

**Scenario:** Story 1.7 AC10 user testing shows <3/5 satisfaction, users find validation "annoying" not "helpful"

**Mitigation:**
- Conduct user testing ASAP (week 3-4 of Epic 1)
- Prepare contingency: Delay MVP for fine-tuning (Option 2) if validation rejected
- Alternative: Pivot to "manual-first" tool with AI suggestions (different product)

**Kill Criteria:** If 3/3 user testers rate validation <3/5, STOP and escalate to PM/leadership

---

## Timeline Breakdown (5 Weeks)

### Week 1: Foundation
- **Days 1-2:** Story 1.3 (CI/CD Pipeline)
- **Days 3-5:** Story 1.4 (Project Foundation)

### Week 2: Walking Skeleton + NLP
- **Days 1-2:** Story 1.5 (Walking Skeleton)
- **Days 3-5:** Story 1.6 (NLP Integration - Part 1)

### Week 3: Validation UI (CRITICAL)
- **Days 1-5:** Story 1.7 (Validation UI Implementation)
  - Day 1-2: Core UI components
  - Day 3-4: Workflow integration
  - Day 5: User testing + iteration

### Week 4: Hybrid Detection + Polish
- **Days 1-4:** Story 1.8 (Hybrid Detection Strategy)
- **Day 5:** Story 1.6 (NLP Integration - Part 2, finalization)

### Week 5: Integration + Demo Prep
- **Days 1-2:** Integration testing (all stories together)
- **Days 3-4:** Bug fixes, polish, documentation
- **Day 5:** Epic 1 demo, stakeholder review, Epic 2 planning

---

## Success Metrics (Updated)

Epic 1 is successful if:

1. ✅ spaCy integrated and functional (even with 29.5% F1 baseline)
2. ✅ **Validation UI enables users to complete review in <2 min per document**
3. ✅ **User testing shows ≥4/5 satisfaction** with validation workflow
4. ✅ Hybrid detection improves F1 to ≥35% (stretch goal: 40-50%)
5. ✅ CI/CD pipeline catches regressions (green builds)
6. ✅ Can demonstrate end-to-end assisted pseudonymization workflow to stakeholders
7. ✅ PM approves Epic 1 deliverables before Epic 2 begins

---

## Handoff to Epic 2

**What Epic 2 Receives:**
- ✅ Working CLI with validation UI
- ✅ spaCy NLP integration (baseline or hybrid detection)
- ✅ Module structure ready for feature additions
- ✅ CI/CD pipeline for continuous testing
- ✅ User feedback from validation UI testing

**What Epic 2 Will Build:**
- Compositional pseudonymization logic (FR4-5)
- Encrypted mapping tables
- Pseudonym libraries
- Audit logging
- Production-quality workflows

**Critical Dependencies:**
- Epic 2 Story 2.2 (Compositional Pseudonymization) depends on Story 1.7 (Validation UI) for flagging ambiguous components
- Epic 2 Story 2.4 (Mapping Tables) stores validation user modifications (FR12)

---

## Next Actions

1. **Immediate:** PM approval of rescoped Epic 1 (5 weeks, validation UI priority)
2. **Week 1:** Begin Story 1.3 (CI/CD) + Story 1.4 (Project Foundation)
3. **Week 2-3:** Focus all resources on Story 1.7 (Validation UI) - CRITICAL PATH
4. **Week 3-4:** Conduct user testing (Story 1.7 AC10) - GO/NO-GO checkpoint
5. **Week 5:** Final integration, demo prep, Epic 2 planning

---

**Document Status:** RESCOPED v2.0 (Post-Story 1.2 Benchmark)
**Date:** 2026-01-16
**Approvals Needed:**
- [ ] PM approval of 5-week Epic 1 timeline
- [ ] Dev lead confirmation of Story 1.7 feasibility (4-5 days)
- [ ] Architect review of hybrid detection approach (Story 1.8)
- [ ] Stakeholder buy-in on "assisted mode" as MVP

**Key Decisions Made:**
- ✅ spaCy selected (29.5% F1, contingency plan activated)
- ✅ Validation UI moved to Epic 1 (critical path)
- ✅ Epic 1 extended to 5 weeks
- ✅ Hybrid detection added (Story 1.8) to reduce validation burden
