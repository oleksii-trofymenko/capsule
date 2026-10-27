# E1-29 · `.env` must never exist with an unverified Windows ACL

| Field | Value |
| --- | --- |
| Status | done |
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

- [x] On Windows, a `.env` created by a run never exists with an unverified ACL: either it is created only after the layout succeeds, or it is restricted before it is moved into place, or the run removes it on failure (as it already does for a JWT key created in a failed run). The plan picks one.
- [x] Proof: make the layout step fail on a run that creates `.env` (for example a broken `whoami.exe` on `PATH`); afterwards there is no `.env`, or its ACL holds only the user SID and SYSTEM. The command and result are in Numbers.
- [x] Tests: the proof above in Git Bash on Windows; an existing `.env` is never removed by a failed run; the CI `stack` job green.

## Allowed files

- `infra/compose/env-init.sh`, `docs/runbooks/compose-stack.md`

## Out of scope

- `secrets/` (already handled since E1-05b). A `.env` the user copied in by hand (already re-checked on every successful run).

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-27 (Orchestrator), platform-engineer plan, option 2 (restrict before the move). PR #33.
- Decisions:
  - 2026-10-27 (plan): option 2. Options 1 and 3 still left a window, and neither fixed a second gap found while planning: on `main` the append path (`cp .env tmp`, then `mv tmp .env`) swapped a restricted `.env` for one with the folder's inherited ACL (Administrators included). Every `mv` onto `.env` now comes from a restricted temp file.
  - 2026-10-27 (security review L1): on Windows the temp file is created inside the already-restricted `secrets/`, so it never has a broader ACL, not even before `restrict_file`. It is the same volume, so `mv` is a rename and keeps the protected DACL (works on Git Bash `noacl` mounts). Linux and `generate-only` keep the temp file in the repo root.
  - 2026-10-27: an append run now silently drops an extra explicit entry on `.env` (it takes the clean temp-file ACL); a run with nothing to append still stops with "also grants access". On an unsupported OS (macOS, Cygwin) the script now stops before creating `.env`.
  - 2026-10-27 (review): code-reviewer and security-engineer approved after one fix round (temp file in `secrets/`, `.acl.tmp` in the trap, runbook lines on appends and editor backup files).
  - Filed 2026-10-27 from the E1-05b re-review (N3); narrowed after the PR #30 review to the window before the layout step.
- Numbers:
  - PR 2 files, +89 / −52. Builder Windows checks: main fails 6 of 36; the branch passes 62 of 62 (including icacls failing on the temp file itself, and a leftover temp file).
  - `make up` from a clean export, warm build cache: 16.1 s (main) → 8.1 s fresh, 6.4 s second run (noise; the script adds one icacls pair and one check).
  - QA 2026-10-27 (qa-engineer, head b038dce, own checks, project `capsule-e129-qa`): pass.
    - Fresh run with 5 fake `whoami.exe` variants: no `.env`, no `secrets/`, no temp files.
    - icacls failing at each of its 11 calls: calls 1–5 leave no `.env`; calls 6–11 leave `.env` as `D:PAI` with only SYSTEM and the user, and remove the new key. icacls that "succeeds" but does nothing is caught by the check (`also grants access to 'BA'`).
    - Existing restricted `.env` with a failure at each call: sha256, ACL and key unchanged in all 12 runs.
    - Happy path: `/v1/ready` 200 after 8 s; second run 7 s, hashes unchanged.
    - Linux container: fresh, second and `generate-only` runs give `.env` 600, `secrets/` 700, key `root:10001 440`, identical to main.
- Left for later:
  - E1-32: `acl_check` does not check the file owner; WSL on `/mnt/c` takes the Linux path with no permission effect; a `secrets/.env.tmp.*` left by a killed run holds a copy of the secrets and is never deleted (restricted and checked on every run); a `secrets/` junction to another drive would turn `mv` into a copy.
