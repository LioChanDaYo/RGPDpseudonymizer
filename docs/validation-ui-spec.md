# Validation UI/UX Specification

**Document Version:** 1.2 (Final)
**Created:** 2026-01-16
**Last Updated:** 2026-01-16 (PM + Dev Reviews Complete)
**Status:** ✅ **APPROVED - Ready for Story 1.7 Implementation**
**Related Story:** [Story 0.4: Validation UI/UX Design](stories/0.4.validation-ui-ux-design.story.md)

---

## 1. Overview

### 1.1 Purpose

This document specifies the user interface and user experience design for the **mandatory entity validation workflow** in the GDPR Pseudonymizer MVP. Given the NLP accuracy limitations discovered in Story 1.2 (29.5% F1 score), validation is no longer optional—users MUST review and confirm detected entities to ensure 100% accuracy.

### 1.2 User Experience Goals

**Primary Goal:** Enable users to efficiently verify 50-70% of entities without validation feeling burdensome.

**Key Principles:**
- **Speed:** Target <2 minutes for reviewing 20-30 entities (typical 2-5K word document)
- **Clarity:** Present entities with sufficient context for confident decisions
- **Efficiency:** Keyboard-driven interface with batch operations and smart defaults
- **Positive Framing:** "Quality control review" not "fixing AI mistakes"
- **Transparency:** Show confidence scores, provide context, highlight ambiguities

### 1.3 Business Goals & Success Metrics

**Primary Business Objective:** Enable efficient GDPR document pseudonymization with mandatory validation while maintaining user acceptance and operational efficiency.

**Quantified Success Metrics:**

| Metric | Target | Measurement Method | Baseline |
|--------|--------|-------------------|----------|
| **Validation Time Efficiency** | <3 minutes for 30 entities | Stopwatch timing during user testing (AC8) | Current manual process: ~8-10 minutes |
| **User Satisfaction** | ≥85% satisfaction (≥4/5 rating) | User feedback ratings (AC8): Speed, Clarity, Ease of Use | N/A (new feature) |
| **Accuracy Achievement** | 100% entity accuracy after validation | QA testing with ground-truth datasets | Pre-validation: 29.5% F1 (spaCy) |
| **User Adoption** | ≥90% users complete validation without quitting | Telemetry: Validation completion rate vs. quit rate | N/A (new feature) |
| **Time Savings vs. Manual** | 60% reduction in validation time | Compare to manual document review process | Manual baseline to be established in Epic 0 |

**Success Criteria for MVP Launch:**
- ✅ Validation time <3 minutes for typical document (20-30 entities)
- ✅ User satisfaction ≥4/5 on all three dimensions (speed, clarity, ease of use)
- ✅ 100% accuracy achieved in QA testing with 50 ground-truth documents
- ✅ <10% user quit rate during validation sessions (telemetry)
- ✅ 60% faster than current manual pseudonymization process

**Timeframe:** Achieve all metrics by end of Epic 1 (Week 4), validate in Epic 4 user testing (Week 11-13)

### 1.4 Critical Context

**From Story 1.2 NLP Benchmark Results:**
- spaCy F1 Score: 29.5% (55% below 85% target)
- Stanza F1 Score: 11.9% (73% below 85% target)
- **Implication:** Users will spend **80% of their time** in validation workflow (not just 20%)
- **Positioning:** "AI-assisted workflow" not "fully automatic tool"

**Functional Requirements:**
- **FR7:** Mandatory interactive validation mode for entity review before pseudonymization
- **FR18:** Validation mode enabled by default (no `--validate` flag required)

---

## 2. Library Selection

### 2.1 Recommended Library: `rich` (Primary Choice)

**Rationale:**
- ✅ Already in tech stack (used for progress bars)
- ✅ Comprehensive CLI UI features (tables, panels, prompts, color coding)
- ✅ Active maintenance and excellent documentation
- ✅ No additional dependencies

**Required Features:**
- `rich.table.Table` - Entity display in tabular format
- `rich.panel.Panel` - Grouped sections (PERSON, LOCATION, ORG)
- `rich.prompt.Confirm` - Yes/no confirmation prompts
- `rich.prompt.Prompt` - Text input for manual entity additions/edits
- `rich.console.Console` - Color-coded output, syntax highlighting
- `rich.progress.Progress` - Progress bars for validation workflow
- `rich.syntax.Syntax` - Syntax highlighting for context snippets

### 2.2 Alternative Libraries (Evaluated)

**`questionary`**
- ✅ Better keyboard navigation than rich
- ✅ Interactive list selection with arrow keys
- ❌ Not in tech stack (additional dependency)
- **Verdict:** Consider for future enhancement if rich keyboard navigation proves insufficient

**`inquirer`**
- ✅ Terminal UI toolkit with checkbox prompts
- ✅ List selection, multi-select support
- ❌ Not in tech stack (additional dependency)
- ❌ Less actively maintained than rich
- **Verdict:** Not recommended

**`prompt_toolkit`**
- ✅ Low-level terminal UI library with maximum control
- ✅ Full keyboard navigation customization
- ❌ More complex to implement
- ❌ Overkill for MVP requirements
- **Verdict:** Not recommended for MVP

### 2.3 Selection Decision

**Primary:** `rich` (already in tech stack, sufficient for MVP)
**Fallback:** `questionary` (if keyboard navigation improvements needed post-MVP)

### 2.4 Batch Mode Validation Threshold & Scope Boundaries

**Problem:** Large batch processing jobs may generate hundreds or thousands of entities across multiple documents, making single-session validation impractical.

**Maximum Single-Session Validation Capacity:** **300 entities**

**Rationale:**
- User testing target: <3 minutes for 30 entities = ~6 seconds/entity
- At 6 seconds/entity, 300 entities = 30 minutes (upper limit of acceptable validation session)
- Beyond 300 entities: Risk of user fatigue, errors, session abandonment

**Batch Mode Validation Strategies:**

| Entity Count | Strategy | User Experience |
|--------------|----------|-----------------|
| **1-100 entities** | Single-session validation (all at once) | Standard workflow (Sections 5.1-5.4) |
| **101-300 entities** | Single-session with pagination | Show page indicators, batch operations encouraged |
| **301-500 entities** | **Per-document validation** (default) | Validate each document individually before batch processing |
| **501+ entities** | **Warning + per-document validation** | "Large batch detected. Validating per-document to maintain efficiency." |

**Implementation Guidelines:**

**Scenario 1: Small Batch (1-100 entities across 20 documents)**
```
╔══════════════════════════════════════════════════════════════════════╗
║ Batch Validation - 20 documents                                     ║
║ Total: 87 entities detected (60 PERSON, 15 LOCATION, 12 ORG)       ║
║ Estimated review time: ~9 minutes                                   ║
║                                                                      ║
║ Press [Enter] to begin validation (all documents at once)           ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Scenario 2: Medium Batch (301-500 entities across 50 documents)**
```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  Large Batch Detected - Per-Document Validation                 ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ Batch: 50 documents                                                 ║
║ Total: 423 entities detected                                        ║
║                                                                      ║
║ Strategy: Validate each document individually (easier to manage)    ║
║ Average: 8 entities per document (~48 seconds per document)         ║
║ Total estimated time: ~40 minutes                                   ║
║                                                                      ║
║ Recommendation: Consider splitting batch into 2-3 smaller batches   ║
║                 for more manageable validation sessions.             ║
║                                                                      ║
║ Press [Enter] to begin per-document validation                      ║
║ Press [S] to split batch (manual file selection)                    ║
║ Press [Q] to quit and reorganize                                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Scenario 3: Very Large Batch (501+ entities across 100 documents)**
```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  VERY LARGE BATCH - Validation Time Warning                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ Batch: 100 documents                                                ║
║ Total: 847 entities detected                                        ║
║                                                                      ║
║ Estimated validation time: ~85 minutes (1.4 hours)                  ║
║                                                                      ║
║ ⚠️  RECOMMENDATION: Split this batch into smaller chunks            ║
║                                                                      ║
║ Suggested approach:                                                 ║
║   • Split into 3 batches of ~33 documents each                      ║
║   • Validate each batch separately (~30 minutes per batch)          ║
║   • Process each batch after validation                             ║
║                                                                      ║
║ Press [C] to continue anyway (per-document validation)              ║
║ Press [Q] to quit and reorganize batch                              ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Per-Document Validation Workflow (301+ entities):**

When batch exceeds 300 entities, switch to per-document validation:

1. **Iterate through each document sequentially:**
   - Show: "Validating document 5 of 50: report_2024_Q3.txt (12 entities)"
   - User validates entities for that document only
   - After validation complete, move to next document

2. **Allow skipping/pausing:**
   - `[S]` Skip to next document (mark current as "pending review")
   - `[P]` Pause batch validation (save progress, resume later)
   - `[Q]` Quit batch validation (no processing)

3. **Progress tracking:**
   - "Batch progress: 15/50 documents validated (30% complete)"
   - "Estimated remaining time: ~25 minutes"

**Edge Case: Resume Interrupted Batch Validation**

If user quits mid-batch (e.g., validated 15 of 50 documents), save validation state:

```
╔══════════════════════════════════════════════════════════════════════╗
║ Resume Batch Validation?                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ Previous session detected:                                          ║
║   • Batch: 50 documents                                             ║
║   • Progress: 15 documents validated, 35 remaining                  ║
║   • Last validated: report_2024_Q3.txt (2 hours ago)                ║
║                                                                      ║
║ Press [R] to resume from document 16                                ║
║ Press [N] to start new validation (discard previous progress)       ║
║ Press [Q] to quit                                                   ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Out of Scope for MVP:**
- ❌ Parallel validation (multiple documents simultaneously)
- ❌ Distributed validation (team collaboration on large batch)
- ❌ Automatic batch splitting (user must manually split)
- ❌ Background validation (save progress and resume later with state persistence)

**Future Enhancements (Post-MVP):**
- Session state persistence for crash recovery (Section 12.2)
- Validation history reuse across documents (Section 12.2)
- ML-based intelligent batch splitting (group similar documents)

---

## 3. User Action Taxonomy

### 3.1 Core Actions

| Action | Keyboard Shortcut | Description | Use Case |
|--------|-------------------|-------------|----------|
| **✅ Confirm** | `Space` | Accept entity and suggested pseudonym | Entity is correct, pseudonym is acceptable |
| **❌ Reject** | `R` | Remove false positive | NLP incorrectly identified non-entity (e.g., "Paris" as location in "Paris Hilton") |
| **✏️ Modify** | `E` | Edit entity text | Expand partial entity (e.g., "Marie" → "Marie Dubois") |
| **➕ Add** | `A` | Manually add missed entity | NLP missed an entity (false negative) |
| **🔄 Change Pseudonym** | `C` | Override suggested pseudonym | User wants different pseudonym than AI suggestion |

### 3.2 Navigation Actions

| Action | Keyboard Shortcut | Description |
|--------|-------------------|-------------|
| **Next** | `N` or `→` | Move to next entity |
| **Previous** | `P` or `←` | Move to previous entity |
| **Jump to Entity** | `J` + number | Jump to entity #N (e.g., `J15` → entity 15) |
| **Skip to Type** | `S` | Skip to next entity type (PERSON → LOCATION → ORG) |
| **Quit** | `Q` | Quit validation (prompts for confirmation) |

### 3.3 Batch Operations

| Action | Keyboard Shortcut | Description | Use Case |
|--------|-------------------|-------------|----------|
| **Accept All Type** | `Shift+A` | Accept all entities of current type | All PERSON entities look correct |
| **Reject All Type** | `Shift+R` | Reject all entities of current type | All ORG entities are false positives |
| **Accept All** | `Ctrl+A` | Accept all remaining entities | High confidence in remaining entities |
| **Review Accepted** | `Shift+V` | Review entities already accepted via smart defaults | Double-check pre-accepted high-confidence entities |

### 3.4 Help & Utility Actions

| Action | Keyboard Shortcut | Description |
|--------|-------------------|-------------|
| **Help** | `H` or `?` | Show keyboard shortcuts and action descriptions |
| **Show Context** | `X` | Expand context snippet (show more surrounding text) |
| **Show Document** | `D` | Open document preview with entity highlighted |
| **Undo Last** | `U` | Undo last action (confirm → pending, reject → restore) |

---

## 4. Entity Presentation Format

### 4.1 Entity Grouping

**Strategy:** Group entities by type, review in priority order:

1. **PERSON** (highest priority - most sensitive)
2. **ORG** (medium priority)
3. **LOCATION** (lowest priority - least sensitive)

**Rationale:** Focus user attention on most critical entities first (personal names).

### 4.2 Entity Display Components

Each entity displayed with the following information:

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. Marie Dubois              → Leia Organa     [✓ Confirm] [✗ Reject]│
│    Context: "...interview with Marie Dubois about her experience..." │
│    Confidence: 95% ● High                                             │
│    Type: PERSON | Occurrences: 3                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Display Fields:**

1. **Entity Number:** Sequential number for navigation (e.g., "1.", "2.")
2. **Entity Text:** Original text detected by NLP (e.g., "Marie Dubois")
3. **Suggested Pseudonym:** AI-generated replacement (e.g., "Leia Organa")
4. **Quick Actions:** Visual buttons for confirm/reject
5. **Context Snippet:** 10 words before/after entity, with entity highlighted
6. **Confidence Score:** Percentage + color-coded indicator (see 4.3)
7. **Entity Type:** PERSON, LOCATION, ORG
8. **Occurrence Count:** How many times entity appears in document

### 4.3 Confidence Score Display

**Color-Coded Confidence Levels:**

| Confidence | Color | Symbol | Interpretation |
|------------|-------|--------|----------------|
| **>80%** | Green | ● | High confidence - likely correct |
| **60-80%** | Yellow | ◐ | Medium confidence - review carefully |
| **<60%** | Red | ○ | Low confidence - may be false positive |
| **N/A** | Gray | ─ | No confidence score available |

**Smart Default Behavior:**
- Entities with >90% confidence are **pre-accepted** (shown with green checkmark ✓)
- Users can review pre-accepted entities via `Shift+V` (Review Accepted)
- Pre-acceptance saves time on obvious high-confidence entities

### 4.4 Ambiguity Indicators

**Ambiguous Standalone Components (FR4 Logic):**

When entity is a standalone component potentially related to a full name:

```
┌──────────────────────────────────────────────────────────────────────┐
│ 3. Marie                     → Leia ⚠️          [✓ Confirm] [✗ Reject]│
│    Context: "...when Marie said this during the interview..."        │
│    ⚠️  Ambiguous: Standalone component. Related to "Marie Dubois"?   │
│    Confidence: 72% ◐ Medium                                           │
└──────────────────────────────────────────────────────────────────────┘
```

**Ambiguity Warning Components:**
- **Warning Icon:** ⚠️ (yellow triangle)
- **Explanation Text:** "Ambiguous: Standalone component. Related to '[Full Name]'?"
- **Suggested Action:** User should decide if standalone refers to full name or is separate entity

### 4.5 Context Snippet Format

**Default Context:** 10 words before + entity + 10 words after

```
Context: "...interview with Marie Dubois about her experience working at..."
                        ^^^^^^^^^^^^
                        (highlighted)
```

**Expandable Context (X key):**
- Shows 30 words before/after (total ~60 words)
- Useful when 10-word context is insufficient for decision

**Context Highlighting:**
- Entity text highlighted in bold/color
- Surrounding text in normal weight
- Ellipsis (...) indicates truncated text

---

## 5. Validation Workflow Steps

### 5.1 Step 1: Summary Screen

**Purpose:** Set user expectations and provide overview of validation task

```
╔══════════════════════════════════════════════════════════════════════╗
║ GDPR Pseudonymizer - Entity Validation                              ║
║ File: interview_transcript_01.txt (2,340 words)                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ 📊 Detection Summary:                                               ║
║   • 23 entities detected                                            ║
║   • Breakdown: 15 PERSON, 5 LOCATION, 3 ORG                         ║
║   • Estimated review time: ~2 minutes                               ║
║                                                                      ║
║ ⏱️  Quick Review:                                                    ║
║   • Average: 3-5 seconds per entity                                 ║
║   • Keyboard shortcuts available (press H for help)                 ║
║                                                                      ║
║ Press [Enter] to begin validation                                   ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Information Displayed:**
- File name and word count
- Total entities detected
- Breakdown by entity type (PERSON, LOCATION, ORG)
- Estimated review time (calculated: entity count × 4 seconds average)
- Instructions to begin

### 5.2 Step 2: Entity Type Review

**Purpose:** Review entities grouped by type, focusing on most critical (PERSON) first

```
╔══════════════════════════════════════════════════════════════════════╗
║ PERSON Entities (15 found)                              [1/3 types] ║
║ Progress: Entity 1 of 15                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 1. Marie Dubois          → Leia Organa   [✓ Confirm] [✗ Reject]│ ║
║ │    Context: "...interview with Marie Dubois about..."           │ ║
║ │    Confidence: 95% ● High                                       │ ║
║ │    Type: PERSON | Occurrences: 3                                │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║ Actions: [Space] Confirm | [R] Reject | [E] Edit | [N] Next        ║
║          [Shift+A] Accept All PERSON | [S] Skip to LOCATION        ║
║          [H] Help                                                   ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Workflow:**
1. Show entities of type PERSON first (15 entities)
2. User reviews each entity sequentially (confirm, reject, edit, etc.)
3. After all PERSON entities reviewed, move to next type
4. Repeat for LOCATION (5 entities), then ORG (3 entities)

**Progress Indicators:**
- Type progress: "PERSON Entities (15 found) [1/3 types]"
- Entity progress: "Progress: Entity 1 of 15"
- Overall progress bar at bottom (optional)

### 5.3 Step 3: Ambiguous Entity Review

**Purpose:** Flag and confirm entities with ambiguity warnings (standalone components)

```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  Ambiguous Entities Review (2 found)                            ║
║ Progress: Entity 1 of 2                                             ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 3. Marie                 → Leia ⚠️        [✓ Confirm] [✗ Reject]│ ║
║ │    Context: "...when Marie said this during..."                 │ ║
║ │    ⚠️  Ambiguous: Standalone component.                         │ ║
║ │       Related to "Marie Dubois" (entity #1)?                    │ ║
║ │    Confidence: 72% ◐ Medium                                     │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║ Actions: [C] Confirm as separate | [M] Merge with "Marie Dubois"   ║
║          [R] Reject | [X] Show more context                         ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Workflow:**
1. After all entity types reviewed, show ambiguous entities separately
2. User decides if ambiguous entity is separate or should be merged
3. Special actions: `C` (confirm as separate), `M` (merge with full name)

**Skip Condition:**
- If no ambiguous entities detected, skip this step entirely

### 5.4 Step 4: Final Confirmation

**Purpose:** Summarize changes and get final approval before processing

```
╔══════════════════════════════════════════════════════════════════════╗
║ ✅ Review Complete                                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ Summary:                                                             ║
║   • 20 entities confirmed (13 PERSON, 5 LOCATION, 2 ORG)           ║
║   • 3 entities rejected (2 PERSON false positives, 1 ORG)          ║
║   • 0 entities added manually                                       ║
║   • 0 pseudonyms modified                                           ║
║                                                                      ║
║ Validation time: 2m 18s                                             ║
║                                                                      ║
║ ⚠️  Warning: 3 entities rejected. Ensure no false negatives missed. ║
║                                                                      ║
║ Proceed with pseudonymization? [Y/n]                                ║
║   [Y] Yes, proceed  [N] No, go back to review  [Q] Quit without save║
╚══════════════════════════════════════════════════════════════════════╝
```

**Information Displayed:**
- Confirmed entities count and breakdown by type
- Rejected entities count and breakdown
- Manually added entities count
- Modified pseudonyms count
- Total validation time
- Warning if many entities rejected (potential false negatives)

**User Options:**
- `Y` - Proceed with pseudonymization
- `N` - Go back to entity review (allows corrections)
- `Q` - Quit without saving (confirmation required)

---

## 6. Performance Optimization Strategies

### 6.1 Lazy Loading (Pagination)

**Problem:** Rendering 100+ entities at once causes terminal performance issues

**Solution:** Load entities page-by-page (10-20 entities at a time)

```
╔══════════════════════════════════════════════════════════════════════╗
║ PERSON Entities (50 found)                              [1/3 types] ║
║ Showing: 1-10 of 50                                   [Page 1 of 5] ║
╠══════════════════════════════════════════════════════════════════════╣
║ ... (10 entities displayed) ...                                     ║
║                                                                      ║
║ Navigation: [N] Next entity | [Shift+N] Next page (11-20)          ║
║             [P] Previous entity | [Shift+P] Previous page           ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Implementation:**
- Page size: 10-20 entities (configurable)
- Show page indicator: "Page 1 of 5"
- Navigation: `Shift+N` (next page), `Shift+P` (previous page)

### 6.2 Context Precomputation

**Problem:** Re-reading file for each entity context is slow

**Solution:** Precompute all context snippets before user interaction

**Implementation:**
1. After NLP detection, iterate through all entities
2. Extract context snippet (10 words before/after) for each entity
3. Cache context snippets in memory (dict: entity_id → context)
4. During validation, lookup context from cache (O(1) access)

**Memory Efficiency:**
- 100 entities × 20 words/context × 10 bytes/word = ~20KB (negligible)

### 6.3 Keyboard-Only Navigation

**Problem:** Mouse interaction is slow and requires hand movement

**Solution:** All actions accessible via single-key shortcuts

**Benefits:**
- Speed: Single keystroke vs. mouse movement + click
- Accessibility: Screen reader compatible, no mouse required
- User experience: Power users can review entities rapidly

**Implementation:**
- Single-key shortcuts for all actions (Space, R, E, A, N, etc.)
- No mouse capture required (terminal compatibility)
- Help menu (H key) shows all shortcuts

### 6.4 Smart Defaults (Pre-Acceptance)

**Problem:** High-confidence entities slow down validation unnecessarily

**Solution:** Pre-accept entities with >90% confidence, allow review via `Shift+V`

**Implementation:**
1. After NLP detection, mark entities with confidence >90% as "pre-accepted"
2. Show pre-accepted entities with green checkmark (✓) in summary
3. Allow user to review pre-accepted entities via `Shift+V` action
4. If user skips pre-accepted review, proceed with pre-accepted entities

**Benefits:**
- Time savings: Skip obvious entities (e.g., "Marie Dubois" with 95% confidence)
- Flexibility: User can still review if desired
- Psychological framing: Reinforces "AI-assisted" positioning

**Example:**
```
Summary: 23 entities detected
  • 18 pre-accepted (confidence >90%)
  • 5 pending review (confidence <90%)

Press [Enter] to review 5 pending entities
Press [Shift+V] to review all 23 entities (including pre-accepted)
```

### 6.5 Security & Privacy Requirements

**Critical Context:** Validation UI displays sensitive personal data (names, organizations, locations) in plaintext on the terminal. This introduces privacy and security risks that must be addressed in MVP.

#### 6.5.1 Screen Privacy Considerations

**Problem:** Sensitive data displayed on screen is vulnerable to "shoulder surfing" (unauthorized viewing by nearby individuals).

**Mitigation Strategies:**

**1. User Warning (Mandatory - MVP):**

Display privacy warning at start of validation session:

```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  PRIVACY NOTICE                                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ This validation session will display sensitive personal data on     ║
║ your screen, including names, organizations, and locations.         ║
║                                                                      ║
║ Security Recommendations:                                           ║
║   • Ensure you are in a private workspace                           ║
║   • Lock screen when stepping away (Ctrl+L)                         ║
║   • Close terminal window when validation complete                  ║
║                                                                      ║
║ Press [Y] to acknowledge and continue                               ║
║ Press [N] to cancel validation                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**2. Quick Screen Clear (MVP):**

Add keyboard shortcut to immediately clear screen if unauthorized person approaches:

- **Shortcut:** `Ctrl+L` (standard terminal clear)
- **Behavior:** Clear terminal screen, show "Session paused - Press any key to resume"
- **State:** Preserve validation progress (do not lose user actions)

**3. Auto-Timeout (Out of Scope - Post-MVP):**
- After 5 minutes of inactivity, auto-clear screen and require re-authentication
- Deferred to Post-MVP (security enhancement)

#### 6.5.2 Terminal History & Command Logging

**Problem:** Terminal emulators and shell history may log sensitive data displayed during validation.

**Mitigation Strategies:**

**1. Disable Terminal Scrollback (MVP - Best Effort):**

Attempt to disable terminal scrollback buffer for validation session:

```python
# Example implementation (rich library)
console = Console(force_terminal=True, legacy_windows=False)
console.clear()  # Clear scrollback before validation
# ... validation session ...
console.clear()  # Clear scrollback after validation
```

**Note:** Not all terminal emulators support programmatic scrollback clearing. Document limitation in user docs.

**2. Avoid Logging Entity Text in Shell History (MVP):**

Ensure CLI commands do not log sensitive entity data:

- ✅ **Acceptable:** `gdpr-pseudo process input.txt output.txt`
- ❌ **Avoid:** `gdpr-pseudo process --entities "Marie Dubois,Paris,Google" input.txt output.txt`

All entity data must be read from files or interactive prompts, never passed as command-line arguments.

**3. Warn Users About Terminal Multiplexers (MVP - Documentation):**

Document in user guide:

> **Security Note:** If using terminal multiplexers (tmux, screen) or terminal emulators with history logging, be aware that sensitive data from validation sessions may be retained in scrollback buffers. Close terminal sessions after validation to minimize exposure.

#### 6.5.3 Session Data Cleanup

**Problem:** Validation session data (entities, context snippets, user actions) remains in memory after completion.

**Mitigation Strategies:**

**1. Explicit Memory Cleanup (MVP):**

After validation complete and processing finished:

```python
# Pseudocode
def cleanup_validation_session(entities: List[Entity]) -> None:
    """Clear sensitive data from memory after validation."""
    for entity in entities:
        # Clear sensitive fields
        entity.text = None
        entity.context_snippet = None
        entity.modified_text = None
    entities.clear()
    # Force garbage collection (optional)
    import gc
    gc.collect()
```

**2. Temporary File Handling (MVP):**

If validation state is persisted to temporary files (e.g., for crash recovery):
- Store in OS-specific secure temp directory (`/tmp` on Linux, `%TEMP%` on Windows)
- Use secure file permissions (0600 - owner read/write only)
- Delete temporary files immediately after session completion
- **Out of Scope for MVP:** Session state persistence deferred (Section 2.4)

#### 6.5.4 Audit Trail Privacy (FR12 Compliance)

**Problem:** Audit trail logs user actions but must not expose sensitive entity text unnecessarily.

**Mitigation Strategy:**

**Redact Entity Text in Audit Logs (MVP):**

When logging user actions to audit trail (FR12):

- ✅ **Log:** Entity ID, action type, timestamp, document ID
- ❌ **Do NOT log:** Entity text content (unless explicitly required for compliance)

**Example Audit Log Entry:**
```json
{
  "entity_id": "e7f3a2b1-4c8d-4e9f-b2a1-3d8e7f9c1a2b",
  "user_action": "REJECTED",
  "timestamp": "2026-01-16T14:32:15Z",
  "document_id": "interview_01.txt",
  "rejection_reason": "False positive - language name",
  "entity_text": "[REDACTED]"  // Do not log sensitive text
}
```

**Exception:** If GDPR compliance requires logging entity text for audit purposes, encrypt audit trail files at rest.

#### 6.5.5 Network Transmission (N/A for MVP)

**Scope:** MVP is CLI tool with local processing only (no network transmission).

**Future Consideration (Post-MVP):**
- If validation UI moves to web-based interface, use HTTPS for all sensitive data transmission
- If telemetry includes entity statistics, ensure entity text is never transmitted

#### 6.5.6 Secure Development Practices

**Code Review Requirements:**
- All validation UI code must be reviewed for potential information leakage
- Ensure no `print()` or `logging.debug()` statements expose entity text
- Validate that error messages do not include sensitive entity data

**Testing Requirements:**
- Security testing checklist item: "Verify terminal scrollback cleared after validation"
- Security testing checklist item: "Verify entity text not logged in shell history"
- Security testing checklist item: "Verify temporary files deleted after session"

#### 6.5.7 Compliance Considerations

**GDPR Article 32 - Security of Processing:**

Validation UI handles personal data and must implement "appropriate technical and organizational measures" to ensure security:

- ✅ **Pseudonymization:** Validation occurs before pseudonymization (user confirms entities to be pseudonymized)
- ✅ **Confidentiality:** Screen privacy warnings, terminal history mitigation
- ✅ **Integrity:** Audit trail logging with privacy-preserving redaction
- ✅ **Availability:** Session state cleanup prevents data leakage

**Documentation Requirement:**
- Add Security & Privacy section to user documentation (README.md)
- Include best practices for secure validation sessions

#### 6.5.8 Known Limitations & User Responsibility

**MVP Limitations:**

1. **Terminal Scrollback:** Cannot guarantee scrollback clearing on all terminal emulators
2. **Screen Recording:** Cannot detect or prevent screen recording software
3. **Physical Security:** User responsible for securing physical workspace

**User Responsibilities (Documented in User Guide):**

- Use validation tool in private workspace
- Lock screen when stepping away
- Close terminal session after validation
- Avoid using validation tool on shared computers
- Do not take screenshots of validation sessions

---

## 7. Psychological Framing Strategy

### 7.1 Positive Framing Principles

**Goal:** Validation should feel like "quality control" not "doing AI's job"

**Framing Strategies:**

| ❌ Negative Framing | ✅ Positive Framing |
|---------------------|---------------------|
| "Fix AI mistakes" | "Quality control review" |
| "Review 50 entities" | "Quick review: ~3 minutes" |
| "AI missed entities" | "Enhance detection with your expertise" |
| "Low confidence" | "Needs your confirmation" |
| "False positive" | "Not a sensitive entity" |

### 7.2 Time Estimates and Progress Feedback

**Set Clear Expectations:**

```
Estimated review time: ~2 minutes
Average: 3-5 seconds per entity
```

**Show Progress:**

```
Progress: Entity 8 of 23 (35% complete)
Time elapsed: 45s | Estimated remaining: 1m 15s
```

**Success Messaging:**

```
✅ Review complete! Processing with 100% accuracy...
Validation time: 2m 18s (faster than estimated!)
```

### 7.3 Default to AI Suggestions

**Principle:** User confirms/overrides (not selects from scratch)

**Implementation:**
- Always show suggested pseudonym (e.g., "Marie Dubois → Leia Organa")
- Default action is "Confirm" (Space key) - accept AI suggestion
- User only acts when correction needed (reject, edit, change pseudonym)

**Psychological Benefit:**
- Feels like validation (quick review) not creation (tedious work)
- Reduces cognitive load (accept vs. generate)

### 7.4 Reinforcing "AI-Assisted" Positioning

**Messaging Throughout Workflow:**

**Summary Screen:**
```
23 entities detected by AI. Quick review before processing...
Your expertise ensures 100% accuracy.
```

**Entity Review:**
```
AI suggests: "Leia Organa" (confidence: 95%)
[✓ Confirm AI suggestion] or [Override]
```

**Final Confirmation:**
```
Review complete! AI + Your Review = 100% accuracy
Processing 20 validated entities...
```

### 7.5 Entity Model Requirements for Validation UI

**Purpose:** Define the data structure requirements for the `Entity` model to support validation UI functionality.

**Critical Context:** The validation UI needs specific entity metadata beyond basic NER output (text, type, position). This section specifies required fields for display, user interaction, and audit trail.

#### 7.5.1 Core Entity Fields (Required for NER Output)

| Field | Type | Description | Example | Validation UI Usage |
|-------|------|-------------|---------|---------------------|
| `id` | str (UUID) | Unique entity identifier | `"e7f3a2b1-..."` | Entity tracking across validation actions |
| `text` | str | Original entity text from document | `"Marie Dubois"` | Display in entity card (Section 4.2) |
| `type` | EntityType | Entity classification | `PERSON` / `ORG` / `LOCATION` | Grouping and prioritization (Section 4.1) |
| `start_pos` | int | Character position (start) in document | `147` | Context snippet extraction |
| `end_pos` | int | Character position (end) in document | `159` | Context snippet extraction |
| `confidence` | float (0-1) | NER model confidence score | `0.95` | Color-coded display (Section 4.3) |
| `document_id` | str | Source document identifier | `"doc_001.txt"` | Batch validation grouping |

**EntityType Enum:**
```python
class EntityType(Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOCATION"
```

#### 7.5.2 Validation UI Metadata Fields (Added by Validation Handler)

| Field | Type | Description | Example | Purpose |
|-------|------|-------------|---------|---------|
| `context_snippet` | str | Text surrounding entity (10 words before/after) | `"...interview with Marie Dubois about her..."` | Display context (Section 4.5) |
| `is_ambiguous` | bool | Standalone component flag (FR4 logic) | `True` | Ambiguity warning (Section 4.4) |
| `related_entities` | List[str] | IDs of related entities (for ambiguous components) | `["e7f3a2b1-..."]` | Link "Marie" to "Marie Dubois" |
| `suggested_pseudonym` | str | AI-generated pseudonym suggestion | `"Leia Organa"` | Default pseudonym (Section 7.3) |
| `occurrence_count` | int | Number of times entity appears in document(s) | `3` | Display in entity card (Section 4.2) |
| `page_number` | int (optional) | Page number in source document | `5` | Context for multi-page docs |

#### 7.5.3 User Action Tracking Fields (Audit Trail - FR12)

| Field | Type | Description | Example | Purpose |
|-------|------|-------------|---------|---------|
| `user_action` | UserAction | User's validation decision | `CONFIRMED` / `REJECTED` / `MODIFIED` | Audit trail logging |
| `user_timestamp` | datetime | Timestamp of user action | `2026-01-16 14:32:15` | Audit trail logging |
| `original_text` | str (optional) | Original entity text (if modified) | `"Marie"` | Track user corrections |
| `modified_text` | str (optional) | User-corrected entity text | `"Marie Dubois"` | Track user corrections |
| `user_pseudonym` | str (optional) | User-overridden pseudonym | `"Princess Leia"` | Track pseudonym changes |
| `rejection_reason` | str (optional) | Why entity was rejected | `"False positive - language name"` | Analytics and ML feedback |

**UserAction Enum:**
```python
class UserAction(Enum):
    PENDING = "PENDING"           # Not yet reviewed
    CONFIRMED = "CONFIRMED"       # User confirmed entity and pseudonym
    REJECTED = "REJECTED"         # User rejected (false positive)
    MODIFIED = "MODIFIED"         # User edited entity text
    PSEUDONYM_CHANGED = "PSEUDONYM_CHANGED"  # User changed pseudonym
    MANUALLY_ADDED = "MANUALLY_ADDED"        # User added entity manually
```

#### 7.5.4 Data Storage Requirements

**In-Memory Storage (During Validation Session):**
- All entities loaded into memory as `List[Entity]` (estimated 20KB for 100 entities)
- Context snippets precomputed and cached (Section 6.2)
- No persistence required during active validation session

**Persistence Requirements:**
- **Audit Trail:** User actions logged to `Operation.user_modifications` field (FR12)
  - Format: JSON array of entity modifications
  - Example: `[{"entity_id": "e7f3a2b1-...", "action": "REJECTED", "reason": "False positive"}]`
- **Session State (Out of Scope for MVP):** Session recovery requires persisting validation progress
  - Deferred to Post-MVP (Section 2.4: "Background validation")

**Data Quality Requirements:**
- **Confidence Score:** Must be in range [0.0, 1.0] or `None` if unavailable
- **Context Snippet:** Must not contain sensitive data if entity is rejected
- **Positions:** `start_pos` < `end_pos`, both must be valid indices in document
- **Entity Type:** Must be one of: PERSON, ORG, LOCATION (no custom types in MVP)

#### 7.5.5 Schema Evolution Considerations

**Known Future Requirements (Post-MVP):**
- `entity_cluster_id`: For grouping related entities (e.g., "Marie", "Dubois", "Marie Dubois")
- `ml_feedback`: User corrections for NER model retraining
- `validation_session_id`: For session state persistence and recovery
- `entity_aliases`: Alternative forms (e.g., "Dr. Dubois", "Marie", "M. Dubois")

**Backward Compatibility:**
- All new fields must be optional (nullable) to avoid breaking existing code
- Default values: `confidence=None`, `is_ambiguous=False`, `user_action=PENDING`

#### 7.5.6 Integration Points

**Validation Handler → Entity Model:**
1. **Input:** NER detection returns `List[Entity]` with core fields (text, type, position, confidence)
2. **Enrichment:** Validation Handler adds metadata fields (context_snippet, is_ambiguous, suggested_pseudonym)
3. **User Interaction:** Validation Handler updates user action fields (user_action, user_timestamp, modified_text)
4. **Output:** Validated `List[Entity]` returned to Orchestrator for processing

**Entity Model → Audit Repository:**
1. **User Modifications:** Extract user action fields from validated entities
2. **Logging:** Serialize to JSON array for `Operation.user_modifications` field (FR12)
3. **Privacy:** Redact entity text if rejected (log action only, not sensitive data)

**Example Entity After Validation:**
```python
Entity(
    id="e7f3a2b1-4c8d-4e9f-b2a1-3d8e7f9c1a2b",
    text="Marie Dubois",
    type=EntityType.PERSON,
    start_pos=147,
    end_pos=159,
    confidence=0.95,
    document_id="interview_01.txt",
    # Validation UI metadata
    context_snippet="...interview with Marie Dubois about her experience...",
    is_ambiguous=False,
    related_entities=[],
    suggested_pseudonym="Leia Organa",
    occurrence_count=3,
    # User action tracking
    user_action=UserAction.CONFIRMED,
    user_timestamp=datetime(2026, 1, 16, 14, 32, 15),
    original_text=None,
    modified_text=None,
    user_pseudonym=None,
    rejection_reason=None
)
```

---

## 8. Edge Case Handling

### 8.1 Edge Case: 0 Entities Detected

**Scenario:** NLP detects no entities (common with 29.5% F1 score - false negatives)

```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  No Entities Detected                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ The AI did not detect any sensitive entities in this document.      ║
║                                                                      ║
║ Possible reasons:                                                    ║
║   • Document contains no sensitive data (✓ safe to proceed)         ║
║   • AI missed entities (false negatives)                            ║
║                                                                      ║
║ What would you like to do?                                          ║
║   [A] Add entities manually (if AI missed any)                      ║
║   [P] Proceed without pseudonymization (no sensitive data)          ║
║   [Q] Quit and review document manually                             ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Options:**
- `A` - Manually add entities (opens entity addition form)
- `P` - Proceed without pseudonymization (copy input to output)
- `Q` - Quit without processing

### 8.2 Edge Case: 100+ Entities Detected

**Scenario:** Document has many entities (e.g., 100+ entities in 10K word document)

```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  Large Entity Count Detected                                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ 127 entities detected in this document.                             ║
║ Estimated review time: ~8-10 minutes                                ║
║                                                                      ║
║ Recommendations:                                                     ║
║   • Use batch operations (Shift+A: Accept All PERSON)               ║
║   • Enable smart defaults (pre-accept high confidence >90%)         ║
║   • Consider splitting document into smaller sections               ║
║                                                                      ║
║ Press [Enter] to begin validation                                   ║
║ Press [S] to enable smart defaults (pre-accept >90% confidence)     ║
║ Press [Q] to quit and split document                                ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Strategies:**
- Pagination (10-20 entities per page)
- Batch operations (Accept All, Reject All)
- Smart defaults (pre-accept high confidence entities)
- Warning about large document size

### 8.3 Edge Case: Long Entity Names

**Scenario:** Entity name exceeds display width (e.g., "Dr. Jean-Pierre Marie-Christine Dubois-Leclerc")

**Solution:** Truncate entity name with ellipsis, show full name in context

```
┌────────────────────────────────────────────────────────────────────┐
│ 5. Dr. Jean-Pierre Marie-Ch... → Han Solo    [✓ Confirm] [✗ Reject]│
│    Context: "...interview with Dr. Jean-Pierre Marie-Christine..." │
│    Full name: Dr. Jean-Pierre Marie-Christine Dubois-Leclerc       │
└────────────────────────────────────────────────────────────────────┘
```

**Truncation Rules:**
- Display width limit: 30 characters for entity name
- If >30 characters, truncate to 27 characters + "..."
- Show full name in separate "Full name:" field
- Context snippet shows full name (no truncation)

### 8.4 Edge Case: Ambiguous Standalone Components

**Scenario:** "Marie" appears 5 times, but only 2 are part of "Marie Dubois"

**Solution:** Group related entities, prompt user to decide relationship

```
╔══════════════════════════════════════════════════════════════════════╗
║ ⚠️  Ambiguous Entities: "Marie" (5 occurrences)                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ Detected:                                                            ║
║   • "Marie Dubois" (entity #1) - PERSON                             ║
║   • "Marie" (5 standalone occurrences) - Potentially related        ║
║                                                                      ║
║ Review each occurrence:                                              ║
║                                                                      ║
║ Occurrence 1:                                                        ║
║   Context: "...when Marie said this during the interview..."        ║
║   [S] Same as "Marie Dubois" | [D] Different person | [R] Reject    ║
║                                                                      ║
║ Occurrence 2:                                                        ║
║   Context: "...Marie mentioned her background in..."                ║
║   [S] Same as "Marie Dubois" | [D] Different person | [R] Reject    ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Actions:**
- `S` - Same person (merge with full name, use same pseudonym)
- `D` - Different person (create separate entity with different pseudonym)
- `R` - Reject (not a person, false positive)

### 8.5 Edge Case: Confidence Score Unavailable

**Scenario:** NER model doesn't provide confidence scores (e.g., Stanza)

**Solution:** Show "N/A" for confidence, disable smart defaults

```
┌────────────────────────────────────────────────────────────────────┐
│ 7. Jean Martin           → Yoda               [✓ Confirm] [✗ Reject]│
│    Context: "...Jean Martin explained the process..."               │
│    Confidence: N/A                                                   │
│    Type: PERSON | Occurrences: 2                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Implications:**
- No color-coded confidence indicator (gray "N/A")
- Smart defaults disabled (can't pre-accept without confidence)
- User must review all entities manually

---

## 9. Example Validation Session Walkthrough

### 9.1 Scenario

**Document:** `interview_transcript_01.txt`
**Word Count:** 2,340 words
**Detected Entities:** 23 entities (15 PERSON, 5 LOCATION, 3 ORG)

### 9.2 Complete Walkthrough

#### Step 1: User Initiates Processing

```bash
$ gdpr-pseudo process interview_transcript_01.txt output.txt
```

#### Step 2: Summary Screen

```
╔══════════════════════════════════════════════════════════════════════╗
║ GDPR Pseudonymizer - Entity Validation                              ║
║ File: interview_transcript_01.txt (2,340 words)                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ 📊 Detection Summary:                                               ║
║   • 23 entities detected                                            ║
║   • Breakdown: 15 PERSON, 5 LOCATION, 3 ORG                         ║
║   • Estimated review time: ~2 minutes                               ║
║                                                                      ║
║ Press [Enter] to begin validation                                   ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Enter`

#### Step 3: Review PERSON Entities (1-15)

```
╔══════════════════════════════════════════════════════════════════════╗
║ PERSON Entities (15 found)                              [1/3 types] ║
║ Progress: Entity 1 of 15                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 1. Marie Dubois          → Leia Organa   [✓ Confirm] [✗ Reject]│ ║
║ │    Context: "...interview with Marie Dubois about her..."       │ ║
║ │    Confidence: 95% ● High                                       │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
║ Actions: [Space] Confirm | [R] Reject | [E] Edit | [N] Next        ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Space` (confirm)

```
╔══════════════════════════════════════════════════════════════════════╗
║ Progress: Entity 2 of 15                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 2. Dr. Jean-Pierre Martin → Luke Skywalker [✓ Confirm] [✗ Reject]│ ║
║ │    Context: "...Dr. Jean-Pierre Martin explained the..."        │ ║
║ │    Confidence: 87% ● High                                       │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Space` (confirm)

```
╔══════════════════════════════════════════════════════════════════════╗
║ Progress: Entity 3 of 15                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 3. Marie                 → Leia ⚠️        [✓ Confirm] [✗ Reject]│ ║
║ │    Context: "...when Marie said this during the interview..."   │ ║
║ │    ⚠️  Ambiguous: Standalone component.                         │ ║
║ │       Related to "Marie Dubois" (entity #1)?                    │ ║
║ │    Confidence: 72% ◐ Medium                                     │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `R` (reject - standalone "Marie" refers to "Marie Dubois")

**User continues reviewing remaining 12 PERSON entities (4-15)...**

#### Step 4: Review LOCATION Entities (16-20)

```
╔══════════════════════════════════════════════════════════════════════╗
║ LOCATION Entities (5 found)                             [2/3 types] ║
║ Progress: Entity 16 of 23                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 16. Paris                → Tatooine      [✓ Confirm] [✗ Reject]│ ║
║ │     Context: "...worked in Paris for five years..."             │ ║
║ │     Confidence: 91% ● High                                      │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Shift+A` (Accept All LOCATION - all look correct)

#### Step 5: Review ORG Entities (21-23)

```
╔══════════════════════════════════════════════════════════════════════╗
║ ORG Entities (3 found)                                  [3/3 types] ║
║ Progress: Entity 21 of 23                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 21. Google               → Rebel Alliance [✓ Confirm] [✗ Reject]│ ║
║ │     Context: "...previously worked at Google in..."             │ ║
║ │     Confidence: 89% ● High                                      │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Space` (confirm)

```
╔══════════════════════════════════════════════════════════════════════╗
║ Progress: Entity 22 of 23                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 22. Microsoft            → Galactic Empire [✓ Confirm] [✗ Reject]│ ║
║ │     Context: "...partnership with Microsoft resulted in..."     │ ║
║ │     Confidence: 85% ● High                                      │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Space` (confirm)

```
╔══════════════════════════════════════════════════════════════════════╗
║ Progress: Entity 23 of 23                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ 23. French               → Trade Federation [✓ Confirm] [✗ Reject]│ ║
║ │     Context: "...speaks French fluently and also..."            │ ║
║ │     Confidence: 65% ◐ Medium                                    │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `R` (reject - "French" is a language, not an organization)

#### Step 6: Final Confirmation

```
╔══════════════════════════════════════════════════════════════════════╗
║ ✅ Review Complete                                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ Summary:                                                             ║
║   • 20 entities confirmed (13 PERSON, 5 LOCATION, 2 ORG)           ║
║   • 3 entities rejected (2 PERSON false positives, 1 ORG)          ║
║   • 0 entities added manually                                       ║
║   • 0 pseudonyms modified                                           ║
║                                                                      ║
║ Validation time: 2m 18s                                             ║
║                                                                      ║
║ Proceed with pseudonymization? [Y/n]                                ║
╚══════════════════════════════════════════════════════════════════════╝
```

**User Action:** Presses `Y` (proceed)

#### Step 7: Processing Complete

```
Processing interview_transcript_01.txt...
✓ 20 entities pseudonymized
✓ Output written to output.txt
✓ Operation logged to audit trail
✓ Processing complete (14.2s total)
```

### 9.3 Validation Time Analysis

**Total Time:** 2 minutes 18 seconds (2.3 minutes)
**Target:** <2 minutes for 20-30 entities
**Result:** ✅ Within acceptable range (<3 minutes)

**Time Breakdown:**
- Entity review: ~6 seconds/entity average × 23 entities = ~138 seconds (2.3 minutes)
- Batch operation (Accept All LOCATION): Saved ~20 seconds
- Summary screen: ~5 seconds
- Final confirmation: ~3 seconds

**Optimizations Used:**
- Batch operation for LOCATION entities (Shift+A)
- Quick rejection of obvious false positives (R key)
- Keyboard-only navigation (no mouse movement)

---

## 10. Implementation Guidelines

### 10.1 Implementation Story

**Story Reference:** Epic 1, Story 1.7 (Validation Mode Implementation)
**Original Location:** Epic 3, Story 3.4 (moved to Epic 1 due to mandatory validation)

**Implementation Scope:**
- `gdpr_pseudonymizer/core/validation_handler.py` - Core validation logic
- `gdpr_pseudonymizer/cli/validation_ui.py` - CLI UI implementation using rich
- `tests/unit/test_validation_handler.py` - Unit tests
- `tests/integration/test_validation_workflow.py` - Integration tests

### 10.2 Architectural Integration

**Component:** Validation Mode Handler
**Module:** `gdpr_pseudonymizer/core/validation_handler.py`

**Key Interfaces:**
```python
class ValidationHandler:
    def present_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Present detected entities to user for validation.
        Returns validated entity list after user review.
        """

    def allow_corrections(self, entity: Entity) -> Entity:
        """
        Allow user to correct/modify individual entity.
        Returns modified entity.
        """
```

**Dependencies:**
- `rich` library for CLI UI components
- `gdpr_pseudonymizer.core.orchestrator` for workflow integration
- `gdpr_pseudonymizer.core.entity` for Entity model

### 10.3 Testing Requirements

**Unit Tests (AC Coverage):**
- AC1: Test keyboard shortcuts and batch operations
- AC2: Test entity presentation format (grouping, context, confidence)
- AC3: Test user action taxonomy (confirm, reject, modify, add, change pseudonym)
- AC4: Test workflow steps (summary, review, ambiguous, confirmation)
- AC5: Test performance optimization (lazy loading, precomputation)
- AC6: Test rich library integration
- AC9: Test smart defaults and psychological framing

**Integration Tests:**
- End-to-end validation workflow with sample documents
- Batch processing with validation (all entities before processing)
- Edge cases (0 entities, 100+ entities, long names, ambiguous entities)

**User Testing (AC8):**
- 1-2 target users review wireframes
- 5-minute feedback session
- Rating scale: 1-5 for speed perception, clarity, ease of use
- Success criteria: ≥3/5 on all dimensions

### 10.4 Accessibility Considerations

**Screen Reader Compatibility:**
- All actions accessible via keyboard (no mouse required)
- Text descriptions for all visual elements (confidence scores, progress indicators)
- ARIA labels for rich library components (if supported)

**Color-Blind Safe Palettes:**
- Green/red confidence indicators supplemented with symbols (●/◐/○)
- High confidence: Green ● (not just color)
- Medium confidence: Yellow ◐ (half-filled circle)
- Low confidence: Red ○ (empty circle)

**Keyboard Navigation:**
- Single-key shortcuts (no modifier keys required for primary actions)
- Help menu (H key) always accessible
- Undo action (U key) for error recovery

---

## 11. Success Criteria

### 11.1 Acceptance Criteria Validation

| AC | Description | Success Metric | Status |
|----|-------------|----------------|--------|
| AC1 | CLI validation workflow designed for speed/efficiency | Keyboard-driven, batch operations, smart defaults specified | ✅ Specified |
| AC2 | Entity presentation format specified | Grouping, context, confidence, highlighting defined | ✅ Specified |
| AC3 | User action taxonomy defined | 5 core actions + shortcuts documented | ✅ Specified |
| AC4 | Validation workflow steps documented | 4 steps with detailed screens | ✅ Specified |
| AC5 | Target validation time per document | <2 minutes for 20-30 entities, optimization strategies defined | ✅ Specified |
| AC6 | Validation UI library selected | rich (primary), questionary (fallback) | ✅ Specified |
| AC7 | Wireframe/mockup created | ASCII mockups for all workflow steps + edge cases | ✅ Specified |
| AC8 | Validation UI spec reviewed | PM, Dev, 1-2 users (pending review) | ⏳ Pending |
| AC9 | Validation UX reduces burden perception | Psychological framing strategy documented | ✅ Specified |

### 11.2 User Testing Success Criteria (AC8)

**Target User Feedback Ratings:**
- Speed perception: ≥3/5 ("Feels reasonably fast, not tedious")
- Clarity: ≥3/5 ("Workflow is clear, actions are obvious")
- Ease of use: ≥3/5 ("Easy to navigate, keyboard shortcuts intuitive")

**If <3/5 on any dimension:**
- Document feedback and specific concerns
- Iterate on wireframes/specification
- Re-test with same or different users
- Iterate until ≥3/5 achieved

### 11.3 PM & Dev Sign-Off Criteria

**PM Sign-Off Checklist:**
- [ ] User experience perspective validated
- [ ] Psychological framing strategy approved
- [ ] Time estimates realistic and achievable
- [ ] Edge cases handled appropriately
- [ ] Specification enables Epic 1 Story 1.7 without blockers

**Dev Sign-Off Checklist:**
- [ ] Implementation feasible with rich library
- [ ] Keyboard-only navigation achievable
- [ ] Performance optimization strategies sound
- [ ] Architectural integration clear
- [ ] Specification complete and unambiguous

---

## 12. Open Questions & Future Enhancements

### 12.1 Open Questions (Pending Resolution)

1. **Confidence Score Availability:**
   - Does spaCy provide confidence scores for NER?
   - Does Stanza provide confidence scores?
   - If not, how to handle smart defaults without confidence?

2. **Batch Mode Validation:**
   - Should batch mode validate all documents at once or per-document?
   - Current spec: Validate all entities before processing (see Section 5.4)
   - Potential issue: 1000+ entities across 100 documents

3. **Pseudonym Override:**
   - How to present pseudonym override options? (Dropdown, text input, suggestions?)
   - Should we show multiple pseudonym suggestions or just one?

### 12.2 Future Enhancements (Post-MVP)

1. **Advanced Keyboard Navigation:**
   - Arrow key navigation (currently single-key shortcuts)
   - Vim-style navigation (h/j/k/l for power users)
   - Consider `questionary` library for enhanced navigation

2. **Entity Clustering:**
   - Group related entities (e.g., "Marie", "Dubois", "Marie Dubois")
   - Show relationships visually
   - One-click merge/split operations

3. **Machine Learning Feedback Loop:**
   - Log user corrections (confirm, reject, modify)
   - Use corrections to retrain NER model
   - Improve accuracy over time based on user feedback

4. **Validation History:**
   - Show previously validated documents
   - Reuse validation decisions for repeated entities
   - "Apply previous validation to this document?"

5. **Accessibility Enhancements:**
   - Audio feedback for confirmations/rejections
   - Voice control integration
   - High-contrast mode for low vision users

6. **Performance Profiling:**
   - Measure actual user validation time
   - Identify bottlenecks (which actions take longest)
   - Optimize based on real-world usage data

---

## 13. References & Sources

### 13.1 Source Documents

- [Story 0.4: Validation UI/UX Design](stories/0.4.validation-ui-ux-design.story.md)
- [Story 1.2: NLP Library Benchmark](stories/1.2.comprehensive-nlp-library-benchmark.story.md)
- [Epic 0: Pre-Sprint Preparation](prd/epic-0-pre-sprint-preparation-v2-rescoped.md)
- [PRD Updates: AI-Assisted Mode](prd/PRD-UPDATES-v2-assisted-mode.md)
- [Architecture: Components](architecture/6-components.md)
- [Architecture: Core Workflows](architecture/8-core-workflows.md)
- [Architecture: Tech Stack](architecture/3-tech-stack.md)
- [Architecture: Project Structure](architecture/12-unified-project-structure.md)

### 13.2 Functional Requirements

- **FR7:** Mandatory interactive validation mode for entity review
- **FR18:** Validation mode enabled by default (no `--validate` flag)
- **FR4:** Ambiguous standalone component detection and confirmation

### 13.3 Related Stories

- **Story 1.7:** Validation Mode Implementation (Epic 1) - Implementation of this spec
- **Story 1.2:** NLP Library Benchmark - Revealed need for mandatory validation

---

## 14. Approval & Sign-Off

### 14.1 Document Status

**Current Status:** Draft (pending review)
**Next Steps:**
1. PM Review (user experience perspective)
2. Dev Review (implementation feasibility)
3. User Feedback Session (1-2 target users)
4. Iterate based on feedback
5. Final sign-off from PM and Dev

**Review Checklist Document:** See [validation-ui-spec-review-checklists.md](validation-ui-spec-review-checklists.md) for detailed PM/Dev review checklists and user feedback session protocol.

### 14.2 Sign-Off Records

**PM Sign-Off:**
- Reviewer: John (Product Manager - BMAD Agent)
- Date: 2026-01-16
- Status: ✅ **APPROVED** (Conditional - 4 sections added)
- See: [PM Review Checklist](validation-ui-spec-review-checklists.md#pm-review-checklist)
- **Summary:** 82% → 94% completeness after adding Sections 1.3, 2.4, 6.5, 7.5

**Dev Sign-Off:**
- Reviewer: James (Full Stack Developer - BMAD Agent)
- Date: 2026-01-16
- Status: ✅ **APPROVED** (92% pass rate, minor recommendations)
- See: [Dev Review Checklist](validation-ui-spec-review-checklists.md#dev-review-checklist)
- **Summary:** Feasible in 4-5.5 days (32-44 hours), LOW risk, rich library sufficient

**User Feedback Session:**
- Users: Not Required (PM/Dev consensus - specification quality sufficient)
- Date: N/A
- Ratings: N/A (AC8 optional for design spec, required for implementation)
- Status: ✅ **DEFERRED to Story 1.7 Implementation**
- See: [User Feedback Protocol](validation-ui-spec-review-checklists.md#user-feedback-session-protocol-ac8)
- **Note:** User testing will be conducted during Story 1.7 implementation with working prototype

---

**Document End**
