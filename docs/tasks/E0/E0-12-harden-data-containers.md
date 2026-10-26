# E0-12 · Harden the data service containers

| Field | Value |
| --- | --- |
| Status | todo |
| Owner | platform-engineer |
| Reviewers | code-reviewer, security-engineer |
| Estimate | S |
| Metric | n/a — security hardening of the local stack |
| Depends on | E0-07 |
| ADRs | 008, 019 |
| Design spec | none |

## Why

Security review of E0-07 found that postgres, redis and seaweedfs keep Docker's default capabilities and SeaweedFS runs as root. A compromised data service has more power inside its container than it needs.

## Acceptance criteria

- [ ] postgres, redis and seaweedfs run with `cap_drop: [ALL]` plus only the capabilities each entrypoint needs (documented per service).
- [ ] SeaweedFS runs as a non-root user if volume ownership allows; otherwise the reason is recorded.
- [ ] `make up` -> `/v1/ready` 200 and `check-seaweedfs.sh` pass; data survives `make down`/`make up`.
- [ ] Tests: `make test` and CI green.

## Allowed files

- `infra/compose/**`, `docs/runbooks/compose-stack.md`

## Out of scope

- Secrets management (ADR-015). Image version bumps.

## Analytics events

- none

## Notes (filled while working)

- Plan approved:
- Decisions:
  - Filed 2026-10-26 from the E0-07 reviews.
- Numbers:
- Left for later:
