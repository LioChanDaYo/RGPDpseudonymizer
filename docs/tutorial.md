# Usage Tutorial

**GDPR Pseudonymizer** - Step-by-step tutorials for common workflows.

---

## Tutorial 1: Single Document Pseudonymization (5 minutes)

Learn the basics by pseudonymizing a single French document.

### Step 1: Create a Test Document

Create a file with French text containing personal information:

```bash
echo "Marie Dubois travaille a Paris pour Acme SA. Elle collabore avec Jean Martin de Lyon." > interview.txt
```

**Entities in this text:**
- **PERSON:** Marie Dubois, Jean Martin
- **LOCATION:** Paris, Lyon
- **ORGANIZATION:** Acme SA

### Step 2: Set Your Passphrase

The tool encrypts all entity mappings. Set a passphrase (minimum 12 characters):

**Windows (PowerShell):**
```powershell
$env:GDPR_PSEUDO_PASSPHRASE = "MySecurePassphrase123"
```

**macOS/Linux:**
```bash
export GDPR_PSEUDO_PASSPHRASE="MySecurePassphrase123"
```

**Important:** Store this passphrase securely. Without it, you cannot reverse pseudonymization.

### Step 3: Run Pseudonymization

```bash
poetry run gdpr-pseudo process interview.txt
```

You'll enter the **interactive validation workflow** - see [Validation UI Walkthrough](#validation-ui-walkthrough) below.

### Step 4: Review Output

After validation, check the pseudonymized file:

```bash
cat interview_pseudonymized.txt
```

**Example output (with neutral theme):**
```
Sophie Martin travaille a Marseille pour TechnoPlus SARL. Elle collabore avec Pierre Laurent de Bordeaux.
```

### Step 5: View Mapping Database

See the entity mappings stored in the encrypted database:

```bash
poetry run gdpr-pseudo list-mappings
```

---

## Tutorial 2: Batch Processing Multiple Documents

Process multiple documents with consistent pseudonyms across all files.

### Step 1: Create Test Documents

```bash
mkdir documents
echo "Marie Dubois est directrice chez Acme SA." > documents/doc1.txt
echo "Jean Martin collabore avec Marie Dubois a Paris." > documents/doc2.txt
echo "Acme SA organise une reunion a Lyon avec Marie Dubois." > documents/doc3.txt
```

### Step 2: Initialize Database

```bash
poetry run gdpr-pseudo init --db project.db
```

Enter a passphrase when prompted (or use environment variable).

### Step 3: Process All Documents

```bash
poetry run gdpr-pseudo batch documents/ --db project.db -o output/
```

**What happens:**
- Each document enters validation workflow
- Same entities receive **same pseudonyms** across all documents
- Progress bar shows completion status

### Step 4: Verify Consistency

```bash
cat output/doc1_pseudonymized.txt
cat output/doc2_pseudonymized.txt
cat output/doc3_pseudonymized.txt
```

"Marie Dubois" should have the same pseudonym in all three documents.

### Step 5: View Statistics

```bash
poetry run gdpr-pseudo stats --db project.db
```

Shows entity counts, themes used, and processing history.

### Filtering by Entity Type

If you only need to pseudonymize certain entity types, use the `--entity-types` flag:

```bash
# Process only PERSON entities (skip LOCATION and ORG)
poetry run gdpr-pseudo batch documents/ --db project.db --entity-types PERSON

# Process PERSON and LOCATION entities (skip ORG)
poetry run gdpr-pseudo batch documents/ --db project.db --entity-types PERSON,LOCATION
```

This is useful when:
- You only need to anonymize people's names but want to keep real locations
- You want to process entity types in separate passes for review efficiency
- Your documents contain many irrelevant ORG detections you want to skip

The `--entity-types` flag also works with the `process` command for single documents.

---

## Tutorial 3: Using Configuration Files

Create a configuration file to set default options.

### Step 1: Generate Config Template

```bash
poetry run gdpr-pseudo config --init
```

This creates `.gdpr-pseudo.yaml` in the current directory.

### Step 2: Edit Configuration

Open `.gdpr-pseudo.yaml` and customize:

```yaml
database:
  path: project_mappings.db

pseudonymization:
  theme: star_wars    # neutral | star_wars | lotr
  model: spacy

batch:
  workers: 4          # 1-8 (use 1 for interactive validation)
  output_dir: pseudonymized_output

logging:
  level: INFO
```

### Step 3: View Effective Configuration

```bash
poetry run gdpr-pseudo config
```

Shows merged configuration from all sources.

### Step 4: Update Config via CLI

Change settings without editing the file:

```bash
# Change theme
poetry run gdpr-pseudo config set pseudonymization.theme lotr

# Change database path
poetry run gdpr-pseudo config set database.path my_mappings.db

# View updated config
poetry run gdpr-pseudo config
```

### Configuration Priority

Settings are applied in this order (highest to lowest priority):

1. CLI flags (e.g., `--theme star_wars`)
2. Custom config file (`--config /path/to/config.yaml`)
3. Project config (`./.gdpr-pseudo.yaml`)
4. Home config (`~/.gdpr-pseudo.yaml`)
5. Default values

**Example:** CLI flag overrides config file:
```bash
# Uses lotr theme even if config says neutral
poetry run gdpr-pseudo process doc.txt --theme lotr
```

---

## Tutorial 4: Choosing a Pseudonym Theme

Compare the three available themes to pick the best one for your use case.

### Theme Comparison

| Entity Type | Neutral | Star Wars | Lord of the Rings |
|-------------|---------|-----------|-------------------|
| **PERSON** | Sophie Martin | Leia Organa | Arwen Evenstar |
| **LOCATION** | Marseille | Coruscant | Rivendell |
| **ORGANIZATION** | TechnoPlus SARL | Rebel Alliance | House of Elrond |

### Neutral Theme (Default)

Best for: Professional documents, legal compliance, realistic output.

```bash
poetry run gdpr-pseudo process doc.txt --theme neutral
```

**Example transformation:**
```
Input:  Marie Dubois travaille a Paris pour Acme SA.
Output: Sophie Martin travaille a Marseille pour TechnoPlus SARL.
```

**Characteristics:**
- French-sounding names
- Real French cities and regions
- Realistic company names with proper suffixes (SA, SARL, SAS)

### Star Wars Theme

Best for: Easy identification of pseudonymized content, fun testing.

```bash
poetry run gdpr-pseudo process doc.txt --theme star_wars
```

**Example transformation:**
```
Input:  Marie Dubois travaille a Paris pour Acme SA.
Output: Leia Organa travaille a Coruscant pour Rebel Alliance.
```

**Characteristics:**
- Iconic Star Wars character names
- Planets and locations from the Star Wars universe
- Factions and organizations (Rebel Alliance, Galactic Empire, etc.)

### Lord of the Rings Theme

Best for: Literary projects, distinctive pseudonymization, fantasy enthusiasts.

```bash
poetry run gdpr-pseudo process doc.txt --theme lotr
```

**Example transformation:**
```
Input:  Marie Dubois travaille a Paris pour Acme SA.
Output: Arwen Evenstar travaille a Rivendell pour House of Elrond.
```

**Characteristics:**
- Characters from Tolkien's Middle-earth
- Locations: Rivendell, Gondor, The Shire, etc.
- Organizations: Kingdoms, houses, and alliances

### Switching Themes

**Important:** Once you've processed documents with a theme, stick with it for consistency. Changing themes mid-project creates inconsistent pseudonyms.

If you must switch:
```bash
# Create new database for new theme
poetry run gdpr-pseudo init --db star_wars_project.db --force
poetry run gdpr-pseudo batch documents/ --db star_wars_project.db --theme star_wars
```

---

## Validation UI Walkthrough

Every document goes through interactive validation to ensure 100% accuracy.

### The Validation Screen

When you process a document, you'll see:

```
================================================================================
Entity Validation Session
================================================================================
Total entities detected: 5
Unique entities to validate: 3 (2 duplicates grouped)

Processing entity 1 of 3
--------------------------------------------------------------------------------
Entity: Marie Dubois
Type: PERSON (detected by spaCy NER)
Confidence: High (92%)

Context:
  "...travaille avec Marie Dubois depuis trois ans. Elle dirige..."
                      ^^^^^^^^^^^^

Proposed pseudonym: [Sophie Martin] (theme: neutral)
--------------------------------------------------------------------------------
[Space] Accept  [R] Reject  [E] Edit  [C] Change pseudonym  [H] Help
```

### Keyboard Shortcuts

**Core Actions:**
| Key | Action | Description |
|-----|--------|-------------|
| `Space` | Accept | Confirm entity and pseudonym |
| `R` | Reject | Mark as false positive (keep original) |
| `E` | Edit | Modify entity text |
| `A` | Add | Add a missed entity manually |
| `C` | Change | Choose different pseudonym |

**Navigation:**
| Key | Action | Description |
|-----|--------|-------------|
| `N` / `Right Arrow` | Next | Go to next entity |
| `P` / `Left Arrow` | Previous | Go to previous entity |
| `X` | Cycle contexts | Show other occurrences of entity (dot indicator shows position: `● ○ ○`) |
| `Q` | Quit | Exit validation (with confirmation) |

**Batch Operations (hidden - press H to see):**
| Key | Action | Description |
|-----|--------|-------------|
| `Shift+A` | Accept All Type | Accept all entities of current type (shows count: `✓ Accepted all 15 PERSON entities`) |
| `Shift+R` | Reject All Type | Reject all entities of current type (shows count: `✗ Rejected all 8 LOCATION entities`) |

**Help:**
| Key | Action |
|-----|--------|
| `H` / `?` | Show help overlay (displays all shortcuts including batch operations) |

### Entity Variant Grouping

The validation UI automatically groups related entity forms into single validation items. For example, if a document contains "Marie Dubois", "Pr. Dubois", and "Dubois", these are shown as one item:

```
Entity: Marie Dubois
Type: PERSON
Also appears as: Pr. Dubois, Dubois
```

Accepting or rejecting this item applies the decision to all variant forms. This reduces validation fatigue when documents use multiple forms to refer to the same person (titles, surnames, abbreviations).

### Validation Workflow

1. **Summary Screen:** See entity counts by type (PERSON, LOCATION, ORG)
2. **Review Entities:** Go through each entity with context (variants grouped)
3. **Make Decisions:** Accept, reject, edit, or change pseudonym
4. **Final Confirmation:** Review summary of changes
5. **Process Document:** Pseudonymization applied

### Tips for Efficient Validation

1. **Press H for all shortcuts:** Many shortcuts (like Shift+A/Shift+R) aren't shown on the main screen
2. **Use batch operations:** Press `Shift+A` to accept all PERSON entities if they look correct
3. **Cycle contexts:** Press `X` to see all occurrences of an entity before deciding — a dot indicator (`● ○ ○ ○`) shows your position; for >10 contexts, a truncated format (`○ ○ … ● … ○ ○`) is used
4. **Trust high-confidence:** Entities with >90% confidence are usually correct
5. **Review low-confidence:** Yellow/red confidence scores need careful review

---

## Common Workflows

### Academic Research: Interview Transcripts

```bash
# Set up project
export GDPR_PSEUDO_PASSPHRASE="AcademicResearch2026!"
poetry run gdpr-pseudo init --db research_project.db

# Process all interviews
poetry run gdpr-pseudo batch interviews/ --db research_project.db -o anonymized/

# Export audit log for ethics board
poetry run gdpr-pseudo export audit_log.json --db research_project.db

# Share anonymized files (keep mappings.db secure!)
```

### HR Analysis: Employee Feedback

```bash
# Pseudonymize for ChatGPT analysis
poetry run gdpr-pseudo process feedback_report.txt --theme star_wars

# Upload pseudonymized version to ChatGPT
# Analyze output (references "Luke Skywalker" instead of real names)
# Map insights back using list-mappings
poetry run gdpr-pseudo list-mappings --search "Luke"
```

### Legal: Case Document Preparation

```bash
# Initialize with strong passphrase
poetry run gdpr-pseudo init --db case_12345.db

# Process case documents
poetry run gdpr-pseudo batch case_documents/ --db case_12345.db --theme neutral

# Export mappings for reference
poetry run gdpr-pseudo list-mappings --db case_12345.db --export mappings.csv
```

---

## Tutorial 5: Managing Mappings

Review and manage your entity-to-pseudonym mappings.

### Validate Existing Mappings

Review stored mappings without processing documents:

```bash
# View all mappings with metadata
poetry run gdpr-pseudo validate-mappings

# Interactive review mode
poetry run gdpr-pseudo validate-mappings --interactive

# Filter by entity type
poetry run gdpr-pseudo validate-mappings --type PERSON
```

### Import Mappings from Another Project

Combine mappings from multiple databases:

```bash
# Import from old project to new
poetry run gdpr-pseudo import-mappings old_project.db --db new_project.db

# Prompt for each duplicate (instead of auto-skipping)
poetry run gdpr-pseudo import-mappings old_project.db --prompt-duplicates
```

### Securely Destroy a Database

When a project is complete and mappings are no longer needed:

```bash
# Interactive destruction (safest - prompts for confirmation and passphrase)
poetry run gdpr-pseudo destroy-table --db project.db

# Force destruction (skips confirmation, still verifies passphrase)
poetry run gdpr-pseudo destroy-table --db project.db --force
```

**Security features:**
- Passphrase verification prevents accidental deletion of wrong database
- SQLite magic number check prevents deletion of non-database files
- Symlink protection prevents redirect attacks
- 3-pass secure wipe overwrites data before file deletion

---

## Tips and Best Practices

### Security

1. **Use environment variables for passphrases** rather than `--passphrase` flag (which appears in shell history)
2. **Store mapping databases separately** from pseudonymized documents — the combination allows re-identification
3. **Use strong passphrases** (12+ characters, mix of letters, numbers, symbols)
4. **Back up your mapping database** before batch operations — you cannot reverse pseudonymization without it

### Workflow Efficiency

1. **Press H during validation** to see all keyboard shortcuts (batch operations are hidden by default)
2. **Use batch accept/reject** (`Shift+A` / `Shift+R`) for entity types where detection is reliable
3. **Process a small test file first** to verify settings before running batch jobs
4. **Use the same database** for all related documents to ensure consistent pseudonyms
5. **Choose your theme upfront** — switching themes mid-project creates inconsistent pseudonyms

### Organization

1. **One database per project** — keep separate mapping databases for unrelated projects
2. **Use `--output` or `-o`** to keep pseudonymized files in a separate directory
3. **Export audit logs regularly** for compliance documentation: `poetry run gdpr-pseudo export audit.json`
4. **Use `stats` command** to monitor processing history and entity counts

### Known Limitations

- **French only** — no other languages in v1.0
- **Text-based formats** — `.txt`, `.md`, `.pdf`, and `.docx` (PDF/DOCX require optional extras: `pip install gdpr-pseudonymizer[formats]`)
- **Validation is mandatory** — every entity must be reviewed (AI detection ~60% F1)
- **Passphrase is irrecoverable** — if lost, existing mappings cannot be decrypted

---

## Troubleshooting

### No entities detected

**Cause:** Document may not contain recognizable French text.

**Solutions:**
1. Ensure text is in French with proper encoding (UTF-8)
2. Check for French names, locations, or organizations
3. Verify file is `.txt` or `.md` format

### Inconsistent pseudonyms across documents

**Cause:** Using different database files.

**Solution:** Always specify the same database:
```bash
poetry run gdpr-pseudo process doc1.txt --db shared.db
poetry run gdpr-pseudo process doc2.txt --db shared.db
```

### Validation UI not responding

**Cause:** Terminal compatibility issue.

**Solutions:**
1. Use a standard terminal (PowerShell, Terminal.app, bash)
2. Avoid running in IDE terminals (may have input issues)
3. Try `poetry shell` then run command directly

### Forgot passphrase

**Consequence:** Cannot access existing mappings or reverse pseudonymization.

**Solution:** Create new database (previous mappings are lost):
```bash
poetry run gdpr-pseudo init --force
```

---

## Next Steps

- [CLI Reference](CLI-REFERENCE.md) - Complete command documentation
- [Installation Guide](installation.md) - Detailed setup instructions
- [FAQ](faq.md) - Common questions and answers
- [Troubleshooting Guide](troubleshooting.md) - Comprehensive error reference
