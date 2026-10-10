# Final-exam dummy fixture: run ledger

Dummy proof runs only (Story 10.6 PR B, B8), "dummy proof, not the exam". The dummy target is never scored as the exam, so no row here is ever `scored`: `ledger-check` fails on a `scored` row, which is how B8.3 proves the ledger check.

| Run ID | Commit | Date (UTC) | Target | Status | Approved by | Note |
|---|---|---|---|---|---|---|
| 0 | adad4e9 | 2026-10-10 | dummy | scored | - | B8.3 throw-away: ledger negative proof, reverted |
