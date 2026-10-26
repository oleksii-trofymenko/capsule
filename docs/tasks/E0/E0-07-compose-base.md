# E0-07 · Base Compose stack and `make up`

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Time to first run |
| Depends on | E0-06 |
| ADRs | 006, 007, 008 (from E0-03) |
| Design spec | none |

## Why

One command brings the backend up the same way on the home PC, on the laptop and later in the cloud.

## Acceptance criteria

- [ ] `apps/api/Dockerfile`: multi-stage, non-root user, pinned base image, health check on `/v1/health`.
- [ ] `infra/compose/compose.base.yml`: api, postgres with pgvector, redis, seaweedfs (ADR-008; same Postgres/Redis image pins as CI) — pinned versions, health checks, restart policies, named volumes.
- [ ] No ports exposed beyond `127.0.0.1`.
- [ ] Services read configuration only from environment variables; `.env.example` complete.
- [ ] `make up`, `make down`, `make logs` work.
- [ ] From a clean clone on the home PC: `make up` → `/v1/ready` returns 200. Record the time; target < 10 min.
- [ ] `infra/compose/README.md`: what each service is for and how to reach it.

## Allowed files

- `apps/api/Dockerfile`, `apps/api/.dockerignore`, `infra/compose/**`, `.env.example`, `Makefile`, `README.md` (quick start)

## Out of scope

- GPU services, observability stack, tunnel (later epics). Worker (E3).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
