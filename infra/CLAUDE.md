# infra — Compose, observability, load tests

Read the root `CLAUDE.md` first. This file adds infrastructure rules.

## Shape

- `compose/` — layered files: `compose.base.yml` (api, worker, postgres+pgvector, redis, seaweedfs), `compose.local-gpu.yml`, `compose.observability.yml`, `compose.tunnel.yml`, `compose.cloud.yml`; `compose.test.yml` is the local `make test` stack.
- `grafana/` — dashboards as code. `k6/` — load scenarios.

## Rules

- Everything configurable through environment variables; `.env.example` lists every variable with a safe dummy value. Real `.env` files never enter Git.
- Pin images by tag and digest (no `latest`); bumps follow the 7-day rule, with the runtime security-release exception (ADR-019). Every service has a health check and a restart policy.
- No ports open to the internet. Public access only through Cloudflare Tunnel; admin UIs (Grafana, Langfuse) only behind Cloudflare Access or Tailscale.
- GPU services live only in `compose.local-gpu.yml`, so the cloud profile runs without them.
- A new service or dashboard is documented in the README of its folder: what it is for, how to reach it, which alert watches it.
- Backups: Postgres daily; restore tested monthly (runbook in `docs/runbooks/`). Media are never backed up: they are deleted within 24 h (ADR-008).
