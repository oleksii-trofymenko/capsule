# apps/api — FastAPI modular monolith

Read the root `CLAUDE.md` first. This file adds backend rules.

## Shape

- `modules/<name>/` — auth, consultations, media, catalog, trends, agent. Each module exposes a service interface; other modules call only that interface, never its tables or internals.
- `core/` — config, database, logging, security, telemetry. No business logic.
- `workers/` — background jobs (photo, audio, generation). HTTP handlers never wait on heavy work.
- `migrations/` — Alembic. `tests/` — unit, integration, contract.

## Rules

- Python 3.13 (ADR-005), full type hints, mypy strict. A `# type: ignore` needs a reason on the same line.
- Pydantic v2 schemas on every request and response. No bare `dict` at the API edge.
- Async all the way: no blocking calls (requests, `time.sleep`, sync DB drivers) in async code.
- Dependencies through `Depends`; no global mutable state. One DB session per request.
- Parameterised queries only. No N+1: eager-load or batch. Every new query ships `EXPLAIN ANALYZE` output in the PR.
- Every external call (LLM, search, storage) has a timeout, retry with backoff, and a clear failure path. POST endpoints that create things accept an idempotency key.
- Errors use one format (RFC 9457 `application/problem+json`). Never leak stack traces.
- Logs are structured JSON with a trace id; no personal data, no prompts with user content at INFO level.
- Config comes from environment variables via one settings object. No hosts, paths or model names in code; model calls use gateway route names only (ADR-010).
- Module boundaries are enforced by Ruff banned-import rules (ADR-005). Every schema change is an Alembic migration (ADR-007).
- Background jobs (SAQ, ADR-006): timeout, bounded retries with backoff, deterministic job key, handler safe to run twice. Every cache and rate-limit key has a TTL; queue keys never do.
- Served by `uvicorn main:create_app --factory --no-access-log` (ADR-021). Test tooling stays in the dev group (ADR-020).

## Tests

- Unit: domain logic, no network.
- Integration: real Postgres and Redis — CI service containers, the same images through Compose locally, found via `DATABASE_URL` and `REDIS_URL`; mark tests `integration` (ADR-016).
- Contract: responses validated against `contracts/openapi.yaml`.
- Each feature: a happy path, a failure path and an edge case. Mock only at system boundaries.
