# E8-02 · Mobile: connection pinning and release-bundle secret scan

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Secrets in repository = 0 (extended to the shipped app bundle by this card) |
| Depends on | E8-01 |
| ADRs | 003, 014; a new ADR for the pinning library (not named in blueprint §4) |
| Design spec | none (no new screens; the existing connection-error copy is reused) |

## Why

As a user on public Wi-Fi, I want the app to refuse to talk to anything but the real Capsule server, so that my session cannot be intercepted. As the owner, I want proof that no secret or internal URL ships inside the app bundle. This card covers threats P4 and P5 in `docs/security.md`; E8-01 covers T5 and R7.

## Acceptance criteria

- [ ] P4 (`docs/security.md`): this card ends the E1 accepted risk and the deviation from blueprint §10 ("certificate pinning for the API"). A man-in-the-middle with a rogue CA installed on the device cannot read or change API traffic.
- [ ] The release build pins the API connection for the E8-01 domain, with at least one backup pin and a documented rotation plan, so a certificate change cannot lock every user out. Debug builds can turn pinning off.
- [ ] A pin mismatch shows the existing connection-error state and never falls back to an unpinned request.
- [ ] P5 (bundle scan per blueprint §10): a CI step scans the built JS bundle (and native config) for secrets, private keys, tokens and internal hostnames, and fails the build on a hit. Only non-secret `EXPO_PUBLIC_*` values may appear.
- [ ] Tests: a unit test for the pin config; a manual check through an intercepting proxy whose CA is installed and trusted on the test device (the request is refused), recorded in Numbers; the CI scan run on a seeded fake secret fails as expected.

## Allowed files

- `apps/mobile/**` (except `CLAUDE.md`), `.github/workflows/ci.yml` (mobile jobs only), `docs/adr/0xx-*.md`, `docs/adr/README.md`, `docs/runbooks/mobile-pinning.md` (new)

## Out of scope

- The named tunnel and domain (E8-01). Store submission (later E8 cards).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27: amended from E1-01 threat model (docs/security.md). Split from the requested single E8-01 because platform and mobile work together are over M.
- Numbers:
- Left for later:
