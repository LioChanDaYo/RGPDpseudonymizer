# Epic 16: English Labels That Show in French - Brownfield Enhancement

**Epic Goal:** In the desktop app set to English, the 29 labels whose English translation already exists show that English. Today they show the French, because their translation key was broken when the texts were extracted. A test keeps it from happening again. No English or French wording changes.

**Target Release:** the next release (none is planned). Story 16.1 lands on main after Story 15.1 and before Story 14.1; no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** Epic 15 (Story 15.1, the review list matches the written file), approved and not merged yet. Epics 12 (Windows installer) and 13 (place pseudonyms) are done and also target the next release.
**Successor:** Epic 14 (first names on short text, Story 14.1), on a local branch that has not been pushed. Story 14.1 is rebased on Story 16.1 once 16.1 is merged. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

**Why a new epic (PM, 2026-11-23):** this is a fix to the desktop app's English translation files and a guard on them. It touches no detection, no review logic and no written output. Epic 15's scope rule allows Story 15.1 only, Epic 14's allows Story 14.1 only ("Nothing else"), and Epic 11 shipped and closed with v2.3.2.

---

## Scope Rule

One story, Story 16.1, on desktop labels whose English is never found because their translation key was extracted broken. Nothing else. Out of scope: any change of English or French wording, and the labels that lack English for another reason (listed below under "Found, other cause").

Lionel's decision, word for word:

- Lionel, 2026-11-23. The question asked: "Should the 29 English labels that show in French be fixed in their own small story, before Story 14.1?" His answer: "yes".

---

## Existing System Context

PM checked on origin/main `1bb6f57`, 2026-11-23, with `rgpd-analysis\r161\pm\pm161.py` (log `logs\pm161.log`): every `tr()` call in `gdpr_pseudonymizer/gui/` read with Python's `ast`, both `.ts` files read as XML, and the shipped `en.qm` loaded with `QTranslator` and asked with `translate(context, source)`.

- **How the English app finds a label.** `install_translator` (`gdpr_pseudonymizer/gui/i18n/translator.py` l.54-82) loads `gui/i18n/en.qm` for English. Each `self.tr("…")` looks its French source up in that file, under the class name as context. When the source is not found, Qt returns the French source, so the English app shows French.
- **How the keys broke.** A source written in Python with a `\u` escape (`self.tr("Ajouter comme entité")`) is « Ajouter comme entité » at run time. The extraction into `.ts` dropped the backslash and kept the letters: the key in `en.ts` is `Ajouter comme entitu00e9`. The English is stored under that broken key and never found. Story 10.13's Context recorded the mechanism (`docs/stories/10.13.pending-names-warning.story.md` l.34). Since then the project's rule is "no `\u` escapes in `tr()`" (10.13 Coding Standards, l.798; Story 11.4 l.192). The PO of Story 14.1 measured it on « Ajouter comme entité » (`rgpd-analysis\r143\po\po143_qt.py`, `logs\po143_qt.log`): `translate('EntityEditor', 'Ajouter comme entité')` gives `''`, and the broken key gives "Add as entity".
- **French loads no translation file.** For French, `install_translator` returns before loading anything (`translator.py` l.61-63): French is the source language. `fr.qm` is 16 bytes and holds no translation (`QTranslator.isEmpty()` is true). So the same broken keys in `fr.ts` change nothing on screen.
- **How the `.qm` files are built (Story 11.5, Task 5.2, `docs/stories/11.5.review-list-shows-written-pseudonym.story.md` l.840).** `.ts` entries are inserted by hand; `pyside6-lupdate` is not run. `en.qm` is built with `pyside6-lrelease` from a copy of `en.ts` without the three stale file-filter entries (`filter_ts_1014.py`: "removed 3"). `fr.qm` is rebuilt and must stay byte-identical. `qm_compare.py` checks that the new `en.qm` differs from main's only in the intended messages. Today `en.ts` has 349 messages and `en.qm` 346 translations (the 3 filters are the difference). The `<location>` line numbers in both `.ts` files are stale (for example `entity_editor.py` line 351 in `en.ts` is line 418 in the code); this epic cites the code lines.
- **What the tests check today.** `tests/unit/gui/test_i18n.py` checks that the translator loads, the language switch and `retranslateUi`, and no label's text. `tests/integration/test_pyinstaller_build.py` l.141-142 checks only that `en.qm` and `fr.qm` exist in the build.
- **Technology stack:** Python 3.11-3.13, Poetry, PySide6-Essentials (Qt 6.8), `pyside6-lrelease`, pytest.

---

## Stories

### Story 16.1: The English App Shows the English of Every Label That Has One

**Problem** (PM, 2026-11-23, origin/main `1bb6f57`, `pm161.log`):

- `gdpr_pseudonymizer/gui/i18n/en.ts` holds **29 keys with a broken escape** (`grep -n '<source>.*u[0-9a-f]\{4\}' gdpr_pseudonymizer/gui/i18n/en.ts`: 29 lines). Each one, with the broken run turned back into its character, is exactly a `tr()` source of the code in the same context: 29 of 29, no false positive.
- They are used at **31 places in the code** (« déjà connu » twice, « Sélection » twice). At each of the 31, `translate()` on the shipped `en.qm` returns nothing: the English app shows the French.
- **9 of the 29 English translations hold the same broken escape** (for example "Continue u25b6" for « Continuer ▶ »). Fixing only the key would make the English app show « Continue u25b6 ». See the open question Q1.
- `fr.ts` holds the same 29 broken keys, all `type="unfinished"` with no translation. They have no effect on screen (French loads no file), but they are fixed too, so that the guard can hold for both files.

**The 29 labels** (French as the code builds it at run time; English as it stands in `en.ts` today; ⚠ = the English holds the broken escape, Q1):

| # | French shown in the English app | English in `en.ts` today | Where in the app | Code | Key line in `en.ts`, `fr.ts` |
|---|---|---|---|---|---|
| 1 | « Entités (0) » | Entities (0) | Review screen, entity list title before any count | `gui/widgets/entity_panel.py:178` | l.758, l.751 |
| 2 | « Entités (%1) » | Entities (%1) | Review screen, entity list title with the count | `entity_panel.py:274` | l.788, l.781 |
| 3 | « Masquer les rejetées » | Hide rejected | Review screen, check box | `entity_panel.py:180` | l.768, l.761 |
| 4 | « Filtrer les entités... » | Filter entities... | Review screen, filter field placeholder | `entity_panel.py:182` | l.773, l.766 |
| 5 | « Accepter les déjà connues » | Accept already known | Review screen, button | `entity_panel.py:183` | l.778, l.771 |
| 6 | « déjà connu » | already known | Review screen, tag on a row already in the database | `entity_panel.py:310`, `:377` | l.794, l.787 |
| 7 | « Toutes vérifiées » | All verified | Review screen, counter once nothing is left | `entity_panel.py:454` | l.799, l.792 |
| 8 | « Accepter la sélection (%1) » | Accept selection (%1) | Review screen, button for several rows | `entity_panel.py:464` | l.809, l.802 |
| 9 | « Rejeter la sélection (%1) » | Reject selection (%1) | Review screen, button for several rows | `entity_panel.py:467` | l.814, l.807 |
| 10 | « Éditeur de document » | Document Editor | Review screen, document view, name read by a screen reader | `gui/widgets/entity_editor.py:65` | l.676, l.669 |
| 11 | « Affiche le document avec les entités surlignées en couleur » | Displays the document with color-highlighted entities | Review screen, document view, description read by a screen reader | `entity_editor.py:68` | l.681, l.674 |
| 12 | « Ajouter comme entité » | Add as entity | Review screen, right-click menu on selected text | `entity_editor.py:418` | l.734, l.727 |
| 13 | « Phrase secrète » | Passphrase | Passphrase window, title | `gui/widgets/passphrase_dialog.py:139` | l.1031, l.1024 |
| 14 | « Phrase secrète : » | Passphrase: | Passphrase window, field label | `passphrase_dialog.py:141` | l.1041, l.1034 |
| 15 | « Entrez votre phrase secrète » | Enter your passphrase | Passphrase window, field placeholder | `passphrase_dialog.py:143` | l.1046, l.1039 |
| 16 | « Afficher/masquer la phrase secrète » | Show/hide passphrase | Passphrase window, tooltip of the show button | `passphrase_dialog.py:146` | l.1051, l.1044 |
| 17 | « Mémoriser pour cette session » | Remember for this session | Passphrase window, check box | `passphrase_dialog.py:148` | l.1056, l.1049 |
| 18 | « Continuer ▶ » | ⚠ Continue u25b6 | Passphrase window, button | `passphrase_dialog.py:153` | l.1066, l.1059 |
| 19 | « Aucune base détectée — créez-en une nouvelle » | ⚠ No database detected u2014 create a new one | Passphrase window, hint when no database is found | `passphrase_dialog.py:204` | l.1086, l.1079 |
| 20 | « Continuer ▶ » | ⚠ Continue u25b6 | Analysis screen, button | `gui/screens/processing.py:178` | l.1140, l.1133 |
| 21 | « ◀ Retour » | ⚠ u25c0 Back | Review screen, back button | `gui/screens/validation.py:231` | l.1455, l.1448 |
| 22 | « Finaliser ▶ » | ⚠ Finalize u25b6 | Review screen (one document), finish button | `validation.py:253` | l.1460, l.1453 |
| 23 | « ◀ Retour » | ⚠ u25c0 Back | Batch screen, file selection, back button | `gui/screens/batch.py:514` | l.8, l.8 |
| 24 | « ◀ Retour » | ⚠ u25c0 Back | Database screen, back button | `gui/screens/database.py:291` | l.376, l.376 |
| 25 | « ← Retour » | ⚠ u2190 Back | Settings screen, back button | `gui/screens/settings.py:280` | l.1226, l.1219 |
| 26 | « ← Retour à l'accueil » | ⚠ u2190 Back to home | Placeholder screen, back button | `gui/screens/stub.py:39` | l.1447, l.1440 |
| 27 | « Sélection » | Selection | Step bar, first step (batch and one document) | `gui/widgets/step_indicator.py:227`, `:233` | l.1408, l.1401 |
| 28 | « Résumé » | Summary | Step bar, last step of a batch | `step_indicator.py:230` | l.1424, l.1417 |
| 29 | « Résultat » | Result | Step bar, last step of one document | `step_indicator.py:236` | l.1434, l.1427 |

Contexts: rows 1-9 `EntityPanel`, 10-12 `EntityEditor`, 13-19 `PassphraseDialog`, 20 `ProcessingScreen`, 21-22 `ValidationScreen`, 23 `BatchScreen`, 24 `DatabaseScreen`, 25 `SettingsScreen`, 26 `StubScreen`, 27-29 `StepIndicator`.

**Found, same cause, with no English at all (PM, 2026-11-23).** Five more `tr()` sources are written with a `\u` escape and were never extracted. They are in neither `en.ts` nor `fr.ts`, so the English app shows them in French too. A future `pyside6-lupdate` run would extract them broken. They have no English to restore, so writing it is new text (Q2):

| French shown | Where in the app | Code | Added by |
|---|---|---|---|
| « ◀ Précédent » | Batch review, previous document button | `validation.py:234` | Story 6.7.3 (`53db8fc`) |
| « Suivant ▶ » | Batch review, next document button | `validation.py:235` | Story 6.7.3 |
| « Valider et terminer ▶ » | Batch review, finish button on the last document | `validation.py:249` | Story 6.7.3 |
| « Valider et continuer ▶ » | Batch review, finish button on the other documents | `validation.py:251` | Story 6.7.3 |
| « Masquer les validées » | Review screen, check box | `entity_panel.py:181` | Story 7.1 (`1e46d6d`) |

**Found, other cause (out of scope, for Lionel to know).**

- **121 more `tr()` calls (113 distinct context and source pairs) have no English**, written with plain characters: they were never put in `en.ts` in their context. About 82 of the 121 are names and descriptions read by a screen reader (`setAccessibleName`, `setAccessibleDescription`). The others include visible labels: « Personnes », « Lieux », « Organisations » on the results screen (`results.py:138-196`); « en attente », « accepté », « rejeté », « modifié », « ajouté » (`entity_editor.py:166-170`, `entity_panel.py:409-413`); « Annulé », « Non traité », « Traitement annulé » on the batch screen; « Document %1 de %2 » (`validation.py:1041`). Some exist in `en.ts` under another context (« Personne », « Lieu », « Organisation » under `EntityEditor`, used in `EntityPanel` at `entity_panel.py:403-405`). The QA backlog already knew part of it (B21, "the batch buttons stay in French"; Epic 10, 10.13 Context). Full list in `pm161.log`. Whether a later story writes their English is Lionel's call (Q3); Story 16.1 does not touch them.
- **The three file-dialog filters** « Documents (…);;Tous (*) » (`main_window.py:439`, `batch.py:581`, `drop_zone.py:166`) are in `en.ts` and left out of `en.qm` on purpose at every build (10.11 QA `BACKLOG-EN-QM`). Unchanged by this epic.
- **`fr.ts` lacks the 40 `ShortcutsHelpDialog` entries** that `en.ts` has. French loads no file, so nothing changes on screen. Unchanged by this epic.
- **Seven `tr()` calls take a variable** (`dialogs/shortcuts_help.py:77`, `:86`, `:115`; `screens/settings.py:258`, `:272`, `:333`, `:335`). A static guard cannot read their source.
- **Three `tr()` sources written with a `\u` escape work today** (`database.py:781` « … et %1 autre(s) », `:811` and `:828` « • %1 → %2 … »): their `en.ts` keys were inserted by hand with the real characters. A guard on the code must not break them, and their wording does not change.

**Scope (the SM writes the detailed story):**

- **Fix the 29 keys.** In `en.ts` and `fr.ts`, each broken key becomes the source the code builds at run time (row by row in the table above). The English translations of rows 1-17 and 27-29 are kept byte for byte. The 9 ⚠ translations change only as Lionel decides in Q1.
- **The five same-cause labels without English** are added only if Lionel approves their English word for word (Q2). Otherwise they stay out, and the guard records them as known.
- **No wording change.** No English or French text changes, apart from Lionel's answers to Q1 and Q2. If the dev or QA finds an existing English translation that is wrong or missing, it is flagged for Lionel; nobody writes it.
- **The French app is unchanged.** If the dev rewrites the `\u` escapes in the code with their characters (10.13's rule), the string each `tr()` call passes at run time stays byte-identical, and a test shows it.
- **Rebuild the `.qm` files the way Story 11.5 did:** hand edits to the `.ts` files, no `pyside6-lupdate`; `en.qm` from a copy of `en.ts` without the three file filters (`filter_ts_1014.py`); `fr.qm` rebuilt and byte-identical to main's (16 bytes, "Generated 0 translation(s)"), so not staged; `qm_compare.py` over every message: the new `en.qm` differs from main's only in the fixed keys (and any label Lionel approved under Q2).
- **A guard, so it cannot happen again. The SM designs it.** Constraints the design must meet:
  - no key and no translation in `en.ts` or `fr.ts` holds a broken `\u` run (`u` + four hex digits standing for a character, as in the 29). Today every such run in a key is a broken escape (29 of 29), so the SM decides how a real word that matches the pattern would be told apart;
  - a `tr()` source written with a `\u` escape is found in the shipped `en.qm`, or it is on a written list of known gaps. Checking the `.ts` files alone is not enough: the next `pyside6-lupdate` run would break any `\u` still in the code;
  - the guard leaves `\n` alone (extracted correctly today: 13 `\n` escapes in `tr()` sources) and handles the three working sources of `database.py`;
  - the brief's wider check, "every `self.tr` source has a translated key in `en.ts`", would fail today on the 121 other-cause calls. If the SM wants it, it starts from a frozen list of today's gaps that may only shrink, and full CI stays green;
  - the guard fails when one of the 29 keys is broken again (shown in the story's test record, as a mutation).
- **Order.** Story 16.1 starts from main after Story 15.1 is merged, or is rebased on it then. Both stories rebuild `en.qm`, which is binary and cannot be merged: 16.1's `.ts` edits are redone on 15.1's `.ts` files and `en.qm` is rebuilt after the rebase. Story 14.1 is rebased on 16.1 after 16.1 is merged, and rebuilds `en.qm` in turn.
- Ships with the next release (none is planned), with a CHANGELOG `[Unreleased]` entry.
- Proof: tests first on CI. Before the release, Lionel hand-checks the English app.
- Out of scope: any wording change; the 121 other-cause gaps; the three file filters; the `ShortcutsHelpDialog` entries missing from `fr.ts`; detection, review logic and written output.

**Open questions (for Lionel; the story does not decide them):**

- **Q1. The 9 English translations that hold the broken escape** (rows 18-26). If only the key is fixed, the English app shows them as they stand: « Continue u25b6 », « u25c0 Back », « Finalize u25b6 », « u2190 Back », « u2190 Back to home », « No database detected u2014 create a new one ». The French source of each has the character (« ▶ », « ◀ », « ← », « — »). Does Lionel want the character put back in the English, so they read « Continue ▶ », « ◀ Back », « Finalize ▶ », « ← Back », « ← Back to home », « No database detected — create a new one »? The words stay as they are.
- **Q2. The five same-cause labels with no English** (« ◀ Précédent », « Suivant ▶ », « Valider et terminer ▶ », « Valider et continuer ▶ », « Masquer les validées »). The SM proposes their English; Lionel approves it word for word, or they stay out of Story 16.1.
- **Q3. The 121 other-cause gaps.** A later story, or nothing for now. Story 16.1 only records them.

**Acceptance (epic level):**

1. For each of the 29 labels, `translate(context, source)` on the shipped `en.qm`, with the source the code builds at run time, returns the English of the table, or the form Lionel chose in Q1. A test checks the exact string for each of the 31 call sites' sources; none can pass on a string that still holds `u25b6`, `u25c0`, `u2190` or `u2014`.
2. The French app is unchanged: the string each `tr()` call passes at run time is byte-identical to main's, and `fr.qm` is byte-identical to main's.
3. `qm_compare.py` over every message: the new `en.qm` differs from main's (after Story 15.1) only in the fixed keys and any label Lionel approved under Q2.
4. No key and no translation in `en.ts` or `fr.ts` holds a broken `\u` run, and the guard designed by the SM is on CI and fails when one key is broken again.
5. No English or French wording changed apart from Lionel's answers to Q1 and Q2; any wrong or missing English found on the way was flagged for him.
6. Tests first on CI; full CI green; QA review; one read-only Codex review of the final head, with a Codex stopping rule written in the story (as in Story 10.21).
7. Story 16.1 merged after Story 15.1, with `en.qm` rebuilt after the rebase; Story 14.1 rebased on it.
8. CHANGELOG `[Unreleased]` entry.
9. Before the release, Lionel's hand check of the English app passes: the review screen (list, buttons, right-click menu), the passphrase window, the back and continue buttons and the step bar show English.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge, under the story's stopping rule.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

Story 16.1 lands on main with its CHANGELOG `[Unreleased]` entry, after Story 15.1 and before Story 14.1, and ships with the next release, none planned. Before that release, Lionel hand-checks the English app. No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] The French app shows exactly what it shows today.
- [ ] No English wording changes apart from Lionel's answers to Q1 and Q2.
- [ ] No CLI change, no mapping-table schema or file format change; the `.qm` files are still found where `translator.py` looks for them, in the package and in the standalone builds.

## Risk Mitigation

- **Primary risks:**
  - Fixing the key alone makes 9 labels show « u25b6 »-style text in English (Q1).
  - `en.qm` is binary: Story 15.1, Story 16.1 and Story 14.1 each rebuild it, so a rebase that keeps one side's file loses the other's messages.
  - Rewriting `\u` escapes in the code could change a French string by one character.
  - A guard on every `tr()` source would fail on 121 gaps of another cause and block CI.
- **Mitigation:**
  - Acceptance 1 checks the exact English string.
  - `en.qm` rebuilt from the merged `.ts` files after each rebase, and `qm_compare.py` run against main's.
  - Acceptance 2 checks the French run-time strings byte for byte.
  - The guard's known-gaps list, as the SM designs it.
  - Lionel's hand check before the release.
- **Rollback plan:** revert the story's merge commit; nothing is released until Lionel's go.

## Definition of Done

- [ ] Story 16.1 merged: the 29 labels show their English in the English app (31 call sites), measured with `translate()` on the shipped `en.qm`; the French app unchanged; CHANGELOG `[Unreleased]` entry
- [ ] Q1 and Q2 answered by Lionel, and his answers applied word for word
- [ ] `en.ts` and `fr.ts` hold no broken `\u` run; `.qm` rebuilt as in Story 11.5; `fr.qm` byte-identical; `qm_compare.py` shows only the intended messages
- [ ] The guard on CI, shown to fail when a key is broken again
- [ ] Tests-first commit and draft PR, QA review, read-only Codex review of the final head
- [ ] No regression in existing features (full CI green)
- [ ] Merged after Story 15.1; Story 14.1 rebased on it
- [ ] Before the next release: Lionel's hand check of the English app passes

---

## Story Manager Handoff

"Please write Story 16.1 for this epic (Lionel: "yes", the 29 English labels that show in French get their own small story, before Story 14.1). Key considerations:

- This fixes the translation files of an existing PySide6 desktop app so that the English it already holds is found, and adds a guard. Nothing else.
- Integration points: `gdpr_pseudonymizer/gui/i18n/en.ts`, `fr.ts`, `en.qm` (`fr.qm` rebuilt, byte-identical, not staged); `translator.py` (French loads no file); the 31 call sites of the table, in `gui/widgets/entity_panel.py`, `entity_editor.py`, `passphrase_dialog.py`, `step_indicator.py` and `gui/screens/processing.py`, `validation.py`, `batch.py`, `database.py`, `settings.py`, `stub.py`; `tests/unit/gui/test_i18n.py`.
- Re-measure the 29 keys, the 31 call sites, the 9 broken translations and the five same-cause labels with your own probe (the PM's is `rgpd-analysis\r161\pm\pm161.py`). Cite code lines; the `.ts` `<location>` lines are stale.
- Put Q1 and Q2 to Lionel before the fix: for Q1 the six strings as they would read with and without the character; for Q2 the French, where it appears, an example and your proposed English. He approves word for word. Q3 is recorded, not decided.
- Rebuild the `.qm` files as Story 11.5 did (hand edits, no `pyside6-lupdate`, `filter_ts_1014.py`, `pyside6-lrelease`, `qm_compare.py`, `fr.qm` byte-identical).
- Design the guard under the constraints of the epic's Scope; show it failing on a broken key.
- Order: after Story 15.1 is merged; rebase and rebuild `en.qm` then; Story 14.1 after 16.1.
- Tests first; QA; one read-only Codex review under the story's stopping rule; Lionel's hand check of the English app before the release.
- Out of scope: any wording change, and the 121 other-cause gaps.
- Each story must include verification that existing functionality remains intact.

The epic should leave the English app showing the English it already has, with a test that keeps the keys from breaking again."
