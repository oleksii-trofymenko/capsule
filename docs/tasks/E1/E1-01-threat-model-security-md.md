# E1-01 · Threat model and `docs/security.md`

| Field | Value |
| --- | --- |
| Status | todo |
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

- [ ] `docs/security.md` exists, with:
  - [ ] Assets: guest credential, access/refresh tokens, account email and password hash, consultation data (flows.md "Guest data"), media (ADR-008), secrets.
  - [ ] Trust boundaries and data flow: phone → Cloudflare Tunnel → API → Postgres/Redis/SeaweedFS; admin UIs never through the public tunnel.
  - [ ] Threats per boundary (STRIDE or similar), each with a mitigation and the E1 card that owns it, or "accepted risk" with a reason. It must cover at least: credential stuffing and brute force, guest-credential farming, token theft and replay (refresh reuse), account enumeration on sign-up/sign-in, guest-data takeover during the move to an account, client-IP spoofing behind the tunnel, and the risk of quick-tunnel URLs leaking.
  - [ ] An OWASP API Security Top 10 (2023) checklist that maps each item to a control or card.
  - [ ] A data policy section: which columns hold personal data, whether each is encrypted at rest, and where logs must not contain them (no email, password, token or IP in logs at INFO level). Retention rules are a placeholder here, filled in by E1-03.
- [ ] The open choices it raises for ADR-014 (token lifetimes, reuse detection, hashing parameters) and for ADR-015 are listed as inputs, not decided here.
- [ ] Tests: none (docs). `make lint` passes.
- [ ] Docs: `docs/security.md` is linked from `docs/blueprint.md` §5 only if the path differs (it should not).

## Allowed files

- `docs/security.md`

## Out of scope

- Writing ADR-014, ADR-015 or the retention ADR (E1-02, E1-04, E1-03).
- Any code or config change.
- Penetration testing.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
- Numbers:
- Left for later:
