# E0-14 · SeaweedFS health check waits for the volume server

| Field | Value |
| --- | --- |
| Status | review |
| Owner | platform-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — stack reliability (failed reads after restart) |
| Depends on | E0-12 |
| ADRs | 008 |
| Design spec | none |

## Why

The SeaweedFS health check (`/healthz` on 8333) passes before the volume server has registered with the master, so the first S3 read after a restart fails with a 500 ("not found" in the log) for 1–2 s after the S3 API comes up (measured 2026-10-27 on 4.48; the ~15–24 s first reported was counted from container start, and most of it is the S3 gateway starting). Each failed read also logs a chunk CipherKey (see E2-01), so fixing the timing reduces that exposure too.

## Acceptance criteria

- [x] The seaweedfs health check also requires the volume server to be registered (e.g. volume `/healthz` on 8080 or the master's `/dir/status` showing a data node, probed from inside the container).
- [x] Proof: after `make down` / `make up --wait` with existing data, an immediate signed S3 GET returns 200 (repeat 5×); before the change it failed.
- [x] `check-seaweedfs.sh` still passes; cold and warm `make up` times recorded.
- [x] The `stack` CI job restarts the stack with existing data and does an immediate signed S3 GET (regression test for this card).
- [x] Tests: `make test` and CI green.

## Allowed files

- `infra/compose/**`, `docs/runbooks/compose-stack.md`, `.github/workflows/ci.yml` (`stack` job only)

## Out of scope

- SeaweedFS image bumps. Log redaction (E2-01).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator), with notes: whitespace-proof pattern, honest before-proof, loud single-try CI GET.
- Decisions:
  - Filed 2026-10-26 from the E0-12 reviews.
  - 2026-10-27: added the CI read-after-restart criterion and `ci.yml` to allowed files (planned in the E0-13 hand-off).
  - Probe: S3 `/healthz` AND `grep -q '"PublicUrl"'` on the master's `/dir/status` (loopback, busybox `wget`; the image also has `curl`, `nc`, `weed`). `PublicUrl` appears only inside DataNodes entries, so the match does not depend on whitespace. Output is compact unless `?pretty`; with no node it is `"DataCenters":null`. No `Volumes>0` requirement: a fresh node reports `Volumes:0`.
  - Rejected volume `/healthz` on 8080: it passed at ~3 s, 13–19 s before registration (polled every 0.8 s, throwaway project).
  - Timeline (polled every 0.8 s, seaweedfs alone): S3 `/healthz` ok at 22.1 s / 15.9 s; GET 500 for 1 and 2 polls with no DataNode; GET 200 on the same poll the DataNode appeared (22.9 s / 17.8 s).
  - CI: the existing restart step also PUTs an object before `make down` and does one signed GET (no retry) after `make up`, from a throwaway container using the seaweedfs image (like `check-seaweedfs.sh`). Failure prints `::error::` with code and body on one line. Run locally against main's check: caught the 500 on try 5 of 5 (tries 1–4 passed).
- Numbers (local: Ryzen 9700X, Docker Desktop 29.8.2):
  - Immediate signed GET after `make down` / `make up`, before (main's check): batch 1: 1/5 failed (500), batch 2: 2/5 failed. With seaweedfs `cpus: 1` (override file, same compose up as `make up`): 2/5 failed. Every 500 came with 9 "not found" log lines.
  - After: 0/5 failed plain, 0/5 failed with `cpus: 1`; no "not found" lines.
  - `make up` cold, clean clone, images and build cache present: 6.2 s (fresh volumes, before/after alike: 6.0–7.0 s). Not measured with an empty image cache.
  - `make up` warm (existing data): before 14.1–22.1 s, after 13.9–24.1 s. No measurable change; values cluster at ~14/19/24 s, a 5 s step.
  - CI `stack` job: before 69 s / 71 s (main runs 40484047910, 40412605083), after 77 s (run 40493413324); restart step 27–30 s → 35 s. Whole workflow 87–91 s → 98 s.
  - `check-seaweedfs.sh` all ok; `make lint` ok; `make test` 59 passed.
- Left for later:
  - The CI step catches a regression only when the race happens (~20–30% of restarts locally); it never fails falsely with the fix.
  - No dashboard or alert for seaweedfs health yet (observability epic, E2).
  - Recheck the `/dir/status` shape on the next SeaweedFS bump (comment in `compose.base.yml`).
