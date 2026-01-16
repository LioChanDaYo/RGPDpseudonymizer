# Epic 0: Pre-Sprint Preparation (v2 - RESCOPED)

**Epic Goal:** Prepare test data and development environment foundation to enable Epic 1 to start without blockers, validating basic NLP library viability before full sprint work begins.

**Duration:** Week -1 to 0 (pre-sprint preparation)

**CRITICAL CHANGE (Post-Story 1.2):**
This epic has been **RESCOPED** following the NLP benchmark results. Validation mode is now **MANDATORY CORE FEATURE** (not optional), requiring immediate UI design attention in Epic 0.

---

## Key Changes from Original Epic 0

| Change | Rationale | Impact |
|--------|-----------|--------|
| **NEW Story 0.4:** Validation UI/UX Design | Validation mode is now mandatory (not optional) due to 29.5% F1 accuracy | Adds 2-3 days to Epic 0 |
| **Updated Story 0.3:** NLP benchmark shows BOTH libraries fail threshold | Contingency plan required: hybrid approach + mandatory validation | Decision criteria adjusted |
| **Architecture implications:** Validation UI is critical path, not Epic 3 feature | Shifts Epic 1 priorities | High impact on dependencies |

---

## Story 0.1: Create Initial Test Corpus *(UNCHANGED)*

**As a** developer,
**I want** an initial test corpus of French documents with ground truth entity annotations,
**so that** I can benchmark NLP library accuracy and validate entity detection quality throughout development.

### Acceptance Criteria

1. **AC1:** Test corpus contains 10 French documents representing target use cases (5 interview transcripts, 5 business documents).
2. **AC2:** Each document manually annotated with ground truth entity boundaries and types (PERSON, LOCATION, ORG).
3. **AC3:** Documents include edge cases: compound names ("Jean-Pierre"), shared name components ("Marie Dubois", "Marie Dupont"), standalone name components.
4. **AC4:** Annotations stored in structured format (JSON or CSV) with: `document_id`, `entity_text`, `entity_type`, `start_offset`, `end_offset`.
5. **AC5:** Test corpus documented with: source/creation methodology, entity type distribution statistics, known edge cases.
6. **AC6:** Total annotation effort <20 hours (2-3 days part-time work).

---

## Story 0.2: Setup Development Environment *(UNCHANGED)*

**As a** developer,
**I want** a standardized development environment with all necessary tools configured,
**so that** I can begin coding immediately in Epic 1 without setup delays.

### Acceptance Criteria

1. **AC1:** Python 3.9+ installed and verified on development machine.
2. **AC2:** Poetry dependency manager installed and project initialized with `pyproject.toml`.
3. **AC3:** Code quality tools configured: Black (formatter), Ruff (linter), mypy (type checker).
4. **AC4:** pytest testing framework installed with basic test directory structure (`tests/unit`, `tests/integration`).
5. **AC5:** Git repository confirmed with `.gitignore` configured for Python projects (exclude `__pycache__`, `.pytest_cache`, virtual environments).
6. **AC6:** Basic `README.md` created with: project description, setup instructions, development workflow.
7. **AC7:** Development environment setup documented (IDE recommendations, required extensions, troubleshooting common issues).

---

## Story 0.3: Quick NLP Library Viability Test *(UPDATED - Contingency Awareness)*

**As a** product manager,
**I want** a quick initial test of spaCy's French NER accuracy on sample documents,
**so that** I can assess viability before committing to full Epic 1 benchmark and identify early red flags.

### Acceptance Criteria

1. **AC1:** spaCy installed with `fr_core_news_lg` French model.
2. **AC2:** Simple script created that processes 3-5 sample documents through spaCy NER pipeline.
3. **AC3:** Script outputs detected entities with types and confidence scores (if available).
4. **AC4:** Manual comparison of detected entities vs known entities in sample documents.
5. **AC5:** Rough accuracy estimate calculated: "Good" (>80%), "Marginal" (60-80%), "Poor" (<60%).
6. **AC6 (UPDATED):** Decision documented with contingency plan awareness:
   - If Good (>80%): Proceed to Epic 1 full benchmark with optimism
   - If Marginal (60-80%): Proceed but prepare for hybrid approach (NLP + regex)
   - **If Poor (<60%): ACTIVATE CONTINGENCY - Mandatory validation mode + hybrid detection + fine-tuning roadmap**
7. **AC7:** Quick test results shared with stakeholders (estimated accuracy, notable strengths/weaknesses, recommendation).
8. **AC8 (NEW):** If "Poor" result, immediately notify PM and Architect to begin validation UI design (Story 0.4).

---

## Story 0.4: Validation UI/UX Design *(NEW - CRITICAL ADDITION)*

**As a** product manager,
**I want** a well-designed validation UI/UX specification for mandatory entity review,
**so that** users can efficiently verify 50-70% of entities without validation feeling burdensome.

**PRIORITY:** 🔴 **CRITICAL PATH** - This story is now MANDATORY following Story 1.2 benchmark results (29.5% F1 accuracy).

### Context

Story 1.2 revealed that spaCy achieves only 29.5% F1 score (vs 85% target). Contingency plan Option 1+3 selected:
- **Option 1:** Accept lower threshold + make validation mode MANDATORY
- **Option 3:** Hybrid approach (NLP + regex patterns) to improve to 40-50% F1

**Implication:** Validation UI is now **core MVP feature**, not optional enhancement. Users will spend 80% of their time in validation workflow.

### Acceptance Criteria

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

### Example Validation UI Wireframe (ASCII Mockup)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ GDPR Pseudonymizer - Entity Validation                                      ║
║ File: interview_transcript_01.txt (2,340 words)                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║ Detected: 23 entities (15 PERSON, 5 LOCATION, 3 ORG)                        ║
║ Review: 2-3 minutes estimated                                                ║
║                                                                              ║
║ ┌──────────────────────────────────────────────────────────────────────────┐ ║
║ │ PERSON Entities (15 found)                                  [1/3]        │ ║
║ ├──────────────────────────────────────────────────────────────────────────┤ ║
║ │ 1. Marie Dubois              → Leia Organa     [✓ Confirm] [✗ Reject]  │ ║
║ │    Context: "...interview with Marie Dubois about..."                   │ ║
║ │    Confidence: 95%                                                       │ ║
║ │                                                                          │ ║
║ │ 2. Dr. Jean-Pierre Martin    → Luke Skywalker  [✓ Confirm] [✗ Reject]  │ ║
║ │    Context: "...Dr. Jean-Pierre Martin explained..."                    │ ║
║ │    Confidence: 87%                                                       │ ║
║ │                                                                          │ ║
║ │ 3. Marie                     → Leia ⚠️          [✓ Confirm] [✗ Reject]  │ ║
║ │    Context: "...when Marie said this..."                                │ ║
║ │    ⚠️  Ambiguous: Standalone component. Related to "Marie Dubois"?      │ ║
║ │                                                                          │ ║
║ │ [Space] Confirm current | [R] Reject | [E] Edit | [N] Next | [Q] Quit  │ ║
║ └──────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║ Actions: [A] Accept all PERSON | [S] Skip to LOCATION | [H] Help           ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Technical Considerations

**Library:** Use `rich` library (already in tech stack):
- `rich.table.Table` for entity display
- `rich.prompt.Confirm` for yes/no decisions
- `rich.console.Console` for color-coded output
- `rich.panel.Panel` for grouped sections

**Performance:**
- Lazy loading: Load entities page-by-page (don't render 100+ entities at once)
- Precompute context snippets (10 words before/after entity)
- Cache document text for fast context lookups

**Accessibility:**
- Keyboard-only navigation (no mouse required)
- Color-blind safe palette (use symbols + colors)
- Screen reader compatible (text-based output)

---

## Epic 0 Definition of Done (UPDATED)

- ✅ Initial test corpus created (10 French documents with ground truth annotations) - **Story 0.1**
- ✅ Development environment configured (Python 3.9+, Poetry, pytest) - **Story 0.2**
- ✅ Quick spaCy benchmark completed (initial accuracy estimate) - **Story 0.3**
- ✅ **Validation UI/UX design specification complete and reviewed** - **Story 0.4** ⭐ NEW
- ✅ Ready to begin Epic 1 Sprint 1 without blockers
- ✅ **PM approval of contingency plan (Option 1+3: Assisted mode + hybrid detection)** ⭐ NEW

---

## Dependencies & Handoffs

### Epic 0 → Epic 1 Handoff

**What Epic 1 Receives:**
1. Test corpus (10 documents, ground truth annotations) - **Story 0.1**
2. Development environment ready (all tools configured) - **Story 0.2**
3. NLP viability assessment (spaCy benchmark results) - **Story 0.3**
4. **Validation UI specification (wireframes, UX design, interaction patterns)** - **Story 0.4** ⭐ NEW

**What Epic 1 Must Implement:**
- Story 1.4 (Project Foundation) includes validation UI module structure
- Story 1.5 (Walking Skeleton) includes basic validation stub
- **NEW Story 1.7:** Full validation UI implementation (moved from Epic 3) ⭐ CRITICAL

---

## Risk Assessment (Post-Benchmark)

### Risk 1: Validation UI Design Underestimated

**Likelihood:** MEDIUM
**Impact:** HIGH (blocks MVP if users find validation too burdensome)

**Mitigation:**
- Story 0.4 includes user feedback session (5-10 min with 2 target users)
- Allocate 2-3 days for Story 0.4 (not rushed)
- PM reviews wireframes before Epic 1 begins

**Kill Criteria:** If 2/2 users in feedback session say "this looks too slow/annoying"

---

### Risk 2: Epic 1 Timeline Impact

**Likelihood:** HIGH
**Impact:** MEDIUM (1-2 week delay to Epic 1)

**Context:** Adding validation UI implementation (Story 1.7) to Epic 1 extends timeline.

**Mitigation:**
- De-scope less critical Epic 1 stories if needed
- Consider extending Epic 1 from 4 weeks → 5 weeks
- Parallel work: Dev implements NLP while PM finalizes validation UX

**Decision Point:** Week 0 - PM decides if Epic 1 extension acceptable

---

### Risk 3: User Research Reveals Validation Workflow Unacceptable

**Likelihood:** LOW
**Impact:** CRITICAL (requires product pivot)

**Scenario:** User interviews (positioning doc Appendix B) reveal 50%+ users find 40-50% detection + validation "too much work"

**Mitigation:**
- Conduct user interviews ASAP (during Epic 0)
- Prepare backup contingency: Delay MVP for fine-tuning (1-2 sprints)
- Alternative: Pivot to manual-first tool with AI suggestions (different product)

**Kill Criteria:** If ≥3/5 users rate validation workflow <3/5 in interviews

---

## Timeline Estimate (Updated)

| Story | Original Est. | New Est. | Change |
|-------|--------------|----------|--------|
| 0.1: Test Corpus | 2-3 days | 2-3 days | No change |
| 0.2: Dev Environment | 1 day | 1 day | No change |
| 0.3: NLP Viability | 1 day | 1 day | No change |
| **0.4: Validation UI Design** | N/A | **2-3 days** | ⭐ NEW |
| **Total** | **4-5 days** | **6-8 days** | **+2-3 days** |

**Recommendation:** Allocate full Week 0 (5 working days) for Epic 0, accepting potential 1-3 day overflow into Week 1.

---

## Success Criteria (Updated)

Epic 0 is successful if:

1. ✅ Test corpus ready (10 docs, annotations, documentation)
2. ✅ Dev environment functional (can run pytest, Black, mypy)
3. ✅ NLP benchmark complete (spaCy viability assessed, contingency plan documented)
4. ✅ **Validation UI design approved by PM and reviewed by 2 users** ⭐ NEW
5. ✅ **PM sign-off on "AI-assisted" positioning and mandatory validation approach** ⭐ NEW
6. ✅ Epic 1 can start without blockers (no critical unknowns)

---

## Next Steps

1. **Immediate (Week 0 - Day 1-2):** Complete Story 0.1-0.2 (test corpus, dev environment)
2. **Week 0 - Day 3:** Complete Story 0.3 (NLP benchmark) - **ALREADY DONE** (Story 1.2 results available)
3. **Week 0 - Day 4-5:** Complete Story 0.4 (validation UI design) - **NEW CRITICAL PATH**
4. **Week 0 - End:** PM approval meeting (positioning, contingency plan, Epic 1 scope)
5. **Week 1 - Start:** Begin Epic 1 with validated approach

---

**Document Status:** RESCOPED v2.0 (Post-Story 1.2 Benchmark)
**Date:** 2026-01-16
**Approvals Needed:**
- [ ] PM approval of rescoped Epic 0
- [ ] Architect review of validation UI design requirements
- [ ] Dev lead confirmation of Epic 1 timeline impact

**Key Decisions Made:**
- ✅ Contingency plan selected: Option 1+3 (Assisted mode + Hybrid detection)
- ✅ Validation UI moved from Epic 3 to Epic 0/1 (critical path)
- ✅ "AI-assisted" positioning approved (see [positioning-messaging-v2-assisted.md](../positioning-messaging-v2-assisted.md))
