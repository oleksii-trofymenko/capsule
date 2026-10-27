# E1-05 · Auth module: guest credential and refresh-token rotation

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | API latency (simple endpoints): p95 < 200 ms, p99 < 500 ms |
| Depends on | E1-02, E1-04 |
| ADRs | 005, 007, 014, 015 |
| Design spec | `docs/design/flows.md` (F6 "Guest data") |

## Why

As a guest, I want to use Capsule straight away without creating an account, so that I can get my first guide in under 90 seconds and decide later whether to sign up. The server needs a credential that identifies this install without knowing who the person is.

## Acceptance criteria

- [ ] Contract first: `contracts/openapi.yaml` gains the guest-credential, token-refresh and logout operations (paths per ADR-014, e.g. `POST /v1/auth/guest`, `POST /v1/auth/refresh`, `POST /v1/auth/logout`). Every error is RFC 9457.
- [ ] `modules/auth` with a service interface. Alembic is initialised (first migration) with tables for principals (guest or account) and refresh-token families, plus `last_activity_at` on guests (used by E1-10).
- [ ] Issuing a guest credential stores no personal data: no IP, device id, email or analytics id.
- [ ] Refresh rotates the token on every use. A reused refresh token returns 401 and revokes its whole family. Logout revokes the family.
- [ ] Expired, malformed, wrong-key and revoked tokens get a 401 problem document, with no detail that helps an attacker.
- [ ] A reusable dependency gives protected endpoints the current principal (guest or account).
- [ ] Signing keys are read from config as ADR-015 requires; `env-init.sh` generates them if missing.
- [ ] Logs carry no token, credential or IP at INFO level.
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
- `infra/compose/env-init.sh`, `infra/compose/test.env` (key variables only)

## Out of scope

- Sign-up, sign-in, moving guest data (E1-07). Rate limits (E1-08). Purge job (E1-10). Mobile (E1-12).
- If Alembic setup and the auth endpoints together go over a day, split Alembic into its own card first.

## Analytics events

- none. The server sends no analytics events; mobile events are in E1-12 and E1-13.

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
- Numbers:
- Left for later:
