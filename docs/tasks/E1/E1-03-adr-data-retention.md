# E1-03 · Data retention, deletion and export ADR and the data-deletion SLO

| Field | Value |
| --- | --- |
| Status | todo |
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

- [ ] A new ADR, written from `000-template.md` and accepted by the owner, records the owner decisions below and also covers:
  - [ ] A retention table: guest data, account data, sessions and refresh tokens (including revoked ones), rate-limit keys, logs, Postgres backups, media (link ADR-008), and the TTL for LangGraph checkpoints (E3).
  - [ ] Guest data: deleted 30 days after last activity. The upper bound is 30; the actual value comes from config. A clear definition of "last activity".
  - [ ] Accounts are never deleted automatically. They are deleted only on "Delete my data".
  - [ ] Postgres backups are kept for at most 30 days, so deleted data leaves backups within 30 days. Media are never backed up (ADR-008).
  - [ ] "Delete my data": the server deletion finishes before the response. The ADR states what is deleted (flows.md list) and what is removed outside our database (PostHog person, Sentry; the per-id Sentry check stays with E2).
  - [ ] Export: format, contents, and the same terms as deletion.
- [ ] `docs/metrics.md` (Engineering) gains the data-deletion SLO: "Data deletion: 100% of 'Delete my data' requests complete on the server before the app confirms; 0 guest records older than the retention period + 24 h". Measured by integration tests (E1-09) and a purge-job metric counting expired guests left after each run (E1-10).
- [ ] `docs/security.md` data-policy section links the ADR.
- [ ] `docs/adr/README.md` index row added.
- [ ] Tests: none (docs). `make lint` passes.

## Allowed files

- `docs/adr/022-data-retention-deletion-export.md`, `docs/adr/README.md` (022 row only), `docs/metrics.md` (data-deletion row only), `docs/security.md` (§6 Retention and the A8 row only), and the acceptance-criteria and Allowed-files lines named by ADR-022 in `docs/tasks/E1/E1-05-auth-module-guest-credential.md`, `docs/tasks/E1/E1-07-sign-up-sign-in-api.md`, `docs/tasks/E1/E1-08-rate-limiting.md`, `docs/tasks/E1/E1-09-delete-and-export-api.md`, `docs/tasks/E1/E1-10-guest-retention-purge-job.md`, `docs/tasks/E1/E1-15-cloudflare-quick-tunnel.md`, `docs/tasks/E1/E1-23-postgres-backups.md`

## Out of scope

- The purge job, delete and export endpoints (E1-09, E1-10), and the backup job itself (home-server operations, later card).
- Changing `docs/design/flows.md` or copy. `{retention_days}` stays a placeholder, filled from config.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan.
  - 2026-10-27, owner: guest data is deleted 30 days after last activity. Accounts are never deleted automatically. Postgres backups are kept for at most 30 days.
  - 2026-10-27, owner: sign-up uses email and password, with no email sending in E1 (no verification, no reset). So there is no way to reach a user by email, and the ADR must not rely on email for deletion or export confirmation.
  - 2026-10-27, owner: self-declared "I'm 18 or older" at sign-up. Store at most a confirmation timestamp, never a birth date.
  - 2026-10-27: amended from E1-01 threat model (docs/security.md). The backup job is now card E1-23.
- Numbers:
- Left for later:
  - Daily Postgres backup job with ≤ 30-day rotation (blueprint §12): card E1-23.
