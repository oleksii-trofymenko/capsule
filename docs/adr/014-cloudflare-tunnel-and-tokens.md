# ADR-014: Cloudflare quick tunnel, opaque guest credential, HS256 access JWT with rotating refresh tokens

- Status: proposed
- Date: 2026-10-27
- Deciders: Orchestrator, security-engineer, project owner
- Related: E1-02, E1-05, E1-07, E1-08, E1-12, E1-13, E1-15, E1-17, E8-01; ADR-003, ADR-015, ADR-022 (retention), ADR-023 (auth libraries); `docs/security.md` (A1–A8, A15, P3, H2, R2–R8); `docs/design/flows.md` F6

## Context

E1 opens the API on the home PC to the internet for the first time. A phone has to prove who it is twice over: as a guest, who has no personal data and appears silently on first launch, and as an account holder with email and password. Guest data must be able to move to an account (flows.md F6). Owner decisions from 2026-10-27:

- Email and password only. E1 sends no email; reset and verification come in E1-17.
- The E1 demo runs on a free quick tunnel (trycloudflare). A domain comes in E8.
- Guest data is deleted 30 days after last activity (ADR-022).
- Budget is €0.
- The host has 32 GB RAM, shared with GPU inference and CPU work (STT, embeddings).

One API process both signs and verifies tokens. The worker never verifies them. Secure-store values on the phone are capped at about 2 KB (ADR-003).

## Options

1. **Opaque guest credential + 10-minute HS256 access JWT + opaque rotating refresh tokens with a 30 s grace rule + argon2id (chosen).** Pros: a stable proof for the guest-data move; no per-request lookup; refresh tokens are not signed, so rotating the signing key does not log anyone out; one secret to protect. Cons: an access token lives up to 10 minutes after logout or reuse detection. A stolen guest credential works as a bearer until the guest is purged (accepted, A9).
2. **Guest credential = a long-lived refresh token, EdDSA access JWT.** Lost: a rotating token cannot anchor the guest-data move, and a lost refresh response would cut the guest off from their data. EdDSA needs `cryptography` and protects nothing extra with a single verifier.
3. **Opaque server-side sessions only (no JWT).** Instant revocation. Lost: a Redis/DB lookup on every request. Blueprint §4 names JWT. Short JWTs already bound the exposure.
4. **Refresh rotation without a grace window, or a grace window that replays the earlier response.** No window: a dropped mobile response revokes the family and logs the user out. Replay: needs the raw token stored, which breaks hash-only storage (A4).
5. **bcrypt for passwords.** Lost: it truncates at 72 bytes and is not memory-hard.

## Decision

The phone holds an opaque guest credential and, after any sign-in, an opaque rotating refresh token, both only in `expo-secure-store` (ADR-003). The API issues 10-minute HS256 access JWTs, stores only SHA-256 hashes of credentials and refresh tokens and argon2id hashes of passwords, and is reachable only through a cloudflared quick tunnel to `api:8000`, with these rules:

- **Guest credential**
  - 256 random bits, base64url (43 characters).
  - `POST /v1/auth/guest` without a body creates a guest principal, with no IP, device id, email or analytics id stored, and returns the credential plus a token pair.
  - `POST /v1/auth/guest` with the credential returns a new token family for the same guest.
  - Valid until the guest principal is purged 30 days after `last_activity_at` (ADR-022, E1-10). Revoked after the guest data moves.
- **Access token**
  - JWT, `alg` HS256 only, with the allow-list fixed in code.
  - Header: `kid` and `typ: at+jwt`.
  - Claims: `iss=capsule-api`, `aud=capsule-mobile`, `sub` (random principal id), `kind` (`guest` | `account`), `iat`, `exp`, `jti`.
  - `exp`, `iat`, `iss`, `aud` and `sub` are required. Lifetime 10 minutes, no leeway.
  - Not checked against the refresh family. It stays valid until `exp`, but the principal dependency rejects tokens whose principal no longer exists.
  - Every verification failure returns the same 401 problem document (R5).
