# E1-27 · Migration runner: lock timeout and a clean error for a malformed URL

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | Availability (home server): 99% — a migration waiting on a lock must not hold up every API query behind it |
| Depends on | E1-05a |
| ADRs | 022 |
| Design spec | none |

## Why

A migration that takes an `ACCESS EXCLUSIVE` lock queues behind any long transaction, and every query from `api` then queues behind the migration. Without `lock_timeout` this looks like an outage (E1-05a review, S4). Separately, a malformed `DATABASE_URL` makes `migrate` print a full traceback, because `database_url_from_env()` runs outside the sanitised block in `env.py` (E1-05a QA).

## Acceptance criteria

- [ ] `env.py` sets `lock_timeout` (start with 5 s) for every migration transaction. A migration that cannot get its lock fails fast with the sanitised one-line error and rolls back.
- [ ] The runbook says what to do when a migration times out on a lock (find the blocker, retry), and how a single migration may raise the limit with `SET LOCAL` when it needs to.
- [ ] A malformed `DATABASE_URL` exits non-zero with the fixed `ConfigError` message only: no traceback, no URL part.
- [ ] Tests: integration test that holds a conflicting lock and checks the migration fails within the timeout; unit test for the malformed URL.
- [ ] Docs: `docs/runbooks/compose-stack.md` (migration section).

## Allowed files

- `apps/api/migrations/env.py`, `apps/api/migrations/errors.py`, `apps/api/tests/**`
- `docs/runbooks/compose-stack.md`

## Out of scope

- `statement_timeout` for `api` queries. Separate roles (E1-26).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05a review (S4) and QA (traceback).
- Numbers:
- Left for later:
