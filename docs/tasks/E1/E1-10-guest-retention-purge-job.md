# E1-10 · Purge expired guest data (first SAQ worker job)

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Data deletion SLO (added to `docs/metrics.md` by E1-03) |
| Depends on | E1-05, E1-03, E1-09 (reuses its delete handlers) |
| ADRs | 006, retention ADR (E1-03) |
| Design spec | `docs/design/flows.md` (F6 "Guest data") |

## Why

As a guest who stopped using Capsule, I want my data removed from the server after 30 days, so that nothing about me is kept longer than the Privacy notice promises.

## Acceptance criteria

- [ ] A scheduled SAQ job deletes every guest whose `last_activity_at` is older than the configured retention (upper bound 30 days, retention ADR), using the E1-09 delete handlers.
- [ ] The job runs at least once every 24 h. Each run also deletes refresh families that expired or were revoked more than 24 h ago. It never prunes the deletion ledger: E1-23 does, and only up to the oldest backup on disk (ADR-022).
- [ ] Job rules (apps/api CLAUDE.md): a timeout, bounded retries with backoff, a deterministic job key, and safe to run twice. It works in batches so one run never locks the tables for long.
- [ ] Each run exposes a count of guests deleted and of expired guests left over. Left over must be 0 after a successful run; this is what the SLO measures. Until E2 adds metrics export, the counts go into a structured log line.
- [ ] A `worker` service is added to Compose (the same image as `api`, hardened like the other services: non-root, dropped capabilities, `check-privileges.sh` passes). `make up` stays healthy.
- [ ] Tests: unit for the selection rule (exactly at the boundary, one second either side); integration with real Postgres and Redis (expired guests removed, active guests and accounts untouched, a second run is a no-op).

## Allowed files

- `apps/api/workers/**`, `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/pyproject.toml`, `apps/api/uv.lock`
- `apps/api/tests/**`
- `infra/compose/compose.base.yml`, `infra/compose/compose.test.yml`, `infra/compose/README.md`

## Out of scope

- Deleting accounts automatically (owner decision: never). Backup rotation. Grafana panels and alerts (E2).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan. It became M instead of S because no SAQ worker exists yet in Compose.
- Numbers:
- Left for later:
