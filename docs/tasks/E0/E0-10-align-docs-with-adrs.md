# E0-10 · Align docs with accepted ADRs

| Field | Value |
| --- | --- |
| Status | review |
| Owner | Orchestrator |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — docs only; prevents agents building to superseded choices |
| Depends on | E0-03, E0-05 |
| ADRs | 005, 006, 008, 010, 016 |
| Design spec | none |

## Why

E0-03 and E0-05 changed several blueprint choices (MinIO → SeaweedFS, arq/Celery → SAQ, Python 3.12 → 3.13, Testcontainers → CI service containers, no media backups, no cloud fallback at €0). Module rules, the README and the blueprint still name the old ones, and E0-06/E0-07 agents read those files first.

## Acceptance criteria

- [x] `apps/api/CLAUDE.md`: Python 3.13 (ADR-005); integration tests against real Postgres and Redis as CI service containers / Compose (ADR-016).
- [x] `infra/CLAUDE.md`: SeaweedFS instead of MinIO; backups cover Postgres only, media are never backed up (ADR-008).
- [x] `README.md`: prerequisites say Python 3.13.
- [x] `docs/blueprint.md`: architecture diagram, stack table (§4), Compose and backup rules (§12) and roadmap lines match ADR-005, 006, 008, 010 and 016; the snapshot note lists the changes.
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
- Numbers: 8 files, ~20 lines changed. Leftover search (`minio|testcontainers|3.12|arq or celery` outside ADRs and done cards): only the blueprint change note, by design.
- Left for later: none.
