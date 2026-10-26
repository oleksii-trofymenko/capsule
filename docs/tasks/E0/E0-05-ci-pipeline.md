# E0-05 · CI pipeline

| Field | Value |
| --- | --- |
| Status | review |
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
- [x] GitHub Actions workflow on pull requests: lint → typecheck → unit tests (API and mobile), with caching of dependencies.
- [x] Jobs run only when their area changed (path filters), plus a full run on `main`.
- [x] Integration test job wired for Postgres and Redis service containers (it may run zero tests until E0-06 adds one).
- [x] gitleaks and dependency audit (pip-audit, npm audit) as jobs; high and critical findings fail the build.
- [ ] Branch protection on `main`: PR required, checks required, squash merge only.
- [x] Record p50 duration over five runs in Notes; target < 8 min.

## Allowed files

- `.github/workflows/**`, `Makefile`, `docs/adr/016-*.md`, `docs/adr/019-*.md`, `docs/adr/README.md`

## Out of scope

- Building and pushing images, EAS builds, eval job (later epics).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner (platform-engineer plan; implementer allowed to push only to the feature branch and open a draft PR).
- Decisions:
  - From E0-01 (2026-10-26): ruleset `main` already requires a PR, linear history and squash merge only. This card only adds the CI jobs as required status checks to that ruleset.
  - One workflow `.github/workflows/ci.yml`: `changes` → `pr-title`, `secrets` (full-history gitleaks), `lint` (`make lint`: lint + typecheck), `unit-api`, `unit-mobile`, `integration` (Postgres 16 + pgvector 0.8.7, Redis 8.10.2), `audit-api`, `audit-mobile` → `ci-ok`. Only `ci-ok` is required; it fails on any failed or cancelled job and checks that its `needs` lists every job.
  - Triggers: `pull_request` (incl. `edited`), push to `main`, daily schedule 04:17 UTC. No `pull_request_target`. Token `contents: read`, no secrets, all actions pinned to SHAs, CI tool resolution capped by `UV_EXCLUDE_NEWER`.
  - Path filter is a plain `git diff` (no third-party action). Shared files (workflows, Makefile, hook config, `contracts/`) run every area; non-PR events run everything.
  - API/mobile jobs switch on `apps/api/pyproject.toml` / `apps/mobile/package.json`; until then they pass with a notice. A missing lockfile then fails loudly.
  - pip-audit fails on any known vulnerability (no severity filter) — owner-approved deviation from "high and critical"; exceptions are per-ID with a reason.
  - CI title regex is intentionally stricter than the local hook (kebab-case scope).
- Reviews: code-reviewer request changes (ADR Decision must be one sentence) → fixed → approve. security-engineer approve (forgeable gate, unpinned tool deps, audit schedule, hygiene → fixed or documented). QA: pass.
- Numbers:
  - p50 over 5 runs (run 40353007333): wall 50 s (48/50/47/54/50), execution 45 s, runner time 80 s; cold first run 55 s. Target < 8 min. Caveat: no real tests yet.
  - Bad PR title → `pr-title` fails and `ci-ok` fails (runs 40350451259, 40354431290); restored title → green (40354641801).
  - `ci-ok` self-check: dropping a job from `needs` → red (40352832283).
  - History scan: 16 commits scanned, no leaks.
- Left for later:
  - Follow-up cards: zizmor + actionlint for workflows (needs ADR); cutoff/hashes for pre-commit's own hook environments; Dependabot/Renovate with a 7-day cooldown (`.github/dependabot.yml`); Grafana panel/alert for CI; `docs/runbooks/` page for a red CI.
  - Bumps due: Node 24.22.1 on/after 2026-10-27; Redis 8.10.3 on/after 2026-11-02 (or earlier via the ADR-019 security-release exception).
  - E0-06: use the `integration` pytest marker, `DATABASE_URL`/`REDIS_URL` (scheme to match the async driver), keep `pyproject.toml` + `uv.lock` in `apps/api`; remove the "0 integration tests" allowance once the first test lands. `apps/api/CLAUDE.md` still says Testcontainers (ADR-016: service containers) — fix with the docs follow-up.
  - E0-07: same Postgres/Redis image pins as CI.
  - After merge: confirm the first scheduled run is green; schedules stop after 60 days without repo activity.
