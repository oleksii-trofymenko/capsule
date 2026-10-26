# ADR-019: CI/CD on GitHub Actions with one required gate check; GHCR and EAS for delivery

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, platform-engineer, project owner
- Related: E0-05, ADR-001, ADR-016, ADR-018, blueprint §4 "CI/CD", §9

## Context

The repository is public on GitHub and the budget is €0. Every PR has to pass the same checks before squash-merge into `main`: PR title, secrets, lint and types, unit and integration tests, and a dependency audit. The target is CI p50 < 8 min. Jobs should run only when their area changed, but a required check that never runs leaves a PR stuck as "Expected — Waiting" ([GitHub docs](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)). The production server is a home PC. Images and app builds come in later epics.

## Options

1. **GitHub Actions on GitHub-hosted runners, with one workflow and one always-running gate job** — standard hosted runners are free for public repositories ([GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), checked 2026-10-26); the code and the ruleset live in one place. Later, images go to GHCR (free for public packages, [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)). The app goes through EAS Build/Update: the Free plan gives 15 Android and 15 iOS builds per month on a low-priority queue and updates for 1,000 MAU ([Expo pricing](https://expo.dev/pricing), checked 2026-10-26). Cons: GitHub becomes a single vendor for code, CI and images.
2. **A self-hosted runner on the home PC** — fast, with access to the GPU. Lost: on a public repository any fork PR could run code on the production machine. GitHub says self-hosted runners "should almost never be used for public repositories" ([secure use](https://docs.github.com/en/actions/reference/security/secure-use)).
3. **GitLab CI or CircleCI with a mirror** — mature pipelines. Lost: capped free minutes, a second platform with its own secrets, and status checks that have to be bridged back to GitHub.

## Decision

One workflow, `.github/workflows/ci.yml`, runs on `pull_request` (never `pull_request_target`), on pushes to `main` and daily, skips API and mobile jobs on PRs that do not touch them, and reports through one always-running `ci-ok` job, which passes only when every job passed or was skipped and is the single required status check.

## Consequences

- Easier: one required check, whatever jobs are added later; area jobs are skipped without blocking merges; free for a public repository.
- Runs: pushes to `main` and the daily schedule run everything, so a new advisory fails the audits without a code change. Concurrency cancels older runs only on PRs; every `main` commit keeps its run. A self-check in `ci-ok` fails if a job is missing from its `needs`. In a public repository GitHub disables scheduled workflows after 60 days without activity and emails failures to whoever last changed the cron line ([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), checked 2026-10-26).
- Security: the workflow token has only `contents: read`; checkout does not keep credentials; no secrets are used; every action is pinned to a commit SHA with a version comment, and the only third-party action is `astral-sh/setup-uv`. Service images are pinned by tag and digest. CI tools installed by uv (pre-commit, pip-audit) are pinned by version, and their transitive dependencies are resolved with `UV_EXCLUDE_NEWER` set to a fixed timestamp at least 7 days old. It is applied to those steps only, because a workflow-wide value makes `uv … --locked` reject the project's `uv.lock`. The timestamp is bumped together with the tool versions. Hook environments that pre-commit builds itself (for example mypy's dependencies) are still resolved by pip without a cutoff.
- Bumps follow ADR-018: own PR, release at least 7 days old, release notes linked, security-engineer review. This ADR adds one refinement. A vendor security release of a runtime image (for example Redis or Postgres) may be adopted at once, pinned by digest, after security-engineer has read its release notes. The 7-day wait still applies to feature releases and to CI-only tools (actions, uv, pre-commit, pip-audit, Node).
- Trust: a green `ci-ok` proves nothing on its own for a PR that changes `.github/`, `.pre-commit-config.yaml`, `Makefile` or a lockfile, because such a PR can change the checks themselves. The owner reviews that diff before merging. Workflows from fork PRs run only after a maintainer approves them ([GitHub docs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks)). A CODEOWNERS-required review is not used: the owner is the only maintainer and cannot approve their own PRs, so it would block every merge.
- Audits: `npm audit --audit-level=high` fails on high and critical findings. pip-audit has no severity filter, so it fails on any known vulnerability, which is stricter than the card asks. An exception is a `--ignore-vuln <ID>` line in the workflow with a reason and a review date, reviewed by security-engineer.
- Harder: a job's check name is part of the contract, so renaming `ci-ok` means updating the ruleset; editing a PR title or body re-runs the whole workflow (`edited` is needed to re-check the title); shared files (workflows, Makefile, hook config, `contracts/`) trigger every area.
- We will monitor: CI p50 and p95 duration (target p50 < 8 min), cache hit rate, audit and gitleaks failures, EAS build quota once mobile builds start.
- Revisit when: p50 exceeds 8 min, the repository becomes private (minutes are no longer free), EAS Free quota runs out two months in a row, or a GPU job is needed in CI.
