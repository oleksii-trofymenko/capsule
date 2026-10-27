# E1-05d · Signing-key loading and database-error log sanitising

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] Signing keys are read from `/run/secrets/jwt_signing_keys` (E1-05b provides the file) as ADR-015 requires. The path is a constant, not a new setting; tests pass keys in memory or call the loader with a test path.
- [x] `api` refuses to start with zero or more than two keys, with an unreadable file, a malformed line, a bad or duplicate `kid`, or a key shorter than 32 bytes after hex decoding (at least 64 hex characters, ADR-014; E1-05b writes exactly 64). The error names the path, the line number, the `kid` or the count, never a value.
- [x] The first key signs; the second only verifies (ADR-015 rotation).
- [x] ADR-022, API half of E1-05a M1: a database error (for example `IntegrityError`) never reaches the logs with the driver's DETAIL, parameters or row values, whether it arrives as `exc_info` or as a log argument. The line carries only the error type, SQLSTATE and constraint name. `migrations/errors.py` uses the same helper, with no change in its output.
- [x] R4: a test proves the access log line holds no client IP and no query string, and `uvicorn.access` writes nothing.
- [x] Tests: unit tests for every rejection above, each asserting the value is not in the message; a unique violation on real Postgres (a temp table is enough) checked in the log line; `make test` and the CI `stack` job green (the real key file passes).

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
  - 2026-10-27 (build, PR #31): keys are `SecretBytes` (binary), which meets ADR-015's "`SecretStr`" intent: masked in repr and JSON. `kid` must match the ADR-015 date format `YYYY-MM-DD(-N)`, so hex can never pass as a kid and be echoed. `Settings.signing_keys` defaults to `()` so the E1-10 worker can build Settings with no key file; `create_app` and `signing_key` refuse zero keys.
  - 2026-10-27 (review, code-reviewer and security-engineer approved after two fix rounds):
    - M1: messages built by libraries (asyncio "Task exception was never retrieved") had DETAIL in `msg`. Now the str/repr of each DB error in the chain is replaced in one pass (longest first), and with a DB `exc_info` the message keeps only its first line.
    - L1/N2: DB errors inside containers (values and keys, depth 8) and in finished Task/Future arguments are described; other arguments pass through unchanged.
    - L2: `JsonHandler.handleError` writes one JSON line (logger, where, error type, ts, request_id), never the message or arguments.
    - CR3: DB-error tracebacks keep frame locations (`traceback.format_list`, no locals, no exception text).
    - R4 test moved to integration (it opens a socket).
    - L3 (Ruff logging rules) moved to E1-31. The PR is ~915 changed lines, over the ~400 guide; mostly tests and review hardening, accepted by the Orchestrator.
- Numbers:
  - `make test`: 74 passed before (main) → 119 after. PR ~935 changed lines (875 insertions, 61 deletions), most of it tests and review hardening.
  - CI at 4d80f2f: all jobs pass, including `stack` (the real key file loads in the container).
  - QA 2026-10-27 (qa-engineer, head 4d80f2f, project `capsule-e105d-qa`): pass on all criteria.
    - Good key: healthy, `/v1/ready` 200; `api` recreate to ready about 2.0 s (median of 3).
    - Refused, with no key value in the log (full and 8-hex grep 0 hits each): 0 keys, blank lines only, 3 keys, 62 hex, odd length, non-hex, 32-hex kid (not echoed), duplicate kid, no `=`, non-ASCII, missing file (Docker Desktop mounts an empty folder; `cannot read (IsADirectoryError)`).
    - Two keys: first signs, the previous one verifies, an unknown kid gives none, repr masked.
    - A real unique violation logged 7 ways (exc_info, %s, %r, dict, mixed, `.orig`, asyncio unretrieved task): every line `IntegrityError (UniqueViolation); sqlstate=23505; constraint=…`; `DETAIL` 0 lines stack-wide.
    - R4: with `X-Forwarded-For` and query strings holding an email and a token, access lines hold no IP and no query; `uvicorn.access` 0 lines.
- Left for later:
  - Rebuilding a named tuple that holds a DB error prints it as a plain tuple (accepted; it only happens when a DB error is inside).
  - A key-file failure prints a plain-text uvicorn traceback before JSON logging starts; it holds no values.
  - `capsule-api:local` is shared by every Compose project, so an isolated QA build replaces the owner's local tag until the next `make up`.
  - E2 Sentry card: turn off frame locals (`include_local_variables`) or scrub `text`, `raw`, `hex_key`; the key loader's locals hold the key file.
  - E1-05: any entry point other than `create_app` that signs tokens needs the same zero-key check; a non-string `kid` header is rejected before lookup.
  - Text a caller formats itself, and objects embedding an exception in their own `repr`, are not caught (E1-31 adds the lint).
