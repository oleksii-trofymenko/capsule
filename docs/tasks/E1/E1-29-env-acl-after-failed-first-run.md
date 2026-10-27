# E1-29 · `.env` from a failed first run keeps its inherited Windows ACL

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

If the first `make up` on Windows writes `.env` and then fails before the `icacls` step, the file keeps the folder's inherited ACL. Later runs see that `.env` exists and skip generation, so the restriction may never be applied (E1-05b re-review, N3; the gap predates E1-05b).

## Acceptance criteria

- [ ] On Windows, every `make up` restricts an existing `.env` to the user SID and SYSTEM (or stops with the SDDL check), not only the run that created it. Same for Linux mode `0600`.
- [ ] Or: `.env` is written to a temp file in the same folder, restricted, then renamed into place, so a failed run leaves no `.env`. Pick one in the plan.
- [ ] Proof: simulate a failure after `.env` is written; the next run leaves `.env` with only the user and SYSTEM entries.
- [ ] Tests: the proof above in Git Bash on Windows; the Linux branch in a container; the CI `stack` job green.

## Allowed files

- `infra/compose/env-init.sh`, `docs/runbooks/compose-stack.md`

## Out of scope

- `secrets/` (already re-checked on every run since E1-05b).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E1-05b re-review (N3).
- Numbers:
- Left for later:
