# Epic 16: English Labels That Show in French - Brownfield Enhancement

**Epic Goal:** In the desktop app set to English, every text shows English. Story 16.1: the 29 labels whose English translation already exists show that English (today their translation key was broken when the texts were extracted, so they show the French), the 9 of them whose English holds the broken escape get their symbol back, and 5 labels of the same cause get English. Story 16.2: every other text with no English gets it, apart from the three file filters left out on purpose, and a guard checks that every `self.tr` source has an `en.ts` key. No French wording changes.

**Target Release:** the next release (none is planned). Order on main: Story 15.1, then Story 16.1, then Story 14.1 (rebased on both), then Story 16.2. No tag and no PyPI release without Lionel's explicit go.
**Predecessor:** Epic 15 (Story 15.1, the review list matches the written file), approved and not merged yet. Epics 12 (Windows installer) and 13 (place pseudonyms) are done and also target the next release.
**Successor:** Epic 14 (first names on short text, Story 14.1), on a local branch that has not been pushed. Story 14.1 is rebased on Stories 15.1 and 16.1 once both are merged; Story 16.2 comes after Story 14.1. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

**Why a new epic (PM, 2026-11-23):** this is a fix to the desktop app's English translation files and a guard on them. It touches no detection, no review logic and no written output. Epic 15's scope rule allows Story 15.1 only, Epic 14's allows Story 14.1 only ("Nothing else"), and Epic 11 shipped and closed with v2.3.2.

---

## Scope Rule

Two stories, on the desktop app's English translation. Story 16.1: the labels whose English is never found because their translation key was extracted broken, and the 5 labels of the same cause with no English. Story 16.2: the texts with no English for another reason, and the full guard. Nothing else. Out of scope: any change of French wording (a French source text that has to change goes to Lionel word for word), detection, review logic and written output.

Lionel's decisions, word for word:

- Lionel, 2026-11-23. The question asked: "Should the 29 English labels that show in French be fixed in their own small story, before Story 14.1?" His answer: "yes".
- Lionel, 2026-11-24. The question asked: "Should the 121 texts with no English get their own story, 16.2, right after 14.1?" What he saw with it: 121 `tr()` calls (113 distinct) never added to `en.ts`, about 82 of them screen-reader names or descriptions, plus visible ones such as « Personnes / Lieux / Organisations », « en attente / accepté », « Annulé », « Document %1 de %2 ». His answer: "yes".

Decisions on English text (orchestrator, 2026-11-24). They change English only and no French wording, so they were not put to Lionel: he validates French product texts only.

- **The 9 English translations that hold the broken escape get their symbol back, with the same words:** « Continue ▶ », « No database detected — create a new one », « ◀ Back », « Finalize ▶ », « ← Back », « ← Back to home » (rows 18-26 of the table below).
- **The 5 labels of the same cause that were never extracted** (« ◀ Précédent », « Suivant ▶ », « Valider et terminer ▶ », « Valider et continuer ▶ », « Masquer les validées ») are in Story 16.1's scope. The SM proposes their English and the PO checks it.
- **Story 16.2's English is new text.** The SM writes it, the PO checks it, and Lionel is not asked. Any French source text that changes goes to Lionel word for word.

---

## Existing System Context

PM checked on origin/main `1bb6f57`, 2026-11-23, with `rgpd-analysis\r161\pm\pm161.py` (log `logs\pm161.log`): every `tr()` call in `gdpr_pseudonymizer/gui/` read with Python's `ast`, both `.ts` files read as XML, and the shipped `en.qm` loaded with `QTranslator` and asked with `translate(context, source)`. On 2026-11-24, on the same tree, `pm162.py` (log `logs\pm162.log`) split the calls with no English by the call that receives them, and resolved the 7 variable `tr()` calls from the shortcut registry.

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
- **9 of the 29 English translations hold the same broken escape** (for example "Continue u25b6" for « Continuer ▶ »). Fixing only the key would make the English app show « Continue u25b6 ». They get their symbol back, same words (decision above).
- `fr.ts` holds the same 29 broken keys, all `type="unfinished"` with no translation. They have no effect on screen (French loads no file), but they are fixed too, so that the guard can hold for both files.

**The 29 labels** (French as the code builds it at run time; English as it stands in `en.ts` today; ⚠ = the English holds the broken escape and gets its symbol back, same words):

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

**Found, same cause, with no English at all (PM, 2026-11-23): in Story 16.1's scope.** Five more `tr()` sources are written with a `\u` escape and were never extracted. They are in neither `en.ts` nor `fr.ts`, so the English app shows them in French too. A future `pyside6-lupdate` run would extract them broken. Their English is new text: the SM proposes it and the PO checks it (decision above). They are 5 of the 121 calls Lionel saw on 2026-11-24, so Story 16.2 does not count them.

| French shown | Where in the app | Code | Added by |
|---|---|---|---|
| « ◀ Précédent » | Batch review, previous document button | `validation.py:234` | Story 6.7.3 (`53db8fc`) |
| « Suivant ▶ » | Batch review, next document button | `validation.py:235` | Story 6.7.3 |
| « Valider et terminer ▶ » | Batch review, finish button on the last document | `validation.py:249` | Story 6.7.3 |
| « Valider et continuer ▶ » | Batch review, finish button on the other documents | `validation.py:251` | Story 6.7.3 |
| « Masquer les validées » | Review screen, check box | `entity_panel.py:181` | Story 7.1 (`1e46d6d`) |

**Found, other cause (Story 16.2, below).** The texts with no English for another reason, the 40 `ShortcutsHelpDialog` entries missing from `fr.ts` and the 7 variable `tr()` calls are Story 16.2's. Two facts matter to Story 16.1's guard:

- **The three file-dialog filters** « Documents (…);;Tous (*) » (`main_window.py:439`, `batch.py:581`, `drop_zone.py:166`) are in `en.ts` and left out of `en.qm` on purpose at every build (10.11 QA `BACKLOG-EN-QM`). Unchanged by Story 16.1; Story 16.2 keeps them out unless the SM finds a reason.
- **Three `tr()` sources written with a `\u` escape work today** (`database.py:781` « … et %1 autre(s) », `:811` and `:828` « • %1 → %2 … »): their `en.ts` keys were inserted by hand with the real characters. A guard on the code must not break them, and their wording does not change.

**Scope (the SM writes the detailed story):**

- **Fix the 29 keys.** In `en.ts` and `fr.ts`, each broken key becomes the source the code builds at run time (row by row in the table above). The English translations of rows 1-17 and 27-29 are kept byte for byte.
- **The 9 ⚠ translations get their symbol back, with the same words:** « Continue ▶ » (rows 18 and 20), « No database detected — create a new one » (19), « ◀ Back » (21, 23 and 24), « Finalize ▶ » (22), « ← Back » (25), « ← Back to home » (26).
- **The five same-cause labels get English.** The SM proposes it and the PO checks it; Lionel is not asked (English only). Each is added to `en.ts` with its English and to `fr.ts` like its other entries.
- **No French wording change.** English changes only by the 9 symbols put back and the 5 new labels. If the dev or QA finds an existing English translation that is wrong or missing, it goes to Story 16.2's list; a French source text that would have to change goes to Lionel word for word.
- **The French app is unchanged.** If the dev rewrites the `\u` escapes in the code with their characters (10.13's rule), the string each `tr()` call passes at run time stays byte-identical, and a test shows it.
- **Rebuild the `.qm` files the way Story 11.5 did:** hand edits to the `.ts` files, no `pyside6-lupdate`; `en.qm` from a copy of `en.ts` without the three file filters (`filter_ts_1014.py`); `fr.qm` rebuilt and byte-identical to main's (16 bytes, "Generated 0 translation(s)"), so not staged; `qm_compare.py` over every message: the new `en.qm` differs from main's only in the fixed keys and the 5 new labels.
- **A guard, so it cannot happen again. The SM designs it.** Constraints the design must meet:
  - no key and no translation in `en.ts` or `fr.ts` holds a broken `\u` run (`u` + four hex digits standing for a character, as in the 29). Today every such run in a key is a broken escape (29 of 29), so the SM decides how a real word that matches the pattern would be told apart;
  - every `tr()` source written with a `\u` escape is found in the shipped `en.qm`: after the fix, the 31 call sites, the 5 new labels and the 3 working sources of `database.py`, 39 calls with no gap left. Checking the `.ts` files alone is not enough: the next `pyside6-lupdate` run would break any `\u` still in the code;
  - the guard leaves `\n` alone (extracted correctly today: 13 `\n` escapes in `tr()` sources) and handles the three working sources of `database.py`;
  - the wider check, "every `self.tr` source has an `en.ts` key", is Story 16.2's. If the SM starts it in Story 16.1, it starts from a frozen list of today's gaps that may only shrink, full CI stays green, and Story 16.2 empties and removes the list;
  - the guard fails when one of the 29 keys is broken again (shown in the story's test record, as a mutation).
- **Order.** Story 16.1 starts from main after Story 15.1 is merged, or is rebased on it then. Both stories rebuild `en.qm`, which is binary and cannot be merged: 16.1's `.ts` edits are redone on 15.1's `.ts` files and `en.qm` is rebuilt after the rebase. Story 14.1 is rebased on 16.1 after 16.1 is merged, and rebuilds `en.qm` in turn; Story 16.2 comes after Story 14.1.
- Ships with the next release (none is planned), with a CHANGELOG `[Unreleased]` entry.
- Proof: tests first on CI. Before the release, Lionel hand-checks the English app.
- Out of scope: any French wording change; the texts with no English for another reason, the `ShortcutsHelpDialog` entries missing from `fr.ts` and the 7 variable `tr()` calls (all Story 16.2); the three file filters; detection, review logic and written output.

**Acceptance (Story 16.1):**

1. For each of the 29 labels, `translate(context, source)` on the shipped `en.qm`, with the source the code builds at run time, returns the English of the table, the 9 ⚠ ones with their symbol back (« Continue ▶ », « ◀ Back », « Finalize ▶ », « ← Back », « ← Back to home », « No database detected — create a new one »). A test checks the exact string for each of the 31 call sites' sources; none can pass on a string that still holds `u25b6`, `u25c0`, `u2190` or `u2014`.
2. For each of the 5 same-cause labels, `translate()` on the shipped `en.qm` returns the English the PO checked, written in the story.
3. The French app is unchanged: the string each `tr()` call passes at run time is byte-identical to main's, and `fr.qm` is byte-identical to main's.
4. `qm_compare.py` over every message: the new `en.qm` differs from main's (after Story 15.1) only in the fixed keys and the 5 new labels.
5. No key and no translation in `en.ts` or `fr.ts` holds a broken `\u` run, and the guard designed by the SM is on CI and fails when one key is broken again.
6. No French wording changed; English changed only by the 9 symbols put back and the 5 new labels; any wrong or missing English found on the way is on Story 16.2's list.
7. Tests first on CI; full CI green; QA review; one read-only Codex review of the final head, with a Codex stopping rule written in the story (as in Story 10.21).
8. Story 16.1 merged after Story 15.1, with `en.qm` rebuilt after the rebase; Story 14.1 rebased on it.
9. CHANGELOG `[Unreleased]` entry.
10. Before the release, Lionel's hand check of the English app passes: the review screen (list, buttons, right-click menu, batch previous/next/finish buttons), the passphrase window, the back and continue buttons and the step bar show English.

**Open questions:** none left. The decisions of 2026-11-24 are under Scope Rule.

### Story 16.2: Texts with No English Translation

Lionel, 2026-11-24: "yes" (Scope Rule above). Ordered after Story 14.1.

**Problem** (PM, origin/main `1bb6f57`, `pm161.log` 2026-11-23 and `pm162.log` 2026-11-24):

- **121 `tr()` calls (113 distinct context and source pairs) have no `en.ts` entry in their context**, so the English app shows them in French. That is the count Lionel saw. 5 of them are the same-cause labels Story 16.1 takes (`validation.py:234`, `:235`, `:249`, `:251`, `entity_panel.py:181`), so **Story 16.2 has 116 calls, 108 distinct pairs** (`pm162.log`). The epic of 2026-11-23 said all 121 were written with plain characters; those 5 are written with a `\u` escape.
- **82 of the 116 (80 distinct) are names and descriptions read by a screen reader**: 37 inside `setAccessibleName`, 45 inside `setAccessibleDescription`.
- **The other 34 are visible**, for example: « Personnes », « Lieux », « Organisations » on the results screen (`results.py:138-145`, `:188-196`); « en attente », « accepté », « rejeté », « modifié », « ajouté » (`entity_editor.py:166-170`, `entity_panel.py:409-413`); « Personne », « Lieu », « Organisation » (`entity_panel.py:403-405`) and « , déjà connu » (`:416`); « Annulé », « Non traité », « Traitement annulé », « En attente de validation », « Pseudonymisation », « Valider les entités par document » and « Aucun fichier de sortie ne sera conservé. » on the batch screen; « Document %1 de %2 » (`validation.py:1041`), the notice on a document already validated (`:240`) and the warning before cancelling a batch (`:1028`); « Neutre / Générique (PER-001, LOC-001) » (`settings.py:307`); « Étape {step} sur {total}: {label} » (`step_indicator.py:219`). Full list in `pm162.log`. The QA backlog already knew part of it (B21, "the batch buttons stay in French"; Epic 10, 10.13 Context).
- **Some have English in `en.ts` under another context**: « Personne », « Lieu », « Organisation » under `EntityEditor`, used in `EntityPanel`; others are listed in `pm161.log` with "same source in context(s)".
- **The 7 `tr()` calls that take a variable** (`dialogs/shortcuts_help.py:77`, `:86`, `:115`; `screens/settings.py:258`, `:272`, `:333`, `:335`) are not in the 121: a reading of the code cannot see their source. Their text comes from `gui/accessibility/shortcuts.py`: the group names and actions of `get_all_shortcuts()` (9 groups, 33 distinct actions) and `NAVIGATION_MODE_DESCRIPTION`. Resolved from the registry and asked of `en.qm` (`pm162.log`):
  - in `ShortcutsHelpDialog`, 35 of 43 values have English. The 8 others are group names already written in English (« Global », « Home », « Validation », « Editor », « Results », « Batch », « Database », « Settings »), so the English app shows them right with no key;
  - in `SettingsScreen` (the shortcut list on the settings screen), 36 of 42 values have no English: 27 actions whose English is in `en.ts` under other contexts (all 27 under `ShortcutsHelpDialog`, some also under `MainWindow`, `BatchScreen` or `ResultsScreen`) and none under `SettingsScreen`, so the English app shows them in French, and the 9 group names. These were outside the 121 Lionel saw. Their English is English only, so it follows the same rule as the rest of the story.
- **Found, for Lionel to know (not in scope).** The French app shows the shortcut group names in English (« Global », « Home », « Navigation Mode »…) in the shortcuts window and on the settings screen: the registry's names are English and French loads no file. Changing them would be French wording, so it is his call; Story 16.2 does not touch it.
- **`fr.ts` lacks the 40 `ShortcutsHelpDialog` entries** that `en.ts` has. French loads no file, so nothing changes on screen.
- **The three file-dialog filters** are in `en.ts`, so they pass a guard on `en.ts` keys, and they are left out of `en.qm` on purpose at every build (`BACKLOG-EN-QM`).

**Scope (the SM writes the detailed story):**

- **Write the English** of the 116 calls in their own context in `en.ts`, and of the `SettingsScreen` shortcut actions. The SM writes it and the PO checks it; Lionel is not asked (English only). Where `en.ts` already holds English for the same French under another context (« Personne » under `EntityEditor`, the 27 actions under `ShortcutsHelpDialog`), the SM reuses it unless it reads wrong in the new place, and says so. The group names that are already English: the SM decides how they get a key, and the English app shows the same words.
- **No French wording change.** Any French source text that changes goes to Lionel word for word before the fix.
- **`fr.ts`:** every new key, and the 40 `ShortcutsHelpDialog` entries it lacks, added like its other entries.
- **The full guard:** every `self.tr` source has an `en.ts` key in its context with a finished translation, with no known-gaps list left. Literal sources are read from the code as Python builds them (`\u` escapes resolved); the 7 variable calls are checked on the values they receive, read from the registry (`get_all_shortcuts()` and `NAVIGATION_MODE_DESCRIPTION`) in each context that uses them. If Story 16.1 started a frozen list, Story 16.2 empties it and removes it. Story 16.1's checks stay. The guard fails when one key is removed (shown in the story's test record, as a mutation).
- **The three file-dialog filters stay out of `en.qm`** unless the SM finds a reason. They have an `en.ts` key, so the guard above holds without touching them; a check against `en.qm` would trip on them. If the SM finds a reason to include them, it tells the orchestrator first: 10.13 recorded `BACKLOG-EN-QM` as Lionel's backlog item (l.270, l.752).
- **Re-measure first.** The counts above were taken on `1bb6f57`. Stories 15.1, 16.1 and 14.1 add texts of their own, so the SM re-measures on main after all three are merged, with a probe of its own.
- **Rebuild the `.qm` files the way Story 11.5 did**, after the rebase on Story 14.1: hand edits, no `pyside6-lupdate`, `filter_ts_1014.py`, `pyside6-lrelease`; `fr.qm` byte-identical; `qm_compare.py`: the new `en.qm` differs from main's only in the new messages.
- Ships with the next release (none is planned), with a CHANGELOG `[Unreleased]` entry.
- Out of scope: any French wording change, including the English group names in the French app; the three file filters; detection, review logic and written output.

**Acceptance (Story 16.2):**

1. Every `tr()` call in `gdpr_pseudonymizer/gui/`, literal or variable, gets English from the shipped `en.qm` (`translate()` returns a non-empty string), apart from the three file filters left out on purpose.
2. The guard is on CI: every `self.tr` source has an `en.ts` key in its context with a finished translation, no known-gaps list; it fails when one key is removed.
3. The French app is unchanged: no French source text changed unless Lionel approved it word for word, and `fr.qm` is byte-identical to main's.
4. Every new English text is listed in the story, written by the SM and checked by the PO.
5. `qm_compare.py` over every message: the new `en.qm` differs from main's (after Story 14.1) only in the new messages.
6. Tests first on CI; full CI green; QA review; one read-only Codex review of the final head, with a Codex stopping rule written in the story.
7. Story 16.2 merged after Story 14.1, with `en.qm` rebuilt after the rebase.
8. CHANGELOG `[Unreleased]` entry.
9. Before the release, Lionel's hand check of the English app passes: the results counts, the review status tags, the batch screen and the shortcut list on the settings screen show English.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge, under the story's stopping rule.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

Order on main: Story 15.1, Story 16.1, Story 14.1 (rebased on both), Story 16.2, each with its CHANGELOG `[Unreleased]` entry. They ship with the next release, none planned. Before that release, Lionel hand-checks the English app. No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] The French app shows exactly what it shows today.
- [ ] English changes only by the 9 symbols put back and the 5 new labels (Story 16.1) and the new English of Story 16.2, written by the SM and checked by the PO.
- [ ] No CLI change, no mapping-table schema or file format change; the `.qm` files are still found where `translator.py` looks for them, in the package and in the standalone builds.

## Risk Mitigation

- **Primary risks:**
  - Fixing the key alone makes 9 labels show « u25b6 »-style text in English.
  - `en.qm` is binary: Stories 15.1, 16.1, 14.1 and 16.2 each rebuild it, so a rebase that keeps one side's file loses the other's messages.
  - Rewriting `\u` escapes in the code could change a French string by one character.
  - A guard on every `tr()` source would fail on today's gaps and block CI before Story 16.2 fills them.
  - English reused from another context can read wrong in its new place.
- **Mitigation:**
  - The 9 symbols are put back, and Acceptance 1 of Story 16.1 checks the exact English string.
  - `en.qm` rebuilt from the merged `.ts` files after each rebase, and `qm_compare.py` run against main's.
  - Acceptance 3 of Story 16.1 checks the French run-time strings byte for byte.
  - The full guard comes with Story 16.2, once every gap has English; a frozen list in Story 16.1, if any, may only shrink.
  - The PO checks every English text; Lionel's hand check before the release.
- **Rollback plan:** revert the story's merge commit; nothing is released until Lionel's go.

## Definition of Done

- [x] Story 16.1 merged: the 29 labels show their English in the English app (30 call sites: 31 when this epic was written, until Story 15.1 merged the two « déjà connu » calls into one, `gui/widgets/entity_panel.py:360`), the 9 ⚠ ones with their symbol back, and the 5 same-cause labels with the English the PO checked, measured with `translate()` on the shipped `en.qm`; the French app unchanged; CHANGELOG `[Unreleased]` entry. Merged 2026-11-25 as PR #136, squash `c4f26fe`
- [x] `en.ts` and `fr.ts` hold no broken `\u` run; `.qm` rebuilt as in Story 11.5; `fr.qm` byte-identical; `qm_compare.py` shows only the intended messages (`messages=358 differing=34` and `messages=353 differing=29`; QA's rebuild of `en.qm` byte-identical to the committed file)
- [x] Story 16.1's guard on CI, shown to fail when a key is broken again (tests first `22d7b36`: 38 xfailed, 0 XPASS on each CI leg; QA re-ran the tests-first commit with `--runxfail` and the mutants)
- [ ] Story 16.2 merged: every `tr()` call has English in the shipped `en.qm` apart from the three file filters; `fr.ts` holds the 40 `ShortcutsHelpDialog` entries; the full guard on CI with no known-gaps list, shown to fail when a key is removed
- [ ] For each story: tests-first commit and draft PR, QA review, read-only Codex review of the final head (Story 16.1: tests first `22d7b36`, draft PR #136; QA gate PASS on `a531f85`; Codex review 1 on `6b0348b`: no findings. Story 16.2 to come)
- [ ] No regression in existing features (full CI green) (Story 16.1: main's CI on `c4f26fe` green, Test Matrix 45707113923: 3,824 passed on each of ubuntu 3.11, ubuntu 3.13 and macOS; Windows 3,674 passed, 3 skipped; Code Quality, Documentation and CodeQL green. Story 16.2 to come)
- [ ] Order kept: 15.1, 16.1, 14.1 (rebased on both), 16.2 (15.1 merged 2026-11-24, `4c40dc2`; 16.1 on 2026-11-25, `c4f26fe`; 14.1, rebased on `c4f26fe`, on 2026-11-27, `2f18895`. 16.2 to come)
- [ ] Before the next release: Lionel's hand check of the English app passes

---

## Story Manager Handoff

"Please write Story 16.1 for this epic (Lionel, 2026-11-23: "yes", the 29 English labels that show in French get their own small story, before Story 14.1). Key considerations:

- This fixes the translation files of an existing PySide6 desktop app so that the English it already holds is found, gives English to 5 labels of the same cause, and adds a guard. Nothing else.
- Integration points: `gdpr_pseudonymizer/gui/i18n/en.ts`, `fr.ts`, `en.qm` (`fr.qm` rebuilt, byte-identical, not staged); `translator.py` (French loads no file); the 31 call sites of the table and the 5 same-cause labels, in `gui/widgets/entity_panel.py`, `entity_editor.py`, `passphrase_dialog.py`, `step_indicator.py` and `gui/screens/processing.py`, `validation.py`, `batch.py`, `database.py`, `settings.py`, `stub.py`; `tests/unit/gui/test_i18n.py`.
- Re-measure the 29 keys, the 31 call sites, the 9 broken translations and the five same-cause labels with your own probe (the PM's is `rgpd-analysis\r161\pm\pm161.py`). Cite code lines; the `.ts` `<location>` lines are stale.
- The 9 ⚠ translations get their symbol back with the same words, as listed in the Scope. Propose the English of the 5 same-cause labels in the story; the PO checks it. Lionel is not asked: English only, no French wording change.
- Rebuild the `.qm` files as Story 11.5 did (hand edits, no `pyside6-lupdate`, `filter_ts_1014.py`, `pyside6-lrelease`, `qm_compare.py`, `fr.qm` byte-identical).
- Design the guard under the constraints of Story 16.1's Scope; show it failing on a broken key.
- Order: after Story 15.1 is merged; rebase and rebuild `en.qm` then; Story 14.1 after 16.1, then Story 16.2.
- Tests first; QA; one read-only Codex review under the story's stopping rule; Lionel's hand check of the English app before the release.
- Out of scope: any French wording change, and everything listed for Story 16.2.
- Each story must include verification that existing functionality remains intact.

Story 16.2 is written after Story 14.1 is merged (Lionel, 2026-11-24: "yes"), from its section above: re-measure on main first, write the English (PO checks it), add the full guard.

The epic should leave the English app showing English everywhere, with a test that keeps every key from going missing again."
