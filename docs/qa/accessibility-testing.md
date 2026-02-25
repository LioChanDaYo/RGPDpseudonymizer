# Accessibility Testing Guide — Manual NVDA & DPI Scaling

**Project:** GDPR Pseudonymizer v2.0
**Date:** 2026-02-24
**Purpose:** Manual testing procedures for NVDA screen reader and DPI scaling (Tasks 5 & 8)

---

## Task 5: NVDA Screen Reader Testing (AC2)

### Prerequisites

**Software Required:**
- NVDA (NonVisual Desktop Access) — Free screen reader for Windows
- Download from: https://www.nvaccess.org/download/
- Recommended version: NVDA 2024.x or later
- GDPR Pseudonymizer v2.0 (current build)

**Test Environment:**
- Windows 10 or Windows 11
- Standard 1080p or 1440p display (100% DPI scale)
- Audio speakers or headphones (for screen reader output)

### Test Procedure

#### 1. NVDA Setup

1. Install NVDA if not already installed
2. Launch NVDA (Ctrl+Alt+N from desktop or from Start menu)
3. Verify NVDA is speaking (should announce "NVDA started")
4. Configure NVDA speech rate: NVDA menu → Preferences → Settings → Speech → Rate (set to 50 for easier testing)

#### 2. Launch Application

```bash
# Launch GDPR Pseudonymizer GUI
poetry run gdpr-gui

# OR if installed via pip:
gdpr-gui
```

3. NVDA should announce the main window title: "GDPR Pseudonymizer"

#### 3. Home Screen Testing

**Test: Navigation and Widgets**

1. Press Tab repeatedly to navigate through home screen
   - **Expected announcements** (in order):
     - "Drop zone, button" (or similar accessible name)
     - "Ouvrir le traitement par lot, button"
     - Recent file buttons (if any exist)

2. Navigate to drop zone
   - Press Tab until NVDA announces the drop zone
   - **Verify announcement**: Should say "Zone de dépôt de fichier" or similar
   - Press Space to activate (should open file dialog)
   - Cancel the dialog

3. Navigate to batch button
   - Press Tab until NV DA announces "Ouvrir le traitement par lot, button"
   - Press Space to activate (should navigate to batch screen)
   - Press Ctrl+, to return to home (opens settings, then cancel)

**Expected Results:**
- ✅ All interactive widgets announced with descriptive labels
- ✅ Tab order is logical (drop zone → batch button → recent files)
- ✅ Button activation works via Space or Enter

**Known Limitations:**
- Recent file list may not have detailed accessible labels (each file should be announced)

#### 4. Processing Screen Testing

**Test: Progress Announcements**

1. Open a test document (use test file: `tests/data/sample_document.txt`)
   - From home screen, drag and drop file onto drop zone OR press Tab → Space → Select file
   - Enter passphrase in dialog (or use cached passphrase)
   - Navigate to processing screen

2. Listen to NVDA announcements during processing
   - **Expected announcements**:
     - "Progression de l'analyse, progress bar, X percent"
     - Phase label updates ("Initialisation", "Détection", "Finalisation")
     - "Annuler le traitement, button" (cancel button)
     - "Continuer vers la validation, button" (after completion)

3. Press Tab to navigate between cancel and continue buttons
   - **Verify**: NVDA announces button names and roles

**Expected Results:**
- ✅ Progress bar value announced as percentage
- ✅ Phase label changes announced
- ✅ Cancel and continue buttons have descriptive names

#### 5. Validation Screen Testing (CRITICAL)

**Test: Entity Announcements and Keyboard Navigation**

1. From processing screen, press Tab to Continue button and activate (Space or Enter)
   - Should navigate to validation screen

2. Test entity editor navigation (Tab to editor area first)
   - Press Escape to exit any dialog
   - Click inside the document editor area (or Tab until editor is focused)
   - Press Space to enter navigation mode
   - **Expected announcement**: "Navigation mode activated" (or similar)

3. Navigate entities with Tab/Shift+Tab
   - Press Tab to move to next entity
   - **Expected announcement**: "PERSON: Jean Dupont, pending" (or similar with entity type, text, and state)
   - Press Tab again to move to next entity
   - **Expected announcement**: Next entity's details

4. Accept/reject entities with Enter/Delete
   - Navigate to an entity (Tab until on an entity)
   - Press Enter to accept
   - **Expected announcement**: "Entity accepted" or "PERSON: Jean Dupont, accepted"
   - Navigate to another entity
   - Press Delete to reject
   - **Expected announcement**: "Entity rejected" or similar

5. Test bulk actions
   - Press Ctrl+Shift+A to accept all pending entities
   - **Expected announcement**: "X entités acceptées" (X entities accepted)
   - Press Ctrl+Z to undo
   - **Expected announcement**: "Annulé" (Undone)

6. Test entity panel (right sidebar)
   - Press Tab repeatedly until sidebar list is focused
   - **Expected announcement**: "Liste des entités détectées" (or similar)
   - Press Up/Down arrows to navigate list
   - **Expected announcements**: Entity details for each item (type, name, status, pseudonym)

**Expected Results:**
- ✅ Entity editor announces entity details dynamically
- ✅ Entity type, name, and status are spoken
- ✅ Keyboard shortcuts work (Tab, Enter, Delete, Ctrl+Shift+A/R, Ctrl+Z/Y)
- ✅ Entity panel list items have detailed announcements
- ✅ Bulk action confirmations are announced

**Known Issues to Document:**
- If entity announcements are missing or incomplete, note which details are missing
- If navigation mode doesn't work, document the error

#### 6. Results Screen Testing

**Test: Document Preview and Buttons**

1. From validation screen, press Tab to "Finaliser" button and activate
   - Confirm finalization in dialog (Tab to Confirmer button, press Enter)
   - Wait for finalization to complete
   - Should navigate to results screen

2. Test results screen navigation
   - Press Tab to navigate through results screen
   - **Expected announcements** (in order):
     - "Aperçu du document pseudonymisé, edit text" (preview text area)
     - "Nouveau document, button"
     - "Enregistrer le document, button"

3. Test preview text area
   - Tab to preview area
   - Press Down/Up arrows to navigate through pseudonymized text
   - **Expected**: NVDA reads text line by line (entity highlights may not be announced, that's acceptable)

**Expected Results:**
- ✅ Preview text area has accessible name
- ✅ Buttons have descriptive labels
- ✅ Preview text is readable by NVDA

#### 7. Batch Screen Testing

**Test: Batch Processing Workflow**

1. Navigate to batch screen (Ctrl+B from home OR menu → Fichier → Traitement par lot)

2. Test selection phase widgets
   - Press Tab to navigate through batch setup
   - **Expected announcements** (in order):
     - "Dossier source, edit text"
     - "Parcourir les dossiers, button"
     - "Ajouter des fichiers, button"
     - "Liste des fichiers à traiter, table"
     - "Dossier de sortie, edit text"
     - "Parcourir le dossier de sortie, button"
     - "Démarrer le traitement par lot, button"

3. Test batch processing (if time permits)
   - Add a test folder with 2-3 sample files
   - Start batch processing
   - **Expected announcements during processing**:
     - "Progression du traitement par lot, progress bar, X percent"
     - "Progression par document, table" (doc table)
     - "Suspendre le traitement, button" (pause button)
     - "Annuler le traitement par lot, button" (cancel button)

**Expected Results:**
- ✅ All form fields have descriptive labels
- ✅ Tables have accessible names
- ✅ Progress updates are announced
- ✅ Pause/cancel buttons are labeled

#### 8. Database & Settings Screens

**Test: Form Fields and Tables**

**Database Screen:**
1. Navigate to database screen (Ctrl+D OR menu → Données → Base de données)
2. Press Tab to navigate
   - **Expected announcements**:
     - "Chemin de la base de données, combo box"
     - "Parcourir, button"
     - "Ouvrir, button"
     - "Recherche dans la base, edit text"
     - "Type d'entité, combo box"
     - "Table des correspondances, table"
     - "Supprimer, button"
     - "Exporter en CSV, button"

**Settings Screen:**
1. Navigate to settings (Ctrl+, OR menu → Édition → Paramètres)
2. Press Tab to navigate
   - **Expected announcements**:
     - "Langue de l'interface, combo box"
     - "Thème par défaut, combo box"
     - "Nombre de processus parallèles, spin box"
     - "Continuer en cas d'erreur, check box, checked" (or unchecked)

**Expected Results:**
- ✅ All form widgets have descriptive accessible names
- ✅ Combo boxes announce current selection
- ✅ Checkboxes announce checked/unchecked state

#### 9. Global Keyboard Shortcuts

**Test: Global Navigation**

1. From any screen, test global shortcuts:
   - Press F1 → Should open keyboard shortcuts help dialog
   - Press Escape → Should close dialog
   - Press Ctrl+O → Should open file dialog
   - Press Escape → Should cancel dialog
   - Press Ctrl+, → Should navigate to settings
   - Press Ctrl+D → Should navigate to database screen

2. Verify NVDA announces screen changes
   - **Expected**: "GDPR Pseudonymizer — [Screen Name]" announced when navigating

**Expected Results:**
- ✅ All keyboard shortcuts work
- ✅ Screen changes are announced
- ✅ Help dialog is accessible

### Test Report Template

After completing testing, document results in the following format:

```markdown
## NVDA Testing Results

**Tester:** [Your Name]
**Date:** [Date]
**NVDA Version:** [e.g., 2024.1]
**Application Version:** v2.0.0

### Summary

- **Overall Status:** ✅ PASS / ⚠️ PARTIAL PASS / ❌ FAIL
- **Critical Issues:** [None / List critical issues]
- **Recommendations:** [None / List improvements]

### Detailed Results

| Screen | Status | Notes |
|--------|--------|-------|
| Home | ✅ PASS | All widgets announced correctly |
| Processing | ✅ PASS | Progress announcements working |
| Validation | ⚠️ PARTIAL PASS | Entity announcements missing [detail] |
| Results | ✅ PASS | Preview accessible |
| Batch | ✅ PASS | All form fields labeled |
| Database | ✅ PASS | Table navigation works |
| Settings | ✅ PASS | Form accessible |

### Critical Issues

1. **[Issue Title]**
   - **Screen:** [Screen name]
   - **Steps to reproduce:** [Steps]
   - **Expected:** [What should happen]
   - **Actual:** [What actually happened]
   - **Severity:** CRITICAL / HIGH / MEDIUM / LOW

### Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
```

---

## Task 8: DPI Scaling Testing (AC3)

### Prerequisites

**Hardware:**
- Windows 10 or Windows 11 PC
- Display capable of at least 1920x1080 resolution

**Software:**
- GDPR Pseudonymizer v2.0 (current build)

### Test Procedure

#### 1. Set DPI Scaling to 100% (Baseline)

1. Open Windows Settings → System → Display
2. Under "Scale and layout", set scaling to 100%
3. Click "Apply" (may require signing out and back in)
4. Restart if prompted

#### 2. Launch Application at 100% DPI

```bash
poetry run gdpr-gui
```

5. Document baseline behavior:
   - Take screenshot of home screen (Win+Shift+S)
   - Measure approximate widget sizes (eyeball or use ruler tool)
   - Note if any text is clipped or truncated
   - Verify all screens are visible and usable

**Expected Results at 100% DPI:**
- ✅ All text readable
- ✅ No text clipping or truncation
- ✅ Buttons and widgets are clickable
- ✅ Layout is balanced and aesthetically pleasing

#### 3. Test at 125% DPI

1. Close application
2. Open Windows Settings → System → Display
3. Set scaling to 125%
4. Sign out and sign back in (required for DPI change)
5. Relaunch application: `poetry run gdpr-gui`

6. **Test all screens** (Home, Processing, Validation, Results, Batch, Database, Settings)
   - Take screenshots of each screen
   - Check for:
     - **Text clipping**: Is any text cut off or truncated?
     - **Overlapping widgets**: Do any widgets overlap or obscure each other?
     - **Layout breaking**: Does the layout look correct?
     - **Scrollbars**: Are scrollbars necessary where they weren't before?

**Expected Results at 125% DPI:**
- ✅ All text readable and properly sized
- ✅ No text clipping or truncation
- ✅ No overlapping widgets
- ✅ Layout adapts gracefully (may use more vertical space)

#### 4. Test at 150% DPI

1. Repeat steps above but set scaling to 150%
2. Sign out and sign back in
3. Relaunch application
4. Test all screens again

**Expected Results at 150% DPI:**
- ✅ All text readable and properly sized
- ✅ No text clipping or truncation
- ✅ No overlapping widgets
- ✅ Layout may require vertical scrolling but remains functional

#### 5. Test at 200% DPI

1. Repeat steps above but set scaling to 200%
2. Sign out and sign back in
3. Relaunch application
4. Test all screens again

**Expected Results at 200% DPI:**
- ✅ All text readable and properly sized
- ✅ No text clipping or truncation
- ✅ No overlapping widgets
- ✅ Layout requires vertical scrolling but remains fully functional

### Specific Tests for Each Screen

#### Home Screen
- Check: Drop zone size, batch button text, recent files list
- **Critical check**: Drop zone should scale proportionally, text should not clip

#### Processing Screen
- Check: Progress bar width, phase label text, button sizes
- **Critical check**: Progress bar should remain visible and not overflow

#### Validation Screen
- Check: Editor pane, entity panel, splitter between panes, action bar buttons
- **Critical check**: Entity text in editor should be readable at all sizes

#### Results Screen
- Check: Entity summary cards, preview text area, buttons
- **Critical check**: Preview text should wrap properly, not clip

#### Batch Screen
- Check: File table columns, folder input fields, buttons
- **Critical check**: Table columns should remain readable, not overlap

#### Database Screen
- Check: DB combo box, search field, entity table columns
- **Critical check**: Table should remain usable, columns should resize

#### Settings Screen
- Check: Form labels, combo boxes, spinners, checkboxes
- **Critical check**: All form elements should remain aligned with labels

### Known Qt DPI Behavior

**Qt 6 DPI Handling:**
- Qt 6 handles DPI scaling automatically for most widgets
- Font sizes scale automatically
- Layout managers (QVBoxLayout, QHBoxLayout, QGridLayout) handle scaling
- Fixed pixel sizes DO NOT scale (avoid using `setFixedSize()` except where necessary)

**Potential Issues:**
- Custom painted widgets (e.g., `StepIndicator`) may not scale correctly if using fixed pixel sizes
- Icon sizes may need adjustment for high DPI
- Monospace fonts (e.g., Consolas in preview) may look disproportionate at high DPI

### Test Report Template

```markdown
## DPI Scaling Test Results

**Tester:** [Your Name]
**Date:** [Date]
**Application Version:** v2.0.0
**Display:** [e.g., 1920x1080, 27" monitor]

### Summary

| DPI Scale | Status | Critical Issues |
|-----------|--------|-----------------|
| 100% | ✅ PASS | None |
| 125% | ✅ PASS | None |
| 150% | ⚠️ PARTIAL PASS | Text clipping in [location] |
| 200% | ❌ FAIL | Layout breaks in [screen] |

### Detailed Results

**100% DPI (Baseline):**
- All screens functional
- No issues detected
- Screenshot: [attach screenshot]

**125% DPI:**
- Home screen: ✅ PASS
- Processing screen: ✅ PASS
- Validation screen: ✅ PASS
- Results screen: ✅ PASS
- Batch screen: ✅ PASS
- Database screen: ✅ PASS
- Settings screen: ✅ PASS
- Screenshot: [attach screenshots]

**150% DPI:**
- Home screen: ✅ PASS
- Processing screen: ⚠️ PARTIAL PASS — Progress bar text slightly clipped
- Validation screen: ✅ PASS
- Results screen: ✅ PASS
- Batch screen: ✅ PASS
- Database screen: ✅ PASS
- Settings screen: ✅ PASS
- Screenshot: [attach screenshots]

**200% DPI:**
- Home screen: ✅ PASS
- Processing screen: ❌ FAIL — Phase label truncated
- Validation screen: ✅ PASS (requires vertical scrolling)
- Results screen: ✅ PASS
- Batch screen: ✅ PASS (table columns adjust)
- Database screen: ❌ FAIL — Search field overlaps type filter
- Settings screen: ✅ PASS
- Screenshot: [attach screenshots]

### Issues Found

1. **Progress Bar Text Clipping at 150% DPI**
   - **Screen:** Processing
   - **Description:** Phase label "Initialisation..." truncated to "Initia..."
   - **Severity:** MEDIUM
   - **Recommendation:** Increase QLabel width or use elided text

2. **Search Field Overlap at 200% DPI**
   - **Screen:** Database
   - **Description:** Search field and type filter combo box overlap by ~10px
   - **Severity:** HIGH
   - **Recommendation:** Review HBoxLayout spacing or use QSizePolicy.Expanding

### Recommendations

1. Test with QT_SCALE_FACTOR environment variable for fractional scaling (e.g., 1.5x)
2. Consider adding maximum width constraints to prevent excessive horizontal expansion
3. Review StepIndicator custom painting for DPI-aware sizing
```

### Additional Testing (Stretch)

If time permits, test with:
- **Qt environment variable:** `QT_SCALE_FACTOR=1.5 poetry run gdpr-gui` (fractional scaling)
- **4K display:** 3840x2160 at 150% or 200% DPI
- **Ultrawide display:** 3440x1440 at 100% or 125% DPI

---

## Testing Checklist

Before marking Tasks 5 and 8 complete, ensure:

**Task 5 (NVDA Testing):**
- [ ] NVDA installed and configured
- [ ] All 7 screens tested (Home, Processing, Validation, Results, Batch, Database, Settings)
- [ ] Entity announcements verified on Validation screen
- [ ] Progress updates verified
- [ ] Keyboard shortcuts verified (F1, Ctrl+O, Ctrl+D, Ctrl+,)
- [ ] Test report documented in this file or separate report file
- [ ] Critical issues logged (if any) with severity and recommendations

**Task 8 (DPI Scaling):**
- [ ] Tested at 100% DPI (baseline)
- [ ] Tested at 125% DPI
- [ ] Tested at 150% DPI
- [ ] Tested at 200% DPI
- [ ] Screenshots taken for each DPI scale
- [ ] All 7 screens tested at each DPI level
- [ ] Layout issues documented (if any)
- [ ] Test report completed with screenshots and issue descriptions

---

## Success Criteria

**Task 5 Complete When:**
- NVDA announces all interactive widgets with descriptive labels
- Entity validation workflow is fully navigable via keyboard
- Progress updates are announced during processing/batch operations
- No critical accessibility issues found
- Report documented with pass/fail for each screen

**Task 8 Complete When:**
- All screens functional at 100%, 125%, 150% DPI
- No critical layout breaking at 200% DPI (minor clipping acceptable)
- Text remains readable at all DPI scales
- No overlapping widgets that block functionality
- Report documented with screenshots and any issues noted

---

## Resources

**NVDA Documentation:**
- Official NVDA User Guide: https://www.nvaccess.org/files/nvda/documentation/userGuide.html
- Keyboard shortcuts: https://www.nvaccess.org/files/nvda/documentation/keyCommands.html

**Windows DPI Settings:**
- Microsoft DPI scaling guide: https://docs.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows

**Qt DPI Scaling:**
- Qt High DPI documentation: https://doc.qt.io/qt-6/highdpi.html
- PySide6 DPI scaling: https://doc.qt.io/qtforpython-6/overviews/scaledpi.html
