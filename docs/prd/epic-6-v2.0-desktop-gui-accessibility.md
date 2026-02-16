# Epic 6: v2.0 — Desktop GUI & Broader Accessibility

**Epic Goal:** Expand beyond CLI-only users to the primary growth market — non-technical professionals (HR, legal, compliance, researchers) who need GDPR-compliant pseudonymization but lack command-line comfort — by delivering a cross-platform desktop GUI, standalone executables, French-first internationalization, and WCAG AA accessibility.

**Target Release:** v2.0.0 — Ship when ready (quality over deadline)
**Duration:** Estimated 10-14 weeks
**Predecessor:** Epic 5 (v1.1.0 released 2026-02-15)

---

## Existing System Context

- **v1.1 MVP:** Fully operational CLI tool on PyPI (`pip install gdpr-pseudonymizer`)
- **Technology Stack:** Python 3.10-3.12, Poetry, spaCy `fr_core_news_lg`, Rich, Typer 0.9.x, SQLite + cryptography (Fernet), structlog
- **Architecture:** CLI → Core → NLP/Pseudonym/Data/Validation layers (see [architecture/](../architecture/))
- **Quality Baseline:** 1267+ tests, 86%+ coverage, all quality gates passing (black, ruff, mypy)
- **v1.1 Capabilities:** GDPR Article 17 erasure, gender-aware pseudonyms, PDF/DOCX input, French documentation, NER F1 ~60% (hybrid), mandatory validation mode, .txt/.md/.pdf/.docx input
- **Key Constraint:** GUI must wrap existing CLI core logic — not duplicate it. The `gdpr_pseudonymizer/core/`, `nlp/`, `pseudonym/`, `data/`, `validation/` modules are the single source of truth.

---

## Strategic Context

### Why GUI Now?

The v1.0/v1.1 CLI tool has validated the core value proposition (local GDPR-compliant pseudonymization). However, the **primary target audience** — French-speaking researchers, HR professionals, compliance officers — overwhelmingly lacks CLI comfort. A desktop GUI:

1. **Unlocks 10x larger user base** — non-technical professionals who can't use CLI
2. **Reduces onboarding from 30 min to 5 min** — drag-and-drop vs `pip install` + CLI commands
3. **Enables visual entity validation** — the tool's #1 workflow becomes intuitive instead of keyboard-driven
4. **Makes standalone distribution possible** — .exe/.app bundles eliminate Python dependency entirely

### What Changes, What Doesn't

| Layer | Changes? | Notes |
|-------|----------|-------|
| Core processing engine | No | GUI calls same `processor.py` as CLI |
| NLP detection pipeline | No | Same spaCy + regex hybrid |
| Pseudonym assignment | No | Same `library_manager.py` |
| Data/mapping layer | No | Same SQLite + Fernet encryption |
| Validation logic | No | Same `validation/` module, new UI frontend |
| CLI interface | No | CLI remains fully functional alongside GUI |
| **NEW: GUI layer** | Yes | New `gui/` package wrapping core logic |
| **NEW: i18n framework** | Yes | New i18n architecture for GUI + CLI --help |
| **NEW: Distribution** | Yes | PyInstaller or equivalent for standalone builds |

---

## Epic 6 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 6.1: UX Architecture & GUI Framework Selection | 🔴 **HIGH** | 1-2 weeks | Roadmap v2.0 | 📋 PENDING |
| 6.2: GUI Application Foundation | 🔴 **HIGH** | 1-2 weeks | Roadmap v2.0 | 📋 PENDING |
| 6.3: Document Processing Workflow | 🔴 **HIGH** | 1-2 weeks | Roadmap v2.0 | 📋 PENDING |
| 6.4: Visual Entity Validation Interface | 🔴 **HIGH** | 2-3 weeks | Roadmap v2.0 | 📋 PENDING |
| 6.5: Batch Processing & Configuration Management | 🟡 **MEDIUM** | 1-2 weeks | Roadmap v2.0 | 📋 PENDING |
| 6.6: Internationalization & French UI | 🟡 **MEDIUM** | 1-2 weeks | FE-010b + 5.4.1 | 📋 PENDING |
| 6.7: Accessibility (WCAG AA) | 🟡 **MEDIUM** | 1 week | Roadmap v2.0 | 📋 PENDING |
| 6.8: Standalone Executables & Distribution | 🔴 **HIGH** | 2-3 weeks | FE-009 | 📋 PENDING |
| 6.9: v2.0 Release Preparation | 🔴 **HIGH** | 1-2 days | — | 📋 PENDING |

**Total Estimated Duration:** 10-16 weeks (target: 10-14 weeks)

---

## Story 6.1: UX Architecture & GUI Framework Selection

**As a** product team,
**I want** a validated UX design and GUI framework recommendation,
**so that** implementation stories have clear wireframes, interaction patterns, and a proven technology choice to build on.

**Priority:** 🔴 **HIGH** — Blocks all other implementation stories

### Context

This is a **design and architecture story**, not an implementation story. The output is a UX specification document and a framework selection decision. No application code is written.

The GUI must feel native and professional for the target audience (French-speaking professionals in corporate/academic environments). The primary workflow — document processing → entity validation → pseudonymized output — must be achievable in under 5 minutes for a first-time user.

### Acceptance Criteria

1. **AC1:** GUI framework evaluated and selected. Candidates:
   - **PySide6/PyQt6** — Native Python, mature, cross-platform, large ecosystem
   - **Tauri** — Rust backend + web frontend, lightweight (~5MB), modern
   - **Electron** — Web-based, heavy (~150MB), but familiar dev experience
   - **Kivy/BeeWare** — Python-native, mobile-capable, less polished
   - Selection criteria: bundle size, startup time, native look-and-feel, Python integration complexity, i18n support, accessibility support, packaging ease
2. **AC2:** UX wireframes created for all primary screens:
   - Home/Welcome screen (drag-and-drop zone, recent files)
   - Single document processing (file selection, progress, results)
   - Entity validation (visual entity highlighting, accept/reject/edit, context display)
   - Batch processing (folder selection, progress, summary)
   - Settings/Configuration (theme, language, default options)
   - Mapping database management (list entities, delete mapping, export)
3. **AC3:** Interaction patterns documented:
   - Drag-and-drop workflow
   - Entity validation UX (click-to-select, right-click context menu, bulk actions)
   - Keyboard shortcuts for power users
   - Progress feedback patterns (single doc, batch)
4. **AC4:** i18n architecture designed:
   - Framework-level i18n approach (gettext, Qt Linguist, or custom)
   - Translation file format and workflow
   - How CLI `--help` text plugs into same i18n system
   - RTL support consideration (future-proofing, not required for FR/EN)
5. **AC5:** Distribution approach evaluated:
   - PyInstaller, cx_Freeze, Briefcase, Nuitka — pros/cons for selected GUI framework
   - Expected bundle size (target: <500MB including spaCy model)
   - Code signing requirements (Windows Authenticode, macOS notarization)
   - Auto-update mechanism consideration (deferred to v2.1 if complex)
6. **AC6:** Repository structure decision:
   - Monorepo (add `gdpr_pseudonymizer/gui/` package) vs separate GUI repo
   - Impact on CI/CD, packaging, releases
7. **AC7:** UX specification reviewed and approved by PM/PO

### Deliverables

- `docs/architecture/gui-ux-specification.md` — Wireframes, interaction patterns, screen inventory
- `docs/architecture/gui-framework-decision.md` — Framework comparison matrix, selection rationale
- Updated `docs/architecture/` sections as needed (tech stack, project structure)

### Estimated Effort: 1-2 weeks

---

## Story 6.2: GUI Application Foundation

**As a** developer,
**I want** a working GUI application shell with navigation, theming, and core infrastructure,
**so that** subsequent stories can build features on a solid foundation.

**Priority:** 🔴 **HIGH** — Foundation for all GUI feature stories

### Context

Implements the selected framework from Story 6.1. Delivers a launchable application with proper window management, navigation structure, and theming — but no pseudonymization features yet. The "walking skeleton" of the GUI.

### Acceptance Criteria

1. **AC1:** Application launches with main window, menu bar, and navigation
2. **AC2:** Light/dark theme support matching the target audience's professional environment
3. **AC3:** Home screen with drag-and-drop zone and recent files list implemented
4. **AC4:** Navigation between screens (Home, Settings, About) functional
5. **AC5:** Settings screen with basic preferences (language, theme, default paths)
6. **AC6:** Application icon and branding consistent with project identity
7. **AC7:** Error handling infrastructure: global error handler, user-friendly error dialogs
8. **AC8:** Logging infrastructure: GUI events logged via structlog (existing logging system)
9. **AC9:** Project structure updated: new `gui/` package integrated into build system
10. **AC10:** Unit tests for GUI infrastructure (window creation, navigation, settings persistence)
11. **AC11:** Application starts in <5 seconds on target hardware (excluding spaCy model load)
12. **AC12:** No regression in CLI functionality — `gdpr-pseudo` CLI commands still work

### Integration Points

- `gdpr_pseudonymizer/gui/` — new package (or separate location per Story 6.1 decision)
- `pyproject.toml` — new GUI dependencies, entry point for GUI launcher
- Existing `gdpr_pseudonymizer/core/`, `data/`, `utils/` — imported, not duplicated

### Estimated Effort: 1-2 weeks

---

## Story 6.3: Document Processing Workflow

**As a** non-technical user,
**I want** to select a document (or drag-and-drop it) and see it processed with a clear progress indicator,
**so that** I can pseudonymize documents without knowing CLI commands.

**Priority:** 🔴 **HIGH** — Core user workflow #1

### Context

This is the primary single-document workflow: open file → process → see results. Processing invokes the existing `core/processor.py` pipeline. The entity validation step (Story 6.4) is triggered automatically after detection, but this story covers the file handling and processing infrastructure.

### Acceptance Criteria

1. **AC1:** File selection via:
   - Drag-and-drop onto main window
   - File open dialog (with filter for .txt, .md, .pdf, .docx)
   - Recent files list
2. **AC2:** Passphrase prompt for mapping database (reuse existing or create new)
3. **AC3:** Processing progress displayed:
   - File reading phase
   - NLP detection phase (with spaCy model loading indicator on first run)
   - Entity count summary before validation
4. **AC4:** spaCy model auto-download with progress bar if not installed
5. **AC5:** Processing runs in background thread (GUI stays responsive)
6. **AC6:** Results screen shows:
   - Pseudonymized document preview (scrollable, with highlighting of replaced entities)
   - Entity summary (count by type: PERSON, LOCATION, ORG)
   - Save button (choose output location and format)
7. **AC7:** Output file saved as pseudonymized .txt (matching v1.1 CLI behavior)
8. **AC8:** Error handling: corrupt files, unsupported formats, empty documents, password-protected PDFs
9. **AC9:** Unit and integration tests for file handling, processing pipeline, and results display
10. **AC10:** No regression in existing CLI processing behavior

### Integration Points

- `gdpr_pseudonymizer/core/processor.py` — called from GUI (same pipeline as CLI)
- `gdpr_pseudonymizer/utils/file_reader.py` — PDF/DOCX extraction
- `gdpr_pseudonymizer/data/mapping_repository.py` — database creation/reuse

### Estimated Effort: 1-2 weeks

---

## Story 6.4: Visual Entity Validation Interface

**As a** user reviewing detected entities,
**I want** a visual interface to see entities highlighted in context, accept/reject/edit them with mouse clicks, and add missed entities by selecting text,
**so that** entity validation is intuitive and fast — even for non-technical users.

**Priority:** 🔴 **HIGH** — The defining feature of the GUI. Users spend 80% of interaction time here.

### Context

The CLI validation UI (Rich-based, keyboard-driven) works for power users but is the #1 barrier for non-technical adoption. The GUI validation interface must make the same workflow accessible to anyone who can use a word processor. This is the story that justifies v2.0's existence.

The validation logic (`validation/` module) stays unchanged — only the presentation layer changes.

### Acceptance Criteria

1. **AC1:** Document view with inline entity highlighting:
   - Color-coded by entity type (PERSON = blue, LOCATION = green, ORG = orange)
   - Pseudonym shown as tooltip or inline annotation
   - Scrollable for long documents
2. **AC2:** Entity panel (sidebar or bottom panel):
   - List of all detected entities grouped by type
   - Status indicator per entity (pending, accepted, rejected, modified)
   - Click entity in panel → scroll to and highlight in document view
3. **AC3:** Entity actions via context menu or buttons:
   - Accept (confirm entity and pseudonym)
   - Reject (remove false positive)
   - Edit entity text (adjust boundaries)
   - Change pseudonym (override suggested pseudonym)
   - Change entity type (reclassify PERSON→ORG, etc.)
4. **AC4:** Add missed entity by text selection:
   - Select text in document view → right-click → "Add as Entity" → choose type
   - Entity added to validation list with auto-assigned pseudonym
5. **AC5:** Bulk actions:
   - "Accept All" per entity type (e.g., accept all PERSON entities)
   - "Accept All High-Confidence" (if confidence scores available)
   - Select multiple entities → bulk accept/reject
6. **AC6:** Validation summary before processing:
   - "You have accepted X entities, rejected Y, added Z manually. Proceed?"
   - Option to go back and revise
7. **AC7:** Keyboard shortcuts for power users:
   - Tab/Shift+Tab to navigate entities
   - Enter to accept, Delete to reject
   - Documented in Help overlay
8. **AC8:** Performance: validation UI responsive with 100+ entities (no lag on scroll/click)
9. **AC9:** Unit tests for entity highlighting, action handling, bulk operations
10. **AC10:** Integration test: open document → validate entities → save pseudonymized output end-to-end

### Integration Points

- `gdpr_pseudonymizer/validation/` — reuse `models.py`, `workflow.py`; new GUI-specific UI layer
- `gdpr_pseudonymizer/core/processor.py` — post-validation processing
- `gdpr_pseudonymizer/pseudonym/library_manager.py` — pseudonym reassignment on edit

### Estimated Effort: 2-3 weeks

---

## Story 6.5: Batch Processing & Configuration Management

**As a** user with multiple documents to process,
**I want** to select a folder or multiple files and process them as a batch with a visual progress dashboard,
**so that** I can pseudonymize entire document sets efficiently.

**Priority:** 🟡 **MEDIUM** — Important for production use, but single-doc workflow comes first

### Context

Batch processing already works via CLI (`gdpr-pseudo batch`). This story wraps the same batch pipeline in a GUI with visual progress tracking and a configuration management screen.

### Acceptance Criteria

1. **AC1:** Batch file selection:
   - Folder selection (processes all supported files in folder)
   - Multi-file selection via file dialog
   - Drag-and-drop multiple files or a folder
2. **AC2:** Batch progress dashboard:
   - Overall progress bar (X of Y documents)
   - Per-document status (queued, processing, validating, done, error)
   - Estimated time remaining
   - Pause/cancel capability
3. **AC3:** Batch validation workflow:
   - Option A: Validate all entities across batch before processing (current CLI behavior)
   - Option B: Validate per-document as batch progresses
   - User selects preference in settings
4. **AC4:** Batch summary report on completion:
   - Documents processed, entities detected/validated, errors encountered
   - Export summary as report (.txt or .html)
5. **AC5:** Configuration management screen:
   - Default pseudonym theme selection
   - Default output directory
   - Default mapping database path
   - Batch processing options (parallelism, continue-on-error)
   - Settings persisted to `.gdpr-pseudo.yaml` (same config file as CLI)
6. **AC6:** Mapping database management screen:
   - List entities in current database (reuses `list-entities` logic)
   - Delete mapping (reuses `delete-mapping` logic for Article 17)
   - Database info (entity count, creation date, last operation)
7. **AC7:** Unit and integration tests for batch workflow, configuration persistence
8. **AC8:** No regression in CLI batch processing

### Integration Points

- `gdpr_pseudonymizer/core/processor.py` — `process_batch()` called from GUI
- `gdpr_pseudonymizer/data/mapping_repository.py` — entity listing, deletion
- `gdpr_pseudonymizer/cli/commands/` — reuse command logic, not CLI wrappers

### Estimated Effort: 1-2 weeks

---

## Story 6.6: Internationalization & French UI

**As a** French-speaking user,
**I want** the GUI interface, CLI help text, and all documentation available in French,
**so that** I can use the tool entirely in my native language.

**Priority:** 🟡 **MEDIUM** — Primary audience is French-speaking; high adoption impact

### Context

This story implements the i18n architecture designed in Story 6.1 and delivers French as the first (and primary) non-English language. It also absorbs two deferred items:
- **FE-010b:** CLI `--help` text translation (deferred from Epic 5 due to Typer/click risk)
- **Story 5.4.1:** Complete French documentation translations (CLI Reference, API Reference, Methodology pages)

### Acceptance Criteria

1. **AC1:** i18n framework integrated into GUI:
   - All user-facing strings externalized to translation files
   - Language switching (FR/EN) in settings, takes effect immediately
   - Fallback to English for missing translations
2. **AC2:** Complete French translation of all GUI screens:
   - Home, Document Processing, Entity Validation, Batch, Settings, About
   - Menu items, buttons, labels, tooltips, error messages, dialogs
3. **AC3 (FE-010b):** CLI `--help` text translated to French:
   - All command descriptions, option help text, examples
   - Activated via `--lang fr` flag or `LANG=fr` environment variable
   - **Note:** Requires careful testing with Typer 0.9.x/click <8.2.0 compatibility
4. **AC4 (Story 5.4.1):** Remaining documentation pages translated:
   - `docs/CLI-REFERENCE.fr.md` — CLI Reference in French
   - `docs/api-reference.fr.md` — API Reference in French
   - `docs/methodology.fr.md` — Methodology page in French
   - MkDocs builds without missing file warnings for `/fr/` pages
5. **AC5:** Language auto-detection from system locale (French system → French UI by default)
6. **AC6:** Translation quality reviewed by native French speaker
7. **AC7:** Unit tests for i18n framework, string externalization, language switching
8. **AC8:** No regression in existing English documentation or CLI behavior

### Integration Points

- `gdpr_pseudonymizer/gui/` — i18n integration in all GUI components
- `gdpr_pseudonymizer/cli/main.py` — `--lang` flag for CLI help text
- `docs/*.fr.md` — new French documentation pages
- `mkdocs.yml` — updated for complete FR coverage

### Estimated Effort: 1-2 weeks

---

## Story 6.7: Accessibility (WCAG AA)

**As a** user with visual or motor impairments,
**I want** the GUI to meet WCAG AA accessibility standards,
**so that** I can use the tool with assistive technologies in professional/academic environments.

**Priority:** 🟡 **MEDIUM** — Required for professional/academic deployment contexts

### Context

Professional and academic environments increasingly require accessibility compliance. WCAG AA provides a reasonable standard for desktop applications. This story focuses on the most impactful accessibility improvements rather than exhaustive compliance.

### Acceptance Criteria

1. **AC1:** Keyboard navigation:
   - All GUI functions accessible without mouse
   - Logical tab order through all screens
   - Focus indicators visible on all interactive elements
   - Keyboard shortcuts documented in Help screen
2. **AC2:** Screen reader support:
   - All interactive elements have accessible labels/roles
   - Entity validation announcements (entity type, name, status)
   - Progress updates announced
   - Tested with at least one screen reader (NVDA on Windows or VoiceOver on macOS)
3. **AC3:** Visual accessibility:
   - Minimum 4.5:1 contrast ratio for all text (WCAG AA)
   - Entity type colors distinguishable for common color blindness types (deuteranopia, protanopia)
   - Text resizable without layout breaking (up to 200%)
   - No information conveyed by color alone (icons/patterns as secondary indicators)
4. **AC4:** High contrast mode support (follows OS setting)
5. **AC5:** Accessibility audit checklist documented and passed
6. **AC6:** Unit tests for focus management, keyboard navigation paths

### Integration Points

- `gdpr_pseudonymizer/gui/` — accessibility attributes on all components
- Entity color scheme — updated for color-blind safety

### Estimated Effort: 1 week

---

## Story 6.8: Standalone Executables & Distribution

**As a** non-technical user,
**I want** to download and run a single installer (.exe on Windows, .app on macOS),
**so that** I can use GDPR Pseudonymizer without installing Python, pip, or any dependencies.

**Priority:** 🔴 **HIGH** — Eliminates the #1 adoption barrier for non-technical users

### Context

Currently, installation requires Python, pip, and a `pip install` command — a significant barrier for non-technical users. Standalone executables bundle Python runtime + all dependencies + spaCy model (~800MB-1GB) into a single distributable package. This is the other half of the "broader accessibility" goal alongside the GUI.

### Acceptance Criteria

1. **AC1:** Packaging tool selected and configured (per Story 6.1 recommendation):
   - PyInstaller, cx_Freeze, Briefcase, or Nuitka
   - Produces single-file or single-directory bundle
2. **AC2:** Windows executable:
   - `.exe` or installer (`.msi` / NSIS installer)
   - Launches GUI by default, CLI available via command line
   - Tested on Windows 10 and Windows 11
3. **AC3:** macOS application:
   - `.app` bundle (inside `.dmg` for distribution)
   - Launches GUI by default
   - Tested on macOS 13+ (Intel and Apple Silicon)
4. **AC4:** Linux package (optional, lower priority):
   - AppImage or .deb package
   - Tested on Ubuntu 22.04+
5. **AC5:** Bundle includes:
   - Python runtime
   - All Python dependencies
   - spaCy `fr_core_news_lg` model
   - GUI framework dependencies
   - Pseudonym libraries and resource files
6. **AC6:** Bundle size target: <500MB (compressed installer)
7. **AC7:** Startup time: <10 seconds on target hardware (first launch may be slower)
8. **AC8:** Code signing:
   - Windows: Authenticode signing (suppresses SmartScreen warning)
   - macOS: notarization (required for Gatekeeper)
   - **Note:** Requires signing certificates — may need to budget for this
9. **AC9:** CI/CD pipeline builds executables on push to release branch:
   - GitHub Actions workflow for Windows, macOS, Linux builds
   - Artifacts uploaded to GitHub Releases
10. **AC10:** Installation documentation updated:
    - "Download and run" instructions for non-technical users
    - Platform-specific installation notes
    - Troubleshooting (antivirus false positives, Gatekeeper warnings)
11. **AC11:** No regression in PyPI package installation path (`pip install gdpr-pseudonymizer`)

### Integration Points

- `pyproject.toml` — packaging tool configuration
- `.github/workflows/` — new build workflow for executables
- `gdpr_pseudonymizer/gui/` — entry point for standalone launcher
- Existing `gdpr_pseudonymizer/cli/` — entry point for CLI mode

### Estimated Effort: 2-3 weeks

---

## Story 6.9: v2.0 Release Preparation

**As a** product manager,
**I want** v2.0.0 published with updated documentation, standalone downloads, and release notes,
**so that** non-technical users can discover, download, and use the tool.

**Priority:** 🔴 **HIGH** — Final story, gates the release

### Acceptance Criteria

1. **AC1:** Version bumped to `2.0.0` in `pyproject.toml`
2. **AC2:** CHANGELOG.md updated with v2.0.0 section
3. **AC3:** README updated: GUI screenshots, download links, updated installation instructions
4. **AC4:** README.fr.md mirrored with French updates
5. **AC5:** Full regression suite passing: black, ruff, mypy, pytest (CLI + GUI tests)
6. **AC6:** `poetry build` succeeds, PyPI package builds cleanly
7. **AC7:** Standalone executables built and tested for Windows, macOS (, Linux)
8. **AC8:** MkDocs documentation rebuilt with GUI user guide section
9. **AC9:** Git tag `v2.0.0` triggers release workflow → PyPI publish + GitHub Release with executable assets
10. **AC10:** Release announcement drafted
11. **AC11:** Landing page or README section for non-technical users ("Download" section with platform buttons)

### Estimated Effort: 1-2 days

---

## Execution Sequence

**Recommended Story Order:**

```
Story 6.1 (UX/Architecture)      ─── Week 1-2 ───── Design gate (blocks all)
Story 6.2 (GUI Foundation)        ─── Week 3-4 ───── Foundation
Story 6.3 (Doc Processing)        ─── Week 5-6 ───── Core workflow
Story 6.4 (Entity Validation)     ─── Week 6-8 ───── Key feature (can overlap 6.3)
Story 6.5 (Batch + Config)        ─── Week 8-9 ───── Production features
Story 6.6 (i18n + French)         ─── Week 9-10 ──── Parallelizable with 6.5
Story 6.7 (Accessibility)         ─── Week 10-11 ─── Parallelizable with 6.8
Story 6.8 (Executables)           ─── Week 10-12 ─── Distribution
Story 6.9 (Release Prep)          ─── Week 12-13 ─── Release gate
```

**Parallelization Opportunities:**
- Stories 6.5 + 6.6 are independent — can run in parallel
- Stories 6.7 + 6.8 are independent — can run in parallel
- Story 6.4 can begin before 6.3 is fully complete (shared foundation from 6.2)

**Critical Path:** 6.1 → 6.2 → 6.3 → 6.4 → 6.8 → 6.9 (longest sequential chain ~10-12 weeks)

**Design Gate:** Story 6.1 MUST be completed and approved before any implementation begins. It produces the framework selection, wireframes, and architecture decisions that all other stories depend on.

---

## Architectural Decisions (Resolved by Story 6.1)

These decisions are **open** and will be resolved during Story 6.1:

| Decision | Options | Constraints |
|----------|---------|-------------|
| GUI Framework | PySide6, Tauri, Electron, Kivy | Must integrate with Python core, support i18n, accessibility |
| Distribution Tool | PyInstaller, Briefcase, Nuitka | Must bundle spaCy model, produce <500MB package |
| i18n Framework | gettext, Qt Linguist, custom | Must support GUI + CLI --help, FR/EN minimum |
| Repo Structure | Monorepo vs separate GUI repo | Must not break existing CLI packaging |
| Auto-update | Built-in vs deferred to v2.1 | Scope risk — may defer |

---

## Compatibility Requirements

- [x] Existing CLI commands remain unchanged and fully functional
- [x] Existing mapping database schema unchanged (no migration needed)
- [x] Existing pseudonym libraries unchanged
- [x] PyPI installation path (`pip install gdpr-pseudonymizer`) continues to work (CLI-only)
- [ ] GUI available as separate install path (standalone executable) or via `pip install gdpr-pseudonymizer[gui]`
- [ ] Configuration file (`.gdpr-pseudo.yaml`) shared between CLI and GUI

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GUI framework choice locks in wrong direction | MEDIUM | HIGH | Story 6.1 design gate with framework evaluation before implementation |
| Standalone bundle size >500MB (spaCy model ~541MB) | HIGH | MEDIUM | Evaluate model compression, lazy download on first run, or smaller model (`fr_core_news_md`) |
| Code signing certificates cost / complexity | MEDIUM | MEDIUM | Budget for signing certs; ship unsigned for initial testing, sign for stable release |
| PyInstaller/framework incompatibility | MEDIUM | HIGH | Prototype bundling in Story 6.1 as part of framework evaluation |
| Typer 0.9.x / click <8.2.0 breaks with i18n changes | MEDIUM | MEDIUM | Isolate CLI i18n behind feature flag; test thoroughly with pinned versions |
| GUI accessibility testing requires specialized knowledge | LOW | MEDIUM | Use automated accessibility linters + manual testing with NVDA/VoiceOver |
| Scope creep (too many GUI features) | MEDIUM | MEDIUM | Strict MVP scope: process, validate, batch, settings. No advanced features in v2.0 |
| Cross-platform GUI inconsistencies | MEDIUM | LOW | Test on all 3 platforms early (Story 6.2); prioritize Windows + macOS |

**Rollback Plan:** GUI is purely additive — the CLI remains fully functional. If any story introduces regressions to CLI functionality, revert GUI commits without affecting CLI releases. v1.1.x hotfix releases remain possible throughout v2.0 development.

---

## Explicitly Deferred (v2.1+ / v3.0)

| Item | Reason | Target |
|------|--------|--------|
| Output format preservation (PDF→PDF, DOCX→DOCX) | Complex rendering; v2.0 outputs .txt from PDF/DOCX | v2.1 |
| Auto-update mechanism | Scope risk; defer unless trivial with chosen framework | v2.1 |
| Confidence score calibration (FE-013) | NLP accuracy concern, not GUI | v3.0 |
| Extended coreference resolution (FE-014) | Research-level NLP complexity | v3.0 |
| Fine-tuned French NER model | Requires training data from v1.x/v2.x users | v3.0 |
| Optional validation mode (`--no-validate`) | Requires fine-tuned model with 70%+ F1 | v3.0 |
| Multi-language NER support (EN, ES, DE) | Requires per-language pseudonym libraries | v3.0 |
| Mobile app | Different platform entirely | v3.0+ |
| Python 3.13 support (FB-006) | Blocked by thinc/spaCy wheels | Monitoring |

---

## Definition of Done

- [ ] All 9 stories completed with acceptance criteria met
- [ ] Existing CLI functionality verified (full test suite passing)
- [ ] All quality gates green: black, ruff, mypy, pytest
- [ ] Test count ≥ v1.1 baseline (1267+), coverage ≥ 86%
- [ ] No regression in existing CLI processing workflows
- [ ] GUI functional on Windows 10/11 and macOS 13+
- [ ] Standalone executables (.exe, .app) tested on target platforms
- [ ] French GUI translation complete and reviewed
- [ ] WCAG AA accessibility checklist passed
- [ ] v2.0.0 published on PyPI and standalone downloads on GitHub Releases
- [ ] Documentation updated (EN + FR) with GUI user guide

---

## Success Criteria

Epic 6 is successful if:

1. Non-technical users can download, install, and pseudonymize a document without CLI knowledge
2. Entity validation is achievable via visual point-and-click interface
3. Batch processing works through GUI with visual progress
4. GUI and CLI share the same core engine — no feature divergence
5. French UI is complete and reviewed by native speaker
6. Standalone executables work on Windows and macOS without Python installed
7. No critical bugs open at release time
8. v2.0.0 published on PyPI and GitHub Releases

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing system running Python 3.10-3.12, Poetry, spaCy, Typer 0.9.x, SQLite + cryptography, Rich, structlog
- **Critical constraint:** GUI must wrap existing core logic (`core/`, `nlp/`, `pseudonym/`, `data/`, `validation/`), not duplicate it
- Integration points: GUI calls same processor pipeline as CLI, shares mapping database, shares config file
- Existing patterns to follow: thin CLI wrappers with lazy imports, command logic in `cli/commands/`, data files in `resources/`, tests mirror source structure
- Critical compatibility requirements: Typer 0.9.x + click <8.2.0 pin, standard `--flag/--no-flag` patterns only, no `Optional[bool]` with flag pairs
- **Story 6.1 is a design gate** — produces framework selection and wireframes that block all implementation
- Each story must include verification that existing CLI functionality remains intact

The epic should maintain system integrity while delivering a desktop GUI, standalone executables, French-first internationalization, and WCAG AA accessibility."

---

**Document Status:** ✅ PM APPROVED
**Created:** 2026-02-16
**Approved:** 2026-02-16
**Author:** Sarah (Product Owner)
**PM Reviewer:** User (Product Manager)
**Next Action:** Story 6.1 design phase — run `/architect` or `/ux-expert` to begin UX architecture & framework selection
