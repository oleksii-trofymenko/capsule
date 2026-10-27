# Security: threat model, OWASP checklist, data policy

| Field | Value |
| --- | --- |
| Status | E1 baseline, written in E1-01 (2026-10-27) |
| Owner | security-engineer |
| Feeds | ADR-014 (E1-02), ADR-015 (E1-04), retention ADR (E1-03) |
| Read with | `docs/design/flows.md` (F6 "Guest data", F10), ADR-003, ADR-004, ADR-008 |

This page says what Capsule protects, who from, and which card owns each control. Reviewers (`security-check` skill, `db-migration` skill, code-reviewer) check changes against it. If an accepted ADR disagrees with this page, the ADR wins and this page gets updated.

## 1. Scope and decisions it rests on

E1 opens the API to the internet for the first time and starts holding accounts. In scope: the mobile app, the tunnel, the API, Postgres, Redis, SeaweedFS, the home PC and CI. Consultation, media upload and LLM threats are noted where they shape an E1 rule. Each later epic adds its own rows.

Owner decisions (2026-10-27):

- Sign-in is email + password. E1 sends no email: no verification and no reset. Reset is E1-17, before external beta.
- E1 uses a free Cloudflare quick tunnel (trycloudflare), with the URL set through env. A named tunnel and a domain come in E8.
- Guest data is deleted 30 days after last activity. Accounts are never deleted automatically. Backups are kept for at most 30 days.
- 18+ is a self-declared checkbox. The server stores only the confirmation time.
- Budget is €0: no paid vault, WAF, email service or monitoring.

## 2. Assets

| Asset | Where it lives | Why it matters |
| --- | --- | --- |
| Guest credential | Phone: `expo-secure-store` only (ADR-003). Server: its hashed record, deleted by the guest-data move, "Delete my data" or the retention purge (ADR-014 has no revocation) | Holds all of a guest's consultation data. Stealing it means taking that data over |
| Access token | Phone memory and secure-store; request headers | Short-lived bearer. Theft = acting as the user until it expires |
| Refresh token and its family | Phone secure-store; server keeps a hash and the family state | Long-lived. Theft = a lasting session unless reuse detection fires |
| Account email | Postgres | Personal data and the sign-in identifier |
| Password hash | Postgres | Offline cracking leads to credential reuse elsewhere |
| 18+ confirmation time | Postgres | Evidence of the age gate. Not sensitive in itself |
| Consultation data | Postgres, from E3 (flows.md "Guest data": requests, voice transcripts, garments found in photos, follow-up answers, guides, wardrobe/style/sizes choices) | Personal data. A wardrobe and sizes profile |
| Media (photos, voice) | SeaweedFS bucket, from E6 (ADR-008) | Highest sensitivity. May show faces, homes, bodies |
| Rate-limit keys | Redis | Built from client IP and email, so they are personal data |
| Secrets | `.env` on the host (written by `make up`): `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SEAWEEDFS_JWT_SIGNING_KEY`, `SEAWEEDFS_JWT_FILER_SIGNING_KEY`, JWT signing keys from E1-05 | Any one of them opens a data store or lets someone forge sessions |
| S3 access key ID (identifier; ADR-024) | `.env` (`SEAWEEDFS_S3_ACCESS_KEY`); sent in clear in every SigV4 request and presigned URL; one SeaweedFS startup log line | Useless without the secret key. Never reused as secret material |
| S3 secret key (secret) | `.env` (`SEAWEEDFS_S3_SECRET_KEY`) | Signs any S3 request: full access to media |

## 3. Trust boundaries and data flow

```text
 [B1] Phone (Expo app)
   | secure-store: guest credential / tokens      MMKV: cache only, no credentials
   | HTTPS, URL from EXPO_PUBLIC_* (changes on every cloudflared restart)
   v
 [B2] Cloudflare edge  *.trycloudflare.com  (TLS ends here; Cloudflare is a processor)
   | outbound-only tunnel started by cloudflared (no inbound router ports)
   v
 ---------------------------- Home PC (Docker) ---------------------------------
   cloudflared (compose.tunnel.yml, E1-15) --> api:8000 only
                                               |
 [B3] api  (networks: edge + backend; also published on 127.0.0.1:${API_HOST_PORT:-8000} for the host)
   |  auth, validation, rate limits, delete/export
   |  network "backend" (internal: true -- no route to host or internet)
   v
 [B4] postgres:5432        redis:6379 (requirepass)     seaweedfs
      (pg_data volume)     (redis_data volume, AOF)     S3 API :8333 (signed requests)
                                                         S3 gRPC :18333 (filer-key JWT)
                                                         master/volume/filer bound to
                                                         127.0.0.1 inside the container
                                                         seaweed_data: never backed up
 --------------------------------------------------------------------------------
 [B5] Host and operations: .env, Docker volumes, logs (driver "local", 10 MB x 3),
      Postgres backups (E1-23), GitHub Actions CI, developer laptop
```

Boundary rules:

- Only `api` is reachable through the tunnel. Postgres, Redis, SeaweedFS and any admin UI (Grafana, Langfuse, later) never go through the public tunnel. Admin access is from the host, or later through Cloudflare Access or Tailscale (E2/E8).
- `api` is the only service on `edge`. Data services are only on `backend`.
- The API treats the tunnel URL as public. No control depends on keeping it secret.

## 4. Threats per boundary

STRIDE: S spoofing, T tampering, R repudiation, I information disclosure, D denial of service, E elevation of privilege.

### B1: Phone

| # | Threat | STRIDE | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| P1 | Token or guest credential read from plain storage, backups, logs or Sentry breadcrumbs | I | Credentials only in `expo-secure-store`, `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`, through `shared/storage`. Nothing in MMKV, logs or breadcrumbs. Both stores excluded from OS backup | E1-18, E1-12 (ADR-003) |
| P2 | Leftover Keychain items after a reinstall give the next user an old session | I/S | First launch after install wipes secure-store and MMKV | E1-18, E1-12 |
| P3 | Logout while offline leaves a live refresh family on the server | S | App wipes locally anyway. **Accepted:** the family stays usable until it expires by lifetime (ADR-014) | E1-13 |
| P4 | Man-in-the-middle with a rogue CA on the device | T/I | Cloudflare TLS. Certificate pinning is **accepted risk for E1**: trycloudflare certificates and hostnames rotate, so a pin would break the app. Pinning comes with the named tunnel and domain. Deviation from blueprint §10 ("certificate pinning for the API") | E8 named-tunnel card (to be filed: named tunnel, domain, pinning, bundle scan) |
| P5 | Secrets shipped in the app bundle | I | Only non-secret `EXPO_PUBLIC_*` values (API base URL). Bundle scan per blueprint §10 | E1-12; scan: E8 named-tunnel card (to be filed: named tunnel, domain, pinning, bundle scan) |

### B2: Cloudflare and tunnel

| # | Threat | STRIDE | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| T1 | Quick-tunnel URL leaks (bundle, screenshots, shared logs), so strangers can reach the API | I/D | **Accepted risk.** The URL ships in every build, so it is public by design. All protection sits in the API: auth on every non-public operation, rate limits, fail-closed behaviour. The URL changes on each cloudflared restart. No Cloudflare account or token exists to leak | E1-15, E1-08 |
| T2 | Postgres, Redis, SeaweedFS or an admin UI reachable through the tunnel | I/E | cloudflared points at `api:8000` only. A check script proves other targets fail | E1-15 |
| T3 | Client-IP spoofing with a forged `CF-Connecting-IP` to dodge per-IP limits or poison them | S | Header trusted only when the "behind tunnel" flag is on. Otherwise the socket address is used. Tested. See rule R2 for the peer check | E1-08, E1-15 |
| T4 | Cloudflare sees plaintext traffic | I | **Accepted.** Cloudflare is a named processor in the Privacy notice | E1-21 |
| T5 | trycloudflare has no uptime promise and is meant for testing | D | **Accepted for the E1 demo only.** Not used for external beta | E8 named-tunnel card (to be filed: named tunnel, domain, pinning, bundle scan) |

### B3: API

| # | Threat | STRIDE | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| A1 | Credential stuffing and brute force on sign-in | S | Per-IP limit on sign-in. Stricter throttle on failed sign-ins per email (see R1). Slow password hash (ADR-014) | E1-08, E1-07 |
| A2 | CPU exhaustion through password hashing (hash floods) | D | Rate limit runs before hashing. Maximum password length set in ADR-014 | E1-08, E1-02 |
| A3 | Guest-credential farming (mass guest issue to fill the DB or get around per-principal limits) | D/S | Per-IP limit on guest issue. Issue stores no personal data. Unused guests purged after retention. **Accepted remainder:** carrier NAT puts many users behind one IP, so limits stay loose | E1-08, E1-05, E1-10 |
| A4 | Refresh-token theft and replay | S | Refresh rotates on every use. A reused token returns 401 and revokes the whole family. Logout revokes the family. Server stores only token hashes | E1-05 (ADR-014) |
| A5 | Forged or tampered JWT (wrong key, `alg=none`, HS/public-key confusion, expired token) | S/E | Fixed algorithm allow-list, key id, expiry checked. All failures give the same 401 problem document | E1-05 (ADR-014, ADR-015) |
| A6 | Account enumeration on sign-in | I | Same problem document and similar timing for an unknown email and a wrong password (dummy hash) | E1-07 |
| A7 | Account enumeration on sign-up | I | **Accepted risk (owner sign-off 2026-10-27).** flows.md 3a needs an "already registered → offer sign-in" answer, and with no email sending we cannot hide that state. Behaviour E1-07 tests: sign-up with a registered email returns a conflict problem document that offers sign-in, with no other account detail. Limited by per-IP sign-up limits. Revisit when E1-17 adds email verification, which can replace the conflict answer with a "check your email" reply | E1-07, E1-08 |
| A8 | Guest-data takeover during the move to an account | E/T | Move only in the sign-up/sign-in request that presents both a valid guest credential and the new session. One transaction that deletes the guest principal and credential and writes the deletion ledger (ADR-014, ADR-022). Never matched by email, device or analytics id. An unknown, deleted or foreign credential moves nothing. Concurrency rule R3 | E1-07 |
| A9 | Stolen guest credential moved into the attacker's account | I | **Accepted:** same impact as the theft itself (P1, A4) | E1-12 |
| A10 | Mass assignment and malformed input | T | Pydantic models with unknown fields forbidden, lengths and enums from the contract. Property-based tests over every operation | E1-05, E1-07, E1-06 |
| A11 | Irreversible "Delete my data" with a stolen access token | T/D | Requires an authenticated principal. **Accepted for E1:** no re-authentication step, because there is no password reset yet | E1-09 |
| A12 | Redis down turns off rate limiting | D | Auth endpoints fail closed with 503 problem documents | E1-08 |
| A13 | Oversized bodies, `/docs` and `/openapi.json` public through the tunnel, stack traces in errors | D/I | Global body size limit, docs off in tunnel mode, RFC 9457 errors with no internals | E1-22 API edge hardening |
| A14 | Sign-up spam (unlimited fake accounts, no email verification) | D | **Accepted** with per-IP sign-up limits | E1-08 |
| A15 | Disputed actions (who signed in, reuse detected) | R | Security events logged under a pseudonymous principal id, without email, IP or token. Dashboards in E2 | E1-05, E1-07, E2 |

### B4: Data stores

| # | Threat | STRIDE | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| D1 | Data services reachable from outside | I/E | `backend` network is `internal: true`. Only `api` is published, on 127.0.0.1 (`API_HOST_PORT`, default 8000). SeaweedFS admin listeners bound to loopback, S3 signed, gRPC IAM gated by the filer key | E0-07, E0-12 (done) |
| D2 | Personal data survives "Delete my data" | I | Every module registers delete and export handlers. A test fails for any user-data table without one. Server deletion finishes before the response | E1-09 |
| D3 | Guest data kept past retention | I | Scheduled purge. Left-over count must be 0 after each run (SLO) | E1-10 |
| D4 | Disk or volume theft exposes emails and hashes | I | **Accepted for E1.** No column encryption yet, and host disk encryption is waiting on the owner (Windows 11 Home has no BitLocker, only Device Encryption where the hardware supports it). SeaweedFS encrypts chunks, but its keys sit on the same disk, which does not yet meet ADR-008 ("a stolen disk must not expose them"); no media exists until E6. Must be fixed before external beta, for media as well as emails and hashes | Card before external beta (to be filed) |
| D5 | Redis rate-limit keys keep IPs and emails indefinitely | I | Every key has a TTL. Keys are HMAC'd (R1) | E1-08 |

### B5: Host, operations, CI

| # | Threat | STRIDE | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| H1 | Secrets committed, logged or left in CI artefacts | I | gitleaks on changes and history (`make lint`). Where secrets live and how they rotate is decided in ADR-015. Nothing secret in Compose output | E0-04, E1-04 |
| H2 | JWT signing key leaks | S/E | Storage, rotation and key id per ADR-015. Rotating the key does not log users out: refresh tokens are opaque and not signed, so only access tokens (10 min) fail and the app refreshes them (ADR-014) | E1-04, E1-05 |
| H3 | Backups leak or outlive deletion | I | Backups encrypted, kept at most 30 days, never include media | E1-23 backup card |
| H4 | Personal data in container logs | I | No email, password, token, credential or IP at INFO (section 6) | E1-05, E1-07, E1-09 |
| H5 | Compromised dependency or image | T/E | Pins by digest or lockfile, 7-day rule, pip-audit and npm audit (ADR-018, ADR-019) | All cards |

## 5. OWASP API Security Top 10 (2023)

| Item | Control in Capsule | Card |
| --- | --- | --- |
| API1 Broken Object Level Authorization | E1 operations act on the current principal only (`/v1/me`-style, no foreign ids in paths). From E3, every query is scoped by principal id and tests try another principal's id | E1-05 (principal dependency), E1-09, E3+ |
| API2 Broken Authentication | Rotating refresh tokens with reuse detection, slow password hash, uniform 401s, rate limits, secure-store on the phone | E1-02, E1-05, E1-07, E1-08, E1-12 |
| API3 Broken Object Property Level Authorization | Explicit request/response schemas, unknown fields forbidden. Export never includes password hashes or tokens. No hash or token in any response | E1-05, E1-07, E1-09, E1-06 |
| API4 Unrestricted Resource Consumption | Redis rate limits per IP and per principal, rate limit before hashing, body size limit. Upload limits in E6, generation limits in E3 | E1-08, E1-22, E3, E6 |
| API5 Broken Function Level Authorization | No admin endpoints on the public API. Admin UIs never go through the tunnel. Guest vs account rules checked server-side | E1-05, E1-15 |
| API6 Unrestricted Access to Sensitive Business Flows | Guest farming and sign-up spam limited per IP (accepted remainder, A3 and A14). Guest-data move needs both credentials | E1-07, E1-08 |
| API7 Server Side Request Forgery | No outbound fetches in E1. From E4/E5, outgoing URLs come from an allow-list only | n/a in E1; E4, E5 |
| API8 Security Misconfiguration | Hardened Compose (non-root, `cap_drop: ALL`, read-only, internal network). Docs off in tunnel mode, no stack traces, uvicorn access log without IPs (R4) | E0-12, E1-22, E1-05 |
| API9 Improper Inventory Management | `contracts/openapi.yaml` is the single list of operations. Property-based tests cover every operation. Only the API is behind the tunnel | E1-06, E1-15 |
| API10 Unsafe Consumption of APIs | Cloudflare headers trusted only behind the flag. From E3, LLM output, product feeds and web content are untrusted: prices, budget and links are checked by code | E1-08; E3, E4, E5 |

## 6. Data policy

### Personal data by column

Planned E1 tables (names are set by E1-05/E1-07; the rules hold whatever the final names are).

| Table / store | Column | Personal | Encrypted at rest (E1) | Allowed in logs |
| --- | --- | --- | --- | --- |
| principals | id (random) | Pseudonymous | No | Yes (only identifier allowed) |
| principals | kind (guest/account), created_at, last_activity_at | Linked to a person | No | kind only |
| accounts | email (normalised) | Yes | No (D4, accepted for E1) | Never |
| accounts | password_hash | Yes (credential) | Hashed, not encrypted | Never |
| accounts | age_confirmed_at | Yes | No | Never |
| refresh families / tokens | token hash, family id, state, timestamps (idle and absolute limits), family revoked_at | Credential material | Hashed | Never the hash or the token; family id at DEBUG only |
| guest credential record | credential hash | Credential material | Hashed | Never |
| Redis rate-limit keys | HMAC of IP and email | Yes (pseudonymised) | No | Never |
| Consultation tables (E3+) | flows.md "Guest data" list | Yes | Decided by the pre-beta encryption card | Never content; counts only |
| SeaweedFS media (E6) | photos, audio | Yes, highest sensitivity | Chunk encryption, keys on the same disk (falls short of ADR-008 until the pre-beta encryption card, D4) | Never; not in traces either |

Rules:

- Store no birth date, device id, IP or analytics id on principals (E1-05, E1-07).
- A new column holding personal data is marked in the model docstring and gets a delete and export handler (`db-migration` skill, E1-09).
- Fixtures use made-up `@example.com` emails only.

### Logs

- At INFO and above, logs never contain email, password, token, guest credential, IP or request bodies. A deletion is logged as a count with the principal type.
- Container logs use the `local` driver, capped at 10 MB × 3 files per service. Their retention is set in the retention ADR.
- Sentry and PostHog rules follow ADR-004 (no PII, auth headers stripped, consent first).

### Retention

[ADR-022](adr/022-data-retention-deletion-export.md) holds the full table, the definition of last activity, the restore steps and the export format. In short:

- Guest data: deleted 30 days after last activity (config, upper bound 30). Accounts: never deleted automatically. Unsaved consultation history of an account: deleted per consultation, 30 days after the last activity on that consultation. Saved guides stay until "Delete my data".
- Refresh families: expired or revoked ones are deleted within 24 h. Rate-limit keys: TTL at most 24 h. LangGraph checkpoints: 24 h after an abandoned consultation (at most 7 days by config).
- Logs: Postgres runs with `log_error_verbosity = terse` and `log_min_error_statement = panic`. cloudflared runs at `info` with no access logging. Container logs are size-capped until Loki (E2, 30 days or less).
- Media: within 24 h, never backed up (ADR-008). Postgres backups: at most 30 days, encrypted, on the external disk only.
- "Delete my data" and the guest-data move delete server data in one transaction and write the principal id to a deletion ledger (a table plus a file on the backup disk). The ledger is pruned only up to the oldest backup on disk. A restore refuses backups older than 30 days, replays the ledger and the purges, then revokes every refresh family and rotates the JWT key before the API takes traffic.
- Sentry, PostHog and Langfuse retention and per-id deletion: to verify in E2. A purged guest's PostHog data follows vendor retention.

### Erasure without a password

E1 has no password reset. A user who forgot their password cannot sign in to use "Delete my data". Until E1-17 ships, erasure and export requests go through the contact address in the Privacy notice. E1-21 owns that contact path, and a runbook covers identity checks and manual deletion through the E1-09 handlers.

## 7. Open inputs for ADRs

These are listed, not decided.

### ADR-014 (E1-02)

- Guest credential: opaque random secret or long-lived refresh token, and how its lifetime relates to the 30-day inactivity rule.
- Access token lifetime (range to weigh: 5–15 min) and refresh lifetime (absolute and idle).
- Reuse detection: a grace window for a retry after a lost response (E1-12 single-flight does not cover it), and whether access tokens die with the family or live until expiry.
- JWT algorithm (EdDSA/ES256 or HS256), claims (`iss`, `aud`, `sub`, `typ` guest/account, `kid`, `jti`).
- Password hashing: argon2id or bcrypt; memory/time parameters sized for a 32 GB host shared with GPU work; maximum input length.
- Password rules: minimum length per NIST SP 800-63B, an offline breached-password list or none, no composition rules.
- Email normalisation (case, Unicode, plus-addressing kept or not).
- Logout scope: this device or all devices.
- JWT and password-hashing libraries (7-day rule).

### ADR-015 (E1-04)

- Where JWT signing keys live locally (`.env` or Docker secret files) and in CI (test-only random values).
- Rotation cadence and how long an old `kid` stays valid; what to do after a leak.
- A password pepper: yes or no, and where it lives.
- The HMAC key for rate-limit keys (R1), and a blind-index key if email gets encrypted.
- Keys for field encryption and backup encryption (E1-23).
- Moving SeaweedFS JWT keys out of Compose `configs.content`.
- File permissions for secret files on the Windows host.

## 8. Rules later cards check against

| # | Rule | Card |
| --- | --- | --- |
| R1 | The failed sign-in limit throttles on email + IP and never locks the account (otherwise anyone can lock out a victim). Rate-limit keys use an HMAC of IP or email, never the raw value, and every key has a TTL | E1-08 |
| R2 | `CF-Connecting-IP` is trusted only when the flag is on **and** the socket peer is the cloudflared container. A direct request through the published host port or from another container on `edge` uses the socket address. The cloudflared container's address on `edge` is dynamic and published-port traffic can arrive from the bridge gateway, so E1-08/E1-15 must fix how the peer is identified (for example a dedicated network for cloudflared and api, or a resolved service name), and test it | E1-08, E1-15 |
| R3 | The guest-data move locks the guest credential row. Two parallel sign-ups or sign-ins with the same credential: one moves, the other moves nothing. Covered by a test | E1-07 |
| R4 | The uvicorn access log is off or replaced by one that logs no client IP and no query string at INFO | E1-05 |
| R5 | Token tests include `alg=none`, HS/public-key confusion, unknown `kid` and expired tokens. All return the same 401 | E1-05 |
| R6 | A retry after a lost refresh response follows the ADR-014 grace rule and is tested in the client and on the server | E1-12, E1-05 |
| R7 | The quick tunnel is for the E1 demo only, not external beta | E1-15, E8 named-tunnel card (to be filed: named tunnel, domain, pinning, bundle scan) |
| R8 | Rate limit runs before any password hash | E1-08 |
| R9 | Every new user-data table ships delete and export handlers, and its columns are added to section 6 | All cards from E3 |
| R10 | Accepted risks in this page (P3, P4, T1, T4, T5, A3, A7, A9, A11, A14, D4) are reviewed at the E1 demo and before external beta | security-engineer |
