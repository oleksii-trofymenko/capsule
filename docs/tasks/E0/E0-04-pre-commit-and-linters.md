# E0-04 · Pre-commit and linters

| Field | Value |
| --- | --- |
| Status | done |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | Secrets in repository |
| Depends on | E0-01 |
| ADRs | 018 (written in this card) |
| Design spec | none |

## Why

Standards are enforced by tools before a commit exists, so reviews spend time on logic, not style, and no secret ever lands in history.

## Acceptance criteria

- [x] ADR-018 written and accepted.
- [x] Pre-commit hooks: Ruff (lint + format), mypy strict on `apps/api`, ESLint + Prettier + `tsc --noEmit` on `apps/mobile`, gitleaks, trailing whitespace and end-of-file fixes, Conventional Commits check on the commit message.
- [x] Shared config files at the root or per app; strict settings from day one.
- [x] `make lint` runs the same checks as the hooks.
- [x] A test commit containing a fake AWS key is blocked (record the output in Notes).
- [x] Hooks run in under 30 s on a clean repository (record the time).
- [x] README "Development" section explains how to install the hooks.

## Allowed files

- `.pre-commit-config.yaml`, `Makefile`, `pyproject.toml` (tool sections only), `apps/mobile/` lint and format configs, `docs/adr/018-*.md`, `docs/adr/README.md`, `README.md`

## Out of scope

- CI (E0-05). Application code.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner (platform-engineer plan, including installing pre-commit via `uv tool` and GNU Make via winget `ezwinports.make`).
- Decisions:
  - pre-commit is the single runner; every hook rev pinned to a commit SHA with a `# frozen: vX.Y.Z` comment; bumps in their own PR, ≥ 7 days after upstream release, reviewed by security-engineer.
  - `make lint` = `pre-commit run --all-files --hook-stage manual`: all commit hooks plus two manual gitleaks scans (unstaged changes, full Git history). `gitleaks dir .` rejected: it ignores `.gitignore` and would flag local `.env` files.
  - Conventional Commits with `--force-scope`: every message needs a scope (`chore(repo): …`). The first two commits on `main` predate the rule.
  - Mobile hooks are shell-free (`npm --prefix apps/mobile exec --no -- <tool>`) and skip until the mobile skeleton adds `package.json` and `tsconfig.json`.
  - mypy `ignore-without-code` and Ruff `PGH003` force an error code on every `# type: ignore`.
- ADR-018 accepted by the owner on 2026-10-26. GitHub secret scanning and push protection enabled the same day (free for public repos).
- Reviews: code-reviewer approve (after blocker B1 — `make lint` did not scan files for secrets — was fixed); security-engineer approve. QA: pass.
- Numbers:
  - Fake AWS key (generated at runtime) committed → blocked: `RuleID: aws-access-token`, `RuleID: generic-api-key`, "leaks found: 2", no commit created. Unstaged key in a tracked file → `make lint` fails (`aws-access-token`). Key committed with `--no-verify` → history scan fails.
  - Bad message `added stuff` → blocked; `chore: x` → blocked (no scope); `chore(repo): x` → accepted.
  - `make lint` warm median 0.88 s (QA: 944/884/884 ms); `pre-commit run --all-files` 0.68 s; first-ever hook install 52.6 s (includes building gitleaks with Go). Target < 30 s.
- Left for later:
  - Mobile skeleton card: add dev dependencies `eslint`, `eslint-config-expo`, `typescript-eslint`, `prettier`, `typescript`, and `apps/mobile/tsconfig.json` with `"strict": true`; revisit `exclude: ^apps/mobile/[^/]+$` so config-only changes re-run the hooks; anything git-ignored in `apps/mobile` must also go into `.prettierignore`.
  - E0-06: move mypy to a local `uv run mypy` hook so strict mode sees FastAPI/Pydantic types.
  - E0-05: full-history gitleaks on every PR and push; check the PR title format (GitHub squash-merges bypass local hooks).
  - README prerequisites still say Python 3.12 (ADR-005: 3.13); `infra/CLAUDE.md` still names MinIO and media backups (ADR-008). Fix with the blueprint update.
