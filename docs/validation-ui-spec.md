# Validation UI/UX Specification

**Document Version:** 1.0
**Created:** 2026-01-16
**Status:** Draft
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

### 1.3 Critical Context

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

### 14.2 Sign-Off Records

**PM Sign-Off:**
- Reviewer: _____________________
- Date: _____________________
- Status: ⏳ Pending
- Comments: _____________________

**Dev Sign-Off:**
- Reviewer: _____________________
- Date: _____________________
- Status: ⏳ Pending
- Comments: _____________________

**User Feedback Session:**
- Users: _____________________
- Date: _____________________
- Ratings: Speed ___/5 | Clarity ___/5 | Ease ___/5
- Status: ⏳ Pending
- Comments: _____________________

---

**Document End**
