# PRD Updates - v2.0 Assisted Mode
## Merge Instructions for Main PRD

**Date:** 2026-01-16
**Context:** Post-Story 1.2 benchmark results, contingency plan approved
**Status:** Ready to merge into [docs/prd.md](../.ignore/prd.md)

---

## Overview of Changes

Following the Story 1.2 NLP benchmark (spaCy: 29.5% F1, Stanza: 11.9% F1), the following PRD sections require updates to reflect the approved "AI-assisted" positioning and mandatory validation mode.

### Summary of Changes
1. **Goals:** Add realistic accuracy expectations
2. **Background Context:** Update value proposition to "AI-assisted"
3. **FR7 & FR18:** Make validation mode MANDATORY by default (not optional)
4. **NFR8-9:** Update accuracy thresholds to reflect hybrid approach
5. **Technical Assumptions:** Document contingency plan decision
6. **Epic 0:** Add Story 0.4 (Validation UI Design)
7. **Epic 1:** Add Stories 1.7-1.8, extend to 5 weeks
8. **Epic List:** Update timeline (13 weeks → 14 weeks)

---

## SECTION 1: Goals *(UPDATE)*

### Current Text (Lines 7-13)
```
### Goals

- Achieve ≥90% NER detection accuracy (precision and recall) on French text benchmark corpus
- Achieve ≥85% installation success rate for first-time users on target platforms
- Validate LLM utility preservation: pseudonymized documents maintain ≥80% usefulness for AI analysis
- Automate entity detection and pseudonymization with 50%+ time savings vs manual redaction for batch processing
- Provide GDPR-compliant pseudonymization with encrypted mapping tables, audit trails, and reversibility
- Enable consistent pseudonymization across document batches (10-100+ files) for corpus-level analysis
- Deliver transparent, cite-able methodology suitable for research ethics board evaluation
```

### Updated Text (REPLACE)
```
### Goals

- **Achieve ≥85% combined accuracy** (AI detection + human verification) on French text benchmark corpus through hybrid approach (NLP + regex patterns + mandatory validation)
- **AI-assisted detection baseline:** 40-50% F1 score (hybrid NLP + regex), with mandatory human verification ensuring 100% coverage
- Achieve ≥85% installation success rate for first-time users on target platforms
- Validate LLM utility preservation: pseudonymized documents maintain ≥80% usefulness for AI analysis
- **Provide AI-assisted entity detection and pseudonymization** with 50%+ time savings vs manual redaction (including validation time)
- Provide GDPR-compliant pseudonymization with encrypted mapping tables, audit trails, reversibility, and human verification audit trail
- Enable consistent pseudonymization across document batches (10-100+ files) for corpus-level analysis
- Deliver transparent, cite-able methodology suitable for research ethics board evaluation, emphasizing human-in-the-loop quality assurance

**Post-MVP Goal (v1.1):**
- Improve AI detection to 70-85% F1 through fine-tuning on domain-specific data, enabling optional validation mode for high-confidence workflows
```

### Rationale
- Sets realistic expectations for MVP (40-50% AI detection)
- Emphasizes **combined** AI + human accuracy (100%)
- Adds v1.1 roadmap for transparency
- Changes "automate" to "AI-assisted" throughout

---

## SECTION 2: Background Context *(UPDATE)*

### Current Text (Lines 15-19)
```
### Background Context

The explosion of LLM capabilities in 2024-2025 has created an urgent dilemma: organizations and researchers possess valuable documents that could benefit enormously from AI analysis, but cannot safely send them to cloud-based services due to embedded personal data and GDPR obligations. Every day, they choose between staying compliant but falling behind, or innovating but taking unacceptable privacy risks. Manual redaction doesn't scale and destroys document coherence, while cloud-based pseudonymization services require trusting third parties with confidential data.

GDPR Pseudonymizer solves this by providing a local Python CLI tool that automatically detects and replaces personal identifiers (names, locations, organizations) with consistent, readable pseudonyms—entirely on the user's infrastructure. The MVP targets **AI-forward organizations and technically-comfortable researchers** as primary users, focusing on French-language text files (.txt, .md) to validate core value propositions: trustworthy local processing, batch efficiency, and maintained document utility for LLM analysis and qualitative research. Phase 2 will expand to GUI for broader adoption. The tool prioritizes the LLM enablement use case for MVP validation while ensuring methodology meets academic rigor standards for research applications.
```

### Updated Text (REPLACE)
```
### Background Context

The explosion of LLM capabilities in 2024-2025 has created an urgent dilemma: organizations and researchers possess valuable documents that could benefit enormously from AI analysis, but cannot safely send them to cloud-based services due to embedded personal data and GDPR obligations. Every day, they choose between staying compliant but falling behind, or innovating but taking unacceptable privacy risks. Manual redaction doesn't scale (16-25 hours for 50 documents) and destroys document coherence, while cloud-based pseudonymization services require trusting third parties with confidential data.

GDPR Pseudonymizer solves this by providing a local Python CLI tool that **intelligently detects and assists with replacing** personal identifiers (names, locations, organizations) with consistent, readable pseudonyms—entirely on the user's infrastructure. The MVP targets **privacy-conscious organizations and technically-comfortable researchers** as primary users, focusing on French-language text files (.txt, .md) to validate core value propositions: trustworthy local processing, human-verified accuracy, batch efficiency, and maintained document utility for LLM analysis and qualitative research.

**Positioning:** The tool combines AI efficiency (40-50% automatic detection via hybrid NLP + regex approach) with human verification (mandatory review ensures 100% accuracy), delivering **50%+ time savings vs manual redaction** while maintaining GDPR-defensible quality. This "AI-assisted" approach is intentionally designed for compliance-focused users who value human oversight for legal defensibility. Phase 2 will expand to GUI for broader adoption and v1.1 will introduce optional validation mode as fine-tuned models improve accuracy to 70-85%. The MVP prioritizes the LLM enablement use case while ensuring methodology meets academic rigor standards for research applications.

**Strategic Context (Post-Benchmark):**
Following comprehensive NLP library evaluation (Story 1.2, Jan 2026), both spaCy and Stanza achieved below-threshold accuracy on French interview/business document corpus (29.5% and 11.9% F1 respectively vs 85% target). The approved contingency plan pivots to "AI-assisted" positioning with mandatory validation mode, positioning human verification as a quality feature rather than limitation. This approach targets early adopters who prioritize privacy and compliance over convenience, with a clear roadmap to semi-automatic (v1.1) and fully automatic (v2.0) workflows as model accuracy improves.
```

### Rationale
- Updates value proposition to "AI-assisted"
- Adds quantified time savings context (16-25 hours manual)
- Explains strategic positioning and target audience shift
- Documents contingency plan decision for transparency
- Adds roadmap context (v1.0 → v1.1 → v2.0)

---

## SECTION 3: Functional Requirements *(UPDATE)*

### FR7 - Validation Mode *(CRITICAL UPDATE)*

**Current Text (Line 45):**
```
**FR7:** The system shall provide an optional interactive validation mode (activated via `--validate` flag) that presents detected entities and classification results for review before pseudonymization is applied. Users may correct, add, or remove entities. Validation mode is recommended for highly sensitive documents but not required.
```

**Updated Text (REPLACE):**
```
**FR7:** The system shall provide a **mandatory interactive validation mode** that presents detected entities and classification results for user review before pseudonymization is applied. Users may confirm, correct, add, or remove entities to ensure 100% accuracy despite AI detection limitations (40-50% automatic coverage). Validation mode includes:
- Entity presentation grouped by type (PERSON, LOCATION, ORG)
- Context display (surrounding text snippets)
- Confidence scores (when available from NLP or pattern matching)
- Batch actions (confirm all high-confidence entities, reject low-confidence false positives)
- Keyboard-driven interface for speed (target: <2 minutes per 2-5K word document)
- Ambiguous standalone component flagging (FR4 integration)

**Rationale:** Validation is MANDATORY for MVP due to NLP accuracy limitations (spaCy baseline: 29.5% F1, hybrid target: 40-50% F1). Human verification ensures zero false negatives and provides legal defensibility for GDPR compliance. Future versions (v1.1+) may introduce optional validation for high-confidence workflows after fine-tuning improves AI accuracy to 70-85%.
```

### FR18 - Default Validation Behavior *(CRITICAL UPDATE)*

**Current Text (Line 67):**
```
**FR18:** The system shall disable validation mode by default (fast processing) and require explicit `--validate` flag to enable interactive review. In batch mode without validation, the system shall provide a summary report of detected entities after processing all documents.
```

**Updated Text (REPLACE):**
```
**FR18:** The system shall **enable validation mode by default** (mandatory review) to ensure accuracy given AI detection limitations. Users MUST review and confirm all detected entities before pseudonymization is applied. The `--validate` flag is not required (validation is always active in MVP). In batch mode, validation occurs before batch processing begins: users review entities from all documents, then batch proceeds with validated entity list.

**Post-MVP (v1.1+):** A `--no-validate` or `--auto` flag may be introduced to skip validation for high-confidence entities (requires fine-tuned model with 70-85% F1 accuracy), but this is explicitly deferred to v1.1 release pending model improvements and user feedback on risk tolerance.

**CLI Behavior:**
- `gdpr-pseudo process document.txt` → **Validation UI opens automatically**
- `gdpr-pseudo batch documents/` → **Validation UI shows all entities from batch before processing**
- No flag required to enable validation (it's the default and only mode in v1.0)
```

### Rationale
- Makes validation mandatory (not optional)
- Sets clear expectations for user workflow
- Documents future optional mode (v1.1+)
- Clarifies CLI behavior

---

## SECTION 4: Non-Functional Requirements *(UPDATE)*

### NFR8 - False Negative Rate *(UPDATE)*

**Current Text (Line 92):**
```
**NFR8:** The system shall maintain false negative rate <10% (missed sensitive entities) to ensure GDPR compliance safety.
```

**Updated Text (REPLACE):**
```
**NFR8:** The system shall maintain **zero false negative rate** in final output through mandatory human verification (FR7). AI detection baseline (hybrid NLP + regex) targets 40-50% recall, with human review catching remaining 50-60% of entities. The combined AI + human workflow ensures 100% entity coverage for GDPR compliance safety.

**Measurement:**
- **AI detection recall:** 40-50% target (hybrid approach)
- **Human verification catch rate:** 100% (mandatory review)
- **Final false negative rate:** 0% (measured on post-validation output)
```

### NFR9 - False Positive Rate *(UPDATE)*

**Current Text (Line 93):**
```
**NFR9:** The system shall maintain false positive rate <15% (incorrectly flagged entities) to minimize user validation burden.
```

**Updated Text (REPLACE):**
```
**NFR9:** The system shall maintain **acceptable false positive rate** from AI detection (estimated 50-70% given 27% precision baseline), with human validation efficiently rejecting false positives during mandatory review. False positives increase validation time but do not affect final output quality (users reject them during review).

**Measurement:**
- **AI detection precision:** 27-40% baseline (tolerates false positives)
- **User validation efficiency:** Target <2 min per document including false positive rejection
- **Final false positive rate:** 0% (measured on post-validation output)

**Design Goal:** Optimize validation UI for fast false positive rejection (batch "reject all ORG entities" action, confidence-based sorting) rather than minimizing AI false positive rate.
```

### Rationale
- Shifts focus from AI accuracy to **combined** AI + human accuracy
- Acknowledges validation catches both false negatives and false positives
- Emphasizes final output quality (100%) over AI baseline

---

## SECTION 5: Technical Assumptions *(UPDATE - NEW SECTION)*

### Insert After Line 179 (Current "Contingency Plans if <85%")

**Current Text (Lines 176-179):**
```
- **Contingency Plans if <85%:**
  - **Option A:** Hybrid approach combining NER with rule-based name detection (French name dictionaries)
  - **Option B:** Lower accuracy threshold but make validation mode (`--validate`) mandatory by default
  - **Option C:** Pivot to English language market where NER models have higher accuracy (requires Brief revision)
```

**Updated Text (REPLACE with expanded section):**
```
### NLP Library Selection - DECISION MADE (Story 1.2 Complete)

**Benchmark Results (2026-01-16):**
- **spaCy `fr_core_news_lg`:** 29.5% F1 score (26.96% precision, 32.67% recall)
- **Stanza `fr_default`:** 11.9% F1 score (10.26% precision, 14.12% recall)
- **Decision:** spaCy selected (2.5x better performance than Stanza)
- **Threshold:** Both libraries FAILED ≥85% F1 requirement

**Root Cause Analysis:**
1. **Model-corpus mismatch:** Pre-trained models trained on news text, our corpus is interview transcripts and business documents
2. **Domain-specific language:** Conversational patterns, mixed formal/informal registers
3. **Entity type misalignment:** ORG detection catastrophic (3.8% precision = 96% false positives)

**Approved Contingency Plan (Option 1 + Option 3):**

**Option 1: Lower Threshold + Mandatory Validation Mode**
- Accept 40-50% AI detection (hybrid approach) as baseline
- Make validation mode MANDATORY for all processing (FR7, FR18 updated)
- Position as "AI-assisted" not "automatic" pseudonymization
- Human review ensures 100% accuracy for GDPR compliance
- **Status:** ✅ APPROVED - Core MVP strategy

**Option 3: Hybrid Detection (NLP + Regex Patterns)**
- Combine spaCy NER with French-specific regex patterns
- Target patterns: Titles (M., Mme, Dr.), compound names (Jean-Pierre), location indicators (à Paris)
- French name dictionaries (INSEE data) for "Firstname Lastname" pattern matching
- Estimated improvement: 29.5% F1 → 40-50% F1
- Reduces validation burden by ~40-50% vs spaCy baseline
- **Status:** ✅ APPROVED - Epic 1 Story 1.8

**Option 2: Fine-Tune spaCy Model (Deferred to v1.1)**
- Collect domain-specific annotated training data from MVP users
- Fine-tune `fr_core_news_lg` on interview/business document corpus
- Target: 70-85% F1 (realistic for fine-tuned model)
- Enables optional validation mode for high-confidence workflows
- **Status:** 📅 DEFERRED to post-MVP (Sprint 4-5, Q2 2026)

**Architecture Documentation:**
- Benchmark report: [docs/nlp-benchmark-report.md](../nlp-benchmark-report.md)
- Tech stack updated: [docs/architecture/3-tech-stack.md](../architecture/3-tech-stack.md) line 9-10
- Positioning strategy: [docs/positioning-messaging-v2-assisted.md](../positioning-messaging-v2-assisted.md)

**Implications for Requirements:**
- FR7: Validation mode now MANDATORY (not optional)
- FR18: Default behavior changed (validation always on)
- NFR8-9: Accuracy measured on final output (AI + human), not AI alone
- Epic 0: Added Story 0.4 (Validation UI/UX Design)
- Epic 1: Added Stories 1.7-1.8 (Validation UI Implementation + Hybrid Detection)
- Timeline: Epic 1 extended 4 weeks → 5 weeks, MVP launch Week 13 → Week 14
```

### Rationale
- Documents decision transparently
- Provides context for all PRD changes
- Links to supporting documentation
- Shows clear roadmap (v1.0 → v1.1 → v2.0)

---

## SECTION 6: Epic 0 *(UPDATE - ADD NEW STORY)*

### Insert After Story 0.3 (Before "## Epic 1")

**Add New Story:**

```markdown
---

### Story 0.4: Validation UI/UX Design *(NEW - CRITICAL)*

**As a** product manager,
**I want** a well-designed validation UI/UX specification for mandatory entity review,
**so that** users can efficiently verify 50-70% of entities without validation feeling burdensome.

**PRIORITY:** 🔴 **CRITICAL PATH** - This story is MANDATORY following Story 1.2 benchmark results (29.5% F1 accuracy).

#### Context

Story 1.2 revealed that spaCy achieves only 29.5% F1 score (vs 85% target). Contingency plan Option 1+3 selected:
- **Option 1:** Accept lower threshold + make validation mode MANDATORY
- **Option 3:** Hybrid approach (NLP + regex patterns) to improve to 40-50% F1

**Implication:** Validation UI is now **core MVP feature**, not optional enhancement. Users will spend 80% of their time in validation workflow.

#### Acceptance Criteria

1. **AC1:** CLI validation workflow designed for speed and efficiency:
   - Keyboard-driven interface (minimal mouse interaction)
   - Batch operations (confirm all PERSON entities, reject all ORG false positives)
   - Smart defaults (pre-accept high-confidence entities if confidence scores available)

2. **AC2:** Entity presentation format specified:
   - Grouped by entity type (PERSON, LOCATION, ORG)
   - Show context (surrounding text snippet)
   - Highlight entity in document preview
   - Display confidence score (if available from NER)

3. **AC3:** User action taxonomy defined:
   - ✅ **Confirm:** Accept entity and suggested pseudonym
   - ❌ **Reject:** Remove false positive
   - ✏️ **Modify:** Edit entity text (e.g., "Marie" → "Marie Dubois" for full name)
   - ➕ **Add:** Manually add missed entity
   - 🔄 **Change Pseudonym:** Override suggested pseudonym

4. **AC4:** Validation workflow steps documented:
   - **Step 1:** Show summary (X entities detected: Y PERSON, Z LOCATION, etc.)
   - **Step 2:** Review by entity type (most critical first: PERSON → ORG → LOCATION)
   - **Step 3:** Confirm ambiguous standalone components (flagged by FR4 logic)
   - **Step 4:** Final confirmation before processing

5. **AC5:** Target validation time per document:
   - **Goal:** <2 minutes for 2-5K word document
   - **Benchmark:** Test with 5 sample documents, measure time
   - **Optimization:** Identify bottlenecks, iterate on UX

6. **AC6:** Validation UI library selected:
   - **Primary candidate:** `rich` (already in tech stack for progress bars)
   - **Features needed:** Tables, color coding, keyboard input, interactive menus
   - **Alternative:** `questionary` or `inquirer` for CLI forms

7. **AC7:** Wireframe/mockup created for validation workflow:
   - ASCII mockup of CLI interface
   - Example validation session walkthrough
   - Edge case handling (0 entities detected, 100+ entities detected)

8. **AC8:** Validation UI spec reviewed by:
   - PM (user experience perspective)
   - Dev (implementation feasibility)
   - 1-2 target users (5-minute feedback session)

9. **AC9 (CRITICAL):** Validation UX reduces burden perception:
   - **User expectation:** "Quick review" not "tedious work"
   - **Design principle:** Default to AI suggestions, user confirms/overrides
   - **Psychological framing:** "Quality control" not "doing AI's job"

#### Example Validation UI Wireframe

See full ASCII mockup in [docs/prd/epic-0-pre-sprint-preparation-v2-rescoped.md](prd/epic-0-pre-sprint-preparation-v2-rescoped.md) lines 100-130.

---
```

### Update Epic 0 Definition of Done (Line ~61)

**Current Text:**
```
**Epic 0 DoD:**
- ✓ Initial test corpus created (10 French documents with ground truth annotations)
- ✓ Development environment configured (Python 3.9+, Poetry, pytest)
- ✓ Quick spaCy benchmark completed (initial accuracy estimate)
- ✓ Ready to begin Epic 1 Sprint 1 without blockers
```

**Updated Text (REPLACE):**
```
**Epic 0 DoD:**
- ✓ Initial test corpus created (10 French documents with ground truth annotations)
- ✓ Development environment configured (Python 3.9+, Poetry, pytest)
- ✓ Quick spaCy benchmark completed (initial accuracy estimate)
- ✓ **Validation UI/UX design specification complete and reviewed** ⭐ NEW
- ✓ **PM approval of contingency plan (Option 1+3: Assisted mode + hybrid detection)** ⭐ NEW
- ✓ Ready to begin Epic 1 Sprint 1 without blockers
```

---

## SECTION 7: Epic 1 *(UPDATE - ADD NEW STORIES)*

### Update Epic 1 Header (Line ~519)

**Current Text:**
```
## Epic 1: Foundation & NLP Validation (Week 1-4)

**Epic Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, and deliver a working "walking skeleton" CLI command that demonstrates basic end-to-end pseudonymization capability for early validation.
```

**Updated Text (REPLACE):**
```
## Epic 1: Foundation & NLP Validation (Week 1-5) *(EXTENDED)*

**Epic Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, **implement mandatory validation UI**, and deliver a working "walking skeleton" CLI command that demonstrates AI-assisted pseudonymization with human-in-the-loop verification for early validation.

**CRITICAL UPDATES (Post-Story 1.2):**
- ✅ **spaCy selected** (29.5% F1 vs Stanza 11.9% F1) - Decision made
- 🔴 **NEW Story 1.7:** Validation UI Implementation (moved from Epic 3) - **CRITICAL PATH**
- 🔴 **NEW Story 1.8:** Hybrid Detection Strategy (NLP + regex patterns)
- ⚠️ **Timeline extended:** 4 weeks → 5 weeks to accommodate validation UI priority
```

### Update Story 1.4 (Project Foundation) - Add Validation Module

**Current Text (Lines ~580-590):**
```
1. **AC1:** Package structure created following Technical Assumptions architecture:
   - `gdpr_pseudonymizer/cli/` - Command-line interface layer
   - `gdpr_pseudonymizer/core/` - Core processing orchestration
   - `gdpr_pseudonymizer/nlp/` - NLP engine (entity detection)
   - `gdpr_pseudonymizer/data/` - Data layer (mapping tables, audit logs)
   - `gdpr_pseudonymizer/pseudonym/` - Pseudonym manager
   - `gdpr_pseudonymizer/utils/` - Utilities (encryption, file handling)
```

**Updated Text (REPLACE AC1 only):**
```
1. **AC1 (UPDATED):** Package structure created following Technical Assumptions architecture:
   - `gdpr_pseudonymizer/cli/` - Command-line interface layer
   - `gdpr_pseudonymizer/core/` - Core processing orchestration
   - `gdpr_pseudonymizer/nlp/` - NLP engine (entity detection)
   - `gdpr_pseudonymizer/data/` - Data layer (mapping tables, audit logs)
   - `gdpr_pseudonymizer/pseudonym/` - Pseudonym manager
   - `gdpr_pseudonymizer/utils/` - Utilities (encryption, file handling)
   - **`gdpr_pseudonymizer/validation/` - Validation UI module (human-in-the-loop)** ⭐ NEW
     - `validation/ui.py` - CLI UI components (entity display, user input)
     - `validation/models.py` - Validation data models (entity review state)
     - `validation/workflow.py` - Validation workflow orchestration
```

### Insert NEW Story 1.7 (After Story 1.6)

**Add Complete Story (see full text in [epic-1-foundation-nlp-validation-v2-rescoped.md](prd/epic-1-foundation-nlp-validation-v2-rescoped.md) lines 250-450)**

Key summary for insertion:

```markdown
---

### Story 1.7: Validation UI Implementation *(NEW - CRITICAL PATH)*

**As a** user,
**I want** an intuitive CLI interface to review and confirm detected entities,
**so that** I can ensure 100% accuracy despite AI limitations while minimizing review time.

**PRIORITY:** 🔴 **CRITICAL** - This is now core MVP functionality (not Epic 3 optional feature)

#### Context

Following Story 1.2 benchmark (29.5% F1), validation mode is **MANDATORY** for MVP. Users will spend 80% of interaction time in validation workflow. This must be polished, fast, and intuitive.

#### Acceptance Criteria Summary

1. Validation UI implemented using `rich` library
2. Entity presentation: grouped by type, context display, confidence scores
3. User actions: Confirm, Reject, Modify, Add, Change Pseudonym, Batch operations
4. Validation workflow: Summary → Review by type → Ambiguous flagging → Final confirmation
5. Performance: <2 min validation per 2-5K word document
6. Accessibility: Keyboard-only, color-blind safe, help overlay
7. Error handling: Invalid input, empty detection, large documents
8. Unit + integration tests for all UI components
9. **User testing: 2-3 users, ≥4/5 satisfaction target**
10. **Validation mode ALWAYS ON** (no `--validate` flag needed)

See full story with 11 ACs and detailed implementation notes in [epic-1-foundation-nlp-validation-v2-rescoped.md](prd/epic-1-foundation-nlp-validation-v2-rescoped.md).

---
```

### Insert NEW Story 1.8 (After Story 1.7)

**Add Complete Story:**

```markdown
---

### Story 1.8: Hybrid Detection Strategy *(NEW - CONTINGENCY PLAN)*

**As a** user,
**I want** improved entity detection using hybrid NLP + regex patterns,
**so that** I spend less time reviewing entities (40-50% detection vs 29.5% baseline).

**PRIORITY:** HIGH - Reduces validation burden, improves user experience

#### Context

Story 1.2 showed spaCy achieves only 29.5% F1 (recall ~33%, precision ~27%). Contingency plan Option 3 adds regex-based fallback patterns to improve detection to estimated 40-50% F1.

**Goal:** Detect additional entities that spaCy misses using French-specific patterns.

#### Acceptance Criteria Summary

1. Regex pattern library for French entities (titles, names, locations, organizations)
2. French name dictionaries integrated (INSEE top 500 first/last names)
3. Hybrid detection pipeline: spaCy → regex → merge → deduplicate
4. Deduplication logic (prefer spaCy entities, add regex-only entities)
5. Performance: Benchmark hybrid approach, target 40-50% F1
6. Confidence score handling (spaCy vs regex confidence)
7. Configuration: Patterns in YAML, user can enable/disable categories
8. Unit tests for each pattern and pipeline integration
9. Integration test on full corpus (compare to baseline)
10. Documentation of hybrid approach and performance gains

#### Expected Impact

| Metric | spaCy Baseline | Hybrid Target | Improvement |
|--------|----------------|---------------|-------------|
| **Recall (PERSON)** | 31.28% | 45-55% | +14-24% |
| **Overall F1** | 29.54% | 40-50% | +10-20% |
| **User validation time** | ~4-5 min/doc | ~2-3 min/doc | -40-50% |

See full story with 10 ACs and regex pattern examples in [epic-1-foundation-nlp-validation-v2-rescoped.md](prd/epic-1-foundation-nlp-validation-v2-rescoped.md).

---
```

### Update Epic 1 Definition of Done (Line ~638)

**Current Text:**
```
**Epic 1 DoD:**
- ✓ NLP library selected (spaCy or Stanza) with ≥85% accuracy validated on 20-30 document test corpus
- ✓ CI/CD pipeline operational (GitHub Actions testing on 2+ platforms)
- ✓ Walking skeleton: Basic `process` command runs end-to-end (naive pseudonymization)
- ✓ Git workflow and code quality tooling established
- ✓ Can demonstrate basic pseudonymization concept to alpha testers
```

**Updated Text (REPLACE):**
```
**Epic 1 DoD (UPDATED):**
- ✅ **spaCy selected** (29.5% F1, best available option) - Contingency plan approved
- ✅ CI/CD pipeline operational (GitHub Actions testing on 2+ platforms)
- ✅ Project foundation with **validation module structure** established
- ✅ Walking skeleton: Basic `process` command with **validation stub**
- ✅ spaCy NLP integration functional (baseline detection)
- ✅ **Validation UI fully implemented and user-tested (Story 1.7)** ⭐ CRITICAL NEW
- ✅ **Hybrid detection (NLP + regex) achieves 40-50% F1 estimated (Story 1.8)** ⭐ NEW
- ✅ Can demonstrate **AI-assisted pseudonymization with human-in-the-loop validation**
- ✅ **PM sign-off on "assisted mode" positioning**
```

---

## SECTION 8: Epic List & Timeline *(UPDATE)*

### Update Epic List Summary (Lines ~353-386)

**Current Text:**
```
### Epic 1: Foundation & NLP Validation (Week 1-4)

**Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, and deliver a working "walking skeleton" CLI command that demonstrates basic end-to-end pseudonymization capability for early validation.
```

**Updated Text (REPLACE entire Epic 1 entry):**
```
### Epic 1: Foundation & NLP Validation (Week 1-5) *(EXTENDED)*

**Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, implement mandatory validation UI, and deliver a working "walking skeleton" CLI command that demonstrates AI-assisted pseudonymization with human-in-the-loop verification.

**UPDATES (Post-Story 1.2):**
- spaCy selected (29.5% F1, contingency plan activated)
- NEW Story 1.7: Validation UI Implementation (critical path)
- NEW Story 1.8: Hybrid Detection (NLP + regex patterns)
- Timeline: 4 weeks → 5 weeks
```

### Update Timeline (Line ~386)

**Current Text:**
```
**Timeline: 13 weeks total (includes 1-week buffer for NLP selection and compositional logic complexity risks)**
```

**Updated Text (REPLACE):**
```
**Timeline: 14 weeks total (includes 1-week Epic 1 extension for validation UI + 1-week contingency buffer)**

**Breakdown:**
- Epic 0 (Pre-Sprint): Week -1 to 0 (1 week) - includes Story 0.4 (Validation UI Design)
- Epic 1 (Foundation): Week 1-5 (5 weeks) - **EXTENDED** for Stories 1.7-1.8
- Epic 2 (Core Engine): Week 6-10 (5 weeks) - shifted +1 week
- Epic 3 (CLI & Batch): Week 11-13 (3 weeks) - shifted +1 week
- Epic 4 (Launch): Week 14 (1 week) - shifted +1 week, includes buffer

**Impact:** MVP launch shifts from Week 13 → Week 14 (+1 week delay)
```

### Update Epic 2-4 Weeks (adjust all subsequent epic headers)

**Epic 2 Header (Line ~640):**
```
## Epic 2: Core Pseudonymization Engine (Week 6-10) *(SHIFTED +1 WEEK)*
```

**Epic 3 Header (Line ~800):**
```
## Epic 3: CLI Interface & Batch Processing (Week 11-13) *(SHIFTED +1 WEEK)*
```

**Epic 4 Header (Line ~980):**
```
## Epic 4: Launch Readiness & LLM Validation (Week 14) *(SHIFTED +1 WEEK)*
```

---

## SECTION 9: Change Log *(UPDATE)*

### Add Entry to Change Log (After Line 24)

**Current Text:**
```
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-11 | v1.0 | Initial PRD creation from Project Brief | John (PM) |
```

**Updated Text (ADD NEW ROW):**
```
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-11 | v1.0 | Initial PRD creation from Project Brief | John (PM) |
| 2026-01-16 | v2.0 | Contingency plan updates: AI-assisted positioning, mandatory validation mode, Epic 0/1 rescoping (Post-Story 1.2 benchmark) | John (PM) |
```

---

## SECTION 10: Documentation References *(NEW SECTION - ADD AFTER CHANGE LOG)*

### Insert New Section (After Change Log, before "## Requirements")

```markdown
---

## Related Documentation (Post-Benchmark Updates)

Following the Story 1.2 NLP benchmark results (Jan 2026), several supplementary documents provide context for PRD v2.0 changes:

### Strategic Documents
- **[NLP Benchmark Report](nlp-benchmark-report.md)** - Comprehensive analysis of spaCy vs Stanza accuracy (Story 1.2 deliverable)
- **[Positioning & Messaging v2](positioning-messaging-v2-assisted.md)** - Updated product positioning for "AI-assisted" approach
- **[Deliverables Summary](DELIVERABLES-SUMMARY-2026-01-16.md)** - Executive summary of contingency plan decisions

### Updated Epic Documents
- **[Epic 0 - Rescoped](prd/epic-0-pre-sprint-preparation-v2-rescoped.md)** - Adds Story 0.4 (Validation UI Design)
- **[Epic 1 - Rescoped](prd/epic-1-foundation-nlp-validation-v2-rescoped.md)** - Adds Stories 1.7-1.8, extends to 5 weeks

### Architecture Updates
- **[Tech Stack](architecture/3-tech-stack.md)** - Lines 9-10 updated with spaCy selection and accuracy limitations

---
```

---

## Summary of PRD Updates

### Sections Modified
1. ✅ **Goals** - Added realistic accuracy expectations (40-50% AI + 100% combined)
2. ✅ **Background Context** - Updated value proposition to "AI-assisted", added strategic context
3. ✅ **FR7** - Validation mode now MANDATORY (not optional)
4. ✅ **FR18** - Default validation behavior changed (always on)
5. ✅ **NFR8-9** - Accuracy measured on final output (AI + human combined)
6. ✅ **Technical Assumptions** - Added comprehensive NLP decision section
7. ✅ **Epic 0** - Added Story 0.4 (Validation UI Design)
8. ✅ **Epic 1** - Added Stories 1.7-1.8, updated header/DoD, extended to 5 weeks
9. ✅ **Epic List** - Updated timeline (13 weeks → 14 weeks), shifted Epic 2-4
10. ✅ **Change Log** - Added v2.0 entry
11. ✅ **Documentation References** - Added new section linking related docs

### Files Created (Reference for Merging)
- [positioning-messaging-v2-assisted.md](../positioning-messaging-v2-assisted.md)
- [epic-0-pre-sprint-preparation-v2-rescoped.md](prd/epic-0-pre-sprint-preparation-v2-rescoped.md)
- [epic-1-foundation-nlp-validation-v2-rescoped.md](prd/epic-1-foundation-nlp-validation-v2-rescoped.md)
- [DELIVERABLES-SUMMARY-2026-01-16.md](../DELIVERABLES-SUMMARY-2026-01-16.md)
- [nlp-benchmark-report.md](../nlp-benchmark-report.md) - Already exists

### Merge Instructions

**Option 1: In-Place Edits (Recommended)**
1. Open [docs/prd.md](../.ignore/prd.md)
2. Apply each section update sequentially (use Find/Replace for efficiency)
3. Verify line numbers after each change (subsequent line numbers will shift)
4. Run final quality check (no broken references, consistent formatting)

**Option 2: Side-by-Side Diff**
1. Create PRD v2.0 copy: `docs/prd-v2.0-draft.md`
2. Apply all changes to draft copy
3. Use diff tool to review changes
4. Merge draft → main PRD after review

**Option 3: Version Control**
1. Create git branch: `prd-v2-assisted-mode`
2. Apply changes to branch copy of prd.md
3. Commit with message: "Update PRD v2.0: AI-assisted positioning, mandatory validation mode"
4. Review PR diff, merge to main

---

**Status:** ✅ Ready to merge
**Estimated Merge Time:** 30-45 minutes (careful find/replace recommended)
**Review Required:** PM final approval before merging to main PRD
