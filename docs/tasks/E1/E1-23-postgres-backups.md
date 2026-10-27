# E1-23 · Postgres backups: daily, encrypted, kept for at most 30 days, with a restore drill

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | Backup restore (new engineering SLO, added to `docs/metrics.md` by this card): a backup at least every 24 h, the restore drill passes monthly |
| Depends on | E1-03, E1-04 |
| ADRs | 007, 008 (media never backed up), 015 (backup key), retention ADR (E1-03); a new ADR only if the encryption tool is not named in ADR-015 or blueprint §4 |
| Design spec | none |

## Why

As a user with an account, I want my saved guides to survive a disk failure on the home server, and I want deleted data to disappear from backups too. Blueprint §12 asks for daily backups with a monthly restore test, and the owner decided backups are kept for at most 30 days.

## Acceptance criteria

- [ ] A daily Postgres backup (logical dump), encrypted before it leaves the host, using a key handled as ADR-015 requires. The key is never stored next to the backups.
- [ ] Rotation: backups older than 30 days are deleted automatically (retention ADR). A test or script run proves that a 31-day-old file is removed and a 29-day-old file is kept.
- [ ] Media are never included. The backup covers only Postgres. A check fails if any volume labelled `capsule.backup: never` (`seaweed_data`) is part of the backup.
- [ ] The destination is configured by env (an external disk on the home PC first). It costs €0.
- [ ] Deletion ledger file (ADR-022): a ledger directory on the external disk, separate from the backup directory.
  - It is bind-mounted read-write into `api` only. The backup directory is never mounted into `api`.
  - NTFS cannot enforce append-only, so each backup run reconciles the file from the ledger table.
  - A missing disk never stops `api` from starting.
  - After rotation, the backup job prunes ledger entries in both the file and the table, removing only those older than the creation time of the oldest backup actually on disk.
  - A test on fake files proves no entry newer than the oldest backup is pruned.
- [ ] Restore drill: one documented command restores the latest backup into a throwaway Postgres and runs a sanity query. The first drill's time and size are recorded in Numbers.
- [ ] Every restore, the drill included, refuses a backup older than 30 days. Then, before the API takes traffic, it runs these steps in order (ADR-022):
  1. Replays the deletion ledger: the external file plus the restored table.
  2. Deletes any principal id found in API error-log lines for failed ledger appends made since the backup was created.
  3. Runs the guest purge, the per-consultation unsaved-history purge and the refresh-family sweep.
  4. Revokes every refresh family and rotates the JWT signing key with no overlap (ADR-015).
  - A test on fake data proves three things: a ledger principal is gone, an over-age backup is refused, and no refresh family survives.
- [ ] A failed backup is visible: a non-zero exit and a log line. A Grafana alert comes later in E2.
- [ ] `docs/metrics.md` gains the backup-restore SLO with how it is measured. The runbook describes backup, restore and key loss.
- [ ] Tests: the rotation and exclusion checks run in CI or `make test` on fake files; the drill runs once by hand on the home PC.

## Allowed files

- `infra/compose/**`, `infra/backup/**` (new), `docs/runbooks/postgres-backup.md` (new), `docs/metrics.md` (backup-restore row only), `Makefile` and `CLAUDE.md` Commands (only if a target is added, with Orchestrator approval), `docs/adr/0xx-*.md` and `docs/adr/README.md` (only if a new tool needs an ADR)

## Out of scope

- Off-site or cloud backups (owner decision 2026-10-27: not yet; external disk only until beta). Point-in-time recovery. Media backup (never, ADR-008).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27: amended from E1-01 threat model (docs/security.md). It replaces the "file a card" note in E1-03.
  - 2026-10-27, owner: Postgres backups are kept for at most 30 days.
- Numbers:
- Left for later:
