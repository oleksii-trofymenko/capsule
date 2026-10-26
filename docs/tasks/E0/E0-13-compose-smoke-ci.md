# E0-13 · Compose smoke test in CI

| Field | Value |
| --- | --- |
| Status | review |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | CI duration (keep the whole run < 8 min) |
| Depends on | E0-07 |
| ADRs | 016, 019 |
| Design spec | none |

## Why

`make up` and the SeaweedFS lockdown are only verified on the home PC. A CI job that builds the image and starts the stack would catch Dockerfile, Compose and SeaweedFS regressions on every PR that touches them.

## Acceptance criteria

- [x] CI job builds the api image and runs the Compose stack with throwaway secrets, waits for `/v1/ready` 200, runs `infra/compose/check-seaweedfs.sh`, then tears down.
- [x] Runs only when `apps/api/**`, `infra/compose/**`, `Makefile` or the workflow change, plus on `main`; included in `ci-ok`.
- [x] Actions and images pinned by SHA/digest; no secrets from the repo.
- [x] Record the added CI time.

## Allowed files

- `.github/workflows/ci.yml`, `infra/compose/**`
- `docs/runbooks/compose-stack.md` (triage notes for the new job; added 2026-10-26 with the owner's approval of the plan)

## Out of scope

- Pushing images (GHCR) — later epic.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner ("ok proceed"), including a restart/persistence step and triage notes in `docs/runbooks/compose-stack.md`.
- Decisions:
  - Filed 2026-10-26 from the E0-07 reviews.
  - New job `stack (compose smoke)` in `ci.yml` runs the real `make up` (env-init, build, `--wait`, `/v1/ready` 200), then `check-seaweedfs.sh` unchanged, then a restart check (Postgres row + Redis key survive `make down`/`make up`; no S3 read after restart until E0-14). Failure dump = `ps --all` + `logs --tail=200` only (never `compose config`/`docker inspect`); teardown `down --volumes` + `rm .env` always.
  - Throwaway secrets: env-init generates them on the runner, every `change-me` key is masked before any later step; no repo secrets, `contents: read`, no new actions or images.
  - Trigger `changes.stack`: `apps/api/**`, `infra/compose/**`, `.env.example`, plus the shared files (workflows, `Makefile`, `contracts/`, `.pre-commit-config.yaml`) — slightly broader than the card's list, accepted (~30 s). Always on `main` pushes and the daily run. Added to `ci-ok.needs`.
  - No Docker layer cache: buildx GHA cache needs a new third-party action (ADR-019); the build takes ~10 s, so not worth it.
- Reviews: code-reviewer changes requested (only blocker: runbook missing from the card's allowed files — fixed here; suggestions `.env.example` trigger, runnable runbook steps, comments → applied). security-engineer approve (low: `.env.example` trigger → applied; notes on masks and log-prefix → comment added).
- Numbers:
  - `stack` job 71–79 s (pull 11–16 s, build 7–10 s, up 4–5 s, SeaweedFS check 1–2 s, restart check 24–32 s, teardown 10–11 s). Runs in parallel.
  - CI wall time 85–95 s on stack-touching PRs (was 57–58 s); docs-only and mobile-only PRs skip the job.
  - Proof runs: green 40409740034, 40410491130, 40411305273; red 40410260803 (re-opened Iceberg port → `stack` and `ci-ok` red). Secret scan of the job logs: 0 generated values.
- Left for later:
  - E0-14: add a signed S3 PUT/GET after the restart once the SeaweedFS health check waits for the volume server.
  - CI service containers in the `integration` job are not hardened (E0-12 leftover).
  - Docker Hub anonymous pull limits on shared runners: re-run; a GHCR mirror is a later-epic option.
