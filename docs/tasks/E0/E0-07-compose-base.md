# E0-07 · Base Compose stack and `make up`

| Field | Value |
| --- | --- |
| Status | done |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Time to first run |
| Depends on | E0-06 |
| ADRs | 006, 007, 008, 016, 021 |
| Design spec | none |

## Why

One command brings the backend up the same way on the home PC, on the laptop and later in the cloud.

## Acceptance criteria

- [x] `apps/api/Dockerfile`: multi-stage, non-root user, pinned base image, health check on `/v1/health`.
- [x] `infra/compose/compose.base.yml`: api, postgres with pgvector, redis, seaweedfs (ADR-008; same Postgres/Redis image pins as CI) — pinned versions, health checks, restart policies, named volumes.
- [x] No ports exposed beyond `127.0.0.1`.
- [x] Services read configuration only from environment variables; `.env.example` complete.
- [x] `make up`, `make down`, `make logs` work.
- [x] From a clean clone on the home PC: `make up` → `/v1/ready` returns 200. Record the time; target < 10 min.
- [x] `infra/compose/README.md`: what each service is for and how to reach it.

## Allowed files

- `apps/api/Dockerfile`, `apps/api/.dockerignore`, `infra/compose/**`, `.env.example`, `Makefile`, `README.md` (quick start)

## Out of scope

- GPU services, observability stack, tunnel (later epics). Worker (E3).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner (platform-engineer plan). Allowed files extended to `apps/api/pyproject.toml` + `uv.lock` (uvicorn), `apps/api/core/logging.py` + unit test, deleting `apps/api/scripts/test-services.sh`, `.github/workflows/ci.yml` (pin-sync + `compose config -q` step), ADR-021 + index, `docs/runbooks/compose-stack.md`.
- Decisions:
  - API image: `python:3.13.17-slim-trixie` by digest (adopted early under ADR-019's runtime security exception for the 3.13.16 security fixes; security-engineer approved), uv 0.13.1 build stage, runtime deps only, uid 10001, read-only root, cap_drop ALL, HEALTHCHECK `/v1/health`. 277 MB.
  - uvicorn 0.54.0 without extras (ADR-021), `--no-access-log`; uvicorn loggers routed into our JSON handler.
  - Compose `infra/compose/compose.base.yml`: api, postgres (pgvector 0.8.7-pg16), redis 8.10.2-alpine (AOF, volatile-lru, password), seaweedfs 4.48. Postgres/Redis pins equal CI, enforced by `check-pins.sh` in the CI lint job. Data services on an `internal: true` network; only `127.0.0.1:8000` published. The api health check uses `/v1/health`, never `/ready`. Logs rotate 10 MB x 3.
  - Secrets until ADR-015: `make up` runs `env-init.sh`, which creates the gitignored `.env` with random values (atomic) and refuses `change-me`. `infra/compose/test.env` (committed) holds throwaway credentials for the local `capsule-test` stack only.
  - SeaweedFS lockdown (security review): master/volume/filer bound to loopback; Iceberg/Lance listeners off; the S3 gRPC IAM port 18333 cannot be closed in 4.48 and needed BOTH `jwt.signing` and `jwt.filer_signing` keys (with `jwt.signing` alone, anonymous `PutIdentity` still created admin identities; cf. GHSA-5fx4-c9qp-36jc). Keys come from `.env` via Compose `configs.content`. `-s3.encryptVolumeData` (keys on the same disk). `check-seaweedfs.sh` proves it (pinned grpcurl image, local only).
  - `make test` runs a separate Compose test stack (`capsule-test`, Postgres + Redis only) and removes it on exit, error or Ctrl-C.
- ADR-021 (uvicorn) accepted by the owner on 2026-10-26.
- Reviews: code-reviewer request changes (Makefile continuations collapsed into tabs) -> fixed -> approve. security-engineer request changes (HIGH: unauthenticated S3 gRPC IAM; MEDIUM: Iceberg/Lance listeners) -> fixed -> approve. QA: pass, no bugs.
- Numbers:
  - Clean clone -> `make up` -> `/v1/ready` 200: 34 s cold (empty build cache, Postgres/Redis images re-pulled), 6-7 s warm; 23-26 s after `make down` with data kept (SeaweedFS leader election). Target < 10 min.
  - Image sizes: api 277 MB, pgvector 631 MB, redis 161 MB, seaweedfs 724 MB.
  - `make test`: 59 passed, ~10-12 s. CI: ~1 min 30 s.
  - Exposure: only `127.0.0.1:8000`; the LAN IP and other ports refuse. Postgres data survives `make down`/`make up`; the api restarts in ~1 s after its process exits.
- Left for later:
  - Disk encryption on the home PC is unconfirmed (`BitLockerProtection=0` for C:, Windows 11 Home). It blocks storing user photos (media card) until the owner confirms Device encryption. SeaweedFS encryption alone does not protect a stolen disk.
  - E0-12: harden the postgres/redis/seaweedfs containers (cap_drop, non-root).
  - E0-13: compose smoke test in CI (build, `up --wait`, `/v1/ready`, `check-seaweedfs.sh`).
  - Bumps: Redis 8.10.3 on/after 2026-11-02 (cluster-only fix, does not apply); SeaweedFS 4.50/4.51 under the 7-day rule. Re-run `check-seaweedfs.sh` after every SeaweedFS bump.
  - Untested: JWT key rotation. Secrets visible in `docker inspect` and Redis args until ADR-015. `.env` is world-readable on NTFS (umask has no effect).
  - Tunnel card: keep `/v1/ready` off the tunnel, set `FORWARDED_ALLOW_IPS`. Observability (E2): filter health-check access lines; no dashboards or alerts yet.
