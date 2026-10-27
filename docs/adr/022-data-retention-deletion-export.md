# ADR-022: Data retention, deletion and export: fixed upper bounds, our own purge jobs, backups that expire and a deletion ledger replayed on restore

- Status: proposed
- Date: 2026-10-27
- Deciders: Orchestrator, security-engineer, project owner
- Related: E1-03, E1-05, E1-07, E1-08, E1-09, E1-10, E1-14, E1-21, E1-23, E2, E3, E6; ADR-004, ADR-008, ADR-009, ADR-013 (planned), ADR-014, ADR-015; `docs/security.md` §6; `docs/design/flows.md` (F6 "Guest data", F10); blueprint §12

## Context

Capsule serves EU users, so GDPR applies. Storage limitation (Art. 5(1)(e)) needs a written retention period for every kind of personal data we hold. Erasure (Art. 17), access (Art. 15) and portability (Art. 20) need a delete and an export that guests and account holders can both use.

The server is one home PC. Postgres holds principals, accounts, refresh-token families, guest credentials and, from E3, consultation data and LangGraph checkpoints. Redis holds rate-limit keys and SAQ jobs. SeaweedFS holds media from E6. Docker keeps container logs (`local` driver, 10 MB × 3 per service). Sentry and PostHog (ADR-004) and Langfuse (ADR-013) arrive in E2/E3.

Constraints:

- The budget is €0.
- E1 sends no email, so neither deletion nor export can be confirmed by email.
- Backups go to one external disk on the home PC. There is no off-site copy yet.
- flows.md needs one fixed `{retention_days}` value for the Privacy notice.

Owner decisions (2026-10-27):

- Guest data is deleted 30 days after last activity.
- Accounts are never deleted automatically.
- An account's unsaved consultation history is deleted 30 days after last activity. Saved guides stay until "Delete my data".
- Postgres backups are kept for at most 30 days, on an external disk only.
- Media are deleted within 24 h and never backed up (ADR-008).

## Options

1. **Fixed upper bounds per data class, enforced by our own jobs and TTLs; backups expire within 30 days, and a deletion ledger is replayed on every restore.** Simple, costs €0, and works the same on any store. Deleted data stays inside encrypted backups for up to 30 days, but it is out of use and comes back only through a restore, which replays the ledger. Cost: we own a ledger and the restore step.
2. **Delete inside the backups as well (decrypt, rewrite and re-encrypt every dump on each deletion).** Nothing deleted survives anywhere. Cost: heavy and fragile, a failed rewrite can corrupt the only copy, and the backup key has to stay online.
3. **Shorter backup retention (for example 7 days) and no ledger.** Deleted data leaves backups sooner. Cost: less room to recover from a slowly noticed fault, and a restore still brings deleted people back for up to 7 days.

## Decision

Every data class has an upper bound fixed here, with the actual value coming from config. Our own purge jobs, Redis TTLs and the ADR-008 media job enforce it. "Delete my data" removes all of a principal's server data before it responds and records the principal id in a deletion ledger. Backups are never edited: they expire within 30 days, and every restore replays the ledger before the API takes traffic.

### Retention table

| Data class | Where | Kept for and trigger (upper bound; actual value from config) | Deleted by | Owner |
| --- | --- | --- | --- | --- |
| Guest principal and all its data (flows.md "Guest data" list) | Postgres | Up to 30 days after last activity | Purge job, which reuses the "Delete my data" handlers. Runs at least once every 24 h | E1-10 |
| Account (email, password hash, `age_confirmed_at`) and saved guides | Postgres | Until "Delete my data". Never deleted automatically | Delete handlers | E1-09 |
| Unsaved consultation history of an account | Postgres | Up to 30 days after the last activity on that consultation | Purge job | E3 (consultation tables), on the E1-10 job |
| Refresh-token families and tokens, including revoked ones | Postgres | Live family: rotated token hashes stay until the family ends (needed for reuse detection). Expired or revoked family: deleted within 24 h. Never outlives its principal | Purge job sweep, plus delete handlers | E1-05, E1-10 |
| Guest-credential record | Postgres | Lives as long as the guest. Deleted with the guest principal in the transaction that moves guest data to an account, or by purge or delete | Move transaction, purge, delete | E1-07, E1-10, E1-09 |
| Rate-limit keys (HMAC of IP or email; principal id) | Redis | TTL = the limit window, at most 24 h. No key without a TTL | Redis expiry. Keys holding a principal id are also removed on delete | E1-08 |
| SAQ job payloads and results | Redis | Payloads carry a principal id only, never content. Results kept at most 24 h | SAQ TTL | E1-10, later job cards |
| LangGraph checkpoints | Postgres `agent_checkpoint` | Deleted when the consultation closes. An abandoned consultation's checkpoints are deleted 24 h after the last write. E3 may lengthen this by config, to 7 days at most, if resume needs it. Always deleted with the principal | SAQ job, plus a delete handler | E3 agent card (ADR-009, E0-11) |
| Container logs | Docker `local` driver, 10 MB × 3 per service | Size cap. Lines hold only the random principal id (`docs/security.md` §6), which links to nothing once the principal is deleted. From E2, Loki keeps logs for at most 30 days | Rotation; Loki retention | E0-07 (done), E2 |
| Sentry (consent only) | EU SaaS | Vendor free-plan retention, 30 days (to verify in E2). Data for the id is deleted on "Delete my data", or ADR-004 is amended so crash reports carry no id (flows.md E2 note) | Vendor retention, plus the Sentry API | E2 |
| PostHog (consent only) | EU SaaS | Vendor free-plan retention, 1 year (to verify in E2). The person is deleted on "Delete my data" | PostHog person-delete API. The app resets its id at once | E2 |
| Langfuse traces (contain user text) | Self-hosted, never behind the tunnel | At most 30 days. Deleted per principal on "Delete my data". Whether self-hosted Langfuse can expire traces is to verify in E2; if it cannot, our own job deletes them through its API | Langfuse retention or our job | ADR-013, E2 |
| Postgres backups | External disk on the home PC, encrypted (ADR-015), Postgres only | At most 30 days after creation | Rotation. Ledger replay on restore | E1-23 |
| Deletion ledger: principal id and deletion time only | Postgres table, and an append-only file on the external backup disk | 31 days, one day longer than the oldest possible backup | Purge job (table); backup job (file) | E1-09 (writes), E1-10 (prunes table), E1-23 (file, replay) |
| Media (photos, voice) | SeaweedFS | Deleted after processing, within 24 h at most. Never backed up | ADR-008 job. Deleted at once on "Delete my data" | E6, E1-09 hook |
| Exports | Built inside the response | Never stored, cached or logged on the server. The app deletes its temporary file after sharing | Nothing to delete | E1-09, E1-14 |

### Last activity

Last activity is the time of the last authenticated API request that succeeded for that principal, token refresh included. Failed or unauthenticated requests, analytics events and offline use of the app do not count. The server writes it at most once per hour per principal. For unsaved consultation history, last activity is the time of the last write to that consultation. The guest purge counts a guest as expired when `last_activity_at` is older than the configured retention. ADR-014 must keep the guest credential's idle lifetime no longer than this retention.

### "Delete my data"

- **Who:** guests and account holders, as the authenticated current principal only. No email confirmation (E1 sends no email). No re-authentication in E1 (accepted risk A11 in `docs/security.md`).
- **Before the response, in one database transaction:**
  - every row the principal owns, through the handlers each module registers: principal, account, refresh families and tokens, guest credential, consultation data, checkpoints;
  - a ledger row.
- **Before the response, right after commit:**
  - The id is appended to the external ledger file. If the append fails, the deletion still stands and is logged as an error; the daily backup job copies any missing ledger rows into the file.
  - The principal's media objects are deleted (ADR-008 hook).
  - Redis keys holding the principal id are deleted.
  - Queued jobs for a deleted principal do nothing.
- **Before the response, on failure:** a database error leaves everything in place and returns a problem document. The app wipes its local stores (secure-store, MMKV, saved guides) only after a success (flows.md F10).
- **Not reached, by design:**
  - Rate-limit keys built from an HMAC of an IP or email expire within 24 h.
  - Container logs hold only the random id, which no longer links to anything.
- **Outside our database:**
  - PostHog person: deleted through its API.
  - Sentry data for the id: deleted through its API, or ADR-004 is amended so crash reports carry no id.
  - Langfuse traces: deleted per principal.
  - All three are E2 work. Until then the app resets its analytics and crash ids at once.
- **People who cannot sign in** (forgotten password, lost phone) use the contact address in the Privacy notice. The owner verifies the request and runs the same handlers, within the one-month GDPR deadline (E1-21 runbook).

### Backups and restore

Backups are never edited. Deleted data leaves them within 30 days, when the backup expires. Every restore, including the monthly drill, does three things before the API takes traffic:

1. Replays the deletion ledger: the union of the external ledger file and the restored ledger table. Every listed principal is deleted again.
2. Runs the guest purge and the unsaved-history purge.
3. Never restores media. Media are not in backups.

The external ledger file closes the gap between the last backup and a disk failure. The API container mounts only the ledger directory on the external disk, never the backup directory.

### Export

- **Same terms as deletion:** guests and accounts, the authenticated current principal only, synchronous, rate limited, no email.
- **Format:** one UTF-8 JSON file named `capsule-export-YYYY-MM-DD.json`. It has a `schema_version` and one section per module export handler.
- **Contents:** the principal's kind, `created_at` and `last_activity_at`; for accounts, the email and `age_confirmed_at`; the consultation data (flows.md list) once it exists.
- **Never included:** password hashes, token or credential hashes, media (deleted within 24 h), or another principal's data.

## Consequences

- Easier: one table answers "how long do we keep X" for the Privacy notice (E1-21), reviewers and the `db-migration` skill. Deletion and export reach new tables through registered handlers without changing E1-09. Backups need no rewrite tooling.
- Harder:
  - Every new user-data table ships delete and export handlers and a row in this table (rule R9).
  - We own the purge jobs, the ledger and its replay.
  - A restore without the replay would break erasure, so the restore runbook must not skip it.
  - Deleted data sits in encrypted backups for up to 30 days, and the Privacy notice says so.
  - The API needs write access to one directory on the external disk.
- We will monitor:
  - Expired guests left after each purge run: must be 0 (data-deletion SLO).
  - Failed ledger-file appends.
  - Media objects older than 24 h (ADR-008).
  - Backup files older than 30 days: must be 0 (E1-23).
- Revisit when:
  - We approach external beta: review whether accounts may be kept forever while dormant (owner decision, a trigger for review only, not a change).
  - E2 finds Sentry, PostHog or Langfuse retention or deletion differs from this table.
  - Backups move off-site or to the cloud.
  - E3 needs checkpoints kept longer than 7 days.
  - E1-17 adds email (confirmation of deletion or export).
