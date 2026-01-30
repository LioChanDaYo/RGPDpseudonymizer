# Alpha Testing Protocol

**Version:** v0.1.0-alpha
**Testing Period:** 1 week from onboarding
**Feedback Deadline:** [DATE - to be set when alpha testers are onboarded]

---

## Overview

This protocol guides you through systematic testing of the GDPR Pseudonymizer alpha release. Your feedback will directly inform Epic 3 development priorities.

**Expected Time Commitment:**
- Scenario 1: 15-20 minutes
- Scenario 2: 20-30 minutes
- Scenario 3: 10-15 minutes (optional)
- Feedback survey: 10 minutes
- **Total: 55-75 minutes**

---

## Prerequisites

Before starting testing scenarios:
1. ✅ Installation complete ([ALPHA-INSTALL.md](ALPHA-INSTALL.md))
2. ✅ Quick start guide completed ([ALPHA-QUICKSTART.md](ALPHA-QUICKSTART.md))
3. ✅ Database passphrase configured (minimum 12 characters)

---

## Test Scenario 1: Single Document Pseudonymization

**Goal:** Validate core workflow with medium-sized document

**Use Case:** Academic researcher anonymizing a 5-page interview transcript before sharing with collaborators.

### Setup

1. **Create or use a 5-page French document** with 20-30 entities:
   - **Option A (Use Your Own):** If you have a real use-case document (5 pages, French), use it
   - **Option B (Create Test Document):** Create a document with:
     - 10-15 person names (e.g., Marie Dubois, Jean Martin, Sophie Laurent)
     - 5-10 locations (e.g., Paris, Lyon, Marseille)
     - 5 organizations (e.g., Acme SA, Université de Paris, CNRS)

2. **Save as:** `scenario1_input.txt` (plain text, UTF-8 encoding)

### Test Steps

```bash
# Set passphrase
export GDPR_PSEUDO_PASSPHRASE="AlphaTest123456"

# Process document
poetry run gdpr-pseudo process scenario1_input.txt --db scenario1.db --theme neutral
```

### During Validation

As you validate entities, **note the following** (for feedback survey):
1. **Validation UI usability:** Is it clear what to do? Confusing?
2. **Entity detection accuracy:** How many entities were missed? How many false positives?
3. **Context display:** Is the context helpful for decision-making?
4. **Keyboard shortcuts:** Are `a`, `r`, `?` intuitive?

### After Processing

1. **Review pseudonymized output:**
   ```bash
   cat scenario1_input_pseudonymized.txt
   # Or open in text editor
   ```

2. **Check output quality:**
   - Are all sensitive entities pseudonymized?
   - Are pseudonyms realistic/appropriate?
   - Is the text still readable and coherent?

3. **Verify mapping database created:**
   ```bash
   ls -lh scenario1.db
   # Should show encrypted database file
   ```

### Feedback to Collect

After completing Scenario 1, rate the following (1-5 scale):
- **Installation difficulty:** 1 = very easy, 5 = very hard
- **Validation UI usability:** 1 = very confusing, 5 = very intuitive
- **Output quality/readability:** 1 = poor/unreadable, 5 = excellent/natural
- **Processing speed:** Acceptable or Too slow?

**Qualitative feedback:**
- What entities were missed by detection?
- What false positives occurred (non-entities detected as entities)?
- What was most confusing during validation?

---

## Test Scenario 2: Batch Processing (Consistency Validation)

**Goal:** Verify consistent pseudonym assignment across multiple documents

**Use Case:** Pseudonymize 3-5 related documents (e.g., multiple interview transcripts with overlapping participants).

### Setup

Create **3-5 French documents** with **overlapping entities**:

**Example:**
- `batch_doc1.txt`: "Marie Dubois travaille à Paris pour Acme SA."
- `batch_doc2.txt`: "Jean Martin collabore avec Marie Dubois à Lyon."
- `batch_doc3.txt`: "Marie Dubois et Jean Martin participent au projet à Paris."

**Key requirement:** At least 2-3 entities should appear in **multiple documents** (e.g., "Marie Dubois" in all 3 documents).

### Test Steps

Process each document sequentially using the **same database**:

```bash
# Set passphrase
export GDPR_PSEUDO_PASSPHRASE="AlphaTest123456"

# Process all documents (same database = consistent mappings)
poetry run gdpr-pseudo process batch_doc1.txt --db batch_test.db
poetry run gdpr-pseudo process batch_doc2.txt --db batch_test.db
poetry run gdpr-pseudo process batch_doc3.txt --db batch_test.db
# ... repeat for doc4, doc5 if created
```

### Validation Instructions

**For the first document (batch_doc1.txt):**
- Accept all entities (creates initial mappings)

**For subsequent documents (batch_doc2.txt, batch_doc3.txt, ...):**
- Watch for **reused entities** (e.g., "Marie Dubois" appearing again)
- Verify tool recognizes entity and proposes **same pseudonym** from first document

### After Processing

1. **Verify consistency across documents:**
   ```bash
   # Check all pseudonymized outputs
   cat batch_doc1_pseudonymized.txt
   cat batch_doc2_pseudonymized.txt
   cat batch_doc3_pseudonymized.txt
   ```

2. **Consistency check:**
   - "Marie Dubois" should have **same pseudonym** in all documents
   - "Paris" should have **same pseudonym** in all documents
   - Any shared entity should be consistently pseudonymized

3. **Manual verification (example):**
   ```
   Doc 1: "Marie Dubois" → "Sophie Laurent"
   Doc 2: "Marie Dubois" → "Sophie Laurent" ✅ (consistent)
   Doc 3: "Marie Dubois" → "Sophie Laurent" ✅ (consistent)
   ```

### Feedback to Collect

After completing Scenario 2, answer:
- **Did entity mappings remain consistent across all documents?** (Yes/No)
- **If inconsistent, which entities had different pseudonyms?** (List examples)
- **Was batch processing workflow intuitive?** (1-5 scale)
- **How long did it take to process all documents?** (minutes)
- **Would you use this for multi-document projects?** (Yes/No/Maybe + why)

---

## Test Scenario 3: Reversibility Test (Optional)

**Goal:** Verify encrypted mapping table allows de-pseudonymization

**Use Case:** After analysis, researcher needs to restore original names for final publication.

**Note:** This scenario is **optional** as de-pseudonymization CLI is not yet implemented in alpha. This tests **manual mapping lookup**.

### Setup

Use output from **Scenario 1** or **Scenario 2**.

### Test Steps

1. **Open mapping database** (manual inspection):
   ```bash
   # Database is encrypted, so we'll test passphrase requirement
   # No CLI command for de-pseudonymization in alpha
   ```

2. **Verify passphrase protection:**
   ```bash
   # Try processing new document with WRONG passphrase
   export GDPR_PSEUDO_PASSPHRASE="WrongPassphrase"
   echo "Marie Dubois est à Paris." > reversal_test.txt
   poetry run gdpr-pseudo process reversal_test.txt --db scenario1.db

   # Should fail or prompt for passphrase
   ```

3. **Verify passphrase works:**
   ```bash
   # Use CORRECT passphrase
   export GDPR_PSEUDO_PASSPHRASE="AlphaTest123456"
   poetry run gdpr-pseudo process reversal_test.txt --db scenario1.db

   # Should succeed and reuse existing mappings
   ```

4. **Manual de-pseudonymization:**
   - Open `scenario1_input.txt` (original)
   - Open `scenario1_input_pseudonymized.txt` (pseudonymized)
   - Manually create mapping table by comparing:
     ```
     Marie Dubois → Sophie Laurent
     Paris → Lille
     Acme SA → Tech Corp
     ```

### Feedback to Collect

After completing Scenario 3 (if attempted):
- **Was passphrase protection working correctly?** (Yes/No)
- **Could you manually create a mapping table?** (Yes/No)
- **Would you want automated de-pseudonymization CLI?** (Yes/No)
- **How important is reversibility for your use case?** (1-5 scale, 1 = not important, 5 = critical)

---

## Feedback Survey Questions

After completing test scenarios, please answer these questions:

### Quantitative Questions (1-5 Scale)

1. **Installation difficulty** (1 = very easy, 5 = very hard)
   - Rate installation process from [ALPHA-INSTALL.md](ALPHA-INSTALL.md)

2. **Validation UI usability** (1 = very confusing, 5 = very intuitive)
   - Rate interactive validation workflow experience

3. **Output quality/readability** (1 = poor/unreadable, 5 = excellent/natural)
   - Rate quality of pseudonymized text (still coherent/readable?)

4. **Processing speed** (Acceptable / Too slow)
   - Was processing time acceptable for your use case?

5. **Entity detection accuracy** (1 = missed most, 5 = caught everything)
   - How much did you trust the AI to catch entities?

6. **Documentation quality** (1 = very unclear, 5 = very clear)
   - Rate installation guide and quick start guide

7. **Overall satisfaction** (1 = very dissatisfied, 5 = very satisfied)
   - Overall impression of the tool in its current state

### Qualitative Questions (Open Text)

8. **Top 3 missing features:**
   - What features do you wish existed that don't?
   - Examples: Auto-accept high-confidence entities, PDF support, GUI, de-pseudonymization CLI

9. **Biggest usability issues:**
   - What was most frustrating or confusing during testing?
   - What should be improved first?

10. **Would you use this in production?** (Yes / No / Maybe + Why)
    - If "Yes": What use case?
    - If "No": What's blocking you?
    - If "Maybe": What needs to change?

11. **Entity detection failures:**
    - List examples of entities that were missed (false negatives)
    - List examples of non-entities detected as entities (false positives)

12. **Installation blockers:**
    - Did you encounter any installation issues? (describe)
    - What OS/Python version did you use?

13. **Feature prioritization:**
    - Rank these potential Epic 3 features (1 = highest priority, 5 = lowest priority):
      - [ ] Auto-accept high-confidence entities (skip validation for obvious names)
      - [ ] Batch processing CLI (process entire folder at once)
      - [ ] PDF file support (pseudonymize PDFs directly)
      - [ ] GUI (graphical interface instead of CLI)
      - [ ] De-pseudonymization CLI (automated reversal)

14. **Open feedback:**
    - What worked well?
    - What didn't work well?
    - Any other comments or suggestions?

---

## Submitting Feedback

### Option 1: Google Form (Recommended)

**Link:** [GOOGLE_FORM_LINK - to be created in Task 5]

**Deadline:** [DATE - 1 week after onboarding]

### Option 2: GitHub Issues

Create an issue with label `alpha-feedback`:
- Title: "Alpha Feedback - [Your Name/Identifier]"
- Body: Answer all survey questions above

**Link:** https://github.com/your-org/gdpr-pseudonymizer/issues/new

### Option 3: Email

Send completed survey to: [your-email@example.com]

**Subject:** "Alpha Feedback - v0.1.0"

---

## Success Criteria (Internal - For PM Review)

After collecting all alpha feedback, the release is successful if:
- ✅ 100% of alpha testers successfully installed tool (AC1)
- ✅ 80%+ of testers rate UI usability ≥3/5 (AC2)
- ✅ 80%+ of testers rate output quality ≥3/5 (AC2)
- ✅ At least 10 actionable feedback items collected (AC5)
- ✅ Entity consistency validated in Scenario 2 (AC4)

---

## Feedback Review Session (Internal)

**Scheduled:** 1 week after feedback deadline
**Attendees:** PM, PO, Dev lead, QA lead

**Agenda:**
1. Review quantitative ratings (installation, UI, output quality)
2. Synthesize qualitative feedback (missing features, usability issues)
3. Identify critical bugs/blockers
4. Prioritize Epic 3 features based on user feedback
5. Adjust Epic 3 scope and timeline

**Outcome:** Epic 3 roadmap adjusted based on real user feedback

---

## Thank You!

Your participation in this alpha test is **invaluable**. Your feedback will directly shape the future of the GDPR Pseudonymizer tool.

**Questions during testing?**
- Email: [your-email@example.com]
- GitHub Issues: https://github.com/your-org/gdpr-pseudonymizer/issues
- Expected response time: Within 24 hours

**After testing:**
- You'll receive a summary of findings and how your feedback was used
- Early access to Epic 3 beta (if interested)

---

**Happy testing!** 🎉
