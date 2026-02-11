# Epic 5: v1.1 — Quick Wins & GDPR Compliance

**Epic Goal:** Address deferred alpha/beta feedback, close the GDPR Article 17 compliance gap, improve pseudonym quality and NER accuracy, translate documentation for the French-speaking primary audience, and add PDF/DOCX format support — all without architectural changes to the v1.0 foundation.

**Target Release:** v1.1.0 (Q2 2026)
**Duration:** 6-7 weeks (ceiling: 8.5 weeks)
**Predecessor:** Epic 4 (v1.0 MVP launched 2026-02-09)

---

## Existing System Context

- **v1.0 MVP:** Fully operational CLI tool on PyPI (`pip install gdpr-pseudonymizer`)
- **Technology Stack:** Python 3.10-3.12, Poetry, spaCy `fr_core_news_lg`, Rich, Typer 0.9.x, SQLite + cryptography (Fernet), structlog
- **Architecture:** CLI → Core → NLP/Pseudonym/Data/Validation layers (see [architecture/](../architecture/))
- **Quality Baseline:** 1077+ tests, 86%+ coverage, all quality gates passing (black, ruff, mypy)
- **Known Limitations:** NER F1 ~40-50% (hybrid), mandatory validation mode, .txt/.md only, no gender-aware pseudonyms, no Article 17 erasure command

---

## Epic 5 Story List

| Story | Priority | Est. Duration | Backlog Source | Status |
|-------|----------|---------------|----------------|--------|
| 5.1: GDPR Right to Erasure | 🔴 **HIGH** | 2-3 days | FE-008 | ✅ DONE |
| 5.2: Gender-Aware Pseudonym Assignment | 🟡 **MEDIUM** | 2-3 days | FE-007 | 📋 PENDING |
| 5.3: NER Accuracy & Annotation Quality | 🟡 **MEDIUM** | 2-3 days | FE-011 + FE-012 | 📋 PENDING |
| 5.4: French Documentation Translation | 🟡 **MEDIUM** | 1-2 weeks | FE-010 / FB-002 | 📋 PENDING |
| 5.5: PDF/DOCX Input Format Support | 🟡 **MEDIUM** | 1-2 weeks | FB-004 | 📋 PENDING |
| 5.6: CLI Polish & Minor Enhancements | 🟢 **LOW** | 2-3 days | FE-001/002/003 + bugs | 📋 PENDING |
| 5.7: v1.1 Release Preparation | 🔴 **HIGH** | 1-2 days | — | 📋 PENDING |

**Total Estimated Duration:** 25-39 days (5-8 weeks, target: 6-7 weeks)

---

## Story 5.1: GDPR Right to Erasure — `delete-mapping` CLI Command (FE-008)

**As a** data controller processing GDPR subject access requests,
**I want** to delete specific entity mappings from the database,
**so that** I can fulfill Article 17 erasure requests without destroying entire documents or affecting other individuals' data.

**Priority:** 🔴 **HIGH** — GDPR compliance; high enterprise/academic value

### Context

Deleting a mapping entry converts **pseudonymization** into **anonymization**: without the mapping, the pseudonym cannot be linked to an identifiable individual, placing the data outside GDPR scope. This is a legally valid approach for Article 17 compliance.

### Acceptance Criteria

1. **AC1:** `delete-mapping` command implemented:
   - `gdpr-pseudo delete-mapping "Marie Dupont" --db mappings.db`
   - `gdpr-pseudo delete-mapping --id <entity-uuid> --db mappings.db`
   - Passphrase verification required before deletion
2. **AC2:** Confirmation prompt: "This will permanently anonymize 'Marie Dupont' (3 occurrences across 2 documents). This cannot be undone. Continue? [y/N]"
3. **AC3:** Audit log entry created in `operations` table with `operation_type='ERASURE'`, entity name, timestamp, requesting user rationale (optional `--reason` flag)
4. **AC4:** `list-entities` command implemented:
   - `gdpr-pseudo list-entities --db mappings.db --search "Dupont"`
   - Shows: entity name, type, pseudonym, first seen date, document count
5. **AC5:** Unit tests: deletion logic, passphrase verification, audit logging, search/filter
6. **AC6:** Integration test: create mapping → list entities → delete mapping → verify gone → verify audit log
7. **AC7:** Documentation: CLI reference updated, GDPR compliance section explaining Article 17 implications
8. **AC8:** No regression in existing `process`, `batch`, `destroy-table` commands

### Integration Points

- `gdpr_pseudonymizer/data/mapping_repository.py` — add `delete_entity()` and `list_entities()` methods
- `gdpr_pseudonymizer/cli/main.py` — add `delete-mapping` and `list-entities` commands (thin wrappers)
- `gdpr_pseudonymizer/cli/commands/` — new command module(s)
- Existing `operations` table schema supports `operation_type='ERASURE'` (no schema change needed)

### Estimated Effort: 2-3 days

---

## Story 5.2: Gender-Aware Pseudonym Assignment (FE-007)

**As a** user pseudonymizing French documents for LLM analysis,
**I want** female names to receive female pseudonyms and male names to receive male pseudonyms,
**so that** pseudonymized documents maintain gender coherence and LLM utility.

**Priority:** 🟡 **MEDIUM** — Improves LLM utility score and document readability

### Context

Currently `PseudonymLibraryManager.get_pseudonym()` receives `gender=None` (spaCy doesn't provide gender) and falls back to a combined male+female+neutral list. A female name like "Marie Dupont" may receive "Jean Martin". The pseudonym libraries already have gender-tagged first names — only the detection/assignment logic is missing.

### Acceptance Criteria

1. **AC1:** French name gender detection implemented using heuristic lookup:
   - Build French first_name → gender mapping from existing pseudonym library data + INSEE public data
   - **Pre-requisite:** Verify INSEE dataset license compatibility with project license (MIT). If restrictive, build lookup purely from existing pseudonym library data.
   - Coverage target: ≥90% of common French first names
   - Fallback: `gender=None` uses combined list (current behavior preserved)
2. **AC2:** Gender detection integrated into pseudonym assignment pipeline:
   - After entity detection, before pseudonym assignment: lookup detected first name → assign gender
   - Gender stored in `entities` table `gender` column (already exists in schema)
3. **AC3:** Pseudonym selection respects gender:
   - Female entity → female pseudonym first name
   - Male entity → male pseudonym first name
   - Unknown gender → random from combined list (no regression)
4. **AC4:** Compound names handled: "Jean-Pierre" → male, "Marie-Claire" → female (first component determines gender)
5. **AC5:** Unit tests: gender lookup, assignment logic, compound names, unknown names, edge cases
6. **AC6:** Integration test: process document → verify gender-matched pseudonyms
7. **AC7:** No regression: existing test suite passes, existing mappings remain valid
8. **AC8:** Documentation: methodology page updated to describe gender-aware assignment

### Integration Points

- `gdpr_pseudonymizer/pseudonym/` — gender lookup module (new file or extend `library_manager.py`)
- `gdpr_pseudonymizer/core/processor.py` — integrate gender detection into pipeline
- `data/` — gender lookup data file (JSON, derived from existing libraries + INSEE)
- Existing `entities` table `gender` column — already in schema, currently unused

### Estimated Effort: 2-3 days

---

## Story 5.3: NER Accuracy & Annotation Quality (FE-011 + FE-012)

**As a** user validating detected entities,
**I want** improved detection accuracy for PERSON, LOCATION, and ORG entities,
**so that** I spend less time manually adding missed entities during validation.

**Priority:** 🟡 **MEDIUM** — Directly reduces validation burden

### Context

Story 4.4 accuracy validation identified specific gaps:
- Last, First name format: 0% recall (no regex pattern)
- ORG entities: 66% false negative rate
- LOCATION entities: 37% false negative rate
- Ground-truth annotations have quality issues inflating false negative metrics

This story combines FE-011 (regex expansion) and FE-012 (annotation cleanup) since they're tightly coupled — accuracy improvements can't be reliably measured without clean ground truth.

### Acceptance Criteria

**Regex Pattern Expansion (FE-011):**
1. **AC1:** `LastName, FirstName` regex pattern added to `regex_matcher.py` (e.g., "Dubois, Jean-Marc")
2. **AC2:** ORG suffix patterns expanded: Association, Fondation, Institut, Groupe, Consortium, Federation + common abbreviations (15+ suffixes total)
3. **AC3:** French geography dictionary added: top 100 cities, 13 regions, 101 departments — stored in `data/` as JSON
4. **AC4:** Accuracy re-run shows measurable improvement: LOCATION FN <25% (from 37%), ORG FN <50% (from 66%)
5. **AC5:** No regression in PERSON detection accuracy

**Annotation Quality Cleanup (FE-012):**
6. **AC6:** `tests/test_corpus/annotations/README.md` entity count corrected to match actual count
7. **AC7:** `board_minutes.json` annotations cleaned: fix entities spanning newlines, ORG/PERSON mislabeling, garbage entries removed
8. **AC8:** Consistent annotation policy for titles documented (include or exclude — pick one and apply)
9. **AC9:** Clean accuracy baseline established and documented

**Quality:**
10. **AC10:** Unit tests for new regex patterns
11. **AC11:** Full accuracy benchmark re-run with clean corpus, results documented in updated `ner-accuracy-report.md`

### Integration Points

- `gdpr_pseudonymizer/nlp/regex_matcher.py` — new patterns
- `data/` — French geography dictionary (new JSON file)
- `tests/test_corpus/annotations/` — cleaned annotations
- `docs/qa/ner-accuracy-report.md` — updated report

### Estimated Effort: 2-3 days

---

## Story 5.4: French Documentation Translation (FE-010)

**As a** French-speaking researcher or compliance officer,
**I want** user-facing documentation available in French,
**so that** I can install, use, and troubleshoot the tool without language barriers.

**Priority:** 🟡 **MEDIUM** — Primary audience is French-speaking; #1 alpha feedback request (FB-002)

### Context

The primary target audience (French academic researchers, HR professionals, compliance officers) speaks French. All documentation is currently in English. Translation lowers the adoption barrier before the v2.0 GUI and demonstrates commitment to the French-speaking community.

### Acceptance Criteria

1. **AC1:** French README available (`README.fr.md`) with language toggle link at top of both EN/FR versions
2. **AC2:** French installation guide available (`docs/installation.fr.md`)
3. **AC3:** French quick start / user guide available (`docs/tutorial.fr.md`)
4. **AC4:** French FAQ and troubleshooting available (`docs/faq.fr.md`, `docs/troubleshooting.fr.md`)
5. **AC5:** MkDocs site updated with FR/EN navigation toggle
6. **AC6:** Native French speaker review for quality (user or external reviewer)
7. **AC7:** No English-only jargon left untranslated in user-facing content

**Out of Scope (deferred to v2.0 i18n):**
- CLI `--help` text translation (requires i18n framework; risk of Typer 0.9.x/click compatibility issues)
- GUI interface translation
- i18n framework architecture
- Developer-facing docs (architecture, PRD, stories)
- CLI error message translation

### Integration Points

- `docs/` — new `.fr.md` files
- `mkdocs.yml` — i18n plugin or manual nav structure
- `README.fr.md` in project root

### Estimated Effort: 1-2 weeks

---

## Story 5.5: PDF/DOCX Input Format Support (FB-004)

**As a** user with documents in PDF or DOCX format,
**I want** to pseudonymize these documents directly without manual conversion to .txt,
**so that** I can process my real-world documents without extra steps.

**Priority:** 🟡 **MEDIUM** — Second most requested alpha feature (FB-004)

### Context

v1.0 only supports `.txt` and `.md` input formats. Real-world users have documents in PDF (academic papers, legal documents) and DOCX (HR files, interview transcripts). Manual conversion loses formatting and creates friction.

### Acceptance Criteria

1. **AC1:** PDF text extraction implemented using `pdfplumber` or `PyMuPDF`:
   - Extract text content from PDF pages
   - Handle multi-page documents
   - Graceful handling of scanned PDFs (warn: "This PDF appears to be scanned/image-based. Text extraction may be incomplete.")
2. **AC2:** DOCX text extraction implemented using `python-docx`:
   - Extract paragraph text from DOCX
   - Handle headers, footers, tables (best-effort text extraction)
3. **AC3:** `process` and `batch` commands accept `.pdf` and `.docx` files:
   - Auto-detect format from file extension
   - Extract text → run existing NER + validation + pseudonymization pipeline
4. **AC4:** Output format options:
   - Default: pseudonymized `.txt` output (extracted text with replacements)
   - Future consideration: preserve original format (`.pdf` → `.pdf`, `.docx` → `.docx`) — document as v1.2+ enhancement if complex
5. **AC5:** New dependencies added as **optional extras** in `pyproject.toml`: `pip install gdpr-pseudonymizer[pdf]` and `pip install gdpr-pseudonymizer[docx]` (or combined `[pdf,docx]`). Base install remains lightweight; clear error message if user tries to process PDF/DOCX without the extra installed.
6. **AC6:** Unit tests: PDF extraction, DOCX extraction, format detection, error handling (corrupt files, password-protected PDFs)
7. **AC7:** Integration test: process PDF and DOCX documents end-to-end
8. **AC8:** Documentation updated: supported formats section, installation notes for new dependencies
9. **AC9:** No regression in existing `.txt`/`.md` processing

### Integration Points

- `gdpr_pseudonymizer/utils/` — new `file_reader.py` or extend existing file handling
- `gdpr_pseudonymizer/core/processor.py` — format detection and extraction dispatch
- `pyproject.toml` — new dependencies
- Existing NER/validation/pseudonymization pipeline — unchanged (receives extracted text)

### Estimated Effort: 1-2 weeks

---

## Story 5.6: CLI Polish & Minor Enhancements

**As a** user of the CLI tool,
**I want** small UX improvements and bug fixes,
**so that** the tool feels polished and reliable.

**Priority:** 🟢 **LOW** — Bundle of small improvements + 10% bug fix allowance

### Context

This story bundles minor backlog items that individually don't warrant a story but collectively improve the user experience. Also serves as the bug fix allowance for any issues reported by v1.0 users between now and v1.1 release.

### Acceptance Criteria

1. **AC1 (FE-001):** Visual indicator for context cycling added to validation UI:
   - Display `Context (2/5): ○ ● ○ ○ ○  [Press X to cycle]` during entity review
   - Improves discoverability of X key
2. **AC2 (FE-002):** Batch operations visual feedback:
   - After Shift+A/R, display confirmation: `✓ Accepted all 15 PERSON entities`
   - Brief summary of affected entities before continuing
3. **AC3 (FE-003):** Performance regression tests added:
   - `pytest-benchmark` tests for hybrid detection pipeline (<30s per document)
   - Integrated into CI/CD pipeline
4. **AC4:** Bug fixes for any critical/high issues reported by v1.0 users (10% scope allowance, ~2-3 days)
5. **AC5:** All existing tests pass, no regression
6. **AC6:** Updated test count and coverage metrics documented

### Integration Points

- `gdpr_pseudonymizer/validation/ui.py` — context indicator, batch feedback
- `tests/` — benchmark tests
- `.github/workflows/ci.yaml` — benchmark integration (optional)

### Estimated Effort: 2-3 days

---

## Story 5.7: v1.1 Release Preparation

**As a** product manager,
**I want** v1.1.0 published to PyPI with updated documentation and release notes,
**so that** users can upgrade and benefit from the new features.

**Priority:** 🔴 **HIGH** — Final story, gates the release

### Acceptance Criteria

1. **AC1:** Version bumped to `1.1.0` in `pyproject.toml`
2. **AC2:** CHANGELOG.md updated with v1.1.0 section (all new features, improvements, bug fixes)
3. **AC3:** README updated: new features highlighted (Article 17 erasure, gender-aware pseudonyms, PDF/DOCX, French docs)
4. **AC4:** Full regression suite passing: black, ruff, mypy, pytest (all tests)
5. **AC5:** `poetry build` succeeds, package builds cleanly
6. **AC6:** MkDocs documentation rebuilt and deployed
7. **AC7:** Git tag `v1.1.0` triggers `release.yaml` → PyPI publish
8. **AC8:** Release announcement drafted for v1.0 users (notify via GitHub Discussions + README)
9. **AC9:** v1.0 users notified of upgrade path: `pip install --upgrade gdpr-pseudonymizer`

### Estimated Effort: 1-2 days

---

## Execution Sequence

**Recommended Story Order:**

```
Story 5.1 (Right to Erasure)     ─── Week 1 ───┐
Story 5.2 (Gender Pseudonyms)    ─── Week 1-2 ──┤ Core feature work
Story 5.3 (NER Accuracy)         ─── Week 2 ────┘
Story 5.5 (PDF/DOCX)             ─── Week 3-4 ── Format support
Story 5.4 (French Docs)          ─── Week 4-5 ── Documentation (can parallel with 5.5)
Story 5.6 (CLI Polish + Bugs)    ─── Week 5-6 ── Polish (absorbs any bugs found)
Story 5.7 (Release Prep)         ─── Week 6-7 ── Release gate
```

**Parallelization Opportunities:**
- Stories 5.1, 5.2, 5.3 are independent — can run in parallel if team capacity allows
- Story 5.4 (docs) can overlap with 5.5 (PDF/DOCX) — different code areas
- Story 5.6 runs last to absorb accumulated bug fixes

**Critical Path:** 5.1 → 5.5 → 5.7 (longest sequential chain ~4-5 weeks)

---

## Compatibility Requirements

- [x] Existing CLI commands (`process`, `batch`, `config`, `destroy-table`) remain unchanged
- [x] Existing mapping database schema unchanged (no migration needed)
- [x] Existing pseudonym libraries unchanged (gender data added alongside, not replacing)
- [x] Performance impact minimal (new features are additive, not modifying hot paths)
- [x] Existing `.txt`/`.md` workflows unaffected by PDF/DOCX addition

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PDF text extraction quality varies (scanned PDFs) | MEDIUM | LOW | Warn users about image-based PDFs; document limitation |
| French translation quality | LOW | MEDIUM | Native speaker review (AC7 in Story 5.4) |
| Gender detection accuracy for rare/unisex names | LOW | LOW | Graceful fallback to combined list; no worse than v1.0 |
| Story 5.5 (PDF/DOCX) takes longer than estimated | MEDIUM | LOW | Output as .txt only (defer format preservation to v1.2) |
| Accumulated bug reports consume Story 5.6 budget | LOW | LOW | Scope allowance is 10%; defer low-priority bugs to v1.2 |
| INSEE gender data license incompatible with MIT | LOW | MEDIUM | Fall back to existing pseudonym library data only (Story 5.2) |
| Optional extras increase installation support burden | LOW | LOW | Clear error messages guide users to install extras; document in FAQ |

**Rollback Plan:** Each story is independently deployable and revertible. If any story introduces regressions, revert its commits without affecting other stories. v1.0.x hotfix releases remain possible throughout.

---

## Explicitly Deferred (v1.1+ / v2.0)

| Item | ID | Reason | Target |
|------|----|--------|--------|
| Confidence score calibration | FE-013 | HIGH effort (1-2 weeks), depends on FE-011 | v1.2+ |
| Extended coreference resolution | FE-014 | HIGH effort, research-level complexity | v1.2+ |
| Standalone executables (.exe/.app) | FE-009 | Coupled with GUI development | v2.0 |
| Desktop GUI | FB-005 | Epic-sized, different user segment | v2.0 |
| Python 3.13 support | FB-006 | Blocked by thinc wheels | Monitoring (MON-005) |
| Fine-tuned French NER model | — | Requires curated training data from v1.x users | v3.0 |
| CLI `--help` i18n (French) | FE-010b | Requires i18n framework; Typer/click compat risk | v2.0 |
| Output format preservation (PDF→PDF) | — | Complex; v1.1 outputs .txt from PDF/DOCX input | v1.2 |

---

## Open PM Decisions (Not Blocking)

1. **Roadmap Transparency:** Publish v1.0 → v1.1 → v2.0 evolution roadmap publicly? Risk: users may wait for v1.1 instead of adopting v1.0.
2. **Fine-Tuning Budget:** Allocate NER fine-tuning budget now or wait for user feedback volume from v1.0/v1.1?

---

## Definition of Done

- [ ] All 7 stories completed with acceptance criteria met
- [ ] Existing v1.0 functionality verified (full test suite passing)
- [ ] All quality gates green: black, ruff, mypy, pytest
- [ ] Test count ≥ v1.0 baseline (1077+), coverage ≥ 86%
- [ ] No regression in existing `.txt`/`.md` processing workflows
- [ ] Documentation updated (EN + FR) for all new features
- [ ] v1.1.0 published on PyPI
- [ ] CHANGELOG and README reflect all v1.1 changes

---

## Success Criteria

Epic 5 is successful if:

1. `delete-mapping` command operational for GDPR Article 17 compliance
2. Gender-matched pseudonyms for ≥90% of common French names
3. NER accuracy measurably improved (LOCATION FN <25%, ORG FN <50%)
4. French documentation available for primary user workflows
5. PDF and DOCX documents processable via CLI
6. No critical bugs open at release time
7. v1.1.0 published on PyPI and documented

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing system running Python 3.10-3.12, Poetry, spaCy, Typer 0.9.x, SQLite + cryptography, Rich
- Integration points: CLI commands (Typer wrappers), NLP pipeline (regex_matcher.py), pseudonym assignment (library_manager.py), data layer (mapping_repository.py), validation UI (ui.py)
- Existing patterns to follow: thin CLI wrappers with lazy imports, command logic in `cli/commands/`, data files in `data/`, tests mirror source structure
- Critical compatibility requirements: Typer 0.9.x + click <8.2.0 pin, standard `--flag/--no-flag` patterns only, no `Optional[bool]` with flag pairs
- Each story must include verification that existing functionality remains intact

The epic should maintain system integrity while delivering GDPR compliance, accuracy improvements, format support, and French documentation."

---

**Document Status:** ✅ PM APPROVED
**Created:** 2026-02-11
**Approved:** 2026-02-11
**Author:** Sarah (Product Owner)
**PM Reviewer:** John (Product Manager)
**Next Action:** Story creation (SM/Dev agent)
