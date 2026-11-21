# Epic 13: Place Pseudonyms That Fit the Word Before Them - Brownfield Enhancement

**Epic Goal:** A place pseudonym is chosen to fit the word right before the place, where the place first appears in the document that gives it its pseudonym, so no drawn place name reads wrong in the French text around it (no more « à Grand Est » or « de Le Centre-Ville »). For example:

- « à »: a name without an article that reads after « à »;
- « en »: a name that reads after « en »;
- « de »: a name starting with a consonant, without an article;
- « d' »: a name starting with a vowel;
- « du » or « au »: a masculine name that contracts that way;
- no such word: a name without an article.

One place keeps one pseudonym in every document. Existing mapping databases keep working: a pseudonym already stored is reused as stored.

**Target Release:** the next release (none is planned). Story 13.1 lands on main first; no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.2 (Epic 11, released 2026-11-17). Epic 12 (Windows installer, Story 12.1) also targets the next release; the two epics are independent.
**Successor:** none set. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

---

## Scope Rule

One story, Story 13.1, on place (LOCATION) pseudonyms only. Nothing else. Out of scope: organisation names, person names, and any detection change.

Lionel's decision, word for word:

- Story 13.1, Lionel, 2026-11-19: a small story makes a place get a pseudonym of the same kind and stops the names that break « à » and « de » from reading wrong, shipped with the next release. The question asked: "Shall the BMAD agents write a small story so a place gets a pseudonym of the same kind and the names that break « à »/« de » no longer read wrong, shipped with the next release?" His answer: "yes".
  - Its "same kind" part is replaced by the 2026-11-20 redesign below. The line stays as history.
- Story 13.1, Lionel, 2026-11-20: he was asked the PO's question whether a country or a department should get a region instead of a city, and whether 8 old region names (« Provence », « Alsace », « Lorraine »…) should count as regions. One option gave the departments and the 7 "countries and international" entries of `french_geography.json` a region, except « Berlin », « Londres » and « Madrid », which kept a city. His words: "i don't understand: what's (c)'s actual rule, spelt out?" Then, after seeing that option spelt out: "that looks useless. why would the place be part of the list?"
- Story 13.1, Lionel, 2026-11-20: Story 13.1 is redesigned. The place pseudonym is chosen from the word just before the place (« à », « en », « de », « d' », « du », « au »), no longer from the kind of place in `french_geography.json`. The question asked: "Shall the SM redesign Story 13.1 so the pseudonym is chosen from the word just before the place (« à », « en », « de », « d' », « du », « au »)?" His answer: "yes, redesign it".

---

## Existing System Context

- **Current relevant functionality:** the default pseudonym theme is `neutral`, in the desktop app (`gdpr_pseudonymizer/gui/config.py:19`) and in the CLI (`gdpr_pseudonymizer/utils/config_manager.py:32`). `LibraryManager._select_location` (`gdpr_pseudonymizer/pseudonym/library_manager.py` l.709) draws uniformly from `_flatten_location_list` (l.272), which joins the cities, the planets or countries, and the regions of the theme, whatever the kind of the original place. Each draw must pass `accepts_value` (l.237): the Story 11.6 rule (no word of the document) and the Story 11.5 check (not given yet). Only the place name is replaced; the text around it is kept as it is.
- **What the draw knows today (PM checked, 2026-11-20):** `LibraryManager.assign_pseudonym` (l.424) gets the entity type, not the text around the place. A detected place carries its position in the document (`start_pos`, `gdpr_pseudonymizer/nlp/entity_detector.py` l.32). The draw is called from `gdpr_pseudonymizer/core/document_processor.py` (l.999), from `gdpr_pseudonymizer/pseudonym/assignment_engine.py` (l.278, l.305, l.473), and from Story 11.7's replace flow in `gdpr_pseudonymizer/core/saved_own_words.py` (l.400, l.430), which draws with no document around it.
- **Technology stack:** Python 3.11-3.13, Poetry, spaCy 3.7 (`fr_core_news_lg`), PySide6-Essentials, pytest.
- **Integration points:** `gdpr_pseudonymizer/pseudonym/library_manager.py` (`assign_pseudonym`, `_select_location`, `_flatten_location_list`, `accepts_value`, the library loader and its floors), the draw's callers above, the three libraries `gdpr_pseudonymizer/resources/pseudonyms/{neutral,star_wars,lotr}.json` (an identical copy sits in `data/pseudonyms/`), `CHANGELOG.md`. `gdpr_pseudonymizer/resources/french_geography.json` and `gdpr_pseudonymizer/nlp/geography_dictionary.py` are no longer the basis; they may serve only as a fallback, and that is the SM's call.

---

## Stories

### Story 13.1: A Place Pseudonym Fits the Word Before the Place

**Problem** (measured by the orchestrator on 2026-11-19 on origin/main `5e270fa`; facts marked PM checked by the PM on the same commit):

- In `neutral.json`, the `locations` keys do not say what they hold:
  - `cities`: 50 cities, including « Le Havre » and « Le Mans »;
  - `countries`: 20 French regions, such as « Bretagne », « Grand Est », « Pays de la Loire » and « Île-de-France »;
  - `regions`: 10 invented districts, all with an article (« La Gare Centrale », « Le Centre-Ville », « Le Secteur Est »…).
- A city can therefore become a region or a district, and the kept text around it reads wrong: « à Lyon » can become « à Grand Est », « à Le Mans » or « à La Gare Centrale », and « de Lyon » can become « de Le Centre-Ville ».
  - After « à »: 32 of the 80 names (40%) give wrong French: the 20 regions, the 10 districts, and « Le Havre » and « Le Mans ».
  - After « de »: 12 of the 80 (15%) do.
- No real name leaks; the output only reads badly. Lionel saw « à Grand Est » and « de Le Centre-Ville » in his own hand check of 2.3.2 (2026-11-17).
- `star_wars.json` and `lotr.json` have no name with a French article. Their names are invented, so they are hardly affected. lotr has one name with an English article, « The Shire » (PM checked). The `planets` key of lotr holds places such as « Weathertop » and « Helm's Deep » (PM checked).
- `french_geography.json` (used by the detector through `nlp/geography_dictionary.py`) lists 100 cities, 18 regions, 7 countries and 101 departments (PM checked). The libraries hold no departments and no real countries.
- **Added by the PM (2026-11-19), for the SM and for Lionel:** the « de » count above covers names with an article only. The same breakage also comes from:
  - regions after « de »: « de Grand Est », « de Pays de la Loire », « de Île-de-France »;
  - elision: 8 neutral cities start with a vowel (« Angers », « Aix-en-Provence », « Amiens », « Annecy », « Orléans », « Argenteuil », « Avignon », « Asnières-sur-Seine »), so « de Lyon » can become « de Angers », and « d'Orléans » can become « d'Lyon ».

  The SM re-measures every case with the chosen mechanism. Whether elision is covered is a question for Lionel (see "Open questions" below).
- **Measured by the orchestrator on 2026-11-20** on the dev corpus (`tests/test_corpus/annotations/` with `tests/test_corpus/business_documents/` and `tests/test_corpus/interview_transcripts/`: 25 documents, 263 LOCATION mentions). This is why the kind of place is no longer the basis:
  - 187 of the mentions are in `french_geography.json`: cities 91, regions 10, departments 4, countries and international 82;
  - **76 (29%) are not**, for example « Europe » ×21, « UK », « US », « Palo Alto », « Barcelone », « Avenue de la Grande Armée »;
  - the word right before the place is « à » 38 times, « de » 31, nothing 29 times, « en » 10, « du » 6. Most of the rest are company names (« Microsoft France ») or list items;
  - places are found mainly by spaCy, not by that list.

**Scope (the SM writes the detailed story):**

- **Fits the word before it.** The pseudonym is chosen to fit the word right before the place, where the place first appears in the document that gives it its pseudonym (the cases of the Epic Goal: « à », « en », « de », « d' », « du » or « au », no such word). The SM and the dev define how that word is read and what happens when no free name fits it. They also define the rule for the `star_wars` and `lotr` themes, and for Story 11.7's replace flow, which draws with no document around it. `neutral_id` (« LOC-001 ») is checked and left unchanged.
- **The geography list is no longer the basis.** `french_geography.json` may serve only as a fallback; whether it does is the SM's call.
- **One place, one pseudonym.** A place keeps one pseudonym in every document.
- **No wrong French after the word it was chosen for.** Names whose article breaks the word before them (« à Grand Est », « à Le Mans », « de Le Centre-Ville ») are not drawn for that word. The mechanism is the SM's and the dev's choice.
- **Realistic examples.** The story shows realistic examples of what a user gets, in short French sentences, before and after, for each case (« à », « en », « de », « d' », « du » or « au », no such word), in each of the three themes.
- **Lionel approves the French first.** Any change to the French pseudonym lists, or to French output text that Lionel would see, is shown to him first. For each change the story gives the French, where it appears, an example and the English. Lionel approves it word for word before it is committed.
- **Stored pseudonyms stay as stored.** Existing mapping databases keep working: a pseudonym already stored is reused as stored. No migration rewrites stored values unless Lionel decides otherwise (see "Open questions" below).
- **The other draw rules still apply.** Every draw still passes the Story 11.6 rule (no word of the document) and the Story 11.5 check (the review list shows the pseudonym that is written). If the mechanism changes text around the name, the review list and the written file must agree.
- **Pool size.** The names that fit one word are fewer than today's single pool. The story measures, per theme and per word before the place, how many distinct real places a database can hold before the `Location-NNN` fallback, and reports it before merge (as Story 11.6 did for names).
- If the libraries change, both copies change together: `gdpr_pseudonymizer/resources/pseudonyms/` and `data/pseudonyms/`. The loader's floors still hold.
- Ships with the next release (none is planned); it lands on main first, with a CHANGELOG `[Unreleased]` entry.
- Proof: tests first on CI. Before the release, Lionel hand-checks a document with places after « à », « en », « de », « d' », « du » and « au », and with no word before them.
- Out of scope: organisation names, person names, and any detection change.

**Known limit (recorded by the PM, 2026-11-20):** a place that later appears after a different word keeps the pseudonym chosen for its first appearance. That holds in the same document and in later documents, since one place keeps one pseudonym in every document. So a place first seen after « de » can later read wrong after « en ».

**Void since 2026-11-20:** the rule based on the kind of place (a city for a city, a region for a region, as far as `french_geography.json` knows the kind), and the PO's question whether a country, a department or an old region name gets a city or a region (the story's Q3).

**Open questions (for Lionel; the SM re-frames them for the new rule; the story does not decide them):**

- **Stored pseudonyms** (the story's Q1). A real place already stored with a pseudonym that reads wrong (a city stored as « Grand Est ») keeps it, so later documents still read « à Grand Est ». Does Lionel want those stored values rewritten, or kept as stored? Kept as stored is the default until he decides.
- **Elision** (the story's Q2). Is elision covered (« de Angers », « d'Lyon »), or left as it is?
- **Masculine or plural names** (the story's Q4). Which masculine or plural names are drawn, and for which places (« dans le Grand Est », « des Hauts-de-France »)?
- **The exact French name lists:** which names serve after each word. Lionel approves them word for word.

**Acceptance (epic level):**

1. With every theme, a new place pseudonym fits the word right before the place where it first appears in the document that gives it its pseudonym, for each case (« à », « en », « de », « d' », « du » or « au », no such word). The rule for a word no free name fits, for `star_wars` and `lotr`, and for Story 11.7's replace flow is written in the story and tested. `neutral_id` is unchanged.
2. No drawn place name gives wrong French after the word it was chosen for in the default `neutral` theme: no « à Grand Est », no « à Le Mans », no « de Le Centre-Ville ». Each case that the story covers is tested.
3. One place keeps one pseudonym in every document. The known limit (a later appearance after a different word keeps the first pseudonym) is written in the story.
4. The story shows realistic before-and-after examples of what a user gets (each case, in each theme).
5. Every change to the French lists or to French output text was shown to Lionel (French, where it appears, an example, the English) and approved word for word before it was committed.
6. An existing mapping database works unchanged: a stored pseudonym is reused exactly as stored, and nothing rewrites stored values (unless Lionel decides otherwise).
7. Every draw still passes the Story 11.6 rule and the Story 11.5 check; the review list and the written file agree.
8. The per-theme pool size per word before the place, before the `Location-NNN` fallback, is measured and reported before merge.
9. Tests first on CI; full CI green; QA review; one read-only Codex review of the final head.
10. CHANGELOG `[Unreleased]` entry.
11. Before the release, Lionel's hand check of a document with places after « à », « en », « de », « d' », « du » and « au », and with no word before them, passes.

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

Story 13.1 lands on main with its CHANGELOG `[Unreleased]` entry and ships with the next release, none planned. Before that release, Lionel hand-checks a document with places after « à », « en », « de », « d' », « du » and « au », and with no word before them. No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] Existing mapping databases open and work unchanged; a stored pseudonym is reused as stored.
- [ ] No CLI flag, GUI screen, mapping-table schema or file format changes.
- [ ] Person and organisation pseudonyms are unchanged; detection is unchanged.

## Risk Mitigation

- **Primary risks:**
  - Splitting the pool by the word before the place makes each pool smaller, so the `Location-NNN` fallback comes sooner. The neutral pools are 50, 20 and 10 today; star_wars has 30, 30 and 20, and lotr 30, 30 and 20. The names that fit « d' » (a vowel first) or « du » and « au » (masculine) are few.
  - The pseudonym fits only the first appearance; a later appearance after a different word can read wrong (the known limit above).
  - If the mechanism changes text outside the place name, the review list and the written file can disagree, or a DOCX, PDF, Excel or CSV output is written differently from a text output.
  - A name can still disagree in gender or article with the words around it (« du » and « au » need a masculine name; « dans le » or « la » before the place).
- **Mitigation:**
  - Pool sizes measured per theme and per word before the place, before merge.
  - Tests that the review list and the written file agree.
  - Realistic examples for each word, shown to Lionel with the French text.
  - Lionel's hand check before the release.
- **Rollback plan:** revert the story's merge commit; nothing is released until Lionel's go.

## Definition of Done

- [x] Story 13.1 merged: a place pseudonym fits the word right before the place where it first appears (with a tested rule for a word no free name fits, for `star_wars` and `lotr`, and for Story 11.7's replace flow); no drawn place name reads wrong after the word it was chosen for in the `neutral` theme; one place keeps one pseudonym in every document; stored pseudonyms reused as stored; Story 11.6 and 11.5 rules still hold; pool sizes measured; CHANGELOG `[Unreleased]` entry. Merged 2026-11-21 as PR #133, squash `c145963`
- [x] Every change to French lists or French output text approved word for word by Lionel before it is committed (the lists L1 to L6, the 15 names and the CHANGELOG entry at STOP B, all on 2026-11-20; Story 13.1, Decisions Recorded)
- [x] Tests-first commit and draft PR, QA review, read-only Codex review of the final head (tests first `f459965`, draft PR #133; QA gate PASS on `24b9c86`; Codex review 1 on `6f766a7`: APPROVE, no findings)
- [x] No regression in existing features (full CI green). Main's CI on `c145963` green (Test Matrix 44878820615: 3,676 passed on each of ubuntu 3.11, ubuntu 3.13 and macOS; Windows 3,526 passed, 3 skipped; Code Quality, Documentation and CodeQL green; Performance & Stability 44878820682: 4 passed, 3 skipped)
- [ ] Before the next release: Lionel's hand check of a document with places after « à », « en », « de », « d' », « du » and « au », and with no word before them, passes

---

## Story Manager Handoff

"Please revise Story 13.1 for the 2026-11-20 redesign (Lionel: "yes, redesign it"). Key considerations:

- This changes how an existing Python/Poetry CLI and PySide6 desktop app draws place pseudonyms; nothing else.
- The pseudonym is chosen to fit the word right before the place, where the place first appears in the document that gives it its pseudonym: « à », « en », « de », « d' », « du » or « au », or no such word (the Epic Goal gives what fits each). The kind of place is no longer the basis; `french_geography.json` may serve only as a fallback, and that is your call.
- Integration points: `gdpr_pseudonymizer/pseudonym/library_manager.py` (`assign_pseudonym` l.424, `_select_location` l.709, `_flatten_location_list` l.272, `accepts_value` l.237, the loader's floors); the draw's callers (`core/document_processor.py` l.999, `pseudonym/assignment_engine.py` l.278, l.305, l.473); Story 11.7's replace flow (`core/saved_own_words.py` l.400, l.430), which has no document around the place; the three libraries in `gdpr_pseudonymizer/resources/pseudonyms/` and their copy in `data/pseudonyms/`; `CHANGELOG.md`.
- In `neutral.json`, the `countries` key holds the French regions and the `regions` key holds the invented districts.
- Define how the word before the place is read, what happens when no free name fits it, and the rule for `star_wars`, `lotr` and the replace flow. The mechanism is your choice and the dev's. Show realistic examples of what a user gets for each word, and re-measure every case with the chosen mechanism.
- One place keeps one pseudonym in every document. Record the known limit: a place that later appears after a different word keeps the pseudonym chosen for its first appearance.
- The kind-based rule and the PO's question on a country, a department or an old region name (Q3) are void. Re-frame for Lionel the questions still open: stored pseudonyms (Q1), elision (Q2), masculine or plural names (Q4), and the exact French name lists.
- Any change to the French lists or to French output text: give Lionel the French, where it appears, an example and the English; he approves word for word before it is committed.
- Stored pseudonyms are reused as stored; no migration unless Lionel decides otherwise.
- Every draw must still pass the Story 11.6 rule and the Story 11.5 check.
- Measure the per-theme pool size per word before the place, before the `Location-NNN` fallback, and report it before merge.
- Next release; tests first; QA; one read-only Codex review; Lionel's hand check before the release.
- Out of scope: organisations, persons, detection.
- Each story must include verification that existing functionality remains intact.

The epic should leave every place pseudonym reading as natural French after the word before it where the place first appears, while existing databases keep the pseudonyms they already hold."
