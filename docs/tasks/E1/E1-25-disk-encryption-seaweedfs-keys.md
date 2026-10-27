# E1-25 · Encryption at rest: host disk and SeaweedFS keys off the data disk (before external beta)

| Field | Value |
| --- | --- |
| Status | todo (backlog: before external beta; not part of the E1 demo) |
| Owner | security-engineer (verification and proposal) → platform-engineer (Compose change) |
| Reviewers | code-reviewer, security-engineer |
| Estimate | M |
| Metric | n/a — security control for threat D4; no product metric or SLO moves |
| Depends on | E1-04 |
| ADRs | 008 ("a stolen disk must not expose them"), 015; a new ADR if the fix conflicts with ADR-008 |
| Design spec | none |

## Why

Threat D4 in `docs/security.md`: if someone steals the home PC's disk, they must not be able to read user data or media. ADR-008 requires that SeaweedFS encryption keys are not exposed by a stolen disk, but today they sit on the same data volume.

## Acceptance criteria

- [ ] The owner confirms host disk encryption is on. Windows 11 Home has no BitLocker, only Device Encryption where the hardware supports it (D4). If the hardware doesn't support it, the card records that and proposes an alternative to the owner. The confirmation and date are recorded in Decisions, with no recovery key or screenshot of one.
- [ ] SeaweedFS encryption keys are moved off the data disk, as ADR-015 requires (for example injected at start and never written to `seaweed_data`). If that is impossible, another fix that meets ADR-008's "a stolen disk must not expose them" is proposed. A fix that changes ADR-008's meaning becomes a new ADR, not a workaround.
- [ ] `check-seaweedfs.sh` still passes, media written before the change are still readable (or the migration plan for them is documented), and the stack restarts unattended after a reboot.
- [ ] Proof: with the stack stopped, a search of the data volume finds no key material. The command and result are in Numbers.
- [ ] Tests: `make up`, `check-seaweedfs.sh`, the CI `stack` job green.
- [ ] ADR-015: `env-init.sh` renders `secrets/seaweedfs_security.toml`, mounted as a file secret at `/etc/seaweedfs/security.toml`; the `configs:` block is gone and `seaweedfs` runs with `read_only: true`; `check-seaweedfs.sh` still passes.

## Allowed files

- `infra/compose/**`, `docs/runbooks/compose-stack.md`, `docs/adr/0xx-*.md` and `docs/adr/README.md` (only if a new ADR is needed)
- ADR-015: `.env.example` (remove `SEAWEEDFS_JWT_SIGNING_KEY` and `SEAWEEDFS_JWT_FILER_SIGNING_KEY`); `.github/workflows/ci.yml` (`stack` job, only if SeaweedFS needs more than the generic `secrets/` masking); `docs/runbooks/secret-leak.md` (SeaweedFS rows)

## Out of scope

- Field encryption of the email (E1-24). Postgres backups (E1-23). SeaweedFS image bumps.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27: amended from E1-01 threat model (docs/security.md), threat D4. Split out of E1-24. The owner's disk-encryption check was already pending from E0 (it blocks the media card).
- Numbers:
- Left for later:
