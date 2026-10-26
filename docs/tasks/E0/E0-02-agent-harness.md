# E0-02 · Agent harness

| Field | Value |
| --- | --- |
| Status | review |
| Owner | Orchestrator |
| Reviewers | You |
| Estimate | S |
| Metric | n/a — harness and docs only |
| Depends on | E0-01 |
| ADRs | none |
| Design spec | none |

## Why

Every agent, in every chat, must start from the same rules, roles and templates, so quality does not depend on which session did the work.

## Acceptance criteria

- [ ] Root `CLAUDE.md` and module `CLAUDE.md` files (`apps/api`, `apps/mobile`, `ml`, `infra`).
- [ ] Nine specialist agents in `.claude/agents/`; the Orchestrator role lives in the root `CLAUDE.md` (main session).
- [ ] Skills in `.claude/skills/`: new-endpoint, db-migration, mobile-screen, agent-node, prompt-change, eval-run, load-test, security-check, adr, release.
- [ ] Commands: `/task`, `/review`, `/adr`.
- [ ] Templates: ADR, task card, PR. `docs/metrics.md`. E0 cards.
- [ ] `docs/blueprint.md`: snapshot of the Project Blueprint with a precedence note and Mermaid diagrams, so no agent depends on a link it cannot open.
- [ ] Every path the root `CLAUDE.md` names either exists or says which card creates it.
- [ ] Smoke test: in Claude Code, `/agents` lists the nine specialists and `/task E0-03` reaches the "plan" step.

## Allowed files

- `CLAUDE.md`, `**/CLAUDE.md`, `.claude/**`, `docs/blueprint.md`, `docs/adr/README.md`, `docs/adr/000-template.md`, `docs/tasks/**`, `docs/metrics.md`, `.github/pull_request_template.md`

## Out of scope

- Writing the ADRs themselves (E0-03).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: drafted in the Blueprint chat.
- Decisions: the Orchestrator is the main session, not a subagent, because subagents cannot start other agents.
- Numbers:
- Left for later: tune agent prompts after the first three cards.
- Review 2026-10-26 (owner): fixed unresolved references — blueprint snapshot added, Makefile targets mapped to cards, git remote moved into E0-01, interim rule for planned ADRs, "n/a" metric allowed, "one implementing specialist".
