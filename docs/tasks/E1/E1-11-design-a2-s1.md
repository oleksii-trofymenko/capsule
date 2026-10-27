# E1-11 · Design: A2 sign-up and sign-in, S1 Settings → Privacy, text field component

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | product-designer |
| Reviewers | code-reviewer, product-analyst (events), security-engineer (error wording vs account enumeration) |
| Estimate | M |
| Metric | Sign-up conversion (guests who create an account within 7 days of their first guide) |
| Depends on | E1-02, E1-03 |
| ADRs | 014, retention ADR (E1-03) |
| Design spec | this card produces it |

## Why

As a guest, I want signing up to be quick and clear, so that I keep my guides without friction. As any user, I want to find "Delete my data" and "Download my data" easily. flows.md sets only the entry and exit for A2 and the requirements for S1. Mobile cannot build a screen without an approved spec, and components.md has no text field.

## Acceptance criteria

- [ ] A2 spec (wireframe and states):
  - [ ] Sign-up: email, password with show/hide, the "I'm 18 or older" checkbox (required; it links to the Privacy notice), and the Terms/Privacy links.
  - [ ] Sign-in.
  - [ ] Switching between them; "email already registered → sign in" (flows.md 3a).
  - [ ] Loading, error, offline and rate-limited (429) states.
  - [ ] Entry from the menu (`source` = `menu`).
  - [ ] Copy says plainly that there is no password reset yet (owner decision). Wording is checked with the owner.
- [ ] S1 layout: the two consent switches, Download my data, Delete my data (F10 flow), sign-in/logout entry, and the offline state.
- [ ] `components.md` gains a text field (default, focus, error, disabled, secure entry, a11y labels, Dynamic Type) and the components A2/S1 need that are still missing. Every spec meets WCAG AA and the 48 dp touch-target rule.
- [ ] `copy-deck.md` gains every new en-GB string for A2, S1 and the errors. Auth errors never reveal whether an email exists beyond what E1-01/E1-07 decide.
- [ ] `flows.md` Analytics table gains `signin_completed` — fires when sign-in succeeds — `source`: menu | signup_conflict; `guest_guides_moved`. The `signup_started` / `signup_completed` sources list `menu` for E1.
- [ ] Tests: none (design). `make lint` passes.

## Allowed files

- `docs/design/flows.md`, `docs/design/components.md`, `docs/design/copy-deck.md`, `docs/design/auth-and-privacy-wireframes.md` (new)

## Out of scope

- A1 save sheet and the return banner. They need guides, so they come in E3.
- Onboarding screens (E3). The Privacy notice text (E1-21). Password reset screens (E1-17 follow-up).

## Analytics events

- Defines `signin_completed` (above). It does not change the existing events except listing sources.

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: email and password. E1 has no email verification and no password reset, so A2 copy must not promise either.
  - 2026-10-27, owner: a self-declared "I'm 18 or older" checkbox at sign-up. The Privacy notice states the same rule (E1-21).
  - 2026-10-27, owner: guest data is deleted 30 days after last activity; `{retention_days}` = 30 in copy examples. Accounts are never deleted automatically.- Numbers:
- Left for later:
