# E1-07c · Move from guest to account

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] Contract first: sign-up and sign-in accept an optional guest credential. The response reports how many guest guides moved, which the app needs for `guest_guides_moved`. It is 0 until E3 adds guides.
- [x] Moving guest data: when a valid guest credential comes with the request, all guest-owned rows move to the account in one transaction. The same transaction deletes the guest principal and its credential and writes the guest principal id to the deletion ledger (ADR-022). If any step fails, nothing moves and the guest credential still works. A guest credential that is unknown, deleted, past retention or not a guest moves nothing, and the sign-up or sign-in still succeeds with 0 moved. Nothing is ever matched by email, device or analytics id.
- [x] Deletion ledger: the move writes the guest principal id through the E1-07b writer in the move transaction and appends it after commit. Tests: the ledger row and file line written by the move; the move with a missing ledger directory still succeeds.
- [x] R3: the move locks the guest credential row, with `lock_timeout` and a 503 as in E1-05c. With two parallel sign-ups or sign-ins using the same credential, one moves the data and the other moves nothing. A guest sign-in racing a move gets 401, never 500.
- [x] A15: "guest data moved" is logged under the account's principal id with the count, without email, IP or token.
- [x] Tests: unit and integration (real Postgres); the move failing halfway; a reused guest credential; R3 on two real connections; the ledger cases above; the Schemathesis fake updated.

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
  - 2026-10-29: allowed-file exception: `apps/api/core/logging.py`, one line, so `count` is an allowed log field and `guest_data_moved` carries it as a field.
  - 2026-10-29 (both reviews): `lock_timeout` bounds only the credential lock; right after it, `SET LOCAL lock_timeout TO DEFAULT`. Waits on the email unique index or the rehash behave as in E1-07, so the "guest credential busy" 503 means exactly that. Supersedes the earlier plan note that a same-email wait could give 503.
  - 2026-10-29 (security review): `guest_data_moved` is logged before the ledger file append, so a cancelled append cannot drop the audit event.
  - 2026-10-29: size ~670 changed lines accepted: ~215 code, the rest R3 and failure-path tests the card requires.
- Numbers (PR, head 0076d31):
  - Tests: 409 (391 before); `test_guest_move.py` 10/10 consecutive runs.
  - Query plans (10,000 guests): credential lock and `FOR SHARE` lookup via `guest_credentials_hash_key` then `principals_pkey`, 0.039 / 0.014 ms; guest delete via `principals_pkey` with cascade (`refresh_families_principal_id_idx`, `refresh_tokens_family_id_idx`), 0.342 ms.
  - QA, Linux image, client p50 / p95 / p99 ms: sign-up 102/108/109 (1 user), 134/142/152 (4); with guest 105/108/108, 133/150/155; sign-in 101/105/106, 130/141/144; with guest 105/110/111, 133/149/156. A move adds 3–8 ms. Within p95 < 600 ms, p99 < 1 s.
  - QA R3 over HTTP: 30 rounds of two parallel moves (sign-up/sign-up, sign-in/sign-in, sign-up/sign-in), each moved once, 0 × 500. Guest sign-in racing a move: 600 requests, only 200/401. Held credential lock: 503 in 2.11 s with `Retry-After: 1`, nothing changed, retry moved.
  - QA logs: 56 `guest_data_moved` lines for 56 moves, all under account ids with `count`; no email, token, credential or password anywhere.
- Left for later:
  - The old guest access token's 401 was checked through ASGI only: no route reads an access token yet. Re-check over HTTP when E1-09 or E3 adds one.
  - When a ledger append fails, `guest_data_moved` (account id) and `ledger_append_failed` (guest id) share a `request_id`, which links the two. This is by design: ADR-022 restore step 2 needs the guest id.
  - Guest sign-in has no `lock_timeout`, so it waits as long as the credential row is held. Today only the short move holds that row.
  - On sign-up a 503 costs one full hash, because the hash runs before the lock. This follows the approved plan; rate limiting is E1-08.
  - No k6 scenario exists yet; QA used an async Python harness.
