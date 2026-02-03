# Epic 3: CLI Polish & Batch Processing (Week 11-13)

**Epic Goal:** Complete the pseudonymization engine with LOCATION/ORG support, deliver production-ready batch processing CLI, and provide comprehensive user documentation for v1.0 MVP launch.

**Timeline:** 3 weeks (Week 11-13, following v0.1.0-alpha release)
**Status:** ✅ **APPROVED** - Ready for development
**Context:** Post-Epic 2 (v0.1.0-alpha released), pre-v1.0 MVP launch (Epic 4)

---

## Epic Context

**What Changed Since Original Epic 3 Plan:**
- Epic 2 delivered single-document pseudonymization workflow (Story 2.6)
- Epic 2 validated batch processing architecture via spike (Story 2.7)
- Alpha release (v0.1.0) revealed critical gap: Only PERSON entities have themed pseudonyms
- Alpha testing period (Week 10-11) provides user feedback to inform implementation details

**Epic 3 Strategic Focus:**
1. **Complete Pseudonymization Engine:** Add LOCATION/ORG pseudonym libraries (HIGH priority gap)
2. **Production-Ready Batch Processing:** Move from spike to full CLI implementation
3. **User-Facing Documentation:** Enable self-service adoption for v1.0 users
4. **CLI Polish:** Error messages, help text, configuration support

---

## Stories Overview

| Story | Title | Effort | Priority | Dependencies |
|-------|-------|--------|----------|--------------|
| 3.0 | LOCATION/ORG Pseudonym Libraries | 3-5 days | HIGH | None (Epic 2 complete) |
| 3.1 | Batch Processing CLI | 4-6 days | HIGH | Story 3.0 |
| 3.2 | Progress Reporting for Batches | 2-3 days | MEDIUM | Story 3.1 |
| 3.3 | Configuration File Support | 2-3 days | MEDIUM | Story 3.1 |
| 3.4 | CLI UX Polish | 2-3 days | MEDIUM | Stories 3.1-3.3 |
| 3.5 | User Documentation & Guides | 3-4 days | HIGH | Stories 3.0-3.4 |

**Total Estimated Effort:** 16-24 days (within 3-week timeline with parallelization)

---

## Story 3.0: LOCATION and ORGANIZATION Pseudonym Libraries

**Source:** FE-005 (Backlog), discovered during Story 2.9 alpha preparation
**Priority:** HIGH - Core feature gap affecting tool utility

**As a** user processing documents with locations and organizations,
**I want** themed pseudonyms for LOCATION and ORGANIZATION entities (not just PERSON),
**so that** all entity types are pseudonymized consistently with my chosen theme (neutral, Star Wars, LOTR).

### Current State (Epic 2)
- ✅ PERSON entities: Full themed pseudonym support (first_names, last_names)
- ❌ LOCATION entities: Detected and validated, but NOT pseudonymized with themes
- ❌ ORGANIZATION entities: Detected and validated, but NOT pseudonymized with themes

### User Impact
Documents with significant location/organization references have incomplete pseudonymization, limiting tool utility for:
- Academic research with geographic data
- Corporate documents with company/agency references
- Interview transcripts mentioning institutions

### Acceptance Criteria

#### AC1: Library Structure Extended
- Add `locations` field to all 3 pseudonym library JSON files (neutral.json, star_wars.json, lotr.json)
- Add `organizations` field to all 3 pseudonym library JSON files
- Maintain backward compatibility with existing PERSON fields (first_names, last_names)

**Example Library Structure:**
```json
{
  "theme": "star_wars",
  "first_names": { "male": [...], "female": [...], "neutral": [...] },
  "last_names": [...],
  "locations": {
    "cities": ["Mos Eisley", "Theed", "Cloud City", ...],
    "planets": ["Tatooine", "Coruscant", "Naboo", ...],
    "regions": ["Outer Rim", "Core Worlds", ...]
  },
  "organizations": {
    "companies": ["Kuat Drive Yards", "Sienar Fleet Systems", ...],
    "agencies": ["Rebel Alliance", "Galactic Empire", ...],
    "institutions": ["Jedi Order", "Galactic Senate", ...]
  }
}
```

#### AC2: Library Content Populated

**Neutral Theme** (French/realistic names):
- 50+ French cities/regions (Paris → Lyon, Marseille → Toulouse, etc.)
- 30+ realistic organization names (Generic Corp, Tech SA, Research Institute, etc.)
- Prioritization based on alpha feedback question #14 (location/org types most common in user documents)

**Star Wars Theme:**
- 50+ Star Wars locations (planets, cities, regions from SW canon)
- 30+ Star Wars organizations (Rebel Alliance, Empire, companies, orders)

**LOTR Theme:**
- 50+ Middle-earth locations (cities, regions, landmarks from LOTR/Hobbit)
- 30+ LOTR organizations (kingdoms, guilds, councils)

**Default Parameters (adjustable based on alpha feedback Week 11):**
- Locations: 50 cities, 20 countries/planets, 10 regions = 80 total per theme
- Organizations: 20 companies, 10 agencies/institutions, 5 government = 35 total per theme

#### AC3: Pseudonymization Logic Updated
- LibraryBasedPseudonymManager extended to handle LOCATION and ORGANIZATION entity types
- Simple pseudonymization (no compositional logic needed - locations/orgs are atomic)
- Gender-neutral selection (locations/orgs have no gender)
- Same collision prevention as PERSON entities (1:1 mapping maintained)

#### AC4: Database Schema Support
- Mapping table stores LOCATION and ORG pseudonyms alongside PERSON
- Entity type column differentiates PERSON vs LOCATION vs ORG mappings
- Encrypted storage applies to all entity types

#### AC5: Testing Coverage
- Unit tests: Library loading, pseudonym selection for LOC/ORG, collision prevention
- Integration tests: End-to-end pseudonymization with PERSON + LOC + ORG in same document
- Test corpus validation: Verify all 3 entity types pseudonymized correctly

#### AC6: Documentation Updated
- ALPHA-*.md docs updated to reflect LOC/ORG support (remove "limitation" notes)
- README.md updated: Remove "PERSON only" limitation
- CHANGELOG.md updated: v0.2.0 (or next version) notes LOC/ORG support added

### Alpha Feedback Integration

**Week 11, Day 2-3:** PM reviews alpha feedback question #14 responses and adjusts library content priorities:
- **If feedback shows:** "80% of LOC entities are addresses" → Increase address entries, reduce city entries
- **If feedback shows:** "Most ORG entities are government agencies" → Prioritize government/agency orgs over companies
- **Implementation:** Adjust Tasks 3.0.2-3.0.3 library population based on feedback (low risk - just data changes)

### Story 3.0 Task Breakdown

1. **Task 3.0.1:** Design library structure (JSON schema extension, database schema update)
2. **Task 3.0.2:** Populate neutral theme (cities/regions + realistic orgs) - **ADJUSTABLE based on alpha feedback**
3. **Task 3.0.3:** Populate Star Wars and LOTR themes - **ADJUSTABLE based on alpha feedback**
4. **Task 3.0.4:** Update LibraryBasedPseudonymManager to handle LOC/ORG entity types
5. **Task 3.0.5:** Add unit tests (library loading, pseudonym selection, collision prevention)
6. **Task 3.0.6:** Add integration tests (multi-entity-type documents)
7. **Task 3.0.7:** Update documentation (ALPHA-*.md, README, CHANGELOG)

**Estimated Effort:** 3-5 days (Week 11, Days 1-4/5)

---

## Story 3.1: Batch Processing CLI

**Source:** Epic 3 original scope, validated by Story 2.7 spike (Epic 2)
**Priority:** HIGH - Core workflow for production use

**As a** user,
**I want** to process multiple documents in a single batch operation via CLI,
**so that** I can pseudonymize entire document corpora efficiently with consistent mappings.

### Context
- Epic 2 Story 2.7 spike validated architecture: multiprocessing.Pool, 1.17x-2.5x speedup
- Epic 2 Story 2.8 fixed critical bug (pseudonym component collision)
- Epic 3 Story 3.0 ensures batch processing has full entity-type support (PERSON + LOC + ORG)

### Acceptance Criteria

#### AC1: Batch Command Implemented
- `gdpr-pseudo batch` command accepts directory path or file pattern
- CLI argument: `--db <database_path>` (required)
- CLI argument: `--theme <theme_name>` (optional, default: neutral)
- CLI argument: `--output-dir <directory>` (optional, default: `<input_dir>_pseudonymized`)
- CLI argument: `--workers <count>` (optional, default: min(cpu_count, 4))

**Example Usage:**
```bash
# Process all .txt files in directory
gdpr-pseudo batch input_docs/ --db mappings.db --theme star_wars

# Process specific files
gdpr-pseudo batch doc1.txt doc2.txt doc3.txt --db mappings.db
```

#### AC2: Process-Based Parallelism
- Use `multiprocessing.Pool` (validated in Story 2.7)
- Worker count: min(cpu_count, 4) (prevents resource exhaustion)
- Each worker processes one document at a time
- Mapping table updates are synchronized (database locks prevent race conditions)

#### AC3: Cross-Document Consistency (FR6 from original PRD)
- Same entity across multiple documents gets same pseudonym
- Mapping table updated incrementally (first worker to see entity creates mapping)
- Database WAL mode ensures concurrent read safety (from Story 2.4)

#### AC4: Error Handling
- Continue processing on individual file errors (don't halt entire batch)
- Collect errors and report at end: "3/50 files failed: <list of files with error messages>"
- Failed files logged with error reason: "doc5.txt: Invalid UTF-8 encoding"

#### AC5: Batch Summary Report
- After processing, display summary:
  - Total files processed / failed
  - Total entities detected (PERSON / LOCATION / ORG breakdown)
  - Total unique pseudonyms created
  - Processing time and throughput (files/second)

**Example Output:**
```
Batch Processing Complete
━━━━━━━━━━━━━━━━━━━━━━━
Files Processed: 47/50 (3 failed)
Entities Detected: 1,245 (PERSON: 823, LOCATION: 312, ORG: 110)
Unique Pseudonyms: 487
Processing Time: 4m 32s (10.4 files/min)

Failed Files:
- doc5.txt: Invalid UTF-8 encoding
- doc12.txt: File not found
- doc48.txt: Corrupted file
```

#### AC6: Performance Validation (NFR2 from original PRD)
- Process 50 documents (avg 3-5 pages each) in <30 minutes on standard hardware
- Target throughput: ≥1.5 files/minute (validated: Story 2.7 showed 1.17x-2.5x speedup)

#### AC7: Testing Coverage
- Unit tests: CLI argument parsing, worker orchestration, error collection
- Integration test: Process 25-document test corpus, verify consistency and performance
- Edge case tests: Empty directory, no .txt files, all files fail

#### AC8: Documentation
- README.md: Add batch processing example
- CLI help text: `gdpr-pseudo batch --help` shows all arguments

### Story 3.1 Task Breakdown

1. **Task 3.1.1:** Implement `batch` CLI command (argument parsing, validation)
2. **Task 3.1.2:** Implement multiprocessing orchestration (worker pool, task distribution)
3. **Task 3.1.3:** Implement cross-document consistency logic (synchronized mapping updates)
4. **Task 3.1.4:** Implement error handling and summary reporting
5. **Task 3.1.5:** **Add pytest-benchmark for automated performance regression tests (1 hour)** - FE-003
6. **Task 3.1.6:** Add unit tests (CLI, orchestration, error handling)
7. **Task 3.1.7:** Add integration test (25-document batch, consistency validation)

**Estimated Effort:** 4-6 days (Week 11, Days 5+ → Week 12)

---

## Story 3.2: Progress Reporting for Large Batches

**Source:** Epic 3 original scope (Story 3.3 progress indicators)
**Priority:** MEDIUM - UX improvement for long-running batches

**As a** user processing large batches (50+ documents),
**I want** real-time progress reporting with visual indicators,
**so that** I understand processing status and can estimate completion time.

### Acceptance Criteria

#### AC1: Progress Bar Implemented
- Use `rich` library for terminal progress bar
- Show: current file, files completed/total, percentage complete
- Update in real-time as workers complete files

**Example Output:**
```
Processing Batch...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47/50 94% [4m 12s]
Current: processing doc48.txt (Worker 3)
Entities Detected: 1,124 | Pseudonyms Created: 456
```

#### AC2: Per-File Progress Details
- Show current file being processed by each worker
- Display entities detected count (live update)
- Display pseudonyms created count (live update)

#### AC3: Estimated Time Remaining
- Calculate ETA based on average file processing time
- Update ETA dynamically as processing speed changes

#### AC4: Completion Summary
- Final summary matches batch summary from Story 3.1 AC5
- Progress bar transitions to "Complete" state with green checkmark

#### AC5: Testing Coverage
- Unit tests: Progress calculation, ETA estimation
- Manual testing: Verify progress bar updates correctly during batch processing

### Story 3.2 Task Breakdown

1. **Task 3.2.1:** Integrate `rich` library for progress bars
2. **Task 3.2.2:** Implement progress tracking (worker status, file counts, ETA calculation)
3. **Task 3.2.3:** Implement live progress display (real-time updates)
4. **Task 3.2.4:** Add unit tests (progress calculation, ETA logic)

**Estimated Effort:** 2-3 days (Week 12)

---

## Story 3.3: Configuration File Support

**Source:** Epic 3 original scope (Story 3.1 AC4)
**Priority:** MEDIUM - UX improvement for repeated workflows

**As a** user,
**I want** to configure default CLI settings via `.gdpr-pseudo.yaml` file,
**so that** I don't have to repeat common arguments for every command.

### Acceptance Criteria

#### AC1: Configuration File Schema
- Support `.gdpr-pseudo.yaml` in project root or home directory (~/)
- Project root config overrides home directory config
- Configuration options:
  - `default_theme`: "neutral" | "star_wars" | "lotr"
  - `default_database`: Path to default mapping database
  - `default_output_dir`: Default output directory for batch processing
  - `batch_workers`: Default worker count for batch processing

**Example `.gdpr-pseudo.yaml`:**
```yaml
default_theme: star_wars
default_database: ~/.gdpr-pseudo/mappings.db
default_output_dir: ./pseudonymized_output
batch_workers: 4
```

#### AC2: CLI Argument Priority
- CLI arguments override config file settings
- Config file settings override built-in defaults
- Priority order: CLI > Project config > Home config > Built-in defaults

**Example:**
```bash
# Uses star_wars theme from config file
gdpr-pseudo process doc.txt

# Overrides config file with CLI argument
gdpr-pseudo process doc.txt --theme neutral
```

#### AC3: Config File Validation
- Validate config file syntax on load (YAML parsing)
- Validate config values (e.g., theme must be neutral/star_wars/lotr)
- Clear error messages for invalid config: "Invalid theme 'harry_potter' in .gdpr-pseudo.yaml (line 2)"

#### AC4: Help Text Documentation
- `gdpr-pseudo --help` explains config file support
- `gdpr-pseudo config --show` command displays current effective config (merged from all sources)

#### AC5: Testing Coverage
- Unit tests: Config file loading, priority resolution, validation
- Integration test: Run commands with various config file combinations

### Story 3.3 Task Breakdown

1. **Task 3.3.1:** Implement config file loading (YAML parsing, file search)
2. **Task 3.3.2:** Implement config priority resolution (CLI > Project > Home > Defaults)
3. **Task 3.3.3:** Implement config validation (schema validation, error messages)
4. **Task 3.3.4:** Add `config --show` command for debugging
5. **Task 3.3.5:** Add unit tests (loading, priority, validation)
6. **Task 3.3.6:** Update help text and documentation

**Estimated Effort:** 2-3 days (Week 12)

---

## Story 3.4: CLI UX Polish

**Source:** Epic 3 original scope (Story 3.6 enhanced error handling)
**Priority:** MEDIUM - Quality-of-life improvements

**As a** user,
**I want** clear, actionable error messages and comprehensive help text,
**so that** I can resolve issues without external support.

### Acceptance Criteria

#### AC1: Error Message Style Guide
- Format: `[ERROR] <Description> | Action: <Suggested action> | Docs: <doc link>`
- Example: `[ERROR] Passphrase incorrect | Action: Use same passphrase from 'init' command | Docs: https://...`

#### AC2: Error Catalog for Common Scenarios
- File not found → "Check file path, use absolute or relative path"
- Invalid passphrase → "Passphrase incorrect, use same passphrase from `init` command"
- spaCy model not installed → "Run: poetry run python scripts/install_spacy_model.py"
- Permission denied → "Check file permissions or run with appropriate privileges"
- Corrupt database → "Mapping table corrupted, restore from backup or re-run `init`"

#### AC3: Help Text Improvements
- `gdpr-pseudo --help`: Show all commands with brief descriptions
- `gdpr-pseudo <command> --help`: Show command-specific arguments and examples
- Include usage examples for common workflows
- **Bug Fix:** Correct program name display in `--help` (shows `gdpr-pseudo.cmd` on Windows instead of `gdpr-pseudo`)

**Example Help Text:**
```
gdpr-pseudo process --help

Process a single document with pseudonymization.

Usage:
  gdpr-pseudo process <file> --db <database> [options]

Arguments:
  <file>         Path to document (.txt or .md)
  --db <path>    Path to mapping database (required)
  --theme <name> Pseudonym theme: neutral, star_wars, lotr (default: neutral)
  --output <path> Output file path (default: <file>_pseudonymized.txt)

Examples:
  # Basic processing
  gdpr-pseudo process interview.txt --db mappings.db

  # With Star Wars theme
  gdpr-pseudo process interview.txt --db mappings.db --theme star_wars
```

#### AC4: Input Validation with User-Friendly Messages
- Validate file existence before processing
- Validate database path (create if doesn't exist, error if unreadable)
- Validate theme name (suggest valid themes if invalid)
- Validate passphrase strength (min 12 characters, warn if weak)
- **Security:** `destroy-table` command must verify passphrase before destruction (prevents accidental deletion of wrong database)

#### AC5: Optional: Visual Indicators for Batch Operations (FE-001/FE-002)
**Conditional based on alpha tester demand** (survey question #13):
- FE-001: Visual indicator for context cycling (e.g., dot navigation ● ○ ○)
- FE-002: Batch operations visual feedback (confirm Shift+A/R actions)
- **Scope Gate:** Only implement if ≥3 alpha testers request this feature

#### AC6: Testing Coverage
- Unit tests: Trigger each error scenario, verify message format
- Manual testing: Verify help text clarity and examples

### Story 3.4 Task Breakdown

1. **Task 3.4.1:** Implement error message style guide (error formatter class)
2. **Task 3.4.2:** Create error catalog (common scenarios + messages)
3. **Task 3.4.3:** Update all CLI commands with improved help text
4. **Task 3.4.4:** Implement input validation (file exists, database valid, theme valid)
5. **Task 3.4.5:** Optional: FE-001/FE-002 visual indicators (if alpha demand ≥3 testers)
6. **Task 3.4.6:** Add unit tests (error scenarios, validation logic)
7. **Task 3.4.7:** Security hygiene - Add CLI warning for `--passphrase` flag (shell history exposure risk); update help text and emit runtime warning recommending env var or interactive prompt
8. **Task 3.4.8:** Security hygiene - Remove dead stub encryption code (`utils/encryption.py`) that was superseded by production `data/encryption.py` in Epic 2
9. **Task 3.4.9:** Bug fix - Correct program name display in `--help` (Windows shows `gdpr-pseudo.cmd` instead of `gdpr-pseudo`)
10. **Task 3.4.10:** Security - Add passphrase verification to `destroy-table` command before allowing database destruction

**Estimated Effort:** 2-3 days (Week 13) + 1-2 hours if FE-001/FE-002 added

---

## Story 3.5: User Documentation & Guides

**Source:** Epic 3 original scope (Story 3.8 beta documentation)
**Priority:** HIGH - Critical for v1.0 self-service adoption

**As a** new user,
**I want** comprehensive installation and usage documentation,
**so that** I can successfully install and use the tool without support.

### Acceptance Criteria

#### AC1: Installation Guide (docs/installation.md)
- Platform-specific instructions: Windows, macOS, Linux
- Prerequisites: Python version, Poetry installation
- Step-by-step installation: Clone repo → Install dependencies → Install spaCy model → Verify
- Troubleshooting section: Common installation issues + solutions
- **Command invocation:** Document clearly that during beta phase, command is `poetry run gdpr-pseudo <cmd>` (direct `gdpr-pseudo` command available after Epic 4 PyPI publication)

**Content:**
- Platform: Windows 11, macOS (Intel/ARM), Ubuntu 22.04
- Python: 3.9-3.13 (note: 3.14+ not supported due to spaCy compatibility)
- Poetry: 1.7+
- **Command usage:** `poetry run gdpr-pseudo <command>` (beta) → `gdpr-pseudo <command>` (v1.0 after pip install)
- Troubleshooting: Python version mismatch, model download failures, permission issues

#### AC2: Usage Tutorial (docs/tutorial.md)
- Quick start: First pseudonymization (5-minute tutorial)
- Common workflows: Single document, batch processing, configuration files
- Validation UI walkthrough: Entity review, keyboard shortcuts
- Theme comparison: neutral vs star_wars vs lotr examples

**Content:**
- Tutorial 1: Single document pseudonymization (process command)
- Tutorial 2: Batch processing multiple documents (batch command)
- Tutorial 3: Using configuration files (.gdpr-pseudo.yaml)
- Tutorial 4: Choosing a pseudonym theme

#### AC3: Update ALPHA-*.md Documentation
- ALPHA-INSTALL.md: Update to reflect Story 3.0 changes (remove "PERSON only" limitation)
- ALPHA-QUICKSTART.md: Update limitations section (LOC/ORG now supported)
- ALPHA-TESTING-PROTOCOL.md: Already updated in Story 2.9 (no changes needed)

#### AC4: README.md Updates
- Update "Quick Start" section: Reflect Epic 3 features (batch processing, config files)
- Update "Documentation" section: Add links to installation.md and tutorial.md
- Update "Known Limitations" section: Remove "PERSON only" note
- Update "Project Metrics": Epic 3 status, story count

#### AC5: Command Reference Documentation
- Create docs/cli-reference.md: All commands, arguments, examples
- Comprehensive reference: `process`, `batch`, `config`, `init`, `stats`, etc.

#### AC6: Testing Coverage
- Documentation review: PM + PO review for clarity, completeness
- User testing: 1-2 friendly users follow installation guide, report issues

### Story 3.5 Task Breakdown

1. **Task 3.5.1:** Create docs/installation.md (platform-specific instructions, troubleshooting)
2. **Task 3.5.2:** Create docs/tutorial.md (quick start, common workflows, validation UI)
3. **Task 3.5.3:** Create docs/cli-reference.md (all commands, comprehensive reference)
4. **Task 3.5.4:** Update ALPHA-INSTALL.md and ALPHA-QUICKSTART.md (remove limitations)
5. **Task 3.5.5:** Update README.md (Quick Start, Documentation section, metrics)
6. **Task 3.5.6:** Documentation review and polish (PM/PO review, user testing)

**Estimated Effort:** 3-4 days (Week 13)

---

## Epic 3 Success Criteria

### Primary Goals
1. ✅ **Core Engine Complete:** LOCATION and ORG pseudonyms supported across all 3 themes
2. ✅ **Batch Processing:** Process 50+ documents efficiently with consistent mappings
3. ✅ **User Documentation:** Self-service installation and usage guides complete
4. ✅ **Alpha Limitations Addressed:** "PERSON only" limitation removed

### Performance Targets
- **Batch Processing:** 50 documents in <30 minutes (≥1.5 files/min)
- **Pseudonym Coverage:** 50+ locations, 30+ organizations per theme
- **Documentation Quality:** ≥80% of users successfully install without support (measured in Epic 4)

### Quality Gates
- ✅ All unit tests passing (target: ≥85% coverage for new code)
- ✅ Integration tests passing (batch processing, multi-entity-type documents)
- ✅ PM + PO documentation review complete
- ✅ No critical bugs blocking v1.0 launch

---

## Epic 3 Dependencies

### From Epic 2 (Complete)
- ✅ Story 2.1: Pseudonym library system (architecture ready for extension)
- ✅ Story 2.2: Compositional pseudonymization (LibraryBasedPseudonymManager extensible)
- ✅ Story 2.4: Encrypted mapping table (supports all entity types)
- ✅ Story 2.6: Single-document workflow (CLI foundation ready)
- ✅ Story 2.7: Batch processing spike (architecture validated)
- ✅ Story 2.8: Pseudonym collision fix (1:1 mapping ensured)

### To Epic 4 (Launch Readiness)
- Story 3.0 output → Epic 4 can test LOC/ORG pseudonymization quality
- Story 3.1 output → Epic 4 can test batch processing at scale
- Story 3.5 output → Epic 4 uses documentation for final polish and FAQ creation

---

## Epic 3 Risks & Mitigation

### Risk 1: Story 3.0 Overruns (>5 days)
**Likelihood:** Low (well-scoped, architecture validated)
**Impact:** HIGH (delays Story 3.1, compresses timeline)
**Mitigation:**
- Story 3.0 has clear task breakdown (7 tasks, each <1 day)
- Alpha feedback adjustments are low-risk (just data population changes)
- If Day 5 not complete → descope FE-001/FE-002 (visual indicators) from Story 3.4

### Risk 2: Alpha Feedback Requires Major Changes
**Likelihood:** Low (FE-005 HIGH priority confirmed, feedback just informs details)
**Impact:** MEDIUM (mid-epic scope changes)
**Mitigation:**
- Story 3.0 designed with "parameterized content" approach (easy to adjust)
- Week 13 buffer (Days 4-5) reserved for larger adjustments
- PM monitors alpha feedback Week 11 Days 2-3 for early warning

### Risk 3: Velocity Not Achievable (2.0 stories/week)
**Likelihood:** Low (user confirmed confidence, Story 2.7 validated batch arch)
**Impact:** HIGH (Epic 3 incomplete, delays v1.0 launch)
**Mitigation:**
- Daily progress tracking Week 11 (Story 3.0 + 3.1)
- If Week 11 ends with Story 3.1 incomplete → descope Story 3.2 or 3.3
- Story 3.5 (documentation) can extend into Epic 4 if needed (less critical)

### Risk 4: pytest-benchmark Integration Issues (FE-003)
**Likelihood:** Very Low (1-hour task, well-understood library)
**Impact:** LOW (optional quality improvement)
**Mitigation:**
- Task 3.1.5 isolated to 1 hour (if fails, defer to Epic 4)
- No Epic 3 blocker if pytest-benchmark deferred

---

## Epic 3 Timeline

**Week 11:**
- Days 1-4: Story 3.0 (LOCATION/ORG Pseudonym Libraries)
- Days 2-3: Alpha feedback review, adjust Story 3.0 Tasks 3.0.2-3.0.3 if needed
- Days 5-7: Story 3.1 start (Batch Processing CLI)

**Week 12:**
- Days 1-3: Story 3.1 completion (Batch Processing CLI + Task 3.1.5 pytest-benchmark)
- Days 4-5: Story 3.2 (Progress Reporting)
- Days 6-7: Story 3.3 (Configuration File Support)

**Week 13:**
- Days 1-3: Story 3.4 (CLI UX Polish)
- Days 4-5: Story 3.5 (User Documentation) + Buffer for alpha feedback adjustments

---

## Epic 3 → Epic 4 Handoff

**Deliverables to Epic 4:**
1. Complete pseudonymization engine (PERSON + LOCATION + ORGANIZATION)
2. Production-ready batch processing CLI
3. User-facing documentation (installation, tutorial, CLI reference)
4. Performance regression tests (pytest-benchmark)
5. Updated ALPHA-*.md docs (no "PERSON only" limitation)

**Epic 4 Focus:**
- LLM validation (verify pseudonymized docs maintain utility)
- Methodology documentation (academic citation)
- FAQ and troubleshooting (based on alpha feedback)
- Launch checklist (README polish, license, PyPI package)

---

**Epic 3 Status:** ✅ APPROVED - Ready for Dev Agent Execution

**PM Contact:** John (Product Manager)
**PO Contact:** Sarah (Product Owner)
**Last Updated:** 2026-01-30
**Next Review:** End of Week 11 (progress check), End of Week 13 (Epic 3 completion)
