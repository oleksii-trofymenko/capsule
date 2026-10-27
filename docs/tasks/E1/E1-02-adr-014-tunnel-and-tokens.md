# E1-02 · ADR-014: Cloudflare Tunnel, guest credential, JWT with rotating refresh tokens

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | security-engineer (drafts with the `adr` skill); the owner accepts |
| Reviewers | code-reviewer, backend-engineer (feasibility) |
| Estimate | S |
| Metric | Decisions on record (every stack choice has an accepted ADR) |
| Depends on | E1-01 |
| ADRs | 014 (planned → accepted); may need a dependency section or a separate ADR for the auth libraries |
| Design spec | `docs/design/flows.md` (F6 "Guest data") |

## Why

Auth endpoints, the app's session handling and the tunnel all depend on one decision about how a phone proves who it is, as a guest and as an account holder, and how the home server is reached. ADR-014 has been `planned` since E0.

## Acceptance criteria

- [ ] `docs/adr/014-*.md` is written from `000-template.md`, with alternatives considered, and accepted by the owner. It decides:
  - [ ] Guest credential: what it is, how it is issued, how long it lasts, and that it lives only in `expo-secure-store` (ADR-003).
  - [ ] Access token format and lifetime; refresh token lifetime; rotation on every use; reuse detection, where a replayed refresh token revokes the whole family; logout and revocation.
  - [ ] Moving guest data to an account happens in one request that presents the guest credential and the new account session together. The guest credential is revoked afterwards. Guest data is never matched by email, device or analytics id (flows.md).
  - [ ] Password storage (algorithm and parameters) and the password rules, with no email sending in E1 (see Decisions).
  - [ ] Signing-key handling, with storage deferred to ADR-015.
  - [ ] Tunnel: a free quick tunnel (trycloudflare) for E1, with the URL set through env. A named tunnel and a domain come in E8 (see Decisions). Only the API is reachable through it.
  - [ ] Libraries. JWT and password-hashing libraries are not named in blueprint §4, so the ADR names them (7-day rule, ADR-018/019) or links a separate dependency ADR.
- [ ] `docs/adr/README.md` index row updated.
- [ ] Tests: none (docs). `make lint` passes.

## Allowed files

- `docs/adr/014-*.md`, `docs/adr/README.md` (index row only), and a separate `docs/adr/0xx-*.md` only if the libraries get their own ADR

## Out of scope

- Implementation (E1-05, E1-07, E1-12, E1-15). Secrets storage (ADR-015, E1-04). Retention periods (E1-03).
- Social sign-in (Apple, Google) and passkeys.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: sign-up uses email and password. E1 sends no email at all: no verification and no password reset. Password reset with a free-tier email service is card E1-17 (before external beta).
  - 2026-10-27, owner: the E1 demo uses a free quick tunnel (trycloudflare), with the URL set through env. Buying a domain is deferred to E8.
  - 2026-10-27, owner: retention. Guest data is deleted 30 days after last activity, accounts are never deleted automatically, and Postgres backups are kept for at most 30 days. The retention ADR (E1-03) records this; ADR-014 links to it for token and session lifetimes.
  - 2026-10-27, owner: at sign-up the user ticks a self-declared "I'm 18 or older" checkbox, and the Privacy notice states the same rule. ADR-014 needs no age verification beyond this.
- Numbers:
- Left for later:
