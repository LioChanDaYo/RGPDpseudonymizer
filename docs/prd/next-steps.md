# Next Steps & Post-Launch Roadmap

## Unified Roadmap

The post-launch roadmap is organized into three horizons, prioritizing **accessibility** (GUI + executables) over **NLP accuracy** (fine-tuning). Rationale: the GUI path unlocks a significantly larger user base (non-technical HR, legal, compliance professionals), while fine-tuning only benefits existing CLI-savvy users and requires curated training data and compute investment that is better informed by a larger user base.

---

### v1.1 — Quick Wins & GDPR Compliance (Q2-Q3 2026)

**Goal:** Address beta feedback, close compliance gaps, and improve pseudonym quality without architectural changes.

| Item | Source | Priority | Effort | Description |
|------|--------|----------|--------|-------------|
| **FE-008: GDPR Right to Erasure** | PM session | High | 2-3 days | `delete-mapping` CLI command for Article 17 selective entity deletion. Converts pseudonymization into anonymization by removing the re-identification link. |
| **FE-007: Gender-Aware Pseudonyms** | Story 3.2 feedback | Medium | 2-3 days | French name gender detection (heuristic or LLM-based) so female names receive female pseudonyms. Improves LLM utility and document coherence. |
| Beta bug fixes | Story 4.6 | High | 1-2 weeks | Critical/high bugs from beta tester feedback (10% scope allowance). |
| UX improvements | Story 4.6 | Medium | 1 week | Usability issues discovered during beta (error messages, workflow friction). |
| **FE-010: French Documentation Translation** | PM session | Medium | 1-2 weeks | Translate user-facing documentation (README, ALPHA-INSTALL, CLI help text, user guide) into French. Primary audience is French-speaking; lowers adoption barrier before GUI. |

**Success criteria:** v1.1 released to early adopters, FE-008 operational, French documentation available, no critical open bugs.

---

### v2.0 — GUI & Broader Accessibility (Q3-Q4 2026)

**Goal:** Expand beyond CLI-savvy users to the primary growth market: non-technical professionals who need GDPR-compliant pseudonymization but lack command-line comfort.

| Item | Priority | Effort | Description |
|------|----------|--------|-------------|
| **Desktop GUI** | Critical | 4-6 weeks | Cross-platform desktop app (Windows/Mac/Linux) wrapping existing CLI core logic. Core workflows: drag-and-drop document processing, visual entity review/editing, batch progress visualization, configuration management. |
| **Standalone executables (FE-009)** | Critical | 2-4 weeks | `.exe` (Windows), `.app` (macOS) bundles via PyInstaller. Includes Python runtime + dependencies + spaCy model (~800MB-1GB). Code signing for OS trust. Ships WITH the GUI — CLI-only .exe has limited value for target users. |
| **French-first UI (i18n)** | High | 1-2 weeks | Primary audience is French-speaking. i18n architecture from day one to avoid costly retrofitting. |
| **WCAG AA accessibility** | High | 1 week | Professional/academic contexts require accessibility compliance. |
| Additional format support | Medium | 1-2 weeks | PDF and DOCX input support (v1.0 limited to .txt/.md). |

**Success criteria:** Non-technical users can download, install, and pseudonymize documents without Python or CLI knowledge. Installation success rate >95% for GUI path.

#### UX Expert Prompt (Phase 2 GUI Design)

*Retained from original planning — to be executed when v2.0 development begins.*

The GDPR Pseudonymizer MVP (CLI tool) is now defined in the PRD. Phase 2 will introduce a GUI to expand accessibility beyond technical users.

Please review [docs/prd.md](docs/prd.md) and [docs/brief.md](docs/brief.md), then design the Phase 2 GUI architecture considering:

- **Target Users:** Non-technical researchers, HR professionals, compliance officers (low CLI comfort)
- **Core Workflows:** Drag-and-drop document processing, visual entity review/editing, batch progress visualization, configuration management
- **Key Constraints:** Maintain local-first architecture (no cloud dependencies), cross-platform desktop app (Windows/Mac/Linux), preserve security model (encrypted mapping tables)
- **Phase 1 Integration:** GUI should wrap existing CLI core logic, not duplicate it
- **Accessibility:** WCAG AA compliance for professional/academic contexts
- **Internationalization (i18n):** French language support must be planned from the start (primary target audience is French-speaking researchers). Architecture must support multi-language UI from day one to avoid costly retrofitting.
- **Standalone Distribution (CRITICAL):** Phase 2 MUST include standalone executables (.exe for Windows, .app for macOS) that bundle the GUI + Python runtime. Non-technical users cannot be expected to install Python. See FE-009 in Epic 4 Future Enhancements for details.

Deliverables: UX architecture document with wireframes, interaction patterns, i18n architecture, and implementation guidance.

---

### v3.0 — NLP Accuracy & Automation (2027+)

**Goal:** Reduce human validation burden through improved AI accuracy, eventually enabling optional or fully automatic processing for high-confidence workflows.

| Item | Priority | Effort | Description |
|------|----------|--------|-------------|
| **Fine-tuned French NER model** | High | 4-8 weeks | Train on accumulated user-validated data. Target: 70-85% F1 (up from 40-50% hybrid baseline). Requires curated training corpus from v1.x/v2.x usage. |
| **Optional validation mode** | High | 1-2 weeks | `--no-validate` flag for high-confidence workflows. Only available when fine-tuned model meets accuracy threshold. |
| **Confidence-based auto-processing** | Medium | 2-3 weeks | Entities above confidence threshold auto-accepted, only low-confidence entities presented for review. Target: 85%+ F1. |
| **Multi-language support** | Medium | 4-6 weeks | English, Spanish, German NER models. Requires per-language pseudonym libraries and validation. |
| **Context-aware detection** | Low | Research | Use document context (pronouns, coreference) to improve entity resolution and gender detection. |

**Strategic note:** Fine-tuning is deferred to v3.0 because:
1. It requires substantial curated training data — best collected from v1.x/v2.x user validations
2. The accuracy improvement only reduces validation time; it doesn't unlock new user segments (unlike the GUI)
3. With a GUI user base, the training data pipeline becomes richer and the investment more justified

**Success criteria:** Fine-tuned model achieves 70%+ F1 on production documents. Optional validation mode available for power users.

---

#### Architect Prompt (Phase 2+ Architecture)

*Retained from original planning — to be executed when v2.0+ development begins.*

The GDPR Pseudonymizer PRD is complete and ready for architectural design.

Please review [docs/prd.md](docs/prd.md) and [docs/brief.md](docs/brief.md), then create the architecture document addressing:

**Critical Decisions (Week 0 Prerequisites):**
- NLP library selection validation (spaCy vs Stanza benchmark protocol - Story 0.3, 1.2)
- Test corpus annotation methodology and quality standards

**Core Architecture (Epic 1-2 Foundation):**
- Module structure and interfaces (cli, core, nlp, data, pseudonym, utils layers)
- Compositional pseudonymization algorithm design (FR4-5-20 implementation approach)
- Data layer design (SQLite schema, Python-native encryption implementation, query patterns)
- Error handling taxonomy and recovery strategies

**Scalability & Performance (Epic 2-3):**
- Process-based batch processing architecture (worker pool management, IPC, state sharing)
- Caching and idempotency implementation (FR19)
- Performance optimization strategies (lazy loading, memory management)

**Quality & Testing (All Epics):**
- Testing strategy details (unit/integration/performance test structure, mocking approaches)
- CI/CD pipeline specifics (GitHub Actions workflow, platform matrix)
- Quality gates per epic (when to block vs warn)

**Constraints:**
- Local-only processing (no network dependencies)
- Consumer hardware target (8GB RAM, dual-core CPU)
- Python 3.9+ cross-platform compatibility
- NFR thresholds (90% accuracy, <30s single-doc, <30min 50-doc batch)

Deliverables: Architecture document with system diagrams, module specifications, data models, and Epic 0-1 implementation guidance.

---

*This PRD was created using the BMAD-METHOD framework with interactive elicitation and multi-perspective validation.*
