# E0-01 · Repository skeleton and README

| Field | Value |
| --- | --- |
| Status | in progress |
| Owner | You (Product Owner) |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | Time to first run (engineering SLO) |
| Depends on | none |
| ADRs | none |
| Design spec | none |

## Why

Agents need a fixed map of the repository so every card can name its allowed files.

## Acceptance criteria

- [ ] Folder tree as in `docs/blueprint.md` §5: `apps/mobile`, `apps/api`, `contracts`, `ml`, `infra`, `docs`, `.claude`, `.github`. Empty folders (including `contracts/`) keep a `.gitkeep`.
- [ ] The agent harness files from E0-02 are in place, including `docs/blueprint.md`.
- [ ] `README.md`: one-paragraph product description, prerequisites (Docker, Node LTS, Python 3.12, uv or pip, Expo CLI), quick start marked "coming in E0-07", links to `CLAUDE.md`, `docs/tasks/README.md`, `docs/adr/README.md`.
- [ ] `.gitignore` for Python, Node, Expo, `.env*` (except `.env.example`), OS files.
- [ ] `.editorconfig` (UTF-8, LF, 2 spaces for TS/YAML/JSON/MD, 4 for Python).
- [ ] `git init` with default branch `main`; first commit `chore: repository skeleton`.
- [ ] Private GitHub repository created, added as `origin`, `main` pushed. Branches, PRs and squash-merges (root `CLAUDE.md`, Orchestrator steps 3–6) depend on this; branch protection comes in E0-05.
- [ ] GitHub connected to claude.ai so cloud sessions can open the repository.

## Allowed files

- Everything at the repository root; empty folders keep a `.gitkeep`.

## Out of scope

- Any application code, packages or tooling config (later cards).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
