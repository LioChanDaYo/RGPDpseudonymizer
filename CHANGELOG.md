# Changelog

All notable changes to the GDPR Pseudonymizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **Validate-once-per-entity** (Story 7.1, FE-020) — Accepting or rejecting one entity occurrence now applies to all same-text occurrences in the document; undo reverts the entire group
- **"Masquer les validées" toggle** (Story 7.1, FE-019) — New checkbox to hide confirmed/known entities from document highlights, letting users focus on remaining pending entities
- **Keyboard shortcuts help dialog — all groups** (Story 7.2, FE-018) — F1 dialog now lists all shortcut groups: Global, Home, Validation, Navigation Mode, Editor, Results, Batch, Database, Settings. Navigation Mode section includes an explanatory paragraph on how to activate (Enter) and deactivate (Escape) navigation mode.
- **Settings screen shortcuts sync** (Story 7.2, FE-018) — Settings screen shortcuts section is now driven by the same `get_all_shortcuts()` registry as the F1 dialog; always in sync.
- **Database path persistence** (Story 7.2, FE-017) — After selecting, browsing to, or creating a database in the passphrase dialog, the path is persisted as `default_db_path` in `.gdpr-pseudo.yaml` and pre-selected on next launch.
- **English F1 dialog translations** — All shortcut action strings and dialog UI labels in the F1 help dialog are now correctly translated to English when the application language is set to English.
- **Neutral ID pseudonym theme** (Story 7.3, FE-016) — New `neutral_id` theme generating counter-based identifiers (PERSON-001, LIEU-001, ORG-001) with sequential numbering per entity type. Available in CLI (`--theme neutral_id`), GUI settings, and configuration file.
- **Excel (.xlsx) format support** (Story 7.4, FE-015) — Process Excel spreadsheets with cell-aware NER: each cell is independently analyzed, pseudonyms are applied per-cell, and output preserves the multi-sheet .xlsx structure. Requires optional `openpyxl` dependency (`pip install gdpr-pseudonymizer[excel]`). Formulas are read as cached values (not preserved in output).
- **CSV format support** (Story 7.4, FE-015) — Process CSV files with automatic encoding detection (UTF-8/Latin-1 fallback) and delimiter sniffing (via `csv.Sniffer`). Each cell is processed independently through the NER pipeline. Output preserves the .csv format with comma delimiter.
- **Tabular document pipeline** (Story 7.4) — New `TabularDocument`/`CellData` dataclasses, `tabular_reader` and `tabular_writer` modules for structured cell-aware reading and writing of Excel and CSV files. `context_label` field on `DetectedEntity` carries cell reference (e.g., "Sheet1!B3") through the pipeline.

- **NER accuracy — regex expansion & POS disambiguation** (Story 7.5, FE-011/FE-012) — Expanded ORG detection patterns (30 suffixes, 22 prefixes) with 12 new keywords (Syndicat, Chambre, Mutuelle, Coopérative, Ordre, Caisse, Union, Confédération, Agence, Comité, Commission, Ligue). Added spaCy POS-tag disambiguation to geography dictionary matching (PROPN filter prevents false positives on ambiguous names). Added 7 international locations (France, Allemagne, Berlin, Londres, Luxembourg, Madrid, Benelux) to geography dictionary. LOCATION false-negative rate reduced from 27.42% to 12.90%.

### Known Issues

- **Python 3.13 not yet supported** — `thinc` (spaCy's ML backend) does not publish Python 3.13 wheels as of v9.1.1. Since spaCy depends on thinc, the entire NLP stack is blocked. PySide6-Essentials supports 3.13 via stable ABI wheels. The `pyproject.toml` constraint (`>=3.10,<3.14`) already allows 3.13; only the missing thinc wheels prevent it. Will be added once thinc ships cp313 wheels.

### Fixed

- **F1 dialog light-mode readability** — Section headers (Global, Validation, etc.) and table cells were unreadable (dark text on dark background) in light mode. Fixed by adding explicit `QTableWidget`/`QHeaderView` QSS rules to `light.qss`/`dark.qss` and making the `QScrollArea` viewport background transparent so labels inherit the dialog's white background.
- **Tab key navigation clarification** — Tab/Shift+Tab navigate entities only when navigation mode is active (entered via Enter). Outside navigation mode, Tab follows standard Qt focus traversal. The F1 dialog and shortcuts registry now correctly reflect this distinction.

---

## [2.0.0] - 2026-03-03

**GDPR Pseudonymizer v2.0.0 — Desktop GUI, Standalone Executables & Accessibility**

### Added

- **Standalone Executables & Distribution** (Story 6.8) — PyInstaller `--onedir` builds for all desktop platforms:
  - Windows: NSIS installer (`gdpr-pseudo-setup-2.0.0.exe`) with Start Menu shortcuts and uninstaller
  - macOS: DMG disk images for both Apple Silicon (arm64) and Intel (x86_64)
  - Linux: AppImage portable executable
  - CI/CD workflow (`build-executables.yaml`) triggered on `v*` tags, uploads assets to GitHub Release
  - Unified entry point (`scripts/standalone_entry.py`) for frozen bundle detection
  - Code signing infrastructure ready for future certificate integration
  - Bundle size ~896MB uncompressed, <500MB compressed

- **Internationalization & French UI** (Story 6.6) — Complete i18n framework for the GUI:
  - `.qm` compiled translation files for French and English
  - FR/EN language switching in settings with immediate UI update
  - System locale auto-detection on first launch
  - All GUI screens, dialogs, tooltips, and status messages fully translated

- **WCAG 2.1 Level AA Accessibility** (Story 6.7) — Comprehensive accessibility support:
  - Full keyboard navigation across all screens and controls
  - Screen reader support with ARIA-equivalent Qt accessibility labels
  - 4.5:1 minimum contrast ratios verified across all themes
  - High contrast mode theme option
  - Visible focus indicators on all interactive elements
  - Accessibility audit checklist completed

- **Batch Validation Workflow** (Story 6.7.3) — Per-document entity validation during batch processing:
  - Validation toggle checkbox ("Valider les entités par document") on batch selection screen, persisted in config
  - BatchWorker validation pause/resume via QWaitCondition — worker pauses after entity detection, waits for user validation, then finalizes with validated entities
  - ValidationScreen batch mode: "Document X de Y" indicator, Précédent/Suivant navigation (hidden when unavailable), "Annuler le lot" button, "Valider et continuer" / "Valider et terminer" context-aware button text
  - Batch cancel shows proper statuses: "Annulé" for processed docs (output files cleaned up), "Non traité" for unprocessed docs, "Traitement annulé" summary title
  - Pseudonym preview generation per document for validation display
  - Cached validation contexts for prev/next document navigation without re-triggering detection
  - ETA calculation excludes cumulative validation pause time
  - Batch screen reset on re-entry from home screen ("Ouvrir un dossier")
  - 19 unit tests + 2 integration tests; all quality gates pass

- **Database Background Threading** (Story 6.7.2) — All database operations run on background threads for responsive GUI:
  - DatabaseWorker (QRunnable) for list, search, delete, and export operations via QThreadPool
  - Cancel-and-replace strategy for cancellable operations (load, search); non-cancellable operations (delete, export) disable interactive controls
  - Debounced search with persistent QTimer (300ms); threshold-based routing (inline <200 entities, background >200)
  - Thread-safe list passing via shallow copy to search worker
  - ListEntitiesResult dataclass bundles entities + DB metadata in single signal payload
  - Loading indicator (QProgressBar) with accessibility labels and i18n integration
  - Browse button auto-opens database; passphrase dialog pre-selects known DB path
  - Comprehensive error handling with French user-facing messages for all project exception types
  - Performance seed script (`tests/fixtures/seed_large_db.py`) for 1200-entity test databases
  - 38 new tests (22 worker + 16 screen); all quality gates pass

- **Batch Processing & Configuration Management** (Story 6.5) — Batch document processing and database management in the GUI:
  - Batch processing screen with 3-phase workflow (selection → progress → summary):
    - Folder and multi-file selection with file discovery (.txt/.md/.pdf/.docx), excludes `*_pseudonymized*`
    - Output directory field with config default or `{input}/_pseudonymized/` fallback
    - Real-time progress dashboard: overall QProgressBar, per-document QTableWidget with status transitions (En attente → En cours → Traité/Erreur), estimated time remaining
    - Pause/resume and cancel controls with confirmation dialog
    - Summary cards (documents, entities, new/reused, errors) and per-document results table
    - Export batch report as `.txt`
  - Database management screen (Article 17 RGPD compliance):
    - Entity listing with search, type filter (PERSON/LOCATION/ORG), checkbox multi-selection
    - Entity deletion with confirmation dialog and ERASURE audit logging
    - CSV export (entity_id, entity_type, full_name, pseudonym_full, first_seen)
    - Recent databases dropdown (max 5, persisted in config)
    - Database info summary (creation date, entity count, last operation)
  - BatchWorker (QRunnable) with pause/cancel via QMutex/QWaitCondition, continue-on-error mode
  - Settings enhancements: workers spinner (1-8), default theme selector (neutral/star_wars/lotr)
  - `set_context()` navigation pattern for screen-to-screen data passing
  - 40 new tests (31 unit + 2 integration for batch/database, 7 settings tests); 1365+ total tests

- **Visual Entity Validation Interface** (Story 6.4) — Full visual entity review and validation workflow in the GUI:
  - Split processing pipeline: DetectionWorker (NLP detection phase) + FinalizationWorker (pseudonymization phase) for two-phase workflow with validation in between
  - EntityEditor (QTextEdit subclass): color-coded entity highlights by type (PERSON=blue, LOCATION=green, ORG=orange), pseudonym tooltips, binary search O(log n) click detection, context menus (accept/reject/edit/change type/change pseudonym), "Add as Entity" via text selection, keyboard navigation mode (Enter/Tab/Shift+Tab/Delete/Escape), zoom support (Ctrl+/-), hide-rejected toggle
  - EntityPanel sidebar: entities grouped by type with section headers, status icons (pending/accepted/rejected/modified), checkbox multi-selection, bulk actions (accept/reject selection, accept all of type, accept known), pending counter with live updates, "deja connu" badge for known entities, text filter (Ctrl+F)
  - GUIValidationState adapter: wraps core ValidationSession with QUndoStack integration for full undo/redo (Ctrl+Z/Ctrl+Shift+Z), supports individual and composite bulk undo, entity state tracking (pending/confirmed/rejected/modified/added)
  - ValidationScreen with QSplitter layout (65% editor / 35% panel), bidirectional editor-panel sync, toolbar with hide-rejected toggle and find bar, bottom action bar (Retour with confirmation dialog, Finaliser with validation summary), status bar integration
  - First-use contextual hints overlay (3 callout bubbles, dismissible, stored in config)
  - DocumentProcessor public API: `detect_entities()`, `build_pseudonym_previews()`, `finalize_document()` methods for split-phase processing
  - 72 new tests (66 unit + 6 integration) across 7 test files; all quality gates pass

- **Document Processing Workflow** (Story 6.3) — Full single-document pseudonymization pipeline in the GUI:
  - PassphraseDialog with auto-detect of existing `.gdpr-pseudo.db` files, session caching, and "Create new" option
  - ProcessingWorker running in background thread (QRunnable + WorkerSignals bridge) — GUI stays responsive
  - Three-phase progress display: file reading (0-10%), model loading (10-40%), NLP detection (40-100%)
  - spaCy model auto-detection and download with progress indicator (ModelManager + ModelDownloadWorker)
  - Processing screen with entity summary, zero-entity warning, time estimate, and step indicator integration
  - Results screen with pseudonymized document preview, entity type breakdown (PERSON/LOCATION/ORG with color indicators), pseudonym highlighting, and "Enregistrer sous..." save dialog
  - Error handling: corrupt files, unsupported formats, empty documents, password-protected PDFs, incorrect passphrase
  - 45 new GUI tests across 5 test files (122 total GUI tests); all quality gates pass

- **GUI Application Foundation** (Story 6.2) — PySide6-based desktop application shell for v2.0:
  - Main window with menu bar (Fichier, Affichage, Outils, Aide), status bar, and keyboard shortcuts (Ctrl+O, Ctrl+Q, Ctrl+,, F1, F11)
  - Light/dark theme system with QSS stylesheets and persistent preference
  - Home screen with drag-and-drop zone (.txt, .md, .pdf, .docx), recent files list, batch processing card
  - Settings screen with auto-save: theme, language, processing defaults, batch options, shortcuts reference
  - 4-step progress indicator widget (single/batch modes) with custom QPainter rendering
  - Toast notification system, confirmation dialogs (destructive/proceeding/informational)
  - Global exception handler with structlog logging and user-friendly error dialog
  - Application icon set (16/32/48/256/512 PNG + ICO), splash screen
  - `gdpr-pseudo-gui` entry point, PySide6-Essentials ~6.7.0 as optional dep (`pip install gdpr-pseudonymizer[gui]`)
  - 77 GUI unit tests (pytest-qt) across 9 test files; startup time 1.706s (<5s threshold)

### Changed

- **Core Processing Hardening & Security** (Story 6.7.1) — Security and quality improvements to the core processing pipeline:
  - **PII sanitization (SEC-001):** New `_sanitize_error_message()` strips quoted strings and capitalized name sequences (French accent-aware) from exception messages before logging/audit. Applied to all 3 PII leak vectors in `document_processor.py`
  - **Typed exception handling (EXC-001):** Replaced bare `except Exception` with typed catches — `(ValueError, RuntimeError)` in `_build_pseudonym_assigner`, `(OSError, AttributeError, ImportError)` in `_get_model_version` — with `logger.warning` instead of silent fallback
  - **DRY refactoring (DRY-001):** Extracted `_normalize_entity_text()` static method, eliminating 3 identical strip_titles/strip_prepositions code blocks
  - **Per-document entity type counts:** Added `entity_type_counts` field to `ProcessingResult` and `_ResolveResult`, populated during entity resolution
  - 26 new tests (10 sanitization, 10 GUI-phase methods, 4 error cases, 2 integration with real SQLite)

### Fixed

- **Wrong passphrase locks out retry**: Cached passphrase was stored before validation — entering a wrong passphrase with "Mémoriser" checked caused all subsequent attempts to silently reuse the bad passphrase. Fixed by clearing cache on `ValueError` (database screen) and on auth-related worker errors (batch screen).
- **Naive/aware datetime mismatch**: `datetime.now(timezone.utc)` (aware) subtracted from naive DB timestamps caused `TypeError`. Fixed by making naive timestamps aware before subtraction.
- **QTableWidget checkboxes invisible in light mode**: `QTableWidget::indicator` styles were missing from both QSS themes (only `QListWidget::indicator` was styled). Added indicator styles for both light and dark themes.
- **QSpinBox invisible text in light mode**: Workers spinner had no explicit QSS styling, inheriting a dark fill. Added `QSpinBox` to input field selectors in both themes.
- **DATA-001**: Entity type counts in ProcessingWorker now count from detected entities list instead of querying entire DB, showing accurate per-document counts instead of cumulative DB totals
- **THREAD-001**: Added cancellation flags to DetectionWorker and FinalizationWorker; cancel buttons now stop workers early between processing phases
- **QSS theme rendering** — Fixed black stripes in light mode on Settings and Home screens caused by QScrollArea forcing `autoFillBackground(True)` on content widgets when QSS overrides the native palette. Added QProgressBar, QStackedWidget, QFrame, and QScrollArea container styles to both light and dark QSS theme files.
- **Empty-string decrypt crash** (Story 6.7.2): `EncryptionService.decrypt("")` now returns `""` instead of crashing with `InvalidTag` from `AESSIV.decrypt(b"", None)`. Affects databases with raw empty strings in encrypted fields.
- **Silent exception swallowing** (Story 6.7.2): `DatabaseWorker` catch-all handlers now log `repr(e)` and `type(e).__name__` instead of empty `str(e)` for exceptions like `cryptography.exceptions.InvalidTag` that have no message.

### Known Limitations

- **UI-001**: Minor layout issues at 200% DPI scaling (all functionality accessible)

### Breaking Changes

None. v2.0.0 is fully backwards compatible with v1.x. Existing mapping databases, configuration files, and CLI workflows continue to work without modification.

---

## [1.1.0] - 2026-02-15

### Added

- **GDPR Right to Erasure** (Story 5.1) — `delete-mapping` command for GDPR Article 17 compliance. Delete specific entity mappings by name or UUID with passphrase verification, confirmation prompt, and ERASURE audit log entry. New `list-entities` command for erasure workflow (shows entity ID, type, pseudonym, first seen date). Optional `--reason` flag for documenting erasure rationale. `--force` flag to skip confirmation in scripted workflows.
- **Gender-aware pseudonym assignment** (Story 5.2) — Automatically detects French first name gender from a 945-name dictionary (470 male, 457 female, 18 ambiguous) and assigns gender-matched pseudonyms. Female names get female pseudonyms, male names get male pseudonyms, and ambiguous/unknown names fall back to the combined list. Supports compound names (e.g., "Marie-Claire" detected as female via first component).
- **GenderDetector module** (`gdpr_pseudonymizer.pseudonym.gender_detector`) — Standalone gender detection class with lazy-loaded INSEE-sourced French name dictionary.
- **Gender lookup data** (`french_gender_lookup.json`) — Built from neutral.json pseudonym library and french_names.json, licensed under Etalab Open License 2.0 (compatible with MIT).
- **NER accuracy improvements** (Story 5.3) — F1 score improved from 29.74% to 59.97% (+30.23pp) through annotation cleanup, regex pattern expansion, and French geography dictionary.
  - Ground-truth annotation cleanup: removed 118 garbage/duplicate annotations, fixed ORG/PERSON mislabeling, aligned title stripping with detection output (1,855 → 1,737 entities)
  - LastName, FirstName regex pattern for reversed name formats (e.g., "Dubois, Jean-Marc")
  - Expanded ORG detection: 18 suffixes (SA, SARL, SAS, SASU, EURL, SNC, SCM, SCI, GIE, EI, SCOP, SEL, Association, Fondation, Institut, Groupe, Consortium, Fédération) and 10 prefixes (Société, Entreprise, Cabinet, Groupe, Compagnie, Association, Fondation, Institut, Consortium, Fédération)
  - French geography dictionary: 100 cities, 18 regions, 101 departments for standalone location detection
  - PERSON recall: 34.23% → 82.93% (+48.70pp), ORG FN rate: 65.71% → 48.09% (PASS), LOCATION FN rate: 36.59% → 33.06% (improved)
- **French documentation translation** (Story 5.4) — `README.fr.md` with full French translation and language toggle. French user guides: `installation.fr.md`, `tutorial.fr.md`, `faq.fr.md`, `troubleshooting.fr.md`. MkDocs i18n via `mkdocs-static-i18n` plugin with FR/EN toggle on documentation site.
- **PDF/DOCX input format support** (Story 5.5) — Process PDF and DOCX documents directly without manual conversion. Text extraction via `pdfplumber` (PDF) and `python-docx` (DOCX) as optional extras. Install with `pip install gdpr-pseudonymizer[formats]` (or `[pdf]`/`[docx]` individually). Output is always `.txt` (plaintext); format preservation planned for v1.2+. Scanned/image-based PDFs produce a warning; OCR is not supported. Both `process` and `batch` commands accept `.pdf` and `.docx` files with auto-detection from extension.
- **CLI polish & minor enhancements** (Story 5.6):
  - Context cycling dot indicator in validation UI: displays `● ○ ○ ○ ○` dots showing current context position with `[Press X to cycle]` hint. Truncated format (`○ ○ … ● … ○ ○`) for >10 contexts.
  - Batch operations feedback with entity count: after Shift+A/R, displays count of affected entities and total occurrences (e.g., `✓ Accepted all 15 PERSON entities (42 total occurrences)`). Accept uses green highlight, reject uses cyan.
  - CI benchmark regression gate: `pytest-benchmark` entity-detection benchmark added to CI pipeline with `--benchmark-json` artifact upload (30-day retention) and `--benchmark-max-time=60` guard.

### Changed

- Version bumped from 1.0.7 to 1.1.0

---

## [1.0.6] - 2026-02-11

### Fixed

- Bundle data files (detection patterns, name dictionary, pseudonym libraries) inside the package so they are included in pip-installed wheels. Previously these files used CWD-relative paths and were missing from pip installs, causing `FileNotFoundError` on `gdpr-pseudo process`.

---

## [1.0.5] - 2026-02-11

### Added

- Auto-download spaCy model on first use — no more manual `python -m spacy download fr_core_news_lg` step required.

---

## [1.0.4] - 2026-02-11

### Fixed

- Tighten click pin to `<8.2.0` — click 8.2.x also incompatible with typer 0.9.x (`Parameter.make_metavar()` signature change). Previous pin `<8.3.0` was insufficient.

---

## [1.0.3] - 2026-02-11

### Fixed

- Pin `click` to `<8.3.0` — typer 0.9.x is incompatible with click 8.3.x, which caused `TypeError: Secondary flag is not valid for non-boolean flag` on fresh pip installs where pip resolved click to 8.3.1.

---

## [1.0.2] - 2026-02-11

### Fixed

- Remaining typer/click flag pair incompatibilities: `--continue-on-error/--stop-on-error` and `--skip-duplicates/--prompt-duplicates` custom secondary names replaced with standard `--flag/--no-flag` pattern that works across all typer versions.

---

## [1.0.1] - 2026-02-11

### Fixed

- CLI crash on newer typer/click versions: `TypeError: Secondary flag is not valid for non-boolean flag` caused by `--success-only/--failures-only` flag pair with `Optional[bool]` type. Split into two separate boolean flags.
- Release workflow missing spaCy model download, causing test failures in CI.

---

## [1.0.0] - 2026-02-11

**GDPR Pseudonymizer v1.0.0 — First Public Release**

A CLI tool for GDPR-compliant pseudonymization of French text documents using NLP-based entity detection, human-in-the-loop validation, and reversible encrypted mappings. This release completes all four MVP epics: NLP Detection & Validation (Epic 1), Pseudonymization Engine (Epic 2), CLI Polish & Batch Processing (Epic 3), and Launch Readiness (Epic 4).

**Highlights:**
- Hybrid NLP + regex entity detection for French text (PERSON, LOCATION, ORG)
- Human-in-the-loop validation UI with keyboard shortcuts and entity variant grouping
- Themed pseudonym libraries (Neutral, Star Wars, LOTR) for all entity types
- AES-256-SIV encrypted mapping tables with passphrase protection
- Batch processing with multiprocessing support
- 1077+ tests, 86%+ coverage, full CI/CD pipeline

### Added
- **Beta Feedback Integration & Bug Fixes** (Story 4.6)
  - Entity variant grouping in validation UI (FB-001)
  - Selective entity type processing via `--entity-types` flag (FB-003)
  - Expanded organization pseudonym library: 196 entries (FE-006)
- **Performance & Stability Validation** (Story 4.5)
  - NFR validation suite with automated performance benchmarks
  - All NFR targets PASS: NFR1 ~6s (<30s), NFR2 ~5min (<30min), NFR4 ~1GB (<8GB), NFR5 0.56s (<5s), NFR6 <1% (<10%)
  - Stress testing: 100-document batch, 10K+ word documents
- **NER Accuracy Comprehensive Validation** (Story 4.4)
  - 22-test automated accuracy validation suite against 25-document annotated corpus
  - Dedicated CI workflow for accuracy regression detection
- **LOCATION and ORGANIZATION pseudonym libraries** (Story 3.0)
  - 80 locations and 35+ organizations per theme (neutral, Star Wars, LOTR)
  - Collision prevention and 1:1 mapping for all entity types
- **Documentation site** deployed to GitHub Pages (Story 4.3)
- **PyPI release workflow** for automated publishing on git tags
- **Community files**: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SUPPORT.md, SECURITY.md
- **GitHub Issue Templates** for bug reports and feature requests

### Changed
- Faster `--help` display via lazy imports — ~55% import time reduction (FB-007)
- License changed from GPL-3.0 to MIT
- Version bumped from 0.1.0-alpha to 1.0.0

### Fixed
- Entity variant grouping bridging bug — ambiguous single-word names now isolated (FB-001)
- `--entity-types` filter not applied in batch mode (FB-003)

### Refactored
- **Codebase Refactoring & Technical Debt Resolution** (Story 4.6.1)
  - R1: Decoupled core/CLI layer via `ProcessingNotifier` callback protocol
  - R2: Centralized French patterns into `utils/french_patterns.py`
  - R3: Decomposed `process_document()` god method into 9 focused sub-methods
  - R4: Fixed encapsulation violations in `PseudonymManager` ABC
  - R5: Factored Union-Find into reusable `UnionFind` class
  - R6: Extracted shared CLI logic into `cli/validators.py`
  - R7: Removed dead code `SimplePseudonymManager` stub
  - R8: Centralized exceptions under `PseudonymizerError` hierarchy
  - R9: Harmonized logging to `structlog` across all modules

---

## [0.1.0-alpha] - 2026-01-30

**Release Status:** Alpha release for early feedback (not production-ready)

**Alpha Testing:** Seeking 3-5 friendly users for feedback on installation, validation UI, and output quality. Testing period: 1 week. See [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) for installation instructions.

### What's New - Epic 2 Complete

#### Core Pseudonymization Features
- ✅ **Pseudonym library system** with 3 themed libraries (neutral, Star Wars, LOTR)
- ✅ **Compositional pseudonymization logic** with component-level matching
  - "Marie Dubois" → "Leia Organa", "Marie" alone → "Leia"
  - Smart handling of partial name matches
- ✅ **French name preprocessing**
  - Title stripping (Dr., M., Mme.)
  - Compound name handling (Jean-Pierre treated as atomic)
- ✅ **Encrypted mapping table** (AES-128-CBC with passphrase protection)
  - PBKDF2 key derivation with 210K iterations
  - Idempotent processing (same document = same mappings)
- ✅ **Audit logging** (GDPR Article 30 compliance)
  - Structured JSON logs with entity types, actions, timestamps
  - Excludes sensitive data (entity values never logged)
- ✅ **Single-document pseudonymization workflow**
  - End-to-end CLI with validation UI
  - Rich terminal interface with keyboard shortcuts
- ✅ **Batch processing architecture** validated
  - Multiprocessing support for parallel document processing
  - Consistent pseudonyms across document sets

#### Critical Bug Fixes
- 🐛 **Story 2.8:** Fixed pseudonym component collision bug
  - Prevented GDPR violation where "Marie" and "Marie Dubois" could map to same pseudonym
  - Ensures strict 1:1 entity-to-pseudonym mapping (GDPR requirement)
  - 18 tests added to prevent regression

#### Validation Workflow (Epic 1)
- ✅ **Rich CLI validation UI** with keyboard shortcuts (`a`/`r`/`?`)
- ✅ **Entity deduplication** (66% time reduction for large documents)
- ✅ **Hybrid detection** (NLP + regex, 35.3% F1 accuracy, +52.2% PERSON detection)
- ✅ **Context display** with entity highlighting
- ✅ **Batch operations** (Accept/Reject All Type)

### Known Limitations

- 🇫🇷 **French language only** - No other languages supported in alpha
- 📝 **Text files only** (.txt, .md) - No PDF, DOCX, or other formats
- ✅ **Validation mandatory** - No automatic mode available (human review required for 100% accuracy)
- 🤖 **AI detection: 40-50% accuracy** - Human validation ensures 100% coverage
- 👤 **PERSON entities only have themed pseudonyms** - LOCATION and ORGANIZATION entities are detected and validated but not pseudonymized with themed names (Epic 3 planned feature - HIGH priority)
- 🪟 **Windows:** spaCy access violations possible (use Linux/macOS/WSL if encountered)
- 🐍 **Python 3.10-3.12 supported** - Python 3.13+ blocked by thinc (spaCy dependency) lacking wheels

### Installation

See [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) for detailed instructions.

**Quick start:**
```bash
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Clone and install
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install

# Install spaCy French model (~571MB)
poetry run python scripts/install_spacy_model.py

# Verify installation
poetry run gdpr-pseudo --help
```

### Testing

- ✅ **802+ tests passing** (86%+ coverage across all modules)
- ✅ **All quality gates pass** (black, ruff, mypy, pytest)
- ✅ **Validated on Python 3.10-3.12** (CI/CD matrix testing)

### Documentation

**Alpha Testing Documentation:**
- [ALPHA-INSTALL.md](docs/ALPHA-INSTALL.md) - Installation guide for alpha testers
- [ALPHA-QUICKSTART.md](docs/ALPHA-QUICKSTART.md) - Quick start tutorial and validation UI walkthrough
- [ALPHA-TESTING-PROTOCOL.md](docs/ALPHA-TESTING-PROTOCOL.md) - Test scenarios and feedback survey

**Project Documentation:**
- [README.md](README.md) - Project overview and quick start
- [docs/prd/](docs/prd/) - Product requirements (Epic 1-2)
- [docs/architecture/](docs/architecture/) - Technical architecture
- [docs/stories/](docs/stories/) - Implementation stories (1.0-2.9)

### Feedback

**How to provide feedback:**
- Complete alpha feedback survey (link in onboarding email)
- Report bugs via [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues)
- Feedback via [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions)

**Feedback deadline:** 1 week after onboarding

### Next Steps

- **Epic 3:** CLI polish & batch processing (Week 11-13)
  - LOCATION and ORGANIZATION pseudonym libraries (HIGH priority)
  - Auto-accept high-confidence entities (reduce validation time)
  - Batch folder processing CLI
  - Performance optimizations
- **Epic 4:** Launch readiness & LLM validation (Week 14)
  - Documentation finalization
  - MVP launch preparation
  - Public beta release

### Contributors

Epic 2 implementation team (Stories 2.0.1 - 2.9):
- Development: James (dev agent) + Claude Sonnet 4.5
- Product Management: John (PM agent) + Claude Sonnet 4.5
- Quality Assurance: QA team
- Product Owner: Sarah

### License

MIT License - See [LICENSE](LICENSE) file for details

---

**Legend:**
- ✅ Added
- 🐛 Fixed
- 🔄 Changed
- ⚠️ Deprecated
- ❌ Removed
- 🔒 Security
