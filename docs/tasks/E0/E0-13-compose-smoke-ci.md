# E0-13 · Compose smoke test in CI

| Field | Value |
| --- | --- |
| Status | todo |
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

- [ ] CI job builds the api image and runs the Compose stack with throwaway secrets, waits for `/v1/ready` 200, runs `infra/compose/check-seaweedfs.sh`, then tears down.
- [ ] Runs only when `apps/api/**`, `infra/compose/**`, `Makefile` or the workflow change, plus on `main`; included in `ci-ok`.
- [ ] Actions and images pinned by SHA/digest; no secrets from the repo.
- [ ] Record the added CI time.

## Allowed files

- `.github/workflows/ci.yml`, `infra/compose/**`

## Out of scope

- Pushing images (GHCR) — later epic.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-26 from the E0-07 reviews.
- Numbers:
- Left for later:
