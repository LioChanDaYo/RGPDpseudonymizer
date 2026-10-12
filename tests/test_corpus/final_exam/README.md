# Final-exam set (Story 10.6 PR B)

A blind test set for the Epic 10 close-out: 30 synthetic French documents written by GPT from a brief Lionel approved (STOP BRIEF, 2026-10-09), annotated independently by two models under `tests/test_corpus/annotations/GUIDELINES.md`, adjudicated by Lionel after Story 10.4 merged, and committed as plain files (Q5 reversed: no encryption).

**Scored exactly once** (AC8): only by a manual `accuracy.yaml` dispatch on `main` with `final_exam="final exam"`, after Lionel's recorded go. The one run is recorded in `RUNS.md`. A re-run is allowed only for an infrastructure failure at the same commit.

**Isolation (every agent):** never open, list or grep this folder. The only files an agent may open, by exact path, are this `README.md`, `RUNS.md` and `FINGERPRINTS.sha256` (anonymous ids and hashes). `git status` and `git diff --stat` are allowed; every content diff excludes the folder (`':!tests/test_corpus/final_exam'`). Final-exam numbers are never used for a decision or for tuning.

Layout:

- `documents/fe_NN.txt`: the 30 documents (`manifest.json` gives each one's half: planted or natural);
- `annotations/fe_NN.json`: the adjudicated annotations, scored by the `final_exam` job;
- `ann_a/`, `ann_b/`: the two model annotations; `decisions.tsv` (one decision per group of identical disagreements), `occurrences.tsv` (per-occurrence decisions for split groups), `spotcheck.tsv`: Lionel's adjudication log;
- `FINGERPRINTS.sha256`: the freeze record (documents, `ann_a/`, `ann_b/`, `manifest.json`), unchanged, plus the lines added at the commit (annotations and the three TSVs). The job checks it before scoring;
- `RUNS.md`: the ledger.

The leakage guard `tests/unit/test_final_exam_leakage.py` checks the detector resources and the unit tests for final-exam-only strings on every CI run.
