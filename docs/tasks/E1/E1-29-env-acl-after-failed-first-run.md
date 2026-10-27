# E1-29 · `.env` must never exist with an unverified Windows ACL

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — security control for ADR-015 file permissions; no product metric or SLO moves |
| Depends on | none |
| ADRs | 015 |
| Design spec | none |

## Why

`env-init.sh` moves a new `.env` into place before the Windows layout step runs. If that run then fails (for example `whoami.exe` fails or the SID check stops it), `.env` keeps the folder's inherited ACL until a later run gets past the layout step, and a run that keeps failing the same way never does (E1-05b re-review, N3). Every successful run already re-applies and checks the ACL of an existing `.env` (since E1-05b), and on Linux `.env` is born 0600 under `umask 077`.

## Acceptance criteria

- [ ] On Windows, a `.env` created by a run never exists with an unverified ACL: either it is created only after the layout succeeds, or it is restricted before it is moved into place, or the run removes it on failure (as it already does for a JWT key created in a failed run). The plan picks one.
- [ ] Proof: make the layout step fail on a run that creates `.env` (for example a broken `whoami.exe` on `PATH`); afterwards there is no `.env`, or its ACL holds only the user SID and SYSTEM. The command and result are in Numbers.
- [ ] Tests: the proof above in Git Bash on Windows; an existing `.env` is never removed by a failed run; the CI `stack` job green.

## Allowed files

- `infra/compose/env-init.sh`, `docs/runbooks/compose-stack.md`

## Out of scope

- `secrets/` (already handled since E1-05b). A `.env` the user copied in by hand (already re-checked on every successful run).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05b re-review (N3); narrowed after the PR #30 review to the window before the layout step.
- Numbers:
- Left for later:
