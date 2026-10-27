# E1-05 · Auth module: guest credential, tables and current principal

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | API latency (simple endpoints): p95 < 200 ms, p99 < 500 ms |
| Depends on | E1-02, E1-04, E1-05a, E1-05b, E1-05d |
| ADRs | 005, 007, 014, 015, 022, 023 |
| Design spec | `docs/design/flows.md` (F6 "Guest data") |

## Why

As a guest, I want to use Capsule straight away without creating an account, so that I can get my first guide in under 90 seconds and decide later whether to sign up. The server needs a credential that identifies this install without knowing who the person is.

## Acceptance criteria

- [ ] Contract first: `POST /v1/auth/guest` in `contracts/openapi.yaml` (201 with a new credential and the first token pair, 200 for an existing credential), plus the shared `bearerAuth` scheme and 401 response. Every error is RFC 9457. Token responses carry `Cache-Control: no-store`.
- [ ] `modules/auth` with a service interface. One migration (on the E1-05a baseline) adds principals (guest or account) with `last_activity_at` on every principal (ADR-022; used by E1-10), guest credentials (no `revoked_at`: ADR-014 never revokes a credential), refresh families (with created and last-refresh times and `revoked_at`) and refresh tokens (hash, state `current`/`rotated`/`superseded`, first rotation time, grace-used time and successor link), so E1-05c needs no schema change. The guest response already issues the first family and token.
- [ ] Issuing a guest credential stores no personal data: no IP, device id, email or analytics id.
- [ ] A guest credential whose principal's `last_activity_at` is older than the configured guest retention gets the same 401 as an unknown credential (ADR-014); a test compares the two responses. The retention is one setting in `core/config.py`, at most 30 days, default 30 (ADR-022); E1-10 reuses it.
- [ ] Expired, malformed, wrong-key and revoked access tokens get a 401 problem document with `WWW-Authenticate: Bearer`, with no detail that helps an attacker.
- [ ] A reusable dependency gives protected endpoints the current principal (guest or account). `kind` comes from the principal row, never from the token claim; a deleted principal gets 401.
- [ ] `last_activity_at` is touched only after a 2xx response (ADR-022: failed and unauthenticated requests do not count), at most hourly, in its own statement. A failed touch is logged without parameters and never turns a 2xx into an error. Guest sign-in with an existing credential counts.
- [ ] Logs carry no token, credential or IP at INFO level.
- [ ] A4 (`docs/security.md`): the server stores only hashes of guest credentials and refresh tokens, never raw values. A test reads the tables and finds no raw value.
- [ ] R5: token tests include `alg=none`, HS/public-key confusion, unknown `kid` and expired tokens. All of them return the same 401.
- [ ] A15: guest created and guest signed in are logged under the pseudonymous principal id, without IP or credential.
- [ ] Tests:
  - [ ] Unit: token issue and verify, R5.
  - [ ] Integration: real Postgres.
  - [ ] Contract: responses match the spec.
  - [ ] Happy, failure and edge paths, including the retention edge.
- [ ] Every new query ships `EXPLAIN ANALYZE` output in the PR.
- [ ] Tell the Orchestrator: `POST /v1/auth/guest` is the first endpoint that takes user input, which triggers E1-06.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`, `apps/api/pyproject.toml`, `apps/api/uv.lock`
- `apps/api/tests/**`
- `.env.example` and `infra/compose/test.env` (the guest retention variable only)

## Out of scope

- Refresh rotation and logout (E1-05c). Key loading and database-error log sanitising (E1-05d).
- Sign-up, sign-in, moving guest data (E1-07). Rate limits (E1-08). Purge job (E1-10). Mobile (E1-12).
- Alembic setup and Postgres logging (E1-05a). Key generation, layout and CI checks (E1-05b).

## Analytics events

- none. The server sends no analytics events; mobile events are in E1-12 and E1-13.

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator), backend-engineer plan part B, with the security-engineer corrections above.
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
  - 2026-10-27 (backend-engineer plan ~1,450 lines): split three ways. E1-05d (keys, database-error logs, R4 test) first, then this card (guest, tables, principal), then E1-05c (refresh and logout).
  - 2026-10-27 (security-engineer): no `revoked_at` on guest credentials; `last_activity_at` only after a 2xx (the plan's pre-handler touch would break ADR-022). `POST /v1/auth/guest` takes no idempotency key (A4, decision above). The key path is a constant (ADR-015); the retention is a setting (ADR-014, ADR-022: "configured retention").
  - 2026-10-27: added the 32-byte key check (E1-05b review) and the API half of the database-error sanitising (E1-05a review, M1).
  - 2026-10-27: split into E1-05a (Alembic, migration runner, Postgres logging) and E1-05b (key plumbing); this card keeps the auth core. `last_activity_at` lives on `principals`. `POST /v1/auth/guest` is exempt from the idempotency-key rule: replaying a stored response would store the raw credential (A4); a lost response leaves an empty guest the purge removes.
- Numbers:
- Left for later:
  - ADR-005 Ruff banned-import rules for module internals: E1-31.
