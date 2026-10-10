# Final-exam dummy fixture: run ledger

Dummy proof runs only (Story 10.6 PR B, B8), "dummy proof, not the exam". The dummy target is never scored as the exam, so no row here is ever `scored`: `ledger-check` fails on a `scored` row, which is how B8.3 proves the ledger check.

| Run ID | Commit | Date (UTC) | Target | Status | Approved by | Note |
|---|---|---|---|---|---|---|

## QA dummy proof runs (B8): dummy proof, not the exam

The ledger table above takes only `scored`, `infra-failure` or `rerun`, and none of these describes a dummy proof run, so QA records the B8 runs in this separate table. `ledger-check` reads the table above only.

| Run ID | Commit | Date (UTC) | Inputs | Result | Stopped at | Note |
|---|---|---|---|---|---|---|
| 38042167180 | adad4e9 | 2026-10-10 | `final_exam=dummy` | success | - | B8.1, B8.2: dummy proof |
| 38042178272 | adad4e9 | 2026-10-10 | `final_exam=dummy`, `force_failure=true` | failure, intended | pytest step, `RuntimeError: forced failure` | B8.5: forced failure |
| 38042214591 | adad4e9 | 2026-10-10 | `final_exam=foo` | failure, intended | Check inputs | B8.3: bad input |
| 38042353260 | 8bdc439 | 2026-10-10 | `final_exam=dummy` | failure, intended | Ledger check | B8.3: throw-away `scored` row, reverted in 3f8674b |
| 38042399414 | be2b926 | 2026-10-10 | `final_exam=dummy` | failure, intended | Fingerprint check | B8.3: throw-away edit of `dummy_04.txt`, reverted in e38193c |
