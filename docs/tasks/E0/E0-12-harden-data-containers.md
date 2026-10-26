# E0-12 · Harden the data service containers

| Field | Value |
| --- | --- |
| Status | done |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — security hardening of the local stack |
| Depends on | E0-07 |
| ADRs | 008, 019 |
| Design spec | none |

## Why

Security review of E0-07 found that postgres, redis and seaweedfs keep Docker's default capabilities and SeaweedFS runs as root. A compromised data service has more power inside its container than it needs.

## Acceptance criteria

- [x] postgres, redis and seaweedfs run with `cap_drop: [ALL]` plus only the capabilities each entrypoint needs (documented per service).
- [x] SeaweedFS runs as a non-root user if volume ownership allows; otherwise the reason is recorded.
- [x] `make up` -> `/v1/ready` 200 and `check-seaweedfs.sh` pass; data survives `make down`/`make up`.
- [x] Tests: `make test` and CI green.

## Allowed files

- `infra/compose/**`, `docs/runbooks/compose-stack.md`

## Out of scope

- Secrets management (ADR-015). Image version bumps.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner ("go on"); fresh-volume tests only under throwaway project names, never the owner's `capsule` project.
- Decisions:
  - Filed 2026-10-26 from the E0-07 reviews.
  - Every service runs as a fixed non-root uid from the start, so no entrypoint needs privileges: api 10001:10001, postgres 999:999, redis 999:1000, seaweedfs 1000:1000; all `cap_drop: [ALL]`, no `cap_add`, `no-new-privileges`. CapPrm/CapEff/CapBnd = 0 in every container.
  - Postgres and redis `read_only: true` with tmpfs (`/tmp` 64 MB; postgres socket dir 1 MB, uid 999). SeaweedFS keeps a writable root because Compose cannot place `configs.content` (JWT keys) into a read-only service — revisit with ADR-015; its `/tmp` (Unix sockets) is a 64 MB tmpfs. api `/tmp` capped at 64 MB too.
  - No `seaweedfs-init` service (approved plan): the image already owns `/data` as uid 1000. Root-written volumes are fixed by a tested one-off chown in the runbook (`--user 0:0`, CHOWN + DAC_READ_SEARCH only, no network, then `chmod 0700` for PGDATA).
  - Cap-by-cap evidence (started as root): postgres needs DAC_OVERRIDE, SETUID, SETGID on a fresh volume; redis without SETUID/SETGID silently keeps running as root; seaweedfs needs SETUID + SETGID for su-exec. Running as the service uid needs none.
  - New CI guard `infra/compose/check-privileges.sh` (called by `check-pins.sh` in the lint job): every service must have a non-root `user`, `cap_drop` ALL, no `cap_add`, `no-new-privileges`. Proven to fail when a `user:` is removed.
- Reviews: security-engineer approve (6 findings: 3, 4 partial, 5, 6 fixed here; 1 and 2 filed). code-reviewer approve (runbook chown for non-root-owned 0700 dirs → fixed). QA pass (all six checks, incl. the runbook repair on deliberately root-owned volumes).
- Numbers: `up --wait` to `/v1/ready` 200: 5–7 s fresh, 15–22 s with data kept (was 6–7 s / 23–26 s in E0-07). `make test` 59 passed, ~11 s. CI ~58 s.
- Left for later:
  - E0-14: SeaweedFS health check passes before the volume server registers (first S3 read fails for ~15–24 s after restart).
  - E2-01: redact SeaweedFS `CipherKey` log lines before any log shipping (security-engineer: medium; required before E2 ships logs).
  - Owner decision: report the CipherKey logging privately to the SeaweedFS maintainers; image-bump card once fixed upstream.
  - ADR-015: test `WEED_JWT_*` env overrides instead of `security.toml`, which would allow a read-only SeaweedFS root.
  - CI service containers in `ci.yml` are not hardened (throwaway, no data); revisit with E0-13.
