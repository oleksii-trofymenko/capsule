# E1-13 · Mobile: sign-up, sign-in and logout screens (A2)

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | mobile-engineer |
| Reviewers | code-reviewer, security-engineer, product-designer |
| Estimate | M |
| Metric | Sign-up conversion (guests who create an account within 7 days of their first guide) |
| Depends on | E1-07, E1-07c, E1-11, E1-12, E1-20 |
| ADRs | 003, 014 |
| Design spec | A2 from E1-11 (`docs/design/auth-and-privacy-wireframes.md`) |

## Why

As a guest, I want to create an account from the menu, so that my data is kept with an account. As a returning user on a new phone, I want to sign in, so that I get my guides back.

## Acceptance criteria

- [ ] A2 sign-up and sign-in are built to the E1-11 spec and copy deck: email, password with show/hide, and the required "I'm 18 or older" checkbox. The submit button is disabled until it is ticked.
- [ ] Sign-up and sign-in send the guest credential, so guest data moves to the account (E1-07c). On success the account tokens replace the guest credential in secure-store, and the guest credential is gone from the device.
- [ ] "Email already registered" switches to sign-in with the email kept.
- [ ] Loading, error, rate-limited (429 with `Retry-After`) and offline states, as specified.
- [ ] Logout revokes on the server, then wipes secure-store and MMKV (ADR-003), and the app starts again as a new guest. If the server is unreachable, the app still wipes locally, and the card notes this risk.
- [ ] Accessibility: labels, focus order, error announced, password managers can autofill (`textContentType`/`autoComplete`), Dynamic Type at 200%.
- [ ] Tests:
  - [ ] Jest + RNTL for each state.
  - [ ] A Maestro flow `e2e/auth.yaml`: guest → sign up → logout → sign in. It uses a made-up `@example.com` email.

## Allowed files

- `apps/mobile/app/**`, `apps/mobile/features/profile/**`, `apps/mobile/shared/**`
- `apps/mobile/e2e/**`, `apps/mobile/**/__tests__/**`

## Out of scope

- Password reset (E1-17 and its mobile follow-up). A1 save sheet and the return banner (E3). Social sign-in.

## Analytics events

All go through `track()` from E1-12.

- `signup_started` — A2 sign-up opened — `source`: menu (save_sheet, return_banner and inline_link come in E3).
- `signup_completed` — account created — `source`; `guest_guides_moved`.
- `signin_completed` — sign-in succeeded — `source`: menu | signup_conflict; `guest_guides_moved`. Defined in flows.md by E1-11.

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
- Numbers:
- Left for later:
