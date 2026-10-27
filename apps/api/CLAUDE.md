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
- Every external call (LLM, search, storage) has a timeout, retry with backoff, and a clear failure path. LLM calls are the exception: retries, fallbacks and per-route timeouts live in gateway config (ADR-010); the `openai` client uses `max_retries=0` and an explicit timeout. POST endpoints that create things accept an idempotency key.
- Errors use one format (RFC 9457 `application/problem+json`). Never leak stack traces.
- Logs are structured JSON with a trace id; no personal data, no prompts with user content at INFO level.
- Config comes from environment variables via one settings object. No hosts, paths or model names in code; model calls use gateway route names only (ADR-010).
- Module boundaries are enforced by Ruff banned-import rules (ADR-005). Every schema change is an Alembic migration (ADR-007).
- Background jobs (SAQ, ADR-006): timeout, bounded retries with backoff, deterministic job key, handler safe to run twice. Every cache and rate-limit key has a TTL; queue keys never do.
- Served by `uvicorn main:create_app --factory --no-access-log` (ADR-021). Test tooling stays in the dev group (ADR-020).

## Migrations

Alembic (ADR-007), sync psycopg 3. `migrations/env.py` reads `DATABASE_URL` through `core/config.py`; the URL never goes into `alembic.ini`. `make up` applies migrations through the one-shot `migrate` Compose service before `api` starts.

To add a migration (from `apps/api`, with `DATABASE_URL` pointing at a local database):

1. `uv run alembic revision -m "<what changes>"`, then write `upgrade()` and `downgrade()` by hand. `target_metadata` is `None` until ORM models exist, so `--autogenerate` has nothing to compare against yet.
2. Remove unused imports and keep the history linear: `tests/unit/test_migrations.py` fails on two heads. If `main` gained a migration meanwhile, rebase and set `down_revision` to the new head.
3. Additive and backward compatible: the old api must still run on the new schema. Indexes on large tables use `op.create_index(..., postgresql_concurrently=True)` inside `with op.get_context().autocommit_block():`.
4. `make test`: the integration suite upgrades its `_test` database to head and runs upgrade → downgrade → upgrade on a fresh one.
5. Never edit a migration that has reached `main`; write a new one.

## Tests

- Unit: domain logic, no network.
- Integration: real Postgres and Redis — CI service containers, the same images through Compose locally, found via `DATABASE_URL` and `REDIS_URL`; mark tests `integration` (ADR-016).
- Contract: responses validated against `contracts/openapi.yaml`.
- Each feature: a happy path, a failure path and an edge case. Mock only at system boundaries.
