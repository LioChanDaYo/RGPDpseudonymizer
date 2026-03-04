# GDPR Pseudonymizer v2.0.0 Released

We're excited to announce **GDPR Pseudonymizer v2.0.0**, completing Epic 6 (v2.0 Desktop GUI & Broader Accessibility) with 9 new stories bringing a full desktop GUI, standalone executables, WCAG AA accessibility, French UI, and core hardening.

## What's New

### Desktop GUI Application (Stories 6.2-6.5)
A full-featured PySide6 desktop application with:
- **Home screen** with drag-and-drop document processing and recent files
- **Visual entity validation** with color-coded highlights, undo/redo, and keyboard navigation
- **Batch processing dashboard** with real-time progress, pause/cancel, and per-document validation
- **Database management** with search, filter, deletion (GDPR Article 17), and CSV export
- **Settings** with theme, language, processing defaults, and batch options
- **Light/dark/high-contrast themes** with persistent preference

Install: `pip install gdpr-pseudonymizer[gui]`

### Standalone Executables (Story 6.8)
Pre-built executables for all desktop platforms — no Python installation required:
- **Windows:** NSIS installer with Start Menu shortcuts and uninstaller
- **macOS:** DMG disk images for both Apple Silicon (arm64) and Intel (x86_64)
- **Linux:** AppImage portable executable
- CI/CD workflow builds and uploads assets to GitHub Releases on every tag

Download: https://github.com/LioChanDaYo/RGPDpseudonymizer/releases/latest

### WCAG 2.1 Level AA Accessibility (Story 6.7)
- Full keyboard navigation with visible focus indicators
- Screen reader support (NVDA, VoiceOver) with accessible labels
- 4.5:1 minimum contrast ratios across all themes
- High contrast mode with 21:1 contrast for critical elements
- Color-blind safe entity palette (Blue/Orange/Purple)

### Internationalization & French UI (Story 6.6)
- Complete French/English GUI with live language switching
- System locale auto-detection on first launch
- All screens, dialogs, tooltips, and status messages translated
- Qt Linguist `.qm` compiled translations

### Batch Validation Workflow (Story 6.7.3)
- Per-document entity validation during batch processing
- "Document X de Y" indicator with Prev/Next navigation
- Cancel with proper status display for each document

### Core Processing Hardening (Story 6.7.1)
- PII sanitization in error messages (SEC-001)
- Typed exception handling replacing bare `except Exception` (EXC-001)
- DRY refactoring of duplicate code (DRY-001)
- Per-document entity type counts (DATA-001 fix)

### Database Background Threading (Story 6.7.2)
- All database operations on background threads for responsive GUI
- Cancel-and-replace strategy for concurrent operations
- Debounced search with 300ms threshold-based routing

## Upgrade

**For developers (PyPI):**
```bash
pip install --upgrade gdpr-pseudonymizer[gui]
```

**For non-technical users:**
Download a standalone executable from [GitHub Releases](https://github.com/LioChanDaYo/RGPDpseudonymizer/releases/latest).

## Breaking Changes

**None.** v2.0.0 is fully backwards compatible with v1.x. Existing mapping databases, configuration files, and CLI workflows continue to work without modification.

## By the Numbers

- **52 stories** completed across 6 epics
- **1,670+ tests** passing (including 393 GUI tests)
- **86%+ code coverage**
- All quality gates green (Black, Ruff, mypy, pytest)
- Tested on Python 3.10-3.12 across Windows, macOS, and Linux
- **4 platform builds:** Windows installer, macOS DMG (arm64 + x86_64), Linux AppImage

## Links

- **PyPI:** https://pypi.org/project/gdpr-pseudonymizer/2.0.0/
- **Documentation:** https://liochandayo.github.io/RGPDpseudonymizer/
- **Documentation (FR):** https://liochandayo.github.io/RGPDpseudonymizer/fr/
- **GUI Guide:** https://liochandayo.github.io/RGPDpseudonymizer/gui-guide/
- **Changelog:** [CHANGELOG.md](https://github.com/LioChanDaYo/RGPDpseudonymizer/blob/main/CHANGELOG.md)
- **Source:** https://github.com/LioChanDaYo/RGPDpseudonymizer
- **Download (Standalone):** https://github.com/LioChanDaYo/RGPDpseudonymizer/releases/latest

## Thank You

Thanks to everyone who tested v1.x and provided feedback. Your bug reports and feature requests directly shaped this release. The desktop GUI opens GDPR Pseudonymizer to a much broader audience of non-technical users who need GDPR-compliant document processing.

---

**Questions?** Open a [GitHub Discussion](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions) or file an [Issue](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues).
