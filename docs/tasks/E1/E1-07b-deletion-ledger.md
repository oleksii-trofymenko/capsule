# E1-07b · Deletion ledger

| Field | Value |
| --- | --- |
| Status | done |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | Data deletion SLO (`docs/metrics.md`); product metric: sign-up conversion, through E1-07c |
| Depends on | E1-05 |
| ADRs | 022 |
| Design spec | n/a (no UI) |

## Why

The guest-data move (E1-07c) and "Delete my data" (E1-09) must record every deleted principal so a restore can replay the deletion (ADR-022). This card builds the ledger and its one writer; nothing calls it yet. Split from E1-07c for size.

## Acceptance criteria

- [x] Migration: a `deletion_ledger` table holding only the principal id (primary key, no foreign key) and the deletion time. Upgrade, downgrade and upgrade again work.
- [x] One writer in `core/`:
  - inserts the row in the caller's transaction and returns the deletion time;
  - after commit, appends `<principal id> <deletion time, ISO-8601 UTC>` as one line to `deletion-ledger.txt` in the directory from config (`DELETION_LEDGER_DIR`, optional, no default path in code);
  - never creates the directory, so a missing mount cannot write into the container filesystem;
  - file I/O runs off the event loop, with a bounded wait.
- [x] A missing, unset or unwritable ledger directory, or a failed append, never fails a request or stops `api` from starting. The writer logs an error with the principal id and the error type only; the table stays the record.
- [x] `api` checks the directory at start-up and logs an error if it is unset, missing, not a directory or not writable.
- [x] `.env.example` documents `DELETION_LEDGER_DIR` (commented).
- [x] Tests: the row is written in the caller's transaction and rolls back with it; the line format; append to a missing directory and to a path that is a file; the timeout path; start-up with a missing directory (logs, `/v1/ready` fine).

## Allowed files

- `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`
- `.env.example` (ledger directory setting only)
- `apps/api/tests/**`

## Out of scope

- Calling the writer: E1-07c (guest-data move) and E1-09 (delete my data).
- The Compose mount, pruning and a `deleted_at` index: E1-23.

## Analytics events

- none.

## Notes (filled while working)

- Plan approved: 2026-10-29 (Orchestrator), from the backend-engineer E1-07c plan, PR A.
- Decisions:
  - 2026-10-29: split from E1-07c for size (~700 lines planned with tests).
  - 2026-10-29: file name fixed as `deletion-ledger.txt`, one line per id; E1-23 must use it. Until E1-23 mounts the directory, `make up` leaves the setting unset, so every deletion logs a failed append. ADR-022 accepts this (restore step 2 reads those errors).
  - 2026-10-29 (security review M1): a cancelled append (cancelled request, or `close()` dropping a queued write) logs `ledger_append_failed` with `error="CancelledError"` and re-raises, so no failed append is silent.
  - 2026-10-29 (both reviews): a relative `DELETION_LEDGER_DIR` is an invalid setting, so `api` refuses to start, like any other invalid setting. An absolute path that is unusable only logs. The asymmetry is intended: a relative value is always a config mistake and would write into the container.
  - 2026-10-29: a write stuck on a hung disk blocks `api` exit until Docker's SIGKILL. Accepted; the table stays the record.
- Numbers (PR, head 78b2f6e):
  - Tests: 391 (371 before).
  - Ledger insert `EXPLAIN (ANALYZE, BUFFERS)` on 10,000 rows: 0.051 ms, 13 shared hits, `deletion_ledger_pkey` only.
  - Append with fsync, Linux container on the Docker Desktop bind mount, 3 × 500 runs: p50 4.0 ms, p95 4.5 ms, max 6.3 ms (tmpfs: p95 0.26 ms). After commit, well inside API p95 < 200 ms.
  - Hung disk (FIFO): two concurrent appends both returned after 2.003 s and logged `TimeoutError`; event loop not blocked.
  - QA start-up matrix: unset, empty, missing, not a directory and read-only each log `ledger_directory_unusable` with the right reason; `api` starts, `/v1/ready` 200, no directory created. No path, email, IP or token in 78 log lines.
- Left for later:
  - Idempotent re-recording of an id (E1-09, E1-23); alerts, strict replay parser, mount and `fsync` on the bind mount (E1-23); see those cards.
  - A read-only mount logs only `OSError` (EROFS), with no errno. Fine under "error type only"; revisit if restore triage needs it.
  - `docs/security.md` §-logs says a deletion is logged as a count with the principal type; the per-id `ledger_append_failed` line follows ADR-022. Align it the next time security.md is edited.
  - The `CancelledError` path is unit-tested only until E1-07c calls the writer.
