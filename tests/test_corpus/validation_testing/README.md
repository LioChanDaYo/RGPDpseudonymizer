# Validation UI User Testing - Test Corpus

This directory contains sample documents and testing materials for **Story 1.7 Task 18: User Testing**.

## Contents

### Test Documents

Five realistic French documents with varying entity counts for validation UI testing:

| File | Approx. Entities | Description | Use Case |
|------|------------------|-------------|----------|
| `doc1_10entities.txt` | 10 | Interview report | Practice/warmup session |
| `doc2_20entities.txt` | 20 | Meeting minutes | Target timing test (2 min goal) |
| `doc3_30entities.txt` | 30 | Annual evaluation | Target timing test (2 min goal) |
| `doc4_50entities.txt` | 50 | Job application | Large document test |
| `doc5_100entities.txt` | 100 | Annual report | Stress test |

### Testing Guide

- **`USER_TESTING_GUIDE.md`**: Complete protocol for conducting user testing sessions
  - Test setup and prerequisites
  - 4-phase testing protocol (30 minutes total)
  - Timing and feedback collection procedures
  - Success criteria and evaluation metrics
  - Sample recruitment email

## Quick Start

### For Test Administrators

1. **Setup**:
   ```bash
   cd tests/test_corpus/validation_testing
   poetry install
   poetry run python scripts/install_spacy_model.py
   ```

2. **Review Guide**:
   ```bash
   cat USER_TESTING_GUIDE.md
   ```

3. **Recruit Users**: 2-3 target users (HR, legal, research professionals)

4. **Conduct Sessions**: Follow the 4-phase protocol in USER_TESTING_GUIDE.md

### For Test Participants

1. **Practice Session**:
   ```bash
   poetry run gdpr-pseudo process doc1_10entities.txt
   ```
   - Learn the interface
   - Try keyboard shortcuts
   - No timing pressure

2. **Timed Tests**:
   ```bash
   poetry run gdpr-pseudo process doc2_20entities.txt
   poetry run gdpr-pseudo process doc3_30entities.txt
   ```
   - Start timer at summary screen
   - Stop timer at final confirmation
   - Work efficiently but accurately

3. **Keyboard Shortcuts**:
   - `[Space]` - Confirm entity
   - `[R]` - Reject false positive
   - `[E]` - Edit entity text
   - `[N]` or `[→]` - Next entity
   - `[P]` or `[←]` - Previous entity
   - `[H]` - Show help
   - `[Q]` - Quit validation

## Document Characteristics

### doc1_10entities.txt
- **Type**: Interview report
- **Length**: ~150 words
- **Entity Types**: PERSON (Marie Dubois, Jean Martin, Sophie Lefebvre), LOCATION (Paris), ORG (TechStart, DataCorp)
- **Complexity**: Simple, clear entities with good context

### doc2_20entities.txt
- **Type**: Meeting minutes
- **Length**: ~250 words
- **Entity Types**: Mix of PERSON, LOCATION, ORG
- **Complexity**: Medium - some compound names, organization names
- **Special**: Tests entity type grouping (PERSON → ORG → LOCATION)

### doc3_30entities.txt
- **Type**: Annual evaluation
- **Length**: ~400 words
- **Entity Types**: Multiple people, locations (Paris, Lyon, Marseille, Toulouse), organizations
- **Complexity**: Medium-high - multiple similar names, partnerships
- **Special**: Tests sustained attention over longer document

### doc4_50entities.txt
- **Type**: Job application/CV
- **Length**: ~700 words
- **Entity Types**: Dense with names, companies, universities
- **Complexity**: High - many proper nouns, potential ambiguity
- **Special**: Tests user fatigue, batch operations

### doc5_100entities.txt
- **Type**: Annual company report
- **Length**: ~1400 words
- **Entity Types**: Very high density of all types
- **Complexity**: Very high - many similar names (Marie Dubois, Marc Dubois, etc.)
- **Special**: Stress test - triggers 100+ entity warning, tests pagination

## Expected Validation Times

Based on target of ~6 seconds per entity:

| Document | Entities | Target Time | Acceptable Max |
|----------|----------|-------------|----------------|
| doc1 (practice) | 10 | 1 minute | No limit |
| doc2 | 20 | 2 minutes | 2.5 minutes |
| doc3 | 30 | 3 minutes | 3.5 minutes |
| doc4 | 50 | 5 minutes | 6 minutes |
| doc5 | 100 | 10 minutes | 12 minutes |

## Success Metrics

### Primary Metrics (Required for PASS)
- ✅ Average validation time ≤2 minutes for doc2 & doc3
- ✅ Speed rating ≥4/5
- ✅ Clarity rating ≥4/5
- ✅ Ease of use rating ≥4/5
- ✅ Completion rate ≥90%

### Secondary Metrics (Nice to Have)
- Users discover and use batch operations (Shift+A, Shift+R)
- Users use help overlay (H key) when confused
- Low error rate (few accidental key presses)
- High confidence in accuracy (≥7/10)

## Testing Tips

### For Administrators
1. **Don't lead**: Let users discover naturally
2. **Take notes**: Capture verbal feedback immediately
3. **Watch for**:
   - Hesitation points
   - Repeated mistakes
   - Frustration signals
   - Efficiency patterns

### For Participants
1. **Be honest**: Confusion helps us improve
2. **Think aloud**: Verbalize your thought process
3. **Use shortcuts**: They're designed for efficiency
4. **Ask questions**: But try to solve first

## Post-Test Analysis

After collecting results from 2-3 users:

1. **Calculate Averages**:
   - Mean validation time per document
   - Mean time per entity
   - Mean ratings across dimensions

2. **Identify Patterns**:
   - Common confusion points
   - Frequently mentioned issues
   - Consistent suggestions

3. **Prioritize Fixes**:
   - Issues affecting >50% of users = High priority
   - Issues affecting 20-50% = Medium priority
   - Issues affecting <20% = Low priority

4. **Document Results**:
   - Add to Story 1.7 Dev Agent Record
   - Update completion notes with findings
   - Create follow-up issues if needed

## Notes

- All documents contain **fictional data** - no real personal information
- Documents are in **French** to match the target use case
- Entity detection may vary depending on spaCy model performance
- Some false positives are intentional to test rejection workflow

## Questions?

Refer to:
- Full testing protocol: `USER_TESTING_GUIDE.md`
- Story documentation: `docs/stories/1.7.validation-ui-implementation.story.md`
- Validation UI spec: `docs/validation-ui-spec.md`
