# E1-21 · Privacy notice (en-GB draft)

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | product-designer (copy), with facts from security-engineer |
| Reviewers | code-reviewer, security-engineer, product-analyst |
| Estimate | S |
| Metric | n/a — docs only; the legal text that A2, the save sheet and Welcome link to |
| Depends on | E1-03 |
| ADRs | retention ADR (E1-03), 004, 008, 014 |
| Design spec | `docs/design/copy-deck.md` (`onb.welcome.legal`, `save.sheet.local_warning`) |

## Why

As a user, I want a plain-English explanation of what Capsule keeps about me, for how long, and how to delete it, so that I can decide whether to trust it. The copy deck and A2 already link to a "Privacy notice" that does not exist, and the owner decided that the 18+ rule must be stated there.

## Acceptance criteria

- [ ] `docs/legal/privacy-notice.md` (en-GB, plain language) covers:
  - [ ] Who we are and how to contact us.
  - [ ] What data we hold (flows.md "Guest data" list, account email) and why.
  - [ ] Legal bases.
  - [ ] Retention: guest data deleted after 30 days without use; accounts kept until you delete them; backups kept at most 30 days; media deleted within 24 h (ADR-008).
  - [ ] Deletion and export from Settings.
  - [ ] Processors: Cloudflare, plus PostHog and Sentry only when the user has consented.
  - [ ] "Capsule is for people aged 18 or older".
  - [ ] No body or appearance rating.
  - [ ] Your GDPR rights and how to complain to a supervisory authority.
- [ ] The notice gives a contact address for erasure and access requests from people who can't sign in (lost phone, forgotten password; there is no reset in E1). The address itself stays `TODO(owner)`: the owner will provide it later (decision 2026-10-27), and it must be filled before external beta.
- [ ] `docs/runbooks/erasure-requests.md` (short) explains how the owner handles such a request: how to check the request without collecting more personal data than the account already holds, how to run the E1-09 deletion for that account, the one-month GDPR deadline, and how to reply.
- [ ] Every fact matches the accepted ADRs. Anything not decided yet is marked `TODO(owner)`, never invented.
- [ ] A note that the text needs a legal check by the owner before external beta.
- [ ] Tests: none (docs). `make lint` passes.

## Allowed files

- `docs/legal/privacy-notice.md` (new), `docs/runbooks/erasure-requests.md` (new)

## Out of scope

- Terms of use. Showing the notice in the app or hosting it at a URL (E8 store listing). A cookie banner (no web app).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27, added to the approved E1 plan. The owner decided that the 18+ rule goes in the Privacy notice, and no card owned the notice.
  - 2026-10-27, owner: self-declared "I'm 18 or older"; guest data 30 days after last activity; accounts never deleted automatically; backups ≤ 30 days.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md). This card now owns the contact address for erasure requests and a short runbook for handling them. It stays S.
- Numbers:
- Left for later:
