# E0-10 · Align docs with accepted ADRs

| Field | Value |
| --- | --- |
| Status | review |
| Owner | Orchestrator |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — docs only; prevents agents building to superseded choices |
| Depends on | E0-03, E0-05 |
| ADRs | 003, 005, 006, 008, 010, 016 |
| Design spec | none |

## Why

E0-03 and E0-05 changed several blueprint choices (MinIO → SeaweedFS, arq/Celery → SAQ, Python 3.12 → 3.13, Testcontainers → CI service containers, no media backups, no cloud fallback at €0). Module rules, the README and the blueprint still name the old ones, and E0-06/E0-07 agents read those files first.

## Acceptance criteria

- [x] `apps/api/CLAUDE.md`: Python 3.13 (ADR-005); integration tests against real Postgres and Redis as CI service containers / Compose (ADR-016).
- [x] `infra/CLAUDE.md`: SeaweedFS instead of MinIO; backups cover Postgres only, media are never backed up (ADR-008).
- [x] `README.md`: prerequisites say Python 3.13.
- [x] `docs/blueprint.md`: architecture diagram, stack table (§4), Compose and backup rules (§12) and roadmap lines match ADR-003, 005, 006, 008, 010 and 016; the snapshot note lists the changes.
- [x] E0-06 and E0-07 cards (not started) name the accepted choices.
- [x] No remaining mention of MinIO, arq/Celery as the choice, Python 3.12 or Testcontainers outside ADRs (where they appear as rejected options).
- [x] Tests: none (docs only); CI green.

## Allowed files

- `apps/api/CLAUDE.md`, `infra/CLAUDE.md`, `README.md`, `docs/blueprint.md`, `docs/tasks/README.md`, `docs/tasks/E0/E0-06-api-skeleton.md`, `docs/tasks/E0/E0-07-compose-base.md`, `docs/tasks/E0/E0-10-align-docs-with-adrs.md`

## Out of scope

- Changing any decision. ADRs are not edited.
- Rewriting the blueprint beyond the lines that conflict with accepted ADRs.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner ("do E0-10 first").
- Decisions:
  - Blueprint changed in its own `docs(blueprint)` commit, as its precedence note requires; the note now lists the ADR-driven changes.
  - Notes in done cards (E0-01…E0-05) keep their historical wording; only cards not started (E0-06, E0-07) were updated.
  - The blueprint's home-prod row now says cloud fallback is off while the budget is €0 (ADR-010).
- Review: code-reviewer requested changes — the first pass missed the ADR-010 cloud-fallback lines (diagram, §3 prose, E3 roadmap, chaos step) because the leftover search omitted `fallback`. Fixed, plus local-dev "no cloud route", Postgres backup target restored ("or the cloud", ADR-008 only excludes media), mobile storage row aligned with ADR-003, E0-06/E0-07 ADR fields updated.
- Numbers: 8 files. Leftover search (`minio|testcontainers|3\.12|arq or celery|fallback|sqlite` outside ADRs and done cards): only the blueprint change note, lines already qualified with "off while the budget is €0" / "once the budget allows (ADR-010)", and the fallback-rate metric and alert (ADR-010 monitors it).
- Left for later: E0-11 — align agent and skill rules with ADR-010 route names (`.claude/skills/agent-node/SKILL.md` uses aliases `fast`/`guide`/`vision`; ADR-010 uses `agent-parse`/`agent-guide`/`vision`/`embed`), check `ml/CLAUDE.md` and `.claude/agents/ai-engineer.md` fallback wording, and sweep the blueprint for ADR-001–004, 007, 009, 018, 019 drift. Before the E3 gateway card.
