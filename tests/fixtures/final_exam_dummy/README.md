# Final-exam dummy fixture

Invented text only (Story 10.6 PR B, B3.6). Laid out like `tests/test_corpus/final_exam/`, so QA can prove the `final_exam` job of `accuracy.yaml` without spending the one real run (AC8, B8):

- `documents/`: four invented documents, `dummy_01` and `dummy_02` planted, `dummy_03` and `dummy_04` natural (`manifest.json`, `target: dummy`);
- `annotations/`: the adjudicated annotations the job scores;
- `ann_a/`, `ann_b/`: two annotator outputs, with three disagreements in `dummy_01` (one `type`, one `boundary`, one `one-sided`) for the tooling tests;
- `FINGERPRINTS.sha256`: the fixture's own fingerprint record (`documents/`, `ann_a/`, `ann_b/`, `manifest.json`, then `annotations/` appended);
- `RUNS.md`: the dummy ledger. Its first table is the ledger that `ledger-check` reads (statuses `scored`, `infra-failure`, `rerun`). It stays empty, because a dummy run is never scored.
  QA's dummy proof runs (B8) go in the separate table below it, "dummy proof, not the exam". `ledger-check` reads only the first table: it stops at the first line that is not a table row. This is the rule chosen for QA LED-001 (2026-10-10), instead of a `dummy` status, which would mix proof runs into the ledger of scored runs.

Every name in it is invented. Unlike the real set, agents may read this folder. After editing any file here, rewrite `FINGERPRINTS.sha256`:

    python scripts/final_exam_fingerprints.py record --root tests/fixtures/final_exam_dummy --include ann_a ann_b documents manifest.json --out tests/fixtures/final_exam_dummy/FINGERPRINTS.sha256
    python scripts/final_exam_fingerprints.py record --root tests/fixtures/final_exam_dummy --include annotations --out tests/fixtures/final_exam_dummy/FINGERPRINTS.sha256 --append
