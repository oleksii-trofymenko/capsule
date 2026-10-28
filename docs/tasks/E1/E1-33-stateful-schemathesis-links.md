# E1-33 · Stateful Schemathesis run with OpenAPI links

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — test tooling; covers success paths the stateless run never reaches |
| Depends on | E1-06 |
| ADRs | 025 |
| Design spec | none |

## Why

The E1-06 run is stateless: it never holds a valid refresh token, so refresh 200, rotation and a logout of a live family are never generated. OpenAPI `links` let Schemathesis chain guest sign-in, refresh and logout (ADR-025, consequences).

## Acceptance criteria

- [ ] `contracts/openapi.yaml` declares `links` from `POST /v1/auth/guest` 201 and `POST /v1/auth/refresh` 200 to refresh and logout, passing the refresh token.
- [ ] A stateful Schemathesis test runs in-process against the E1-06 fakes, deterministic, inside the `unit (api)` job's time budget (ADR-025).
- [ ] No 500s and no schema violations on any generated chain; refresh 200 and logout 204 of a live family both appear in the run.
- [ ] Tests: the stateful suite in CI.

## Allowed files

- `contracts/openapi.yaml`, `apps/api/tests/**`

## Out of scope

- Grace and reuse rules (covered by `tests/integration`). Real databases.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-28 from E1-06.
- Numbers:
- Left for later:
