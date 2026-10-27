# E8-01 · Named Cloudflare tunnel on an owned domain

| Field | Value |
| --- | --- |
| Status | todo (blocked on the owner's domain purchase, about €10 a year) |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Availability (home server): 99% (a stable URL makes the external uptime monitor possible) |
| Depends on | E1-15; the owner buys a domain |
| ADRs | 014, 015 (tunnel token) |
| Design spec | none |

## Why

As a beta tester, I want the app to reach the server at one stable, trusted address, so that it keeps working after the home PC restarts and my connection can be pinned. The E1 quick tunnel changes URL on every restart, has no uptime guarantee and does not support Server-Sent Events. This card covers threats T5 and R7 in `docs/security.md`, and provides the stable hostname P4 needs. E8-02 covers P4 (pinning) and P5 (bundle scan).

## Acceptance criteria

- [ ] T5 / R7 (`docs/security.md`): the quick tunnel (testing only, no uptime promise, E1 demo only) is not used for external beta. This card replaces it before any external tester gets a build.
- [ ] A named tunnel on the owner's domain (for example `api.<domain>`) replaces the quick tunnel in `compose.tunnel.yml`. The tunnel token is stored as ADR-015 requires, and only the API is reachable, as in E1-15.
- [ ] The trusted-peer setting from E1-08/E1-15 (R2) still holds with the named tunnel.
- [ ] Streaming works through the tunnel: a test SSE endpoint, or the E3 stream if it exists, delivers events without buffering from a phone on mobile data.
- [ ] The mobile env points at the stable URL, and the runbook drops the "URL changes on restart" step.
- [ ] Tests: the E1-15 check scripts pass against the named tunnel, `GET /v1/health` works through the domain, and the SSE check passes.

## Allowed files

- `infra/compose/compose.tunnel.yml`, `infra/compose/check-*.sh`, `infra/compose/README.md`, `docs/runbooks/compose-stack.md`, `apps/mobile/.env.example`

## Out of scope

- Certificate pinning and the bundle scan (E8-02). Cloudflare Access for admin UIs (separate card). Moving the stack to the cloud.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27: amended from E1-01 threat model (docs/security.md).
  - Cost flag: a domain costs about €10 a year, which breaks the €0 budget. The owner deferred buying it to E8 (2026-10-27). The card stays blocked until the owner buys one.
  - It may be pulled forward before E3 streaming, because quick tunnels do not support SSE (see E1-15).
- Numbers:
- Left for later:
