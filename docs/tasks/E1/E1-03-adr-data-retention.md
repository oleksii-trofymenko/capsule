# E1-03 · Data retention, deletion and export ADR and the data-deletion SLO

| Field | Value |
| --- | --- |
| Status | done |
| Owner | security-engineer (drafts with the `adr` skill); the owner accepts |
| Reviewers | code-reviewer, product-analyst (metric) |
| Estimate | S |
| Metric | Decisions on record (every stack choice has an accepted ADR) |
| Depends on | E1-01 |
| ADRs | new ADR (next free number, expected 022); 008 (media, existing) |
| Design spec | `docs/design/flows.md` (F6 "Guest data", F10) |

## Why

GDPR storage limitation needs a written retention period for every kind of data we hold, and flows.md needs one fixed `{retention_days}`. Sign-up, "Delete my data", the purge job and LangGraph checkpoints (E0-11 note) all read their rules from this ADR.

## Acceptance criteria

- [x] A new ADR, written from `000-template.md` and accepted by the owner, records the owner decisions below and also covers:
  - [x] A retention table: guest data, account data, sessions and refresh tokens (including revoked ones), rate-limit keys, logs, Postgres backups, media (link ADR-008), and the TTL for LangGraph checkpoints (E3).
  - [x] Guest data: deleted 30 days after last activity. The upper bound is 30; the actual value comes from config. A clear definition of "last activity".
  - [x] Accounts are never deleted automatically. They are deleted only on "Delete my data".
  - [x] Postgres backups are kept for at most 30 days, so deleted data leaves backups within 30 days. Media are never backed up (ADR-008).
  - [x] "Delete my data": the server deletion finishes before the response. The ADR states what is deleted (flows.md list) and what is removed outside our database (PostHog person, Sentry; the per-id Sentry check stays with E2).
  - [x] Export: format, contents, and the same terms as deletion.
- [x] `docs/metrics.md` (Engineering) gains the data-deletion SLO: "Data deletion: 100% of 'Delete my data' requests complete on the server before the app confirms; 0 guest records older than the retention period + 24 h". Measured by integration tests (E1-09) and a purge-job metric counting expired guests left after each run (E1-10).
- [x] `docs/security.md` data-policy section links the ADR.
- [x] `docs/adr/README.md` index row added.
- [x] Tests: none (docs). `make lint` passes.

## Allowed files

- `docs/adr/022-data-retention-deletion-export.md`, `docs/adr/README.md` (022 row only), `docs/metrics.md` (data-deletion row only), `docs/security.md` (§6 Retention and the A8 row only), and the acceptance-criteria and Allowed-files lines named by ADR-022 in `docs/tasks/E1/E1-05-auth-module-guest-credential.md`, `docs/tasks/E1/E1-07-sign-up-sign-in-api.md`, `docs/tasks/E1/E1-08-rate-limiting.md`, `docs/tasks/E1/E1-09-delete-and-export-api.md`, `docs/tasks/E1/E1-10-guest-retention-purge-job.md`, `docs/tasks/E1/E1-15-cloudflare-quick-tunnel.md`, `docs/tasks/E1/E1-23-postgres-backups.md`

## Out of scope

- The purge job, delete and export endpoints (E1-09, E1-10), and the backup job itself (home-server operations, later card).
- Changing `docs/design/flows.md` or copy. `{retention_days}` stays a placeholder, filled from config.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator). security-engineer drafted the text; the Orchestrator wrote it to disk.
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: guest data is deleted 30 days after last activity. Accounts are never deleted automatically. Postgres backups are kept for at most 30 days.
  - 2026-10-27, owner: sign-up uses email and password, with no email sending in E1 (no verification, no reset). So there is no way to reach a user by email, and the ADR must not rely on email for deletion or export confirmation.
  - 2026-10-27, owner: self-declared "I'm 18 or older" at sign-up. Store at most a confirmation timestamp, never a birth date.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md). The backup job is now card E1-23.
  - 2026-10-27, owner: unsaved consultation history of an account is deleted per consultation, 30 days after its last activity.
  - 2026-10-27: deletion ledger (DB table plus a file on the backup disk) replayed on every restore; written by the guest-data move (E1-07) and "Delete my data" (E1-09); pruned only up to the oldest backup on disk (E1-23).
  - 2026-10-27: restore refuses backups older than 30 days and revokes every refresh family and rotates the JWT key before traffic.
  - 2026-10-27: Postgres runs terse with no statement logging; sign-up checks the email before insert; cloudflared at info with no access log.
- Numbers: ADR-022 with 18 data classes; data-deletion SLO added to `docs/metrics.md`. Review: code-reviewer request changes (2 blockers) then approve; security-engineer approve with 4 mediums, all folded in, then approve.
- Left for later:
  - E2: PostHog and Sentry per-id deletion; the ids sent with a delete request cannot be tied to the caller (accept in E2 or derive the analytics id server-side).
  - E1-17: make password and email changes survive a restore (ADR-022 revisit trigger).
  - Daily Postgres backup job with ≤ 30-day rotation (blueprint §12): card E1-23.
