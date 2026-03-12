# Epic 8: v2.2 — Output Format Preservation & Auto-Update

**Epic Goal:** Enable pseudonymized documents to retain their original format (PDF->PDF, DOCX->DOCX) instead of flattening to plaintext, and implement an auto-update mechanism so standalone executable users receive new versions without manual downloads.

**Target Release:** v2.2.0
**Duration:** Estimated 5-7 weeks
**Predecessor:** Epic 7 (v2.1.0)

---

## Existing System Context

- **v2.1:** Desktop GUI + CLI, standalone executables, Excel/CSV support (Epic 7), neutral theme, improved NER accuracy, 1670+ tests
- **Current limitation:** All input formats (PDF, DOCX, Excel) are processed and output as plaintext (.txt). Users processing DOCX contracts or PDF reports lose all formatting, headers, tables, and layout.
- **Auto-update gap:** Standalone executable users must manually check GitHub Releases and re-download — no notification or in-app update path exists.

---

## Strategic Context

### Why Format Preservation?

v2.0-v2.1 successfully expanded the user base to non-technical professionals. These users process **formatted documents** — contracts (DOCX), reports (PDF), HR files (DOCX) — and losing formatting in the output is a significant adoption barrier. "I pseudonymized my contract but got back a wall of text" is the most common complaint after validation UX (addressed in v2.1).

### Why Auto-Update?

Standalone executable users (the primary non-technical audience) have no `pip install --upgrade` path. Without auto-update, they may run outdated versions indefinitely, missing security fixes, accuracy improvements, and new features.

---

## Epic 8 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 8.1: DOCX Format Preservation | HIGH | 2-3 weeks | Epic 6 deferred | Draft |
| 8.2: PDF Format Preservation | HIGH | 1-2 weeks | Epic 6 deferred | Draft |
| 8.3: Auto-Update Mechanism | MED | 1 week | Epic 6 deferred | Draft |
| 8.4: v2.2 Release Preparation | HIGH | 1-2 days | — | Draft |

**Total Estimated Duration:** 5-7 weeks

---

## Story 8.1: DOCX Format Preservation

**As a** user who processes Word documents,
**I want** the pseudonymized output to be a .docx file that preserves the original formatting, headers, tables, and layout,
**so that** I can use the pseudonymized document in the same professional context as the original.

**Priority:** HIGH — Most requested format; python-docx makes this tractable

### Context

python-docx (already a dependency for input) supports paragraph-level text replacement while preserving formatting runs. The approach is to identify entity positions within paragraph text, then replace entity text in-place within the existing XML structure — preserving fonts, styles, headers, footers, tables, and images.

**Complexity warning:** Entities frequently span multiple formatting runs in DOCX (e.g., "Marie" in one run, " Dupont" in a bold run). Run-splitting and re-merging while preserving per-run formatting is a known pain point with python-docx. Budget time for this edge case — it will dominate the implementation effort.

### Acceptance Criteria

1. **AC1:** DOCX input produces DOCX output with pseudonymized content
2. **AC2:** Preserved elements:
   - Paragraph formatting (fonts, sizes, bold/italic/underline, colors)
   - Headers and footers
   - Tables (cell content pseudonymized, structure preserved)
   - Lists and numbering
   - Page layout (margins, orientation, page breaks)
   - Images (untouched — no text extraction from images)
3. **AC3:** Entity replacement maintains original formatting runs (if "Marie Dupont" is bold, "Leia Organa" is bold)
4. **AC4:** Output file naming: `{original_name}_pseudonymized.docx`
5. **AC5:** GUI "Save" dialog defaults to .docx when input was .docx
6. **AC6:** CLI `--output-format` flag: `auto` (match input), `txt` (force plaintext), `docx` (force DOCX)
7. **AC7:** Fallback: if format preservation fails for a section, log warning and output plaintext for that section
8. **AC8:** Error handling: complex DOCX features (tracked changes, comments, embedded objects) handled gracefully
9. **AC9:** No regression in existing .txt output path
10. **AC10:** Unit and integration tests for format preservation, entity replacement accuracy, and edge cases

### Integration Points

- `gdpr_pseudonymizer/utils/file_writer.py` — new `write_docx()` function
- `gdpr_pseudonymizer/core/processor.py` — format-aware output selection
- `gdpr_pseudonymizer/cli/commands/process.py` — `--output-format` flag

### Estimated Effort: 2-3 weeks

> **Estimate note (PM):** Bumped from 1-2 weeks due to run-splitting complexity. Simple paragraph replacement is fast, but cross-run entity replacement with formatting preservation is the long pole.

---

## Story 8.2: PDF Format Preservation

**As a** user who processes PDF reports,
**I want** the pseudonymized output to be a PDF that preserves the original layout,
**so that** I can share pseudonymized reports in their original format.

**Priority:** HIGH — Second most common format; technically more complex than DOCX

### Context

PDF format preservation is significantly harder than DOCX because PDF is a page-description language, not a document-description language. Text positions are absolute coordinates, and replacing text of different length disrupts layout. Two approaches:

- **Overlay approach:** Redact original text with white rectangles, then overlay pseudonymized text at the same position (using PyMuPDF/fitz). Simpler but may have visual artifacts.
- **Reconstruction approach:** Extract full structure, rebuild PDF with pseudonymized content. More faithful but extremely complex.

The overlay approach is recommended for v2.2 as the pragmatic choice.

### Acceptance Criteria

1. **AC1:** PDF input produces PDF output with pseudonymized content
2. **AC2:** Overlay approach: original entity text covered by white rectangle, pseudonym text placed at same position
3. **AC3:** Font matching: pseudonym text uses same font family and approximate size as original (best-effort)
4. **AC4:** Multi-page PDFs handled correctly
5. **AC5:** Tables in PDFs: entity text within table cells pseudonymized (best-effort, depends on PDF structure)
6. **AC6:** Output file naming: `{original_name}_pseudonymized.pdf`
7. **AC7:** GUI "Save" dialog defaults to .pdf when input was .pdf
8. **AC8:** CLI `--output-format` flag extended: `pdf` option added
9. **AC9:** Known limitation documented: scanned PDFs (image-based) are not supported for format preservation — plaintext output with warning
10. **AC10:** Known limitation documented: complex layouts (multi-column, floating text boxes) may have visual artifacts
11. **AC11:** Fallback: if overlay fails, output plaintext with warning
12. **AC12:** No regression in existing processing
13. **AC13:** Unit and integration tests for overlay placement, multi-page, and edge cases

### Integration Points

- `gdpr_pseudonymizer/utils/file_writer.py` — new `write_pdf()` function (PyMuPDF/fitz)
- `gdpr_pseudonymizer/core/processor.py` — entity position tracking for overlay placement
- `pyproject.toml` — PyMuPDF dependency (may already be present for input)

### Risk Note

PDF format preservation is inherently "best-effort." The overlay approach will work well for simple, text-based PDFs but may produce visual artifacts with complex layouts. This should be clearly communicated to users as a beta feature in v2.2.

### Pre-Sprint Spike Required: PyMuPDF License

**BLOCKER:** PyMuPDF (fitz) is licensed under AGPL-3.0. AGPL is a viral copyleft license — distributing standalone executables that link to PyMuPDF may impose AGPL obligations on the entire application. While this project is already open-source, verify:
1. AGPL compatibility with the project's current license (MIT/Apache/etc.)
2. Whether PyInstaller bundling constitutes "linking" under AGPL
3. If AGPL is incompatible, evaluate alternatives: `pypdf`, `pdfplumber`, or `reportlab` for the overlay approach

**This must be resolved before Story 8.2 development begins.** Do not discover this mid-sprint.

### Estimated Effort: 1-2 weeks

---

## Story 8.3: Auto-Update Mechanism

**As a** standalone executable user,
**I want** the application to notify me when a new version is available and offer to download it,
**so that** I always have the latest features, accuracy improvements, and security fixes.

**Priority:** MEDIUM — Important for long-term user retention; not blocking for format preservation

### Context

Auto-update for standalone executables (PyInstaller bundles) requires:
1. A version check against a known endpoint (GitHub Releases API)
2. A download mechanism for the platform-specific executable
3. A replacement/installation mechanism

For v2.2, the recommended approach is **notification + download link** (not silent auto-install), which is simpler and avoids code-signing complications with self-modifying executables.

### Acceptance Criteria

1. **AC1:** On launch, app checks GitHub Releases API for latest version (non-blocking, background)
2. **AC2:** If newer version available, shows a non-intrusive notification banner:
   - "Version X.Y.Z is available. [Download] [Dismiss] [Don't remind me for this version]"
3. **AC3:** "Download" opens the GitHub Releases page in the system browser (platform-specific asset)
4. **AC4:** "Don't remind me for this version" persists the dismissed version in config
5. **AC5:** Check frequency: once per day (not every launch)
6. **AC6:** Works offline gracefully — no error if network unavailable, just skips check
7. **AC7:** PyPI users (`pip install`) are excluded from auto-update checks (they use `pip install --upgrade`)
8. **AC8:** Settings toggle: "Check for updates automatically" (default: on)
9. **AC9:** No telemetry or analytics — only a GET request to GitHub API
10. **AC10:** GitHub API rate limiting handled: use conditional requests (`If-None-Match` / ETag headers) to avoid 60 req/hour unauthenticated limit. Cache last response locally; return cached version on 304 Not Modified.
11. **AC11:** Unit tests for version comparison, API response parsing, rate limiting, and notification logic

### Implementation Notes

- GitHub API endpoint: `https://api.github.com/repos/LioChanDaYo/RGPDpseudonymizer/releases/latest`
- Version comparison: semantic versioning (`packaging.version.Version`)
- Detection of PyInstaller bundle: `getattr(sys, '_MEIPASS', None)` — only show update notification in bundled mode
- Config key: `update_check_enabled`, `update_dismissed_version`, `update_last_check`

### Integration Points

- `gdpr_pseudonymizer/gui/updater.py` — new module for update checking
- `gdpr_pseudonymizer/gui/main_window.py` — notification banner integration
- `gdpr_pseudonymizer/gui/config.py` — update preferences persistence

### Estimated Effort: 1 week

---

## Story 8.4: v2.2 Release Preparation

**As a** product manager,
**I want** v2.2.0 published with format preservation and auto-update,
**so that** users can output pseudonymized documents in their original format.

**Priority:** HIGH — Gates the release

### Acceptance Criteria

1. **AC1:** Version bumped to `2.2.0` in `pyproject.toml`
2. **AC2:** CHANGELOG.md updated with v2.2.0 section
3. **AC3:** README updated: format preservation feature, auto-update mention
4. **AC4:** README.fr.md mirrored
5. **AC5:** Full regression suite passing
6. **AC6:** Standalone executables built and tested
7. **AC7:** Git tag `v2.2.0` triggers release workflow
8. **AC8:** Release notes highlight format preservation as headline feature
9. **AC9:** Known limitations for PDF preservation clearly documented

### Estimated Effort: 1-2 days

---

## Execution Sequence

```
Story 8.1 (DOCX Preservation)     --- Week 1-3 ---    More tractable, higher confidence (run-splitting adds time)
Story 8.2 (PDF Preservation)      --- Week 2-4 ---    Can overlap with 8.1 (independent). License spike MUST complete before start.
Story 8.3 (Auto-Update)           --- Week 3-4 ---    Independent, parallelizable
Story 8.4 (Release Prep)          --- Week 5-6 ---    Release gate
```

