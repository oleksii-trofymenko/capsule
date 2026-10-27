# E1-08 · Rate limits per IP and per credential

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | API latency (simple endpoints): p95 < 200 ms, p99 < 500 ms (the limiter must not push it over) |
| Depends on | E1-05 |
| ADRs | 006 (Redis for rate limits); a new ADR only if a library not named in blueprint §4 is added |
| Design spec | none |

## Why

The API becomes reachable from the internet through the tunnel. Without limits, anyone can create unlimited guest credentials or guess passwords, and the home server falls over (flows.md: "Rate limits apply per guest credential and per IP").

## Acceptance criteria

- [ ] Redis-backed limits:
  - [ ] Per client IP on guest-credential issue, sign-up and sign-in.
  - [ ] Per principal (guest or account) on authenticated endpoints.
  - [ ] A stricter per-email limit on failed sign-ins.
  - [ ] Every key has a TTL.
- [ ] Limits come from config. The defaults and the reasons for them are written in the card notes.
- [ ] Going over a limit returns 429 as an RFC 9457 problem document with `Retry-After`. The contract documents the 429 response on the affected operations.
- [ ] Client IP: `CF-Connecting-IP` is trusted only when a config flag says the API sits behind the tunnel; otherwise the socket address is used. A test proves a spoofed header is ignored when the flag is off.
- [ ] Redis down: auth endpoints fail closed with 503 problem documents, not 500s.
- [ ] Tests: unit for the limit logic; integration with real Redis (limit reached, window resets, Redis down); contract.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/core/**`, `apps/api/modules/auth/**`, `apps/api/main.py`, `apps/api/pyproject.toml`, `apps/api/uv.lock`
- `apps/api/tests/**`, `docs/adr/0xx-*.md` and `docs/adr/README.md` (only if a library is added)

## Out of scope

- Cloudflare-side WAF rules. Limits on consultation endpoints (E3 sets them).
- The error format, which already exists in the contract.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
- Numbers:
- Left for later:
