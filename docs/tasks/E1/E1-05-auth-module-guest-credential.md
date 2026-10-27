# E1-05 · Auth module: guest credential and refresh-token rotation

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | API latency (simple endpoints): p95 < 200 ms, p99 < 500 ms |
| Depends on | E1-02, E1-04, E1-05a, E1-05b |
| ADRs | 005, 007, 014, 015 |
| Design spec | `docs/design/flows.md` (F6 "Guest data") |

## Why

As a guest, I want to use Capsule straight away without creating an account, so that I can get my first guide in under 90 seconds and decide later whether to sign up. The server needs a credential that identifies this install without knowing who the person is.

## Acceptance criteria

- [ ] Contract first: `contracts/openapi.yaml` gains the guest-credential, token-refresh and logout operations (paths per ADR-014, e.g. `POST /v1/auth/guest`, `POST /v1/auth/refresh`, `POST /v1/auth/logout`). Every error is RFC 9457.
- [ ] `modules/auth` with a service interface. One migration (on the E1-05a baseline) adds principals (guest or account) with `last_activity_at` on every principal (ADR-022; used by E1-10), guest credentials, refresh families and refresh tokens with the ADR-014 states.
- [ ] Issuing a guest credential stores no personal data: no IP, device id, email or analytics id.
- [ ] Refresh rotates the token on every use. A reused refresh token returns 401 and revokes its whole family. Logout revokes the family.
- [ ] Expired, malformed, wrong-key and revoked tokens get a 401 problem document, with no detail that helps an attacker.
- [ ] A reusable dependency gives protected endpoints the current principal (guest or account).
- [ ] Signing keys are read from `/run/secrets/jwt_signing_keys` (E1-05b provides the file) as ADR-015 requires; `api` refuses to start with zero or more than two keys, and the error names no value.
- [ ] Each key is at least 32 bytes after hex decoding (at least 64 hex characters, ADR-014; E1-05b writes exactly 64). A shorter or non-hex value stops `api` with an error that names the `kid`, never the value.
- [ ] Logs carry no token, credential or IP at INFO level.
- [ ] ADR-022, API half of E1-05a M1: a database error (for example `IntegrityError`) never reaches the logs with the driver's DETAIL, parameters or row values. The JSON formatter and the exception handler log only the error type, SQLSTATE and constraint name. A test triggers a unique violation and checks the log line.
- [ ] A4 (`docs/security.md`): the server stores only token hashes, never raw tokens. The same applies to guest credentials (§6). A test reads the tables and finds no raw value.
- [ ] R4: the uvicorn access log is off, or replaced by one that logs no client IP and no query string at INFO. A test checks this.
- [ ] R5: token tests include `alg=none`, HS/public-key confusion, unknown `kid` and expired tokens. All of them return the same 401.
- [ ] R6 (server side): a retry after a lost refresh response follows the ADR-014 grace rule. Tested inside and just outside the grace window.
- [ ] A15: security events (sign-in, refresh reuse detected, family revoked) are logged under the pseudonymous principal id, without email, IP or token.
- [ ] Tests:
  - [ ] Unit: token issue and verify, rotation, reuse detection.
  - [ ] Integration: real Postgres.
  - [ ] Contract: responses match the spec.
  - [ ] Happy, failure and edge paths, including two concurrent refreshes with the same token.
- [ ] Every new query ships `EXPLAIN ANALYZE` output in the PR.
- [ ] Tell the Orchestrator: the refresh endpoint is the first one that takes user input, which triggers E1-06.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`, `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/alembic.ini`
- `apps/api/tests/**`
- `infra/compose/test.env` (key variables only), `.env.example` (new API variables only)

## Out of scope

- Sign-up, sign-in, moving guest data (E1-07). Rate limits (E1-08). Purge job (E1-10). Mobile (E1-12).
- Alembic setup and Postgres logging (E1-05a). Key generation, layout and CI checks (E1-05b).
- If the PR goes over ~400 lines, split refresh and logout into E1-05c.

## Analytics events

- none. The server sends no analytics events; mobile events are in E1-12 and E1-13.

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
  - 2026-10-27: added the 32-byte key check (E1-05b review) and the API half of the database-error sanitising (E1-05a review, M1).
  - 2026-10-27: split into E1-05a (Alembic, migration runner, Postgres logging) and E1-05b (key plumbing); this card keeps the auth core. `last_activity_at` lives on `principals`. `POST /v1/auth/guest` is exempt from the idempotency-key rule: replaying a stored response would store the raw credential (A4); a lost response leaves an empty guest the purge removes.
- Numbers:
- Left for later:
