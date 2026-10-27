# E1-06 · Property-based API tests with Schemathesis

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — test tooling; catches 500s and contract drift on endpoints that take user input |
| Depends on | E1-05 (`POST /v1/auth/guest` is the first endpoint that accepts user input) |
| ADRs | 020 (revisits its "Schemathesis lost" option), new ADR for Schemathesis |
| Design spec | none |

## Why

ADR-020 rejected Schemathesis while the API had only two GET endpoints with no input, and set the trigger to revisit "when endpoints accept user input". Input endpoints such as sign-up and sign-in are where generated requests find crashes, 500s and schema drift that hand-picked tests miss.

## Acceptance criteria

- [ ] New ADR adds Schemathesis as a dev-only dependency (7-day rule, security-engineer review) and supersedes the "Schemathesis lost" reasoning in ADR-020.
- [ ] Schemathesis runs in-process against the app with fakes (no real Postgres/Redis), deterministic seed, fast enough for the `unit (api)` job or its own CI job.
- [ ] Every operation in `contracts/openapi.yaml` is covered; no 500s and no schema violations.
- [ ] Decide whether the ADR-020 contract helper stays (exact checks) or is removed.
- [ ] Tests: the property-based suite in CI.

## Allowed files

- `apps/api/**`, `docs/adr/0xx-*.md`, `docs/adr/README.md`, `.github/workflows/ci.yml` (only if a new job is added)

## Out of scope

- Load testing (k6). Fuzzing against real databases.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-26 when the owner accepted ADR-020. Card number assumes the E1 roadmap items become E1-01…E1-05; renumber if product-analyst orders E1 differently.
- Numbers:
- Left for later:
