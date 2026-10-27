# E1-05c · Refresh-token rotation and logout

| Field | Value |
| --- | --- |
| Status | todo |
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

- [ ] Contract first: `POST /v1/auth/refresh` and `POST /v1/auth/logout` in `contracts/openapi.yaml`. Every error is RFC 9457. The descriptions state that neither takes an idempotency key, and describe the grace rule.
- [ ] Refresh rotates the token on every use, under the family-row `FOR UPDATE` lock, and every success (grace included) updates the family's last-refresh time. A reused refresh token returns 401 and revokes its whole family. Logout revokes the family and always returns 204, including for unknown or revoked tokens.
- [ ] The revocation commits before the 401 is sent. A test reads the family row from a separate connection.
- [ ] Expired (idle over 30 days, older than 90 days), malformed, unknown and revoked refresh tokens get the same 401 problem document. An unknown token revokes nothing.
- [ ] R6 (server side): a retry after a lost refresh response follows the ADR-014 grace rule (single use, 30 s, successor still `current`; the successor becomes `superseded` before the new token is inserted). Tested inside and just outside the window, a second grace attempt, and a superseded successor coming back.
- [ ] Two concurrent refreshes with the same token, on two real connections: both get 200, exactly one token is `current` and grace is used. A third concurrent one revokes the family.
- [ ] The refresh transaction sets `lock_timeout = '2s'` with `SET LOCAL`. SQLSTATE 55P03 rolls everything back and returns a 503 problem with `Retry-After: 1`; a retry with the same token still works.
- [ ] A guest family whose principal's `last_activity_at` is older than the configured guest retention gets the same 401 as an unknown token, with the same predicate as `find_active_guest` (E1-05 security review L3: the 30-day refresh idle limit is independent of `GUEST_RETENTION_DAYS`, so without this a guest past retention could refresh and be revived).
- [ ] `last_activity_at` is touched after a 2xx refresh only (ADR-022), with the hourly cap. A failed refresh does not touch it.
- [ ] A4: rotated, superseded and new tokens are stored as hashes only. A test reads the table.
- [ ] A15: grace used, reuse detected and family revoked (with reason) are logged under the principal id, with no token, hash or IP.
- [ ] Logs carry no token or IP at INFO level for refresh and logout.
- [ ] Tests: unit, integration (real Postgres) and contract; happy, failure and edge paths. Every new query ships `EXPLAIN ANALYZE` output in the PR. p95 measured on an isolated stack.

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
- Numbers:
- Left for later:
