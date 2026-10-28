# E1-07c · Deletion ledger and the move from guest to account

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Sign-up conversion (guests who create an account within 7 days of their first guide) |
| Depends on | E1-07 |
| ADRs | 014, 022 |
| Design spec | `docs/design/flows.md` (F6 step 3a, "Guest data") |

## Why

A guest who signs up or signs in must keep what they made as a guest, and the guest principal must then be deleted for good. That is the first deletion, so it needs the ADR-022 deletion ledger. Split from E1-07 for size.

## Acceptance criteria

- [ ] Contract first: sign-up and sign-in accept an optional guest credential. The response reports how many guest guides moved, which the app needs for `guest_guides_moved`. It is 0 until E3 adds guides.
- [ ] Moving guest data: when a valid guest credential comes with the request, all guest-owned rows move to the account in one transaction. The same transaction deletes the guest principal and its credential and writes the guest principal id to the deletion ledger (ADR-022). If any step fails, nothing moves and the guest credential still works. A guest credential that is unknown, deleted, past retention or not a guest moves nothing, and the sign-up or sign-in still succeeds with 0 moved. Nothing is ever matched by email, device or analytics id.
- [ ] Deletion ledger (ADR-022):
  - a table holding only the principal id and the deletion time;
  - one writer in `core/` that inserts the row in the caller's transaction and, after commit, appends the id to the ledger file at the path from config;
  - a missing or unwritable ledger directory never fails the request or stops `api` from starting; the writer logs an error with the principal id only, and the table stays the record;
  - E1-09 reuses the writer;
  - tests: ledger row written by the move, append failure, missing directory at start-up.
- [ ] R3: the move locks the guest credential row, with `lock_timeout` and a 503 as in E1-05c. With two parallel sign-ups or sign-ins using the same credential, one moves the data and the other moves nothing. A guest sign-in racing a move gets 401, never 500.
- [ ] A15: "guest data moved" is logged under the account's principal id with the count, without email, IP or token.
- [ ] Tests: unit and integration (real Postgres); the move failing halfway; a reused guest credential; R3 on two real connections; the ledger cases above; the Schemathesis fake updated.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`
- `.env.example` (ledger directory setting only)
- `apps/api/tests/**`

## Out of scope

- The Compose mount for the ledger directory on the backup disk (E1-23). Delete my data (E1-09).

## Analytics events

- none server-side. The app sends `guest_guides_moved` (E1-13).

## Notes (filled while working)

- Plan approved: 2026-10-28 (Orchestrator), from the backend-engineer E1-07 plan, part C.
- Decisions:
  - Filed 2026-10-28: split from E1-07.
- Numbers:
- Left for later:
