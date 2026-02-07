# Next Steps

### UX Expert Prompt

*Note: While the MVP is CLI-only, this prompt is included for Phase 2 GUI planning.*

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

### Architect Prompt

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

*This PRD was created using the BMAD-METHOD™ framework with interactive elicitation and multi-perspective validation.*
