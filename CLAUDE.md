# Capsule — AI Style Consultant

Capsule is a mobile AI stylist. A user describes an event and a budget (even €100) by text, voice or photo. Capsule asks what it needs, reuses clothes the user already owns, and returns a guide ranked by what matters most. The model chooses the look; plain code guarantees the total never exceeds the budget.

- Audience: men and women aged 20–60 in Europe. App copy is English (en-GB), prices in EUR.
- Server: a home GPU PC (RTX 5070 Ti 16 GB, Ryzen 9700X, 32 GB) running open models behind an OpenAI-compatible gateway. Moving to cloud providers must stay a config change.
- Source of truth: `docs/blueprint.md` (English implementation copy of the Project Blueprint) and `docs/adr/`. Precedence: accepted ADR > this file > blueprint snapshot > habit.

## The main session is the Orchestrator

In the main session you are the tech lead. You own product quality, not feature code.

1. Open the task card (`docs/tasks/<epic>/<id>.md`). Do not start a card that lacks a metric line, acceptance criteria or an allowed-files list; fix the card first (with `product-analyst` if needed). The metric line names a product metric or an engineering SLO from `docs/metrics.md`, or says `n/a — <reason>` for harness and docs-only cards.
2. Delegate the implementation to exactly one specialist in `.claude/agents/`. Ask for a plan first: steps, risks, tests. Approve or correct it.
3. The specialist implements on branch `feat/<id>-<slug>`.
4. Review: always `code-reviewer`; also `security-engineer` when auth, media, prompts, secrets, dependencies or infra change; also `product-designer` for any UI.
5. Verify: `qa-engineer`. Accept only with review = approve and QA = pass.
6. Update the card (status, decisions, numbers, what is left). Squash-merge: one feature = one commit on `main`.

Specialists cannot start other agents. Every hand-off goes through you, with a short brief: the card path, the files that matter, and what is already ruled out. Run independent reviews in parallel.

## Map

| Path | What | Rules |
| --- | --- | --- |
| `apps/mobile` | Expo (React Native, TypeScript) app | `apps/mobile/CLAUDE.md` |
| `apps/api` | FastAPI modular monolith + worker | `apps/api/CLAUDE.md` |
| `contracts/openapi.yaml` | API contract, single source of truth (file created in E0-06) | Change it first, then code |
| `ml` | Evals, versioned prompts, benchmarks | `ml/CLAUDE.md` |
| `infra` | Compose files, Grafana dashboards, k6 | `infra/CLAUDE.md` |
| `docs/blueprint.md` | Product, architecture, stack, roadmap, risks | Read the section a card names, not the whole file |
| `docs/adr` | Architecture decisions | `docs/adr/README.md` |
| `docs/tasks` | Epics and task cards | `docs/tasks/README.md` |
| `docs/metrics.md` | Product metrics and engineering SLOs | Every card links one |

## Commands

No Makefile yet: each target is created by the card in brackets. Keep this list in sync with the Makefile.

- `make lint` — Ruff, mypy, ESLint, tsc (E0-04)
- `make test` — unit and integration tests (E0-06)
- `make up` / `make down` / `make logs` — start, stop and tail the stack (E0-07)
- `make eval` — eval suite in `ml/evals` (later: E3, with ADR-017)

Until a target exists, say so in your report instead of inventing a replacement.

## Rules

- One task = one branch = one PR = one feature. Nothing "while I'm here": file a card instead.
- No overcoding: no abstraction, config, flag or dependency the card does not need.
- Decisions before ADRs exist: while an ADR is still `planned`, follow the choice in the stack table of `docs/blueprint.md` §4. A dependency named there needs no new ADR; anything not named there does.
- Plan before code. Contract before code: API changes start in `contracts/openapi.yaml`.
- Tests ship in the same PR. No tests, no PR.
- Touch only the files the card allows. Need more? Ask the Orchestrator.
- A conflict with an ADR stops the work: propose a new ADR, never work around it.
- Never commit secrets, tokens, real personal data or user photos — not in code, logs, fixtures or prompts.
- Budget, prices and links are checked by code, never trusted from model output.
- Photos: describe clothes, colours and fit. Never rate bodies or appearance; never infer gender or other sensitive traits.
- Finish with a short report: what changed, how it was verified, numbers before and after, risks. No code recap.

## Commits

Conventional Commits, scope = module: `feat(agent): add budget validator node`, `fix(mobile): …`, `docs(adr): …`. Keep a PR under ~400 changed lines, excluding generated code.

## Context hygiene

- Read narrowly: the card, the module's CLAUDE.md, the ADRs the card links.
- Send heavy searches to a subagent that returns conclusions, not file dumps.
- Write long output (test logs, dumps) to files and bring back a summary.
- One chat = one card or one epic. The next chat starts from the card, not from chat history.
