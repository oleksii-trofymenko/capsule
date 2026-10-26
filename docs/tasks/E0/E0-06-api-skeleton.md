# E0-06 · API skeleton with health checks

| Field | Value |
| --- | --- |
| Status | review |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | M |
| Metric | Time to first run |
| Depends on | E0-01 |
| ADRs | 005, 007, 016 |
| Design spec | none |

## Why

Every later backend card needs the same base: settings, logging, error format and health checks that Compose and the uptime monitor can rely on.

## Acceptance criteria

- [x] `contracts/openapi.yaml` created with `GET /v1/health` (liveness) and `GET /v1/ready` (checks Postgres and Redis), and the problem+json error schema.
- [x] FastAPI app in `apps/api` with the module layout from `apps/api/CLAUDE.md`; only `core/` is filled in this card.
- [x] One settings object from environment variables; `.env.example` lists every variable with a dummy value.
- [x] Structured JSON logs with a request id; no personal data.
- [x] Errors returned as RFC 9457 problem+json.
- [x] `/ready` returns 503 with the failing dependency named when Postgres or Redis is down.
- [x] Tests: unit for settings; integration for `/ready` up and down against real Postgres and Redis (CI service containers, `integration` marker, ADR-016); contract test against the OpenAPI file.
- [x] `make test` passes locally; record the run time.

## Allowed files

- `apps/api/**`, `contracts/openapi.yaml`, `.env.example`, `pyproject.toml`, `Makefile` (test target only)

## Out of scope

- Dockerfile and Compose (E0-07). Auth (E1). Telemetry export (E2).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner (backend-engineer plan; allowed files extended to `ci.yml` (exit-5 allowance removed; certifi ignore), `.pre-commit-config.yaml` (mypy as local `uv run` hook), `.gitignore` (one negation), ADR-020 + index).
- Decisions:
  - Dependencies: runtime fastapi 0.146.0, pydantic 2.14.1, sqlalchemy 2.1.5, psycopg[binary] 3.3.6 (one driver with LangGraph's checkpointer), redis 8.1.0; dev pytest, hypothesis, mypy, plus httpx, pyyaml, jsonschema (+ stubs) under ADR-020. Resolved with `exclude-newer = 2026-10-19`. Avoided: pydantic-settings, structlog, pytest-asyncio, alembic (first migration card), uvicorn (E0-07).
  - Python 3.13 via `apps/api/.python-version`; psycopg async needs a selector event loop on Windows (tests use anyio `loop_factory`).
  - `/v1/ready`: per-dependency single-flight probe, budget `READY_PROBE_TIMEOUT_S` (1.0 s); an overrunning probe is cancelled once and not awaited (driver cleanup runs in the background, tracked); while it cleans up, the dependency reports failing at once. Consequence (in the contract): a dependency may stay "failing" up to ~10 s after recovering from a hang. Client timeouts are separate and longer (`DATABASE_CONNECT_TIMEOUT_S`, `REDIS_SOCKET_TIMEOUT_S`, 5 s).
  - Errors: RFC 9457 for 404/405/422/500/503; 422 strips `input`/`ctx`; 5xx hide detail; OpenAPI/docs URLs disabled. Logs: JSON with request id, allow-listed extras; third-party loggers at WARNING; DB engine `hide_parameters=True`.
  - `make test` uses only `CAPSULE_TEST_*` URLs or throwaway containers (same pinned images as CI on 127.0.0.1:55432/56379); the integration fixture refuses DB names not ending in `_test`.
  - CI: certifi PYSEC-2026-4320 ignored in pip-audit as a false positive (security-engineer, review by 2026-11-09; remove at the next `exclude-newer` bump ≥ 2026-10-27).
  - `.gitignore`: `!/apps/api/modules/media/` after the unanchored `media/` (user-media protection elsewhere kept).
  - PR size ~1,830 lines excl. `uv.lock` (≈ tests 50 %, contract 12 %); code-reviewer advised against splitting.
- Reviews: security-engineer approve (on green audit). code-reviewer approve → QA fail (B1: `/ready` 11 s when Postgres hangs on a pooled connection; B2: httpx logged full URLs) → fixed; code-reviewer found two concurrency defects in the fix (unshared probes per request; double cancel interrupting cleanup) → fixed → approve. QA re-test: pass.
- Numbers:
  - `/ready` with Postgres paused on a pooled connection: 11,033 ms → 1,011 ms; worst 503 across all QA cases 1,036 ms (limit 1,250 ms). 10 concurrent calls with Postgres paused → 1 probe task, 1 connection; 0 / 0 after cleanup.
  - In-process latency (500 requests, before the probe rework): `/v1/health` p95 0.33 ms, `/v1/ready` p95 3.63 ms.
  - Tests: 57 (unit 39, contract 9, integration 9). CI run e2b780c: unit-api 13 s, integration 31 s, whole run ~59 s.
  - `make test` warm median 9.45 s (pytest ~6.2 s); cold ~22 s with image pull.
- Left for later:
  - Remove the certifi ignore at the next `exclude-newer` bump (≥ 2026-10-27; review by 2026-11-09).
  - E0-07: uvicorn with `--no-access-log` and uvicorn loggers routed to the JSON handler; don't route `/v1/ready` through the tunnel (or rate-limit it); Compose healthcheck/uptime intervals must tolerate "failing up to ~10 s after recovery"; Compose replaces `test-services.sh` (image pins currently in two places); Windows uvicorn needs a selector loop.
  - First DB-writing card: move the `_test` DB guard into an autouse session fixture and guard Redis too; review `exc` text in logs for personal data; log route templates instead of raw paths (C4).
  - First Alembic card adds alembic.
