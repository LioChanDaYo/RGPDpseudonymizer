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

### Epic 5: v1.1 — Quick Wins & GDPR Compliance (Q2 2026)

**Goal:** Address deferred alpha/beta feedback, close the GDPR Article 17 compliance gap, improve pseudonym quality and NER accuracy, translate documentation for the French-speaking primary audience, and add PDF/DOCX format support.

---

**Timeline: Epics 0-4: 14 weeks (v1.0 MVP). Epic 5: 6-7 weeks (v1.1)**

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
- **Q2 2026 (Epic 5):** v1.1 release — GDPR erasure, gender-aware pseudonyms, PDF/DOCX, French docs, NER accuracy improvements

---

**Epic 5 DoD:**
- ✓ GDPR Article 17 `delete-mapping` command operational
- ✓ Gender-matched pseudonyms for ≥90% of common French first names
- ✓ NER accuracy improved: LOCATION FN <25%, ORG FN <50%
- ✓ French documentation available for primary user workflows
- ✓ PDF and DOCX input format support functional
- ✓ CLI polish and minor enhancements applied
- ✓ v1.1.0 published on PyPI

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
