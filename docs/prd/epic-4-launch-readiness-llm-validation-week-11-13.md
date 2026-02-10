# Epic 4: Launch Readiness & LLM Validation (Week 11-13)

**Epic Goal:** Validate LLM utility preservation with real AI services, complete comprehensive documentation package, achieve all NFR quality thresholds, and prepare for confident early adopter release with full user support.

---

### Story 4.1: LLM Utility Preservation Testing (NFR10)

**As a** product manager,
**I want** rigorous validation that pseudonymized documents maintain usefulness for LLM analysis,
**so that** I can confidently market the primary value proposition to LLM users.

#### Acceptance Criteria

1. **AC1:** LLM API access configured: OpenAI API (ChatGPT) and Anthropic API (Claude) keys obtained, testing budget allocated ($50-100).
2. **AC2:** Test set prepared: 10 representative documents (5 interview transcripts, 5 business documents) per Technical Assumptions protocol.
3. **AC3:** Standardized prompts executed for both original and pseudonymized versions:
   - "Summarize the main themes in this document"
   - "Identify key relationships between individuals mentioned"
   - "Extract action items and decisions made"
4. **AC4:** Evaluation rubric applied: Thematic accuracy, relationship coherence, factual preservation, overall utility (1-5 scale).
5. **AC5:** Results analyzed: Average utility score ≥4.0/5.0 (80% threshold from NFR10).
6. **AC6:** Edge cases documented: Scenarios where pseudonymization degraded utility, recommendations for users.
7. **AC7:** Results documented: Methodology, findings, example comparisons (original vs pseudonymized LLM outputs).
8. **AC8:** **Go/No-Go Decision:** If <80% utility, determine if acceptable with caveats or requires changes before launch.

---

### Story 4.2: Comprehensive Cross-Platform Installation Validation (NFR3)

**As a** user,
**I want** reliable installation across all target platforms,
**so that** I can adopt the tool regardless of my operating system.

#### Acceptance Criteria

1. **AC1:** Comprehensive platform testing:
   - Windows: 10, 11 (64-bit)
   - macOS: Intel (Big Sur+), Apple Silicon (M1/M2)
   - Linux: Ubuntu 20.04, 22.04, 24.04; Debian 11, 12; Fedora 35+
2. **AC2:** Installation testing protocol: Fresh OS installs (VMs or containers), follow documentation, track success/failure and time.
3. **AC3:** Common failure scenarios tested: Missing Python, pip not found, model download failures, permission issues.
4. **AC4:** Installation success rate validated (NFR3): ≥85% across all platforms.
5. **AC5:** Installation time tracked: ≥80% of users complete first successful pseudonymization within 30 minutes (NFR14).
6. **AC6:** Troubleshooting guide enhanced: Document all discovered issues with platform-specific solutions.
7. **AC7:** Docker container validated: Works on all platforms as fallback for complex environments.
8. **AC8:** Beta tester installation data analyzed: Incorporate real-world installation experiences.

---

### Story 4.3: Complete Documentation Package (NFR13)

**As a** user,
**I want** comprehensive, well-organized documentation,
**so that** I can install, use, and troubleshoot the tool without developer support.

#### Acceptance Criteria

1. **AC1:** Installation Guide complete:
   - Platform-specific instructions (Windows/Mac/Linux)
   - Python/Poetry setup
   - Model download process
   - Docker installation alternative
   - Troubleshooting common issues
   - Video walkthrough (optional, nice-to-have)
2. **AC2:** Usage Tutorial complete:
   - Quick start (first pseudonymization in 5 minutes)
   - All CLI commands with examples
   - Common workflows (single document, batch, validation mode)
   - Configuration file examples
   - Tips and best practices
3. **AC3:** Methodology Description complete (academic citation):
   - Technical approach (NER library, algorithm description)
   - Validation procedures and quality controls
   - Limitations and edge cases
   - GDPR compliance mapping
   - Suitable for ethics board review
   - Proper academic formatting with citations
4. **AC4:** FAQ complete:
   - Common questions (accuracy expectations, supported formats, GDPR compliance)
   - Comparison with alternatives
   - Roadmap and Phase 2 GUI plans
5. **AC5:** Troubleshooting Guide complete:
   - Error message reference
   - Common failure scenarios with solutions
   - Platform-specific issues
   - When to file bug reports
6. **AC6:** API Reference (for developers):
   - Module documentation
   - Core classes and functions
   - Extension points for customization
7. **AC7:** Documentation hosted: GitHub Pages or Read the Docs with search functionality.
8. **AC8:** Documentation effectiveness validated: <20% of users require support beyond documentation (NFR14 target).
9. **AC9:** Python version support aligned across all sources (TD-004):
   - Verify spaCy 3.7+ wheel availability for Python 3.12 and 3.13
   - If verified: Add to CI/CD matrix (ci.yaml) and update pyproject.toml
   - If NOT verified: Tighten pyproject.toml to match actual tested versions
   - Align ALPHA-INSTALL.md, coding-standards.md, and all documentation to match
   - Note: Story 4.2 confirmed Python 3.12 works on Ubuntu 24.04 and Fedora 39

---

### Story 4.4: NER Accuracy Comprehensive Validation (NFR8-9)

**As a** quality assurance lead,
**I want** final validation of NER accuracy thresholds on expanded test corpus,
**so that** I can confidently report quality metrics to users and stakeholders.

#### Acceptance Criteria

1. **AC1:** Full 25-document test corpus processed with current implementation.
2. **AC2:** False negative rate calculated (NFR8): <10% of sensitive entities missed.
3. **AC3:** False positive rate calculated (NFR9): <15% of flagged entities are false positives.
4. **AC4:** Accuracy by entity type reported: PERSON, LOCATION, ORG precision/recall.
5. **AC5:** Edge case accuracy documented: Compound names, titles, abbreviations, ambiguous components.
6. **AC6:** Confidence score analysis: Correlation between NER confidence and actual accuracy (informational for future features).
7. **AC7:** Results compared to Epic 1 benchmarking: Validate no regression from full implementation complexity.
8. **AC8:** Quality report created: Accuracy metrics, known limitations, recommended validation mode use cases.
9. **AC9:** Monitoring baselines reviewed (MON-001, MON-003, MON-004):
   - MON-001: Validation UI performance — report validation time per unique entity and completion rate against targets (<10s/entity, ≥90% completion)
   - MON-003: LOCATION/ORG detection accuracy — report user-added entities by type against target (<10%)
   - MON-004: Context cycling UX discoverability — assess whether users discover X key cycling

---

### Story 4.5: Performance & Stability Validation (NFR1-2, NFR5-6)

**As a** quality assurance lead,
**I want** comprehensive performance and stability testing,
**so that** users experience reliable, fast processing.

#### Acceptance Criteria

1. **AC1:** Single-document performance (NFR1): 100 test runs with 2-5K word documents, validate <30s processing time on standard hardware.
2. **AC2:** Batch performance (NFR2): 10 test runs with 50-document batches, validate <30min processing time.
3. **AC3:** Startup time (NFR5): 50 test runs, validate <5 seconds CLI startup (cold start).
4. **AC4:** Crash/error rate (NFR6): 1000+ operations across all commands, validate <10% error rate.
5. **AC5:** Memory profiling: Verify no memory leaks during batch processing, stays within 8GB RAM constraint (NFR4).
6. **AC6:** Stress testing: Process 100-document batch, validate behavior (should complete or fail gracefully with clear errors).
7. **AC7:** Performance regression testing: Compare to Epic 2-3 baseline, ensure no degradation.
8. **AC8:** Performance report created: Metrics summary, hardware specifications used, optimization recommendations for Phase 2.
9. **AC9:** Monitoring baselines reviewed (MON-002, MON-005):
   - MON-002: Hybrid detection processing time — validate 0.07s average holds at scale, report p95/p99 against <30s target
   - MON-005: spaCy Python version compatibility — report current wheel availability for 3.12/3.13/3.14, feed findings to Story 4.3 AC9 (TD-004)

---

### Story 4.6: Beta Feedback Integration & Bug Fixes

**As a** product manager,
**I want** to address critical bugs and usability issues discovered during beta testing,
**so that** the launch version provides a polished user experience.

#### Key References

- **Alpha Feedback Summary:** [docs/qa/alpha-feedback-summary.md](../qa/alpha-feedback-summary.md) — consolidated tester feedback (7 items, 3 new)
- **Alpha Testing Protocol:** [docs/ALPHA-TESTING-PROTOCOL.md](../ALPHA-TESTING-PROTOCOL.md) — test scenarios and survey structure
- **Product Backlog:** [docs/BACKLOG.md](../BACKLOG.md) — TD-002, TD-004, FE-006, FE-010 feed into this story
- **NER Accuracy Report:** [docs/qa/ner-accuracy-report.md](../qa/ner-accuracy-report.md) — accuracy baselines relevant to FB-001 (entity variant grouping)
- **Performance Report:** [docs/qa/performance-stability-report.md](../qa/performance-stability-report.md) — startup time baseline relevant to FB-007 (slow --help)

#### Acceptance Criteria

1. **AC1:** Beta feedback analyzed: Categorize issues by severity (critical, high, medium, low) and type (bug, usability, feature request).
2. **AC2:** Critical bugs fixed: Anything causing data loss, crashes, incorrect pseudonymization, or security issues.
3. **AC3:** High-priority usability issues addressed: Confusing errors, unintuitive workflows, documentation gaps.
4. **AC4:** Medium issues triaged: Fix if time allows, defer to post-launch updates if necessary.
5. **AC5:** Low priority and feature requests: Document for Phase 2 consideration, provide clear roadmap communication.
6. **AC6:** Bug fix testing: Regression tests for all fixes, validate no new issues introduced.
7. **AC7:** Beta testers notified: Release notes with fixes, request final verification.
8. **AC8:** Launch readiness review: PM/Dev/QA sign-off that product is ready for public release.
9. **AC9:** Organization pseudonym library expanded (FE-006):
   - Expand neutral theme from 35 to 150-200 entries (80-100 companies, 40-50 agencies, 30-50 institutions)
   - Evaluate location library expansion needs (currently 80 entries)
   - Validate batch processing of 50+ documents no longer exhausts library
   - Source: Story 3.0 batch processing testing identified library exhaustion at 15+ documents
10. **AC10:** External user testing conducted (TD-002):
    - Recruit 2-3 external users (academic researchers, HR professionals, or compliance officers)
    - Provide test documents (20-50 entities each)
    - Measure: validation time, satisfaction (1-5 scale), completion rate
    - Target: ≥4/5 satisfaction, <5 min validation time for 50 entities
    - Document feedback and iterate on UX if needed
    - Source: Story 1.7 QA Gate (AC10), deferred from Epic 1 → Epic 2 → Epic 4

#### Completion Status: DONE (2026-02-09)

**Features delivered:**
- FB-001: Entity variant grouping in validation UI (Union-Find clustering with ambiguous surname isolation)
- FB-003: `--entity-types` CLI flag for selective entity type processing (process + batch commands)
- FB-007: Lazy imports for faster `--help` display (~55% import time reduction)
- AC9: Expanded neutral ORG library from 35 to 196 entries (101 companies, 50 agencies, 45 institutions)
- FB-006: Python 3.13 evaluation — deferred (blocked by thinc lacking wheels)

**Bugs found and fixed during testing:**
- Entity variant grouping bridging bug: Union-Find transitive bridging where titled surnames could incorrectly merge different people sharing the same family name
- `--entity-types` filter not applied in batch mode: `entity_type_filter` not forwarded to `process_document()` in 3 batch call sites

**Deferred items documented:**
- FB-002 (French docs → FE-010 v1.1), FB-004 (DOCX/PDF → v1.1), FB-005 (GUI → v2.0)
- FE-014: Extended coreference resolution (v1.1+)

**Testing:** 727 tests passing (686 unit + 41 batch), all quality gates pass (black, ruff, mypy)

**Sign-offs:** Dev (2026-02-09), QA PASS (2026-02-09), PM (2026-02-09)

---

### Story 4.6.1: Codebase Refactoring & Technical Debt Resolution

**As a** developer,
**I want** to resolve architectural violations, eliminate code duplication, and decompose overgrown methods before adding new features,
**so that** the codebase remains maintainable, testable, and extensible for launch and beyond.

#### Key References

- **Refactoring Plan:** [docs/refactoring-plan.md](../refactoring-plan.md) — 9 items (R1–R9) identified post-Story 4.6
- **Story File:** [docs/stories/4.6.1.codebase-refactoring-technical-debt.story.md](../stories/4.6.1.codebase-refactoring-technical-debt.story.md)

#### Acceptance Criteria

1. **AC1:** Zero functionality regression — full test suite passes after each refactoring item. Test count >= 1005, coverage >= 86%.
2. **AC2:** Layer violation resolved (R1) — `core/` has zero imports from `cli/`. Notification callback replaces direct `console.print()`.
3. **AC3:** French patterns centralized (R2) — single source of truth in `utils/french_patterns.py`. Zero duplicate definitions.
4. **AC4:** Divergent preposition bug fixed (R2b) — `entity_grouping.py` pattern aligned with canonical pattern; accuracy tests confirm no regression.
5. **AC5:** `process_document()` decomposed (R3) — no method exceeds 80 lines; each sub-method has unit tests; public API unchanged.
6. **AC6:** Encapsulation violations fixed (R4) — public methods replace all private attribute access across module boundaries.
7. **AC7:** Union-Find factored (R5) — single `UnionFind` class, generic clustering function.
8. **AC8:** CLI duplication factored (R6) — shared validators for entity types, theme, and DB init.
9. **AC9:** Dead code removed (R7) — `SimplePseudonymManager` deleted.
10. **AC10:** Exceptions centralized (R8) — all custom exceptions in `exceptions.py`, inheriting from `PseudonymizerError`.
11. **AC11:** Logging harmonized (R9) — all modules use structlog.
12. **AC12:** Each item delivered as atomic commit(s), independently revertible.

---

### Story 4.7: Final Launch Preparation

**As a** product manager,
**I want** all launch materials ready for public early adopter release,
**so that** users can discover, adopt, and successfully use the tool.

#### Acceptance Criteria

1. **AC1:** PyPI package published: `gdpr-pseudonymizer` v1.0.0 available via `pip install gdpr-pseudonymizer`.
2. **AC2:** GitHub repository public: README, documentation links, contributing guide, code of conduct, license (open-source, likely MIT or Apache 2.0).
3. **AC3:** Release announcement prepared: Blog post or article describing project, use cases, key features, getting started.
4. **AC4:** Community channels established: GitHub Discussions or forum for user questions, issue reporting.
5. **AC5:** Outreach plan executed: Post to relevant communities (Reddit r/datascience, r/privacy, academic mailing lists, LinkedIn).
6. **AC6:** Early adopter targets contacted: Direct outreach to identified potential users (researchers, enterprises).
7. **AC7:** Support process documented: How users get help, expected response times, escalation path.
8. **AC8:** Success metrics tracking setup: User count, downloads, GitHub stars, issue volume, community activity.

---

## Future Enhancements (Post-Launch Backlog)

These items were identified during Phase 1 development but deferred to post-launch releases (see [next-steps.md](next-steps.md) for the unified roadmap: v1.1 quick wins, v2.0 GUI, v3.0 NLP accuracy):

### FE-007: Gender-Aware Pseudonym Assignment for French Names

**Source:** Story 3.2 (user feedback during batch processing testing)

**Problem:**
Currently, pseudonym assignment does not preserve gender for PERSON entities when using French pseudonyms. The NER detectors (spaCy, Stanza) identify PERSON entities but do not provide gender classification. As a result:
- `PseudonymLibraryManager.get_pseudonym()` receives `gender=None`
- Falls back to using combined male+female+neutral names list
- A female name like "Marie Dupont" may receive a male pseudonym like "Jean Martin"

**Impact:**
- Reduces utility for LLM analysis where gender context matters
- May affect document coherence (pronouns, gendered references)
- Less natural pseudonymized output for French-language documents

**Potential Solutions:**
1. **LLM-based gender detection:** Use Claude/GPT to classify PERSON entities by gender before pseudonym assignment
2. **Name-based heuristic:** Build French name→gender lookup (though error-prone for unisex names)
3. **Context-based inference:** Analyze surrounding pronouns/adjectives for gender hints
4. **User validation extension:** Add gender selection to validation workflow

**Priority:** Medium (enhances quality but not blocking for core functionality)

**Target Release:** v1.1

**Effort Estimate:** Story-sized (2-3 days)

---

### FE-008: GDPR Right to Erasure - Selective Entity Deletion

**Source:** User feedback (PM session, 2026-02-05)

**Problem:**
Currently, there is no CLI command to delete specific entity mappings from the database. To fulfill GDPR Article 17 "Right to Erasure" requests, users must either:
- Delete the entire mapping database (destroys all mappings, not just the requested individual)
- Manually edit the SQLite database (requires technical expertise, bypasses encryption)

**GDPR Legal Basis:**
Deleting a mapping entry effectively converts **pseudonymization** into **anonymization**:
- Before deletion: "Leia Organa" → links to "Marie Dupont" (personal data under GDPR)
- After deletion: "Leia Organa" → no link exists (anonymous data, outside GDPR scope)

This is a legally valid approach for Article 17 compliance because:
- The **ability to re-identify** is what makes data "personal"
- Without the mapping, the pseudonym cannot be linked to an identifiable individual
- The document content remains intact, but the data subject is no longer identifiable

**User Story:**
```
As a data controller processing GDPR subject access requests,
I want to delete specific entity mappings from the database,
So that I can fulfill Article 17 erasure requests without destroying entire documents or affecting other individuals' data.
```

**Proposed CLI:**
```bash
# Delete by entity name
gdpr-pseudo delete-mapping "Marie Dupont" --db mappings.db

# Delete by entity ID (for programmatic use)
gdpr-pseudo delete-mapping --id <entity-uuid> --db mappings.db

# List entities (to find the one to delete)
gdpr-pseudo list-entities --db mappings.db --search "Dupont"
```

**Acceptance Criteria:**
1. **AC1:** `delete-mapping` command removes entity from `entities` table
2. **AC2:** Passphrase verification required before deletion (security)
3. **AC3:** Confirmation prompt: "This will permanently anonymize 'Marie Dupont'. Continue? [y/N]"
4. **AC4:** Audit log entry created in `operations` table with `operation_type='DESTROY'`
5. **AC5:** `list-entities` command shows all entities with search/filter capability
6. **AC6:** Documentation explains GDPR compliance implications

**Impact:**
- **High value** for enterprise/academic users with GDPR compliance requirements
- Enables selective erasure without data loss
- Differentiates tool from competitors (most anonymization tools lack this granularity)

**Potential Solutions:**
1. **Direct deletion:** Remove entity row from `entities` table
2. **Soft deletion:** Mark entity as `deleted=True` (preserves audit trail but complicates queries)
3. **Cryptographic erasure:** Delete encryption key for specific entity (requires per-entity keys - architectural change)

**Recommendation:** Direct deletion (Option 1) - simplest, meets GDPR requirements, audit trail via `operations` table.

**Priority:** High (significant compliance value, low implementation effort)

**Target Release:** v1.1

**Effort Estimate:** Story-sized (2-3 days)

---

### FE-009: Standalone Executable Distribution (.exe/.app)

**Source:** PM review during Story 4.2 planning (installation accessibility analysis)

**Problem:**
The v1.0 MVP requires Python installation and command-line comfort, which excludes non-technical users (HR professionals, legal teams, compliance officers) who would benefit from the tool but lack technical skills. While `pip install` (Story 4.7) simplifies installation for users with Python, it still requires:
- Python 3.9-3.11 pre-installed
- Command-line/terminal usage
- Understanding of virtual environments (recommended)

Docker was considered but is actually **harder** for non-technical Windows/Mac users (requires Docker Desktop, virtualization, container concepts).

**User Story:**
```
As a non-technical Windows or macOS user,
I want to download and run GDPR Pseudonymizer without installing Python or using the command line,
So that I can pseudonymize my documents with minimal technical barriers.
```

**Proposed Solution:**
Create standalone executables using PyInstaller or similar:
- **Windows:** `.exe` installer or portable executable
- **macOS:** `.app` bundle (drag to Applications)
- **Linux:** AppImage or .deb/.rpm packages (optional, Linux users typically more technical)

**Technical Considerations:**
1. **PyInstaller bundling:** Package Python runtime + all dependencies + spaCy model (~800MB-1GB total)
2. **Code signing:** Required for macOS Gatekeeper and Windows SmartScreen trust
3. **Auto-update mechanism:** Consider for future versions
4. **GUI wrapper:** Standalone exe should include Phase 2 GUI, not just CLI

**Relationship to Phase 2 GUI:**
This enhancement is **tightly coupled** with Phase 2 GUI development. The standalone executable should ship WITH the GUI — a CLI-only .exe provides limited value to non-technical users. Recommended approach:
1. Phase 2 GUI development
2. Bundle GUI + CLI into standalone executables
3. Distribute via GitHub Releases, website download

**Priority:** High (critical for Phase 2 broader adoption goal)

**Target Release:** v2.0

**Effort Estimate:** Epic-sized (depends on GUI complexity, 2-4 weeks including signing/distribution)

**Phase 2 Requirement:** This is a **must-have** for v2.0 launch, not a nice-to-have.

---
