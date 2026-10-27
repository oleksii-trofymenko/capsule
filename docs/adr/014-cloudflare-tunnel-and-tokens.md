# ADR-014: Cloudflare quick tunnel, opaque guest credential, HS256 access JWT with rotating refresh tokens

- Status: accepted (2026-10-27)
- Date: 2026-10-27
- Deciders: Orchestrator, security-engineer, project owner
- Related: E1-02, E1-05, E1-07, E1-08, E1-12, E1-13, E1-15, E1-17, E8-01; ADR-003, ADR-015, ADR-022 (retention, deletion ledger), ADR-023 (auth libraries); `docs/security.md` (P1, P3, A1–A9, A15, H2, R2–R8); `docs/design/flows.md` F6

## Context

E1 opens the API on the home PC to the internet for the first time. A phone has to prove who it is twice over: as a guest, who has no personal data and appears silently on first launch, and as an account holder with email and password. Guest data must be able to move to an account (flows.md F6). Owner decisions from 2026-10-27:

- Email and password only. E1 sends no email; reset and verification come in E1-17.
- The E1 demo runs on a free quick tunnel (trycloudflare). A domain comes in E8.
- Guest data is deleted 30 days after last activity (ADR-022).
- Budget is €0.
- The host has 32 GB RAM, shared with GPU inference and CPU work (STT, embeddings).

One API process both signs and verifies tokens. The worker never verifies them. Secure-store values on the phone are capped at about 2 KB (ADR-003).

## Options

1. **Opaque guest credential + 10-minute HS256 access JWT + opaque rotating refresh tokens with a single-use 30 s grace rule + argon2id (chosen).**
   - Pros: a stable proof for the guest-data move. Refresh tokens are not signed, so rotating the signing key logs nobody out. One signing secret. The JWT carries the principal id, so a request needs only one primary-key read of the principal row, which also makes deletion take effect at once.
   - Cons: after logout or reuse detection, an access token keeps working until `exp` (10 minutes at most) as long as its principal exists. A stolen guest credential works as a bearer until the guest expires (accepted, P1 and A9).
2. **Guest credential = a long-lived refresh token, EdDSA access JWT.** Lost: a rotating token cannot anchor the guest-data move, and a lost refresh response would cut the guest off from their data. EdDSA needs `cryptography` and protects nothing extra with a single verifier.
3. **Opaque server-side sessions only (no JWT).** Pros: logout and reuse detection revoke at once. Lost: every request needs a session-row read on top of the principal read. Sliding expiry adds writes. Blueprint §4 names JWT. A 10-minute JWT bounds the gap.
4. **Refresh rotation without a grace window, or a grace window that replays the earlier response.** No window: a dropped mobile response revokes the family and logs the user out. Replay: needs the raw token stored, which breaks hash-only storage (A4).
5. **bcrypt for passwords.** Lost: it truncates at 72 bytes and is not memory-hard.

## Decision

The phone holds an opaque guest credential and, after any sign-in, an opaque rotating refresh token, both only in `expo-secure-store`; the API authenticates requests with 10-minute HS256 access JWTs checked against the principal row, stores only hashes of credentials, refresh tokens and passwords, and is reachable only through a cloudflared quick tunnel to `api:8000`, following the rules below.

### Rules

**Guest credential**
- 256 random bits, base64url (43 characters). The server keeps a SHA-256 hash.
- `POST /v1/auth/guest` without a body creates a guest principal and returns the credential plus a token pair. No IP, device id, email or analytics id is stored.
- `POST /v1/auth/guest` with the credential returns a new token family for the same guest.
- Rejected with the same 401 as an unknown credential when the guest's `last_activity_at` is older than the configured ADR-022 retention (upper bound 30 days; a shorter retention shortens the credential's life too), even if the purge (E1-10) has not run yet.

**Access token**
- `alg` HS256 only; the allow-list is fixed in code.
- Header: `kid` and `typ`, both required.
  - `kid` is looked up by exact match in the configured key set, with no fallback key.
  - `typ` is checked explicitly to equal `at+jwt`.
- Claims, all required: `iss=capsule-api`, `aud=capsule-mobile`, `sub` (random principal id), `kind` (`guest` | `account`), `iat`, `exp`, `jti`. Lifetime 10 minutes, no leeway.
- Every request loads the principal row by `sub`. A missing principal returns 401.
- Authorisation, guest versus account included, comes from the principal row, never from the `kind` claim.
- The token is not checked against its refresh family.
- Every verification failure returns the same 401 problem document (R5).
- Any future JWT type gets its own signing key, or its own `aud` and `typ`.

**Refresh token**
- 256 random bits, opaque, SHA-256 hash stored.
- One family per sign-in or guest session.
- Idle limit 30 days (since the family's last refresh). Absolute limit 90 days (since the family was created). Owner decision, 2026-10-27.
- Each token has a state: `current`, `rotated` or `superseded`. Every hash of a live family is kept until the family ends (ADR-022).
- `POST /v1/auth/refresh`:
  1. Find the family by the token hash. An unknown hash returns 401 and revokes nothing.
  2. Lock the family row (`SELECT … FROM refresh_families … FOR UPDATE`) before reading any token state.
  3. A revoked or expired family returns 401.
  4. The family's `current` token rotates: it becomes `rotated` (keeping its first rotation time) and a new `current` successor is issued.

**Grace rule (R6), the only exception to reuse detection**
- A `rotated` token may be presented again only when all of these hold:
  - its direct successor is still the family's `current` token (never used);
  - no more than 30 s have passed since that token was first rotated;
  - grace has not been used for that token before.
- The server then marks the successor `superseded`, issues a new `current` successor, marks grace as used for the presented token, and logs an A15 event.
- Any other known token of the family that is not `current` (a `rotated` token outside the rule, a `superseded` token, a second grace attempt) revokes the whole family and returns 401, with an A15 event.
- Client side (E1-12): one refresh in flight at a time, a 15 s timeout, one retry.

**Logout**
- `POST /v1/auth/logout` takes the refresh token and revokes the family it belongs to (this device only).
- It returns the same success response for an unknown or already revoked token.
- "Sign out everywhere", and revoking every family on password reset, come in E1-17.
- Offline logout leaves the family alive until it expires (P3, accepted).

**Guest-data move**
- Happens only inside the sign-up or sign-in request that presents both a valid guest credential and the new account session.
- One transaction, with the guest credential row locked (R3).
- The transaction moves the guest-owned rows, then **deletes** the guest principal, its credential and its refresh families, and writes the guest principal id to the deletion ledger (ADR-022).
- Never matched by email, device or analytics id.
- If any step fails, nothing moves and nothing is deleted.

**Passwords**
- argon2id: m = 65536 KiB (64 MiB), t = 3, p = 1, 16-byte salt, 32-byte hash.
- Order of operations: rate limits first (R8). Then an `asyncio.Semaphore` with 4 slots, acquired with a 1 s timeout. Only then is the hash offloaded to a worker thread.
- If the semaphore times out, the API returns 503 with `Retry-After` and no hash runs.
- Peak hashing memory is therefore about 256 MiB.
- Unknown emails are verified against a dummy hash through the same path (A6). `check_needs_rehash` runs on sign-in.

**Password rules**
- Minimum 12 and maximum 128 code points after NFC. Any Unicode allowed, spaces included.
- No composition rules and no forced expiry.
- Rejected, case-insensitive:
  - a password on a blocklist built from a top-1,000,000 breached-password corpus, filtered to entries of 12 or more characters (a data file; source and licence recorded in E1-07);
  - "capsule";
  - the email's local part.
- The minimum of 12 is a **deliberate deviation from NIST SP 800-63B rev 4** (15 for single-factor passwords), signed off by the owner on 2026-10-27.

**Email**
- Trim, NFC, lowercase the whole address. `+tag` and dots are kept.
- At most 254 characters and a minimal syntax check (one `@`, a dotted domain). No deliverability check.

**Signing key**
- At least 32 random bytes per `kid`.
- The verifier accepts the current key and at most one previous key, for at least 10 minutes after rotation.
- Rotation logs nobody out, because refresh tokens are not signed.
- Storage, rotation cadence and the leak runbook belong to ADR-015.

**Tunnel**
- `cloudflared tunnel --url http://api:8000`. No Cloudflare account or token. Image pinned by digest (ADR-019).
- The URL goes into `EXPO_PUBLIC_API_BASE_URL` and changes on every restart, so no control depends on keeping it secret (T1).
- Only the API is reachable through it.
- For the E1 demo only, not external beta (R7). E8-01 replaces it with a named tunnel, a domain and certificate pinning.

**Libraries:** ADR-023.

## Consequences

- Easier: guests and accounts share one refresh mechanism. Deleting a principal invalidates its access tokens at once. Key rotation is invisible to users. The token on the phone is 43 characters, well under the secure-store limit.
- Harder:
  - One primary-key read per authenticated request.
  - Revocation takes effect for access tokens only at `exp` while the principal exists.
  - The refresh state machine needs these tests:
    - rotation;
    - grace inside the 30 s window, and just outside it;
    - a second grace attempt on the same token;
    - presenting the superseded successor;
    - a rotated token presented under grace while its successor rotates normally, in both orders (the family ends up revoked);
    - two concurrent refreshes with the same token.
  - Without email reset, a forgotten password after the 90-day limit or a logout goes through the contact-address erasure path until E1-17.
  - Quick tunnels have no uptime promise, cap in-flight requests at 200 and do not support Server-Sent Events.
- We will monitor:
  - reuse-detected family revocations and grace hits per day (A15 events; a rise points at token theft or a client bug);
  - hash-semaphore 503s;
  - argon2id hash time on the 9700X (target 100–300 ms; recorded in E1-07);
  - sign-in and sign-up 429s.
- Revisit when:
  - a second service must verify tokens (move to EdDSA)
  - E1-17 adds email (verification, reset, sign out everywhere, A7)
  - E3 needs streaming through the tunnel
  - E8 brings the named tunnel
  - hash time leaves 100–300 ms or competes with inference
  - NIST guidance or a store review changes the password rules
