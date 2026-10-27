# Architecture Decision Records

One file per decision: `docs/adr/NNN-short-title.md`, from `000-template.md`. Accepted ADRs are never edited; a change is a new ADR that supersedes the old one. Write them with the `adr` skill or `/adr <title>`.

## Index

| ADR | Decision | Status | Lands in |
| --- | --- | --- | --- |
| [001](001-expo-react-native.md) | Expo (React Native) + TypeScript strict + Expo Router for mobile | accepted | E0-03 |
| [002](002-tanstack-query-zustand.md) | TanStack Query for server state, Zustand for local state | accepted | E0-03 |
| [003](003-mobile-secure-storage.md) | Tokens in expo-secure-store (this device only); query cache in MMKV; SQLite deferred | accepted | E0-03 |
| [004](004-sentry-posthog.md) | Sentry for crashes and performance, PostHog for analytics and flags | accepted | E0-03 |
| [005](005-fastapi-modular-monolith.md) | Python 3.13 + FastAPI modular monolith; OpenAPI 3.1 as the contract | accepted | E0-03 |
| [006](006-redis-saq-worker.md) | Redis for queue, cache and rate limits; SAQ worker | accepted | E0-03 |
| [007](007-postgres-pgvector.md) | PostgreSQL + pgvector as the single database, Alembic migrations | accepted | E0-03 |
| [008](008-s3-storage-seaweedfs.md) | S3 API for media; SeaweedFS locally; deletion within 24 h by our own job | accepted | E0-03 |
| [009](009-langgraph-agent.md) | LangGraph for the agent graph | accepted | E0-03 |
| [010](010-litellm-gateway.md) | LiteLLM as the provider-agnostic gateway with routing and fallback | accepted | E0-03 |
| 011 | Ollama first, vLLM after a benchmark | planned | E3 |
| 012 | Model choice and VRAM budget on 16 GB | planned | E3 / E6 |
| 013 | OpenTelemetry → Grafana stack, Langfuse for LLM traces | planned | E2 |
| 014 | Cloudflare Tunnel, JWT with rotating refresh tokens | planned | E1 |
| 015 | Secrets: SOPS / Docker secrets locally, a vault in the cloud | planned | E1 |
| [016](016-test-strategy.md) | Test strategy: pytest against real Postgres and Redis, Jest + RNTL, Maestro, k6 | accepted | E0-05 |
| 017 | Eval runner and LLM-as-judge in CI | planned | E3 |
| [018](018-code-quality-pre-commit.md) | Code quality: Ruff, mypy strict, ESLint, Prettier, pre-commit, Conventional Commits | accepted | E0-04 |
| [019](019-ci-cd-github-actions.md) | CI/CD: GitHub Actions with one required gate check (`ci-ok`); GHCR and EAS for delivery | accepted | E0-05 |
| [020](020-api-test-tooling.md) | API test tooling: httpx, PyYAML and jsonschema as dev-only dependencies | accepted | E0-06 |
| [021](021-asgi-server-uvicorn.md) | uvicorn (no extras) as the ASGI server for the API | accepted | E0-07 |
| [022](022-data-retention-deletion-export.md) | Data retention, deletion and export: fixed upper bounds, own purge jobs, backups expire in ≤ 30 days, deletion ledger replayed on restore | accepted | E1-03 |
