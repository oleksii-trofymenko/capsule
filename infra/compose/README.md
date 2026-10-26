# Compose stack

`compose.base.yml` runs the backend the same way on the home PC, a laptop and, later, the cloud. Start it with `make up` from the repository root (see the root README). Later layers (`compose.local-gpu.yml`, `compose.observability.yml`, `compose.tunnel.yml`, `compose.cloud.yml`) come with their own cards.

| Service | What it is for | How to reach it | Data | Alert |
| --- | --- | --- | --- | --- |
| `api` | FastAPI app (`apps/api`), served by uvicorn (ADR-021) | `http://127.0.0.1:${API_HOST_PORT:-8000}` from the host: `/v1/health` (liveness), `/v1/ready` (Postgres + Redis) | none | none yet (observability epic, E2) |
| `postgres` | PostgreSQL 16 + pgvector, the only database (ADR-007) | inside the stack as `postgres:5432`; from the host: `docker compose -p capsule exec postgres psql -U capsule capsule` | volume `capsule_pg_data` | none yet (E2) |
| `redis` | Queue, cache, rate limits (ADR-006); AOF, `volatile-lru`, password | inside the stack as `redis:6379`; from the host: `docker compose -p capsule exec redis redis-cli` (`REDISCLI_AUTH` is set) | volume `capsule_redis_data` | none yet (E2) |
| `seaweedfs` | S3 API for media (ADR-008), single node | inside the stack as `http://seaweedfs:8333`, signed requests only; S3 gRPC `seaweedfs:18333` (IAM calls need a JWT) | volume `capsule_seaweed_data`, never backed up | none yet (E2) |

The worker (E3), GPU services, observability and the tunnel are out of scope here.

## Ports and networks

- Only `api` publishes a port, and only on `127.0.0.1`. Nothing is reachable from the LAN or the internet.
- `postgres`, `redis` and `seaweedfs` sit only on `backend`, an `internal` network with no route to the host or the internet. `api` is on `backend` and `edge`.
- SeaweedFS binds its master, volume and filer (HTTP and gRPC) to the container's loopback, because their APIs have no auth. The Iceberg and Lance catalog listeners are switched off. On `backend` exactly two ports listen:
  - `8333`: S3 API, signed requests only (the identity from `.env`);
  - `18333`: S3 gRPC. It cannot be closed in 4.48, and its IAM service (`PutIdentity`, `PutPolicy`, ...) would let any container create an admin identity (GHSA-5fx4-c9qp-36jc). `security.toml` sets `[jwt.filer_signing]` and `[jwt.signing]` keys from `.env`, so those calls need a valid JWT. Tested on 4.48: `jwt.filer_signing` is the key that closes it; `jwt.signing` alone does not.
- `bash infra/compose/check-seaweedfs.sh` (after `make up`) proves all of this from a neighbouring container: listeners, IAM gRPC without or with a forged token (must be `Unauthenticated`), unsigned and wrong-secret S3 (403), signed S3 (200). It uses a pinned `fullstorydev/grpcurl` image for the gRPC call only. Run it after every SeaweedFS bump.
- When the tunnel arrives: route only the public API paths through it. `/v1/ready` must not be public: every call probes Postgres and Redis.

## Health checks and restarts

- Every service has a health check (start period 30 s, checked every 1 s during it, then every 10 s, 3 retries) and `restart: unless-stopped`. Restarts after a reboot need Docker Desktop to start at login (Settings → General).
- The API's health check is `/v1/health`, defined in `apps/api/Dockerfile`. It is never `/v1/ready`: after a dependency recovers from a hang, `/v1/ready` may keep failing for up to about 10 s (E0-06), and readiness must not restart the API.
- `make up` waits for every health check, then for `/v1/ready` to return 200 (up to 60 s).

## Configuration and secrets

- Compose reads the repository-root `.env` (`--env-file .env`). It is gitignored. On first run `make up` creates it from `.env.example` and replaces every `change-me` with 48 random hex characters, which are safe inside URLs. Compose refuses to start if a required value is missing.
- The API gets only environment variables. Compose builds `DATABASE_URL` and `REDIS_URL` from the credentials and service names.
- This is temporary until ADR-015 (SOPS / Docker secrets): the secrets are visible to `docker inspect` on the host.
- `test.env` holds test-only credentials for the throwaway `capsule-test` project that `make test` starts (`compose.test.yml` publishes Postgres on `127.0.0.1:55432` and Redis on `127.0.0.1:56379`). It is removed with its volumes when the tests end. CI uses its own service containers.

## Image pins

- Every image is pinned by tag and digest. Each release was at least 7 days old when pinned (ADR-018, ADR-019). The one exception is the API's base image, python 3.13.17 (2026-10-24), adopted early as a runtime security release under ADR-019 after security-engineer review.
- The Postgres and Redis pins must equal the CI service containers (ADR-016). The uv image in `apps/api/Dockerfile` must equal `UV_VERSION` in CI. `check-pins.sh` checks both in the CI lint job; run it by hand with `bash infra/compose/check-pins.sh`.
- Change all of these in the same PR.

## Container privileges (E0-12)

Every service runs as a fixed non-root user, with `cap_drop: [ALL]`, no added capability and `no-new-privileges`:

| Service | `user` | Root filesystem |
| --- | --- | --- |
| `api` | `10001:10001` | read-only, tmpfs `/tmp` (64 MB) |
| `postgres` | `999:999` (image's `postgres`) | read-only, tmpfs `/tmp` (64 MB) and `/var/run/postgresql` (1 MB) |
| `redis` | `999:1000` (image's `redis`) | read-only, tmpfs `/tmp` (64 MB) |
| `seaweedfs` | `1000:1000` (image's `seaweed`) | writable, because Compose cannot place `configs.content` in a read-only container; tmpfs `/tmp` (64 MB, Unix sockets) |

`check-privileges.sh` (run by `check-pins.sh` in the CI lint job) fails if any service has no non-root `user`, lacks `cap_drop: [ALL]`, has a `cap_add`, or lacks `no-new-privileges:true`. The uids belong to the pinned images. After an image bump, check them with `docker run --rm --entrypoint id <image> <user>` and the runbook's privilege check.

## Media encryption at rest (ADR-008)

- SeaweedFS runs with `-s3.encryptVolumeData`: every uploaded chunk is encrypted with its own key. The keys are stored in the filer metadata on the same disk, so this alone does not protect against a stolen disk.
- That protection must come from full-disk encryption of the drive holding Docker Desktop's data (`%LOCALAPPDATA%\Docker\wsl`). Check it in Settings → Privacy & security → Device encryption (Windows Home) or with `manage-bde -status` as administrator (Pro).
- The media card must not store user photos until disk encryption is confirmed on the home PC.
- Buckets, lifecycle rules and the 24-hour deletion job come with the media card.

## Backups

- Postgres (`capsule_pg_data`) will be backed up daily, with a monthly restore test, by its own card (runbook in `docs/runbooks/`).
- Redis holds only queue, cache and rate-limit state.
- Media (`capsule_seaweed_data`) are never backed up (ADR-008). The volume carries the label `capsule.backup=never`.

## Runbook

[`docs/runbooks/compose-stack.md`](../../docs/runbooks/compose-stack.md): stack not healthy, `.env` problems, pin drift, SeaweedFS exposure check, permission errors on data volumes, resetting volumes, the CI `stack` job (E0-13), which runs `make up`, `check-seaweedfs.sh` and a restart on every PR that touches the stack.
