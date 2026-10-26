# ADR-006: Redis for queue, cache and rate limits; SAQ as the background worker

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, project owner
- Related: E0-03, ADR-005, ADR-009, blueprint §3, §4, §10

## Context

Photo processing, voice transcription (30 s note, p95 < 5 s) and guide generation (p95 < 25 s) must never block HTTP. The API also needs a response cache and rate limiting. The codebase is async end to end (FastAPI, LangGraph, LiteLLM client). The blueprint left the worker open ("arq or Celery"). As of 2026, arq is officially in maintenance-only mode.

## Options

1. **Redis + SAQ** — asyncio-native, Redis-backed, actively maintained; no polling (low pickup latency), job timeouts, retries, heartbeats for abandoned jobs and a small web UI. Cons: smaller community than Celery; fewer ready-made integrations.
2. **Redis + arq** — the blueprint's first idea; simple and async. Lost: maintenance-only, so no new features and an expected migration later.
3. **Redis + Celery** — the most mature Python queue, scheduling and routing built in. Lost: sync-first; running async LangGraph code inside it needs workarounds, and it is heavier than this MVP needs.

## Decision

Use one Redis instance for the job queue, cache and rate limits, and SAQ as the worker for photo, audio and generation jobs, every job with a timeout, bounded retries with backoff and an idempotency key.

## Consequences

- Easier: async code runs unchanged in the worker; one Redis to operate; abandoned jobs are detected.
- Harder: Redis is a single point of failure on the home PC; job payloads must stay small (IDs, not files).
- We will monitor: queue depth, job wait and run time, retries and failures per job type.
- Revisit when: SAQ stops being maintained, we need multi-node routing or scheduled workflows it cannot express, or queue wait time breaks the guide latency target.
