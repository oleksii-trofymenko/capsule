# E1-05d · Signing-key loading and database-error log sanitising

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — core security plumbing (key loading, log hygiene); no product metric or SLO moves |
| Depends on | E1-05a, E1-05b |
| ADRs | 014, 015, 022 |
| Design spec | none |

## Why

The auth core (E1-05, E1-05c) needs the JWT signing keys loaded and checked at start, and every later endpoint needs database errors logged without the rejected values. Both are core pieces with no auth tables, so they ship first (split from E1-05 for size).

## Acceptance criteria

- [ ] Signing keys are read from `/run/secrets/jwt_signing_keys` (E1-05b provides the file) as ADR-015 requires. The path is a constant, not a new setting; tests pass keys in memory or call the loader with a test path.
- [ ] `api` refuses to start with zero or more than two keys, with an unreadable file, a malformed line, a bad or duplicate `kid`, or a key shorter than 32 bytes after hex decoding (at least 64 hex characters, ADR-014; E1-05b writes exactly 64). The error names the path, the line number, the `kid` or the count, never a value.
- [ ] The first key signs; the second only verifies (ADR-015 rotation).
- [ ] ADR-022, API half of E1-05a M1: a database error (for example `IntegrityError`) never reaches the logs with the driver's DETAIL, parameters or row values, whether it arrives as `exc_info` or as a log argument. The line carries only the error type, SQLSTATE and constraint name. `migrations/errors.py` uses the same helper, with no change in its output.
- [ ] R4: a test proves the access log line holds no client IP and no query string, and `uvicorn.access` writes nothing.
- [ ] Tests: unit tests for every rejection above, each asserting the value is not in the message; a unique violation on real Postgres (a temp table is enough) checked in the log line; `make test` and the CI `stack` job green (the real key file passes).

## Allowed files

- `apps/api/core/**`, `apps/api/migrations/errors.py`, `apps/api/main.py` (only to pass keys on), `apps/api/tests/**`

## Out of scope

- Tokens, tables and endpoints (E1-05, E1-05c).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator), from the backend-engineer E1-05 plan, part A.
- Decisions:
  - Filed 2026-10-27: split from E1-05 (plan estimate ~1,450 lines for the whole card).
  - 2026-10-27: no `JWT_SIGNING_KEYS_FILE` setting; the path is fixed by ADR-015 (no config the card does not need).
- Numbers:
- Left for later:
