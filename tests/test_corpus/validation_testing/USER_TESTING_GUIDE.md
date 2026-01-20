# User Testing Guide - Validation UI (Task 18)

## Overview

This guide supports Task 18 of Story 1.7: User Testing of the validation UI. The goal is to validate that the validation workflow is intuitive, efficient, and meets the <2 minute target for 20-30 entity documents.

## Test Objective

**Target Metrics:**
- **Speed**: <2 minutes validation time for 20-30 entity documents
- **Satisfaction**: ≥4/5 rating on Speed, Clarity, and Ease of Use
- **Completion Rate**: ≥90% (users complete validation without giving up)

## Test Setup

### Prerequisites

1. Install GDPR Pseudonymizer (ensure Story 1.7 implementation is installed)
2. Install spaCy French model: `poetry run python scripts/install_spacy_model.py`
3. Navigate to test corpus: `cd tests/test_corpus/validation_testing`

### Test Documents

Five sample documents with varying entity counts:

| Document | Entities | Use Case |
|----------|----------|----------|
| `doc1_10entities.txt` | ~10 | Practice/Warmup |
| `doc2_20entities.txt` | ~20 | Target validation time test |
| `doc3_30entities.txt` | ~30 | Target validation time test |
| `doc4_50entities.txt` | ~50 | Large document test |
| `doc5_100entities.txt` | ~100 | Stress test |

## Testing Protocol

### Phase 1: Introduction (5 minutes)

**Explain to the user:**

1. **Purpose**: "We're testing a new validation UI for reviewing AI-detected personal data before pseudonymization."

2. **Workflow Overview**:
   - Summary screen shows detected entities
   - Review each entity with context
   - Confirm (Space), Reject (R), or Modify (E) entities
   - Final confirmation before processing

3. **Keyboard Shortcuts** (show help screen):
   ```
   [Space]  Confirm entity
   [R]      Reject false positive
   [E]      Edit entity text
   [N/→]    Next entity
   [P/←]    Previous entity
   [H]      Help
   [Q]      Quit
   ```

### Phase 2: Practice (5 minutes)

**Practice Document**: `doc1_10entities.txt` (10 entities)

1. Run command:
   ```bash
   poetry run gdpr-pseudo process doc1_10entities.txt
   ```

2. Let user familiarize themselves with:
   - Summary screen
   - Entity review interface
   - Keyboard shortcuts
   - Final confirmation

3. **Note**: Don't time this session - it's for learning

### Phase 3: Timed Testing (15 minutes)

**Test Documents**: `doc2_20entities.txt` and `doc3_30entities.txt`

For each document:

1. **Before starting**:
   - User should be ready with stopwatch
   - Remind: "Validate as you normally would - accuracy over speed, but work efficiently"

2. **Run command**:
   ```bash
   poetry run gdpr-pseudo process doc2_20entities.txt
   ```

3. **Time tracking**:
   - Start timer when summary screen appears
   - Stop timer when final confirmation is accepted
   - Record time in minutes:seconds

4. **Observe** (don't interrupt):
   - Note any confusion or hesitation
   - Watch for keyboard shortcut usage
   - Identify any error recovery attempts

### Phase 4: Feedback Collection (5 minutes)

**Ratings (1-5 scale):**

1. **Speed Rating**: "How fast did the validation feel?"
   - 1 = Very slow, frustrating
   - 3 = Acceptable pace
   - 5 = Very fast, efficient

2. **Clarity Rating**: "How clear were the instructions and entity displays?"
   - 1 = Very confusing
   - 3 = Mostly clear
   - 5 = Crystal clear

3. **Ease of Use Rating**: "How easy was it to use the keyboard shortcuts?"
   - 1 = Very difficult
   - 3 = Manageable
   - 5 = Very easy

**Open-ended Questions:**

1. "What was confusing or unclear?"
2. "What felt slow or inefficient?"
3. "What was particularly helpful?"
4. "Would you change anything about the workflow?"
5. "On a scale of 1-10, how confident are you that you validated accurately?"

### Optional: Large Document Test

If time permits, test with `doc4_50entities.txt`:
- Does user feel overwhelmed?
- Do they use batch operations (Shift+A, Shift+R)?
- How long does it take?

## Recording Results

### Timing Data Template

```
User: [Initials]
Date: [YYYY-MM-DD]

Practice Session (doc1_10entities.txt):
- Completed: Yes/No
- Issues: [Note any problems]

Test Session 1 (doc2_20entities.txt):
- Time: [MM:SS]
- Entities validated: [#]
- User actions: [e.g., "3 confirmed, 1 rejected, 1 modified"]
- Notes: [Observations]

Test Session 2 (doc3_30entities.txt):
- Time: [MM:SS]
- Entities validated: [#]
- User actions: [e.g., "5 confirmed, 2 rejected"]
- Notes: [Observations]

Ratings:
- Speed: [1-5]
- Clarity: [1-5]
- Ease of Use: [1-5]
- Confidence in Accuracy: [1-10]

Qualitative Feedback:
- Confusing: [User comments]
- Slow/Inefficient: [User comments]
- Helpful: [User comments]
- Suggestions: [User comments]
```

## Success Criteria

**PASS if:**
- Average validation time ≤2 minutes for 20-30 entity documents
- Average ratings ≥4/5 on all three dimensions
- Completion rate ≥90% (users don't give up)

**INVESTIGATE if:**
- Average time >2 minutes → Look for UX friction points
- Any rating <4/5 → Identify specific issues
- Users struggle with keyboard shortcuts → Consider visual hints

## Common Issues to Watch For

1. **Keyboard Confusion**:
   - User forgets shortcuts (presses wrong keys)
   - User tries to use mouse instead
   - **Fix**: More prominent help hints

2. **Context Overload**:
   - User takes too long to read context
   - User doesn't understand what to do with ambiguous entities
   - **Fix**: Shorten context, clearer ambiguity warnings

3. **Navigation Issues**:
   - User doesn't know how to go back
   - User gets lost in entity list
   - **Fix**: Better progress indicators

4. **Uncertainty**:
   - User unsure if entity is correct
   - User doesn't trust AI suggestions
   - **Fix**: More confidence indicators

## Post-Testing

### Aggregate Results

Calculate:
- Average validation time per document
- Average time per entity (total time / # entities)
- Average ratings across all dimensions
- Common feedback themes

### Prioritize Improvements

**Priority 1** (affects >50% of users):
- Blockers or major confusion

**Priority 2** (affects 20-50% of users):
- Moderate friction points

**Priority 3** (affects <20% of users):
- Minor nice-to-haves

### Document in Story

Add results to Story 1.7 Completion Notes:
- Timing data
- Rating averages
- Key feedback themes
- Recommended improvements

## Tips for Test Administrator

1. **Don't lead**: Let users discover the interface naturally
2. **Take notes**: Write down verbal comments as they happen
3. **Watch the screen**: Note where users hesitate or get stuck
4. **Be encouraging**: Reassure users that confusion helps identify issues
5. **Don't interrupt**: Let them work through problems unless completely stuck

## Sample User Recruitment Email

```
Subject: User Testing - GDPR Data Validation Tool (30 min, $50 compensation)

Hi [Name],

We're looking for users to test a new validation interface for our GDPR
pseudonymization tool. The test involves:

- 30-minute session (can be remote or in-person)
- Testing a document validation workflow
- Providing feedback on usability
- $50 Amazon gift card compensation

We're looking for people who:
- Work with sensitive documents (HR, legal, research)
- Are comfortable with basic keyboard shortcuts
- Can provide honest feedback

Interested? Reply to schedule a session.

Thanks,
[Your name]
```

## Questions?

If you have questions about this testing protocol, refer to:
- Story 1.7 documentation: `docs/stories/1.7.validation-ui-implementation.story.md`
- Validation UI spec: `docs/validation-ui-spec.md`
- Help overlay in the application (press H during validation)
