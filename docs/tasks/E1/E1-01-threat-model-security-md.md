# E1-01 · Threat model and `docs/security.md`

| Field | Value |
| --- | --- |
| Status | done |
| Owner | security-engineer |
| Reviewers | code-reviewer |
| Estimate | M |
| Metric | n/a — docs only; it is the input to ADR-014, ADR-015 and the retention ADR |
| Depends on | none |
| ADRs | 003, 004, 008 (existing); informs 014, 015 and the retention ADR (E1-03) |
| Design spec | `docs/design/flows.md` (F6 "Guest data", F10) |

## Why

E1 opens the API to the internet through a tunnel and starts holding accounts. Before any auth code, we need one page that names what we protect, from whom, and the rules every later card checks against. `docs/security.md` is already referenced by the security-engineer agent and the `db-migration` skill but does not exist yet.

## Acceptance criteria

- [x] `docs/security.md` exists, with:
  - [x] Assets: guest credential, access/refresh tokens, account email and password hash, consultation data (flows.md "Guest data"), media (ADR-008), secrets.
  - [x] Trust boundaries and data flow: phone → Cloudflare Tunnel → API → Postgres/Redis/SeaweedFS; admin UIs never through the public tunnel.
  - [x] Threats per boundary (STRIDE or similar), each with a mitigation and the E1 card that owns it, or "accepted risk" with a reason. It must cover at least: credential stuffing and brute force, guest-credential farming, token theft and replay (refresh reuse), account enumeration on sign-up/sign-in, guest-data takeover during the move to an account, client-IP spoofing behind the tunnel, and the risk of quick-tunnel URLs leaking.
  - [x] An OWASP API Security Top 10 (2023) checklist that maps each item to a control or card.
  - [x] A data policy section: which columns hold personal data, whether each is encrypted at rest, and where logs must not contain them (no email, password, token or IP in logs at INFO level). Retention rules are a placeholder here, filled in by E1-03.
- [x] The open choices it raises for ADR-014 (token lifetimes, reuse detection, hashing parameters) and for ADR-015 are listed as inputs, not decided here.
- [x] Tests: none (docs). `make lint` passes.
- [x] Docs: `docs/security.md` is linked from `docs/blueprint.md` §5 only if the path differs (it should not).

## Allowed files

- `docs/security.md`

## Out of scope

- Writing ADR-014, ADR-015 or the retention ADR (E1-02, E1-04, E1-03).
- Any code or config change.
- Penetration testing.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator). security-engineer drafted the full text; the Orchestrator wrote it to disk because the agent has no write tools.
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - Threats with no owning card get new owners: E1-22 API edge hardening (body size, docs off in tunnel mode, no stack traces), E1-23 backups (encrypted, kept at most 30 days), a pre-beta encryption card (fields, host disk, media keys for ADR-008), and an E8 named-tunnel card (named tunnel, domain, pinning, bundle scan).
  - A7 sign-up enumeration: accepted with per-IP limits. Conflict problem document offers sign-in, with no other detail. Owner sign-off pending.
  - Erasure without a password: manual request through the E1-21 contact address until E1-17 ships.
- Numbers: `docs/security.md` is about 230 lines: 5 boundaries, 33 threats (11 accepted, listed in R10), OWASP 10/10 mapped, 10 rules (R1–R10). Review: code-reviewer requested changes (1 blocker, 7 suggestions), all fixed, then approved. `make lint` passes.
- Left for later:
  - Follow-up cards PR: file E1-22, E1-23, the pre-beta encryption card and the E8 named-tunnel card. Add to acceptance criteria: R1, R2 and D5 to E1-08; R3 and A15 to E1-07; A4, R4, R5, R6 and A15 to E1-05; R6 to E1-12; the peer-identification part of R2 to E1-15.
  - Owner sign-off on A7.
