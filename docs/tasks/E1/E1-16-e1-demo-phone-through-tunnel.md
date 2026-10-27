# E1-16 · E1 demo: sign up and sign in through the tunnel

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | qa-engineer |
| Reviewers | code-reviewer |
| Estimate | S |
| Metric | n/a — verification card; it proves the E1 demo and records numbers for the epic report |
| Depends on | E1-08, E1-13, E1-14, E1-15, E1-22, E1-26 |
| ADRs | 016 |
| Design spec | A2 and S1 from E1-11 |

## Why

E1 ends with a demo (`docs/tasks/README.md`): the app on an Android emulator and an iOS Simulator signs up and signs in against the home PC through the tunnel. This card checks it end to end and records numbers, so the epic report is based on evidence.

## Acceptance criteria

- [ ] On an Android emulator (Windows PC) and an iOS Simulator (laptop), each using the public tunnel URL (never localhost or the LAN), against `make up` plus the quick tunnel (owner decision 2026-10-27: no physical phone, no paid Apple account):
  - [ ] Silent guest start.
  - [ ] Sign up with a made-up `@example.com` email and the 18+ checkbox.
  - [ ] Logout, then sign in.
  - [ ] Delete my data, then the app is a guest again.
  - [ ] Repeated wrong passwords get a 429.
  - [ ] Through the public URL, `/docs` and `/openapi.json` return 404, and an oversized request body is rejected with a problem document (E1-22).
- [ ] Recorded numbers: p50/p95 latency of guest issue, sign-up, sign-in and refresh through the tunnel (≥ 20 requests each), compared with the same calls on the LAN. App cold start on the Android emulator (indicative only; the release-build cold-start SLO needs a real device later).
- [ ] The Maestro flow from E1-13 passes on at least the Android emulator. If it cannot run through the tunnel, the reason is noted.
- [ ] The DB holds no leftover data from the demo account after deletion (SQL check, output in the card).
- [ ] R10 (`docs/security.md`): at the demo, security-engineer reviews the accepted risks (P3, P4, T1, T4, T5, A3, A7, A9, A11, A14, D4) and records the outcome in this card.
- [ ] Tests: this card is the test. Results go into this card's Numbers section.

## Allowed files

- `docs/tasks/E1/E1-16-e1-demo-phone-through-tunnel.md`, `apps/mobile/e2e/**` (fixes to flows only)

## Out of scope

- Fixing bugs found here. File them as cards. Load testing (E7).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md). Now depends on E1-22 (API edge hardening).
- Numbers:
- Left for later:
