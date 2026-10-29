# E1-34 · Database outage answers 503, not 500

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | Availability (home server): 99% — a database outage must read as "try again", not as an error |
| Depends on | E1-07 |
| ADRs | 014 |
| Design spec | none |

## Why

When Postgres is down, every endpoint that touches it (guest sign-in, refresh, logout, sign-up, sign-in) answers a generic 500, while `/v1/ready` correctly says 503. The app must treat a 503 as retryable and never as a logout (E1-12); a 500 gives it no such signal. Seen in E1-05c and E1-07 QA.

## Acceptance criteria

- [ ] A database connection failure (connection refused, timeout or pool exhausted) maps to the `ServiceBusyError` 503 problem with `Retry-After`, through one handler in `core`. Other database errors stay 500.
- [ ] The log line carries the error type only, never the DSN, row data or SQL parameters (ADR-022).
- [ ] The contract documents 503 on every operation that uses the database.
- [ ] Tests: integration with Postgres stopped (or an unreachable URL) for guest sign-in, refresh and sign-in; the 503 carries `Retry-After`; after Postgres is back the same request succeeds.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/core/**`, `apps/api/modules/auth/**`
- `apps/api/tests/**`

## Out of scope

- Redis outages (sign-in does not need Redis today). Health and readiness (already 503).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-28 from E1-07 QA (also seen in E1-05c QA).
- Numbers:
- Left for later:
