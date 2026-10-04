# Held-Out Set

## Purpose

A small set of synthetic French documents, kept apart from the 25-document main corpus. It shows whether a detector change generalises or only fits the strings of the main corpus (Epic 10, gate G5). Story 10.1 created it.

**This set is never used for tuning.**

## Rules for detector stories (10.2 onwards)

- **Detector-story agents must not open `held_out/documents/` or `held_out/annotations/`.** Every later story's Dev Notes must repeat this rule.
- Detector stories read only the four aggregate lines in `accuracy-output.txt`: `[HELD-OUT Overall]`, `[HELD-OUT PERSON]`, `[HELD-OUT LOCATION]`, `[HELD-OUT ORG]`. They never read held-out FP/FN lists, per-document breakdowns or entity text.
- No held-out entity text may appear outside this folder: not in detector resources (`gdpr_pseudonymizer/resources/**`), unit tests, stories, the QA report, the CHANGELOG or PR text. A non-slow guard test enforces this (Story 10.1, Task 5.5b).
- A gain on the main corpus with a loss on the held-out set is reported as a red flag for overfitting (G5).

## How it is scored

The accuracy suite scores the held-out set separately from the main corpus, with the same detector and the same `match_entities` scorer (`tests/accuracy/conftest.py`). The four aggregate lines above are printed and nothing else. Held-out entities are never added to the main-corpus totals.

## Layout

```
held_out/
├── README.md                 # this file
├── documents/<stem>.txt      # synthetic documents (6)
└── annotations/<stem>.json   # same schema as tests/test_corpus/annotations/
```

## Authoring and annotation

- Text authored by an LLM agent (the Story 10.1 dev agent), reviewed by Lionel on 2026-10-03. No LLM-calling script or prompt is committed.
- All people, companies and records are invented. No user data and no real public figures (product constraint 4).
- The documents are seeded with the same kinds of hard case as the main corpus (particle surnames, Mc/Mac names, apostrophes, greeting and salutation lines, a "Last, First" name, initials, role acronyms, organisation + country, places inside organisation names, foreign places, US/UK abbreviations, defined-term aliases). The strings themselves do not come from the main corpus.
- Annotations are made **by hand** under [`../annotations/GUIDELINES.md`](../annotations/GUIDELINES.md), after Lionel has reviewed the text (STOP B). They are never pre-annotated by `HybridDetector`, by the analysis scripts, or by `scripts/auto_annotate_corpus.py` (retired in Story 10.1; it must never be used here).
