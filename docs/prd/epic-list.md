# Epic List

### Epic 0: Pre-Sprint Preparation (Week -1 to 0)

**Goal:** Prepare test data and development environment foundation to enable Epic 1 to start without blockers, validating basic NLP library viability before full sprint work begins.

---

### Epic 1: Foundation & NLP Validation (Week 1-4)

**Goal:** Select and validate NLP library against accuracy criteria, establish CI/CD infrastructure, and deliver a working "walking skeleton" CLI command that demonstrates basic end-to-end pseudonymization capability for early validation.

---

### Epic 2: Core Pseudonymization Engine (Week 4-8)

**Goal:** Implement production-quality compositional pseudonymization logic with encrypted mapping tables and audit trails, enabling consistent entity replacement across documents while validating architectural scalability for batch processing.

---

### Epic 3: CLI Polish & Batch Processing (Week 11-13)

**Goal:** Complete the pseudonymization engine with LOCATION/ORG support, deliver production-ready batch processing CLI, and provide comprehensive user documentation for v1.0 MVP launch.

---

### Epic 4: Launch Readiness & LLM Validation (Week 14)

**Goal:** Validate LLM utility preservation with real AI services, complete comprehensive documentation package, achieve all NFR quality thresholds, and prepare for confident v1.0 MVP launch with full user support.

---

### Epic 5: v1.1 — Quick Wins & GDPR Compliance ✅ COMPLETE (2026-02-15)

**Goal:** Address deferred alpha/beta feedback, close the GDPR Article 17 compliance gap, improve pseudonym quality and NER accuracy, translate documentation for the French-speaking primary audience, and add PDF/DOCX format support.

---

### Epic 6: v2.0 — Desktop GUI & Broader Accessibility ✅ COMPLETE (2026-03-04)

**Goal:** Expand beyond CLI-only users to the primary growth market — non-technical professionals who need GDPR-compliant pseudonymization but lack command-line comfort — by delivering a cross-platform desktop GUI, standalone executables, French-first internationalization, and WCAG AA accessibility.

---

### Epic 7: v2.1 — GUI Polish, Excel Support & NER Accuracy

**Goal:** Refine the v2.0 desktop GUI based on real user feedback, add Excel/CSV format support for the HR/compliance audience, introduce a neutral pseudonym theme, and improve NER accuracy through regex pattern expansion.

---

### Epic 8: v2.4 — Output Format Preservation & Auto-Update

**Goal:** Enable pseudonymized documents to retain their original format (PDF->PDF, DOCX->DOCX) instead of flattening to plaintext, and implement an auto-update mechanism for standalone executable users.

---

### Epic 9: v3.0 — NLP Accuracy & Intelligence

**Goal:** Transform the pseudonymization engine from "good enough with mandatory validation" to "trustworthy with optional validation" (PARKED — requires Lionel's decision) by fine-tuning a French NER model to 70-85% F1, implementing confidence-based auto-validation (PARKED — requires Lionel's decision), and adding coreference resolution.

> **Sequencing:** Epic 10 precedes Epic 9. Epic 9 starts from Epic 10's merged close-out baseline. The optional no-validation mode, training on users' validation data and crowdsourced annotation are PARKED pending Lionel's decision (see Epic 9 file).

---

### Epic 10: v2.3 — Detection Precision Quick Wins (re-opened for release blockers, Lionel 2026-10-16: Stories 10.12 to 10.17; 10.1 to 10.11 complete 2026-10-15)

**Goal:** Raise detection precision and benchmark trustworthiness with local, deterministic changes (benchmark repair + held-out set, same-type overlap dedup, ORG role filter, LOCATION noise and name-boundary rules, salutation and org-plus-country handling), without lowering recall. Baseline: F1 58.53% at commit `fceef65` (CI run 37013929807). Sequenced before Epic 9; no release inside the epic.

---

**Timeline: Epics 0-4: 14 weeks (v1.0 MVP). Epic 5: 6-7 weeks (v1.1). Epic 6: 10-14 weeks (v2.0). Epic 7: 4-6 weeks (v2.1). Epic 8: 5-7 weeks (v2.4). Epic 9: 8-12 weeks (v3.0). Epic 10: 13-19 weeks + 10.6 in parallel (v2.3 candidate, runs before Epic 9)**

---

### Epic Definitions of Done

**Epic 0 DoD:**
- ✓ Initial test corpus created (10 French documents with ground truth annotations)
- ✓ Development environment configured (Python 3.9+, Poetry, pytest)
- ✓ Quick spaCy benchmark completed (initial accuracy estimate)
- ✓ Ready to begin Epic 1 Sprint 1 without blockers

**Epic 1 DoD:**
- ✓ NLP library selected (spaCy or Stanza) with ≥85% accuracy validated on 20-30 document test corpus
- ✓ CI/CD pipeline operational (GitHub Actions testing on 2+ platforms)
- ✓ Walking skeleton: Basic `process` command runs end-to-end (naive pseudonymization)
- ✓ Git workflow and code quality tooling established
- ✓ Can demonstrate basic pseudonymization concept to alpha testers

**Epic 2 DoD:**
- ✓ Compositional pseudonymization logic (FR4-5) passes comprehensive unit tests
- ✓ Compound name handling (FR20) implemented and tested
- ✓ Encrypted mapping table operational with Python-native encryption
- ✓ Audit logging (FR12) captures all required fields
- ✓ Single-document performance meets NFR1 (<30s for 2-5K words)
- ✓ Architectural validation: Basic batch processing proves design scales
- ✓ **Alpha Release:** 3-5 friendly users provide initial feedback (after week 6)

**Epic 3 DoD:**
- ✓ LOCATION and ORGANIZATION pseudonym libraries complete for all 3 themes (50+ locations, 30+ orgs per theme)
- ✓ Batch processing CLI functional with process-based parallelism (NFR2: <30min for 50 docs)
- ✓ Progress reporting with real-time indicators for large batches
- ✓ Configuration file support (.gdpr-pseudo.yaml) operational
- ✓ CLI UX polish complete (error messages, help text)
- ✓ User documentation complete (installation guide, tutorial, CLI reference)
- ✓ Performance regression tests (pytest-benchmark) integrated
- ✓ **Post-Alpha Improvements:** Alpha tester feedback integrated into Story 3.0 implementation

**Epic 4 DoD:**
- ✓ LLM utility preservation validated: ≥80% utility score (NFR10) with real ChatGPT/Claude API testing
- ✓ Cross-platform installation achieves ≥85% success rate (NFR3) across all target platforms
- ✓ Comprehensive documentation complete (NFR13): installation guide, tutorial, methodology, FAQ
- ✓ Error message catalog finalized with style guide compliance (NFR7)
- ✓ NER accuracy thresholds validated (NFR8: <10% false negatives, NFR9: <15% false positives)
- ✓ All bug fixes from beta testing applied (10% scope allowance)
- ✓ Ready for public early adopter release with full support capability

---

### Release Strategy

- **Week 10 (Post-Epic 2):** Alpha release v0.1.0 to 3-5 friendly users for core functionality feedback ✅ COMPLETE (2026-01-30)
- **Week 13 (Post-Epic 3):** Beta release v0.2.0 to 10-15 early adopters for production workflow validation ✅ COMPLETE
- **Week 14+ (Post-Epic 4):** Public v1.0 MVP release to broader early adopter community ✅ COMPLETE (2026-02-09, PyPI published)
- **Q2 2026 (Epic 5):** v1.1 release — GDPR erasure, gender-aware pseudonyms, PDF/DOCX, French docs, NER accuracy improvements ✅ COMPLETE (2026-02-15)
- **Epic 6:** v2.0 release — Desktop GUI, standalone executables, French-first i18n, WCAG AA accessibility ✅ COMPLETE (2026-03-04)
- **Epic 7:** v2.1 release — GUI polish, Excel/CSV support, neutral theme, NER regex expansion
- **Epic 8:** v2.4 release — Output format preservation (DOCX->DOCX, PDF->PDF), auto-update
- **Epic 9:** v3.0 release — Fine-tuned NER model, confidence calibration, coreference resolution, optional validation
- **Epic 10:** v2.3 candidate — detection precision quick wins. No release is part of the epic; v2.3.0 ships only on Lionel's explicit go

