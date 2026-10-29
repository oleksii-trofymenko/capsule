# E1-07a · Password hasher, password rules and email normalisation

| Field | Value |
| --- | --- |
| Status | done |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | API latency (password endpoints): p95 < 600 ms, p99 < 1 s — this card measures the hash time that budget spends |
| Depends on | E1-05 |
| ADRs | 014, 023 |
| Design spec | none |

## Why

Sign-up and sign-in (E1-07) need a password hasher that cannot be used to exhaust the home server's CPU, the password rules from ADR-014, and one email normalisation rule. Split from E1-07 for size.

## Acceptance criteria

- [x] `argon2-cffi` as ADR-023 names it, added to the runtime dependencies and the lock, with every new package released at least 7 days earlier (ADR-018/019). pip-audit clean.
- [x] argon2id with the ADR-014 parameters. A constant dummy hash with the same parameters for unknown emails; a test asserts it does not need rehashing.
- [x] `asyncio.Semaphore(4)`, acquired with a 1 s timeout, in front of a dedicated 4-thread executor created in the lifespan. A timeout raises an error that maps to 503 with `Retry-After: 1` and runs no hash. A slot is released only when its hash thread finishes, so a cancelled request never lets a fifth hash run. Hashing never runs inside a database transaction.
- [x] Password rules from ADR-014 (length in code points after NFC, blocklist, the product name, the email's local part), checked by a Pydantic validator that the real app and the Schemathesis fake share. A broken rule returns 422 and never echoes the value.
- [x] The blocklist is a data file in `modules/auth/data/` from a permissively licensed source (proposed: SecLists, MIT), filtered to the minimum length; source, version and licence recorded in the file header.
- [x] Email normalisation from ADR-014 (trim, NFC, lower case; `+tag` and dots kept), with the 254-character limit checked after normalising.
- [x] Hash and verify time on the home PC recorded in the card.
- [x] Tests: unit for the parameters, the dummy hash, rules at the boundaries (11/12 and 128/129 code points), normalisation variants, a semaphore timeout that runs no hash, and a cancelled caller holding its slot.

## Allowed files

- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/main.py`
- `apps/api/pyproject.toml`, `apps/api/uv.lock`
- `apps/api/tests/**`

## Out of scope

- Endpoints (E1-07). Rate limits (E1-08), which go in front of the semaphore.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-28 (Orchestrator), from the backend-engineer E1-07 plan, part A.
- Decisions:
  - Filed 2026-10-28: split from E1-07.
  - 2026-10-28 (PR #38): ADR-014 parameters kept (t=3). Measured in the Linux image they sit inside the 100–300 ms band; the 87 ms first measured came from the Windows wheel and does not count. No ADR change.
  - 2026-10-28: the product-name rule is a substring match after casefold (an equal match could never pass the 12-character minimum).
  - 2026-10-28 (security L3): the password may not contain the email's local part with any `+tag` removed when that part is at least 4 code points; shorter local parts block only an equal password.
  - 2026-10-28: passwords and emails that do not encode as UTF-8 (lone surrogates) get 422, never 500. Emails with whitespace, C0/C1 controls or Unicode format characters (Cf) anywhere are refused.
  - 2026-10-28: models carrying a password or email set `hide_input_in_errors=True`. The hasher instance is private, so nothing can bypass the semaphore.
  - 2026-10-28: the 503 comes from a generic `ServiceBusyError` in `core/errors.py` with `Retry-After`; `HasherBusyError` subclasses it. The E1-05c lock-timeout 503 can move onto it in E1-07.
  - 2026-10-28: blocklist from SecLists `Pwdb_top-1000000.txt` (commit 12274c98, MIT), NFC + casefold, 12–128 code points, without email-shaped, `$hex[...]` and control-character lines: 29,931 entries, 427 kB.
- Numbers (PR #38; QA in the Linux image on the 9700X, 60 runs each, two runs):
  - Hash: median 106–108 ms, p95 112–114 ms, max 124 ms.
  - Verify: median 104–107 ms, p95 110–117 ms. Dummy verify for an unknown email: median 104–108 ms, the same cost.
  - 4 hashes in parallel, per call: median 127–132 ms, p95 136–140 ms, max 151 ms.
  - CPU guard: a fifth call is refused after 1.00 s with no hash started; 503 with `Retry-After: 1` through the app. Bursts of 20–60 calls never ran more than 4 hashes or used more than 4 cores.
  - Tests: 329 (267 before E1-07a's base); 62 new.
- Left for later:
  - E1-07 QA must check what this card could not without endpoints: no hash inside a database transaction, and the Schemathesis fake sharing `NewCredentials`.
  - The margin under the 100 ms floor is thin (single samples at 98–99 ms). If a CPU or cloud move takes the median below 100 ms, propose t=4 (about 133 ms) in a new ADR.
  - Fullwidth "ＣＡＰＳＵＬＥ" passes the product-name rule (no NFKC); ADR-014 only asks for case-insensitive. Not filed.
  - A request-body size limit is E1-22.
