# E0-16 · Harden the throwaway S3 client containers

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — container hardening consistency (E0-12 baseline) |
| Depends on | E0-14 |
| ADRs | 008 |
| Design spec | none |

## Why

The short-lived containers that sign S3 requests in the CI `stack` job and in `check-seaweedfs.sh` run as root with default capabilities, unlike the services hardened in E0-12 (security-engineer, E0-14 review, rated low).

## Acceptance criteria

- [ ] Every throwaway `docker run` that talks to seaweedfs in `.github/workflows/ci.yml` (`stack` job) and `infra/compose/check-seaweedfs.sh` adds `--user 1000:1000 --cap-drop ALL --security-opt no-new-privileges:true`.
- [ ] The runbook repro snippets in `docs/runbooks/compose-stack.md` that start such containers do the same.
- [ ] `check-seaweedfs.sh` still passes all checks; the CI `stack` job still logs `s3: 200 kept`.
- [ ] Tests: `make lint` and CI green.

## Allowed files

- `.github/workflows/ci.yml` (`stack` job only), `infra/compose/check-seaweedfs.sh`, `docs/runbooks/compose-stack.md`

## Out of scope

- Changing the services themselves. Log redaction (E2-01).

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-27 from the E0-14 security review.
  - Also fold in a one-line runbook warning: the repro snippets break in Git Bash when `MSYS_NO_PATHCONV=1` is exported (E0-14 QA note).
- Numbers:
- Left for later:
