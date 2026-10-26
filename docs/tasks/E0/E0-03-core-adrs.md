# E0-03 · ADR-001 to ADR-010 for the core stack

| Field | Value |
| --- | --- |
| Status | review |
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

- [x] Ten files `docs/adr/001-…` to `010-…`, each from the template, one page at most.
- [x] Each has at least two real alternatives with the reason they lost, and a "revisit when" trigger.
- [x] ADR-010 states that model names and providers live only in gateway config, and that moving to cloud providers is a config change.
- [x] ADR-007 states why one Postgres (with pgvector) beats a separate vector database at MVP scale.
- [ ] The owning specialist reviews each ADR; you accept them; status set to `accepted`.
- [x] `docs/adr/README.md` index updated.

## Allowed files

- `docs/adr/**`

## Out of scope

- ADRs planned for later epics (011–019, except where E0-04 and E0-05 add 016, 018 and 019).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner, via `/task E0-03`.
- Decisions:
  - ADR-006: SAQ instead of arq (arq maintenance-only since 2026) or Celery. Owner's choice.
  - ADR-008: SeaweedFS behind the S3 API instead of MinIO (community edition archived April 2026); media deleted within 24 h by our own job, never backed up. Owner's choice for the store.
  - ADR-005: Python 3.13 instead of 3.12 (3.12 security-only since April 2025).
  - ADR-003: expo-sqlite deferred; offline history and queue use the persisted TanStack Query cache only (one offline mechanism, ADR-002).
  - ADR-007: two named exceptions to "Alembic only" — LangGraph checkpoint schema (created by an Alembic migration) and LiteLLM's own database.
  - ADR-010: `litellm` PyPI package banned everywhere after the March 2026 supply-chain compromise; official image ≥ 1.83.0 pinned by digest.
- Reviews: mobile-engineer (001–004), backend-engineer (005–008), ai-engineer (009–010), security-engineer (003, 004, 008, 010): all accept with changes, all changes applied. code-reviewer: approve.
- Numbers: 10 ADRs, each one page; 4 reviewers, 0 rejections.
- Left for later:
  - Blueprint §4 and §12 still name MinIO, arq/Celery and Python 3.12+; update in its own `docs(blueprint)` commit. README prerequisites say Python 3.12.
  - Client-generated idempotency key for queued chat messages is a contract change (backend-engineer, chat card).
  - Verify SeaweedFS lifecycle, presigned URLs and SSE with an integration test before `media` relies on them.
  - €50/month analytics spend trigger in ADR-004 to be confirmed by the owner.
