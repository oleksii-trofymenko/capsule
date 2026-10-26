# Capsule — AI Style Consultant

Capsule is a mobile AI stylist. You describe an event and a budget (even €100) by text, voice or photo. Capsule asks what it needs, reuses clothes you already own, and returns a guide ranked by what matters most in the look. The model chooses the look; plain code guarantees the total never exceeds the budget. It runs on open models on a home GPU server, and moving to a cloud provider is a config change.

## Prerequisites

- Docker with Compose v2
- Node.js LTS and the Expo CLI (`npx expo`)
- Python 3.12 with uv (or pip)
- Git and, optionally, the GitHub CLI (`gh`)

## Quick start

Coming in E0-07: `make up` will start the whole stack from a clean clone.

## Development

Every commit runs the hooks in `.pre-commit-config.yaml` (ADR-018): Ruff, mypy strict, ESLint, Prettier, `tsc`, gitleaks, whitespace fixes and a Conventional Commits check on the message.

Install once per machine (free tools only):

```sh
uv tool install pre-commit --python 3.13
# Windows only, for make:
winget install ezwinports.make --accept-package-agreements --accept-source-agreements
```

Then, in the repository:

```sh
make hooks   # installs the pre-commit and commit-msg hooks
make lint    # runs every hook on all files, same checks as on commit
```

Without `make`, use `pre-commit install` and `pre-commit run --all-files`. The first run builds the hook environments (about a minute); later runs are fast. Commit messages must look like `feat(agent): add budget validator node`. Do not bypass hooks with `--no-verify`.

## How we work

- [`CLAUDE.md`](CLAUDE.md) — rules for everyone working in this repo, people and agents
- [`docs/tasks/README.md`](docs/tasks/README.md) — epics and task cards
- [`docs/adr/README.md`](docs/adr/README.md) — architecture decisions
- [`docs/blueprint.md`](docs/blueprint.md) — product, architecture and roadmap
