# Validation UI Quick Reference Guide

**Story 6.4**: Visual Entity Validation Interface
**For**: Manual performance testing and user guidance

---

## 🖼️ Screen Layout

```
┌─────────────────────────────────────────────┬────────────────────────────┐
│  ☐ Masquer les rejetées                    │ Entités (100)  Reste : 85  │
├─────────────────────────────────────────────┤────────────────────────────┤
│                                             │ ── PERSONNES (45) ─────    │
│  DOCUMENT VIEW (Left Side)                 │ ○ Jean Dupont              │
│                                             │    → Pierre Lambert        │
│  Le contrat entre Jean Dupont résidant     │ ○ Marie Martin             │
│  au 15 rue de la Paix, Paris et la         │    → Claire Dubois         │
│  société Nexia Corp...                      │ ✓ Sophie Bernard (known)   │
│                                             │    → Elise Fournier        │
│  [Entities are highlighted in color]       │                            │
│                                             │ ── LIEUX (30) ─────────    │
│                                             │ ○ Paris                    │
│                                             │    → Lyon                  │
│                                             │                            │
│                                             │ ── ORGANISATIONS (25) ──   │
│                                             │ ○ Nexia Corp               │
│                                             │    → TechStart SA          │
├─────────────────────────────────────────────┴────────────────────────────┤
│                    [◀ Retour]                          [Finaliser ▶]     │
├──────────────────────────────────────────────────────────────────────────┤
│ 15/100 entités traitées | 10 acceptées, 3 rejetées, 2 modifiées         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ How to Accept/Reject Entities

### **Method 1: Right-Click Context Menu** ⭐ PRIMARY

**To Accept an Entity:**
1. **Right-click** on a highlighted entity in the document (left side)
2. Click **"Accepter"** from the menu
3. Status changes: ○ → ✓

**To Reject an Entity:**
1. **Right-click** on the entity
2. Click **"Rejeter"**
3. Entity turns red with strikethrough (or disappears if "Masquer les rejetées" is checked)

**Other Context Menu Options:**
- **"Modifier le texte..."** — Edit entity text (opens dialog)
- **"Changer le pseudonyme"** — Enter custom pseudonym
- **"Changer le type >"** — Submenu: Personne / Lieu / Organisation

---

### **Method 2: Keyboard Navigation Mode** ⚡ POWER USER

**Activate Navigation Mode:**
1. Click in the document editor (left side)
2. Press **Enter** key
3. Border turns blue → you're in navigation mode
4. First pending entity is highlighted

**Navigate & Accept:**
- **Tab** — Next entity
- **Shift+Tab** — Previous entity
- **Enter** — Accept current entity + auto-advance to next
- **Delete** — Reject current entity + auto-advance to next
- **Escape** — Exit navigation mode

**Tip**: This is MUCH faster for processing many entities!

---

### **Method 3: Sidebar Panel Actions**

**Individual Entity:**
1. Click entity in sidebar (right side)
2. Document scrolls to that entity
3. Then use Method 1 (right-click) or Method 2 (keyboard)

**Bulk Actions** (Bottom of Sidebar):
- **"Accepter la sélection (N)"** — Check multiple entities → bulk accept
- **"Rejeter la sélection (N)"** — Check multiple entities → bulk reject
- **"Tout accepter: PERSONNES"** — Accept all pending of current type
- **"Accepter les déjà connues"** — Auto-accept all entities found in database

---

## 🎨 Entity Color Coding

| Color | Meaning |
|-------|---------|
| **Blue** (light bg) | PERSON entity |
| **Green** (light bg) | LOCATION entity |
| **Orange** (light bg) | ORGANISATION entity |
| **Red + strikethrough** | Rejected entity |
| **Faded color (50% opacity)** | "déjà connu" (known from database) |

**Hover over any entity** → Tooltip shows:
- Entity type
- Suggested pseudonym
- Confidence score

---

## 🚫 What Left-Click Does

**Left-click on entity** → **Selects** it (sidebar scrolls to entity)

⚠️ **Left-click does NOT accept the entity!**

**Why?** To avoid accidental accepts. You must:
- Right-click → Accepter
- OR keyboard: Enter → Tab/Enter to accept

---

## ⌨️ Keyboard Shortcuts Summary

| Shortcut | Action |
|----------|--------|
| **Enter** | Enter/exit navigation mode |
| **Tab** | Next entity (in nav mode) |
| **Shift+Tab** | Previous entity (in nav mode) |
| **Enter** (in nav mode) | Accept entity + advance |
| **Delete** (in nav mode) | Reject entity + advance |
| **Ctrl+Z** | Undo last action |
| **Ctrl+Shift+Z** or **Ctrl+Y** | Redo |
| **Ctrl+F** | Focus sidebar filter field |
| **Escape** | Exit navigation mode |

---

## 📋 Typical Workflow

### **Quick Workflow** (Mouse + Keyboard Mix)

1. Look at document, find highlighted entity
2. **Right-click** entity → **Accepter** (or Rejeter)
3. Repeat for next entity
4. Use **"Accepter les déjà connues"** for known entities (saves time!)
5. Click **"Finaliser"** when done

### **Power User Workflow** (Keyboard Only) ⚡

1. Click in document
2. Press **Enter** (enter navigation mode)
3. **Tab** through entities
4. **Enter** to accept, **Delete** to reject
5. Repeat until "Reste : 0"
6. **Escape** → Click **"Finaliser"**

### **Bulk Workflow** (For Many Similar Entities)

1. In sidebar, check multiple entities of same type
2. Click **"Accepter la sélection"**
3. Or use **"Tout accepter: PERSONNES"** for all pending persons
4. Review exceptions individually

---

## 🎯 Performance Testing Tips

When testing with `doc5_100entities.txt`:

1. **Don't validate all 100 entities** — not needed for performance test!
2. **Just verify UI responsiveness**:
   - Accept/reject 5-10 entities
   - Test scrolling (mouse wheel, Page Up/Down)
   - Click different entities to test selection speed
   - Try bulk action with 5+ entities

3. **What to look for**:
   - ✅ Context menu appears instantly on right-click
   - ✅ Status icon changes immediately after accept/reject
   - ✅ Scrolling is smooth (no lag or stutter)
   - ✅ Sidebar syncs instantly when clicking document entities

---

## 🐛 Troubleshooting

**"I right-clicked but no menu appears"**
- Make sure you clicked directly on a **highlighted entity** (colored text)
- Try clicking in the middle of the entity text, not at the edges

**"Left-click does nothing"**
- Correct! Left-click only **selects** the entity (sidebar scrolls)
- To **accept**, you must **right-click → Accepter**

**"Entities aren't highlighted"**
- Check if spaCy model is loaded (detection phase completed?)
- Look at status bar — should show "X/Y entités traitées"

**"I want to accept all entities at once"**
- Use **"Tout accepter: PERSONNES"** for all persons
- Repeat for LIEUX, ORGANISATIONS
- Or check multiple entities → **"Accepter la sélection"**

**"Navigation mode (Enter key) doesn't work"**
- Make sure document editor (left side) is **focused** first (click in it)
- Then press Enter — you should see blue border appear

---

## 📸 Visual Clues

**When you're doing it right:**
- Right-click → menu appears with "Accepter" at top
- After accept → status icon changes from ○ to ✓
- Sidebar "Reste : X" counter decreases
- Bottom status bar updates: "15/100 entités traitées | 11 acceptées, 3 rejetées"

**When something's wrong:**
- Right-click but no menu → you're not clicking on an entity
- Left-click but nothing happens → expected! Use right-click instead
- Accept but status doesn't change → functional bug (report to QA)

---

## 🎓 Quick Demo Script

Try this 30-second demo to understand the UI:

```
1. Right-click any blue highlighted name → click "Accepter"
   → Notice: status icon changes to ✓

2. Right-click next entity → click "Rejeter"
   → Notice: entity turns red with strikethrough

3. Click in document, press Enter key
   → Notice: blue border appears (navigation mode)

4. Press Tab twice
   → Notice: highlight moves to next entity

5. Press Enter
   → Notice: entity accepted, moves to next automatically

6. Press Escape
   → Notice: blue border disappears (exited nav mode)

7. Check 3 entities in sidebar → click "Accepter la sélection"
   → Notice: all 3 change to ✓ at once
```

---

## 📚 Reference

- **Full Story**: [docs/stories/6.4.visual-entity-validation-interface.story.md](../stories/6.4.visual-entity-validation-interface.story.md)
- **Performance Test**: [docs/qa/PERF-001-manual-test-guide.md](PERF-001-manual-test-guide.md)
- **Implementation**:
  - EntityEditor: [gdpr_pseudonymizer/gui/widgets/entity_editor.py](../../gdpr_pseudonymizer/gui/widgets/entity_editor.py)
  - EntityPanel: [gdpr_pseudonymizer/gui/widgets/entity_panel.py](../../gdpr_pseudonymizer/gui/widgets/entity_panel.py)
  - ValidationScreen: [gdpr_pseudonymizer/gui/screens/validation.py](../../gdpr_pseudonymizer/gui/screens/validation.py)
