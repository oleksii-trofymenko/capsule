# E0-04 · Pre-commit and linters

| Field | Value |
| --- | --- |
| Status | todo |
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

- [ ] ADR-018 written and accepted.
- [ ] Pre-commit hooks: Ruff (lint + format), mypy strict on `apps/api`, ESLint + Prettier + `tsc --noEmit` on `apps/mobile`, gitleaks, trailing whitespace and end-of-file fixes, Conventional Commits check on the commit message.
- [ ] Shared config files at the root or per app; strict settings from day one.
- [ ] `make lint` runs the same checks as the hooks.
- [ ] A test commit containing a fake AWS key is blocked (record the output in Notes).
- [ ] Hooks run in under 30 s on a clean repository (record the time).
- [ ] README "Development" section explains how to install the hooks.

## Allowed files

- `.pre-commit-config.yaml`, `Makefile`, `pyproject.toml` (tool sections only), `apps/mobile/` lint and format configs, `docs/adr/018-*.md`, `docs/adr/README.md`, `README.md`

## Out of scope

- CI (E0-05). Application code.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
