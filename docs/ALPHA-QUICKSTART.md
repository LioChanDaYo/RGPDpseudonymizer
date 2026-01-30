# Alpha Quick Start Guide

**Version:** v0.1.0-alpha
**Estimated Time:** 10 minutes for first pseudonymization

---

## Your First Pseudonymization (5 Minutes)

Let's pseudonymize a simple French document to verify everything works.

### Step 1: Create a Test Document

Create a file named `test.txt` with French text containing personal information:

```bash
echo "Marie Dubois travaille à Paris pour Acme SA. Elle collabore avec Jean Martin de Lyon." > test.txt
```

**What's in this test:**
- 2 person names: Marie Dubois, Jean Martin
- 2 locations: Paris, Lyon
- 1 organization: Acme SA

### Step 2: Set Database Passphrase

The tool encrypts all entity mappings. Set a passphrase (minimum 12 characters):

**Windows (PowerShell):**
```powershell
$env:GDPR_PSEUDO_PASSPHRASE = "MySecurePassphrase123"
```

**macOS/Linux:**
```bash
export GDPR_PSEUDO_PASSPHRASE="MySecurePassphrase123"
```

**Security Note:** Use a strong passphrase. If lost, you cannot reverse pseudonymization.

### Step 3: Run Pseudonymization

```bash
poetry run gdpr-pseudo process test.txt
```

**What happens next:** You'll enter the interactive validation workflow (see next section).

### Step 4: Interactive Validation Workflow

The tool detects entities and asks you to confirm each one. Here's what you'll see:

```
================================================================================
Entity Validation Session
================================================================================
Total entities detected: 5
Unique entities to validate: 5

Processing entity 1 of 5
────────────────────────────────────────────────────────────────────────────────
Entity: Marie Dubois
Type: PERSON (detected by spaCy NER)
Confidence: High

Context:
  "Marie Dubois travaille à Paris pour Acme SA."
   ^^^^^^^^^^^^^

Proposed pseudonym: [Leia Organa] (theme: neutral)

────────────────────────────────────────────────────────────────────────────────
[a] Accept   [r] Reject   [?] More info

Your choice:
```

**Validation Guide:**
- Press **`a`** to accept entity (will be pseudonymized)
- Press **`r`** to reject entity (will be kept as-is, not pseudonymized)
- Press **`?`** for more information about the entity

**Example validation session:**
1. Marie Dubois → Press **`a`** (accept)
2. Paris → Press **`a`** (accept)
3. Acme SA → Press **`a`** (accept)
4. Jean Martin → Press **`a`** (accept)
5. Lyon → Press **`a`** (accept)

### Step 5: Review Output

After validation, check the pseudonymized output:

```bash
cat test_pseudonymized.txt
```

**Expected output:**
```
Leia Organa travaille à Coruscant pour Rebel Alliance. Elle collabore avec Luke Skywalker de Tatooine.
```

**Original vs Pseudonymized:**
- Marie Dubois → Leia Organa
- Paris → Coruscant
- Acme SA → Rebel Alliance
- Jean Martin → Luke Skywalker
- Lyon → Tatooine

### Step 6: Check Encrypted Mapping Table

The tool stores entity mappings in an encrypted database:

```bash
# Database file created (default location)
ls mappings.db
```

**What's stored:**
- Original entity → Pseudonym mappings (encrypted)
- Ensures consistent pseudonyms across multiple documents
- Allows de-pseudonymization (reversibility)

---

## Batch Processing (Processing Multiple Documents)

To pseudonymize multiple documents with consistent entity mappings:

### Example: 3 Documents with Overlapping Entities

**Create test documents:**
```bash
echo "Marie Dubois travaille à Paris." > doc1.txt
echo "Jean Martin collabore avec Marie Dubois." > doc2.txt
echo "Marie Dubois et Jean Martin sont à Lyon." > doc3.txt
```

**Process sequentially (reuses same database):**
```bash
poetry run gdpr-pseudo process doc1.txt
poetry run gdpr-pseudo process doc2.txt
poetry run gdpr-pseudo process doc3.txt
```

**Result:** "Marie Dubois" receives the **same pseudonym** across all three documents (idempotency).

**Verification:**
```bash
# Check all outputs
cat doc1_pseudonymized.txt
cat doc2_pseudonymized.txt
cat doc3_pseudonymized.txt

# All should show "Marie Dubois" mapped to same pseudonym (e.g., "Leia Organa")
```

---

## Validation UI Walkthrough

### Understanding Entity Detection

The tool uses **hybrid detection**:
1. **spaCy NER (NLP):** Detects named entities using French language model
2. **Regex patterns:** Catches entities missed by NLP (French titles, compound names)

**Detection accuracy (v0.1.0-alpha):**
- Recall: ~40-50% (catches about half of entities automatically)
- **Why validation is mandatory:** AI detection misses entities, so human review ensures 100% accuracy

### Validation UI Components

**Entity Card:**
```
Entity: Marie Dubois
Type: PERSON (detected by spaCy NER)
Confidence: High
```

**Context Display:**
```
Context:
  "Marie Dubois travaille à Paris pour Acme SA."
   ^^^^^^^^^^^^^
```
- Shows sentence containing entity
- Highlights entity with `^` markers

**Proposed Pseudonym:**
```
Proposed pseudonym: [Leia Organa] (theme: neutral)
```
- Shows replacement name from pseudonym library
- Theme can be changed with `--theme` option (neutral/star_wars/lotr)

**Keyboard Shortcuts:**
- **`a`**: Accept entity (pseudonymize it)
- **`r`**: Reject entity (keep original, don't pseudonymize)
- **`?`**: Show more information about entity type

**Batch Operations (Coming in Epic 3):**
- Accept All / Reject All Type (not available in alpha)
- Currently: Must validate each entity individually

---

## Known Limitations (v0.1.0-alpha)

### Language Support
- **French only** - No other languages supported in alpha
- French text must use proper accents (é, è, à, etc.)

### File Formats
- **Text files only:** `.txt` and `.md` (Markdown)
- **No support for:**
  - PDF files
  - Word documents (.docx)
  - Excel spreadsheets
  - HTML files
- **Workaround:** Convert files to plain text before processing

### Validation Mode
- **Validation mandatory** - No automatic mode available
- Every entity must be manually accepted/rejected
- **Why:** AI detection accuracy is 40-50%, human validation ensures 100%
- **Epic 3 feature:** Auto-accept high-confidence entities (coming soon)

### Pseudonym Support
- **PERSON, LOCATION, and ORGANIZATION entities supported** - All three entity types have themed pseudonyms
  - PERSON: First name + last name from themed libraries
  - LOCATION: Cities, regions, and planets/countries from themed libraries
  - ORGANIZATION: Companies, agencies, and institutions from themed libraries
- Themed pseudonyms available for all 3 themes (neutral, Star Wars, LOTR)
- **Alpha feedback requested:** Survey question #14 asks about your specific use cases to inform implementation details

### Detection Accuracy
- **AI detection:** 40-50% recall (misses about half of entities)
- **Common misses:**
  - Uncommon French names
  - Organization names without common suffixes (SA, SARL, etc.)
  - Locations not in spaCy's training data
- **Mitigation:** Validation workflow ensures nothing is missed

### Performance
- **Single document:** ~5-30 seconds (depending on size)
- **Batch processing:** Process-based parallelism (tested in Story 2.7)
- **Large documents (100+ pages):** May take several minutes for validation

### Platform Quirks
- **Windows:** CLI shows as `gdpr-pseudo.cmd` (normal behavior)
- **Windows:** Possible spaCy access violations (rare, use WSL if encountered)
- **All platforms:** Must use `poetry run` prefix for all commands

### Reversibility
- **Mapping table location:** Must remember where database file is stored
- **Passphrase:** If forgotten, de-pseudonymization is impossible
- **No GUI:** Command-line only (GUI planned for Epic 4)

---

## Pseudonym Library Themes

Change the theme to use different pseudonym sets:

### Neutral Theme (Default)
```bash
poetry run gdpr-pseudo process input.txt --theme neutral
```
- Uses realistic-sounding names
- Example: Marie Dubois → Sophie Laurent

### Star Wars Theme
```bash
poetry run gdpr-pseudo process input.txt --theme star_wars
```
- Uses Star Wars universe names
- Example: Marie Dubois → Leia Organa, Paris → Coruscant

### Lord of the Rings Theme
```bash
poetry run gdpr-pseudo process input.txt --theme lotr
```
- Uses LOTR universe names
- Example: Marie Dubois → Arwen Evenstar, Paris → Rivendell

**Recommendation for Testing:**
- Use `neutral` theme for realistic pseudonymization
- Use `star_wars` or `lotr` for fun/distinguishable testing

---

## Common Workflows

### Workflow 1: Pseudonymize Academic Research Data

**Use case:** Anonymize interview transcripts before sharing with collaborators.

```bash
# Set passphrase (keep secure!)
export GDPR_PSEUDO_PASSPHRASE="AcademicResearch2026"

# Process all transcripts
poetry run gdpr-pseudo process interview_1.txt
poetry run gdpr-pseudo process interview_2.txt
poetry run gdpr-pseudo process interview_3.txt

# Result: Consistent pseudonyms across all interviews
# Share: *_pseudonymized.txt files
# Keep secure: mappings.db (for de-pseudonymization)
```

### Workflow 2: Pseudonymize for ChatGPT Analysis

**Use case:** Analyze sensitive documents with ChatGPT without exposing real names.

```bash
# Pseudonymize document
export GDPR_PSEUDO_PASSPHRASE="ChatGPTAnalysis123"
poetry run gdpr-pseudo process company_report.txt --theme star_wars

# Upload pseudonymized version to ChatGPT
# Analyze output using pseudonyms
# De-pseudonymize ChatGPT's response (manual mapping lookup)
```

**Security Note:** Never upload original mapping database to cloud services.

---

## Troubleshooting

### Problem: "Passphrase too short" error

**Error message:**
```
Error: Passphrase must be at least 12 characters
```

**Solution:** Use a passphrase with 12+ characters:
```bash
# TOO SHORT (11 characters)
export GDPR_PSEUDO_PASSPHRASE="short"

# CORRECT (12+ characters)
export GDPR_PSEUDO_PASSPHRASE="MySecurePass123"
```

### Problem: Entities not detected correctly

**Example:** "Marie Dubois" detected as two separate entities.

**Workaround (alpha version):**
1. Reject incorrect detections during validation
2. Report issue via feedback survey (helps improve AI model)

**Coming in Epic 3:** Improved compound name detection

### Problem: Validation UI not showing entities

**Possible cause:** No entities detected in document.

**Solution:**
1. Verify document contains French text with names/locations/organizations
2. Check file encoding (should be UTF-8)
3. Try with test document from Step 1 of this guide

### Problem: Different pseudonym for same entity across documents

**Possible cause:** Using different database files.

**Solution:** Ensure all documents use the same database:
```bash
# CORRECT (all use same DB)
poetry run gdpr-pseudo process doc1.txt --db shared.db
poetry run gdpr-pseudo process doc2.txt --db shared.db

# INCORRECT (different DBs = different pseudonyms)
poetry run gdpr-pseudo process doc1.txt --db db1.db
poetry run gdpr-pseudo process doc2.txt --db db2.db
```

---

## Next Steps

1. **Complete test scenarios:** See [ALPHA-TESTING-PROTOCOL.md](ALPHA-TESTING-PROTOCOL.md)
2. **Try with your own documents:** Process real use-case documents (2-5 pages recommended)
3. **Provide feedback:** Complete feedback survey (link in onboarding email)

---

## Feedback & Support

**Found a bug?**
- Report via GitHub Issues: https://github.com/your-org/gdpr-pseudonymizer/issues
- Include: Input file (if shareable), error message, steps to reproduce

**Have a feature request?**
- Include in feedback survey (link in onboarding email)
- Email: [your-email@example.com]

**Questions about usage?**
- Email: [your-email@example.com]
- Expected response time: Within 24 hours

---

**Thank you for alpha testing!** Your feedback is invaluable for improving the tool before the official release.
