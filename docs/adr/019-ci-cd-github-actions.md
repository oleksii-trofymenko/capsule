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

`.github/workflows/ci.yml` runs on `pull_request` and on pushes to `main`, never on `pull_request_target`. A `changes` job turns `git diff` into area flags so API and mobile jobs can be skipped (on `main` everything runs). The aggregate `ci-ok` job (`if: always()`) passes only when every job passed or was skipped, and it is the only required status check.

## Consequences

- Easier: one required check, whatever jobs are added later; area jobs are skipped without blocking merges; free for a public repository.
- Security: the workflow token has only `contents: read`; checkout does not keep credentials; no secrets are used; every action is pinned to a commit SHA with a version comment, and the third-party code is `astral-sh/setup-uv` alone. Bumps follow ADR-018 (own PR, release at least 7 days old, release notes, security-engineer review). Service images are pinned by tag and digest.
- Audits: `npm audit --audit-level=high` fails on high and critical findings. pip-audit has no severity filter, so it fails on any known vulnerability, which is stricter than the card asks. An exception is a `--ignore-vuln <ID>` line in the workflow with a reason and a review date, reviewed by security-engineer.
- Harder: a job's check name is part of the contract, so renaming `ci-ok` means updating the ruleset; editing a PR title or body re-runs the whole workflow (`edited` is needed to re-check the title); shared files (workflows, Makefile, hook config, `contracts/`) trigger every area.
- We will monitor: CI p50 and p95 duration (target p50 < 8 min), cache hit rate, audit and gitleaks failures, EAS build quota once mobile builds start.
- Revisit when: p50 exceeds 8 min, the repository becomes private (minutes are no longer free), EAS Free quota runs out two months in a row, or a GPU job is needed in CI.
