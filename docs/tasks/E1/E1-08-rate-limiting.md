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
  - [ ] A global limit across all clients on sign-in plus sign-up, on top of the per-IP limit, so that requests spread across many IPs cannot keep the password hasher saturated (A1, A2). Default and reason in the card notes. Refresh and guest-credential endpoints never count against this global budget. Accepted remainder: while an attack fills the bucket, real users cannot sign in or sign up (CPU is protected, availability of sign-in is not); record it under R10 in `docs/security.md` when this card lands.
  - [ ] Per-IP keys group IPv6 clients by their /64 prefix and IPv4 clients by the full address, so one host cannot dodge the limit by rotating addresses inside its /64. Tested with two addresses in the same /64.
  - [ ] Per principal (guest or account) on authenticated endpoints.
  - [ ] R1 (`docs/security.md`): failed sign-ins are throttled on email plus IP. The account is never locked, so an attacker cannot lock out the real user.
  - [ ] R1/D5: rate-limit keys use an HMAC of the IP or email (HMAC key per ADR-015), never the raw value, and every key has a TTL.
- [ ] Limits come from config. The defaults and the reasons for them are written in the card notes.
- [ ] Going over a limit returns 429 as an RFC 9457 problem document with `Retry-After`. The contract documents the 429 response on the affected operations.
- [ ] R2: `CF-Connecting-IP` is trusted only when the "behind tunnel" flag is on **and** the socket peer is the cloudflared container. The peer identity comes from config, so this card doesn't wait for E1-15, which fixes how the peer is identified. In every other case the socket address is used. Tests show the header is ignored on a direct request through the published host port, on a request from another container on `edge`, and when the flag is off.
- [ ] R8 (and A2): the rate limit runs before any password hash, so a flood of sign-ins cannot exhaust the CPU. A test shows a throttled request never reaches the hasher.
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
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
- Numbers:
- Left for later:
