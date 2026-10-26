# E0-05 · CI pipeline

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | CI duration |
| Depends on | E0-04 |
| ADRs | 016 and 019 (written in this card) |
| Design spec | none |

## Why

Every PR gets the same automatic checks, so "works on my machine" never reaches `main`.

## Acceptance criteria

- [ ] ADR-016 (test strategy) and ADR-019 (CI/CD) written and accepted.
- [ ] GitHub Actions workflow on pull requests: lint → typecheck → unit tests (API and mobile), with caching of dependencies.
- [ ] Jobs run only when their area changed (path filters), plus a full run on `main`.
- [ ] Integration test job wired for Postgres and Redis service containers (it may run zero tests until E0-06 adds one).
- [ ] gitleaks and dependency audit (pip-audit, npm audit) as jobs; high and critical findings fail the build.
- [ ] Branch protection on `main`: PR required, checks required, squash merge only.
- [ ] Record p50 duration over five runs in Notes; target < 8 min.

## Allowed files

- `.github/workflows/**`, `Makefile`, `docs/adr/016-*.md`, `docs/adr/019-*.md`, `docs/adr/README.md`

## Out of scope

- Building and pushing images, EAS builds, eval job (later epics).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - From E0-01 (2026-10-26): ruleset `main` already requires a PR, linear history and squash merge only. This card only adds the CI jobs as required status checks to that ruleset.
- Numbers:
- Left for later:
