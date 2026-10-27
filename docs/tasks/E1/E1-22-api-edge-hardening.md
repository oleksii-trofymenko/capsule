# E1-22 · API edge hardening: body size limit, docs off in tunnel mode, clean errors

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — edge hardening for threat A13; no product metric or SLO moves, and latency is already covered by E1-05/E1-08 |
| Depends on | E1-05 |
| ADRs | 005, 014 |
| Design spec | none |

## Why

The tunnel makes the API public. Threat A13 in `docs/security.md` covers three problems: oversized request bodies can exhaust the home server, the interactive docs and the schema show attackers every endpoint, and stack traces in error responses leak internals.

## Acceptance criteria

- [ ] A global request-body size limit, set in config with a documented default. Larger bodies are rejected with 413 as an RFC 9457 problem document before the body is fully read. The limit also applies to chunked requests that have no `Content-Length`.
- [ ] In tunnel mode, `/docs`, `/redoc` and `/openapi.json` return 404. This uses the same tunnel-mode setting as E1-08; whichever card lands first adds it. Outside tunnel mode (local development) they keep working.
- [ ] Every unhandled exception returns a generic RFC 9457 500 with no stack trace, exception message or file path. The full error goes only to the server log, with the trace id.
- [ ] Tests:
  - [ ] Unit: the error handler hides details.
  - [ ] Integration: an oversized body gives 413, including a chunked body; docs give 404 with tunnel mode on and 200 with it off.
  - [ ] Contract: 413 and 500 are documented as problem documents.

## Allowed files

- `contracts/openapi.yaml`, `apps/api/core/**`, `apps/api/main.py`, `apps/api/tests/**`

## Out of scope

- Rate limits (E1-08). Cloudflare-side rules. Upload limits for media (E6 sets its own).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27: amended from E1-01 threat model (docs/security.md), threat A13. It gates the E1 demo (E1-16).
- Numbers:
- Left for later:
