# E1-15 · Cloudflare quick tunnel to the home PC (`compose.tunnel`)

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Availability (home server): 99% (external uptime monitor; this card makes the API reachable from outside so it can be measured) |
| Depends on | E1-02, E1-04 |
| ADRs | 014, 015 |
| Design spec | none |

## Why

As the project owner, I want to reach the API on the home PC from my phone over mobile data, with no open router ports, so that I can demo sign-up and sign-in anywhere.

## Acceptance criteria

- [ ] `infra/compose/compose.tunnel.yml` adds `cloudflared` running a free quick tunnel (trycloudflare) to the `api` service only. The image is pinned by digest (`check-pins.sh`), the service is non-root with all capabilities dropped (`check-privileges.sh`), and it needs no Cloudflare account or token.
- [ ] The tunnel is opt-in: plain `make up` does not start it. A documented command (and a Make target only if the Orchestrator approves it) starts it and prints the public URL.
- [ ] Only the API is reachable through the tunnel. Postgres, Redis, SeaweedFS and any admin UI are not. A check script or CI step proves this, for example that requests for other host ports through the tunnel fail.
- [ ] The API runs with the "behind tunnel" flag from E1-08, so `CF-Connecting-IP` is trusted only in this setup.
- [ ] R2, peer side (`docs/security.md`): fix how the API identifies the cloudflared container as the socket peer. Its address on `edge` is dynamic, and traffic through the published host port can arrive from the bridge gateway, so use for example a dedicated network for cloudflared and api, or a resolved service name. The result goes into the API's trusted-peer config from E1-08. A check proves that requests through the published host port, or from another container on `edge`, are not treated as the tunnel.
- [ ] R7 / T5: the runbook and `compose.tunnel.yml` comment state that the quick tunnel is for the E1 demo only, not external beta. E8-01 replaces it.
- [ ] M6 (ADR-022): cloudflared runs with `--loglevel info`, never debug (request lines with client IPs and URLs appear only at debug), and with no access logging. A check asserts the flag in `compose.tunnel.yml`.
- [ ] The runbook explains how to put the printed URL into the mobile env (`EXPO_PUBLIC_*`, E1-12) and that the URL changes every time cloudflared restarts.
- [ ] Tests: `make up` plus the tunnel on the home PC, `GET /v1/health` through the public URL returns 200 from a phone on mobile data, and the check scripts pass. CI keeps passing without the tunnel.

## Allowed files

- `infra/compose/compose.tunnel.yml`, `infra/compose/check-pins.sh`, `infra/compose/check-privileges.sh`, `infra/compose/README.md`, `docs/runbooks/compose-stack.md`, `Makefile` (only with Orchestrator approval), `CLAUDE.md` (Commands list, only if a Make target is added)

## Out of scope

- Buying a domain, named tunnels, pinning and the bundle scan (E8-01). Cloudflare Access for admin UIs (E2/E8).
- An external uptime monitor (E2).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: the E1 demo uses a free quick tunnel (trycloudflare) with the URL set through env. Buying a domain (needed for a named tunnel with a stable URL) is deferred to E8.
  - 2026-10-27, owner: email and password with no email sending, a self-declared 18+ checkbox, and 30-day guest retention. None of these changes this card, but the tunnel exposes the auth endpoints, so E1-08 rate limits must be live before the demo (E1-16).
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
- Numbers:
- Left for later:
  - Quick tunnels are meant for testing. They have no uptime guarantee and a concurrent-request cap, and Cloudflare documents that they do not support Server-Sent Events. Check this before E3 streaming; it may force E8-01 (domain and named tunnel) earlier.
  - The random URL is unlisted, not secret. Treat the API as public (E1-01 threat model).
