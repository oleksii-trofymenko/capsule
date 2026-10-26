# E0-01 · Repository skeleton and README

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] Folder tree as in `docs/blueprint.md` §5: `apps/mobile`, `apps/api`, `contracts`, `ml`, `infra`, `docs`, `.claude`, `.github`. Empty folders (including `contracts/`) keep a `.gitkeep`.
- [x] The agent harness files from E0-02 are in place, including `docs/blueprint.md`.
- [x] `README.md`: one-paragraph product description, prerequisites (Docker, Node LTS, Python 3.12, uv or pip, Expo CLI), quick start marked "coming in E0-07", links to `CLAUDE.md`, `docs/tasks/README.md`, `docs/adr/README.md`.
- [x] `.gitignore` for Python, Node, Expo, `.env*` (except `.env.example`), OS files.
- [x] `.editorconfig` (UTF-8, LF, 2 spaces for TS/YAML/JSON/MD, 4 for Python).
- [x] `git init` with default branch `main`; first commit `chore: repository skeleton`. *(Landed as `chore: initial repo skeleton`; see Notes.)*
- [x] Private GitHub repository created, added as `origin`, `main` pushed. Branches, PRs and squash-merges (root `CLAUDE.md`, Orchestrator steps 3–6) depend on this; branch protection comes in E0-05. *(Done as a public repo, and protection moved here; see Notes.)*
- [x] GitHub connected to claude.ai so cloud sessions can open the repository.

## Allowed files

- Everything at the repository root; empty folders keep a `.gitkeep`.

## Out of scope

- Any application code, packages or tooling config (later cards).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26, in the Orchestrator session.
- Decisions:
  - Repository is **public**, not private: on a free GitHub account branch rules are enforced only on public repos. The pushed history was scanned for secrets and personal data first; the three local reference files (Blueprint PDF, the Ukrainian "how to work with Claude" PDF, the Chat & Guide HTML) are gitignored.
  - Branch protection moved forward from E0-05: ruleset `main` is active (PR required, 0 approvals, linear history, no force pushes, no deletions, empty bypass list); repo allows squash merge only and deletes head branches on merge. E0-05 still adds required status checks.
  - First commit landed as `chore: initial repo skeleton` instead of `chore: repository skeleton`; `main` cannot be rewritten, accepted as is.
  - `.gitattributes` (`* text=auto eol=lf`, images and PDFs binary) added in PR #1 so scripts and Dockerfiles stay LF on Windows checkouts.
  - GitHub CLI installed on the home PC and logged in, so the Orchestrator can open PRs.
- Numbers: time to first run not measurable yet (no runnable stack until E0-07).
- Left for later: none. GitHub connected to claude.ai on 2026-10-26: Claude GitHub App given access to `capsule` (owner-confirmed). Its pending permission update (Actions/Checks/Webhooks write) was left unaccepted until cloud PR/CI features are needed.
