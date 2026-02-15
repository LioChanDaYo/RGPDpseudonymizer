# CLI Reference

This document provides complete reference documentation for the `gdpr-pseudo` command-line interface.

## Table of Contents

- [Global Options](#global-options)
- [Commands](#commands)
  - [init](#init)
  - [process](#process)
  - [batch](#batch)
  - [config](#config)
  - [list-mappings](#list-mappings)
  - [validate-mappings](#validate-mappings)
  - [stats](#stats)
  - [import-mappings](#import-mappings)
  - [export](#export)
  - [delete-mapping](#delete-mapping)
  - [list-entities](#list-entities)
  - [destroy-table](#destroy-table)
- [GDPR Compliance](#gdpr-compliance)
- [Configuration File](#configuration-file)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

---

## Global Options

These options are available for all commands:

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | | Show version and exit |
| `--config PATH` | `-c` | Path to config file (default: `~/.gdpr-pseudo.yaml` or `./.gdpr-pseudo.yaml`) |
| `--verbose` | `-v` | Enable verbose logging (DEBUG level) |
| `--quiet` | `-q` | Suppress non-error output |
| `--help` | | Show help message and exit |

**Example:**
```bash
gdpr-pseudo --version
gdpr-pseudo --config ./custom-config.yaml process input.txt
```

---

## Commands

### init

Initialize a new encrypted mapping database.

**Usage:**
```bash
gdpr-pseudo init [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase (min 12 characters) |
| `--force` | `-f` | | Overwrite existing database if it exists |

**Examples:**
```bash
# Initialize with interactive passphrase prompt
gdpr-pseudo init

# Initialize with custom database path
gdpr-pseudo init --db project_mappings.db

# Initialize with passphrase from environment
export GDPR_PSEUDO_PASSPHRASE="your_secure_passphrase"
gdpr-pseudo init

# Force overwrite existing database
gdpr-pseudo init --force
```

**Passphrase Requirements:**
- Minimum 12 characters
- Stored only in memory (never on disk)
- Use environment variable `GDPR_PSEUDO_PASSPHRASE` for automation

---

### process

Process a single document with pseudonymization.

**Usage:**
```bash
gdpr-pseudo process INPUT_FILE [OPTIONS]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_FILE` | Yes | Input file path (.txt, .md, .pdf, or .docx) |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output PATH` | `-o` | `<input>_pseudonymized.ext` | Output file path |
| `--theme TEXT` | `-t` | `neutral` | Pseudonym library theme (neutral/star_wars/lotr) |
| `--model TEXT` | `-m` | `spacy` | NLP model name |
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--entity-types TEXT` | | (all) | Filter entity types to process (comma-separated: PERSON,LOCATION,ORG). Only specified types will be detected and pseudonymized. |

**Examples:**
```bash
# Process with default settings
gdpr-pseudo process input.txt

# Process with custom output
gdpr-pseudo process input.txt -o output.txt

# Process with Star Wars theme
gdpr-pseudo process input.txt --theme star_wars

# Process with custom database
gdpr-pseudo process input.txt --db project.db

# Process only PERSON and LOCATION entities (skip ORG)
gdpr-pseudo process input.txt --entity-types PERSON,LOCATION

# Process a PDF document (requires: pip install gdpr-pseudonymizer[pdf])
gdpr-pseudo process report.pdf

# Process a DOCX document (requires: pip install gdpr-pseudonymizer[docx])
gdpr-pseudo process interview.docx -o interview_pseudonymized.txt
```

**PDF/DOCX Notes:**
- PDF and DOCX support requires optional dependencies. Install with `pip install gdpr-pseudonymizer[formats]`.
- Output is always `.txt` (plaintext) for PDF/DOCX inputs. Format preservation is planned for v1.2+.
- Scanned/image-based PDFs will produce a warning if little text is extracted. OCR is not supported.

---

### batch

Process multiple documents in a directory.

**Usage:**
```bash
gdpr-pseudo batch INPUT_PATH [OPTIONS]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_PATH` | Yes | Input directory or file path |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output PATH` | `-o` | Same as input with `_pseudonymized` suffix | Output directory |
| `--theme TEXT` | `-t` | `neutral` | Pseudonym library theme |
| `--model TEXT` | `-m` | `spacy` | NLP model name |
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--recursive` | `-r` | | Process subdirectories recursively |
| `--continue-on-error` | | Yes | Continue processing on individual file errors |
| `--stop-on-error` | | | Stop on first error |
| `--workers` | `-w` | 1 | Number of parallel workers (1-8). Use 1 for interactive validation, 2-8 for parallel processing without validation |
| `--entity-types TEXT` | | (all) | Filter entity types to process (comma-separated: PERSON,LOCATION,ORG). Only specified types will be detected and pseudonymized. |

**Examples:**
```bash
# Process all files in a directory
gdpr-pseudo batch ./documents/

# Process recursively with custom output
gdpr-pseudo batch ./documents/ -o ./output/ --recursive

# Process with specific theme
gdpr-pseudo batch ./documents/ --theme star_wars

# Stop on first error
gdpr-pseudo batch ./documents/ --stop-on-error

# Parallel processing (no validation, faster for pre-validated entities)
gdpr-pseudo batch ./documents/ --workers 4

# Sequential with validation (default)
gdpr-pseudo batch ./documents/ --workers 1

# Process only PERSON entities across all documents
gdpr-pseudo batch ./documents/ --entity-types PERSON

# Process PERSON and ORG entities in parallel
gdpr-pseudo batch ./documents/ --entity-types PERSON,ORG --workers 4

# Process directory with mixed formats (.txt, .pdf, .docx)
gdpr-pseudo batch ./documents/ --recursive
```

**Supported formats:** `.txt`, `.md`, `.pdf`, `.docx`. PDF/DOCX require optional extras (`pip install gdpr-pseudonymizer[formats]`). Output files from PDF/DOCX inputs use `.txt` extension.

---

### config

View or modify configuration settings.

**Usage:**
```bash
gdpr-pseudo config [OPTIONS] [COMMAND]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--init` | | | Generate a template `.gdpr-pseudo.yaml` in current directory |
| `--force` | `-f` | | Overwrite existing config file when using `--init` |

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| `set KEY VALUE` | Set a configuration value |

**Examples:**
```bash
# View current effective configuration
gdpr-pseudo config

# Generate config template
gdpr-pseudo config --init

# Overwrite existing config
gdpr-pseudo config --init --force

# Set configuration values
gdpr-pseudo config set pseudonymization.theme star_wars
gdpr-pseudo config set database.path my_mappings.db
gdpr-pseudo config set batch.workers 4
gdpr-pseudo config set logging.level DEBUG
```

**Configuration Keys:**

| Key | Type | Description |
|-----|------|-------------|
| `database.path` | string | Database file path |
| `pseudonymization.theme` | string | Pseudonym theme (neutral/star_wars/lotr) |
| `pseudonymization.model` | string | NLP model (spacy) |
| `batch.workers` | integer | Parallel workers (1-8) |
| `batch.output_dir` | string | Default output directory |
| `logging.level` | string | Log level (DEBUG/INFO/WARNING/ERROR) |

---

### list-mappings

View entity-to-pseudonym mappings from the database.

**Usage:**
```bash
gdpr-pseudo list-mappings [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--type TEXT` | `-t` | | Filter by entity type (PERSON/LOCATION/ORG) |
| `--search TEXT` | `-s` | | Search by entity name (case-insensitive) |
| `--export PATH` | `-e` | | Export mappings to CSV file |
| `--limit INT` | `-l` | | Limit number of results |

**Examples:**
```bash
# List all mappings
gdpr-pseudo list-mappings

# Filter by entity type
gdpr-pseudo list-mappings --type PERSON

# Search for specific entity
gdpr-pseudo list-mappings --search "Marie"

# Export to CSV
gdpr-pseudo list-mappings --export mappings.csv

# Combine filters
gdpr-pseudo list-mappings --type PERSON --search "Dubois" --limit 10
```

---

### validate-mappings

Review existing mappings without processing documents.

**Usage:**
```bash
gdpr-pseudo validate-mappings [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--interactive` | `-i` | | Interactive mode to review each mapping |
| `--type TEXT` | `-t` | | Filter by entity type |

**Examples:**
```bash
# View all mappings with metadata
gdpr-pseudo validate-mappings

# Interactive review mode
gdpr-pseudo validate-mappings --interactive

# Filter by entity type
gdpr-pseudo validate-mappings --type PERSON
```

**Note:** This command is read-only and does not modify the database.

---

### stats

Show database statistics and usage information.

**Usage:**
```bash
gdpr-pseudo stats [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |

**Examples:**
```bash
# View statistics
gdpr-pseudo stats

# View statistics for specific database
gdpr-pseudo stats --db project.db
```

**Output includes:**
- Database info (path, size, creation date)
- Entity counts by type (PERSON, LOCATION, ORG)
- Theme distribution
- Processing history (successful/failed operations)
- Most recent operation

---

### import-mappings

Import mappings from another database.

**Usage:**
```bash
gdpr-pseudo import-mappings SOURCE_DB [OPTIONS]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `SOURCE_DB` | Yes | Source database file to import from |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Target database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Target database passphrase |
| `--source-passphrase TEXT` | | (prompt) | Source database passphrase |
| `--skip-duplicates` | | Yes | Skip duplicate entities |
| `--prompt-duplicates` | | | Prompt for each duplicate |

**Examples:**
```bash
# Import from another database
gdpr-pseudo import-mappings old_project.db

# Import to specific database
gdpr-pseudo import-mappings old_project.db --db new_project.db

# Prompt for duplicate handling
gdpr-pseudo import-mappings old.db --prompt-duplicates
```

---

### export

Export audit log to JSON or CSV file.

**Usage:**
```bash
gdpr-pseudo export OUTPUT_PATH [OPTIONS]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `OUTPUT_PATH` | Yes | Output file path (.json or .csv) |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--type TEXT` | `-t` | | Filter by operation type (PROCESS/BATCH/etc.) |
| `--from DATE` | | | Filter operations after this date (YYYY-MM-DD) |
| `--to DATE` | | | Filter operations before this date (YYYY-MM-DD) |
| `--success-only` | | | Export only successful operations |
| `--failures-only` | | | Export only failed operations |
| `--limit INT` | `-l` | | Limit number of results |

**Examples:**
```bash
# Export all operations to JSON
gdpr-pseudo export audit_log.json

# Export to CSV
gdpr-pseudo export audit_log.csv

# Filter by date range
gdpr-pseudo export audit.json --from 2026-01-01 --to 2026-01-31

# Filter by operation type
gdpr-pseudo export audit.json --type PROCESS

# Export only successful operations
gdpr-pseudo export audit.json --success-only
```

---

### delete-mapping

Delete an entity mapping from the database (GDPR Article 17 erasure).

Deleting a mapping converts pseudonymization into **anonymization**: without the mapping, the pseudonym cannot be linked to an identifiable individual, placing the data outside GDPR scope.

**Usage:**
```bash
gdpr-pseudo delete-mapping [ENTITY_NAME] [OPTIONS]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `ENTITY_NAME` | No* | Entity name to delete (*provide either name or `--id`) |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--id TEXT` | | | Entity UUID to delete (alternative to name) |
| `--reason TEXT` | `-r` | | Reason for deletion (GDPR request reference) |
| `--force` | `-f` | | Skip confirmation prompt |

**Examples:**
```bash
# Delete by entity name (interactive confirmation)
gdpr-pseudo delete-mapping "Marie Dupont"

# Delete by entity UUID (from list-entities output)
gdpr-pseudo delete-mapping --id abc12345

# Delete with reason for audit trail
gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

# Delete without confirmation (for automation)
gdpr-pseudo delete-mapping "Marie Dupont" --force

# Specify database
gdpr-pseudo delete-mapping "Marie Dupont" --db project.db
```

**Audit Trail:**
Every deletion creates an `ERASURE` entry in the operations table with:
- Entity name, type, and ID
- Deletion timestamp
- Optional reason text (from `--reason` flag)

---

### list-entities

List entities with search capability, optimized for the GDPR erasure workflow.

**Usage:**
```bash
gdpr-pseudo list-entities [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path |
| `--passphrase TEXT` | `-p` | (prompt) | Database passphrase |
| `--search TEXT` | `-s` | | Search by entity name (case-insensitive substring) |
| `--type TEXT` | `-t` | | Filter by entity type (PERSON/LOCATION/ORG) |
| `--limit INT` | `-l` | | Limit number of results |

**Examples:**
```bash
# List all entities
gdpr-pseudo list-entities

# Search by name
gdpr-pseudo list-entities --search "Dupont"

# Filter by type
gdpr-pseudo list-entities --type PERSON

# Combine filters with limit
gdpr-pseudo list-entities --search "Marie" --type PERSON --limit 10
```

**Output columns:**
- **Entity ID** (truncated UUID) — use with `delete-mapping --id`
- **Entity Name** — original (decrypted) name
- **Type** — PERSON, LOCATION, or ORG
- **Pseudonym** — assigned pseudonym
- **First Seen** — date entity was first detected
- **Doc Count** — N/A (per-entity document tracking planned for v1.2)

**Difference from `list-mappings`:**
- `list-mappings` — mapping review workflow (shows theme, confidence, CSV export)
- `list-entities` — GDPR erasure workflow (shows entity ID for `--id` deletion, first seen date)

---

### destroy-table

Securely delete the mapping database.

**Usage:**
```bash
gdpr-pseudo destroy-table [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--db PATH` | | `mappings.db` | Database file path to destroy |
| `--force` | `-f` | | Skip confirmation prompt |
| `--passphrase TEXT` | `-p` | (prompt) | Passphrase to verify database ownership (recommended) |
| `--skip-passphrase-check` | | | Skip passphrase verification (not recommended) |

**Examples:**
```bash
# Delete with confirmation and passphrase verification (safest)
gdpr-pseudo destroy-table

# Delete specific database with passphrase
gdpr-pseudo destroy-table --db project.db -p "your_passphrase"

# Skip confirmation (requires passphrase by default)
gdpr-pseudo destroy-table --force

# Skip both confirmation and passphrase (dangerous!)
gdpr-pseudo destroy-table --force --skip-passphrase-check
```

**Security Features:**

1. **Passphrase Verification:** By default, you must provide the correct passphrase to prove ownership of the database before deletion.

2. **SQLite Magic Number Check:** The tool verifies the file is a valid SQLite database before attempting deletion (prevents accidental deletion of non-database files).

3. **Symlink Protection:** Symbolic links are rejected to prevent attacks where a symlink could redirect deletion to unintended files.

4. **3-Pass Secure Wipe:** Data is overwritten before file deletion to prevent recovery.

**⚠️ WARNING:** This operation is irreversible! Use `--skip-passphrase-check` only when you're certain and have no other option.

---

## GDPR Compliance

### Article 17 — Right to Erasure

GDPR Article 17 grants data subjects the right to request deletion of their personal data. The `delete-mapping` command fulfills this requirement.

**How it works:**

1. **Pseudonymization vs Anonymization:** When a document is processed, entity names are replaced with pseudonyms (e.g., "Marie Dupont" becomes "Leia Organa"). The mapping between the real name and the pseudonym is stored in the encrypted database. As long as the mapping exists, the pseudonymized data is still considered personal data under GDPR.

2. **Deletion = Anonymization:** When a mapping is deleted via `delete-mapping`, the link between the pseudonym and the real identity is permanently destroyed. The pseudonymized documents remain unchanged, but they are now **anonymous** — the pseudonym "Leia Organa" can no longer be linked to "Marie Dupont". Anonymous data falls outside GDPR scope.

3. **Audit Trail:** Every deletion creates an `ERASURE` audit log entry recording who was deleted, when, and why. This provides the compliance evidence that the erasure request was fulfilled.

**Erasure Workflow:**

```bash
# 1. Receive GDPR erasure request for "Marie Dupont"
# 2. Search for the entity
gdpr-pseudo list-entities --search "Dupont"

# 3. Delete the mapping with audit reason
gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

# 4. Verify deletion
gdpr-pseudo list-entities --search "Dupont"

# 5. Export audit log for compliance records
gdpr-pseudo export erasure_audit.json --type ERASURE
```

**Important notes:**
- Deletion is **permanent and irreversible** — the mapping cannot be recovered
- The pseudonymized documents are **not modified** — only the mapping database is affected
- Other entities in the database are **unaffected** by the deletion
- The audit log entry persists even after deletion, providing compliance evidence

**PII Retention in Audit Logs:**

The `ERASURE` audit log entry intentionally retains the deleted entity's **name**, **type**, and **internal ID**. This is necessary to prove that a specific erasure request was fulfilled — without this information, there would be no way to verify compliance with the original GDPR request.

This retention is justified under GDPR Article 17(3)(e) (establishment, exercise, or defence of legal claims) and Article 5(2) (accountability principle — the controller must be able to demonstrate compliance). The audit log serves as evidence that the data subject's right to erasure was exercised.

The retained PII in audit logs is:
- Protected by the same AES-256-SIV encryption as all other database content
- Accessible only with the database passphrase
- Minimal (name and type only — no addresses, contact details, or other personal data)
- Necessary for the legitimate purpose of compliance evidence

---

## Configuration File

The CLI supports configuration files in YAML format. Configuration priority (highest to lowest):

1. CLI flags
2. Custom config file (`--config`)
3. Project config (`./.gdpr-pseudo.yaml`)
4. Home config (`~/.gdpr-pseudo.yaml`)
5. Defaults

### Configuration Schema

```yaml
database:
  path: mappings.db

pseudonymization:
  theme: neutral    # neutral | star_wars | lotr
  model: spacy

logging:
  level: INFO       # DEBUG | INFO | WARNING | ERROR
  file: gdpr-pseudo.log  # Optional, logs to file if set
```

### Security Note

**Passphrase is NOT supported in config files** for security reasons. Plaintext credential storage is forbidden.

Use one of these methods instead:
1. **Interactive prompt** (most secure - default behavior)
2. **Environment variable** `GDPR_PSEUDO_PASSPHRASE` (for automation)
3. **CLI flag** `--passphrase` (visible in process lists - use with caution)

**Warning about `--passphrase` flag:**
When you use `--passphrase` on the command line, the passphrase may be:
- Visible in shell history (`~/.bash_history`, `~/.zsh_history`)
- Visible in process lists (`ps aux`)
- Logged by audit systems

For security-sensitive environments, prefer the environment variable or interactive prompt.

---

## Common Workflows

### First-Time Setup

```bash
# 1. Initialize database
gdpr-pseudo init

# 2. Process your first document
gdpr-pseudo process interview.txt

# 3. View the results
gdpr-pseudo list-mappings
```

### Batch Processing Workflow

```bash
# 1. Initialize database (if not already done)
gdpr-pseudo init --db project.db

# 2. Process all documents in a directory
gdpr-pseudo batch ./raw_interviews/ -o ./pseudonymized/ --db project.db

# 3. View statistics
gdpr-pseudo stats --db project.db
```

### Mapping Management Workflow

```bash
# 1. List current mappings
gdpr-pseudo list-mappings

# 2. Filter by type
gdpr-pseudo list-mappings --type PERSON

# 3. Validate mappings for quality
gdpr-pseudo validate-mappings --interactive

# 4. Export for review
gdpr-pseudo list-mappings --export review.csv
```

### GDPR Erasure Workflow

```bash
# 1. Find the entity to delete
gdpr-pseudo list-entities --search "Dupont"

# 2. Delete the mapping (with audit reason)
gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

# 3. Verify deletion
gdpr-pseudo list-entities --search "Dupont"

# 4. Export audit trail for compliance
gdpr-pseudo export erasure_log.json --type ERASURE
```

### Export Audit Log for Compliance

```bash
# Export all operations
gdpr-pseudo export audit_complete.json

# Export operations from specific period
gdpr-pseudo export audit_january.json --from 2026-01-01 --to 2026-01-31

# Export only successful operations
gdpr-pseudo export audit_success.csv --success-only
```

### Combining Projects

```bash
# Import mappings from old project to new
gdpr-pseudo import-mappings old_project.db --db new_project.db

# Verify import
gdpr-pseudo stats --db new_project.db
```

---

## Pseudonymization Methodology

### Gender-Aware Pseudonym Assignment

Starting with v1.1, the pseudonymizer automatically detects the gender of French first names and assigns gender-matched pseudonyms. This preserves gender coherence in pseudonymized documents, improving readability and LLM utility.

**How it works:**

1. **Gender Detection:** When a PERSON entity is detected (e.g., "Marie Dupont"), the first name is looked up in a French gender dictionary (~930 names from INSEE public data).

2. **Gender-Matched Selection:** The pseudonym engine selects a replacement first name from the matching gender pool:
   - Female name (e.g., "Marie") -> female pseudonym first name (e.g., "Léa")
   - Male name (e.g., "Jean") -> male pseudonym first name (e.g., "Lucas")
   - Unknown/ambiguous name -> random from combined male+female list (preserves previous behavior)

3. **Compound Names:** Hyphenated French names use the first component for gender detection:
   - "Jean-Pierre" -> "Jean" -> male
   - "Marie-Claire" -> "Marie" -> female

4. **Ambiguous Names:** Names that are genuinely unisex in French (e.g., Camille, Dominique, Claude) are treated as unknown and receive pseudonyms from the combined list.

**Data Sources:**
- Gender dictionary built from INSEE Fichier des prenoms (Open License 2.0 / Etalab) and existing pseudonym library data
- ~470 male names, ~457 female names, ~18 ambiguous names
- Coverage: >=90% of common French first names

**No configuration needed:** Gender-aware assignment is automatic and requires no user action. It works across all pseudonym themes (neutral, star_wars, lotr).

---

## Troubleshooting

### Database Not Found

**Error:** `Database file not found: mappings.db`

**Solution:** Run `gdpr-pseudo init` to create a new database.

### Incorrect Passphrase

**Error:** `Incorrect passphrase. Please check your passphrase and try again.`

**Solution:**
- Verify you're using the correct passphrase
- If you've forgotten the passphrase, the database cannot be recovered
- Create a new database with `gdpr-pseudo init --force`

### Passphrase in Config File

**Error:** `Passphrase in config file is forbidden for security`

**Solution:** Remove the `passphrase` field from your config file. Use:
- Environment variable: `export GDPR_PSEUDO_PASSPHRASE="your_passphrase"`
- Interactive prompt (default)
- CLI flag: `--passphrase` (not recommended for security)

### Invalid Theme

**Error:** `Invalid theme 'xyz' is not recognized`

**Solution:** Use one of the valid themes: `neutral`, `star_wars`, `lotr`

### File Permission Errors

**Error:** `Permission denied: cannot access file`

**Solution:**
- Check file permissions with `ls -la`
- Ensure you have read/write access to the file
- On Windows, close any applications using the file

### Database Corruption

**Error:** `Database may be corrupted`

**Solution:**
1. If you have a backup, restore it
2. Export what data you can with `gdpr-pseudo export`
3. Create a new database with `gdpr-pseudo init --force`

### Memory Issues with Large Batches

**Symptom:** Processing slows or crashes on large directories

**Solution:**
- Process files in smaller batches
- Use `--limit` to process a subset
- Close other applications to free memory

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User Error (invalid input, file not found) |
| 2 | System Error (unexpected exception) |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GDPR_PSEUDO_PASSPHRASE` | Database passphrase (for automation) |

---

## Related Documentation

- [Installation Guide](installation.md) - Setup instructions for all platforms
- [Usage Tutorial](tutorial.md) - Step-by-step usage tutorials
- [FAQ](faq.md) - Common questions and answers
- [Troubleshooting](troubleshooting.md) - Error reference and solutions
