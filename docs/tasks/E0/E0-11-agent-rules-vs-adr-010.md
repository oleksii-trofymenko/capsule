# E0-11 · Align agent and skill rules with ADR-010 and the other accepted ADRs

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | Orchestrator (with ai-engineer as reviewer) |
| Reviewers | code-reviewer, ai-engineer |
| Estimate | S |
| Metric | n/a — harness and docs only; prevents the E3 gateway card building to old names |
| Depends on | E0-10 |
| ADRs | 010 (and a sweep of 001–004, 007, 009, 018, 019) |
| Design spec | none |

## Why

The `agent-node` skill names model aliases (`fast`, `guide`, `vision`) and an "invalid → fallback alias" rule, while ADR-010 fixes logical route names (`agent-parse`, `agent-guide`, `vision`, `embed`) and no cloud route at €0. Agents on E3 read the skill first.

## Acceptance criteria

- [ ] `.claude/skills/agent-node/SKILL.md` uses ADR-010 route names; a model fallback means another local route, never a cloud route while the budget is €0.
- [ ] `.claude/agents/ai-engineer.md` and `ml/CLAUDE.md` fallback wording checked against ADR-010 and fixed if needed.
- [ ] Sweep of `.claude/**`, module `CLAUDE.md` files and `docs/blueprint.md` against ADR-001–004, 007, 009, 018, 019; conflicts fixed or listed.
- [ ] `.claude/skills/new-endpoint/SKILL.md` checklist gains one line: the first endpoint that accepts user input triggers card E1-06 (Schemathesis, per ADR-020).
- [ ] Tests: none (docs only); CI green.

## Allowed files

- `.claude/**`, `**/CLAUDE.md`, `docs/blueprint.md`, `docs/tasks/E0/E0-11-agent-rules-vs-adr-010.md`

## Out of scope

- Changing any decision; ADRs are not edited.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
