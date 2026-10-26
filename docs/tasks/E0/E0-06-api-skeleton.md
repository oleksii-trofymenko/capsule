# E0-06 · API skeleton with health checks

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | M |
| Metric | Time to first run |
| Depends on | E0-01 |
| ADRs | 005, 007 (from E0-03; while planned, follow `docs/blueprint.md` §4 as the root `CLAUDE.md` says) |
| Design spec | none |

## Why

Every later backend card needs the same base: settings, logging, error format and health checks that Compose and the uptime monitor can rely on.

## Acceptance criteria

- [ ] `contracts/openapi.yaml` created with `GET /v1/health` (liveness) and `GET /v1/ready` (checks Postgres and Redis), and the problem+json error schema.
- [ ] FastAPI app in `apps/api` with the module layout from `apps/api/CLAUDE.md`; only `core/` is filled in this card.
- [ ] One settings object from environment variables; `.env.example` lists every variable with a dummy value.
- [ ] Structured JSON logs with a request id; no personal data.
- [ ] Errors returned as RFC 9457 problem+json.
- [ ] `/ready` returns 503 with the failing dependency named when Postgres or Redis is down.
- [ ] Tests: unit for settings; integration for `/ready` up and down with Testcontainers; contract test against the OpenAPI file.
- [ ] `make test` passes locally; record the run time.

## Allowed files

- `apps/api/**`, `contracts/openapi.yaml`, `.env.example`, `pyproject.toml`, `Makefile` (test target only)

## Out of scope

- Dockerfile and Compose (E0-07). Auth (E1). Telemetry export (E2).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
