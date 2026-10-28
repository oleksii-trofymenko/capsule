# E1-07 · Sign-up and sign-in API (accounts)

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] Contract first: sign-up and sign-in operations in `contracts/openapi.yaml`. Neither takes an idempotency key (owner, 2026-10-28; see Notes). The optional guest credential is added by E1-07c.
- [x] Sign-up takes an email, a password (rules from ADR-014) and `age_confirmed: true`. Without the age confirmation it returns 422. The server stores only the confirmation time, never a birth date.
- [x] Emails are normalised (E1-07a) before the uniqueness check. Passwords are hashed through the E1-07a hasher and never logged or returned. A hash that needs rehashing is updated on sign-in.
- [x] A7 (`docs/security.md`): sign-up with an email that is already registered returns a conflict problem document that offers sign-in (flows.md 3a), with no other account detail. Owner signed off on this trade-off on 2026-10-27.
- [x] ADR-022 (logs): sign-up looks up the normalised email before inserting, and the A7 conflict comes from that check. The unique constraint stays as a backstop. A unique violation maps to the same conflict problem document, and its database text (which contains the email) is never logged or returned.
- [x] Wrong email or password returns the same problem document, with similar timing.
- [x] Logout revokes the account's refresh family on this device only (the E1-05c endpoint; tested with two devices).
- [x] No email, password or token in logs.
- [x] A15: security events (sign-up, sign-in, failed sign-in) are logged under the pseudonymous principal id, without email, IP or token.
- [x] Tests:
  - [x] Unit and integration (real Postgres).
  - [x] Contract.
  - [x] Happy, failure and edge paths: duplicate email in different letter case, two parallel sign-ups with the same email (one 409), missing age confirmation.
  - [x] Schemathesis (ADR-025): the fake gains `sign_up` and `sign_in` with the real signatures; no argon2 in the fake.
  - [x] p95 and p99 measured on an isolated stack against the password-endpoint SLO.
- [x] Fixtures use made-up emails on a reserved domain (`example.com`) only.
- [x] Hashing uses the E1-07a path (semaphore, 503 with `Retry-After`), outside any transaction; the hasher 503 is in the contract.

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
  - 2026-10-28 (PR #40): the password is bounded at 512 characters as sent (contract and schemas) and 12–128 code points after NFC (ADR-014). On sign-in, over 128 after NFC gets the same 401 with no hash; that difference depends only on the caller's own input.
  - 2026-10-28: an unknown or invalid email runs the same indexed lookup (an invalid one as `""`) and a dummy verify. Lookup, hash and write are separate steps: no hash runs while a transaction or connection is held (tested via the pool).
  - 2026-10-28: the A7 409 is `urn:capsule:problem:email-registered` with no account detail. The unique-violation backstop matches SQLSTATE 23505 plus the constraint name only and never logs the database text.
  - 2026-10-28: the E1-05c lock-timeout 503 now goes through `core.ServiceBusyError`, like the hasher 503; responses unchanged.
  - 2026-10-28: rehash on sign-in is a compare-and-set on the old hash; `password_rehashed` is logged only when a row changed.
  - 2026-10-28: Schemathesis replaces "valid data accepted" for sign-up only with a check that allows 201, 409, or a 422 naming only rules JSON Schema cannot express. The contract's sign-up example must get 201.
- Numbers (PR #40):
  - Builder, isolated stack, closed loop, 50 requests per user, no rate limits: p95 / p99 ms — sign-in 120/135 (1 user), 154/179 (4), 372/391 (10); wrong password 123/129, 149/153, 372/390; sign-up 125/136, 154/159, 394/405. No 503s. Within p95 < 600 ms, p99 < 1 s.
  - Security probe: unknown, invalid, empty email and wrong password medians 92.7–94.2 ms with byte-identical 401s. 120 concurrent sign-ins: 40 × 401, 80 × 503, no 500s, pool back to 0.
  - Queries on 100,000 accounts: email lookup 0.02 ms (index `accounts_email_key`), insert 0.22 ms, rehash update 0.11 ms.
  - Tests: 371 (329 before).
  - QA (head df55bec, own stack, async client; k6 scenario not written yet): p95 / p99 ms — sign-in 147/159 (1 user), 156/162 (4), 373/417 (10); wrong password 123/136, 153/158, 372/391; sign-up 126/128, 157/159, 382/403. Throughput levels off at about 30 requests/s (4 hash slots × ~130 ms). Unknown email vs wrong password medians 115.2 / 116.1 ms over 30 alternating runs; 10/10 parallel sign-up races gave one 201 and one 409; 60 concurrent sign-ins gave about 26 × 503, all with `Retry-After: 1`, no 500s. Longest API transaction during a sign-in burst 13.7 ms (the account lookup), so no hash spans a transaction.
  - Database down: sign-up and sign-in answer 500, as guest sign-in does; filed as E1-34.
- Left for later:
  - No rate limits until E1-08: one client can keep the 4 hash slots busy or create unlimited accounts. Sign-up and sign-in must not go through the tunnel before E1-08 (E1-15 gated).
  - E1-17: re-check the password hash under a row lock in the token-issuing transaction (security review), so a sign-in racing a reset cannot keep access; reset revokes every family.
  - When the ADR-014 parameters change, regenerate `DUMMY_HASH` (the needs-rehash test fails until then).
  - Guest-data move and the deletion ledger: E1-07c.
