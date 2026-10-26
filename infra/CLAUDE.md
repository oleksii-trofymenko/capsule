# infra — Compose, observability, load tests

Read the root `CLAUDE.md` first. This file adds infrastructure rules.

## Shape

- `compose/` — layered files: `compose.base.yml` (api, worker, postgres+pgvector, redis, minio), `compose.local-gpu.yml`, `compose.observability.yml`, `compose.tunnel.yml`, `compose.cloud.yml`.
- `grafana/` — dashboards as code. `k6/` — load scenarios.

## Rules

- Everything configurable through environment variables; `.env.example` lists every variable with a safe dummy value. Real `.env` files never enter Git.
- Pin image versions (no `latest`). Every service has a health check and a restart policy.
- No ports open to the internet. Public access only through Cloudflare Tunnel; admin UIs (Grafana, Langfuse) only behind Cloudflare Access or Tailscale.
- GPU services live only in `compose.local-gpu.yml`, so the cloud profile runs without them.
- A new service or dashboard is documented in the README of its folder: what it is for, how to reach it, which alert watches it.
- Backups: Postgres and MinIO daily; restore tested monthly (runbook in `docs/runbooks/`).
