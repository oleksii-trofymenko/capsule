# E1-27 · Migration runner: lock timeout and a clean error for a malformed URL

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] `env.py` sets `lock_timeout` (start with 5 s) for every migration transaction. A migration that cannot get its lock fails fast with the sanitised one-line error and rolls back.
- [x] The runbook says what to do when a migration times out on a lock (find the blocker, retry), and how a single migration may raise the limit with `SET LOCAL` when it needs to.
- [x] A malformed `DATABASE_URL` exits non-zero with the fixed `ConfigError` message only: no traceback, no URL part.
- [x] Tests: integration test that holds a conflicting lock and checks the migration fails within the timeout; unit test for the malformed URL.
- [x] Docs: `docs/runbooks/compose-stack.md` (migration section).

## Allowed files

- `apps/api/migrations/env.py`, `apps/api/migrations/errors.py`, `apps/api/tests/**`
- `docs/runbooks/compose-stack.md`

## Out of scope

- `statement_timeout` for `api` queries. Separate roles (E1-26).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator), backend-engineer plan. PR #32.
- Decisions:
  - 2026-10-27 (plan): `lock_timeout` is a session setting through libpq `options` in `connect_args`, not `SET LOCAL`: `autocommit_block()` commits the transaction, so a `SET LOCAL` would be lost. A migration raises it with `SET LOCAL` (or plain `SET` inside an `autocommit_block()`). `LOCK_TIMEOUT = "5s"` is a constant; it overrides any `options` in `DATABASE_URL`.
  - 2026-10-27: URL parsing and engine creation run inside the sanitised `try`; `ConfigError` exits as one line with no chain.
  - 2026-10-27 (review, code-reviewer approved): runbook rollback wording (what ran before or inside a finished `autocommit_block()` stays applied), `SET LOCAL` scope, and the lock test sets `idle_in_transaction_session_timeout = '20s'` on the blocker so a regression fails in about 20 s instead of hanging.
  - 2026-10-27 (QA): a non-numeric port prints `migration failed: ValueError` and an out-of-range port `migration failed: OperationalError (OperationalError)`, not the `ConfigError` line the criterion names. Accepted: one line, no value, documented in the runbook. Port validation moves to E1-28 (`core/config.py`).
  - Filed 2026-10-27 from the E1-05a review (S4) and QA (traceback).
- Numbers:
  - `make test`: 119 passed before → 126 after (+3 unit, +4 integration). PR 5 files, ~190 changed lines.
  - Lock test: 5.1 s; with the timeout removed it fails at 20.05 s instead of hanging.
  - QA 2026-10-27 (qa-engineer, head be7d69f, project `capsule-e127-qa`, own image tag): pass.
    - `migrate` 0.77 s, `api` ready, `/v1/ready` 200.
    - Lock held on `alembic_version`: 3 runs fail in 6.3–6.5 s wall (5.6 s inside the container) with the one-line 55P03 message, no traceback. Blocked version INSERT after `downgrade base`: fails in 6.3 s and rolls back (0 rows).
    - `api` answered `/v1/ready` in 4 ms during the wait; no restarts.
    - `?options=-c lock_timeout=0` in the URL cannot switch it off (55P03 in 6.3 s).
    - Runbook blocker query finds the holder while `migrate` waits and an idle-in-transaction holder older than 1 minute; `pg_terminate_backend` then the rerun passes.
    - 10 malformed URLs: one line each; password, host, user and traceback hits 0.
- Left for later:
  - `compose.base.yml` tags `api` and `migrate` as `capsule-api:local` for every project, so parallel stacks from different branches overwrite each other's image (QA ran on a private tag). File a card if parallel work continues.
