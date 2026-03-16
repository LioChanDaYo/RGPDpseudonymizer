# GUI User Guide

GDPR Pseudonymizer v2.0 includes a desktop GUI application for visual entity validation and document processing. This guide covers all GUI features and workflows.

---

## Getting Started

### Launching the GUI

**From PyPI install:**
```bash
pip install gdpr-pseudonymizer[gui]
gdpr-pseudo-gui
```

**From source:**
```bash
poetry run gdpr-pseudo-gui
```

**Standalone executable:** Double-click the downloaded executable (Windows .exe, macOS .dmg, Linux AppImage). No Python required.

On first launch, the application auto-detects your system language (French or English) and applies the default light theme.

### Home Screen

The home screen is your starting point. It provides:

- **Drag-and-drop zone** — Drop `.txt`, `.md`, `.pdf`, `.docx`, `.xlsx`, or `.csv` files to start processing
- **Recent files list** — Quick access to previously processed documents
- **Batch processing card** — Click to open the batch processing workflow
- **Menu bar** — Access all features via File, View, Tools, and Help menus

<!-- TODO: Add home screen screenshot -->

---

## Single Document Workflow

### Step 1: Open a Document

- **Drag and drop** a file onto the home screen, or
- Use **File > Open** (Ctrl+O), or
- Click a recent file from the list

### Step 2: Enter Passphrase

A passphrase dialog appears for the mapping database:

- Enter a passphrase (minimum 12 characters)
- The app auto-detects existing `.gdpr-pseudo.db` files in the document directory and remembers your last-used database across sessions
- Check "Remember" to cache the passphrase for the session
- Choose "Create new" to start a fresh mapping database

> **Tip:** The previously selected database is pre-selected automatically on the next launch. Your selection is saved in `.gdpr-pseudo.yaml` as `default_db_path`.

### Step 3: Processing

The processing screen shows a 3-phase progress bar:

1. **File reading** (0-10%) — Loading and parsing the document
2. **Model loading** (10-40%) — Loading the spaCy French NLP model
3. **NLP detection** (40-100%) — Detecting entities in the text

If the spaCy model isn't installed, the app automatically downloads it with a progress indicator.

### Step 4: Entity Validation

After detection, the validation screen opens with a split-pane layout:

- **Document editor** (65%) — Your text with color-coded entity highlights
- **Entity panel** (35%) — Sidebar listing all detected entities grouped by type

See [Entity Validation](#entity-validation) below for detailed instructions.

### Step 5: Results & Save

After finalizing validation, the results screen shows:

- Pseudonymized document preview with highlighted pseudonyms
- Entity type breakdown (PERSON, LOCATION, ORG with color indicators)
- **"Enregistrer sous..."** button to save the pseudonymized document

---

## Entity Validation

The validation screen is where you review and confirm all detected entities.

### Entity Colors

Entities are color-coded by type (designed to be color-blind safe):

| Type | Light Theme | Dark Theme |
|------|------------|------------|
| **PERSON** | Blue background | Blue background |
| **LOCATION** | Orange background | Orange background |
| **ORG** | Purple background | Purple background |
| **Rejected** | Red with strikethrough | Red with strikethrough |

### Entity Status Icons (Sidebar)

| Icon | Meaning |
|------|---------|
| ○ | Pending (not yet reviewed) |
| ✓ | Confirmed / Added |
| ✗ | Rejected |
| ✎ | Modified |

Known entities (already in the database) show a "déjà connu" badge.

### Reviewing Entities

**With the mouse:**

1. **Click an entity** in the editor to select it and highlight it in the sidebar
2. **Click an entity** in the sidebar to scroll to it in the editor
3. **Right-click an entity** in the editor for a context menu:
   - Accept
   - Reject
   - Modify text...
   - Change pseudonym
   - Change type (PERSON, LOCATION, ORG)
4. **Right-click selected text** to add it as a new entity

**With the keyboard (Navigation Mode):**

1. Press **Enter** to enter navigation mode (focuses the first pending entity)
2. Use **Tab** / **Shift+Tab** to move between entities (only active while in navigation mode)
3. Press **Enter** to accept the current entity
4. Press **Delete** to reject the current entity
5. Press **Shift+F10** or the **Menu key** to open the context menu
6. Press **Escape** to exit navigation mode

> **Note:** Tab and Shift+Tab navigate entities only when navigation mode is active. Outside navigation mode they follow standard focus traversal. Press **F1** to open the keyboard shortcuts help dialog listing all shortcuts.

### Bulk Actions

**Using the sidebar:**

- Check multiple entities using their checkboxes
- Click **"Accepter la sélection"** or **"Rejeter la sélection"**
- Click **"Tout accepter : PERSONNES"** (or LOCATIONS/ORGANISATIONS) to accept all pending of a type
- Click **"Accepter les déjà connues"** to accept all known entities

**Using keyboard shortcuts:**

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+A | Accept all pending entities |
| Ctrl+Shift+R | Reject all pending entities |
| Ctrl+Z | Undo last action |
| Ctrl+Shift+Z / Ctrl+Y | Redo |
| Ctrl+F | Focus the entity filter field |

### Filtering Entities

Use the filter field at the top of the sidebar to search entities by text. Type to filter in real-time; use the clear button to reset.

### Hide Rejected / Hide Confirmed

- Check **"Hide rejected"** to hide strikethrough rejected entities in the editor.
- Check **"Hide confirmed"** ("Masquer les validées") to hide already-accepted and known entities, letting you focus on remaining pending entities.

### Finalizing

When all entities have been reviewed (the pending counter shows "Toutes vérifiées"):

1. Click **"Finaliser"** at the bottom of the screen
2. A summary dialog confirms your changes
3. The document is pseudonymized and the results screen appears

---

## Batch Processing

### Step 1: Select Files

1. From the home screen, click the batch processing card, or use **File > Open Folder** (Ctrl+Shift+O)
2. Choose a folder or select multiple files
3. The app discovers all supported files (`.txt`, `.md`, `.pdf`, `.docx`, `.xlsx`, `.csv`), excluding already-pseudonymized files (`*_pseudonymized*`)
4. Set the output directory (defaults to `{input}/_pseudonymized/`)
5. Optionally enable **"Valider les entités par document"** to review entities per document

### Step 2: Processing Dashboard

The batch screen shows:

- **Overall progress bar** with percentage
- **Per-document table** with status transitions: En attente → En cours → Traité / Erreur
- **Estimated time remaining**
- **Pause/Resume** and **Cancel** controls

### Step 3: Per-Document Validation (Optional)

If validation is enabled, the batch pauses after each document's entity detection:

- A "Document X de Y" indicator shows your position
- Use **Précédent/Suivant** buttons to navigate between documents
- Review and validate entities as in single-document mode
- Click **"Valider et continuer"** to proceed to the next document
- Click **"Valider et terminer"** on the last document
- Click **"Annuler le lot"** to cancel remaining documents

### Step 4: Summary & Export

After all documents are processed:

- Summary cards show: documents processed, entities detected, new/reused pseudonyms, errors
- Per-document results table with status
- **Export** button to save a batch report as `.txt`

---

## Database Management

Access via **Tools > Database Management** from the menu bar.

### Viewing Entities

- Browse all entity mappings stored in the database
- Filter by type (PERSON, LOCATION, ORG)
- Search by entity name
- View: entity ID, type, full name, pseudonym, first seen date

### Deleting Entities (GDPR Article 17)

1. Select entities using checkboxes
2. Click **"Supprimer"**
3. Confirm in the dialog
4. An ERASURE audit log entry is created for compliance

### Exporting

Click **"Exporter CSV"** to export the entity list as a CSV file with columns: entity_id, entity_type, full_name, pseudonym_full, first_seen.

### Recent Databases

The app remembers the last 5 databases opened (displayed in a dropdown). Database info shows: creation date, entity count, last operation.

---

## Settings

Access via **Tools > Settings** (Ctrl+,).

### Appearance

- **Theme:** Light, Dark, or High Contrast
- **Language:** French or English (changes apply immediately, no restart)

### Processing Defaults

- **Pseudonym theme:** Neutral, Star Wars, or LOTR
- **NLP model:** spaCy (default)
- **Default output directory**

### Batch Options

- **Workers:** 1-8 parallel workers (use 1 for interactive validation)
- **Default theme:** Pseudonym theme for batch processing

---

## Keyboard Shortcuts Reference

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| Ctrl+Shift+O | Open folder (batch) |
| Ctrl+Q | Quit application |
| Ctrl+, | Open settings |
| F1 | Keyboard shortcuts help |
| F11 | Toggle fullscreen |

### Validation Screen

| Shortcut | Action |
|----------|--------|
| Enter | Enter navigation mode / Accept entity |
| Tab | Next entity |
| Shift+Tab | Previous entity |
| Delete | Reject entity |
| Escape | Exit navigation mode |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z / Ctrl+Y | Redo |
| Ctrl+F | Filter entities |
| Ctrl+Shift+A | Accept all pending |
| Ctrl+Shift+R | Reject all pending |
| Shift+F10 / Menu key | Entity context menu |

### Editor

| Shortcut | Action |
|----------|--------|
| Ctrl++ | Zoom in |
| Ctrl+- | Zoom out |

---

## Accessibility Features

GDPR Pseudonymizer v2.0 meets **WCAG 2.1 Level AA** accessibility standards.

### Keyboard Navigation

All interactive elements are accessible via keyboard. Focus indicators (2px solid outline) are visible on all controls. In high contrast mode, focus indicators are enhanced (3px bold yellow).

### Screen Reader Support

The application is compatible with screen readers (NVDA on Windows, VoiceOver on macOS):

- All buttons and controls have accessible names and descriptions
- Entity editor announces: type, text, and status for each entity
- Entity panel announces: type, text, known status, validation status, and pseudonym

### High Contrast Mode

- Automatic detection of OS high contrast settings
- Manual selection via **View > High Contrast** theme
- 21:1 contrast ratio for critical elements
- Bold font weights for improved readability
- Bright yellow focus indicators on pure black background

### Color-Blind Safe Design

Entity colors are chosen to be distinguishable without relying on red/green contrast:
- Blue (PERSON), Orange (LOCATION), Purple (ORG)

### DPI Scaling

The application supports display scaling from 100% to 200%. Minor layout adjustments may occur at 200% DPI (known limitation UI-001), but all functionality remains accessible.
