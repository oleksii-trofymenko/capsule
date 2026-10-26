# Architecture Decision Records

One file per decision: `docs/adr/NNN-short-title.md`, from `000-template.md`. Accepted ADRs are never edited; a change is a new ADR that supersedes the old one. Write them with the `adr` skill or `/adr <title>`.

## Index

| ADR | Decision | Status | Lands in |
| --- | --- | --- | --- |
| 001 | Expo (React Native) + TypeScript strict + Expo Router for mobile | planned | E0-03 |
| 002 | TanStack Query for server state, Zustand for local state | planned | E0-03 |
| 003 | Tokens in Keychain/Keystore (expo-secure-store); SQLite/MMKV for cache | planned | E0-03 |
| 004 | Sentry for crashes and performance, PostHog for analytics and flags | planned | E0-03 |
| 005 | Python + FastAPI modular monolith; OpenAPI 3.1 as the contract | planned | E0-03 |
| 006 | Redis for queue, cache and rate limits; arq or Celery worker | planned | E0-03 |
| 007 | PostgreSQL + pgvector as the single database, Alembic migrations | planned | E0-03 |
| 008 | MinIO (S3-compatible) for media with TTL deletion | planned | E0-03 |
| 009 | LangGraph for the agent graph | planned | E0-03 |
| 010 | LiteLLM as the provider-agnostic gateway with routing and fallback | planned | E0-03 |
| 011 | Ollama first, vLLM after a benchmark | planned | E3 |
| 012 | Model choice and VRAM budget on 16 GB | planned | E3 / E6 |
| 013 | OpenTelemetry → Grafana stack, Langfuse for LLM traces | planned | E2 |
| 014 | Cloudflare Tunnel, JWT with rotating refresh tokens | planned | E1 |
| 015 | Secrets: SOPS / Docker secrets locally, a vault in the cloud | planned | E1 |
| 016 | Test strategy: pytest, Testcontainers, RNTL, Maestro, k6 | planned | E0-05 |
| 017 | Eval runner and LLM-as-judge in CI | planned | E3 |
| 018 | Code quality: Ruff, mypy strict, ESLint, Prettier, pre-commit, Conventional Commits | planned | E0-04 |
| 019 | CI/CD: GitHub Actions, GHCR, EAS Build/Update | planned | E0-05 |
