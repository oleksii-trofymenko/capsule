# ADR-006: Redis for queue, cache and rate limits; SAQ as the background worker

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, project owner
- Related: E0-03, ADR-005, ADR-009, blueprint §3, §4, §10

## Context

Photo processing, voice transcription (30 s note, p95 < 5 s) and guide generation (p95 < 25 s) must never block HTTP. The API also needs a response cache and rate limiting. The codebase is async end to end (FastAPI, LangGraph, the gateway client). The blueprint left the worker open ("arq or Celery"). As of 2026 arq is officially in maintenance-only mode ([PyPI](https://pypi.org/project/arq/)).

## Options

1. **Redis + SAQ** — asyncio-native, Redis-backed, actively maintained; blocks on Redis instead of polling (low pickup latency), job timeouts, retries with backoff, heartbeats for abandoned jobs, cron jobs and a small web UI ([comparison](https://saq-py.readthedocs.io/en/stable/comparison.html)). Cons: smaller community than Celery; fewer ready-made integrations.
2. **Redis + arq** — the blueprint's first idea; simple and async. Lost: maintenance-only, so no new features and an expected migration later.
3. **Redis + Celery** — the most mature Python queue, scheduling and routing built in. Lost: sync-first; running async LangGraph code inside it needs workarounds, and it is heavier than this MVP needs.

## Decision

Use one Redis instance (AOF with `appendfsync everysec`, `maxmemory-policy volatile-lru`) for the job queue, cache and rate limits, and SAQ as the worker for photo, audio and generation jobs; every job has a timeout, bounded retries with backoff, a deterministic job key (e.g. `photo:{media_id}`) and a handler that is safe to run twice.

## Consequences

- Easier: async code runs unchanged in the worker; one Redis to operate; abandoned jobs are detected.
- Harder: every cache and rate-limit key has a TTL and queue keys never do, so only cache keys can be evicted; HTTP POST idempotency keys are a separate API concern, not the job key; Redis is a single point of failure on the home PC; job payloads stay small (IDs, not files).
- We will monitor: queue depth, job wait and run time, retries and failures per job type, Redis memory and evictions.
- Revisit when: job wait p95 exceeds 2 s for 10 minutes at the k6 25-VU load, SAQ has no release for 12 months, or we need multi-node routing it cannot express.
