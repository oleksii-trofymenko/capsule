# ADR-016: Test strategy: pytest against real Postgres and Redis, Jest + RNTL, Maestro, k6

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, platform-engineer, project owner
- Related: E0-05, E0-06, ADR-001, ADR-005, ADR-006, ADR-007, ADR-019, blueprint §4 "Tests", §9, §10

## Context

One developer plus agents ships a FastAPI API with an async worker (ADR-005, ADR-006) on PostgreSQL 16 + pgvector and Redis (ADR-007), and an Expo app (ADR-001). Every PR ships its tests, and CI must stay under 8 min p50 (`docs/metrics.md`). Bugs that matter most live at the edges mocks hide: pgvector queries, JSONB, async drivers, Redis TTLs and job keys. Development is on Windows with Docker Desktop and CI is on Linux, so the test setup has to behave the same on both. Budget is €0.

## Options

1. **pytest (+ Hypothesis) for unit tests; pytest against real Postgres + pgvector and Redis started outside the test process (CI service containers, the Compose stack locally); Jest + React Native Testing Library (`jest-expo`) for the app; Maestro for critical mobile flows; k6 for load** — the same pinned images in CI and locally; tests only read `DATABASE_URL` and `REDIS_URL`. Cons: the database has to be running before tests start; tests must clean up their own data.
2. **Testcontainers (blueprint's first idea)** — each test session starts its own containers from code. Lost: a new dependency, a second definition of every image next to Compose, slower and less predictable container start on Windows Docker Desktop, and the card asks for CI service containers anyway.
3. **Mocks or in-memory SQLite for data access** — fastest and nothing to run. Lost: pgvector, JSONB and async driver behaviour go untested, and ADR-007 allows one database engine only.

For the app, Vitest lost to Jest because the Expo preset (`jest-expo`) is built for Jest.

## Decision

API tests use pytest, and those that need Postgres or Redis are marked `@pytest.mark.integration` and reach real services through `DATABASE_URL` and `REDIS_URL` (CI service containers, Compose locally), while app tests use Jest + RNTL via `jest-expo`.

## Consequences

- Scope: Maestro (mobile E2E) and k6 (load) arrive with their own cards; this ADR only fixes the layers they slot into.
- Easier: one way to reach the database everywhere; integration tests exercise the real SQL, pgvector and Redis; CI runs unit (`-m "not integration"`) and integration (`-m integration`) as separate jobs.
- Harder: each integration test owns its data (transaction rollback or unique keys), because the database is shared across the run. Once a project exists, "no tests collected" fails the unit jobs. The integration job treats it as a warning only until the first integration test lands; the card that adds that test removes the exception. The CI service image tags are pinned in `.github/workflows/ci.yml` and must match the Compose files.
- We will monitor: unit and integration job duration in CI, flaky reruns, CI p50 against the 8-minute target.
- Revisit when: the integration job exceeds 4 minutes, tests need parallel isolated databases, or a service cannot run as a CI service container.
