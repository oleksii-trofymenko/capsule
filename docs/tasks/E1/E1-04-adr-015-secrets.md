# E1-04 · ADR-015: secrets handling

| Field | Value |
| --- | --- |
| Status | done |
| Owner | platform-engineer (drafts with the `adr` skill); the owner accepts |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | Secrets in repository = 0 (gitleaks in pre-commit and CI) |
| Depends on | E1-01 |
| ADRs | 015 (planned → accepted) |
| Design spec | none |

## Why

E1 adds the first long-lived application secrets: JWT signing keys, and later the email-provider key (E1-17). Today `make up` writes random secrets into `.env`. ADR-015 decides whether that is enough on the home PC, and how keys are stored and rotated, before E1-05 starts reading them.

## Acceptance criteria

- [x] `docs/adr/015-*.md` is written from `000-template.md`, with alternatives (plain `.env`, Docker secrets, SOPS), and accepted by the owner. It decides:
  - [x] Where secrets live locally, in CI and in the future cloud (the cloud part is a config change, not code).
  - [x] How JWT signing keys are created and rotated, and how a key id lets old tokens validate during rotation.
  - [x] What `make up` / `env-init.sh` must generate, and that no secret ever appears in logs, Compose output or CI artefacts.
  - [x] €0: no paid vault.
- [x] `docs/adr/README.md` index row updated.
- [x] Tests: none (docs). `make lint` passes.

## Allowed files

- `docs/adr/015-*.md`, `docs/adr/README.md` (index row only); the ADR-015 criterion and Allowed files lines only in `docs/tasks/E1/E1-05-auth-module-guest-credential.md`, `docs/tasks/E1/E1-08-rate-limiting.md`, `docs/tasks/E1/E1-17-password-reset-email.md`, `docs/tasks/E1/E1-23-postgres-backups.md`, `docs/tasks/E1/E1-24-email-field-encryption.md`, `docs/tasks/E1/E1-25-disk-encryption-seaweedfs-keys.md`

## Out of scope

- Implementing key generation (E1-05 changes `env-init.sh` if the ADR requires it). Cloud vault setup.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator). platform-engineer drafted the text without editing files (shared checkout); the Orchestrator wrote it to disk.
- Decisions:
  - Filed 2026-10-27 from the approved E1 plan. 2026-10-27: the Orchestrator keeps ADR-015 in E1.
  - The E1 quick tunnel needs no tunnel token (E1-15), so the first secrets in scope are the JWT keys.
  - 2026-10-27, owner: no pepper; `age` for backups; off-host copies of the age identity and the email keys in the owner's password manager plus a USB stick; 90-day manual JWT rotation; infra credentials stay in `.env`; repo outside OneDrive.
  - 2026-10-27: per-service Compose file secrets in `secrets/`; Linux layout `root:<consumer GID>` 0440 via sudo (CI uses it too); Windows `icacls` user SID + SYSTEM, verified on Docker Desktop 29.8.2; JWT keys mounted into `api` only.
- Numbers: ADR-015, 6 cards amended. Review: code-reviewer request changes (3 blockers) then approve; security-engineer approve with 2 mediums, folded in, then approve.
- Left for later:
  - E2: add the PostHog personal API key and the Sentry auth token to the inventory.
  - E1-05 must confirm `docker compose config --quiet` passes on the CI runner's Compose version with no `secrets/` files.