- **Refresh token**
  - 256 random bits, opaque, one family per sign-in or guest session.
  - Idle limit 30 days (since the family's last refresh). Absolute limit 90 days (since the family was created; owner decision 2026-10-27).
  - `POST /v1/auth/refresh` locks the token row (`FOR UPDATE`) and rotates on every use.
- **Grace and reuse rule (R6)**
  - Presenting a token that has already been rotated is allowed only when its direct successor has never been used and no more than 30 s have passed since that token was first rotated. The server then revokes the unused successor and issues a new one. Retries do not restart the 30 s window.
  - In every other case the server revokes the whole family and returns 401.
  - An unknown token returns 401 and revokes nothing.
  - Client (E1-12): one refresh in flight at a time, a 15 s timeout, one retry.
- **Logout:** `POST /v1/auth/logout` revokes the family on this device. "Sign out everywhere", and revoking every family on password reset, come in E1-17. Offline logout leaves the family alive until it expires (P3, accepted).
- **Guest-data move:** happens only inside the sign-up or sign-in request that presents both a valid guest credential and the new account session. One transaction, guest credential row locked (R3), credential revoked afterwards. Never matched by email, device or analytics id.
- **Passwords**
  - argon2id: m = 65536 KiB (64 MiB), t = 3, p = 1, 16-byte salt, 32-byte hash.
  - Hashing runs in a threadpool behind a semaphore of 4, so it uses at most about 256 MiB of RAM.
  - Rate limiting runs before any hash (R8). Unknown emails are checked against a dummy hash (A6). `check_needs_rehash` runs on sign-in.
- **Password rules**
  - Minimum 12 and maximum 128 code points after NFC. Any Unicode allowed, spaces included.
  - No composition rules and no forced expiry.
  - Rejected, case-insensitive: a password on an offline list of the 10,000 most common passwords (a data file with its licence recorded in E1-07), "capsule", and the email's local part.
  - The minimum of 12 is a **deliberate deviation from NIST SP 800-63B rev 4** (15 for single-factor passwords), signed off by the owner on 2026-10-27.
- **Email**
  - Trim, NFC, lowercase the whole address. `+tag` and dots are kept.
  - At most 254 characters and a minimal syntax check (one `@`, a dotted domain). No deliverability check.
- **Signing key**
  - At least 32 random bytes, chosen by `kid`.
  - During rotation the verifier accepts the current key and one previous key for at least 10 minutes. Rotation logs nobody out, because refresh tokens are not signed.
  - Storage, rotation cadence and the leak runbook belong to ADR-015.
- **Tunnel**
  - `cloudflared tunnel --url http://api:8000`. No Cloudflare account or token. Image pinned by digest (ADR-019).
  - The URL goes into `EXPO_PUBLIC_API_BASE_URL` and changes on every restart, so no control depends on keeping it secret (T1).
  - Only the API is reachable through it.
  - For the E1 demo only, not external beta (R7). E8-01 replaces it with a named tunnel, a domain and certificate pinning.
- **Libraries:** see ADR-023.

## Consequences

- Easier: guests and accounts share one refresh mechanism. Protected endpoints need no session lookup. Key rotation is invisible to users. The token on the phone is 43 characters, well under the secure-store limit.
- Harder:
  - Revocation takes effect for access tokens only at `exp` (10 minutes at most).
  - The grace rule needs careful tests: inside and just outside 30 s, and two concurrent refreshes.
  - Without email reset, a forgotten password after the 90-day limit or a logout goes through the contact-address erasure path until E1-17.
  - Quick tunnels have no uptime promise, cap in-flight requests at 200 and do not support Server-Sent Events.
- We will monitor:
  - Rate of reuse-detected family revocations (alert on spikes; a rise points at token theft or a client bug).
  - Grace-rule hits per day.
  - argon2id hash time on the 9700X (target 100–300 ms; recorded in E1-07).
  - Sign-in 429s.
- Revisit when:
  - a second service must verify tokens (move to EdDSA)
  - E1-17 adds email (verification, reset, sign out everywhere, A7)
  - E3 needs streaming through the tunnel
  - E8 brings the named tunnel
  - hash time leaves 100–300 ms or competes with inference
  - NIST guidance or a store review changes the password rules