**Parallelization:** Stories 8.1, 8.2, and 8.3 are fully independent.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PDF overlay visual artifacts | HIGH | MEDIUM | Document as beta; offer plaintext fallback; improve iteratively |
| DOCX formatting run splitting | MEDIUM | MEDIUM | Test with diverse real-world DOCX files; fallback to plaintext per-paragraph |
| Entity position tracking across formats | MEDIUM | HIGH | Design position mapping carefully in 8.1; reuse pattern for 8.2 |
| Auto-update blocked by corporate firewalls | MEDIUM | LOW | Graceful offline handling; manual download always available |
| PyMuPDF license compatibility | LOW | HIGH | Verify AGPL/commercial license compatibility before implementation |

---

## Definition of Done

- [ ] All 4 stories completed with acceptance criteria met
- [ ] DOCX->DOCX and PDF->PDF output functional for common document types
- [ ] Auto-update notification working in standalone executables
- [ ] All quality gates green
- [ ] Test count >= v2.1 baseline, coverage >= 86%
- [ ] No regression in existing processing workflows
- [ ] v2.2.0 published on PyPI and GitHub Releases
- [ ] Known limitations clearly documented

---

## Explicitly Deferred (v3.0+)

| Item | Reason | Target |
|------|--------|--------|
| Excel format preservation (.xlsx->.xlsx) | v2.1 Story 7.4 adds Excel *input* support; format-preserving *output* (xlsx->xlsx) is included in 7.4 AC4 but may be deferred to v2.2 if 7.4 slips | v2.1 or v2.2 |
| Silent auto-install (replace running binary) | Code-signing complexity; notification approach is safer | v3.0+ |
| Scanned PDF OCR + pseudonymization | Requires OCR pipeline (Tesseract); out of scope | v3.0+ |
| Image-embedded text pseudonymization | Requires image processing; out of scope | v3.0+ |

---

## Architect Feasibility Review

**Reviewed by:** Winston (Architect) — 2026-03-06
**Verdict:** GO WITH SPIKE — PyMuPDF license is a hard blocker for Story 8.2

### Story-Level Assessment

| Story | Feasibility | Notes |
|-------|------------|-------|
| 8.1 DOCX Preservation | Yellow | `python-docx` is already a dependency. Cross-run entity replacement (entities spanning multiple XML formatting runs) is the hard part — requires run-splitting/merging with formatting preservation. 2-3 week estimate is realistic. Approach is sound. |
| 8.2 PDF Preservation | **Red — License Blocker** | PyMuPDF is AGPL-3.0. This project is MIT. AGPL is incompatible with MIT distribution — bundling PyMuPDF in standalone executables would impose AGPL obligations on the entire binary. Must resolve before development starts. |
| 8.3 Auto-Update | Green | Straightforward HTTP check against GitHub API. All building blocks exist (PySide6 for UI, `packaging` for version comparison). Rate limiting with ETag caching is well-documented. |
| 8.4 Release | Green | Standard. |

### Recommendation: Story 8.2 License Resolution

**Spike `pypdf` (BSD-licensed) overlay approach immediately.** `pypdf` supports text redaction and overlay but with less control than PyMuPDF. If `pypdf` cannot produce acceptable overlays, consider:

1. **Ship DOCX-only preservation in v2.2**, defer PDF to v2.3
2. **HTML-to-PDF rebuild via WeasyPrint (BSD)** — extract text + approximate structure, rebuild as a new PDF. Less faithful but license-clean.
3. **`reportlab` (BSD)** for PDF generation with overlaid pseudonymized text

PDF format preservation quality will be inherently limited regardless of library choice. The overlay approach produces visible artifacts on complex PDFs. Ensure the "best-effort / beta" framing is prominent in the UI, not just documentation.

---

**Document Status:** REVIEWED
**Created:** 2026-03-06
**Author:** Sarah (Product Owner)
**Reviewed by:** John (PM) — 2026-03-06
**Review Notes:** Approved with modifications: Story 8.1 estimate bumped to 2-3 weeks (run-splitting complexity), PyMuPDF license spike added as pre-sprint blocker for 8.2, GitHub API rate limiting AC added to 8.3, Excel deferred table entry corrected. Total epic duration adjusted to 5-7 weeks.
