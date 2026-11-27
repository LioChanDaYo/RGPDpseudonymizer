# Epic 14: First Names Found on Short Text - Brownfield Enhancement

**Epic Goal:** A first name on its own in a short text is found and offered for review far more often than today, so it is not left in clear text. Short texts are email greetings and sign-offs, chats, one-line notes and single spreadsheet cells, for example « Bonjour Nadia, », « Merci Pierre pour ton aide. » or « Cordialement,⏎Véronique ». And when the detector finds nothing, the desktop app no longer suggests that the document may hold no personal data.

**Target Release:** the next release (none is planned). Story 14.1 lands on main first; no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.2 (Epic 11, released 2026-11-17). Epics 12 (Windows installer, Story 12.1) and 13 (place pseudonyms, Story 13.1) are done and also target the next release; the three epics are independent.
**Successor:** none set. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

**Why a new epic (PM, 2026-11-22):** this is a detection recall fix with a user-facing message, for the next release; Epic 13's scope rule allows place pseudonyms only and excludes any detection change, Epic 10 (v2.3, precision) shipped with v2.3.0, and Epic 9 is the v3.0 fine-tuned model, which is out of scope here.

---

## Scope Rule

One story, Story 14.1, on lone first names missed on short text and on the desktop « Aucune entité détectée » message. Nothing else. Out of scope: organisation and place detection, person names written in full (already strong), and other spaCy models.

Lionel's decisions, word for word:

- Lionel, 2026-11-21: the question asked: "Should I have an agent measure how often a lone first name is detected as a place, on the ordinary test documents?" His answer: "yes, measure it".
- Lionel, 2026-11-22: the question asked: "Should an agent measure how often each of the app's first names is missed in short realistic sentences, before deciding on a fix?" His answer: "yes, measure it".
- Story 14.1, Lionel, 2026-11-22: the question asked: "Should the BMAD agents write a story for the next release to fix first names missed on short text, and the misleading « peut-être pas de données personnelles » message?" His answer: "yes, write the story".

---

## Existing System Context

- **Current relevant functionality:** `HybridDetector` runs spaCy `fr_core_news_lg` and the app's own patterns. The spaCy label map (`gdpr_pseudonymizer/nlp/spacy_detector.py:204-213`) maps only PER, LOC, GPE and ORG (and their long forms); any other label, MISC included, is dropped (PM checked). The detector also loads its own first-name list, `gdpr_pseudonymizer/resources/french_names.json`, through `gdpr_pseudonymizer/nlp/name_dictionary.py`.
- **The two first-name lists (PM checked, 2026-11-22, on `1bb6f57`):**
  - the pseudonym library `gdpr_pseudonymizer/resources/pseudonyms/neutral.json` holds 739 distinct first names (387 male, 352 female);
  - `french_names.json` holds 505 entries, 451 distinct;
  - the two lists share 278 names;
  - « Hélène » is in `french_names.json` but not in the library; « Elodie » without the accent is in neither, while « Élodie » is in both; « Azure » and « Ruby » are in the library only.
- **What the user sees when a name is missed:**
  - Desktop app: a missed name is not in the review list (`gdpr_pseudonymizer/gui/workers/detection_worker.py:167-191`). The only way to catch it is to select it in the read-only editor and use « Ajouter comme entité » (`gdpr_pseudonymizer/gui/widgets/entity_editor.py:359-367`).
  - Desktop app, nothing found at all: `gdpr_pseudonymizer/gui/screens/processing.py:317-319` shows the warning panel. Its text is set in `retranslateUi` (`processing.py:170-174`): « Aucune entité détectée. Le document ne contient peut-être pas de données personnelles, ou le format n'est pas supporté pour l'analyse NLP. » « Continuer ▶ » is still offered. The text is a Qt source string, also in `gdpr_pseudonymizer/gui/i18n/fr.ts:1123` and `gdpr_pseudonymizer/gui/i18n/en.ts:1130` (English: "No entities detected. The document may not contain personal data, or the format is not supported for NLP analysis."), and in the compiled `fr.qm` and `en.qm` beside them.
  - Command line: it asks for a missed name only when nothing is left to review (`ask_for_missed_names`, `gdpr_pseudonymizer/validation/workflow.py:1014`, Story 10.18). Context only: the CLI line « No entities detected in document. » (`validation/workflow.py:221`) is not in scope.
- **Technology stack:** Python 3.11-3.13, Poetry, spaCy (`fr_core_news_lg`), PySide6-Essentials, pytest.
- **Integration points:** `gdpr_pseudonymizer/nlp/spacy_detector.py` (label map), `gdpr_pseudonymizer/nlp/hybrid_detector.py`, `gdpr_pseudonymizer/nlp/name_dictionary.py` and `gdpr_pseudonymizer/resources/french_names.json`, the library first names in `gdpr_pseudonymizer/resources/pseudonyms/neutral.json`, `gdpr_pseudonymizer/gui/screens/processing.py`, `gdpr_pseudonymizer/gui/i18n/{fr,en}.ts` and `.qm`, `CHANGELOG.md`.

---

## Stories

### Story 14.1: A Lone First Name on Short Text Is Found, and « Aucune entité détectée » No Longer Reassures

**Problem** (measured by QA on 2026-11-22 on origin/main `1bb6f57`; full log `C:\Users\devea\Documents\GitHub\rgpd-analysis\r142\qa\measure.log`, outside the repository, every case in `grid_cases.jsonl` beside it):

- **The test.** The 739 first names of `neutral.json` (387 male, 352 female), each put in 10 short invented French sentences, were run through the app's real detector (`HybridDetector`, `fr_core_news_lg` 3.8.0). The sentences:
  - « Bonjour X, »
  - « Cordialement,⏎X »
  - « Merci X pour ton aide. »
  - « X a appelé hier. »
  - « J'ai vu X ce matin. »
  - « X viendra demain à la réunion. »
  - « Réponse de X : d'accord. »
  - « Comme convenu avec X, nous signons lundi. »
  - « — X »
  - a two-line email
- **The result, over 7,390 cases:** PERSON 69.4%, LOCATION 6.0%, ORG 1.1%, **missed 23.5%. A missed name is left in clear text.**
  - Worst sentences: « Merci X… » 38.2% missed, the two-line email 37.5%, « Réponse de X : » 32.1%.
  - 157 of the 739 names are missed in 5 or more of the 10 sentences. That includes Pierre, Nicolas, Sarah, Manon, Nadia, Georges, Bernard and Véronique, each missed in 9 of 10 (all except « Bonjour X, »).
  - Female names are missed 29.7% of the time, male names 17.9%.
- **The cause.**
  - 79.9% of the misses: spaCy tagged the name MISC, and the label map drops it.
  - 20.1%: spaCy found nothing at all (206 of these are in « Réponse de X : »).
- **What the user sees.** The missed name is not in the desktop review list; it can be caught only by selecting it and using « Ajouter comme entité ». If it was the only name in the document, the desktop app says « Aucune entité détectée. Le document ne contient peut-être pas de données personnelles… » and still offers « Continuer ». The command line asks for missed names only when nothing is left to review.
- **The long business documents of the dev corpus behave much better.** Lone library first names were caught 37 times out of 38, and none of the first-name MISC spans there is a gold PERSON left in clear text. **The risk is short texts.**
- **A fix simulated in memory only:** "a MISC span or token whose text is a library first name becomes PERSON".
  - Token reading: misses fall from 23.5% to 4.7% on the test sentences.
  - Cost: wrong PERSONs.
    - On the 25 dev documents: « Azure » ×14 and « Ruby » ×1, both in the library's first names.
    - On 156 invented non-name sentences: 32 more, such as « Pierre de taille », « Alerte Ambre » and « Aurore boréale ».
    - « M. Bernard » and « Mme Laurent » would shrink to the bare surname.
  - It does not help names outside the library (« Hélène », « Elodie »), nor the 20% where spaCy finds nothing. (PM note: « Hélène » is in `french_names.json`, so a mechanism using that list would reach it; « Elodie » without the accent is in neither list.)

**Scope (the SM writes the detailed story):**

- **Fewer first names missed on short text.** The SM and the dev choose the mechanism: MISC handling, a first-name dictionary, the detector's own list `french_names.json` (451 distinct names), or a mix.
- **Measured the same way.** The chosen mechanism is measured with the same grid (the 739 names in the 10 sentences), in both readings (span and token), with its false-positive cost on the 156 non-name sentences, and on the 25 dev-corpus documents (`tests/test_corpus/annotations/` with `business_documents/` and `interview_transcripts/`). The « M. Bernard » / « Mme Laurent » shrink is checked and reported.
- **Lionel decides the trade-off with numbers.** Before the mechanism is fixed in the story, the SM shows Lionel, for each candidate mechanism, the missed rate on the grid and the wrong PERSONs it adds (count and examples, « Azure », « Pierre de taille »…). Leaking a real name is worse than replacing a non-name; still, the false positives are measured and shown to him, and he picks.
- **The misleading message.** The « Aucune entité détectée … peut-être pas de données personnelles » message is changed so it no longer suggests the document holds nothing personal. Its French and English change together in `processing.py`, `fr.ts`, `en.ts`, and the `.qm` files are rebuilt.
- **Lionel approves the French first.** Any new French text is shown to Lionel word for word, with where it appears, an example and the English, and approved before it is committed.
- **No accuracy regression on the dev corpus**, measured as Epic 10 did (gates G1, G3, G5):
  - The dev triggers the CI accuracy workflow on the story branch (`gh workflow run accuracy.yaml --ref <branch> -f reason="14.1"`), cites the run ID and pastes the `[Overall]`, `[PERSON]`, `[LOCATION]`, `[ORG]` and held-out lines from the `accuracy-results` artifact. QA re-runs it independently.
  - The baseline is the latest cited accuracy run on main; the SM finds it and records it in the story.
  - No agent opens, edits or runs `tests/accuracy/` locally, and no agent opens the held-out or final-exam documents; held-out numbers are read only from the CI artifact.
  - Any drop in an overall or per-type recall or precision stops the story and goes to Lionel with the numbers before merge. The simulated fix above already adds wrong PERSONs on the dev documents, so this is expected to need his decision.
- Ships with the next release (none is planned); it lands on main first, with a CHANGELOG `[Unreleased]` entry.
- Proof: tests first on CI. Before the release, Lionel hand-checks short texts with lone first names (greeting, sign-off, « Merci X », « Réponse de X : ») and a document where nothing is found.
- Out of scope: organisation and place detection, person names written in full, and other spaCy models.

**Open questions (for Lionel; the story does not decide them):**

- **The mechanism and its cost.** Which mechanism ships, given its missed rate and the wrong PERSONs it adds (on the grid, the 156 non-name sentences and the dev corpus)?
- **The new message.** The exact French text (and its English) replacing « Aucune entité détectée … ». Lionel approves it word for word.

**Acceptance (epic level):**

1. On the grid (739 names × 10 sentences), the missed rate falls below today's 23.5% with the mechanism Lionel chose; both readings and the per-sentence rates are reported before and after.
2. The false-positive cost of that mechanism (the 156 non-name sentences and the 25 dev documents, with examples) and the « M. Bernard » / « Mme Laurent » result were shown to Lionel with numbers, and he chose the mechanism before it was fixed in the story.
3. Tests cover lone first names in short texts (at least « Merci X… », the two-line email, « Réponse de X : » and « Cordialement,⏎X »), and non-names that must stay unchanged as Lionel decided.
4. When nothing is found, the desktop app no longer says the document may hold no personal data. The new French and English texts are in `processing.py`, `fr.ts`, `en.ts` and the rebuilt `.qm` files.
5. Every new French text was shown to Lionel (the French, where it appears, an example, the English) and approved word for word before it was committed.
6. CI accuracy run on the story branch cited with its run ID and pasted lines, QA re-run cited; no overall or per-type recall or precision drop against main's latest cited run, unless Lionel accepted it with the numbers in front of him.
7. Organisation and place detection, and person names written in full, are unchanged apart from what the accuracy run reports and Lionel accepted.
8. Tests first on CI; full CI green; QA review; one read-only Codex review of the final head.
9. CHANGELOG `[Unreleased]` entry.
10. Before the release, Lionel's hand check of short texts with lone first names, and of a document where nothing is found, passes.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

Story 14.1 lands on main with its CHANGELOG `[Unreleased]` entry and ships with the next release, none planned. Before that release, Lionel hand-checks short texts with lone first names and a document where nothing is found. No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] Existing mapping databases open and work unchanged.
- [ ] No CLI flag, mapping-table schema or file format changes. The only GUI change is the text of the « Aucune entité détectée » warning.
- [ ] Pseudonym generation is unchanged; organisation and place detection are unchanged.

## Risk Mitigation

- **Primary risks:**
  - Wrong PERSONs: words that are also first names (« Azure », « Ruby », « Pierre de taille », « Alerte Ambre », « Aurore boréale ») get replaced.
  - « M. Bernard » and « Mme Laurent » shrink to the bare surname.
  - Names outside the chosen list, and the 20% of misses where spaCy finds nothing, stay missed.
  - A precision drop on the dev corpus, or a held-out change, hidden behind a recall gain.
- **Mitigation:**
  - The grid, the 156 non-name sentences and the dev corpus measured before and after, shown to Lionel with numbers before the mechanism is fixed.
  - CI accuracy runs cited with run IDs, QA re-run, held-out lines read from the artifact.
  - Lionel's hand check before the release.
- **Rollback plan:** revert the story's merge commit; nothing is released until Lionel's go.

## Definition of Done

- [x] Story 14.1 merged: fewer lone first names missed on short text with the mechanism Lionel chose; the « Aucune entité détectée » message no longer suggests the document holds nothing personal; CHANGELOG `[Unreleased]` entry. Merged 2026-11-27 as PR #137, squash `2f18895`
- [x] Grid, non-name sentences and dev corpus measured before and after, and the trade-off decided by Lionel with numbers (Story 14.1, Dev Notes "Measurements" and Decisions Recorded: Q6, "yes, wherever it stands alone", on 2026-11-24; G3 on 2026-11-26. On the head, 0 of the grid's 7,390 cases missed, against 1,738 before, Task 2.4 and QA)
- [x] Every new French text approved word for word by Lionel before it is committed (the message in his own wording, 2026-11-25; the CHANGELOG entry at STOP B, 2026-11-26; Story 14.1, Decisions Recorded)
- [x] CI accuracy run and QA re-run cited; no recall or precision drop unless Lionel accepted it (G1 run 45776619159 on `4367cfe`, QA's G2 run 45781934884 on `0439076`, identical; main's run 45954644200 on `2f18895`, identical. PERSON precision 0.9219 → 0.9091 accepted by Lionel at G3, 2026-11-26; the `[Overall]` precision 0.8068 → 0.8001, the same 20 wrong persons, shown to him in the final PR text of PR #137, which he approved the same day (Story 14.1, Decisions Recorded, "The final PR text"); no recall drop; `docs/qa/ner-accuracy-report.md`, Story 14.1 section)
- [x] Tests-first commit and draft PR, QA review, read-only Codex review of the final head (tests first `282af61`, draft PR #137, 22 xfailed on each CI leg, 18 on Windows, 0 XPASS; QA gate PASS on `0439076`; Codex review 1 on `ac72640`: no P0/P1, its P2 and P3 to `docs/BACKLOG.md` TD-011 and TD-012 on Lionel's answer)
- [x] No regression in existing features (full CI green). Main's CI on `2f18895` green (Test Matrix 45954642815: 3,854 passed on each of ubuntu 3.11, ubuntu 3.13 and macOS; Windows 3,699 passed, 3 skipped; Code Quality, Documentation and CodeQL green; Performance & Stability 45954642908: 4 passed, 3 skipped)
- [ ] Before the next release: Lionel's hand check of short texts with lone first names, and of a document where nothing is found, passes

---

## Story Manager Handoff

"Please write Story 14.1 (Lionel, 2026-11-22: "yes, write the story"). Key considerations:

- This changes how an existing Python/Poetry CLI and PySide6 desktop app detects lone first names, and one desktop warning text; nothing else.
- The problem and its numbers are in the Problem section above (QA, 2026-11-22, `1bb6f57`): 23.5% of lone library first names missed in 10 short sentences; 79.9% of the misses are spaCy MISC spans that the label map (`nlp/spacy_detector.py:204-213`) drops; 20.1% are found by nothing.
- The mechanism is your choice and the dev's: MISC handling, a first-name dictionary, `french_names.json` (451 distinct names, 278 shared with the library's 739), or a mix. Measure each candidate with the same grid (both readings), its false-positive cost on the 156 non-name sentences, and on the 25 dev documents, and report the « M. Bernard » / « Mme Laurent » result.
- Show Lionel the trade-off (missed names versus non-names replaced) with numbers before the mechanism is fixed in the story. Leaking a real name is worse than replacing a non-name, but he sees the false positives.
- Change the « Aucune entité détectée … peut-être pas de données personnelles » text (`gui/screens/processing.py:170-174`, shown at `:317-319`; `gui/i18n/fr.ts`, `en.ts`, rebuilt `.qm`) so it no longer suggests the document holds nothing personal. Give Lionel the French, where it appears, an example and the English; he approves word for word before it is committed.
- Accuracy: the CI accuracy workflow on the story branch (G1), cited run ID and pasted lines, QA re-run, held-out lines from the artifact (G5); any recall or precision drop stops for Lionel (G3). No agent opens `tests/accuracy/`, `tests/test_corpus/held_out/` or `tests/test_corpus/final_exam/`. Record main's latest cited run as the baseline.
- Next release; lands on main first; CHANGELOG `[Unreleased]`; tests first; QA; one read-only Codex review; Lionel's hand check before the release.
- Out of scope: organisation and place detection, person names written in full, other spaCy models.
- Each story must include verification that existing functionality remains intact.

The epic should leave a lone first name in a greeting, a sign-off or a one-line note found and offered for review, and should never let the app tell a user that a document with a missed name may hold nothing personal."
