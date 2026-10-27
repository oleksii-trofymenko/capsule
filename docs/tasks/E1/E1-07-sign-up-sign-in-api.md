# E1-07 · Sign-up, sign-in and logout API, with the move from guest to account

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Sign-up conversion (guests who create an account within 7 days of their first guide) |
| Depends on | E1-05, E1-03 |
| ADRs | 014, retention ADR (E1-03) |
| Design spec | `docs/design/flows.md` (F6 step 3a, "Guest data") |

## Why

As a guest who liked a guide, I want to create an account with my email and a password, so that my guides and choices are safe if I lose or change my phone. As a returning user on a new phone, I want to sign in, so that I see my saved guides.

## Acceptance criteria

- [ ] Contract first: sign-up and sign-in operations in `contracts/openapi.yaml`. Both accept an optional guest credential to move guest data. Sign-up accepts an idempotency key.
- [ ] Sign-up takes an email, a password (rules from ADR-014) and `age_confirmed: true`. Without the age confirmation it returns 422. The server stores only the confirmation time, never a birth date.
- [ ] Emails are normalised before the uniqueness check. Passwords are hashed as ADR-014 requires and never logged or returned.
- [ ] A7 (`docs/security.md`): sign-up with an email that is already registered returns a conflict problem document that offers sign-in (flows.md 3a), with no other account detail. The owner's sign-off on this enumeration trade-off is pending and must be recorded in Decisions before merge.
- [ ] Wrong email or password returns the same problem document, with similar timing.
- [ ] Moving guest data: when a valid guest credential comes with the request, all guest-owned rows move to the account in one transaction and the guest credential is revoked. If any step fails, nothing moves and the guest credential still works. A guest credential that is revoked or belongs to someone else moves nothing. Nothing is ever matched by email, device or analytics id.
- [ ] The response reports how many guest guides moved, which the app needs for `guest_guides_moved`. It is 0 until E3 adds guides.
- [ ] Logout revokes the account's refresh family on this device.
- [ ] R3: the guest-data move locks the guest credential row. With two parallel sign-ups or sign-ins using the same credential, one moves the data and the other moves nothing.
- [ ] No email, password or token in logs.
- [ ] A15: security events (sign-up, sign-in, failed sign-in, guest data moved) are logged under the pseudonymous principal id, without email, IP or token.
- [ ] Tests:
  - [ ] Unit and integration (real Postgres).
  - [ ] Contract.
  - [ ] Happy, failure and edge paths: duplicate email in different letter case, the move failing halfway, a reused guest credential, missing age confirmation.
  - [ ] Two parallel sign-ups with the same guest credential (R3).
- [ ] Fixtures use made-up emails on a reserved domain (`example.com`) only.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`
- `apps/api/tests/**`

## Out of scope

- Email verification, password reset and any email sending (owner decision; reset is E1-17).
- Rate limits (E1-08). Mobile screens (E1-13). Social sign-in.

## Analytics events

- none server-side. The app sends `signup_completed` and `signin_completed` (E1-13).

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: email and password only. E1 sends no email: no verification and no reset (reset is E1-17, before external beta).
  - 2026-10-27, owner: a self-declared "I'm 18 or older" checkbox at sign-up. The API rejects sign-up without it.
  - 2026-10-27, owner: accounts are never deleted automatically. Guest data is deleted 30 days after last activity, so a guest who signs up after that starts empty.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
- Numbers:
- Left for later:
