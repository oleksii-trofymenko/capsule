# E1-07 · Sign-up and sign-in API (accounts)

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | backend-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | API latency (password endpoints): p95 < 600 ms, p99 < 1 s; product metric: sign-up conversion (completed with E1-07c and E1-13) |
| Depends on | E1-05, E1-05c, E1-07a |
| ADRs | 014, retention ADR (E1-03) |
| Design spec | `docs/design/flows.md` (F6 step 3a, "Guest data") |

## Why

As a guest who liked a guide, I want to create an account with my email and a password, so that my guides and choices are safe if I lose or change my phone. As a returning user on a new phone, I want to sign in, so that I see my saved guides.

## Acceptance criteria

- [ ] Contract first: sign-up and sign-in operations in `contracts/openapi.yaml`. Neither takes an idempotency key (owner, 2026-10-28; see Notes). The optional guest credential is added by E1-07c.
- [ ] Sign-up takes an email, a password (rules from ADR-014) and `age_confirmed: true`. Without the age confirmation it returns 422. The server stores only the confirmation time, never a birth date.
- [ ] Emails are normalised (E1-07a) before the uniqueness check. Passwords are hashed through the E1-07a hasher and never logged or returned. A hash that needs rehashing is updated on sign-in.
- [ ] A7 (`docs/security.md`): sign-up with an email that is already registered returns a conflict problem document that offers sign-in (flows.md 3a), with no other account detail. Owner signed off on this trade-off on 2026-10-27.
- [ ] ADR-022 (logs): sign-up looks up the normalised email before inserting, and the A7 conflict comes from that check. The unique constraint stays as a backstop. A unique violation maps to the same conflict problem document, and its database text (which contains the email) is never logged or returned.
- [ ] Wrong email or password returns the same problem document, with similar timing.
- [ ] Logout revokes the account's refresh family on this device only (the E1-05c endpoint; tested with two devices).
- [ ] No email, password or token in logs.
- [ ] A15: security events (sign-up, sign-in, failed sign-in) are logged under the pseudonymous principal id, without email, IP or token.
- [ ] Tests:
  - [ ] Unit and integration (real Postgres).
  - [ ] Contract.
  - [ ] Happy, failure and edge paths: duplicate email in different letter case, two parallel sign-ups with the same email (one 409), missing age confirmation.
  - [ ] Schemathesis (ADR-025): the fake gains `sign_up` and `sign_in` with the real signatures; no argon2 in the fake.
  - [ ] p95 and p99 measured on an isolated stack against the password-endpoint SLO.
- [ ] Fixtures use made-up emails on a reserved domain (`example.com`) only.
- [ ] Hashing uses the E1-07a path (semaphore, 503 with `Retry-After`), outside any transaction; the hasher 503 is in the contract.

## Allowed files

- `contracts/openapi.yaml`
- `apps/api/modules/auth/**`, `apps/api/core/**`, `apps/api/migrations/**`, `apps/api/main.py`
- `apps/api/tests/**`

## Out of scope

- The hasher and password rules (E1-07a). Guest-data move and deletion ledger (E1-07c).
- Email verification, password reset and any email sending (owner decision; reset is E1-17).
- Rate limits (E1-08). Mobile screens (E1-13). Social sign-in.

## Analytics events

- none server-side. The app sends `signup_completed` and `signin_completed` (E1-13).

## Notes (filled while working)

- Plan approved: 2026-10-28 (Orchestrator), from the backend-engineer E1-07 plan, part B.
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: email and password only. E1 sends no email: no verification and no reset (reset is E1-17, before external beta).
  - 2026-10-27, owner: a self-declared "I'm 18 or older" checkbox at sign-up. The API rejects sign-up without it.
  - 2026-10-27, owner: accounts are never deleted automatically. Guest data is deleted 30 days after last activity, so a guest who signs up after that starts empty.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md).
  - 2026-10-28: split for size (~1,700 lines planned) into E1-07a (hasher and rules), E1-07 (endpoints, this card) and E1-07c (deletion ledger and guest-data move).
  - 2026-10-28, owner: sign-up takes no idempotency key, like guest, refresh and logout. A stored replayable response would hold raw tokens (A4). A retry after a lost 201 gets 409 and the app signs in with the same password; the guest data has already moved.
  - 2026-10-28, owner: password endpoints get their own SLO, p95 < 600 ms, p99 < 1 s (`docs/metrics.md`).
  - 2026-10-28: the A7 conflict uses a fixed problem `type` the app keys on. The access-token issuer takes the principal kind instead of hardcoding `guest`.
- Numbers:
- Left for later:
