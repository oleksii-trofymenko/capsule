# E1-32 · env-init on Windows: file owner, WSL, leftover temp files

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — security control for ADR-015 file permissions; no product metric or SLO moves |
| Depends on | E1-29 |
| ADRs | 015 |
| Design spec | none |

## Why

The E1-29 reviews and QA left four edge cases in `infra/compose/env-init.sh` (ADR-015 file layout). None is reachable on the owner's normal setup (Git Bash, repo under the user profile), but each can break the "only the user and SYSTEM can read `.env` and `secrets/`" rule without any warning.

## Acceptance criteria

- [ ] Owner (E1-29 security L2): on Windows, `.env`, `secrets/` and every file in it must be owned by the current user SID. Another owner stops `make up` with a message that names the file, never its content. (`icacls /save` writes no owner; read it another way, for example `icacls` output with `/q` or PowerShell `Get-Acl`.)
- [ ] WSL (E1-29 security L3): `make up` from WSL on a Windows drive (`/mnt/<x>`, drvfs) stops with a message pointing to Git Bash, because `chmod` has no effect there. WSL on its own Linux file system keeps the Linux path.
- [ ] Leftover temp files (E1-29 QA): a `secrets/.env.tmp.*` left by a killed run is deleted on the next successful run, after `.env` is in place. The runbook line "removed on exit" says what happens after a kill.
- [ ] Junction (E1-29 code review): `secrets/` that is a symlink or junction stops the run, so `mv` from it to `.env` is always a same-volume rename.
- [ ] Tests: each case reproduced in Git Bash on a `mktemp -d` copy (owner via a file created by another account or `icacls /setowner` where possible; WSL by faking the drvfs check), the E1-29 checks still pass, the CI `stack` job green.

## Allowed files

- `infra/compose/env-init.sh`, `docs/runbooks/compose-stack.md`

## Out of scope

- Linux owner checks (already handled by the `root:<GID>` layout). `generate-only` on Windows.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-29 reviews (security L2, L3; code review junction note) and QA (leftover temp file).
- Numbers:
- Left for later:
