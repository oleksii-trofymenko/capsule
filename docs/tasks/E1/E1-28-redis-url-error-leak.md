# E1-28 · URL settings: config errors name no value, ports are validated

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — log hygiene fix; no product metric or SLO moves |
| Depends on | none |
| ADRs | 015 |
| Design spec | none |

## Why

E1-05a fixed a leak for `DATABASE_URL`: a host that `urlsplit` cannot parse was quoted in the `ConfigError`. `REDIS_URL` still has it. `Settings.from_env` with a bracketed host prints `'secrethost' does not appear to be an IPv4 or IPv6 address`, which can carry a mistyped password into the logs.

## Acceptance criteria

- [ ] A `REDIS_URL` that cannot be parsed raises a fixed-message `ConfigError` `from None`, the same way `DATABASE_URL` does. The message names the variable, never a part of its value.
- [ ] `DATABASE_URL` and `REDIS_URL` with a non-numeric or out-of-range port raise the fixed `ConfigError` at config time, so `migrate` prints the `ConfigError` line instead of `migration failed: ValueError` / `OperationalError` (E1-27 QA).
- [ ] Tests: unit tests for a bracketed host, a bad port and a URL with a password, each checking the message holds no part of the input.

## Allowed files

- `apps/api/core/config.py`, `apps/api/tests/unit/test_config.py`

## Out of scope

- Other settings.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05a review.
  - 2026-10-27: added port validation for both URLs (E1-27 QA).
- Numbers:
- Left for later:
