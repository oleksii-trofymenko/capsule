# ADR-018: Code quality enforced by pre-commit: Ruff, mypy strict, ESLint, Prettier, tsc, gitleaks, Conventional Commits

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, platform-engineer, project owner
- Related: E0-04, E0-05, E0-06, ADR-001, ADR-005, blueprint §4 "Code quality", §9

## Context

One developer plus agents writes Python (API, agent, evals) and TypeScript (Expo app). Reviews must spend time on logic, not style, and a secret must never reach Git history: once pushed, it has to be rotated and history rewritten. The checks have to run the same way on the Windows dev PC, on a future cloud machine and in CI (E0-05). Budget is €0, so only free, open-source tools. A full run must take under 30 s so nobody skips it.

## Options

1. **pre-commit as the single runner** — one pinned YAML for Python and TypeScript; each hook runs in its own cached environment (Python hooks, gitleaks built from source), so nothing is installed globally except `pre-commit` itself; CI runs the same file. Cons: first install builds environments (about a minute); mobile hooks rely on `apps/mobile/node_modules`.
2. **Husky + lint-staged + commitlint** — standard in JavaScript projects. Lost: needs a root `package.json` and Node just to commit Python, and Python tools would still need their own install and version pinning.
3. **Checks in CI only, no local hooks** — nothing to install. Lost: a secret is already in history before CI sees it, and every style failure costs a CI round-trip.

## Decision

Every commit passes the hooks in `.pre-commit-config.yaml` (trailing whitespace, end of file, gitleaks on staged changes, Ruff lint and format, mypy `strict` on `apps/api`, Prettier, ESLint and `tsc --noEmit` on `apps/mobile`, Conventional Commits with a required scope on the message), installed with `make hooks`; `make lint` runs the same hooks on all files plus gitleaks on unstaged changes and on the full Git history; hook revs are pinned to commit SHAs, and settings live in the root `pyproject.toml` and `apps/mobile/` config files.

## Consequences

- Easier: one command for local checks and CI; tool versions pinned in one file; secrets blocked before the commit exists.
- Harder: `make` on Windows needs `winget install ezwinports.make`; `pre-commit` needs `uv tool install pre-commit --python 3.13`. The mobile `package.json` must list `eslint`, `eslint-config-expo`, `typescript-eslint`, `prettier` and `typescript` as dev dependencies. mypy runs in an isolated environment without project dependencies; when the API skeleton lands (E0-06) it moves to a local hook run through `uv run` so FastAPI and Pydantic types are visible.
- Secret scanning is git-based (staged, unstaged, history), not `gitleaks dir`: the directory scan ignores `.gitignore` and flags every developer's local `.env`. Untracked files are not scanned until they are staged, which is when the commit hook sees them.
- Local hooks can be bypassed (`git commit --no-verify`, edits in the GitHub web UI), so E0-05 runs a full-history gitleaks scan on every PR and push, and GitHub secret scanning with push protection is enabled on the repository (free for public repositories).
- Supply chain: hook revs are commit SHAs with a `# frozen: vX.Y.Z` comment. A bump is its own PR, made at least 7 days after the upstream release, links the release notes and is reviewed by security-engineer.
- We will monitor: full hook run time (baseline in E0-04 notes), gitleaks findings in CI (E0-05).
- Revisit when: a full run exceeds 30 s, or a faster single tool (for example Biome replacing ESLint + Prettier) supports the Expo rules we rely on.
