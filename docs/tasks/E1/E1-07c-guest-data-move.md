# E1-07c · Move from guest to account

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Sign-up conversion (guests who create an account within 7 days of their first guide) |
| Depends on | E1-07, E1-07b |
| ADRs | 014, 022 |
| Design spec | `docs/design/flows.md` (F6 step 3a, "Guest data") |

## Why

A guest who signs up or signs in must keep what they made as a guest, and the guest principal must then be deleted for good. That is the first deletion, so it writes to the ADR-022 deletion ledger built in E1-07b. Split from E1-07 for size.

## Acceptance criteria

- [ ] Contract first: sign-up and sign-in accept an optional guest credential. The response reports how many guest guides moved, which the app needs for `guest_guides_moved`. It is 0 until E3 adds guides.
- [ ] Moving guest data: when a valid guest credential comes with the request, all guest-owned rows move to the account in one transaction. The same transaction deletes the guest principal and its credential and writes the guest principal id to the deletion ledger (ADR-022). If any step fails, nothing moves and the guest credential still works. A guest credential that is unknown, deleted, past retention or not a guest moves nothing, and the sign-up or sign-in still succeeds with 0 moved. Nothing is ever matched by email, device or analytics id.
- [ ] Deletion ledger: the move writes the guest principal id through the E1-07b writer in the move transaction and appends it after commit. Tests: the ledger row and file line written by the move; the move with a missing ledger directory still succeeds.
- [ ] R3: the move locks the guest credential row, with `lock_timeout` and a 503 as in E1-05c. With two parallel sign-ups or sign-ins using the same credential, one moves the data and the other moves nothing. A guest sign-in racing a move gets 401, never 500.
- [ ] A15: "guest data moved" is logged under the account's principal id with the count, without email, IP or token.
- [ ] Tests: unit and integration (real Postgres); the move failing halfway; a reused guest credential; R3 on two real connections; the ledger cases above; the Schemathesis fake updated.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/errors.py`, `apps/api/main.py`
- `apps/api/tests/**`

## Out of scope

- The ledger itself (E1-07b). The Compose mount for the ledger directory on the backup disk (E1-23). Delete my data (E1-09).

## Analytics events

- none server-side. The app sends `guest_guides_moved` (E1-13).

## Notes (filled while working)

- Plan approved: 2026-10-28 (Orchestrator), from the backend-engineer E1-07 plan, part C.
- Decisions:
  - Filed 2026-10-28: split from E1-07.
  - 2026-10-29: the ledger moved to E1-07b for size. Plan (backend-engineer, PR B) approved: the move runs after the hash or verify, in the final write transaction together with account creation, so a 503 or a failure halfway rolls everything back; lock order guest credential then principal (no deadlock with guest sign-in); `lock_timeout` set only when a credential is sent; guest sign-in gets `FOR SHARE OF c` and no `lock_timeout` (its wait is the short move transaction); a wrong-shaped credential gets 422, an unknown, deleted, expired or non-guest one moves nothing. Sign-up 201 and sign-in 200 return a new `AccountSession` (token pair plus `guest_guides_moved`).
- Numbers:
- Left for later:
