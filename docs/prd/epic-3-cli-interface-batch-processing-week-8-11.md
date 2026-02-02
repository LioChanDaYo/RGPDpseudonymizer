# Epic 3: CLI Interface & Batch Processing (Week 8-11)

**Epic Goal:** Deliver complete command-line interface with all user-facing commands, process-based parallel batch processing, and optional interactive validation mode, achieving production-ready workflows for real-world use cases.

---

### Story 3.1: Complete CLI Command Set (FR15)

**As a** user,
**I want** all planned CLI commands implemented with consistent interface and help documentation,
**so that** I can perform all necessary operations through intuitive commands.

#### Acceptance Criteria

1. **AC1:** All commands from FR15 implemented:
   - `init` - Initialize new mapping table with passphrase
   - `process` - Process single document (already exists from Epic 2, enhanced)
   - `batch` - Process multiple documents
   - `list-mappings` - View entity↔pseudonym correspondences
   - `validate-mappings` - Review existing mappings without processing
   - `stats` - Show statistics (# entities, # documents, library exhaustion %)
   - `import-mappings` - Load mappings from previous project
   - `export` - Export audit log
   - `destroy-table` - Secure deletion with confirmation prompt
   - `clear-mappings` - Delete pseudonym mappings (single entity or all) with confirmation prompt
2. **AC2:** Consistent command structure: global options (--config, --verbose), command-specific options.
3. **AC3:** Help text for all commands: `gdpr-pseudo --help`, `gdpr-pseudo process --help`.
4. **AC4:** Configuration file support: `.gdpr-pseudo.yaml` in home directory or project root for default settings (including custom passphrase).
5. **AC5:** Unit tests for each command: argument parsing, execution, error handling.
6. **AC6:** CLI documentation: Command reference with examples, common workflows.
7. **AC7 (Bug #5):** `clear-mappings` command functionality:
   - `clear-mappings --all` - Clear all pseudonym mappings with confirmation prompt
   - `clear-mappings --entity "Name"` - Clear specific entity mapping
   - `clear-mappings --type PERSON|LOCATION|ORG` - Clear all mappings of specific type
   - Confirmation prompt required for all deletion operations
   - Success message showing count of deleted mappings
8. **AC8 (Bug #6):** Shorter default passphrase option:
   - Configuration file (`.gdpr-pseudo.yaml`) supports custom passphrase setting
   - Default passphrase shortened from current implementation
   - Documentation updated with passphrase configuration examples
   - Security warning if passphrase is too short (< 12 characters)

---

### Story 3.2: Interactive Validation Mode (FR7, FR18)

**As a** user,
**I want** optional interactive validation mode to review detected entities before pseudonymization,
**so that** I can ensure quality and catch NER errors on sensitive documents.

#### Acceptance Criteria

1. **AC1:** `--validate` flag implemented for `process` and `batch` commands.
2. **AC2:** Validation mode workflow:
   - Detect entities using NER
   - Present entities to user in readable format (grouped by type: PERSON, LOCATION, ORG)
   - Allow user actions: confirm, remove entity, add missed entity, modify entity text
   - Show ambiguous standalone components flagged by FR4 logic
   - Apply user modifications before final pseudonymization
3. **AC3:** Interactive UI using `rich` library: formatted tables, color-coded entity types, keyboard navigation.
4. **AC4:** Default behavior (FR18): Validation mode OFF by default (fast processing).
5. **AC5:** Batch mode with validation: User reviews entities from all documents, then batch proceeds.
6. **AC6:** User modifications logged in audit log (FR12).
7. **AC7:** Unit tests: Validation flow, user input handling, modification application.
8. **AC8:** Integration test: Run validation mode on test document, simulate user interactions, verify final output.
9. **AC9 (Bug #2):** Title preservation in validation display:
   - When displaying entity and pseudonym during interactive validation, preserve titles in both original and pseudonym
   - Example: "Mme Nathalie Rousseau" should show pseudonym as "Mme Salomé Blanchard" (not "Salomé Blanchard")
   - Apply to all supported titles: M., Mme, Mlle, Dr, Pr, Maître, Me, etc.
   - Validation UI should clearly show titled form to avoid user confusion

---

### Story 3.3: Process-Based Batch Processing

**As a** user,
**I want** to efficiently process 10-100+ documents in a single batch operation,
**so that** I can pseudonymize entire document corpora with consistent mappings.

#### Acceptance Criteria

1. **AC1:** `batch` command implemented: accepts directory path or file list, processes all documents.
2. **AC2:** Process-based parallelism using `multiprocessing` module (per Technical Assumptions): worker pool with size min(cpu_count, 4).
3. **AC3:** Cross-document consistency (FR6): Mapping table updates incrementally ensure same entity gets same pseudonym across batch.
4. **AC4:** Progress indicators using `rich` library: progress bar, current file, entities detected, estimated time remaining.
5. **AC5:** Error handling: Continue processing on individual file errors, report failures at end.
6. **AC6:** Performance validation (NFR2): Process 50 documents in <30 minutes on standard hardware.
7. **AC7:** Batch summary report (FR18): After processing, show detected entities across all documents, statistics, any errors.
8. **AC8:** Unit tests: Batch orchestration, worker management, error handling.
9. **AC9:** Integration test: Process 25-document test corpus in batch, verify consistency and performance.

---

### Story 3.4: Idempotent Processing with Validation Mode (FR19 Clarification)

**As a** user,
**I want** clear behavior when re-processing documents with existing mappings,
**so that** I can iterate on documents without creating inconsistent pseudonyms.

#### Acceptance Criteria

1. **AC1:** Without `--validate`: Reuse ALL existing mappings, detect and add only new entities, output uses consistent pseudonyms.
2. **AC2:** With `--validate`: Present ALL entities (existing + new), show existing pseudonyms, allow user to change any mapping.
3. **AC3:** Document hash stored in mapping table: Detect when document content changes (new entities likely).
4. **AC4:** User-friendly messaging: "Document previously processed on [date], reusing 15 existing mappings, found 2 new entities."
5. **AC5:** Unit tests: Idempotency scenarios (exact reprocess, modified document, new entities), validation mode interaction.
6. **AC6:** Integration test: Process document, modify document, reprocess with/without validation, verify correct behavior.

---

### Story 3.5: Markdown Format-Aware Processing (FR21)

**As a** user,
**I want** Markdown files processed intelligently without breaking syntax,
**so that** pseudonymized Markdown remains valid and usable.

#### Acceptance Criteria

1. **AC1:** Markdown parser integrated: Identify exclusion zones (URLs, code blocks, inline code, image references).
2. **AC2:** Pseudonymization skips exclusion zones: Names in URLs, code blocks, inline code not replaced.
3. **AC3:** Comprehensive edge case handling from Technical Assumptions test suite:
   - Nested code blocks within lists
   - URLs with name-like query parameters
   - Inline code with French names
   - Markdown tables with name headers
   - Image alt text with names
   - Link references (text vs URL)
   - Mixed HTML in Markdown
4. **AC4:** Unit tests: Each edge case validated, regression tests for Markdown parsing.
5. **AC5:** Integration test: Process complex Markdown document with all edge cases, verify syntax validity and correct exclusions.
6. **AC6:** Plain text (.txt) processing unchanged (no Markdown parsing).

---

### Story 3.6: Enhanced Error Handling & Messages (NFR7)

**As a** user,
**I want** clear, actionable error messages when things go wrong,
**so that** I can resolve issues without external support.

#### Acceptance Criteria

1. **AC1:** Error message style guide implemented: `[ERROR] Clear description | Suggested action | Reference: <doc link>`.
2. **AC2:** Error catalog created covering common scenarios:
   - File not found → "Check file path, use absolute or relative path"
   - Invalid passphrase → "Passphrase incorrect, use same passphrase from `init` command"
   - Model not installed → "Run `python -m spacy download fr_core_news_lg`"
   - Low disk space → "Free up disk space or change output directory"
   - Permission denied → "Check file permissions or run with appropriate privileges"
   - Corrupt database → "Mapping table corrupted, restore from backup or run `init` for new table"
3. **AC3:** Contextual help: Error messages link to relevant documentation sections.
4. **AC4:** User-friendly validation: Validate inputs before processing (file exists, passphrase strength, valid config).
5. **AC5:** Unit tests: Trigger each error scenario, verify message format and clarity.
6. **AC6:** Target validation (NFR7): ≥80% of users resolve issues without support (measured in Beta testing).
7. **AC7 (Bug #1):** Early passphrase validation:
   - Validate passphrase BEFORE starting any document processing or entity detection
   - Current issue: Processing begins before passphrase check, wasting time on incorrect passphrase
   - Validation order: passphrase → file existence → file permissions → model availability → processing
   - Fast-fail on invalid passphrase with clear error message (ref AC2)
   - Unit test: Verify processing does not start with invalid passphrase

---

### Story 3.7: Cross-Platform Installation Testing (NFR3 Initial Validation)

**As a** user,
**I want** smooth installation on Windows, macOS, and Linux,
**so that** I can start using the tool quickly without setup frustration.

#### Acceptance Criteria

1. **AC1:** Installation tested on minimum 3 platforms: Windows 11, macOS (Intel or ARM), Ubuntu 22.04.
2. **AC2:** Installation script created: Checks Python version, installs dependencies, downloads NLP model, verifies installation.
3. **AC3:** Installation documentation updated: Platform-specific instructions, troubleshooting section.
4. **AC4:** Common installation issues documented with solutions:
   - Python version mismatch
   - pip vs Poetry installation
   - Model download failures (network issues, firewall)
   - Platform-specific dependency issues
5. **AC5:** Docker container option created as fallback for complex environments.
6. **AC6:** Initial NFR3 validation: ≥80% installation success rate on tested platforms (comprehensive validation in Epic 4).
7. **AC7:** Beta testers installation experience tracked: success rate, time to completion, support requests.

---

### Story 3.8: Beta Release Preparation

**As a** product manager,
**I want** to release a beta version to 10-15 early adopters after Epic 3,
**so that** I can validate production workflows and gather feedback for final polish in Epic 4.

#### Acceptance Criteria

1. **AC1:** Beta release package: PyPI-publishable package with proper versioning (`v0.2.0-beta`).
2. **AC2:** Comprehensive documentation: Installation guide, usage tutorial (all commands), configuration reference.
3. **AC3:** Beta testers recruited: 10-15 users (5 researchers, 5-7 LLM users, 1-2 compliance/legal professionals).
4. **AC4:** Beta testing protocol: Specific workflows to test (batch processing, validation mode, idempotency), feedback survey.
5. **AC5:** Beta feedback collection: Structured survey + open-ended feedback + usage analytics (if users opt-in).
6. **AC6:** Beta support channel: Dedicated communication channel (Slack/Discord) for beta testers.
7. **AC7:** Beta feedback review: Scheduled review session (end of week 10-11) to prioritize Epic 4 work and identify critical bugs.

---

### Story 3.9: NER & Title Handling Improvements

**As a** user processing French legal documents with professional titles and organizations,
**I want** accurate entity detection and complete title preservation throughout the pseudonymization process,
**so that** professional titles (Maître, Me) are not lost and organization patterns (Cabinet X) are correctly detected as ORG entities.

#### Acceptance Criteria

1. **AC1 (Bug #3):** Cabinet pattern detection:
   - Add pattern matching rules to detect "Cabinet [Name]" as ORGANIZATION entity
   - Patterns: "Cabinet [LastName]", "Cabinet [LastName] & Associés", "Cabinet [Name1] et [Name2]"
   - Use entity ruler or pattern matching before NER pipeline
   - Test case: "Cabinet Mercier & Associés" in `tests/test_corpus/interview_transcripts/interview_05.txt` should be detected as ORG (not PERSON)
2. **AC2 (Bug #4):** Professional title recognition:
   - Extend title recognition to include "Maître", "Me", "Me." (attorney titles)
   - Titles preserved in both final output AND validation UI display (related to Bug #2 in Story 3.2)
   - Example: "Maître Dubois" → "Maître [Pseudonym]" (title not stripped)
3. **AC3:** Unit tests for Cabinet patterns:
   - `test_cabinet_pattern_single_name()`: "Cabinet Mercier" → ORG
   - `test_cabinet_pattern_with_associates()`: "Cabinet Mercier & Associés" → ORG
   - `test_cabinet_pattern_multiple_names()`: "Cabinet Dupont et Martin" → ORG
   - `test_cabinet_pattern_not_person()`: Verify NOT detected as PERSON
4. **AC4:** Unit tests for professional titles:
   - `test_maitre_title_detection()`: "Maître Dubois" detected with title
   - `test_me_title_detection()`: "Me Dubois" detected with title
   - `test_maitre_title_preserved_in_output()`: Title appears in pseudonymized output
   - `test_me_title_preserved_in_output()`: Title appears in pseudonymized output
5. **AC5:** Integration tests:
   - Process `interview_05.txt` with "Cabinet Mercier & Associés" and verify ORG detection
   - Process document with "Maître"/"Me" titles and verify preservation
6. **AC6:** Regression testing:
   - All existing tests pass
   - No breaking changes to existing title detection (M., Mme, Dr, etc.)
   - No breaking changes to PERSON/LOCATION/ORG detection
7. **AC7:** Test corpus update:
   - Add or update test corpus documents with Cabinet patterns and professional titles

**Note:** Full story details available in [docs/stories/3.9.ner-title-handling-improvements.story.md](../stories/3.9.ner-title-handling-improvements.story.md)

---
