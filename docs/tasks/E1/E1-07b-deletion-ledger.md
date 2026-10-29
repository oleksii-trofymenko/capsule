# E1-07b · Deletion ledger

| Field | Value |
| --- | --- |
| Status | in progress |
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

- [ ] Migration: a `deletion_ledger` table holding only the principal id (primary key, no foreign key) and the deletion time. Upgrade, downgrade and upgrade again work.
- [ ] One writer in `core/`:
  - inserts the row in the caller's transaction and returns the deletion time;
  - after commit, appends `<principal id> <deletion time, ISO-8601 UTC>` as one line to `deletion-ledger.txt` in the directory from config (`DELETION_LEDGER_DIR`, optional, no default path in code);
  - never creates the directory, so a missing mount cannot write into the container filesystem;
  - file I/O runs off the event loop, with a bounded wait.
- [ ] A missing, unset or unwritable ledger directory, or a failed append, never fails a request or stops `api` from starting. The writer logs an error with the principal id and the error type only; the table stays the record.
- [ ] `api` checks the directory at start-up and logs an error if it is unset, missing, not a directory or not writable.
- [ ] `.env.example` documents `DELETION_LEDGER_DIR` (commented).
- [ ] Tests: the row is written in the caller's transaction and rolls back with it; the line format; append to a missing directory and to a path that is a file; the timeout path; start-up with a missing directory (logs, `/v1/ready` fine).

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
- Numbers:
- Left for later:
