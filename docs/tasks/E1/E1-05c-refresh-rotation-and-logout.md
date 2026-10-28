# E1-05c · Refresh-token rotation and logout

| Field | Value |
| --- | --- |
| Status | done |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | API latency (simple endpoints): p95 < 200 ms, p99 < 500 ms |
| Depends on | E1-05 |
| ADRs | 014, 022 |
| Design spec | none |

## Why

Access tokens live 10 minutes, so the app needs to renew them without asking the person to sign in again, and a stolen refresh token must stop working as soon as it is used twice (ADR-014). Split from E1-05 for size.

## Acceptance criteria

- [x] Contract first: `POST /v1/auth/refresh` and `POST /v1/auth/logout` in `contracts/openapi.yaml`. Every error is RFC 9457. The descriptions state that neither takes an idempotency key, and describe the grace rule.
- [x] Refresh rotates the token on every use, under the family-row `FOR UPDATE` lock, and every success (grace included) updates the family's last-refresh time. A reused refresh token returns 401 and revokes its whole family. Logout revokes the family and always returns 204, including for unknown or revoked tokens.
- [x] The revocation commits before the 401 is sent. A test reads the family row from a separate connection.
- [x] Expired (idle over 30 days, older than 90 days), malformed, unknown and revoked refresh tokens get the same 401 problem document. An unknown token revokes nothing.
- [x] R6 (server side): a retry after a lost refresh response follows the ADR-014 grace rule (single use, 30 s, successor still `current`; the successor becomes `superseded` before the new token is inserted). Tested inside and just outside the window, a second grace attempt, and a superseded successor coming back.
- [x] Two concurrent refreshes with the same token, on two real connections: both get 200, exactly one token is `current` and grace is used. A third concurrent one revokes the family.
- [x] The refresh transaction sets `lock_timeout = '2s'` with `SET LOCAL`. SQLSTATE 55P03 rolls everything back and returns a 503 problem with `Retry-After: 1`; a retry with the same token still works.
- [x] A guest family whose principal's `last_activity_at` is older than the configured guest retention gets the same 401 as an unknown token, with the same predicate as `find_active_guest` (E1-05 security review L3: the 30-day refresh idle limit is independent of `GUEST_RETENTION_DAYS`, so without this a guest past retention could refresh and be revived).
- [x] `last_activity_at` is touched after a 2xx refresh only (ADR-022), with the hourly cap. A failed refresh does not touch it.
- [x] A4: rotated, superseded and new tokens are stored as hashes only. A test reads the table.
- [x] A15: grace used, reuse detected and family revoked (with reason) are logged under the principal id, with no token, hash or IP.
- [x] Logs carry no token or IP at INFO level for refresh and logout.
- [x] Tests: unit, integration (real Postgres) and contract; happy, failure and edge paths. Every new query ships `EXPLAIN ANALYZE` output in the PR. p95 measured on an isolated stack.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/main.py`
- `apps/api/migrations/**` (one additive migration, only if a column E1-05 promised turns out wrong)
- `apps/api/tests/**`

## Out of scope

- Guest credential, tables and the principal dependency (E1-05). Sign-up and sign-in (E1-07). Rate limits (E1-08). Mobile single-flight refresh (E1-12).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator), from the backend-engineer E1-05 plan, part C.
- Decisions:
  - Filed 2026-10-27: split from E1-05 (the split the card allowed).
  - 2026-10-27 (security-engineer): two concurrent refreshes both succeeding is the intended ADR-014 behaviour; a client that keeps the superseded token is logged out on its next refresh, which E1-12's single-flight rule prevents.
  - 2026-10-27 (security-engineer): refresh and logout are exempt from the idempotency-key rule. Replaying a stored refresh response would store a raw token (A4); the grace rule is the recovery path. Logout creates nothing and always returns 204.
  - 2026-10-27 (security-engineer): `lock_timeout` 2 s, 503 with `Retry-After: 1`. Tell E1-12 that a 503 is retryable and must never log the user out.
  - 2026-10-28: no migration; the E1-05 columns were right.
  - 2026-10-28: the grace window is read and written on `statement_timestamp()`, so a lock wait of up to 2 s neither shrinks nor stretches it.
  - 2026-10-28: grace supersedes the family's single `current` token by `family_id` (partial unique index), which is the successor because `decide()` checked it under the lock. Accepted by both reviewers.
  - 2026-10-28 (security L1): logout with a rotated or superseded token still returns 204 and revokes the family, but is logged as `reuse_detected` plus `family_revoked reason=reuse`.
  - 2026-10-28: the access token is signed inside the transaction, so a signing failure rolls back the rotation.
- Numbers (PR #35, isolated stack, 100k principals / 100k families / 300k tokens, one uvicorn process):
  - Refresh at 10 users: p95 56.9 ms, p99 61.3 ms (builder); QA re-measured p95 55.7–57.5 ms, p99 59.1–62.1 ms over 3 runs. Target met.
  - At 1 user: p95 7.1 ms. At 25 users: p95 205 ms, p99 306 ms. At 50 users: p95 552 ms. Throughput flattens at about 270 refreshes/s, limited by the API process's CPU, not Postgres.
  - Refresh costs about 15% more than guest sign-in (8 statements against 3).
  - Every new query is an index lookup, 0.03–0.21 ms in EXPLAIN ANALYZE.
  - Tests: 259 on `main` after merge (205 before); 14 unit, 3 contract and 37 integration added.
  - 503 under a held family lock in 2.01 s; the same token got 200 in 7.5 ms after release.
- Left for later:
  - E1-12: a 503 or a 500 from refresh is retryable and never a logout; never log out while a refresh is in flight (an honest logout with a rotated token inside 30 s is counted as reuse).
  - E1-06: two more input-taking endpoints to cover.
  - E1-08: rate-limit refresh and logout, which are unauthenticated and each open a transaction.
  - E1-10: revoked families stay until its sweep; an index on `refresh_families.revoked_at` may be needed then.
  - Optional hardening, not filed: assert that the grace supersede changed exactly one row; lock before reading `t.state` in logout so a logout racing a refresh is labelled exactly. A Postgres outage answers 500, not 503 (shared error middleware); file a card if that should change.
  - Telemetry for refresh and logout waits for a metrics module; the load script is not committed until `infra/k6` exists.