---

**Epic 5 DoD:**
- ✓ GDPR Article 17 `delete-mapping` command operational
- ✓ Gender-matched pseudonyms for ≥90% of common French first names
- ✓ NER accuracy improved: LOCATION FN <25%, ORG FN <50%
- ✓ French documentation available for primary user workflows
- ✓ PDF and DOCX input format support functional
- ✓ CLI polish and minor enhancements applied
- ✓ v1.1.0 published on PyPI

**Epic 6 DoD:**
- ✓ Desktop GUI functional on Windows 10/11 and macOS 13+
- ✓ Standalone executables (.exe, .app) tested on target platforms
- ✓ Visual entity validation interface operational
- ✓ French GUI translation complete and reviewed
- ✓ WCAG AA accessibility checklist passed
- ✓ CLI functionality fully preserved (no regressions)
- ✓ v2.0.0 published on PyPI and standalone downloads on GitHub Releases

**Epic 7 DoD:**
- [x] Validate-once-per-entity operational (FE-020)
- [x] All keyboard shortcuts documented in Help menu (FE-018)
- [x] Hide-confirmed toggle functional (FE-019)
- [x] Last-used database persisted across sessions (FE-017)
- [x] Neutral pseudonym theme (PER-001, LOC-001, ORG-001) functional (FE-016)
- [x] Excel (.xlsx) and CSV format support operational (FE-015)
- [ ] NER regex patterns expanded, accuracy improved (FE-011)
- [ ] Ground-truth corpus cleaned (FE-012)
- [ ] v2.1.0 published on PyPI and GitHub Releases

**Epic 8 DoD:**
- [ ] DOCX input produces pseudonymized DOCX output with formatting preserved
- [ ] PDF input produces pseudonymized PDF output (overlay approach)
- [ ] Auto-update notification functional in standalone executables
- [ ] v2.4.0 published on PyPI and GitHub Releases

**Epic 9 DoD:**
- [ ] Fine-tuned French NER model achieves F1 >= 70% on held-out test set
- [ ] All entities receive calibrated confidence scores (0.0-1.0)
- [ ] Coreference resolution links pronouns to antecedent entities
- [ ] Optional `--no-validate` mode functional with guard rails — **PARKED, requires Lionel's decision**
- [ ] v3.0.0 published on PyPI and GitHub Releases
- [ ] Fine-tuned model package available for installation

**Epic 10 DoD:**
- [x] Annotation guidelines approved by Lionel and applied to the whole corpus; held-out set (≥5 documents) scored separately
- [x] Same-type overlap dedup and ORG role filter shipped (10.2)
- [x] Line-break span boundaries and run-on regex shapes fixed (10.3a, split from 10.3, Lionel, 2026-10-06)
- [x] LOCATION noise filters and name-boundary rules shipped (10.3b, split from 10.3, Lionel, 2026-10-06)
- [x] Type-aware exact match in the merge shipped (10.3c, added at 10.3a STOP R, Lionel, 2026-10-06)
- [x] Salutation splitting / bare first names and org-plus-country merge shipped (10.4)
- [x] DB init no longer deletes a database another process created (10.5, data-layer hardening, Lionel, 2026-10-07)
- [x] Mapping lookup is type-aware: the same text under another type gets its own pseudonym and row; continuity for existing databases as Lionel decides at the story's STOP (10.7, data layer, added by Lionel at 10.3c STOP R, 2026-10-09)
- [x] Desktop app keys candidates by type: one span found with two types gives two candidates, rejecting one keeps the other, and no confirmed occurrence is dropped (10.8, 10.3c regression, before any release, added by Lionel, 2026-10-13)
- [x] Desktop app edit applies to every occurrence of the name and type, as in the CLI; no other occurrence is left in clear (10.9, before the next release, added by Lionel, 2026-10-13)
- [x] Desktop batch review keeps each document's own result and decisions, and an action on a hand-added row acts on that row only (10.10: PRE-001 to PRE-003, before any release, added by Lionel, 2026-10-14)
- [x] A custom pseudonym ("Changer le pseudonyme", CLI [C]) is used in the written file and stored for later documents (10.11, after 10.7, before any release; added by Lionel, 2026-10-14)
- [ ] The erasure log keeps no erased name: `delete-mapping` records date, row id, type and reason only; names already in the log are removed and the file compacted once on the first 2.3.0 open; every deletion overwrites the deleted data (10.12, release blocker B1, Lionel 2026-10-16)
- [ ] A warning before writing a document with names still to review, in desktop batch review and single-document validation, and a line in the CLI's final summary, with the texts Lionel approved (10.13, release blocker B2, Lionel 2026-10-16)
- [ ] Desktop app: opening a document or folder during a batch is refused with a message that leads back to the batch, every batch hand-off is tied to its run, and finalization works on copies of the review (10.14, Codex release review #1 and #4, Lionel 2026-10-16)
- [ ] CLI: on Excel and CSV files, a name corrected with [E] or retyped with [T] is replaced in its cell, and a name added with [A] is replaced at every place of that name and type (10.15, Codex release review #2 and the PO's finding, Lionel 2026-10-16)
- [ ] Custom pseudonyms: a name of the review counts whatever its capitals, the generation guard keeps roles and spellings, and the reach follows the current name (10.16, Codex release review #6, #7 and #8, Lionel 2026-10-16)
- [ ] Desktop app: a name added by hand is replaced at every place of that name and type (10.17, the PO's finding, Lionel 2026-10-16)
- [x] Final-exam set (10.6): 30 documents frozen and annotated by two models before 10.4 merged, adjudicated by Lionel after 10.4 merged, then committed as plain files (documents' sha256 checked against the freeze record; no encryption, Lionel, 2026-10-09) and scored exactly once at close-out; accuracy output carries 95% bootstrap ranges; Lionel picks the public figure among main, held-out and final exam
- [x] Every story closed with a cited CI accuracy run (G1), independent QA check (G2), no unapproved recall drop (G3), held-out numbers (G5, 10.2, 10.3a, 10.3b, 10.3c, 10.4)
- [x] Close-out baseline recorded as Epic 9's starting point, with the `[Overall]`/`[PERSON]`/`[LOCATION]`/`[ORG]`/`[HELD-OUT …]` lines pasted into the QA report (`accuracy-results` artifacts are kept 30 days, `.github/workflows/accuracy.yaml:83`), not just the run ID; no release cut without Lionel's go

---

### NFR Validation Distribution (Incremental Quality Gates)

| NFR | Epic 1 | Epic 2 | Epic 3 | Epic 4 |
|-----|--------|--------|--------|--------|
| NFR1 (Single-doc performance) | - | ✓ Validate | ✓ Maintain | ✓ Verify |
| NFR2 (Batch performance) | - | Architectural spike | ✓ Validate | ✓ Verify |
| NFR3 (Installation success) | Basic setup | - | Sample (2-3 platforms) | ✓ Comprehensive |
| NFR5 (Startup time) | - | ✓ Validate | ✓ Maintain | ✓ Verify |
| NFR6 (Crash rate) | - | Unit test coverage | ✓ Integration testing | ✓ Comprehensive |
| NFR7 (Error messages) | Basic errors | Core errors | CLI errors | ✓ Complete catalog |
| NFR8-9 (Accuracy) | ✓ Benchmark | ✓ Validate | ✓ Maintain | ✓ Comprehensive |
| NFR10 (LLM utility) | - | - | - | ✓ Validate |
| NFR13 (Documentation) | Basic README | API docs start | User guide draft | ✓ Complete |

---
