# E1-06 · Property-based API tests with Schemathesis

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] New ADR adds Schemathesis as a dev-only dependency (7-day rule, security-engineer review) and supersedes the "Schemathesis lost" reasoning in ADR-020.
- [x] Schemathesis runs in-process against the app with fakes (no real Postgres/Redis), deterministic seed, fast enough for the `unit (api)` job or its own CI job.
- [x] Every operation in `contracts/openapi.yaml` is covered; no 500s and no schema violations.
- [x] Decide whether the ADR-020 contract helper stays (exact checks) or is removed.
- [x] Tests: the property-based suite in CI.

## Allowed files

- `apps/api/**`, `contracts/openapi.yaml` (added 2026-10-28: contract-first fixes), `docs/adr/0xx-*.md`, `docs/adr/README.md`, `.github/workflows/ci.yml` (only if a new job is added)

## Out of scope

- Load testing (k6). Fuzzing against real databases.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-28 (Orchestrator), after a spike.
- Decisions:
  - Filed 2026-10-26 when the owner accepted ADR-020. Card number assumes the E1 roadmap items become E1-01…E1-05; renumber if product-analyst orders E1 differently.
  - 2026-10-28: ADR-025 (proposed; owner accepts). `schemathesis==4.32.0`, dev group only (released 2026-10-18, under the existing `exclude-newer`); 13 dev packages, none in the runtime image. pip-audit clean apart from the existing certifi ignore.
  - 2026-10-28: in-process with a service-level `FakeAuthService` (real `TokenService` and hashing), fake probes and a fake engine. SQL and lock behaviour stay with `tests/integration`. A drift guard compares method names, signatures and async-ness with `AuthService`.
  - 2026-10-28: stateless, all default checks, phases examples + coverage + fuzzing (pinned by a test), `derandomize=True`, no example database, 100 examples per operation. Runs in `unit (api)`; no new CI job.
  - 2026-10-28: the ADR-020 contract helper stays: ~27 uses, 17 against real Postgres/Redis, and exact checks generated cases cannot reach.
  - 2026-10-28: contract fixes found by the spike: the `X-Request-ID` request parameter loses its `pattern` (the server replaces an invalid id); a shared 400 `BadRequest` on the three POSTs, also declared on the routes so the status-code parity check stays exact.
- Numbers (PR #36):
  - Tests: 267 (259 before). Schemathesis module: 7 tests, 601 cases, about 2.9 s; identical case log hash over 5 QA runs. `unit (api)` in CI: 174 passed in 8.8 s.
  - Detection: an injected handler exception fails as ST101, and contract drift on `GuestSession.expires_in` fails as ST108.
- Left for later:
  - E1-33: stateful run with OpenAPI `links` (guest, then refresh, then logout), so refresh 200 and a live logout are generated.
  - The fake never raises `FamilyBusyError`, so 503 is not generated; covered in `tests/integration`.
  - `.github/workflows/ci.yml`: the certifi ignore comment should say "dev-only via httpx and requests"; fix in the next `exclude-newer` bump.
