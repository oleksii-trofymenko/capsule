# E0-03 · ADR-001 to ADR-010 for the core stack

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | Orchestrator (with the `adr` skill) |
| Reviewers | mobile-engineer (001–004), backend-engineer (005–008), ai-engineer (009–010), you |
| Estimate | M |
| Metric | Decisions on record |
| Depends on | E0-01 |
| ADRs | 001–010 |
| Design spec | none |

## Why

Agents must not re-decide the stack in every card. Ten short records fix the core choices and the triggers to revisit them.

## Acceptance criteria

- [ ] Ten files `docs/adr/001-…` to `010-…`, each from the template, one page at most.
- [ ] Each has at least two real alternatives with the reason they lost, and a "revisit when" trigger.
- [ ] ADR-010 states that model names and providers live only in gateway config, and that moving to cloud providers is a config change.
- [ ] ADR-007 states why one Postgres (with pgvector) beats a separate vector database at MVP scale.
- [ ] The owning specialist reviews each ADR; you accept them; status set to `accepted`.
- [ ] `docs/adr/README.md` index updated.

## Allowed files

- `docs/adr/**`

## Out of scope

- ADRs planned for later epics (011–019, except where E0-04 and E0-05 add 016, 018 and 019).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
- Numbers:
- Left for later:
