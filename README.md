# Capsule — AI Style Consultant

Capsule is a mobile AI stylist. You describe an event and a budget (even €100) by text, voice or photo. Capsule asks what it needs, reuses clothes you already own, and returns a guide ranked by what matters most in the look. The model chooses the look; plain code guarantees the total never exceeds the budget. It runs on open models on a home GPU server, and moving to a cloud provider is a config change.

## Prerequisites

- Docker with Compose v2
- Node.js LTS and the Expo CLI (`npx expo`)
- Python 3.12 with uv (or pip)
- Git and, optionally, the GitHub CLI (`gh`)

## Quick start

Coming in E0-07: `make up` will start the whole stack from a clean clone.

## How we work

- [`CLAUDE.md`](CLAUDE.md) — rules for everyone working in this repo, people and agents
- [`docs/tasks/README.md`](docs/tasks/README.md) — epics and task cards
- [`docs/adr/README.md`](docs/adr/README.md) — architecture decisions
- [`docs/blueprint.md`](docs/blueprint.md) — product, architecture and roadmap
