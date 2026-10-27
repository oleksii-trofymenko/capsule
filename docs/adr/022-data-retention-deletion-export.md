# ADR-022: Data retention, deletion and export: fixed upper bounds, our own purge jobs, backups that expire and a deletion ledger replayed on restore

- Status: proposed
- Date: 2026-10-27
- Deciders: Orchestrator, security-engineer, project owner
- Related: E1-03, E1-05, E1-07, E1-08, E1-09, E1-10, E1-14, E1-15, E1-21, E1-23, E2, E3, E6; ADR-004, ADR-008, ADR-009, ADR-013 (planned), ADR-014, ADR-015; `docs/security.md` §6; `docs/design/flows.md` (F6 "Guest data", F10); blueprint §12

## Context

Capsule serves EU users, so GDPR applies. Storage limitation (Art. 5(1)(e)) needs a written retention period for every kind of personal data we hold. Erasure (Art. 17), access (Art. 15) and portability (Art. 20) need a delete and an export that guests and account holders can both use.

The server is one home PC:

- Postgres holds principals, accounts, refresh-token families and guest credentials. From E3 it also holds consultation data and LangGraph checkpoints.
- Redis holds rate-limit keys and SAQ jobs.
- SeaweedFS holds media from E6.
- Docker keeps container logs (`local` driver, 10 MB × 3 per service) for every service, Postgres and cloudflared included.
- Sentry and PostHog (ADR-004) and Langfuse (ADR-013) arrive in E2/E3.

Constraints:

- The budget is €0.
- E1 sends no email, so neither deletion nor export can be confirmed by email.
- Backups go to one external disk (USB, NTFS) on the home PC. There is no off-site copy yet.
- flows.md needs one fixed `{retention_days}` value for the Privacy notice.

Owner decisions (2026-10-27):

- Guest data is deleted 30 days after last activity.
- Accounts are never deleted automatically.
- An account's unsaved consultation history is deleted per consultation, 30 days after the last activity on that consultation. Saved guides stay until "Delete my data".
- Postgres backups are kept for at most 30 days, on the external disk only.
- Media are deleted within 24 h and never backed up (ADR-008).

## Options

1. **Fixed upper bounds per data class, enforced by our own jobs and TTLs; backups expire within 30 days, and a deletion ledger is replayed on every restore (chosen).** Simple, costs €0, and works the same on any store. Deleted data stays inside encrypted backups for up to 30 days, but it is out of use and comes back only through a restore, which replays the ledger. Cost: we own a ledger, a mount on the backup disk and the restore steps.
2. **Delete inside the backups as well (decrypt, rewrite and re-encrypt every dump on each deletion).** Nothing deleted survives anywhere. Cost: heavy and fragile, a failed rewrite can corrupt the only copy, and the backup identity would have to live on the host, which ADR-015 forbids.
3. **Shorter backup retention (for example 7 days) and no ledger.** Deleted data leaves backups sooner. Cost: less room to recover from a slowly noticed fault, and a restore still brings deleted people back for up to 7 days.

## Decision

Every data class has an upper bound fixed here, with the actual value coming from config. Our own purge jobs, Redis TTLs and the ADR-008 media job enforce it. "Delete my data" and the guest-data move delete server data in one transaction and record the principal id in a deletion ledger. Backups are never edited: they expire within 30 days, and every restore replays the ledger and revokes all sessions before the API takes traffic.

### Retention table

| Data class | Where | Kept for and trigger (upper bound; actual value from config) | Deleted by | Owner |
| --- | --- | --- | --- | --- |
| Guest principal and all its data (flows.md "Guest data" list) | Postgres | Up to 30 days after last activity | Purge job, which reuses the "Delete my data" handlers. Runs at least once every 24 h | E1-10 |
| Account (email, password hash, `age_confirmed_at`) and saved guides | Postgres | Until "Delete my data". Never deleted automatically | Delete handlers | E1-09 |
| Unsaved consultation history of an account, per consultation | Postgres | Up to 30 days after the last activity on that consultation | Purge job | E3 (consultation tables), on the E1-10 job |
| Refresh-token families and tokens, including revoked ones | Postgres | Live family: every token hash (`current`, `rotated`, `superseded`) stays until the family ends (reuse detection, ADR-014). Expired or revoked family: deleted within 24 h. Never outlives its principal. Every family is revoked on restore | Purge job sweep, delete handlers, restore step 4 | E1-05, E1-10, E1-23 |
| Guest principal and credential after a move to an account | Postgres | Deleted inside the move transaction, which also writes the guest principal id to the ledger | Move transaction | E1-07 |
| Guest-credential record otherwise | Postgres | Lives as long as the guest. Deleted by purge or "Delete my data" | Purge, delete handlers | E1-10, E1-09 |
| Rate-limit keys: HMAC of IP or email; principal id for per-principal limits | Redis | TTL = the limit window, at most 24 h. No key without a TTL | Redis expiry. Per-principal keys are also removed on "Delete my data" | E1-08 |
| SAQ job payloads and results | Redis | Payloads carry a principal id only, never content. Results kept at most 24 h | SAQ TTL | E1-10, later job cards |
| LangGraph checkpoints | Postgres `agent_checkpoint` | Deleted when the consultation closes. An abandoned consultation's checkpoints are deleted 24 h after the last write. E3 may lengthen this by config, to 7 days at most, if resume needs it. Always deleted with the principal | SAQ job, plus a delete handler | E3 agent card (ADR-009, E0-11) |
| Postgres server log | `postgres` container stderr, Docker `local` driver | Same as container logs (below). Runs with `log_error_verbosity = terse` and `log_min_error_statement = panic`, so error lines carry no DETAIL, CONTEXT or STATEMENT with row values. Sign-up checks for an existing email before inserting, so the unique-violation text, which contains the email, is never relied on | Rotation | E1-05 (settings), E1-07 (check before insert) |
| cloudflared log | `cloudflared` container, Docker `local` driver | Same as container logs. Runs at `--loglevel info`, never debug, with no access logging, so no client IP or URL is written | Rotation | E1-15 |
| Container logs (all services) | Docker `local` driver, 10 MB × 3 per service | Size cap only, until E2. Accepted because lines hold no email, password, token, credential, IP or body (`docs/security.md` §6), only the random principal id. That id links to nothing once the principal is deleted, and the `local` driver has no time-based rotation at €0. From E2, Loki keeps logs for at most 30 days | Rotation; Loki retention | E0-07 (done), E2 |
| Sentry (consent only) | EU SaaS | Vendor free-plan retention, 30 days (to verify in E2). Per-id deletion on "Delete my data" in E2, or ADR-004 is amended so crash reports carry no id (flows.md E2 note) | Vendor retention, plus the Sentry API | E2 |
| PostHog (consent only) | EU SaaS | Vendor free-plan retention, 1 year (to verify in E2). The person is deleted on "Delete my data". A purged guest's PostHog data follows vendor retention only, because the server never stores the analytics id | PostHog person-delete API. The app resets its id at once | E2 |
| Langfuse traces (contain user text) | Self-hosted, never behind the tunnel | At most 30 days. Deleted per principal on "Delete my data". Whether self-hosted Langfuse can expire traces is to verify in E2; if it cannot, our own job deletes them through its API | Langfuse retention or our job | ADR-013, E2 |
| Postgres backups | External disk, age-encrypted (ADR-015), Postgres only | At most 30 days after creation. A restore refuses any backup older than 30 days | Rotation; ledger replay and session revocation on restore | E1-23 |
| Deletion ledger: principal id and deletion time only | Postgres table, and a file in a ledger directory on the external disk | Until older than the creation time of the oldest backup actually on disk (normally 31 days or less) | The backup job prunes the file and the table after rotation | E1-07 (writer, used by the guest-data move), E1-09 (reuses the writer), E1-23 (file, pruning, replay) |
| Media (photos, voice) | SeaweedFS | Deleted after processing, within 24 h at most. Never backed up | ADR-008 job. Deleted at once on "Delete my data" | E6, E1-09 hook |
| Exports | Built inside the response | Never stored, cached or logged on the server. The app deletes its temporary file after sharing | Nothing to delete | E1-09, E1-14 |

### Last activity

Last activity for a principal is the time of the last authenticated API request that succeeded for it. These requests count:

- any authenticated endpoint;
- `POST /v1/auth/refresh`;
- `POST /v1/auth/guest` that presents an existing guest credential;
- sign-in.

These do not count: failed or unauthenticated requests, analytics events and offline use of the app. The server writes `last_activity_at` at most once per hour per principal. For unsaved consultation history, last activity is the time of the last write to that consultation.

The guest purge treats a guest as expired when `last_activity_at` is older than the configured retention. The guest credential is rejected from that moment, even before the purge runs (ADR-014).

### "Delete my data"

- **Who:** guests and account holders, as the authenticated current principal only. No email confirmation (E1 sends no email). No re-authentication in E1 (accepted risk A11).
- **In one database transaction:**
  - every row the principal owns, through the handlers each module registers: principal, account, refresh families and tokens, guest credential, consultation data, checkpoints;
  - the ledger row;
  - the principal's media object keys, collected before the commit.
- **After commit, before the response:**
  - The id is appended to the external ledger file.
  - The collected media objects are deleted. A failed object delete is left to the ADR-008 24 h job.
  - Redis keys holding the principal id are deleted.
  - Queued jobs for a deleted principal do nothing.
- **On failure:** a database error leaves everything in place and returns a problem document. The app wipes its local stores (secure-store, MMKV, saved guides) only after a success (flows.md F10).
- **Not reached, by design:**
  - Rate-limit keys built from an HMAC of an IP or email expire within 24 h.
  - Container logs hold only the random id, which no longer links to anything.
- **People who cannot sign in** (forgotten password, lost phone) use the contact address in the Privacy notice. The owner verifies the request and runs the same handlers, within the one-month GDPR deadline (E1-21 runbook).

### Guest-data move

The move runs in the sign-up or sign-in request (ADR-014, R3). In that same transaction, the guest principal and its credential are deleted and the guest principal id is written to the ledger. After commit, the id is appended to the ledger file. A restore can therefore never bring back the guest, or a guest credential that would move the same data a second time.

### Third parties

- From E2, the "Delete my data" request carries the app's analytics id and crash id when they exist. The server uses them once, to call the PostHog person-delete API and the Sentry deletion API, and never stores or logs them. A failed vendor call does not undo the deletion. It is logged without the ids, and vendor retention covers the rest.
- The PostHog personal API key and the Sentry auth token are E2 additions to the ADR-015 secrets list (Compose file secrets, one per purpose).
- A guest removed by the purge job has no ids on the server, so its PostHog and Sentry data follow vendor retention only.
- In E1, the app resets both ids at once (ADR-004, flows.md F10).

### Deletion ledger

- **What it holds:** the principal id and the deletion time. Nothing else.
- **Written by:** one writer (E1-07, reused by E1-09). It inserts the row in the caller's transaction. After commit, it appends the id to a file in a ledger directory on the external disk.
- **Mounts:** the ledger directory is the only part of the external disk mounted into `api`. The backup directory is never mounted there.
- **Integrity:** NTFS cannot enforce append-only, so the file is not trusted alone. Each backup run reconciles it from the table, and restore uses the union of both.
- **Disk missing or unwritable:** `api` still starts and requests still succeed. The writer logs an error with the principal id only, and the table stays the record.
- **Pruning:** after rotation, the backup job prunes the file and the table, removing only entries older than the creation time of the oldest backup actually on disk.

### Backups and restore

Backups are never edited. Deleted data leaves them within 30 days, when the backup expires. A restore, including the monthly drill, refuses any backup older than 30 days. Then, with the API stopped:

1. **Replay the deletion ledger:** the union of the external file and the restored table. Every listed principal is deleted again, media hook included.
2. **Check the API error log for failed ledger appends** made since the backup was created. Delete those principal ids too.
3. **Run the purges:** guest purge, the per-consultation unsaved-history purge and the refresh-family sweep.
4. **Revoke every refresh family and rotate the JWT signing key with no overlap** (ADR-015). The restored token state is stale. Accounts sign in again. Guests re-authenticate with their guest credential through `POST /v1/auth/guest`. A guest created after the backup gets a 401 and starts again as a new guest.

Only then does the API take traffic. Media are never restored, because they are never backed up.

**Residual risk (accepted):** a failed ledger append, followed by the database disk dying before the next backup copies the row into the file. Step 2 catches this while the API logs survive. If they are lost too, that one deletion can come back on restore. The window is at most 24 h and needs two failures.

### Leftover copies

Deleted Redis keys can stay in the AOF file until its next rewrite. Deleted Postgres rows stay as dead tuples until autovacuum and in WAL segments until they are recycled. Logical dumps contain only live rows, so neither copy reaches a backup.

### Export

- **Same terms as deletion:** guests and accounts, the authenticated current principal only, synchronous, rate limited, no email.
- **Format:** one UTF-8 JSON file named `capsule-export-YYYY-MM-DD.json`. It has a `schema_version` and one section per module export handler.
- **Contents:** the principal's kind, `created_at` and `last_activity_at`; for accounts, the email and `age_confirmed_at`; the consultation data (flows.md list) once it exists.
- **Never included:** password hashes, token or credential hashes, analytics or crash ids, media (deleted within 24 h), or another principal's data.

## Consequences

- Easier: one table answers "how long do we keep X" for the Privacy notice (E1-21), reviewers and the `db-migration` skill. Deletion and export reach new tables through registered handlers without changing E1-09. Backups need no rewrite tooling.
- Harder:
  - Every new user-data table ships delete and export handlers and a row in this table (rule R9).
  - We own the purge jobs, the ledger, its mount and the restore steps. A restore that skips them would break erasure.
  - Every restore logs everyone out.
  - Deleted data sits in encrypted backups for up to 30 days, and the Privacy notice says so.
  - Size-capped container logs can hold old pseudonymous lines until E2.
- We will monitor:
  - Expired guests left after each purge run: must be 0 (data-deletion SLO).
  - Failed ledger-file appends and a missing ledger disk.
  - Media objects older than 24 h (ADR-008).
  - Backup files older than 30 days: must be 0 (E1-23).
- Revisit when:
  - Before external beta: review whether dormant accounts may be kept forever (owner decision; a trigger for review only, not a change).
  - E2 finds Sentry, PostHog or Langfuse retention or deletion differs from this table.
  - Backups move off-site or to the cloud.
  - E3 needs checkpoints kept longer than 7 days.
  - E1-17 adds email (confirmation of deletion or export).
