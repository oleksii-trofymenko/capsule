# E0-14 · SeaweedFS health check waits for the volume server

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — stack reliability (failed reads after restart) |
| Depends on | E0-12 |
| ADRs | 008 |
| Design spec | none |

## Why

The SeaweedFS health check (`/healthz` on 8333) passes before the volume server has registered with the master, so the first S3 read after a restart fails with "volume not found" for ~15–24 s. Each failed read also logs a chunk CipherKey (see E2-01), so fixing the timing reduces that exposure too.

## Acceptance criteria

- [ ] The seaweedfs health check also requires the volume server to be registered (e.g. volume `/healthz` on 8080 or the master's `/dir/status` showing a data node, probed from inside the container).
- [ ] Proof: after `make down` / `make up --wait` with existing data, an immediate signed S3 GET returns 200 (repeat 5×); before the change it failed.
- [ ] `check-seaweedfs.sh` still passes; cold and warm `make up` times recorded.
- [ ] Tests: `make test` and CI green.

## Allowed files

- `infra/compose/**`, `docs/runbooks/compose-stack.md`

## Out of scope

- SeaweedFS image bumps. Log redaction (E2-01).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-26 from the E0-12 reviews.
- Numbers:
- Left for later:
